"""
Tests for the STEP analysis / rendering / keep-out pipeline (lib/).

Grounded in the real vendor files: the OZ510 Transmitter's I/O is mirrored
across X relative to the Receiver (SMA at x=+12.7 vs -12.7) while most of the
internal assembly is shared — the exact situation the pipeline exists to
catch. Run with: make test  (or: pytest tests/)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RX_STEP = PROJECT_ROOT / "parts" / "vendor" / "zonu-oz510-receiver" / "OZ510 Receiver.STEP"
TX_STEP = PROJECT_ROOT / "parts" / "vendor" / "zonu-oz510-transmitter" / "OZ510 Transmitter.STEP"


def _sma_x(analysis: dict) -> float:
    """X of the SMA connector axis: a Z-axis cylinder near the front tip."""
    candidates = [
        f
        for f in analysis["features"]
        if f["axis_label"] == "Z"
        and 2.0 <= f["radius"] <= 2.9
        and max(f["p1"][2], f["p2"][2]) > 40.0
    ]
    assert candidates, "no SMA-like feature found near the front tip"
    return candidates[0]["p1"][0]


def test_analyze_finds_mirrored_sma():
    """Per-part analysis must locate the SMA on opposite sides of X."""
    from lib.analyze_step import analyze

    rx, tx = analyze(RX_STEP), analyze(TX_STEP)
    assert abs(_sma_x(rx) - (-12.7)) < 0.3, "RX SMA should sit at x=-12.7"
    assert abs(_sma_x(tx) - (+12.7)) < 0.3, "TX SMA should sit at x=+12.7"


def test_analyze_exact_bbox():
    """Kernel-derived bbox must match the known module envelope."""
    from lib.analyze_step import analyze

    size = analyze(RX_STEP)["bbox_size"]
    assert abs(size[0] - 38.10) < 0.05
    assert abs(size[1] - 12.649) < 0.05
    assert abs(size[2] - 76.327) < 0.05


def test_compare_reports_not_identical():
    """
    compare(RX, TX) must NOT call the two files identical — assuming so is
    the mistake that produced the v1 housing bug.
    """
    from lib.analyze_step import compare

    result = compare(RX_STEP, TX_STEP)
    assert set(result["scores"]) == {"identity", "mirror_x", "mirror_y", "mirror_z"}
    assert all(0.0 <= s <= 1.0 for s in result["scores"].values())
    assert result["scores"]["identity"] < 0.95, "RX and TX must not read as identical"
    # The mirrored I/O should make mirror_x far outscore the other mirrors
    assert result["scores"]["mirror_x"] > result["scores"]["mirror_y"]
    assert result["scores"]["mirror_x"] > result["scores"]["mirror_z"]


def test_keepout_contains_module():
    """A keep-out prism must fully swallow the part it was derived from."""
    import cadquery as cq

    from lib.housing import keepout_prism

    module = (
        cq.importers.importStep(str(RX_STEP))
        .rotate((0, 0, 0), (1, 0, 0), 90)  # housing orientation, Z-up
        .val()
    )
    keepout = keepout_prism(module, axis="Z", clearance=1.0, extend_pos=5.0)

    leftover = module.cut(keepout).Volume()  # module material outside the keep-out
    assert leftover < 1.0, f"{leftover:.2f} mm^3 of module sticks out of the keep-out"
    assert keepout.Volume() > module.Volume()


def test_interference_measures_real_overlap():
    """interference() reports true overlap and 0.0 only for genuine clearance."""
    import cadquery as cq

    from lib.housing import interference

    a = cq.Workplane("XY").box(2, 2, 2)
    apart = cq.Workplane("XY").box(2, 2, 2).translate((10, 0, 0))
    overlapping = cq.Workplane("XY").box(2, 2, 2).translate((1, 0, 0))
    assert interference(a, apart) == 0.0
    assert abs(interference(a, overlapping) - 4.0) < 0.01  # 1 x 2 x 2 slab


def test_clearance_measures_min_gap():
    """clearance() gives the exact minimum distance; 0.0 only when touching."""
    import cadquery as cq

    from lib.housing import clearance

    a = cq.Workplane("XY").box(2, 2, 2)
    apart = cq.Workplane("XY").box(2, 2, 2).translate((5, 0, 0))
    overlapping = cq.Workplane("XY").box(2, 2, 2).translate((1, 0, 0))
    diagonal = cq.Workplane("XY").box(2, 2, 2).translate((5, 5, 0))
    assert abs(clearance(a, apart) - 3.0) < 1e-6
    assert clearance(a, overlapping) == 0.0
    assert abs(clearance(a, diagonal) - 3.0 * 2**0.5) < 1e-6


def test_interference_never_converts_errors_to_clearance():
    """A failed boolean must raise — not return a passing 0.0 (audit fix)."""
    import pytest

    from lib.housing import interference

    class ExplodingShape:
        def intersect(self, other):
            raise RuntimeError("kernel boolean failed")

    with pytest.raises(RuntimeError, match="kernel boolean failed"):
        interference(ExplodingShape(), ExplodingShape())


def test_export_all_zero_matches_is_failure():
    """Bulk export must not exit 0 when nothing was exported (audit fix)."""
    from lib.export import export_all

    assert export_all(part_filter="no-such-part-xyz") == 1


def test_export_all_build_error_is_failure(monkeypatch, tmp_path):
    """A part that raises during build must produce a failing exit code."""
    import lib.export as ex

    fake = tmp_path / "boom_part"
    fake.mkdir()
    (fake / "model.py").write_text("raise RuntimeError('build exploded')\n")
    monkeypatch.setattr(ex, "discover_parts", lambda: [fake / "model.py"])
    assert ex.export_all() == 1


def test_section_cut_reveals_interior(tmp_path):
    """section_cut removes the + side; bad stations raise instead of rendering lies."""
    import cadquery as cq
    import pytest

    from lib.render_step import section_cut

    hollow = (
        cq.Workplane("XY").box(20, 20, 10, centered=(True, True, False)).faces(">Z").shell(-2)
    )  # closed box, 2 mm walls... open shell downward
    cut = section_cut(hollow.val(), "Z", 5.0)
    bb = cut.BoundingBox()
    assert bb.zmax <= 5.01, "material above the cut plane must be gone"
    assert cut.Volume() < hollow.val().Volume()

    with pytest.raises(ValueError, match="beyond the part"):
        section_cut(hollow.val(), "Z", 99.0)
    with pytest.raises(ValueError, match="axis must be"):
        section_cut(hollow.val(), "Q", 5.0)


def test_render_file_section_suffix(tmp_path):
    """Section renders carry a _sec suffix so they never clobber whole views."""
    import cadquery as cq

    from lib.render_step import render_file

    step = tmp_path / "box.step"
    cq.exporters.export(cq.Workplane("XY").box(10, 10, 10), str(step))
    written = render_file(step, out_dir=tmp_path, views=("iso",), size=200, section=("Z", 2.5))
    assert [p.name for p in written] == ["box_secZ2p5_iso.png"]
    assert written[0].stat().st_size > 500


def test_render_smoke(tmp_path):
    """Offscreen rendering writes non-trivial PNGs for the requested views."""
    import cadquery as cq

    from lib.render_step import render_scene

    box = cq.Workplane("XY").box(10, 20, 5).val()
    written = render_scene(
        [(box, (0.6, 0.6, 0.6), 1.0)], tmp_path, "smoke", views=("front", "top"), size=300
    )
    assert [p.name for p in written] == ["smoke_front.png", "smoke_top.png"]
    for p in written:
        assert p.stat().st_size > 500
