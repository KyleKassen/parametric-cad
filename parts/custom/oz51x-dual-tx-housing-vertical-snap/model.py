"""Two-hook / two-snap PA12 cover on the verified OZ51x mounting architecture.

Canonical XY is the printing/cover plane, Z points out of the open base.
Installed +Y is FRONT I/O. All units are mm. See DESIGN.md / CONNECTOR.md.
No sibling source files are modified.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).absolute().parent
PROJECT_ROOT = PART_DIR.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from lib.features import Build, recessed_panel, rounded_box  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "oz51x_snap_parent", PART_DIR.parent / "oz510-dual-housing" / "refine_opus5.py"
)
_refine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_refine)
_canon = _refine._canon
orient_to_mounting = _canon.orient_to_mounting


def load_params(path=PART_DIR / "params.json"):
    return _refine.load_params_file(Path(path))


def layout(params):
    result = _refine.layout(params)
    result["cover_fastener_count"] = 0
    result["latch_count"] = 2
    result["fixed_hook_count"] = 2
    return result


def box(w, d, h, x, y, z):
    """Boolean tool / internal mechanical feature, lower Z datum."""
    return cq.Workplane("XY").box(w, d, h, centered=(True, True, False)).translate((x, y, z))


def cylinder(r, x, y, z, height):
    return cq.Workplane("XY").circle(r).extrude(height).translate((x, y, z))


def d_profile(params, depth):
    """Rounded D/trapezoid, controlled maximum envelope, XY extrusion.

    The compensation keeps the broad rounded corners at cutout_w overall,
    rather than accidentally shrinking a nominally dimensioned trapezoid.
    This is a coupon-qualified design allowance, not a certified vendor STEP.
    """
    pc = params["panel_connector"]
    width, height, radius = pc["cutout_w"], pc["cutout_h"], pc["cutout_radius"]
    angle = math.radians(pc["side_angle_degrees"])
    compensation = radius * (1 / math.tan(math.pi / 4 - angle / 2) - 1)
    top = width / 2 + compensation
    bottom = top - height * math.tan(angle)
    return (
        cq.Workplane("XY")
        .polyline(
            [(-top, height / 2), (top, height / 2), (bottom, -height / 2), (-bottom, -height / 2)]
        )
        .close()
        .extrude(depth)
        .edges("|Z")
        .fillet(radius)
    )


def _front_connector(base, params, L):
    pc, h = params["panel_connector"], params["housing"]
    tool = d_profile(params, h["wall"] + 2)
    tool = tool.rotate((0, 0, 0), (1, 0, 0), 90).translate(
        (pc["x"], L["back_outer_y"] + 1, L["panel_connector_z"])
    )
    base = base.cut(tool)
    for dx in (-pc["screw_spacing"] / 2, pc["screw_spacing"] / 2):
        base = base.cut(
            _refine._y_cyl(
                pc["screw_hole_dia"] / 2,
                pc["x"] + dx,
                L["panel_connector_z"],
                L["plenum_y1"] - 1,
                h["wall"] + 2,
            )
        )
    rp = _refine.production(params)["rear_panel"]
    depth = pc["flange_recess"]
    well = rounded_box(
        rp["de9_flange_long"] + 0.8,
        rp["de9_flange_short"] + 0.8,
        depth + 0.2,
        1.5,
        top_break=0,
        bottom_break=0,
    )
    well = well.rotate((0, 0, 0), (1, 0, 0), 90).translate(
        (pc["x"], L["back_outer_y"] + 0.2, L["panel_connector_z"])
    )
    return base.cut(well)


def _remove_cover_columns(base, params, L):
    h = params["housing"]
    r = h["corner_post_dia"] / 2 + 0.1
    # Remove post lobes while leaving the functional central bay partition.
    rib_post_y = L["interior_half_y"] - h["corner_post_dia"] / 2 - 1
    for y in (-rib_post_y, 0, rib_post_y):
        tool = cylinder(r, 0, y, h["floor"], L["base_height"])
        rib = box(h["bay_gap"], 2 * r + 2, L["base_height"] + 2, 0, y, 0)
        base = base.cut(tool.cut(rib))
        base = base.union(
            cylinder(h["corner_post_pilot_dia"] / 2 + 0.2, 0, y, 0.2, L["base_height"] - 0.2)
        )
    # The two obsolete corner towers no longer crowd the fiber plenum.
    post_r = h["corner_post_dia"] / 2
    for side in (-1, 1):
        x = side * (L["interior_half_x"] - post_r - 1)
        y = L["plenum_y1"] - post_r - 1
        base = base.cut(cylinder(r, x, y, h["floor"], L["base_height"]))
    # Keep the spool web hub, but remove the unused blind screw bore.
    base = base.union(
        cylinder(h["corner_post_pilot_dia"] / 2 + 0.2, 0, L["spool_y"], 0.2, L["base_height"] - 0.2)
    )
    # Retain a 1 mm floor underneath each module's pilot, with actual overlap.
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1 if bay.get("mirror_x") else 1
        for hole in (params["module"]["screw_hole_front"], params["module"]["screw_hole_back"]):
            base = base.union(
                cylinder(
                    h["screw_boss_pilot_dia"] / 2 + 0.2, cx + sign * hole["x"], -hole["z"], 0.2, 0.8
                )
            )
    return base


def _snap_pockets(base, params, L):
    s = params["snap"]
    roof = L["base_height"] - s["hook_top_below_seam"] + s["roof_clearance"]
    bottom = L["base_height"] - s["hook_depth"] - 1.2
    for side in (-1, 1):
        for y in s["tip_y"]:
            local_roof = roof + (s["fixed_roof_relief"] if side == -1 else 0)
            # Blind inner-wall pockets; outside skin remains >=1.7 mm.
            pocket = box(
                s["pocket_depth"] + 2,
                s["hook_width"] + 1,
                local_roof - bottom,
                side * (L["interior_half_x"] + (s["pocket_depth"] - 2) / 2),
                y,
                bottom,
            )
            base = base.cut(pocket)
    return base


def _service_edge_breaks(base, params, L):
    """Deburr exposed tray/partition crests without touching hook catch roofs."""
    c = 0.4
    for x in L["bay_cx"]:
        mouth = rounded_box(
            L["bay_w"] + 2 * c, L["bay_d"] + 2 * c, 2, c, top_break=0, bottom_break=c
        )
        base = base.cut(mouth.translate((x, 0, L["base_height"] - c)))
    mouth = rounded_box(
        2 * L["interior_half_x"] + 2 * c,
        params["fiber_bay"]["depth"] + 2 * c,
        2,
        c,
        top_break=0,
        bottom_break=c,
    )
    mouth = mouth.translate((0, (L["plenum_y0"] + L["plenum_y1"]) / 2, L["base_height"] - c))
    # Spool crown is functional fiber retention, not a cavity mouth.
    spool_keep = cylinder(
        params["fiber_bay"]["spool_dia"] / 2 + 2, 0, L["spool_y"], 0, L["base_height"] + 3
    )
    return base.cut(mouth.cut(spool_keep))


def _base_build(params):
    L, p = layout(params), _refine.production(params)
    raw = _canon._create_base_canonical(_refine._canonical_without_rear_connector(params))
    trim = rounded_box(
        2 * L["outer_half_x"],
        L["total_depth"],
        L["base_height"],
        p["edges"]["plan_radius"],
        top_break=0.6,
        bottom_break=0.4,
    )
    trim = trim.translate((0, (L["back_outer_y"] - L["outer_half_y"]) / 2, 0))
    b = Build(raw.intersect(trim), "inherited_interface_tray")
    b.boolean(lambda v: _remove_cover_columns(v, params, L), "remove_cover_screw_structure")
    b.boolean(lambda v: _refine._lighten_spool(v, params, L, p), "hollow_fiber_spool")
    b.boolean(lambda v: _refine._mount_flanges(v, params, L, p), "preserved_mount_flanges")
    b.boolean(lambda v: _refine._cable_anchors(v, params, L, p), "harness_anchors")
    b.pocket(lambda v: _service_edge_breaks(v, params, L), "deburr_service_rims")
    b.pocket(lambda v: _refine._sc_flange_wells(v, params, L, p), "sc_adapter_lands")
    b.pocket(lambda v: _front_connector(v, params, L), "d_shaped_front_connector")
    b.pocket(lambda v: _snap_pockets(v, params, L), "four_blind_hook_pockets")
    b.hole(lambda v: _refine._drains(v, params, L, p), "preserved_gravity_drains")
    b.hole(lambda v: _refine._mount_face_drainage(v, params, L, p), "mount_face_drainage")
    b.hole(lambda v: _refine._base_labels(v, params, L, p), "sma_identification")
    return b


def _create_base_canonical(params):
    return _base_build(params).result


def latch_hook(params, tip_y, side=1):
    """Rigid hook/downleg. The +X copy rides on a planar cantilever."""
    L, s = layout(params), params["snap"]
    z = L["base_height"]
    xi = s["beam_outer_x"] - s["beam_thickness"]
    xo = s["beam_outer_x"]
    reach = L["interior_half_x"] + s["hook_reach"]
    low, top = z - s["hook_depth"], z - s["hook_top_below_seam"]
    # Ramp under the hook; its flat top catches the pocket roof.
    profile = [
        (xi, z + 0.25),
        (xo, z + 0.25),
        (xo, top),
        (reach, top),
        (reach, top - 0.7),
        (xo, low),
        (xi, low),
    ]
    hook = cq.Workplane("XZ").polyline(profile).close().extrude(s["hook_width"])
    hook = hook.translate((0, tip_y + s["hook_width"] / 2, 0))
    return hook if side == 1 else hook.mirror("YZ")


def snap_clearance_tool(params, tip_y):
    """Envelope of flexible cover region, for independent motion verification."""
    L, s = layout(params), params["snap"]
    xi = s["beam_outer_x"] - s["beam_thickness"] - 0.01
    return box(
        L["outer_half_x"] - xi + 2,
        s["beam_length"] + s["hook_width"] + 2,
        s["hook_depth"] + params["housing"]["lid_thickness"] + 2,
        (xi + L["outer_half_x"] + 2) / 2,
        tip_y - s["beam_length"] / 2,
        L["base_height"] - s["hook_depth"] - 1,
    )


def _cover_latches(cover, params, L):
    s = params["snap"]
    z, t = L["base_height"], params["housing"]["lid_thickness"]
    xi, xo = s["beam_outer_x"] - s["beam_thickness"], s["beam_outer_x"]
    for y in s["tip_y"]:
        root, end = y - s["beam_length"], y + s["hook_width"] / 2
        # Round-ended relief retains a broad root at the parent cover frame.
        inner = rounded_box(
            s["slot"], end - root + s["slot"], t + 2, s["root_radius"], top_break=0, bottom_break=0
        )
        inner = inner.translate((xi - s["slot"] / 2, (root + end + s["slot"]) / 2, z - 1))
        outer = box(
            L["outer_half_x"] - xo + 2,
            end - root + s["slot"],
            t + 2,
            (xo + L["outer_half_x"] + 2) / 2,
            (root + end + s["slot"]) / 2,
            z - 1,
        )
        # A recessed side button bridges outward from the free end only.
        pad = rounded_box(
            L["outer_half_x"] - 0.6 - xi, s["hook_width"], t, 1.0, top_break=0.4, bottom_break=0
        )
        pad = pad.translate(((xi + L["outer_half_x"] - 0.6) / 2, y, z))
        endgap = box(
            L["outer_half_x"] - xi + s["slot"] + 2,
            s["slot"],
            t + 2,
            (xi - s["slot"] + L["outer_half_x"] + 2) / 2,
            end + s["slot"] / 2,
            z - 1,
        )
        cover = cover.cut(inner).cut(outer).cut(endgap).union(pad)
        cover = cover.union(latch_hook(params, y, 1)).union(latch_hook(params, y, -1))
    return cover


def _cover_pads(cover, params, L):
    # Small registration pads carry in-plane shear without encircling fibers.
    s = params["snap"]
    for x in (-23, 23):
        pad = rounded_box(9, 2, s["pad_depth"] + 0.2, 0.8, top_break=0, bottom_break=0.4)
        pad = pad.translate(
            (x, -L["interior_half_y"] + s["pad_clearance"] + 1, L["base_height"] - s["pad_depth"])
        )
        cover = cover.union(pad)
    return cover


def _cover_build(params):
    L, c = layout(params), params["cover_design"]
    z, t = L["base_height"], params["housing"]["lid_thickness"]
    cy = (L["back_outer_y"] - L["outer_half_y"]) / 2
    stock = rounded_box(
        2 * L["outer_half_x"], L["total_depth"], t, 3, top_break=c["rim_break"], bottom_break=0.6
    ).translate((0, cy, z))
    b = Build(stock, "rounded_cover_stock")
    panel = b.pocket(
        lambda v: recessed_panel(
            v,
            "+Z",
            frame=c["frame"],
            depth=c["recess_depth"],
            radius=c["recess_radius"],
            wall=t,
            min_wall=2.0,
        ),
        "framed_cover_panel",
    )
    p = panel.plane
    chamfer = c["panel_break"]
    mouth_plane = cq.Plane(
        origin=p.origin + p.zDir * (panel.depth - chamfer), xDir=p.xDir, normal=p.zDir
    )
    mouth = rounded_box(
        panel.length + 2 * chamfer,
        panel.width + 2 * chamfer,
        4,
        panel.radius + chamfer,
        bottom_break=chamfer,
        top_break=0,
        plane=mouth_plane,
    )
    b.pocket(lambda v: v.cut(mouth), "panel_mouth_break")
    b.rib(lambda v: _cover_pads(v, params, L), "shear_locators")
    b.rib(lambda v: _cover_latches(v, params, L), "two_hooks_two_planar_release_tabs")
    # Raised lettering stays below the frame and preserves the 2 mm panel skin.
    for text, x, y, size in [
        ("DUAL TX", -5, cy, c["label_size"]),
        ("RF + TTL", 5, cy, c["label_size"] * 0.6),
    ]:
        mark = cq.Workplane("XY").text(
            text, size, c["label_depth"] + 0.1, font="Arial", combine=True
        )
        mark = mark.rotate((0, 0, 0), (0, 0, 1), 90).translate(
            (x, y, z + t - c["recess_depth"] - 0.1)
        )
        b.rib(lambda v, tool=mark: v.union(tool), "label_" + text.replace(" ", "_"))
    return b


def _create_lid_canonical(params):
    return _cover_build(params).result


def create_base(params=None):
    params = load_params() if params is None else params
    return orient_to_mounting(_create_base_canonical(params), params)


def create_lid(params=None):
    params = load_params() if params is None else params
    return orient_to_mounting(_create_lid_canonical(params), params)


def create_part(params=None):
    params = load_params() if params is None else params
    return cq.Workplane("XY").newObject([create_base(params).val(), create_lid(params).val()])


def build_stages(params=None):
    params = load_params() if params is None else params
    yield from _base_build(params).stages()
    yield from _cover_build(params).stages()


def export_all():
    params = load_params()
    version = params["version"]
    out = PART_DIR / "exports"
    out.mkdir(exist_ok=True)
    base, cover = _create_base_canonical(params), _create_lid_canonical(params)
    installed = {
        "base": orient_to_mounting(base, params),
        "cover": orient_to_mounting(cover, params),
    }
    assembly = cq.Assembly(name="dual_tx_snap_housing")
    assembly.add(installed["base"], name="base", color=cq.Color(0.19, 0.21, 0.24))
    assembly.add(installed["cover"], name="cover", color=cq.Color(0.25, 0.27, 0.30))
    assembly.export(str(out / f"{PART_DIR.name}_{version}.step"))
    # Record validity before STL tessellation mutates OCCT triangulation caches.
    summary = {
        name: {
            "valid": shape.val().isValid(),
            "solids": len(shape.solids().vals()),
            "volume_mm3": shape.val().Volume(),
        }
        for name, shape in installed.items()
    }
    if not all(row["valid"] and row["solids"] == 1 for row in summary.values()):
        raise ValueError("Base and cover must each be one valid solid before export")
    for name, part in installed.items():
        for extension in ("step", "stl"):
            cq.exporters.export(
                part,
                str(out / f"{name}_{version}.{extension}"),
                tolerance=0.05,
                angularTolerance=0.1,
            )
    # Flat print datum files avoid requiring the operator to infer rotation.
    cover_flat = cover.rotate((0, 0, 0), (1, 0, 0), 180).translate(
        (0, 0, layout(params)["base_height"] + params["housing"]["lid_thickness"])
    )
    for name, part in (("base_print", base), ("cover_print", cover_flat)):
        cq.exporters.export(
            part, str(out / f"{name}_{version}.stl"), tolerance=0.05, angularTolerance=0.1
        )
    for name in installed:
        reread = cq.importers.importStep(str(out / f"{name}_{version}.step"))
        summary[name]["step_roundtrip_valid"] = reread.val().isValid()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    export_all()
