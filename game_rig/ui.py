"""Sidebar panels."""

import textwrap

from bpy.types import Panel

SEVERITY_ICON = {"ERROR": "ERROR", "WARNING": "INFO", "INFO": "DOT"}


def wrapped(layout, text, icon="NONE", width=34):
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


class GR_Panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Game Rig"


class GR_PT_main(GR_Panel):
    bl_label = "Game Rig Kit"

    def draw(self, context):
        s = context.scene.gr_settings
        layout = self.layout
        wrapped(layout, "1. Markers  2. Build  3. Bind  4. IK  5. Retarget", icon="INFO")
        col = layout.column(align=True)
        col.prop(s, "rig_name")
        col.prop(s, "ik_bones")
        col.prop(s, "fingers")
        layout.operator("game_rig.markers", icon="EMPTY_AXIS")
        layout.operator("game_rig.build", icon="ARMATURE_DATA")


class GR_PT_bind(GR_Panel):
    bl_label = "Skinning"
    bl_parent_id = "GR_PT_main"

    def draw(self, context):
        self.layout.prop(context.scene.gr_settings, "max_influences")
        self.layout.operator("game_rig.bind", icon="MOD_ARMATURE")


class GR_PT_ik(GR_Panel):
    bl_label = "IK"
    bl_parent_id = "GR_PT_main"

    def draw(self, context):
        s = context.scene.gr_settings
        row = self.layout.row(align=True)
        row.prop(s, "ik_legs", toggle=True)
        row.prop(s, "ik_arms", toggle=True)
        row = self.layout.row(align=True)
        row.operator("game_rig.ik_setup", icon="CONSTRAINT_BONE")
        row.operator("game_rig.ik_remove", icon="X")


class GR_PT_names(GR_Panel):
    bl_label = "Rename and Retarget"
    bl_parent_id = "GR_PT_main"

    def draw(self, context):
        s = context.scene.gr_settings
        layout = self.layout
        layout.prop(s, "mapping_sheet")
        layout.operator("game_rig.mapping_sheet", icon="TEXT")
        layout.operator("game_rig.rename", icon="OUTLINER_OB_FONT")
        layout.separator()
        layout.prop(s, "source_rig")
        layout.prop(s, "step")
        layout.operator("game_rig.retarget", icon="ACTION")


class GR_PT_check(GR_Panel):
    bl_label = "Checker"
    bl_parent_id = "GR_PT_main"

    def draw(self, context):
        self.layout.operator("game_rig.check", icon="VIEWZOOM")
        for item in context.scene.gr_issues:
            wrapped(self.layout.box(), item.message, icon=SEVERITY_ICON.get(item.severity, "DOT"))


classes = (GR_PT_main, GR_PT_bind, GR_PT_ik, GR_PT_names, GR_PT_check)
