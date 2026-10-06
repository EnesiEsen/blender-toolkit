"""Scene settings and the stored list of problems found by the Doctor."""
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup


class FK_Issue(PropertyGroup):
    severity: StringProperty()  # ERROR, WARNING or INFO
    code: StringProperty()
    object_name: StringProperty()
    message: StringProperty()
    data: StringProperty()  # extra argument of the fix, for example an image name
    fixable: BoolProperty()


class FK_Settings(PropertyGroup):
    target: EnumProperty(name="Target", default="PROP", items=(
        ("PROP", "Prop", "A static object: collision, LODs, YTYP archetype, textures"),
        ("MLO", "MLO / Interior", "An interior with rooms, portals and entities"),
        ("PED", "Ped / Clothing", "A rigged character or clothing piece"),
    ))
    resource_name: StringProperty(name="Resource Name", default="my_props",
                                  description="Name of the FiveM resource folder that is created")
    output_dir: StringProperty(name="Output Folder", subtype="DIR_PATH",
                               description="The resource folder is created here")
    export_format: EnumProperty(name="Format", default="NATIVE", items=(
        ("NATIVE", "FiveM (binary)", "Binary .ydr/.ybn/.ytyp/.ytd, ready for the stream folder"),
        ("CWXML", "CodeWalker XML", "XML files you open or convert in CodeWalker"),
    ))
    selected_only: BoolProperty(name="Selected Only", default=False, description="Export only the selected assets")
    auto_fix: BoolProperty(name="Fix Problems First", default=True,
                           description="Fix the safe problems (names, scale, UVs, materials, texture sizes) first")
    max_texture: EnumProperty(name="Max Texture Size", default="2048", items=(
        ("512", "512", ""), ("1024", "1024", "Good for small props"), ("2048", "2048", "Usual maximum for props"),
        ("4096", "4096", "Heavy: costs a lot of video memory"),
    ))
    tri_limit: IntProperty(name="Triangle Warning", default=100000, min=100,
                           description="Warn when one prop has more triangles than this")

    # Prop
    separate: BoolProperty(name="One Prop per Object", default=True,
                           description="Off: all selected objects become a single prop")
    collision: EnumProperty(name="Collision", default="PROXY", items=(
        ("NONE", "None", "No collision"),
        ("PROXY", "Simplified Copy", "A low-poly copy of the mesh (best for most props)"),
        ("HULL", "Convex Hull", "The tightest convex shape around the mesh: very cheap, fills hollows"),
        ("MESH", "Exact Mesh", "The visible mesh itself: precise but heavy"),
    ))
    collision_tris: IntProperty(name="Collision Triangles", default=300, min=12, soft_max=5000,
                                description="Target triangle count of the simplified collision")
    make_lods: BoolProperty(name="Generate LODs", default=True)
    lod_preset: EnumProperty(name="LOD Strength", default="AUTO", items=(
        ("AUTO", "Balanced", "50 %, 25 % and 10 % of the triangles"),
        ("AGGRESSIVE", "Aggressive", "35 %, 12 % and 4 %: fewer triangles, lower quality"),
        ("GENTLE", "Gentle", "70 %, 45 % and 25 %: keeps more detail"),
    ))
    lod_scale: FloatProperty(name="LOD Distance Scale", default=1.0, min=0.1, max=10.0,
                             description="Multiplies the LOD distances worked out from the size of the prop")
    mlo_collision: EnumProperty(name="Interior Collision", default="PROXY", items=(
        ("PROXY", "Simplified Copy", "A low-poly copy of every room mesh"),
        ("MESH", "Exact Mesh", "The room meshes themselves: precise but heavy"),
    ))
    mlo_collision_tris: IntProperty(name="Triangles per Mesh", default=1500, min=12, soft_max=20000,
                                    description="Target triangle count of the simplified collision of each room mesh")
    ped_armature: PointerProperty(name="GTA Skeleton", type=bpy.types.Object,
                                  poll=lambda self, ob: ob.type == "ARMATURE",
                                  description="The ped skeleton (imported from a YFT) the meshes should be rigged to")
    ped_backup: BoolProperty(name="Keep Weight Backup", default=True,
                             description="Keep a hidden copy of every mesh before its weights are moved")
    ped_mapping: StringProperty(name="Mapping Sheet", default="fk_bone_map",
                                description="Text block with 'source bone = GTA bone' lines that override the guesses")
    create_ytyp: BoolProperty(name="Create YTYP Archetype", default=True)
    convert_dds: BoolProperty(name="Convert Textures to DDS", default=True,
                              description="FiveM needs DDS textures (DXT1/DXT5 with mipmaps); others are converted")
    create_ytd: BoolProperty(name="Also Write a YTD", default=False,
                             description="Also create a shared texture dictionary named like the prop (Sollumz "
                                         "2.8.3+); textures are embedded in the drawable anyway")
