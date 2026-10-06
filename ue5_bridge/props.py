"""Scene settings and the list of problems found by the rig check."""
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import PropertyGroup


class UE_Issue(PropertyGroup):
    severity: StringProperty()
    code: StringProperty()
    object_name: StringProperty()
    message: StringProperty()


class UE_Settings(PropertyGroup):
    output_dir: StringProperty(name="Export Folder", subtype="DIR_PATH",
                               description="StaticMeshes, SkeletalMeshes and Animations folders are created here")
    prefixes: BoolProperty(name="UE Name Prefixes", default=True,
                           description="Name files SM_ (static), SK_ (skeletal), A_ (animation) like the UE guide")
    center_origin: BoolProperty(name="Center at Origin", default=True,
                                description="Export every part at (0, 0, 0) wherever it sits (scene stays unchanged)")
    skeletal_mode: EnumProperty(name="Skeletal Meshes", default="PER_MESH", items=(
        ("PER_MESH", "One File per Mesh", "Modular parts (trousers, jacket, shoes) share the skeleton, one FBX each"),
        ("COMBINED", "One File", "The skeleton and all its meshes in a single FBX"),
    ))
    fix_rig: BoolProperty(name="Fix Skeleton on Export", default=True,
                          description="Add a single root bone when there are several (on the export copy only)")
    root_name: StringProperty(name="Root Bone", default="root",
                              description="Name of the root bone that is added or used")
    only_deform: BoolProperty(name="Only Deform Bones", default=True,
                              description="Leave control and helper bones out of the FBX")
    leaf_bones: BoolProperty(name="Leaf Bones", default=False,
                             description="Add an end bone to every chain. Leave off: UE5 shows them as phantom bones")
    armature_node: EnumProperty(name="Armature Node", default="NULL", items=(
        ("NULL", "Null", "The armature object is exported as an empty node (Blender default)"),
        ("ROOT", "Root", "The armature object is exported as a root node"),
        ("LIMBNODE", "Limb Node", "The armature object is exported as a bone-like node"),
    ), description="How the armature object itself is written. Try another one if UE5 imports an extra root bone")
    tangents: BoolProperty(name="Tangent Space", default=True)
    anim_source: EnumProperty(name="Animations", default="ACTIONS", items=(
        ("ACTIONS", "All Actions", "Every action that animates this skeleton"),
        ("NLA", "NLA Tracks", "Every NLA track becomes its own file (named after the track)"),
        ("ACTIVE", "Active Action", "Only the action that is assigned to the armature now"),
    ))
    root_motion: BoolProperty(name="Root Motion", default=False,
                              description="Move the walking motion from the hips to the root bone so UE5 can drive the "
                                          "character with it (Motion Matching, root motion)")
    hips_bone: StringProperty(name="Hips Bone", default="",
                              description="Bone whose horizontal motion goes to the root bone. Empty: guess by name")
    bake_step: FloatProperty(name="Bake Step", default=1.0, min=0.1, max=10.0,
                             description="Frames between baked keys (1 = every frame)")
