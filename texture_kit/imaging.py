"""Pixel work with numpy. Images are always read as stored (Non-Color), so nothing is converted behind your back."""

import math
from pathlib import Path

import bpy
import numpy as np

INDEX = {"R": 0, "G": 1, "B": 2, "A": 3}


def is_pow2(n):
    return n > 0 and n & (n - 1) == 0


def nearest_pow2(n):
    return 1 if n <= 1 else 2 ** round(math.log2(n))


def fit_size(width, height, limit, pow2=True):
    """The size an exported texture gets: nearest power of two per side, scaled down together to fit the limit."""
    w, h = (nearest_pow2(width), nearest_pow2(height)) if pow2 else (width, height)
    if max(w, h) > limit:
        factor = limit / max(w, h)
        w, h = max(1, round(w * factor)), max(1, round(h * factor))
        if pow2:
            w, h = nearest_pow2(w), nearest_pow2(h)
    return w, h


DATA_SPACES = ("Non-Color", "Raw")


def is_data(image):
    return image.colorspace_settings.name in DATA_SPACES


def linear_to_srgb(values):
    values = np.clip(values, 0.0, 1.0)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * np.power(values, 1 / 2.4) - 0.055)


def read(image, encode=False):
    """Stored values of the image as (height, width, 4) float32.

    Byte images are read as stored, whatever their color space (Blender returns bytes / 255). Nothing is copied or
    re-tagged: doing that to an unsaved generated image (a bake result) blanks it. `encode` turns a linear float color
    image into the sRGB values a PNG needs.
    """
    width, height = image.size
    if not width or not height:
        raise ValueError(f"'{image.name}' has no pixel data")
    data = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(data)
    data = data.reshape(height, width, 4)
    if encode and image.is_float and not is_data(image):
        data[..., :3] = linear_to_srgb(data[..., :3])
    return data


def resample(array, width, height):
    """Scale a (height, width, 4) array with Blender's own scaler, on a temporary image."""
    if array.shape[:2] == (height, width):
        return array
    tmp = create("tk_resample", array)
    try:
        tmp.scale(width, height)
        return read(tmp)
    finally:
        bpy.data.images.remove(tmp)


def pixels_at(image, width, height, encode=False):
    """Stored values of the image at the given size, as (height, width, 4) float32."""
    return resample(read(image, encode), width, height)


def set_colorspace(image, name):
    """Change the color space without losing pixels (Blender blanks an unsaved generated image that is re-tagged)."""
    if image.source == "GENERATED":
        data = read(image)
        image.colorspace_settings.name = name
        image.pixels.foreach_set(data.ravel())
        image.update()
    else:
        image.colorspace_settings.name = name


def create(name, array, is_data=True):
    """A new image from a (height, width, 4) array."""
    height, width = array.shape[:2]
    image = bpy.data.images.new(name, width, height, alpha=True, float_buffer=False, is_data=is_data)
    image.pixels.foreach_set(np.clip(array, 0.0, 1.0).astype(np.float32).ravel())
    image.update()
    return image


def save(image, path, file_format):
    image.filepath_raw = str(path)
    image.file_format = file_format
    image.save()
    return path


def save_scaled_copy(image, width, height, path, file_format):
    """Write a (scaled) copy of an image without touching the original."""
    data = pixels_at(image, width, height, encode=True)
    tmp = create(Path(path).stem, data, is_data=is_data(image))
    try:
        save(tmp, path, file_format)
    finally:
        bpy.data.images.remove(tmp)
    return path


def channel(image, name, width, height, fallback):
    """One channel of an image as (height, width) float32; `fallback` fills the array when there is no image."""
    if image is None:
        return np.full((height, width), fallback, dtype=np.float32)
    data = pixels_at(image, width, height)
    if name == "LUMA":
        return (data[..., 0] * 0.2126 + data[..., 1] * 0.7152 + data[..., 2] * 0.0722).astype(np.float32)
    return data[..., INDEX.get(name or "R", 0)].copy()


def pack(slots, size=None):
    """Combine four channels. Each slot is a dict with image, channel, invert and value. Returns (height, width, 4)."""
    if size is None:
        sizes = [tuple(s["image"].size) for s in slots if s["image"] is not None]
        size = (max(w for w, _ in sizes), max(h for _, h in sizes)) if sizes else (1024, 1024)
    width, height = size
    out = np.ones((height, width, 4), dtype=np.float32)
    for index, slot in enumerate(slots):
        values = channel(slot["image"], slot["channel"], width, height, slot["value"])
        out[..., index] = 1.0 - values if slot["invert"] else values
    return out
