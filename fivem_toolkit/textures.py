"""Textures for FiveM: PNG/JPG/... to DDS (DXT1 or DXT5 with a full mipmap chain).

Sollumz exports textures only from DDS files (it skips anything else with a warning) and Blender cannot write DDS, so
this module has its own small block-compression encoder (numpy, no external tools).
"""

import math
import struct
from pathlib import Path

import bpy
import numpy as np

CHUNK = 65536  # blocks encoded at a time, keeps the memory use of a 4K texture small
DDSD_FLAGS = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000  # caps, height, width, pixel format, mip count, linear size
DDSCAPS = 0x1000 | 0x8 | 0x400000  # texture, complex, mipmap
ALPHA_CODES = np.array([[7, 0], [0, 7], [6, 1], [5, 2], [4, 3], [3, 4], [2, 5], [1, 6]], dtype=np.float32) / 7.0


def pow2_size(width, height, limit):
    """Nearest power of two per side, never above `limit`."""

    def snap(n):
        return min(limit, max(4, 2 ** round(math.log2(max(n, 1)))))

    return snap(width), snap(height)


def is_dds(image):
    return Path(bpy.path.abspath(image.filepath)).suffix.lower() == ".dds" or bool(
        image.packed_file and image.packed_file.data.startswith(b"DDS ")
    )


def read_rgba8(image):
    """Pixels of a Blender image as a (height, width, 4) uint8 array, top row first (the order DDS wants)."""
    width, height = image.size
    buffer = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    pixels = buffer.reshape(height, width, 4)
    if image.is_float:  # linear float image: store it the way 8-bit textures are stored (sRGB)
        linear = np.clip(pixels[..., :3], 0.0, 1.0)
        pixels[..., :3] = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - 0.055)
    return np.flipud(np.rint(np.clip(pixels, 0.0, 1.0) * 255).astype(np.uint8))


def to_blocks(pixels):
    """(h, w, 4) -> (blocks, 16, 4): 4x4 pixel blocks in row order, padded at the edge when a side is below 4."""
    height, width = pixels.shape[:2]
    pad_h, pad_w = -height % 4, -width % 4
    if pad_h or pad_w:
        pixels = np.pad(pixels, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
        height, width = pixels.shape[:2]
    blocks = pixels.reshape(height // 4, 4, width // 4, 4, 4).transpose(0, 2, 1, 3, 4)
    return blocks.reshape(-1, 16, 4)


def rgb565(rgb):
    r, g, b = (np.rint(rgb[:, i] * f / 255.0).astype(np.uint16) for i, f in enumerate((31, 63, 31)))
    return (r << 11) | (g << 5) | b


def from_rgb565(value):
    r, g, b = (value >> 11) & 31, (value >> 5) & 63, value & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], axis=1).astype(np.float32)


def encode_bc1(rgb):
    """(n, 16, 3) float colors 0..255 -> (n, 8) uint8 DXT1 blocks. Endpoints come from the principal color axis."""
    mean = rgb.mean(axis=1, keepdims=True)
    centered = rgb - mean
    axis = np.linalg.eigh(np.einsum("npi,npj->nij", centered, centered))[1][:, :, -1]
    along = np.einsum("npi,ni->np", centered, axis)
    high = np.clip(mean[:, 0] + axis * along.max(axis=1)[:, None], 0, 255)
    low = np.clip(mean[:, 0] + axis * along.min(axis=1)[:, None], 0, 255)
    c0, c1 = rgb565(high), rgb565(low)
    c0, c1 = np.maximum(c0, c1), np.minimum(c0, c1)  # c0 > c1 selects the four-color mode
    p0, p1 = from_rgb565(c0), from_rgb565(c1)
    palette = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], axis=1)  # (n, 4, 3)
    distance = ((rgb[:, :, None, :] - palette[:, None, :, :]) ** 2).sum(axis=3)  # (n, 16, 4)
    indices = distance.argmin(axis=2).astype(np.uint32)
    indices[c0 == c1] = 0
    packed = (indices << (2 * np.arange(16, dtype=np.uint32))).sum(axis=1, dtype=np.uint32)
    out = np.empty((len(rgb), 8), dtype=np.uint8)
    out[:, 0:2] = c0.astype("<u2").view(np.uint8).reshape(-1, 2)
    out[:, 2:4] = c1.astype("<u2").view(np.uint8).reshape(-1, 2)
    out[:, 4:8] = packed.astype("<u4").view(np.uint8).reshape(-1, 4)
    return out


