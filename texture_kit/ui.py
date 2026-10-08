"""Sidebar panels."""

import textwrap

from bpy.types import Panel

SEVERITY_ICON = {"ERROR": "ERROR", "WARNING": "INFO", "INFO": "DOT"}


def wrapped(layout, text, icon="NONE", width=34):
    """Label that wraps onto several lines; sidebar labels are cut off at the region width otherwise."""
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


class TK_PT_main(Panel):
    bl_label = "Texture Kit"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texture Kit"

    def draw(self, context):
        s = context.scene.tk_settings
        layout = self.layout
        col = layout.column(align=True)
        col.prop(s, "export_dir")
        col.prop(s, "file_format")
        col.prop(s, "size_limit")
        col.prop(s, "power_of_two")


class TK_PT_doctor(Panel):
    bl_label = "Doctor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texture Kit"
    bl_parent_id = "TK_PT_main"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.tk_settings, "doctor_max")
        layout.operator("texture_kit.scan", icon="VIEWZOOM")
        issues = context.scene.tk_issues
        if not len(issues):
            return
        layout.operator("texture_kit.fix_all", icon="CHECKMARK")
        for index, item in enumerate(issues):
            box = layout.box()
            wrapped(box, item.message, icon=SEVERITY_ICON.get(item.severity, "DOT"))
            if item.fixable:
                box.operator("texture_kit.fix").index = index


class TK_PT_export(Panel):
    bl_label = "Export Texture Set"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texture Kit"
    bl_parent_id = "TK_PT_main"

    def draw(self, context):
        s = context.scene.tk_settings
        layout = self.layout
        col = layout.column(align=True)
        col.prop(s, "asset_name")
        col.prop(s, "normal_mode")
        col.prop(s, "pack_orm")
        if s.pack_orm:
            col.prop(s, "ao_image")
        layout.operator("texture_kit.export", icon="EXPORT")


class TK_PT_pack(Panel):
    bl_label = "Channel Packer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texture Kit"
    bl_parent_id = "TK_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = context.scene.tk_settings
        layout = self.layout
        layout.operator("texture_kit.pack_preset", icon="PRESET")
        for label, slot in (("R", s.slot_r), ("G", s.slot_g), ("B", s.slot_b), ("A", s.slot_a)):
            box = layout.box()
            box.label(text=label)
            box.template_ID(slot, "image", open="image.open")
            if slot.image:
                row = box.row(align=True)
                row.prop(slot, "channel", text="")
                row.prop(slot, "invert", toggle=True)
            else:
                box.prop(slot, "value")
        col = layout.column(align=True)
        col.prop(s, "pack_name")
        col.prop(s, "pack_size")
        col.prop(s, "pack_save")
        layout.operator("texture_kit.pack", icon="NODE_COMPOSITING")


class TK_PT_normal(Panel):
    bl_label = "Normal Map"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texture Kit"
    bl_parent_id = "TK_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = context.scene.tk_settings
        self.layout.template_ID(s, "normal_image", open="image.open")
        self.layout.operator("texture_kit.flip_normal", icon="ARROW_LEFTRIGHT")


classes = (TK_PT_main, TK_PT_doctor, TK_PT_export, TK_PT_pack, TK_PT_normal)
