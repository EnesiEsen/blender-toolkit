"""The modifiers the kit adds, and keeping them in a sensible order."""

import math

# Names tell the kit which modifiers are its own; the order is boolean, mirror, array, bevel, weighted normal.
BEVEL, NORMAL, MIRROR, ARRAY, RADIAL, CUT = (
    "HS Bevel",
    "HS Weighted Normal",
    "HS Mirror",
    "HS Array",
    "HS Radial",
    "HS Cut ",
)


def is_ours(modifier):
    return modifier.name.startswith("HS ")


def priority(modifier):
    name = modifier.name
    if name.startswith(CUT):
        return 0
    if name == MIRROR:
        return 1
    if name in (ARRAY, RADIAL):
        return 2
    return 3 if name == BEVEL else 4


def order(obj):
    """Put the kit's modifiers after the user's own, in the order boolean, mirror, array, bevel, weighted normal."""
    mine = sorted((m for m in obj.modifiers if is_ours(m)), key=priority)
    wanted = [m for m in obj.modifiers if not is_ours(m)] + mine
    for index, modifier in enumerate(wanted):
        obj.modifiers.move(list(obj.modifiers).index(modifier), index)


def ensure(obj, name, kind):
    modifier = obj.modifiers.get(name)
    if modifier is None or modifier.type != kind:
        if modifier is not None:
            obj.modifiers.remove(modifier)
        modifier = obj.modifiers.new(name, kind)
    return modifier


def smart_bevel(obj, width, segments, method, angle, harden):
    """A bevel that follows the sharp edges plus a weighted normal modifier. Returns the bevel modifier."""
    bevel = ensure(obj, BEVEL, "BEVEL")
    bevel.width, bevel.segments, bevel.limit_method = width, segments, method
    bevel.angle_limit, bevel.harden_normals = angle, harden
    bevel.use_clamp_overlap, bevel.miter_outer, bevel.profile = True, "MITER_ARC", 0.5
    normal = ensure(obj, NORMAL, "WEIGHTED_NORMAL")
    normal.mode, normal.weight, normal.keep_sharp, normal.thresh = "FACE_AREA", 50, True, 0.01
    order(obj)
    return bevel


def add_mirror(obj, axes, bisect):
    modifier = ensure(obj, MIRROR, "MIRROR")
    modifier.use_axis = axes
    modifier.use_bisect_axis = (bisect and axes[0], bisect and axes[1], bisect and axes[2])
    modifier.use_mirror_merge, modifier.use_clip = True, True
    order(obj)
    return modifier


def add_array(obj, count, offset):
    modifier = ensure(obj, ARRAY, "ARRAY")
    modifier.fit_type, modifier.count = "FIXED_COUNT", count
    modifier.use_relative_offset, modifier.use_object_offset = True, False
    modifier.relative_offset_displace = (offset, 0.0, 0.0)
    modifier.use_merge_vertices = True
    order(obj)
    return modifier


def add_radial(obj, count, axis):
    """Copies around the chosen axis of the object, driven by a child empty so they follow the object."""
    import bpy

    modifier = ensure(obj, RADIAL, "ARRAY")
    center = bpy.data.objects.get("HS Radial Center " + obj.name)
    if center is None:
        center = bpy.data.objects.new("HS Radial Center " + obj.name, None)
        center.empty_display_type = "ARROWS"
        center.empty_display_size = 0.3
        for collection in obj.users_collection or [bpy.context.scene.collection]:
            collection.objects.link(center)
        center.parent = obj
    rotation = [0.0, 0.0, 0.0]
    rotation["XYZ".index(axis)] = 2 * math.pi / count
    center.rotation_euler = rotation
    modifier.fit_type, modifier.count = "FIXED_COUNT", count
    modifier.use_relative_offset, modifier.use_constant_offset = False, False
    modifier.use_object_offset, modifier.offset_object = True, center
    modifier.use_merge_vertices = False
    order(obj)
    return modifier
