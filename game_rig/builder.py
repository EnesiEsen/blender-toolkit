"""Landmark markers and the armature that is built from them."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

from . import layout, ue_bones

PREFIX = "GR_"
COLLECTION = "GR Markers"


def marker_names():
    names = []
    for name in ue_bones.LANDMARKS:
        names += [PREFIX + name] if name in ue_bones.CENTER else [f"{PREFIX}{name}_L"]
    return names


def world_bounds(objects):
    low, high = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for ob in objects:
        for corner in ob.bound_box:
            point = ob.matrix_world @ Vector(corner)
            low = Vector(map(min, low, point))
            high = Vector(map(max, high, point))
    return low, high


def create_markers(context, objects):
    """Empties at standard human proportions around the given meshes. Existing markers are moved."""
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        raise ValueError(rpt_("Select the character mesh first."))
    low, high = world_bounds(meshes)
    height = high.z - low.z
    center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION)
        context.scene.collection.children.link(collection)
    for name, (fx, fy, fz) in ue_bones.LANDMARKS.items():
        label = PREFIX + name if name in ue_bones.CENTER else f"{PREFIX}{name}_L"
        marker = bpy.data.objects.get(label)
        if marker is None:
            marker = bpy.data.objects.new(label, None)
            collection.objects.link(marker)
        marker.empty_display_type, marker.empty_display_size = "SPHERE", height * 0.015
        marker.show_in_front = True
        marker.location = center + Vector((fx * height, fy * height, fz * height))
    return height


def read_markers():
    """{landmark: world point} for both sides, the right side mirrored from the left across the pelvis."""
    points = {}
    for name in ue_bones.LANDMARKS:
        label = PREFIX + name if name in ue_bones.CENTER else f"{PREFIX}{name}_L"
        marker = bpy.data.objects.get(label)
        if marker is None:
            raise ValueError(rpt_("The marker '{name}' is missing: create the markers first.").format(name=label))
        points[name if name in ue_bones.CENTER else f"{name}_L"] = marker.matrix_world.translation.copy()
    middle = points["Pelvis"].x
    for name in ue_bones.LANDMARKS:
        if name not in ue_bones.CENTER:
            left = points[f"{name}_L"]
            points[f"{name}_R"] = Vector((2 * middle - left.x, left.y, left.z))
    return points


def build_rig(context, name, points, ik=True, fingers=True):
    """The mannequin skeleton as an armature object at the world origin."""
    spots = layout.positions(points, ik, fingers)
    tree = ue_bones.parents(ik, fingers)
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    context.scene.collection.objects.link(rig)
    for other in context.view_layer.objects:
        if other is not None:
            other.select_set(False)
    rig.select_set(True)
    context.view_layer.objects.active = rig
    with context.temp_override(object=rig, active_object=rig):
        bpy.ops.object.mode_set(mode="EDIT")
    try:
        edit = data.edit_bones
        for bone in tree:
            head, tail = spots[bone]
            made = edit.new(bone)
            made.head, made.tail = head, tail
            made.use_deform = bone not in ue_bones.HELPERS
        size = max((tail - head).length for head, tail in spots.values())
        for bone, parent in tree.items():
            if parent is not None:
                edit[bone].parent = edit[parent]
                if (edit[bone].head - edit[parent].tail).length < 1e-4 * max(
                    size, 1e-6
                ) and bone not in ue_bones.HELPERS:
                    edit[bone].use_connect = True
    finally:
        with context.temp_override(object=rig, active_object=rig):
            bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    return rig
