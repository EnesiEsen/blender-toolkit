# UE5 asset pipeline: five add-ons for game-ready assets

[Türkçe](ue5-pipeline.tr.md) · [Back to the overview](../README.md)

These add-ons cover the steps between "finished model" and "imported into Unreal Engine 5". Each one is independent and
has its own sidebar tab; they work best together, and **UE5 Bridge** (see its guide) exports the result.

| Add-on | Sidebar tab | What it is for |
|---|---|---|
| [Texture Kit](#texture-kit) | Texture Kit | Texture checks, normal map flip, ORM packing, Unreal-named export |
| [Texel Density](#texel-density) | Texel Density | Measure, color and set the texture density of every asset |
| [Collision Maker](#collision-maker) | Collision | UBX / USP / UCP / UCX collision shapes, a checker, exported with the mesh |
| [Hard Surface Kit](#hard-surface-kit) | Hard Surface | Bevels, cutters, arrays, grooves, cleanup, Apply Stack |
| [Game Rig Kit](#game-rig-kit) | Game Rig | UE5 mannequin skeleton, skinning, IK, renaming, animation retarget |

> **A suggested order for one asset:** model with the **Hard Surface Kit**, set **Texel Density**, bake and check textures
> with **Texture Kit**, add **Collision Maker** shapes, then export with **UE5 Bridge**. For characters: **Game Rig Kit**
> first, then the same steps.

All five were tested in Blender 5.0.1 and 5.2.0. None of them was tried inside Unreal Engine (it is not installed here);
the rules come from Epic's documentation.

## Texture Kit

Problems it prevents: normal maps with the wrong green channel, color textures stored as data (or the reverse), sizes that
are not powers of two, and the pile of loose files that ends up in Unreal.

1. Select the object. In **Doctor** press **Check Textures**. It lists images whose color space is wrong for their use
   (normal, roughness and metallic need **Non-Color**, color maps **sRGB**), images that are missing, not a power of two or
   above the size you set. **Fix** or **Fix All** corrects the color spaces; sizes are fixed by the export.
2. In **Export Texture Set** choose the folder, the asset name, the maximum size and the file format.
   **Normal Map: Blender to Unreal** flips the green channel for you (Blender is OpenGL, Unreal wants DirectX).
   **Pack ORM** puts occlusion, roughness and metallic into the red, green and blue channels of one texture; pick the
   occlusion map in **AO Image** (a material has no input for it).
3. **Export for Unreal** writes `T_<name>_BC` (base color), `T_<name>_N`, `T_<name>_ORM` and `T_<name>_E` (emission), all
   scaled to powers of two within your limit, plus `T_<name>_import_notes.txt` that says what to set in Unreal for each file
   (Normalmap compression, sRGB off for N and ORM).
4. **Channel Packer** combines any four channels of other images into one new image (for example a glossiness map inverted
   into roughness). **Normal Map** flips the green channel of any image.

Your original images and materials are never changed. Baked, unsaved images are handled safely.

## Texel Density

Texel density is how many texture pixels cover one meter of surface. A world looks sharp and consistent only when it is the
same everywhere. A common target for props is **512 px/m** (about 5 px/cm).

1. Choose the **Target** (presets from 128 to 4096 px/m, or your own) and press **Measure** on the active object. The panel
   shows the average, lowest and highest density, how much of the surface is off target, how much of the UV square is used
   and how many faces lie outside it. The texture size comes from the material's base color image (or your default).
2. **Show Colors** paints every face: **blue** too low, **green** on target, **red** too high. **Hide Colors** removes it.
3. **Set Density** scales the UV islands. **Each Island** gives every island exactly the target. **Whole Object** scales
   everything together and keeps the relative sizes. In Edit Mode only the selected faces change.
4. **Copy from Active** gives other selected objects the density of the active one. **Pack Islands (Keep Density)** arranges
   the islands without changing their size.

Set the density first, then pack, so that nothing is scaled again afterwards. UDIM tiles are not handled.

## Collision Maker

Unreal reads collision shapes from objects named `UBX_` (box), `USP_` (sphere), `UCP_` (capsule) and `UCX_` (convex), followed
by the mesh name and a number: `UBX_Crate_00`.

1. Select a mesh, pick a **Shape** and press **Create Collision**. **Auto** chooses the simplest shape that fits: box, sphere,
   capsule, one convex hull, or **Convex Parts** for concave meshes (a donut, an L-shaped room).
2. The shapes are children of the mesh, shown as wire and hidden from renders. **Box Fit** can be oriented or axis aligned;
   **Max Vertices** limits a hull (Unreal accepts 255); **Parts** sets how many hulls Convex Parts may use.
3. **Check Collision** finds shapes Unreal would ignore or distort: orphans, non-convex hulls, too many vertices, mesh names
   with dots or spaces. **Fix** replaces a bad hull by its convex hull.
4. **UE5 Bridge** exports the shapes in the same FBX as the mesh, with matching names, and keeps their position relative to
   the mesh. Shapes are never exported as meshes of their own.

Convex Parts uses a simple splitting method, not a full approximate convex decomposition; check the result in Unreal's
collision view for very complex shapes.

## Hard Surface Kit

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

## Game Rig Kit

Builds the Unreal Engine 5 mannequin skeleton (bone names and hierarchy of the standard Manny and Quinn) on your character,
skins the mesh, adds IK and retargets animations.

1. Select the character mesh and press **Create Markers**. Twelve empties appear at standard human proportions (a T-pose
   facing -Y). Move the left-side markers onto the joints of your model; the right side is mirrored.
2. **Build Rig** creates the skeleton: root, pelvis, five spine bones, neck, head, arms with fingers, legs with feet and balls
   and, if you keep **IK Helper Bones**, ik_foot and ik_hand bones. Press it again after moving markers.
3. **Bind Meshes**: select the meshes, then the rig last. Automatic heat weights are created, then limited to **Max
   Influences** bones per vertex (4 is the mobile limit), tiny weights removed and the rest normalized. The mesh should be
   closed and clean; if heat weights fail, envelope weights are used and you are told.
4. **Set Up IK** adds IK to legs and arms: target bones, knee and elbow poles, and a pole angle chosen so the rest pose does
   not move. The foot and hand follow the rotation of their target.
5. **Rename to UE5** renames a Mixamo, Rigify or generic rig to the mannequin names (vertex groups follow). **Create Mapping
   Sheet** lists the bones that could not be matched; write `source bone = ue bone` lines and run it again.
6. **Retarget Animation**: pick the **Source Rig** (with an action), select the target rig and press the button. The motion
   is transferred as how far each bone turned from its rest pose, so rigs with different rest poses work; the pelvis
   movement is scaled by the height ratio.
7. **Check Skeleton** compares the rig with the mannequin: single root, missing bones, extra bones, object transform, names.

Limits: no twist bones, face rig or foot locking; fingers are placed by proportion, so check them; the retarget copies
rotations (and pelvis position) only.
