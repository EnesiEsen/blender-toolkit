"""Scene settings and the list of problems found by the checker."""

from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup


class CM_Issue(PropertyGroup):
    severity: StringProperty()
    code: StringProperty()
    message: StringProperty()
    object_name: StringProperty()
    fixable: BoolProperty()


class CM_Settings(PropertyGroup):
    shape: EnumProperty(
        name="Shape",
        default="AUTO",
        items=(
            ("AUTO", "Auto", "Pick the simplest shape that fits the mesh"),
            ("BOX", "Box (UBX)", "One box"),
            ("SPHERE", "Sphere (USP)", "One sphere"),
            ("CAPSULE", "Capsule (UCP)", "One capsule"),
            ("CONVEX", "Convex Hull (UCX)", "The tightest convex shape around the mesh"),
            ("DECOMPOSE", "Convex Parts (UCX)", "Several convex hulls that follow a concave mesh more closely"),
        ),
    )
    box_fit: EnumProperty(
        name="Box Fit",
        default="OBB",
        items=(
            ("OBB", "Oriented", "A box that may be rotated to fit tighter"),
            ("AABB", "Axis Aligned", "A box that follows the object's axes"),
        ),
    )
    capsule_axis: EnumProperty(
        name="Capsule Axis",
        default="AUTO",
        items=(("AUTO", "Auto", "The longest direction of the mesh"), ("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")),
    )
    max_vertices: IntProperty(
        name="Max Vertices",
        default=64,
        min=8,
        max=255,
        description="Largest number of vertices of one hull (Unreal limits a hull to 255)",
    )
    parts: IntProperty(name="Parts", default=6, min=2, max=32, description="How many hulls Convex Parts may use")
    replace: BoolProperty(name="Replace Existing", default=True, description="Remove the old shapes of the mesh first")
