"""Self-check for game_rig. Run it with `python tools/bdev.py check blender-toolkit/game_rig`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_game_rig.py

Builds the UE5 mannequin skeleton from markers and checks the hierarchy, symmetry and positions; skins a mesh and checks
the weights; renames Mixamo and Rigify rigs; sets up IK and checks the rest pose and that the targets are reached;
runs the skeleton checker; and retargets an animation between rigs with different rest poses against an
independent geometric expectation.
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "game_rig")
spec = importlib.util.spec_from_file_location(
    "game_rig", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
gr = importlib.util.module_from_spec(spec)
sys.modules["game_rig"] = gr
spec.loader.exec_module(gr)
from game_rig import bind, builder, checker, rename, ue_bones  # noqa: E402  (needs the module registered above)

gr.register()
failures = []
sc = bpy.context.scene
s = sc.gr_settings


def check(condition, message):
    if not condition:
        failures.append(message)


def near(a, b, tol=1e-3):
    return abs(a - b) <= tol


def select_only(*objects, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objects)
    bpy.context.view_layer.objects.active = active or objects[0]


# ---- the skeleton definition
tree = ue_bones.parents(ik=True, fingers=True)
check(list(tree)[0] == "root" and sum(1 for p in tree.values() if p is None) == 1, "one root, listed first")
check(
    all(parent is None or list(tree).index(parent) < list(tree).index(child) for child, parent in tree.items()),
    "every parent is listed before its children",
)
for name in ("spine_05", "neck_02", "thumb_03_r", "pinky_01_l", "ik_hand_gun", "calf_l", "ball_r", "ik_foot_root"):
    check(name in tree, f"the mannequin bone {name} exists")
check(len(ue_bones.parents(ik=False, fingers=False)) == 1 + 1 + 5 + 3 + 2 * 8, "bone count without fingers and IK")

# ---- markers from a character-sized mesh
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.0, 3.0, 0.9))
body = bpy.context.object
body.name = "Body"
body.scale = (0.6, 0.3, 1.8)
bpy.context.view_layer.update()
select_only(body)
check(bpy.ops.game_rig.markers() == {"FINISHED"}, "markers are created")
check(
    len([o for o in bpy.data.objects if o.name.startswith("GR_")]) == 3 + 9, "3 center markers and 9 left-side markers"
)
points = builder.read_markers()
check(
    near(points["Pelvis"].z, 0.53 * 1.8) and near(points["HeadTop"].z, 1.8),
    f"markers follow the proportions: {points['Pelvis']}",
)
check(
    near(points["Ankle_R"].x - points["Pelvis"].x, -(points["Ankle_L"].x - points["Pelvis"].x)),
    "the right side mirrors the left",
)
check(near(points["Pelvis"].x, 2.0) and near(points["Pelvis"].y, 3.0), "markers are centered on the mesh")

# ---- building the rig
s.rig_name, s.ik_bones, s.fingers = "Hero", True, True
check(bpy.ops.game_rig.build() == {"FINISHED"}, "build finishes")
rig = bpy.data.objects["Hero"]
bones = rig.data.bones
check(set(bones.keys()) == set(tree), f"the rig has exactly the mannequin bones: {set(tree) ^ set(bones.keys())}")
check(all((b.parent.name if b.parent else None) == tree[b.name] for b in bones), "the hierarchy is the mannequin's")
check(
    not bones["root"].use_deform and not bones["ik_foot_l"].use_deform and bones["thigh_l"].use_deform,
    "helpers do not deform",
)
check((bones["pelvis"].head_local - points["Pelvis"]).length < 1e-4, "the pelvis sits on its marker")
check(
    (bones["thigh_l"].head_local - points["Hip_L"]).length < 1e-4
    and (bones["calf_r"].tail_local - points["Ankle_R"]).length < 1e-4,
    "limb bones run between their markers",
)
asym = max(
    (
        bones[n].head_local
        - Vector(
            (
                2 * points["Pelvis"].x - bones[n.replace("_l", "_r")].head_local.x,
                bones[n.replace("_l", "_r")].head_local.y,
                bones[n.replace("_l", "_r")].head_local.z,
            )
        )
    ).length
    for n in tree
    if n.endswith("_l")
)
check(asym < 1e-4, f"left and right bones are mirror images (worst {asym:.2e})")
check(
    len([b for b in bones if b.name.startswith(("index", "thumb", "middle", "ring", "pinky"))]) == 30, "30 finger bones"
)
check(bones["spine_02"].use_connect and bones["calf_l"].use_connect, "chains are connected")

# moving a marker moves the rig on the next build
bpy.data.objects["GR_Knee_L"].location.y -= 0.05
select_only(body)
bpy.ops.object.mode_set(mode="OBJECT")
s.rig_name = "Hero2"
bpy.ops.game_rig.build()
check(
    bpy.data.objects["Hero2"].data.bones["calf_l"].head_local.y < bones["calf_l"].head_local.y - 0.04,
    "a moved marker moves the knee",
)
bpy.data.objects.remove(bpy.data.objects["Hero2"])
bpy.data.objects["GR_Knee_L"].location.y += 0.05

# ---- skinning
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.25, depth=1.7, location=(2.0, 3.0, 0.95))
tube = bpy.context.object
tube.name = "Tube"
select_only(tube, rig, active=rig)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="DESELECT")
tube.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
s.max_influences = 3
result = bind.bind(bpy.context, rig, [tube], 3)
check(result.get("Tube") == "ARMATURE_AUTO", f"automatic weights worked: {result}")
check(any(m.type == "ARMATURE" and m.object == rig for m in tube.modifiers), "the mesh has the armature modifier")
worst_count, worst_sum = 0, 0.0
for v in tube.data.vertices:
    weights = [g.weight for g in v.groups if g.weight > 0]
    worst_count = max(worst_count, len(weights))
    worst_sum = max(worst_sum, abs(sum(weights) - 1.0))
check(worst_count <= 3, f"at most 3 influences per vertex ({worst_count})")
check(worst_sum < 1e-3, f"the weights of every vertex add up to 1 ({worst_sum:.2e})")
check({g.name for g in tube.vertex_groups} <= set(bones.keys()), "vertex groups are named after bones")

# ---- renaming Mixamo and Rigify names
expected = {
    "mixamorig:Hips": "pelvis",
    "mixamorig:Spine": "spine_01",
    "mixamorig:Spine2": "spine_03",
    "mixamorig:Neck": "neck_01",
    "mixamorig:Head": "head",
    "mixamorig:LeftShoulder": "clavicle_l",
    "mixamorig:LeftArm": "upperarm_l",
    "mixamorig:LeftForeArm": "lowerarm_l",
    "mixamorig:RightHand": "hand_r",
    "mixamorig:LeftHandIndex1": "index_01_l",
    "mixamorig:RightHandThumb3": "thumb_03_r",
    "mixamorig:LeftHandPinky2": "pinky_02_l",
    "mixamorig:LeftUpLeg": "thigh_l",
    "mixamorig:LeftLeg": "calf_l",
    "mixamorig:RightFoot": "foot_r",
    "mixamorig:RightToeBase": "ball_r",
    "DEF-spine": "pelvis",
    "DEF-spine.001": "spine_01",
    "DEF-spine.006": "head",
    "DEF-upper_arm.L": "upperarm_l",
    "DEF-forearm.R": "lowerarm_r",
    "DEF-thigh.L": "thigh_l",
    "DEF-shin.R": "calf_r",
    "DEF-foot.L": "foot_l",
    "DEF-toe.R": "ball_r",
    "DEF-f_index.01.L": "index_01_l",
    "DEF-shoulder.R": "clavicle_r",
    "DEF-hand.L": "hand_l",
    "Arm.L": "upperarm_l",
    "L_Thigh": "thigh_l",
    "Hips": "pelvis",
    "Foot_R": "foot_r",
}
wrong = {k: (rename.ue_name(k), v) for k, v in expected.items() if rename.ue_name(k) != v}
check(not wrong, f"Mixamo, Rigify and generic names are matched: {wrong}")
check(
    rename.ue_name("Tail01") is None and rename.ue_name("mixamorig:LeftHandIndex4") is None,
    "unknown names stay unmatched",
)

arm_data = bpy.data.armatures.new("Mix")
mixamo = bpy.data.objects.new("Mix", arm_data)
sc.collection.objects.link(mixamo)
select_only(mixamo)
bpy.ops.object.mode_set(mode="EDIT")
chain = [
    ("mixamorig:Hips", None, (0, 0, 1.0), (0, 0, 1.1)),
    ("mixamorig:Spine", "mixamorig:Hips", (0, 0, 1.1), (0, 0, 1.3)),
    ("mixamorig:LeftUpLeg", "mixamorig:Hips", (0.1, 0, 1.0), (0.1, 0, 0.5)),
    ("mixamorig:LeftLeg", "mixamorig:LeftUpLeg", (0.1, 0, 0.5), (0.1, 0, 0.1)),
    ("Tail", "mixamorig:Hips", (0, 0.1, 1.0), (0, 0.4, 1.0)),
]
for name, parent, head, tail in chain:
    made = arm_data.edit_bones.new(name)
    made.head, made.tail = head, tail
    if parent:
        made.parent = arm_data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")
leg = bpy.data.objects.new("MixLeg", bpy.data.meshes.new("MixLeg"))
sc.collection.objects.link(leg)
leg.vertex_groups.new(name="mixamorig:LeftUpLeg")
mod = leg.modifiers.new("Armature", "ARMATURE")
mod.object = mixamo
select_only(mixamo)
renames, unmatched = rename.rename_rig(mixamo)
check(
    {b.name for b in mixamo.data.bones} == {"pelvis", "spine_01", "thigh_l", "calf_l", "Tail"},
    f"bones are renamed: {[b.name for b in mixamo.data.bones]}",
)
check(unmatched == ["Tail"], f"the unmatched bone is reported: {unmatched}")
check(leg.vertex_groups[0].name == "thigh_l", f"vertex groups follow the bones: {leg.vertex_groups[0].name}")
text, count = rename.mapping_sheet(mixamo, "gr_bone_map")
check(count == 1 and "Tail" in text.as_string(), "the mapping sheet lists the unmatched bone")
text.clear()
text.write("Tail = spine_02\n")
rename.rename_rig(mixamo, text)
check("spine_02" in mixamo.data.bones and "Tail" not in mixamo.data.bones, "the sheet decides what the guesses cannot")

# ---- IK: the rest pose does not change and the targets are reached
select_only(rig)
check(bpy.ops.game_rig.ik_setup() == {"FINISHED"}, "ik setup finishes")
for name in ("pole_knee_l", "pole_elbow_r", "ik_foot_l", "ik_hand_r"):
    check(name in rig.data.bones, f"{name} exists")
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = rig.evaluated_get(depsgraph)
worst = max((evaluated.pose.bones[b.name].head - b.head_local).length for b in rig.data.bones)
check(worst < 2e-3, f"the rest pose is unchanged by IK (worst {worst:.2e})")
foot = rig.pose.bones["ik_foot_l"]
rest_pose_matrix = foot.matrix.copy()
moved_matrix = rest_pose_matrix.copy()
moved_matrix.translation += Vector((0.0, -0.10, 0.12))  # forward and up, in armature space
foot.matrix = moved_matrix
bpy.context.view_layer.update()
evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
ankle = evaluated.pose.bones["foot_l"].head
target = evaluated.pose.bones["ik_foot_l"].head
check((ankle - target).length < 2e-3, f"the ankle follows the IK target: {(ankle - target).length:.2e}")
knee = evaluated.pose.bones["calf_l"].head
hip = evaluated.pose.bones["thigh_l"].head
check(
    knee.y < min(hip.y, ankle.y) - 0.005,
    f"the knee bends forward, toward the pole: knee y {knee.y:.3f}, hip y {hip.y:.3f}, ankle y {ankle.y:.3f}",
)
pivot = rest_pose_matrix.translation
foot.matrix = (
    Matrix.Translation(pivot)
    @ Matrix.Rotation(math.radians(30), 4, "X")
    @ Matrix.Translation(-pivot)
    @ rest_pose_matrix
)
bpy.context.view_layer.update()
evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
turn = (
    evaluated.pose.bones["foot_l"]
    .matrix.to_quaternion()
    .rotation_difference(evaluated.pose.bones["ik_foot_l"].matrix.to_quaternion())
).angle
check(turn < 0.02, f"the foot turns with the IK target ({turn:.4f} rad apart)")
foot.matrix = rest_pose_matrix
check(
    bpy.ops.game_rig.ik_remove() == {"FINISHED"} and "pole_knee_l" not in rig.data.bones,
    "remove IK deletes constraints and poles",
)
check(not any(c.name.startswith("GR ") for p in rig.pose.bones for c in p.constraints), "no kit constraints remain")

# ---- the checker
issues = {i["code"] for i in checker.check(rig)}
check("MISSING" not in issues and "ROOTS" not in issues, f"a built rig matches the mannequin: {issues}")
broken = bpy.data.objects.new("Broken", bpy.data.armatures.new("Broken"))
sc.collection.objects.link(broken)
select_only(broken)
bpy.ops.object.mode_set(mode="EDIT")
for name, head in (("Hips", (0, 0, 1)), ("Extra.1", (1, 0, 1))):
    made = broken.data.edit_bones.new(name)
    made.head, made.tail = head, (head[0], head[1], head[2] + 0.2)
bpy.ops.object.mode_set(mode="OBJECT")
broken_codes = {i["code"] for i in checker.check(broken)}
check({"ROOTS", "MISSING", "NAMES"} <= broken_codes, f"a broken rig is reported: {broken_codes}")
bpy.ops.game_rig.check()
check(len(sc.gr_issues) >= 3, "the check operator fills the list")


# ---- retargeting between different rest poses
def make_chain(name, spec, location=(0, 0, 0)):
    data = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, data)
    ob.location = location
    sc.collection.objects.link(ob)
    select_only(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone, parent, head, tail in spec:
        made = data.edit_bones.new(bone)
        made.head, made.tail = head, tail
        if parent:
            made.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


source = make_chain(
    "Src",
    [
        ("mixamorig:Hips", None, (0, 0, 1.0), (0, 0, 1.2)),
        ("mixamorig:Spine", "mixamorig:Hips", (0, 0, 1.2), (0, 0, 1.5)),
        ("mixamorig:LeftShoulder", "mixamorig:Spine", (0, 0, 1.5), (0.2, 0, 1.5)),
        ("mixamorig:LeftArm", "mixamorig:LeftShoulder", (0.2, 0, 1.5), (0.6, 0, 1.5)),
        ("mixamorig:LeftForeArm", "mixamorig:LeftArm", (0.6, 0, 1.5), (1.0, 0, 1.5)),
    ],
)
down = Vector((0.8, 0, -0.6)).normalized()  # the target's arm hangs lower: a different rest pose
elbow_t = Vector((0.2, 0, 3.0)) + down * 0.8
target_rig = make_chain(
    "Dst",
    [
        ("pelvis", None, (0, 0, 2.0), (0, 0, 2.4)),
        ("spine_01", "pelvis", (0, 0, 2.4), (0, 0, 3.0)),
        ("clavicle_l", "spine_01", (0, 0, 3.0), (0.2, 0, 3.0)),
        ("upperarm_l", "clavicle_l", (0.2, 0, 3.0), tuple(elbow_t)),
        ("lowerarm_l", "upperarm_l", tuple(elbow_t), tuple(elbow_t + down * 0.8)),
    ],
)
src_arm = source.pose.bones["mixamorig:LeftArm"]
source.animation_data_create()
source.animation_data.action = bpy.data.actions.new("Wave")
swing = Matrix.Rotation(math.radians(50), 4, "Y")  # world rotation of the upper arm about Y at frame 10
src_arm.rotation_mode = "QUATERNION"
src_arm.keyframe_insert("rotation_quaternion", frame=1)
bpy.context.scene.frame_set(10)
rest_matrix = source.data.bones["mixamorig:LeftArm"].matrix_local
shoulder_joint = rest_matrix.translation
src_arm.matrix = (
    Matrix.Translation(shoulder_joint) @ swing @ Matrix.Translation(-shoulder_joint) @ rest_matrix
)  # a pure turn
src_arm.keyframe_insert("rotation_quaternion", frame=10)
hips = source.pose.bones["mixamorig:Hips"]
hips.keyframe_insert("location", frame=1)
hips_rest = hips.matrix.copy()
hips.matrix = Matrix.Translation((0.0, 0.5, 0.0)) @ hips_rest  # half a meter along world Y
hips.keyframe_insert("location", frame=10)
bpy.context.scene.frame_set(1)
select_only(target_rig)
s.source_rig = source
s.step = 1
check(bpy.ops.game_rig.retarget() == {"FINISHED"}, "retarget finishes")
action = target_rig.animation_data.action
check(
    action is not None and action.name == "Wave_UE",
    f"the new action is named after the source: {action.name if action else None}",
)
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
evaluated = target_rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
rest_dir = (
    target_rig.data.bones["upperarm_l"].tail_local - target_rig.data.bones["upperarm_l"].head_local
).normalized()
direction = (evaluated.pose.bones["upperarm_l"].tail - evaluated.pose.bones["upperarm_l"].head).normalized()
check((direction - rest_dir).length < 1e-3, "frame 1 (rest) keeps the target in its own rest pose")
bpy.context.scene.frame_set(10)
bpy.context.view_layer.update()
evaluated = target_rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
direction = (evaluated.pose.bones["upperarm_l"].tail - evaluated.pose.bones["upperarm_l"].head).normalized()
expected_dir = (swing.to_3x3() @ rest_dir).normalized()
check(
    (direction - expected_dir).length < 2e-3,
    f"the upper arm turns like the source: {[round(x, 3) for x in direction]} vs {[round(x, 3) for x in expected_dir]}",
)
forearm = (evaluated.pose.bones["lowerarm_l"].tail - evaluated.pose.bones["lowerarm_l"].head).normalized()
forearm_rest = (
    target_rig.data.bones["lowerarm_l"].tail_local - target_rig.data.bones["lowerarm_l"].head_local
).normalized()
check((forearm - (swing.to_3x3() @ forearm_rest).normalized()).length < 2e-3, "the forearm follows its parent")
moved = evaluated.pose.bones["pelvis"].head - target_rig.data.bones["pelvis"].head_local
check(
    (moved - Vector((0, 1.0, 0))).length < 2e-3,
    f"the hips travel is scaled by the height ratio (0.5 m x 2): {tuple(round(x, 3) for x in moved)}",
)

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Build Rig")
prefs.language = "en_US"
check(translated == "Rig'i Kur", f"Turkish translation active ({translated!r})")

gr.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("OK: game_rig markers, build, skin, rename, ik, checker, retarget")
