"""Shader side: builds the node group that blends any number of PBR texture sets by mask.

Per layer, from the second one on: height-based blend (the layer wins where its mask is high or where its surface sits
above what is below it), softened by noise. Optional "Enhancer": procedural detail normal, crevice dirt and micro
displacement, which add no image textures (so no sampler budget).
"""
import bpy

ENHANCER_PANEL = "Enhancer"


def by_id(sockets, identifier):
    return next(s for s in sockets if s.identifier == identifier)


def node(tree, kind, x, y, parent=None, **props):
    n = tree.nodes.new(kind)
    n.parent = parent
    n.location = (x, y)
    for key, value in props.items():
        setattr(n, key, value)
    return n


def feed(tree, value, socket):
    if isinstance(value, bpy.types.NodeSocket):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def math(tree, op, x, y, parent, *args, clamp=False):
    n = node(tree, "ShaderNodeMath", x, y, parent, operation=op, use_clamp=clamp)
    for socket, value in zip(n.inputs, args, strict=False):  # the node has more sockets than values given
        feed(tree, value, socket)
    return n.outputs[0]


def mix(tree, data_type, fac, a, b, x, y, parent):
    n = node(tree, "ShaderNodeMix", x, y, parent, data_type=data_type)
    suffix = "Color" if data_type == "RGBA" else "Float"
    tree.links.new(fac, by_id(n.inputs, "Factor_Float"))
    feed(tree, a, by_id(n.inputs, "A_" + suffix))
    feed(tree, b, by_id(n.inputs, "B_" + suffix))
    return by_id(n.outputs, "Result_" + suffix)


def map_range(tree, value, lo, hi, out_lo, out_hi, x, y, parent):
    n = node(tree, "ShaderNodeMapRange", x, y, parent, clamp=True)
    feed(tree, value, by_id(n.inputs, "Value"))
    for ident, v in (("From Min", lo), ("From Max", hi), ("To Min", out_lo), ("To Max", out_hi)):
        feed(tree, v, by_id(n.inputs, ident))
    return by_id(n.outputs, "Result")


def layer_textures(tree, maps, vector, x, y, frame, lite):
    """Image nodes for one texture set; missing maps (and, in lite mode, normal and roughness) become flat values."""
    out, images = {}, 0
    for row, kind in enumerate(("color", "normal", "rough", "height")):
        ny = y - row * 300
        path = maps.get(kind)
        if path and (not lite or kind in ("color", "height")):
            image = bpy.data.images.load(path, check_existing=True)
            if kind != "color":
                image.colorspace_settings.name = "Non-Color"
            tex = node(tree, "ShaderNodeTexImage", x, ny, frame, image=image)
            tree.links.new(vector, tex.inputs["Vector"])
            out[kind] = tex.outputs["Color"]
            images += 1
        elif kind == "normal":
            rgb = node(tree, "ShaderNodeRGB", x, ny, frame)
            rgb.outputs[0].default_value = (0.5, 0.5, 1.0, 1.0)
            out[kind] = rgb.outputs[0]
        else:
            value = node(tree, "ShaderNodeValue", x, ny, frame)
            value.outputs[0].default_value = 0.8 if kind == "rough" else 0.5
            out[kind] = value.outputs[0]
    return out, images


def group_node_of(mat, tree):
    if mat and mat.node_tree:
        return next((n for n in mat.node_tree.nodes if n.type == "GROUP" and n.node_tree == tree), None)
    return None


def slider_key(item):
    """Stable identity of a group input: ("G", name) general, ("E", name) enhancer, ("L", layer index, name)."""
    parent = item.parent
    if parent is None or not parent.name:  # root-level items report an unnamed root panel as their parent
        return ("G", item.name)
    if parent.name == ENHANCER_PANEL:
        return ("E", item.name)
    return ("L", int(parent.name.split(".")[0]) - 1, item.name)


