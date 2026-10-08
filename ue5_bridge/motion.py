"""Root motion: move the horizontal motion of the hips onto the root bone, keeping the pose of every other bone.

Unreal (Motion Matching, root motion) drives the character with the root bone, so the walk must travel on it.
The hips keep only the motion that is left over (bobbing, sway), and the final pose of every frame stays exactly
what the animator made.
"""

import re

from mathutils import Matrix, Vector

HIPS_WORDS = ("hips", "pelvis", "hip")


def find_hips(armature, preferred=""):
    """The pose bone whose horizontal motion becomes root motion: the named one, else the first hips-like bone."""
    bones = armature.pose.bones
    if preferred:
        return bones.get(preferred)
    plain = {b: re.sub(r"[^a-z]", "", b.name.lower()) for b in bones}
    for word in HIPS_WORDS:
        for bone, key in sorted(plain.items(), key=lambda kv: len(kv[1])):
            if key == word or key.endswith(word):
                return bone
    return None


def keyframe_pose(bone, frame):
    bone.keyframe_insert("location", frame=frame)
    mode = "rotation_quaternion" if bone.rotation_mode == "QUATERNION" else "rotation_euler"
    bone.keyframe_insert(mode, frame=frame)
    bone.keyframe_insert("scale", frame=frame)


def extract_root_motion(context, armature, action, root_name, hips_name, start, end):
    """Rewrite `action` (assigned to `armature`) so the root bone carries the hips' horizontal motion.

    The hips must be a direct child of the root bone. Returns the horizontal distance the root travels in meters.
    """
    scene = context.scene
    pose = armature.pose
    root, hips = pose.bones[root_name], pose.bones[hips_name]
    if hips.parent != root:
        raise ValueError(f"'{hips_name}' must be a direct child of '{root_name}'")
    armature.animation_data_create()
    armature.animation_data.action = action
    previous_frame = scene.frame_current
    frames = list(range(int(start), int(end) + 1))
    sampled = {}
    for frame in frames:  # first read the whole animation, then rewrite it
        scene.frame_set(frame)
        context.view_layer.update()
        sampled[frame] = hips.matrix.copy()
    root_rest = root.bone.matrix_local.copy()
    hips_in_root_rest = root_rest.inverted() @ hips.bone.matrix_local
    for frame in frames:
        matrix = sampled[frame]
        target = Matrix.Translation(Vector((matrix.translation.x, matrix.translation.y, 0.0)))
        root.matrix_basis = root_rest.inverted() @ target
        hips.matrix_basis = hips_in_root_rest.inverted() @ target.inverted() @ matrix
        keyframe_pose(root, frame)
        keyframe_pose(hips, frame)
    scene.frame_set(previous_frame)
    first, last = sampled[frames[0]].translation, sampled[frames[-1]].translation
    return Vector((last.x - first.x, last.y - first.y, 0.0)).length
