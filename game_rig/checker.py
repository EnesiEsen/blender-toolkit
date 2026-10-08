"""Check a skeleton against the UE5 mannequin."""

from bpy.app.translations import pgettext_rpt as rpt_

from . import ue_bones

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"


def issue(severity, code, message):
    return {"severity": severity, "code": code, "message": message}


def check(armature):
    found = []
    names = {b.name for b in armature.data.bones}
    roots = [b.name for b in armature.data.bones if b.parent is None]
    if len(roots) != 1:
        found.append(
            issue(
                ERROR,
                "ROOTS",
                rpt_("The skeleton has {count} root bones ({roots}): Unreal needs exactly one.").format(
                    count=len(roots), roots=", ".join(roots[:4])
                ),
            )
        )
    missing = [b for b in ue_bones.REQUIRED if b not in names]
    if missing:
        found.append(
            issue(
                ERROR,
                "MISSING",
                rpt_("Missing mannequin bones: {names}.").format(
                    names=", ".join(missing[:8]) + ("..." if len(missing) > 8 else "")
                ),
            )
        )
    optional = [b for b in ue_bones.parents(ik=False) if b not in names and b not in ue_bones.REQUIRED]
    if optional:
        found.append(
            issue(
                WARNING,
                "OPTIONAL",
                rpt_("{count} optional bones are missing (fingers, upper spine, neck).").format(count=len(optional)),
            )
        )
    known = set(ue_bones.parents(ik=True)) | {"interaction", "center_of_mass"}
    odd = [n for n in sorted(names) if n not in known and not n.startswith("pole_")]
    if odd:
        found.append(
            issue(
                INFO,
                "EXTRA",
                rpt_("{count} bones are not mannequin bones (for example {name}): they are kept.").format(
                    count=len(odd), name=odd[0]
                ),
            )
        )
    _, rotation, scale = armature.matrix_world.decompose()
    if any(abs(c - 1.0) > 1e-4 for c in scale) or any(abs(a) > 1e-4 for a in rotation.to_euler()):
        found.append(
            issue(
                WARNING,
                "TRANSFORM",
                rpt_("'{name}' has scale or rotation on the object: apply it (Ctrl+A).").format(name=armature.name),
            )
        )
    if any(" " in n or "." in n for n in names):
        found.append(issue(WARNING, "NAMES", rpt_("Some bone names contain spaces or dots: Unreal replaces them.")))
    return found
