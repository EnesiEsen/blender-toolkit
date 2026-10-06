"""MLO builder: reads rooms, portals and entities from a collection layout in Blender and fills the Sollumz MLO
archetype.

Layout (names are matched case-insensitively):

    <interior collection>
        room.<name>          sub-collection: every mesh in it becomes an entity of that room
        room.limbo           optional: objects that belong to the limbo room (GTA allows 12 of them at most)
        portal.<a>.<b>       one quad (4 vertices) in the opening between room a and room b; `limbo` is the outside

The first portal of every interior should connect `limbo` to a room: that is the entrance.
Portal corners follow Sollumz's own convention: counter-clockwise as seen from the `a` side. If CodeWalker shows a
portal facing the wrong way, swap its two room names.
"""
import re
from dataclasses import dataclass

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

from . import compat, names, prop

LIMBO = "limbo"
MAX_LIMBO_ENTITIES = 12  # the limit Sollumz enforces
ROOM_PAD = 0.1  # meters added around the objects of a room for its bounding box
ROOM_PREFIX, PORTAL_PREFIX = "room.", "portal."


@dataclass
class Layout:
    rooms: dict  # room name -> mesh objects
    portals: list  # (room name a, room name b, quad object)
    problems: list  # messages that block the build


def clean(name):
    """Lower-case name without Blender's .001 suffix."""
    return re.sub(r"\.\d{3}$", "", name).lower()


def is_portal(ob):
    return clean(ob.name).startswith(PORTAL_PREFIX)


def read_layout(root):
    """Collect rooms and portals under a collection and list what is wrong with the layout."""
    rooms, portals, problems = {}, [], []

    def walk(collection):
        for child in collection.children:
            key = clean(child.name)
            if key.startswith(ROOM_PREFIX):
                room = names.asset_name(key[len(ROOM_PREFIX):])
                rooms.setdefault(room, []).extend(
                    o for o in child.all_objects if o.type == "MESH" and not is_portal(o))
            else:
                walk(child)

    walk(root)
    for ob in root.all_objects:
        if not is_portal(ob):
            continue
        parts = clean(ob.name).split(".")
        if len(parts) != 3 or not parts[1] or not parts[2]:
            problems.append(rpt_("Portal '{name}' must be named portal.<room>.<room>.").format(name=ob.name))
            continue
        if ob.type != "MESH" or len(ob.data.vertices) != 4 or len(ob.data.polygons) != 1:
            problems.append(rpt_("Portal '{name}' must be a single quad (4 vertices, 1 face).").format(name=ob.name))
            continue
        portals.append((names.asset_name(parts[1]), names.asset_name(parts[2]), ob))
    if not rooms:
        problems.append(rpt_("No room.<name> sub-collections found in '{name}'.").format(name=root.name))
    owners = {}
    for room, objs in rooms.items():
        for ob in objs:
            if ob in owners and owners[ob] != room:
                problems.append(rpt_("'{name}' is in two rooms ({a}, {b}).").format(name=ob.name, a=owners[ob], b=room))
            owners[ob] = room
    for a, b, ob in portals:
        for room in (a, b):
            if room != LIMBO and room not in rooms:
                problems.append(rpt_("Portal '{name}' refers to the unknown room '{room}'.").format(
                    name=ob.name, room=room))
    if portals and not any(LIMBO in (a, b) for a, b, _ in portals):
        problems.append(rpt_("No entrance: add a portal between '{limbo}' and one of the rooms.").format(limbo=LIMBO))
    if not portals and rooms:
        problems.append(rpt_("No portals found: add portal.<room>.<room> quads."))
    if len(rooms.get(LIMBO, [])) > MAX_LIMBO_ENTITIES:
        problems.append(rpt_("The limbo room can hold {limit} objects at most.").format(limit=MAX_LIMBO_ENTITIES))
    return Layout(rooms, portals, problems)


