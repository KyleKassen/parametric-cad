"""
OZ51x Dual-TX Housing — thin wrapper over the shared family builder
===================================================================
One RF transmitter + one TTL transmitter (both transmitter-handed bays),
rear DE-9 signal connector, no front wiring slots. All geometry comes from
parts/custom/oz510-dual-housing/model.py driven by this part's params.json —
see that module and this params.json for the design documentation.
"""

import importlib.util
import json
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"
BUILDER_FILE = PART_DIR.parent / "oz510-dual-housing" / "model.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("oz51x_housing_builder", BUILDER_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_builder = _load_builder()
layout = _builder.layout
create_base = _builder.create_base
create_lid = _builder.create_lid
orient_to_mounting = _builder.orient_to_mounting


def load_params(path: Path = PARAMS_FILE) -> dict:
    with open(path) as f:
        return json.load(f)


def create_part(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()
    return _builder.create_part(params)


def export_part(result, name=None, version="v1", formats=None):
    if name is None:
        name = PART_DIR.name
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

    L = layout(params)
    print(f"\n  Building: {params['part_name']} ({params.get('version', 'v1')})")
    print(
        f"  Outer envelope: {L['envelope_width']:.1f} (W) × "
        f"{L['envelope_depth']:.1f} (D) × "
        f"{L['envelope_height']:.1f} (H) mm\n"
    )

    fmts = ["step"] + (["stl"] if "--stl" in sys.argv else [])
    export_part(part, version=params.get("version", "v1"), formats=fmts)
