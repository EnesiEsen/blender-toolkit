"""Orchestration: validate the layers, then build the mask modifier, the node group and the material."""
import os

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

from . import maps as maps_mod
from .masks import build_mask_modifier
from .shader import build_group, group_node_of, restore_values, slider_values

MAT_SUFFIX = " Terrain"
# Measured: OpenGL EEVEE allows 32 samplers per material and reserves 2; Vulkan (Blender 5.2) handled 256 textures.
OPENGL_TEXTURE_LIMIT = 30
# EEVEE allows 14 mesh attributes per material; UV and the normal-map tangent take 2, leaving 12 x 4 packed masks.
EEVEE_LAYER_LIMIT = 1 + 12 * 4


def material_name(ob):
    return ob.name + MAT_SUFFIX


def group_tree(ob):
    return bpy.data.node_groups.get(f"TB {ob.name}")


def is_built(ob):
    return group_tree(ob) is not None and bpy.data.materials.get(material_name(ob)) is not None


def gpu_backend():
    try:
        import gpu
        return gpu.platform.backend_type_get()
    except (SystemError, ImportError):  # no GPU context (background mode without one)
        return "UNKNOWN"


def check_layers(ob):
    """Validate the layer list and return the texture maps of every layer. Raises ValueError with a user message."""
    layers = list(ob.tb_layers)
    if not layers:
        raise ValueError(rpt_("Add at least one layer first."))
    found_maps = []
    for i, layer in enumerate(layers):
        folder = bpy.path.abspath(layer.folder)
        if not os.path.isdir(folder):
            raise ValueError(rpt_("'{name}': texture folder not found.").format(name=layer.name))
        found = maps_mod.find_maps(folder)
        if "color" not in found:
            raise ValueError(rpt_("'{name}': no color texture in the folder (Color/Albedo/Diffuse).").format(
                name=layer.name))
        if i and layer.mask not in ob.vertex_groups:
            raise ValueError(rpt_("'{name}': mask vertex group is not set or missing.").format(name=layer.name))
        found_maps.append(found)
    return found_maps


def build(ob):
    """(Re)build mask modifier, node group and material of an object. Returns a one-line summary."""
    found_maps = check_layers(ob)
    layers = list(ob.tb_layers)
    settings = ob.tb_settings

    mat = bpy.data.materials.get(material_name(ob))
    tree = group_tree(ob)
    old_values = slider_values(tree, group_node_of(mat, tree)) if tree else {}

    build_mask_modifier(ob, [layer.mask for layer in layers[1:]])
    tree = build_group(ob, layers, found_maps, lite=settings.lite, enhancer=settings.enhancer)

    mat = mat or bpy.data.materials.new(material_name(ob))
    if not mat.use_nodes:
        mat.use_nodes = True
    mat.displacement_method = "BOTH" if settings.enhancer else "BUMP"
    nt = mat.node_tree
    nt.nodes.clear()
    group = nt.nodes.new("ShaderNodeGroup")
    group.node_tree = tree
    group.label = "Terrain Blend"
    group.location = (-400, 0)
    group.width = 240
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    displacement = nt.nodes.new("ShaderNodeDisplacement")
    displacement.location = (0, -700)
    displacement.inputs["Midlevel"].default_value = 0.0
    displacement.inputs["Scale"].default_value = 1.0
    output = nt.nodes.new("ShaderNodeOutputMaterial")
    output.location = (350, 0)
    for out_name, target in (("Base Color", bsdf.inputs["Base Color"]), ("Roughness", bsdf.inputs["Roughness"]),
                             ("Normal", bsdf.inputs["Normal"]), ("Displacement", displacement.inputs["Height"])):
        nt.links.new(group.outputs[out_name], target)
    nt.links.new(bsdf.outputs[0], output.inputs["Surface"])
    nt.links.new(displacement.outputs[0], output.inputs["Displacement"])
    restore_values(tree, group, old_values)

    message = rpt_("{layers} layers, {textures} textures: '{material}'").format(
        layers=len(layers), textures=tree["tb_textures"], material=mat.name)
    if not ob.material_slots:
        ob.data.materials.append(mat)
    elif ob.active_material != mat:
        old = ob.active_material
        if old:
            old.use_fake_user = True  # keep the replaced material from being purged on save
            message += rpt_(" (kept the old '{material}')").format(material=old.name)
        ob.active_material = mat
    return message


def rebuild_if_built(ob):
    """Used by option toggles: rebuild only when the object already has a terrain material and valid layers."""
    if ob is not None and is_built(ob):
        try:
            build(ob)
        except ValueError:
            pass  # the user fixes the layers and presses Build; a toggle must not raise inside an RNA update
