# Consuming the GLB from Angular + three.js

The generated GLB is designed to drop into a `GLTFLoader`-based viewer.
This doc shows the patterns specific to this skill's output.

## Loading

```typescript
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

new GLTFLoader().load('silos_scene.glb', (gltf) => {
  // Enable shadows + clone materials so each mesh is independently colorable
  gltf.scene.traverse((obj) => {
    if (!(obj as THREE.Mesh).isMesh) return;
    const mesh = obj as THREE.Mesh;

    if (mesh.name === 'Ground' || mesh.name.startsWith('Ground')) {
      mesh.receiveShadow = true;
    } else {
      mesh.castShadow = true;
      mesh.receiveShadow = true;
    }
    // Defensive: ensure each mesh has its own material instance
    if (Array.isArray(mesh.material)) {
      mesh.material = mesh.material.map(m => m.clone());
    } else if (mesh.material) {
      mesh.material = (mesh.material as THREE.Material).clone();
    }
  });
  scene.add(gltf.scene);
});
```

## Changing a silo's color

```typescript
const silo = scene.getObjectByName('Silo.001') as THREE.Mesh;
(silo.material as THREE.MeshStandardMaterial).color.set(0xff5544);
```

The ladder/railing (`Silo.001_Hardware`) keeps its own color — only the silo
body changes.

## Controlling grain level (cutaway only)

```typescript
const grain = scene.getObjectByName('Grain_Volume') as THREE.Mesh;

function setGrainLevel(percent: number) {
  grain.scale.y = Math.max(0, Math.min(100, percent)) / 100;
  grain.visible = percent > 0.01;
}
```

The default GLB has the grain at "100%" geometry. `scale.y = 0.5` shows
half-full, `scale.y = 0` hides it.

## Coloring a sensor by temperature

```typescript
function setSensorColor(name: string, temperatureC: number) {
  const sensor = scene.getObjectByName(name) as THREE.Mesh;
  const mat = sensor.material as THREE.MeshStandardMaterial;
  if (temperatureC < 25)      mat.color.set(0x66bbff);  // cool blue
  else if (temperatureC < 35) mat.color.set(0xffcc44);  // warm yellow
  else                        mat.color.set(0xff3344);  // hot red
}

setSensorColor('Sensor.001', 32);
```

Each sensor has its own material (thanks to the `salt` epsilon in the builder),
so coloring `Sensor.001` doesn't affect `Sensor.002`.

## Lighting setup (recommended for the white PBR look)

```typescript
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;

// Environment map — biggest factor in making white PBR look white, not gray
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

scene.add(new THREE.AmbientLight(0xffffff, 0.6));

const sun = new THREE.DirectionalLight(0xffffff, 2.0);
sun.position.set(40, 80, 30);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = -0.0005;
scene.add(sun);
```

## Common gotchas

**Silos look gray instead of their assigned colors.**
You forgot one of these: `outputColorSpace = SRGBColorSpace`,
`toneMapping = ACESFilmicToneMapping`, or `scene.environment` from PMREM.

**Changing one sensor's color changes all of them.**
Materials got merged. Either clone them after load (snippet above) or
ensure the builder used `unique_pbr(..., salt=...)`.

**Grain looks translucent / shimmering from above.**
The grain mesh has `doubleSided: true` in the builder, but if your client
overrides it: `(grain.material as THREE.MeshStandardMaterial).side = THREE.DoubleSide`.

**Tooltip / outline appears even on hardware (ladder, railing).**
Filter by name: `if (name.startsWith('Silo.') && !name.includes('_Hardware'))`.
