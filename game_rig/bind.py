"""Skin meshes to the rig with automatic weights, then limit, clean and normalize them."""

import bpy


def bind(context, armature, meshes, max_influences=4):
    """Parent the meshes to the rig with automatic weights. Returns {mesh name: method used}."""
    used = {}
    for mesh in meshes:
        for method in ("ARMATURE_AUTO", "ARMATURE_ENVELOPE"):
            for other in context.view_layer.objects:
                if other is not None:
                    other.select_set(False)
            mesh.select_set(True)
            armature.select_set(True)
            context.view_layer.objects.active = armature
            try:
                with context.temp_override(
                    object=armature,
                    active_object=armature,
                    selected_objects=[armature, mesh],
                    selected_editable_objects=[armature, mesh],
                ):
                    bpy.ops.object.parent_set(type=method)
            except RuntimeError:
                continue
            used[mesh.name] = method
            break
        else:
            continue
        clean_weights(context, mesh, max_influences)
    return used


def clean_weights(context, mesh, max_influences):
    """Keep the strongest `max_influences` bones per vertex, drop tiny weights and make the rest add up to 1."""
    context.view_layer.objects.active = mesh
    with context.temp_override(
        object=mesh, active_object=mesh, selected_objects=[mesh], selected_editable_objects=[mesh]
    ):
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=max_influences)
        bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.001)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
