"""Mesh work with bmesh: sharp edges, shading, grooves and cleanup."""

import contextlib
import math

import bmesh


@contextlib.contextmanager
def bmesh_of(obj):
    """The mesh of the object as a bmesh (the edit mesh while editing); written back on exit."""
    editing = obj.mode == "EDIT"
    bm = bmesh.from_edit_mesh(obj.data) if editing else bmesh.new()
    if not editing:
        bm.from_mesh(obj.data)
    try:
        yield bm
    finally:
        if editing:
            bmesh.update_edit_mesh(obj.data)
        else:
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()


def bevel_layer(bm):
    return bm.edges.layers.float.get("bevel_weight_edge") or bm.edges.layers.float.new("bevel_weight_edge")


def mark_sharp(obj, angle, bevel_weight=True):
    """Mark every edge sharper than `angle` as sharp (and give it a bevel weight). Returns how many edges."""
    with bmesh_of(obj) as bm:
        layer = bevel_layer(bm) if bevel_weight else None
        count = 0
        for edge in bm.edges:
            if len(edge.link_faces) == 2 and edge.calc_face_angle(0.0) > angle:
                edge.smooth = False
                count += 1
                if layer is not None:
                    edge[layer] = 1.0
    return count


def shade_hard(obj, angle):
    """Smooth shading with hard edges where the surface bends more than `angle`. Returns the number of hard edges."""
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return mark_sharp(obj, angle, bevel_weight=False)


def groove(obj, width, depth, raised=False):
    """Inset the selected faces, then push them straight in (a groove) or out (a raised panel).

    The walls are vertical and the edges that bend are marked sharp (with a bevel weight), ready for the bevel modifier.
    Returns the number of faces.
    """
    with bmesh_of(obj) as bm:
        faces = [f for f in bm.faces if f.select]
        if not faces:
            raise ValueError("no faces selected")
        ring = bmesh.ops.inset_region(
            bm, faces=faces, thickness=width, depth=0.0, use_boundary=True, use_even_offset=True
        )
        ring = set(ring["faces"])
        extruded = bmesh.ops.extrude_face_region(bm, geom=faces)["geom"]
        floor = {g for g in extruded if isinstance(g, bmesh.types.BMFace)}
        new_verts = [g for g in extruded if isinstance(g, bmesh.types.BMVert)]
        walls = {f for face in floor for edge in face.edges for f in edge.link_faces if f not in floor}
        push = depth if raised else -depth
        for vert in new_verts:
            normal = sum((f.normal for f in vert.link_faces if f in floor), start=type(vert.co)()).normalized()
            vert.co += normal * push
        bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")
        layer = bevel_layer(bm)
        limit = math.radians(30)
        for face in floor | walls | ring:
            for edge in face.edges:
                if len(edge.link_faces) == 2 and edge.calc_face_angle(0.0) > limit:
                    edge.smooth = False
                    edge[layer] = 1.0
    return len(faces)


def clean(obj, merge_distance, dissolve_angle, quads=False):
    """Merge doubles, drop loose vertices, dissolve flat edges. Returns (vertices before, vertices after)."""
    with bmesh_of(obj) as bm:
        before = len(bm.verts)
        selected = [v for v in bm.verts if v.select]
        scope = selected if (obj.mode == "EDIT" and selected) else bm.verts[:]
        bmesh.ops.remove_doubles(bm, verts=scope, dist=merge_distance)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context="VERTS")
        bm.verts.ensure_lookup_table()
        scope = [v for v in bm.verts if v.select] if (obj.mode == "EDIT" and selected) else bm.verts[:]
        bmesh.ops.dissolve_limit(
            bm, angle_limit=dissolve_angle, verts=scope, edges=list({e for v in scope for e in v.link_edges})
        )
        if quads:
            bmesh.ops.join_triangles(
                bm, faces=bm.faces[:], angle_face_threshold=math.radians(40), angle_shape_threshold=math.radians(40)
            )
        after = len(bm.verts)
    return before, after
