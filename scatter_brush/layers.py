"""Surface scatter: a Geometry Nodes modifier that spreads a category's models over a weight-painted area.

The vertex group is the density map: weight 1 gets the full density, weak weights thin out smoothly, painted-out areas
get nothing. Everything stays live (paint, see) until you bake the result into real objects.
"""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Matrix

TREE_VERSION = 2
TREE_NAMES = {False: "SB Scatter", True: "SB Scatter (Even)"}
MOD_PREFIX = "Scatter "

# name, socket type, default, min, max
INPUTS = (
    ("Geometry", "NodeSocketGeometry", None, None, None),
    ("Assets", "NodeSocketCollection", None, None, None),
    ("Weights", "NodeSocketString", "", None, None),
    ("Density", "NodeSocketFloat", 10.0, 0.0, 100000.0),
    ("Min Distance", "NodeSocketFloat", 0.0, 0.0, 1000.0),
    ("Cutoff", "NodeSocketFloat", 0.02, 0.0, 1.0),
    ("Falloff", "NodeSocketFloat", 1.0, 0.1, 8.0),
    ("Seed", "NodeSocketInt", 1, 0, 100000),
    ("Scale Min", "NodeSocketFloat", 0.8, 0.01, 100.0),
    ("Scale Max", "NodeSocketFloat", 1.2, 0.01, 100.0),
    ("Edge Scale", "NodeSocketFloat", 0.5, 0.0, 1.0),
    ("Height Variation", "NodeSocketFloat", 0.1, 0.0, 1.0),
    ("Turn", "NodeSocketFloat", 6.2832, 0.0, 6.2832),
    ("Tilt", "NodeSocketFloat", 0.1, 0.0, 1.5708),
    ("Align", "NodeSocketFloat", 1.0, 0.0, 1.0),
    ("Sink", "NodeSocketFloat", 0.0, -1000.0, 1000.0),
)


def _socket(sockets, name):
    """First usable socket called `name` (nodes such as Random Value keep one socket per data type)."""
    for s in sockets:
        if s.name == name and s.enabled:
            return s
    raise KeyError(name)


def _in(node, name):
    return _socket(node.inputs, name)


def _out(node, name):
    return _socket(node.outputs, name)


