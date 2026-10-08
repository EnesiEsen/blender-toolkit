"""The one-click retopology: prepare a copy, run the engine, tidy the result, measure it."""

import math

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import Operator

from . import guides, meshing, report
from .meshing import RetopoError
from .props import PRESETS

MATCH_TOLERANCE = 0.25  # a result within 25 % of the target face count is accepted without a second pass


def resolve_preset(context, src, settings):
    """Return (preset name, sharp angle, smoothing). AUTO decides from how many sharp edges the source has."""
    if settings.preset != "AUTO":
        return settings.preset, settings.sharp_angle, settings.smoothing
    mesh = meshing.evaluated_mesh(context, src)
    ratio = meshing.sharp_ratio(mesh)
    bpy.data.meshes.remove(mesh)
    name = "HARD" if ratio >= meshing.HARD_SURFACE_RATIO else "ORGANIC"
    return name, PRESETS[name]["sharp_angle"], PRESETS[name]["smoothing"]


def resolve_engine(settings):
    if settings.engine == "QREMESHIFY" and not meshing.qremeshify_available():
        raise RetopoError(rpt_("The QRemeshify extension is not installed or not enabled."))
    if settings.engine == "AUTO":
        return "QREMESHIFY" if meshing.qremeshify_available() else "QUADRIFLOW"
    return settings.engine


def finish(context, result, src, settings):
    """Name, place and link the result like the source; snap it; hide the source."""
    result.name = result.data.name = src.name + "_retopo"
    result["rk_source"] = src.name
    for collection in list(result.users_collection):
        collection.objects.unlink(result)
    for collection in src.users_collection or [context.scene.collection]:
        collection.objects.link(result)
    result.data.shade_smooth()
    if settings.snap:
        snap = result.modifiers.new("RK Snap", "SHRINKWRAP")
        snap.target, snap.wrap_method = src, "NEAREST_SURFACEPOINT"
        snap.show_on_cage = True
    if settings.hide_source:
        src.hide_set(True)
    meshing.select_only(context, result)


def run(context, src, settings):
    """Retopologize `src`. Returns (result object, one-line summary)."""
    if src is None or src.type != "MESH" or not len(src.data.polygons):
        raise RetopoError(rpt_("Select a mesh with faces."))
    preset, sharp_angle, smoothing = resolve_preset(context, src, settings)
    engine = resolve_engine(settings)
    symmetry = (settings.symmetry_x, settings.symmetry_y, settings.symmetry_z)
    has_guides = guides.count(src) > 0
    ignored_guides = settings.use_guides and engine == "QUADRIFLOW" and has_guides
    followed = settings.use_guides and engine == "QREMESHIFY" and has_guides
    work = meshing.working_copy(context, src, for_quadwild=engine == "QREMESHIFY", use_guides=settings.use_guides)
    try:
        if engine == "QUADRIFLOW":
            result = meshing.run_quadriflow(
                context, work, settings.target_faces, preset in ("SIMPLE", "HARD"), any(symmetry)
            )
            work = None  # QuadriFlow remeshed the copy in place: the copy is the result
            passes = 1
        else:
            # QuadWild's own preprocessing resamples the mesh and moves guide lines off their place, so it is skipped
            # when guides are followed (the working copy is already cleaned and kept inside QuadWild's size range).
            cfg = {"smoothing": smoothing, "sharp_angle": sharp_angle, "symmetry": symmetry, "preprocess": not followed}
            scale, passes = 1.0, 1
            result = meshing.run_qremeshify(context, work, cfg, scale)
            faces = len(result.data.polygons)
            if settings.match_target and abs(faces - settings.target_faces) > MATCH_TOLERANCE * settings.target_faces:
                scale = min(10.0, max(0.05, scale * math.sqrt(faces / settings.target_faces)))  # faces ~ 1 / scale^2
                meshing.discard(result)
                result = meshing.run_qremeshify(context, work, cfg, scale)
                passes = 2
    finally:
        if work is not None:
            meshing.discard(work)
    finish(context, result, src, settings)
    data = report.analyze(context, result, src)
    report.store(context, result.name, data)
    quad_pct = 100.0 * data["quads"] / max(1, data["faces"])
    message = rpt_(
        "{preset}/{engine}: {faces} faces, {quads:.0f}% quads, deviation {dev:.2f}%, {passes} pass(es)"
    ).format(preset=preset, engine=engine, faces=data["faces"], quads=quad_pct, dev=data["dev_avg"], passes=passes)
    if followed:
        message += rpt_(", guides followed")
    if ignored_guides:
        message += rpt_(" (guides are ignored by QuadriFlow: use QRemeshify)")
    return result, message


class RK_OT_retopo(Operator):
    bl_idname = "retopo_kit.retopo"
    bl_label = "Retopologize"
    bl_description = "Build a clean quad mesh from the active object; the original is kept (hidden by default)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and context.mode == "OBJECT"

    def execute(self, context):
        try:
            _, message = run(context, context.object, context.scene.rk_settings)
        except RetopoError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, message)
        return {"FINISHED"}


classes = (RK_OT_retopo,)
