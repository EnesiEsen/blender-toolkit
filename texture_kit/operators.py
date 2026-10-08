"""Operators: Doctor, texture set export, channel packer and normal map flip."""

from pathlib import Path

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import IntProperty
from bpy.types import Operator

from . import doctor, export, imaging


def selected_meshes(context):
    return [o for o in context.selected_objects if o.type == "MESH"]


class TK_OT_scan(Operator):
    bl_idname = "texture_kit.scan"
    bl_label = "Check Textures"
    bl_description = "Look for textures that Unreal would import wrongly: color space, size, missing data"
    bl_options = {"REGISTER"}

    def execute(self, context):
        objects = selected_meshes(context)
        if not objects:
            self.report({"ERROR"}, rpt_("Select at least one mesh."))
            return {"CANCELLED"}
        context.scene.tk_issues.clear()
        for found in doctor.scan(objects, int(context.scene.tk_settings.doctor_max)):
            item = context.scene.tk_issues.add()
            item.severity, item.code, item.message = found["severity"], found["code"], found["message"]
            item.image_name, item.fixable = found["image"], found["fixable"]
        count = len(context.scene.tk_issues)
        self.report(
            {"INFO"}, rpt_("{count} problems found.").format(count=count) if count else rpt_("No problems found.")
        )
        return {"FINISHED"}


class TK_OT_fix(Operator):
    bl_idname = "texture_kit.fix"
    bl_label = "Fix"
    bl_description = "Fix this problem"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty()

    def execute(self, context):
        item = context.scene.tk_issues[self.index]
        try:
            doctor.fix(item.image_name, item.code, bpy.data.images)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        context.scene.tk_issues.remove(self.index)
        return {"FINISHED"}


class TK_OT_fix_all(Operator):
    bl_idname = "texture_kit.fix_all"
    bl_label = "Fix All"
    bl_description = "Fix every problem that has an automatic fix"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        issues = context.scene.tk_issues
        fixed = 0
        for index in reversed(range(len(issues))):
            if issues[index].fixable:
                doctor.fix(issues[index].image_name, issues[index].code, bpy.data.images)
                issues.remove(index)
                fixed += 1
        self.report({"INFO"}, rpt_("{fixed} fixed, {left} left.").format(fixed=fixed, left=len(issues)))
        return {"FINISHED"}


class TK_OT_export(Operator):
    bl_idname = "texture_kit.export"
    bl_label = "Export for Unreal"
    bl_description = "Write T_<name>_BC, _N, _ORM and _E of the active object's materials, sized for Unreal"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        try:
            written = export.export_object(context.object, context.scene.tk_settings)
        except export.ExportError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report(
            {"INFO"}, rpt_("Exported {count} files to {folder}").format(count=len(written), folder=written[0].parent)
        )
        return {"FINISHED"}


class TK_OT_pack_preset(Operator):
    bl_idname = "texture_kit.pack_preset"
    bl_label = "Set Up ORM"
    bl_description = "Occlusion in red, roughness in green, metallic in blue"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.tk_settings
        for slot, value in ((s.slot_r, 1.0), (s.slot_g, 0.5), (s.slot_b, 0.0), (s.slot_a, 1.0)):
            slot.image, slot.channel, slot.invert, slot.value = None, "R", False, value
        s.pack_name = "T_Packed_ORM"
        return {"FINISHED"}


class TK_OT_pack(Operator):
    bl_idname = "texture_kit.pack"
    bl_label = "Pack Channels"
    bl_description = "Combine four channels of other images into one new image (the sources stay untouched)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.tk_settings
        slots = [
            dict(image=sl.image, channel=sl.channel, invert=sl.invert, value=sl.value)
            for sl in (s.slot_r, s.slot_g, s.slot_b, s.slot_a)
        ]
        size = None if s.pack_size == "AUTO" else (int(s.pack_size), int(s.pack_size))
        try:
            data = imaging.pack(slots, size)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        image = imaging.create(s.pack_name or "T_Packed", data)
        if s.pack_save:
            if not s.export_dir:
                self.report({"ERROR"}, rpt_("Choose an export folder first."))
                return {"CANCELLED"}
            folder = Path(bpy.path.abspath(s.export_dir))
            folder.mkdir(parents=True, exist_ok=True)
            imaging.save(image, folder / (image.name + export.EXT[s.file_format]), s.file_format)
        self.report(
            {"INFO"}, rpt_("Created '{name}' ({w} x {h}).").format(name=image.name, w=image.size[0], h=image.size[1])
        )
        return {"FINISHED"}


class TK_OT_flip_normal(Operator):
    bl_idname = "texture_kit.flip_normal"
    bl_label = "Flip Green Channel"
    bl_description = "New normal map with the green channel inverted: OpenGL to DirectX and back"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.tk_settings.normal_image is not None

    def execute(self, context):
        s = context.scene.tk_settings
        source = s.normal_image
        try:
            data = imaging.read(source)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        data[..., 1] = 1.0 - data[..., 1]
        image = imaging.create(f"{source.name}_flipped", data)
        if s.pack_save and s.export_dir:
            folder = Path(bpy.path.abspath(s.export_dir))
            folder.mkdir(parents=True, exist_ok=True)
            imaging.save(image, folder / (image.name + export.EXT[s.file_format]), s.file_format)
        self.report({"INFO"}, rpt_("Created '{name}'.").format(name=image.name))
        return {"FINISHED"}


classes = (TK_OT_scan, TK_OT_fix, TK_OT_fix_all, TK_OT_export, TK_OT_pack_preset, TK_OT_pack, TK_OT_flip_normal)
