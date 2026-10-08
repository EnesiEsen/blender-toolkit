"""Terrain Blend: blend any number of PBR texture sets on one mesh, each placed by a vertex-group mask.

Vertex groups are packed 4 per color attribute by a Geometry Nodes modifier (see masks.py), so the material is live
while weight painting and stays inside EEVEE's attribute limit. See README.md for the workflow.
"""

import bpy
from bpy.props import CollectionProperty, IntProperty, PointerProperty

from . import automask, i18n, operators, props, ui

classes = (props.TB_Layer, props.TB_Settings, *automask.classes, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.tb_layers = CollectionProperty(type=props.TB_Layer)
    bpy.types.Object.tb_index = IntProperty()
    bpy.types.Object.tb_settings = PointerProperty(type=props.TB_Settings)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Object.tb_settings
    del bpy.types.Object.tb_index
    del bpy.types.Object.tb_layers
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
