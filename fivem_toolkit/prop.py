"""Prop builder: plain meshes become Sollumz drawables with converted materials, LODs, collision, a YTYP archetype and a
texture dictionary. Sollumz does the conversion; this module orders the steps and fills in what Sollumz leaves to
the user.
"""
from types import SimpleNamespace

import bmesh
import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

from . import compat, doctor, names, textures

LOD_RATIOS = {"AUTO": (0.5, 0.25, 0.1), "AGGRESSIVE": (0.35, 0.12, 0.04), "GENTLE": (0.7, 0.45, 0.25)}
MIN_LOD_SOURCE_TRIS = 200  # below this a LOD saves nothing worth having
MIN_LOD_TRIS = 12


class BuildError(Exception):
    """A problem the user can act on; the message goes to the status bar."""


def world_radius(drawable):
    """Half the diagonal of the world-space bounding box of the drawable's models (its bounding sphere radius)."""
    points = [m.matrix_world @ Vector(c) for m in compat.children_of(drawable, compat.MODEL) for c in m.bound_box]
    if not points:
        return 1.0
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return max((high - low).length / 2.0, 0.05)


def lod_distances(radius, scale=1.0):
    """LOD switch distances in meters, from the size of the prop: small things should vanish sooner than buildings."""
    near = min(250.0, max(15.0, 12.0 * radius)) * scale
    return {"high": near, "med": near * 2.2, "low": near * 5.0, "vlow": min(9998.0, near * 12.0)}


def archetype_lod_dist(radius, scale=1.0):
    """Distance at which the whole prop stops being drawn."""
    return min(1200.0, max(60.0, 40.0 * radius)) * scale


