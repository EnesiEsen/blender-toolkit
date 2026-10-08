# Blender Toolkit

Ten Blender add-ons that remove the slow, repetitive parts of game-asset work: blending many terrain textures,
retopologizing any model, getting props and characters into FiveM, and a full pipeline to Unreal Engine 5 (hard-surface
modeling, texel density, textures, collision, rigging and FBX export), and a brush that scatters grass, rocks and trees.

**Blender 5.0 to 5.2** (tested on 5.0.1 and 5.2.0 LTS) · GPL-3.0-or-later · English and Turkish interface

[Türkçe README](README.tr.md)

### General-purpose tools

These work in any Blender project and have nothing to do with a game engine.

| Add-on | What it does | Guide |
|---|---|---|
| **Terrain Blend** | Blend any number of PBR texture sets on one mesh, using vertex groups as masks. Auto masks from slope, height or noise. | [docs/terrain_blend.md](docs/terrain_blend.md) |
| **Scatter Brush** | Scatter grass, rocks and trees where you weight paint, or with a click brush. Categories, model chances, slope, height and keep-away filters. | [docs/scatter_brush.md](docs/scatter_brush.md) |
| **Retopo Kit** | One-click quad retopology for props, vehicles and characters, with guide curves and a quality report. | [docs/retopo_kit.md](docs/retopo_kit.md) |
| **Hard Surface Kit** | Non-destructive bevels, cutters, arrays, grooves and an Apply Stack for game-ready meshes. | [docs/hardsurface_kit.md](docs/hardsurface_kit.md) |

### Game-engine tools: Unreal Engine 5

For getting finished assets into Unreal Engine 5. Each one is independent.

| Add-on | What it does | Guide |
|---|---|---|
| **UE5 Bridge** | FBX export for Unreal Engine 5: static meshes, modular skeletal meshes, animations, root motion. | [docs/ue5_bridge.md](docs/ue5_bridge.md) |
| **Texture Kit** | Texture checks, normal map flip, ORM packing and Unreal-named export. | [docs/ue5-pipeline.md](docs/ue5-pipeline.md#texture-kit) |
| **Texel Density** | Measure, show as colors and set the texture density of every asset. | [docs/ue5-pipeline.md](docs/ue5-pipeline.md#texel-density) |
| **Collision Maker** | UBX / USP / UCP / UCX collision shapes and a checker, exported with the mesh. | [docs/ue5-pipeline.md](docs/ue5-pipeline.md#collision-maker) |
| **Game Rig Kit** | UE5 mannequin skeleton, skinning, IK, renaming and animation retarget. | [docs/ue5-pipeline.md](docs/ue5-pipeline.md#game-rig-kit) |

### FiveM

On top of Sollumz, for GTA V / FiveM servers.

| Add-on | What it does | Guide |
|---|---|---|
| **FiveM Toolkit** | Check, fix, build and export props, MLO interiors and ped clothing for FiveM, on top of Sollumz. | [docs/fivem_toolkit.md](docs/fivem_toolkit.md) |

![Terrain Blend](docs/images/terrain_blend.png)

## Install

1. Download the `.zip` of an add-on from the [`dist`](dist/) folder (open the file and press the download button), or
   build it yourself, see [CONTRIBUTING.md](CONTRIBUTING.md).
2. In Blender: **Edit > Preferences > Get Extensions**, open the drop-down arrow in the top-right corner and choose
   **Install from Disk...**, then pick the zip. Do not unzip it.
3. Make sure the add-on is ticked. Its panel appears in the 3D viewport sidebar (press `N`), in a tab with the add-on's
   name.

The add-ons are independent: install only the ones you need.

Optional companions:

- **Retopo Kit** works with Blender's built-in QuadriFlow. Install the free
  [QRemeshify](https://github.com/ksami/QRemeshify) add-on as well to get guide curves and sharper results.
- **FiveM Toolkit** needs the [Sollumz](https://docs.sollumz.org) add-on (free, GPL). It was tested with the Sollumz
  development builds 2.8.0 (Blender 5.0) and 2.8.3 (Blender 5.2).

## Design rules

- **Your scene is not damaged.** Exports work on temporary copies. Retopology keeps the original (hidden). Fixes that
  change your data are explicit buttons, never silent.
- **No hard limits where a limit is not needed.** For example Terrain Blend takes any number of layers and warns only
  when your GPU or render engine is about to run out of texture slots.
- **Explain the problem, offer the fix.** The FiveM Doctor and the UE5 skeleton check say what is wrong in plain words
  and fix the safe problems with one click.
- **Works on 5.0 and 5.2.** The two versions differ in places (EEVEE texture and attribute limits, Vulkan, numpy 1.x vs
  2.x, layered actions). Every add-on has a headless test suite that runs on both.

## How well is it tested?

Each add-on has a test that runs headless in Blender 5.0.1 (OpenGL) and 5.2.0 LTS (Vulkan) and builds real scenes:
14 and 49 texture layers, retopology with guide curves, a prop to MLO to ped export through Sollumz, and FBX files that
are exported and imported back to check the result. Details and what is **not** covered:

| Area | Verified | Not verified |
|---|---|---|
| Terrain Blend | 14-layer and 49-layer materials on both versions, enhancer, auto masks | Very large meshes (millions of vertices) |
| Retopo Kit | Quad result, guide-following, presets, report | QRemeshify on macOS and Linux |
| FiveM Toolkit | Doctor, props with LODs and collision, DDS output, MLO, ped weight retargeting, export with Sollumz | Loading the result in a live FiveM server or CodeWalker |
| UE5 Bridge | FBX re-import: single root bone, no leaf bones, size, animation length, root-motion extraction | Import in Unreal Engine itself (none was available) |

Screenshots in this repository are generated by a script from the add-ons running in Blender 5.2.

## Languages

The interface is English with a complete Turkish translation (Blender follows **Preferences > Interface > Language**).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE). Blender add-ons that use `bpy` are derivative works of Blender and are
licensed accordingly.
