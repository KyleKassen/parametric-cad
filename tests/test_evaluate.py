"""
Tests for the lib/evaluate.py agent evaluation pipeline.

Each test builds a tiny synthetic part in tmp_path and runs the real pipeline
(build -> export -> re-import -> validate -> report -> promote) against it.
Failure cases are the point: wrong dimensions, wrong solid count, STEP
round-trip corruption, validator failures, and the promotion guarantee that a
failed attempt never replaces an accepted artifact.
Run with: make test  (or: pytest tests/)
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BOX_MODEL = """\
import json
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent


def load_params(path=None):
    return json.loads((PART_DIR / "params.json").read_text())


def create_part(params=None):
    if params is None:
        params = load_params()
    d = params["dimensions"]
    return cq.Workplane("XY").box(d["length"], d["width"], d["thickness"])
"""


def make_part(tmp_path, model_body=BOX_MODEL, dims=None, spec=None, name="widget"):
    part = tmp_path / name
    part.mkdir()
    (part / "model.py").write_text(model_body)
    params = {"part_name": name, "version": "v1",
              "dimensions": dims or {"length": 10.0, "width": 20.0, "thickness": 5.0}}
    (part / "params.json").write_text(json.dumps(params))
    if spec is not None:
        (part / "spec.json").write_text(json.dumps(spec))
    return part


def box_spec(x=10.0, y=20.0, z=5.0, solids=1, **extra):
    return {
        "schema": "part-spec/1",
        "units": "mm",
        "solid_count": solids,
        "dimensions": [
            {"id": "len_x", "kind": "bbox", "axis": "x", "expected": x, "tol": 0.05},
            {"id": "wid_y", "kind": "bbox", "axis": "y", "expected": y, "tol": 0.05},
            {"id": "thk_z", "kind": "bbox", "axis": "z", "expected": z, "tol": 0.05},
        ],
        **extra,
    }


def run(part_dir, **kw):
    from lib.evaluate import evaluate_part

    kw.setdefault("render", False)
    kw.setdefault("quiet", True)
    return evaluate_part(part_dir, **kw)


def check_by_id(report, check_id):
    matches = [c for c in report["checks"] if c["id"] == check_id]
    assert matches, f"no check {check_id!r} in {[c['id'] for c in report['checks']]}"
    return matches[0]


def accepted_step(part_dir):
    return part_dir / "exports" / "widget_v1.step"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_pass_promotes_artifact(tmp_path):
    part = make_part(tmp_path, spec=box_spec())
    report = run(part)

    assert report["overall"] == "PASS"
    assert report["exit_code"] == 0
    assert report["promoted"] is True
    assert accepted_step(part).is_file()
    # attempt artifacts exist and the report round-trips as JSON
    attempt_report = part / Path(report["artifacts"]["report"]).name
    attempt_dirs = list((part / "exports" / "attempts").iterdir())
    assert len(attempt_dirs) == 1
    saved = json.loads((attempt_dirs[0] / "report.json").read_text())
    assert saved["overall"] == "PASS"
    # accepted report written next to the accepted step
    assert (part / "exports" / "widget_v1_report.json").is_file()
    del attempt_report


def test_validation_runs_against_reimported_step(tmp_path):
    """The bbox in the report must come from the exported artifact."""
    part = make_part(tmp_path, spec=box_spec())
    report = run(part)
    assert report["geometry"]["solid_count"] == 1
    assert abs(report["geometry"]["bbox_size"][0] - 10.0) < 0.01


def test_no_spec_still_runs_baseline_checks(tmp_path):
    part = make_part(tmp_path)  # no spec.json
    report = run(part)
    assert report["overall"] == "PASS"
    assert check_by_id(report, "brep_valid")["status"] == "PASS"
    assert check_by_id(report, "non_empty")["status"] == "PASS"


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------
def test_wrong_dimension_fails(tmp_path):
    part = make_part(tmp_path, spec=box_spec(x=12.0))  # model builds 10.0
    report = run(part)

    assert report["overall"] == "FAIL"
    assert report["exit_code"] == 1
    assert report["promoted"] is False
    assert check_by_id(report, "dim:len_x")["status"] == "FAIL"
    assert not accepted_step(part).exists()


def test_wrong_solid_count_fails(tmp_path):
    part = make_part(tmp_path, spec=box_spec(solids=2))
    report = run(part)

    assert report["overall"] == "FAIL"
    assert check_by_id(report, "solid_count")["status"] == "FAIL"
    assert report["promoted"] is False


def test_step_roundtrip_failure_is_error(tmp_path, monkeypatch):
    """A corrupt exported file must surface as ERROR at re-import, exit 2."""
    import lib.evaluate as ev

    part = make_part(tmp_path, spec=box_spec())
    monkeypatch.setattr(ev, "export_step",
                        lambda shape, path: path.write_text("not a STEP file"))
    report = run(part)

    assert report["overall"] == "ERROR"
    assert report["exit_code"] == 2
    assert check_by_id(report, "reimport")["status"] == "ERROR"
    assert report["promoted"] is False
    assert not accepted_step(part).exists()


def test_empty_geometry_never_passes(tmp_path):
    """create_part() yielding no solids must fail, not export an empty 'PASS'."""
    empty_model = BOX_MODEL.replace(
        'return cq.Workplane("XY").box(d["length"], d["width"], d["thickness"])',
        'return cq.Workplane("XY").rect(5, 5)',  # wire only, no solid
    )
    part = make_part(tmp_path, model_body=empty_model, spec=box_spec())
    report = run(part)

    assert report["overall"] in ("FAIL", "ERROR")
    assert report["exit_code"] != 0
    assert report["promoted"] is False
    assert not accepted_step(part).exists()


def test_build_exception_is_error(tmp_path):
    broken = BOX_MODEL.replace('d = params["dimensions"]',
                               'raise RuntimeError("boom")')
    part = make_part(tmp_path, model_body=broken, spec=box_spec())
    report = run(part)

    assert report["overall"] == "ERROR"
    assert report["exit_code"] == 2
    assert check_by_id(report, "build")["status"] == "ERROR"
    assert "boom" in check_by_id(report, "build")["message"]
    assert report["promoted"] is False


# ---------------------------------------------------------------------------
# Part-specific validators
# ---------------------------------------------------------------------------
def test_validator_pass_sees_exported_step(tmp_path):
    part = make_part(tmp_path, spec=box_spec(
        validators=[{"id": "sees_step", "script": "check.py"}]))
    (part / "check.py").write_text(
        "import os, sys\nfrom pathlib import Path\n"
        "sys.exit(0 if Path(os.environ['EVAL_STEP_PATH']).is_file() else 1)\n")
    report = run(part)
    assert check_by_id(report, "validator:sees_step")["status"] == "PASS"
    assert report["overall"] == "PASS"


def test_validator_nonzero_exit_fails(tmp_path):
    part = make_part(tmp_path, spec=box_spec(
        validators=[{"id": "angry", "script": "check.py"}]))
    (part / "check.py").write_text("import sys\nprint('clearance violated')\nsys.exit(3)\n")
    report = run(part)

    c = check_by_id(report, "validator:angry")
    assert c["status"] == "FAIL"
    assert c["exit_code"] == 3
    assert report["overall"] == "FAIL"
    assert report["promoted"] is False


def test_validator_missing_script_is_error(tmp_path):
    part = make_part(tmp_path, spec=box_spec(
        validators=[{"id": "ghost", "script": "does_not_exist.py"}]))
    report = run(part)
    assert check_by_id(report, "validator:ghost")["status"] == "ERROR"
    assert report["overall"] == "ERROR"
    assert report["exit_code"] == 2


# ---------------------------------------------------------------------------
# Positioned feature checks (cylinder_at) — the handedness catcher
# ---------------------------------------------------------------------------
HOLED_MODEL = BOX_MODEL.replace(
    'return cq.Workplane("XY").box(d["length"], d["width"], d["thickness"])',
    'return (cq.Workplane("XY").box(d["length"], d["width"], d["thickness"])\n'
    '            .faces(">Z").workplane().center(3.0, 0).hole(4.0))',
)


def test_cylinder_at_accepts_correct_side(tmp_path):
    spec = box_spec()
    spec["dimensions"].append(
        {"id": "offset_hole", "kind": "cylinder_at", "diameter": 4.0, "tol": 0.1,
         "axis": "Z", "type": "hole", "at": [3.0, 0.0, 0.0], "pos_tol": 0.5})
    part = make_part(tmp_path, model_body=HOLED_MODEL, spec=spec)
    report = run(part)
    c = check_by_id(report, "dim:offset_hole")
    assert c["status"] == "PASS"
    assert c["measured"] < 0.01


def test_cylinder_at_rejects_mirrored_hole(tmp_path):
    """A hole of the right size on the WRONG side must fail — the v1 bug."""
    spec = box_spec()
    spec["dimensions"].append(
        {"id": "mirrored_hole", "kind": "cylinder_at", "diameter": 4.0, "tol": 0.1,
         "axis": "Z", "type": "hole", "at": [-3.0, 0.0, 0.0], "pos_tol": 0.5})
    part = make_part(tmp_path, model_body=HOLED_MODEL, spec=spec)
    report = run(part)
    c = check_by_id(report, "dim:mirrored_hole")
    assert c["status"] == "FAIL"
    assert abs(c["measured"] - 6.0) < 0.01  # nearest candidate is 6 mm away
    assert report["overall"] == "FAIL"
    assert report["promoted"] is False


def test_cylinder_at_no_candidate_fails(tmp_path):
    spec = box_spec()
    spec["dimensions"].append(
        {"id": "phantom", "kind": "cylinder_at", "diameter": 9.0,
         "at": [0.0, 0.0, 0.0]})
    part = make_part(tmp_path, model_body=HOLED_MODEL, spec=spec)
    report = run(part)
    c = check_by_id(report, "dim:phantom")
    assert c["status"] == "FAIL"
    assert "anywhere" in c["message"]


# ---------------------------------------------------------------------------
# Spec structure: unresolved values, broken spec
# ---------------------------------------------------------------------------
def test_unresolved_hard_dimension_blocks_acceptance(tmp_path):
    spec = box_spec()
    spec["dimensions"].append(
        {"id": "mystery_bore", "kind": "cylinder", "diameter": 6.0, "unresolved": True})
    part = make_part(tmp_path, spec=spec)
    report = run(part)

    assert check_by_id(report, "dim:mystery_bore")["status"] == "ERROR"
    assert report["overall"] == "ERROR"
    assert report["promoted"] is False


def test_unresolved_soft_dimension_warns_only(tmp_path):
    spec = box_spec()
    spec["dimensions"].append(
        {"id": "nice_to_know", "kind": "volume", "unresolved": True, "severity": "soft"})
    part = make_part(tmp_path, spec=spec)
    report = run(part)

    assert report["overall"] == "PASS"
    assert "dim:nice_to_know" in report["warnings"]


def test_broken_spec_json_is_error(tmp_path):
    part = make_part(tmp_path)
    (part / "spec.json").write_text("{not valid json")
    report = run(part)
    assert report["overall"] == "ERROR"
    assert check_by_id(report, "spec")["status"] == "ERROR"


# ---------------------------------------------------------------------------
# Promotion guarantee
# ---------------------------------------------------------------------------
def test_failed_attempt_never_replaces_accepted_artifact(tmp_path):
    part = make_part(tmp_path, spec=box_spec())
    report1 = run(part)
    assert report1["promoted"] is True
    accepted = accepted_step(part)
    original_bytes = accepted.read_bytes()
    original_report = (part / "exports" / "widget_v1_report.json").read_text()

    # Regress the model so the spec fails, and evaluate again
    params = json.loads((part / "params.json").read_text())
    params["dimensions"]["length"] = 13.0
    (part / "params.json").write_text(json.dumps(params))
    report2 = run(part)

    assert report2["overall"] == "FAIL"
    assert report2["promoted"] is False
    assert accepted.read_bytes() == original_bytes, "accepted STEP clobbered by failed attempt"
    assert (part / "exports" / "widget_v1_report.json").read_text() == original_report


def test_no_promote_flag_leaves_exports_untouched(tmp_path):
    part = make_part(tmp_path, spec=box_spec())
    report = run(part, promote=False)
    assert report["overall"] == "PASS"
    assert report["promoted"] is False
    assert not accepted_step(part).exists()


# ---------------------------------------------------------------------------
# --init-spec draft scaffolding
# ---------------------------------------------------------------------------
def test_init_spec_drafts_from_measured_geometry(tmp_path):
    from lib.evaluate import init_spec

    part = make_part(tmp_path, model_body=HOLED_MODEL)
    spec_path = init_spec(part, quiet=True)
    spec = json.loads(spec_path.read_text())

    assert spec["solid_count"] == 1
    bbox_x = next(d for d in spec["dimensions"]
                  if d["kind"] == "bbox" and d["axis"] == "x")
    assert abs(bbox_x["expected"] - 10.0) < 0.01
    assert all(d.get("unresolved") for d in spec["dimensions"]), (
        "every drafted value must demand review")
    cyl = [d for d in spec["dimensions"] if d["kind"] == "cylinder"]
    assert any(abs(d["diameter"] - 4.0) < 0.01 for d in cyl), "the bore must be drafted"

    # A draft must not be able to PASS the gate untouched
    report = run(part)
    assert report["overall"] == "ERROR"
    assert report["promoted"] is False


def test_init_spec_refuses_overwrite_without_force(tmp_path):
    import pytest

    from lib.evaluate import init_spec

    part = make_part(tmp_path, spec=box_spec())
    with pytest.raises(ValueError, match="already exists"):
        init_spec(part, quiet=True)
    init_spec(part, force=True, quiet=True)  # explicit force is allowed
    assert json.loads((part / "spec.json").read_text())["solid_count"] == 1


def test_init_spec_resolved_draft_passes(tmp_path):
    """The intended loop: draft -> review (drop unresolved) -> gate passes."""
    from lib.evaluate import init_spec

    part = make_part(tmp_path)
    spec_path = init_spec(part, quiet=True)
    spec = json.loads(spec_path.read_text())
    for d in spec["dimensions"]:
        d.pop("unresolved", None)
    spec["unresolved"] = []
    spec_path.write_text(json.dumps(spec))

    report = run(part)
    assert report["overall"] == "PASS"
    assert report["promoted"] is True


# ---------------------------------------------------------------------------
# Part resolution
# ---------------------------------------------------------------------------
def test_unknown_part_raises_value_error(tmp_path):
    from lib.evaluate import resolve_part_dir

    with pytest.raises(ValueError, match="part not found"):
        resolve_part_dir("no-such-part-anywhere")
    empty = tmp_path / "no_model"
    empty.mkdir()
    with pytest.raises(ValueError, match="no model.py"):
        resolve_part_dir(str(empty))
