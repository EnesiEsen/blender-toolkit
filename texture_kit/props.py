"""Scene settings, the channel packer slots and the list of problems found by the Doctor."""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

SIZES = (("512", "512", ""), ("1024", "1024", ""), ("2048", "2048", ""), ("4096", "4096", ""), ("8192", "8192", ""))
CHANNELS = (
    ("R", "Red", ""),
    ("G", "Green", ""),
    ("B", "Blue", ""),
    ("A", "Alpha", ""),
    ("LUMA", "Luminance", "Brightness of the color"),
)


class TK_Issue(PropertyGroup):
    severity: StringProperty()  # ERROR, WARNING or INFO
    code: StringProperty()
    message: StringProperty()
    image_name: StringProperty()
    fixable: BoolProperty()


class TK_PackSlot(PropertyGroup):
    image: PointerProperty(name="Source Image", type=bpy.types.Image)
    channel: EnumProperty(name="Channel", items=CHANNELS, default="R", description="Which channel of the image to take")
    invert: BoolProperty(name="Invert", description="Use 1 - value (for example gloss to roughness)")
    value: FloatProperty(name="Value", default=1.0, min=0.0, max=1.0, description="Used when no image is set")


class TK_Settings(PropertyGroup):
    export_dir: StringProperty(
        name="Export Folder", subtype="DIR_PATH", description="The texture files are written here"
    )
    asset_name: StringProperty(
        name="Asset Name", description="Used in the file names (T_<name>_BC). Empty: the material name"
    )
    size_limit: EnumProperty(
        name="Max Size", items=SIZES, default="2048", description="Larger textures are scaled down"
    )
    power_of_two: BoolProperty(
        name="Power of Two",
        default=True,
        description="Scale every texture to the nearest power of two (Unreal streams only those)",
    )
    file_format: EnumProperty(name="File Format", default="PNG", items=(("PNG", "PNG", ""), ("TARGA", "TGA", "")))
    normal_mode: EnumProperty(
        name="Normal Map",
        default="FLIP",
        items=(
            ("FLIP", "Blender to Unreal", "Flip the green channel: Blender is OpenGL (Y+), Unreal wants DirectX (Y-)"),
            ("KEEP", "Keep as it is", "Export the normal map unchanged"),
        ),
    )
    pack_orm: BoolProperty(
        name="Pack ORM",
        default=True,
        description="Occlusion in red, roughness in green and metallic in blue, in one texture",
    )
    ao_image: PointerProperty(
        name="AO Image",
        type=bpy.types.Image,
        description="Ambient occlusion for the ORM texture (a material has no AO input)",
    )
    doctor_max: EnumProperty(name="Warn Above", items=SIZES, default="4096")
    normal_image: PointerProperty(name="Normal Map", type=bpy.types.Image)
    pack_name: StringProperty(name="Name", default="T_Packed")
    pack_size: EnumProperty(name="Size", default="AUTO", items=(("AUTO", "Largest Source", ""), *SIZES))
    pack_save: BoolProperty(name="Save to Export Folder", default=False)
    slot_r: PointerProperty(type=TK_PackSlot)
    slot_g: PointerProperty(type=TK_PackSlot)
    slot_b: PointerProperty(type=TK_PackSlot)
    slot_a: PointerProperty(type=TK_PackSlot)
