"""Export qualification coupons cut from the actual housing model.

Run from the repository with:
    uv run python parts/custom/oz51x-dual-tx-housing-vertical-snap/make_coupons.py

The latch pair is cropped in its original seated frame before any print
transforms. The connector slab uses the same cutter function as the full base.
These samples qualify local fit; they do not qualify complete-cover retention.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).absolute().parent
OUT_DIR = PART_DIR / "exports" / "coupons"


def load_model():
    spec = importlib.util.spec_from_file_location("oz51x_snap_coupon_source", PART_DIR / "model.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bounds(part):
    bb = part.val().BoundingBox()
    return {
        "min": [bb.xmin, bb.ymin, bb.zmin],
        "max": [bb.xmax, bb.ymax, bb.zmax],
        "size": [bb.xlen, bb.ylen, bb.zlen],
    }


def require_solid(part, name):
    solids = part.solids().vals()
    if len(solids) != 1 or not part.val().isValid():
        raise ValueError(f"{name}: expected one valid solid, got {len(solids)}")
    return {
        "valid": True,
        "solids": 1,
        "volume_mm3": part.val().Volume(),
        "bounds_mm": bounds(part),
    }


def at_print_datum(part, invert=False):
    # Retain X/Y datums; only the cover is inverted so its outer face is down.
    printable = part.rotate((0, 0, 0), (1, 0, 0), 180) if invert else part
    dz = -printable.val().BoundingBox().zmin
    printable = printable.translate((0, 0, dz))
    return printable, {"rotation_x_degrees": 180 if invert else 0, "translation_z_mm": dz}


def create_coupons(model, params):
    layout = model.layout(params)
    snap = params["snap"]
    if 70.0 not in snap["tip_y"]:
        raise ValueError("This crop targets the actual positive-X latch at canonical Y=70")
    root_y = 70.0 - snap["beam_length"]
    if root_y < 39.0 + 3.0:
        raise ValueError("Latch root moved outside the coupon's retained root attachment")
    upper_z = layout["base_height"] + params["housing"]["lid_thickness"] + 1.0
    region = {"min": [35.0, 39.0, 22.0], "max": [48.0, 76.0, upper_z]}
    crop = model.box(13.0, 37.0, upper_z - 22.0, 41.5, 57.5, 22.0)
    base = model._create_base_canonical(params).intersect(crop).clean()
    cover = model._create_lid_canonical(params).intersect(crop).clean()
    base_data = require_solid(base, "latch base, seated frame")
    cover_data = require_solid(cover, "latch cover, seated frame")
    common_volume = base.val().intersect(cover.val()).Volume()
    if common_volume > 1e-5:
        raise ValueError(f"Seated latch coupons interfere by {common_volume:.9f} mm3")

    pc = params["panel_connector"]
    wall = params["housing"]["wall"]
    # A 42 x 24 mm slab of the actual wall thickness. Its outward face is at
    # the full housing's front datum, so cutter and recess depths are identical.
    slab = model.box(
        42.0,
        wall,
        24.0,
        pc["x"],
        layout["back_outer_y"] - wall / 2,
        layout["panel_connector_z"] - 12.0,
    )
    connector = model._front_connector(slab, params, layout).clean()
    require_solid(connector, "DE-9 panel coupon")
    seated = {"latch_base": base, "latch_cover": cover, "de9_panel": connector}
    report = {
        "units": "mm",
        "latch_target": {"side": "+X", "tip_y": 70.0, "root_y": root_y},
        "crop_canonical_mm": region,
        "seated_latch_interference_mm3": common_volume,
        "seated_latch_base": base_data,
        "seated_latch_cover": cover_data,
        "source_model_sha256": hashlib.sha256((PART_DIR / "model.py").read_bytes()).hexdigest(),
        "resolved_params_sha256": hashlib.sha256(
            json.dumps(params, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "print_parts": {},
    }
    printable = {}
    for name, part in seated.items():
        printable[name], transform = at_print_datum(part, invert=name == "latch_cover")
        checked = require_solid(printable[name], name + ", print frame")
        if abs(checked["bounds_mm"]["min"][2]) > 1e-6:
            raise ValueError(f"{name}: print datum is not Z=0")
        report["print_parts"][name] = {**checked, "from_canonical_frame": transform}
    return seated, printable, report


def main():
    model = load_model()
    params = model.load_params()
    version = params["version"]
    seated, printable, report = create_coupons(model, params)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, part in printable.items():
        for extension in ("step", "stl"):
            cq.exporters.export(
                part,
                str(OUT_DIR / f"{name}_coupon_{version}.{extension}"),
                tolerance=0.03,
                angularTolerance=0.1,
            )
    assembly = cq.Assembly(name="latch_coupon_seated")
    assembly.add(seated["latch_base"], name="base", color=cq.Color(0.22, 0.25, 0.28))
    assembly.add(seated["latch_cover"], name="cover", color=cq.Color(0.5, 0.6, 0.7))
    assembly.export(str(OUT_DIR / f"latch_coupon_seated_{version}.step"))
    (OUT_DIR / "coupon_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT_DIR / "README.md").write_text(
        "# Fit coupons\n\n"
        "Generated by `make_coupons.py` from the actual housing functions.\n\n"
        f"- `latch_base_coupon_{version}`: cropped positive-X wall and pocket at Y=70; "
        "the cut at canonical Z=22 forms a flat footing.\n"
        f"- `latch_cover_coupon_{version}`: matching cover section including the 26 mm "
        "beam, its root, hook, release button, and adjacent inner stop. "
        "Its outer face is down in the print file.\n"
        f"- `de9_panel_coupon_{version}`: actual connector cutout and flange recess in "
        "a 42 x 24 mm slab of the housing wall thickness. It stands on its "
        "lower edge in the same canonical orientation as the base's I/O panel. "
        "Use a brim for an FDM trial.\n\n"
        "Each print STEP/STL is a separate valid solid with its lowest point "
        "at Z=0. X/Y datums are retained rather than packing the parts. "
        f"`latch_coupon_seated_{version}.step` shows their original relative seating; "
        "do not infer assembly placement from the independently transformed "
        "print files. See `coupon_validation.json` for transforms and checks.\n\n"
        "Use the production material and process to qualify spring action "
        "and fit. The latch sample checks the local spring/pocket joint; it "
        "does not reproduce the full cover's fixed-hook installation or "
        "establish retention force, endurance, or temperature rating. "
        "No material may be trimmed from the active beam or hook to obtain "
        "a passing result without updating the full design.\n\n"
        "Fit the purchased DE-9, mounting hardware, and mating cable to the "
        "connector coupon. Confirm full mating and flange seating. "
        "See `../../CONNECTOR.md` for the candidate connector, design "
        "allowances, and electrical limitations.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
