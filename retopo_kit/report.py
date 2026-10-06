"""Quality report of a retopology result: face types, poles, edge-length evenness, distance to the source surface."""
import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import Operator
from mathutils.bvhtree import BVHTree

from . import meshing


def world_vertices(mesh, matrix):
    count = len(mesh.vertices)
    co = np.empty(count * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(count, 3)
    m = np.array(matrix, dtype=np.float64)
    return co @ m[:3, :3].T + m[:3, 3]


def surface_tree(context, source):
    """BVH tree of the source's evaluated mesh in world space, and the diagonal of its bounding box."""
    mesh = meshing.evaluated_mesh(context, source)
    co = world_vertices(mesh, source.matrix_world)
    mesh.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in mesh.loop_triangles]
    tree = BVHTree.FromPolygons([tuple(c) for c in co.tolist()], tris)
    diagonal = float(np.linalg.norm(co.max(axis=0) - co.min(axis=0)))
    bpy.data.meshes.remove(mesh)
    return tree, diagonal


def analyze(context, ob, source=None):
    """Measure `ob` (modifiers included). Returns a dict; deviation values are in percent of the source's diagonal."""
    mesh = meshing.evaluated_mesh(context, ob)
    n_faces, n_verts, n_edges = len(mesh.polygons), len(mesh.vertices), len(mesh.edges)
    sizes = np.empty(n_faces, dtype=np.int32)
    mesh.polygons.foreach_get("loop_total", sizes)
    edge_verts = np.empty(n_edges * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edge_verts)
    edge_verts = edge_verts.reshape(n_edges, 2)
    corner_edges = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("edge_index", corner_edges)
    faces_per_edge = np.bincount(corner_edges, minlength=n_edges)
    boundary = faces_per_edge == 1
    non_manifold = (faces_per_edge > 2) | (faces_per_edge == 0)
    valence = np.bincount(edge_verts.ravel(), minlength=n_verts)
    skip = np.zeros(n_verts, dtype=bool)  # poles on a border or on a non-manifold edge are not interesting
    skip[edge_verts[boundary | non_manifold].ravel()] = True
    interior = ~skip
    co = world_vertices(mesh, ob.matrix_world)
    lengths = np.linalg.norm(co[edge_verts[:, 0]] - co[edge_verts[:, 1]], axis=1)
    out = {
        "faces": n_faces, "quads": int((sizes == 4).sum()), "tris": int((sizes == 3).sum()),
        "ngons": int((sizes > 4).sum()),
        "pole3": int(((valence == 3) & interior).sum()), "pole5": int(((valence == 5) & interior).sum()),
        "polen": int(((valence >= 6) & interior).sum()), "non_manifold": int(non_manifold.sum()),
        "edge_cv": float(lengths.std() / lengths.mean()) if len(lengths) and lengths.mean() > 0 else 0.0,
        "has_dev": False, "dev_avg": 0.0, "dev_max": 0.0,
    }
    if source is not None and n_verts:
        tree, diagonal = surface_tree(context, source)
        dist = np.array([tree.find_nearest(tuple(c))[3] for c in co.tolist()])
        if diagonal > 0:
            out.update(has_dev=True, dev_avg=float(dist.mean() / diagonal * 100),
                       dev_max=float(dist.max() / diagonal * 100))
    bpy.data.meshes.remove(mesh)
    return out


def store(context, name, data):
    report = context.scene.rk_report
    report.valid, report.object_name = True, name
    for key, value in data.items():
        setattr(report, key, value)


class RK_OT_report(Operator):
    bl_idname = "retopo_kit.report"
    bl_label = "Analyze Mesh"
    bl_description = "Measure quad share, poles, edge evenness and the distance to the source surface"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        ob = context.object
        source = bpy.data.objects.get(ob.get("rk_source", ""))
        store(context, ob.name, analyze(context, ob, source))
        self.report({"INFO"}, rpt_("Analyzed '{name}'.").format(name=ob.name))
        return {"FINISHED"}


classes = (RK_OT_report,)
