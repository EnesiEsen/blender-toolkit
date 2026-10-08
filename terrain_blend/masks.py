"""Geometry Nodes side: packs the vertex-group masks into color attributes the shader can read.

EEVEE reads at most 14 mesh attributes per material, and Blender 5.0's EEVEE cannot read vertex groups in a shader at
all. Both limits are avoided by storing four vertex groups per FLOAT_COLOR point attribute (tb_mask0 = RGBA of
masks 1-4, tb_mask1 = masks 5-8, ...). The modifier re-evaluates while weight painting, so the material follows live.
"""

import bpy

from .shader import node

MOD_NAME = "TB Masks"


def build_mask_modifier(ob, masks):
    name = f"TB Masks {ob.name}"
    tree = bpy.data.node_groups.get(name) or bpy.data.node_groups.new(name, "GeometryNodeTree")
    tree.is_modifier = True
    tree.nodes.clear()
    tree.interface.clear()
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    geometry = node(tree, "NodeGroupInput", -400, 0).outputs[0]
    for pack in range(0, len(masks), 4):
        x = (pack // 4) * 500
        combine = node(tree, "FunctionNodeCombineColor", x, -300)
        for channel, group in enumerate(masks[pack : pack + 4]):
            attribute = node(tree, "GeometryNodeInputNamedAttribute", x - 250, -200 - channel * 150, data_type="FLOAT")
            attribute.inputs["Name"].default_value = group
            tree.links.new(attribute.outputs["Attribute"], combine.inputs[channel])
        store = node(tree, "GeometryNodeStoreNamedAttribute", x + 200, 0, data_type="FLOAT_COLOR", domain="POINT")
        store.inputs["Name"].default_value = f"tb_mask{pack // 4}"
        tree.links.new(geometry, store.inputs["Geometry"])
        tree.links.new(combine.outputs["Color"], store.inputs["Value"])
        geometry = store.outputs["Geometry"]
    tree.links.new(geometry, node(tree, "NodeGroupOutput", (len(masks) // 4 + 1) * 500, 0).inputs[0])
    modifier = ob.modifiers.get(MOD_NAME) or ob.modifiers.new(MOD_NAME, "NODES")
    modifier.node_group = tree
