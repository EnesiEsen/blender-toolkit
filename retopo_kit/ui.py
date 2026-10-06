"""Sidebar panels: one-click retopology, guides and the quality report."""
import textwrap

from bpy.app.translations import pgettext_iface as iface_
from bpy.types import Panel

from . import guides, meshing


def wrapped(layout, text, icon="NONE", width=34):
    """Label that wraps onto several lines; sidebar labels are cut off at the region width otherwise."""
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(iface_(text), width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


class RK_PT_main(Panel):
    bl_label = "Retopo Kit"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Retopo Kit"

    def draw(self, context):
        layout = self.layout
        s = context.scene.rk_settings
        layout.prop(s, "preset")
        layout.prop(s, "target_faces")
        row = layout.row(align=True)
        row.prop(s, "symmetry_x", toggle=True)
        row.prop(s, "symmetry_y", toggle=True)
        row.prop(s, "symmetry_z", toggle=True)
        col = layout.column(align=True)
        col.prop(s, "snap")
        col.prop(s, "hide_source")
        layout.operator("retopo_kit.retopo", icon="MOD_REMESH")
        if not meshing.qremeshify_available():
            wrapped(layout.box(), "QRemeshify is not installed: using QuadriFlow. Install it for guide curves and "
                    "sharper results.", icon="INFO")

        sub = layout.box()
        sub.label(text="Advanced")
        sub.prop(s, "engine")
        sub.prop(s, "sharp_angle")
        sub.prop(s, "smoothing")
        sub.prop(s, "match_target")
        sub.prop(s, "use_guides")
        if context.space_data is not None and context.space_data.type == "VIEW_3D":
            sub.prop(context.space_data.overlay, "show_retopology")


class RK_PT_guides(Panel):
    bl_label = "Guides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Retopo Kit"
    bl_parent_id = "RK_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        wrapped(layout, "Lines the new quads should follow (eyes, mouth, fingers, panel gaps).")
        col = layout.column(align=True)
        col.operator("retopo_kit.draw_guide", icon="GREASEPENCIL")
        col.operator("retopo_kit.apply_guides", icon="CHECKMARK")
        col.operator("retopo_kit.mark_guides", icon="EDGESEL")
        col.operator("retopo_kit.clear_guides", icon="X")
        target = guides.target_of(context)
        if target is not None:
            wrapped(layout, iface_("Guide edges on '{name}': {count}").format(
                name=target.name, count=guides.count(target)))


class RK_PT_report(Panel):
    bl_label = "Quality Report"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Retopo Kit"
    bl_parent_id = "RK_PT_main"

    def draw(self, context):
        layout = self.layout
        layout.operator("retopo_kit.report", icon="VIEWZOOM")
        r = context.scene.rk_report
        if not r.valid:
            return
        quad_pct = 100.0 * r.quads / max(1, r.faces)
        col = layout.column(align=True)
        col.label(text=r.object_name, icon="MESH_DATA")
        col.label(text=iface_("{faces} faces, {pct:.0f}% quads").format(faces=r.faces, pct=quad_pct))
        col.label(text=iface_("{tris} tris, {ngons} n-gons").format(tris=r.tris, ngons=r.ngons))
        col.label(text=iface_("Poles 3 / 5 / 6+: {p3} / {p5} / {pn}").format(p3=r.pole3, p5=r.pole5, pn=r.polen))
        col.label(text=iface_("Edge length variation: {cv:.0f}%").format(cv=r.edge_cv * 100))
        if r.has_dev:
            wrapped(col, iface_("Distance to source (avg / max): {avg:.2f}% / {mx:.2f}%").format(
                avg=r.dev_avg, mx=r.dev_max))
        if r.non_manifold:
            col.label(text=iface_("{count} non-manifold edges").format(count=r.non_manifold), icon="ERROR")
        if quad_pct < 90:
            wrapped(layout, "Many triangles: raise the target faces or add guides.", icon="INFO")


classes = (RK_PT_main, RK_PT_guides, RK_PT_report)
