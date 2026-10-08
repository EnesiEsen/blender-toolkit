"""Operators of the kit."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import Operator

from . import bind, builder, checker, ik, rename, retarget


def active_armature(context):
    ob = context.object
    return ob if ob is not None and ob.type == "ARMATURE" else None


class GR_OT_markers(Operator):
    bl_idname = "game_rig.markers"
    bl_label = "Create Markers"
    bl_description = "Place landmark markers around the selected character mesh; move them onto the joints"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type == "MESH" for o in context.selected_objects) and context.mode == "OBJECT"

    def execute(self, context):
        try:
            height = builder.create_markers(context, context.selected_objects)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, rpt_("Markers created for a character {height:.2f} m tall.").format(height=height))
        return {"FINISHED"}


class GR_OT_build(Operator):
    bl_idname = "game_rig.build"
    bl_label = "Build Rig"
    bl_description = "Build the UE5 mannequin skeleton from the markers (the right side is mirrored from the left)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.gr_settings
        try:
            points = builder.read_markers()
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        rig = builder.build_rig(context, s.rig_name or "Rig", points, s.ik_bones, s.fingers)
        self.report(
            {"INFO"}, rpt_("Built '{name}' with {count} bones.").format(name=rig.name, count=len(rig.data.bones))
        )
        return {"FINISHED"}


class GR_OT_bind(Operator):
    bl_idname = "game_rig.bind"
    bl_label = "Bind Meshes"
    bl_description = "Skin the selected meshes to the active rig with automatic weights, then limit and normalize them"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_armature(context) is not None and any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):
        rig = active_armature(context)
        meshes = [o for o in context.selected_objects if o.type == "MESH"]
        used = bind.bind(context, rig, meshes, context.scene.gr_settings.max_influences)
        if not used:
            self.report({"ERROR"}, rpt_("Automatic weights failed: check that the meshes are closed and clean."))
            return {"CANCELLED"}
        if "ARMATURE_ENVELOPE" in used.values():
            self.report({"WARNING"}, rpt_("Heat weights failed for some meshes: envelope weights were used instead."))
        else:
            self.report({"INFO"}, rpt_("{count} meshes bound.").format(count=len(used)))
        return {"FINISHED"}


class GR_OT_rename(Operator):
    bl_idname = "game_rig.rename"
    bl_label = "Rename to UE5"
    bl_description = "Rename the bones of the active rig (Mixamo, Rigify, generic) to the UE5 mannequin names"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_armature(context) is not None and context.mode == "OBJECT"

    def execute(self, context):
        sheet = bpy.data.texts.get(context.scene.gr_settings.mapping_sheet)
        try:
            renames, unmatched = rename.rename_rig(active_armature(context), sheet)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report(
            {"WARNING" if unmatched else "INFO"},
            rpt_("{done} bones renamed, {left} not matched.").format(done=len(renames), left=len(unmatched)),
        )
        return {"FINISHED"}


class GR_OT_mapping_sheet(Operator):
    bl_idname = "game_rig.mapping_sheet"
    bl_label = "Create Mapping Sheet"
    bl_description = "Create a text block listing the bones that could not be matched, to fill in by hand"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_armature(context) is not None

    def execute(self, context):
        text, count = rename.mapping_sheet(active_armature(context), context.scene.gr_settings.mapping_sheet)
        self.report({"INFO"}, rpt_("Sheet '{name}': {count} bones to fill in.").format(name=text.name, count=count))
        return {"FINISHED"}


class GR_OT_ik_setup(Operator):
    bl_idname = "game_rig.ik_setup"
    bl_label = "Set Up IK"
    bl_description = (
        "Add IK to the legs and arms: target bones, knee and elbow poles, and rotation that follows the target"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_armature(context) is not None and context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.gr_settings
        errors = ik.setup(context, active_armature(context), s.ik_legs, s.ik_arms)
        if not errors:
            self.report({"ERROR"}, rpt_("No UE5 leg or arm bones were found: build or rename the rig first."))
            return {"CANCELLED"}
        self.report({"INFO"}, rpt_("IK set up on {count} limbs.").format(count=len(errors)))
        return {"FINISHED"}


class GR_OT_ik_remove(Operator):
    bl_idname = "game_rig.ik_remove"
    bl_label = "Remove IK"
    bl_description = "Remove the IK constraints and the pole bones"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_armature(context) is not None and context.mode == "OBJECT"

    def execute(self, context):
        self.report(
            {"INFO"}, rpt_("{count} constraints removed.").format(count=ik.remove(context, active_armature(context)))
        )
        return {"FINISHED"}


class GR_OT_retarget(Operator):
    bl_idname = "game_rig.retarget"
    bl_label = "Retarget Animation"
    bl_description = "Copy the animation of the source rig onto the active rig (bones are matched by their UE5 names)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        s = context.scene.gr_settings
        return active_armature(context) is not None and s.source_rig is not None and context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.gr_settings
        sheet = rename.read_sheet(bpy.data.texts.get(s.mapping_sheet))
        try:
            action, count = retarget.retarget(context, s.source_rig, active_armature(context), s.step, sheet)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, rpt_("'{name}': {count} bones copied.").format(name=action.name, count=count))
        return {"FINISHED"}


class GR_OT_check(Operator):
    bl_idname = "game_rig.check"
    bl_label = "Check Skeleton"
    bl_description = "Compare the active rig with the UE5 mannequin"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return active_armature(context) is not None

    def execute(self, context):
        context.scene.gr_issues.clear()
        for found in checker.check(active_armature(context)):
            item = context.scene.gr_issues.add()
            item.severity, item.code, item.message = found["severity"], found["code"], found["message"]
        count = len(context.scene.gr_issues)
        self.report(
            {"INFO"},
            rpt_("{count} findings.").format(count=count) if count else rpt_("The skeleton matches the mannequin."),
        )
        return {"FINISHED"}


classes = (
    GR_OT_markers,
    GR_OT_build,
    GR_OT_bind,
    GR_OT_rename,
    GR_OT_mapping_sheet,
    GR_OT_ik_setup,
    GR_OT_ik_remove,
    GR_OT_retarget,
    GR_OT_check,
)
