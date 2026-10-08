"""Guide lines: curves (or selected edges) become seam + sharp edges on the source mesh, which QRemeshify keeps as
hard lines, so the quads of the result follow them. The original seam/sharp state is stored and restored on clear.
"""

import heapq

import bmesh
import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import Operator
from mathutils import kdtree

LAYER = "rk_guide"
WAS_SEAM, WAS_SHARP, IS_GUIDE = 1, 2, 4


def guide_layer(bm):
    return bm.edges.layers.int.get(LAYER) or bm.edges.layers.int.new(LAYER)


def mark(edge, layer):
    """Make an edge a guide (seam + sharp), remembering what it was."""
    if edge[layer] & IS_GUIDE:
        return
    edge[layer] = IS_GUIDE | (WAS_SEAM if edge.seam else 0) | (WAS_SHARP if not edge.smooth else 0)
    edge.seam, edge.smooth = True, False


def shortest_path(bm, start, goal):
    """Edges of the shortest route along the mesh from vertex `start` to `goal` (Dijkstra on edge length)."""
    best, came, heap = {start.index: 0.0}, {}, [(0.0, start.index)]
    while heap:
        cost, index = heapq.heappop(heap)
        if index == goal.index:
            break
        if cost > best.get(index, float("inf")):
            continue
        for edge in bm.verts[index].link_edges:
            other = edge.other_vert(bm.verts[index])
            new_cost = cost + edge.calc_length()
            if new_cost < best.get(other.index, float("inf")):
                best[other.index], came[other.index] = new_cost, edge
                heapq.heappush(heap, (new_cost, other.index))
    path, index = [], goal.index
    while index != start.index:
        if index not in came:
            return []  # the two points lie on separate parts of the mesh
        edge = came[index]
        path.append(edge)
        index = edge.other_vert(bm.verts[index]).index
    return path[::-1]


def curve_chains(context, curve):
    """Ordered world-space point lists of a curve object: one list per spline, plus whether it is closed."""
    mesh = bpy.data.meshes.new_from_object(curve.evaluated_get(context.evaluated_depsgraph_get()))
    matrix = curve.matrix_world
    points = [matrix @ v.co for v in mesh.vertices]
    adjacency = {i: [] for i in range(len(points))}
    for e in mesh.edges:
        a, b = e.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen, chains = set(), []
    starts = [i for i, n in adjacency.items() if len(n) == 1] + list(adjacency)  # open ends first, then rings
    for first in starts:
        if first in seen:
            continue
        chain, current = [], first
        while current is not None and current not in seen:
            seen.add(current)
            chain.append(current)
            current = next((n for n in adjacency[current] if n not in seen), None)
        closed = len(chain) > 2 and chain[0] in adjacency[chain[-1]]
        chains.append(([points[i] for i in chain], closed))
    bpy.data.meshes.remove(mesh)
    return chains


def apply_curves(context, target, curves):
    """Mark the mesh edges nearest to the curves as guides. Returns the number of edges marked."""
    bm = bmesh.new()
    bm.from_mesh(target.data)
    layer = guide_layer(bm)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    inverse = target.matrix_world.inverted()
    tree = kdtree.KDTree(len(bm.verts))
    for v in bm.verts:
        tree.insert(v.co, v.index)
    tree.balance()
    marked = 0
    for curve in curves:
        for points, closed in curve_chains(context, curve):
            nearest = []
            for p in points:
                index = tree.find(inverse @ p)[1]
                if not nearest or nearest[-1] != index:
                    nearest.append(index)
            if closed and nearest[0] != nearest[-1]:
                nearest.append(nearest[0])
            for a, b in zip(nearest, nearest[1:], strict=False):
                for edge in shortest_path(bm, bm.verts[a], bm.verts[b]):
                    marked += not (edge[layer] & IS_GUIDE)
                    mark(edge, layer)
    bm.to_mesh(target.data)
    bm.free()
    target.data.update()
    return marked


def count(ob):
    """Number of guide edges stored on a mesh object."""
    attribute = ob.data.attributes.get(LAYER)
    if attribute is None:
        return 0
    return sum(1 for item in attribute.data if item.value & IS_GUIDE)


