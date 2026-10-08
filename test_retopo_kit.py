"""Self-check for retopo_kit. Run it with `python tools/bdev.py check blender-toolkit/retopo_kit`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_retopo_kit.py

Covers the quality report against a brute-force reference, guide curves (marking, fidelity of the result, restoring the
original seams), the QuadriFlow and QRemeshify engines (QRemeshify parts are skipped when the extension is missing),
the presets, the error messages and the Turkish translation.
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "retopo_kit")
spec = importlib.util.spec_from_file_location(
    "retopo_kit", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
rk = importlib.util.module_from_spec(spec)
sys.modules["retopo_kit"] = rk
spec.loader.exec_module(rk)
from retopo_kit import guides, meshing, report  # noqa: E402  (needs the module registered above)

rk.register()
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.preferences.addon_enable(module="bl_ext.user_default.qremeshify")
    except Exception:  # noqa: BLE001  the extension is optional
        pass


def add_sphere(segments=96, rings=64):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1.0)
    return bpy.context.object


def ctx(ob):
    return bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob])


def reference_stats(ob):
    """Brute-force face types and poles, independent of the numpy implementation under test."""
    m = ob.data
    edge_faces = {}
    for p in m.polygons:
        for key in p.edge_keys:
            edge_faces[key] = edge_faces.get(key, 0) + 1
    border = {v for key, n in edge_faces.items() if n != 2 for v in key}
    valence = {}
    for a, b in edge_faces:
        valence[a] = valence.get(a, 0) + 1
        valence[b] = valence.get(b, 0) + 1
    interior = [v for v in valence if v not in border]
    return {
        "quads": sum(len(p.vertices) == 4 for p in m.polygons),
        "tris": sum(len(p.vertices) == 3 for p in m.polygons),
        "pole3": sum(valence[v] == 3 for v in interior),
        "pole5": sum(valence[v] == 5 for v in interior),
        "polen": sum(valence[v] >= 6 for v in interior),
    }


# ---- quality report: quads and triangles
reset()
bpy.ops.mesh.primitive_grid_add(x_subdivisions=12, y_subdivisions=12, size=2)
grid = bpy.context.object
context = bpy.context
data = report.analyze(context, grid)
want = reference_stats(grid)
check(all(data[k] == want[k] for k in want), f"report on a quad grid: {data} vs {want}")
check(all(data[k] == 0 for k in ("tris", "pole3", "pole5", "polen")), "a quad grid has no poles")
bm = bmesh.new()
bm.from_mesh(grid.data)
bmesh.ops.triangulate(bm, faces=bm.faces)
bm.to_mesh(grid.data)
bm.free()
data = report.analyze(context, grid)
want = reference_stats(grid)
check(all(data[k] == want[k] for k in want), f"report on a triangulated grid: {data} vs {want}")
check(data["quads"] == 0 and data["polen"] > 0, "triangulated grid: no quads, many 6-valence vertices")

# ---- quality report: distance to the source
reset()
source = add_sphere(64, 32)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.05)
bigger = bpy.context.object
data = report.analyze(bpy.context, bigger, source)
# 0.05 m off a unit sphere, relative to the 3.46 m diagonal of its bounding box: 1.44 %
check(data["has_dev"] and 1.3 < data["dev_avg"] < 1.6, f"deviation of a sphere 5% larger: {data['dev_avg']:.2f}%")
check(report.analyze(bpy.context, source, source)["dev_max"] < 0.01, "a mesh does not deviate from itself")

# ---- guides: mark, follow the curve, restore
reset()
sphere = add_sphere(64, 32)
bpy.ops.curve.primitive_bezier_circle_add(radius=1.0)
circle = bpy.context.object
verts = sphere.data.vertices
equator = [e.index for e in sphere.data.edges if all(abs(verts[v].co.z) < 1e-4 for v in e.vertices)]
sphere.data.edges[equator[0]].use_seam = True  # a seam the user had before
for o in bpy.context.view_layer.objects:
    o.select_set(o == circle)
bpy.context.scene.rk_settings.guide_target = sphere
with ctx(circle):
    check(bpy.ops.retopo_kit.apply_guides() == {"FINISHED"}, "apply guides")
marked = guides.count(sphere)
check(marked >= 60, f"guide edges marked: {marked}")
flagged = [e for e in sphere.data.edges if sphere.data.attributes["rk_guide"].data[e.index].value & guides.IS_GUIDE]
check(all(abs(verts[v].co.z) < 0.12 for e in flagged for v in e.vertices), "guide edges lie on the curve")
check(all(e.use_seam for e in flagged), "guide edges are seams")
sharp = sphere.data.attributes["sharp_edge"].data
check(all(sharp[e.index].value for e in flagged), "guide edges are sharp")
with ctx(sphere):
    bpy.ops.retopo_kit.clear_guides()
check(guides.count(sphere) == 0 and "rk_guide" not in sphere.data.attributes, "guides cleared")
check(sphere.data.edges[equator[0]].use_seam, "a seam that existed before stays after clearing")
check(sum(e.use_seam for e in sphere.data.edges) == 1, "no other seam is left behind")

bpy.context.view_layer.objects.active = sphere  # edit-mode marking
bpy.ops.object.mode_set(mode="EDIT")
bm = bmesh.from_edit_mesh(sphere.data)
bm.edges.ensure_lookup_table()
for e in bm.edges:
    e.select_set(False)
bm.edges[equator[1]].select_set(True)
bmesh.update_edit_mesh(sphere.data)
bpy.ops.retopo_kit.mark_guides()
bpy.ops.object.mode_set(mode="OBJECT")
check(guides.count(sphere) == 1, "mark selected edges")

# ---- QuadriFlow engine and AUTO preset on a smooth shape
reset()
sphere = add_sphere(96, 64)
settings = bpy.context.scene.rk_settings
settings.engine, settings.target_faces = "QUADRIFLOW", 800
with ctx(sphere):
    check(bpy.ops.retopo_kit.retopo() == {"FINISHED"}, "retopo with QuadriFlow")
result = bpy.data.objects.get(sphere.name + "_retopo")
check(result is not None and result["rk_source"] == sphere.name, "result named after the source")
if result is not None:
    stats = report.analyze(bpy.context, result, sphere)
    check(stats["quads"] / stats["faces"] > 0.95, f"QuadriFlow quads: {stats['quads']}/{stats['faces']}")
    check(stats["dev_avg"] < 1.5, f"QuadriFlow deviation {stats['dev_avg']:.2f}%")
    check(0.3 * 800 < stats["faces"] < 2.0 * 800, f"QuadriFlow face count {stats['faces']} for target 800")
    check(sphere.hide_get() and "RK Snap" in result.modifiers, "source hidden, snap modifier added")
    check(bpy.context.scene.rk_report.valid and bpy.context.scene.rk_report.faces == stats["faces"], "report stored")

# ---- presets
settings.preset = "HARD"
check(settings.sharp_angle == 30.0 and not settings.smoothing, "hard-surface preset values")
settings.preset = "ORGANIC"
check(settings.sharp_angle == 80.0 and settings.smoothing, "organic preset values")
mesh = meshing.evaluated_mesh(bpy.context, sphere)
check(meshing.sharp_ratio(mesh) < meshing.HARD_SURFACE_RATIO, "a smooth sphere is not hard surface")
bpy.data.meshes.remove(mesh)
bpy.ops.mesh.primitive_cube_add(size=2)
cube = bpy.context.object
mesh = meshing.evaluated_mesh(bpy.context, cube)
check(meshing.sharp_ratio(mesh) >= meshing.HARD_SURFACE_RATIO, "a cube is hard surface")
bpy.data.meshes.remove(mesh)

# ---- error messages
settings.preset = "AUTO"
bpy.ops.object.empty_add()
empty = bpy.context.object
try:
    remesh_run = __import__("retopo_kit.remesh", fromlist=["run"]).run
    remesh_run(bpy.context, empty, settings)
    check(False, "retopo of an empty must raise")
except meshing.RetopoError as e:
    check("mesh" in str(e).lower(), f"empty message: {e}")
original = meshing.qremeshify_available
meshing.qremeshify_available = lambda: False
settings.engine = "QREMESHIFY"
try:
    remesh_run(bpy.context, cube, settings)
    check(False, "QRemeshify requested but missing must raise")
except meshing.RetopoError as e:
    check("QRemeshify" in str(e), f"missing-engine message: {e}")
meshing.qremeshify_available = original

# ---- QRemeshify engine: target faces, guide fidelity, hard-surface corners
reset()
if not meshing.qremeshify_available():
    print("NOTE: QRemeshify not available, skipping its tests")
else:
    settings = bpy.context.scene.rk_settings
    settings.engine, settings.match_target = "QREMESHIFY", True
    settings.target_faces, settings.hide_source = 1500, False
    sphere = add_sphere(96, 64)
    with ctx(sphere):
        check(bpy.ops.retopo_kit.retopo() == {"FINISHED"}, "retopo with QRemeshify")
    plain = bpy.data.objects.get(sphere.name + "_retopo")
    if plain is not None:
        stats = report.analyze(bpy.context, plain, sphere)
        check(stats["quads"] / stats["faces"] > 0.9, f"QRemeshify quads: {stats['quads']}/{stats['faces']}")
        check(stats["dev_avg"] < 1.5, f"QRemeshify deviation {stats['dev_avg']:.2f}%")
        check(0.6 * 1500 < stats["faces"] < 1.4 * 1500, f"QRemeshify face count {stats['faces']} for target 1500")
        plain.name = "plain"

    def ring_loop(ob, tol=0.004):
        """True when the vertices within `tol` of the equator contain one chain that goes all the way around."""
        m = ob.data
        band = {v.index for v in m.vertices if abs(v.co.z) < tol}
        adjacent = {i: set() for i in band}
        for e in m.edges:
            a, b = e.vertices
            if a in band and b in band:
                adjacent[a].add(b)
                adjacent[b].add(a)
        seen = set()
        for start in band:
            if start in seen:
                continue
            chain, stack = [], [start]
            seen.add(start)
            while stack:
                v = stack.pop()
                chain.append(v)
                for n in adjacent[v] - seen:
                    seen.add(n)
                    stack.append(n)
            angles = sorted(math.atan2(m.vertices[i].co.y, m.vertices[i].co.x) for i in chain)
            gaps = [b - a for a, b in zip(angles, angles[1:], strict=False)] + [angles[0] + 2 * math.pi - angles[-1]]
            if len(chain) >= 40 and max(gaps) < 0.3:
                return True
        return False

    sphere = add_sphere(96, 64)
    bpy.ops.curve.primitive_bezier_circle_add(radius=1.0)
    ring = bpy.context.object
    for o in bpy.context.view_layer.objects:
        o.select_set(o == ring)
    settings.guide_target = sphere
    with ctx(ring):
        bpy.ops.retopo_kit.apply_guides()
    settings.match_target = False
    with ctx(sphere):
        check(bpy.ops.retopo_kit.retopo() == {"FINISHED"}, "guided retopo")
    guided = bpy.data.objects.get(sphere.name + "_retopo")
    if guided is not None and plain is not None:
        check(ring_loop(guided), "guided result has an edge loop on the guide curve")
        check(not ring_loop(plain), "an unguided result has no such loop")
        guided.name = "guided"
        settings.use_guides = False
        with ctx(sphere):
            bpy.ops.retopo_kit.retopo()
        ignored = bpy.data.objects.get(sphere.name + "_retopo")
        check(ignored is not None and not ring_loop(ignored), "Use Guides off ignores the marked guides")
        settings.use_guides = True

    bpy.ops.mesh.primitive_cube_add(size=2)
    cube = bpy.context.object
    settings.match_target, settings.target_faces = True, 600
    with ctx(cube):
        check(bpy.ops.retopo_kit.retopo() == {"FINISHED"}, "retopo of a cube")
    box = bpy.data.objects.get(cube.name + "_retopo")
    if box is not None:
        corners = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        missed = [c for c in corners if min(math.dist(c, tuple(v.co)) for v in box.data.vertices) > 0.06]
        check(not missed, f"hard-surface corners kept, missed: {missed}")
        check(report.analyze(bpy.context, box, cube)["dev_avg"] < 1.0, "cube retopo stays on the surface")

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Retopologize")
prefs.language = "en_US"
check(translated == "Retopo Yap", f"Turkish translation active ({translated!r})")

rk.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("OK: retopo_kit report, guides, engines, presets")
