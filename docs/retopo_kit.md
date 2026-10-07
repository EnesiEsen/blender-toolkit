# Retopo Kit

One-click quad retopology for any model: simple props, hard-surface vehicles, characters. Optional guide curves tell the
result where the edge flow must go (eyes, mouth, fingers, panel gaps). A quality report tells you whether the result is
clean.

[Türkçe](retopo_kit.tr.md) · [Back to the overview](../README.md)

![Retopo Kit panel](images/retopo_kit.png)

## Quick start

1. Select the high-poly or messy mesh.
2. Pick a **Preset** (or leave **Auto**) and set **Target Faces**.
3. Press **Retopologize**. A new object named `<name>_retopo` is created and selected; your original is kept and hidden
   (turn **Hide Source** off to keep it visible).
4. Open **Quality Report** and press **Analyze Mesh** to see how clean the result is.

## Step-by-step guide: retopologizing a model

The example is a very dense monkey head. The same steps apply to a prop, a vehicle or a character; the differences are in
"What to choose for which model". The yellow numbers in the pictures match the numbers in the text.

> **Where is the panel?** In the 3D view press `N` to open the sidebar and click the **Retopo Kit** tab. In the screenshots the
> panel appears under the **Item** tab because of how the pictures were taken; in your Blender it has its own tab.

### 1. Preparation

- Give it a **clean, closed surface.** Delete loose parts and inner faces, and merge doubled vertices with
  *Edit Mode > Mesh > Clean Up > Merge by Distance*. Apply scale and rotation (`Ctrl+A > All Transforms`).
- **Apply** modifiers such as Subdivision: retopology works on the mesh data, not on what the viewport shows.
- With **QRemeshify** installed you get the best result, and only it follows guide curves. Without it Blender's QuadriFlow is
  used; the panel tells you with a notice.

### 2. One-click retopology

![Source and retopology result](images/steps/retopo-1-result.png)

1. Select the source model (**1** in the picture, left). Be in Object Mode.
2. **Preset** (3): choose *Organic / Character* for a head.
3. **Target Faces** (4): the approximate face count of the result. Here 1100.
4. Press **Retopologize** (5). A new object `<name>_retopo` appears (**2**, right, as a wireframe). The original is hidden by
   default; in this picture **Hide Source** is off for comparison.
5. The **Quality Report** (6) fills in for the result:

| Value | Good result | Meaning |
|---|---|---|
| Quad share | 95 % and up | Few triangles and n-gons. Below 90 % the panel warns you |
| Poles 3 / 5 / 6+ | none for 6+, few for 3 and 5 | Poles are the knots of the edge flow; there should be few, well placed |
| Edge length variation | under 25 % | How even the quads are |
| Distance to source | under 1 % | How close the result is to the source. If it is large, raise Target Faces |
| Non-manifold | 0 | No holes or doubled edges |

If the result is not good enough change the **Preset** or raise **Target Faces** and try again; every attempt creates a new
`_retopo` object, so delete the old one.

### 3. Steer the flow with guide curves (QRemeshify)

Guides are the paths the new quads must follow: around the eyes, the mouth, fingers, door and window edges of a vehicle.

![Guide curves](images/steps/retopo-2-guides.png)

1. Select the source model and open the **Guides** sub-panel.
2. Press **Draw Guide** (3). Blender creates a curve called `RK Guide` and switches to Edit Mode with the **Draw** tool. **Hold the
   mouse button and drag** over the model: the line sticks to the surface. Every drag is a separate line; you can draw the
   eyes and the mouth in the same curve (**1** around the eye, **2** the mouth).
3. Press **Apply Guides** (4). The curve is turned into the shortest path along the mesh edges and those edges are marked; the
   *Guide edges on '...'* counter in the panel (5) shows how many. Edit Mode is left automatically.
4. **Click the model to select it again.** Retopologize works on the selected, active mesh, not on the curve.

*Alternative:* In Edit Mode use **Mark Selected Edges** for edges you selected yourself; no drawing needed.

**Clear Guides** removes the marks and restores the seams and sharp edges the mesh had before.

### 4. Retopology with guides

![Result that follows the guides](images/steps/retopo-3-follow.png)

1. Set **Engine** to *QRemeshify* (3) or leave *Auto*, and keep **Use Guides** (6 in the previous picture) on.
2. Press **Retopologize**.
3. In the result (**2**, the wireframe head on the right) **concentric edge loops** now follow the guides around the eyes. The
   red lines on the left (**1**) stay on the source; clean them with **Clear Guides** when you are done.

Without guides the same model ends up with arbitrary triangles and knots at the eyes; loops are what lets the eyelids fold
correctly in animation.

### What to choose for which model

| Model | Preset | Target Faces (approx.) | Extra tips |
|---|---|---|---|
| Crate, barrel, simple prop | Simple Prop | 300 - 1500 | No guides needed. Either engine works |
| Vehicle body | Hard Surface / Vehicle | 4 000 - 10 000 | **Sharp Angle** 30. Draw guides for door gaps, window frames and lights. If the vehicle is symmetric and centered on the world origin, turn on **X** symmetry |
| Character body | Organic / Character | 8 000 - 15 000 | Retopologize the body and the clothes as **separate objects** |
| Character head | Organic / Character | 3 000 - 6 000 | Draw guides for eyes, mouth, nostrils and brows |
| Sculpt or scan | Organic / Character | any density | Very dense meshes (over 90 000 triangles) are decimated automatically |

