"""Scatter Brush: spread grass, rocks and trees over a weight-painted area, or place them with a click brush.

Make a category from your models (grass blades, rocks, trees), set its randomness once, then either paint a vertex
group on the ground (live Geometry Nodes layer) or click and drag in the viewport. See README.md.
"""

import bpy

from . import i18n, operators, props, ui

classes = (*props.classes, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    props.register()
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    operators.cleanup()
    props.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
