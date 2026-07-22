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
        f for f in analysis["features"]
        if f["axis_label"] == "Z" and 2.0 <= f["radius"] <= 2.9
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


def test_render_smoke(tmp_path):
    """Offscreen rendering writes non-trivial PNGs for the requested views."""
    import cadquery as cq

    from lib.render_step import render_scene

    box = cq.Workplane("XY").box(10, 20, 5).val()
    written = render_scene([(box, (0.6, 0.6, 0.6), 1.0)], tmp_path, "smoke",
                           views=("front", "top"), size=300)
    assert [p.name for p in written] == ["smoke_front.png", "smoke_top.png"]
    for p in written:
        assert p.stat().st_size > 500
