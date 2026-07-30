"""
Agent-facing part evaluation pipeline: build -> export -> re-import -> validate
-> render -> report -> promote.

One command takes a part directory (any parts/*/<name>/ with a model.py that
defines create_part(params=None)), builds it, exports the result to an
attempt-specific STEP file under exports/attempts/<attempt-id>/, re-imports
that artifact, and validates the ARTIFACT (never just the in-memory object):

  - BREP validity (BRepCheck via Shape.isValid)
  - non-empty geometry (>= 1 solid, positive volume)
  - expected solid count           (spec.json: solid_count)
  - dimensional requirements       (spec.json: dimensions[] -- bbox / volume /
                                    cylinder-feature checks, each with
                                    tolerances and hard/soft severity)
  - part-specific validators       (spec.json: validators[] -- scripts such as
                                    the OZ51x fit_check.py; exit 0 = PASS)
  - design refinement              (spec.json: design{} -- lib/design_review.py
                                    measures edge breaks, blank faces, fastener
                                    rhythm, radius vocabulary ... on the same
                                    re-imported artifact and scores them 0-100)

Standardized verification renders of the exported artifact are produced in the
attempt directory; --product-render adds studio hero renders alongside them. A
machine-readable report (schema "part-eval/2") with per-check
PASS / FAIL / ERROR results is written to
exports/attempts/<attempt-id>/report.json. The full numeric design review lands
in that report under "design" (a "design-review/2" document, plus a "gate" key
recording the bar it was held to), so an agent can read every metric, value and
finding without re-running anything.

The exported STEP is promoted to the accepted location
exports/<part>_<version>.step (plus _report.json, _views/ and, with
--product-render, _product_views/) ONLY when every hard check passes. Failed or
incomplete attempts never touch accepted outputs.

Exit status: 0 = all hard checks PASS, 1 = at least one hard FAIL,
2 = a hard check ERRORed or could not be evaluated.

Usage:
    uv run python -m lib.evaluate PART [--json out.json] [--views iso,front,top]
                                  [--size 900] [--no-render] [--no-promote]
                                  [--no-design] [--design-min-score N]
                                  [--product-render [--product-views hero,...]]

    PART is a part directory (parts/custom/x) or a bare part name searched
    under parts/custom/ and parts/vendor/ (plus parts/_template).

Units: mm. spec.json schema: see README "Agent evaluation workflow".
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import cadquery as cq

from lib.analyze_step import _cylinder_features

PROJECT_ROOT = Path(__file__).parent.parent

DEFAULT_VIEWS = ("iso", "front", "top")
DEFAULT_PRODUCT_VIEWS = ("hero",)
DEFAULT_TOL = 0.1  # mm, when a dimension gives "expected" without "tol"
VALIDATOR_TIMEOUT = 900  # seconds

# The bar a part is held to when its spec.json says nothing about design. It is
# advisory: the check is emitted at SOFT severity, so every part in the repo
# reports its refinement number and lands in report["warnings"] when it is
# short, without the gate breaking builds that predate the gate. A part opts in
# by writing "design": {"min_score": N}, and that is what makes it hard -- a
# part that states a bar has chosen to be held to it.
DESIGN_ADVISORY_MIN_SCORE = 70.0

PASS, FAIL, ERROR = "PASS", "FAIL", "ERROR"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _rel(path: Path) -> str:
    """Project-relative posix path when possible (stable in reports)."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _check(check_id: str, status: str, message: str, severity: str = "hard", **extra) -> dict:
    return {"id": check_id, "status": status, "severity": severity, "message": message, **extra}


def _bounds(dim: dict) -> tuple[float, float]:
    """Accepted [lo, hi] range: explicit min/max, or expected +/- tol."""
    if "min" in dim or "max" in dim:
        return dim.get("min", -math.inf), dim.get("max", math.inf)
    expected = dim["expected"]
    tol = dim.get("tol", DEFAULT_TOL)
    return expected - tol, expected + tol


def _range_str(dim: dict) -> str:
    if "min" in dim or "max" in dim:
        return f"[{dim.get('min', '-inf')}, {dim.get('max', 'inf')}]"
    return f"{dim['expected']} +/- {dim.get('tol', DEFAULT_TOL)}"


def resolve_part_dir(arg: str) -> Path:
    """Accept a part directory path or a bare name under parts/."""
    p = Path(arg)
    if p.is_dir():
        if (p / "model.py").exists():
            return p.resolve()
        raise ValueError(f"{arg} has no model.py -- not a buildable part directory")
    for group in ("custom", "vendor", "."):
        cand = PROJECT_ROOT / "parts" / group / arg
        if (cand / "model.py").exists():
            return cand.resolve()
    raise ValueError(
        f"part not found: {arg!r} -- pass a directory containing model.py, "
        f"or a name under parts/custom/ or parts/vendor/"
    )


