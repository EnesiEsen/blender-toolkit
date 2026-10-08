"""Export the textures of a material the way Unreal wants them: T_<name>_BC / _N / _ORM / _E, power-of-two sizes."""

import re
from pathlib import Path

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

from . import imaging, material

EXT = {"PNG": ".png", "TARGA": ".tga"}

NOTES = {
    "BC": "Base color. sRGB on, default compression.",
    "N": "Normal map (DirectX, green flipped for Unreal). Compression: Normalmap, sRGB off. Do not flip green again.",
    "ORM": "Red = ambient occlusion, green = roughness, blue = metallic. Compression: Masks (no sRGB), sRGB off.",
    "E": "Emission color. sRGB on.",
}


class ExportError(Exception):
    """A problem the user can act on."""


def clean(name):
    return re.sub(r"[^A-Za-z0-9_]+", "_", re.sub(r"\.\d{3}$", "", name)).strip("_") or "Texture"


def export_material(mat, s, folder):
    """Write the texture set of one material. Returns the list of written paths."""
    info = material.gather(mat)
    name = clean(s.asset_name) if s.asset_name.strip() else clean(mat.name)
    ext, fmt, limit = EXT[s.file_format], s.file_format, int(s.size_limit)
    written, kinds = [], []

    def target(source):
        return imaging.fit_size(*source.size, limit, s.power_of_two)

    def out(kind):
        return folder / f"T_{name}_{kind}{ext}"

    base = info.get("base", {}).get("image")
    if base is not None:
        written.append(imaging.save_scaled_copy(base, *target(base), out("BC"), fmt))
        kinds.append("BC")

    normal = info.get("normal", {}).get("image")
    if normal is not None:
        w, h = target(normal)
        data = imaging.pixels_at(normal, w, h)
        if s.normal_mode == "FLIP":
            data[..., 1] = 1.0 - data[..., 1]
        data[..., 3] = 1.0
        image = imaging.create(f"T_{name}_N", data)
        try:
            written.append(imaging.save(image, out("N"), fmt))
        finally:
            bpy.data.images.remove(image)
        kinds.append("N")

    rough, metal, ao = info.get("rough", {}), info.get("metal", {}), s.ao_image
    sources = [i for i in (ao, rough.get("image"), metal.get("image")) if i is not None]
    if s.pack_orm and sources:
        w, h = imaging.fit_size(max(i.size[0] for i in sources), max(i.size[1] for i in sources), limit, s.power_of_two)
        orm = np.ones((h, w, 4), dtype=np.float32)
        orm[..., 0] = imaging.channel(ao, "R", w, h, 1.0)
        orm[..., 1] = imaging.channel(rough.get("image"), rough.get("channel"), w, h, _scalar(rough, 0.5))
        orm[..., 2] = imaging.channel(metal.get("image"), metal.get("channel"), w, h, _scalar(metal, 0.0))
        image = imaging.create(f"T_{name}_ORM", orm)
        try:
            written.append(imaging.save(image, out("ORM"), fmt))
        finally:
            bpy.data.images.remove(image)
        kinds.append("ORM")

    emission = info.get("emission", {}).get("image")
    if emission is not None:
        written.append(imaging.save_scaled_copy(emission, *target(emission), out("E"), fmt))
        kinds.append("E")

    if written:
        notes = folder / f"T_{name}_import_notes.txt"
        notes.write_text("\n".join(f"T_{name}_{k}{ext}: {NOTES[k]}" for k in kinds) + "\n", encoding="utf-8")
        written.append(notes)
    return written


def _scalar(hit, default):
    value = hit.get("value")
    return float(value) if isinstance(value, (int, float)) else default


def export_object(ob, s):
    """Texture sets of every material of the object. Raises ExportError when nothing can be exported."""
    if not s.export_dir:
        raise ExportError(rpt_("Choose an export folder first."))
    folder = Path(bpy.path.abspath(s.export_dir))
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for mat in dict.fromkeys(slot.material for slot in ob.material_slots if slot.material):
        written += export_material(mat, s, folder)
    if not written:
        raise ExportError(
            rpt_("No image textures are connected to the Principled BSDF of '{name}'.").format(name=ob.name)
        )
    return written
