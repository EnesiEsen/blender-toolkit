"""Texture Kit: check textures, pack channels (ORM) and export texture sets that Unreal imports correctly.

Everything works on copies: your images and materials are never overwritten. See README.md.
"""

import bpy
from bpy.props import CollectionProperty, PointerProperty

from . import i18n, operators, props, ui

classes = (props.TK_Issue, props.TK_PackSlot, props.TK_Settings, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.tk_settings = PointerProperty(type=props.TK_Settings)
    bpy.types.Scene.tk_issues = CollectionProperty(type=props.TK_Issue)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.tk_issues
    del bpy.types.Scene.tk_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