class _Graph:
    """Small helper that keeps the node building code short."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links

    def node(self, bl_idname, **props):
        n = self.nodes.new(bl_idname)
        for key, value in props.items():
            setattr(n, key, value)
        return n

    def link(self, out_socket, in_socket):
        self.links.new(out_socket, in_socket)

    def feed(self, node, name, value):
        """Set an input to a constant, or link it when `value` is a socket."""
        socket = _in(node, name)
        if isinstance(value, bpy.types.NodeSocket):
            self.link(value, socket)
        else:
            socket.default_value = value

    def math(self, op, a, b=None, c=None):
        n = self.node("ShaderNodeMath", operation=op)
        for index, value in enumerate((a, b, c)):
            if value is None:
                continue
            if isinstance(value, bpy.types.NodeSocket):
                self.link(value, n.inputs[index])
            else:
                n.inputs[index].default_value = value
        return n.outputs[0]

    def random(self, kind, low, high, seed):
        n = self.node("FunctionNodeRandomValue", data_type=kind)
        self.feed(n, "Min", low)
        self.feed(n, "Max", high)
        self.feed(n, "Seed", seed)
        return _out(n, "Value")


def build_tree(tree, even):
    """Fill an empty node group. `even` swaps random distribution for Poisson disk (a node property, so two trees)."""
    tree.nodes.clear()
    tree.interface.clear()
    for name, kind, default, low, high in INPUTS:
        item = tree.interface.new_socket(name, in_out="INPUT", socket_type=kind)
        if default is not None:
            item.default_value = default
        if low is not None:
            item.min_value, item.max_value = low, high
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    g = _Graph(tree)
    gi = g.node("NodeGroupInput")
    go = g.node("NodeGroupOutput")
    gin = gi.outputs

    # Weight per point: the vertex group, or 1 when the name is empty / not found.
    attr = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT")
    g.link(gin["Weights"], _in(attr, "Name"))
    missing = g.math("SUBTRACT", 1.0, _out(attr, "Exists"))
    weight = g.math("MAXIMUM", _out(attr, "Attribute"), missing)

    # Only the mesh is a ground: instances of earlier layers must not receive points (nodes reach into instances).
    ground = g.node("GeometryNodeSeparateComponents")
    g.link(gin["Geometry"], ground.inputs[0])
    store = g.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
    g.link(_out(ground, "Mesh"), _in(store, "Geometry"))
    _in(store, "Name").default_value = "sb_w"
    g.link(weight, _in(store, "Value"))

    # Faces that touch any weight (the average of non-negative corners is > 0 exactly then).
    face_w = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT")
    _in(face_w, "Name").default_value = "sb_w"
    touched = g.node("FunctionNodeCompare", data_type="FLOAT", operation="GREATER_THAN")
    g.link(_out(face_w, "Attribute"), _in(touched, "A"))
    _in(touched, "B").default_value = 1e-5

    dist = g.node("GeometryNodeDistributePointsOnFaces", distribute_method="POISSON" if even else "RANDOM")
    g.link(_out(store, "Geometry"), _in(dist, "Mesh"))
    g.link(_out(touched, "Result"), _in(dist, "Selection"))
    if even:
        g.link(gin["Min Distance"], _in(dist, "Distance Min"))
        g.link(gin["Density"], _in(dist, "Density Max"))
    else:
        g.link(gin["Density"], _in(dist, "Density"))
    g.link(gin["Seed"], _in(dist, "Seed"))
    points = _out(dist, "Points")

    # Per point acceptance: weak weights thin out instead of cutting off in face-sized steps.
    pw = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT")
    _in(pw, "Name").default_value = "sb_w"
    w_pt = _out(pw, "Attribute")
    chance = g.math("POWER", w_pt, gin["Falloff"])
    roll = g.random("FLOAT", 0.0, 1.0, g.math("ADD", gin["Seed"], 11))
    lose = g.node("FunctionNodeCompare", data_type="FLOAT", operation="GREATER_THAN")
    g.link(roll, _in(lose, "A"))
    g.link(chance, _in(lose, "B"))
    weak = g.node("FunctionNodeCompare", data_type="FLOAT", operation="LESS_EQUAL")
    g.link(w_pt, _in(weak, "A"))
    g.link(gin["Cutoff"], _in(weak, "B"))
    reject = g.node("FunctionNodeBooleanMath", operation="OR")
    g.link(_out(lose, "Result"), reject.inputs[0])
    g.link(_out(weak, "Result"), reject.inputs[1])
    keep = g.node("GeometryNodeDeleteGeometry", domain="POINT")
    g.link(points, _in(keep, "Geometry"))
    g.link(reject.outputs[0], _in(keep, "Selection"))

    # Which model: a random child of the category collection.
    info = g.node("GeometryNodeCollectionInfo")
    g.link(gin["Assets"], _in(info, "Collection"))
    _in(info, "Separate Children").default_value = True
    _in(info, "Reset Children").default_value = True
    size = g.node("GeometryNodeAttributeDomainSize", component="INSTANCES")
    g.link(_out(info, "Instances"), _in(size, "Geometry"))
    last = g.math("MAXIMUM", g.math("SUBTRACT", _out(size, "Instance Count"), 1), 0)
    pick = g.random("INT", 0, last, g.math("ADD", gin["Seed"], 23))

    # Scale: random size, smaller where the weight is weak, optional extra height stretch.
    base = g.random("FLOAT", gin["Scale Min"], gin["Scale Max"], g.math("ADD", gin["Seed"], 31))
    shrink = g.math("MULTIPLY", g.math("SUBTRACT", 1.0, w_pt), gin["Edge Scale"])
    size_f = g.math("MULTIPLY", base, g.math("SUBTRACT", 1.0, shrink))
    hv = g.random(
        "FLOAT",
        g.math("MULTIPLY", gin["Height Variation"], -1.0),
        gin["Height Variation"],
        g.math("ADD", gin["Seed"], 37),
    )
    tall = g.math("MULTIPLY", size_f, g.math("ADD", 1.0, hv))
    scale = g.node("ShaderNodeCombineXYZ")
    g.link(size_f, scale.inputs["X"])
    g.link(size_f, scale.inputs["Y"])
    g.link(tall, scale.inputs["Z"])

    # Rotation: lean toward the surface normal, then random turn and tilt in that frame.
    lean = g.node("ShaderNodeMix", data_type="VECTOR")
    g.link(gin["Align"], _in(lean, "Factor"))
    _in(lean, "A").default_value = (0.0, 0.0, 1.0)
    g.link(_out(dist, "Normal"), _in(lean, "B"))
    align = g.node("FunctionNodeAlignEulerToVector", axis="Z")
    g.link(_out(lean, "Result"), _in(align, "Vector"))
    tilt_n = g.math("MULTIPLY", gin["Tilt"], -1.0)
    spin = g.node("ShaderNodeCombineXYZ")
    g.link(g.random("FLOAT", tilt_n, gin["Tilt"], g.math("ADD", gin["Seed"], 41)), spin.inputs["X"])
    g.link(g.random("FLOAT", tilt_n, gin["Tilt"], g.math("ADD", gin["Seed"], 43)), spin.inputs["Y"])
    g.link(g.random("FLOAT", 0.0, gin["Turn"], g.math("ADD", gin["Seed"], 47)), spin.inputs["Z"])
    turned = g.node("FunctionNodeRotateEuler", rotation_type="EULER", space="LOCAL")
    g.link(_out(align, "Rotation"), _in(turned, "Rotation"))
    g.link(spin.outputs["Vector"], _in(turned, "Rotate By"))

    inst = g.node("GeometryNodeInstanceOnPoints")
    g.link(_out(keep, "Geometry"), _in(inst, "Points"))
    g.link(_out(info, "Instances"), _in(inst, "Instance"))
    _in(inst, "Pick Instance").default_value = True
    g.link(pick, _in(inst, "Instance Index"))
    g.link(_out(turned, "Rotation"), _in(inst, "Rotation"))
    g.link(scale.outputs["Vector"], _in(inst, "Scale"))

    drop = g.node("ShaderNodeCombineXYZ")
    g.link(g.math("MULTIPLY", gin["Sink"], -1.0), drop.inputs["Z"])
    moved = g.node("GeometryNodeTranslateInstances")
    g.link(_out(inst, "Instances"), _in(moved, "Instances"))
    g.link(drop.outputs["Vector"], _in(moved, "Translation"))
    _in(moved, "Local Space").default_value = False

    join = g.node("GeometryNodeJoinGeometry")
    g.link(gin["Geometry"], join.inputs[0])
    g.link(_out(moved, "Instances"), join.inputs[0])
    g.link(_out(join, "Geometry"), go.inputs[0])

    tree["sb_version"] = TREE_VERSION
    tree.is_modifier = True


def get_tree(even=False):
    name = TREE_NAMES[bool(even)]
    tree = bpy.data.node_groups.get(name)
    if tree is None:
        tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    if tree.get("sb_version") != TREE_VERSION:
        build_tree(tree, bool(even))
    return tree


def socket_ids(tree):
    """{input name: identifier}; identifiers belong to this tree build, so look them up fresh."""
    return {
        item.name: item.identifier
        for item in tree.interface.items_tree
        if item.item_type == "SOCKET" and item.in_out == "INPUT"
    }


def set_input(mod, identifier, value):
    """Set a Geometry Nodes modifier input: 5.2 keeps them in `mod.properties.inputs`, 5.0 in `mod[identifier]`."""
    properties = getattr(mod, "properties", None)
    if properties is not None:
        getattr(properties.inputs, identifier).value = value
    else:
        mod[identifier] = value


def get_input(mod, identifier):
    properties = getattr(mod, "properties", None)
    if properties is not None:
        return getattr(properties.inputs, identifier).value
    return mod[identifier]


def find_category(scene, uid):
    for cat in scene.sb_categories:
        if cat.uid == uid:
            return cat
    return None


def push(ob, mod, cat, layer):
    """Write the category settings (and the layer's weights / density factor) into one modifier."""
    mod.node_group = get_tree(cat.even)
    ids = socket_ids(mod.node_group)
    low, high = sorted((cat.scale_min, cat.scale_max))
    values = {
        "Assets": cat.collection,
        "Weights": layer.group,
        "Density": cat.density * layer.density,
        "Min Distance": cat.min_distance,
        "Cutoff": cat.threshold,
        "Falloff": cat.falloff,
        "Seed": cat.seed,
        "Scale Min": low,
        "Scale Max": high,
        "Edge Scale": cat.edge_scale,
        "Height Variation": cat.height_var,
        "Turn": cat.yaw,
        "Tilt": cat.tilt,
        "Align": cat.align,
        "Sink": cat.sink,
    }
    for name, value in values.items():
        set_input(mod, ids[name], value)
    ob.update_tag()


def push_layer(ob, layer, scene):
    mod = ob.modifiers.get(layer.modifier)
    cat = find_category(scene, layer.cat_id)
    if mod is not None and cat is not None:
        push(ob, mod, cat, layer)


def sync_category(scene, cat):
    """Category settings changed: refresh the modifiers of every surface that uses it."""
    for ob in scene.objects:
        for layer in ob.sb_layers:
            if layer.cat_id == cat.uid:
                push_layer(ob, layer, scene)


def add_layer(ob, cat, group, scene):
    """Add a scatter layer for `cat` on mesh `ob`, painted by vertex group `group` ('' = the whole surface)."""
    mod = ob.modifiers.new(MOD_PREFIX + cat.name, "NODES")
    layer = ob.sb_layers.add()
    layer.modifier = mod.name
    layer.cat_id = cat.uid
    layer.group = group
    layer.density = 1.0
    push(ob, mod, cat, layer)
    return layer


def remove_layer(ob, index):
    layer = ob.sb_layers[index]
    mod = ob.modifiers.get(layer.modifier)
    if mod is not None:
        ob.modifiers.remove(mod)
    ob.sb_layers.remove(index)


def bake_layer(context, ob, index, collection, keep_layer=False, limit=None):
    """Turn the instances one layer makes into real linked-duplicate objects (they share the source mesh data).

    Only this layer is evaluated: the other scatter modifiers of the object are switched off for the moment.
    Raises ValueError when the layer makes more than `limit` instances (nothing is created then).
    """
    layer = ob.sb_layers[index]
    mod = ob.modifiers.get(layer.modifier)
    saved = {m.name: m.show_viewport for m in ob.modifiers if m.name.startswith(MOD_PREFIX)}
    for m in ob.modifiers:
        if m.name in saved:
            m.show_viewport = m.name == mod.name
    context.view_layer.update()
    made = []
    try:
        depsgraph = context.evaluated_depsgraph_get()
        found = [
            (inst.object.original, Matrix(inst.matrix_world))
            for inst in depsgraph.object_instances
            if inst.is_instance and inst.parent is not None and inst.parent.original == ob
        ]
        if limit is not None and len(found) > limit:
            raise ValueError(
                rpt_("The layer makes {count} objects, more than the limit of {limit}. Lower the density.").format(
                    count=len(found), limit=limit
                )
            )
        for src, matrix in found:
            copy = src.copy()
            copy.parent = None
            copy.animation_data_clear()
            copy.hide_viewport = False
            copy.hide_render = False
            copy.matrix_world = matrix
            collection.objects.link(copy)
            made.append(copy)
    finally:
        for m in ob.modifiers:
            if m.name in saved:
                m.show_viewport = saved[m.name]
    if made and not keep_layer:
        remove_layer(ob, index)
    return made


def transform_issue(ob):
    """True when the ground object has scale or rotation: instances live in its local space and would inherit both."""
    return any(abs(v - 1.0) > 1e-4 for v in ob.scale) or any(abs(a) > 1e-4 for a in ob.rotation_euler)


def layers_of(ob):
    """[(index, layer, modifier or None)] for the scatter layers of an object."""
    return [(i, layer, ob.modifiers.get(layer.modifier)) for i, layer in enumerate(ob.sb_layers)]
