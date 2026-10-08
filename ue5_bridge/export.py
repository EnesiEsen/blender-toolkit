"""FBX export for Unreal Engine 5: static meshes, skeletal meshes (modular parts share the skeleton) and animations.

Every export works on temporary copies, so nothing in your scene is moved, applied or renamed.
"""

import re
from pathlib import Path

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

from . import motion, rig


class ExportError(Exception):
    """A problem the user can act on."""


def ue_name(name, prefix, s):
    """`Crate.001` -> `SM_Crate`: ASCII letters, digits and underscores, with the UE prefix when enabled."""
    base = re.sub(r"[^A-Za-z0-9_]+", "_", re.sub(r"\.\d{3}$", "", name)).strip("_") or "asset"
    return base if (not s.prefixes or base.startswith(prefix)) else prefix + base


def target_folder(s, kind):
    if not s.output_dir:
        raise ExportError(rpt_("Choose an export folder first."))
    return Path(bpy.path.abspath(s.output_dir)) / kind


def fbx_options(s, kind):
    """Settings that follow the Unreal Engine guidance: FBX unit scale, default axes, no phantom leaf bones."""
    options = dict(
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        use_space_transform=True,
        bake_space_transform=False,
        mesh_smooth_type="FACE",
        use_tspace=s.tangents,
        use_mesh_modifiers=True,
        path_mode="AUTO",
        add_leaf_bones=s.leaf_bones,
        use_armature_deform_only=s.only_deform,
        armature_nodetype=s.armature_node,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
    )
    if kind == "STATIC":
        options.update(object_types={"MESH"}, bake_anim=False)
    elif kind == "SKELETAL":
        options.update(object_types={"ARMATURE", "MESH"}, bake_anim=False)
    else:
        options.update(
            object_types={"ARMATURE"},
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            bake_anim_force_startend_keying=True,
            bake_anim_step=s.bake_step,
            bake_anim_simplify_factor=1.0,
        )
    return options


def write_fbx(context, objects, path, s, kind):
    path.parent.mkdir(parents=True, exist_ok=True)
    for other in list(context.view_layer.objects):
        if other is not None:
            other.select_set(False)
    for ob in objects:
        ob.select_set(True)
    context.view_layer.objects.active = objects[0]
    with context.temp_override(
        selected_objects=objects, selected_editable_objects=objects, active_object=objects[0], object=objects[0]
    ):
        result = bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, **fbx_options(s, kind))
    if result != {"FINISHED"} or not path.exists():
        raise ExportError(rpt_("The FBX exporter failed for '{name}'.").format(name=path.name))
    return path


COLLISION = re.compile(r"^(UBX|USP|UCP|UCX)_(.+)_(\d+)$")  # Unreal's collision shape names: UBX_<mesh>_00


def collision_shapes(ob):
    """Collision shapes of a mesh: its children named UBX_/USP_/UCP_/UCX_ and objects named after it."""
    found = {c for c in ob.children if c.type == "MESH" and COLLISION.match(c.name)}
    for other in bpy.data.objects:
        match = COLLISION.match(other.name) if other.type == "MESH" else None
        if match and match.group(2) == ob.name:
            found.add(other)
    return sorted(found, key=lambda o: o.name)


def static_copy(context, ob, s, anchor=None, name=None):
    """A temporary mesh object with the modifiers applied and rotation and scale baked in.

    With Center at Origin the mesh sits at the origin; a collision shape (`anchor` is its mesh) keeps its place relative
    to that mesh.
    """
    mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(context.evaluated_depsgraph_get()))
    matrix = ob.matrix_world.copy()
    if s.center_origin:
        origin = anchor.matrix_world.translation if anchor is not None else matrix.translation
        matrix.translation = matrix.translation - origin
    mesh.transform(matrix)
    copy = bpy.data.objects.new(name or rig.TEMP + ob.name, mesh)
    context.scene.collection.objects.link(copy)
    return copy


def is_skinned(ob):
    return any(m.type == "ARMATURE" and m.object for m in ob.modifiers)


def export_static(context, objects, s):
    """One FBX per mesh in StaticMeshes/, with its collision shapes (UBX_, USP_, UCP_, UCX_) in the same file.

    Skinned meshes are skipped (export them as skeletal meshes) and so are the collision shapes themselves.
    """
    folder = target_folder(s, "StaticMeshes")
    paths = []
    for ob in objects:
        if ob.type != "MESH" or is_skinned(ob) or COLLISION.match(ob.name):
            continue
        copy = static_copy(context, ob, s)
        # the copy carries a temporary name; Unreal matches a shape to its mesh by name, so the shapes use the same one
        shapes = []
        for shape in collision_shapes(ob):
            kind, _, number = COLLISION.match(shape.name).groups()
            shapes.append(static_copy(context, shape, s, anchor=ob, name=f"{kind}_{copy.name}_{number}"))
        try:
            target = folder / (ue_name(ob.name, "SM_", s) + ".fbx")
            paths.append(write_fbx(context, [copy, *shapes], target, s, "STATIC"))
        finally:
            for temp in (copy, *shapes):
                mesh = temp.data
                bpy.data.objects.remove(temp)
                bpy.data.meshes.remove(mesh)
    return paths


