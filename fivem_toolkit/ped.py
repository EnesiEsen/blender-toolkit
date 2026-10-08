"""Ped tools: check and repair the rigging of a character or clothing mesh, and move its vertex weights onto the
GTA V skeleton. The bone names come from Sollumz's own registry (BoneProperties.xml), so no skeleton file is needed
to validate.

Weights are never lost: groups that do not exist on the GTA skeleton are merged into the nearest ancestor bone that
does, and a hidden backup of the mesh is kept before anything is changed.
"""

import importlib
import re
import xml.etree.ElementTree as ET

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import kdtree

from . import compat, doctor

MAX_INFLUENCES = 4  # the GTA V vertex format stores four bone weights
FINGERS = {"thumb": 0, "index": 1, "middle": 2, "ring": 3, "pinky": 4, "little": 4}
PREFIX = re.compile(r"^(mixamorig\d*[:_]?|def[-_.]|deform[-_.]|org[-_.]|bone[-_.])", re.IGNORECASE)
_REGISTRY = {}


def gta_bones():
    """{bone name: parent bone name or None} of the GTA V ped skeleton (Sollumz's registry); empty without it."""
    package = compat.package()
    if package is None:
        return {}
    if package not in _REGISTRY:
        path = importlib.import_module(f"{package}.tools.drawablehelper").BonePropertiesManager.dictionary_xml
        items = [
            (int(n.find("Index").get("value")), int(n.find("ParentIndex").get("value")), n.findtext("Name"))
            for n in ET.parse(path).getroot()
        ]
        by_index = {index: name for index, _, name in items}
        _REGISTRY[package] = {name: by_index.get(parent) for _, parent, name in items}
    return _REGISTRY[package]


