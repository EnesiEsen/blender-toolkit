"""Self-check for fivem_toolkit. Run it with `python tools/bdev.py check blender-toolkit/fivem_toolkit`, or by hand:
blender -b --factory-startup --python-exit-code 1 --python test_fivem_toolkit.py

Needs Sollumz (installed as the `sollumz_dev` extension here). Covers the Doctor on deliberately broken meshes, the
prop pipeline (drawables, converted materials, LODs, collision placement, YTYP, texture dictionaries) and a real export
of the resource folder in both binary and CodeWalker XML form.
"""

import importlib.util
import os
import sys
import tempfile

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "fivem_toolkit")
spec = importlib.util.spec_from_file_location(
    "fivem_toolkit", os.path.join(PKG, "__init__.py"), submodule_search_locations=[PKG]
)
fk = importlib.util.module_from_spec(spec)
sys.modules["fivem_toolkit"] = fk
spec.loader.exec_module(fk)
from fivem_toolkit import compat, doctor, mlo, names, ped, prop, resource  # noqa: E402  (needs the module registered above)

fk.register()
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def reset(sollumz=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if sollumz:
        bpy.ops.preferences.addon_enable(module="bl_ext.user_default.sollumz_dev")


def save_image(name, width, height, folder):
    img = bpy.data.images.new(name, width, height)
    img.filepath_raw = os.path.join(folder, name + ".png")
    img.file_format = "PNG"
    img.save()
    return img


def textured_material(name, image):
    mat = bpy.data.materials.new(name)
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    mat.node_tree.links.new(node.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    return mat


def codes(found):
    return sorted(p["code"] for p in found)


# ---- names
check(names.asset_name("My Crate.001") == "my_crate", "asset_name strips the suffix and spaces")
check(names.asset_name("Tür Kapı!") == "t_r_kap", f"asset_name keeps only ascii ({names.asset_name('Tür Kapı!')})")
check(names.is_valid("crate_2") and not names.is_valid("Crate") and not names.is_valid("a.001"), "is_valid")
check(names.unique("crate", {"crate", "crate_2"}) == "crate_3", "unique")

tmp = tempfile.mkdtemp(prefix="fk_")
reset()
sc = bpy.context.scene
s = sc.fk_settings
s.tri_limit = 100
s.max_texture = "2048"

# ---- Doctor on a deliberately broken mesh: odd name, scaled, no UV or material, odd texture, a modifier, many tris
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.0)
broken = bpy.context.object
broken.name = "My Crate"
broken.scale = (2.0, 1.0, 0.5)
mesh = broken.data
while mesh.uv_layers:
    mesh.uv_layers.remove(mesh.uv_layers[0])
broken.modifiers.new("b", "BEVEL")
odd = textured_material("odd", save_image("odd_d", 300, 200, tmp))
bpy.context.view_layer.update()
before = tuple(broken.dimensions)
found = doctor.scan([broken], s)
check(
    {"NAME", "TRANSFORM", "MODIFIERS", "NO_UV", "NO_MATERIAL", "TRI_COUNT"} <= set(codes(found)),
    f"doctor finds the problems of a broken mesh: {codes(found)}",
)
mesh.materials.append(odd)
check("TEXTURE_SIZE" in codes(doctor.scan([broken], s)), "doctor flags a 300x200 texture")
fixed, failed = doctor.fix_all(bpy.context, doctor.scan([broken], s))
left = codes(doctor.scan([broken], s))
check(left == ["TRI_COUNT"], f"after fix_all only the unfixable problem is left: {left} ({failed})")
bpy.context.view_layer.update()
check(broken.name == "my_crate" and tuple(broken.scale) == (1.0, 1.0, 1.0), "name and scale fixed")
check(
    all(abs(a - b) < 1e-3 for a, b in zip(broken.dimensions, before, strict=True)),
    f"applying the scale keeps the size: {tuple(broken.dimensions)} vs {before}",
)
uv = broken.data.uv_layers[0].data
check(len({round(v.uv[0], 3) for v in uv}) > 2, "box projection gives varied UVs")
check(tuple(bpy.data.images["odd_d"].size) == (256, 256), f"texture snapped to {tuple(bpy.data.images['odd_d'].size)}")
check(not broken.modifiers, "modifiers applied")
check(
    codes(doctor.scan([bpy.data.objects.new("empty_obj", bpy.data.meshes.new("e"))], s)).count("EMPTY_MESH") == 1,
    "doctor flags a mesh without faces",
)

# ---- the prop pipeline needs Sollumz
if not compat.ready():
    print("NOTE: Sollumz is not available, skipping the prop pipeline tests")
else:
    reset()
    sc = bpy.context.scene
    s = sc.fk_settings
    s.resource_name, s.output_dir = "test_props", tmp
    barrel_tex = textured_material("barrel_mat", save_image("barrel_d", 256, 256, tmp))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0, location=(5.0, 3.0, 1.0))
    barrel = bpy.context.object
    barrel.name = "Barrel A"
    barrel.data.materials.append(barrel_tex)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(-4.0, 0.0, 0.0))
    box = bpy.context.object
    box.name = "box b"
    plain = bpy.data.materials.new("plain")
    box.data.materials.append(plain)
    s.collision, s.collision_tris, s.make_lods, s.separate = "PROXY", 100, True, True
    s.create_ytd = compat.has_ytd()

    try:
        prop.build(bpy.context, [], s)
        check(False, "building from an empty selection must raise")
    except prop.BuildError as e:
        check("mesh" in str(e).lower(), f"empty selection message: {e}")

    drawables, summary = prop.build(bpy.context, [barrel, box], s)
    by_name = {d.name: d for d in drawables}
    check(sorted(by_name) == ["barrel_a", "box_b"], f"drawables named after sanitized objects: {sorted(by_name)}")
    for d in drawables:
        for model in compat.children_of(d, compat.MODEL):
            check(
                all(m.sollum_type == compat.SHADER_MATERIAL for m in model.data.materials if m is not None),
                f"{d.name}: materials converted to Sollumz shaders",
            )
    barrel_d, box_d = by_name["barrel_a"], by_name["box_b"]
    barrel_model = compat.children_of(barrel_d, compat.MODEL)[0]
    base_tris = doctor.triangles(barrel_model.data)
    lods = barrel_model.sz_lods
    check(all(getattr(lods, k).has_mesh for k in ("high", "medium", "low", "very_low")), "barrel has four LOD meshes")
    tri_by_level = [doctor.triangles(lods.get_lod(compat.LOD_LEVELS[k]).mesh) for k in ("med", "low", "vlow")]
    check(
        tri_by_level == sorted(tri_by_level, reverse=True) and tri_by_level[0] < base_tris,
        f"LOD triangle counts shrink: {base_tris} -> {tri_by_level}",
    )
    check(not compat.children_of(box_d, compat.MODEL)[0].sz_lods.medium.has_mesh, "a 12-triangle box gets no LODs")
    p = barrel_d.drawable_properties
    check(0 < p.lod_dist_high < p.lod_dist_med < p.lod_dist_low < p.lod_dist_vlow <= 9998, "LOD distances grow")
    composite = next((c for c in barrel_d.children if compat.kind(c) == compat.COMPOSITE), None)
    check(composite is not None, "barrel has a collision composite")
    check(
        composite is None or not [i for i in doctor.scan([barrel_d, composite], s) if i["code"] == "NAME"],
        "the embedded collision is not flagged as a badly named asset",
    )
    uv_names = [u.name for u in barrel_model.data.uv_layers]
    check(
        "UVMap 0" in uv_names and "Color 1" in [a.name for a in barrel_model.data.color_attributes],
        f"meshes carry the names the Sollumz shaders expect: {uv_names}",
    )
    check(
        all(
            "UVMap 0" in [u.name for u in lods.get_lod(compat.LOD_LEVELS[k]).mesh.uv_layers]
            for k in ("med", "low", "vlow")
        ),
        "LOD meshes carry them too",
    )
    texture = bpy.data.images["barrel_d"]
    check(
        texture.filepath.endswith(".dds") and os.path.exists(bpy.path.abspath(texture.filepath)),
        f"the texture was converted to a DDS file: {texture.filepath}",
    )
    check("fk_source" in texture, "the original path is remembered")
    if composite is not None:
        shapes = [c for c in composite.children_recursive if c.type == "MESH"]
        tris = sum(doctor.triangles(c.data) for c in shapes)
        check(0 < tris <= 140, f"collision is simplified: {tris} triangles")
        check(
            all(m.sollum_type == compat.COLLISION_MATERIAL for c in shapes for m in c.data.materials)
            and all(len(c.data.materials) for c in shapes),
            "collision meshes carry a collision material",
        )
        corners = [c.matrix_world @ Vector(v) for c in shapes for v in c.bound_box]
        centre = sum(corners, Vector()) / len(corners)
        check(
            (centre - barrel_model.matrix_world.translation).length < 0.3,
            f"collision sits on the model: {tuple(round(x, 2) for x in centre)} vs "
            f"{tuple(round(x, 2) for x in barrel_model.matrix_world.translation)}",
        )
    archetypes = [a for y in sc.ytyps for a in y.archetypes]
    check(sorted(a.name for a in archetypes) == ["barrel_a", "box_b"], "one archetype per prop")
    check(
        all(abs(a.lod_dist - prop.archetype_lod_dist(prop.world_radius(a.asset))) < 0.01 for a in archetypes),
        "archetype distances",
    )
    check(sc.ytyps[0].name == "test_props", "the YTYP is named like the resource")
    if compat.has_ytd():
        txds = sc.sz_txds.texture_dictionaries
        check([t.name for t in txds] == ["barrel_a"], "a texture dictionary for the textured prop")
        check([t.name for t in txds[0].textures] == ["barrel_d"], "it holds the barrel texture")
    try:
        prop.build(bpy.context, [barrel_model], s)
        check(False, "building from Sollumz objects must raise")
    except prop.BuildError:
        pass

    # ---- export: binary and XML
    for fmt, suffix in (("NATIVE", ""), ("CWXML", ".xml")):
        s.export_format = fmt
        s.resource_name = "res_" + fmt.lower()
        path, files = resource.export(bpy.context, s)
        check({"barrel_a.ydr" + suffix, "box_b.ydr" + suffix} <= set(files), f"{fmt}: drawables exported: {files}")
        if fmt == "NATIVE":  # the 256x256 DXT1 texture with mipmaps (43 KB) is embedded in the drawable
            size = (path / "stream" / "barrel_a.ydr").stat().st_size
            check(size > 30000, f"the binary drawable holds its texture: {size} bytes")
        elif compat.has_ytd():  # older Sollumz builds do not write the DDS next to the XML
            dds_files = list((path / "stream").rglob("barrel_d.dds"))
            check(dds_files and dds_files[0].stat().st_size == 43832, f"the XML export carries the DDS: {dds_files}")
        ytyp_files = [f for f in files if f.endswith(".ytyp" + suffix)]
        check(len(ytyp_files) == 1, f"{fmt}: one YTYP exported: {files}")
        if compat.has_ytd():
            check("barrel_a.ytd" + suffix in files, f"{fmt}: texture dictionary exported: {files}")
        manifest = (path / "fxmanifest.lua").read_text(encoding="utf-8")
        binary_name = ytyp_files[0].removesuffix(".xml")  # the XML is converted to binary with CodeWalker
        check(
            f"data_file 'DLC_ITYP_REQUEST' 'stream/{binary_name}'" in manifest and "fx_version" in manifest,
            f"{fmt}: fxmanifest loads the YTYP",
        )
        if fmt == "CWXML":
            text = (path / "stream" / "barrel_a.ydr.xml").read_text(encoding="utf-8")
            check(
                'Bounds type="Composite"' in text and "LodDistHigh" in text and "DrawableModelsMedium" in text,
                "XML drawable has collision and LOD data",
            )
    s.output_dir = ""
    try:
        resource.export(bpy.context, s)
        check(False, "export without a folder must raise")
    except resource.ExportError:
        pass


