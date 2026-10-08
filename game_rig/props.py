"""Scene settings and the list of problems found by the rig check."""

import bpy
from bpy.props import BoolProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup


class GR_Issue(PropertyGroup):
    severity: StringProperty()
    code: StringProperty()
    message: StringProperty()


class GR_Settings(PropertyGroup):
    rig_name: StringProperty(name="Rig Name", default="Rig", description="Name of the armature that is built")
    ik_bones: BoolProperty(
        name="IK Helper Bones", default=True, description="Add the mannequin's ik_foot and ik_hand bones"
    )
    fingers: BoolProperty(name="Fingers", default=True, description="Add the finger bones")
    max_influences: IntProperty(
        name="Max Influences",
        default=4,
        min=1,
        max=8,
        description="Bones that may move one vertex (4 is the mobile limit, 8 the PC default)",
    )
    mapping_sheet: StringProperty(
        name="Mapping Sheet",
        default="gr_bone_map",
        description="Text block with 'source bone = UE bone' lines that override the guesses",
    )
    source_rig: PointerProperty(
        name="Source Rig",
        type=bpy.types.Object,
        poll=lambda self, ob: ob.type == "ARMATURE",
        description="The rig whose animation is copied (Mixamo, Rigify, ...)",
    )
    step: IntProperty(name="Frame Step", default=1, min=1, max=10, description="Frames between baked keys")
    ik_legs: BoolProperty(name="Legs", default=True)
    ik_arms: BoolProperty(name="Arms", default=True)
