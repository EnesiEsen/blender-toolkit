"""Property groups stored on the object: the layer list and the options."""
from bpy.props import BoolProperty, StringProperty
from bpy.types import PropertyGroup

from . import core


def _rebuild(self, context):
    core.rebuild_if_built(self.id_data)


class TB_Layer(PropertyGroup):
    name: StringProperty(name="Name", default="Layer")
    folder: StringProperty(
        name="Texture Folder", subtype="DIR_PATH",
        description="Folder of one texture set (Color, Normal, Roughness and Height/Displacement files)")
    mask: StringProperty(name="Mask", description="Vertex group that decides where this layer is visible")


class TB_Settings(PropertyGroup):
    lite: BoolProperty(
        name="Lite Preview", update=_rebuild,
        description="Use only the color and height maps (2 textures per layer). Needed for many layers on the OpenGL "
                    "EEVEE backend (32 texture limit). Turn off for final quality")
    enhancer: BoolProperty(
        name="Texture Enhancer", update=_rebuild,
        description="Add procedural detail normal, crevice dirt and micro displacement (no extra textures)")
