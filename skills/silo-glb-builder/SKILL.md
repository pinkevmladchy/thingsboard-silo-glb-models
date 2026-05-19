---
name: silo-glb-builder
description: Generate GLB 3D models of grain silos for Angular/three.js apps — either a multi-silo yard scene (silos auto-arranged in a grid + warehouse) or a single cutaway silo with sensors and adjustable grain level. Use this skill whenever the user asks to create, generate, build, or export a silo .glb file; whenever they want a 3D grain silo for an Angular/Three.js viewer; whenever they mention silos with sensors, grain volume, temperature monitoring, or 3D agriculture/elevator visualizations; or whenever they want to control silo count, sizes, or sensor layout in a 3D model. Trigger even if they don't say "GLB" explicitly — phrases like "build me a 3D silo model" or "I need a silo scene for my app" are enough.
---

# Silo GLB Builder

Generates two types of glTF/GLB 3D models for grain silo dashboards:

1. **`yard`** — A scene with N silos auto-arranged in a `rows × cols` grid + one warehouse. Used for overview dashboards.
2. **`cutaway`** — A single silo with a 90° wedge cut out, showing the floor, grain volume, and N sensors on a vertical cable. Used for inspecting one silo in detail.

Colors and materials are **fixed defaults** — silos and warehouse are light gray, hardware (ladders/railings) is dark gray, grain is orange, sensors are teal, ground is white. The Angular client can change colors at runtime — this skill just produces the geometry.

---

## Quick start

For a `yard` scene with auto-arranged silos:
```bash
python scripts/build_yard.py --rows 2 --cols 2 --output yard.glb
```

For a `cutaway` with default 3 sensors:
```bash
python scripts/build_cutaway.py --output cutaway.glb
```

With custom dimensions / sensors:
```bash
python scripts/build_cutaway.py \
  --radius 1.2 --body-h 4.0 \
  --sensors '[{"name":"Sensor.001","x":0,"y":3.5,"z":0}, ...]' \
  --output cutaway.glb
```

For anything beyond defaults, pass `--config <file.json>`. See `references/yard.md` and `references/cutaway.md` for full schemas.

---

## Workflow

When a user asks for a silo model:

### 1. Decide which type

- **A scene of multiple silos** (a "silo yard", "farm", "facility overview", "we have N silos") → use `build_yard.py`
- **A single silo opened up to show what's inside** (a "cutaway", "section view", "silo with sensors", "internal view") → use `build_cutaway.py`

If unclear, ask: "Should this be an overview scene with several silos, or a detailed cutaway of one silo showing the inside?"

### 2. Gather the few parameters that matter

For a **yard**:
- Number of silos → `rows × cols` (grid is centered around origin)
- Per-silo size: radius, body height, cone height (all have defaults)
- Include the warehouse? (default yes)

For a **cutaway**:
- Silo dimensions: radius, body height, cone height (defaults exist)
- Sensors: how many and where in local silo coordinates (defaults to 3 evenly-spaced on center axis)
- Include the central sensor cable? (default yes)

Defaults are documented in the reference files. If the user gives partial info, fill in sane defaults and tell them what you chose.

### 3. Run the script

For simple cases, CLI flags are enough:
```bash
python scripts/build_yard.py --rows 3 --cols 2 --output /mnt/user-data/outputs/yard.glb
```

For complex sensor layouts, write a JSON config file:
```bash
python scripts/build_cutaway.py --config /tmp/cutaway.json --output /mnt/user-data/outputs/cutaway.glb
```

Read `references/yard.md` or `references/cutaway.md` for the exact JSON schema before writing a config.

Output goes to `/mnt/user-data/outputs/` so it can be presented to the user.

### 4. Present the file

Use `present_files` with the output path. Briefly summarize:
- The list of named meshes (so the user knows what to address from Angular)
- Any defaults you chose
- For cutaway: remind that `mesh.scale.y` controls grain level

---

## Design contract — IMPORTANT

The generated GLB obeys these invariants. Don't break them when modifying the scripts:

1. **Geometry is the source of truth.** Heights, radii, and positions live in the geometry itself — no baked node transforms, no `extras` metadata. Angular reads dimensions via `geometry.boundingBox`.

2. **Each independently-controllable part = its own named mesh.**
   - Silo body + cone roof + corrugation rings + ribs → **one** mesh (`Silo.001`)
   - Ladder + railing → **separate** mesh (`Hardware.001`)
   - Each sensor → its own mesh (`Sensor.001`, `Sensor.002`, ...)

3. **Each mesh has its own unique PBR material.** glTF exporters merge materials with identical parameters. The `unique_pbr(..., salt=N)` helper adds a tiny roughness epsilon so meshes stay independently colorable from Angular via `material.color.set(...)`.

4. **Naming convention:**
   - Numbered same-type entities: `Pascal.NNN` (e.g., `Silo.001`, `Hardware.001`, `Sensor.001`)
   - Top-level groups: `PascalCase` (e.g., `Warehouse`, `Grain_Volume`)
   - **Avoid underscores like `Silo.001_Hardware`** — use a parallel `Hardware.NNN` mesh instead, so each independently-controlled part has a top-level name.

See `references/conventions.md` for the full reasoning.

---

## Resources in this skill

- `scripts/build_yard.py` — Builds the multi-silo yard scene
- `scripts/build_cutaway.py` — Builds the single cutaway silo with sensors
- `scripts/silo_lib.py` — Shared geometry & material helpers
- `references/yard.md` — Full parameter schema for `yard`
- `references/cutaway.md` — Full parameter schema for `cutaway`
- `references/conventions.md` — Naming + design contract
- `references/angular_usage.md` — How to consume the GLB from Angular + three.js

Read the relevant reference file BEFORE writing a JSON config. The references contain the canonical schema and avoid guesswork.
