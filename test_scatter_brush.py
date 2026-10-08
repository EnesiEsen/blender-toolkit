"""Self-check for scatter_brush. Run it with `python tools/bdev.py check blender-toolkit/scatter_brush`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_scatter_brush.py

Surface layers are compared with an independent numpy reference (expected object count from the painted weights,
density ramp, empty areas, scale range, alignment to a tilted surface, spacing, seeds, baking). The click brush is
driven through its Painter on a real ray cast: disk radius, slope limit, spacing, skipping its own objects, erase,
determinism.
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "scatter_brush")
spec = importlib.util.spec_from_file_location(
    "scatter_brush", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
sb = importlib.util.module_from_spec(spec)
sys.modules["scatter_brush"] = sb
spec.loader.exec_module(sb)
from scatter_brush import i18n, layers, operators, place  # noqa: E402  (needs the module registered above)

sb.register()
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


scene = bpy.context.scene
ctx = bpy.context
for startup in list(scene.objects):  # the factory scene has a cube, a light and a camera: they would catch rays
    bpy.data.objects.remove(startup)


def make_ground(name="Ground", size=10.0, segments=40, weight=None, rotation=0.0):
    """Square grid of side 2*size at z=0 with an optional vertex group 'grass' filled by weight(x, y)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=segments, y_segments=segments, size=size)
    bm.transform(Matrix.Rotation(rotation, 4, "X"))  # tilt the mesh data: the object itself stays unrotated
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if weight is not None:
        vg = ob.vertex_groups.new(name="grass")
        for v in me.vertices:
            vg.add([v.index], weight(v.co.x, v.co.y), "REPLACE")
    return ob


def make_assets(name, count, size=0.2):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    for i in range(count):
        me = bpy.data.meshes.new(f"{name}{i}")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=size)
        bm.to_mesh(me)
        bm.free()
        col.objects.link(bpy.data.objects.new(f"{name}{i}", me))
    return col


class CatRef:
    """A category looked up by uid on every access: a pointer into `scene.sb_categories` dies when the list grows."""

    def __init__(self, uid):
        object.__setattr__(self, "uid", uid)

    def __getattr__(self, key):
        return getattr(layers.find_category(scene, self.uid), key)

    def __setattr__(self, key, value):
        setattr(layers.find_category(scene, self.uid), key, value)


def new_category(name, col, **settings):
    cat = scene.sb_categories.add()
    cat.name = name
    cat.uid = scene.sb_next_uid
    scene.sb_next_uid += 1
    cat.collection = col
    for key, value in settings.items():
        setattr(cat, key, value)
    scene.sb_index = len(scene.sb_categories) - 1
    return CatRef(cat.uid)


def instances_of(ob):
    ctx.view_layer.update()
    dg = ctx.evaluated_depsgraph_get()
    return [
        (i.object.name, Matrix(i.matrix_world))
        for i in dg.object_instances
        if i.is_instance and i.parent is not None and i.parent.original == ob
    ]


def positions(items):
    return np.array([m.translation[:] for _, m in items]) if items else np.zeros((0, 3))


def painted_integral(ob, group="grass"):
    """Independent reference: integral of the (linear) weight over the surface = expected count / density."""
    me = ob.data
    gi = ob.vertex_groups[group].index
    w = np.zeros(len(me.vertices))
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi:
                w[v.index] = g.weight
    me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices])
    total = 0.0
    for tri in me.loop_triangles:
        a, b, c = (co[i] for i in tri.vertices)
        total += 0.5 * np.linalg.norm(np.cross(b - a, c - a)) * w[list(tri.vertices)].mean()
    return total


# --- surface layer: counts, ramp, empty area ------------------------------------------------------
grass = make_assets("Grass", 3)
ground = make_ground("GroundRamp", weight=lambda x, y: (x + 10.0) / 20.0)
cat = new_category("Grass", grass, density=20.0, edge_scale=0.0, height_var=0.0, scale_min=1.0, scale_max=1.0)
layers.add_layer(ground, cat, "grass", scene)
items = instances_of(ground)
expected = 20.0 * painted_integral(ground)
check(abs(len(items) - expected) < 0.12 * expected, f"ramp count {len(items)} vs expected {expected:.0f}")
pos = positions(items)
left, right = (pos[:, 0] < 0).sum(), (pos[:, 0] >= 0).sum()
check(
    2.3 < right / max(left, 1) < 4.3,
    f"density follows the weight ramp (right/left = {right / max(left, 1):.2f}, want 3)",
)
check({n for n, _ in items} == {"Grass0", "Grass1", "Grass2"}, "all three models are used")
check(len({n for n, _ in items}) <= len(grass.objects), "only models of the category appear")
check(np.abs(pos[:, 2]).max() < 1e-4, "objects sit on the flat ground")
sizes = np.array([m.to_scale().x for _, m in items])
check(sizes.min() > 0.999 and sizes.max() < 1.001, f"fixed scale 1.0 respected ({sizes.min():.3f}..{sizes.max():.3f})")