def skinned_meshes(armature):
    return [
        o
        for o in bpy.data.objects
        if o.type == "MESH"
        and any(m.type == "ARMATURE" and m.object == armature for m in o.modifiers)
        and not o.name.startswith(rig.TEMP)
    ]


def export_skeletal(context, armatures, s):
    """FBX files in SkeletalMeshes/: one per modular part (sharing the skeleton) or one for everything."""
    folder = target_folder(s, "SkeletalMeshes")
    paths = []
    for armature in armatures:
        meshes = skinned_meshes(armature)
        if not meshes:
            raise ExportError(rpt_("No mesh is skinned to '{name}'.").format(name=armature.name))
        groups = [[m] for m in meshes] if s.skeletal_mode == "PER_MESH" else [meshes]
        for group in groups:
            label = group[0].name if s.skeletal_mode == "PER_MESH" else armature.name
            copy = rig.RigCopy(context, armature, group, s)
            try:
                paths.append(
                    write_fbx(
                        context,
                        [copy.armature, *copy.meshes],
                        folder / (ue_name(label, "SK_", s) + ".fbx"),
                        s,
                        "SKELETAL",
                    )
                )
            finally:
                copy.cleanup()
    return paths


def action_bone_names(action):
    """Names of the pose bones an action animates (works with Blender's layered actions)."""
    names = set()
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fcurve in bag.fcurves:
                    match = re.match(r'pose\.bones\["(.+?)"\]', fcurve.data_path)
                    if match:
                        names.add(match.group(1))
    return names


def animation_sources(armature, s):
    """[(name, action or None, first frame, last frame, NLA track name or None)] for the chosen source."""
    data = armature.animation_data
    found = []
    if s.anim_source == "ACTIVE":
        if data and data.action:
            found.append((data.action.name, data.action, *data.action.frame_range, None))
    elif s.anim_source == "NLA":
        for track in data.nla_tracks if data else []:
            if track.strips:
                found.append(
                    (
                        track.name,
                        None,
                        min(t.frame_start for t in track.strips),
                        max(t.frame_end for t in track.strips),
                        track.name,
                    )
                )
    else:
        bones = {b.name for b in armature.data.bones}
        for action in bpy.data.actions:
            if action_bone_names(action) & bones:
                found.append((action.name, action, *action.frame_range, None))
    return found


def export_animations(context, armatures, s):
    """One FBX per animation in Animations/, optionally with the walking motion moved to the root bone."""
    folder = target_folder(s, "Animations")
    scene = context.scene
    paths = []
    for armature in armatures:
        sources = animation_sources(armature, s)
        if not sources:
            raise ExportError(rpt_("'{name}' has no animation to export.").format(name=armature.name))
        for name, action, start, end, track in sources:
            copy = rig.RigCopy(context, armature, [], s, apply_transform=False)
            saved_range = (scene.frame_start, scene.frame_end)
            try:
                data = copy.armature.animation_data_create()
                if track is None:
                    data.action = action.copy()
                    for t in list(data.nla_tracks):
                        data.nla_tracks.remove(t)
                else:
                    data.action = None
                    for t in data.nla_tracks:
                        t.mute = t.name != track
                scene.frame_start, scene.frame_end = int(start), int(end)
                if s.root_motion:
                    if track is not None:
                        raise ExportError(rpt_("Root motion needs actions, not NLA tracks."))
                    hips = motion.find_hips(copy.armature, s.hips_bone)
                    if hips is None:
                        raise ExportError(rpt_("Could not find the hips bone: type its name in Hips Bone."))
                    root = rig.root_above(context, copy.armature, hips.name, s.root_name)
                    motion.extract_root_motion(context, copy.armature, data.action, root, hips.name, start, end)
                paths.append(
                    write_fbx(
                        context,
                        [copy.armature],
                        folder / (ue_name(f"{armature.name}_{name}", "A_", s) + ".fbx"),
                        s,
                        "ANIM",
                    )
                )
            finally:
                scene.frame_start, scene.frame_end = saved_range
                if track is None and copy.armature.animation_data and copy.armature.animation_data.action:
                    bpy.data.actions.remove(copy.armature.animation_data.action)
                copy.cleanup()
    return paths
