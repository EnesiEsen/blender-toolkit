"""Self-check for ue5_bridge. Run it with `python tools/bdev.py check blender-toolkit/ue5_bridge`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_ue5_bridge.py

Exports static meshes, modular skeletal meshes and animations to FBX, imports the files back into Blender and checks
what Unreal would see: one root bone, no phantom leaf bones, the right size, the animation length and, with root motion
on, the walk travelling on the root bone. Unreal Engine itself is not needed (nor available); the rules come from
Epic's guidance.
"""
import importlib.util
import math
import os
import sys
import tempfile

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "ue5_bridge")
spec = importlib.util.spec_from_file_location("ue5_bridge", os.path.join(PKG, "__init__.py"),
                                              submodule_search_locations=[PKG])
ue = importlib.util.module_from_spec(spec)
sys.modules["ue5_bridge"] = ue
spec.loader.exec_module(ue)
from ue5_bridge import export, motion, rig  # noqa: E402  (needs the module registered above)

ue.register()
failures = []
tmp = tempfile.mkdtemp(prefix="ue_")


def check(condition, message):
    if not condition:
        failures.append(message)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene.ue_settings
    s.output_dir = tmp
    return bpy.context.scene, s


def make_rig(name, bones, location=(0, 0, 0)):
    """Bones pointing along +Y, so local axes equal armature axes and keyframes are easy to read."""
    data = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for bone, parent, head in bones:
        edit = data.edit_bones.new(bone)
        edit.head, edit.tail = head, (head[0], head[1] + 0.1, head[2])
        if parent:
            edit.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.location = location
    return ob


def skinned_box(name, armature, weights, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=location)
    ob = bpy.context.object
    ob.name = name
    ob.parent = armature
    ob.matrix_parent_inverse = armature.matrix_world.inverted()
    for bone in weights:
        ob.vertex_groups.new(name=bone)
    for v in ob.data.vertices:
        for bone, weight in weights.items():
            ob.vertex_groups[bone].add([v.index], weight, "REPLACE")
    ob.modifiers.new("Armature", "ARMATURE").object = armature
    return ob


def import_fbx(path):
    before = {o.as_pointer() for o in bpy.data.objects}
    bpy.ops.import_scene.fbx(filepath=str(path))
    return [o for o in bpy.data.objects if o.as_pointer() not in before]


def remove(objects):
    for o in objects:
        bpy.data.objects.remove(o)


def world_size(ob):
    points = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]


# ---- names
sc, s = reset()
check(export.ue_name("My Crate.001", "SM_", s) == "SM_My_Crate", "ue_name sanitizes and prefixes")
check(export.ue_name("SM_Crate", "SM_", s) == "SM_Crate", "an existing prefix is kept")
s.prefixes = False
check(export.ue_name("Crate", "SM_", s) == "Crate", "prefixes can be turned off")
s.prefixes = True

# ---- rig check: two root bones, a scaled armature object, the default name
sc, s = reset()
bad = make_rig("Armature", [("Hips", None, (0, 0, 1)), ("Spine", "Hips", (0, 0, 1.1)), ("Prop", None, (0.5, 0, 1))])
bad.scale = (2, 2, 2)
bpy.context.view_layer.update()
issues = {i["code"] for i in rig.scan(bad)}
check({"MULTI_ROOT", "ARMATURE_TRANSFORM", "ARMATURE_NAME"} <= issues,
      f"rig check finds the problems: {sorted(issues)}")
bpy.context.view_layer.objects.active = bad
check(rig.ensure_single_root(bpy.context, bad, "root") == "root" and len(rig.root_bones(bad)) == 1,
      "a single root is added above both roots")
check({b.name for b in bad.data.bones["root"].children} == {"Hips", "Prop"} and not bad.data.bones["root"].use_deform,
      "the old roots hang under it and the new root does not deform")

