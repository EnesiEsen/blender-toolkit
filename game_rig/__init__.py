"""Game Rig Kit: build an Unreal Engine 5 mannequin skeleton on your character, skin it, add IK and retarget animations.

Place the landmark markers, press Build Rig, bind the mesh. Mixamo and Rigify rigs can be renamed to the UE5 names and
their animations retargeted. See README.md.
"""

import bpy
from bpy.props import CollectionProperty, PointerProperty

from . import i18n, operators, props, ui

classes = (props.GR_Issue, props.GR_Settings, *operators.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gr_settings = PointerProperty(type=props.GR_Settings)
    bpy.types.Scene.gr_issues = CollectionProperty(type=props.GR_Issue)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.gr_issues
    del bpy.types.Scene.gr_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