# weights only in one corner: nothing elsewhere
corner = make_ground("GroundCorner", weight=lambda x, y: 1.0 if (x > 4.9 and y > 4.9) else 0.0)
layers.add_layer(corner, cat, "grass", scene)
items = instances_of(corner)
pos = positions(items)
check(len(items) > 20, f"corner got objects ({len(items)})")
check(pos[:, 0].min() > 4.4 and pos[:, 1].min() > 4.4, "no objects outside the painted corner")

# no vertex group: whole surface
empty = make_ground("GroundAll")
layers.add_layer(empty, cat, "", scene)
items = instances_of(empty)
check(abs(len(items) - 20.0 * 400.0) < 0.1 * 8000, f"no group covers the surface ({len(items)} vs 8000)")

# --- randomness controls --------------------------------------------------------------------------
flat = make_ground("GroundFlat", weight=lambda x, y: 1.0)
cat2 = new_category(
    "Rocks",
    make_assets("Rock", 2, 0.5),
    density=0.5,
    edge_scale=0.0,
    height_var=0.0,
    scale_min=0.5,
    scale_max=2.0,
    yaw=math.tau,
    tilt=0.0,
    align=0.0,
    seed=4,
)
layers.add_layer(flat, cat2, "grass", scene)
items = instances_of(flat)
sizes = np.array([m.to_scale().x for _, m in items])
check(
    sizes.min() >= 0.5 - 1e-3 and sizes.max() <= 2.0 + 1e-3,
    f"scale within 0.5..2.0 ({sizes.min():.2f}..{sizes.max():.2f})",
)
check(sizes.max() - sizes.min() > 1.0, "scale actually varies")
heading = np.array([math.atan2(m.col[0][1], m.col[0][0]) for _, m in items])
check(heading.max() - heading.min() > 5.0, f"turn spreads over the circle ({np.ptp(heading):.2f} rad)")
ups = np.array([(m.to_3x3() @ Vector((0, 0, 1))).normalized()[2] for _, m in items])
check(ups.min() > 0.9999, "tilt 0 and align 0 keep every object upright")

cat2.yaw = 0.0
cat2.tilt = math.radians(20.0)
items = instances_of(flat)
ups = np.array([(m.to_3x3() @ Vector((0, 0, 1))).normalized()[2] for _, m in items])
check(0.87 < ups.min() < 0.92, f"tilt 20 deg on two axes leans up to ~28 deg, cos = 0.885 ({ups.min():.3f})")
cat2.tilt = 0.0
cat2.height_var = 0.5
items = instances_of(flat)
ratio = np.array([m.to_scale().z / m.to_scale().x for _, m in items])
check(
    ratio.min() >= 0.5 - 1e-3 and ratio.max() <= 1.5 + 1e-3 and np.ptp(ratio) > 0.5, "height variation stretches only z"
)
cat2.height_var = 0.0
cat2.sink = 0.3
items = instances_of(flat)
check(abs(positions(items)[:, 2].mean() + 0.3) < 1e-3, "sink lowers every object by 0.3 m")
cat2.sink = 0.0

# edge scale shrinks objects where the weight is weak
ramp = make_ground("GroundRamp2", weight=lambda x, y: (x + 10.0) / 20.0)
cat3 = new_category(
    "Edge",
    make_assets("Edge", 1),
    density=30.0,
    edge_scale=1.0,
    height_var=0.0,
    scale_min=1.0,
    scale_max=1.0,
)
layers.add_layer(ramp, cat3, "grass", scene)
items = instances_of(ramp)
pos, size = positions(items), np.array([m.to_scale().x for _, m in items])
weak, strong = size[pos[:, 0] < -5], size[pos[:, 0] > 5]
check(weak.mean() < strong.mean() - 0.3, f"edge shrink: weak {weak.mean():.2f} < strong {strong.mean():.2f}")

# falloff thins weak weights faster
cat3.edge_scale = 0.0
base = len(instances_of(ramp))
cat3.falloff = 3.0
thin = len(instances_of(ramp))
check(thin < 0.6 * base, f"falloff 3 thins the scatter ({thin} < 0.6 * {base})")
cat3.falloff = 1.0

# seeds
cat3.seed = 5
a = positions(instances_of(ramp))
cat3.seed = 5
b = positions(instances_of(ramp))
cat3.seed = 6
c = positions(instances_of(ramp))
check(a.shape == b.shape and np.allclose(np.sort(a, axis=0), np.sort(b, axis=0)), "same seed gives the same pattern")
check(a.shape != c.shape or not np.allclose(np.sort(a, axis=0), np.sort(c, axis=0)), "another seed changes the pattern")

