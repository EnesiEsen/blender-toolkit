"""Create, find, check and remove collision shapes."""

import math
import re

import bmesh
import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Matrix

from . import fit, hulls, shapes

PATTERN = re.compile(r"^(UBX|USP|UCP|UCX)_(.+)_(\d+)$")
COLORS = {
    "UBX": (0.2, 0.6, 1.0, 1.0),
    "USP": (0.2, 1.0, 0.6, 1.0),
    "UCP": (1.0, 0.8, 0.2, 1.0),
    "UCX": (1.0, 0.4, 0.2, 1.0),
}
PREFIX = {"BOX": "UBX", "SPHERE": "USP", "CAPSULE": "UCP", "CONVEX": "UCX", "DECOMPOSE": "UCX"}
ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"


def is_shape(obj):
    return obj.type == "MESH" and PATTERN.match(obj.name) is not None


def shapes_of(mesh_obj):
    """Collision objects that belong to a mesh: its children and objects named after it."""
    found = {c for c in mesh_obj.children if is_shape(c)}
    for other in bpy.data.objects:
        match = PATTERN.match(other.name) if other.type == "MESH" else None
        if match and match.group(2) == mesh_obj.name:
            found.add(other)
    return sorted(found, key=lambda o: o.name)


def remove_shapes(mesh_obj):
    count = 0
    for shape in shapes_of(mesh_obj):
        data = shape.data
        bpy.data.objects.remove(shape)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
        count += 1
    return count


def auto_kind(points, volume, settings):
    """Pick the simplest shape that fits: box, sphere, capsule, convex hull or convex parts."""
    _, _, half = fit.box_fit(points, "OBB")
    if volume > 0:
        if volume / (8.0 * float(np.prod(half))) > 0.85:
            return "BOX"
        _, radius = fit.bounding_sphere(points)
        if volume / (4.0 / 3.0 * math.pi * radius**3) > 0.7:
            return "SPHERE"
        _, _, cap_radius, cap_half = fit.capsule(points)
        cap_volume = math.pi * cap_radius**2 * 2 * cap_half + 4.0 / 3.0 * math.pi * cap_radius**3
        if volume / cap_volume > 0.8:
            return "CAPSULE"
        if hulls.hull_volume(points) / volume > 1.25:
            return "DECOMPOSE"
    return "CONVEX"


def build_shapes(kind, points, settings):
    """[(prefix, vertices, faces)] in the object's local space."""
    prefix = PREFIX[kind]
    if kind == "BOX":
        center, axes, half = fit.box_fit(points, settings.box_fit)
        verts, faces = shapes.box(half)
        return [(prefix, shapes.place(verts, center, axes), faces)]
    if kind == "SPHERE":
        center, radius = fit.bounding_sphere(points)
        verts, faces = shapes.sphere(radius)
        return [(prefix, verts + center, faces)]
    if kind == "CAPSULE":
        center, direction, radius, half_height = fit.capsule(points, settings.capsule_axis)
        verts, faces = shapes.capsule(radius, half_height)
        return [(prefix, shapes.place(verts, center, shapes.frame_for(direction)), faces)]
    if kind == "CONVEX":
        verts, faces, _ = hulls.limited_hull(points, settings.max_vertices)
        return [(prefix, verts, faces)]
    return [(prefix, v, f) for v, f, _ in hulls.decompose(points, settings.parts, settings.max_vertices)]


def make_object(mesh_obj, name, verts, faces, prefix):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    shape = bpy.data.objects.new(name, mesh)
    for collection in mesh_obj.users_collection or [bpy.context.scene.collection]:
        collection.objects.link(shape)
    shape.parent = mesh_obj  # same transform as the mesh: coordinates are the mesh's local ones
    shape.display_type = "WIRE"
    shape.show_wire = True
    shape.hide_render = True
    shape.color = COLORS[prefix]
    return shape


def unique_name(prefix, base, index):
    while True:
        name = f"{prefix}_{base}_{index:02d}"
        if name not in bpy.data.objects:
            return name
        index += 1


def create(context, mesh_obj, settings):
    """Create the shapes of one mesh object. Returns the new objects. Raises ValueError on unusable meshes."""
    if mesh_obj.type != "MESH" or is_shape(mesh_obj):
        raise ValueError(rpt_("'{name}' is not a mesh that can get collision.").format(name=mesh_obj.name))
    points, volume = fit.mesh_points(mesh_obj, context.evaluated_depsgraph_get())
    if len(points) < 4:
        raise ValueError(rpt_("'{name}' has too few vertices.").format(name=mesh_obj.name))
    kind = auto_kind(points, volume, settings) if settings.shape == "AUTO" else settings.shape
    specs = build_shapes(kind, points, settings)
    if settings.replace:
        remove_shapes(mesh_obj)
    created = []
    for index, (prefix, verts, faces) in enumerate(specs):
        created.append(make_object(mesh_obj, unique_name(prefix, mesh_obj.name, index), verts, faces, prefix))
    return created


