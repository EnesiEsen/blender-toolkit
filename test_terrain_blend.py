"""Self-check for terrain_blend. Run it with `python tools/bdev.py check blender-toolkit/terrain_blend`, or by hand:
blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 --python test_terrain_blend.py

Builds 14 layers (the base + 13 vertex groups, one stripe each) from texture folders named like ambientCG, Poly Haven
and Poliigon downloads, renders with EEVEE and Cycles and checks every stripe shows its own texture. Also covers the
library import, Lite mode, the Enhancer, rebuilds keeping slider values and the automatic masks.
Environment: AK_LAYERS (default 14), BDEV_BACKEND (opengl: only the Lite material can be rendered, 32-sampler limit).
"""
import colorsys
import importlib.util
import os
import sys
import tempfile

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "terrain_blend")
spec = importlib.util.spec_from_file_location("terrain_blend", os.path.join(PKG, "__init__.py"),
                                              submodule_search_locations=[PKG])
tb = importlib.util.module_from_spec(spec)
sys.modules["terrain_blend"] = tb
spec.loader.exec_module(tb)
from terrain_blend import core, maps, masks, shader  # noqa: E402  (needs the module registered above)

tb.register()

LAYERS = int(os.environ.get("AK_LAYERS", 14))  # any count; the add-on has no layer limit
OPENGL = os.environ.get("BDEV_BACKEND") == "opengl"
NAMING = [  # (color, normal(s), rough, height) file names per vendor style
    ("Ground_2K_Color.png", ["Ground_2K_NormalDX.png", "Ground_2K_NormalGL.png"],
     "Ground_2K_Roughness.png", "Ground_2K_Displacement.png"),
    ("path_diff_2k.jpg", ["path_nor_dx_2k.png", "path_nor_gl_2k.png"], "path_rough_2k.png", "path_disp_2k.png"),
    ("Rock_COL_VAR1_2K.jpg", ["Rock_NRM_2K.jpg"], "Rock_ROUGH_2K.jpg", "Rock_DISP_2K.jpg"),
    ("only_albedo.png", [], None, None),  # missing maps fall back to flat values
]
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def save_image(path, rgb):
    img = bpy.data.images.new(os.path.basename(path), 8, 8)
    img.pixels = [*rgb, 1.0] * 64
    img.filepath_raw = path
    img.file_format = "JPEG" if path.endswith(".jpg") else "PNG"
    img.save()
    bpy.data.images.remove(img)


def palette(i):
    return colorsys.hsv_to_rgb(i / LAYERS, 0.8, 0.9)


# ---- fixtures: a texture library with one folder per set, plus a folder that is not a set
library = tempfile.mkdtemp(prefix="tb_lib_")
for i in range(LAYERS):
    folder = os.path.join(library, f"set{i:02d}")
    os.makedirs(folder)
    color, normals, rough, height = NAMING[i % len(NAMING)]
    save_image(os.path.join(folder, color), palette(i))
    for n in normals:
        save_image(os.path.join(folder, n), (0.5, 0.5, 1.0))
    if rough:
        save_image(os.path.join(folder, rough), (0.7, 0.7, 0.7))
    if height:
        save_image(os.path.join(folder, height), (0.5, 0.5, 0.5))
os.makedirs(os.path.join(library, "not_a_set"))
save_image(os.path.join(library, "not_a_set", "readme_icon.png"), (0, 0, 0))

# ---- map detection
check(maps.find_maps(os.path.join(library, "set00"))["normal"].endswith("NormalGL.png"), "OpenGL normal preferred")
check(maps.find_maps(os.path.join(library, "set01"))["normal"].endswith("nor_gl_2k.png"), "nor_gl naming")
check(set(maps.find_maps(os.path.join(library, "set02"))) == {"color", "normal", "rough", "height"}, "full set")
check(set(maps.find_maps(os.path.join(library, "set03"))) == {"color"}, "color-only set")
check([name for name, _ in maps.find_sets(library)] == [f"set{i:02d}" for i in range(LAYERS)], "find_sets skips junk")

# ---- scene: stripes of vertex groups named like the sets
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=LAYERS * 10, y_subdivisions=4, size=2)
ob = bpy.context.object
old = bpy.data.materials.new("Old")
ob.data.materials.append(old)
for k in range(1, LAYERS):
    stripe = [v.index for v in ob.data.vertices if min(int((v.co.x + 1) / 2 * LAYERS), LAYERS - 1) == k]
    ob.vertex_groups.new(name=f"set{k:02d}").add(stripe, 1.0, "REPLACE")


