"""UE5 Bridge: clean FBX export to Unreal Engine 5 (static meshes, modular skeletal meshes, animations, root motion).

Everything is exported from temporary copies, so the scene stays untouched. See README.md.
"""
import bpy
from bpy.props import CollectionProperty, PointerProperty

from . import i18n, operators, props, ui

classes = (props.UE_Issue, props.UE_Settings, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ue_settings = PointerProperty(type=props.UE_Settings)
    bpy.types.Scene.ue_issues = CollectionProperty(type=props.UE_Issue)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.ue_issues
    del bpy.types.Scene.ue_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
