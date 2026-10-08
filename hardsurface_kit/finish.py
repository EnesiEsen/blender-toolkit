"""Apply the whole modifier stack so the result is an ordinary mesh that exports cleanly."""

import bpy


def apply_stack(context, obj):
    """Bake every modifier into the mesh (custom normals included) and delete the kit's helper objects."""
    if obj.type != "MESH":
        raise ValueError(f"'{obj.name}' is not a mesh.")
    if obj.data.shape_keys is not None:
        raise ValueError(f"'{obj.name}' has shape keys: they cannot be applied with the modifiers.")
    if not obj.modifiers:
        return False
    depsgraph = context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(
        obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph
    )
    helpers = [m.object for m in obj.modifiers if m.type == "BOOLEAN" and m.name.startswith("HS Cut ") and m.object]
    helpers += [
        m.offset_object for m in obj.modifiers if m.type == "ARRAY" and m.name == "HS Radial" and m.offset_object
    ]
    old = obj.data
    obj.data = mesh
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    for helper in helpers:
        data = helper.data
        bpy.data.objects.remove(helper)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return True