def load_part_module(part_dir: Path):
    model_path = part_dir / "model.py"
    spec = importlib.util.spec_from_file_location(f"parts.{part_dir.name}.model", model_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_step(shape, path: Path) -> None:
    """Export a built part to STEP. Module-level so tests can monkeypatch it."""
    cq.exporters.export(shape, str(path))


# ---------------------------------------------------------------------------
# Spec (acceptance requirements) — spec.json next to model.py, all optional
# ---------------------------------------------------------------------------
def load_spec(part_dir: Path) -> tuple[dict | None, list[dict]]:
    """Return (spec, error_checks). A broken spec is an ERROR, never ignored."""
    spec_path = part_dir / "spec.json"
    if not spec_path.exists():
        return None, []
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return None, [_check("spec", ERROR, f"spec.json unreadable: {e}")]

    errors = []
    units = spec.get("units", "mm")
    if units != "mm":
        errors.append(_check("spec", ERROR, f"unsupported units {units!r} (only mm)"))
    for dim in spec.get("dimensions", []):
        if "id" not in dim or "kind" not in dim:
            errors.append(_check("spec", ERROR, f"dimension entry missing id/kind: {dim}"))
    return spec, errors


# ---------------------------------------------------------------------------
# Design refinement contract - spec.json "design", all optional
# ---------------------------------------------------------------------------
def _design_metric_ids() -> set[str]:
    """
    Known metric ids, or an empty set if lib/design_review.py cannot load.

    METRIC_IDS, not one role's weights: a waiver for a metric that this part's
    ROLE does not use should still resolve to a known id, so the author gets
    "this role does not use that metric" rather than "unknown metric".
    """
    try:
        from lib.design_review import METRIC_IDS

        return set(METRIC_IDS)
    except Exception:
        return set()


def _design_roles() -> tuple[str, ...]:
    """Known role names, or () if lib/design_review.py cannot load."""
    try:
        from lib.design_review import ROLES

        return tuple(ROLES)
    except Exception:
        return ()


def _design_waivers(raw, known: set[str]) -> tuple[dict[str, str], list[dict]]:
    """
    Normalize the waivers block to {metric: reason}, accepting either
    {"symmetry": "why"} or [{"metric": "symmetry", "reason": "why"}].

    A reason is REQUIRED, and an unknown metric id is an error rather than a
    no-op. A metric that drops out of the score with nobody's name on it, or a
    waiver that silently waives nothing because of a typo, is exactly how a
    standard rots - so both are spec errors, hard, like any other malformed spec.
    """
    errors: list[dict] = []
    if raw is None:
        return {}, errors
    entries: list[tuple] = []
    if isinstance(raw, dict):
        entries = list(raw.items())
    elif isinstance(raw, list):
        for i, item in enumerate(raw):
            if isinstance(item, dict) and ("metric" in item or "id" in item):
                entries.append((item.get("metric", item.get("id")), item.get("reason")))
            else:
                errors.append(
                    _check(
                        "design_spec",
                        ERROR,
                        f"design.waivers[{i}] must be an object with 'metric' and 'reason'",
                    )
                )
    else:
        return {}, [
            _check("design_spec", ERROR, 'design "waivers" must be an object or a list of objects')
        ]

    waivers: dict[str, str] = {}
    for metric, reason in entries:
        if not isinstance(metric, str) or not metric.strip():
            errors.append(
                _check("design_spec", ERROR, f"design waiver has no metric id: {reason!r}")
            )
            continue
        metric = metric.strip()
        if not isinstance(reason, str) or not reason.strip():
            errors.append(
                _check(
                    "design_spec",
                    ERROR,
                    f"design waiver for {metric!r} has no reason -- every waiver needs a "
                    f"written justification, so waiving a metric is deliberate",
                )
            )
            continue
        if known and metric not in known:
            errors.append(
                _check(
                    "design_spec",
                    ERROR,
                    f"design waiver names unknown metric {metric!r} "
                    f"(known: {', '.join(sorted(known))})",
                )
            )
            continue
        waivers[metric] = reason.strip()
    return waivers, errors


def design_config(spec: dict | None) -> tuple[dict | None, list[dict], dict]:
    """
    Resolve the spec.json "design" block into a lib/design_review.py config.

    Returns (config, error_checks, gate). config is None ONLY when the part
    opts out with "design": {"enabled": false} - an absent block is not opting
    out: the review still runs, at soft severity against DESIGN_ADVISORY_
    MIN_SCORE, so a part written before this gate existed reports its number
    and warns instead of failing.

    Accepted keys (every one optional):

        "design": {
          "enabled":     true,             # false skips the review entirely
          "role":        "enclosure",      # enclosure|cover|plate|bracket|sheet|structural
          "min_score":   70,               # overall bar 0-100; PRESENT = opt-in
          "severity":    "hard",           # default hard when min_score is set
          "metric_severity": "soft",       # default for per-metric gates
          "symmetry_max_faces": 6000,      # cost guard; tripping it is an ERROR
          "waivers": {"symmetry": "handed part - mirrored variant by design"},
          "metrics": {"edge_break_coverage": {"min_score": 80, "severity": "hard"},
                      "face_composition":    {"max_value": 0.35},
                      "pattern_discipline":  {"enabled": false,
                                              "reason": "welded, not bolted"}}
        }

    "design_review" is accepted as an alias for "design" (it is the name
    lib/design_review.py documents for the same block).

    "role" selects the rubric: which metrics apply, their weights and their
    thresholds. Absent means "enclosure", which is deliberately the STRICTEST
    rubric - claiming a lighter one must always be an explicit act. An unknown
    role is a hard spec ERROR, for the same reason an unknown metric id is: a
    typo must never quietly buy a part a different standard. A role is also a
    claim about the GEOMETRY, and lib/design_review.py checks it against the
    measured B-rep: a `cover` that is not thin, a `sheet` part that encloses a
    void, and a `sheet` part with no bend radius at all - a flat blank claiming
    the blanked-perimeter exclusion that the formed radii are supposed to pay
    for - are all role ERRORs and are re-judged as an `enclosure`.

    There is no "turned" role and nothing to declare for one. A body of
    revolution - a shaft, a spacer, a standoff, a bushing, a knob, a gland, a
    spool - is DETECTED, and while it has nothing off its axis
    feature_composition and pattern_discipline are measured on its MERIDIAN
    PROFILE rather than on a feature layout it does not have: how many distinct
    diameters it is turned to, and whether its shoulder roots are radiused,
    chamfered or left square. The gate used to read every part in that class as
    defective for having no bolt pattern, which taught agents to drill holes
    nothing needs; it then EXCUSED the two metrics instead, which renormalised
    0.28 of the rubric out of the mean and handed a chamfered bar band A. Both
    metrics are scored on every turned part, so nothing is free and no turned
    part is ever coached towards a bolt pattern. An off-axis hole on a turned
    part is judged like any other hole.

    There is no "weights" key and no "style.radius_ladder" key. Writing either
    is a hard spec ERROR - see lib.design_review.RETIRED_CONFIG_KEYS for the
    measurements that killed them. Both were the same defect: a part declaring
    the standard it is measured against.

    Nothing in this block can lower a RUBRIC FLOOR. A floored metric cannot be
    waived or disabled, and a per-metric min_score below its floor is a spec
    ERROR - see lib.design_review.RUBRIC_FLOORS. An unmet floor caps the
    reported band at "D" and fails the score check at every severity, and its
    own check is emitted at the OVERALL severity, so a part that opted in with a
    min_score fails HARD while a part that predates the gate still only warns.
    "metric_severity" never reaches a floor: "this metric does not matter to me"
    is the one claim a floor exists to refuse.
    """
    errors: list[dict] = []
    raw = None
    if isinstance(spec, dict):
        raw = spec.get("design", spec.get("design_review"))
    if raw is not None and not isinstance(raw, dict):
        errors.append(_check("design_spec", ERROR, 'spec.json "design" must be an object'))
        raw = None
    block = dict(raw or {})

    gate = {
        "source": "spec.json design block" if raw is not None else "default (no design block)",
        "opted_in": "min_score" in block,
        "severity_explicit": "severity" in block,
        "enabled": block.get("enabled", True) is not False,
    }
    if not gate["enabled"]:
        gate["reason"] = 'opted out with "enabled": false'
        return None, errors, gate

    known = _design_metric_ids()
    waivers, waiver_errors = _design_waivers(block.get("waivers"), known)
    errors += waiver_errors
    metrics = block.get("metrics") or {}
    if not isinstance(metrics, dict):
        errors.append(_check("design_spec", ERROR, 'design "metrics" must be an object'))
        metrics = {}
    for mid in metrics:
        if known and mid not in known:
            errors.append(
                _check(
                    "design_spec",
                    ERROR,
                    f"design.metrics names unknown metric {mid!r} "
                    f"(known: {', '.join(sorted(known))})",
                )
            )

    roles = _design_roles()
    role = block.get("role", "enclosure")
    if not isinstance(role, str) or (roles and role not in roles):
        errors.append(
            _check(
                "design_spec",
                ERROR,
                f"design names unknown role {role!r} "
                f"(known: {', '.join(roles) if roles else 'unavailable'})",
            )
        )
        role = "enclosure"

    cfg = dict(block)
    cfg["role"] = role
    cfg["waivers"] = waivers
    cfg["metrics"] = metrics

    # One validator, not two. lib/design_review.py owns what the config surface
    # accepts (retired keys, waiver reasons, the symmetry cost guard, the radius
    # ladder); the audit found this file and that one disagreeing about it, and
    # when two gates disagree the looser one is the gate. Its verdicts are
    # raised here as HARD spec errors, because a part that never set a
    # min_score would otherwise hear about a rejected key at soft severity.
    try:
        from lib.design_review import config_errors as _design_config_errors

        for message in _design_config_errors(cfg):
            errors.append(_check("design_spec", ERROR, message))
    except ImportError:
        pass

    cfg["min_score"] = float(block.get("min_score", DESIGN_ADVISORY_MIN_SCORE))
    # Opting in is what makes the gate hard; silence stays advisory.
    cfg["severity"] = block.get("severity", "hard" if gate["opted_in"] else "soft")
    cfg["metric_severity"] = block.get("metric_severity", cfg["severity"])
    gate.update(
        min_score=cfg["min_score"],
        severity=cfg["severity"],
        metric_severity=cfg["metric_severity"],
        role=role,
        role_explicit="role" in block,
        waivers=waivers,
        advisory=not gate["opted_in"],
    )
    return cfg, errors, gate


def _axis_line_distance(feature: dict, pt: list[float]) -> float:
    """
    Distance from a point to a cylinder feature's infinite axis LINE.

    Deliberately the line, not the segment: position along the axis is
    unconstrained (a hole's depth doesn't matter for "is it on the correct
    side"), which is exactly the handedness question and keeps authoring easy.
    """
    p1, d = feature["p1"], feature["dir"]
    v = [pt[i] - p1[i] for i in range(3)]
    c = [v[1] * d[2] - v[2] * d[1], v[2] * d[0] - v[0] * d[2], v[0] * d[1] - v[1] * d[0]]
    dlen = math.sqrt(sum(x * x for x in d)) or 1.0
    return math.sqrt(sum(x * x for x in c)) / dlen


def _eval_dimension(dim: dict, geo: dict) -> dict:
    """Evaluate one spec dimension against the re-imported artifact geometry."""
    severity = dim.get("severity", "hard")
    check_id = f"dim:{dim.get('id', '?')}"
    kind = dim.get("kind")

    if dim.get("unresolved") or (
        kind in ("bbox", "volume")
        and "expected" not in dim
        and "min" not in dim
        and "max" not in dim
    ):
        return _check(
            check_id,
            ERROR,
            "unresolved value -- resolve the spec before acceptance",
            severity,
            kind=kind,
        )

    if kind == "bbox":
        axis = dim.get("axis", "").lower()
        if axis not in ("x", "y", "z"):
            return _check(check_id, ERROR, f"bbox check needs axis x|y|z, got {axis!r}", severity)
        measured = geo["bbox_size"]["xyz".index(axis)]
        lo, hi = _bounds(dim)
        ok = lo <= measured <= hi
        return _check(
            check_id,
            PASS if ok else FAIL,
            f"bbox {axis} = {measured:.3f} mm (accept {_range_str(dim)})",
            severity,
            kind=kind,
            measured=round(measured, 3),
        )

    if kind == "volume":
        measured = geo["volume"]
        lo, hi = _bounds(dim)
        ok = lo <= measured <= hi
        return _check(
            check_id,
            PASS if ok else FAIL,
            f"volume = {measured:.1f} mm^3 (accept {_range_str(dim)})",
            severity,
            kind=kind,
            measured=round(measured, 1),
        )

    if kind == "cylinder":
        expected_d = dim.get("diameter")
        if expected_d is None:
            return _check(check_id, ERROR, "cylinder check needs 'diameter'", severity)
        tol = dim.get("tol", DEFAULT_TOL)
        axis = dim.get("axis")
        ftype = dim.get("type")
        count_min = dim.get("count_min", 1)
        matches = [
            f
            for f in geo["features"]
            if abs(f["diameter"] - expected_d) <= tol
            and (axis is None or f["axis_label"] == axis)
            and (ftype is None or f["type"] == ftype)
        ]
        ok = len(matches) >= count_min
        what = (
            f"d={expected_d}+/-{tol}"
            + (f" {axis}-axis" if axis else "")
            + (f" {ftype}" if ftype else "")
        )
        return _check(
            check_id,
            PASS if ok else FAIL,
            f"{len(matches)} cylinder feature(s) matching {what} (need >= {count_min})",
            severity,
            kind=kind,
            measured=len(matches),
        )

    if kind == "cylinder_at":
        expected_d, at = dim.get("diameter"), dim.get("at")
        if expected_d is None or at is None:
            return _check(
                check_id, ERROR, "cylinder_at needs 'diameter' and 'at' [x, y, z]", severity
            )
        tol = dim.get("tol", DEFAULT_TOL)
        pos_tol = dim.get("pos_tol", 1.0)
        axis = dim.get("axis")
        ftype = dim.get("type")
        best = None
        for f in geo["features"]:
            if abs(f["diameter"] - expected_d) > tol:
                continue
            if axis is not None and f["axis_label"] != axis:
                continue
            if ftype is not None and f["type"] != ftype:
                continue
            d = _axis_line_distance(f, at)
            if best is None or d < best:
                best = d
        what = (
            f"d={expected_d}+/-{tol}"
            + (f" {axis}-axis" if axis else "")
            + (f" {ftype}" if ftype else "")
        )
        if best is None:
            return _check(
                check_id,
                FAIL,
                f"no cylinder matching {what} anywhere in the artifact",
                severity,
                kind=kind,
            )
        ok = best <= pos_tol
        return _check(
            check_id,
            PASS if ok else FAIL,
            f"nearest {what} axis is {best:.3f} mm from {at} (allow <= {pos_tol})",
            severity,
            kind=kind,
            measured=round(best, 3),
        )

    return _check(check_id, ERROR, f"unknown dimension kind {kind!r}", severity, kind=kind)


def _run_validator(v: dict, part_dir: Path, step_path: Path, attempt_dir: Path) -> dict:
    """Run one part-specific validator script. exit 0 = PASS, nonzero = FAIL."""
    severity = v.get("severity", "hard")
    check_id = f"validator:{v.get('id', v.get('script', '?'))}"
    script = part_dir / v.get("script", "")
    if not script.is_file():
        return _check(check_id, ERROR, f"validator script not found: {v.get('script')}", severity)

    env = dict(
        os.environ,
        PYTHONUTF8="1",
        EVAL_STEP_PATH=str(step_path),
        EVAL_PART_DIR=str(part_dir),
        EVAL_ATTEMPT_DIR=str(attempt_dir),
    )
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=v.get("timeout", VALIDATOR_TIMEOUT),
        )
    except subprocess.TimeoutExpired:
        return _check(
            check_id,
            ERROR,
            f"validator timed out after {v.get('timeout', VALIDATOR_TIMEOUT)}s",
            severity,
        )
    except OSError as e:
        return _check(check_id, ERROR, f"validator could not run: {e}", severity)

    log_path = attempt_dir / f"{check_id.replace(':', '_').replace('/', '_')}.log"
    log_path.write_text(
        proc.stdout + ("\n--- stderr ---\n" + proc.stderr if proc.stderr else ""), encoding="utf-8"
    )
    if proc.returncode == 0:
        return _check(check_id, PASS, f"exit 0 (log: {_rel(log_path)})", severity)
    tail = "; ".join(line.strip() for line in (proc.stdout + proc.stderr).strip().splitlines()[-3:])
    return _check(
        check_id,
        FAIL,
        f"exit {proc.returncode}: {tail} (log: {_rel(log_path)})",
        severity,
        exit_code=proc.returncode,
    )


