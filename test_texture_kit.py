"""Self-check for texture_kit. Run it with `python tools/bdev.py check blender-toolkit/texture_kit`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_texture_kit.py

Builds a material from known pixel values, then checks the Doctor, the exported texture set (names, sizes, flipped green
channel, packed ORM channels read back from the written files), the channel packer, the normal map flip and the Turkish
text.
"""

import importlib.util
import os
import sys
import tempfile

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "texture_kit")
spec = importlib.util.spec_from_file_location(
    "texture_kit", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
tk = importlib.util.module_from_spec(spec)
sys.modules["texture_kit"] = tk
spec.loader.exec_module(tk)
from texture_kit import doctor, imaging, material  # noqa: E402  (needs the module registered above)

tk.register()
failures = []
tmp = tempfile.mkdtemp(prefix="tk_")


def check(condition, message):
    if not condition:
        failures.append(message)


def close(a, b, tol=0.012):
    return abs(a - b) <= tol


def flat(name, width, height, rgba, is_data=True):
    """An image filled with one color."""
    array = np.empty((height, width, 4), dtype=np.float32)
    array[:] = rgba
    return imaging.create(name, array, is_data=is_data)


def load_back(path):
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = "Non-Color"
    return image, imaging.read(image)


# ---- pure helpers
check(
    imaging.fit_size(1000, 600, 2048) == (1024, 512),
    f"fit_size rounds to powers of two: {imaging.fit_size(1000, 600, 2048)}",
)
check(imaging.fit_size(4096, 2048, 1024) == (1024, 512), "fit_size keeps the aspect ratio when scaling down")
check(imaging.fit_size(1000, 600, 2048, pow2=False) == (1000, 600), "fit_size can keep any size")
check(imaging.is_pow2(512) and not imaging.is_pow2(600), "is_pow2")

# ---- a material with known pixel values
normal = flat("normal_src", 8, 8, (0.2, 0.3, 0.9, 1.0))
mix = flat("mix_src", 8, 8, (0.1, 0.6, 0.9, 1.0))
metal_img = flat("metal_src", 8, 8, (0.75, 0.75, 0.75, 1.0))
ao_img = flat("ao_src", 8, 8, (0.5, 0.5, 0.5, 1.0))
base = flat("base_src", 1000, 600, (0.8, 0.2, 0.1, 1.0), is_data=False)

mat = bpy.data.materials.new("Crate Mat.001")
mat.use_nodes = True
tree = mat.node_tree
bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")


def image_node(image):
    node = tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    return node


tree.links.new(image_node(base).outputs["Color"], bsdf.inputs["Base Color"])
normal_map = tree.nodes.new("ShaderNodeNormalMap")
tree.links.new(image_node(normal).outputs["Color"], normal_map.inputs["Color"])
tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
separate = tree.nodes.new("ShaderNodeSeparateColor")
tree.links.new(image_node(mix).outputs["Color"], separate.inputs["Color"])
tree.links.new(separate.outputs["Green"], bsdf.inputs["Roughness"])
tree.links.new(image_node(metal_img).outputs["Color"], bsdf.inputs["Metallic"])

bpy.ops.mesh.primitive_cube_add()
ob = bpy.context.object
ob.name = "Crate"
ob.data.materials.append(mat)

# ---- tracing
info = material.gather(mat)
check(info["base"]["image"] == base, "base color image is traced")
check(
    info["normal"]["image"] == normal and info["normal"]["via"] == ["NORMAL_MAP"],
    f"normal image through Normal Map: {info['normal']}",
)
check(
    info["rough"]["image"] == mix and info["rough"]["channel"] == "G",
    f"roughness reads the green channel: {info['rough']}",
)
check(info["metal"]["image"] == metal_img and info["metal"]["channel"] is None, "metallic image is traced")
check(info["emission"]["image"] is None, "an unlinked input has no image")

# ---- doctor
sc = bpy.context.scene
s = sc.tk_settings
imaging.set_colorspace(normal, "sRGB")
check(close(imaging.read(normal)[0, 0, 1], 0.3), "re-tagging a generated image keeps its pixels")
bpy.ops.object.select_all(action="DESELECT")
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
codes = {(i["code"], i["image"]) for i in doctor.scan([ob], 4096)}
check(("COLORSPACE", "normal_src") in codes, f"normal map in sRGB is reported: {sorted(codes)}")
check(("NOT_POW2", "base_src") in codes, "a 1000 x 600 texture is reported")
check(
    ("TOO_LARGE", "base_src") in {(i["code"], i["image"]) for i in doctor.scan([ob], 512)},
    "a texture above the limit is reported",
)
bpy.ops.texture_kit.scan()
check(len(sc.tk_issues) >= 2, "the scan operator fills the list")
bpy.ops.texture_kit.fix_all()
check(normal.colorspace_settings.name == "Non-Color", "Fix All sets the normal map to Non-Color")
check(close(imaging.read(normal)[0, 0, 1], 0.3), "fixing the color space keeps the pixels")
check(not [i for i in doctor.scan([ob], 4096) if i["code"] == "COLORSPACE"], "no color space problem is left")
imaging.set_colorspace(metal_img, "sRGB")
imaging.set_colorspace(base, "Non-Color")
fixed = {(i["code"], i["image"]) for i in doctor.scan([ob], 4096) if i["code"] == "COLORSPACE"}
check(fixed == {("COLORSPACE", "metal_src"), ("COLORSPACE", "base_src")}, f"both directions are detected: {fixed}")
bpy.ops.texture_kit.scan()
bpy.ops.texture_kit.fix_all()
check(
    metal_img.colorspace_settings.name == "Non-Color" and base.colorspace_settings.name.startswith("sRGB"),
    "color textures go back to sRGB and data textures to Non-Color",
)

# ---- export of the texture set
s.export_dir, s.asset_name, s.size_limit, s.power_of_two = tmp, "Crate", "2048", True
s.ao_image, s.pack_orm, s.normal_mode, s.file_format = ao_img, True, "FLIP", "PNG"
check(bpy.ops.texture_kit.export() == {"FINISHED"}, "export finishes")
names = sorted(os.listdir(tmp))
check(
    {"T_Crate_BC.png", "T_Crate_N.png", "T_Crate_ORM.png", "T_Crate_import_notes.txt"} <= set(names),
    f"files are named for Unreal: {names}",
)
bc, bc_px = load_back(os.path.join(tmp, "T_Crate_BC.png"))
check(tuple(bc.size) == (1024, 512), f"base color is resized to powers of two: {tuple(bc.size)}")
check(
    close(bc_px[10, 10, 0], 0.8) and close(bc_px[10, 10, 1], 0.2) and close(bc_px[10, 10, 2], 0.1),
    f"base color values survive the resize: {bc_px[10, 10]}",
)
n_img, n_px = load_back(os.path.join(tmp, "T_Crate_N.png"))
check(
    close(n_px[0, 0, 0], 0.2) and close(n_px[0, 0, 1], 0.7) and close(n_px[0, 0, 2], 0.9),
    f"green channel is flipped: {n_px[0, 0]}",
)
orm_img, orm_px = load_back(os.path.join(tmp, "T_Crate_ORM.png"))
check(
    close(orm_px[0, 0, 0], 0.5) and close(orm_px[0, 0, 1], 0.6) and close(orm_px[0, 0, 2], 0.75),
    f"ORM holds AO, roughness (green of the source) and metallic: {orm_px[0, 0]}",
)
check(
    "Normalmap" in open(os.path.join(tmp, "T_Crate_import_notes.txt"), encoding="utf-8").read(),
    "import notes explain the normal map",
)

s.normal_mode, s.size_limit = "KEEP", "512"
tmp2 = tempfile.mkdtemp(prefix="tk2_")
s.export_dir = tmp2
bpy.ops.texture_kit.export()
bc2, _ = load_back(os.path.join(tmp2, "T_Crate_BC.png"))
check(tuple(bc2.size) == (512, 256), f"the size limit scales down together: {tuple(bc2.size)}")
n2, n2_px = load_back(os.path.join(tmp2, "T_Crate_N.png"))
check(close(n2_px[0, 0, 1], 0.3), "Keep as it is leaves the normal map unchanged")

# ---- an object without textures
bpy.ops.mesh.primitive_plane_add()
plain = bpy.context.object
plain.data.materials.append(bpy.data.materials.new("Plain"))
refused = False
s.ao_image = None
try:
    s.export_dir = tmp2
    bpy.ops.texture_kit.export()
except RuntimeError as e:
    refused = "Principled" in str(e)
check(refused, "an object without textures is refused with a message")

# ---- channel packer
s.slot_r.image, s.slot_r.channel = ao_img, "R"
s.slot_g.image, s.slot_g.channel, s.slot_g.invert = mix, "G", True
s.slot_b.image = None
s.slot_b.value = 0.3
s.slot_a.image, s.slot_a.value = None, 1.0
s.pack_name, s.pack_size, s.pack_save = "T_Test_ORM", "AUTO", False
check(bpy.ops.texture_kit.pack() == {"FINISHED"}, "pack finishes")
packed = bpy.data.images["T_Test_ORM"]
data = imaging.read(packed)
check(tuple(packed.size) == (8, 8), "packed image takes the largest source size")
check(
    close(data[3, 3, 0], 0.5) and close(data[3, 3, 1], 0.4) and close(data[3, 3, 2], 0.3) and close(data[3, 3, 3], 1.0),
    f"channels land where they should (with invert): {data[3, 3]}",
)
check(packed.colorspace_settings.name == "Non-Color", "packed data is Non-Color")

# ---- normal map flip
s.normal_image = normal
bpy.ops.texture_kit.flip_normal()
flipped = imaging.read(bpy.data.images["normal_src_flipped"])
check(close(flipped[0, 0, 1], 0.7) and close(flipped[0, 0, 0], 0.2), "flip normal inverts only green")
s.normal_image = bpy.data.images["normal_src_flipped"]
bpy.ops.texture_kit.flip_normal()
twice = imaging.read(bpy.data.images["normal_src_flipped_flipped"])
check(close(twice[0, 0, 1], 0.3), "flipping twice gives the original")

# ---- preset
bpy.ops.texture_kit.pack_preset()
check((s.slot_g.value, s.slot_b.value, s.slot_r.image) == (0.5, 0.0, None), "the ORM preset resets the slots")

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Export for Unreal")
prefs.language = "en_US"
check(translated == "Unreal İçin Dışa Aktar", f"Turkish translation active ({translated!r})")

tk.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("OK: texture_kit doctor, export, packer, normal flip")
