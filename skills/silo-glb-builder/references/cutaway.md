# Cutaway scene — parameter reference

A `cutaway` is a single silo with a 90° wedge removed from the front, exposing:
- The inner floor (gray)
- A wavy "heap" of orange grain
- N sensors hanging on a central vertical cable

Colors and materials are **fixed defaults** — the Angular client recolors at
runtime. This skill produces the geometry only.

## Parameters

### Silo geometry

| Parameter | CLI flag    | Default | Notes |
|-----------|-------------|---------|-------|
| `radius`  | `--radius`  | `1.0`   | Silo body radius |
| `body_h`  | `--body-h`  | `3.0`   | Cylinder body height |
| `cone_h`  | `--cone-h`  | `0.5`   | Cone roof height |
| `grain_h` | `--grain-h` | `2.70`  | Grain base fill (heap peaks slightly above) |

### Sensors

By default, **3 sensors** are placed evenly along the central Y axis (at 83%, 50%, 17% of body height).

To customize, pass `--sensors` with a JSON list, or set `sensors` in a config file:

```json
[
  { "name": "Sensor.001", "x": 0, "y": 2.5, "z": 0 },
  { "name": "Sensor.002", "x": 0, "y": 1.5, "z": 0 },
  { "name": "Sensor.003", "x": 0, "y": 0.5, "z": 0 }
]
```

Each sensor needs: `name` (optional, auto-generated otherwise), `x`, `y`, `z`.

**Sensor coordinates** live in the silo's local frame:
- `x = 0, z = 0` is the silo's central axis
- `y = 0` is the bottom of the silo's floor (the floor itself sits at `y = 0.08..0.16`)
- Keep `y ∈ [0.2, body_h - 0.1]` to stay safely inside
- Keep `x² + z² < (radius - 0.15)²` to avoid the wall

### Optional toggles

| Flag             | Default | What it does |
|------------------|---------|--------------|
| `--no-cable`     | (on)    | Skip the central vertical cable |
| `--no-ground`    | (on)    | Skip the ground plane |

## Examples

### 1. Default cutaway (3 centered sensors, cable, full grain)

```bash
python build_cutaway.py --output cutaway.glb
```

### 2. Bigger silo with 5 sensors

`/tmp/cutaway.json`:
```json
{
  "radius": 1.2,
  "body_h": 4.0,
  "cone_h": 0.6,
  "grain_h": 3.6,
  "sensors": [
    { "name": "Sensor.001", "x": 0, "y": 3.5, "z": 0 },
    { "name": "Sensor.002", "x": 0, "y": 2.8, "z": 0 },
    { "name": "Sensor.003", "x": 0, "y": 2.1, "z": 0 },
    { "name": "Sensor.004", "x": 0, "y": 1.4, "z": 0 },
    { "name": "Sensor.005", "x": 0, "y": 0.7, "z": 0 }
  ]
}
```
```bash
python build_cutaway.py --config /tmp/cutaway.json --output cutaway.glb
```

### 3. Wall-mounted sensors (no cable)

```json
{
  "add_cable": false,
  "sensors": [
    { "name": "Sensor.North", "x": 0,     "y": 1.5, "z": -0.85 },
    { "name": "Sensor.South", "x": 0,     "y": 1.5, "z": 0.85 },
    { "name": "Sensor.East",  "x": 0.85,  "y": 1.5, "z": 0 },
    { "name": "Sensor.West",  "x": -0.85, "y": 1.5, "z": 0 }
  ]
}
```

## Output meshes

| Name                  | Description |
|-----------------------|-------------|
| `Silo.Cutaway`        | Body + ceiling + cone roof + rings + ribs (light gray) |
| `Silo.Cutaway_Floor`  | Inner floor disk (darker gray) |
| `Grain_Volume`        | Orange grain heap with wavy top (double-sided) |
| `Cable`               | Central vertical cable + mount cap, one mesh (if `add_cable`) |
| `Sensor.NNN`          | One mesh per sensor (teal, each with its own material) |
| `Ground`              | White ground plane (if `add_ground`) |

## Grain level at runtime

The grain ships at 100%. The Angular client controls fill level via:

```typescript
const grain = scene.getObjectByName('Grain_Volume') as THREE.Mesh;
grain.scale.y = percent / 100;          // 0 = empty, 1 = full
grain.visible = percent > 0.01;
```

`mesh.geometry.boundingBox` provides the true full height — no metadata needed.
