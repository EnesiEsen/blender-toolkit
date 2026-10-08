"""Sidebar panel."""

import textwrap

from bpy.types import Panel

SEVERITY_ICON = {"ERROR": "ERROR", "WARNING": "INFO", "INFO": "DOT"}


def wrapped(layout, text, icon="NONE", width=34):
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


class CM_PT_main(Panel):
    bl_label = "Collision Maker"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Collision"

    def draw(self, context):
        s = context.scene.cm_settings
        layout = self.layout
        col = layout.column(align=True)
        col.prop(s, "shape")
        if s.shape == "BOX":
            col.prop(s, "box_fit")
        if s.shape == "CAPSULE":
            col.prop(s, "capsule_axis")
        if s.shape in ("CONVEX", "DECOMPOSE", "AUTO"):
            col.prop(s, "max_vertices")
        if s.shape in ("DECOMPOSE", "AUTO"):
            col.prop(s, "parts")
        col.prop(s, "replace")
        layout.operator("collision_maker.create", icon="MESH_CUBE")
        row = layout.row(align=True)
        row.operator("collision_maker.remove", icon="X")
        row.operator("collision_maker.toggle", icon="HIDE_OFF")


class CM_PT_check(Panel):
    bl_label = "Checker"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Collision"
    bl_parent_id = "CM_PT_main"

    def draw(self, context):
        layout = self.layout
        layout.operator("collision_maker.check", icon="VIEWZOOM")
        for index, item in enumerate(context.scene.cm_issues):
            box = layout.box()
            wrapped(box, item.message, icon=SEVERITY_ICON.get(item.severity, "DOT"))
            if item.fixable:
                box.operator("collision_maker.fix").index = index


classes = (CM_PT_main, CM_PT_check)
