"""FiveM Toolkit: one-click props, an asset Doctor and a FiveM resource export, built on top of Sollumz.

Sollumz must be installed and enabled. See README.md for the workflow.
"""
import bpy
from bpy.props import CollectionProperty, PointerProperty

from . import i18n, operators, props, ui

classes = (props.FK_Issue, props.FK_Settings, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fk_settings = PointerProperty(type=props.FK_Settings)
    bpy.types.Scene.fk_issues = CollectionProperty(type=props.FK_Issue)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.fk_issues
    del bpy.types.Scene.fk_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
