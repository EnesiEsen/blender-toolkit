"""Operators: rig check and fix, and the three exports."""

from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import Operator

from . import export, rig


def selected_armatures(context):
    """Selected armatures plus the armatures that the selected skinned meshes use."""
    found = {}
    for ob in context.selected_objects:
        if ob.type == "ARMATURE":
            found[ob.name] = ob
        elif ob.type == "MESH":
            for modifier in ob.modifiers:
                if modifier.type == "ARMATURE" and modifier.object:
                    found[modifier.object.name] = modifier.object
    return list(found.values())


def refresh(context):
    context.scene.ue_issues.clear()
    for armature in selected_armatures(context):
        for found in rig.scan(armature):
            item = context.scene.ue_issues.add()
            item.severity, item.code, item.object_name, item.message = (
                found["severity"],
                found["code"],
                found["object"],
                found["message"],
            )
    return len(context.scene.ue_issues)


class UE_OT_check(Operator):
    bl_idname = "ue5_bridge.check"
    bl_label = "Check Skeleton"
    bl_description = "List what would go wrong when the selected skeleton is imported into Unreal Engine 5"
    bl_options = {"REGISTER"}

    def execute(self, context):
        count = refresh(context)
        self.report(
            {"INFO"}, rpt_("{count} problems found.").format(count=count) if count else rpt_("No problems found.")
        )
        return {"FINISHED"}


class UE_OT_fix_root(Operator):
    bl_idname = "ue5_bridge.fix_root"
    bl_label = "Add Root Bone"
    bl_description = "Give the selected skeletons exactly one root bone (the export does this on its copy anyway)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and bool(selected_armatures(context))

    def execute(self, context):
        for armature in selected_armatures(context):
            rig.ensure_single_root(context, armature, context.scene.ue_settings.root_name)
        refresh(context)
        return {"FINISHED"}


class ExportOperator(Operator):
    """Shared behaviour: run an export function and report what was written."""

    bl_options = {"REGISTER"}
    kind = ""

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and len(context.selected_objects) > 0

    def objects(self, context):
        raise NotImplementedError

    def run(self, context, objects, s):
        raise NotImplementedError

    def execute(self, context):
        s = context.scene.ue_settings
        selected, active = list(context.selected_objects), context.view_layer.objects.active
        try:
            paths = self.run(context, self.objects(context), s)
        except (export.ExportError, ValueError) as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        finally:  # the export selects its temporary copies: give the user back the selection
            for other in list(context.view_layer.objects):
                if other is not None:
                    other.select_set(other in selected)
            context.view_layer.objects.active = active
        if not paths:
            self.report({"WARNING"}, rpt_("Nothing to export in the selection."))
            return {"CANCELLED"}
        self.report(
            {"INFO"}, rpt_("Exported {count} files to {folder}").format(count=len(paths), folder=paths[0].parent)
        )
        return {"FINISHED"}


class UE_OT_export_static(ExportOperator):
    bl_idname = "ue5_bridge.export_static"
    bl_label = "Export Static Meshes"
    bl_description = "One FBX per selected mesh, centered at the origin, with the UE5 settings"

    def objects(self, context):
        return list(context.selected_objects)

    def run(self, context, objects, s):
        return export.export_static(context, objects, s)


class UE_OT_export_skeletal(ExportOperator):
    bl_idname = "ue5_bridge.export_skeletal"
    bl_label = "Export Skeletal Meshes"
    bl_description = "The skinned meshes of the selected skeletons (modular parts are exported one by one)"

    def objects(self, context):
        return selected_armatures(context)

    def run(self, context, objects, s):
        return export.export_skeletal(context, objects, s)


class UE_OT_export_animations(ExportOperator):
    bl_idname = "ue5_bridge.export_animations"
    bl_label = "Export Animations"
    bl_description = "Every action or NLA track of the selected skeletons as its own FBX, optionally with root motion"

    def objects(self, context):
        return selected_armatures(context)

    def run(self, context, objects, s):
        return export.export_animations(context, objects, s)


classes = (UE_OT_check, UE_OT_fix_root, UE_OT_export_static, UE_OT_export_skeletal, UE_OT_export_animations)
