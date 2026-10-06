"""Retopo Kit: one-click quad retopology (QuadriFlow or QRemeshify), guide curves and a quality report.

Workflow: pick a preset and a target face count, press Retopologize. For faces, hands and other hard areas, draw guide
curves first so the quads follow them. See README.md.
"""
import bpy
from bpy.props import PointerProperty

from . import guides, i18n, props, remesh, report, ui

classes = (props.RK_Settings, props.RK_Report, *report.classes, *guides.classes, *remesh.classes, *ui.classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.rk_settings = PointerProperty(type=props.RK_Settings)
    bpy.types.Scene.rk_report = PointerProperty(type=props.RK_Report)
    bpy.app.translations.register(__package__, i18n.translations)


def unregister():
    bpy.app.translations.unregister(__package__)
    del bpy.types.Scene.rk_report
    del bpy.types.Scene.rk_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
