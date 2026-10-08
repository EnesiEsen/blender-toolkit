"""Self-check for texel_density. Run it with `python tools/bdev.py check blender-toolkit/texel_density`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_texel_density.py

Compares the numpy density with a brute-force per-polygon reference, checks the world-space scale, texture-size
handling, the color attribute, UV island detection and that Set Density really produces the target (islands and whole
object).
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "texel_density")
spec = importlib.util.spec_from_file_location(
    "texel_density", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
td = importlib.util.module_from_spec(spec)
sys.modules["texel_density"] = td
spec.loader.exec_module(td)
from texel_density import density, uvtools  # noqa: E402  (needs the module registered above)

td.register()
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def near(a, b, tol=0.01):
    return abs(a - b) <= tol * max(abs(b), 1e-9)


def quad(name, size=2.0, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    ob = bpy.context.object
    ob.name = name
    return ob


def set_uv(ob, scale=1.0, offset=(0.0, 0.0)):
    """UVs covering `scale` of the 0-1 square."""
    uv = ob.data.uv_layers.active.uv
    for loop in ob.data.loops:
        v = ob.data.vertices[loop.vertex_index].co
        u0 = (v.x / ob_size(ob) + 0.5) * scale + offset[0]
        v0 = (v.y / ob_size(ob) + 0.5) * scale + offset[1]
        uv[loop.index].vector = (u0, v0)


def ob_size(ob):
    return max(max(v.co.x for v in ob.data.vertices) - min(v.co.x for v in ob.data.vertices), 1e-9)


def textured(ob, side):
    mat = bpy.data.materials.new(ob.name + "_mat")
    mat.use_nodes = True
    image = bpy.data.images.new(ob.name + "_img", side, side)
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    ob.data.materials.append(mat)


sc = bpy.context.scene
s = sc.td_settings
s.default_size = "1024"

# ---- 2 m x 2 m plane, UV fills the square, 1024 px texture: sqrt(1024^2 / 4) = 512 px/m
plane = quad("plane")
set_uv(plane, 1.0)
data = density.analyze(plane, 1024)
check(near(data["average"], 512.0), f"2 m plane with full UV and 1024 px is 512 px/m: {data['average']}")
set_uv(plane, 0.5)
check(near(density.analyze(plane, 1024)["average"], 256.0), "half the UV size halves the density")
plane.scale = (2, 1, 1)
bpy.context.view_layer.update()
expected = math.sqrt(1024 * 1024 * 0.25 / 8.0)
check(near(density.analyze(plane, 1024)["average"], expected), "object scale is part of the world-space surface")
plane.scale = (1, 1, 1)
bpy.context.view_layer.update()

# ---- the material's texture size replaces the default
textured(plane, 2048)
set_uv(plane, 1.0)
check(near(density.analyze(plane, 1024)["average"], 1024.0), "an image of 2048 px doubles the density")

# ---- independent per-polygon reference on a real mesh (ico sphere with smart UVs)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.5, location=(5, 0, 0))
ico = bpy.context.object
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
bpy.ops.object.mode_set(mode="OBJECT")
ico.scale = (1.0, 2.0, 0.5)
ico.rotation_euler = (0.3, 0.2, 0.1)
bpy.context.view_layer.update()
data = density.analyze(ico, 1024)
mesh, uvl, mw = ico.data, ico.data.uv_layers.active, ico.matrix_world
worst = 0.0
for poly in mesh.polygons:
    pts = [
        mw @ mesh.vertices[mesh.loops[i].vertex_index].co
        for i in range(poly.loop_start, poly.loop_start + poly.loop_total)
    ]
    uvs = [uvl.uv[i].vector for i in range(poly.loop_start, poly.loop_start + poly.loop_total)]
    area = sum(0.5 * ((pts[k] - pts[0]).cross(pts[k + 1] - pts[0])).length for k in range(1, len(pts) - 1))
    uv_area = sum(
        0.5
        * abs(
            (uvs[k][0] - uvs[0][0]) * (uvs[k + 1][1] - uvs[0][1])
            - (uvs[k][1] - uvs[0][1]) * (uvs[k + 1][0] - uvs[0][0])
        )
        for k in range(1, len(uvs) - 1)
    )
    reference = math.sqrt(uv_area * 1024 * 1024 / area)
    worst = max(worst, abs(data["density"][poly.index] - reference) / reference)
check(worst < 1e-4, f"per-polygon density matches a brute-force reference (worst relative error {worst:.2e})")

# ---- colors
sc.td_settings.preset = "512"
target = s.target()
check(target == 512.0, "preset value")
rgb = density.colors(np.array([512.0, 1024.0, 256.0, 0.0]), 512.0)
check(rgb[0][1] > rgb[0][0] and rgb[0][1] > rgb[0][2], "on target is green")
check(rgb[1][0] > rgb[1][1] and rgb[1][0] > rgb[1][2], "double density is red")
check(rgb[2][2] > rgb[2][0] and rgb[2][2] > rgb[2][1], "half density is blue")
check(abs(rgb[3][0] - rgb[3][1]) < 1e-6, "no UV area is gray")
bpy.ops.object.select_all(action="DESELECT")
plane.select_set(True)
bpy.context.view_layer.objects.active = plane
bpy.ops.texel_density.show()
attribute = plane.data.color_attributes.get("TD_Density")
check(attribute is not None and attribute.domain == "CORNER", "show colors writes a face-corner attribute")
bpy.ops.texel_density.hide()
check(plane.data.color_attributes.get("TD_Density") is None, "hide colors removes it")

# ---- island detection on a hand-made mesh: a strip of two quads welded in UV, plus a third quad cut apart in UV
bm = bmesh.new()
verts = [bm.verts.new((x, y, 0)) for y in (0, 1) for x in (0, 1, 2, 3)]
for a, b, c, d in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6)):
    bm.faces.new((verts[a], verts[b], verts[c], verts[d]))
uv_layer = bm.loops.layers.uv.new("UVMap")
for face in bm.faces:
    for loop in face.loops:
        loop[uv_layer].uv = (loop.vert.co.x * 0.2, loop.vert.co.y * 0.2)
bm.faces.ensure_lookup_table()
for loop in bm.faces[2].loops:
    loop[uv_layer].uv.x += 0.5  # the third quad is cut from the others in UV
bm.faces.ensure_lookup_table()
groups = uvtools.find_islands(list(bm.faces), uv_layer)
check(
    sorted(len(g) for g in groups) == [1, 2], f"UV islands: two welded quads and one apart ({[len(g) for g in groups]})"
)
bm.free()

# ---- Set Density: each island exactly on target, relative sizes kept in object mode
bpy.ops.mesh.primitive_grid_add(x_subdivisions=3, y_subdivisions=1, size=2.0, location=(0, 8, 0))
strip = bpy.context.object
strip.name = "strip"
bm = bmesh.new()
bm.from_mesh(strip.data)
uv_layer = bm.loops.layers.uv.verify()
bm.faces.ensure_lookup_table()
bm.faces.index_update()
for face in bm.faces:
    for loop in face.loops:
        co = loop.vert.co
        loop[uv_layer].uv = ((co.x + 1) * 0.25 + (0.0 if face.index < 2 else 0.4), (co.y + 1) * 0.25)
bm.to_mesh(strip.data)
bm.free()
strip.data.update()
sizes_before = density.analyze(strip, 1024)["density"]
check(len({round(d, 3) for d in sizes_before}) >= 1, "strip measured")
bpy.ops.object.select_all(action="DESELECT")
strip.select_set(True)
bpy.context.view_layer.objects.active = strip
s.preset, s.mode = "1024", "ISLAND"
check(bpy.ops.texel_density.set() == {"FINISHED"}, "set density finishes")
after = density.analyze(strip, 1024)
check(np.allclose(after["density"], 1024.0, rtol=2e-3), f"each island is on target: {after['density']}")

# object mode keeps the ratio between islands
bm = bmesh.new()
bm.from_mesh(strip.data)
uv_layer = bm.loops.layers.uv.verify()
bm.faces.ensure_lookup_table()
for face in bm.faces:
    if face.index >= 2:
        for loop in face.loops:
            loop[uv_layer].uv *= 0.5  # that island is now half as dense
bm.to_mesh(strip.data)
bm.free()
strip.data.update()
before = density.analyze(strip, 1024)
ratio_before = before["density"][2] / before["density"][0]
s.preset, s.mode = "512", "OBJECT"
bpy.ops.texel_density.set()
after = density.analyze(strip, 1024)
check(near(after["average"], 512.0, 0.005), f"whole-object mode hits the target on average: {after['average']}")
check(near(after["density"][2] / after["density"][0], ratio_before, 0.005), "whole-object mode keeps the island ratio")

# ---- copy from active
other = quad("other", 1.0, (0, -8, 0))
set_uv(other, 1.0)
bpy.ops.object.select_all(action="DESELECT")
other.select_set(True)
strip.select_set(True)
bpy.context.view_layer.objects.active = strip
bpy.ops.texel_density.copy()
check(
    near(density.analyze(other, 1024)["average"], density.analyze(strip, 1024)["average"], 0.005),
    "copy from active matches the density",
)

# ---- measuring fills the report; errors are explained
bpy.ops.texel_density.analyze()
report = sc.td_report
check(report.valid and report.object_name == "strip" and near(report.average, 512.0, 0.005), "the report is stored")
bare = quad("bare", 1.0, (9, 9, 0))
while bare.data.uv_layers:
    bare.data.uv_layers.remove(bare.data.uv_layers[0])
bpy.ops.object.select_all(action="DESELECT")
bare.select_set(True)
bpy.context.view_layer.objects.active = bare
refused = False
try:
    bpy.ops.texel_density.analyze()
except RuntimeError as e:
    refused = "UV" in str(e)
check(refused, "a mesh without UVs is refused with a message")

# ---- pack keeps the scale of the islands
strip2 = strip
bpy.ops.object.select_all(action="DESELECT")
strip2.select_set(True)
bpy.context.view_layer.objects.active = strip2
before = density.analyze(strip2, 1024)["density"].copy()
try:
    bpy.ops.texel_density.pack()
    after = density.analyze(strip2, 1024)["density"]
    check(np.allclose(before, after, rtol=0.02), f"pack islands keeps the density: {before} -> {after}")
except RuntimeError as e:
    failures.append(f"pack islands failed: {e}")

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Show Colors")
prefs.language = "en_US"
check(translated == "Renkleri Göster", f"Turkish translation active ({translated!r})")

td.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("OK: texel_density analysis, colors, islands, set density, copy, pack")