def world_bounds(objects):
    points = [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def portal_corners(portal, from_center):
    """World-space corners of a portal quad, ordered counter-clockwise as seen from `from_center`."""
    mesh = portal.data
    polygon = mesh.polygons[0]
    # the polygon lists its vertices counter-clockwise about its normal
    corners = [portal.matrix_world @ mesh.vertices[i].co for i in polygon.vertices]
    centroid = sum(corners, Vector()) / 4
    normal = (portal.matrix_world.to_3x3() @ polygon.normal).normalized()
    if normal.dot(from_center - centroid) < 0:
        corners.reverse()
    return corners


def build(context, root, s):
    """Build the whole MLO from the layout under `root`. Returns (archetype, summary text). Raises prop.BuildError."""
    try:
        compat.require()
    except compat.SollumzMissing as e:
        raise prop.BuildError(str(e)) from e
    layout = read_layout(root)
    if layout.problems:
        raise prop.BuildError(rpt_("Fix the layout first: {list}").format(list="; ".join(layout.problems[:3])))
    meshes = [o for objs in layout.rooms.values() for o in objs if compat.kind(o) == "sollumz_none"]
    if not meshes:
        raise prop.BuildError(rpt_("The rooms contain no meshes."))
    room_of = {o: room for room, objs in layout.rooms.items() for o in objs}

    # Every mesh becomes a prop (drawable + archetype) that the MLO then references as an entity.
    inner = prop.settings_with(s, collision="NONE", separate=True, create_ytyp=True)
    drawables, _ = prop.build(context, meshes, inner)
    models = [m for d in drawables for m in compat.children_of(d, compat.MODEL)]
    mlo_name = names.asset_name(root.name)
    composite = prop.make_composite(context, models, mlo_name, s.mlo_collision, s.mlo_collision_tris)

    sc = context.scene
    ytyp = sc.ytyps[sc.ytyp_index]
    sc.create_archetype_type = compat.ARCHETYPE_MLO
    compat.select_only(context, composite)
    bpy.ops.sollumz.createarchetypefromselected()
    archetype = next((a for a in ytyp.archetypes if a.asset == composite), None)
    if archetype is None:
        raise prop.BuildError(rpt_("Sollumz did not create the MLO archetype."))

    inverse = composite.matrix_world.inverted()
    low, high = world_bounds(models)
    ids, centers = {}, {}

    limbo = archetype.new_room()
    limbo.name, limbo.timecycle = LIMBO, ""
    limbo.bb_min, limbo.bb_max = inverse @ low, inverse @ high
    ids[LIMBO] = limbo.id
    centers[LIMBO] = (low + high) / 2
    for room, objs in layout.rooms.items():
        if room == LIMBO:
            continue
        room_low, room_high = world_bounds(objs)
        pad = Vector((ROOM_PAD,) * 3)
        item = archetype.new_room()
        item.name = room
        item.bb_min, item.bb_max = inverse @ (room_low - pad), inverse @ (room_high + pad)
        ids[room] = item.id
        centers[room] = (room_low + room_high) / 2

    for a, b, ob in layout.portals:
        portal_center = ob.matrix_world @ (sum((v.co for v in ob.data.vertices), Vector()) / 4)
        from_center = centers.get(a) if a != LIMBO else 2 * portal_center - centers[b]
        corners = [inverse @ c for c in portal_corners(ob, from_center)]
        portal = archetype.new_portal()
        portal.room_from_id, portal.room_to_id = str(ids[a]), str(ids[b])
        portal.corner1, portal.corner2, portal.corner3, portal.corner4 = corners

    for ob in meshes:
        drawable = ob.parent
        entity = archetype.new_entity()
        entity.archetype_name = names.asset_name(drawable.name)
        entity.linked_object = drawable
        entity.attached_room_id = str(ids[room_of[ob]])

    compat.select_only(context, composite, *drawables)
    return archetype, rpt_("MLO '{name}': {rooms} rooms, {portals} portals, {entities} entities").format(
        name=mlo_name, rooms=len(layout.rooms) + (LIMBO not in layout.rooms), portals=len(layout.portals),
        entities=len(meshes))


def create_template(context, name):
    """A starter layout: an interior with two rooms, a portal between them and an entrance. Returns the collection."""
    root = bpy.data.collections.new(name)
    context.scene.collection.children.link(root)

    def room(label, x):
        collection = bpy.data.collections.new(f"{ROOM_PREFIX}{label}")
        root.children.link(collection)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 1.5))
        shell = context.object
        shell.scale = (4, 4, 3)
        shell.name = f"{label}_shell"
        for coll in list(shell.users_collection):
            coll.objects.unlink(shell)
        collection.objects.link(shell)
        return shell

    room("hall", 0)
    room("kitchen", 4)

    def portal(label, location, rotation):
        mesh = bpy.data.meshes.new(label)
        mesh.from_pydata([(-1, 0, -1.2), (1, 0, -1.2), (1, 0, 1.2), (-1, 0, 1.2)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new(label, mesh)
        ob.location, ob.rotation_euler = location, rotation
        root.objects.link(ob)

    portal("portal.hall.kitchen", (2, 0, 1.5), (0, 0, 1.5708))
    portal("portal.limbo.hall", (-2, 0, 1.5), (0, 0, 1.5708))
    return root