# ---------------------------------------------------------------------------
# Promotion — accepted outputs are replaced only by a fully passing attempt
# ---------------------------------------------------------------------------
def _atomic_copy(src: Path, dst: Path) -> None:
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def _promote(
    part_dir: Path,
    name: str,
    version: str,
    step_path: Path,
    render_paths: list[Path],
    product_paths: list[Path] | None = None,
) -> dict:
    exports = part_dir / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    accepted_step = exports / f"{name}_{version}.step"
    _atomic_copy(step_path, accepted_step)

    def copy_all(paths: list[Path], suffix: str) -> list[str]:
        if not paths:
            return []
        dest_dir = exports / f"{name}_{version}_{suffix}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = []
        for p in paths:
            dst = dest_dir / p.name
            _atomic_copy(p, dst)
            out.append(_rel(dst))
        return out

    return {
        "step": _rel(accepted_step),
        "report": _rel(exports / f"{name}_{version}_report.json"),
        "views": copy_all(render_paths, "views"),
        # "..._product_views" rather than "..._product" so the accepted hero
        # renders fall under the repo's existing **/exports/*_views/ ignore rule
        # - a generated artifact must not start showing up in git status.
        "product": copy_all(list(product_paths or []), "product_views"),
    }


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------
def _say_design(review: dict | None, say, top_findings: int = 3) -> None:
    """
    Console summary of the design review: sub-scores, then the ranked findings.

    The findings are the actionable half - "score 31" tells an agent it failed,
    "7724 mm of unbroken convex edge" tells it what to do - so they are printed
    even though the full list is in the report JSON.
    """
    if not review or review.get("status") in ("skipped", "error"):
        return
    metrics = review.get("metrics") or {}
    for err in review.get("config_errors") or []:
        say(f"   design CONFIG ERROR: design.{err.get('key')}: {err.get('message')}")
    if review.get("role_error"):
        say(f"   design ROLE ERROR: {review['role_error']}")
    if review.get("score") is not None:
        role = review.get("role") or "?"
        article = "an" if role[:1].lower() in "aeiou" else "a"
        say(
            f"   design: {review['score']:.1f}/100  band {review.get('band')} "
            f"({review.get('band_label')})  as {article} {role}, "
            f"measured weight {review.get('coverage', 0) * 100:.0f}%"
        )
    # "absent" and "not required" now mean OPPOSITE things - one is a defect
    # scored 0 at full weight, the other is renormalised out - so they must
    # never render the same way.
    label = {"scored": None, "not_required": "  n/r", "absent_defect": "ABSENT", "error": "ERROR"}
    for mid, m in metrics.items():
        score = (
            f"{m['score']:5.1f}"
            if m.get("status") == "scored" and m.get("score") is not None
            else f"{label.get(m.get('status'), m.get('status', '?')):>6}"
        )
        say(f"           {score}  {mid:<21} {m.get('message', '')}")
    # The floors and the configuration delta are the two things this summary
    # exists to make unmissable. A floor is why a part cannot pass no matter
    # what the mean says, and the delta is the sentence that used to be absent
    # entirely: how much of the score is the spec.json rather than the part.
    for f in review.get("floors") or []:
        if f.get("met"):
            say(f"           floor OK  {f['metric']:<21} {f['detail']}")
        else:
            say(f"           FLOOR UNMET  {f['metric']}: {f['detail']}")
            say(
                f"                        band capped at {review.get('band')} (measured "
                f"{review.get('band_uncapped')}) - a floor cannot be waived or averaged away"
            )
    cd = review.get("config_delta") or {}
    if cd.get("knobs"):
        say(f"           config: {cd.get('message')}")
        if not cd.get("within_cap", True):
            say(f"           CONFIG ERROR: over the {cd.get('cap')}-point cap")
    findings = review.get("findings") or []
    for f in findings[:top_findings]:
        say(f"           -> [{f.get('severity', '?')}] {f.get('message', '')}")
    if len(findings) > top_findings:
        say(f"           -> ... {len(findings) - top_findings} more finding(s) in the report JSON")


