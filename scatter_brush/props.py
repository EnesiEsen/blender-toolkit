"""Scene and object data: categories (a collection of assets plus all scatter settings) and surface layers."""

import math

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup


def _changed(self, context):
    """A category setting moved: push it into every surface layer that uses the category."""
    from . import layers

    layers.sync_category(context.scene, self)


class SB_Category(PropertyGroup):
    name: StringProperty(name="Name", default="Category")
    uid: IntProperty(default=0)
    collection: PointerProperty(
        name="Assets",
        type=bpy.types.Collection,
        description="Collection that holds the models of this category",
        update=_changed,
    )
    output: PointerProperty(
        name="Placed", type=bpy.types.Collection, description="Collection that receives the brush-placed objects"
    )

    # Variation (brush and surface layers)
    scale_min: FloatProperty(name="Scale Min", default=0.8, min=0.01, soft_max=5.0, update=_changed)
    scale_max: FloatProperty(name="Scale Max", default=1.2, min=0.01, soft_max=5.0, update=_changed)
    height_var: FloatProperty(
        name="Height Variation",
        description="Extra random stretch of the height only",
        default=0.1,
        min=0.0,
        max=1.0,
        update=_changed,
    )
    yaw: FloatProperty(
        name="Random Turn",
        description="Largest random turn around the up axis",
        default=math.tau,
        min=0.0,
        max=math.tau,
        subtype="ANGLE",
        update=_changed,
    )
    tilt: FloatProperty(
        name="Random Tilt",
        description="Largest random lean away from the up axis",
        default=math.radians(6.0),
        min=0.0,
        max=math.radians(60.0),
        subtype="ANGLE",
        update=_changed,
    )
    align: FloatProperty(
        name="Align to Surface",
        description="0 = always upright, 1 = follows the surface normal",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=_changed,
    )
    sink: FloatProperty(
        name="Sink",
        description="Push the objects into the ground (meters)",
        default=0.0,
        soft_min=-1.0,
        soft_max=1.0,
        subtype="DISTANCE",
        update=_changed,
    )
    seed: IntProperty(name="Seed", default=1, min=0, update=_changed)

    # Brush
    radius: FloatProperty(name="Radius", default=2.0, min=0.0, soft_max=50.0, subtype="DISTANCE")
    count: IntProperty(name="Objects per Stamp", default=6, min=1, soft_max=100)
    spacing: FloatProperty(
        name="Stroke Spacing",
        description="Dragging stamps again after this fraction of the radius",
        default=0.35,
        min=0.05,
        max=2.0,
        subtype="FACTOR",
    )
    max_slope: FloatProperty(
        name="Max Slope",
        description="Skip surfaces steeper than this (90 = no limit)",
        default=math.radians(90.0),
        min=math.radians(5.0),
        max=math.radians(90.0),
        subtype="ANGLE",
    )

    # Surface layers
    density: FloatProperty(
        name="Density",
        description="Objects per square meter where the weight is 1",
        default=10.0,
        min=0.0,
        soft_max=500.0,
        update=_changed,
    )
    even: BoolProperty(
        name="Even Spacing", description="Keep the minimum distance between objects (slower)", update=_changed
    )
    min_distance: FloatProperty(
        name="Min Distance",
        description="Smallest gap between two objects",
        default=0.0,
        min=0.0,
        soft_max=10.0,
        subtype="DISTANCE",
        update=_changed,
    )
    falloff: FloatProperty(
        name="Edge Falloff",
        description="Above 1 thins the objects faster toward weak weights",
        default=1.0,
        min=0.1,
        max=8.0,
        update=_changed,
    )
    threshold: FloatProperty(
        name="Weight Cutoff",
        description="Weights at or below this get no objects",
        default=0.02,
        min=0.0,
        max=0.99,
        update=_changed,
    )
    edge_scale: FloatProperty(
        name="Shrink at Edges",
        description="Objects get smaller where the weight is weak",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=_changed,
    )


def _layer_changed(self, context):
    from . import layers

    layers.push_layer(self.id_data, self, context.scene)


class SB_Layer(PropertyGroup):
    """One scatter modifier on a surface object: a category painted by a vertex group."""

    modifier: StringProperty()
    cat_id: IntProperty()
    group: StringProperty(name="Weights", description="Vertex group that paints the area", update=_layer_changed)
    density: FloatProperty(
        name="Density ×",
        description="Multiplies the category density on this surface",
        default=1.0,
        min=0.0,
        soft_max=10.0,
        update=_layer_changed,
    )


classes = (SB_Category, SB_Layer)


def register():
    bpy.types.Scene.sb_categories = CollectionProperty(type=SB_Category)
    bpy.types.Scene.sb_index = IntProperty(default=0)
    bpy.types.Scene.sb_next_uid = IntProperty(default=1)
    bpy.types.Scene.sb_erase = BoolProperty(
        name="Erase", description="The brush removes placed objects instead (also: hold Shift)"
    )
    bpy.types.Object.sb_layers = CollectionProperty(type=SB_Layer)


def unregister():
    del bpy.types.Object.sb_layers
    del bpy.types.Scene.sb_erase
    del bpy.types.Scene.sb_next_uid
    del bpy.types.Scene.sb_index
    del bpy.types.Scene.sb_categories