def inputs_of(tree):
    return [i for i in tree.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT"]


def slider_values(tree, group_node):
    """Current slider values of the material's group node, so a rebuild keeps the user's settings."""
    if not group_node:
        return {}
    return {slider_key(i): by_id(group_node.inputs, i.identifier).default_value for i in inputs_of(tree)}


def restore_values(tree, group_node, values):
    for item in inputs_of(tree):
        key = slider_key(item)
        if key in values:
            by_id(group_node.inputs, item.identifier).default_value = values[key]


def apply_enhancer(tree, gin, enh, coord, color, rough, normal, relief_value, x):
    """Add detail normal, crevice dirt and micro displacement. Returns (color, rough, normal, relief_value)."""
    frame = node(tree, "NodeFrame", 0, 0, label="Enhancer")

    def ginput(key):
        return by_id(gin.outputs, enh[key].identifier)

    def noise(scale_key, detail, roughness, y):
        vec = node(tree, "ShaderNodeVectorMath", x, y, frame, operation="SCALE")
        tree.links.new(coord, vec.inputs["Vector"])
        tree.links.new(ginput(scale_key), vec.inputs["Scale"])
        n = node(tree, "ShaderNodeTexNoise", x + 200, y, frame)
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = roughness
        tree.links.new(vec.outputs[0], n.inputs["Vector"])
        return n.outputs["Fac"]

    # Detail normal: fine procedural bump on top of the blended normal map.
    bump = node(tree, "ShaderNodeBump", x + 500, 0, frame)
    bump.inputs["Distance"].default_value = 0.02
    tree.links.new(noise("detail_scale", 6.0, 0.6, 0), bump.inputs["Height"])
    tree.links.new(ginput("detail"), bump.inputs["Strength"])
    tree.links.new(normal, bump.inputs["Normal"])

    # Dirt: ambient occlusion marks crevices, low-frequency noise breaks the pattern up.
    ao = node(tree, "ShaderNodeAmbientOcclusion", x + 500, -300, frame)
    ao.inputs["Distance"].default_value = 0.5
    crevice = math(tree, "SUBTRACT", x + 700, -300, frame, 1.0, ao.outputs["AO"])
    variation = map_range(tree, noise("dirt_scale", 4.0, 0.5, -500), 0.3, 0.7, 0.2, 1.0, x + 700, -500, frame)
    dirt = math(tree, "MULTIPLY", x + 900, -300, frame, crevice, variation)
    dirt = math(tree, "MULTIPLY", x + 1100, -300, frame, dirt, ginput("dirt"), clamp=True)
    color = mix(tree, "RGBA", dirt, color, ginput("dirt_color"), x + 1300, -300, frame)
    dirty_rough = node(tree, "ShaderNodeValue", x + 1100, -500, frame)
    dirty_rough.outputs[0].default_value = 0.95
    rough = mix(tree, "FLOAT", dirt, rough, dirty_rough.outputs[0], x + 1300, -500, frame)

    # Micro displacement: centered high-frequency noise added to the relief.
    micro = math(tree, "SUBTRACT", x + 700, -800, frame, noise("micro_scale", 10.0, 0.7, -800), 0.5)
    micro = math(tree, "MULTIPLY", x + 900, -800, frame, micro, ginput("micro"))
    relief_value = math(tree, "ADD", x + 1100, -800, frame, relief_value, micro)
    return color, rough, bump.outputs["Normal"], relief_value


def build_group(ob, layers, maps, lite=False, enhancer=False):
    """(Re)build the node group "TB <object>". Returns it; tree["tb_textures"] holds the image texture count."""
    name = f"TB {ob.name}"
    tree = bpy.data.node_groups.get(name) or bpy.data.node_groups.new(name, "ShaderNodeTree")
    tree.nodes.clear()
    tree.interface.clear()
    face = tree.interface
    outputs = {n: face.new_socket(n, in_out="OUTPUT", socket_type=t) for n, t in (
        ("Base Color", "NodeSocketColor"), ("Roughness", "NodeSocketFloat"),
        ("Normal", "NodeSocketVector"), ("Displacement", "NodeSocketFloat"))}

    def slider(label, default, lo, hi, panel=None):
        s = face.new_socket(label, in_out="INPUT", socket_type="NodeSocketFloat", parent=panel)
        s.default_value, s.min_value, s.max_value = default, lo, hi
        return s

    noise_scale = slider("Blend Noise Scale", 8.0, 0.0, 1000.0)
    normal_strength = slider("Normal Strength", 1.0, 0.0, 10.0)
    relief = slider("Relief (m)", 0.05, 0.0, 10.0)
    enh = {}
    if enhancer:
        panel = face.new_panel(ENHANCER_PANEL, default_closed=True)
        enh = {
            "detail": slider("Detail Strength", 0.25, 0.0, 1.0, panel),
            "detail_scale": slider("Detail Scale", 80.0, 0.0, 2000.0, panel),
            "dirt": slider("Dirt Amount", 0.6, 0.0, 2.0, panel),
            "dirt_scale": slider("Dirt Scale", 5.0, 0.0, 200.0, panel),
            "micro": slider("Micro Displacement (m)", 0.01, 0.0, 1.0, panel),
            "micro_scale": slider("Micro Scale", 150.0, 0.0, 4000.0, panel),
        }
        enh["dirt_color"] = face.new_socket("Dirt Color", in_out="INPUT", socket_type="NodeSocketColor", parent=panel)
        enh["dirt_color"].default_value = (0.07, 0.05, 0.035, 1.0)
    panels = []
    for i, layer in enumerate(layers):
        panel = face.new_panel(f"{i + 1}. {layer.name}", default_closed=True)
        s = {"scale": slider("Scale", 20.0, 0.01, 10000.0, panel)}
        if i:
            s["soft"] = slider("Softness", 0.5, 0.01, 2.0, panel)
            s["height"] = slider("Height Influence", 0.5, 0.0, 4.0, panel)
            s["noise"] = slider("Noise", 0.3, 0.0, 2.0, panel)
        panels.append(s)

    shared = node(tree, "NodeFrame", 0, 0, label="Shared")
    gin = node(tree, "NodeGroupInput", -1800, 400, shared)
    coord = node(tree, "ShaderNodeTexCoord", -1800, 0, shared).outputs["UV" if ob.data.uv_layers else "Generated"]
    noise_vector = node(tree, "ShaderNodeVectorMath", -1550, 200, shared, operation="SCALE")
    tree.links.new(coord, noise_vector.inputs["Vector"])
    tree.links.new(by_id(gin.outputs, noise_scale.identifier), noise_vector.inputs["Scale"])
    noise = node(tree, "ShaderNodeTexNoise", -1350, 200, shared)
    noise.inputs["Detail"].default_value = 4.0
    tree.links.new(noise_vector.outputs[0], noise.inputs["Vector"])
    noise_centered = math(tree, "SUBTRACT", -1150, 200, shared, noise.outputs["Fac"], 0.5)

    mask_sockets = []
    for pack in range((len(layers) - 1 + 3) // 4):
        attribute = node(tree, "ShaderNodeAttribute", -1550, -300 - pack * 300, shared,
                         attribute_type="GEOMETRY", attribute_name=f"tb_mask{pack}")
        separate = node(tree, "ShaderNodeSeparateColor", -1350, -300 - pack * 300, shared)
        tree.links.new(attribute.outputs["Color"], separate.inputs[0])
        mask_sockets += [separate.outputs["Red"], separate.outputs["Green"], separate.outputs["Blue"],
                         attribute.outputs["Alpha"]]

    color = normal = rough = height = None
    textures = 0
    for i, (layer, layer_maps, s) in enumerate(zip(layers, maps, panels, strict=True)):
        x, y = -800 + i * 1100, 600
        frame = node(tree, "NodeFrame", 0, 0, label=f"{i + 1}. {layer.name}")
        lin = node(tree, "NodeGroupInput", x, y, frame)
        inp = {k: by_id(lin.outputs, v.identifier) for k, v in s.items()}
        vector = node(tree, "ShaderNodeVectorMath", x + 200, y, frame, operation="SCALE")
        tree.links.new(coord, vector.inputs["Vector"])
        tree.links.new(inp["scale"], vector.inputs["Scale"])
        t, count = layer_textures(tree, layer_maps, vector.outputs[0], x + 400, y, frame, lite)
        textures += count
        if i == 0:
            color, normal, rough, height = t["color"], t["normal"], t["rough"], t["height"]
        else:
            # Height blend: the layer wins where its mask is high or its surface sits above what is below it.
            mx = x + 700
            above = math(tree, "SUBTRACT", mx, y, frame, t["height"], height)
            v = math(tree, "MULTIPLY_ADD", mx, y - 200, frame, above, inp["height"], mask_sockets[i - 1])
            v = math(tree, "MULTIPLY_ADD", mx, y - 400, frame, noise_centered, inp["noise"], v)
            lo = math(tree, "MULTIPLY_ADD", mx, y - 600, frame, inp["soft"], -0.5, 0.5)
            hi = math(tree, "MULTIPLY_ADD", mx, y - 800, frame, inp["soft"], 0.5, 0.5)
            fac = map_range(tree, v, lo, hi, 0.0, 1.0, mx + 200, y - 300, frame)
            color = mix(tree, "RGBA", fac, color, t["color"], mx + 400, y, frame)
            normal = mix(tree, "RGBA", fac, normal, t["normal"], mx + 400, y - 300, frame)
            rough = mix(tree, "FLOAT", fac, rough, t["rough"], mx + 400, y - 600, frame)
            height = mix(tree, "FLOAT", fac, height, t["height"], mx + 400, y - 900, frame)
        for socket in lin.outputs:
            socket.hide = not socket.is_linked

    end = -800 + len(layers) * 1100
    normal_map = node(tree, "ShaderNodeNormalMap", end, 0)
    tree.links.new(normal, normal_map.inputs["Color"])
    tree.links.new(by_id(gin.outputs, normal_strength.identifier), normal_map.inputs["Strength"])
    final_normal = normal_map.outputs["Normal"]
    relief_value = math(tree, "MULTIPLY", end, -300, None,
                        math(tree, "SUBTRACT", end - 200, -300, None, height, 0.5),
                        by_id(gin.outputs, relief.identifier))
    if enhancer:
        color, rough, final_normal, relief_value = apply_enhancer(
            tree, gin, enh, coord, color, rough, final_normal, relief_value, end + 300)
        end += 1800
    gout = node(tree, "NodeGroupOutput", end + 300, 0)
    for key, value in (("Base Color", color), ("Roughness", rough),
                       ("Normal", final_normal), ("Displacement", relief_value)):
        tree.links.new(value, by_id(gout.inputs, outputs[key].identifier))
    tree["tb_textures"] = textures
    return tree
