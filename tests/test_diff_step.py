"""
Tests for lib/diff_step.py — geometric diff between STEP artifacts.

Run with: make test  (or: pytest tests/)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _export(tmp_path, name, wp):
    import cadquery as cq

    path = tmp_path / name
    cq.exporters.export(wp, str(path))
    return path


def test_identical_files_diff_to_zero(tmp_path):
    import cadquery as cq

    from lib.diff_step import diff

    box = cq.Workplane("XY").box(20, 20, 5)
    a = _export(tmp_path, "a.step", box)
    b = _export(tmp_path, "b.step", box)
    result = diff(a, b)
    assert result["identical"] is True
    assert result["added_mm3"] == 0.0
    assert result["removed_mm3"] == 0.0
    assert result["features_added"] == []
    assert result["features_removed"] == []


def test_added_and_removed_material_measured(tmp_path):
    import cadquery as cq

    from lib.diff_step import diff

    old = cq.Workplane("XY").box(20, 20, 5)
    # new: gains a 5x5x5 boss on top, loses a 4 mm bore through the middle
    new = (
        cq.Workplane("XY")
        .box(20, 20, 5)
        .faces(">Z")
        .workplane()
        .rect(5, 5)
        .extrude(5)
        .faces(">Z")
        .workplane()
        .hole(4.0)
    )
    a = _export(tmp_path, "old.step", old)
    b = _export(tmp_path, "new.step", new)

    result = diff(a, b)
    assert result["identical"] is False
    import math

    bore_per_5mm = math.pi * 2.0**2 * 5  # d=4 bore through 5 mm of material
    # boss adds 5*5*5 = 125 minus the bore passing through its full height
    assert abs(result["added_mm3"] - (125.0 - bore_per_5mm)) < 1.5
    # bore removes its volume from the ORIGINAL 5-thick plate
    assert abs(result["removed_mm3"] - bore_per_5mm) < 1.5
    assert any("d=4" in f for f in result["features_added"]), "new bore is a feature add"


def test_render_diff_writes_overlay(tmp_path):
    import cadquery as cq

    from lib.diff_step import diff, render_diff

    old = cq.Workplane("XY").box(20, 20, 5)
    new = cq.Workplane("XY").box(20, 20, 8)
    a = _export(tmp_path, "old.step", old)
    b = _export(tmp_path, "new.step", new)
    result = diff(a, b)
    written = render_diff(result, tmp_path / "views", views=("iso",), size=200)
    assert len(written) == 1
    assert written[0].name == "diff_old_vs_new_iso.png"
    assert written[0].stat().st_size > 500


def test_cli_exit_codes(tmp_path):
    import cadquery as cq

    from lib.diff_step import main

    box = cq.Workplane("XY").box(10, 10, 5)
    bigger = cq.Workplane("XY").box(10, 10, 6)
    a = _export(tmp_path, "a.step", box)
    b = _export(tmp_path, "b.step", bigger)
    same = _export(tmp_path, "same.step", box)

    assert main([str(a), str(same), "--no-render"]) == 0
    assert main([str(a), str(b), "--no-render"]) == 1
    assert main([str(a), str(tmp_path / "missing.step"), "--no-render"]) == 2