def decimated(context, mesh, ratio):
    """A copy of `mesh` reduced to about `ratio` of its triangles; UVs and material slots survive."""
    temp = bpy.data.objects.new("fk_temp", mesh)
    context.collection.objects.link(temp)
    modifier = temp.modifiers.new("fk", "DECIMATE")
    modifier.ratio = ratio
    context.view_layer.update()
    out = bpy.data.meshes.new_from_object(temp.evaluated_get(context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(temp)
    return out


def collision_mesh(context, model, mode, target_tris):
    """Mesh (in the model's local space) used for the collision of one model."""
    mesh = bpy.data.meshes.new_from_object(model.evaluated_get(context.evaluated_depsgraph_get()))
    if mode == "HULL":
        bm = bmesh.new()
        bm.from_mesh(mesh)
        hull = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
        bmesh.ops.delete(bm, geom=hull["geom_interior"] + hull["geom_unused"], context="VERTS")
        bm.to_mesh(mesh)
        bm.free()
    tris = doctor.triangles(mesh)
    if tris > target_tris:
        reduced = decimated(context, mesh, target_tris / tris)
        bpy.data.meshes.remove(mesh)
        mesh = reduced
    mesh.materials.clear()
    return mesh


class SceneFlags:
    """Sets Sollumz scene options for the duration of a block and puts the user's values back afterwards."""

    def __init__(self, scene, **flags):
        self.scene, self.flags, self.saved = scene, flags, {}

    def __enter__(self):
        for key, value in self.flags.items():
            if hasattr(self.scene, key):
                self.saved[key] = getattr(self.scene, key)
                setattr(self.scene, key, value)

    def __exit__(self, *exc):
        for key, value in self.saved.items():
            setattr(self.scene, key, value)


def make_lods(context, model, s):
    """Fill the medium, low and very low LOD slots of one model; returns how many were created."""
    base = model.data
    previous = doctor.triangles(base)
    if previous < MIN_LOD_SOURCE_TRIS:
        return 0
    created = 0
    for key, ratio in zip(("med", "low", "vlow"), LOD_RATIOS[s.lod_preset], strict=True):
        mesh = decimated(context, base, ratio)
        count = doctor.triangles(mesh)
        if count < MIN_LOD_TRIS or count > previous * 0.8:  # no real saving: skip this level
            bpy.data.meshes.remove(mesh)
            continue
        mesh.name = f"{base.name}_{key}"
        compat.prepare_mesh(mesh)
        model.sz_lods.get_lod(compat.LOD_LEVELS[key]).mesh = mesh
        previous, created = count, created + 1
    return created


def make_composite(context, models, name, mode, target_tris):
    """One composite bound (unparented) built from simplified copies of `models`, placed where the models are."""
    sc = context.scene
    proxies = []
    for model in models:
        mesh = collision_mesh(context, model, mode, target_tris)
        proxy = bpy.data.objects.new(f"{name}_col", mesh)
        proxy.matrix_world = model.matrix_world.copy()
        context.collection.objects.link(proxy)
        proxies.append(proxy)
    if not proxies:
        return None
    before = {o.as_pointer() for o in bpy.data.objects}  # by identity: Sollumz reuses names when it converts
    compat.select_only(context, *proxies)
    with SceneFlags(sc, create_seperate_composites=False, center_composite_to_selection=False,
                    bound_child_type=compat.BVH):
        bpy.ops.sollumz.converttocomposite()
    composites = [o for o in bpy.data.objects if o.as_pointer() not in before and compat.kind(o) == compat.COMPOSITE]
    if not composites:
        raise BuildError(rpt_("Sollumz did not create the collision of '{name}'.").format(name=name))
    composite = composites[0]
    composite.name = name
    shapes = [c for c in composite.children_recursive if c.type == "MESH"]
    if shapes:  # Sollumz warns about bounds without a collision material
        compat.select_only(context, *shapes)
        bpy.ops.sollumz.clearandcreatecollisionmaterial()
    return composite


def add_collision(context, drawable, s):
    """Collision of one prop: a composite bound parented to the drawable, keeping its place in the world."""
    composite = make_composite(context, compat.children_of(drawable, compat.MODEL), f"{drawable.name}.col",
                               s.collision, s.collision_tris)
    if composite is not None:
        world = composite.matrix_world.copy()
        composite.parent = drawable
        composite.matrix_world = world
    return composite


def add_archetypes(context, drawables, s):
    """One YTYP archetype per drawable, in a YTYP named like the resource. Returns the archetypes of these drawables."""
    sc = context.scene
    if not len(sc.ytyps):
        bpy.ops.sollumz.createytyp()
        sc.ytyps[0].name = s.resource_name
    ytyp = sc.ytyps[sc.ytyp_index]
    sc.create_archetype_type = compat.ARCHETYPE_BASE
    existing = {a.name for y in sc.ytyps for a in y.archetypes}
    todo = [d for d in drawables if names.asset_name(d.name) not in existing]
    if todo:
        compat.select_only(context, *todo)
        bpy.ops.sollumz.createarchetypefromselected()
    mine = [a for a in ytyp.archetypes if a.asset in drawables]
    for archetype in mine:
        archetype.lod_dist = archetype_lod_dist(world_radius(archetype.asset), s.lod_scale)
    return mine


def add_texture_dictionaries(context, drawables):
    """A texture dictionary per drawable, named like it, holding the images its materials use."""
    sc = context.scene
    made = 0
    existing = {t.name for t in sc.sz_txds.texture_dictionaries}
    for drawable in drawables:
        name = names.asset_name(drawable.name)
        images = {img for model in compat.children_of(drawable, compat.MODEL) for mat in model.data.materials
                  for img in doctor.material_images(mat) if img is not None}
        if name in existing or not images:
            continue
        txd = sc.sz_txds.new_texture_dictionary(name)
        for image in sorted(images, key=lambda i: i.name):
            txd.new_texture(image)
        made += 1
    return made


def settings_with(s, **overrides):
    """A plain copy of the scene settings with some values replaced, for building parts of a bigger asset."""
    values = {p.identifier: getattr(s, p.identifier) for p in s.bl_rna.properties if p.identifier != "rna_type"}
    return SimpleNamespace(**{**values, **overrides})


def build(context, objects, s):
    """Turn plain mesh objects into FiveM props. Returns (drawables, summary text). Raises BuildError."""
    try:
        compat.require()
    except compat.SollumzMissing as e:
        raise BuildError(str(e)) from e
    meshes = [o for o in objects if o.type == "MESH" and compat.kind(o) == "sollumz_none"]
    if not meshes:
        raise BuildError(rpt_("Select the mesh objects that should become props."))
    problems = doctor.scan(meshes, s)
    notes = []
    if s.auto_fix:
        fixed, failed = doctor.fix_all(context, problems)
        notes.append(rpt_("{count} problems fixed").format(count=fixed))
        problems = doctor.scan(meshes, s)
    blocking = [p for p in problems if p["severity"] == doctor.ERROR]
    if blocking:
        raise BuildError(rpt_("Fix these first: {list}").format(list="; ".join(p["message"] for p in blocking[:3])))

    if s.convert_dds:  # Sollumz exports textures from DDS files only
        images = {img for o in meshes for m in o.data.materials for img in doctor.material_images(m) if img is not None}
        for image in sorted(images, key=lambda i: i.name):
            textures.convert_image(image, int(s.max_texture))
    before = {o.as_pointer() for o in bpy.data.objects}  # by identity: the drawable takes the name of the mesh it wraps
    with SceneFlags(context.scene, create_seperate_drawables=s.separate, center_drawable_to_selection=False,
                    auto_create_embedded_col=s.collision == "MESH"):
        compat.select_only(context, *meshes)
        bpy.ops.sollumz.converttodrawable()
    made = [o for o in bpy.data.objects if o.as_pointer() not in before and compat.kind(o) == compat.DRAWABLE]
    if not made:
        raise BuildError(rpt_("Sollumz could not convert the selection."))

    models = [m for d in made for m in compat.children_of(d, compat.MODEL)]
    compat.select_only(context, *models)
    bpy.ops.sollumz.autoconvertmaterials()
    for model in models:
        compat.prepare_mesh(model.data)

    lod_count = 0
    if s.make_lods:
        for drawable in made:
            created = sum(make_lods(context, m, s) for m in compat.children_of(drawable, compat.MODEL))
            if created:
                distances = lod_distances(world_radius(drawable), s.lod_scale)
                for key, value in distances.items():
                    setattr(drawable.drawable_properties, f"lod_dist_{key}", value)
            lod_count += created
        notes.append(rpt_("{count} LOD meshes").format(count=lod_count))
    if s.collision in ("PROXY", "HULL"):
        for drawable in made:
            add_collision(context, drawable, s)
        notes.append(rpt_("collision: {mode}").format(mode=s.collision.lower()))
    if s.create_ytyp:
        add_archetypes(context, made, s)
        notes.append(rpt_("YTYP archetypes"))
    if s.create_ytd and compat.has_ytd():
        notes.append(rpt_("{count} texture dictionaries").format(count=add_texture_dictionaries(context, made)))
    elif s.create_ytd:
        notes.append(rpt_("no YTD (update Sollumz to 2.8.3 or newer)"))
    compat.select_only(context, *made)
    return made, rpt_("{count} props built: {notes}").format(count=len(made), notes=", ".join(notes))
