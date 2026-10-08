"""Sidebar panels."""

import textwrap

from bpy.types import Panel

SEVERITY_ICON = {"ERROR": "ERROR", "WARNING": "INFO", "INFO": "DOT"}


def wrapped(layout, text, icon="NONE", width=34):
    """Label that wraps onto several lines; sidebar labels are cut off at the region width otherwise."""
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


class UE_PT_main(Panel):
    bl_label = "UE5 Bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE5"

    def draw(self, context):
        layout = self.layout
        s = context.scene.ue_settings
        col = layout.column(align=True)
        col.prop(s, "output_dir")
        col.prop(s, "prefixes")
        col.prop(s, "center_origin")
        layout.operator("ue5_bridge.export_static", icon="MESH_CUBE")


class UE_PT_skeletal(Panel):
    bl_label = "Skeleton"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE5"
    bl_parent_id = "UE_PT_main"

    def draw(self, context):
        layout = self.layout
        s = context.scene.ue_settings
        col = layout.column(align=True)
        col.prop(s, "skeletal_mode")
        col.prop(s, "fix_rig")
        col.prop(s, "root_name")
        col.prop(s, "only_deform")
        col.prop(s, "leaf_bones")
        col.prop(s, "armature_node")
        col.prop(s, "tangents")
        row = layout.row(align=True)
        row.operator("ue5_bridge.check", icon="VIEWZOOM")
        row.operator("ue5_bridge.fix_root", icon="BONE_DATA")
        for item in context.scene.ue_issues:
            wrapped(layout.box(), item.message, icon=SEVERITY_ICON.get(item.severity, "DOT"))
        layout.operator("ue5_bridge.export_skeletal", icon="ARMATURE_DATA")


class UE_PT_animation(Panel):
    bl_label = "Animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE5"
    bl_parent_id = "UE_PT_main"

    def draw(self, context):
        layout = self.layout
        s = context.scene.ue_settings
        col = layout.column(align=True)
        col.prop(s, "anim_source")
        col.prop(s, "bake_step")
        col.prop(s, "root_motion")
        if s.root_motion:
            col.prop(s, "hips_bone")
            wrapped(
                layout,
                "Only the horizontal movement of the hips is moved to the root bone (turning stays on the hips).",
                icon="INFO",
            )
        layout.operator("ue5_bridge.export_animations", icon="ACTION")


classes = (UE_PT_main, UE_PT_skeletal, UE_PT_animation)
