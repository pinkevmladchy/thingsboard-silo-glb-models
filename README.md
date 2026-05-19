# GLB Models — ThingsBoard IoT Hub Silo Solution

This repository stores 3D models (GLB format) used in the ThingsBoard IoT Hub **Silo Solution**. The models demonstrate how to work with 3D objects inside ThingsBoard dashboards — visualizing grain silos, sensors, and yard layouts driven by live telemetry.

## What's inside

### 3D Models
- `silos_scene.glb` — multi-silo yard scene with silos arranged in a grid alongside a warehouse.
- `silo_cutaway.glb` — single cutaway silo showing internal sensors and adjustable grain level.

### Skill
- `skills/silo-glb-builder/` — a Claude Code skill that generates these silo GLB models. It can build:
  - a multi-silo yard scene (silos auto-arranged in a grid plus a warehouse), or
  - a single cutaway silo with sensors and a configurable grain level.

  Use the skill whenever you need to create, regenerate, or customize silo GLB assets for the ThingsBoard 3D viewer (silo count, sizes, sensor layout, etc.).

## Purpose

The models here are intended to be loaded into ThingsBoard dashboards (via the 3D widget / Angular + three.js viewer) to show how IoT telemetry — grain volume, temperature, sensor readings — can be visualized on top of real 3D geometry.

## How it's used

The ThingsBoard widget needs a **public URL** to fetch a GLB model from, so this repository acts as that hosting layer — each committed `.glb` is served via its raw GitHub URL and loaded directly by the widget at runtime.

Anyone can do the same: create a public repo, drop GLB files into it, and point the ThingsBoard 3D widget at the raw file URLs. This is a simple pattern for hosting and sharing 3D assets for ThingsBoard dashboards without standing up a dedicated asset server.
