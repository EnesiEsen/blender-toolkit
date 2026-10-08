"""Scale UV islands so that they get a given texel density."""

import bmesh
import numpy as np

from . import density


def find_islands(faces, uv_layer, eps=1e-5):
    """Group faces into UV islands: neighbours that share an edge and have the same UV coordinates on it."""
    index = {face: i for i, face in enumerate(faces)}
    parent = list(range(len(faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    limit = eps * eps
    for face in faces:
        for loop in face.loops:
            other = loop.link_loop_radial_next
            if other is loop or other.face not in index:
                continue
            a0, a1 = loop[uv_layer].uv, loop.link_loop_next[uv_layer].uv
            b0, b1 = other.link_loop_next[uv_layer].uv, other[uv_layer].uv
            if (a0 - b0).length_squared < limit and (a1 - b1).length_squared < limit:
                parent[find(index[face])] = find(index[other.face])
    groups = {}
    for face in faces:
        groups.setdefault(find(index[face]), []).append(face)
    return list(groups.values())


def island_bounds(island, uv_layer):
    coords = np.array([loop[uv_layer].uv[:] for face in island for loop in face.loops])
    return coords.min(axis=0), coords.max(axis=0)


def scale_island(island, uv_layer, factor, pivot):
    px, py = pivot
    for face in island:
        for loop in face.loops:
            uv = loop[uv_layer].uv
            uv.x = px + (uv.x - px) * factor
            uv.y = py + (uv.y - py) * factor


def apply_density(obj, target, mode="ISLAND", default_size=2048, selected_only=False):
    """Scale the UV islands of a mesh object to the target density. Returns {"islands": n, "scaled": n}."""
    mesh = obj.data
    editing = obj.mode == "EDIT"
    if editing:
        obj.update_from_editmode()
    data = density.analyze(obj, default_size)
    bm = bmesh.from_edit_mesh(mesh) if editing else bmesh.new()
    if not editing:
        bm.from_mesh(mesh)
    try:
        uv_layer = bm.loops.layers.uv.active
        bm.faces.ensure_lookup_table()
        faces = [f for f in bm.faces if not f.hide and (f.select or not (editing and selected_only))]
        islands = find_islands(faces, uv_layer)
        scaled = 0
        if mode == "OBJECT":
            ids = [f.index for f in faces]
            px, area = data["px"][ids].sum(), data["area"][ids].sum()
            if px <= 0 or area <= 0:
                return {"islands": len(islands), "scaled": 0}
            factor = target / float(np.sqrt(px / area))
            bounds = [island_bounds(i, uv_layer) for i in islands]
            pivot = (0.0, 0.0)
            if bounds:
                low, high = np.min([b[0] for b in bounds], axis=0), np.max([b[1] for b in bounds], axis=0)
                pivot = tuple((low + high) / 2)
            for island in islands:
                scale_island(island, uv_layer, factor, pivot)
                scaled += 1
        else:
            for island in islands:
                ids = [f.index for f in island]
                px, area = data["px"][ids].sum(), data["area"][ids].sum()
                if px <= 0 or area <= 0:
                    continue
                low, high = island_bounds(island, uv_layer)
                scale_island(
                    island,
                    uv_layer,
                    target / float(np.sqrt(px / area)),
                    ((low[0] + high[0]) / 2, (low[1] + high[1]) / 2),
                )
                scaled += 1
        if editing:
            bmesh.update_edit_mesh(mesh)
        else:
            bm.to_mesh(mesh)
            mesh.update()
        return {"islands": len(islands), "scaled": scaled}
    finally:
        if not editing:
            bm.free()
