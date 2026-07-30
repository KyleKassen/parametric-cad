"""
Tests for lib/fit.py — the declarative assembly fit engine.

A synthetic tray-with-pocket part exercises every constraint kind
(max_interference, min_clearance, max_outside), the transform pipeline, the
error paths (which must ERROR, never silently pass), and the integration into
lib/evaluate.py's acceptance gate.
Run with: make test  (or: pytest tests/)
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

FIT_MODEL = """\
import json
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent


def load_params(path=None):
    return json.loads((PART_DIR / "params.json").read_text())


def create_part(params=None):
    # 40x40x10 tray with a centered 20x20 pocket, 8 deep (floor 2 thick)
    tray = cq.Workplane("XY").box(40, 40, 10, centered=(True, True, False))
    pocket = (cq.Workplane("XY").box(20, 20, 8, centered=(True, True, False))
              .translate((0, 0, 2)))
    return tray.cut(pocket)


def create_region(params=None):
    # the pocket's open volume, as a keep-out region solid
    return (cq.Workplane("XY").box(20, 20, 8, centered=(True, True, False))
            .translate((0, 0, 2)))


def create_peg(params=None):
    # 10x10x8 peg that sits centered in the pocket with 5 mm side clearance
    return (cq.Workplane("XY").box(10, 10, 8, centered=(True, True, False))
            .translate((0, 0, 2)))
