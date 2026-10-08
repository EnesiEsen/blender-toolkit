"""Operators: analyze, show colors, set and copy density, pack islands."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import Operator

from . import density, uvtools


def mesh_objects(context):
    return [o for o in context.selected_objects if o.type == "MESH"]


def fill_report(context, obj, data, s):
    report = context.scene.td_report
    stats = density.summary(data, s.target(), s.tolerance)
    report.valid, report.object_name = True, obj.name
    for key, value in stats.items():
        setattr(report, key, value)


class TD_OT_analyze(Operator):
    bl_idname = "texel_density.analyze"
    bl_label = "Measure"
    bl_description = "Measure the texel density of the active object (pixels per meter)"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        s = context.scene.td_settings
        obj = context.object
        if obj.mode == "EDIT":
            obj.update_from_editmode()
        try:
            data = density.analyze(obj, int(s.default_size))
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        fill_report(context, obj, data, s)
        self.report(
            {"INFO"}, rpt_("'{name}': {value:.0f} px/m on average.").format(name=obj.name, value=data["average"])
        )
        return {"FINISHED"}


class TD_OT_show(Operator):
    bl_idname = "texel_density.show"
    bl_label = "Show Colors"
    bl_description = "Color every face by its density: blue too low, green on target, red too high"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(mesh_objects(context)) and context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.td_settings
        shown = 0
        for obj in mesh_objects(context):
            try:
                data = density.analyze(obj, int(s.default_size))
            except ValueError:
                continue
            density.show_colors(obj, data, s.target())
            shown += 1
        space = context.space_data
        if shown and space is not None and space.type == "VIEW_3D":
            space.shading.type, space.shading.color_type = "SOLID", "VERTEX"
        if not shown:
            self.report({"ERROR"}, rpt_("None of the selected meshes has a UV map."))
            return {"CANCELLED"}
        return {"FINISHED"}


class TD_OT_hide(Operator):
    bl_idname = "texel_density.hide"
    bl_label = "Hide Colors"
    bl_description = "Remove the density colors"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(mesh_objects(context)) and context.mode == "OBJECT"

    def execute(self, context):
        for obj in mesh_objects(context):
            density.hide_colors(obj)
        return {"FINISHED"}


class TD_OT_set(Operator):
    bl_idname = "texel_density.set"
    bl_label = "Set Density"
    bl_description = "Scale the UV islands so that the selected objects (or faces in Edit Mode) get the target density"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        s = context.scene.td_settings
        targets = [context.object] if context.mode == "EDIT_MESH" else mesh_objects(context)
        done = 0
        for obj in targets:
            try:
                result = uvtools.apply_density(obj, s.target(), s.mode, int(s.default_size), s.selected_only)
            except ValueError as e:
                self.report({"WARNING"}, str(e))
                continue
            done += result["scaled"]
        if not done:
            self.report({"ERROR"}, rpt_("Nothing was scaled: check that the meshes have UV maps and faces."))
            return {"CANCELLED"}
        self.report({"INFO"}, rpt_("{count} UV islands scaled.").format(count=done))
        return {"FINISHED"}


class TD_OT_copy(Operator):
    bl_idname = "texel_density.copy"
    bl_label = "Copy from Active"
    bl_description = "Give the other selected objects the texel density of the active object"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.td_settings
        try:
            wanted = density.analyze(context.object, int(s.default_size))["average"]
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        count = 0
        for obj in mesh_objects(context):
            if obj is context.object:
                continue
            try:
                uvtools.apply_density(obj, wanted, "OBJECT", int(s.default_size))
                count += 1
            except ValueError:
                continue
        self.report({"INFO"}, rpt_("{count} objects now have {value:.0f} px/m.").format(count=count, value=wanted))
        return {"FINISHED"}


class TD_OT_pack(Operator):
    bl_idname = "texel_density.pack"
    bl_label = "Pack Islands (Keep Density)"
    bl_description = "Arrange the UV islands without scaling them, so the density stays as it is"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and context.mode in ("OBJECT", "EDIT_MESH")

    def execute(self, context):
        obj = context.object
        was_object = context.mode == "OBJECT"
        tool = context.scene.tool_settings
        sync = tool.use_uv_select_sync
        try:
            if was_object:
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
            tool.use_uv_select_sync = True
            bpy.ops.uv.pack_islands(scale=False, rotate=False, margin=0.005)
        finally:
            tool.use_uv_select_sync = sync
            if was_object and obj.mode == "EDIT":
                bpy.ops.object.mode_set(mode="OBJECT")
        return {"FINISHED"}


classes = (TD_OT_analyze, TD_OT_show, TD_OT_hide, TD_OT_set, TD_OT_copy, TD_OT_pack)
