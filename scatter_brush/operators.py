"""Operators: categories, assets, surface layers and the modal click brush."""

import random

import bpy
import gpu
import numpy as np
from bpy.app.translations import pgettext_iface as iface_
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import BoolProperty, IntProperty
from bpy.types import Operator, SpaceView3D
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

from . import layers, place

BAKE_LIMIT = 20000
UI_REGIONS = {"UI", "TOOLS", "HEADER", "TOOL_HEADER", "FOOTER", "NAVIGATION_BAR", "ASSET_SHELF", "ASSET_SHELF_HEADER"}


def active_category(context):
    scene = context.scene
    if 0 <= scene.sb_index < len(scene.sb_categories):
        return scene.sb_categories[scene.sb_index]
    return None


def has_category(context):
    cat = active_category(context)
    return cat is not None


def base_name(name):
    """'Rock.003' -> 'Rock', 'Rock_12' -> 'Rock'."""
    stem = name.rsplit(".", 1)[0] if name.rsplit(".", 1)[-1].isdigit() else name
    return stem.rstrip("0123456789_ ") or stem


def move_objects(objects, collection):
    for ob in objects:
        for other in list(ob.users_collection):
            if other is not collection:
                other.objects.unlink(ob)
        if ob.name not in collection.objects:
            collection.objects.link(ob)


class SB_OT_category_add(Operator):
    bl_idname = "scatter_brush.category_add"
    bl_label = "New Category from Selection"
    bl_description = "Make a category from the selected models. They move into their own collection"
    bl_options = {"REGISTER", "UNDO"}

    hide: BoolProperty(
        name="Hide the Models",
        default=True,
        description="Exclude the asset collection from the view layer (it keeps working as a source)",
    )

    def execute(self, context):
        scene = context.scene
        chosen = list(context.selected_objects)
        cat = scene.sb_categories.add()
        cat.uid = scene.sb_next_uid
        scene.sb_next_uid += 1
        names = {c.name for c in scene.sb_categories if c is not cat}
        stem = base_name(chosen[0].name) if chosen else "Category"
        cat.name, n = stem, 1
        while cat.name in names:
            n += 1
            cat.name = f"{stem} {n}"
        collection = bpy.data.collections.new(f"{cat.name} Assets")
        scene.collection.children.link(collection)
        move_objects(chosen, collection)
        cat.collection = collection
        scene.sb_index = len(scene.sb_categories) - 1
        if self.hide:
            layer_collection = context.view_layer.layer_collection.children.get(collection.name)
            if layer_collection is not None:
                layer_collection.exclude = True
        self.report({"INFO"}, rpt_("Category '{name}': {count} models.").format(name=cat.name, count=len(chosen)))
        return {"FINISHED"}


class SB_OT_category_remove(Operator):
    bl_idname = "scatter_brush.category_remove"
    bl_label = "Remove Category"
    bl_description = "Delete the category and its surface layers. The models and placed objects stay"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return has_category(context)

    def execute(self, context):
        scene = context.scene
        cat = active_category(context)
        for ob in scene.objects:
            for index in reversed(range(len(ob.sb_layers))):
                if ob.sb_layers[index].cat_id == cat.uid:
                    layers.remove_layer(ob, index)
        scene.sb_categories.remove(scene.sb_index)
        scene.sb_index = max(0, min(scene.sb_index, len(scene.sb_categories) - 1))
        return {"FINISHED"}


class SB_OT_assets_add(Operator):
    bl_idname = "scatter_brush.assets_add"
    bl_label = "Add Selected"
    bl_description = "Move the selected objects into the category's asset collection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        cat = active_category(context)
        return cat is not None and cat.collection is not None and bool(context.selected_objects)

    def execute(self, context):
        cat = active_category(context)
        chosen = list(context.selected_objects)
        move_objects(chosen, cat.collection)
        self.report({"INFO"}, rpt_("{count} models added to '{name}'.").format(count=len(chosen), name=cat.name))
        return {"FINISHED"}


