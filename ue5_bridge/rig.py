"""Skeleton checks and the temporary export copy of a rig. The scene is never changed: everything that has to be fixed
for Unreal (one root bone, no object transform surprises, centered at the origin) is done on copies that are deleted
after the export.
"""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"
TEMP = "ue_tmp_"


def issue(severity, code, ob, message):
    return {"severity": severity, "code": code, "object": ob.name, "message": message}


def root_bones(armature):
    return [b for b in armature.data.bones if b.parent is None]


def scan(armature):
    """Problems of one armature that would make the UE5 import go wrong."""
    found = []
    roots = root_bones(armature)
    if len(roots) > 1:
        found.append(
            issue(
                ERROR,
                "MULTI_ROOT",
                armature,
                rpt_("'{name}' has {count} root bones ({roots}): UE5 needs exactly one.").format(
                    name=armature.name, count=len(roots), roots=", ".join(b.name for b in roots[:4])
                ),
            )
        )
    if not any(b.use_deform for b in armature.data.bones):
        found.append(
            issue(ERROR, "NO_DEFORM", armature, rpt_("'{name}' has no deform bones.").format(name=armature.name))
        )
    _, rotation, scale = armature.matrix_world.decompose()
    if any(abs(c - 1.0) > 1e-4 for c in scale) or any(abs(a) > 1e-4 for a in rotation.to_euler()):
        found.append(
            issue(
                WARNING,
                "ARMATURE_TRANSFORM",
                armature,
                rpt_("'{name}' has scale or rotation on the object: apply it (Ctrl+A) before animating.").format(
                    name=armature.name
                ),
            )
        )
    if armature.name.lower().startswith("armature"):
        found.append(
            issue(
                INFO,
                "ARMATURE_NAME",
                armature,
                rpt_("'{name}' keeps Blender's default name: UE5 can mistake it for a bone.").format(
                    name=armature.name
                ),
            )
        )
    return found


def unique_bone_name(armature, name):
    taken = {b.name for b in armature.data.bones}
    candidate, n = name, 1
    while candidate in taken:
        n += 1
        candidate = f"{name}_{n}"
    return candidate


def ensure_single_root(context, armature, name="root", force=False):
    """Give the armature exactly one root bone (adds one above the others when needed). Returns its name.

    `force` adds a new root even when there is only one root bone already (root motion needs a bone above the hips).
    """
    roots = root_bones(armature)
    if len(roots) == 1 and not force:
        return roots[0].name
    context.view_layer.objects.active = armature
    with context.temp_override(object=armature, active_object=armature):
        bpy.ops.object.mode_set(mode="EDIT")
    edit = armature.data.edit_bones
    orphans = [b for b in edit if b.parent is None]
    root = edit.new(unique_bone_name(armature, name))
    root.head, root.tail = (0.0, 0.0, 0.0), (0.0, 0.0, 0.1)
    root.use_deform = False
    for bone in orphans:
        bone.parent = root
    root_name = root.name
    with context.temp_override(object=armature, active_object=armature):
        bpy.ops.object.mode_set(mode="OBJECT")
    return root_name


def root_above(context, armature, hips_name, name="root"):
    """Name of the bone the hips hang directly under, adding a root bone above the hips when they are the root."""
    hips = armature.data.bones[hips_name]
    if hips.parent is None:
        return ensure_single_root(context, armature, name, force=True)
    if hips.parent.parent is None:
        return hips.parent.name
    raise ValueError(rpt_("'{hips}' must hang directly under the root bone for root motion.").format(hips=hips_name))


class RigCopy:
    """Copies of an armature and some of its meshes that can be altered freely and are removed by `cleanup`."""

    def __init__(self, context, armature, meshes, settings, apply_transform=True):
        self.context, self.objects = context, []
        scene = context.scene
        self.armature = self._copy(armature, scene)
        self.meshes = []
        shift = -armature.matrix_world.translation if settings.center_origin else None
        for mesh in meshes:
            copy = self._copy(mesh, scene)
            for modifier in copy.modifiers:
                if modifier.type == "ARMATURE" and modifier.object == armature:
                    modifier.object = self.armature
            if mesh.parent == armature:
                copy.parent = self.armature
                copy.matrix_parent_inverse = mesh.matrix_parent_inverse.copy()
            elif shift is not None:
                copy.location = copy.location + shift
            self.meshes.append(copy)
        if shift is not None:
            self.armature.location = self.armature.location + shift
        context.view_layer.update()
        self.root_name = None
        if settings.fix_rig:
            self.root_name = ensure_single_root(context, self.armature, settings.root_name)
        scaled = any(abs(c - 1.0) > 1e-6 for c in self.armature.scale)
        if apply_transform and (scaled or any(abs(a) > 1e-6 for a in self.armature.rotation_euler)):
            self.apply_transform()

    def _copy(self, ob, scene):
        copy = ob.copy()
        copy.data = ob.data.copy()
        copy.name = TEMP + ob.name
        scene.collection.objects.link(copy)
        self.objects.append(copy)
        return copy

    def apply_transform(self):
        """Apply rotation and scale of the armature copy (and its meshes), as Ctrl+A would."""
        context = self.context
        everything = [self.armature, *self.meshes]
        for other in list(context.view_layer.objects):
            if other is not None:
                other.select_set(False)
        for ob in everything:
            ob.select_set(True)
        context.view_layer.objects.active = self.armature
        with context.temp_override(
            object=self.armature,
            active_object=self.armature,
            selected_objects=everything,
            selected_editable_objects=everything,
        ):
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True, properties=False)

    def cleanup(self):
        for ob in self.objects:
            data = ob.data
            bpy.data.objects.remove(ob)
            if data is not None and data.users == 0:
                (bpy.data.armatures if isinstance(data, bpy.types.Armature) else bpy.data.meshes).remove(data)
