"""Texel density maths with numpy: how many texture pixels cover one meter of surface (px/m, world space)."""

import numpy as np

COLOR_ATTRIBUTE = "TD_Density"


def base_color_image(material):
    """The image behind the Base Color of a material, else the first image texture in it."""
    if material is None or material.node_tree is None:
        return None
    nodes = material.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None and "Base Color" in bsdf.inputs:
        socket = bsdf.inputs["Base Color"]
        for _ in range(8):
            if not socket.is_linked:
                break
            node = socket.links[0].from_node
            if node.type == "TEX_IMAGE":
                return node.image
            socket = next((i for i in node.inputs if i.is_linked), None)
            if socket is None:
                break
    return next((n.image for n in nodes if n.type == "TEX_IMAGE" and n.image), None)


def slot_sizes(obj, default):
    """(width, height) of the base color texture of every material slot of the object."""
    sizes = []
    for slot in obj.material_slots:
        image = base_color_image(slot.material)
        if image is not None and image.size[0] and image.size[1]:
            sizes.append((float(image.size[0]), float(image.size[1])))
        else:
            sizes.append((float(default), float(default)))
    return sizes or [(float(default), float(default))]


def analyze(obj, default_size=2048):
    """Texel density of every polygon of a mesh object.

    Returns a dict of numpy arrays per polygon (area in square meters, UV area, pixel area, density in px/m, UV center)
    and the totals. Raises ValueError when the mesh has no UV map or no faces.
    """
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise ValueError(f"'{obj.name}' has no UV map.")
    mesh.calc_loop_triangles()
    triangles = mesh.loop_triangles
    count = len(triangles)
    if not count:
        raise ValueError(f"'{obj.name}' has no faces.")

    verts = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", verts)
    matrix = np.array(obj.matrix_world, dtype=np.float64)
    world = verts.reshape(-1, 3).astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]
    world *= obj.users_scene[0].unit_settings.scale_length if obj.users_scene else 1.0

    tri_verts = np.empty(count * 3, dtype=np.int32)
    tri_loops = np.empty(count * 3, dtype=np.int32)
    tri_poly = np.empty(count, dtype=np.int32)
    triangles.foreach_get("vertices", tri_verts)
    triangles.foreach_get("loops", tri_loops)
    triangles.foreach_get("polygon_index", tri_poly)
    p = world[tri_verts.reshape(-1, 3)]
    area3d = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)

    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    uv_layer.uv.foreach_get("vector", uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    t = uv[tri_loops.reshape(-1, 3)]
    ab, ac = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
    area_uv = 0.5 * np.abs(ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0])

    poly_count = len(mesh.polygons)
    material_index = np.empty(poly_count, dtype=np.int32)
    mesh.polygons.foreach_get("material_index", material_index)
    sizes = np.array(slot_sizes(obj, default_size))
    material_index = np.clip(material_index, 0, len(sizes) - 1)
    texture_px = sizes[material_index, 0] * sizes[material_index, 1]

    poly_area = np.bincount(tri_poly, weights=area3d, minlength=poly_count)
    poly_uv = np.bincount(tri_poly, weights=area_uv, minlength=poly_count)
    poly_px = poly_uv * texture_px
    valid = poly_area > 1e-12
    density = np.zeros(poly_count)
    density[valid] = np.sqrt(poly_px[valid] / poly_area[valid])

    starts = np.empty(poly_count, dtype=np.int32)
    totals = np.empty(poly_count, dtype=np.int32)
    mesh.polygons.foreach_get("loop_start", starts)
    mesh.polygons.foreach_get("loop_total", totals)
    center = np.add.reduceat(uv, starts, axis=0) / totals[:, None]

    total_area = poly_area[valid].sum()
    average = float(np.sqrt(poly_px[valid].sum() / total_area)) if total_area > 0 else 0.0
    return {
        "area": poly_area,
        "uv_area": poly_uv,
        "px": poly_px,
        "density": density,
        "center": center,
        "valid": valid,
        "average": average,
    }


def summary(data, target, tolerance_percent):
    """Numbers for the panel: min, max, average, how much of the surface is within tolerance, UV use."""
    density, valid, area = data["density"], data["valid"], data["area"]
    unwrapped = valid & (data["uv_area"] > 1e-12)
    d = density[unwrapped]
    inside_tile = (data["center"] >= 0).all(axis=1) & (data["center"] <= 1).all(axis=1)
    band = tolerance_percent / 100.0
    ok = unwrapped & (np.abs(density - target) <= target * band)
    total = area[valid].sum()
    return {
        "faces": int(len(density)),
        "average": data["average"],
        "minimum": float(d.min()) if len(d) else 0.0,
        "maximum": float(d.max()) if len(d) else 0.0,
        "coverage": float(data["uv_area"][inside_tile].sum() * 100.0),
        "outside": int((~inside_tile).sum()),
        "flagged": float(100.0 * (1.0 - area[ok].sum() / total)) if total > 0 else 0.0,
        "unwrapped": int(len(density) - unwrapped.sum()),
    }


def hsv_to_rgb(h, s, v):
    i = np.floor(h * 6.0)
    f = h * 6.0 - i
    i = i.astype(int) % 6
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [v, q, p, p, t], default=v)
    g = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [t, v, v, q, p], default=p)
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4], [p, p, t, v, v], default=q)
    return np.stack([r, g, b], axis=-1)


def colors(density, target):
    """Blue = too low, green = on target, red = too high (a factor of two either way saturates)."""
    ratio = np.maximum(density, 1e-6) / target
    shift = np.clip(np.log2(ratio), -1.0, 1.0)
    rgb = hsv_to_rgb((1.0 - shift) / 3.0, np.full_like(shift, 0.85), np.full_like(shift, 0.9))
    rgb[density <= 0] = (0.35, 0.35, 0.35)
    return rgb


def show_colors(obj, data, target):
    """Write the per-face colors into a face-corner color attribute and make it the active one."""
    mesh = obj.data
    existing = mesh.color_attributes.get(COLOR_ATTRIBUTE)
    if existing is not None:
        mesh.color_attributes.remove(existing)
    attribute = mesh.color_attributes.new(COLOR_ATTRIBUTE, "FLOAT_COLOR", "CORNER")
    totals = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_total", totals)
    rgba = np.ones((len(mesh.polygons), 4), dtype=np.float32)
    rgba[:, :3] = colors(data["density"], target)
    attribute.data.foreach_set("color", np.repeat(rgba, totals, axis=0).ravel())
    mesh.color_attributes.active_color = attribute
    mesh.update()
    return attribute


def hide_colors(obj):
    attribute = obj.data.color_attributes.get(COLOR_ATTRIBUTE)
    if attribute is not None:
        obj.data.color_attributes.remove(attribute)
        return True
    return False