# ---- the interior (MLO) builder
if compat.ready():
    reset()
    sc = bpy.context.scene
    s = sc.fk_settings
    s.resource_name, s.output_dir, s.mlo_collision_tris = "test_mlo", tmp, 200
    empty = bpy.data.collections.new("empty_interior")
    sc.collection.children.link(empty)
    check(any("No room" in p for p in mlo.read_layout(empty).problems), "an interior without rooms is reported")
    root = mlo.create_template(bpy.context, "My Interior")
    layout = mlo.read_layout(root)
    check(not layout.problems, f"the template is a valid layout: {layout.problems}")
    check(sorted(layout.rooms) == ["hall", "kitchen"] and len(layout.portals) == 2, "rooms and portals are read")
    bad = bpy.data.objects.new("portal.hall.attic", bpy.data.meshes.new("tri"))
    bad.data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    root.objects.link(bad)
    problems = " | ".join(mlo.read_layout(root).problems)
    check("single quad" in problems, f"a triangle portal is rejected: {problems}")
    bpy.data.objects.remove(bad)
    wrong = bpy.data.objects.new("portal.hall.pantry", bpy.data.meshes.new("quad"))
    wrong.data.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
    root.objects.link(wrong)
    check(
        "unknown room 'pantry'" in " | ".join(mlo.read_layout(root).problems), "a portal to a missing room is reported"
    )
    bpy.data.objects.remove(wrong)

    archetype, summary = mlo.build(bpy.context, root, s)
    check(archetype.type == compat.ARCHETYPE_MLO, f"an MLO archetype was created ({archetype.type})")
    room_name = {r.id: r.name for r in archetype.rooms}
    check([r.name for r in archetype.rooms] == ["limbo", "hall", "kitchen"], f"rooms: {list(room_name.values())}")
    composite = archetype.asset
    check(
        compat.kind(composite) == compat.COMPOSITE and composite.name == "my_interior",
        "the asset is the collision composite",
    )
    inverse = composite.matrix_world.inverted()
    by_pair = {(room_name[int(p.room_from_id)], room_name[int(p.room_to_id)]): p for p in archetype.portals}
    check(set(by_pair) == {("hall", "kitchen"), ("limbo", "hall")}, f"portal connections: {sorted(by_pair)}")
    for (a, b), portal in by_pair.items():
        corners = [Vector(c) for c in (portal.corner1, portal.corner2, portal.corner3, portal.corner4)]
        centre = sum(corners, Vector()) / 4
        normal = (corners[1] - corners[0]).cross(corners[2] - corners[0])
        # counter-clockwise seen from room a: its normal points at a. The hall (x = 0) lies at -x of both portals.
        check(normal.x < 0, f"portal {a}->{b} winds counter-clockwise as seen from {a}: normal {tuple(normal)}")
        check(abs(centre.z - 1.5) < 1e-3, f"portal {a}->{b} corners are in asset space: {tuple(centre)}")
    hall_shell = bpy.data.objects["hall_shell.model"]
    low, high = (inverse @ Vector(c) for c in ((-2, -2, 0), (2, 2, 3)))
    hall = next(r for r in archetype.rooms if r.name == "hall")
    inside = all(a <= b + 1e-3 for a, b in zip(hall.bb_min, low, strict=True)) and all(
        a >= b - 1e-3 for a, b in zip(hall.bb_max, high, strict=True)
    )
    check(inside, f"room bounds hold the shell: {tuple(hall.bb_min)}")
    entity_rooms = {e.archetype_name: room_name[int(e.attached_room_id)] for e in archetype.entities}
    check(entity_rooms == {"hall_shell": "hall", "kitchen_shell": "kitchen"}, f"entities by room: {entity_rooms}")
    check(
        all(
            e.linked_object is not None and compat.kind(e.linked_object) == compat.DRAWABLE for e in archetype.entities
        ),
        "entities link their drawables",
    )
    check(
        {a.name for y in sc.ytyps for a in y.archetypes} >= {"hall_shell", "kitchen_shell", "my_interior"},
        "every entity has its own archetype",
    )
    check(hall_shell.parent is not None, "the room meshes were converted")
    for fmt, suffix in (("NATIVE", ""), ("CWXML", ".xml")):
        s.export_format, s.resource_name = fmt, "mlo_" + fmt.lower()
        path, files = resource.export(bpy.context, s)
        check(
            {"hall_shell.ydr" + suffix, "my_interior.ybn" + suffix} <= set(files),
            f"{fmt}: MLO assets exported: {files}",
        )
        if fmt == "CWXML":
            ytyp_file = next(path / "stream" / f for f in files if f.endswith(".ytyp.xml"))
            ytyp_text = ytyp_file.read_text(encoding="utf-8")
            check(
                "CMloArchetypeDef" in ytyp_text and "<name>kitchen</name>" in ytyp_text and "limbo" in ytyp_text,
                "the YTYP XML holds the MLO with its rooms",
            )


