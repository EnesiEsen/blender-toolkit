"""Sidebar panel: layer list, layer settings, options and the live sliders of the material."""
import bpy
from bpy.app.translations import pgettext_iface as iface_
from bpy.types import Panel, UIList

from . import core
from .shader import ENHANCER_PANEL, by_id, group_node_of, slider_key


class TB_UL_layers(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.label(text=f"{index + 1}. {item.name}", icon="ERROR" if not item.folder else "TEXTURE")
        row.label(text=iface_("Base") if index == 0 else (item.mask or iface_("no mask")), icon="GROUP_VERTEX")


class TB_PT_panel(Panel):
    bl_label = "Terrain Blend"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Terrain Blend"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def draw(self, context):
        ob = context.object
        layout = self.layout
        row = layout.row()
        row.template_list("TB_UL_layers", "", ob, "tb_layers", ob, "tb_index", rows=6)
        col = row.column(align=True)
        col.operator("terrain_blend.layer_add", icon="ADD", text="")
        col.operator("terrain_blend.layer_remove", icon="REMOVE", text="")
        col.separator()
        col.operator("terrain_blend.layer_move", icon="TRIA_UP", text="").direction = -1
        col.operator("terrain_blend.layer_move", icon="TRIA_DOWN", text="").direction = 1
        col = layout.column(align=True)
        col.operator("terrain_blend.from_library", icon="FILE_FOLDER")
        col.operator("terrain_blend.from_groups", icon="GROUP_VERTEX")

        if ob.tb_layers and 0 <= ob.tb_index < len(ob.tb_layers):
            layer = ob.tb_layers[ob.tb_index]
            box = layout.box()
            box.prop(layer, "name")
            box.prop(layer, "folder")
            if ob.tb_index == 0:
                box.label(text="The base layer covers everything and needs no mask.", icon="INFO")
            else:
                box.prop_search(layer, "mask", ob, "vertex_groups", icon="GROUP_VERTEX")
                box.operator("terrain_blend.auto_mask", icon="MOD_MASK")

        box = layout.box()
        box.prop(ob.tb_settings, "lite")
        box.prop(ob.tb_settings, "enhancer")
        layout.operator("terrain_blend.build", icon="NODE_MATERIAL")

        tree = core.group_tree(ob)
        mat = bpy.data.materials.get(core.material_name(ob))
        group = group_node_of(mat, tree) if tree else None
        if not group:
            return
        self.draw_warnings(layout, ob, tree)
        self.draw_sliders(layout, ob, tree, group)

    def draw_warnings(self, layout, ob, tree):
        textures = tree.get("tb_textures", 0)
        if core.gpu_backend() == "OPENGL" and textures > core.OPENGL_TEXTURE_LIMIT:
            warn = layout.box()
            warn.alert = True
            warn.label(text=iface_("{count} textures: EEVEE on OpenGL shows pink above {limit}.").format(
                count=textures, limit=core.OPENGL_TEXTURE_LIMIT), icon="ERROR")
            warn.label(text=iface_("Turn on Lite Preview, use Cycles, or the Vulkan backend (Blender 5.2+)."))
        if len(ob.tb_layers) > core.EEVEE_LAYER_LIMIT:
            warn = layout.box()
            warn.alert = True
            warn.label(text=iface_("EEVEE shows at most {limit} layers (GPU limit).").format(
                limit=core.EEVEE_LAYER_LIMIT), icon="ERROR")
            warn.label(text=iface_("Cycles has no limit; use it for the final render."))

    def draw_sliders(self, layout, ob, tree, group):
        box = layout.box()
        box.label(text="Live Settings", icon="PREFERENCES")
        selected = ob.tb_index
        for item in tree.interface.items_tree:
            if item.item_type != "SOCKET" or item.in_out != "INPUT":
                continue
            key = slider_key(item)
            if key[0] == "L" and key[1] != selected:
                continue
            label = iface_(item.name)
            if key[0] == "L":
                label = f"{ob.tb_layers[selected].name}: {label}"
            elif key[0] == "E":
                label = f"{ENHANCER_PANEL}: {label}"
            box.prop(by_id(group.inputs, item.identifier), "default_value", text=label)


classes = (TB_UL_layers, TB_PT_panel)
