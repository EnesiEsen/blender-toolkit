"""Rename the bones of a Mixamo, Rigify or generic rig to the UE5 mannequin names."""

import re

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

PREFIX = re.compile(r"^(mixamorig\d*[:_]?|def[-_.]|deform[-_.]|org[-_.]|bip\d*[_ ]?|bone[-_.])", re.IGNORECASE)
SIDE = (
    re.compile(r"^(left|right)[-_.: ]?", re.IGNORECASE),
    re.compile(r"[-_.: ]?(left|right)$", re.IGNORECASE),
    re.compile(r"[-_.: ](l|r)$", re.IGNORECASE),
    re.compile(r"^(l|r)[-_.: ]", re.IGNORECASE),
    re.compile(r"[-_.: ](l|r)[-_.: ]", re.IGNORECASE),
)
FINGER = re.compile(r"^(?:hand)?f?(thumb|index|middle|ring|pinky|little)0*(\d)$")
BASES = {
    "hips": "pelvis", "pelvis": "pelvis", "hip": "pelvis", "root": "root",
    "spine": "spine_01", "spine1": "spine_02", "spine2": "spine_03", "spine3": "spine_04", "spine4": "spine_05",
    "spine01": "spine_01", "spine02": "spine_02", "spine03": "spine_03", "spine04": "spine_04", "spine05": "spine_05",
    "chest": "spine_03", "upperchest": "spine_04",
    "neck": "neck_01", "neck1": "neck_01", "neck2": "neck_02", "neck01": "neck_01", "neck02": "neck_02", "head": "head",
    "shoulder": "clavicle", "clavicle": "clavicle", "collar": "clavicle",
    "arm": "upperarm", "upperarm": "upperarm", "uparm": "upperarm",
    "forearm": "lowerarm", "lowerarm": "lowerarm", "loarm": "lowerarm",
    "hand": "hand",
    "upleg": "thigh", "upperleg": "thigh", "thigh": "thigh",
    "leg": "calf", "lowerleg": "calf", "calf": "calf", "shin": "calf",
    "foot": "foot", "toebase": "ball", "toe": "ball", "ball": "ball",
}  # fmt: skip
RIGIFY = {"spine": "pelvis", "spine001": "spine_01", "spine002": "spine_02", "spine003": "spine_03",
          "spine004": "neck_01", "spine005": "neck_02", "spine006": "head"}  # fmt: skip
CENTER = ("pelvis", "root", "head")


def split_side(text):
    """(side letter 'l'/'r' or None, the name without the side marker)."""
    for pattern in SIDE:
        match = pattern.search(text)
        if match:
            letter = match.group(1).lower()
            return ("l" if letter in ("left", "l") else "r"), text[: match.start()] + "_" + text[match.end() :]
    return None, text


def ue_name(name):
    """The UE5 mannequin name of a bone of another rig, or None when it cannot be guessed."""
    rigify = name.lower().startswith("def")
    text = PREFIX.sub("", name)
    side, text = split_side(text)
    core = re.sub(r"[^a-z0-9]", "", text.lower())
    finger = FINGER.match(core)
    if finger:
        number = int(finger.group(2))
        if not 1 <= number <= 3 or side is None:
            return None
        return f"{'pinky' if finger.group(1) == 'little' else finger.group(1)}_{number:02d}_{side}"
    base = (RIGIFY.get(core) if rigify else None) or BASES.get(core)
    if base is None:
        return None
    if base.startswith(("spine_", "neck_")) or base in CENTER:
        return base
    return f"{base}_{side}" if side else None


def read_sheet(text_block):
    """{source name: ue name} from a text block with 'source = ue' lines."""
    mapping = {}
    if text_block is None:
        return mapping
    for line in text_block.as_string().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            source, target = (part.strip() for part in line.split("=", 1))
            if source and target:
                mapping[source] = target
    return mapping


def plan(armature, sheet=None):
    """([(old, new)], [unmatched names]) without changing anything. The sheet beats the guesses."""
    sheet = sheet or {}
    taken, renames, unmatched = set(), [], []
    for bone in armature.data.bones:
        new = sheet.get(bone.name) or ue_name(bone.name)
        if new is None or new in taken:
            unmatched.append(bone.name)
            continue
        taken.add(new)
        if new != bone.name:
            renames.append((bone.name, new))
    return renames, unmatched


def apply(armature, renames):
    """Rename in two steps so that swaps and chains cannot collide. Vertex groups of bound meshes follow the bones."""
    bones = armature.data.bones
    for index, (old, _) in enumerate(renames):
        bones[old].name = f"__gr_tmp_{index}"
    for index, (_, new) in enumerate(renames):
        bones[f"__gr_tmp_{index}"].name = new
    return len(renames)


def rename_rig(armature, sheet_text=None):
    renames, unmatched = plan(armature, read_sheet(sheet_text))
    if not renames and unmatched and len(unmatched) == len(armature.data.bones):
        raise ValueError(rpt_("No bone name could be matched: fill the mapping sheet."))
    apply(armature, renames)
    return renames, unmatched


def mapping_sheet(armature, name):
    """A text block that lists the bones that were not matched, to be filled in by hand."""
    _, unmatched = plan(armature)
    text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    text.clear()
    text.write("# source bone = UE5 bone (one per line)\n" + "".join(f"{bone} = \n" for bone in unmatched))
    return text, len(unmatched)
