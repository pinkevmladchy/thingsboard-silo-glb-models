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
SILO_COLOR     = [0.72, 0.72, 0.72]
HARDWARE_COLOR = [0.32, 0.32, 0.34]
WAREHOUSE_COLOR = [0.72, 0.72, 0.72]
GROUND_COLOR   = [1.0, 1.0, 1.0]


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

    # ---- Warehouse (optional, default yes) ----
    # Place it to the left of the silos, with a small gap
    if cfg["add_warehouse"]:
        wh_w, wh_h, wh_d = 2.8, 1.4, 2.0
        # Leftmost silo's surface is at x0 - radius. Put warehouse another 1 unit left.
        wh_x = x0 - radius - 1.0 - wh_w / 2
        wh_z = 0.0

        body = trimesh.creation.box(extents=[wh_w, wh_h, wh_d])
        body.apply_translation([wh_x, wh_h / 2, wh_z])
        roof = trimesh.creation.box(extents=[wh_w + 0.15, 0.08, wh_d + 0.15])
        roof.apply_translation([wh_x, wh_h + 0.04, wh_z])
        warehouse = trimesh.util.concatenate([body, roof])
        warehouse.visual = unique_pbr("Warehouse_Mat", WAREHOUSE_COLOR,
                                       metallic=0.1, roughness=0.7, salt=999)
        scene.add_geometry(warehouse, node_name="Warehouse",
                           geom_name="Warehouse")

    # ---- Ground (optional, default yes) ----
    if cfg["add_ground"]:
        # Auto-size ground to comfortably contain everything
        gw = max(14, cols * sx + 8)
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