# ---- static meshes: centered, rotation and scale baked in, the scene untouched
sc, s = reset()
bpy.ops.mesh.primitive_cube_add(size=2, location=(5, 3, 1))
crate = bpy.context.object
crate.name = "Crate A"
crate.scale = (2.0, 1.0, 0.5)
crate.rotation_euler = (0, 0, math.radians(30))
bpy.context.view_layer.update()
expected = world_size(crate)
located = tuple(crate.location)
compat_select = [crate]
for o in bpy.context.view_layer.objects:
    o.select_set(o in compat_select)
bpy.context.view_layer.objects.active = crate
check(bpy.ops.ue5_bridge.export_static() == {"FINISHED"}, "static export operator")
path = os.path.join(tmp, "StaticMeshes", "SM_Crate_A.fbx")
check(os.path.exists(path), f"static FBX written: {os.listdir(tmp)}")
check(tuple(crate.location) == located and tuple(crate.scale) == (2.0, 1.0, 0.5) and crate.name == "Crate A",
      "the scene object was not touched")
if os.path.exists(path):
    imported = import_fbx(path)
    meshes = [o for o in imported if o.type == "MESH"]
    check(len(meshes) == 1, f"one mesh imported: {[o.name for o in imported]}")
    if meshes:
        bpy.context.view_layer.update()
        size = world_size(meshes[0])
        check(all(abs(a - b) < 0.02 * max(b, 0.1) for a, b in zip(size, expected, strict=True)),
              f"size survives the FBX round trip (units, axes): {[round(x, 3) for x in size]} vs "
              f"{[round(x, 3) for x in expected]}")
        centre = sum((meshes[0].matrix_world @ Vector(c) for c in meshes[0].bound_box), Vector()) / 8
        check(centre.length < 0.05, f"the part is centered at the origin: {tuple(round(x, 3) for x in centre)}")
    remove(imported)

# ---- skeletal meshes: two roots, scaled armature object, two modular parts
sc, s = reset()
skeleton = make_rig("Hero", [("Hips", None, (0, 0, 1)), ("Spine", "Hips", (0, 0, 1.1)), ("Head", "Spine", (0, 0, 1.2)),
                             ("Prop", None, (0.5, 0, 1))], location=(4, 2, 0))
body = skinned_box("body", skeleton, {"Hips": 0.5, "Spine": 0.5}, location=(4, 2, 1.0))
jacket = skinned_box("jacket", skeleton, {"Spine": 0.6, "Head": 0.4}, location=(4, 2, 1.2))
for o in bpy.context.view_layer.objects:
    o.select_set(o == skeleton)
bpy.context.view_layer.objects.active = skeleton
before_bones = [b.name for b in skeleton.data.bones]
check(bpy.ops.ue5_bridge.export_skeletal() == {"FINISHED"}, "skeletal export operator")
skeletal_dir = os.path.join(tmp, "SkeletalMeshes")
files = sorted(os.listdir(skeletal_dir)) if os.path.isdir(skeletal_dir) else []
check(files == ["SK_body.fbx", "SK_jacket.fbx"], f"one file per modular part: {files}")
check([b.name for b in skeleton.data.bones] == before_bones and len(rig.root_bones(skeleton)) == 2,
      "the scene skeleton was not changed (the fix happens on the copy)")
check(not [o for o in bpy.data.objects if o.name.startswith(rig.TEMP)], "no temporary objects are left behind")
for name in files:
    imported = import_fbx(os.path.join(tmp, "SkeletalMeshes", name))
    armatures = [o for o in imported if o.type == "ARMATURE"]
    check(len(armatures) == 1, f"{name}: one armature imported")
    if armatures:
        bones = armatures[0].data.bones
        roots = [b.name for b in bones if b.parent is None]
        check(roots == ["root"] or len(roots) == 1, f"{name}: exactly one root bone in the file: {roots}")
        check(not [b.name for b in bones if b.name.endswith("_end")], f"{name}: no phantom leaf bones: "
              f"{[b.name for b in bones]}")
        check({"Hips", "Spine", "Head", "Prop", "root"} <= {b.name for b in bones}, f"{name}: all bones present")
        mesh = next((o for o in imported if o.type == "MESH"), None)
        check(mesh is not None and len(mesh.vertex_groups) >= 2, f"{name}: the weights came along")
        if mesh is not None:
            bpy.context.view_layer.update()
            size = world_size(mesh)
            check(all(abs(v - 0.4) < 0.02 for v in size),
                  f"{name}: the part is 0.4 m wide: {[round(v, 3) for v in size]}")
            low = min((mesh.matrix_world @ Vector(c)).z for c in mesh.bound_box)
            check(-0.5 < low < 1.5, f"{name}: the part keeps its place relative to the skeleton: z from {low:.2f}")
    remove(imported)

