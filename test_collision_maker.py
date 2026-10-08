"""Self-check for collision_maker. Run it with `python tools/bdev.py check blender-toolkit/collision_maker`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_collision_maker.py

Checks the shape fits against known geometry (rotated box, sphere, capsule), that every hull is really convex and within
its vertex limit, that decomposition hugs an L-shaped mesh better than one hull, the Unreal naming, parenting and Auto
choice, and the checker with its fixes.
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "collision_maker")
spec = importlib.util.spec_from_file_location(
    "collision_maker", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
cm = importlib.util.module_from_spec(spec)
sys.modules["collision_maker"] = cm
spec.loader.exec_module(cm)
from collision_maker import core, fit, hulls, shapes  # noqa: E402  (needs the module registered above)

cm.register()
failures = []
rng = np.random.default_rng(7)


def check(condition, message):
    if not condition:
        failures.append(message)


def near(a, b, tol=0.02):
    return abs(a - b) <= tol * max(abs(b), 1e-9)


def rotation(angle_x, angle_y, angle_z):
    return np.array(
        Matrix.Rotation(angle_z, 3, "Z") @ Matrix.Rotation(angle_y, 3, "Y") @ Matrix.Rotation(angle_x, 3, "X")
    )


def corners(half):
    return np.array(
        [(x * half[0], y * half[1], z * half[2]) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float
    )


# ---- pure fits
R = rotation(0.4, 0.3, 0.7)
box_points = corners((1.0, 0.5, 2.0)) @ R.T + np.array([3.0, -1.0, 2.0])
center, axes, half = fit.obb(box_points)
check(
    np.allclose(sorted(half), [0.5, 1.0, 2.0], atol=1e-6),
    f"oriented box finds the half extents of a rotated box: {sorted(half)}",
)
check(np.allclose(center, [3.0, -1.0, 2.0], atol=1e-6), "oriented box finds the center")
check(np.prod(fit.aabb(box_points)[2]) > np.prod(half) * 1.5, "an axis-aligned box of a rotated box is much looser")

phi = rng.uniform(0, 2 * math.pi, 400)
cos_t = rng.uniform(-1, 1, 400)
sphere_points = 2.0 * np.stack(
    [np.sqrt(1 - cos_t**2) * np.cos(phi), np.sqrt(1 - cos_t**2) * np.sin(phi), cos_t], axis=1
) + [1, 2, 3]
c, r = fit.bounding_sphere(sphere_points)
check(near(r, 2.0, 0.02) and np.allclose(c, [1, 2, 3], atol=0.05), f"bounding sphere: radius {r:.3f}, center {c}")

cap_verts, _ = shapes.capsule(0.5, 1.5)
cap_points = cap_verts @ rotation(0.0, 1.0, 0.5).T + [0.5, 0.5, 0.5]
c, direction, radius, half_height = fit.capsule(cap_points)
check(
    near(radius, 0.5, 0.03) and near(half_height, 1.5, 0.03),
    f"capsule fit: r {radius:.3f}, half height {half_height:.3f}",
)
check(abs(abs(direction @ (rotation(0.0, 1.0, 0.5) @ [0, 0, 1])) - 1.0) < 1e-3, "capsule finds its axis")

# ---- hulls: convex, within the vertex limit, volume sane
cloud = rng.normal(size=(300, 3)) * [1.0, 0.6, 0.3]
verts, faces, volume = hulls.hull(cloud)
worst = 0.0
for face in faces:
    p0, p1, p2 = verts[face[0]], verts[face[1]], verts[face[2]]
    normal = np.cross(p1 - p0, p2 - p0)
    normal /= np.linalg.norm(normal)
    worst = max(worst, float(((verts - p0) @ normal).max()))
check(worst < 1e-6, f"every hull face has all vertices behind it (max {worst:.2e})")
limited, _, limited_volume = hulls.limited_hull(cloud, 24)
check(len(limited) <= 24, f"limited hull has at most 24 vertices ({len(limited)})")
check(
    0.7 * volume < limited_volume <= volume * 1.0001,
    f"reducing vertices keeps most of the volume ({limited_volume / volume:.2f})",
)


# ---- decomposition of an L shape (area 3 thick 1; one hull has 3.5)
def box_surface(half, center, count=120):
    """Random points on the six faces of a box, like the vertices of a real mesh surface."""
    points = []
    for axis in range(3):
        for sign in (-1, 1):
            p = rng.uniform(-1, 1, (count, 3)) * half
            p[:, axis] = sign * half[axis]
            points.append(p)
    return np.concatenate(points) + center


dense = np.concatenate([box_surface((1.0, 0.5, 0.5), (1.0, 0.0, 0.5)), box_surface((0.5, 0.5, 1.0), (0.5, 0.0, 1.0))])
single = hulls.hull_volume(dense)
parts = hulls.decompose(dense, 4, 64)


def inside_hull(samples, verts, faces):
    """Points of `samples` that lie inside the convex hull (all face planes agree)."""
    middle = verts.mean(axis=0)
    ok = np.ones(len(samples), dtype=bool)
    for face in faces:
        p0 = verts[face[0]]
        normal = np.cross(verts[face[1]] - p0, verts[face[2]] - p0)
        if np.dot(normal, middle - p0) > 0:
            normal = -normal
        ok &= (samples - p0) @ normal <= 1e-9
    return ok


samples = rng.uniform([0, -0.5, 0], [2, 0.5, 2], (40000, 3))
in_l = (samples[:, 0] <= 1.0) | (
    samples[:, 2] <= 1.0
)  # the L: the part of the 2 x 2 square that is not the empty corner
covered = np.zeros(len(samples), dtype=bool)
for verts_p, faces_p, _ in parts:
    covered |= inside_hull(samples, verts_p, faces_p)
union = covered.mean() * 4.0  # sample box volume is 2 * 1 * 2
check(
    2.9 <= union <= single - 0.1,
    f"convex parts follow the L better than one hull: union {union:.3f} vs one hull {single:.3f}",
)
check(covered[in_l].mean() > 0.97, f"the parts cover the L ({covered[in_l].mean():.3f})")

# ---- the operator on real objects
sc = bpy.context.scene
s = sc.cm_settings


def select_only(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


bpy.ops.mesh.primitive_cube_add(size=2)
crate = bpy.context.object
crate.name = "Crate"
crate.scale = (1.0, 0.5, 2.0)
crate.rotation_euler = (0.2, 0.3, 0.4)
crate.location = (5, 0, 0)
bpy.context.view_layer.update()
select_only(crate)
s.shape, s.box_fit, s.replace = "BOX", "OBB", True
check(bpy.ops.collision_maker.create() == {"FINISHED"}, "create finishes")
box = bpy.data.objects.get("UBX_Crate_00")
check(box is not None and box.parent == crate, "box is named UBX_<mesh>_00 and parented to the mesh")
check(box is not None and box.display_type == "WIRE" and box.hide_render, "shapes are wire and hidden from renders")
check(
    box is not None and np.allclose(np.array(box.matrix_world), np.array(crate.matrix_world), atol=1e-5),
    "the shape shares the mesh transform",
)
points, volume = core.shape_volumes(box)
_, mesh_volume = fit.mesh_points(crate, bpy.context.evaluated_depsgraph_get())
check(near(volume, mesh_volume, 0.01), f"the box has the volume of the box mesh: {volume:.3f} vs {mesh_volume:.3f}")
check(
    bpy.ops.collision_maker.create() == {"FINISHED"} and len(core.shapes_of(crate)) == 1,
    "Replace Existing keeps one shape",
)

s.shape = "SPHERE"
bpy.ops.collision_maker.create()
sphere_obj = bpy.data.objects.get("USP_Crate_00")
check(sphere_obj is not None and len(core.shapes_of(crate)) == 1, "sphere replaces the box and is named USP_")

s.shape = "CAPSULE"
bpy.ops.collision_maker.create()
check(bpy.data.objects.get("UCP_Crate_00") is not None, "capsule is named UCP_")

s.shape, s.max_vertices = "CONVEX", 16
bpy.ops.collision_maker.create()
hull_obj = bpy.data.objects.get("UCX_Crate_00")
check(hull_obj is not None and len(hull_obj.data.vertices) <= 16, "convex hull respects Max Vertices")


# ---- auto choice
def fresh(kind, **kw):
    getattr(bpy.ops.mesh, kind)(**kw)
    ob = bpy.context.object
    select_only(ob)
    return ob


s.shape, s.replace, s.max_vertices = "AUTO", True, 64
cube = fresh("primitive_cube_add", size=2)
cube.name = "AutoCube"
bpy.ops.collision_maker.create()
check(bpy.data.objects.get("UBX_AutoCube_00") is not None, "auto picks a box for a cube")
ball = fresh("primitive_uv_sphere_add", radius=1.0)
ball.name = "AutoBall"
bpy.ops.collision_maker.create()
check(bpy.data.objects.get("USP_AutoBall_00") is not None, "auto picks a sphere for a sphere")
pole = fresh("primitive_cylinder_add", radius=0.5, depth=4.0)
pole.name = "AutoPole"
bpy.ops.collision_maker.create()
check(bpy.data.objects.get("UCP_AutoPole_00") is not None, "auto picks a capsule for a long cylinder")
donut = fresh("primitive_torus_add", major_radius=2.0, minor_radius=0.5)
donut.name = "AutoDonut"
s.parts = 6
bpy.ops.collision_maker.create()
parts_made = core.shapes_of(donut)
check(
    len(parts_made) >= 3 and all(o.name.startswith("UCX_") for o in parts_made),
    f"auto splits a torus into convex parts ({len(parts_made)})",
)

# ---- checker and fixes
bpy.ops.collision_maker.check()
check(len(sc.cm_issues) == 0, f"fresh shapes are clean: {[i.message for i in sc.cm_issues]}")
orphan = bpy.data.objects.new("UCX_Nobody_00", bpy.data.meshes.new("orphan"))
sc.collection.objects.link(orphan)
orphan.data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], [], [(0, 2, 1), (0, 1, 3), (1, 2, 3), (0, 3, 2)])
dented = bpy.data.objects.new("UCX_AutoCube_07", bpy.data.meshes.new("dented"))
sc.collection.objects.link(dented)
dented.parent = cube
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bm.verts.ensure_lookup_table()
bm.verts[0].co *= 0.2  # pull one corner in: the shape is no longer convex
bm.to_mesh(dented.data)
bm.free()
dotted = fresh("primitive_cube_add", size=1)
dotted.name = "Has.Dot"
bpy.ops.collision_maker.create()
bpy.ops.collision_maker.check()
codes = {(i.code, i.object_name) for i in sc.cm_issues}
check(("ORPHAN", "UCX_Nobody_00") in codes, f"an orphan shape is reported: {sorted(codes)}")
check(("NONCONVEX", "UCX_AutoCube_07") in codes, "a non-convex hull is reported")
check(("NAME", "Has.Dot") in codes, "a mesh name with a dot is reported")
index = next(i for i, item in enumerate(sc.cm_issues) if item.code == "NONCONVEX")
bpy.ops.collision_maker.fix(index=index)
points, volume = core.shape_volumes(dented)
check(hulls.hull_volume(points) <= volume * 1.001, "Fix makes the shape convex")

# ---- an unapplied transform on a shape is reported and applied by Fix
moved = bpy.data.objects.new("UCX_AutoCube_08", bpy.data.meshes.new("moved"))
sc.collection.objects.link(moved)
moved.parent = cube
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bm.to_mesh(moved.data)
bm.free()
moved.location, moved.scale = (1.0, 2.0, 3.0), (2.0, 1.0, 1.0)
bpy.context.view_layer.update()
before = sorted(tuple(round(c, 5) for c in (moved.matrix_world @ v.co)) for v in moved.data.vertices)
bpy.ops.collision_maker.check()
codes = {(i.code, i.object_name) for i in sc.cm_issues}
check(("TRANSFORM", "UCX_AutoCube_08") in codes, f"an unapplied shape transform is reported: {sorted(codes)}")
index = next(i for i, item in enumerate(sc.cm_issues) if item.code == "TRANSFORM")
bpy.ops.collision_maker.fix(index=index)
bpy.context.view_layer.update()
after = sorted(tuple(round(c, 5) for c in (moved.matrix_world @ v.co)) for v in moved.data.vertices)
check(before == after, "Fix applies the transform without moving the shape")
check(not core.has_own_transform(moved), "the shape's own transform is identity afterwards")
bpy.ops.collision_maker.check()
check(
    ("TRANSFORM", "UCX_AutoCube_08") not in {(i.code, i.object_name) for i in sc.cm_issues},
    "the transform report is gone after Fix",
)

# ---- remove and toggle
select_only(crate)
bpy.ops.collision_maker.remove()
check(not core.shapes_of(crate), "Remove Collision deletes the shapes of the mesh")
bpy.ops.collision_maker.toggle()
check(all(o.hide_get() for o in sc.objects if core.is_shape(o)), "toggle hides every shape")
bpy.ops.collision_maker.toggle()
check(not any(o.hide_get() for o in sc.objects if core.is_shape(o)), "toggle shows them again")

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Create Collision")
prefs.language = "en_US"
check(translated == "Çarpışma Oluştur", f"Turkish translation active ({translated!r})")

cm.unregister()
if failures:
    print("FAIL\n" + "\n".join(f for f in failures if f))
    sys.exit(1)
print("OK: collision_maker fits, hulls, decomposition, naming, auto, checker")
