"""Sidebar panels."""

from bpy.types import Panel


class HS_Panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Hard Surface"


class HS_PT_main(HS_Panel):
    bl_label = "Hard Surface Kit"

    def draw(self, context):
        self.layout.label(text="Select a mesh, then use the tools below.", icon="INFO")
        self.layout.operator("hardsurface_kit.finish", icon="CHECKMARK")


class HS_PT_bevel(HS_Panel):
    bl_label = "Bevel and Shading"
    bl_parent_id = "HS_PT_main"

    def draw(self, context):
        s = context.scene.hs_settings
        col = self.layout.column(align=True)
        col.prop(s, "bevel_width")
        col.prop(s, "bevel_segments")
        col.prop(s, "bevel_method")
        if s.bevel_method == "ANGLE":
            col.prop(s, "bevel_angle")
        col.prop(s, "harden_normals")
        col.prop(s, "shade_angle")
        col.prop(s, "mark_bevel")
        self.layout.operator("hardsurface_kit.bevel", icon="MOD_BEVEL")
        self.layout.operator("hardsurface_kit.mark_sharp", icon="EDGESEL")


class HS_PT_cutters(HS_Panel):
    bl_label = "Cutters"
    bl_parent_id = "HS_PT_main"

    def draw(self, context):
        s = context.scene.hs_settings
        col = self.layout.column(align=True)
        col.prop(s, "cut_operation")
        col.prop(s, "cut_solver")
        col.prop(s, "cutter_size")
        self.layout.operator("hardsurface_kit.cutter_add", icon="MOD_BOOLEAN")
        row = self.layout.row(align=True)
        row.operator("hardsurface_kit.cutter_new", text="Box").kind = "BOX"
        row.operator("hardsurface_kit.cutter_new", text="Cylinder").kind = "CYLINDER"
        row = self.layout.row(align=True)
        row.operator("hardsurface_kit.cutter_apply", icon="CHECKMARK")
        row.operator("hardsurface_kit.cutter_remove", icon="X")


class HS_PT_arrays(HS_Panel):
    bl_label = "Mirror and Arrays"
    bl_parent_id = "HS_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = context.scene.hs_settings
        layout = self.layout
        row = layout.row(align=True)
        row.prop(s, "mirror_x", toggle=True)
        row.prop(s, "mirror_y", toggle=True)
        row.prop(s, "mirror_z", toggle=True)
        layout.prop(s, "mirror_bisect")
        layout.operator("hardsurface_kit.mirror", icon="MOD_MIRROR")
        col = layout.column(align=True)
        col.prop(s, "array_count")
        col.prop(s, "array_offset")
        layout.operator("hardsurface_kit.array", icon="MOD_ARRAY")
        col = layout.column(align=True)
        col.prop(s, "radial_count")
        col.prop(s, "radial_axis")
        layout.operator("hardsurface_kit.radial", icon="MOD_ARRAY")


class HS_PT_edit(HS_Panel):
    bl_label = "Grooves and Cleanup"
    bl_parent_id = "HS_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = context.scene.hs_settings
        layout = self.layout
        col = layout.column(align=True)
        col.prop(s, "groove_width")
        col.prop(s, "groove_depth")
        row = layout.row(align=True)
        row.operator("hardsurface_kit.groove", text="Groove").raised = False
        row.operator("hardsurface_kit.groove", text="Panel").raised = True
        col = layout.column(align=True)
        col.prop(s, "merge_distance")
        col.prop(s, "dissolve_angle")
        col.prop(s, "join_quads")
        layout.operator("hardsurface_kit.clean", icon="BRUSH_DATA")


classes = (HS_PT_main, HS_PT_bevel, HS_PT_cutters, HS_PT_arrays, HS_PT_edit)