# ---- animations: actions, the walk on the root bone, NLA tracks
sc, s = reset()
actor = make_rig("Actor", [("Hips", None, (0, 0, 1)), ("Spine", "Hips", (0, 0, 1.1))], location=(3, 3, 0))
actor.animation_data_create()
hips = actor.pose.bones["Hips"]
for frame, (y, z) in ((1, (0.0, 0.0)), (13, (1.2, 0.05)), (25, (2.4, 0.0))):
    hips.location = (0.0, y, z)
    hips.keyframe_insert("location", frame=frame)
actor.animation_data.action.name = "walk"
idle = bpy.data.actions.new("idle")
actor.animation_data.action = idle
spine = actor.pose.bones["Spine"]
for frame, x in ((1, 0.0), (11, 0.02)):
    spine.location = (x, 0.0, 0.0)
    spine.keyframe_insert("location", frame=frame)
actor.animation_data.action = None
check(export.action_bone_names(bpy.data.actions["walk"]) == {"Hips"}, "action_bone_names reads layered actions")
for o in bpy.context.view_layer.objects:
    o.select_set(o == actor)
bpy.context.view_layer.objects.active = actor
s.anim_source, s.root_motion = "ACTIONS", True
check(bpy.ops.ue5_bridge.export_animations() == {"FINISHED"}, "animation export operator")
anim_dir = os.path.join(tmp, "Animations")
check(sorted(os.listdir(anim_dir)) == ["A_Actor_idle.fbx", "A_Actor_walk.fbx"],
      f"one file per action: {os.listdir(anim_dir)}")
check(actor.animation_data.action is None and sorted(a.name for a in bpy.data.actions) == ["idle", "walk"],
      "the scene actions were not changed and no copies remain")
original = bpy.data.actions["walk"]
check({tuple(round(k.co[1], 3) for k in fc.keyframe_points) for layer in original.layers for strip in layer.strips
       for bag in strip.channelbags for fc in bag.fcurves if fc.array_index == 1} == {(0.0, 1.2, 2.4)},
      "the original walk action keeps the motion on the hips")

imported = import_fbx(os.path.join(anim_dir, "A_Actor_walk.fbx"))
arm = next((o for o in imported if o.type == "ARMATURE"), None)
check(arm is not None and arm.animation_data and arm.animation_data.action, "the animation file holds an action")
if arm is not None and arm.animation_data and arm.animation_data.action:
    first, last = arm.animation_data.action.frame_range
    check(abs((last - first) - 24) < 0.5, f"the animation is 24 frames long: {first} - {last}")
    roots = [b.name for b in arm.data.bones if b.parent is None]
    check(roots == ["root"], f"the animation skeleton has the single root bone: {roots}")

    def head_at(frame, name):
        sc.frame_set(int(frame))
        bpy.context.view_layer.update()
        return arm.matrix_world @ arm.pose.bones[name].head

    travelled = head_at(last, "root") - head_at(first, "root")
    check(abs(travelled.length - 2.4) < 0.08, f"the root bone travels the 2.4 m of the walk: {travelled.length:.3f}")
    hips_vs_root = (head_at(last, "Hips") - head_at(last, "root")) - (head_at(first, "Hips") - head_at(first, "root"))
    check(hips_vs_root.length < 0.08, f"the hips no longer carry the walk: {hips_vs_root.length:.3f}")
remove(imported)