def issue(severity, code, obj, message, fixable=False):
    return {"severity": severity, "code": code, "object": obj.name, "message": message, "fixable": fixable}


def has_own_transform(shape):
    """True when a shape's location, rotation or scale differ from its parent's (the shapes made here have none)."""
    identity = Matrix.Identity(4)
    return any(
        abs(a - b) > 1e-4
        for ra, rb in zip(shape.matrix_basis, identity, strict=True)
        for a, b in zip(ra, rb, strict=True)
    )


def shape_volumes(shape):
    mesh = shape.data
    points = np.array([v.co[:] for v in mesh.vertices], dtype=np.float64)
    return points, fit.triangle_volume(points, _triangles(mesh)) if len(mesh.polygons) else 0.0


def _triangles(mesh):
    mesh.calc_loop_triangles()
    tri = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", tri)
    return tri.reshape(-1, 3)


def scan(objects):
    """Problems of every collision shape in the scene, plus naming problems of the meshes that have shapes."""
    found = []
    shapes_seen = [o for o in objects if is_shape(o)]
    for shape in shapes_seen:
        kind, base = PATTERN.match(shape.name).group(1), PATTERN.match(shape.name).group(2)
        target = (
            shape.parent if shape.parent is not None and shape.parent.type == "MESH" else bpy.data.objects.get(base)
        )
        if target is None:
            found.append(
                issue(
                    ERROR,
                    "ORPHAN",
                    shape,
                    rpt_(
                        "'{name}' belongs to no mesh: Unreal ignores it. Parent it to its mesh or fix the name."
                    ).format(name=shape.name),
                )
            )
        if shape.parent is not None and has_own_transform(shape):
            found.append(
                issue(
                    WARNING,
                    "TRANSFORM",
                    shape,
                    rpt_("'{name}' has its own transform: apply it so Unreal puts the shape right.").format(
                        name=shape.name
                    ),
                    fixable=True,
                )
            )
        points, volume = shape_volumes(shape)
        if kind == "UBX" and len(shape.data.vertices) != 8:
            found.append(
                issue(
                    WARNING,
                    "NOT_BOX",
                    shape,
                    rpt_("'{name}' is a box shape but has {count} vertices instead of 8.").format(
                        name=shape.name, count=len(shape.data.vertices)
                    ),
                )
            )
        if kind == "UCX":
            if len(shape.data.vertices) > 255:
                found.append(
                    issue(
                        ERROR,
                        "TOO_MANY",
                        shape,
                        rpt_("'{name}' has {count} vertices: Unreal accepts 255 at most.").format(
                            name=shape.name, count=len(shape.data.vertices)
                        ),
                        fixable=True,
                    )
                )
            if volume > 0 and len(points) >= 4 and hulls.hull_volume(points) > volume * 1.03:
                found.append(
                    issue(
                        ERROR,
                        "NONCONVEX",
                        shape,
                        rpt_("'{name}' is not convex: Unreal would use its hull.").format(name=shape.name),
                        fixable=True,
                    )
                )
    for mesh_obj in {s.parent for s in shapes_seen if s.parent is not None}:
        if re.search(r"[. ]", mesh_obj.name):
            found.append(
                issue(
                    WARNING,
                    "NAME",
                    mesh_obj,
                    rpt_(
                        "'{name}' contains a dot or space: Unreal may not match its collision shapes. Rename it."
                    ).format(name=mesh_obj.name),
                )
            )
    return found


def fix(shape, max_vertices, code="NONCONVEX"):
    """Fix one reported problem: TRANSFORM applies the shape's own transform, anything else swaps in a convex hull."""
    if code == "TRANSFORM":
        shape.data.transform(shape.matrix_basis)
        shape.matrix_basis = Matrix.Identity(4)
        shape.data.update()
        return
    points = np.array([v.co[:] for v in shape.data.vertices], dtype=np.float64)
    verts, faces, _ = hulls.limited_hull(points, max_vertices)
    mesh = shape.data
    mesh.clear_geometry()
    mesh.from_pydata(verts.tolist(), [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
