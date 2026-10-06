"""Sidebar panels. The target (Prop, MLO, Ped) chooses which settings and buttons are shown."""
import textwrap

from bpy.app.translations import pgettext_iface as iface_
from bpy.types import Panel

from . import compat

SEVERITY_ICON = {"ERROR": "ERROR", "WARNING": "INFO", "INFO": "DOT"}


def wrapped(layout, text, icon="NONE", width=34):
    """Label that wraps onto several lines; sidebar labels are cut off at the region width otherwise."""
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


def draw_prop(layout, context, s):
    col = layout.column(align=True)
    col.prop(s, "separate")
    col.prop(s, "collision")
    if s.collision in ("PROXY", "HULL"):
        col.prop(s, "collision_tris")
    col.prop(s, "make_lods")
    if s.make_lods:
        col.prop(s, "lod_preset")
        col.prop(s, "lod_scale")
    col.prop(s, "create_ytyp")
    col.prop(s, "convert_dds")
    col.prop(s, "create_ytd")
    col.prop(s, "auto_fix")
    layout.operator("fivem_toolkit.build_prop", icon="MESH_CUBE")


def draw_mlo(layout, context, s):
    wrapped(layout, "Select the interior collection in the outliner. Inside it: room.<name> sub-collections with "
            "the meshes, and portal.<room>.<room> quads (limbo = outside).", icon="INFO")
    layout.operator("fivem_toolkit.mlo_template", icon="ADD")
    col = layout.column(align=True)
    col.prop(s, "mlo_collision")
    if s.mlo_collision == "PROXY":
        col.prop(s, "mlo_collision_tris")
    col.prop(s, "make_lods")
    col.prop(s, "convert_dds")
    col.prop(s, "auto_fix")
    layout.operator("fivem_toolkit.mlo_check", icon="VIEWZOOM")
    layout.operator("fivem_toolkit.build_mlo", icon="HOME")


def draw_ped(layout, context, s):
    wrapped(layout, "Select the rigged meshes. Check Assets (Doctor below) lists weight problems; Retarget Weights "
            "moves the weights onto GTA bones without losing them.", icon="INFO")
    col = layout.column(align=True)
    col.prop(s, "ped_armature")
    col.prop(s, "ped_backup")
    col.prop(s, "ped_mapping")
    layout.operator("fivem_toolkit.ped_mapping_sheet", icon="TEXT")
    layout.operator("fivem_toolkit.ped_retarget", icon="ARMATURE_DATA")
    layout.operator("fivem_toolkit.scan", icon="VIEWZOOM")


TARGETS = {"PROP": draw_prop, "MLO": draw_mlo, "PED": draw_ped}


class FK_PT_main(Panel):
    bl_label = "FiveM Toolkit"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FiveM"

    def draw(self, context):
        layout = self.layout
        s = context.scene.fk_settings
        if not compat.ready():
            wrapped(layout.box(), "Sollumz is not installed or not enabled. Install it from Preferences > "
                    "Get Extensions.", icon="ERROR")
        layout.prop(s, "target", expand=True)
        TARGETS[s.target](layout, context, s)


class FK_PT_doctor(Panel):
    bl_label = "Doctor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FiveM"
    bl_parent_id = "FK_PT_main"

    def draw(self, context):
        layout = self.layout
        s = context.scene.fk_settings
        col = layout.column(align=True)
        col.prop(s, "max_texture")
        col.prop(s, "tri_limit")
        layout.operator("fivem_toolkit.scan", icon="VIEWZOOM")
        items = context.scene.fk_issues
        if not len(items):
            return
        layout.operator("fivem_toolkit.fix_all", icon="CHECKMARK")
        for index, item in enumerate(items):
            box = layout.box()
            wrapped(box, item.message, icon=SEVERITY_ICON.get(item.severity, "DOT"))
            if item.fixable:
                box.operator("fivem_toolkit.fix", text=iface_("Fix")).index = index


class FK_PT_export(Panel):
    bl_label = "Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FiveM"
    bl_parent_id = "FK_PT_main"

    def draw(self, context):
        layout = self.layout
        s = context.scene.fk_settings
        col = layout.column(align=True)
        col.prop(s, "resource_name")
        col.prop(s, "output_dir")
        col.prop(s, "export_format")
        col.prop(s, "selected_only")
        layout.operator("fivem_toolkit.export", icon="EXPORT")


classes = (FK_PT_main, FK_PT_doctor, FK_PT_export)
