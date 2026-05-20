#!/usr/bin/env python3
"""Build a multi-silo yard scene (silos + warehouse + ground) as GLB.

Silos are auto-arranged in a `rows × cols` grid centered at origin.
All silos in a grid share the same dimensions. Colors are fixed defaults.

Usage:
  python build_yard.py --rows 2 --cols 2 --output yard.glb
  python build_yard.py --rows 3 --cols 2 --radius 0.5 --body-h 1.6 --output yard.glb
  python build_yard.py --config config.json --output yard.glb
  python build_yard.py --rows 2 --cols 2 --no-warehouse --output yard.glb
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from silo_lib import build_silo_with_details, unique_pbr


# Fixed colors (linear PBR baseColorFactor, 0..1)
SILO_COLOR             = [0.72, 0.72, 0.72]
HARDWARE_COLOR         = [0.32, 0.32, 0.34]
WAREHOUSE_COLOR        = [0.78, 0.78, 0.80]   # light cool gray wall panels
WAREHOUSE_TRIM_COLOR   = [0.35, 0.38, 0.42]   # darker — ribs, roof, ridge
WAREHOUSE_DOORS_COLOR  = [0.45, 0.48, 0.52]   # medium gray rolling doors
GROUND_COLOR           = [1.0, 1.0, 1.0]


def build_industrial_warehouse(grid_x0, silo_radius):
    """Industrial warehouse — long, low, metal-clad, with rolling doors.

    Returns (wall_mesh, trim_mesh, door_mesh).
      - wall_mesh: solid wall body
      - trim_mesh: vertical ribs (metal cladding) + roof + horizontal vent strip
                   + door segments
      - door_mesh: two rolling doors on the front

    Placed left of the silo grid with a 1.2-unit gap from the leftmost silo.
    """
    # Warehouse proportions (wide and low, industrial)
    W, H, D = 4.4, 1.2, 1.6
    ridge_h = 0.18

    # Position to the LEFT of the silo grid
    x = grid_x0 - silo_radius - 1.2 - W / 2
    z = 0.0

    walls, trim, doors = [], [], []

    # ---- Main solid body ----
    body = trimesh.creation.box(extents=[W, H, D])
    body.apply_translation([x, H / 2, z])
    walls.append(body)

    # ---- Vertical ribs (metal cladding) on long sides ----
    rib_w, rib_d = 0.04, 0.025
    rib_h = H * 0.94
    n_ribs_long = 18
    for side_z in (-D / 2 - rib_d / 2, D / 2 + rib_d / 2):
        for i in range(n_ribs_long):
            rx = -W / 2 + (i + 0.5) * (W / n_ribs_long)
            rib = trimesh.creation.box(extents=[rib_w, rib_h, rib_d])
            rib.apply_translation([x + rx, rib_h / 2 + 0.02, z + side_z])
            trim.append(rib)

    # ---- Vertical ribs on short sides ----
    n_ribs_short = 6
    for side_x in (-W / 2 - rib_d / 2, W / 2 + rib_d / 2):
        for i in range(n_ribs_short):
            rz = -D / 2 + (i + 0.5) * (D / n_ribs_short)
            rib = trimesh.creation.box(extents=[rib_d, rib_h, rib_w])
            rib.apply_translation([x + side_x, rib_h / 2 + 0.02, z + rz])
            trim.append(rib)

    # ---- Mono-pitch roof slab + back ridge ----
    roof = trimesh.creation.box(extents=[W + 0.16, 0.06, D + 0.16])
    roof.apply_translation([x, H + 0.03, z])
    trim.append(roof)

    ridge = trimesh.creation.box(extents=[W + 0.16, 0.10, ridge_h])
    ridge.apply_translation([x, H + 0.05, z - D / 2 - 0.04])
    trim.append(ridge)

    # ---- Horizontal vent strip near roofline ----
    strip = trimesh.creation.box(extents=[W * 0.92, 0.06, D + 0.02])
    strip.apply_translation([x, H - 0.08, z])
    trim.append(strip)

    # ---- Two rolling doors on the front (+Z) wall ----
    door_w, door_h, door_t = 1.1, 0.95, 0.04
    door_y = door_h / 2 + 0.04
    door_z = z + D / 2 + door_t / 2 + 0.005

    for dx in (-W * 0.22, W * 0.22):
        door = trimesh.creation.box(extents=[door_w, door_h, door_t])
        door.apply_translation([x + dx, door_y, door_z])
        doors.append(door)

        # Horizontal segment lines on each door (roller panel look)
        for k in range(1, 5):
            seg_y = door_h * (k / 5)
            seg = trimesh.creation.box(extents=[door_w * 0.96, 0.018, 0.012])
            seg.apply_translation([x + dx, 0.04 + seg_y, door_z + 0.012])
            trim.append(seg)

    wall_mesh = trimesh.util.concatenate(walls)
    trim_mesh = trimesh.util.concatenate(trim)
    door_mesh = trimesh.util.concatenate(doors)
    return wall_mesh, trim_mesh, door_mesh


DEFAULTS = {
    "rows":         2,
    "cols":         2,
    "spacing_x":    1.5,
    "spacing_z":    1.5,
    "radius":       0.48,
    "body_h":       1.5,
    "cone_h":       0.25,
    "add_warehouse": True,
    "add_ground":    True,
}


def build_scene(config: dict) -> trimesh.Scene:
    cfg = {**DEFAULTS, **config}
    rows = int(cfg["rows"])
    cols = int(cfg["cols"])
    sx   = float(cfg["spacing_x"])
    sz   = float(cfg["spacing_z"])
    radius = float(cfg["radius"])
    body_h = float(cfg["body_h"])
    cone_h = float(cfg["cone_h"])

    scene = trimesh.Scene()

    # ---- Silos in a grid, centered at origin ----
    x0 = -(cols - 1) * sx / 2
    z0 = -(rows - 1) * sz / 2
    n = 1
    for row in range(rows):
        for col in range(cols):
            name = f"Silo.{n:03d}"
            x = x0 + col * sx
            z = z0 + row * sz

            n_rings = 9 if body_h >= 1.7 else 7
            silo_mesh, hw_mesh = build_silo_with_details(
                x, z, radius, body_h, cone_h,
                n_rings=n_rings, n_ribs=14,
                add_ladder=True, add_railing=True,
            )

            silo_mesh.visual = unique_pbr(f"{name}_Mat", SILO_COLOR,
                                           metallic=0.1, roughness=0.7, salt=n)
            scene.add_geometry(silo_mesh, node_name=name, geom_name=name)

            if hw_mesh is not None:
                hw_name = f"Hardware.{n:03d}"
                hw_mesh.visual = unique_pbr(f"{hw_name}_Mat", HARDWARE_COLOR,
                                             metallic=0.4, roughness=0.55, salt=n)
                scene.add_geometry(hw_mesh,
                                   node_name=hw_name,
                                   geom_name=hw_name)
            n += 1

    # ---- Industrial warehouse (long, low, metal-clad) ----
    # Placed to the LEFT of the silo grid with a small gap.
    if cfg["add_warehouse"]:
        wh_main, wh_trim, wh_doors = build_industrial_warehouse(x0, radius)

        wh_main.visual = unique_pbr("Warehouse_Mat", WAREHOUSE_COLOR,
                                      metallic=0.2, roughness=0.7, salt=999)
        scene.add_geometry(wh_main, node_name="Warehouse",
                           geom_name="Warehouse")

        wh_trim.visual = unique_pbr("Warehouse_Trim_Mat", WAREHOUSE_TRIM_COLOR,
                                      metallic=0.45, roughness=0.55, salt=998)
        scene.add_geometry(wh_trim, node_name="Warehouse_Trim",
                           geom_name="Warehouse_Trim")

        wh_doors.visual = unique_pbr("Warehouse_Doors_Mat", WAREHOUSE_DOORS_COLOR,
                                       metallic=0.4, roughness=0.5, salt=997)
        scene.add_geometry(wh_doors, node_name="Warehouse_Doors",
                           geom_name="Warehouse_Doors")

    # ---- Ground (optional, default yes) ----
    if cfg["add_ground"]:
        # Auto-size ground. Industrial warehouse is 4.4 wide + 1.2 gap from silos,
        # so the scene extends further left than before.
        gw = max(16, cols * sx + 12)
        gd = max(7,  rows * sz + 3)
        ground = trimesh.creation.box(extents=[gw, 0.02, gd])
        ground.apply_translation([0, -0.01, 0])
        ground.visual = unique_pbr("Ground_Mat", GROUND_COLOR,
                                    metallic=0.0, roughness=0.95, salt=1000)
        scene.add_geometry(ground, node_name="Ground", geom_name="Ground")

    return scene


def main():
    ap = argparse.ArgumentParser(description="Build a multi-silo yard GLB scene.")
    ap.add_argument("--output", "-o", required=True, help="Output .glb path")
    ap.add_argument("--config", help="JSON config file (overrides other flags)")
    ap.add_argument("--rows", type=int, help="Grid rows (default 2)")
    ap.add_argument("--cols", type=int, help="Grid cols (default 2)")
    ap.add_argument("--spacing-x", type=float, dest="spacing_x",
                    help="Center-to-center distance along X (default 1.5)")
    ap.add_argument("--spacing-z", type=float, dest="spacing_z",
                    help="Center-to-center distance along Z (default 1.5)")
    ap.add_argument("--radius", type=float, help="Silo radius (default 0.48)")
    ap.add_argument("--body-h", type=float, dest="body_h",
                    help="Silo body height (default 1.5)")
    ap.add_argument("--cone-h", type=float, dest="cone_h",
                    help="Silo cone roof height (default 0.25)")
    ap.add_argument("--no-warehouse", action="store_true", help="Skip the warehouse")
    ap.add_argument("--no-ground", action="store_true", help="Skip the ground plane")
    args = ap.parse_args()

    if args.config:
        config = json.loads(Path(args.config).read_text())
    else:
        config = {}
        for k in ("rows", "cols", "spacing_x", "spacing_z",
                  "radius", "body_h", "cone_h"):
            v = getattr(args, k)
            if v is not None:
                config[k] = v
        if args.no_warehouse: config["add_warehouse"] = False
        if args.no_ground:    config["add_ground"]    = False

    scene = build_scene(config)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.export(out)
    print(f"Wrote {out}")
    print("Meshes:")
    for name in scene.geometry:
        print(f"  {name}")


if __name__ == "__main__":
    main()
