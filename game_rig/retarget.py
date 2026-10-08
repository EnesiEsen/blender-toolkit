"""Copy the animation of one rig onto another by transferring how far every bone turned from its rest pose."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Quaternion

from . import rename

HIPS = "pelvis"


def depth(bone):
    count = 0
    while bone.parent is not None:
        bone, count = bone.parent, count + 1
    return count


def pairs(source, target, sheet=None):
    """[(source bone, target bone)] ordered so that parents come first. Names are matched through the UE5 names."""
    sheet = sheet or {}
    wanted = {b.name: b for b in target.data.bones}
    found, used = [], set()
    for bone in source.data.bones:
        mapped = sheet.get(bone.name) or rename.ue_name(bone.name)
        if mapped in wanted and mapped not in used:
            found.append((bone.name, mapped))
            used.add(mapped)
    return sorted(found, key=lambda pair: depth(wanted[pair[1]]))


def rest_offset(bone):
    """Rotation of a bone relative to its parent in the rest pose (armature space for a root bone)."""
    if bone.parent is None:
        return bone.matrix_local.to_quaternion()
    return (bone.parent.matrix_local.inverted() @ bone.matrix_local).to_quaternion()


def rotation_of(bone, cache):
    """Armature-space rotation of a bone in the pose being built: animated bones are in `cache`, others at rest."""
    if bone.name not in cache:
        parent = rotation_of(bone.parent, cache) if bone.parent else Quaternion()
        cache[bone.name] = parent @ rest_offset(bone)
    return cache[bone.name]


def source_frames(source):
    action = source.animation_data.action if source.animation_data else None
    if action is None:
        raise ValueError(rpt_("'{name}' has no animation to copy.").format(name=source.name))
    first, last = action.frame_range
    return int(first), int(last), action


def retarget(context, source, target, step=1, sheet=None):
    """Bake the animation of `source` onto `target`. Returns (new action, number of bones copied)."""
    first, last, action = source_frames(source)
    mapped = pairs(source, target, sheet)
    if not mapped:
        raise ValueError(
            rpt_("No bone of '{source}' matches a bone of '{target}'.").format(source=source.name, target=target.name)
        )
    scene = context.scene
    sw, tw = source.matrix_world.to_quaternion(), target.matrix_world.to_quaternion()
    tw_inverse = tw.inverted()
    t_bones, s_bones = target.data.bones, source.data.bones
    height = {n: abs((source.matrix_world @ s_bones[n].head_local).z) for n, _ in mapped}
    result = bpy.data.actions.new(f"{action.name}_UE")
    target.animation_data_create()
    target.animation_data.action = result
    for pbone in target.pose.bones:
        pbone.rotation_mode = "QUATERNION"
    keep_frame = scene.frame_current

    try:
        for frame in range(first, last + 1, step):
            scene.frame_set(frame)
            arm_rotation = {}
            for s_name, t_name in mapped:
                s_pose, s_bone, t_bone = source.pose.bones[s_name], s_bones[s_name], t_bones[t_name]
                delta = (sw @ s_pose.matrix.to_quaternion()) @ (sw @ s_bone.matrix_local.to_quaternion()).inverted()
                desired = tw_inverse @ (delta @ (tw @ t_bone.matrix_local.to_quaternion()))
                parent = rotation_of(t_bone.parent, arm_rotation) if t_bone.parent else Quaternion()
                frame_of_bone = parent @ rest_offset(t_bone)
                basis = frame_of_bone.inverted() @ desired
                arm_rotation[t_name] = desired
                pbone = target.pose.bones[t_name]
                pbone.rotation_quaternion = basis
                pbone.keyframe_insert("rotation_quaternion", frame=frame)
                if t_name == HIPS:
                    moved = source.matrix_world @ s_pose.head - source.matrix_world @ s_bone.head_local
                    ratio = abs((target.matrix_world @ t_bone.head_local).z) / max(height[s_name], 1e-6)
                    pbone.location = frame_of_bone.inverted() @ (tw_inverse @ (moved * ratio))
                    pbone.keyframe_insert("location", frame=frame)
    finally:
        scene.frame_set(keep_frame)
    return result, len(mapped)
