"""Layer list operators and the Build operator."""

import os

from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator

from . import core, maps


def _layers(ob):
    return ob.tb_layers


class TB_OT_layer_add(Operator):
    bl_idname = "terrain_blend.layer_add"
    bl_label = "Add Layer"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob = context.object
        layer = _layers(ob).add()
        layer.name = "Base" if len(_layers(ob)) == 1 else f"Layer {len(_layers(ob))}"
        ob.tb_index = len(_layers(ob)) - 1
        return {"FINISHED"}


class TB_OT_layer_remove(Operator):
    bl_idname = "terrain_blend.layer_remove"
    bl_label = "Remove Layer"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob = context.object
        if _layers(ob):
            _layers(ob).remove(ob.tb_index)
            ob.tb_index = max(0, min(ob.tb_index, len(_layers(ob)) - 1))
        return {"FINISHED"}


class TB_OT_layer_move(Operator):
    bl_idname = "terrain_blend.layer_move"
    bl_label = "Move Layer"
    bl_options = {"REGISTER", "UNDO"}
    direction: IntProperty(default=-1)

    def execute(self, context):
        ob = context.object
        target = ob.tb_index + self.direction
        if 0 <= target < len(_layers(ob)):
            _layers(ob).move(ob.tb_index, target)
            ob.tb_index = target
        return {"FINISHED"}


class TB_OT_from_groups(Operator):
    bl_idname = "terrain_blend.from_groups"
    bl_label = "Add From Vertex Groups"
    bl_description = "Add a base layer and one layer for every vertex group that is not used as a mask yet"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob = context.object
        if not _layers(ob):
            _layers(ob).add().name = "Base"
        used = {layer.mask for layer in _layers(ob)}
        for group in ob.vertex_groups:
            if group.name not in used:
                layer = _layers(ob).add()
                layer.name = layer.mask = group.name
        return {"FINISHED"}


class TB_OT_from_library(Operator):
    bl_idname = "terrain_blend.from_library"
    bl_label = "Add From Texture Library"
    bl_description = (
        "Pick a folder that contains one sub-folder per texture set (for example your ambientCG downloads). "
        "Every sub-folder with a color map becomes a layer; a vertex group with the same name becomes its mask"
    )
    bl_options = {"REGISTER", "UNDO"}

    directory: StringProperty(subtype="DIR_PATH")

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        ob = context.object
        root = bpy_abspath(self.directory)
        if not os.path.isdir(root):
            self.report({"ERROR"}, rpt_("Folder not found."))
            return {"CANCELLED"}
        sets = maps.find_sets(root)
        if not sets:
            self.report({"ERROR"}, rpt_("No texture set found: each sub-folder needs a Color/Albedo/Diffuse file."))
            return {"CANCELLED"}
        known = {layer.folder for layer in _layers(ob)}
        groups = {g.name.lower(): g.name for g in ob.vertex_groups}
        added = 0
        for name, path in sets:
            if path in known or path + os.sep in known:
                continue
            layer = _layers(ob).add()
            layer.name = name
            layer.folder = path
            layer.mask = "" if len(_layers(ob)) == 1 else groups.get(name.lower(), "")
            added += 1
        ob.tb_index = max(0, len(_layers(ob)) - 1)
        self.report({"INFO"}, rpt_("{count} layers added; set the mask of the ones marked in red.").format(count=added))
        return {"FINISHED"}


def bpy_abspath(path):
    import bpy

    return os.path.normpath(bpy.path.abspath(path))


class TB_OT_build(Operator):
    bl_idname = "terrain_blend.build"
    bl_label = "Build / Update Material"
    bl_description = "Rebuild the material and the mask modifier from the layers; slider values are kept"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        try:
            self.report({"INFO"}, core.build(context.object))
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


classes = (TB_OT_layer_add, TB_OT_layer_remove, TB_OT_layer_move, TB_OT_from_groups, TB_OT_from_library, TB_OT_build)