# the extraction alone, on a copy: the walk moves to the root bone and the final pose of every frame is unchanged
sc, s = reset()
actor = make_rig("Actor", [("root", None, (0, 0, 0)), ("Hips", "root", (0, 0, 1)), ("Spine", "Hips", (0, 0, 1.1))])
actor.animation_data_create()
hips = actor.pose.bones["Hips"]
for frame, (y, z) in ((1, (0.0, 0.0)), (13, (1.2, 0.05)), (25, (2.4, 0.0))):
    hips.location = (0.0, y, z)
    hips.keyframe_insert("location", frame=frame)
walk = actor.animation_data.action
before = {}
for frame in (1, 7, 13, 19, 25):
    sc.frame_set(frame)
    bpy.context.view_layer.update()
    before[frame] = actor.pose.bones["Spine"].matrix.copy()
distance = motion.extract_root_motion(bpy.context, actor, walk, "root", "Hips", 1, 25)
check(abs(distance - 2.4) < 1e-3, f"the extraction reports the walked distance: {distance}")
for frame, matrix in before.items():
    sc.frame_set(frame)
    bpy.context.view_layer.update()
    now = actor.pose.bones["Spine"].matrix
    off = max(abs(now[r][c] - matrix[r][c]) for r in range(4) for c in range(4))
    check(off < 1e-4, f"frame {frame}: the pose of the spine is unchanged by the extraction (off by {off:.5f})")
sc.frame_set(25)
bpy.context.view_layer.update()
root_bone, hips_bone = actor.pose.bones["root"], actor.pose.bones["Hips"]
check(abs(root_bone.location.y - 2.4) < 1e-3 or abs(root_bone.matrix.translation.y - 2.4) < 1e-3,
      "the root bone is at the end of the walk")
check(abs(hips_bone.matrix.translation.y - 2.4) < 1e-3, "the hips still end up where the animator put them")
try:
    motion.extract_root_motion(bpy.context, actor, walk, "root", "Spine", 1, 25)
    check(False, "hips that are not a child of the root must be refused")
except ValueError:
    pass
check(motion.find_hips(actor).name == "Hips", "the hips bone is found by name")
check(not isinstance(Matrix(), type(None)), "sanity")

# ---- NLA tracks: one file per track, and root motion on NLA is refused
sc, s = reset()
nla = make_rig("Nla", [("Hips", None, (0, 0, 1)), ("Spine", "Hips", (0, 0, 1.1))])
nla.animation_data_create()
for label, offset in (("runA", 0.0), ("runB", 0.5)):
    action = bpy.data.actions.new(label)
    nla.animation_data.action = action
    for frame, y in ((1, offset), (21, offset + 1.0)):
        nla.pose.bones["Hips"].location = (0.0, y, 0.0)
        nla.pose.bones["Hips"].keyframe_insert("location", frame=frame)
    nla.animation_data.action = None
    track = nla.animation_data.nla_tracks.new()
    track.name = label
    track.strips.new(label, 1, action)
for o in bpy.context.view_layer.objects:
    o.select_set(o == nla)
bpy.context.view_layer.objects.active = nla
s.anim_source, s.root_motion = "NLA", False
check(bpy.ops.ue5_bridge.export_animations() == {"FINISHED"}, "NLA export")
check(sorted(os.listdir(os.path.join(tmp, "Animations"))) == ["A_Actor_idle.fbx", "A_Actor_walk.fbx", "A_Nla_runA.fbx",
                                                              "A_Nla_runB.fbx"], "one file per NLA track")
s.root_motion = True
try:  # an operator that reports an ERROR raises RuntimeError when called from a script
    refused = bpy.ops.ue5_bridge.export_animations() == {"CANCELLED"}
except RuntimeError as e:
    refused = "NLA" in str(e)
check(refused, "root motion on NLA tracks is refused with a message")
check(all(not t.mute for t in nla.animation_data.nla_tracks), "the NLA tracks of the scene were not muted")

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Export Animations")
prefs.language = "en_US"
check(translated == "Animasyonları Dışa Aktar", f"Turkish translation active ({translated!r})")

ue.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("OK: ue5_bridge static, skeletal, animation, root motion")
