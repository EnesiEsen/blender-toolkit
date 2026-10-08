"""Convex hulls with bmesh, vertex reduction and a simple convex decomposition."""

import bmesh
import numpy as np


def hull(points):
    """Convex hull of a point cloud: (vertices (m, 3), faces, volume)."""
    bm = bmesh.new()
    try:
        for p in points:
            bm.verts.new(p)
        result = bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
        # geom_interior and geom_unused overlap: delete each vertex once
        leftovers = [e for e in result["geom_interior"] + result["geom_unused"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.delete(bm, geom=list(dict.fromkeys(leftovers)), context="VERTS")
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        verts = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        faces = [tuple(v.index for v in f.verts) for f in bm.faces]
        volume = abs(bm.calc_volume())
    finally:
        bm.free()
    return verts, faces, volume


def hull_volume(points):
    return hull(points)[2]


def farthest_points(points, count):
    """`count` well spread points (farthest point sampling), starting from the one farthest from the center."""
    if len(points) <= count:
        return points
    chosen = [int(np.linalg.norm(points - points.mean(axis=0), axis=1).argmax())]
    distance = np.linalg.norm(points - points[chosen[0]], axis=1)
    for _ in range(count - 1):
        index = int(distance.argmax())
        chosen.append(index)
        distance = np.minimum(distance, np.linalg.norm(points - points[index], axis=1))
    return points[chosen]


def limited_hull(points, max_vertices):
    """Convex hull with at most `max_vertices` vertices (the hull of the best spread hull vertices)."""
    verts, faces, volume = hull(points)
    if len(verts) <= max_vertices:
        return verts, faces, volume
    return hull(farthest_points(verts, max_vertices))


def _split(points, fraction):
    _, vectors = np.linalg.eigh(np.cov((points - points.mean(axis=0)).T))
    along = (points - points.mean(axis=0)) @ vectors[:, -1]
    cut = np.quantile(along, fraction)
    margin = 0.02 * max(float(np.ptp(along)), 1e-9)  # the halves overlap a little so no gap opens at the cut
    return points[along <= cut + margin], points[along >= cut - margin]


def decompose(points, parts, max_vertices=64):
    """Split a concave point cloud into up to `parts` clusters whose hulls hug it better than one hull does."""
    clusters = [(points, hull_volume(points))]
    while len(clusters) < parts:
        clusters.sort(key=lambda c: c[1], reverse=True)
        biggest, _ = clusters[0]
        if len(biggest) < 12:
            break
        best = None
        for fraction in (0.35, 0.5, 0.65):
            a, b = _split(biggest, fraction)
            if len(a) < 4 or len(b) < 4:
                continue
            va, vb = hull_volume(a), hull_volume(b)
            if best is None or va + vb < best[0]:
                best = (va + vb, (a, va), (b, vb))
        if best is None:
            break
        clusters = [*clusters[1:], best[1], best[2]]
    return [limited_hull(c[0], max_vertices) for c in clusters]