def encode_bc3_alpha(alpha):
    """(n, 16) alpha 0..255 -> (n, 8) uint8: two endpoints and sixteen 3-bit indices."""
    high, low = alpha.max(axis=1), alpha.min(axis=1)
    codes = high[:, None] * ALPHA_CODES[:, 0] + low[:, None] * ALPHA_CODES[:, 1]  # (n, 8)
    indices = np.abs(alpha[:, :, None] - codes[:, None, :]).argmin(axis=2).astype(np.uint64)
    packed = (indices << (3 * np.arange(16, dtype=np.uint64))).sum(axis=1, dtype=np.uint64)
    out = np.empty((len(alpha), 8), dtype=np.uint8)
    out[:, 0], out[:, 1] = high, low
    out[:, 2:8] = packed.astype("<u8").view(np.uint8).reshape(-1, 8)[:, :6]
    return out


def encode_level(pixels, with_alpha):
    """Compress one mip level; returns its bytes."""
    blocks = to_blocks(pixels).astype(np.float32)
    parts = []
    for start in range(0, len(blocks), CHUNK):
        chunk = blocks[start : start + CHUNK]
        color = encode_bc1(chunk[:, :, :3])
        parts.append(np.hstack([encode_bc3_alpha(chunk[:, :, 3]), color]) if with_alpha else color)
    return np.vstack(parts).tobytes()


def mip_chain(pixels):
    """Box-filtered mip levels down to 1x1, largest first (a side of 1 is kept as it is)."""
    levels = [pixels]
    current = pixels.astype(np.float32)
    while current.shape[0] > 1 or current.shape[1] > 1:
        h, w = current.shape[0], current.shape[1]
        if h % 2 or w % 2:  # only power-of-two textures reach here; pad the odd side otherwise
            current = np.pad(current, ((0, h % 2), (0, w % 2), (0, 0)), mode="edge")
            h, w = current.shape[0], current.shape[1]
        sy, sx = (2 if h > 1 else 1), (2 if w > 1 else 1)
        current = current.reshape(h // sy, sy, w // sx, sx, 4).mean(axis=(1, 3))
        levels.append(np.rint(current).astype(np.uint8))
    return levels


def dds_file_bytes(pixels, with_alpha):
    """A complete DDS file: header, then DXT1 (opaque) or DXT5 (with alpha) data for every mip level."""
    levels = mip_chain(pixels)
    block_bytes = 16 if with_alpha else 8
    data = b"".join(encode_level(level, with_alpha) for level in levels)
    height, width = pixels.shape[:2]
    linear = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * block_bytes
    header = struct.pack("<4sIIIIIII11I", b"DDS ", 124, DDSD_FLAGS, height, width, linear, 0, len(levels), *([0] * 11))
    pixel_format = struct.pack("<II4sIIIII", 32, 0x4, b"DXT5" if with_alpha else b"DXT1", 0, 0, 0, 0, 0)
    caps = struct.pack("<IIIII", DDSCAPS, 0, 0, 0, 0)
    return header + pixel_format + caps + data


def has_alpha(pixels):
    return bool((pixels[..., 3] < 250).any())


def write_dds(path, pixels, with_alpha=None):
    """Encode (height, width, 4) uint8 pixels to a DDS file. Returns the format name."""
    with_alpha = has_alpha(pixels) if with_alpha is None else with_alpha
    Path(path).write_bytes(dds_file_bytes(pixels, with_alpha))
    return "DXT5" if with_alpha else "DXT1"


def dds_folder(image):
    """Where the DDS of an image goes: next to its file, else next to the .blend, else a temporary folder."""
    source = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
    if source is not None and source.parent.is_dir():
        return source.parent
    if bpy.data.filepath:
        folder = Path(bpy.path.abspath("//")) / "fk_textures"
    else:
        folder = Path(bpy.app.tempdir) / "fk_textures"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def convert_image(image, limit=2048):
    """Convert one image to DDS (power-of-two sides up to `limit`) and point the Blender image at the new file."""
    if is_dds(image):
        return Path(bpy.path.abspath(image.filepath))
    width, height = image.size
    if (width, height) != pow2_size(width, height, limit):
        image.scale(*pow2_size(width, height, limit))
    path = dds_folder(image) / (Path(image.name).stem + ".dds")
    pixels = read_rgba8(image)
    write_dds(path, pixels)
    image["fk_source"] = image.filepath or image.name
    image.filepath = str(path)
    image.reload()
    return path
