"""Find which image feeds which input of the Principled BSDF of a material."""

ROLES = {
    "base": "Base Color",
    "metal": "Metallic",
    "rough": "Roughness",
    "normal": "Normal",
    "emission": "Emission Color",
    "alpha": "Alpha",
}
CHANNELS = {"Red": "R", "Green": "G", "Blue": "B", "R": "R", "G": "G", "B": "B", "Alpha": "A"}


def principled(material):
    """The Principled BSDF that feeds the material output (or the first one in the tree)."""
    if material is None or material.node_tree is None:
        return None
    nodes = material.node_tree.nodes
    outputs = [n for n in nodes if n.type == "OUTPUT_MATERIAL"]
    for out in sorted(outputs, key=lambda n: not n.is_active_output):
        links = out.inputs["Surface"].links
        if links and links[0].from_node.type == "BSDF_PRINCIPLED":
            return links[0].from_node
    return next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)


def _value(socket):
    value = getattr(socket, "default_value", None)
    try:
        return tuple(value)
    except TypeError:
        return value


def trace(socket, channel=None, depth=0):
    """Follow an input socket upstream to an image texture node.

    Passes through Normal Map, Separate Color and Reroute nodes. Returns {"image", "channel", "value", "via"}: the image
    (or None), the channel it is read from (None = all), the socket's own value and the node types in between.
    """
    result = {"image": None, "channel": channel, "value": _value(socket), "via": []}
    if depth > 12 or not socket.is_linked:
        return result
    link = socket.links[0]
    node, out = link.from_node, link.from_socket
    if node.type == "TEX_IMAGE":
        result["image"] = node.image
        if out.name == "Alpha":
            result["channel"] = "A"
        return result
    if node.type == "NORMAL_MAP":
        inner = node.inputs["Color"]
    elif node.type in ("SEPARATE_COLOR", "SEPARATE_RGB"):
        inner, channel = node.inputs[0], CHANNELS.get(out.name, channel)
    elif node.type == "REROUTE":
        inner = node.inputs[0]
    else:
        result["via"].append(node.type)  # a node we do not look through
        return result
    nested = trace(inner, channel, depth + 1)
    nested["via"] = [node.type, *nested["via"]]
    return nested


def gather(material):
    """{role: trace result} for the inputs of the material's Principled BSDF."""
    bsdf = principled(material)
    if bsdf is None:
        return {}
    return {role: trace(bsdf.inputs[name]) for role, name in ROLES.items() if name in bsdf.inputs}
