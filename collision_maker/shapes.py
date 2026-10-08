"""Mesh data of the primitive shapes (vertices and faces, in a canonical frame, then placed)."""

import math

import numpy as np


def lathe(profile, segments):
    """Surface of revolution around Z. `profile` runs from the top pole to the bottom pole as (radius, z)."""
    verts, faces, rings = [], [], []
    for radius, z in profile:
        if radius <= 1e-12:
            verts.append((0.0, 0.0, z))
            rings.append([len(verts) - 1])
        else:
            start = len(verts)
            for k in range(segments):
                angle = 2 * math.pi * k / segments
                verts.append((radius * math.cos(angle), radius * math.sin(angle), z))
            rings.append(list(range(start, start + segments)))
    for upper, lower in zip(rings[:-1], rings[1:], strict=True):
        for k in range(segments):
            k2 = (k + 1) % segments
            if len(upper) == 1:
                faces.append((upper[0], lower[k2], lower[k]))
            elif len(lower) == 1:
                faces.append((upper[k], upper[k2], lower[0]))
            else:
                faces.append((upper[k], upper[k2], lower[k2], lower[k]))
    return np.array(verts, dtype=np.float64), faces


def sphere(radius, segments=16, rings=8):
    profile = [
        (radius * math.sin(math.pi * i / rings), radius * math.cos(math.pi * i / rings)) for i in range(rings + 1)
    ]
    return lathe(profile, segments)


def capsule(radius, half_height, segments=16, rings=4):
    """Capsule along Z: a hemisphere on top, a cylinder of height 2 * half_height, a hemisphere below."""
    quarter = 0.5 * math.pi / rings
    upper = [(radius * math.sin(quarter * i), half_height + radius * math.cos(quarter * i)) for i in range(rings + 1)]
    lower = [(radius * math.cos(quarter * i), -half_height - radius * math.sin(quarter * i)) for i in range(rings + 1)]
    return lathe(upper + (lower if half_height > 1e-9 else lower[1:]), segments)


def box(half):
    sx, sy, sz = half
    verts = np.array([(x * sx, y * sy, z * sz) for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)], dtype=np.float64)
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return verts, faces


def place(verts, center, axes):
    """Move canonical vertices into position: columns of `axes` are the shape's X, Y and Z directions."""
    return verts @ np.asarray(axes).T + np.asarray(center)


def frame_for(direction):
    """A right-handed frame whose Z axis is `direction`."""
    z = np.asarray(direction, dtype=np.float64)
    z = z / np.linalg.norm(z)
    helper = np.array([1.0, 0.0, 0.0]) if abs(z[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    x = np.cross(helper, z)
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(z, x), z], axis=1)
