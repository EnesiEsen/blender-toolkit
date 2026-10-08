"""Sollumz glue. Sollumz is a moving target (the dev builds installed for Blender 5.0 and 5.2 differ), so
everything that touches it goes through this file: detection, calling operators with only the arguments they
accept, object type names.
"""

import importlib

import bpy

# Sollumz object types (sollumz_properties.SollumType values); plain strings compare equal to the enum members.
DRAWABLE = "sollumz_drawable"
MODEL = "sollumz_drawable_model"
FRAGMENT = "sollumz_fragment"
COMPOSITE = "sollumz_bound_composite"
BVH = "sollumz_bound_geometrybvh"
BOUND_BOX = "sollumz_bound_box"
SHADER_MATERIAL = "sollumz_material_shader"
COLLISION_MATERIAL = "sollumz_material_collision"
ARCHETYPE_BASE = "sollumz_archetype_base"
ARCHETYPE_MLO = "sollumz_archetype_mlo"
LOD_LEVELS = {"high": "sollumz_high", "med": "sollumz_medium", "low": "sollumz_low", "vlow": "sollumz_verylow"}


class SollumzMissing(Exception):
    """Sollumz is not installed or not enabled; the message tells the user what to do."""


def ready():
    return (
        hasattr(bpy.types.Scene, "ytyps") and hasattr(bpy.ops, "sollumz") and hasattr(bpy.ops.sollumz, "export_assets")
    )


def require():
    if not ready():
        raise SollumzMissing("Sollumz is not installed or not enabled (Preferences > Get Extensions > Sollumz).")


def kind(ob):
    """The Sollumz type of an object; plain objects (and all objects without Sollumz) are 'sollumz_none'."""
    return getattr(ob, "sollum_type", "sollumz_none")


def package():
    """Module name of the enabled Sollumz add-on (it depends on how Sollumz was installed), or None."""
    return next((n for n in bpy.context.preferences.addons.keys() if n.rsplit(".", 1)[-1].startswith("sollumz")), None)


def prepare_mesh(mesh):
    """Give a mesh the UV map and color attribute names the Sollumz shaders expect (UVMap 0, Color 1)."""
    name = package()
    if name is None:
        return
    helper = importlib.import_module(f"{name}.tools.meshhelper")
    helper.mesh_rename_uv_maps_by_order(mesh)
    helper.mesh_rename_color_attrs_by_order(mesh)
    helper.mesh_add_missing_uv_maps(mesh)
    helper.mesh_add_missing_color_attrs(mesh)


def has_ytd():
    """Texture dictionaries (YTD) are authored in Sollumz 2.8.3 and newer only."""
    return hasattr(bpy.types.Scene, "sz_txds")


def op_args(op, **wanted):
    """Keep only the arguments `op` knows about, so one call works on every Sollumz build."""
    known = {p.identifier for p in op.get_rna_type().properties}
    return {k: v for k, v in wanted.items() if k in known}


def call(op, **wanted):
    return op(**op_args(op, **wanted))


def select_only(context, *objects):
    for other in list(context.view_layer.objects):
        if other is not None:
            other.select_set(False)
    for ob in objects:
        ob.select_set(True)
    context.view_layer.objects.active = objects[0] if objects else None


def children_of(drawable, sollum_type):
    return [c for c in drawable.children_recursive if kind(c) == sollum_type]


def drawables(context, selected_only=False):
    """Drawable roots in the scene (or only the selected ones)."""
    pool = context.selected_objects if selected_only else context.scene.objects
    return [o for o in pool if kind(o) == DRAWABLE]