Side options: **Symmetry X / Y / Z** adds a Mirror modifier to the result (the mirror center is the object origin), **Snap to
Source** adds a Shrinkwrap so later edits stay on the source surface.

### 5. After retopology

- Fix the edge loops around joints (knee, elbow, shoulder) by hand for animation; retopology gives you a good **base**.
- Unwrap the UVs and **bake** textures from the high-poly source to the low-poly (*Render Properties > Bake*, *Selected to
  Active*).
- Export the mesh to FiveM with the **FiveM Toolkit**, or to Unreal with the **UE5 Bridge**.

### Common problems

| Symptom | Cause and fix |
|---|---|
| The **Retopologize** button is grey | You must be in Object Mode with a mesh selected. After drawing guides click the model again |
| "QRemeshify is not installed" | QuadriFlow is used and guide curves are ignored. Install QRemeshify |
| The result is too dense or too sparse | **Target Faces** is approximate. Change it and retry; **Match Target** makes a second pass |
| The result is far from the source | The mesh may have holes or non-manifold edges. Repair it with *Merge by Distance* and *Fill Holes* |
| It takes a long time | A very dense mesh is normal; the add-on decimates anything above 90 000 triangles first |
| Hard edges got soft | Lower **Sharp Angle** or choose the *Hard Surface* preset |

## Presets

| Preset | Use it for | What it does |
|---|---|---|
| Auto | Anything | Looks at how many sharp edges the mesh has and picks Hard Surface or Organic. |
| Simple Prop | Boxes, crates, simple shapes | Keeps sharp edges (30 degrees) and the boundary, no extra smoothing. |
| Hard Surface / Vehicle | Machines, vehicles, architecture | Keeps sharp edges crisp (30 degrees), no smoothing. |
| Organic / Character | Characters, creatures, sculpts | Smooth flow (80 degrees), smoothing on; only seams act as hard lines. |

Choosing a preset sets **Sharp Angle** and **Smoothing**; you can change both afterwards under **Advanced**.

## Engines

| Engine | Strengths | Notes |
|---|---|---|
| QuadriFlow | Built into Blender, fast | Ignores guide curves. |
| QRemeshify | Better quality, follows sharp edges **and guide curves** | Separate free add-on ([ksami/QRemeshify](https://github.com/ksami/QRemeshify)). |
| Auto (default) | Uses QRemeshify when it is installed, otherwise QuadriFlow | The panel tells you which one is used. |

## Guide curves

Guides are lines the new quads should follow. They work with QRemeshify.

1. Open the **Guides** sub-panel.
2. **Draw Guide** creates a curve and starts Blender's Draw tool with surface projection: drag on the model to draw
   (around an eye, along a mouth, across a panel gap). Repeat for each line.
3. **Apply Guides** converts the selected curves into guide edges on the target mesh (the shortest path along the mesh
   edges between the curve points). Or in Edit Mode, select edges and press **Mark Selected Edges**.
4. Press **Retopologize** with **Use Guides** on. The edges you marked become hard lines the new topology follows.
5. **Clear Guides** removes the marks and restores the seams and sharp edges the mesh had before.

## Other controls

| Control | What it does |
|---|---|
| Symmetry X / Y / Z | Adds a Mirror modifier to the result along that axis. |
| Snap to Source | Adds a Shrinkwrap modifier (`RK Snap`) so later edits stay on the source surface. |
| Hide Source | Hides the original after retopology. |
| Match Target | If the first result is far from Target Faces, runs a second pass (QRemeshify). |
| Sharp Angle | Edges sharper than this stay hard lines. |
| Smoothing | Smooths the result after quadrangulation. |
| Retopology overlay | Shows Blender's retopology overlay in the viewport. |

## Quality report

**Analyze Mesh** measures the active mesh:

- number of faces and the share of quads, triangles and n-gons
- poles (vertices where 3, 5 or 6+ edges meet)
- edge length variation (lower means more even quads)
- distance to the source surface, average and maximum, as a percentage of the model size
- non-manifold edges

A warning appears when less than 90 % of the faces are quads: raise **Target Faces** or add guides.

## Tips

- Remove loose parts and internal faces before you retopologize; the engines work best on a clean closed surface.
- Very dense meshes (over about 90,000 triangles) are decimated automatically on a working copy first, and very sparse
  ones (under about 2,500) are subdivided, so the engines get a sensible input. Your original is never touched.
- For characters, retopologize the body and the clothing as separate objects.
- Retopology gives you a good base, not a finished animation mesh. Check face loops around joints yourself.

## Limits

- Guide curves need QRemeshify; with QuadriFlow they are ignored and the panel says so.
- Results are not identical between different engines or versions.
- The QRemeshify build used in the tests is the Windows one. On macOS and Linux install the matching QRemeshify build;
  Retopo Kit itself is plain Python and falls back to QuadriFlow.
