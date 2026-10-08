"""Where every bone goes, computed from the landmark points."""

from mathutils import Vector

from . import ue_bones

UP = Vector((0.0, 0.0, 1.0))
FRONT = Vector((0.0, -1.0, 0.0))


def finger_points(wrist, tip):
    """{bone: (head, tail)} of the five fingers of a hand, for the hand on the given side."""
    reach = tip - wrist
    length = reach.length
    along = reach.normalized()
    side = (FRONT - along * FRONT.dot(along)).normalized()  # toward the index finger
    out = {}
    for finger, spread, scale in (
        ("index", 0.09, 0.95),
        ("middle", 0.03, 1.0),
        ("ring", -0.03, 0.95),
        ("pinky", -0.09, 0.78),
    ):
        base = wrist + along * (0.30 * length) + side * (spread * length)
        total = 0.70 * length * scale
        points = [base, base + along * total * 0.45, base + along * total * 0.75, base + along * total]
        for n in range(3):
            out[f"{finger}_{n + 1:02d}"] = (points[n], points[n + 1])
    base = wrist + along * (0.12 * length) + side * (0.11 * length)
    direction = (along * 0.6 + side * 0.7 - UP * 0.15).normalized()
    total = 0.45 * length
    points = [base + direction * total * f for f in (0.0, 0.4, 0.7, 1.0)]
    for n in range(3):
        out[f"thumb_{n + 1:02d}"] = (points[n], points[n + 1])
    return out


def positions(p, ik=True, fingers=True):
    """{bone: (head, tail)} in world space. `p` maps landmark names (Pelvis, Shoulder_L, ...) to points."""
    pelvis, neck, top = p["Pelvis"], p["Neck"], p["HeadTop"]
    ground = min(p["ToeTip_L"].z, p["ToeTip_R"].z)
    height = top.z - ground
    root_head = Vector((pelvis.x, pelvis.y, ground))
    out = {"root": (root_head, root_head + UP * 0.08 * height), "pelvis": (pelvis, pelvis + UP * 0.04 * height)}
    spine = [pelvis.lerp(neck, i / 5) for i in range(6)]
    for i, name in enumerate(ue_bones.SPINE):
        out[name] = (spine[i], spine[i + 1])
    lift = top - neck
    out["neck_01"] = (neck, neck + lift * 0.18)
    out["neck_02"] = (neck + lift * 0.18, neck + lift * 0.36)
    out["head"] = (neck + lift * 0.36, top)
    for s, key in (("l", "L"), ("r", "R")):
        sign = 1.0 if s == "l" else -1.0
        shoulder, elbow, wrist, tip = p[f"Shoulder_{key}"], p[f"Elbow_{key}"], p[f"Wrist_{key}"], p[f"FingerTip_{key}"]
        out[f"clavicle_{s}"] = (Vector((neck.x + sign * 0.02 * height, neck.y, neck.z)), shoulder)
        out[f"upperarm_{s}"] = (shoulder, elbow)
        out[f"lowerarm_{s}"] = (elbow, wrist)
        out[f"hand_{s}"] = (wrist, wrist.lerp(tip, 0.30))
        if fingers:
            for name, (head, tail) in finger_points(wrist, tip).items():
                finger, number = name.rsplit("_", 1)
                out[f"{finger}_{number}_{s}"] = (head, tail)
        out[f"thigh_{s}"] = (p[f"Hip_{key}"], p[f"Knee_{key}"])
        out[f"calf_{s}"] = (p[f"Knee_{key}"], p[f"Ankle_{key}"])
        out[f"foot_{s}"] = (p[f"Ankle_{key}"], p[f"ToeBase_{key}"])
        out[f"ball_{s}"] = (p[f"ToeBase_{key}"], p[f"ToeTip_{key}"])
    if ik:
        out["ik_foot_root"] = (root_head, root_head + UP * 0.05 * height)
        out["ik_hand_root"] = (root_head, root_head + UP * 0.05 * height)
        out["ik_hand_gun"] = out["hand_r"]
        for s in ue_bones.SIDES:
            out[f"ik_foot_{s}"] = out[f"foot_{s}"]
            out[f"ik_hand_{s}"] = out[f"hand_{s}"]
    return out
