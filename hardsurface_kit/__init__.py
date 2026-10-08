"""Hard Surface Kit: a non-destructive hard-surface workflow made of ordinary modifiers.

Smart Bevel with weighted normals, boolean cutters you can move and remove, mirror and radial arrays, panel grooves,
mesh cleanup and an Apply Stack that leaves a clean, game-ready mesh. See README.md.
"""

import bpy
from bpy.props import PointerProperty

from . import i18n, operators, props, ui

classes = (props.HS_Settings, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.hs_settings = PointerProperty(type=props.HS_Settings)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.hs_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