def ctx():
    return bpy.context.temp_override(object=ob, active_object=ob)


try:
    core.build(ob)
    check(False, "build without layers must raise")
except ValueError as e:
    check("at least one layer" in str(e), f"empty-layer message: {e}")

with ctx():
    bpy.ops.terrain_blend.from_library(directory=library)
    check(len(ob.tb_layers) == LAYERS, f"library import added {len(ob.tb_layers)} layers")
    check(all(ob.tb_layers[k].mask == f"set{k:02d}" for k in range(1, LAYERS)), "masks matched by name")
    check(ob.tb_layers[0].mask == "", "base layer has no mask")
    bpy.ops.terrain_blend.from_library(directory=library)
    check(len(ob.tb_layers) == LAYERS, "importing the same library twice adds nothing")

full_count = sum(len(maps.find_maps(layer.folder)) for layer in ob.tb_layers)
lite_count = sum(1 + ("height" in maps.find_maps(layer.folder)) for layer in ob.tb_layers)
with ctx():
    check(bpy.ops.terrain_blend.build() == {"FINISHED"}, "build operator")
mat = ob.active_material
tree = core.group_tree(ob)
check(mat.name == core.material_name(ob) and old.use_fake_user, "replaced material is kept")
check(tree["tb_textures"] == full_count, f"full mode textures {tree['tb_textures']} != {full_count}")
stores = [n for n in ob.modifiers[masks.MOD_NAME].node_group.nodes if n.type == "STORE_NAMED_ATTRIBUTE"]
check(len(stores) == (LAYERS + 2) // 4, "masks pack 4 per color attribute")

ob.tb_settings.lite = True  # the update callback rebuilds
tree = core.group_tree(ob)
check(tree["tb_textures"] == lite_count < full_count, f"lite mode textures {tree['tb_textures']} != {lite_count}")
if not OPENGL:
    ob.tb_settings.lite = False


def layer_scale(index):  # interface items are recreated by every rebuild, so look the slider up fresh
    t = core.group_tree(ob)
    item = next(i for i in shader.inputs_of(t) if shader.slider_key(i) == ("L", index, "Scale"))
    return shader.by_id(shader.group_node_of(ob.active_material, t).inputs, item.identifier)


layer_scale(3).default_value = 5.0
ob.tb_settings.enhancer = True
check(layer_scale(3).default_value == 5.0, "slider values survive a rebuild")
ob.tb_settings.enhancer = False
check(layer_scale(3).default_value == 5.0, "slider values survive turning the enhancer off")

ob.tb_layers[2].folder = os.path.join(library, "missing")
try:
    core.build(ob)
    check(False, "missing folder must raise")
except ValueError:
    pass
ob.tb_layers[2].folder = os.path.join(library, "set02")
core.build(ob)

# ---- rendering
sc = bpy.context.scene
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = LAYERS * 20, 20
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.location = (0, 0, 5)
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2
sc.world = bpy.data.worlds.new("w")
sc.world.color = (1, 1, 1)


def render(engine):
    sc.render.engine = engine
    if engine == "CYCLES":
        sc.cycles.samples = 4
        sc.cycles.device = "CPU"
    bpy.ops.render.render()
    path = os.path.join(library, engine + ".png")
    bpy.data.images["Render Result"].save_render(path)
    img = bpy.data.images.load(path, check_existing=False)
    w = sc.render.resolution_x
    px = img.pixels[:]
    bpy.data.images.remove(img)
    return [px[(10 * w + k * 20 + 10) * 4:(10 * w + k * 20 + 10) * 4 + 3] for k in range(LAYERS)], px


def broken(rgb):
    return (rgb[0] > 0.95 and rgb[1] < 0.05 and rgb[2] > 0.95) or max(rgb) < 0.05  # pink = failed shader, or black


def mean_diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b, strict=True)) / len(a)


lit_off = {}
for engine in ("BLENDER_EEVEE", "CYCLES"):
    stripes, lit_off[engine] = render(engine)
    check(not any(broken(rgb) for rgb in stripes), f"{engine}: lit material renders (pink or black stripe found)")

