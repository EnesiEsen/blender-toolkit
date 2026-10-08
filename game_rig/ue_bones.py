"""The UE5 mannequin skeleton: bone names, hierarchy and the landmarks that place it."""

FINGERS = ("thumb", "index", "middle", "ring", "pinky")
SIDES = ("l", "r")
SPINE = tuple(f"spine_{i:02d}" for i in range(1, 6))

# Landmarks as fractions of the character height (T-pose, the character faces -Y, left side is +X).
LANDMARKS = {
    "Pelvis": (0.0, 0.0, 0.53),
    "Neck": (0.0, 0.0, 0.82),
    "HeadTop": (0.0, 0.0, 1.0),
    "Shoulder": (0.10, 0.0, 0.80),
    "Elbow": (0.27, 0.006, 0.80),
    "Wrist": (0.42, 0.0, 0.80),
    "FingerTip": (0.52, 0.0, 0.80),
    "Hip": (0.055, 0.0, 0.51),
    "Knee": (0.055, -0.012, 0.28),
    "Ankle": (0.055, 0.0, 0.04),
    "ToeBase": (0.055, -0.07, 0.02),
    "ToeTip": (0.055, -0.12, 0.01),
}
CENTER = ("Pelvis", "Neck", "HeadTop")


def parents(ik=True, fingers=True):
    """{bone: parent or None} in an order where every parent comes before its children."""
    tree = {"root": None, "pelvis": "root"}
    previous = "pelvis"
    for name in SPINE:
        tree[name] = previous
        previous = name
    tree["neck_01"], tree["neck_02"], tree["head"] = "spine_05", "neck_01", "neck_02"
    for s in SIDES:
        tree[f"clavicle_{s}"] = "spine_05"
        tree[f"upperarm_{s}"] = f"clavicle_{s}"
        tree[f"lowerarm_{s}"] = f"upperarm_{s}"
        tree[f"hand_{s}"] = f"lowerarm_{s}"
        if fingers:
            for finger in FINGERS:
                parent = f"hand_{s}"
                for n in (1, 2, 3):
                    tree[f"{finger}_{n:02d}_{s}"] = parent
                    parent = f"{finger}_{n:02d}_{s}"
        tree[f"thigh_{s}"] = "pelvis"
        tree[f"calf_{s}"] = f"thigh_{s}"
        tree[f"foot_{s}"] = f"calf_{s}"
        tree[f"ball_{s}"] = f"foot_{s}"
    if ik:
        tree["ik_foot_root"], tree["ik_hand_root"] = "root", "root"
        tree["ik_hand_gun"] = "ik_hand_root"
        for s in SIDES:
            tree[f"ik_foot_{s}"] = "ik_foot_root"
            tree[f"ik_hand_{s}"] = "ik_hand_gun"
    return tree


REQUIRED = tuple(
    ["root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head"]
    + [f"{b}_{s}" for s in SIDES for b in ("clavicle", "upperarm", "lowerarm", "hand", "thigh", "calf", "foot", "ball")]
)
HELPERS = ("root", "ik_foot_root", "ik_hand_root", "ik_hand_gun", "ik_foot_l", "ik_foot_r", "ik_hand_l", "ik_hand_r")
