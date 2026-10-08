"""Scene settings and the stored quality report."""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

# Preset values: sharp angle (degrees) above which an edge is kept as a hard feature, smoothing after quadrangulation.
PRESETS = {
    "SIMPLE": {"sharp_angle": 30.0, "smoothing": False},
    "HARD": {"sharp_angle": 30.0, "smoothing": False},
    "ORGANIC": {"sharp_angle": 80.0, "smoothing": True},
}


def _preset_changed(self, context):
    values = PRESETS.get(self.preset)
    if values:
        self.sharp_angle, self.smoothing = values["sharp_angle"], values["smoothing"]


class RK_Settings(PropertyGroup):
    preset: EnumProperty(
        name="Preset",
        update=_preset_changed,
        default="AUTO",
        items=(
            ("AUTO", "Auto", "Pick hard-surface or organic by looking at how many sharp edges the mesh has"),
            ("SIMPLE", "Simple Prop", "Boxes, props and other simple shapes: keep sharp edges and the boundary"),
            ("HARD", "Hard Surface / Vehicle", "Machines, vehicles, architecture: keep sharp edges crisp"),
            (
                "ORGANIC",
                "Organic / Character",
                "Characters, creatures, sculpts: smooth flow, only seams act as hard lines",
            ),
        ),
    )
    engine: EnumProperty(
        name="Engine",
        default="AUTO",
        items=(
            ("AUTO", "Auto", "QRemeshify when it is installed, otherwise Blender's QuadriFlow"),
            (
                "QREMESHIFY",
                "QRemeshify",
                "Best quality, follows sharp edges and guide curves (needs the QRemeshify extension)",
            ),
            ("QUADRIFLOW", "QuadriFlow", "Built into Blender, fast, ignores guide curves"),
        ),
    )
    target_faces: IntProperty(
        name="Target Faces",
        default=2000,
        min=50,
        soft_max=50000,
        description="Approximate number of faces of the result",
    )
    match_target: BoolProperty(
        name="Match Target",
        default=True,
        description="QRemeshify: run a second pass when the first result is far from the target",
    )
    use_guides: BoolProperty(
        name="Use Guides",
        default=True,
        description="Keep the guide edges and seams of the source as hard lines (QRemeshify only)",
    )
    sharp_angle: FloatProperty(
        name="Sharp Angle", default=35.0, min=1.0, max=179.0, description="Edges sharper than this stay as hard lines"
    )
    smoothing: BoolProperty(name="Smoothing", default=True, description="Smooth the result after quadrangulation")
    symmetry_x: BoolProperty(name="X", description="Symmetry along the X axis (adds a Mirror modifier)")
    symmetry_y: BoolProperty(name="Y", description="Symmetry along the Y axis (adds a Mirror modifier)")
    symmetry_z: BoolProperty(name="Z", description="Symmetry along the Z axis (adds a Mirror modifier)")
    snap: BoolProperty(
        name="Snap to Source",
        default=True,
        description="Add a Shrinkwrap modifier so later edits stay on the source surface",
    )
    hide_source: BoolProperty(name="Hide Source", default=True)
    guide_target: PointerProperty(
        name="Guide Target",
        type=bpy.types.Object,
        poll=lambda self, ob: ob.type == "MESH",
        description="Mesh that receives the guide lines",
    )


class RK_Report(PropertyGroup):
    valid: BoolProperty()
    object_name: StringProperty()
    faces: IntProperty()
    quads: IntProperty()
    tris: IntProperty()
    ngons: IntProperty()
    pole3: IntProperty()
    pole5: IntProperty()
    polen: IntProperty()
    non_manifold: IntProperty()
    edge_cv: FloatProperty()
    has_dev: BoolProperty()
    dev_avg: FloatProperty()
    dev_max: FloatProperty()
