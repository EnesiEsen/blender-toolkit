"""Operators: Doctor (scan, fix), Prop builder and the resource export."""
import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import IntProperty
from bpy.types import Operator

from . import compat, doctor, mlo, ped, prop, resource


def scan_pool(context):
    """Selected objects, or every asset in the scene when nothing is selected."""
    pool = list(context.selected_objects)
    if not pool:
        pool = [o for o in context.scene.objects if doctor.is_asset_root(o)]
    return pool


def refresh(context):
    s = context.scene.fk_settings
    context.scene.fk_issues.clear()
    pool = scan_pool(context)
    found_issues = doctor.scan(pool, s)
    if s.target == "PED":
        found_issues += ped.scan(pool)
    for found in found_issues:
        item = context.scene.fk_issues.add()
        item.severity, item.code, item.object_name = found["severity"], found["code"], found["object"]
        item.message, item.data, item.fixable = found["message"], found["data"], found["code"] in doctor.FIXES
    return len(context.scene.fk_issues)


def issue_dict(item):
    return {"severity": item.severity, "code": item.code, "object": item.object_name, "message": item.message,
            "data": item.data}


class FK_OT_scan(Operator):
    bl_idname = "fivem_toolkit.scan"
    bl_label = "Check Assets"
    bl_description = "Look for problems that break FiveM assets: names, scale, UVs, materials, textures, triangles"
    bl_options = {"REGISTER"}

    def execute(self, context):
        count = refresh(context)
        message = rpt_("{count} problems found.").format(count=count) if count else rpt_("No problems found.")
        self.report({"INFO"}, message)
        return {"FINISHED"}


class FK_OT_fix(Operator):
    bl_idname = "fivem_toolkit.fix"
    bl_label = "Fix"
    bl_description = "Fix this problem"
    bl_options = {"REGISTER", "UNDO"}
    index: IntProperty()

    def execute(self, context):
        items = context.scene.fk_issues
        if not 0 <= self.index < len(items):
            return {"CANCELLED"}
        try:
            doctor.fix(context, issue_dict(items[self.index]))
        except (ValueError, KeyError, RuntimeError) as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        refresh(context)
        return {"FINISHED"}


class FK_OT_fix_all(Operator):
    bl_idname = "fivem_toolkit.fix_all"
    bl_label = "Fix All"
    bl_description = "Fix every problem that has an automatic fix"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        fixed, failed = doctor.fix_all(context, [issue_dict(i) for i in context.scene.fk_issues])
        remaining = refresh(context)
        self.report({"WARNING" if failed else "INFO"}, rpt_("{fixed} fixed, {left} left.").format(
            fixed=fixed, left=remaining) + (" " + failed[0] if failed else ""))
        return {"FINISHED"}


class FK_OT_build_prop(Operator):
    bl_idname = "fivem_toolkit.build_prop"
    bl_label = "Build Props"
    bl_description = ("Turn the selected meshes into FiveM props: Sollumz drawable, converted materials, LODs, "
                      "collision, YTYP archetype and texture dictionary")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type == "MESH" for o in context.selected_objects) and context.mode == "OBJECT"

    def execute(self, context):
        try:
            _, summary = prop.build(context, context.selected_objects, context.scene.fk_settings)
        except prop.BuildError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        refresh(context)
        self.report({"INFO"}, summary)
        return {"FINISHED"}


class FK_OT_export(Operator):
    bl_idname = "fivem_toolkit.export"
    bl_label = "Export Resource"
    bl_description = "Write the FiveM resource: stream folder with the assets and an fxmanifest.lua"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return compat.ready() and context.mode == "OBJECT"

    def execute(self, context):
        s = context.scene.fk_settings
        try:
            path, files = resource.export(context, s)
        except resource.ExportError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, rpt_("Exported {count} files to {path}").format(count=len(files), path=path))
        return {"FINISHED"}


def rigged_selection(context):
    return [o for o in context.selected_objects if ped.is_rigged_candidate(o)]


