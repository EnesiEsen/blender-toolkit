# UE5 Bridge

Clean FBX export from Blender to Unreal Engine 5: static meshes, modular skeletal meshes that share one skeleton,
animations (one file per action or NLA track) and optional root motion. Every export works on temporary copies of your
objects, so nothing in your scene is moved, applied or renamed.

[Türkçe](ue5_bridge.tr.md) · [Back to the overview](../README.md)

![UE5 Bridge panel](images/ue5_bridge.png)

> **Status.** The exported files were checked by importing them back into Blender (bone hierarchy, sizes, animation
> length, root motion). The add-on was **not** tested inside Unreal Engine, because none was available. The settings
> follow Epic's FBX guidance; the one setting that may need a try in Unreal is **Armature Node** (see Troubleshooting).

The panel is in the sidebar tab **UE5**.

## What the exports use

These FBX settings are fixed on purpose, because they are the ones that import into Unreal at the right size and
orientation: Apply Scalings = *FBX Units Scale* (1 Blender meter becomes 100 Unreal centimeters), default axes
(-Z forward, Y up), face smoothing, tangent space (optional), no leaf bones, primary bone axis Y. File names are made
safe for Unreal: ASCII letters, digits and underscores, Blender's `.001` suffix removed.

## Static meshes

1. Select the meshes.
2. Set the **Export Folder** (a `StaticMeshes` folder is created inside it).
3. Press **Export Static Meshes**. One FBX per mesh, modifiers applied, rotation and scale baked in.

| Option | What it does |
|---|---|
| UE Name Prefixes | Names the files `SM_` (static), `SK_` (skeletal), `A_` (animation) unless the name already starts that way. |
| Center at Origin | Exports every part at (0, 0, 0), wherever it sits in the scene. |

Skinned meshes are skipped here; export them as skeletal meshes.

## Skeletal meshes

Select the armature (or its meshes) and press **Export Skeletal Meshes**. Files go to `SkeletalMeshes`.

| Option | What it does |
|---|---|
| Skeletal Meshes: One File per Mesh | Modular parts (trousers, jacket, shoes) are exported one by one, all sharing the same skeleton, so they fit together in Unreal. |
| Skeletal Meshes: One File | The skeleton and all its meshes in a single FBX. |
| Fix Skeleton on Export | Unreal needs exactly one root bone. If the skeleton has several, a root bone (named by **Root Bone**, default `root`) is added above them **on the export copy only**. |
| Only Deform Bones | Leaves control and helper bones out of the file. |
| Leaf Bones | Off by default. When on, Blender adds an extra end bone to every chain, which Unreal shows as phantom bones. |
| Armature Node | How the armature object itself is written (*Null*, *Root*, *Limb Node*). |
| Tangent Space | Writes tangents. |

**Check Skeleton** lists problems without changing anything: more than one root bone, no deform bones, scale or rotation
on the armature object, and the default name `Armature` (Unreal can mistake it for a bone). **Add Root Bone** fixes the
root problem on the real skeleton, if you want it fixed in the .blend file as well.

## Animations

Select the armature and press **Export Animations**. Files go to `Animations`, named `A_<armature>_<animation>.fbx`.

| Option | What it does |
|---|---|
| Animations: All Actions | Every action that animates this skeleton, one file each. |
| Animations: NLA Tracks | Every NLA track becomes its own file, named after the track. |
| Animations: Active Action | Only the action assigned to the armature now. |
| Bake Step | Frames between baked keys (1 = every frame). All bones are baked. |
| Root Motion | See below. |
| Hips Bone | Name of the hips bone for root motion. Leave empty to guess from the name (hips, pelvis ...). |

### Root motion

Unreal drives a character with the root bone (Root Motion, Motion Matching). With **Root Motion** on, the horizontal
movement of the hips (forward, sideways) is moved onto the root bone for every frame. The hips keep only what is left
over (bobbing, sway), and the final pose of every frame stays exactly what you animated. Turning is not extracted: it
stays on the hips.

- If the hips are the only root, a new root bone is added above them (on the export copy).
- If the hips sit deeper in the hierarchy than directly under the root, the export stops with a message.
- Root motion works with actions. With **NLA Tracks** it is refused with a message, because tracks can blend several
  actions.

## Typical workflow

1. Build the skeleton once, apply object scale and rotation (`Ctrl+A`), and give the armature a real name (`Hero`, not
   `Armature`).
2. **Check Skeleton**.
3. **Export Skeletal Meshes** once: import it into Unreal and let it create the skeleton asset.
4. **Export Animations**; when importing into Unreal, pick that existing skeleton so all animations share it.

## Troubleshooting

- **Unreal shows an extra root bone or the character is rotated.** Try another **Armature Node** value (*Root* or
  *Limb Node*). This was the one setting that could not be tested in Unreal.
- **The character is 100 times too small or too big.** Make sure the Blender scene unit scale is 1 and that you are not
  applying scale twice. The exports use FBX Units Scale.
- **Phantom bones at the end of every chain.** Keep **Leaf Bones** off.
- **Animation plays but the character does not move in the world.** Turn on **Root Motion** and enable root motion on the
  animation asset in Unreal.

## Limits

- Not verified inside Unreal Engine itself (see the status note).
- Root motion extracts translation only, no yaw (turning).
- Only the FBX path is covered. Alembic, USD and the Unreal Python API are not used.
