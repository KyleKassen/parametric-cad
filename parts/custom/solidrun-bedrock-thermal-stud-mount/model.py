"""T1 SolidRun thermal stud plate, millimetres; reproducible parametric CadQuery source.

The custom part is exact nominal geometry. Purchased hardware is simplified
catalog envelope geometry without helical threads, not a supplier CAD model.
Input contains alternative products. Tile plus one clipped fin bank is a derived
spatial reference, not vendor-configured hardware or a verified thermal joint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path

import cadquery as cq

from lib.features import Build, rounded_box

HERE = Path(__file__).resolve().parent


def load_params() -> dict:
    return json.loads((HERE / "params.json").read_text(encoding="utf-8"))


def housing_points(p: dict) -> list[tuple[float, float]]:
    return [tuple(xy) for xy in p["housing_points"]]


def thermal_field(p: dict, side: str, include_vents: bool = True) -> cq.Shape:
    """Exact nominal compound pocket volume; mechanical lands stay at datum."""
    depth = p["thermal_pocket_depth"]
    field = rounded_box(
        p["thermal_field_width"],
        p["thermal_field_length"],
        depth,
        p["thermal_field_corner_radius"],
        top_break=0,
        bottom_break=0,
    ).val()
    d = (
        p["tile_contact_land_diameter"]
        if side == "top"
        else p["underside_countersink_land_diameter"]
    )
    for x, y in housing_points(p):
        field = field.cut(cyl(d, depth + 2, x, y, -1))
    if include_vents:
        x0, x1 = p["thermal_vent_start_x"], p["thermal_vent_end_x"]
        for y in p["thermal_vent_y_positions"]:
            vent = (
                rounded_box(
                    x1 - x0, p["thermal_vent_width"], depth, 0.25, top_break=0, bottom_break=0
                )
                .val()
                .translate(((x1 + x0) / 2, y, 0))
            )
            field = field.fuse(vent)
    if side == "top":
        field = field.translate((0, 0, p["plate_thickness"] - depth))
    if include_vents:
        stock = rounded_box(
            p["plate_width"],
            p["plate_length"],
            p["plate_thickness"],
            p["corner_radius"],
            top_break=p["edge_break"],
            bottom_break=p["edge_break"],
        ).val()
        field = field.intersect(stock)
    return field.clean()


def stud_points(p: dict) -> list[tuple[float, float]]:
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


def cyl(d: float, h: float, x: float = 0, y: float = 0, z: float = 0) -> cq.Solid:
    return cq.Solid.makeCylinder(d / 2, h, cq.Vector(x, y, z))


def cone(d0: float, d1: float, h: float, x: float, y: float, z: float) -> cq.Solid:
    return cq.Solid.makeCone(d0 / 2, d1 / 2, h, cq.Vector(x, y, z))


def _build(params: dict | None = None) -> Build:
    p = load_params() if params is None else params
    t, c = p["plate_thickness"], p["bore_deburr"]
    if t <= 2.5 or p["countersink_angle_deg"] != 90:
        raise ValueError("Revise the engineering and screw-seat check for this thickness/angle.")
    b = Build(
        rounded_box(
            p["plate_width"],
            p["plate_length"],
            t,
            p["corner_radius"],
            top_break=p["edge_break"],
            bottom_break=p["edge_break"],
        ),
        "01_faced_contoured_edge_broken_stock",
    )
    for side in ("bottom", "top"):
        tool = thermal_field(p, side)
        b.pocket(lambda s, tool=tool: s.cut(tool), f"02_{side}_thermal_compound_pocket_hard_lands")
    for i, (x, y) in enumerate(housing_points(p), 1):
        d, mouth = p["housing_clearance_diameter"], p["countersink_diameter_reference"]
        depth = (mouth - d) / 2
        tool = cyl(d, t + 2, x, y, -1)
        # Controlled underside seat; no arbitrary late edge treatment on this rim.
        tool = tool.fuse(cone(mouth, d, depth, x, y, 0))
        tool = tool.fuse(cone(d, d + 2 * c, c, x, y, t - c))
        b.hole(lambda s, tool=tool: s.cut(tool), f"02_housing_bore_and_90deg_seat_{i}")
    for i, (x, y) in enumerate(stud_points(p), 1):
        d = p["stud_clearance_diameter"]
        tool = cyl(d, t + 2, x, y, -1)
        tool = tool.fuse(cone(d + 2 * c, d, c, x, y, 0))
        tool = tool.fuse(cone(d, d + 2 * c, c, x, y, t - c))
        b.hole(lambda s, tool=tool: s.cut(tool), f"03_panel_stud_clearance_{i}")
    return b


def create_part(params: dict | None = None) -> cq.Workplane:
    return _build(params).result


def build_stages(params: dict | None = None):
    yield from _build(params).stages()


def housing_screw(p: dict) -> cq.Shape:
    """Ideal conical head proxy; actual DIN7991 seat must be gauged.

    Catalog 2.3 mm head-height is retained in params; the nominal 2.0 mm cone
    is not a complete or conservative representation of the real head.
    The nominal cone seat and overall 8 mm length govern this reference envelope.
    """
    d, hd = p["screw_diameter"], p["screw_head_diameter"]
    z, length = p["screw_head_recess_nominal"], p["screw_length_overall"]
    h = (hd - d) / 2
    s = cone(hd, d, h, 0, 0, z).fuse(cyl(d, length - h, z=z + h))
    key = (
        cq.Workplane("XY")
        .polygon(6, p["screw_hex_drive"] / math.cos(math.pi / 6))
        .extrude(0.8)
        .val()
    )
    return s.cut(key.translate((0, 0, z))).clean()


def panel_stud(p: dict) -> cq.Shape:
    """FPE catalog envelope; anchoring thread/adhesive not modeled or rated."""
    return (
        cyl(
            p["stud_base_diameter_reference"],
            p["stud_base_thickness_reference"],
            z=-p["stud_base_thickness_reference"],
        )
        .fuse(cyl(p["stud_diameter"], p["stud_projection"]))
        .clean()
    )


def panel_reference(p: dict) -> cq.Shape:
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
        .translate((0, 0, -t))
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


def washer(p: dict) -> cq.Shape:
    return cyl(p["washer_od"], p["washer_thickness_nominal"]).cut(
        cyl(p["washer_id"], p["washer_thickness_nominal"])
    )


def nut(p: dict) -> cq.Shape:
    s = (
        cq.Workplane("XY")
        .polygon(6, p["nut_across_flats"] / math.cos(math.pi / 6))
        .extrude(p["nut_height_nominal"])
    )
    s = s.edges("#Z").chamfer(0.2).val()
    return s.cut(cyl(p["stud_diameter"], p["nut_height_nominal"]))


def normalize(s: cq.Shape, p: dict) -> cq.Shape:
    return s.rotate(
        (0, 0, 0), tuple(p["device_rotate_axis"]), p["device_rotate_angle_deg"]
    ).translate(tuple(p["device_translate"]))


def load_device(source: Path, p: dict, work: Path) -> list[cq.Shape]:
    if hashlib.sha256(source.read_bytes()).hexdigest() != p["input_step_sha256"]:
        raise ValueError(
            "Changed source: repeat the component identity audit before using indices."
        )
    staged = work / "input_device.step"
    if source.resolve() != staged.resolve():
        shutil.copyfile(source, staged)
    originals = cq.importers.importStep(str(staged)).val().Solids()
    assert len(originals) == 22
    shapes = [normalize(s, p) for s in originals]
    tile = shapes[p["device_tile_index_zero_based"]]
    assert abs(tile.BoundingBox().zmin) < 1e-5 and abs(tile.BoundingBox().zmax - 29) < 1e-5
    return shapes


def derived_device(p: dict, shapes: list[cq.Shape]) -> list[tuple[str, cq.Shape, str]]:
    z0, z1 = p["device_fin_split_normalized_z"], p["device_fin_bank_top_normalized_z"]
    clip = (
        cq.Workplane("XY")
        .box(300, 300, z1 - z0, centered=(True, True, False))
        .translate((0, 0, z0))
        .val()
    )
    bank = shapes[p["device_60w_index_zero_based"]].intersect(clip)
    assert bank.isValid() and len(bank.Solids()) == 1
    return [
        ("Tile_SOURCE", shapes[p["device_tile_index_zero_based"]], "device"),
        ("ONE_60W_BANK_CLIPPED_REFERENCE_NOT_VENDOR_HYBRID", bank, "device"),
    ] + [
        (f"aux_SOURCE_{i:02d}", shapes[i], "device")
        for i in p["device_auxiliary_indices_zero_based"]
    ]


def components(p: dict, shapes: list[cq.Shape]) -> list[tuple[str, cq.Shape, str]]:
    t = p["plate_thickness"]
    items = [
        ("adapter_T1", create_part(p).val(), "plate"),
        ("FPE_PANEL_REFERENCE_ONLY", panel_reference(p), "panel"),
    ]
    items += [(n, s.translate((0, 0, t)), k) for n, s, k in derived_device(p, shapes)]
    items += [
        ("Dow340_top_NOMINAL_FILLED_POCKET", thermal_field(p, "top"), "tim_top"),
        ("Dow340_bottom_NOMINAL_FILLED_POCKET", thermal_field(p, "bottom"), "tim_bottom"),
    ]
    for i, (x, y) in enumerate(housing_points(p), 1):
        items.append(
            (f"McMaster_91294A188_M4x8_{i}", housing_screw(p).translate((x, y, 0)), "screw")
        )
    for i, (x, y) in enumerate(stud_points(p), 1):
        items += [
            (f"FPE_WGU30_M3_L12_REFERENCE_{i}", panel_stud(p).translate((x, y, 0)), "stud"),
            (f"McMaster_98688A142_washer_{i}", washer(p).translate((x, y, t)), "washer"),
            (
                f"McMaster_90576A102_locknut_{i}",
                nut(p).translate((x, y, t + p["washer_thickness_nominal"])),
                "nut",
            ),
        ]
    return items


COLORS = {
    "tim_top": (0.16, 0.55, 0.65),
    "tim_bottom": (0.16, 0.55, 0.65),
    "plate": (0.68, 0.71, 0.75),
    "panel": (0.42, 0.46, 0.52),
    "device": (0.25, 0.27, 0.31),
    "screw": (0.16, 0.17, 0.18),
    "stud": (0.66, 0.68, 0.7),
    "washer": (0.66, 0.68, 0.7),
    "nut": (0.66, 0.68, 0.7),
}


def export_step(items: list[tuple[str, cq.Shape, str]], path: Path) -> None:
    assy = cq.Assembly(name=path.stem)
    for name, s, kind in items:
        assy.add(s, name=name, color=cq.Color(*COLORS[kind]))
    assy.export(str(path))


def bbox(s: cq.Shape) -> dict:
    b = s.BoundingBox()
    return {a: [round(getattr(b, a + "min"), 7), round(getattr(b, a + "max"), 7)] for a in "xyz"}


def planar_files(p: dict, work: Path) -> None:
    """Manufacturing planar vectors, in mm; no bend development is needed."""
    import csv

    import ezdxf

    def outline(ms):
        w, half_length, r = p["plate_width"] / 2, p["plate_length"] / 2, p["corner_radius"]
        bulge = math.tan(math.pi / 8)
        ms.add_lwpolyline(
            [
                (-w + r, -half_length, 0),
                (w - r, -half_length, bulge),
                (w, -half_length + r, 0),
                (w, half_length - r, bulge),
                (w - r, half_length, 0),
                (-w + r, half_length, bulge),
                (-w, half_length - r, 0),
                (-w, -half_length + r, bulge),
            ],
            format="xyb",
            close=True,
            dxfattribs={"layer": "PROFILE"},
        )

    def new():
        doc = ezdxf.new("R2010")
        doc.units = ezdxf.units.MM
        for n, c in [
            ("PROFILE", 7),
            ("HOUSING_DRILL", 3),
            ("STUD_DRILL", 5),
            ("CSK_REF", 1),
            ("PANEL_STUD_CENTERS", 4),
        ]:
            doc.layers.new(n, dxfattribs={"color": c})
        return doc, doc.modelspace()

    for under in (False, True):
        doc, ms = new()
        outline(ms)
        for x, y in housing_points(p):
            ms.add_circle(
                (x, y), p["housing_clearance_diameter"] / 2, dxfattribs={"layer": "HOUSING_DRILL"}
            )
            if under:
                ms.add_circle(
                    (x, y), p["countersink_diameter_reference"] / 2, dxfattribs={"layer": "CSK_REF"}
                )
        for x, y in stud_points(p):
            ms.add_circle(
                (x, y), p["stud_clearance_diameter"] / 2, dxfattribs={"layer": "STUD_DRILL"}
            )
        doc.saveas(work / ("plate_underside_machining_mm.dxf" if under else "plate_profile_mm.dxf"))
    doc, ms = new()
    for x, y in stud_points(p):
        ms.add_point((x, y), dxfattribs={"layer": "PANEL_STUD_CENTERS"})
        # A circle is a LOCATION MARKER, not a hole instruction for the main panel.
        ms.add_circle((x, y), 1.5, dxfattribs={"layer": "PANEL_STUD_CENTERS"})
    doc.saveas(work / "FPE_stud_pattern_mm.dxf")
    with (work / "FPE_stud_coordinates_mm.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "x_from_adapter_center_mm",
                "y_from_adapter_center_mm",
                "x_from_B_mm",
                "y_from_C_mm",
                "feature",
            ]
        )
        for i, (x, y) in enumerate(stud_points(p), 1):
            w.writerow(
                [
                    i,
                    x,
                    y,
                    x + p["plate_width"] / 2,
                    y + p["plate_length"] / 2,
                    "FPE WGU30 M3 load stud L12 reverse side zero offset; reference placement",
                ]
            )


def export_all(p: dict, source: Path, output: Path, work: Path) -> tuple:
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    print("Importing original device and building T1...", flush=True)
    shapes = load_device(source, p, work)
    items = components(p, shapes)
    plate = items[0][1]
    cq.exporters.export(plate, str(work / "plate_T1.step"))
    cq.exporters.export(
        plate, str(work / "plate_T1_preview.stl"), tolerance=0.03, angularTolerance=0.1
    )
    export_step(items, work / "assembled_device_mount_T1.step")
    export_step(
        [i for i in items if i[2] in {"plate", "device", "screw", "tim_top"}],
        work / "device_adapter_T1.step",
    )
    export_step(
        [i for i in items if i[2] in {"plate", "screw", "stud", "washer", "nut"}],
        work / "mount_hardware_T1.step",
    )
    export_step(
        [i for i in items if i[2] in {"panel", "stud"}], work / "FPE_interface_REFERENCE_ONLY.step"
    )
    export_step(
        [(n, sh.rotate((0, 0, 0), (1, 0, 0), 90), k) for n, sh, k in items],
        work / "vertical_fin_installation_REFERENCE.step",
    )
    for side in ("top", "bottom"):
        field = thermal_field(p, side)
        cq.exporters.export(field, str(work / f"TIM_{side}_NOMINAL_POCKET_VOLUME.step"))
        face = max(
            [f for f in field.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().z) > 0.99],
            key=lambda f: f.Area(),
        )
        planar = cq.Compound.makeCompound(face.Wires()).translate((0, 0, -face.Center().z))
        cq.exporters.export(planar, str(work / f"thermal_{side}_pocket_contour_mm.dxf"))
    planar_files(p, work)
    metadata = {
        "revision": p["revision"],
        "units": "mm",
        "plate_volume_mm3": plate.Volume(),
        "plate_mass_kg_at_2700_kg_m3": plate.Volume() * 2.7e-6,
        "component_count": len(items),
        "source_device_solids": 22,
        "installed_device_solids": 21,
        "assembly_bbox_mm": bbox(cq.Compound.makeCompound([s for _, s, _ in items])),
        "components": [
            {
                "name": n,
                "kind": k,
                "valid": s.isValid(),
                "solids": len(s.Solids()),
                "bbox_mm": bbox(s),
            }
            for n, s, k in items
        ],
        "hardware_geometry": (
            "Simplified catalog proxies; ideal conical head is not a complete or conservative "
            "hardware envelope. Not supplier CAD or a real thread/seat fit test."
        ),
        "datum": (
            "Plate underside Z0; Tile mounting face Z5.1; source preserved; "
            "hybrid is derived reference."
        ),
        "thermal_fields": {
            side: {
                "area_mm2": thermal_field(p, side).Volume() / p["thermal_pocket_depth"],
                "primary_thermal_area_mm2_excluding_vents": thermal_field(p, side, False).Volume()
                / p["thermal_pocket_depth"],
                "volume_mm3": thermal_field(p, side).Volume(),
            }
            for side in ("top", "bottom")
        },
        "derived_configuration_limit": (
            "Tile and one fin bank clipped from the 60W alternative. Spatial fit only; "
            "no physical joint, product availability or 60W hybrid rating established."
        ),
    }
    (work / "cad_build_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    for path in work.iterdir():
        if path.name != "input_device.step" and path.is_file():
            shutil.copyfile(path, output / path.name)
    print(
        f"Built {len(items)} distinct components; plate {plate.Volume():.3f} mm3 / "
        f"{plate.Volume() * 2.7e-6:.4f} kg",
        flush=True,
    )
    return shapes, items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=HERE / "references/input_device.step")
    ap.add_argument("--out", type=Path, default=HERE / "exports")
    ap.add_argument("--work-dir", type=Path)
    args = ap.parse_args()
    if args.work_dir:
        export_all(load_params(), args.source, args.out, args.work_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="solidrun_thermal_") as td:
            export_all(load_params(), args.source, args.out, Path(td))


if __name__ == "__main__":
    main()