class SB_OT_assets_prepare(Operator):
    bl_idname = "scatter_brush.assets_prepare"
    bl_label = "Prepare Models"
    bl_description = (
        "Apply scale and rotation of the category's models and put their origin at the bottom center, "
        "so they stand on the ground and the random scale works"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        cat = active_category(context)
        return cat is not None and cat.collection is not None

    def execute(self, context):
        cat = active_category(context)
        done, skipped = 0, []
        for ob in place.sources(cat):
            me = ob.data if ob.type == "MESH" else None
            if me is None or me.users > 1 or ob.parent is not None or me.library is not None:
                skipped.append(ob.name)
                continue
            basis = ob.matrix_basis.copy()
            basis.translation = (0.0, 0.0, 0.0)
            me.transform(basis)
            ob.matrix_basis = Matrix.Translation(ob.location)
            if len(me.vertices):
                co = np.empty(len(me.vertices) * 3, dtype=np.float32)
                me.vertices.foreach_get("co", co)
                co = co.reshape(-1, 3)
                low, high = co.min(axis=0), co.max(axis=0)
                shift = Vector(((low[0] + high[0]) / 2.0, (low[1] + high[1]) / 2.0, low[2]))
                me.transform(Matrix.Translation(-shift))
                ob.location += shift
            me.update()
            done += 1
        message = rpt_("{count} models prepared.").format(count=done)
        if skipped:
            message += rpt_(" Skipped (shared mesh, parent or not a mesh): {names}.").format(
                names=", ".join(skipped[:5])
            )
        self.report({"INFO"} if done else {"WARNING"}, message)
        return {"FINISHED"}


class SB_OT_layer_add(Operator):
    bl_idname = "scatter_brush.layer_add"
    bl_label = "Add Surface Layer"
    bl_description = "Scatter the active category over the active mesh, painted by its active vertex group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ob = context.object
        cat = active_category(context)
        return ob is not None and ob.type == "MESH" and cat is not None

    def execute(self, context):
        ob = context.object
        cat = active_category(context)
        if cat.collection is None or not place.sources(cat):
            self.report({"ERROR"}, rpt_("The category has no models. Add some first."))
            return {"CANCELLED"}
        group = ob.vertex_groups.active.name if ob.vertex_groups.active else ""
        layers.add_layer(ob, cat, group, context.scene)
        if layers.transform_issue(ob):
            self.report(
                {"WARNING"}, rpt_("The ground has scale or rotation: apply it (Ctrl+A) so objects keep their size.")
            )
        if group:
            self.report(
                {"INFO"}, rpt_("'{cat}' scatters where '{group}' is painted.").format(cat=cat.name, group=group)
            )
        else:
            self.report(
                {"INFO"}, rpt_("'{cat}' covers the whole surface. Add a vertex group to limit it.").format(cat=cat.name)
            )
        return {"FINISHED"}


class _LayerOperator(Operator):
    index: IntProperty()

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def layer(self, context):
        ob = context.object
        if not 0 <= self.index < len(ob.sb_layers):
            self.report({"ERROR"}, rpt_("The layer no longer exists."))
            return None
        return ob.sb_layers[self.index]


class SB_OT_layer_remove(_LayerOperator):
    bl_idname = "scatter_brush.layer_remove"
    bl_label = "Remove Layer"
    bl_description = "Remove this surface layer (the vertex group stays)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if self.layer(context) is None:
            return {"CANCELLED"}
        layers.remove_layer(context.object, self.index)
        return {"FINISHED"}


class SB_OT_layer_paint(_LayerOperator):
    bl_idname = "scatter_brush.layer_paint"
    bl_label = "Paint Weights"
    bl_description = "Switch to Weight Paint with this layer's vertex group (it is created when missing)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        layer = self.layer(context)
        if layer is None:
            return {"CANCELLED"}
        ob = context.object
        group = ob.vertex_groups.get(layer.group) if layer.group else None
        if group is None:
            cat = layers.find_category(context.scene, layer.cat_id)
            group = ob.vertex_groups.new(name=layer.group or (cat.name if cat else "Scatter"))
            layer.group = group.name
        ob.vertex_groups.active_index = group.index
        context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
        return {"FINISHED"}


class SB_OT_layer_bake(_LayerOperator):
    bl_idname = "scatter_brush.layer_bake"
    bl_label = "Bake to Objects"
    bl_description = "Turn this layer's instances into real objects you can move, delete or export one by one"
    bl_options = {"REGISTER", "UNDO"}

    keep: BoolProperty(name="Keep the Layer", default=False, description="Keep the live layer as well")

    def execute(self, context):
        layer = self.layer(context)
        if layer is None:
            return {"CANCELLED"}
        ob = context.object
        cat = layers.find_category(context.scene, layer.cat_id)
        if cat is None:
            self.report({"ERROR"}, rpt_("The layer's category was removed."))
            return {"CANCELLED"}
        out = place.output_collection(context.scene, cat)
        try:
            made = layers.bake_layer(context, ob, self.index, out, self.keep, limit=BAKE_LIMIT)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        for copy in made:
            copy["sb_placed"] = 1
            copy["sb_cat"] = cat.uid
        self.report({"INFO"}, rpt_("{count} objects baked into '{name}'.").format(count=len(made), name=out.name))
        return {"FINISHED"}


class SB_OT_seed(Operator):
    bl_idname = "scatter_brush.seed"
    bl_label = "New Seed"
    bl_description = "Roll a new random pattern"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return has_category(context)

    def execute(self, context):
        active_category(context).seed = random.randint(0, 99999)
        return {"FINISHED"}


class SB_OT_clear(Operator):
    bl_idname = "scatter_brush.clear"
    bl_label = "Delete Placed Objects"
    bl_description = "Delete every object the brush (or a bake) placed for this category"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return has_category(context)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        count = place.clear_placed(context.scene, active_category(context))
        self.report({"INFO"}, rpt_("{count} objects deleted.").format(count=count))
        return {"FINISHED"}


# ----------------------------------------------------------------------------------------------------------------------
# Modal brush

STATE = {"hit": None, "ring": None, "radius": 1.0, "erase": False, "handle": None}


def ring(center, normal, radius, steps=48):
    t1 = normal.orthogonal().normalized()
    t2 = normal.cross(t1)
    lift = normal * 0.02
    return [
        tuple(center + lift + (t1 * np.cos(a) + t2 * np.sin(a)) * radius)
        for a in np.linspace(0.0, 2.0 * np.pi, steps + 1)
    ]


def surface_ring(painter, loc, normal, radius, steps=48):
    """The brush circle draped over the surface (every point ray-cast down), so bumps do not hide half of it."""
    height = radius * 2.0 + 1.0
    points = []
    for p in ring(loc, normal, radius, steps):
        p = Vector(p)
        hit = painter.cast(p + normal * height, -normal, height * 2.0)
        points.append(tuple(hit[0] + hit[1] * 0.03) if hit else tuple(p))
    return points


def draw_brush():
    """POST_VIEW callback: the brush circle on the surface under the cursor."""
    hit = STATE["hit"]
    if hit is None:
        return
    loc, normal = hit
    try:
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        radius = max(STATE["radius"], 0.1)
        color = (0.95, 0.3, 0.25, 1.0) if STATE["erase"] else (0.4, 0.9, 0.35, 1.0)
        gpu.state.blend_set("ALPHA")
        gpu.state.depth_test_set("LESS_EQUAL")
        gpu.state.line_width_set(2.0)
        shader.bind()
        shader.uniform_float("color", color)
        outline = STATE["ring"] or ring(loc, normal, radius)
        batch_for_shader(shader, "LINE_STRIP", {"pos": outline}).draw(shader)
        batch_for_shader(shader, "LINE_STRIP", {"pos": ring(loc, normal, radius * 0.08, 12)}).draw(shader)
        gpu.state.line_width_set(1.0)
        gpu.state.depth_test_set("NONE")
        gpu.state.blend_set("NONE")
    except Exception:  # a drawing problem must never take the viewport down
        pass


def start_draw():
    if STATE["handle"] is None:
        STATE["handle"] = SpaceView3D.draw_handler_add(draw_brush, (), "WINDOW", "POST_VIEW")


def stop_draw():
    if STATE["handle"] is not None:
        SpaceView3D.draw_handler_remove(STATE["handle"], "WINDOW")
        STATE["handle"] = None
    STATE["hit"] = None
    STATE["ring"] = None


class SB_OT_paint(Operator):
    bl_idname = "scatter_brush.paint"
    bl_label = "Start Brush"
    bl_description = (
        "Click or drag in the viewport to place the active category's models with its settings. "
        "Shift+click or E erases, Ctrl+Wheel or [ ] changes the radius, Esc or right click ends"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        cat = active_category(context)
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and context.mode == "OBJECT"
            and cat is not None
            and cat.collection is not None
            and bool(place.sources(cat))
        )

    def invoke(self, context, event):
        self.area = context.area
        self.region = next((r for r in self.area.regions if r.type == "WINDOW"), None)
        self.rv3d = self.area.spaces.active.region_3d
        if self.region is None or self.rv3d is None:
            self.report({"ERROR"}, rpt_("Run the brush from a 3D viewport."))
            return {"CANCELLED"}
        self.painter = place.Painter(context, active_category(context))
        self.pressed = False
        self.dirty = False
        self.erasing = False
        STATE["radius"] = self.painter.cat.radius
        STATE["erase"] = context.scene.sb_erase
        start_draw()
        context.window_manager.modal_handler_add(self)
        self.status(context)
        return {"RUNNING_MODAL"}

    def status(self, context):
        mode = iface_("Erase") if STATE["erase"] else iface_("Place")
        context.workspace.status_text_set(
            iface_(
                "Scatter Brush [{mode}]   LMB: stamp / drag   Shift+LMB or E: erase   "
                "Ctrl+Wheel or [ ]: radius   Esc / RMB: finish"
            ).format(mode=mode)
        )

    def over_viewport(self, event):
        x, y = event.mouse_x, event.mouse_y
        r = self.region
        if not (r.x <= x < r.x + r.width and r.y <= y < r.y + r.height):
            return False
        for other in self.area.regions:
            if (
                other.type in UI_REGIONS
                and other.width > 1
                and other.height > 1
                and other.x <= x < other.x + other.width
                and other.y <= y < other.y + other.height
            ):
                return False
        return True

    def surface(self, event):
        co = (event.mouse_x - self.region.x, event.mouse_y - self.region.y)
        origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, co)
        direction = view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, co)
        return self.painter.cast(origin, direction)

    def finish(self, context):
        stop_draw()
        context.workspace.status_text_set(None)
        self.area.tag_redraw()

    def set_hit(self, found):
        STATE["hit"] = found
        STATE["ring"] = None
        if found is not None:
            radius = max(self.painter.cat.radius, 0.1)
            STATE["ring"] = surface_ring(self.painter, found[0], found[1], radius)

    def set_radius(self, context, factor):
        cat = self.painter.cat
        cat.radius = min(max(cat.radius * factor, 0.05), 200.0)
        STATE["radius"] = cat.radius
        self.set_hit(STATE["hit"])

    def modal(self, context, event):
        try:
            self.painter.cat  # noqa: B018  (raises when the category was deleted while the tool runs)
        except ReferenceError:
            self.finish(context)
            return {"CANCELLED"}
        if event.type in {"ESC", "RIGHTMOUSE", "RET"} and event.value == "PRESS":
            self.finish(context)
            return {"FINISHED"}
        if not self.over_viewport(event) and not self.pressed:
            STATE["hit"] = STATE["ring"] = None
            self.area.tag_redraw()
            return {"PASS_THROUGH"}

        if event.type == "E" and event.value == "PRESS":
            context.scene.sb_erase = not context.scene.sb_erase
            STATE["erase"] = context.scene.sb_erase
            self.status(context)
            self.area.tag_redraw()
            return {"RUNNING_MODAL"}
        if event.type in {"LEFT_BRACKET", "RIGHT_BRACKET"} and event.value == "PRESS":
            self.set_radius(context, 1.0 / 1.15 if event.type == "LEFT_BRACKET" else 1.15)
            self.area.tag_redraw()
            return {"RUNNING_MODAL"}
        if event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"} and event.ctrl:
            self.set_radius(context, 1.15 if event.type == "WHEELUPMOUSE" else 1.0 / 1.15)
            self.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "MOUSEMOVE":
            found = self.surface(event)
            self.set_hit(found)
            if self.pressed and found is not None:
                loc, normal = found
                if self.erasing:
                    self.dirty |= bool(self.painter.erase(loc))
                else:
                    self.dirty |= bool(self.painter.move(loc, normal))
            self.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE":
            if event.value == "PRESS":
                found = self.surface(event)
                self.set_hit(found)
                self.pressed = True
                self.erasing = event.shift or context.scene.sb_erase
                STATE["erase"] = self.erasing
                self.painter.rebuild_grid()
                self.painter.last = None
                if found is not None:
                    loc, normal = found
                    if self.erasing:
                        self.dirty |= bool(self.painter.erase(loc))
                    else:
                        self.dirty |= bool(self.painter.stamp(loc, normal))
                self.area.tag_redraw()
                return {"RUNNING_MODAL"}
            if event.value == "RELEASE" and self.pressed:
                self.pressed = False
                STATE["erase"] = context.scene.sb_erase
                if self.dirty:
                    bpy.ops.ed.undo_push(message="Scatter Brush stroke")
                    self.dirty = False
                self.area.tag_redraw()
                return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        self.finish(context)


classes = (
    SB_OT_category_add,
    SB_OT_category_remove,
    SB_OT_assets_add,
    SB_OT_assets_prepare,
    SB_OT_layer_add,
    SB_OT_layer_remove,
    SB_OT_layer_paint,
    SB_OT_layer_bake,
    SB_OT_seed,
    SB_OT_clear,
    SB_OT_paint,
)


def cleanup():
    stop_draw()
