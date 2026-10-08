"""Collision Maker: box, sphere, capsule, convex and decomposed collision shapes with Unreal's naming, plus a checker.

Select a mesh, pick a shape (or Auto) and press Create. The shapes are children of the mesh, named UBX_/USP_/UCP_/UCX_,
and UE5 Bridge exports them with the mesh. See README.md.
"""

import bpy
from bpy.props import CollectionProperty, PointerProperty

from . import i18n, operators, props, ui

classes = (props.CM_Issue, props.CM_Settings, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cm_settings = PointerProperty(type=props.CM_Settings)
    bpy.types.Scene.cm_issues = CollectionProperty(type=props.CM_Issue)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.cm_issues
    del bpy.types.Scene.cm_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
