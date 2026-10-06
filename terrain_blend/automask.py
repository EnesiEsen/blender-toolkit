"""Generate a vertex-group mask from slope, height or noise, so layers can be placed without hand painting."""
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import Operator
from mathutils import Vector, noise


def smoothstep(x, lo, hi):
    if hi <= lo:
        return (x >= lo).astype(np.float32)
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def vertex_data(ob):
    """World-space z of every vertex and the z component of its world-space unit normal."""
    mesh = ob.data
    count = len(mesh.vertices)
    co = np.empty(count * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(count, 3)
    nor = np.empty(count * 3, dtype=np.float32)
    mesh.vertex_normals.foreach_get("vector", nor)
    nor = nor.reshape(count, 3)
    m = np.array(ob.matrix_world, dtype=np.float64)
    z = co @ m[2, :3] + m[2, 3]
    normal_world = nor @ np.linalg.inv(m[:3, :3])  # inverse transpose, applied to row vectors
    normal_world /= np.maximum(np.linalg.norm(normal_world, axis=1, keepdims=True), 1e-12)
    return co, z, normal_world[:, 2]


def read_weights(ob, group):
    weights = np.zeros(len(ob.data.vertices), dtype=np.float32)
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == group.index:
                weights[v.index] = g.weight
    return weights


def write_weights(ob, group, weights):
    """Replace the group content; weights are quantized to 1/255 so a few vg.add calls cover every vertex."""
    group.remove(range(len(ob.data.vertices)))
    levels = np.rint(np.clip(weights, 0.0, 1.0) * 255).astype(np.int32)
    for level in np.unique(levels):
        if level:
            group.add(np.nonzero(levels == level)[0].tolist(), float(level) / 255.0, "REPLACE")


# Sensible "From"/"To" per source: degrees for slope, meters for height, 0-1 for noise.
RANGE_DEFAULTS = {"SLOPE": (20.0, 40.0), "HEIGHT": (0.0, 10.0), "NOISE": (0.4, 0.6)}


def _mode_changed(self, context):
    self.low, self.high = RANGE_DEFAULTS[self.mode]


class TB_OT_auto_mask(Operator):
    bl_idname = "terrain_blend.auto_mask"
    bl_label = "Generate Mask"
    bl_description = "Fill a vertex group from slope, height or noise (pick the group first, it is created if missing)"
    bl_options = {"REGISTER", "UNDO"}

    group: StringProperty(name="Vertex Group", description="Created when it does not exist")
    mode: EnumProperty(name="Source", items=(
        ("SLOPE", "Slope", "Steepness of the surface (0 = flat, 90 = vertical)"),
        ("HEIGHT", "Height", "World-space height in meters"),
        ("NOISE", "Noise", "Random patches"),
    ), default="SLOPE", update=_mode_changed)
    low: FloatProperty(name="From", default=20.0, description="Value where the mask starts (degrees, meters or 0-1)")
    high: FloatProperty(name="To", default=40.0, description="Value where the mask reaches 1")
    invert: BoolProperty(name="Invert", default=False)
    combine: EnumProperty(name="Combine", items=(
        ("REPLACE", "Replace", "Overwrite the group"),
        ("MULTIPLY", "Intersect", "Keep only where both the old and the new mask are set"),
        ("MAX", "Union", "Keep where either the old or the new mask is set"),
    ), default="REPLACE")
    noise_scale: FloatProperty(name="Noise Scale", default=0.1, min=0.0001, description="Patch size (1 / meters)")
    seed: IntProperty(name="Seed", default=0)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def invoke(self, context, event):
        if not self.group:
            ob = context.object
            layers = ob.tb_layers
            if ob.tb_index > 0 and ob.tb_index < len(layers):
                self.group = layers[ob.tb_index].mask or layers[ob.tb_index].name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "group", context.object, "vertex_groups")
        layout.prop(self, "mode")
        layout.prop(self, "low")
        layout.prop(self, "high")
        if self.mode == "NOISE":
            layout.prop(self, "noise_scale")
            layout.prop(self, "seed")
        layout.prop(self, "invert")
        layout.prop(self, "combine")

    def execute(self, context):
        ob = context.object
        if not self.group:
            self.report({"ERROR"}, rpt_("Choose or type a vertex group name."))
            return {"CANCELLED"}
        co, z, normal_z = vertex_data(ob)
        if self.mode == "SLOPE":
            value = np.degrees(np.arccos(np.clip(normal_z, -1.0, 1.0)))
        elif self.mode == "HEIGHT":
            value = z
        else:
            offset = Vector((self.seed * 17.3, self.seed * 31.7, self.seed * 5.9))
            value = np.array([noise.noise(Vector(c) * self.noise_scale + offset) * 0.5 + 0.5 for c in co.tolist()],
                             dtype=np.float32)
        low, high = RANGE_DEFAULTS[self.mode]
        if self.properties.is_property_set("low"):  # a script or the dialog chose the range
            low = self.low
        if self.properties.is_property_set("high"):
            high = self.high
        weights = smoothstep(value, low, high)
        if self.invert:
            weights = 1.0 - weights
        group = ob.vertex_groups.get(self.group) or ob.vertex_groups.new(name=self.group)
        if self.combine != "REPLACE":
            old = read_weights(ob, group)
            weights = weights * old if self.combine == "MULTIPLY" else np.maximum(weights, old)
        write_weights(ob, group, weights)
        self.report({"INFO"}, rpt_("Mask '{group}': {count} of {total} vertices set").format(
            group=group.name, count=int((weights > 0.003).sum()), total=len(weights)))
        return {"FINISHED"}


classes = (TB_OT_auto_mask,)