# ---- ped tools: bone names, weight problems, retargeting onto the GTA skeleton
check(
    ped.to_gta("mixamorig:Hips") == "SKEL_Pelvis" and ped.to_gta("mixamorig:LeftHandIndex2") == "SKEL_L_Finger11",
    "Mixamo bone names are recognised",
)
check(
    ped.to_gta("mixamorig:RightUpLeg") == "SKEL_R_Thigh" and ped.to_gta("mixamorig:LeftLeg") == "SKEL_L_Calf",
    "Mixamo legs: UpLeg is the thigh, Leg is the calf",
)
check(
    ped.to_gta("DEF-thigh.L") == "SKEL_L_Thigh" and ped.to_gta("DEF-f_index.01.R") == "SKEL_R_Finger10",
    "Rigify bone names are recognised",
)
check(ped.to_gta("mixamorig:LeftArmRoll") is None and ped.to_gta("Cape") is None, "unknown bones stay unknown")
check(ped.read_mapping("# c\nCape = SKEL_Spine3\nbad line\n") == {"cape": "SKEL_Spine3"}, "mapping sheet parser")

if compat.ready():
    reset()
    sc = bpy.context.scene
    s = sc.fk_settings
    gta = ped.gta_bones()
    check(
        len(gta) > 800 and gta["SKEL_ROOT"] is None and gta["SKEL_L_UpperArm"] == "SKEL_L_Clavicle",
        "the GTA bone registry is read from Sollumz",
    )

    def make_rig(name, bones, prefix=""):
        data = bpy.data.armatures.new(name)
        rig = bpy.data.objects.new(name, data)
        sc.collection.objects.link(rig)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        for bone, parent, head, tail in bones:
            edit = data.edit_bones.new(prefix + bone)
            edit.head, edit.tail = head, tail
            if parent:
                edit.parent = data.edit_bones[prefix + parent]
        bpy.ops.object.mode_set(mode="OBJECT")
        return rig

    mixamo = make_rig(
        "mixamo",
        [
            ("Hips", None, (0, 0, 1.0), (0, 0, 1.1)),
            ("Spine", "Hips", (0, 0, 1.1), (0, 0, 1.2)),
            ("Spine1", "Spine", (0, 0, 1.2), (0, 0, 1.3)),
            ("Spine2", "Spine1", (0, 0, 1.3), (0, 0, 1.4)),
            ("Neck", "Spine2", (0, 0, 1.4), (0, 0, 1.5)),
            ("Head", "Neck", (0, 0, 1.5), (0, 0, 1.7)),
            ("LeftShoulder", "Spine2", (0, 0, 1.4), (0.15, 0, 1.4)),
            ("LeftArm", "LeftShoulder", (0.15, 0, 1.4), (0.45, 0, 1.4)),
            ("LeftArmRoll", "LeftArm", (0.3, 0, 1.4), (0.45, 0, 1.4)),
            ("LeftForeArm", "LeftArm", (0.45, 0, 1.4), (0.7, 0, 1.4)),
            ("LeftHand", "LeftForeArm", (0.7, 0, 1.4), (0.8, 0, 1.4)),
            ("LeftHandIndex1", "LeftHand", (0.8, 0, 1.4), (0.85, 0, 1.4)),
            ("LeftHandIndex2", "LeftHandIndex1", (0.85, 0, 1.4), (0.9, 0, 1.4)),
            ("LeftUpLeg", "Hips", (0.1, 0, 1.0), (0.1, 0, 0.55)),
            ("LeftLeg", "LeftUpLeg", (0.1, 0, 0.55), (0.1, 0, 0.1)),
            ("LeftFoot", "LeftLeg", (0.1, 0, 0.1), (0.1, 0.1, 0.05)),
        ],
        prefix="mixamorig:",
    )
    wanted = [
        "SKEL_ROOT",
        "SKEL_Pelvis",
        "SKEL_Spine0",
        "SKEL_Spine1",
        "SKEL_Spine2",
        "SKEL_Neck_1",
        "SKEL_Head",
        "SKEL_L_Clavicle",
        "SKEL_L_UpperArm",
        "SKEL_L_Forearm",
        "SKEL_L_Hand",
        "SKEL_L_Finger10",
        "SKEL_L_Finger11",
        "SKEL_L_Thigh",
        "SKEL_L_Calf",
        "SKEL_L_Foot",
    ]
    gta_rig = make_rig(
        "gta",
        [(n, None if i == 0 else "SKEL_ROOT", (0, 0, 0.1 * i), (0, 0, 0.1 * i + 0.05)) for i, n in enumerate(wanted)],
    )

    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.45, location=(0.4, 0, 1.4))
    skin = bpy.context.object
    skin.name = "jacket"
    modifier = skin.modifiers.new("Armature", "ARMATURE")
    modifier.object = mixamo
    heads = {b.name: b.head_local for b in mixamo.data.bones}
    for name in heads:
        skin.vertex_groups.new(name=name)
    plain = []
    for v in skin.data.vertices:
        world = skin.matrix_world @ v.co
        order = sorted(heads, key=lambda n: (heads[n] - world).length)
        if v.index % 25 == 0:
            continue  # left without any weight on purpose
        count = 6 if v.index % 10 == 1 else 2
        scale = 0.8 if v.index % 10 == 2 else 1.0  # a few vertices do not add up to 1
        raw = [1.0 / (k + 1) for k in range(count)]
        for k, bone in enumerate(order[:count]):
            skin.vertex_groups[bone].add([v.index], scale * raw[k] / sum(raw), "REPLACE")
        if v.index % 10 not in (1, 2):
            plain.append(v.index)
    unused = skin.vertex_groups.new(name="mixamorig:Unused")

    codes_before = codes(ped.scan_ped(skin))
    check(
        {"UNWEIGHTED", "INFLUENCES", "NOT_NORMALIZED", "UNKNOWN_BONE", "EMPTY_GROUPS"} <= set(codes_before),
        f"ped doctor finds the weight problems: {codes_before}",
    )
    roll_before = {
        i: sum(
            g.weight
            for g in skin.data.vertices[i].groups
            if skin.vertex_groups[g.group].name in ("mixamorig:LeftArm", "mixamorig:LeftArmRoll")
        )
        for i in plain
    }
    group_names = [g.name for g in skin.vertex_groups]
    s.ped_armature = gta_rig
    compat.select_only(bpy.context, skin)
    check(bpy.ops.fivem_toolkit.ped_retarget() == {"FINISHED"}, "retarget operator")
    names_after = {g.name for g in skin.vertex_groups}
    check(names_after <= set(gta), f"every vertex group is a GTA bone now: {sorted(names_after - set(gta))}")
    check("SKEL_L_UpperArm" in names_after and "SKEL_Pelvis" in names_after, "groups were renamed")
    arm = skin.vertex_groups.get("SKEL_L_UpperArm")
    check(arm is not None, f"the upper arm group exists: {sorted(names_after)}")
    if arm is not None:
        for i in plain[:40]:
            after = sum(g.weight for g in skin.data.vertices[i].groups if g.group == arm.index)
            check(
                abs(after - roll_before[i]) < 1e-3,
                f"vertex {i}: the twist bone weight went into the upper arm ({roll_before[i]:.3f} -> {after:.3f})",
            )
            break
    check(
        all(m.object == gta_rig for m in skin.modifiers if m.type == "ARMATURE"), "the modifier uses the GTA skeleton"
    )
    backup = bpy.data.objects.get("jacket_weights_backup")
    check(
        backup is not None and backup.hide_get() and [g.name for g in backup.vertex_groups] == group_names,
        "a hidden backup keeps the original groups",
    )
    codes_mid = codes(ped.scan_ped(skin))
    check("UNKNOWN_BONE" not in codes_mid and "UNWEIGHTED" in codes_mid, f"after retargeting: {codes_mid}")
    fixed, failed = doctor.fix_all(bpy.context, ped.scan_ped(skin))
    codes_after = codes(ped.scan_ped(skin))
    check(not failed and codes_after == [], f"ped fixes clear the rest: {codes_after} {failed}")
    weights_now = ped.vertex_weights(skin)
    check(
        all(w and len(w) <= 4 and abs(sum(w.values()) - 1.0) < 0.01 for w in weights_now),
        "every vertex has 1-4 bones that add up to 1",
    )
    pelvis = gta_rig.data.bones["SKEL_Pelvis"]
    check(pelvis.bone_properties.tag != 0, f"Sollumz bone tags were applied: {pelvis.bone_properties.tag}")
    sheet_op = bpy.ops.fivem_toolkit.ped_mapping_sheet()
    check(sheet_op == {"FINISHED"} and "fk_bone_map" in bpy.data.texts, "mapping sheet created")

# ---- translation
prefs = bpy.context.preferences.view
prefs.language, prefs.use_translate_interface = "tr_TR", True
translated = bpy.app.translations.pgettext_iface("Build Props")
prefs.language = "en_US"
check(translated == "Prop Oluştur", f"Turkish translation active ({translated!r})")

fk.unregister()
if failures:
    print("FAIL\n" + "\n".join(failures))
    sys.exit(1)
print("OK: fivem_toolkit doctor, prop pipeline, export")
