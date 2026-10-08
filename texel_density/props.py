"""Scene settings and the stored measurement."""

from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

PRESETS = (
    ("128", "128 px/m", "Far background, large terrain"),
    ("256", "256 px/m", "Environment, low priority"),
    ("512", "512 px/m", "Props and architecture (about 5 px/cm)"),
    ("1024", "1024 px/m", "Hero props, weapons, vehicles"),
    ("2048", "2048 px/m", "Close-up details, first-person items"),
    ("4096", "4096 px/m", "Extreme close-ups"),
    ("CUSTOM", "Custom", "Type your own value"),
)
SIZES = (("512", "512", ""), ("1024", "1024", ""), ("2048", "2048", ""), ("4096", "4096", ""), ("8192", "8192", ""))


def _target_changed(self, context):
    return None


class TD_Report(PropertyGroup):
    valid: BoolProperty()
    object_name: StringProperty()
    faces: IntProperty()
    average: FloatProperty()
    minimum: FloatProperty()
    maximum: FloatProperty()
    coverage: FloatProperty()
    outside: IntProperty()
    flagged: FloatProperty()
    unwrapped: IntProperty()
    needed: FloatProperty()
    suggested: IntProperty()


class TD_Settings(PropertyGroup):
    preset: EnumProperty(name="Target", items=PRESETS, default="512", description="Pixels per meter you aim for")
    custom: FloatProperty(name="Custom (px/m)", default=512.0, min=1.0, soft_max=8192.0)
    default_size: EnumProperty(
        name="Texture Size",
        items=SIZES,
        default="2048",
        description="Used for materials that have no image (the density depends on the texture size)",
    )
    tolerance: FloatProperty(
        name="Tolerance",
        default=10.0,
        min=1.0,
        max=100.0,
        subtype="PERCENTAGE",
        description="Faces within this distance of the target count as correct",
    )
    mode: EnumProperty(
        name="Scale",
        default="ISLAND",
        items=(
            ("ISLAND", "Each Island", "Every UV island gets exactly the target density"),
            (
                "OBJECT",
                "Whole Object",
                "All islands scale together: the object gets the target on average and keeps its relative sizes",
            ),
        ),
    )
    selected_only: BoolProperty(
        name="Selected Faces Only", default=True, description="In Edit Mode: only the selected faces are scaled"
    )

    def target(self):
        return self.custom if self.preset == "CUSTOM" else float(self.preset)