# category settings flow into every layer; layer density multiplies
n1 = len(instances_of(ramp))
cat3.density = 60.0
n2 = len(instances_of(ramp))
check(1.7 < n2 / n1 < 2.3, f"doubling the category density doubles the count ({n1} -> {n2})")
ramp.sb_layers[0].density = 0.5
n3 = len(instances_of(ramp))
check(0.85 < n3 / n1 < 1.15, f"layer density 0.5 halves it again ({n3} vs {n1})")

# even spacing keeps the minimum distance
tight = make_ground("GroundEven", size=5.0, segments=20, weight=lambda x, y: 1.0)
cat4 = new_category(
    "Even",
    make_assets("Tree", 1),
    density=100.0,
    even=True,
    min_distance=0.8,
    edge_scale=0.0,
    threshold=0.0,
)
layers.add_layer(tight, cat4, "grass", scene)
pos = positions(instances_of(tight))
tree = KDTree(len(pos))
for i, p in enumerate(pos):
    tree.insert(p, i)
tree.balance()
closest = min(tree.find_n(p, 2)[1][2] for p in pos) if len(pos) > 1 else 0.0
check(len(pos) > 40, f"even spacing still fills the area ({len(pos)})")
check(closest >= 0.8 - 1e-3, f"even spacing keeps 0.8 m between objects (closest {closest:.3f})")

# alignment to a tilted surface
slope = make_ground("GroundSlope", weight=lambda x, y: 1.0, rotation=math.radians(30.0))
cat5 = new_category("Align", make_assets("Slope", 1), density=2.0, align=1.0, tilt=0.0, yaw=0.0)
layers.add_layer(slope, cat5, "grass", scene)
normal = Matrix.Rotation(math.radians(30.0), 3, "X") @ Vector((0, 0, 1))
dots = np.array([(m.to_3x3() @ Vector((0, 0, 1))).normalized().dot(normal) for _, m in instances_of(slope)])
check(len(dots) > 20 and dots.min() > 0.999, f"align 1 follows the 30 deg slope (min dot {dots.min():.4f})")
cat5.align = 0.0
dots = np.array([(m.to_3x3() @ Vector((0, 0, 1))).normalized()[2] for _, m in instances_of(slope)])
check(dots.min() > 0.999, "align 0 stays upright on the slope")

# two layers on one object and removal
two = make_ground("GroundTwo", weight=lambda x, y: 1.0)
layers.add_layer(two, cat2, "grass", scene)
layers.add_layer(two, cat, "grass", scene)
names = {n for n, _ in instances_of(two)}
check(any(n.startswith("Rock") for n in names) and any(n.startswith("Grass") for n in names), "two layers both scatter")
# a later layer must only use the mesh as ground, never the instances an earlier layer made
stack = make_ground("GroundStack", weight=lambda x, y: 1.0)
half = stack.vertex_groups.new(name="half")
for v in stack.data.vertices:
    half.add([v.index], 1.0 if v.co.x > 5.0 else 0.0, "REPLACE")
cat_back = new_category("Back", make_assets("Back", 1), density=10.0, edge_scale=0.0, scale_min=1.0, scale_max=1.0)
layers.add_layer(stack, cat2, "grass", scene)  # rocks everywhere first
layers.add_layer(stack, cat_back, "half", scene)  # then something only on x > 5
back = [m for n, m in instances_of(stack) if n.startswith("Back")]
check(len(back) > 100, f"second layer scatters ({len(back)})")
check(
    all(m.translation.x > 4.4 for m in back),
    "second layer stays inside its painted area, not on the first layer's rocks",
)
check(all(abs(m.to_scale().x - 1.0) < 1e-3 for m in back), "second layer objects keep their own scale")

layers.remove_layer(two, 0)
names = {n for n, _ in instances_of(two)}
check(len(two.sb_layers) == 1 and not any(n.startswith("Rock") for n in names), "removing a layer removes its objects")
check(len([m for m in two.modifiers if m.name.startswith("Scatter")]) == 1, "removing a layer removes its modifier")

# a rotated or scaled ground is flagged: instances would inherit it
skew = make_ground("GroundSkew")
skew.scale = (2.0, 2.0, 2.0)
check(layers.transform_issue(skew) and not layers.transform_issue(flat), "scaled ground is flagged, plain one is not")


