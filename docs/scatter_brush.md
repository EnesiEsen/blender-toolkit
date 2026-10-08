# Scatter Brush

Spread grass, rocks, trees or any other models over a level in two ways: **paint a vertex group** on the ground and let the
models grow there with a smooth density falloff, or **click and drag a brush** in the viewport to place them by hand. Both
use the same **categories**: a category is a set of models (for example 15 rocks, or 5 grass blades) plus all the
randomness settings you saved for it.

[Türkçe](scatter_brush.tr.md) · [Back to the overview](../README.md)

The panel is in the sidebar tab **Scatter** (press `N` in the 3D view; in the screenshots it sits under *Item* because of how
the pictures were taken). Tested in Blender 5.0.1 and 5.2.0. The yellow numbers in the pictures match the numbers in the text.

## 1. Make a category

![Categories](images/steps/scatter-1-category.png)

1. Select your models (for example the 5 grass blades) and press **+** at the list. Scatter Brush makes a category named
   after the first model and **moves the models into their own collection** (`<name> Assets`). That collection is excluded
   from the view layer so the originals do not stand in your level; they still work as the source. Switch *Hide the Models* off
   in the redo panel if you want to keep them visible. Make one category per kind: Grass, Rocks, Trees.
2. **Models** shows the collection of the active category. You can drag it to another collection, or fill it with more models:
   select objects and press **Add Selected** (3, left).
3. **Prepare Models** (3, right) applies the scale and rotation of each model and puts its origin at the **bottom centre**.
   Do this once: the origin is the point that touches the ground, and the random scale is multiplied with whatever scale the
   object already has. A red notice appears when a model needs this. Models that share their mesh with another object, have
   a parent, or are not meshes are skipped and listed in the message.

## 2. Randomness (the same for both modes)

![Variation and brush settings](images/steps/scatter-2-brush.png)

Everything here belongs to the active category and is saved with the file. The model for each object is picked at random
from the category.

| # | Setting | What it does |
|---|---|---|
| 1 | **Scale Min / Max** | Each object gets a random size between the two values. **Height Variation** stretches only the height on top of that, so plants differ in height more than in width. |
| 2 | **Random Turn / Random Tilt** | Largest random turn around the up axis (360 is a free turn) and the largest random lean away from it. |
| 3 | **Align to Surface** | 0 keeps everything upright, 1 follows the slope of the ground. |
| 4 | **Sink**, **Seed** | Push objects into the ground (a rock half buried), and the random pattern. The arrows button rolls a new seed. |
| 5 | **Start Brush** | The click brush, see section 4. |
| 6 | **Radius, Objects per Stamp, Stroke Spacing, Min Distance, Max Slope** | The click brush settings, see section 4. |
| 7 | **Erase** | Makes the brush erase (also: hold `Shift`, or press `E`). |
| 8 | **Delete Placed Objects** | Removes every object the brush or a bake placed for this category. |

## 3. Scatter where you paint weights

![Weight paint layers](images/steps/scatter-3-weights.png)

1. Select the **ground mesh** and pick the category (for example *Grass*). Make a vertex group on the ground with the **+**
   at the group list (4), name it (`grass`), and keep it selected. **Apply the scale and rotation of the ground first**
   (`Ctrl+A`): the objects live in the ground's space and would inherit them. A red notice appears when it is needed.
2. Press **Add Surface Layer** (5). The layer appears below (6) with the group it uses (7). Nothing grows yet, because the
   group is empty: its weight is 0 everywhere.
3. Press the **weight paint** icon of the layer (6, the first icon after the visibility one). Blender switches to Weight
   Paint with that group; paint with weight 1 where the grass should be full and with less where it should fade out. The
   models appear live while you paint (1). Go back to Object Mode when you are done.
4. The area **fades out smoothly**: the density follows the weight at every point of every face, not face by face (2).
   Tune it in the panel (3):

   | Setting | What it does |
   |---|---|
   | **Density** | Objects per square meter where the weight is 1. **Density ×** on the layer (8) multiplies it for one ground only. |
   | **Edge Falloff** | 1 follows the weight linearly, 2 or more thins the objects faster toward weak weights, so the patch has a tighter edge. |
   | **Weight Cutoff** | Weights at or below this get no objects at all. |
   | **Shrink at Edges** | Objects get smaller where the weight is weak, so the edge of a lawn is made of short grass. |
   | **Even Spacing / Min Distance** | Keeps at least that distance between two objects (good for trees and rocks; a bit slower). |

5. Add more layers for other categories (Rocks on a `rocks` group, Trees on a `trees` group). A layer is a Geometry Nodes
   modifier; the screen icon switches it off, the cross removes it. Leave the weights field empty to scatter over the
   whole surface.
6. **Bake to Objects** (6, middle icon) turns a layer into real objects you can move, delete or export one by one. They are
   linked duplicates (they share the mesh of the model), placed in the collection `<category> Placed`, and the layer is
   removed (the redo panel can keep it). More than 20 000 objects are refused: lower the density first.

## 4. Click brush

![Click brush](images/steps/scatter-4-brush.png)

Pick a category and press **Start Brush** (3). The green circle follows the surface under the mouse and is draped over
bumps (2).

| Action | Result |
|---|---|
| Left click | Places **Objects per Stamp** objects inside the circle (1), each with a random model, size, turn and lean from the category. |
| Left drag | Stamps again each time the mouse has moved **Stroke Spacing** × radius. |
| `Shift` + left click, or `E` | Erase mode: removes the brush objects of the category inside the circle (the circle turns red). |
| `Ctrl` + wheel, or `[` and `]` | Change the **Radius**. The wheel alone and the middle mouse button still move the view. |
| `Esc`, `Enter` or right click | End the tool. |

The settings (4): **Radius** (0 places exactly at the cursor), **Objects per Stamp**, **Stroke Spacing**, **Min Distance**
(no two objects closer than this, also against objects from earlier strokes) and **Max Slope** (skips steeper ground, so no
grass on cliffs). Each stroke is one undo step. The brush ignores its own objects when it looks for the ground, so you can
paint over an area you already filled.

The placed objects are ordinary linked duplicates in `<category> Placed`; the rest of Blender (move, delete, export) works on
them as on any object.

## Limits, honestly

- **Models need preparation.** The scale and rotation of the source object are ignored by the layers and the brush; the
  origin is the point that touches the ground. Use **Prepare Models**.
- **The ground must have scale 1 and no rotation** for surface layers. The click brush does not care.
- The density is per square meter of ground surface. A very sparse ground mesh (a few big faces) limits how
  well the falloff follows your painting; the weights are interpolated across each face.
- The model of each object is picked uniformly at random. There are no per-model weights.
- Objects do not avoid each other or other layers unless you set a **Min Distance** (brush) or **Even Spacing** (layer).
- Live layers exist only in Blender. For Unreal Engine, **Bake to Objects** first. Thousands of single objects are a heavy
  FBX; for foliage you may prefer to export the models once and scatter them again inside Unreal. This was not tried in
  Unreal here.
- The click brush needs Object Mode and a 3D viewport; there is no pen pressure support.
- Verified on Blender 5.0.1 and 5.2.0 with scripted checks (object counts against an independent calculation, scale and
  turn ranges, slopes, spacing, baking), and the click brush with simulated mouse events in a real window.
