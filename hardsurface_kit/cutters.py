"""Boolean cutters: objects that stay editable until you apply them."""

import bmesh
import bpy

from . import stack


def cuts_of(target):
    return [m for m in target.modifiers if m.type == "BOOLEAN" and m.name.startswith(stack.CUT)]


def is_cutter(obj):
    return bool(obj.get("hs_target"))


def add_cutter(target, cutter, operation, solver):
    """Cut `cutter` into `target` with a boolean modifier; the cutter is shown as wire and follows the target."""
    if cutter is target or cutter.type != "MESH" or target.type != "MESH":
        raise ValueError(f"'{cutter.name}' cannot cut '{target.name}'.")
    modifier = target.modifiers.get(stack.CUT + cutter.name)
    if modifier is None:
        modifier = target.modifiers.new(stack.CUT + cutter.name, "BOOLEAN")
    modifier.object, modifier.operation, modifier.solver = cutter, operation, solver
    cutter.display_type, cutter.hide_render = "WIRE", True
    cutter["hs_target"] = target.name
    cutter.parent = target
    cutter.matrix_parent_inverse = target.matrix_world.inverted()
    stack.order(target)
    return modifier


def new_cutter(context, kind, size, location):
    """A box or cylinder cutter of the given size at a location (world space)."""
    bm = bmesh.new()
    if kind == "CYLINDER":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.5, radius2=0.5, depth=1.0)
    else:
        bmesh.ops.create_cube(bm, size=1.0)
    mesh = bpy.data.meshes.new("HS Cutter")
    bm.to_mesh(mesh)
    bm.free()
    cutter = bpy.data.objects.new("HS Cutter", mesh)
    cutter.scale = size
    cutter.location = location
    context.collection.objects.link(cutter)
    cutter.display_type = "WIRE"
    return cutter


def delete_cutter(cutter):
    mesh = cutter.data
    bpy.data.objects.remove(cutter)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def remove_cutters(target, delete=True):
    """Remove the cut modifiers of a target (and the cutter objects). Returns how many."""
    count = 0
    for modifier in cuts_of(target):
        cutter = modifier.object
        target.modifiers.remove(modifier)
        if cutter is not None and delete:
            delete_cutter(cutter)
        elif cutter is not None:
            cutter.display_type = "TEXTURED"
            cutter.hide_render = False
        count += 1
    return count


def apply_cutters(context, target):
    """Apply the cut modifiers in order and delete the cutter objects. Returns how many were applied."""
    count = 0
    for modifier in cuts_of(target):
        cutter = modifier.object
        with context.temp_override(object=target, active_object=target, selected_objects=[target]):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        if cutter is not None:
            delete_cutter(cutter)
        count += 1
    return count