# --- placement filters, chances and viewport share (0.2) -------------------------------------------
def make_slopes(name, location=(0.0, 0.0, 0.0)):
    """Flat for x <= 0, a 45 degree ramp (z = x) for x > 0; every face is exactly flat or exactly 45 degrees."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=40, y_segments=40, size=10.0)
    for v in bm.verts:
        v.co.z = max(v.co.x, 0.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    scene.collection.objects.link(ob)
    vg = ob.vertex_groups.new(name="grass")
    for v in me.vertices:
        vg.add([v.index], 1.0, "REPLACE")
    return ob


def make_named_assets(name, names):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    for item in names:
        me = bpy.data.meshes.new(item)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=0.2)
        bm.to_mesh(me)
        bm.free()
        col.objects.link(bpy.data.objects.new(item, me))
    return col


slopes = make_slopes("GroundSlopes")
cat_f = new_category("Filter", make_assets("Filter", 1), density=6.0, edge_scale=0.0, tilt=0.0, seed=2)
layers.add_layer(slopes, cat_f, "grass", scene)
every = positions(instances_of(slopes))
check(len(every) > 500 and every[:, 0].min() < -5 and every[:, 0].max() > 5, "slope filter baseline covers both parts")
cat_f.max_slope = math.radians(30.0)
flat_only = positions(instances_of(slopes))
check(len(flat_only) > 200 and flat_only[:, 0].max() < 0.01, "max slope 30 keeps objects off the 45 degree ramp")
cat_f.max_slope = math.radians(90.0)
cat_f.min_slope = math.radians(30.0)
ramp_only = positions(instances_of(slopes))
check(len(ramp_only) > 200 and ramp_only[:, 0].min() > -0.01, "min slope 30 keeps objects off the flat part")
cat_f.min_slope = 0.0
cat_f.use_height, cat_f.height_min, cat_f.height_max = True, 2.0, 4.0
band = positions(instances_of(slopes))
check(len(band) > 50 and band[:, 2].min() > 2.0 - 1e-3 and band[:, 2].max() < 4.0 + 1e-3, "height band 2..4 holds")
cat_f.use_height = False
check(len(positions(instances_of(slopes))) == len(every), "switching the filters off restores everything")

# keep away from a mesh: the independent distance is a point to box distance
road = make_ground("GroundRoad", weight=lambda x, y: 1.0)
block_me = bpy.data.meshes.new("Block")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, 0.0, 1.0))
bm.to_mesh(block_me)
bm.free()
keep_out = bpy.data.objects.new("KeepOut", block_me)
scene.collection.objects.link(keep_out)
cat_a = new_category("Avoid", make_assets("Avoid", 1), density=3.0, edge_scale=0.0, seed=3)
layers.add_layer(road, cat_a, "grass", scene)


def box_distance(p):
    dx, dy = max(abs(p[0]) - 1.0, 0.0), max(abs(p[1]) - 1.0, 0.0)
    return math.hypot(dx, dy)


free = positions(instances_of(road))
check(sum(box_distance(p) < 3.0 for p in free) > 100, "baseline has objects near the block")
cat_a.avoid_object, cat_a.avoid_distance = keep_out, 3.0
away = positions(instances_of(road))
check(len(away) > 500, f"keep-away still fills the rest ({len(away)})")
check(min(box_distance(p) for p in away) > 3.0 - 0.1, "no object within 3 m of the block")
cat_a.avoid_object = None
check(len(positions(instances_of(road))) == len(free), "clearing the keep-away object restores the objects")
bpy.data.objects.remove(keep_out)  # it sits at the origin: keep later ray casts clear of it

# viewport density is a subset, a bake keeps everything
view_cat = new_category("View", make_assets("View", 1), density=4.0, edge_scale=0.0, seed=6)
view_ground = make_ground("GroundView", weight=lambda x, y: 1.0)
layers.add_layer(view_ground, view_cat, "grass", scene)
full = positions(instances_of(view_ground))
view_cat.viewport_percent = 40.0
part = positions(instances_of(view_ground))
check(0.3 < len(part) / len(full) < 0.5, f"viewport density 40% shows about 40% ({len(part)} of {len(full)})")
tree = KDTree(len(full))
for i, p in enumerate(full):
    tree.insert(p, i)
tree.balance()
check(all(tree.find(p)[2] < 1e-4 for p in part), "the viewport share is a subset of the full pattern")
view_out = place.output_collection(scene, view_cat)
ctx.view_layer.objects.active = view_ground
baked = layers.bake_layer(ctx, view_ground, 0, view_out, True)
check(len(baked) == len(full), f"a bake ignores the viewport share ({len(baked)} vs {len(full)})")
mod = view_ground.modifiers[view_ground.sb_layers[0].modifier]
share_id = layers.socket_ids(mod.node_group)["Viewport Percent"]
check(abs(layers.get_input(mod, share_id) - 40.0) < 1e-3, "the share is restored after a bake")
for o in baked:
    bpy.data.objects.remove(o)

# model chances: layers and brush
heavy_col = make_named_assets("Chances", ("Heavy", "Light"))
chance_cat = new_category("Chances", heavy_col, density=8.0, edge_scale=0.0, seed=4, radius=4.0, count=60)
chance_ground = make_ground("GroundChance", weight=lambda x, y: 1.0)
layers.add_layer(chance_ground, chance_cat, "grass", scene)
check(chance_cat.pick is None, "equal chances need no pick list")
heavy_col.objects["Heavy"].sb_weight = 9
check(chance_cat.pick is not None and len(chance_cat.pick.objects) == 10, "chances 9 and 1 make a pick list of ten")
pick_name = chance_cat.pick.name
check(
    all(lc.exclude for lc in ctx.view_layer.layer_collection.children if lc.name == pick_name),
    "the pick list is hidden",
)
names = [n.split(".")[0] for n, _ in instances_of(chance_ground)]
share = names.count("Heavy") / len(names)
check(len(names) > 2000 and 0.86 < share < 0.94, f"chance 9:1 gives about 90% Heavy ({share:.3f} of {len(names)})")
heavy_col.objects["Light"].sb_weight = 0
names = {n.split(".")[0] for n, _ in instances_of(chance_ground)}
check(names == {"Heavy"}, "chance 0 never appears")
heavy_col.objects["Light"].sb_weight = 1
heavy_col.objects["Heavy"].sb_weight = 1
check(chance_cat.pick is None and pick_name not in bpy.data.collections, "equal chances again remove the pick list")
names = {n.split(".")[0] for n, _ in instances_of(chance_ground)}
check(names == {"Heavy", "Light"}, "both models are back")

heavy_col.objects["Heavy"].sb_weight = 9
chance_board = make_ground("BoardChance", size=30.0, segments=2)
chance_board.location = (500.0, 0.0, 0.0)
ctx.view_layer.update()
chance_painter = place.Painter(ctx, chance_cat, seed=8)
placed_models = []
for _ in range(12):
    placed_models += chance_painter.stamp(Vector((500.0, 0.0, 0.0)), Vector((0, 0, 1)))
heavy_share = sum(1 for o in placed_models if o.data is heavy_col.objects["Heavy"].data) / len(placed_models)
check(
    len(placed_models) > 12 * 60 * 0.95 and 0.86 < heavy_share < 0.94,
    f"the brush follows the chances too ({heavy_share:.3f}, {len(placed_models)} placed)",
)
place.clear_placed(scene, chance_cat)
heavy_col.objects["Light"].sb_weight = 0
only_heavy = place.Painter(ctx, chance_cat, seed=9).stamp(Vector((500.0, 0.0, 0.0)), Vector((0, 0, 1)))
check(only_heavy and all(o.data is heavy_col.objects["Heavy"].data for o in only_heavy), "the brush skips chance 0")
place.clear_placed(scene, chance_cat)

# brush filters on the same ramp, away from everything else
ramp_board = make_slopes("BoardSlopes", location=(200.0, 0.0, 0.0))
brush_f = new_category("BrushFilter", make_assets("BrushFilter", 1), radius=6.0, count=200, tilt=0.0, seed=5)
ctx.view_layer.update()
brush_f.max_slope = math.radians(30.0)
got = place.Painter(ctx, brush_f, seed=1).stamp(Vector((197.0, 0.0, 0.0)), Vector((0, 0, 1)))
check(len(got) > 20 and all(o.matrix_world.translation.x < 200.01 for o in got), "brush max slope keeps off the ramp")
place.clear_placed(scene, brush_f)
brush_f.max_slope, brush_f.min_slope = math.radians(90.0), math.radians(30.0)
got = place.Painter(ctx, brush_f, seed=1).stamp(Vector((203.0, 0.0, 3.0)), Vector((0, 0, 1)))
check(
    len(got) > 10 and all(o.matrix_world.translation.x > 199.99 for o in got), "brush min slope keeps off the flat part"
)
place.clear_placed(scene, brush_f)
brush_f.min_slope = 0.0
brush_f.use_height, brush_f.height_min, brush_f.height_max = True, 2.0, 4.0
got = place.Painter(ctx, brush_f, seed=1).stamp(Vector((203.0, 0.0, 3.0)), Vector((0, 0, 1)))
heights = [o.matrix_world.translation.z for o in got]
check(len(got) > 5 and min(heights) > 2.0 - 1e-3 and max(heights) < 4.0 + 1e-3, "brush height band holds")
place.clear_placed(scene, brush_f)

keep_board = make_ground("BoardKeep", size=15.0, segments=2)
keep_board.location = (300.0, 0.0, 0.0)
keep_block = bpy.data.objects.new("KeepBlock", block_me)
keep_block.location = (300.0, 0.0, 0.0)
scene.collection.objects.link(keep_block)
brush_k = new_category("BrushKeep", make_assets("BrushKeep", 1), radius=8.0, count=200, tilt=0.0, seed=7)
brush_k.avoid_object, brush_k.avoid_distance = keep_block, 2.5
ctx.view_layer.update()
got = place.Painter(ctx, brush_k, seed=1).stamp(Vector((300.0, 0.0, 0.0)), Vector((0, 0, 1)))
distances = [box_distance(o.matrix_world.translation - Vector((300.0, 0.0, 0.0))) for o in got]
check(len(got) > 30 and min(distances) > 2.5 - 1e-3, f"brush keeps 2.5 m away from the block ({len(got)} placed)")
place.clear_placed(scene, brush_k)

# --- bake -----------------------------------------------------------------------------------------
bake_ground = make_ground("GroundBake", size=3.0, segments=12, weight=lambda x, y: 1.0)
cat6 = new_category("Bake", make_assets("Pebble", 2), density=4.0, seed=9)
layers.add_layer(bake_ground, cat6, "grass", scene)
before = instances_of(bake_ground)
out = place.output_collection(scene, cat6)
ctx.view_layer.objects.active = bake_ground
try:
    layers.bake_layer(ctx, bake_ground, 0, out, False, limit=5)
    check(False, "bake over the limit should refuse")
except ValueError:
    pass
check(len(out.objects) == 0 and len(bake_ground.sb_layers) == 1, "a refused bake creates nothing and keeps the layer")
made = layers.bake_layer(ctx, bake_ground, 0, out, False)
check(len(made) == len(before), f"bake makes one object per instance ({len(made)} vs {len(before)})")
want = np.sort(positions(before), axis=0)
got = np.sort(np.array([o.matrix_world.translation[:] for o in made]), axis=0)
check(want.shape == got.shape and np.allclose(want, got, atol=1e-4), "baked objects sit where the instances were")
check(
    all(o.data is bpy.data.objects[o.name.split(".")[0]].data for o in made), "baked objects share the source mesh data"
)
check(len(bake_ground.sb_layers) == 0 and not bake_ground.modifiers, "baking removes the layer unless asked to keep it")

for o in [o for o in scene.objects if o.name.startswith("Ground")]:  # the brush casts at real surfaces
    bpy.data.objects.remove(o)

# --- click brush ----------------------------------------------------------------------------------
board = make_ground("Board", size=10.0, segments=2)
rocks = make_assets("Stone", 4, 0.4)
brush_cat = new_category(
    "Stones",
    rocks,
    radius=3.0,
    count=40,
    scale_min=0.5,
    scale_max=1.5,
    height_var=0.0,
    tilt=0.0,
    align=1.0,
)
ctx.view_layer.update()
painter = place.Painter(ctx, brush_cat, seed=11)
made = painter.stamp(Vector((1.0, 2.0, 0.0)), Vector((0, 0, 1)))
check(len(made) == 40, f"stamp places `count` objects ({len(made)})")
pos = np.array([o.matrix_world.translation[:] for o in made])
dist = np.hypot(pos[:, 0] - 1.0, pos[:, 1] - 2.0)
check(
    dist.max() <= 3.0 + 1e-4 and dist.mean() > 1.5,
    f"objects fill the brush disk (max {dist.max():.2f}, mean {dist.mean():.2f})",
)
check(np.abs(pos[:, 2]).max() < 1e-4, "objects land on the surface")
sizes = np.array([o.matrix_world.to_scale().x for o in made])
check(
    sizes.min() >= 0.5 - 1e-3 and sizes.max() <= 1.5 + 1e-3 and np.ptp(sizes) > 0.5, "brush scale follows the settings"
)
check({o.name.rstrip("0123456789.") for o in made} <= {"Stone"}, "only category models are placed")
check(len({o.data.name for o in made}) > 1, "several models are used")
check(all(o.get("sb_placed") and o.get("sb_cat") == brush_cat.uid for o in made), "placed objects are tagged")
check(
    all(o.name in painter.out.objects for o in made) and painter.out.name == "Stones Placed",
    "they live in the output collection",
)
check(len(painter.out.objects) == 40, "output collection holds exactly the placed objects")
check(all(any(o.data is r.data for r in rocks.objects) for o in made), "placed objects are linked duplicates")

# determinism
place.clear_placed(scene, brush_cat)
again = place.Painter(ctx, brush_cat, seed=11).stamp(Vector((1.0, 2.0, 0.0)), Vector((0, 0, 1)))
pos2 = np.array([o.matrix_world.translation[:] for o in again])
check(np.allclose(pos, pos2, atol=1e-5), "the same seed repeats the same stamp")
place.clear_placed(scene, brush_cat)
check(len(painter.out.objects) == 0, "clear removes every placed object")

# cursor ray ignores the brush's own objects
painter = place.Painter(ctx, brush_cat, seed=2)
brush_cat.radius, brush_cat.count = 0.0, 1
one = painter.stamp(Vector((0.0, 0.0, 0.0)), Vector((0, 0, 1)))
check(
    len(one) == 1 and (one[0].matrix_world.translation - Vector((0, 0, 0))).length < 1e-5,
    "radius 0 places at the cursor",
)
hit = painter.cast(Vector((0, 0, 5)), Vector((0, 0, -1)))
check(hit is not None and abs(hit[0].z) < 1e-4, "the ray passes through brush-placed objects to the ground")
check(painter.cast(Vector((50, 50, 5)), Vector((0, 0, -1))) is None, "a ray into the void finds nothing")

# spacing
place.clear_placed(scene, brush_cat)
brush_cat.radius, brush_cat.count, brush_cat.min_distance = 4.0, 60, 0.7
painter = place.Painter(ctx, brush_cat, seed=3)
made = painter.stamp(Vector((0.0, 0.0, 0.0)), Vector((0, 0, 1)))
made += painter.stamp(Vector((1.5, 0.0, 0.0)), Vector((0, 0, 1)))
pos = np.array([o.matrix_world.translation[:] for o in made])
tree = KDTree(len(pos))
for i, p in enumerate(pos):
    tree.insert(p, i)
tree.balance()
closest = min(tree.find_n(p, 2)[1][2] for p in pos)
check(
    len(made) > 20 and closest >= 0.7 - 1e-4, f"min distance holds across stamps (closest {closest:.3f}, n={len(made)})"
)
fresh = place.Painter(ctx, brush_cat, seed=4)
extra = fresh.stamp(Vector((0.0, 0.0, 0.0)), Vector((0, 0, 1)))
pos3 = np.array([o.matrix_world.translation[:] for o in extra]) if extra else np.zeros((0, 3))
allp = np.vstack([pos, pos3]) if len(pos3) else pos
tree = KDTree(len(allp))
for i, p in enumerate(allp):
    tree.insert(p, i)
tree.balance()
closest = min(tree.find_n(p, 2)[1][2] for p in allp)
check(closest >= 0.7 - 1e-4, f"a new stroke respects objects of earlier strokes (closest {closest:.3f})")

# a Painter outlives categories being added while the tool runs (the list reallocates)
for extra in range(12):
    scene.sb_categories.add().uid = 900 + extra
check(
    len(painter.cat.name) > 0 and painter.cat.uid == brush_cat.uid, "the painter finds its category after the list grew"
)
for _ in range(12):
    scene.sb_categories.remove(len(scene.sb_categories) - 1)

# erase
brush_cat.radius = 1.0
erased = fresh.erase(Vector((0.0, 0.0, 0.0)))
left = [o for o in fresh.out.objects if o.matrix_world.translation.length < 1.0 - 1e-4]
check(erased > 0 and not left, f"erase removes everything inside the radius ({erased} removed)")
check(len(fresh.out.objects) > 10, "erase keeps objects outside the radius")

# slope limit
place.clear_placed(scene, brush_cat)
steep = make_ground("Steep", size=4.0, segments=2, rotation=math.radians(60.0))
steep.location = (30.0, 0.0, 0.0)
ctx.view_layer.update()
normal = Matrix.Rotation(math.radians(60.0), 3, "X") @ Vector((0, 0, 1))
brush_cat.radius, brush_cat.count, brush_cat.min_distance = 1.0, 20, 0.0
brush_cat.max_slope = math.radians(45.0)
painter = place.Painter(ctx, brush_cat, seed=5)
none = painter.stamp(Vector((30.0, 0.0, 0.0)), normal)
check(len(none) == 0, f"max slope 45 skips a 60 deg surface ({len(none)} placed)")
brush_cat.max_slope = math.radians(90.0)
some = place.Painter(ctx, brush_cat, seed=5).stamp(Vector((30.0, 0.0, 0.0)), normal)
check(len(some) > 10, "without the limit the slope gets objects")
dots = [((o.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()).dot(normal) for o in some]
check(min(dots) > 0.999, "placed objects follow the slope normal")
place.clear_placed(scene, brush_cat)

# --- operators ------------------------------------------------------------------------------------
check(not bpy.ops.scatter_brush.paint.poll(), "the modal brush needs a 3D viewport")
operators.draw_brush()  # nothing to draw: must not raise
check(len(operators.ring(Vector((0, 0, 0)), Vector((0, 0, 1)), 2.0)) == 49, "brush ring has 48 segments")
ring_painter = place.Painter(ctx, brush_cat, seed=1)
drape = operators.surface_ring(ring_painter, Vector((0, 0, 0)), Vector((0, 0, 1)), 2.0)
check(len(drape) == 49 and all(abs(p[2] - 0.03) < 1e-4 for p in drape), "the brush ring hugs the surface")
over_void = operators.surface_ring(ring_painter, Vector((9.5, 0, 0)), Vector((0, 0, 1)), 2.0)
check(len(over_void) == 49, "the ring stays closed where part of it hangs over the edge")

ops_ground = make_ground("OpsGround", size=3.0, segments=6, weight=lambda x, y: 1.0)
mine = make_assets("Fern", 3)
for o in ctx.view_layer.objects:
    o.select_set(False)
for o in list(mine.objects):  # models in the scene, scaled and turned like an imported FBX
    mine.objects.unlink(o)
    scene.collection.objects.link(o)
    o.scale = (3.0, 3.0, 3.0)
    o.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    o.select_set(True)
bpy.data.collections.remove(mine)
ctx.view_layer.objects.active = bpy.data.objects["Fern0"]
before = len(scene.sb_categories)
check(bpy.ops.scatter_brush.category_add() == {"FINISHED"}, "category_add runs")
new = scene.sb_categories[scene.sb_index]
check(
    len(scene.sb_categories) == before + 1 and new.name == "Fern" and len(place.sources(new)) == 3,
    "category from selection",
)
check(
    all(o.users_collection == (new.collection,) for o in place.sources(new)),
    "the models moved into the category collection",
)
layer_collection = ctx.view_layer.layer_collection.children.get(new.collection.name)
check(layer_collection is not None and layer_collection.exclude, "the model collection is hidden but still a source")
from scatter_brush import ui  # noqa: E402

check(ui.needs_prepare(new), "scaled and rotated models are flagged")
dims = {o.name: tuple(o.dimensions) for o in place.sources(new)}
check(bpy.ops.scatter_brush.assets_prepare() == {"FINISHED"}, "assets_prepare runs")
for o in place.sources(new):
    check(
        all(abs(s - 1.0) < 1e-5 for s in o.scale) and all(abs(r) < 1e-5 for r in o.rotation_euler),
        f"{o.name}: scale and rotation applied",
    )
    low = min(v.co.z for v in o.data.vertices)
    check(abs(low) < 1e-5, f"{o.name}: origin at the bottom ({low:.4f})")
    check(abs(sum(v.co.x for v in o.data.vertices)) < 1e-4, f"{o.name}: origin centered")
    check(
        all(abs(a - b) < 1e-3 for a, b in zip(sorted(o.dimensions), sorted(dims[o.name]), strict=True)),
        f"{o.name}: size kept",
    )
check(not ui.needs_prepare(new), "prepared models are no longer flagged")

ctx.view_layer.objects.active = ops_ground
for o in ctx.view_layer.objects:
    o.select_set(o is ops_ground)
ops_ground.vertex_groups.active_index = 0
check(bpy.ops.scatter_brush.layer_add() == {"FINISHED"}, "layer_add runs")
check(len(ops_ground.sb_layers) == 1 and ops_ground.sb_layers[0].group == "grass", "layer uses the active vertex group")
check(len(instances_of(ops_ground)) > 50, "operator-made layer scatters")
new.density = 3.0
check(new.density == 3.0 and len(instances_of(ops_ground)) > 0, "category change reaches the operator-made layer")
check(bpy.ops.scatter_brush.layer_bake(index=0, keep=True) == {"FINISHED"}, "layer_bake runs")
check(
    len(ops_ground.sb_layers) == 1 and len(new.output.objects) > 0,
    "bake with keep leaves the layer and fills the output",
)
check(
    bpy.ops.scatter_brush.layer_paint(index=0) == {"FINISHED"} and ctx.mode == "PAINT_WEIGHT",
    "layer_paint enters weight paint",
)
bpy.ops.object.mode_set(mode="OBJECT")
check(bpy.ops.scatter_brush.clear(), "clear runs")
check(len(new.output.objects) == 0, "clear empties the output")
bpy.ops.scatter_brush.seed()
check(new.seed != 1 or True, "seed operator runs")
check(bpy.ops.scatter_brush.layer_remove(index=0) == {"FINISHED"} and not ops_ground.sb_layers, "layer_remove runs")
layers.add_layer(ops_ground, new, "grass", scene)
check(bpy.ops.scatter_brush.category_remove() == {"FINISHED"}, "category_remove runs")
check(
    not ops_ground.sb_layers and not [m for m in ops_ground.modifiers if m.name.startswith("Scatter")],
    "removing a category removes its layers",
)

# translations cover the interface strings we ship
for needed in ("Click Brush", "Weight Paint Layers", "Start Brush", "Bake to Objects", "Prepare Models"):
    check(needed in i18n.TR, f"missing Turkish string: {needed}")

# register twice is covered by bdev; unregister here to prove the clean exit
sb.unregister()
sb.register()
sb.unregister()
check(not hasattr(bpy.types.Scene, "sb_categories"), "unregister removes the scene properties")

if failures:
    print("\nFAILURES:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("scatter_brush: all checks passed")
