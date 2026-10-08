"""Fit simple shapes to a point cloud with numpy. All coordinates are in the object's local space."""

import numpy as np


def mesh_points(obj, depsgraph):
    """(vertices, volume) of the evaluated mesh (modifiers included). The volume is 0 for meshes that are not closed."""
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)
        points = co.reshape(-1, 3).astype(np.float64)
        mesh.calc_loop_triangles()
        count = len(mesh.loop_triangles)
        tri = np.empty(count * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("vertices", tri)
        edges_open = any(e.is_loose for e in mesh.edges) or any(len(p.vertices) < 3 for p in mesh.polygons)
        volume = triangle_volume(points, tri.reshape(-1, 3)) if count and not edges_open else 0.0
    finally:
        evaluated.to_mesh_clear()
    return points, volume


def triangle_volume(points, triangles):
    """Volume enclosed by a closed triangle mesh (absolute value of the signed tetrahedron sum)."""
    a, b, c = points[triangles[:, 0]], points[triangles[:, 1]], points[triangles[:, 2]]
    return abs(float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)


def aabb(points):
    low, high = points.min(axis=0), points.max(axis=0)
    return (low + high) / 2, np.eye(3), (high - low) / 2


def obb(points):
    """Oriented box from the principal axes (PCA); falls back to the axis-aligned box when that is smaller."""
    center = points.mean(axis=0)
    _, vectors = np.linalg.eigh(np.cov((points - center).T))
    axes = vectors[:, ::-1].copy()
    if np.linalg.det(axes) < 0:
        axes[:, 2] *= -1
    projected = (points - center) @ axes
    low, high = projected.min(axis=0), projected.max(axis=0)
    half = (high - low) / 2
    best = (center + axes @ ((low + high) / 2), axes, half)
    plain = aabb(points)
    return plain if np.prod(plain[2]) <= np.prod(half) * 1.0001 else best


def box_fit(points, mode="OBB"):
    return aabb(points) if mode == "AABB" else obb(points)


def bounding_sphere(points, iterations=200):
    """Nearly smallest sphere (Badoiu-Clarkson). Returns (center, radius)."""
    center = (points.min(axis=0) + points.max(axis=0)) / 2
    for i in range(1, iterations + 1):
        far = points[np.linalg.norm(points - center, axis=1).argmax()]
        center = center + (far - center) / (i + 1)
    return center, float(np.linalg.norm(points - center, axis=1).max())


def capsule(points, axis="AUTO"):
    """Capsule around the points: (center, axis vector, radius, half height of the cylinder part)."""
    if axis == "AUTO":
        _, vectors = np.linalg.eigh(np.cov((points - points.mean(axis=0)).T))
        direction = vectors[:, -1]
    else:
        direction = np.eye(3)["XYZ".index(axis)]
    along = points @ direction
    center = points.mean(axis=0)
    mid = (along.max() + along.min()) / 2
    center = center + direction * (mid - center @ direction)
    offsets = points - center
    radial = np.linalg.norm(offsets - np.outer(offsets @ direction, direction), axis=1)
    radius = float(radial.max())
    half_length = float(np.abs(offsets @ direction).max())
    return center, direction, radius, max(half_length - radius, 0.0)
