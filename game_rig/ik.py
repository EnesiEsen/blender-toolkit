"""IK for legs and arms: helper bones, constraints and a pole angle that leaves the rest pose untouched."""

import math

from mathutils import Vector

CHAINS = {
    "leg": {
        "end": "calf",
        "target": "ik_foot",
        "pole": "pole_knee",
        "base": "thigh",
        "tip": "foot",
        "dir": Vector((0, -1, 0)),
    },
    "arm": {
        "end": "lowerarm",
        "target": "ik_hand",
        "pole": "pole_elbow",
        "base": "upperarm",
        "tip": "hand",
        "dir": Vector((0, 1, 0)),
    },
}


def _edit(context, rig, mode):
    import bpy

    with context.temp_override(object=rig, active_object=rig):
        bpy.ops.object.mode_set(mode=mode)


def helper_bones(context, rig, kinds, sides=("l", "r")):
    """Create the ik target and pole bones that are missing. Returns the names of the new bones."""
    created = []
    _edit(context, rig, "EDIT")
    try:
        edit = rig.data.edit_bones
        root = edit.get("root")
        for kind in kinds:
            c = CHAINS[kind]
            for s in sides:
                end, base, tip = edit.get(f"{c['end']}_{s}"), edit.get(f"{c['base']}_{s}"), edit.get(f"{c['tip']}_{s}")
                if None in (end, base, tip):
                    continue
                target = f"{c['target']}_{s}"
                if target not in edit:
                    bone = edit.new(target)
                    bone.head, bone.tail, bone.roll = tip.head.copy(), tip.tail.copy(), tip.roll
                    bone.parent = (edit.get("ik_hand_gun") if kind == "arm" else edit.get("ik_foot_root")) or root
                    bone.use_deform = False
                    created.append(target)
                pole = f"{c['pole']}_{s}"
                if pole not in edit:
                    knee = end.head.copy()
                    reach = (base.tail - base.head).length
                    bone = edit.new(pole)
                    bone.head = knee + c["dir"] * 0.35 * reach
                    bone.tail = bone.head + Vector((0, 0, 0.05 * reach))
                    bone.parent = root
                    bone.use_deform = False
                    created.append(pole)
    finally:
        _edit(context, rig, "OBJECT")
    return created


def rest_error(context, rig, bone_names):
    """How far the evaluated pose moves the given bones from their rest position (sum of distances)."""
    context.view_layer.update()
    evaluated = rig.evaluated_get(context.evaluated_depsgraph_get())
    return sum((evaluated.pose.bones[n].head - rig.data.bones[n].head_local).length for n in bone_names)


def add_constraints(context, rig, kind, side):
    c = CHAINS[kind]
    end_name, target, pole = f"{c['end']}_{side}", f"{c['target']}_{side}", f"{c['pole']}_{side}"
    tip_name = f"{c['tip']}_{side}"
    pose = rig.pose.bones
    for old in [k for k in pose[end_name].constraints if k.name.startswith("GR ")]:
        pose[end_name].constraints.remove(old)
    ik = pose[end_name].constraints.new("IK")
    ik.name = "GR IK"
    ik.target, ik.subtarget = rig, target
    ik.pole_target, ik.pole_subtarget = rig, pole
    ik.chain_count = 2
    watched = [end_name, tip_name]
    best = None
    for angle in (0.0, math.pi / 2, math.pi, -math.pi / 2):
        ik.pole_angle = angle
        error = rest_error(context, rig, watched)
        if best is None or error < best[0] - 1e-9:
            best = (error, angle)
    ik.pole_angle = best[1]
    for old in [k for k in pose[tip_name].constraints if k.name.startswith("GR ")]:
        pose[tip_name].constraints.remove(old)
    follow = pose[tip_name].constraints.new("COPY_ROTATION")
    follow.name = "GR Foot Rotation" if kind == "leg" else "GR Hand Rotation"
    follow.target, follow.subtarget = rig, target
    return best[0]


def setup(context, rig, legs=True, arms=True):
    """Add IK to the legs and arms of a UE5 rig. Returns the rest pose error (should be ~0) per chain."""
    kinds = [k for k, wanted in (("leg", legs), ("arm", arms)) if wanted]
    helper_bones(context, rig, kinds)
    errors = {}
    for kind in kinds:
        for side in ("l", "r"):
            if (
                f"{CHAINS[kind]['end']}_{side}" in rig.pose.bones
                and f"{CHAINS[kind]['target']}_{side}" in rig.pose.bones
            ):
                errors[f"{kind}_{side}"] = add_constraints(context, rig, kind, side)
    return errors


def remove(context, rig):
    """Remove the constraints and the pole bones the kit added (the ik targets of the mannequin stay)."""
    removed = 0
    for pbone in rig.pose.bones:
        for constraint in [k for k in pbone.constraints if k.name.startswith("GR ")]:
            pbone.constraints.remove(constraint)
            removed += 1
    _edit(context, rig, "EDIT")
    try:
        for bone in [b for b in rig.data.edit_bones if b.name.startswith("pole_")]:
            rig.data.edit_bones.remove(bone)
    finally:
        _edit(context, rig, "OBJECT")
    return removed
