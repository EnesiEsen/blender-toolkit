"""Operators of the kit."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import EnumProperty
from bpy.types import Operator

from . import cutters, finish, meshtools, stack


def selected_meshes(context):
    return [o for o in context.selected_objects if o.type == "MESH" and not cutters.is_cutter(o)]


class HS_Operator(Operator):
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"


class HS_OT_bevel(HS_Operator):
    bl_idname = "hardsurface_kit.bevel"
    bl_label = "Smart Bevel"
    bl_description = "Bevel the sharp edges with a modifier and fix the shading with a weighted normal modifier"

    @classmethod
    def poll(cls, context):
        return bool(selected_meshes(context)) and context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.hs_settings
        for obj in selected_meshes(context):
            if s.bevel_method == "WEIGHT" and s.mark_bevel:
                meshtools.mark_sharp(obj, s.shade_angle, bevel_weight=True)
            meshtools.shade_hard(obj, s.shade_angle)
            stack.smart_bevel(obj, s.bevel_width, s.bevel_segments, s.bevel_method, s.bevel_angle, s.harden_normals)
        return {"FINISHED"}


class HS_OT_mark_sharp(HS_Operator):
    bl_idname = "hardsurface_kit.mark_sharp"
    bl_label = "Mark Sharp Edges"
    bl_description = "Mark the edges that bend more than the smooth angle as sharp (and give them a bevel weight)"

    def execute(self, context):
        s = context.scene.hs_settings
        total = sum(meshtools.mark_sharp(o, s.shade_angle, s.mark_bevel) for o in selected_meshes(context))
        self.report({"INFO"}, rpt_("{count} edges marked sharp.").format(count=total))
        return {"FINISHED"}


class HS_OT_cutter_add(HS_Operator):
    bl_idname = "hardsurface_kit.cutter_add"
    bl_label = "Use Selected as Cutters"
    bl_description = "Cut the other selected meshes into the active object with boolean modifiers"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and len(selected_meshes(context)) > 1

    def execute(self, context):
        s = context.scene.hs_settings
        target = context.object
        count = 0
        for cutter in selected_meshes(context):
            if cutter is target:
                continue
            cutters.add_cutter(target, cutter, s.cut_operation, s.cut_solver)
            count += 1
        self.report({"INFO"}, rpt_("{count} cutters added.").format(count=count))
        return {"FINISHED"}


class HS_OT_cutter_new(HS_Operator):
    bl_idname = "hardsurface_kit.cutter_new"
    bl_label = "New Cutter"
    bl_description = "Add a box or cylinder cutter at the 3D cursor and cut it into the active object"

    kind: EnumProperty(name="Shape", default="BOX", items=(("BOX", "Box", ""), ("CYLINDER", "Cylinder", "")))

    def execute(self, context):
        s = context.scene.hs_settings
        target = context.object
        cutter = cutters.new_cutter(context, self.kind, s.cutter_size, context.scene.cursor.location)
        cutters.add_cutter(target, cutter, s.cut_operation, s.cut_solver)
        for obj in context.view_layer.objects:
            if obj is not None:
                obj.select_set(obj is target)
        return {"FINISHED"}


class HS_OT_cutter_apply(HS_Operator):
    bl_idname = "hardsurface_kit.cutter_apply"
    bl_label = "Apply Cutters"
    bl_description = "Make the cuts permanent and delete the cutter objects"

    @classmethod
    def poll(cls, context):
        return bool(selected_meshes(context)) and context.mode == "OBJECT"

    def execute(self, context):
        applied = sum(cutters.apply_cutters(context, o) for o in selected_meshes(context))
        self.report({"INFO"}, rpt_("{count} cuts applied.").format(count=applied))
        return {"FINISHED"}


class HS_OT_cutter_remove(HS_Operator):
    bl_idname = "hardsurface_kit.cutter_remove"
    bl_label = "Remove Cutters"
    bl_description = "Remove the cuts (and the cutter objects) from the selected meshes"

    @classmethod
    def poll(cls, context):
        return bool(selected_meshes(context)) and context.mode == "OBJECT"

    def execute(self, context):
        removed = sum(cutters.remove_cutters(o) for o in selected_meshes(context))
        self.report({"INFO"}, rpt_("{count} cuts removed.").format(count=removed))
        return {"FINISHED"}


class HS_OT_mirror(HS_Operator):
    bl_idname = "hardsurface_kit.mirror"
    bl_label = "Mirror"
    bl_description = "Mirror the object with a modifier"

    def execute(self, context):
        s = context.scene.hs_settings
        for obj in selected_meshes(context):
            stack.add_mirror(obj, (s.mirror_x, s.mirror_y, s.mirror_z), s.mirror_bisect)
        return {"FINISHED"}


class HS_OT_array(HS_Operator):
    bl_idname = "hardsurface_kit.array"
    bl_label = "Linear Array"
    bl_description = "Repeat the object along X with an array modifier"

    def execute(self, context):
        s = context.scene.hs_settings
        for obj in selected_meshes(context):
            stack.add_array(obj, s.array_count, s.array_offset)
        return {"FINISHED"}


class HS_OT_radial(HS_Operator):
    bl_idname = "hardsurface_kit.radial"
    bl_label = "Radial Array"
    bl_description = "Repeat the object around its own origin (bolts, vents, wheels)"

    def execute(self, context):
        s = context.scene.hs_settings
        for obj in selected_meshes(context):
            stack.add_radial(obj, s.radial_count, s.radial_axis)
        return {"FINISHED"}


class HS_OT_groove(HS_Operator):
    bl_idname = "hardsurface_kit.groove"
    bl_label = "Groove / Panel"
    bl_description = "Edit Mode: inset the selected faces and push them in (groove) or out (panel)"

    raised: bpy.props.BoolProperty(name="Raised Panel", default=False)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and context.mode == "EDIT_MESH"

    def execute(self, context):
        s = context.scene.hs_settings
        try:
            count = meshtools.groove(context.object, s.groove_width, s.groove_depth, self.raised)
        except ValueError:
            self.report({"ERROR"}, rpt_("Select the faces first."))
            return {"CANCELLED"}
        self.report({"INFO"}, rpt_("{count} faces done.").format(count=count))
        return {"FINISHED"}


class HS_OT_clean(HS_Operator):
    bl_idname = "hardsurface_kit.clean"
    bl_label = "Clean Mesh"
    bl_description = "Merge doubled vertices, remove loose ones and dissolve flat edges"

    @classmethod
    def poll(cls, context):
        return bool(selected_meshes(context)) and context.mode in ("OBJECT", "EDIT_MESH")

    def execute(self, context):
        s = context.scene.hs_settings
        targets = [context.object] if context.mode == "EDIT_MESH" else selected_meshes(context)
        before = after = 0
        for obj in targets:
            b, a = meshtools.clean(obj, s.merge_distance, s.dissolve_angle, s.join_quads)
            before, after = before + b, after + a
        self.report({"INFO"}, rpt_("Vertices: {before} to {after}.").format(before=before, after=after))
        return {"FINISHED"}


class HS_OT_finish(HS_Operator):
    bl_idname = "hardsurface_kit.finish"
    bl_label = "Apply Stack"
    bl_description = "Apply all modifiers (cutters, mirror, bevel ...) into a clean mesh and delete the helper objects"

    @classmethod
    def poll(cls, context):
        return bool(selected_meshes(context)) and context.mode == "OBJECT"

    def execute(self, context):
        done = 0
        for obj in selected_meshes(context):
            try:
                done += bool(finish.apply_stack(context, obj))
            except ValueError as e:
                self.report({"WARNING"}, str(e))
        self.report({"INFO"}, rpt_("{count} objects applied.").format(count=done))
        return {"FINISHED"}


classes = (
    HS_OT_bevel,
    HS_OT_mark_sharp,
    HS_OT_cutter_add,
    HS_OT_cutter_new,
    HS_OT_cutter_apply,
    HS_OT_cutter_remove,
    HS_OT_mirror,
    HS_OT_array,
    HS_OT_radial,
    HS_OT_groove,
    HS_OT_clean,
    HS_OT_finish,
)