class FK_OT_ped_retarget(Operator):
    bl_idname = "fivem_toolkit.ped_retarget"
    bl_label = "Retarget Weights"
    bl_description = ("Rename and merge the vertex groups of the selected meshes onto GTA V bones; groups of bones the "
                      "GTA skeleton lacks go to their nearest parent bone")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and any(ped.is_rigged_candidate(o) for o in context.selected_objects)

    def execute(self, context):
        s = context.scene.fk_settings
        sheet = bpy.data.texts.get(s.ped_mapping)
        total = {"mapped": 0, "merged": 0, "dropped": []}
        try:
            for ob in rigged_selection(context):
                result = ped.retarget(context, ob, s.ped_armature, sheet.as_string() if sheet else "", s.ped_backup)
                total["mapped"] += result["mapped"]
                total["merged"] += len(result["merged"])
                total["dropped"] += result["dropped"]
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        refresh(context)
        message = rpt_("{mapped} GTA bones used, {merged} groups merged into parent bones.").format(
            mapped=total["mapped"], merged=total["merged"])
        if total["dropped"]:
            message += " " + rpt_("No match for: {names}").format(names=", ".join(total["dropped"][:6]))
        self.report({"WARNING" if total["dropped"] else "INFO"}, message)
        return {"FINISHED"}


class FK_OT_ped_mapping_sheet(Operator):
    bl_idname = "fivem_toolkit.ped_mapping_sheet"
    bl_label = "Create Mapping Sheet"
    bl_description = "Create a text block listing the vertex groups that could not be matched, to fill in by hand"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.fk_settings
        gta = ped.gta_bones()
        resolve = ped.make_resolver(gta, {})
        lines = ["# source bone = GTA bone   (one per line; lines starting with # are ignored)"]
        for ob in rigged_selection(context):
            lines += [f"{g.name} = " for g in ob.vertex_groups if not resolve(g.name)]
        sheet = bpy.data.texts.get(s.ped_mapping) or bpy.data.texts.new(s.ped_mapping)
        sheet.from_string("\n".join(lines))
        self.report({"INFO"}, rpt_("Mapping sheet '{name}' written: fill in the GTA bone after each '='.").format(
            name=sheet.name))
        return {"FINISHED"}


def interior_root(context):
    """The collection chosen in the outliner (the one that holds the room.* sub-collections)."""
    return context.view_layer.active_layer_collection.collection


class FK_OT_mlo_template(Operator):
    bl_idname = "fivem_toolkit.mlo_template"
    bl_label = "Create Interior Template"
    bl_description = "Add a starter interior: two rooms, a portal between them and an entrance from limbo"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = mlo.create_template(context, context.scene.fk_settings.resource_name)
        self.report({"INFO"}, rpt_("Created '{name}': rename the rooms, replace the shells with your models.").format(
            name=root.name))
        return {"FINISHED"}


class FK_OT_mlo_check(Operator):
    bl_idname = "fivem_toolkit.mlo_check"
    bl_label = "Check Interior"
    bl_description = "List what is wrong with the room and portal layout of the active collection"
    bl_options = {"REGISTER"}

    def execute(self, context):
        layout = mlo.read_layout(interior_root(context))
        context.scene.fk_issues.clear()
        for message in layout.problems:
            item = context.scene.fk_issues.add()
            item.severity, item.code, item.message = doctor.ERROR, "LAYOUT", message
        self.report({"INFO"}, rpt_("{count} layout problems.").format(count=len(layout.problems)))
        return {"FINISHED"}


class FK_OT_build_mlo(Operator):
    bl_idname = "fivem_toolkit.build_mlo"
    bl_label = "Build Interior"
    bl_description = ("Turn the room meshes into props, build the interior collision and fill the MLO archetype "
                      "with rooms, portals and entities")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        try:
            _, summary = mlo.build(context, interior_root(context), context.scene.fk_settings)
        except prop.BuildError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, summary)
        return {"FINISHED"}


classes = (FK_OT_scan, FK_OT_fix, FK_OT_fix_all, FK_OT_build_prop, FK_OT_export, FK_OT_mlo_template,
           FK_OT_mlo_check, FK_OT_build_mlo, FK_OT_ped_retarget, FK_OT_ped_mapping_sheet)
