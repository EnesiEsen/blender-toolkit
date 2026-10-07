"""The Doctor: finds what makes a FiveM asset fail (names, unapplied transforms, missing UVs or materials, oversized
textures, ...) and fixes the safe problems with one click. Works on plain meshes before the build and on Sollumz assets.
"""
import os

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Matrix

from . import compat, names, textures

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"
ROOT_TYPES = (compat.DRAWABLE, compat.FRAGMENT, compat.COMPOSITE, "sollumz_drawable_dictionary")


def issue(severity, code, ob, message, data=""):
    return {"severity": severity, "code": code, "object": ob.name if ob is not None else "", "message": message,
            "data": data}


def is_asset_root(ob):
    """Objects whose name becomes the asset name: Sollumz roots and plain meshes that are about to be converted."""
    if compat.kind(ob) == compat.COMPOSITE:  # a collision parented to a drawable is embedded in it, not an asset
        return ob.parent is None
    if compat.kind(ob) in ROOT_TYPES:
        return ob.parent is None or compat.kind(ob.parent) != compat.FRAGMENT
    return ob.type == "MESH" and compat.kind(ob) == "sollumz_none"


def material_images(material):
    """Images used by the texture nodes of a material (None for a node without an image)."""
    found, stack, seen = [], [material.node_tree] if material and material.node_tree else [], set()
    while stack:
        tree = stack.pop()
        if tree in seen:
            continue
        seen.add(tree)
        for node in tree.nodes:
            if node.type == "TEX_IMAGE":
                found.append(node.image)
            elif node.type == "GROUP" and node.node_tree:
                stack.append(node.node_tree)
    return found