def evaluate_part(
    part: str | Path,
    views: tuple[str, ...] = DEFAULT_VIEWS,
    size: int = 900,
    render: bool = True,
    promote: bool = True,
    json_out: str | Path | None = None,
    quiet: bool = False,
    design: bool = True,
    design_min_score: float | None = None,
    product_render: bool = False,
    product_views: tuple[str, ...] = DEFAULT_PRODUCT_VIEWS,
    product_size: int = 1600,
) -> dict:
    """
    Run the full evaluation pipeline. Returns the report dict (see schema).

    design=False skips the refinement review entirely (it costs seconds on a
    dense part); design_min_score overrides the bar from the command line for a
    one-off, without editing the part's spec.json.
    """

    def say(line: str) -> None:
        if not quiet:
            print(line)

    part_dir = resolve_part_dir(str(part))
    name = part_dir.name
    attempt_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    attempt_dir = part_dir / "exports" / "attempts" / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)

    checks: list[dict] = []
    report: dict = {
        "schema": "part-eval/2",
        "part": name,
        "part_dir": _rel(part_dir),
        "attempt_id": attempt_id,
        "attempt_dir": _rel(attempt_dir),
        "started": datetime.now().isoformat(timespec="seconds"),
        "checks": checks,
        "promoted": False,
        "accepted": None,
        "artifacts": {},
    }

    spec, spec_errors = load_spec(part_dir)
    checks.extend(spec_errors)
    report["spec"] = _rel(part_dir / "spec.json") if (part_dir / "spec.json").exists() else None
    if spec:
        report["assumptions"] = spec.get("assumptions", [])
        report["unresolved"] = spec.get("unresolved", [])

    say(f"== evaluate: {name} ==")
    say(f"   attempt: {attempt_id}")

    aborted = False
    step_path: Path | None = None
    render_paths: list[Path] = []
    product_paths: list[Path] = []

    # -- build ---------------------------------------------------------------
    version = "v1"
    result = None
    try:
        module = load_part_module(part_dir)
        if not hasattr(module, "create_part"):
            raise AttributeError("model.py has no create_part(params=None)")
        params = None
        if hasattr(module, "load_params"):
            params = module.load_params()
        elif (part_dir / "params.json").exists():
            params = json.loads((part_dir / "params.json").read_text(encoding="utf-8"))
        if isinstance(params, dict):
            version = params.get("version", "v1")
        t0 = time.perf_counter()
        result = module.create_part(params)
        checks.append(_check("build", PASS, f"create_part() ok in {time.perf_counter() - t0:.1f}s"))
    except Exception as e:
        checks.append(_check("build", ERROR, f"{type(e).__name__}: {e}"))
        aborted = True
    report["version"] = version

    # -- export to the attempt-specific STEP ----------------------------------
    if not aborted:
        step_path = attempt_dir / f"{name}_{version}.step"
        try:
            export_step(result, step_path)
            if not step_path.is_file() or step_path.stat().st_size == 0:
                raise RuntimeError("exporter wrote no data")
            checks.append(
                _check("export", PASS, f"{_rel(step_path)} ({step_path.stat().st_size // 1024} KB)")
            )
            report["artifacts"]["step"] = _rel(step_path)
        except Exception as e:
            checks.append(_check("export", ERROR, f"{type(e).__name__}: {e}"))
            aborted = True

    # -- re-import; all geometry checks run on THIS shape, not the in-memory one
    geo: dict | None = None
    if not aborted:
        try:
            wp = cq.importers.importStep(str(step_path))
            vals = wp.vals()
            shape = vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)
            solids = wp.solids().vals() if vals else []
            bb = shape.BoundingBox()
            geo = {
                "shape": shape,
                "solid_count": len(solids),
                "volume": sum(abs(s.Volume()) for s in solids),
                "bbox_size": (bb.xlen, bb.ylen, bb.zlen),
            }
            checks.append(
                _check(
                    "reimport",
                    PASS,
                    f"{geo['solid_count']} solid(s), volume {geo['volume']:.1f} mm^3, "
                    f"bbox {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm",
                )
            )
        except Exception as e:
            checks.append(
                _check(
                    "reimport",
                    ERROR,
                    f"exported STEP failed to re-import -- {type(e).__name__}: {e}",
                )
            )
            aborted = True

    if not aborted:
        report["geometry"] = {
            "solid_count": geo["solid_count"],
            "volume_mm3": round(geo["volume"], 1),
            "bbox_size": [round(v, 3) for v in geo["bbox_size"]],
        }

        # baseline hard checks (always run, spec or no spec)
        valid = geo["shape"].isValid()
        checks.append(
            _check(
                "brep_valid",
                PASS if valid else FAIL,
                "BRepCheck_Analyzer " + ("passed" if valid else "REJECTED the shape"),
            )
        )
        non_empty = geo["solid_count"] >= 1 and geo["volume"] > 0
        checks.append(
            _check(
                "non_empty",
                PASS if non_empty else FAIL,
                f"{geo['solid_count']} solid(s), volume {geo['volume']:.1f} mm^3"
                + ("" if non_empty else " -- empty export is a failure"),
            )
        )

        if spec:
            if "solid_count" in spec:
                ok = geo["solid_count"] == spec["solid_count"]
                checks.append(
                    _check(
                        "solid_count",
                        PASS if ok else FAIL,
                        f"{geo['solid_count']} solid(s), expected {spec['solid_count']}",
                        measured=geo["solid_count"],
                        expected=spec["solid_count"],
                    )
                )
            dims = spec.get("dimensions", [])
            if any(d.get("kind") in ("cylinder", "cylinder_at") for d in dims):
                geo["features"] = _cylinder_features(geo["shape"])
            for dim in dims:
                checks.append(_eval_dimension(dim, geo))

    # -- part-specific validators (run even alongside geometry FAILs, so the
    #    agent gets the full picture in one attempt; skipped when aborted) -----
    if not aborted and spec:
        for v in spec.get("validators", []):
            checks.append(_run_validator(v, part_dir, step_path, attempt_dir))

    # -- declarative fit cases (spec.json "fit" block) -------------------------
    fit_scene: list = []
    if not aborted and spec and spec.get("fit"):
        try:
            from lib.fit import run_fit

            fit_checks, fit_scene = run_fit(spec["fit"], part_dir)
            checks.extend(fit_checks)
        except Exception as e:
            checks.append(_check("fit", ERROR, f"{type(e).__name__}: {e}"))

    # -- design refinement review of the SAME re-imported artifact -------------
    #    Measured, not asserted: lib/design_review.py scores edge breaks, blank
    #    faces, fastener rhythm and the rest off the exported B-rep. Severity is
    #    soft unless the part opted in (see design_config), so switching the
    #    gate on cannot fail a part that never agreed to be measured -- it only
    #    lands in report["warnings"].
    if not aborted and design:
        cfg, cfg_errors, gate = design_config(spec)
        checks.extend(cfg_errors)
        if design_min_score is not None and cfg is not None:
            # Naming a bar on the command line is the same act as writing
            # min_score into spec.json, so the override is hard too -- unless
            # the spec explicitly chose a severity, which stays the author's.
            cfg["min_score"] = float(design_min_score)
            if not gate.get("severity_explicit"):
                cfg["severity"] = "hard"
            gate.update(
                min_score=cfg["min_score"],
                severity=cfg["severity"],
                advisory=False,
                source="--design-min-score override",
            )
        if cfg is None:
            report["design"] = {
                "gate": gate,
                "status": "skipped",
                "message": gate.get("reason", "design review disabled"),
            }
        else:
            try:
                from lib.design_review import design_review_checks, review_shape

                t0 = time.perf_counter()
                review = review_shape(geo["shape"], source=_rel(step_path), config=cfg)
                gate["elapsed_s"] = round(time.perf_counter() - t0, 2)
                review["gate"] = gate
                report["design"] = review
                checks.extend(design_review_checks(review, cfg))
            except Exception as e:
                checks.append(
                    _check(
                        "design_review",
                        ERROR,
                        f"{type(e).__name__}: {e}",
                        gate.get("severity", "soft"),
                    )
                )
                report["design"] = {
                    "gate": gate,
                    "status": "error",
                    "message": f"{type(e).__name__}: {e}",
                }

    # -- standardized renders of the exported artifact ------------------------
    if not aborted and render:
        try:
            from lib.render_step import render_file

            render_paths = render_file(
                step_path, out_dir=attempt_dir / "views", views=views, size=size
            )
            if fit_scene and spec.get("fit", {}).get("render"):
                from lib.fit import render_fit_scene

                render_paths += render_fit_scene(fit_scene, attempt_dir / "views", size=size)
            checks.append(
                _check(
                    "render", PASS, f"{len(render_paths)} view(s) -> {_rel(attempt_dir / 'views')}"
                )
            )
            report["artifacts"]["views"] = [_rel(p) for p in render_paths]
        except Exception as e:
            checks.append(_check("render", ERROR, f"{type(e).__name__}: {e}"))

    # -- studio hero renders (opt-in; soft because presentation is not acceptance)
    if not aborted and render and product_render:
        try:
            from lib.render_step import render_file

            product_paths = render_file(
                step_path,
                out_dir=attempt_dir / "product",
                views=product_views,
                size=product_size,
                quality="product",
            )
            checks.append(
                _check(
                    "render_product",
                    PASS,
                    f"{len(product_paths)} hero view(s) -> {_rel(attempt_dir / 'product')}",
                    "soft",
                )
            )
            report["artifacts"]["product_views"] = [_rel(p) for p in product_paths]
        except Exception as e:
            checks.append(_check("render_product", ERROR, f"{type(e).__name__}: {e}", "soft"))

    # -- verdict ---------------------------------------------------------------
    hard = [c for c in checks if c.get("severity", "hard") == "hard"]
    if any(c["status"] == ERROR for c in hard):
        overall = ERROR
    elif any(c["status"] == FAIL for c in hard):
        overall = FAIL
    else:
        overall = PASS
    report["warnings"] = [
        c["id"] for c in checks if c.get("severity") == "soft" and c["status"] != PASS
    ]

    # -- promote only a fully passing attempt ----------------------------------
    if overall == PASS and promote:
        try:
            report["accepted"] = _promote(
                part_dir, name, version, step_path, render_paths, product_paths
            )
            report["promoted"] = True
        except Exception as e:
            checks.append(_check("promote", ERROR, f"{type(e).__name__}: {e}"))
            overall = ERROR

    report["overall"] = overall
    report["exit_code"] = {PASS: 0, FAIL: 1, ERROR: 2}[overall]
    report["finished"] = datetime.now().isoformat(timespec="seconds")

    # -- persist the report (attempt dir always; accepted copy only on promote)
    report_json = json.dumps(report, indent=2, default=str)
    (attempt_dir / "report.json").write_text(report_json, encoding="utf-8")
    report["artifacts"]["report"] = _rel(attempt_dir / "report.json")
    if report["promoted"]:
        accepted_report = part_dir / "exports" / f"{name}_{version}_report.json"
        accepted_report.write_text(report_json, encoding="utf-8")
    if json_out:
        Path(json_out).write_text(report_json, encoding="utf-8")

    for c in checks:
        say(
            f"   [{c['status']:<5}] {c['id']}: {c['message']}"
            + (" (soft)" if c.get("severity") == "soft" else "")
        )
    _say_design(report.get("design"), say)
    say(
        f"   overall: {overall}"
        + (
            f" -- promoted to {report['accepted']['step']}"
            if report["promoted"]
            else " -- NOT promoted"
            if promote
            else " (promotion disabled)"
        )
    )
    say(f"   report: {_rel(attempt_dir / 'report.json')}")
    return report