def split_side(name):
    """Side letter (L, R or None) and the name without rig prefix, in lower-case letters and digits only."""
    text = PREFIX.sub("", name)
    side = None
    patterns = (
        r"^(left|right)[-_.:]?",
        r"[-_.:]?(left|right)$",
        r"[-_.:](l|r)$",
        r"^(l|r)[-_.:]",
        r"[-_.:](l|r)[-_.:]",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            side = "L" if match.group(1).lower() in ("left", "l") else "R"
            text = text[: match.start()] + "_" + text[match.end() :]
            break
    return side, re.sub(r"[^a-z0-9]", "", text.lower())


def to_gta(name):
    """Best guess of the GTA V bone that a bone of another rig (Mixamo, Rigify, generic) corresponds to, or None."""
    side, core = split_side(name)
    fixed = {
        "hips": "SKEL_Pelvis",
        "pelvis": "SKEL_Pelvis",
        "spine": "SKEL_Spine0",
        "spine1": "SKEL_Spine1",
        "spine001": "SKEL_Spine1",
        "spine2": "SKEL_Spine2",
        "spine002": "SKEL_Spine2",
        "chest": "SKEL_Spine2",
        "spine3": "SKEL_Spine3",
        "spine003": "SKEL_Spine3",
        "neck": "SKEL_Neck_1",
        "head": "SKEL_Head",
    }
    if side is None:
        return fixed.get(core)
    limbs = {
        "shoulder": "Clavicle",
        "clavicle": "Clavicle",
        "arm": "UpperArm",
        "upperarm": "UpperArm",
        "forearm": "Forearm",
        "lowerarm": "Forearm",
        "hand": "Hand",
        "upleg": "Thigh",
        "thigh": "Thigh",
        "upperleg": "Thigh",
        "leg": "Calf",
        "shin": "Calf",
        "calf": "Calf",
        "lowerleg": "Calf",
        "foot": "Foot",
        "toebase": "Toe0",
        "toe": "Toe0",
        "toes": "Toe0",
        "ball": "Toe0",
    }
    if core in limbs:
        return f"SKEL_{side}_{limbs[core]}"
    finger = re.match(r"^(?:hand|f)?(thumb|index|middle|ring|pinky|little)0?([1-3])$", core)
    if finger:
        return f"SKEL_{side}_Finger{FINGERS[finger.group(1)]}{int(finger.group(2)) - 1}"
    return None


def read_mapping(text):
    """Lines of `source bone = GTA bone` -> {lower-case source: GTA name}. Lines starting with # are comments."""
    mapping = {}
    for line in (text or "").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            source, target = (part.strip() for part in line.split("=", 1))
            if source and target:
                mapping[source.lower()] = target
    return mapping


def make_resolver(gta, mapping):
    lower = {name.lower(): name for name in gta}

    def resolve(name):
        key = name.lower()
        if key in mapping:
            return mapping[key]
        return lower.get(key) or (to_gta(name) if to_gta(name) in gta else None)

    return resolve


def vertex_weights(ob):
    """[{group index: weight}] per vertex."""
    return [{g.group: g.weight for g in v.groups} for v in ob.data.vertices]


def armature_of(ob):
    return next((m.object for m in ob.modifiers if m.type == "ARMATURE" and m.object), None)


def is_rigged_candidate(ob):
    return ob.type == "MESH" and (len(ob.vertex_groups) > 0 or armature_of(ob) is not None)


def write_weights(ob, weights):
    """Replace all vertex groups of `ob` by `weights` ([{group name: weight}] per vertex)."""
    ob.vertex_groups.clear()
    groups = {}
    for vertex, entry in enumerate(weights):
        for name, weight in entry.items():
            if name not in groups:
                groups[name] = ob.vertex_groups.new(name=name)
            groups[name].add([vertex], weight, "REPLACE")


def normalized(entry):
    total = sum(entry.values())
    return {k: v / total for k, v in entry.items()} if total > 0 else {}


# ---- checks and fixes


def scan_ped(ob):
    """Rigging problems of one mesh as issue dicts."""
    if not is_rigged_candidate(ob):
        return []
    found = []
    armature = armature_of(ob)
    gta = gta_bones()
    if armature is None:
        found.append(
            doctor.issue(
                doctor.ERROR,
                "NO_ARMATURE",
                ob,
                rpt_("'{name}' has vertex groups but no Armature modifier.").format(name=ob.name),
            )
        )
    names_by_index = {g.index: g.name for g in ob.vertex_groups}
    weights = vertex_weights(ob)
    unweighted = sum(1 for w in weights if not w)
    if unweighted:
        found.append(
            doctor.issue(
                doctor.ERROR,
                "UNWEIGHTED",
                ob,
                rpt_("'{name}': {count} vertices have no bone weight.").format(name=ob.name, count=unweighted),
            )
        )
    heavy = sum(1 for w in weights if len(w) > MAX_INFLUENCES)
    if heavy:
        found.append(
            doctor.issue(
                doctor.WARNING,
                "INFLUENCES",
                ob,
                rpt_("'{name}': {count} vertices use more than {limit} bones.").format(
                    name=ob.name, count=heavy, limit=MAX_INFLUENCES
                ),
            )
        )
    loose = sum(1 for w in weights if w and abs(sum(w.values()) - 1.0) > 0.01)
    if loose:
        found.append(
            doctor.issue(
                doctor.WARNING,
                "NOT_NORMALIZED",
                ob,
                rpt_("'{name}': the weights of {count} vertices do not add up to 1.").format(name=ob.name, count=loose),
            )
        )
    used = {g for w in weights for g in w}
    empty = [n for i, n in names_by_index.items() if i not in used]
    if empty:
        found.append(
            doctor.issue(
                doctor.INFO,
                "EMPTY_GROUPS",
                ob,
                rpt_("'{name}' has {count} empty vertex groups.").format(name=ob.name, count=len(empty)),
            )
        )
    if gta:
        unknown = [n for n in names_by_index.values() if n not in gta]
        if unknown:
            found.append(
                doctor.issue(
                    doctor.WARNING,
                    "UNKNOWN_BONE",
                    ob,
                    rpt_("'{name}': {count} vertex groups are not GTA bones (use Retarget Weights).").format(
                        name=ob.name, count=len(unknown)
                    ),
                    ", ".join(unknown[:20]),
                )
            )
    if armature is not None and all(b.bone_properties.tag == 0 for b in armature.data.bones if b.parent):
        found.append(
            doctor.issue(
                doctor.WARNING,
                "BONE_TAGS",
                armature,
                rpt_("The bones of '{name}' have no Sollumz bone tags.").format(name=armature.name),
            )
        )
    return found


def fix_unweighted(context, item):
    ob = bpy.data.objects[item["object"]]
    weights = vertex_weights(ob)
    names_by_index = {g.index: g.name for g in ob.vertex_groups}
    weighted = [i for i, w in enumerate(weights) if w]
    if not weighted:
        raise ValueError(rpt_("'{name}' has no weights at all.").format(name=ob.name))
    tree = kdtree.KDTree(len(weighted))
    for slot, i in enumerate(weighted):
        tree.insert(ob.data.vertices[i].co, slot)
    tree.balance()
    result = [{names_by_index[g]: w for g, w in entry.items()} for entry in weights]
    for i, entry in enumerate(weights):
        if not entry:
            result[i] = dict(result[weighted[tree.find(ob.data.vertices[i].co)[1]]])
    write_weights(ob, result)


def fix_influences(context, item):
    ob = bpy.data.objects[item["object"]]
    names_by_index = {g.index: g.name for g in ob.vertex_groups}
    result = []
    for entry in vertex_weights(ob):
        top = dict(sorted(entry.items(), key=lambda kv: kv[1], reverse=True)[:MAX_INFLUENCES])
        result.append(normalized({names_by_index[g]: w for g, w in top.items()}))
    write_weights(ob, result)


def fix_normalize(context, item):
    ob = bpy.data.objects[item["object"]]
    names_by_index = {g.index: g.name for g in ob.vertex_groups}
    write_weights(ob, [normalized({names_by_index[g]: w for g, w in e.items()}) for e in vertex_weights(ob)])


def fix_empty_groups(context, item):
    ob = bpy.data.objects[item["object"]]
    used = {g for w in vertex_weights(ob) for g in w}
    for group in [g for g in ob.vertex_groups if g.index not in used]:
        ob.vertex_groups.remove(group)


def fix_bone_tags(context, item):
    armature = bpy.data.objects[item["object"]]
    compat.select_only(context, armature)
    bpy.ops.sollumz.apply_bone_properties_to_armature()


FIXES = {
    "UNWEIGHTED": fix_unweighted,
    "INFLUENCES": fix_influences,
    "NOT_NORMALIZED": fix_normalize,
    "EMPTY_GROUPS": fix_empty_groups,
    "BONE_TAGS": fix_bone_tags,
}
doctor.FIXES.update(FIXES)


# ---- retargeting


def retarget(context, ob, target_armature=None, mapping_text="", keep_backup=True):
    """Rename and merge the vertex groups of `ob` onto GTA V bones. Returns a dict describing what happened."""
    gta = gta_bones()
    if not gta:
        raise ValueError(rpt_("The GTA bone list needs Sollumz."))
    resolve = make_resolver(gta, read_mapping(mapping_text))
    source = armature_of(ob)
    names_by_index = {g.index: g.name for g in ob.vertex_groups}
    target, merged, dropped = {}, {}, []
    for index, name in names_by_index.items():
        direct = resolve(name)
        if direct:
            target[index] = direct
            continue
        bone = source.data.bones.get(name) if source else None
        parent = bone.parent if bone else None
        while parent is not None and not resolve(parent.name):
            parent = parent.parent
        if parent is not None:
            target[index] = resolve(parent.name)
            merged[name] = target[index]
        else:
            dropped.append(name)
    backup = None
    if keep_backup:
        backup = ob.copy()
        backup.data = ob.data.copy()
        backup.name = f"{ob.name}_weights_backup"
        for collection in ob.users_collection:
            collection.objects.link(backup)
        backup.hide_set(True)
    result = []
    for entry in vertex_weights(ob):
        acc = {}
        for group, weight in entry.items():
            if group in target:
                acc[target[group]] = acc.get(target[group], 0.0) + weight
        result.append(normalized(acc))
    write_weights(ob, result)
    if target_armature is not None:
        for modifier in ob.modifiers:
            if modifier.type == "ARMATURE":
                modifier.object = target_armature
    missing = sorted(
        {
            n
            for n in (g.name for g in ob.vertex_groups)
            if target_armature is not None and n not in target_armature.data.bones
        }
    )
    return {
        "mapped": len(set(target.values())),
        "merged": merged,
        "dropped": dropped,
        "missing_in_armature": missing,
        "backup": backup.name if backup else "",
    }


def scan(objects):
    return [item for ob in objects for item in scan_ped(ob)]