ob.tb_settings.enhancer = True
tree = core.group_tree(ob)
nodes_on = len(tree.nodes)
check(tree["tb_textures"] == (lite_count if OPENGL else full_count), "enhancer adds no image textures")
check(any(shader.slider_key(i)[0] == "E" for i in shader.inputs_of(tree)), "enhancer sliders exist")
check(ob.active_material.displacement_method == "BOTH", "enhancer enables displacement")
base_a, base_b = render("BLENDER_EEVEE")[1], render("BLENDER_EEVEE")[1]
stripes, enhanced = render("BLENDER_EEVEE")
check(not any(broken(rgb) for rgb in stripes), "enhancer: lit material renders")
check(mean_diff(enhanced, lit_off["BLENDER_EEVEE"]) > mean_diff(base_a, base_b) + 0.001, "enhancer changes the image")
ob.tb_settings.enhancer = False
check(len(core.group_tree(ob).nodes) < nodes_on, "enhancer off removes its nodes")
check(ob.active_material.displacement_method == "BUMP", "enhancer off restores bump")

# Exact blend check: show the blended Base Color unlit.
nt = ob.active_material.node_tree
group = shader.group_node_of(ob.active_material, core.group_tree(ob))
emission = nt.nodes.new("ShaderNodeEmission")
nt.links.new(group.outputs["Base Color"], emission.inputs["Color"])
nt.links.new(emission.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
for engine in ("BLENDER_EEVEE", "CYCLES"):
    for k, rgb in enumerate(render(engine)[0]):
        want = palette(k)
        if max(abs(a - b) for a, b in zip(rgb, want, strict=True)) > 0.04:
            got, exp = (tuple(round(c, 2) for c in x) for x in (rgb, want))
            failures.append(f"{engine} stripe {k}: got {got} want {exp}")

# ---- automatic masks on a ramp: flat for x < 0, a 26.6 degree slope for x > 0
bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=8, size=4)
ramp = bpy.context.object
for v in ramp.data.vertices:
    v.co.z = 0.5 * v.co.x if v.co.x > 0 else 0.0
ramp.data.update()


def weights(name):
    group = ramp.vertex_groups[name]
    out = {}
    for v in ramp.data.vertices:
        out[v.index] = next((g.weight for g in v.groups if g.group == group.index), 0.0)
    return out


def region(w, test):
    return [w[v.index] for v in ramp.data.vertices if test(v.co)]


def run_mask(**kw):
    with bpy.context.temp_override(object=ramp, active_object=ramp):
        return bpy.ops.terrain_blend.auto_mask(**kw)


run_mask(group="slope", mode="SLOPE", low=10.0, high=20.0)
w = weights("slope")
check(min(region(w, lambda c: c.x > 0.6)) > 0.99 and max(region(w, lambda c: c.x < -0.6)) < 0.01, "slope mask")
run_mask(group="high", mode="HEIGHT", low=0.5, high=1.0)
w = weights("high")
check(min(region(w, lambda c: c.x > 2.0 - 1e-4)) > 0.99 and max(region(w, lambda c: c.x < 1.0)) < 0.01, "height mask")
run_mask(group="slope", mode="HEIGHT", low=0.5, high=1.0, combine="MULTIPLY")  # slope AND height
w = weights("slope")
check(max(region(w, lambda c: c.x < 1.0)) < 0.01 and min(region(w, lambda c: c.x > 2.0 - 1e-4)) > 0.99, "intersect")
run_mask(group="inv", mode="SLOPE", low=10.0, high=20.0, invert=True)
w = weights("inv")
check(min(region(w, lambda c: c.x < -0.6)) > 0.99 and max(region(w, lambda c: c.x > 0.6)) < 0.01, "inverted mask")
run_mask(group="n1", mode="NOISE", noise_scale=0.7, seed=1)
run_mask(group="n2", mode="NOISE", noise_scale=0.7, seed=2)
n1, n2 = weights("n1"), weights("n2")
check(0.02 < sum(n1.values()) / len(n1) < 0.98 and n1 != n2, "noise mask varies with the seed")
ramp.rotation_euler.x = 1.5707963  # standing up: every vertex normal is horizontal, so the slope is 90 degrees
bpy.context.view_layer.update()
run_mask(group="wall", mode="SLOPE", low=60.0, high=80.0)
check(min(weights("wall").values()) > 0.99, "slope uses world-space normals")

# ---- translation (Blender shows it when the interface language is Turkish)
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Add Layer")
prefs.language = "en_US"
check(translated == "Katman Ekle", f"Turkish translation active ({translated!r})")

tb.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
mode = "OpenGL lite" if OPENGL else "full"
print(f"OK: {LAYERS} layers, {full_count} textures ({lite_count} lite), {mode}, EEVEE + Cycles")
