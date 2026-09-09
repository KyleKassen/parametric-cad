"""Tie the independent final enclosure audit to current R2 parameters and STEP."""

import hashlib
import json
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
R2 = HERE.parents[1]
R1 = R2.parent / "sce20-layout"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    fit = json.loads((HERE / "candidate_fit.json").read_text())
    params = json.loads((R2 / "params.json").read_text())
    evaluation = json.loads((R2 / "exports/repository_full_evaluation.json").read_text())
    for name, placement in fit["placements"].items():
        assert params["placements"][name] == placement, name
    root_panel = R2 / "exports/Backpanel_R2.step"
    # The evaluation reports its isolated attempt rather than promoting geometry.
    evaluation_panel = R2.parents[2] / evaluation["artifacts"]["step"]
    a = cq.importers.importStep(str(root_panel)).val()
    b = cq.importers.importStep(str(evaluation_panel)).val()
    difference = abs(a.cut(b).Volume()) + abs(b.cut(a).Volume())
    assert difference < 1e-6, difference
    inputs = [
        R2 / "params.json",
        R2 / "spec.json",
        root_panel,
        evaluation_panel,
        R2 / "exports/repository_full_evaluation.json",
        R1 / "references/enclosure/source_enclosure.brep",
        *[Path(p) for p in fit["inputs"].values()],
    ]
    report = {
        "schema": "sce20-stacked-r2-enclosure-input-evidence/1",
        "status": "PASS",
        "placements_match_current_params": True,
        "backpanel_vs_evaluation_symmetric_difference_mm3": difference,
        "independent_enclosure_status": fit["status"],
        "repository_evaluation_overall_status": evaluation["overall"],
        "repository_design_score": next(
            check["measured"]
            for check in evaluation["checks"]
            if check["id"] == "design_review.score"
        ),
        "repository_design_min_score": 70,
        "repository_design_gate_status": "FAIL",
        "sha256": {str(p): digest(p) for p in inputs},
    }
    (HERE / "final_input_evidence.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "sha256"}, indent=2))


if __name__ == "__main__":
    main()
