"""OZ51x Dual-TX vertical housing, production refinement — Opus 5 edition.

RF and TTL transmitter bays stacked vertically, wall-mounted, with the
removable service cover on the large outward face.

This file is a thin wrapper, identical to its TX peer except for this
docstring.  All refinement geometry lives in the family directory alongside
the canonical builder it layers onto:

    parts/custom/oz510-dual-housing/refine_opus5.py

That module calls the canonical builder's own `_create_base_canonical` /
`_create_lid_canonical` to produce the verified interface geometry, then
applies the refinement as explicit boolean operations on top.  Nothing in
`oz510-dual-housing/model.py` is modified, so the interface geometry of this
part is the same code path as v1 by construction rather than by assertion.

See DESIGN.md in this directory.
"""

import importlib.util
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"
REFINER_FILE = PART_DIR.parent / "oz510-dual-housing" / "refine_opus5.py"


def _load_refiner():
    spec = importlib.util.spec_from_file_location("oz51x_refine_opus5", REFINER_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_refine = _load_refiner()

load_params_file = _refine.load_params_file
layout = _refine.layout
orient_to_mounting = _refine.orient_to_mounting
create_base = _refine.create_base
create_lid = _refine.create_lid
build_stages = _refine.build_stages


def load_params(path: Path = PARAMS_FILE) -> dict:
    return load_params_file(path)


def create_part(params: dict | None = None) -> cq.Workplane:
    return _refine.create_part(load_params() if params is None else params)


def export_part(result, name=None, version="v1", formats=None):
    """Write `result` to exports/<name>_<version>.<fmt> for each format."""
    name = PART_DIR.name if name is None else name
    formats = ["step"] if formats is None else formats
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for fmt in formats:
        path = EXPORTS_DIR / f"{name}_{version}.{fmt}"
        cq.exporters.export(result, str(path))
        print(f"  ✓ Exported {path.relative_to(PROJECT_ROOT)}")
        out.append(path)
    return out


if __name__ == "__main__":
    params = load_params()
    version = params.get("version", "v1")
    fmts = ["step"] + (["stl"] if "--stl" in sys.argv else [])

    L = layout(params)
    print(f"\n  Building: {params['part_name']} ({version})")
    print(
        f"  Outer envelope: {L['envelope_width']:.1f} (W) × "
        f"{L['envelope_depth']:.1f} (D) × "
        f"{L['envelope_height']:.1f} (H) mm\n"
    )

    # The assembly, plus each printable part on its own — a fused compound is
    # not something a shop can quote or a slicer can lay out.
    export_part(create_part(params), version=version, formats=fmts)
    export_part(create_base(params), name=f"{PART_DIR.name}_base", version=version, formats=fmts)
    export_part(create_lid(params), name=f"{PART_DIR.name}_cover", version=version, formats=fmts)
