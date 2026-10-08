"""Sidebar panels (View3D > N panel > Scatter)."""

import textwrap

from bpy.types import Panel, UIList

from . import layers, place


def wrapped(layout, text, icon="NONE", width=34):
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


def active_category(context):
    scene = context.scene
    if 0 <= scene.sb_index < len(scene.sb_categories):
        return scene.sb_categories[scene.sb_index]
    return None


def needs_prepare(cat):
    """True when a model has scale or rotation on its object: the random sizes would stack on top of it."""
    if cat.collection is None:
        return False
    for ob in list(cat.collection.all_objects)[:50]:
        if any(abs(s - 1.0) > 1e-4 for s in ob.scale) or any(abs(r) > 1e-4 for r in ob.rotation_euler):
            return True
    return False


class SB_UL_categories(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon="OUTLINER_COLLECTION")
        count = len(item.collection.all_objects) if item.collection else 0
        row.label(text=str(count), icon="OBJECT_DATA")


class SB_PT_main(Panel):
    bl_label = "Scatter Brush"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scatter"

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        row = layout.row()
        row.template_list("SB_UL_categories", "", scene, "sb_categories", scene, "sb_index", rows=3)
        col = row.column(align=True)
        col.operator("scatter_brush.category_add", text="", icon="ADD")
        col.operator("scatter_brush.category_remove", text="", icon="REMOVE")
        cat = active_category(context)
        if cat is None:
            wrapped(layout, "Select your models (grass blades, rocks, trees) and press + to make a category.", "INFO")
            return
        layout.prop(cat, "collection", text="Models")
        row = layout.row(align=True)
        row.operator("scatter_brush.assets_add", icon="IMPORT")
        row.operator("scatter_brush.assets_prepare", icon="CHECKMARK")
        if needs_prepare(cat):
            box = layout.box()
            box.alert = True
            wrapped(box, "A model has scale or rotation on its object. Press Prepare Models.", "ERROR")
        if cat.collection is not None and not place.sources(cat):
            wrapped(layout, "The category is empty. Select objects, then Add Selected.", "ERROR")


class SB_PT_variation(Panel):
    bl_label = "Variation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scatter"
    bl_parent_id = "SB_PT_main"

    @classmethod
    def poll(cls, context):
        return active_category(context) is not None

    def draw(self, context):
        cat = active_category(context)
        layout = self.layout
        col = layout.column(align=True)
        col.prop(cat, "scale_min")
        col.prop(cat, "scale_max")
        col.prop(cat, "height_var", slider=True)
        col = layout.column(align=True)
        col.prop(cat, "yaw")
        col.prop(cat, "tilt")
        col.prop(cat, "align", slider=True)
        layout.prop(cat, "sink")
        row = layout.row(align=True)
        row.prop(cat, "seed")
        row.operator("scatter_brush.seed", text="", icon="FILE_REFRESH")


class SB_PT_brush(Panel):
    bl_label = "Click Brush"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scatter"
    bl_parent_id = "SB_PT_main"

    @classmethod
    def poll(cls, context):
        return active_category(context) is not None

    def draw(self, context):
        cat = active_category(context)
        layout = self.layout
        layout.operator("scatter_brush.paint", icon="BRUSH_DATA")
        col = layout.column(align=True)
        col.prop(cat, "radius")
        col.prop(cat, "count")
        col.prop(cat, "spacing", slider=True)
        col.prop(cat, "min_distance")
        col.prop(cat, "max_slope")
        layout.prop(context.scene, "sb_erase", toggle=True, icon="X")
        layout.operator("scatter_brush.clear", icon="TRASH")


class SB_PT_surface(Panel):
    bl_label = "Weight Paint Layers"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scatter"
    bl_parent_id = "SB_PT_main"

    @classmethod
    def poll(cls, context):
        return active_category(context) is not None

    def draw(self, context):
        scene = context.scene
        cat = active_category(context)
        ob = context.object
        layout = self.layout
        col = layout.column(align=True)
        col.prop(cat, "density")
        col.prop(cat, "falloff")
        col.prop(cat, "threshold", slider=True)
        col.prop(cat, "edge_scale", slider=True)
        col.prop(cat, "even")
        if cat.even:
            col.prop(cat, "min_distance")
        if ob is None or ob.type != "MESH":
            wrapped(layout, "Select the ground mesh to scatter on.", "INFO")
            return
        box = layout.box()
        box.label(text=ob.name, icon="MESH_DATA")
        if layers.transform_issue(ob):
            warn = box.box()
            warn.alert = True
            wrapped(warn, "The ground has scale or rotation: apply it (Ctrl+A) so objects keep their size.", "ERROR")
        row = box.row()
        row.template_list("MESH_UL_vgroups", "", ob, "vertex_groups", ob.vertex_groups, "active_index", rows=3)
        side = row.column(align=True)
        side.operator("object.vertex_group_add", text="", icon="ADD")
        box.operator("scatter_brush.layer_add", icon="PARTICLES")
        for index, layer, mod in layers.layers_of(ob):
            owner = layers.find_category(scene, layer.cat_id)
            card = layout.box()
            row = card.row(align=True)
            row.label(text=owner.name if owner else "(category removed)", icon="OUTLINER_COLLECTION")
            if mod is not None:
                row.prop(mod, "show_viewport", text="", emboss=False)
            row.operator("scatter_brush.layer_paint", text="", icon="WPAINT_HLT").index = index
            row.operator("scatter_brush.layer_bake", text="", icon="OBJECT_DATA").index = index
            row.operator("scatter_brush.layer_remove", text="", icon="X").index = index
            card.prop_search(layer, "group", ob, "vertex_groups", text="Weights")
            card.prop(layer, "density")
            if mod is None:
                card.alert = True
                card.label(text="The modifier is missing. Remove the layer.", icon="ERROR")


classes = (SB_UL_categories, SB_PT_main, SB_PT_variation, SB_PT_brush, SB_PT_surface)