"""


def make_fit_part(tmp_path, cases, name="tray"):
    part = tmp_path / name
    part.mkdir()
    (part / "model.py").write_text(FIT_MODEL)
    (part / "params.json").write_text(json.dumps({"part_name": name, "version": "v1"}))
    (part / "spec.json").write_text(
        json.dumps({"schema": "part-spec/1", "units": "mm", "fit": {"cases": cases}})
    )
    return part


def run_cases(tmp_path, cases):
    from lib.fit import run_fit

    part = make_fit_part(tmp_path, cases)
    checks, scene = run_fit({"cases": cases}, part)
    return checks, scene


def by_id(checks, check_id):
    matches = [c for c in checks if c["id"] == check_id]
    assert matches, f"no check {check_id!r} in {[c['id'] for c in checks]}"
    return matches[0]


PEG = {"source": "builder", "builder": "create_peg"}
TRAY = {"source": "builder", "builder": "create_part"}
REGION = {"source": "builder", "builder": "create_region"}


def test_interference_pass_and_fail(tmp_path):
    cases = [
        {"id": "clear", "a": TRAY, "b": PEG, "max_interference": 0.5},
        {
            "id": "rammed",
            "a": TRAY,
            "b": {**PEG, "transform": [{"translate": [8, 0, 0]}]},
            "max_interference": 0.5,
        },
    ]
    checks, _ = run_cases(tmp_path, cases)
    assert by_id(checks, "fit:clear:max_interference")["status"] == "PASS"
    rammed = by_id(checks, "fit:rammed:max_interference")
    assert rammed["status"] == "FAIL"
    assert abs(rammed["measured"] - 240.0) < 1.0  # 3 x 10 x 8 mm bite into the wall


def test_min_clearance_pass_and_fail(tmp_path):
    # The seated peg TOUCHES the pocket floor -> clearance 0. Hover it 3 mm
    # so the true minimum gap (floor 3 mm < sides 5 mm) is a real number.
    hover = {**PEG, "transform": [{"translate": [0, 0, 3]}]}
    cases = [
        {"id": "seated", "a": TRAY, "b": PEG, "min_clearance": 0.5},
        {"id": "roomy", "a": TRAY, "b": hover, "min_clearance": 2.5},
        {"id": "tight", "a": TRAY, "b": hover, "min_clearance": 4.0},
    ]
    checks, _ = run_cases(tmp_path, cases)
    seated = by_id(checks, "fit:seated:min_clearance")
    assert seated["status"] == "FAIL"
    assert seated["measured"] == 0.0  # touching reads as zero, not as roomy
    roomy = by_id(checks, "fit:roomy:min_clearance")
    assert roomy["status"] == "PASS"
    assert abs(roomy["measured"] - 3.0) < 0.01  # peg bottom to pocket floor
    assert by_id(checks, "fit:tight:min_clearance")["status"] == "FAIL"


def test_max_outside_containment(tmp_path):
    cases = [
        {"id": "inside", "a": REGION, "b": PEG, "max_outside": 0.5},
        {
            "id": "sticking_out",
            "a": REGION,
            "b": {**PEG, "transform": [{"translate": [7, 0, 0]}]},
            "max_outside": 0.5,
        },
    ]
    checks, _ = run_cases(tmp_path, cases)
    assert by_id(checks, "fit:inside:max_outside")["status"] == "PASS"
    out = by_id(checks, "fit:sticking_out:max_outside")
    assert out["status"] == "FAIL"
    assert abs(out["measured"] - 160.0) < 1.0  # 2 x 10 x 8 mm proud of the region


def test_transforms_apply_in_order(tmp_path):
    import cadquery as cq

    from lib.fit import _apply_transform

    bar = cq.Workplane("XY").box(10, 2, 2)  # long in X
    rotated = _apply_transform(
        bar, [{"rotate": {"axis": "Z", "angle": 90}}, {"translate": [0, 0, 5]}]
    )
    bb = rotated.val().BoundingBox()
    assert abs(bb.ylen - 10.0) < 0.01, "rotation about Z should move the long axis to Y"
    assert abs(bb.xlen - 2.0) < 0.01
    assert abs((bb.zmin + bb.zmax) / 2 - 5.0) < 0.01, "translate should follow the rotate"


def test_error_paths_never_pass(tmp_path):
    cases = [
        {"id": "no_constraint", "a": TRAY, "b": PEG},
        {"id": "bad_source", "a": TRAY, "b": {"source": "hologram"}, "max_interference": 1.0},
        {
            "id": "bad_builder",
            "a": TRAY,
            "b": {"source": "builder", "builder": "create_unicorn"},
            "max_interference": 1.0,
        },
        {
            "id": "missing_step",
            "a": TRAY,
            "b": {"source": "step", "path": "parts/vendor/nope/missing.STEP"},
            "max_interference": 1.0,
        },
    ]
    checks, _ = run_cases(tmp_path, cases)
    assert by_id(checks, "fit:no_constraint")["status"] == "ERROR"
    for cid in ("bad_source", "bad_builder", "missing_step"):
        assert by_id(checks, f"fit:{cid}:max_interference")["status"] == "ERROR"


def test_scene_contains_reference_and_placed_solids(tmp_path):
    cases = [{"id": "clear", "a": TRAY, "b": PEG, "max_interference": 0.5}]
    _, scene = run_cases(tmp_path, cases)
    assert len(scene) == 2
    opacities = sorted(op for _, _, op in scene)
    assert opacities[0] < 1.0 <= opacities[1], "reference solid should be translucent"


def test_evaluate_gates_on_fit_block(tmp_path):
    from lib.evaluate import evaluate_part

    bad = make_fit_part(
        tmp_path,
        [
            {
                "id": "rammed",
                "a": TRAY,
                "b": {**PEG, "transform": [{"translate": [8, 0, 0]}]},
                "max_interference": 0.5,
            },
        ],
        name="bad_tray",
    )
    report = evaluate_part(bad, render=False, quiet=True)
    assert report["overall"] == "FAIL"
    assert report["promoted"] is False
    assert not (bad / "exports" / "bad_tray_v1.step").exists()

    good = make_fit_part(
        tmp_path,
        [
            {"id": "clear", "a": TRAY, "b": PEG, "max_interference": 0.5},
            {
                "id": "roomy",
                "a": TRAY,
                "b": {**PEG, "transform": [{"translate": [0, 0, 3]}]},
                "min_clearance": 2.5,
            },
        ],
        name="good_tray",
    )
    report = evaluate_part(good, render=False, quiet=True)
    assert report["overall"] == "PASS"
    assert report["promoted"] is True
    assert (good / "exports" / "good_tray_v1.step").is_file()
