"""
SC/APC Simplex Adapter (flanged) — datasheet-derived vendor stand-in
====================================================================
A purchased part, modeled from the FS.com AD-SCA-SCA-SM-SX-FS datasheet
drawing so housings can verify panel cutouts, flange seating, and internal
connector corridors against real geometry. Not for fabrication.

Frame: X = flange long axis, Y = mating axis, Z = short axis.
Origin at the body/flange center. Units: mm.
"""

import json
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"


def load_params(path: Path = PARAMS_FILE) -> dict:
    with open(path) as f:
        return json.load(f)


def create_part(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()
    d = params["dimensions"]

    # Rectangular body tube with the through-cavity for the SC plugs
    body = cq.Workplane("XY").box(d["body_long"], d["body_len"], d["body_short"])
    cavity = cq.Workplane("XY").box(
        d["body_long"] - 2 * d["body_wall"],
        d["body_len"] + 2.0,
        d["body_short"] - 2 * d["body_wall"],
    )
    part = body.cut(cavity)

    # Mid-body mounting flange with the two screw holes
    flange = (
        cq.Workplane("XY")
        .box(d["flange_len"], d["flange_thickness"], d["flange_wide"])
    )
    for sx in (-d["screw_spacing"] / 2.0, +d["screw_spacing"] / 2.0):
        hole = cq.Solid.makeCylinder(
            d["screw_hole_dia"] / 2.0, d["flange_thickness"] + 2.0,
            cq.Vector(sx, -d["flange_thickness"] / 2.0 - 1.0, 0),
            cq.Vector(0, 1, 0),
        )
        flange = flange.cut(cq.Workplane("XY").newObject([hole]))
    part = part.union(flange)

    # Center web that carries the ceramic split sleeve
    web = (
        cq.Workplane("XY")
        .box(d["body_long"] - 2 * d["body_wall"] + 0.2,
             d["center_web_thickness"],
             d["body_short"] - 2 * d["body_wall"] + 0.2)
        .faces(">Y").workplane()
        .hole(d["sleeve_od"] + 0.01)
    )
    part = part.union(web)

    # Ceramic split sleeve (modeled as a plain tube)
    sleeve = (
        cq.Workplane("XZ")
        .circle(d["sleeve_od"] / 2.0).circle(d["sleeve_id"] / 2.0)
        .extrude(d["sleeve_len"] / 2.0, both=True)
    )
    part = part.union(sleeve)

    return part


def export_part(result, name="sc-apc-simplex-adapter", version="v1", formats=None):
    if formats is None:
        formats = ["step"]
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for fmt in formats:
        p = EXPORTS_DIR / f"{name}_{version}.{fmt}"
        cq.exporters.export(result, str(p))
        print(f"  ✓ Exported {p.relative_to(PROJECT_ROOT)}")
        out.append(p)
    return out


if __name__ == "__main__":
    params = load_params()
    part = create_part(params)
    print(f"\n  Building: {params['part_name']} ({params.get('version', 'v1')})")
    fmts = ["step"] + (["stl"] if "--stl" in sys.argv else [])
    export_part(part, version=params.get("version", "v1"), formats=fmts)
