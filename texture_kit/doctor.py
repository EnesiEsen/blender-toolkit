"""The texture Doctor: finds what makes Unreal import a texture wrongly (color space, size, missing data)."""

from bpy.app.translations import pgettext_rpt as rpt_

from . import imaging, material

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"
DATA_ROLES = ("normal", "rough", "metal")
COLOR_ROLES = ("base", "emission")
DATA_SPACES = ("Non-Color", "Raw")


def issue(severity, code, image, message, fixable=False):
    return {"severity": severity, "code": code, "image": image.name, "message": message, "fixable": fixable}


def check(role, image, max_size):
    """Problems of one image that is used as `role`."""
    width, height = image.size
    if not width or not height:
        return [
            issue(
                ERROR,
                "MISSING",
                image,
                rpt_("'{name}' has no pixel data: the file is missing or unreadable.").format(name=image.name),
            )
        ]
    found = []
    space = image.colorspace_settings.name
    if role in DATA_ROLES and space not in DATA_SPACES:
        found.append(
            issue(
                ERROR,
                "COLORSPACE",
                image,
                rpt_("'{name}' holds data ({role}) but its color space is {space}: set it to Non-Color.").format(
                    name=image.name, role=role, space=space
                ),
                fixable=True,
            )
        )
    if role in COLOR_ROLES and not space.startswith("sRGB"):
        found.append(
            issue(
                ERROR,
                "COLORSPACE",
                image,
                rpt_("'{name}' is a color texture but its color space is {space}: set it to sRGB.").format(
                    name=image.name, space=space
                ),
                fixable=True,
            )
        )
    if not (imaging.is_pow2(width) and imaging.is_pow2(height)):
        found.append(
            issue(
                WARNING,
                "NOT_POW2",
                image,
                rpt_(
                    "'{name}' is {w} x {h}, not a power of two: Unreal cannot stream it. Export Texture Set resizes it."
                ).format(name=image.name, w=width, h=height),
            )
        )
    if max(width, height) > max_size:
        found.append(
            issue(
                WARNING,
                "TOO_LARGE",
                image,
                rpt_("'{name}' is {w} x {h}, above {limit}. Export Texture Set scales it down.").format(
                    name=image.name, w=width, h=height, limit=max_size
                ),
            )
        )
    return found


def scan(objects, max_size):
    """Check every image that feeds the material inputs of the given objects."""
    found, seen = [], set()
    for ob in objects:
        for slot in ob.material_slots:
            for role, hit in material.gather(slot.material).items():
                image = hit["image"]
                if image is None or (image.name, role) in seen:
                    continue
                seen.add((image.name, role))
                found += check(role, image, max_size)
    return found


def fix(image_name, code, images):
    """Apply the automatic fix of one issue. Only color spaces are fixed: sizes are handled by the export."""
    image = images.get(image_name)
    if image is None:
        raise ValueError(rpt_("The image no longer exists."))
    if code != "COLORSPACE":
        raise ValueError(rpt_("This problem cannot be fixed automatically."))
    roles = set(_roles_of(image))
    imaging.set_colorspace(image, "Non-Color" if roles & set(DATA_ROLES) else "sRGB")


def _roles_of(image):
    import bpy

    found = {}
    for mat in bpy.data.materials:
        for role, hit in material.gather(mat).items():
            if hit["image"] == image:
                found[role] = hit
    return found
