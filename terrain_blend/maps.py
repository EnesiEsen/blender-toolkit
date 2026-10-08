"""Find the texture maps of one PBR set by file name (ambientCG, Poly Haven, Poliigon, Quixel, Substance exports)."""

import os
import re

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga", ".webp", ".bmp")
MAP_TOKENS = {
    "color": {"color", "col", "basecolor", "albedo", "diffuse", "diff"},
    "normal": {"normal", "normalgl", "normaldx", "nor", "nrm", "norm"},
    "rough": {"roughness", "rough"},
    "height": {"height", "displacement", "disp", "bump"},
}


def tokens(filename):
    return set(re.split(r"[^a-z0-9]+", os.path.splitext(filename)[0].lower()))


def find_maps(folder):
    """Return {kind: path} for the maps found in folder; DirectX normals are used only when no OpenGL one exists."""
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(IMAGE_EXT))
    maps = {}
    for kind, keys in MAP_TOKENS.items():
        hits = [f for f in files if tokens(f) & keys]
        if kind == "normal":
            hits.sort(key=lambda f: any(t.endswith("dx") for t in tokens(f)))
        if hits:
            maps[kind] = os.path.join(folder, hits[0])
    return maps


def find_sets(root):
    """Sub-folders of root that hold a color map: [(folder_name, folder_path)], sorted by name."""
    sets = []
    for entry in sorted(os.listdir(root)):
        path = os.path.join(root, entry)
        if os.path.isdir(path) and "color" in find_maps(path):
            sets.append((entry, path))
    return sets
