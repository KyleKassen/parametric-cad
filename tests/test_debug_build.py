"""
Tests for lib/debug_build.py — stage-by-stage build bisection.

Run with: make test  (or: pytest tests/)
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STAGED_MODEL = """\
import cadquery as cq


def create_part(params=None):
    wp = cq.Workplane("XY").box(20, 20, 5)
    wp = wp.faces(">Z").workplane().hole(6.0)
    return wp


def build_stages(params=None):
    wp = cq.Workplane("XY").box(20, 20, 5)
    yield "stock", wp
    wp = wp.faces(">Z").workplane().hole(6.0)
    yield "bore", wp
"""

FAILING_STAGE = STAGED_MODEL.replace(
    '    wp = wp.faces(">Z").workplane().hole(6.0)\n    yield "bore", wp',
    '    wp = wp.edges("|Z").fillet(50.0)  # radius >> part: kernel error\n'
    '    yield "impossible_fillet", wp',
)

DRIFTED_MODEL = STAGED_MODEL.replace(
    'def build_stages(params=None):\n    wp = cq.Workplane("XY").box(20, 20, 5)',
    'def build_stages(params=None):\n    wp = cq.Workplane("XY").box(20, 20, 4)',
)


def make_part(tmp_path, body, name="staged"):
    part = tmp_path / name
    part.mkdir()
    (part / "model.py").write_text(body)
    (part / "params.json").write_text(json.dumps({"part_name": name, "version": "v1"}))
    return part


def test_all_stages_pass(tmp_path):
    from lib.debug_build import debug_build

    result = debug_build(make_part(tmp_path, STAGED_MODEL), quiet=True)
    assert result["ok"] is True
    assert [s["name"] for s in result["stages"]] == ["stock", "bore"]
    assert "drift_mm3" not in result


def test_failure_is_localized_to_last_good_stage(tmp_path):
    from lib.debug_build import debug_build

    result = debug_build(make_part(tmp_path, FAILING_STAGE), quiet=True)
    assert result["ok"] is False
    assert result["failed_after"] == "stock"
    assert result["error"], "the kernel error must be reported"
    assert [s["name"] for s in result["stages"]] == ["stock"]


def test_fallback_without_build_stages(tmp_path):
    from lib.debug_build import debug_build

    plain = STAGED_MODEL.split("def build_stages")[0]
    result = debug_build(make_part(tmp_path, plain), quiet=True)
    assert result["ok"] is True
    assert result["stages"] == []

    broken = plain.replace(
        'cq.Workplane("XY").box(20, 20, 5)', '(_ for _ in ()).throw(RuntimeError("boom"))'
    )
    result = debug_build(make_part(tmp_path, broken, name="broken"), quiet=True)
    assert result["ok"] is False
    assert "boom" in result["error"]


def test_drift_between_stages_and_create_part_is_flagged(tmp_path):
    from lib.debug_build import debug_build

    result = debug_build(make_part(tmp_path, DRIFTED_MODEL), quiet=True)
    assert result["ok"] is True
    assert result.get("drift_mm3", 0) > 50, "stage/create_part drift must be warned about"


def test_stage_renders_written(tmp_path):
    from lib.debug_build import debug_build

    part = make_part(tmp_path, STAGED_MODEL)
    result = debug_build(part, render=True, out_dir=tmp_path / "dbg", size=200, quiet=True)
    assert result["ok"] is True
    names = sorted(Path(p).name for p in result["renders"])
    assert names == ["01_stock_iso.png", "02_bore_iso.png"]
