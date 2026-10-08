"""Texel Density: measure how many texture pixels cover a meter of surface, see it as colors, and set it exactly.

Consistent density is what makes a game world look sharp everywhere. See README.md.
"""

import bpy
from bpy.props import PointerProperty

from . import i18n, operators, props, ui

classes = (props.TD_Report, props.TD_Settings, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.td_settings = PointerProperty(type=props.TD_Settings)
    bpy.types.Scene.td_report = PointerProperty(type=props.TD_Report)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.td_report
    del bpy.types.Scene.td_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
