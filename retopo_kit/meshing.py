"""Mesh preparation and the two remesh engines (QuadriFlow built in, QRemeshify optional)."""

import math

import bmesh
import bpy

from . import guides

# QuadWild (inside QRemeshify) works on roughly 1k to 100k triangles; stay well inside that range.
TRIS_MIN, TRIS_MAX = 2500, 90000
HARD_SURFACE_RATIO = 0.04  # at least this share of the edges sharper than 35 degrees: treat as hard surface


class RetopoError(Exception):
    """A failure the user can act on; the message is shown in the status bar."""


def qremeshify_available():
    return hasattr(bpy.types.Scene, "quadwild_props") and hasattr(bpy.ops, "qremeshify")


def tri_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


def sharp_ratio(mesh, angle=35.0):
    """Share of the manifold edges whose two faces meet at more than `angle` degrees."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    limit, total, sharp = math.radians(angle), 0, 0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            total += 1
            sharp += e.calc_face_angle(0.0) > limit
    bm.free()
    return sharp / total if total else 0.0


def evaluated_mesh(context, ob):
    """A standalone copy of the object's mesh with all modifiers applied (the caller removes it)."""
    return bpy.data.meshes.new_from_object(ob.evaluated_get(context.evaluated_depsgraph_get()))


def working_copy(context, src, for_quadwild, use_guides=True):
    """A cleaned duplicate of src (same transform) that the engines can chew on. The caller deletes it."""
    mesh = evaluated_mesh(context, src)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    if not use_guides:
        guides.restore(bm)  # the run ignores the guide marks: seams and sharp edges are what they were before them
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    passes = 0
    while for_quadwild and tris < TRIS_MIN and passes < 6:  # too coarse for QuadWild: subdivide without smoothing
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True)
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        passes += 1
    bm.to_mesh(mesh)
    bm.free()
    work = bpy.data.objects.new(src.name + "_work", mesh)
    work.matrix_world = src.matrix_world.copy()
    context.collection.objects.link(work)
    if for_quadwild and tris > TRIS_MAX:  # too dense: decimate, keeping the shape
        mod = work.modifiers.new("RK Decimate", "DECIMATE")
        mod.ratio = TRIS_MAX / tris
        mod.delimit = {"SEAM", "SHARP"}  # do not merge across guide lines
        context.view_layer.update()
        reduced = evaluated_mesh(context, work)
        work.modifiers.remove(mod)
        old, work.data = work.data, reduced
        bpy.data.meshes.remove(old)
    return work


def select_only(context, ob):
    for other in list(context.view_layer.objects):
        if other is not None:  # objects removed during the run can leave empty slots in the view layer list
            other.select_set(False)
    ob.select_set(True)
    context.view_layer.objects.active = ob


def acting_on(context, ob):
    """Context in which operators see `ob` as the only selected and active object, whatever the caller's context was."""
    select_only(context, ob)
    return context.temp_override(object=ob, active_object=ob, selected_objects=[ob])


def run_quadriflow(context, work, faces, sharp, symmetry):
    with acting_on(context, work):
        result = bpy.ops.object.quadriflow_remesh(
            target_faces=faces,
            mode="FACES",
            use_mesh_symmetry=symmetry,
            use_preserve_sharp=sharp,
            use_preserve_boundary=sharp,
            smooth_normals=False,
        )
    if result != {"FINISHED"} or not len(work.data.polygons):
        raise RetopoError("QuadriFlow could not remesh this mesh (it must be closed and free of loose parts).")
    return work


def run_qremeshify(context, work, cfg, scale):
    """Run QRemeshify on the working copy; returns the new object. QRemeshify's own settings are restored afterwards."""
    sc = context.scene
    qw, qp = sc.quadwild_props, sc.quadpatches_props
    saved = {
        k: getattr(qw, k)
        for k in (
            "debug",
            "useCache",
            "enableRemesh",
            "enableSmoothing",
            "enableSharp",
            "sharpAngle",
            "symmetryX",
            "symmetryY",
            "symmetryZ",
        )
    }
    saved_scale = qp.scaleFact
    try:
        qw.debug, qw.useCache, qw.enableRemesh, qw.enableSharp = False, False, cfg.get("preprocess", True), True
        qw.enableSmoothing, qw.sharpAngle = cfg["smoothing"], cfg["sharp_angle"]
        qw.symmetryX, qw.symmetryY, qw.symmetryZ = cfg["symmetry"]
        qp.scaleFact = scale
        before = set(bpy.data.objects.keys())
        with acting_on(context, work):
            bpy.ops.qremeshify.remesh()
        new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    finally:
        for key, value in saved.items():
            setattr(qw, key, value)
        qp.scaleFact = saved_scale
    if not new or not len(new[0].data.polygons):
        raise RetopoError("QRemeshify returned no mesh. Check that the source is closed and not too thin.")
    return new[0]


def discard(ob):
    """Remove a temporary object and its mesh."""
    mesh = ob.data
    bpy.data.objects.remove(ob)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
