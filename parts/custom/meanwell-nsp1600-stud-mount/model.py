"""N1 Mean Well NSP-1600 adapter; editable parametric CadQuery source, mm.

Only the custom adapter is manufacturing geometry. All 19 original PSU solids
are preserved, translated onto the adapter. Purchased hardware and main panel
are reference envelopes; no helical thread or supplier anchor rating is implied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path

import cadquery as cq

from lib.features import Build, rounded_box

HERE = Path(__file__).resolve().parent


def load_params():
    return json.loads((HERE / "params.json").read_text(encoding="utf8"))


def housing_points(p):
    return [tuple(xy) for xy in p["housing_points"]]


def stud_points(p):
    a = math.radians(p["stud_pattern_rotation_deg"])
    return [
        (
            sx * p["stud_pitch_x"] / 2 * math.cos(a)
            - sy * p["stud_pitch_y"] / 2 * math.sin(a)
            + p["stud_pattern_center_x"],
            sx * p["stud_pitch_x"] / 2 * math.sin(a)
            + sy * p["stud_pitch_y"] / 2 * math.cos(a)
            + p["stud_pattern_center_y"],
        )
        for sx in (-1, 1)
        for sy in (-1, 1)
    ]


def cyl(d, h, x=0, y=0, z=0):
    return cq.Solid.makeCylinder(d / 2, h, cq.Vector(x, y, z))


def cone(d0, d1, h, x=0, y=0, z=0):
    return cq.Solid.makeCone(d0 / 2, d1 / 2, h, cq.Vector(x, y, z))


def relief_tools(p):
    for x in p["fan_relief_centers_x"]:
        yield (
            rounded_box(
                p["fan_relief_width"],
                p["fan_relief_length"],
                p["fan_relief_depth"] + 0.01,
                p["fan_relief_radius"],
                top_break=0,
                bottom_break=0,
            )
            .val()
            .translate((x, p["fan_relief_center_y"], p["plate_thickness"] - p["fan_relief_depth"]))
        )


def _build(params=None):
    p = load_params() if params is None else params
    t, c = p["plate_thickness"], p["bore_deburr"]
    if t <= p["fan_relief_depth"] + 2 or p["countersink_angle_deg"] != 90:
        raise ValueError("Revise structural and screw-seat checks for these dimensions.")
    b = Build(
        rounded_box(
            p["plate_width"],
            p["plate_length"],
            t,
            p["corner_radius"],
            top_break=p["edge_break"],
            bottom_break=p["edge_break"],
        ).translate((0, p["plate_center_y"], 0)),
        "01_faced_stock_contour_external_edge_breaks",
    )
    for i, tool in enumerate(relief_tools(p), 1):
        b.pocket(lambda s, tool=tool: s.cut(tool), f"02_fan_frame_relief_{i}")
    for i, (x, y) in enumerate(housing_points(p), 1):
        d, mouth = p["housing_clearance_diameter"], p["countersink_diameter_reference"]
        tool = cyl(d, t + 2, x, y, -1).fuse(cone(mouth, d, (mouth - d) / 2, x, y, 0))
        tool = tool.fuse(cone(d, d + 2 * c, c, x, y, t - c))
        b.hole(lambda s, tool=tool: s.cut(tool), f"03_M3_bore_underside_90deg_seat_H{i}")
    for i, (x, y) in enumerate(stud_points(p), 1):
        d = p["stud_clearance_diameter"]
        tool = cyl(d, t + 2, x, y, -1).fuse(cone(d + 2 * c, d, c, x, y, 0))
        tool = tool.fuse(cone(d, d + 2 * c, c, x, y, t - c))
        b.hole(lambda s, tool=tool: s.cut(tool), f"04_stud_clearance_S{i}")
    return b


def create_part(params=None):
    return _build(params).result


def build_stages(params=None):
    yield from _build(params).stages()


def housing_screw(p):
    """Ideal conical-head proxy. Physical 1.7mm DIN7991 head MUST be seat-gauged.

    Nominal cone height1.5mm is not a complete or conservative real-head envelope.
    Overall screw length includes the head. No thread fit is represented.
    """
    d, hd = p["screw_diameter"], p["screw_head_diameter"]
    h, z = (hd - d) / 2, p["screw_head_recess_nominal"]
    s = cone(hd, d, h, z=z).fuse(cyl(d, p["screw_length_overall"] - h, z=z + h))
    key = (
        cq.Workplane("XY")
        .polygon(6, p["screw_hex_drive"] / math.cos(math.pi / 6))
        .extrude(0.8)
        .val()
    )
    return s.cut(key.translate((0, 0, z))).clean()


def panel_stud(p):
    """FPE WGU30 M3 L12 reference envelope only; concealed anchorage omitted."""
    return (
        cyl(
            p["stud_base_diameter_reference"],
            p["stud_base_thickness_reference"],
            z=-p["stud_base_thickness_reference"],
        )
        .fuse(cyl(p["stud_diameter"], p["stud_projection"]))
        .clean()
    )


def panel_reference(p):
    t = p["panel_reference_thickness"]
    s = (
        rounded_box(
            p["panel_reference_width"],
            p["panel_reference_length"],
            t,
            p["corner_radius"],
            top_break=p["edge_break"],
            bottom_break=p["edge_break"],
        )
        .val()
        .translate((0, p["plate_center_y"], -t))
    )
    for x, y in stud_points(p):
        s = s.cut(
            cyl(
                p["stud_cavity_diameter_reference"],
                p["stud_cavity_depth_reference"] + 0.01,
                x,
                y,
                -p["stud_cavity_depth_reference"],
            )
        )
    return s.clean()


def washer(p):
    return cyl(p["washer_od"], p["washer_thickness_nominal"]).cut(
        cyl(p["washer_id"], p["washer_thickness_nominal"])
    )


def nut(p):
    s = (
        cq.Workplane("XY")
        .polygon(6, p["nut_across_flats"] / math.cos(math.pi / 6))
        .extrude(p["nut_height_nominal"])
        .edges("#Z")
        .chamfer(0.2)
        .val()
    )
    return s.cut(cyl(p["stud_diameter"], p["nut_height_nominal"]))


def normalize(s, p):
    return s.translate(tuple(p["device_translate"]))


def load_device(source, p, work):
    if hashlib.sha256(source.read_bytes()).hexdigest() != p["input_step_sha256"]:
        raise ValueError("Original STEP changed; repeat geometry and component identity audit.")
    staged = work / "input_device.step"
    if source.resolve() != staged.resolve():
        shutil.copyfile(source, staged)
    shapes = normalize(cq.importers.importStep(str(staged)).val(), p).Solids()
    assert len(shapes) == p["device_solids"] == 19
    assert all(s.isValid() for s in shapes)
    return shapes


def components(p, shapes):
    t = p["plate_thickness"]
    items = [
        ("adapter_N1", create_part(p).val(), "plate"),
        ("FPE_PANEL_REFERENCE_ONLY", panel_reference(p), "panel"),
    ]
    items += [
        (f"device_original_solid_{i:03d}", s.translate((0, 0, t)), "device")
        for i, s in enumerate(shapes)
    ]
    for i, (x, y) in enumerate(housing_points(p), 1):
        items.append(
            (f"McMaster_91294A128_M3x8_H{i}", housing_screw(p).translate((x, y, 0)), "screw")
        )
    for i, (x, y) in enumerate(stud_points(p), 1):
        items += [
            (f"FPE_WGU30_M3_L12_REFERENCE_S{i}", panel_stud(p).translate((x, y, 0)), "stud"),
            (f"McMaster_98688A142_washer_S{i}", washer(p).translate((x, y, t)), "washer"),
            (
                f"McMaster_90576A102_locknut_S{i}",
                nut(p).translate((x, y, t + p["washer_thickness_nominal"])),
                "nut",
            ),
        ]
    return items


COLORS = {
    "plate": (0.66, 0.70, 0.75),
    "panel": (0.4, 0.44, 0.5),
    "device": (0.63, 0.65, 0.68),
    "screw": (0.12, 0.13, 0.14),
    "stud": (0.67, 0.69, 0.72),
    "washer": (0.67, 0.69, 0.72),
    "nut": (0.67, 0.69, 0.72),
}


def export_step(items, path):
    assy = cq.Assembly(name=path.stem)
    for n, s, k in items:
        assy.add(s, name=n, color=cq.Color(*COLORS[k]))
    assy.export(str(path))


def bbox(s):
    b = s.BoundingBox()
    return {a: [round(getattr(b, a + "min"), 7), round(getattr(b, a + "max"), 7)] for a in "xyz"}


def planar_files(p, work):
    import ezdxf

    def new():
        doc = ezdxf.new("R2010")
        doc.units = ezdxf.units.MM
        for name, c in [
            ("PROFILE", 7),
            ("HOUSING_DRILL", 3),
            ("STUD_DRILL", 5),
            ("CSK_REF", 1),
            ("POCKET_TOP", 2),
            ("PANEL_STUD_CENTERS", 4),
        ]:
            doc.layers.new(name, dxfattribs={"color": c})
        return doc, doc.modelspace()

    def rect(ms, w, length, r, x, y, layer):
        w, h, b = w / 2, length / 2, math.tan(math.pi / 8)
        points = [
            (-w + r, -h, 0),
            (w - r, -h, b),
            (w, -h + r, 0),
            (w, h - r, b),
            (w - r, h, 0),
            (-w + r, h, b),
            (-w, h - r, 0),
            (-w, -h + r, b),
        ]
        ms.add_lwpolyline(
            [(a + x, c + y, d) for a, c, d in points],
            format="xyb",
            close=True,
            dxfattribs={"layer": layer},
        )

    for mode, name in [
        ("drill", "profile_drill_N1.dxf"),
        ("csk", "countersinks_UNDERSIDE_N1.dxf"),
        ("pocket", "fan_reliefs_TOP_N1.dxf"),
    ]:
        doc, ms = new()
        rect(
            ms,
            p["plate_width"],
            p["plate_length"],
            p["corner_radius"],
            0,
            p["plate_center_y"],
            "PROFILE",
        )
        if mode == "pocket":
            for x in p["fan_relief_centers_x"]:
                rect(
                    ms,
                    p["fan_relief_width"],
                    p["fan_relief_length"],
                    p["fan_relief_radius"],
                    x,
                    p["fan_relief_center_y"],
                    "POCKET_TOP",
                )
        else:
            for x, y in housing_points(p):
                ms.add_circle(
                    (x, y),
                    p["housing_clearance_diameter"] / 2,
                    dxfattribs={"layer": "HOUSING_DRILL"},
                )
                if mode == "csk":
                    ms.add_circle(
                        (x, y),
                        p["countersink_diameter_reference"] / 2,
                        dxfattribs={"layer": "CSK_REF"},
                    )
            for x, y in stud_points(p):
                ms.add_circle(
                    (x, y), p["stud_clearance_diameter"] / 2, dxfattribs={"layer": "STUD_DRILL"}
                )
        doc.saveas(work / name)
    doc, ms = new()
    for x, y in stud_points(p):
        ms.add_point((x, y), dxfattribs={"layer": "PANEL_STUD_CENTERS"})
    doc.saveas(work / "FPE_stud_pattern_REFERENCE_N1.dxf")
    with (work / "FPE_stud_coordinates_N1.csv").open("w", newline="", encoding="utf8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "x_mm", "y_mm", "x_from_B_mm", "y_from_C_mm", "feature"])
        for i, (x, y) in enumerate(stud_points(p), 1):
            writer.writerow(
                [
                    f"S{i}",
                    x,
                    y,
                    x + p["plate_width"] / 2,
                    y - (p["plate_center_y"] - p["plate_length"] / 2),
                    "FPE WGU30 M3 L12 reverse zero-offset; REFERENCE placement only",
                ]
            )


def export_all(p, source, output, work):
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    shapes = load_device(source, p, work)
    items = components(p, shapes)
    plate = items[0][1]
    cq.exporters.export(plate, str(work / "plate_N1.step"))
    cq.exporters.export(
        plate, str(work / "plate_N1_preview_ONLY.stl"), tolerance=0.03, angularTolerance=0.1
    )
    export_step(items, work / "assembled_device_mount_N1.step")
    export_step(
        [i for i in items if i[2] in {"plate", "device", "screw"}], work / "device_adapter_N1.step"
    )
    export_step(
        [i for i in items if i[2] in {"plate", "screw", "stud", "washer", "nut"}],
        work / "mount_hardware_N1.step",
    )
    export_step(
        [i for i in items if i[2] in {"panel", "stud"}], work / "FPE_interface_REFERENCE_ONLY.step"
    )
    planar_files(p, work)
    meta = {
        "revision": p["revision"],
        "units": "mm",
        "plate_volume_mm3": plate.Volume(),
        "plate_mass_kg_at_2700_kg_m3": plate.Volume() * 2.7e-6,
        "component_count": len(items),
        "source_device_solids": 19,
        "installed_device_solids": 19,
        "assembly_bbox_mm": bbox(cq.Compound.makeCompound([s for _, s, _ in items])),
        "components": [
            dict(name=n, kind=k, valid=s.isValid(), solids=len(s.Solids()), bbox_mm=bbox(s))
            for n, s, k in items
        ],
        "hardware_geometry": (
            "Simplified ideal catalog proxies. No real thread, seat or FPE anchor validation."
        ),
        "datums": "A=plate underside Z0, B=left X-62.5, C=fan end Y-300.6. PSU bottom Z5 nominal.",
    }
    (work / "cad_build_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf8")
    for path in work.iterdir():
        if path.is_file() and path.name != "input_device.step":
            shutil.copyfile(path, output / path.name)
    print(
        f"N1: {len(items)} distinct solids, plate {plate.Volume():.3f} mm3, "
        f"{plate.Volume() * 2.7e-6:.4f} kg",
        flush=True,
    )
    return shapes, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=HERE / "references/input_device.step")
    ap.add_argument("--out", type=Path, default=HERE / "exports")
    ap.add_argument("--work-dir", type=Path)
    args = ap.parse_args()
    if args.work_dir:
        export_all(load_params(), args.source, args.out, args.work_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="nsp1600_n1_") as td:
            export_all(load_params(), args.source, args.out, Path(td))


if __name__ == "__main__":
    main()
