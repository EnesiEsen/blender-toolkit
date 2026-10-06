# FiveM Toolkit

Turn plain Blender meshes into FiveM assets with fewer clicks: a **Doctor** that finds what breaks FiveM assets and fixes
the safe problems, a **Prop** builder (drawable, collision, LODs, archetype, DDS textures), an **MLO / Interior** builder
and **Ped** weight tools. It sits on top of [Sollumz](https://docs.sollumz.org), which does the actual GTA V file
conversion; this add-on prepares your scene for it and drives it.

[Türkçe](fivem_toolkit.tr.md) · [Back to the overview](../README.md)

![FiveM Toolkit panel](images/fivem_toolkit.png)

## Requirements

- Blender 5.0 to 5.2.
- **Sollumz** installed and enabled. If it is missing, the panel shows a red notice. Tested with the Sollumz
  development builds 2.8.0 (Blender 5.0) and 2.8.3 (Blender 5.2).

The panel is in the sidebar tab **FiveM**. Choose what you are making with **Prop**, **MLO / Interior** or
**Ped / Clothing**. The **Doctor** and **Export** sub-panels are shared.

## Doctor: check and fix

Press **Check Assets** (select the objects, or leave nothing selected to check the scene). Each problem is listed in plain
words with a **Fix** button, or press **Fix All**.

| Problem | Fixed automatically? | What it means |
|---|---|---|
| Invalid or duplicate asset name | Yes | FiveM asset names must be lower-case letters, digits and underscores and unique. |
| Unapplied scale or rotation | Yes | The transform is applied so the prop has the right size in game. |
| Modifiers still on the mesh | Yes | They are applied before conversion. |
| No UV map | Yes | A simple box-projected UV map is generated. Unwrap properly yourself for a good result. |
| No material / unused material slots | Yes | A default material (`fk_default`) is added, unused slots are removed. |
| Texture too large (above **Max Texture Size**, 512 to 4096) | Yes | The texture is scaled down. |
| Texture not DDS | Yes | Converted to DDS with power-of-two sides, never above **Max Texture Size**. See below. |
| Missing texture file | No | Relink or remove the texture. |
| More triangles than **Triangle Warning** (default 100,000) | No | Reduce the mesh, for example with Retopo Kit. |
| Empty mesh | No | Delete it. |

## Prop

Select the meshes and press **Build Props**. For each object (or for all together when **One Prop per Object** is off):

1. The Doctor's safe fixes run first (**Fix Problems First**).
2. The mesh becomes a Sollumz drawable and the materials are converted.
3. **Collision**: *Simplified Copy* (a low-poly copy, default, with **Collision Triangles** as target), *Convex Hull*,
   *Exact Mesh* or *None*.
4. **Generate LODs**: medium, low and very-low versions. **LOD Strength**: *Balanced* (50 / 25 / 10 % of the triangles),
   *Aggressive* (35 / 12 / 4 %) or *Gentle* (70 / 45 / 25 %). Levels that would save almost nothing are skipped, and
   tiny meshes get none. **LOD Distance Scale** multiplies the distances, which are worked out from the prop's size.
5. **Create YTYP Archetype**: a Sollumz archetype for every prop, with the right bounds and LOD distances.
6. **Convert Textures to DDS**: FiveM needs DDS (DXT1 or DXT5 with mipmaps). The add-on has its own encoder and keeps
   the alpha channel when there is one.

Then open **Export**: set **Resource Name** and **Output Folder**, choose **FiveM (binary)** (`.ydr`, `.ybn`, `.ytyp`,
`.ytd`, ready for `stream/`) or **CodeWalker XML**, and press **Export Resource**. You get a resource folder with a
`stream` folder and an `fxmanifest.lua` that already lists the `.ytyp` files. **Selected Only** exports just the selection.

## MLO / Interior

Interiors are described by the outliner structure of one collection:

```
my_interior                  <- select this collection
  room.hall                  <- one sub-collection per room, with its meshes
  room.kitchen
  portal.hall.kitchen        <- a quad that joins two rooms (the opening)
  portal.limbo.hall          <- limbo = the outside; this one is the entrance
```

1. **Create Interior Template** adds a starter layout (two rooms, a portal between them, an entrance). Replace the
   boxes with your own meshes.
2. **Check Interior** lists what is wrong with the rooms and portals (for example a portal that names a missing room, or
   too many objects in limbo: GTA allows 12 at most).
3. **Build Interior** turns the room meshes into props, builds the interior collision (**Interior Collision**:
   simplified copy with **Triangles per Mesh**, or exact mesh), and fills the MLO archetype with rooms, portals and
   entities. **Generate LODs**, **Convert Textures to DDS** and **Fix Problems First** apply here too.
4. Export with **Export Resource** as for props.

## Ped / Clothing

For rigged characters and clothing meshes.

1. Select the rigged meshes. Set **GTA Skeleton** to the ped skeleton you imported from a GTA file (Sollumz YFT import).
2. **Check Assets** lists weight problems: no armature, unweighted vertices, more than 4 bone influences per vertex (the
   GTA vertex format stores 4), weights that do not add up to 1, empty groups, and groups that match no GTA bone.
3. **Retarget Weights** renames and merges the vertex groups onto GTA V bones. It guesses the match from the names
   (Mixamo, Rigify and generic rigs: left/right, spine, fingers ...). Groups with no GTA counterpart are **merged into
   their nearest ancestor bone that exists**, so no weight is lost. A hidden backup copy of each mesh is kept when
   **Keep Weight Backup** is on.
4. For names the add-on cannot guess, press **Create Mapping Sheet**: it makes a text block listing the unmatched groups.
   Fill in `source bone = GTA bone` lines and run **Retarget Weights** again; your lines override the guesses.

The bone names come from Sollumz's own bone registry, so you do not need a skeleton file to validate.

## Limits and good to know

- The output is checked by exporting through Sollumz and reading it back, not by loading it in a live FiveM server or in
  CodeWalker. Test your first asset in game before you build a big pack.
- Textures end up **embedded in the `.ydr`**. A separate `.ytd` is optional (**Also Write a YTD**, off by default,
  needs Sollumz 2.8.3 or newer): the `.ytd` files Sollumz wrote in the tests were much smaller than expected, so they are
  not used by default.
- MLO portal direction follows Sollumz (counter-clockwise seen from the first room in the portal's name). If a portal
  looks inverted in CodeWalker, swap the two room names.
- YMT files (ped metadata, for example `.ymt` for clothing) are not written; Sollumz does not support them.
- This add-on does not touch the game or any server. It only writes asset files.
