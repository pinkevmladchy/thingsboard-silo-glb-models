# Naming conventions & design contract

These rules keep the GLB consumable from Angular without surprises.

## Naming

| Pattern              | When                                            | Example |
|----------------------|-------------------------------------------------|--------|
| `Pascal.NNN`         | Numbered same-type entities                     | `Silo.001`, `Sensor.003`, `Hardware.001` |
| `Silo.Cutaway`       | Single cutaway silo + components                | `Silo.Cutaway_Floor` |
| `Pascal_Pascal`      | Top-level multi-word objects                    | `Sensor_Cable`, `Grain_Volume` |
| `Pascal`             | Singleton                                       | `Warehouse`, `Ground` |

**Avoid** subpart-style names like `Silo.001_Hardware`. When two parts share
a number (e.g., a silo and its ladder/railing), give the second part its own
top-level name with matching number — `Hardware.001` rather than `Silo.001_Hardware`.
This way every independently-controlled mesh has a single, clean name.

Don't use snake_case in mesh names. Three.js convention is PascalCase, and tools
like `scene.getObjectByName()` are case-sensitive.

## "Geometry is source of truth"

When generating a GLB:

- Heights, radii, positions live in **vertex coordinates**. The geometry itself
  represents the "100%" / "full" / "default" state.
- Don't bake non-identity scale, rotation, or translation into the node — let
  trimesh emit identity transforms.
- Don't embed `extras` metadata describing dimensions ("maxHeight": 1.8, etc.).
  Angular reads everything from `geometry.boundingBox`.

Why: the consumer (Angular) treats `mesh.scale.y = 0.5` as "50% of what's
visible by default". If the model ships with `scale.y = 0` baked in, every
consumer has to know that magic number. Keep it simple.

## "Independently-controlled = separate mesh"

If a thing needs its own color, visibility, or scale at runtime, it must be a
**separate named mesh**.

- Body, roof, rings, ribs — same color, controlled together → **one mesh**
- Body vs ladder/railing — different colors → **two meshes**
- Each sensor — different temperatures/colors → **separate mesh each**
- Grain — independent scale.y → **separate mesh**

## "Unique materials"

glTF exporters merge materials with identical PBR parameters. To prevent this,
use the `unique_pbr(..., salt=N)` helper, which adds `N * 1e-4` to the
roughness factor. The visual difference is invisible; the runtime difference
is huge — each mesh can have its color changed independently.

If you ever see "I changed Silo.001's color and Silo.002 changed too" — that's
this issue. Bump the salt values to make sure each material is unique.

## Coordinate system

- **+Y is up** (matches three.js default and glTF spec)
- **XZ is the ground plane**
- All cylinders/cones/silos have their **base at y = 0** in local coordinates
  before being placed in the scene. This way `mesh.scale.y` "grows upward".
