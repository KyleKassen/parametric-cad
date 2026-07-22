"""
SC/APC Connector (0.9mm pigtail) — datasheet-derived vendor stand-in
====================================================================
The connector on the OZ510 modules' factory pigtails (and on any pigtail
plugged into a housing's internal SC adapter port). Modeled from the Leviton
GD102431 drawing lengths + the FOCIS-3 SC envelope so housings can verify
the straight corridor a mated connector needs. Not for fabrication.

Frame: plug axis = +Y; origin at the grip's front face (the plane that stops
against the adapter body end when mated). Units: mm.
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

    # Plug shroud: inserts into the adapter (+Y from the origin)
    part = (
        cq.Workplane("XY")
        .box(d["plug_w"], d["plug_len"], d["plug_h"], centered=(True, False, True))
    )

    # Ferrule, protruding from the shroud to its mated tip position
    ferrule = cq.Solid.makeCylinder(
        d["ferrule_dia"] / 2.0, d["ferrule_tip_y"],
        cq.Vector(0, 0, 0), cq.Vector(0, 1, 0),
    )
    part = part.union(cq.Workplane("XY").newObject([ferrule]))

    # Outer push-pull grip, behind the stop face (-Y)
    grip = (
        cq.Workplane("XY")
        .box(d["grip_w"], d["grip_len"], d["grip_h"], centered=(True, False, True))
        .translate((0, -d["grip_len"], 0))
    )
    part = part.union(grip)

    # Crimp barrel
    crimp = cq.Solid.makeCylinder(
        d["crimp_dia"] / 2.0, d["crimp_len"],
        cq.Vector(0, -d["grip_len"] - d["crimp_len"], 0), cq.Vector(0, 1, 0),
    )
    part = part.union(cq.Workplane("XY").newObject([crimp]))

    # Strain-relief boot: cone from the crimp down to the fiber
    boot_len = d["overall_len"] - d["ferrule_tip_y"] - d["grip_len"] - d["crimp_len"]
    boot = cq.Solid.makeCone(
        d["crimp_dia"] / 2.0, d["boot_tip_dia"] / 2.0, boot_len,
        cq.Vector(0, -d["grip_len"] - d["crimp_len"], 0), cq.Vector(0, -1, 0),
    )
    part = part.union(cq.Workplane("XY").newObject([boot]))

    return part


def export_part(result, name="sc-apc-connector", version="v1", formats=None):
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
