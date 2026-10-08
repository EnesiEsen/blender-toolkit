# Hard Surface Kit

A non-destructive hard-surface modeling toolbox: bevels, cutters, arrays, grooves, cleanup and a clean Apply Stack. It is a
general-purpose add-on for any 3D project; it does not need any of the Unreal Engine add-ons (though its Apply Stack
result is exactly what a game engine wants).

[Türkçe](hardsurface_kit.tr.md) · [Back to the overview](../README.md)

Sidebar tab: **Hard Surface**. Tested in Blender 5.0.1 and 5.2.0.

A non-destructive workflow built from ordinary modifiers, so you can change anything until you apply it.

1. **Smart Bevel**: shades the mesh smooth with hard edges above the **Smooth Angle**, adds a Bevel modifier (limit by angle
   or by weights) and a Weighted Normal modifier, and keeps them in the right order. **Mark Sharp Edges** marks the edges
   and gives them bevel weights.
2. **Cutters**: select the cutter objects and the target last, then **Use Selected as Cutters** (cut, add or intersect).
   Cutters stay editable, are shown as wire and follow the target. **New Cutter** adds a box or cylinder at the 3D cursor.
   **Apply Cutters** makes the cuts permanent; **Remove Cutters** undoes them.
3. **Mirror and Arrays**: mirror with optional cut at the center, a linear array, and a **radial array** around the object's
   origin (bolts, vents, wheels) driven by a child empty.
4. **Grooves and Cleanup** (Edit Mode): **Groove** and **Panel** inset the selected faces and push them in or out with
   vertical walls, marking the edges sharp for the bevel. **Clean Mesh** merges doubles, removes loose vertices and dissolves
   flat edges.
5. **Apply Stack** bakes every modifier, including the custom normals, into a clean mesh and deletes the helper objects.
   Meshes with shape keys are skipped.

There is no interactive draw tool for cutters; you place and size them with the tools above.
