"""Scene settings of every tool of the kit."""

import math

from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty
from bpy.types import PropertyGroup


class HS_Settings(PropertyGroup):
    bevel_width: FloatProperty(name="Width", default=0.02, min=0.0001, soft_max=1.0, subtype="DISTANCE", unit="LENGTH")
    bevel_segments: IntProperty(name="Segments", default=3, min=1, max=16)
    bevel_method: EnumProperty(
        name="Limit",
        default="ANGLE",
        items=(
            ("ANGLE", "Angle", "Bevel the edges that are sharper than the angle"),
            ("WEIGHT", "Weights", "Bevel the edges that carry a bevel weight (Mark Sharp can set them)"),
        ),
    )
    bevel_angle: FloatProperty(name="Angle", default=math.radians(30), min=0.0, max=math.pi, subtype="ANGLE")
    harden_normals: BoolProperty(
        name="Harden Normals",
        default=True,
        description="Keep the big faces flat-shaded across the bevel (no dark smudges)",
    )
    shade_angle: FloatProperty(
        name="Smooth Angle",
        default=math.radians(30),
        min=0.0,
        max=math.pi,
        subtype="ANGLE",
        description="Edges sharper than this are shaded as hard edges",
    )
    mark_bevel: BoolProperty(
        name="Set Bevel Weights", default=True, description="Also give the sharp edges a bevel weight of 1"
    )
    cut_operation: EnumProperty(
        name="Operation",
        default="DIFFERENCE",
        items=(
            ("DIFFERENCE", "Cut", "Remove the cutter from the object"),
            ("UNION", "Add", "Merge the cutter into the object"),
            ("INTERSECT", "Intersect", "Keep only what both share"),
        ),
    )
    cut_solver: EnumProperty(
        name="Solver",
        default="EXACT",
        items=(
            ("EXACT", "Exact", "Most reliable, slower"),
            ("MANIFOLD", "Manifold", "Fast; needs closed, clean meshes"),
            ("FLOAT", "Fast", "Quick but can fail on touching faces"),
        ),
    )
    cutter_size: FloatVectorProperty(name="Size", default=(0.5, 0.5, 0.5), min=0.001, subtype="XYZ", unit="LENGTH")
    mirror_x: BoolProperty(name="X", default=True)
    mirror_y: BoolProperty(name="Y")
    mirror_z: BoolProperty(name="Z")
    mirror_bisect: BoolProperty(
        name="Cut at Center", description="Remove the half on the wrong side of the mirror plane"
    )
    array_count: IntProperty(name="Count", default=3, min=2, max=256)
    array_offset: FloatProperty(name="Offset", default=1.0, description="Distance between copies in object sizes")
    radial_count: IntProperty(name="Count", default=8, min=2, max=256)
    radial_axis: EnumProperty(name="Axis", default="Z", items=(("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")))
    groove_width: FloatProperty(name="Width", default=0.02, min=0.0001, subtype="DISTANCE", unit="LENGTH")
    groove_depth: FloatProperty(name="Depth", default=0.02, min=0.0001, subtype="DISTANCE", unit="LENGTH")
    merge_distance: FloatProperty(name="Merge Distance", default=0.0001, min=0.0, subtype="DISTANCE", unit="LENGTH")
    dissolve_angle: FloatProperty(
        name="Dissolve Angle",
        default=math.radians(0.5),
        min=0.0,
        max=math.radians(30),
        subtype="ANGLE",
        description="Flat edges under this angle are removed",
    )
    join_quads: BoolProperty(name="Triangles to Quads", default=False)
