"""Sidebar panel."""

from bpy.app.translations import pgettext_iface as iface_
from bpy.types import Panel


class TD_PT_main(Panel):
    bl_label = "Texel Density"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texel Density"

    def draw(self, context):
        s = context.scene.td_settings
        layout = self.layout
        col = layout.column(align=True)
        col.prop(s, "preset")
        if s.preset == "CUSTOM":
            col.prop(s, "custom")
        col.prop(s, "default_size")
        col.prop(s, "tolerance")
        layout.operator("texel_density.analyze", icon="VIEWZOOM")
        self.draw_report(context, layout, s)
        row = layout.row(align=True)
        row.operator("texel_density.show", icon="COLOR")
        row.operator("texel_density.hide", icon="X")

    def draw_report(self, context, layout, s):
        r = context.scene.td_report
        if not r.valid:
            return
        box = layout.box()
        box.label(text=r.object_name, icon="MESH_DATA")
        col = box.column(align=True)
        col.label(text=iface_("Average: {a:.0f} px/m ({c:.2f} px/cm)").format(a=r.average, c=r.average / 100))
        col.label(text=iface_("Lowest {lo:.0f}, highest {hi:.0f} px/m").format(lo=r.minimum, hi=r.maximum))
        col.label(
            text=iface_("{p:.0f}% of the surface is off target").format(p=r.flagged),
            icon="ERROR" if r.flagged > 20 else "NONE",
        )
        col.label(text=iface_("UV space used: {c:.0f}%").format(c=r.coverage))
        if r.outside:
            col.label(text=iface_("{n} faces lie outside 0-1").format(n=r.outside), icon="INFO")
        if r.unwrapped:
            col.label(text=iface_("{n} faces without UV area").format(n=r.unwrapped), icon="ERROR")


class TD_PT_set(Panel):
    bl_label = "Set Density"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texel Density"
    bl_parent_id = "TD_PT_main"

    def draw(self, context):
        s = context.scene.td_settings
        layout = self.layout
        layout.prop(s, "mode")
        if context.mode == "EDIT_MESH":
            layout.prop(s, "selected_only")
        layout.operator("texel_density.set", icon="UV")
        layout.operator("texel_density.copy", icon="COPYDOWN")
        layout.operator("texel_density.pack", icon="UV_ISLANDSEL")


classes = (TD_PT_main, TD_PT_set)