def restore(bm):
    """Put every guide edge of a bmesh back to the seam/sharp state it had before; returns how many."""
    layer = bm.edges.layers.int.get(LAYER)
    restored = 0
    if layer is not None:
        for edge in bm.edges:
            if edge[layer] & IS_GUIDE:
                edge.seam = bool(edge[layer] & WAS_SEAM)
                edge.smooth = not edge[layer] & WAS_SHARP
                restored += 1
        bm.edges.layers.int.remove(layer)
    return restored


def clear(target):
    bm = bmesh.new()
    bm.from_mesh(target.data)
    restored = restore(bm)
    bm.to_mesh(target.data)
    bm.free()
    target.data.update()
    return restored


def target_of(context):
    settings = context.scene.rk_settings
    ob = settings.guide_target
    if ob is None and context.object is not None and context.object.type == "MESH":
        ob = context.object
    return ob


class RK_OT_draw_guide(Operator):
    bl_idname = "retopo_kit.draw_guide"
    bl_label = "Draw Guide"
    bl_description = (
        "Create a guide curve and start the Draw tool with surface projection: drag on the model to draw "
        "lines the new quads should follow, then press Apply Guides"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and context.mode == "OBJECT"

    def execute(self, context):
        context.scene.rk_settings.guide_target = context.object
        curve = bpy.data.curves.new("RK Guide", "CURVE")
        curve.dimensions = "3D"
        ob = bpy.data.objects.new("RK Guide", curve)
        context.collection.objects.link(ob)
        paint = context.scene.tool_settings.curve_paint_settings
        paint.curve_type, paint.depth_mode, paint.use_pressure_radius = "POLY", "SURFACE", False
        for other in list(context.view_layer.objects):
            if other is not None:
                other.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            bpy.ops.wm.tool_set_by_id(name="builtin.draw")
        except RuntimeError:  # no 3D view in this context: the user picks the Draw tool in the toolbar
            self.report({"WARNING"}, rpt_("Pick the Draw tool in the toolbar, then drag on the model."))
        return {"FINISHED"}


class RK_OT_apply_guides(Operator):
    bl_idname = "retopo_kit.apply_guides"
    bl_label = "Apply Guides"
    bl_description = "Turn the selected curve objects into guide edges on the target mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        target = target_of(context)
        if target is None:
            self.report({"ERROR"}, rpt_("Select the mesh that should receive the guides."))
            return {"CANCELLED"}
        if context.object is not None and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        curves = [o for o in context.view_layer.objects if o is not None and o.select_get() and o.type == "CURVE"]
        if not curves:
            self.report({"ERROR"}, rpt_("Select at least one guide curve."))
            return {"CANCELLED"}
        marked = apply_curves(context, target, curves)
        self.report({"INFO"}, rpt_("{count} guide edges marked on '{name}'.").format(count=marked, name=target.name))
        return {"FINISHED"}


class RK_OT_mark_guides(Operator):
    bl_idname = "retopo_kit.mark_guides"
    bl_label = "Mark Selected Edges"
    bl_description = "Edit mode: turn the selected edges into guide edges"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and context.mode == "EDIT_MESH"

    def execute(self, context):
        ob = context.object
        bm = bmesh.from_edit_mesh(ob.data)
        layer = guide_layer(bm)
        bm.edges.ensure_lookup_table()
        selected = [e for e in bm.edges if e.select]
        for edge in selected:
            mark(edge, layer)
        bmesh.update_edit_mesh(ob.data)
        self.report({"INFO"}, rpt_("{count} edges marked as guides.").format(count=len(selected)))
        return {"FINISHED"}


class RK_OT_clear_guides(Operator):
    bl_idname = "retopo_kit.clear_guides"
    bl_label = "Clear Guides"
    bl_description = "Remove the guide marks and restore the seams and sharp edges the mesh had before"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and context.mode == "OBJECT"

    def execute(self, context):
        target = target_of(context)
        restored = clear(target) if target is not None else 0
        self.report({"INFO"}, rpt_("{count} guide edges cleared.").format(count=restored))
        return {"FINISHED"}


classes = (RK_OT_draw_guide, RK_OT_apply_guides, RK_OT_mark_guides, RK_OT_clear_guides)