def triangles(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


def scan_object(ob, settings, seen_images):
    found = []
    if is_asset_root(ob) and not names.is_valid(ob.name):
        found.append(issue(ERROR, "NAME", ob, rpt_("'{name}' is not a valid asset name (use lowercase letters, digits "
                                                  "and underscores).").format(name=ob.name)))
    if ob.type != "MESH" or compat.kind(ob).startswith("sollumz_bound"):
        return found
    mesh = ob.data
    if not len(mesh.polygons):
        return [*found, issue(ERROR, "EMPTY_MESH", ob, rpt_("'{name}' has no faces.").format(name=ob.name))]
    _, rotation, scale = ob.matrix_basis.decompose()
    if any(abs(c - 1.0) > 1e-4 for c in scale) or any(abs(a) > 1e-4 for a in rotation.to_euler()):
        found.append(issue(WARNING, "TRANSFORM", ob,
                           rpt_("'{name}' has unapplied scale or rotation.").format(name=ob.name)))
    if ob.modifiers:
        found.append(issue(WARNING, "MODIFIERS", ob, rpt_("'{name}' has modifiers that are not applied.").format(
            name=ob.name)))
    if not mesh.uv_layers:
        found.append(issue(ERROR, "NO_UV", ob, rpt_("'{name}' has no UV map.").format(name=ob.name)))
    if not mesh.materials or any(m is None for m in mesh.materials):
        found.append(issue(ERROR, "NO_MATERIAL", ob, rpt_("'{name}' has an empty material slot or none.").format(
            name=ob.name)))
    elif len(mesh.materials) > 1 and {p.material_index for p in mesh.polygons} != set(range(len(mesh.materials))):
        found.append(issue(WARNING, "UNUSED_SLOTS", ob, rpt_("'{name}' has material slots no face uses.").format(
            name=ob.name)))
    tris = triangles(mesh)
    if tris > settings.tri_limit:
        found.append(issue(WARNING, "TRI_COUNT", ob, rpt_("'{name}' has {tris} triangles (limit {limit}).").format(
            name=ob.name, tris=tris, limit=settings.tri_limit)))
    limit = int(settings.max_texture)
    for material in mesh.materials:
        for image in material_images(material):
            if image is None:
                found.append(issue(ERROR, "TEXTURE_MISSING", ob,
                                   rpt_("A texture node in '{material}' has no image.").format(material=material.name)))
                continue
            if image in seen_images:
                continue
            seen_images.add(image)
            if not image.has_data and not image.packed_file and not os.path.exists(bpy.path.abspath(image.filepath)):
                found.append(issue(ERROR, "TEXTURE_MISSING", ob, rpt_("Image '{image}' is missing on disk.").format(
                    image=image.name), image.name))
                continue
            width, height = image.size
            if width and height and (width, height) != textures.pow2_size(width, height, limit) and (
                    width > limit or height > limit or (width & (width - 1)) or (height & (height - 1))):
                found.append(issue(WARNING, "TEXTURE_SIZE", ob, rpt_(
                    "Image '{image}' is {w}x{h}: use a power of two up to {limit}.").format(
                        image=image.name, w=width, h=height, limit=limit), image.name))
            if not textures.is_dds(image):
                found.append(issue(WARNING, "TEXTURE_FORMAT", ob, rpt_(
                    "Image '{image}' is not a DDS file: FiveM needs DDS (the fix converts it).").format(
                        image=image.name), image.name))
    return found


def scan(objects, settings):
    """All problems of `objects` (and their children). Returns a list of issue dicts."""
    pool, seen_objects = [], set()
    for ob in objects:
        for o in (ob, *ob.children_recursive):
            if o.name not in seen_objects:
                seen_objects.add(o.name)
                pool.append(o)
    found, seen_images, asset_names = [], set(), {}
    for ob in pool:
        found += scan_object(ob, settings, seen_images)
        if is_asset_root(ob):
            asset_names.setdefault(names.asset_name(ob.name), []).append(ob)
    for name, owners in asset_names.items():
        if len(owners) > 1:
            found.append(issue(ERROR, "DUPLICATE_NAME", owners[1],
                               rpt_("{count} assets would be exported as '{name}'.").format(
                                   count=len(owners), name=name)))
    return found


# ---- fixes


def fix_name(context, item):
    ob = bpy.data.objects.get(item["object"])
    if ob is not None:  # already renamed by an earlier fix of the same object
        ob.name = names.unique(names.asset_name(ob.name), {o.name for o in bpy.data.objects if o != ob})


def fix_transform(context, item):
    ob = bpy.data.objects[item["object"]]
    if ob.children:
        raise ValueError(rpt_("'{name}' has children: apply its scale and rotation by hand.").format(name=ob.name))
    location, rotation, scale = ob.matrix_basis.decompose()
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    ob.data.transform(Matrix.LocRotScale(None, rotation, scale))
    ob.matrix_basis = Matrix.Translation(location)


def fix_modifiers(context, item):
    ob = bpy.data.objects[item["object"]]
    evaluated = bpy.data.meshes.new_from_object(ob.evaluated_get(context.evaluated_depsgraph_get()))
    old = ob.data
    ob.modifiers.clear()
    ob.data = evaluated
    if old.users == 0:
        bpy.data.meshes.remove(old)


def box_uv(mesh):
    """UVs by box projection: every face is flattened along the axis its normal points to most."""
    count = len(mesh.vertices)
    co = np.empty(count * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(count, 3)
    loop_vertex = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loop_vertex)
    sizes = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_total", sizes)
    normals = np.empty(len(mesh.polygons) * 3, dtype=np.float32)
    mesh.polygons.foreach_get("normal", normals)
    axis = np.abs(normals.reshape(-1, 3)).argmax(axis=1).repeat(sizes)
    p = co[loop_vertex]
    u = np.where(axis == 0, p[:, 1], p[:, 0])
    v = np.where(axis == 2, p[:, 1], p[:, 2])
    scale = 1.0 / max(float((co.max(axis=0) - co.min(axis=0)).max()), 1e-6)
    layer = mesh.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", np.stack([u * scale, v * scale], axis=1).ravel())


def fix_uv(context, item):
    box_uv(bpy.data.objects[item["object"]].data)


def fix_material(context, item):
    mesh = bpy.data.objects[item["object"]].data
    default = bpy.data.materials.get("fk_default") or bpy.data.materials.new("fk_default")
    if not mesh.materials:
        mesh.materials.append(default)
    for i, m in enumerate(mesh.materials):
        if m is None:
            mesh.materials[i] = default


def fix_slots(context, item):
    ob = bpy.data.objects[item["object"]]
    with context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.material_slot_remove_unused()


def fix_texture(context, item):
    image = bpy.data.images[item["data"]]
    width, height = image.size
    image.scale(*textures.pow2_size(width, height, int(context.scene.fk_settings.max_texture)))


def fix_texture_format(context, item):
    textures.convert_image(bpy.data.images[item["data"]], int(context.scene.fk_settings.max_texture))


FIXES = {"TEXTURE_FORMAT": fix_texture_format, "NAME": fix_name, "TRANSFORM": fix_transform,
         "MODIFIERS": fix_modifiers, "NO_UV": fix_uv,
         "NO_MATERIAL": fix_material, "UNUSED_SLOTS": fix_slots, "TEXTURE_SIZE": fix_texture,
         "DUPLICATE_NAME": fix_name}


def fix(context, item):
    """Apply the fix of one issue. Raises ValueError with a message when it cannot be fixed."""
    function = FIXES.get(item["code"])
    if function is None:
        raise ValueError(rpt_("This problem cannot be fixed automatically."))
    function(context, item)


def fix_all(context, items):
    """Fix everything fixable; returns (fixed count, list of messages for what failed)."""
    fixed, failed = 0, []
    # modifiers before the scale (a bevel must see the unscaled mesh), renames last (issues refer to current names)
    order = {"TRANSFORM": 1, "TEXTURE_FORMAT": 1, "NAME": 2, "DUPLICATE_NAME": 2}
    for item in sorted(items, key=lambda i: order.get(i["code"], 0)):
        if item["code"] not in FIXES:
            continue
        try:
            fix(context, item)
            fixed += 1
        except (ValueError, KeyError, RuntimeError) as e:
            failed.append(f"{item['object']}: {e}")
    return fixed, failed
