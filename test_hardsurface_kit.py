"""Self-check for hardsurface_kit. Run it with `python tools/bdev.py check blender-toolkit/hardsurface_kit`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_hardsurface_kit.py

Checks the modifier stack and its order, volumes after bevels, cuts, unions and intersections, mirror and arrays,
grooves, sharp edge marking, cleanup, Apply Stack and the Turkish text.
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "hardsurface_kit")
spec = importlib.util.spec_from_file_location(
    "hardsurface_kit", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
hs = importlib.util.module_from_spec(spec)
sys.modules["hardsurface_kit"] = hs
spec.loader.exec_module(hs)
from hardsurface_kit import cutters, meshtools  # noqa: E402  (needs the module registered above)

hs.register()
failures = []
sc = bpy.context.scene
s = sc.hs_settings


def check(condition, message):
    if not condition:
        failures.append(message)


def near(a, b, tol=0.01):
    return abs(a - b) <= tol * max(abs(b), 1e-9)


def only(*objects):
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objects)
    bpy.context.view_layer.objects.active = objects[0]


def evaluated_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)


def volume(obj):
    mesh = evaluated_mesh(obj)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    value = abs(bm.calc_volume())
    bm.free()
    bpy.data.meshes.remove(mesh)
    return value


def stats(obj):
    mesh = evaluated_mesh(obj)
    xs = [v.co.x for v in mesh.vertices]
    out = (len(mesh.vertices), max(xs) - min(xs), mesh)
    return out


def cube(name, location=(0, 0, 0), size=2.0):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    ob = bpy.context.object
    ob.name = name
    return ob


# ---- smart bevel and the order of the stack
block = cube("Block")
only(block)
check(abs(volume(block) - 8.0) < 1e-6, "a 2 m cube has volume 8")
check(bpy.ops.hardsurface_kit.bevel() == {"FINISHED"}, "smart bevel finishes")
check(
    [m.name for m in block.modifiers] == ["HS Bevel", "HS Weighted Normal"],
    f"bevel then weighted normal: {[m.name for m in block.modifiers]}",
)
bevel = block.modifiers["HS Bevel"]
check(
    bevel.segments == 3 and bevel.limit_method == "ANGLE" and bevel.harden_normals, "bevel settings come from the panel"
)
v = volume(block)
check(7.9 < v < 8.0, f"bevel removes a little volume: {v:.4f}")
count, _, mesh = stats(block)
check(count > 8 * 3, f"bevel adds geometry: {count} vertices")
bpy.data.meshes.remove(mesh)
check(
    all(p.use_smooth for p in block.data.polygons),
    "the base mesh is shaded smooth (the normals are handled by the modifiers)",
)

# ---- cutters: difference, union, intersect (cutter half inside: overlap volume 0.5)
cutter = cube("Notch", (1.0, 0, 0), 1.0)
only(block, cutter)
bpy.context.view_layer.objects.active = block
s.cut_operation, s.cut_solver = "DIFFERENCE", "EXACT"
check(bpy.ops.hardsurface_kit.cutter_add() == {"FINISHED"}, "cutter add finishes")
names = [m.name for m in block.modifiers]
check(names == ["HS Cut Notch", "HS Bevel", "HS Weighted Normal"], f"the cut comes before the bevel: {names}")
check(
    cutter.display_type == "WIRE" and cutter.parent == block and cutter.hide_render,
    "the cutter is wire, hidden from renders and parented",
)
check(near(cutter.matrix_world.translation.x, 1.0, 1e-4), "parenting keeps the cutter where it was")
bevel.width = 0.0001  # make the bevel negligible for the volume checks
check(near(volume(block), 7.5, 0.01), f"difference removes the overlap: {volume(block):.4f}")
block.modifiers["HS Cut Notch"].operation = "UNION"
check(near(volume(block), 8.5, 0.01), f"union adds the cutter minus the overlap: {volume(block):.4f}")
block.modifiers["HS Cut Notch"].operation = "INTERSECT"
check(near(volume(block), 0.5, 0.01), f"intersect keeps the overlap: {volume(block):.4f}")
block.modifiers["HS Cut Notch"].operation = "DIFFERENCE"

# apply
only(block)
check(bpy.ops.hardsurface_kit.cutter_apply() == {"FINISHED"}, "apply cutters finishes")
check("Notch" not in bpy.data.objects and not cutters.cuts_of(block), "the cutter object and its modifier are gone")
permanent = volume(block)
check(near(permanent, 7.5, 0.01), f"the cut is permanent: {permanent:.4f}")

# remove instead of apply
cutter2 = cube("Hole", (0, 0, 0), 0.5)
only(block, cutter2)
bpy.context.view_layer.objects.active = block
bpy.ops.hardsurface_kit.cutter_add()
only(block)
bpy.ops.hardsurface_kit.cutter_remove()
check("Hole" not in bpy.data.objects and not cutters.cuts_of(block), "remove cutters deletes modifier and object")

# new cutter at the cursor
sc.cursor.location = (0.0, 0.0, 1.0)
s.cutter_size = (0.4, 0.4, 0.4)
only(block)
bpy.ops.hardsurface_kit.cutter_new(kind="CYLINDER")
newcut = bpy.data.objects.get("HS Cutter")
check(
    newcut is not None and newcut.parent == block and near(newcut.matrix_world.translation.z, 1.0, 1e-4),
    "a new cutter appears at the 3D cursor and cuts the active object",
)
only(block)
bpy.ops.hardsurface_kit.cutter_remove()

# ---- mirror and arrays
half = cube("Half", (0, 0, 0), 2.0)
half.data.transform(Matrix.Translation((1.0, 0.0, 0.0)))  # the mesh spans x 0..2 while the origin stays at 0
only(half)
s.mirror_x, s.mirror_y, s.mirror_z, s.mirror_bisect = True, False, False, False
bpy.ops.hardsurface_kit.mirror()
_, width, mesh = stats(half)
bpy.data.meshes.remove(mesh)
check(near(width, 4.0, 0.001), f"mirror around the object origin gives a mesh from x -2 to 2: {width}")
half.modifiers.remove(half.modifiers["HS Mirror"])

unit = cube("Unit", (0, 0, 0), 2.0)
only(unit)
s.array_count, s.array_offset = 4, 1.0
bpy.ops.hardsurface_kit.array()
_, width, mesh = stats(unit)
bpy.data.meshes.remove(mesh)
check(near(width, 8.0, 0.001), f"4 touching copies are 8 m long: {width}")
unit.modifiers.remove(unit.modifiers["HS Array"])

bolt = cube("Bolt", (0, 0, 0), 0.5)
only(bolt)
bolt.data.transform(Matrix.Translation((3.0, 0.0, 0.0)))  # the bolt sits 3 m from its origin
s.radial_count, s.radial_axis = 4, "Z"
bpy.ops.hardsurface_kit.radial()
mesh = evaluated_mesh(bolt)
check(len(mesh.vertices) == 4 * 8, f"radial array makes 4 copies of 8 vertices: {len(mesh.vertices)}")
centers = {
    (round(c.x, 2), round(c.y, 2))
    for c in [sum((v.co for v in mesh.vertices[i * 8 : (i + 1) * 8]), Vector()) / 8 for i in range(4)]
}
check(centers == {(3.0, 0.0), (0.0, 3.0), (-3.0, 0.0), (0.0, -3.0)}, f"the copies sit around the origin: {centers}")
bpy.data.meshes.remove(mesh)
check(bpy.data.objects.get("HS Radial Center Bolt") is not None, "the radial center is an empty child")

# ---- sharp edges and shading
box = cube("Sharp")
only(box)
check(meshtools.mark_sharp(box, math.radians(30)) == 12, "all 12 edges of a cube are sharp")
check(sum(1 for e in box.data.edges if not e.use_edge_sharp) == 0, "they are flagged sharp on the mesh")
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3)
ball = bpy.context.object
check(meshtools.mark_sharp(ball, math.radians(30), False) == 0, "a smooth sphere has no sharp edges")

# ---- grooves and panels
slab = cube("Slab")
only(slab)
bpy.ops.object.mode_set(mode="EDIT")
bm = bmesh.from_edit_mesh(slab.data)
for f in bm.faces:
    f.select_set(f.normal.z > 0.9)
bmesh.update_edit_mesh(slab.data)
s.groove_width, s.groove_depth = 0.2, 0.05
check(bpy.ops.hardsurface_kit.groove(raised=False) == {"FINISHED"}, "groove finishes")
bpy.ops.object.mode_set(mode="OBJECT")
check(near(volume(slab), 8.0 - 1.6 * 1.6 * 0.05, 0.001), f"a groove removes inner area x depth: {volume(slab):.4f}")
check(len(slab.data.vertices) == 16, f"the inset adds a ring of vertices: {len(slab.data.vertices)}")
panel = cube("Panel")
only(panel)
bpy.ops.object.mode_set(mode="EDIT")
bm = bmesh.from_edit_mesh(panel.data)
for f in bm.faces:
    f.select_set(f.normal.z > 0.9)
bmesh.update_edit_mesh(panel.data)
bpy.ops.hardsurface_kit.groove(raised=True)
bpy.ops.object.mode_set(mode="OBJECT")
check(near(volume(panel), 8.0 + 1.6 * 1.6 * 0.05, 0.001), "a raised panel adds volume")

# ---- cleanup
bpy.ops.mesh.primitive_grid_add(x_subdivisions=6, y_subdivisions=6)
flat = bpy.context.object
only(flat)
before_count = len(flat.data.vertices)
bpy.ops.hardsurface_kit.clean()
check(
    before_count > 40 and len(flat.data.vertices) == 4,
    f"cleanup dissolves a flat grid to one quad: {before_count} -> {len(flat.data.vertices)}",
)
twin = cube("Twin")
other = cube("TwinB")
only(twin, other)
bpy.ops.object.join()
joined = bpy.context.object
check(len(joined.data.vertices) == 16, "two cubes at the same place have doubled vertices")
bpy.ops.hardsurface_kit.clean()
check(len(joined.data.vertices) == 8, f"merge by distance removes the doubles: {len(joined.data.vertices)}")

# ---- apply stack
body = cube("Body")
tool = cube("Tool", (1.0, 0, 0), 1.0)
only(body)
bpy.ops.hardsurface_kit.bevel()
only(body, tool)
bpy.context.view_layer.objects.active = body
bpy.ops.hardsurface_kit.cutter_add()
s.mirror_x = True
only(body)
bpy.ops.hardsurface_kit.mirror()
expected = volume(body)
expected_vertices, _, mesh = stats(body)
bpy.data.meshes.remove(mesh)
check(bpy.ops.hardsurface_kit.finish() == {"FINISHED"}, "apply stack finishes")
check(not body.modifiers and "Tool" not in bpy.data.objects, "no modifiers and no cutter objects remain")
check(
    near(volume(body), expected, 1e-6),
    f"the applied mesh equals the evaluated one: {volume(body):.5f} vs {expected:.5f}",
)
check(len(body.data.vertices) == expected_vertices, "the same vertex count as the evaluated mesh")
check(body.data.has_custom_normals, "custom normals survive the apply")

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Smart Bevel")
prefs.language = "en_US"
check(translated == "Akıllı Bevel", f"Turkish translation active ({translated!r})")

hs.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("OK: hardsurface_kit bevel, cutters, mirror, arrays, grooves, cleanup, apply stack")
