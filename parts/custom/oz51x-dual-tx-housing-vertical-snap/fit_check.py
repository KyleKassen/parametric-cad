"""Independent dimensional and service-motion checks for the snap housing.

Run from the repository: python parts/custom/oz51x-dual-tx-housing-vertical-snap/fit_check.py
Writes references/fit_report.json; does not silently treat failed CAD booleans
as clearance. This checks rigid geometry, not fatigue or elastic snap force.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

PART_DIR = Path(__file__).resolve().parent
ROOT = PART_DIR.parents[2]
sys.path.insert(0, str(ROOT))

import cadquery as cq  # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape  # noqa: E402

from lib.housing import interference  # noqa: E402


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def box(w, d, h, center):
    return cq.Workplane("XY").box(w, d, h).translate(center)


def cylinder(radius, point, direction, length):
    return cq.Workplane("XY").newObject(
        [cq.Solid.makeCylinder(radius, length, cq.Vector(*point), cq.Vector(*direction))]
    )


def distance(first, second):
    """Minimum distance between actual BReps; failure is never called clearance."""
    measure = BRepExtrema_DistShapeShape(first.val().wrapped, second.val().wrapped)
    measure.Perform()
    if not measure.IsDone():
        raise RuntimeError("BRep minimum-distance calculation failed")
    return measure.Value()


def main() -> int:
    model = load_module(PART_DIR / "model.py", "snap_fit_model")
    params = model.load_params()
    layout = model.layout(params)
    housing = params["housing"]
    snap = params["snap"]
    rows = []

    def result(name, passed, **details):
        rows.append({"check": name, "passed": bool(passed), **details})
        print(f"{'PASS' if passed else 'FAIL'} {name}", details if details else "")

    def clear(name, first, second, threshold=0.05):
        volume = interference(first, second)
        result(name, volume < threshold, overlap_mm3=round(volume, 6))
        return volume

    def canonical(installed):
        return installed.translate(
            (layout["envelope_width"] / 2.0, 0, -layout["outer_half_x"])
        ).rotate((0, 0, 0), (0, 1, 0), -90)

    supplied_step = os.environ.get("EVAL_STEP_PATH")
    if supplied_step:
        assembly_solids = cq.importers.importStep(supplied_step).solids().vals()
        if len(assembly_solids) != 2:
            raise ValueError(
                f"Expected two printable solids in EVAL_STEP_PATH, got {len(assembly_solids)}"
            )
        base_solid, cover_solid = sorted(
            assembly_solids, key=lambda solid: solid.Volume(), reverse=True
        )
        base = canonical(cq.Workplane("XY").newObject([base_solid]))
        cover = canonical(cq.Workplane("XY").newObject([cover_solid]))
        artifact_source = str(Path(supplied_step).resolve())
    else:
        version = params["version"]
        base_path = PART_DIR / "exports" / f"base_{version}.step"
        cover_path = PART_DIR / "exports" / f"cover_{version}.step"
        base = canonical(cq.importers.importStep(str(base_path)))
        cover = canonical(cq.importers.importStep(str(cover_path)))
        artifact_source = f"exports/{base_path.name} and exports/{cover_path.name}"

    for name, shape in (("base", base), ("cover", cover)):
        solids = shape.solids().vals()
        result(
            f"{name}: valid single solid",
            len(solids) == 1 and all(s.isValid() for s in solids),
            solid_count=len(solids),
            volume_mm3=round(shape.val().Volume(), 3),
        )
    clear("cover fully seated against base", base, cover)

    # Both bays use the available OZ510 STEP as a mechanical reference. It is
    # not an exact STEP of either user's OZ516 RF or OZ510TTL unit.
    family_fit = load_module(
        PART_DIR.parent / "oz510-dual-housing" / "fit_check.py", "canonical_fit"
    )
    hardware = []
    for bay, center in zip(layout["bays"], layout["bay_cx"]):
        module = family_fit.place_module(
            ROOT / "parts" / "vendor" / bay["step"], center, layout["plate_bottom_z"]
        )
        hardware.append((f"OZ510 reference STEP in {bay['label']} bay", module))

    adapter_model = load_module(
        ROOT / "parts/vendor/sc-apc-simplex-adapter/model.py", "fit_adapter"
    )
    connector_model = load_module(ROOT / "parts/vendor/sc-apc-connector/model.py", "fit_connector")
    adapter_dimensions = adapter_model.load_params()["dimensions"]
    adapter = adapter_model.create_part()
    connector = connector_model.create_part()
    recess = layout["production"]["rear_panel"]["flange_recess_depth"]
    for index, ax in enumerate(layout["adapter_x"], 1):
        # Seat the flange in the actual recess, not on the original outer face.
        installed_adapter = family_fit.place_adapter(
            adapter, adapter_dimensions, layout, ax
        ).translate((0, -recess, 0))
        installed_connector = family_fit.place_connector(
            connector, adapter_dimensions, layout, ax
        ).translate((0, -recess, 0))
        hardware.extend(
            [
                (f"SC/APC adapter {index}", canonical(installed_adapter)),
                (f"mated SC/APC connector {index}", canonical(installed_connector)),
            ]
        )

    for name, shape in hardware:
        clear(f"{name}: base clearance", base, shape)
        clear(f"{name}: cover clearance", cover, shape)

    # Independent functional probes span the whole rear connector and both
    # jackscrews, and the original four plate/standoff slots.
    pc = params["panel_connector"]
    rear = box(
        pc["rear_keepout_w"],
        pc["rear_keepout_depth"],
        pc["rear_keepout_h"],
        (
            pc["x"],
            layout["plenum_y1"] - pc["rear_keepout_depth"] / 2.0,
            layout["panel_connector_z"],
        ),
    )
    clear("DE-9 rear body/harness reservation", base, rear)
    clear("DE-9 rear body/harness to cover", cover, rear)
    hardware.append(("DE-9 rear body/harness reservation", rear))
    for sign in (-1, 1):
        px = pc["x"] + sign * pc["screw_spacing"] / 2.0
        nut = cylinder(
            6.35 / 2.0, (px, layout["plenum_y1"] - 3.0, layout["panel_connector_z"]), (0, 1, 0), 3.0
        )
        clear(f"DE-9 jackscrew {sign:+d}: interior nut access", base, nut)

    flange = layout["production"]["mount_flange"]
    # These are the user's retained interface, independent of mutable inputs.
    slot_width, slot_length, slot_x = 4.5, 9.0, 53.1
    slot_y = (-22.0, 74.0)
    result(
        "plate/standoff interface: preserved 4.5 x 9 slots and original centers",
        abs(flange["slot_width"] - slot_width) < 1e-8
        and abs(flange["slot_length"] - slot_length) < 1e-8
        and tuple(flange["slot_y"]) == slot_y
        and abs(layout["outer_half_x"] + flange["extension"] / 2 + 1 - slot_x) < 1e-8,
        width_mm=slot_width,
        length_mm=slot_length,
        centers_xy_mm=[[side * slot_x, y] for side in (-1, 1) for y in slot_y],
    )
    # Representative M3 large washer; the test does not approve tightening
    # torque or every position allowed by the deliberately wider slot.
    washer_od, washer_id, washer_t = 9.0, 3.2, 0.8
    for sign in (-1, 1):
        for sy in slot_y:
            px = sign * slot_x
            slot = (
                cq.Workplane("XY")
                .center(px, sy)
                .slot2D(slot_length - 0.04, slot_width - 0.04, 90)
                .extrude(flange["thickness"] + 2.0)
                .translate((0, 0, -1.0))
            )
            clear(f"plate/standoff slot x={px:g}, y={sy:g}", base, slot)
            # Four material witnesses outside the expected boundary prevent
            # enlarged or missing slot walls from passing the empty gauge.
            witnesses = []
            for side in (-1, 1):
                witnesses.append(box(0.1, 2.0, 0.5, (px + side * 2.32, sy, 1.5)))
                witnesses.append(box(0.2, 0.1, 0.5, (px, sy + side * 4.57, 1.5)))
            retained = [interference(base, v) / v.val().Volume() for v in witnesses]
            result(
                f"plate/standoff slot x={px:g}, y={sy:g}: boundary material retained",
                min(retained) > 0.99,
                minimum_material_fraction=round(min(retained), 6),
            )
            washer = (
                cq.Workplane("XY")
                .circle(washer_od / 2)
                .circle(washer_id / 2)
                .extrude(washer_t)
                .translate((px, sy, flange["thickness"]))
            )
            clear(f"M3 washer x={px:g}, y={sy:g}: seated hardware clearance", base, washer)
            bearing = (
                cq.Workplane("XY")
                .circle(washer_od / 2)
                .circle(washer_id / 2)
                .extrude(0.1)
                .translate((px, sy, flange["thickness"] - 0.11))
            )
            fractions = []
            for side in (-1, 1):
                half = box(washer_od / 2, washer_od, 1, (px + side * washer_od / 4, sy, 2.9))
                fractions.append(
                    interference(base, bearing.intersect(half)) / bearing.val().Volume()
                )
            result(
                f"M3 washer x={px:g}, y={sy:g}: bearing on both sides of slot",
                min(fractions) >= 0.2,
                washer_od_id_thickness_mm=[washer_od, washer_id, washer_t],
                fraction_of_total_annular_area_per_side=[round(v, 6) for v in fractions],
                total_bearing_area_mm2=round(sum(fractions) * bearing.val().Volume() / 0.1, 3),
            )
    minimum_radius = params["fiber_bay"]["min_bend_radius"]
    result(
        "fiber spool: retained 15 mm minimum bend-radius design",
        abs(minimum_radius - 15.0) < 1e-8
        and abs(params["fiber_bay"]["spool_dia"] - 30.0) < 1e-8,
        minimum_radius_mm=minimum_radius,
        drum_diameter_mm=params["fiber_bay"]["spool_dia"],
    )
    contact_band = (
        cq.Workplane("XY")
        .circle(minimum_radius - 0.1)
        .circle(minimum_radius - 0.3)
        .extrude(layout["base_height"] - housing["floor"] - 3.0)
        .translate((0, layout["spool_y"], housing["floor"] + 1.0))
    )
    retained_contact = interference(base, contact_band) / contact_band.val().Volume()
    result(
        "fiber spool: continuous contact surface at required radius",
        retained_contact > 0.99,
        minimum_radius_mm=minimum_radius,
        material_fraction=round(retained_contact, 6),
    )
    wrap = (
        cq.Workplane("XY")
        .circle(minimum_radius + 1.2)
        .circle(minimum_radius + 0.3)
        .extrude(layout["base_height"] - housing["floor"] - 3.0)
        .translate((0, layout["spool_y"], housing["floor"] + 1.0))
    )
    clear("fiber wrap space outside spool", base, wrap)
    clear("fiber wrap space beneath cover", cover, wrap)

    # Measure the exported retention flange and partition, then put a solid
    # service probe across their narrowest gap, including the flange height.
    spool = base.intersect(cylinder(
        17.0, (0, layout["spool_y"], housing["floor"] + 0.2),
        (0, 0, 1), layout["base_height"] - housing["floor"],
    ))
    partition = base.intersect(box(
        4.0, housing["wall"] + 0.4, layout["base_height"] - housing["floor"] - 1.0,
        (0, layout["plenum_y0"] - housing["wall"] / 2,
         (layout["base_height"] + housing["floor"]) / 2),
    ))
    spool_bounds = spool.val().BoundingBox()
    partition_back = partition.val().BoundingBox().ymax
    measured_gap = spool_bounds.ymin - partition_back
    required_gap = max(8.0, params["fiber_service"]["min_flange_partition_gap"])
    result(
        "fiber service: exported flange-to-partition gap at least 8 mm",
        measured_gap >= required_gap - 1e-6,
        minimum_gap_mm=round(measured_gap, 6),
        partition_face_y_mm=round(partition_back, 6),
        flange_edge_y_mm=round(spool_bounds.ymin, 6),
    )
    service_probe = box(
        10.0, required_gap - 0.1, layout["base_height"] - housing["floor"] + 1.0,
        (0, partition_back + required_gap / 2,
         (layout["base_height"] + housing["floor"]) / 2 + 0.6),
    )
    clear("fiber service: open access through partition/flange gap", base, service_probe)

    planar_connector_gap = layout["plenum_y1"] - pc["rear_keepout_depth"] - spool_bounds.ymax
    actual_connector_gap = distance(spool, rear)
    required_connector_gap = max(3.0, params["fiber_service"]["min_flange_connector_gap"])
    result(
        "fiber service: spool clears DE-9 rear reservation by at least 3 mm",
        planar_connector_gap >= required_connector_gap - 1e-6
        and actual_connector_gap >= required_connector_gap - 1e-6,
        full_flange_envelope_gap_mm=round(planar_connector_gap, 6),
        actual_brep_gap_mm=round(actual_connector_gap, 6),
        fiber_band_gap_mm=round(distance(wrap, rear), 6),
    )
    for name, shape in hardware:
        if name.startswith(("SC/APC adapter", "mated SC/APC connector")):
            gap = distance(spool, shape)
            clear(f"{name}: fiber wrap separation", wrap, shape)
            result(
                f"{name}: relocated spool clearance",
                gap >= 3.0,
                minimum_brep_gap_mm=round(gap, 6),
            )

    # Six mm of routing space is available on the partition-facing half.
    # Do not imply that this width continues behind the DE-9 on the other half.
    routing_width = max(6.0, params["fiber_service"]["routing_channel_width"])
    routing = (
        cq.Workplane("XY")
        .circle(minimum_radius + 0.2 + routing_width)
        .circle(minimum_radius + 0.2)
        .extrude(layout["base_height"] - housing["floor"] - 3.0)
        .translate((0, layout["spool_y"], housing["floor"] + 1.0))
    )
    routing = routing.intersect(box(
        60, 30, layout["base_height"] + 4,
        (0, layout["spool_y"] - 15, layout["base_height"] / 2),
    ))
    routing_overlaps = [("base", interference(base, routing))]
    routing_overlaps += [(name, interference(shape, routing)) for name, shape in hardware]
    worst_name, worst_overlap = max(routing_overlaps, key=lambda pair: pair[1])
    result(
        "fiber service: 6 mm routing channel on partition-facing semicircle",
        worst_overlap < 0.05,
        channel_width_mm=routing_width,
        max_overlap_mm3=round(worst_overlap, 6),
        worst_against=worst_name,
    )
    hardware.append(("fiber wrap space", wrap))

    # Check the rigid portion of the cover through its actual service motion.
    # Flexible hooks are excluded only from the rigid closing test; their
    # seated fit and conservative swept inward-release volume are checked
    # separately. There is no finite-element or fatigue model here.
    rigid_cover = cover
    for tip_y in snap["tip_y"]:
        rigid_cover = rigid_cover.cut(model.snap_clearance_tool(params, tip_y))
    pivot_start = (-layout["outer_half_x"], 0, layout["base_height"])
    pivot_end = (-layout["outer_half_x"], 1, layout["base_height"])
    sweep_max = 0.0
    sweep_worst = None
    for angle in range(0, 31, 2):
        tilted = rigid_cover.rotate(pivot_start, pivot_end, -angle)
        for name, part in [("base", base)] + hardware:
            volume = interference(part, tilted)
            if volume > sweep_max:
                sweep_max, sweep_worst = volume, {"angle_degrees": angle, "against": name}
    result(
        "rigid hook closing sweep: 30 to 0 degrees",
        sweep_max < 0.05,
        max_overlap_mm3=round(sweep_max, 6),
        worst_pose=sweep_worst,
    )

    insertion = rigid_cover.rotate(pivot_start, pivot_end, -30)
    insertion_max = 0.0
    for lift in range(0, 11):
        raised = insertion.translate((0, 0, lift))
        insertion_max = max(insertion_max, interference(base, raised))
    result(
        "angled rigid-hook insertion: 10 mm lowering at 30 degrees",
        insertion_max < 0.05,
        max_overlap_mm3=round(insertion_max, 6),
    )

    for tip_y in snap["tip_y"]:
        nominal_hook = model.latch_hook(params, tip_y)
        hook = cover.intersect(nominal_hook)
        hook_fraction = hook.val().Volume() / nominal_hook.val().Volume()
        result(
            f"latch y={tip_y:g}: exported downleg/hook present",
            hook_fraction > 0.99,
            material_fraction=round(hook_fraction, 6),
        )
        hook_top = layout["base_height"] - snap["hook_top_below_seam"]
        contact = box(
            0.6,
            snap["hook_width"] - 1.0,
            0.35,
            (layout["interior_half_x"] + 0.35, tip_y, hook_top - 0.275),
        )
        contact_volume = interference(cover, contact)
        result(
            f"latch y={tip_y:g}: outward retaining shoulder",
            contact_volume > 0.9,
            retained_material_mm3=round(contact_volume, 6),
        )
        roof = hook_top + snap["roof_clearance"]
        keeper = box(
            0.6,
            snap["hook_width"] - 1.0,
            0.8,
            (layout["interior_half_x"] + 0.35, tip_y, roof + 0.5),
        )
        keeper_volume = interference(base, keeper)
        result(
            f"latch y={tip_y:g}: solid keeper above catch",
            keeper_volume > 2.3,
            retained_material_mm3=round(keeper_volume, 6),
        )
        hook_max = 0.0
        for index in range(14):
            stroke = snap["release_travel"] * index / 13
            released = hook.translate((-stroke, 0, 0))
            hook_max = max(hook_max, interference(base, released))
            for _, part in hardware:
                hook_max = max(hook_max, interference(part, released))
        result(
            f"latch y={tip_y:g}: inward release stroke",
            hook_max < 0.05,
            stroke_mm=snap["release_travel"],
            max_overlap_mm3=round(hook_max, 6),
        )

        # The distal pad and hook move together. Check their rigid translated
        # envelope against the surrounding fixed cover; this does not assert
        # a uniformly translated or elastically solved whole cantilever.
        tip_inner = snap["beam_outer_x"] - snap["beam_thickness"]
        tip_clip = box(
            layout["outer_half_x"] - tip_inner,
            snap["hook_width"],
            snap["hook_depth"] + housing["lid_thickness"] + 2,
            (
                (tip_inner + layout["outer_half_x"]) / 2,
                tip_y,
                layout["base_height"] + (housing["lid_thickness"] - snap["hook_depth"]) / 2,
            ),
        )
        tip = cover.intersect(tip_clip)
        static_cover = cover.cut(model.snap_clearance_tool(params, tip_y))
        tip_release = tip.translate((-snap["release_travel"], 0, 0))
        clear(
            f"latch y={tip_y:g}: finger pad clears fixed cover at release",
            static_cover,
            tip_release,
        )
        overtravel = tip.translate((-(snap["slot"] + 0.2), 0, 0))
        stop_volume = interference(static_cover, overtravel)
        result(
            f"latch y={tip_y:g}: geometric stop beyond nominal slot travel",
            stop_volume > 0.5,
            tested_travel_mm=snap["slot"] + 0.2,
            stop_overlap_mm3=round(stop_volume, 6),
        )

    report = {
        "part": PART_DIR.name,
        "version": params["version"],
        "verified_artifact": artifact_source,
        "all_passed": all(row["passed"] for row in rows),
        "limitations": [
            "Geometry checks do not establish elastic force, fatigue life, "
            "thermal performance, or environmental rating.",
            "Both actual modules (OZ516 RF and OZ510TTL) are represented by the available "
            "OZ510 reference STEP; neither exact module fit is certified.",
            "Verify both actual modules' mounting, fiber exits, headers and pinouts "
            "before manufacture.",
            "SC/APC models are datasheet-derived stand-ins; confirm the ordered adapter "
            "and pigtail against the fit coupon.",
            "Fiber routing checks use the existing 0.9 mm pigtail/short-boot references "
            "and do not validate a complete routed fiber curve or full fingertip access.",
            "M3 washer checks apply at slot centers with a representative 9 x 3.2 x 0.8 mm "
            "flat washer; they do not establish load capacity or assembly torque.",
            "The DE-9 reserved envelope is not the exact purchased connector or a wiring approval.",
            "Closing sweep removes the flexible latch regions and checks their release stroke "
            "separately; it does not simulate elastic deformation.",
        ],
        "checks": rows,
    }
    out = PART_DIR / "references"
    out.mkdir(exist_ok=True)
    (out / "fit_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
