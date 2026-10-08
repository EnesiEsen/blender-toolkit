"""Operators: create, remove, show or hide, check and fix collision shapes."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import IntProperty
from bpy.types import Operator

from . import core


def selected_meshes(context):
    return [o for o in context.selected_objects if o.type == "MESH" and not core.is_shape(o)]


class CM_OT_create(Operator):
    bl_idname = "collision_maker.create"
    bl_label = "Create Collision"
    bl_description = "Create collision shapes for the selected meshes, named for Unreal and parented to the mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(selected_meshes(context)) and context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.cm_settings
        made, problems = [], []
        for obj in selected_meshes(context):
            try:
                made += core.create(context, obj, s)
            except ValueError as e:
                problems.append(str(e))
        if problems and not made:
            self.report({"ERROR"}, problems[0])
            return {"CANCELLED"}
        self.report({"INFO"}, rpt_("{count} collision shapes created.").format(count=len(made)))
        return {"FINISHED"}


class CM_OT_remove(Operator):
    bl_idname = "collision_maker.remove"
    bl_label = "Remove Collision"
    bl_description = "Delete the collision shapes of the selected meshes"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(selected_meshes(context)) and context.mode == "OBJECT"

    def execute(self, context):
        removed = sum(core.remove_shapes(o) for o in selected_meshes(context))
        self.report({"INFO"}, rpt_("{count} collision shapes removed.").format(count=removed))
        return {"FINISHED"}


class CM_OT_toggle(Operator):
    bl_idname = "collision_maker.toggle"
    bl_label = "Show / Hide Collision"
    bl_description = "Show or hide every collision shape in the scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        shapes = [o for o in context.scene.objects if core.is_shape(o)]
        hide = any(not o.hide_get() for o in shapes)
        for shape in shapes:
            shape.hide_set(hide)
        return {"FINISHED"}


class CM_OT_check(Operator):
    bl_idname = "collision_maker.check"
    bl_label = "Check Collision"
    bl_description = (
        "Find shapes Unreal would ignore or distort: orphans, non-convex hulls, too many vertices, bad names"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        context.scene.cm_issues.clear()
        for found in core.scan(list(context.scene.objects)):
            item = context.scene.cm_issues.add()
            item.severity, item.code, item.message = found["severity"], found["code"], found["message"]
            item.object_name, item.fixable = found["object"], found["fixable"]
        count = len(context.scene.cm_issues)
        self.report(
            {"INFO"}, rpt_("{count} problems found.").format(count=count) if count else rpt_("No problems found.")
        )
        return {"FINISHED"}


class CM_OT_fix(Operator):
    bl_idname = "collision_maker.fix"
    bl_label = "Fix"
    bl_description = "Replace the shape by its convex hull"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty()

    def execute(self, context):
        item = context.scene.cm_issues[self.index]
        shape = bpy.data.objects.get(item.object_name)
        if shape is None:
            self.report({"ERROR"}, rpt_("The object no longer exists."))
            return {"CANCELLED"}
        core.fix(shape, context.scene.cm_settings.max_vertices)
        context.scene.cm_issues.remove(self.index)
        return {"FINISHED"}


classes = (CM_OT_create, CM_OT_remove, CM_OT_toggle, CM_OT_check, CM_OT_fix)
