# Terrain Blend

Blend any number of PBR texture sets on one mesh. Each set (grass, path, rock, mud ...) is a **layer**; a **vertex
group** says where the layer is visible. The add-on builds the material and a small Geometry Nodes modifier for you and
keeps everything adjustable with live sliders.

[Türkçe](terrain_blend.tr.md) · [Back to the overview](../README.md)

![Terrain Blend panel](images/terrain_blend.png)

## Quick start

1. Select your terrain mesh. Create one **vertex group per surface** (`path`, `rock`, `mud` ...) and paint weights, or
   let the add-on generate them (step 4).
2. Keep each texture set in its own folder. The add-on finds the maps by file name, so downloads from ambientCG,
   Poly Haven, Poliigon, Quixel or Substance work as they are:

   | Map | Recognized words in the file name |
   |---|---|
   | Color | `color`, `col`, `basecolor`, `albedo`, `diffuse`, `diff` |
   | Normal | `normal`, `normalgl`, `normaldx`, `nor`, `nrm`, `norm` (OpenGL is preferred over DirectX) |
   | Roughness | `roughness`, `rough` |
   | Height | `height`, `displacement`, `disp`, `bump` |

   A set needs at least a color map. Missing maps are simply left out.
3. Open the **Terrain Blend** panel and press **Add From Texture Library**. Pick the folder that contains the set
   folders. Every sub-folder with a color map becomes a layer, and a vertex group with the same name becomes its mask.
   The first layer is the **base** and needs no mask. (**Add From Vertex Groups** goes the other way: one layer per
   vertex group, and you set the texture folders by hand.)
4. Select a layer and press **Generate Mask** to fill its vertex group from **slope**, **height** or **noise** instead of
   painting. Choose the range (From / To), invert it, or combine it with the existing weights (replace, intersect,
   union).
5. Press **Build / Update Material**. The material and the **TB Masks** modifier are created.
6. Tune the result with the **Live Settings** sliders. Nothing needs to be rebuilt.

## Panel reference

| Control | What it does |
|---|---|
| Layer list (+ / - / arrows) | Add, remove and reorder layers. Later layers are painted on top of earlier ones. |
| Name, Texture Folder, Mask | The layer's name, its texture set folder and the vertex group that decides where it shows. |
| Generate Mask | Fill the mask from slope (degrees), height (meters) or noise (0 to 1, with scale and seed). |
| Lite Preview | Use only the color and height maps (2 textures per layer). Use it for many layers on EEVEE with the OpenGL backend. Switch it off for the final look. |
| Texture Enhancer | Procedural fine detail normal, crevice dirt and micro displacement on top of the textures. No extra image files. |
| Build / Update Material | Rebuild the material and the modifier. Slider values you set are kept. |

**Live Settings** (global): Blend Noise Scale (breaks up the edges between layers), Normal Strength, Relief (height in
meters). **Per layer**: Scale (texture tiling), Softness, Height Influence (let the height map push the transition),
Noise. **Enhancer**: Detail Strength and Scale, Dirt Amount and Scale, Dirt Color, Micro Displacement and Scale.

## How many layers can I use?

There is no limit set by the add-on. The limits come from the render engine, and the panel warns you before you hit
them:

| Engine | Limit | What to do |
|---|---|---|
| Cycles | None that matters | Use it for final renders. |
| EEVEE, Vulkan backend (Blender 5.2) | Up to 256 textures, 49 layers | Fine for large sets. |
| EEVEE, OpenGL backend (Blender 5.0, or 5.2 on OpenGL) | About 30 textures. With 4 maps per layer that is 7 layers; above it surfaces turn pink | Turn on **Lite Preview** (2 maps per layer, 14 layers) or use Cycles. |
| EEVEE, any backend | 49 layers (a GPU attribute limit: masks are packed 4 per attribute) | Use Cycles for more. |

Tested with 14-layer and 49-layer materials in Blender 5.0.1 and 5.2.0.

## Good to know

- Masks reach the shader through a Geometry Nodes modifier named **TB Masks**. If you apply or remove it, press
  **Build / Update Material** to put it back.
- Blender 5.0 EEVEE cannot read vertex groups directly in a material. That is why the add-on packs them into color
  attributes. You do not need to do anything; it works the same on 5.0 and 5.2.
- Each object keeps its own layer list, so different terrains can use different sets.
- Textures are referenced from their folders, not copied. Keep the folders where they are, or use
  **File > External Data > Pack Resources** before sharing the .blend file.

## Limits

- The base layer always covers the whole mesh.
- Auto masks work per vertex, so a low-poly mesh gives coarse masks. Subdivide the mesh or paint the group yourself for
  fine control.
- The tests use grids of about ten thousand vertices. The material itself does not depend on the vertex count, but
  **Generate Mask** loops over every vertex, so expect it to take longer on very dense meshes.
