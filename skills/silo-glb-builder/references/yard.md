# Yard scene — parameter reference

A `yard` is a small silo facility seen externally: N identical silos auto-arranged
in a `rows × cols` grid centered at origin, optionally with a warehouse to the
left and a white ground plane underneath.

All silos in a grid share the **same dimensions and colors**. Colors and
materials are fixed defaults — this skill produces geometry. To recolor at
runtime, the Angular client uses `material.color.set(...)`.

## Parameters

All parameters are optional. Use CLI flags for simple cases or a JSON config
file via `--config` for everything in one place.

| Parameter      | CLI flag           | Default | Notes |
|----------------|--------------------|---------|-------|
| `rows`         | `--rows`           | `2`     | Grid rows |
| `cols`         | `--cols`           | `2`     | Grid cols |
| `spacing_x`    | `--spacing-x`      | `1.5`   | Center-to-center along X |
| `spacing_z`    | `--spacing-z`      | `1.5`   | Center-to-center along Z |
| `radius`       | `--radius`         | `0.48`  | Silo body radius |
| `body_h`       | `--body-h`         | `1.5`   | Height of cylindrical part |
| `cone_h`       | `--cone-h`         | `0.25`  | Height of cone roof |
| `add_warehouse`| `--no-warehouse`   | `true`  | Set false to skip warehouse |
| `add_ground`   | `--no-ground`      | `true`  | Set false to skip ground plane |

The grid is **always centered around `x = 0, z = 0`**.
Silos are named `Silo.001`, `Silo.002`, ... in **row-major order** (left-to-right, then top-to-bottom).

## Example configs

### 1. Default 2×2 grid

```bash
python build_yard.py --output yard.glb
```

### 2. 3×3 grid of larger silos

```bash
python build_yard.py --rows 3 --cols 3 --radius 0.6 --body-h 1.8 --output yard.glb
```

### 3. A row of 5 silos, no warehouse

```bash
python build_yard.py --rows 1 --cols 5 --no-warehouse --output yard.glb
```

### 4. Config file form

`/tmp/my_yard.json`:
```json
{
  "rows": 2,
  "cols": 4,
  "spacing_x": 1.4,
  "spacing_z": 1.4,
  "radius": 0.5,
  "body_h": 1.6,
  "cone_h": 0.28
}
```
```bash
python build_yard.py --config /tmp/my_yard.json --output yard.glb
```

## Output meshes

For each silo in the grid, the GLB will contain TWO meshes (with matching numbering):
- `Silo.NNN`            — body + cone roof + corrugation rings + ribs (one mesh, light gray)
- `Hardware.NNN`        — ladder + top railing (one mesh, dark gray)

`Silo.001` and `Hardware.001` refer to the same silo's body and its hardware respectively.

Plus, if enabled:
- `Warehouse`           — main wall body (light cool gray, industrial style)
- `Warehouse_Trim`      — vertical metal-cladding ribs + roof + ridge + vent strip + door segments (darker gray)
- `Warehouse_Doors`     — two rolling-style doors on the front (medium gray)
- `Ground`              — flat plane (white)

The warehouse is a long, low industrial building (4.4 × 1.2 × 1.6) with
vertical ribbed metal cladding, a mono-pitch roof, and two rolling doors on
the front. It sits to the left of the silo grid with a 1.2-unit gap.

## Tips when calling this from the skill

- If the user says "I want 8 silos" → ask "rows × cols?" or pick `2 × 4` and tell them
- If they don't say a size → use defaults and mention them
- The warehouse is auto-positioned to the **left of the grid** with a 1-unit gap from the leftmost silo
- The ground plane auto-resizes to fit everything
