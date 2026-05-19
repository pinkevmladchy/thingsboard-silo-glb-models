#!/usr/bin/env python3
"""Build a cutaway silo (single silo with a 90° wedge removed) as GLB.

Outputs these named meshes:
  - Silo.Cutaway          : shell + ceiling + cone roof + rings + ribs
  - Silo.Cutaway_Floor    : inner floor
  - Grain_Volume          : orange wavy grain heap (scale.y to control level)
  - Cable                 : vertical rod + mount cap (one mesh)
  - Sensor.001, .002, ... : individual sensor spheres (each with unique material)
  - Ground                : white ground plane

Usage:
  python build_cutaway.py --output cutaway.glb
  python build_cutaway.py --radius 1.2 --body-h 4.0 --output cutaway.glb
  python build_cutaway.py --sensors '[{"name":"Sensor.001","x":0,"y":2.5,"z":0}, ...]' \\
                          --output cutaway.glb
  python build_cutaway.py --config config.json --output cutaway.glb
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from silo_lib import (
    make_cutaway_silo_shell, make_cutaway_cone_roof, make_cutaway_floor,
    make_cutaway_torus, make_wavy_grain, unique_pbr,
)


# Fixed colors (linear PBR, 0..1)
SILO_COLOR    = [0.72, 0.72, 0.72]
FLOOR_COLOR   = [0.55, 0.55, 0.55]
GRAIN_COLOR   = [0.94, 0.55, 0.20]
SENSOR_COLOR  = [0.15, 0.70, 0.78]
CABLE_COLOR   = [0.18, 0.18, 0.18]
GROUND_COLOR  = [1.0, 1.0, 1.0]


DEFAULTS = {
    "radius":         1.0,
    "body_h":         3.0,
    "cone_h":         0.5,
    "wall":           0.05,
    "floor_t":        0.08,
    "grain_h":        2.70,    # heap peak stays below cylinder top (3.0)
    "grain_amp":      0.08,
    "grain_bump":     0.12,
    "n_rings":        9,
    "n_ribs":         14,
    "cut_start":      -45,     # 90° wedge total
    "cut_end":         45,
    "sensor_radius":  0.09,
    "add_cable":      True,
    "add_ground":     True,
    "cable_radius":   0.012,
}


def build_cutaway(config: dict) -> trimesh.Scene:
    cfg = {**DEFAULTS, **config}
    R       = float(cfg["radius"])
    H_BODY  = float(cfg["body_h"])
    H_CONE  = float(cfg["cone_h"])
    WALL    = float(cfg["wall"])
    FLOOR_T = float(cfg["floor_t"])
    GRAIN_H = float(cfg["grain_h"])
    CUT_START = float(cfg["cut_start"])
    CUT_END   = float(cfg["cut_end"])

    scene = trimesh.Scene()

    # ---- Silo body parts (one merged mesh) ----
    silo_parts = []

    shell = make_cutaway_silo_shell(R, H_BODY, WALL, sections=64,
                                     cut_start_deg=CUT_START, cut_end_deg=CUT_END)
    silo_parts.append(shell)

    # Horizontal ceiling (separates grain from the cone visually)
    ceiling = make_cutaway_floor(R - WALL * 0.5, thickness=0.04, sections=64,
                                  cut_start_deg=CUT_START, cut_end_deg=CUT_END)
    ceiling.apply_translation([0, H_BODY - 0.04, 0])
    silo_parts.append(ceiling)

    roof = make_cutaway_cone_roof(R, H_CONE, sections=64,
                                   cut_start_deg=CUT_START, cut_end_deg=CUT_END)
    roof.apply_translation([0, H_BODY, 0])
    silo_parts.append(roof)

    # Corrugation rings (back-half arc)
    ring_minor = 0.025
    for hy in np.linspace(H_BODY * 0.06, H_BODY * 0.94, int(cfg["n_rings"])):
        t = make_cutaway_torus(major_r=R * 1.005, minor_r=ring_minor,
                                major_seg=64, minor_seg=8,
                                cut_start_deg=CUT_START, cut_end_deg=CUT_END)
        t.apply_translation([0, hy, 0])
        silo_parts.append(t)

    # Vertical ribs — only on the BACK half (outside the cut)
    rib_w, rib_d = 0.04, 0.03
    cs, ce = np.deg2rad(CUT_START), np.deg2rad(CUT_END)
    def in_cut(a):
        a = ((a + np.pi) % (2 * np.pi)) - np.pi
        return cs <= a <= ce
    n_ribs = int(cfg["n_ribs"])
    for i in range(n_ribs):
        ang = 2 * np.pi * i / n_ribs
        if in_cut(ang):
            continue
        rx = (R + rib_d * 0.4) * np.cos(ang)
        rz = (R + rib_d * 0.4) * np.sin(ang)
        rib = trimesh.creation.box(extents=[rib_w, H_BODY * 0.98, rib_d])
        rot = trimesh.transformations.rotation_matrix(-ang, [0, 1, 0])
        rib.apply_transform(rot)
        rib.apply_translation([rx, H_BODY * 0.49, rz])
        silo_parts.append(rib)

    silo_body = trimesh.util.concatenate(silo_parts)
    silo_body.visual = unique_pbr("Silo.Cutaway_Mat", SILO_COLOR,
                                    metallic=0.1, roughness=0.7, salt=0)
    scene.add_geometry(silo_body, node_name="Silo.Cutaway",
                       geom_name="Silo.Cutaway")

    # ---- Floor ----
    floor = make_cutaway_floor(R - WALL, thickness=FLOOR_T, sections=64,
                                cut_start_deg=CUT_START, cut_end_deg=CUT_END)
    floor.visual = unique_pbr("Silo.Cutaway_Floor_Mat", FLOOR_COLOR,
                                metallic=0.0, roughness=0.85, salt=1)
    scene.add_geometry(floor, node_name="Silo.Cutaway_Floor",
                       geom_name="Silo.Cutaway_Floor")

    # ---- Grain ----
    grain = make_wavy_grain(R - WALL, base_height=GRAIN_H, sections=64,
                             cut_start_deg=CUT_START, cut_end_deg=CUT_END,
                             wave_amp=float(cfg["grain_amp"]),
                             n_radial_waves=3, n_angular_waves=5,
                             center_bump=float(cfg["grain_bump"]))
    grain.apply_translation([0, FLOOR_T, 0])
    grain.visual = unique_pbr("Grain_Volume_Mat", GRAIN_COLOR,
                                metallic=0.0, roughness=0.95,
                                double_sided=True, salt=2)
    scene.add_geometry(grain, node_name="Grain_Volume",
                       geom_name="Grain_Volume")

    # ---- Sensors ----
    sensors = cfg.get("sensors")
    if sensors is None:
        # Default: 3 sensors centered on Y axis, evenly spaced
        sensors = [
            {"name": "Sensor.001", "x": 0, "y": H_BODY * 0.83, "z": 0},
            {"name": "Sensor.002", "x": 0, "y": H_BODY * 0.50, "z": 0},
            {"name": "Sensor.003", "x": 0, "y": H_BODY * 0.17, "z": 0},
        ]

    sensor_radius = float(cfg["sensor_radius"])
    for i, s in enumerate(sensors):
        name = s.get("name", f"Sensor.{i+1:03d}")
        sphere = trimesh.creation.icosphere(subdivisions=3, radius=sensor_radius)
        sphere.apply_translation([float(s.get("x", 0)),
                                   float(s.get("y", 0)),
                                   float(s.get("z", 0))])
        sphere.visual = unique_pbr(f"{name}_Mat", SENSOR_COLOR,
                                     metallic=0.2, roughness=0.5,
                                     salt=10 + i)
        scene.add_geometry(sphere, node_name=name, geom_name=name)

    # ---- Sensor cable (rod + top cap as ONE mesh) ----
    if cfg["add_cable"] and sensors:
        top_y = max(float(s.get("y", 0)) for s in sensors)
        cable_top_y = top_y + 0.25
        cable_bottom_y = FLOOR_T
        cable_h = cable_top_y - cable_bottom_y
        cable_r = float(cfg["cable_radius"])

        rod = trimesh.creation.cylinder(radius=cable_r, height=cable_h, sections=24)
        rod.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        rod.apply_translation([0, cable_bottom_y + cable_h / 2, 0])

        cap = trimesh.creation.cylinder(radius=cable_r * 2.5, height=0.04, sections=24)
        cap.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        cap.apply_translation([0, cable_top_y + 0.02, 0])

        cable = trimesh.util.concatenate([rod, cap])
        cable.visual = unique_pbr("Cable_Mat", CABLE_COLOR,
                                    metallic=0.4, roughness=0.5, salt=100)
        scene.add_geometry(cable, node_name="Cable", geom_name="Cable")

    # ---- Ground ----
    if cfg["add_ground"]:
        ground = trimesh.creation.box(extents=[6, 0.02, 6])
        ground.apply_translation([0, -0.01, 0])
        ground.visual = unique_pbr("Ground_Mat", GROUND_COLOR,
                                     metallic=0.0, roughness=0.95, salt=200)
        scene.add_geometry(ground, node_name="Ground", geom_name="Ground")

    return scene


def main():
    ap = argparse.ArgumentParser(description="Build a cutaway silo GLB.")
    ap.add_argument("--output", "-o", required=True)
    ap.add_argument("--config", help="JSON config file (overrides other flags)")
    ap.add_argument("--radius", type=float, help="Silo radius (default 1.0)")
    ap.add_argument("--body-h", type=float, dest="body_h",
                    help="Cylinder body height (default 3.0)")
    ap.add_argument("--cone-h", type=float, dest="cone_h",
                    help="Cone roof height (default 0.5)")
    ap.add_argument("--grain-h", type=float, dest="grain_h",
                    help="Grain base fill height (default 2.7)")
    ap.add_argument("--sensors", help="JSON list of sensor specs: [{name,x,y,z}, ...]")
    ap.add_argument("--no-cable", action="store_true",
                    help="Skip the central sensor cable")
    ap.add_argument("--no-ground", action="store_true",
                    help="Skip the ground plane")
    args = ap.parse_args()

    if args.config:
        config = json.loads(Path(args.config).read_text())
    else:
        config = {}
        for k in ("radius", "body_h", "cone_h", "grain_h"):
            v = getattr(args, k)
            if v is not None:
                config[k] = v
        if args.sensors:
            config["sensors"] = json.loads(args.sensors)
        if args.no_cable:  config["add_cable"]  = False
        if args.no_ground: config["add_ground"] = False

    scene = build_cutaway(config)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.export(out)
    print(f"Wrote {out}")
    print("Meshes:")
    for name in scene.geometry:
        print(f"  {name}")


if __name__ == "__main__":
    main()