# ---------------------------------------------------------------------------
# Spec scaffolding — measure the artifact, draft an acceptance contract
# ---------------------------------------------------------------------------
def init_spec(part: str | Path, force: bool = False, quiet: bool = False) -> Path:
    """
    Build + export + re-import the part and write a DRAFT spec.json from the
    measured geometry. Every value is marked unresolved:true, so evaluating
    against the draft ERRORs until each number has been consciously reviewed —
    a spec transcribed blindly from the model would only ever prove the model
    equals itself.
    """
    part_dir = resolve_part_dir(str(part))
    spec_path = part_dir / "spec.json"
    if spec_path.exists() and not force:
        raise ValueError(f"{_rel(spec_path)} already exists -- pass --force to overwrite")

    module = load_part_module(part_dir)
    if not hasattr(module, "create_part"):
        raise ValueError("model.py has no create_part(params=None)")
    params = module.load_params() if hasattr(module, "load_params") else None
    result = module.create_part(params)

    attempt_dir = part_dir / "exports" / "attempts" / (time.strftime("%Y%m%d-%H%M%S") + "-initspec")
    attempt_dir.mkdir(parents=True, exist_ok=True)
    version = params.get("version", "v1") if isinstance(params, dict) else "v1"
    step_path = attempt_dir / f"{part_dir.name}_{version}.step"
    export_step(result, step_path)

    wp = cq.importers.importStep(str(step_path))
    vals = wp.vals()
    shape = vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)
    solids = wp.solids().vals() if vals else []
    volume = sum(abs(s.Volume()) for s in solids)
    bb = shape.BoundingBox()

    dims: list[dict] = [
        {
            "id": f"envelope_{axis}",
            "kind": "bbox",
            "axis": axis,
            "expected": round(v, 3),
            "tol": 0.1,
            "unresolved": True,
        }
        for axis, v in zip("xyz", (bb.xlen, bb.ylen, bb.zlen))
    ]
    dims.append(
        {
            "id": "material_volume",
            "kind": "volume",
            "min": round(volume * 0.95, 1),
            "max": round(volume * 1.05, 1),
            "severity": "soft",
            "unresolved": True,
        }
    )

    # group cylindrical features by (diameter, axis, type) -> count
    groups: dict[tuple, int] = {}
    for f in _cylinder_features(shape):
        key = (round(f["diameter"], 2), f["axis_label"], f["type"])
        groups[key] = groups.get(key, 0) + 1
    for n, ((dia, axis, ftype), count) in enumerate(
        sorted(groups.items(), key=lambda kv: -kv[0][0])[:8]
    ):
        dims.append(
            {
                "id": f"cylinders_{n}_d{dia:g}".replace(".", "p"),
                "kind": "cylinder",
                "diameter": dia,
                "tol": 0.1,
                "axis": axis,
                "type": ftype,
                "count_min": count,
                "unresolved": True,
            }
        )

    # Refinement gate, drafted deliberately SOFT: the bar is the repo standard
    # (DESIGN_ADVISORY_MIN_SCORE), not wherever this draft happens to land, so
    # scaffolding a part can never enshrine its own first-draft roughness as the
    # acceptance criterion. Raising "severity" to "hard" is the author's move.
    design_block = {
        "enabled": True,
        # The strictest rubric by default. Claiming cover/plate/bracket/sheet/
        # structural must be a deliberate edit, never something a scaffolder
        # guessed from the bounding box.
        "role": "enclosure",
        "min_score": DESIGN_ADVISORY_MIN_SCORE,
        "severity": "soft",
        "metric_severity": "soft",
        "metrics": {"edge_break_coverage": {"min_score": 60}},
        "waivers": {},
    }

    draft = {
        "schema": "part-spec/1",
        "part_name": (params or {}).get("part_name", part_dir.name),
        "units": "mm",
        "solid_count": len(solids),
        "dimensions": dims,
        "validators": [],
        "design": design_block,
        "assumptions": [
            "DRAFT generated by lib.evaluate --init-spec from measured geometry "
            "-- it proves nothing until each value is reviewed against the "
            "actual requirements and its unresolved flag removed.",
            'The "design" block gates refinement (lib/design_review.py). It is '
            'drafted soft: set "severity": "hard" once the part clears its bar, '
            "and give every waiver a written reason.",
            'The "role" is drafted as "enclosure", the strictest rubric. If this '
            "part is really a cover, plate, bracket, sheet-metal or structural "
            "member, set it - the role changes which metrics apply and how they "
            "are weighted, and it is the only honest way to be judged.",
        ],
        "unresolved": ["every dimension entry is pending review"],
    }
    spec_path.write_text(json.dumps(draft, indent=4), encoding="utf-8")
    if not quiet:
        print(
            f"  draft spec ({len(dims)} dimension entries, "
            f"{len(solids)} solid(s)) -> {_rel(spec_path)}"
        )
        print(
            "  review each entry, delete the ones that aren't requirements, "
            "and remove its 'unresolved' flag"
        )
        try:  # never let the advisory score block the draft it annotates
            from lib.design_review import review_shape

            review = review_shape(shape, source=_rel(step_path))
            if review.get("score") is not None:
                print(
                    f"  design refinement today: {review['score']:.1f}/100 "
                    f"(band {review['band']}) against a drafted bar of "
                    f"{DESIGN_ADVISORY_MIN_SCORE:g}"
                )
        except Exception as e:
            print(f"  design refinement not measured ({type(e).__name__}: {e})")
    return spec_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build, export, re-import, validate, render, and report a part."
    )
    ap.add_argument("part", help="part directory, or a name under parts/custom|vendor")
    ap.add_argument("--json", dest="json_out", help="also write the report JSON here")
    ap.add_argument(
        "--views",
        default=",".join(DEFAULT_VIEWS),
        help="comma-separated render views (default: iso,front,top)",
    )
    ap.add_argument("--size", type=int, default=900, help="render size in px")
    ap.add_argument("--no-render", action="store_true", help="skip renders")
    ap.add_argument(
        "--no-promote", action="store_true", help="evaluate only; never touch accepted exports"
    )
    ap.add_argument("--no-design", action="store_true", help="skip the design refinement review")
    ap.add_argument(
        "--design-min-score",
        type=float,
        default=None,
        help="override the design score bar for this run (0-100)",
    )
    ap.add_argument(
        "--product-render", action="store_true", help="also write studio hero renders (slower)"
    )
    ap.add_argument(
        "--product-views",
        default=",".join(DEFAULT_PRODUCT_VIEWS),
        help="comma-separated hero views (default: hero)",
    )
    ap.add_argument(
        "--product-size", type=int, default=1600, help="hero render width in px (default 1600)"
    )
    ap.add_argument(
        "--init-spec",
        action="store_true",
        help="measure the part and write a DRAFT spec.json, then exit",
    )
    ap.add_argument(
        "--force", action="store_true", help="with --init-spec: overwrite an existing spec.json"
    )
    args = ap.parse_args(argv)

    if args.init_spec:
        try:
            init_spec(args.part, force=args.force)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        return 0

    try:
        report = evaluate_part(
            args.part,
            views=tuple(v.strip() for v in args.views.split(",") if v.strip()),
            size=args.size,
            render=not args.no_render,
            promote=not args.no_promote,
            json_out=args.json_out,
            design=not args.no_design,
            design_min_score=args.design_min_score,
            product_render=args.product_render,
            product_views=tuple(v.strip() for v in args.product_views.split(",") if v.strip()),
            product_size=args.product_size,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
