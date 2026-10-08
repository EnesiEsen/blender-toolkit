"""Click brush: where and how objects are placed and erased. No modal or drawing code, so a test can drive it."""

import math
import random

import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

UP = Vector((0.0, 0.0, 1.0))
MAX_PER_STAMP = 1000
RAY_SKIPS = 48  # how many brush-placed objects a cursor ray may pass through before it gives up


def sources(cat):
    """The models of a category, in name order so a seed gives the same picks every time."""
    if cat.collection is None:
        return []
    return sorted((o for o in cat.collection.all_objects), key=lambda o: o.name)


def pickable(cat):
    """The models the brush may pick: the ones whose chance is above zero."""
    return [o for o in sources(cat) if o.sb_weight > 0]


def output_collection(scene, cat):
    """The collection that holds the objects the brush placed for this category (made on first use)."""
    out = cat.output
    if out is None or out.name not in bpy.data.collections:
        out = bpy.data.collections.new(f"{cat.name} Placed")
        scene.collection.children.link(out)
        cat.output = out
    elif out.name not in {c.name for c in scene.collection.children_recursive}:
        scene.collection.children.link(out)
    return out


def placement_matrix(rng, cat, loc, normal):
    """World matrix for one object: random size, turn and lean on top of the (blended) surface normal."""
    lean = UP.lerp(normal, cat.align)
    if lean.length < 1e-6:
        lean = UP.copy()
    frame = UP.rotation_difference(lean.normalized()).to_matrix()
    low, high = sorted((cat.scale_min, cat.scale_max))
    size = rng.uniform(low, high)
    height = size * (1.0 + rng.uniform(-cat.height_var, cat.height_var))
    tilt = cat.tilt
    spin = Euler((rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), rng.uniform(0.0, cat.yaw))).to_matrix()
    matrix = (frame @ spin).to_4x4() @ Matrix.Diagonal((size, size, height, 1.0))
    matrix.translation = loc - UP * cat.sink
    return matrix


def disk_point(rng, center, normal, radius):
    """Uniform random point on the disk of `radius` around `center`, lying in the plane of `normal`."""
    r = radius * math.sqrt(rng.random())
    angle = rng.uniform(0.0, math.tau)
    t1 = normal.orthogonal().normalized()
    t2 = normal.cross(t1)
    return center + t1 * (r * math.cos(angle)) + t2 * (r * math.sin(angle))


