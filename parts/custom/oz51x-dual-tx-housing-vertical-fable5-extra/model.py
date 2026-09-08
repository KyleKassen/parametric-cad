"""OZ51x Dual-TX vertical housing, Fable 5 Extra Edition — thin wrapper.

Transmitter-handed variant of the redesigned vertical housing. All geometry
comes from the redesigned family builder in
parts/custom/oz51x-dual-rx-housing-vertical-fable5-extra/model.py; this
wrapper only supplies the TX params (mirror_x bays, TX identity label).
"""

import importlib.util
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"
BUILDER_FILE = PART_DIR.parent / "oz51x-dual-rx-housing-vertical-fable5-extra" / "model.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("oz51x_fable5_vertical_builder", BUILDER_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_builder = _load_builder()
layout = _builder.layout
create_base = _builder.create_base
create_lid = _builder.create_lid
orient_to_mounting = _builder.orient_to_mounting


def load_params(path: Path = PARAMS_FILE) -> dict:
    return _builder.load_params_file(path)


def create_part(params: dict | None = None) -> cq.Workplane:
    return _builder.create_part(load_params() if params is None else params)


def export_part(result, name=None, version="v1", formats=None):
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
    part = create_part(params)
    L = layout(params)
    print(f"\n  Building: {params['part_name']} ({params.get('version', 'v1')})")
    print(
        f"  Outer envelope: {L['envelope_width']:.1f} (W) × "
        f"{L['envelope_depth']:.1f} (D) × "
        f"{L['envelope_height']:.1f} (H) mm  (incl. mount flanges)\n"
    )
    fmts = ["step"] + (["stl"] if "--stl" in sys.argv else [])
    export_part(part, version=params.get("version", "v1"), formats=fmts)
