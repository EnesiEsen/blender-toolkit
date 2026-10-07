# Changelog

Each add-on has its own version. Dates are release dates in the repository.

## 2026-10-07

### FiveM Toolkit 0.1.1
- Fix: the Doctor no longer reports the collision that Build Props embeds in a prop (`<name>.col`) as a badly named asset.

### Documentation
- Step-by-step guides with annotated screenshots for all four add-ons, in English and Turkish.

## 2026-10-06

### Terrain Blend 1.1.0
- Any number of texture layers, each from a texture folder (maps found by file name) with a vertex group as mask.
- Add layers from a texture library folder or from the existing vertex groups.
- Auto masks from slope, height or noise.
- Texture Enhancer (detail normal, crevice dirt, micro displacement) and a Lite Preview mode.
- Works on Blender 5.0 (OpenGL EEVEE) and 5.2 (Vulkan EEVEE); warns before GPU texture and attribute limits.

### Retopo Kit 1.0.0
- One-click quad retopology with presets (Auto, Simple Prop, Hard Surface / Vehicle, Organic / Character).
- QuadriFlow built in; QRemeshify when installed, with guide curves.
- Guide curves: draw, apply, mark edges, clear.
- Symmetry, snap to source, quality report.

### FiveM Toolkit 0.1.0
- Doctor: finds and fixes asset problems.
- Prop builder: Sollumz drawable, collision, LODs, YTYP archetype, DDS textures.
- MLO / Interior: template, check and build from a collection layout.
- Ped / Clothing: weight checks and retargeting onto GTA V bones.
- Resource export with `fxmanifest.lua` (FiveM binary or CodeWalker XML).

### UE5 Bridge 0.1.0
- FBX export for static meshes, modular skeletal meshes and animations with Unreal naming and settings.
- Skeleton check and single-root-bone fix on the export copy.
- Root motion extraction from the hips.
- Not yet tested inside Unreal Engine.