class Painter:
    """State of one brush session: the random stream, the spacing grid of what is already placed, the skip list."""

    strokes = 0

    def __init__(self, context, cat, seed=None):
        self.scene = context.scene
        self.context = context
        self.uid = cat.uid
        self.sources = pickable(cat)
        self.chances = [o.sb_weight for o in self.sources]
        self.avoid = None
        avoid_object = cat.avoid_object
        if avoid_object is not None and avoid_object.type == "MESH":
            self.avoid = (avoid_object, BVHTree.FromObject(avoid_object, context.evaluated_depsgraph_get()))
        self.out = output_collection(self.scene, cat)
        assets = [o for c in context.scene.sb_categories if c.collection for o in c.collection.all_objects]
        self.skip = {o.name for o in assets}
        self.skip_data = {o.data for o in assets if o.data is not None}  # linked duplicates share it
        self.rng = random.Random(seed if seed is not None else cat.seed * 1000003 + Painter.strokes)
        Painter.strokes += 1
        self.grid = {}
        self.last = None
        self.made = 0
        self.rebuild_grid()

    @property
    def cat(self):
        """The category, looked up fresh: a pointer to it dies when another category is added (the list reallocates)."""
        for cat in self.scene.sb_categories:
            if cat.uid == self.uid:
                return cat
        raise ReferenceError("The category was removed.")

    # -- spacing grid --------------------------------------------------------------------------------------------
    def _cell(self, p):
        size = self.cat.min_distance
        return (math.floor(p.x / size), math.floor(p.y / size), math.floor(p.z / size))

    def rebuild_grid(self):
        self.grid = {}
        if self.cat.min_distance <= 0.0:
            return
        for ob in self.out.objects:
            if ob.get("sb_placed"):
                self._add(ob.matrix_world.translation.copy())

    def _add(self, p):
        if self.cat.min_distance > 0.0:
            self.grid.setdefault(self._cell(p), []).append(p)

    def _crowded(self, p):
        gap = self.cat.min_distance
        if gap <= 0.0:
            return False
        cx, cy, cz = self._cell(p)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in self.grid.get((cx + dx, cy + dy, cz + dz), ()):
                        if (q - p).length < gap:
                            return True
        return False

    # -- surface -------------------------------------------------------------------------------------------------
    def cast(self, origin, direction, distance=10000.0):
        """First surface hit that is not one of the brush's own objects: (location, normal) or None."""
        depsgraph = self.context.evaluated_depsgraph_get()
        origin = Vector(origin)
        direction = Vector(direction).normalized()
        for _ in range(RAY_SKIPS):
            hit, loc, normal, _index, ob, _matrix = self.scene.ray_cast(depsgraph, origin, direction, distance=distance)
            if not hit:
                return None
            orig = ob.original
            if not orig.get("sb_placed") and orig.name not in self.skip and orig.data not in self.skip_data:
                return loc, normal.normalized()
            step = (loc - origin).length + 1e-3
            distance -= step
            origin = loc + direction * 1e-3
            if distance <= 0.0:
                return None
        return None

    # -- placement filters ---------------------------------------------------------------------------------------
    def allowed(self, cat, p, n):
        """False where the category must stay empty: wrong slope, outside the height band, near the keep-away mesh."""
        slope = n.angle(UP)
        if slope > cat.max_slope + 1e-4 or slope < cat.min_slope - 1e-4:
            return False
        if cat.use_height and not (min(cat.height_min, cat.height_max) <= p.z <= max(cat.height_min, cat.height_max)):
            return False
        if self.avoid is not None:
            obj, tree = self.avoid
            hit = tree.find_nearest(obj.matrix_world.inverted() @ p)
            if hit[0] is not None and hit[3] < cat.avoid_distance:
                return False
        return True

    # -- stamps --------------------------------------------------------------------------------------------------
    def spawn(self, src, matrix):
        ob = src.copy()  # linked duplicate: the mesh data stays shared with the source
        ob.parent = None
        ob.animation_data_clear()
        ob.hide_viewport = False
        ob.hide_render = False
        ob.matrix_world = matrix
        ob["sb_placed"] = 1
        ob["sb_cat"] = self.cat.uid
        self.out.objects.link(ob)
        return ob

    def stamp(self, loc, normal):
        """One click: up to `count` objects spread over the brush disk. Returns the new objects."""
        cat = self.cat
        if not self.sources:
            return []
        made = []
        for _ in range(min(cat.count, MAX_PER_STAMP)):
            if cat.radius > 0.0:
                p = disk_point(self.rng, loc, normal, cat.radius)
                hit = self.cast(p + normal * (cat.radius * 2.0 + 1.0), -normal, cat.radius * 4.0 + 2.0)
                if hit is None:
                    continue
                p, n = hit
            else:
                p, n = loc, normal
            if not self.allowed(cat, p, n) or self._crowded(p):
                continue
            src = self.rng.choices(self.sources, weights=self.chances)[0]
            made.append(self.spawn(src, placement_matrix(self.rng, cat, p, n)))
            self._add(p.copy())
        self.last = loc.copy()
        self.made += len(made)
        return made

    def move(self, loc, normal):
        """Mouse dragged with the button down: stamp again once the cursor has travelled far enough."""
        step = max(self.cat.radius * self.cat.spacing, 0.25 if self.cat.radius <= 0.0 else 0.05)
        if self.last is None or (loc - self.last).length >= step:
            return self.stamp(loc, normal)
        return []

    def erase(self, loc):
        """Remove the brush-placed objects of this category inside the brush radius. Returns how many."""
        r2 = self.cat.radius**2
        gone = [
            ob
            for ob in self.out.objects
            if ob.get("sb_placed") and (ob.matrix_world.translation - loc).length_squared <= max(r2, 1e-4)
        ]
        for ob in gone:
            bpy.data.objects.remove(ob, do_unlink=True)
        if gone:
            self.rebuild_grid()
        self.last = loc.copy()
        return len(gone)


def clear_placed(scene, cat):
    """Delete every brush-placed object of a category. Returns how many."""
    out = cat.output
    if out is None:
        return 0
    gone = [ob for ob in out.objects if ob.get("sb_placed")]
    for ob in gone:
        bpy.data.objects.remove(ob, do_unlink=True)
    return len(gone)
