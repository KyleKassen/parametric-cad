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

Standardized verification renders of the exported artifact are produced in the
attempt directory. A machine-readable report (schema "part-eval/1") with
per-check PASS / FAIL / ERROR results is written to
exports/attempts/<attempt-id>/report.json.

The exported STEP is promoted to the accepted location
exports/<part>_<version>.step (plus _report.json and _views/) ONLY when every
hard check passes. Failed or incomplete attempts never touch accepted outputs.

Exit status: 0 = all hard checks PASS, 1 = at least one hard FAIL,
2 = a hard check ERRORed or could not be evaluated.

Usage:
    uv run python -m lib.evaluate PART [--json out.json] [--views iso,front,top]
                                  [--size 900] [--no-render] [--no-promote]

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
DEFAULT_TOL = 0.1  # mm, when a dimension gives "expected" without "tol"
VALIDATOR_TIMEOUT = 900  # seconds

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
        and "expected" not in dim and "min" not in dim and "max" not in dim
    ):
        return _check(check_id, ERROR, "unresolved value -- resolve the spec before acceptance",
                      severity, kind=kind)

    if kind == "bbox":
        axis = dim.get("axis", "").lower()
        if axis not in ("x", "y", "z"):
            return _check(check_id, ERROR, f"bbox check needs axis x|y|z, got {axis!r}", severity)
        measured = geo["bbox_size"]["xyz".index(axis)]
        lo, hi = _bounds(dim)
        ok = lo <= measured <= hi
        return _check(check_id, PASS if ok else FAIL,
                      f"bbox {axis} = {measured:.3f} mm (accept {_range_str(dim)})",
                      severity, kind=kind, measured=round(measured, 3))

    if kind == "volume":
        measured = geo["volume"]
        lo, hi = _bounds(dim)
        ok = lo <= measured <= hi
        return _check(check_id, PASS if ok else FAIL,
                      f"volume = {measured:.1f} mm^3 (accept {_range_str(dim)})",
                      severity, kind=kind, measured=round(measured, 1))

    if kind == "cylinder":
        expected_d = dim.get("diameter")
        if expected_d is None:
            return _check(check_id, ERROR, "cylinder check needs 'diameter'", severity)
        tol = dim.get("tol", DEFAULT_TOL)
        axis = dim.get("axis")
        ftype = dim.get("type")
        count_min = dim.get("count_min", 1)
        matches = [
            f for f in geo["features"]
            if abs(f["diameter"] - expected_d) <= tol
            and (axis is None or f["axis_label"] == axis)
            and (ftype is None or f["type"] == ftype)
        ]
        ok = len(matches) >= count_min
        what = (f"d={expected_d}+/-{tol}"
                + (f" {axis}-axis" if axis else "") + (f" {ftype}" if ftype else ""))
        return _check(check_id, PASS if ok else FAIL,
                      f"{len(matches)} cylinder feature(s) matching {what} (need >= {count_min})",
                      severity, kind=kind, measured=len(matches))

    if kind == "cylinder_at":
        expected_d, at = dim.get("diameter"), dim.get("at")
        if expected_d is None or at is None:
            return _check(check_id, ERROR,
                          "cylinder_at needs 'diameter' and 'at' [x, y, z]", severity)
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
        what = (f"d={expected_d}+/-{tol}"
                + (f" {axis}-axis" if axis else "") + (f" {ftype}" if ftype else ""))
        if best is None:
            return _check(check_id, FAIL,
                          f"no cylinder matching {what} anywhere in the artifact",
                          severity, kind=kind)
        ok = best <= pos_tol
        return _check(check_id, PASS if ok else FAIL,
                      f"nearest {what} axis is {best:.3f} mm from {at} (allow <= {pos_tol})",
                      severity, kind=kind, measured=round(best, 3))

    return _check(check_id, ERROR, f"unknown dimension kind {kind!r}", severity, kind=kind)


def _run_validator(v: dict, part_dir: Path, step_path: Path, attempt_dir: Path) -> dict:
    """Run one part-specific validator script. exit 0 = PASS, nonzero = FAIL."""
    severity = v.get("severity", "hard")
    check_id = f"validator:{v.get('id', v.get('script', '?'))}"
    script = part_dir / v.get("script", "")
    if not script.is_file():
        return _check(check_id, ERROR, f"validator script not found: {v.get('script')}", severity)

    env = dict(os.environ,
               PYTHONUTF8="1",
               EVAL_STEP_PATH=str(step_path),
               EVAL_PART_DIR=str(part_dir),
               EVAL_ATTEMPT_DIR=str(attempt_dir))
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=PROJECT_ROOT, env=env, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=v.get("timeout", VALIDATOR_TIMEOUT),
        )
    except subprocess.TimeoutExpired:
        return _check(check_id, ERROR,
                      f"validator timed out after {v.get('timeout', VALIDATOR_TIMEOUT)}s",
                      severity)
    except OSError as e:
        return _check(check_id, ERROR, f"validator could not run: {e}", severity)

    log_path = attempt_dir / f"{check_id.replace(':', '_').replace('/', '_')}.log"
    log_path.write_text(proc.stdout + ("\n--- stderr ---\n" + proc.stderr if proc.stderr else ""),
                        encoding="utf-8")
    if proc.returncode == 0:
        return _check(check_id, PASS, f"exit 0 (log: {_rel(log_path)})", severity)
    tail = "; ".join(line.strip() for line in (proc.stdout + proc.stderr).strip().splitlines()[-3:])
    return _check(check_id, FAIL, f"exit {proc.returncode}: {tail} (log: {_rel(log_path)})",
                  severity, exit_code=proc.returncode)


# ---------------------------------------------------------------------------
# Promotion — accepted outputs are replaced only by a fully passing attempt
# ---------------------------------------------------------------------------
def _atomic_copy(src: Path, dst: Path) -> None:
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def _promote(part_dir: Path, name: str, version: str, step_path: Path,
             render_paths: list[Path]) -> dict:
    exports = part_dir / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    accepted_step = exports / f"{name}_{version}.step"
    _atomic_copy(step_path, accepted_step)

    accepted_views = []
    if render_paths:
        views_dir = exports / f"{name}_{version}_views"
        views_dir.mkdir(parents=True, exist_ok=True)
        for p in render_paths:
            dst = views_dir / p.name
            _atomic_copy(p, dst)
            accepted_views.append(_rel(dst))
    return {
        "step": _rel(accepted_step),
        "report": _rel(exports / f"{name}_{version}_report.json"),
        "views": accepted_views,
    }


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------
def evaluate_part(
    part: str | Path,
    views: tuple[str, ...] = DEFAULT_VIEWS,
    size: int = 900,
    render: bool = True,
    promote: bool = True,
    json_out: str | Path | None = None,
    quiet: bool = False,
) -> dict:
    """Run the full evaluation pipeline. Returns the report dict (see schema)."""

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
        "schema": "part-eval/1",
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
        checks.append(_check("build", PASS,
                             f"create_part() ok in {time.perf_counter() - t0:.1f}s"))
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
            checks.append(_check("export", PASS,
                                 f"{_rel(step_path)} ({step_path.stat().st_size // 1024} KB)"))
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
            checks.append(_check(
                "reimport", PASS,
                f"{geo['solid_count']} solid(s), volume {geo['volume']:.1f} mm^3, "
                f"bbox {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm"))
        except Exception as e:
            checks.append(_check("reimport", ERROR,
                                 f"exported STEP failed to re-import -- {type(e).__name__}: {e}"))
            aborted = True

    if not aborted:
        report["geometry"] = {
            "solid_count": geo["solid_count"],
            "volume_mm3": round(geo["volume"], 1),
            "bbox_size": [round(v, 3) for v in geo["bbox_size"]],
        }

        # baseline hard checks (always run, spec or no spec)
        valid = geo["shape"].isValid()
        checks.append(_check("brep_valid", PASS if valid else FAIL,
                             "BRepCheck_Analyzer " + ("passed" if valid else "REJECTED the shape")))
        non_empty = geo["solid_count"] >= 1 and geo["volume"] > 0
        checks.append(_check("non_empty", PASS if non_empty else FAIL,
                             f"{geo['solid_count']} solid(s), volume {geo['volume']:.1f} mm^3"
                             + ("" if non_empty else " -- empty export is a failure")))

        if spec:
            if "solid_count" in spec:
                ok = geo["solid_count"] == spec["solid_count"]
                checks.append(_check(
                    "solid_count", PASS if ok else FAIL,
                    f"{geo['solid_count']} solid(s), expected {spec['solid_count']}",
                    measured=geo["solid_count"], expected=spec["solid_count"]))
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

    # -- standardized renders of the exported artifact ------------------------
    if not aborted and render:
        try:
            from lib.render_step import render_file

            render_paths = render_file(step_path, out_dir=attempt_dir / "views",
                                       views=views, size=size)
            if fit_scene and spec.get("fit", {}).get("render"):
                from lib.fit import render_fit_scene

                render_paths += render_fit_scene(fit_scene, attempt_dir / "views", size=size)
            checks.append(_check("render", PASS,
                                 f"{len(render_paths)} view(s) -> {_rel(attempt_dir / 'views')}"))
            report["artifacts"]["views"] = [_rel(p) for p in render_paths]
        except Exception as e:
            checks.append(_check("render", ERROR, f"{type(e).__name__}: {e}"))

    # -- verdict ---------------------------------------------------------------
    hard = [c for c in checks if c.get("severity", "hard") == "hard"]
    if any(c["status"] == ERROR for c in hard):
        overall = ERROR
    elif any(c["status"] == FAIL for c in hard):
        overall = FAIL
    else:
        overall = PASS
    report["warnings"] = [c["id"] for c in checks
                          if c.get("severity") == "soft" and c["status"] != PASS]

    # -- promote only a fully passing attempt ----------------------------------
    if overall == PASS and promote:
        try:
            report["accepted"] = _promote(part_dir, name, version, step_path, render_paths)
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
        say(f"   [{c['status']:<5}] {c['id']}: {c['message']}"
            + (" (soft)" if c.get("severity") == "soft" else ""))
    say(f"   overall: {overall}"
        + (f" -- promoted to {report['accepted']['step']}" if report["promoted"]
           else " -- NOT promoted" if promote else " (promotion disabled)"))
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

    attempt_dir = part_dir / "exports" / "attempts" / (
        time.strftime("%Y%m%d-%H%M%S") + "-initspec")
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
        {"id": f"envelope_{axis}", "kind": "bbox", "axis": axis,
         "expected": round(v, 3), "tol": 0.1, "unresolved": True}
        for axis, v in zip("xyz", (bb.xlen, bb.ylen, bb.zlen))
    ]
    dims.append({"id": "material_volume", "kind": "volume",
                 "min": round(volume * 0.95, 1), "max": round(volume * 1.05, 1),
                 "severity": "soft", "unresolved": True})

    # group cylindrical features by (diameter, axis, type) -> count
    groups: dict[tuple, int] = {}
    for f in _cylinder_features(shape):
        key = (round(f["diameter"], 2), f["axis_label"], f["type"])
        groups[key] = groups.get(key, 0) + 1
    for n, ((dia, axis, ftype), count) in enumerate(
            sorted(groups.items(), key=lambda kv: -kv[0][0])[:8]):
        dims.append({"id": f"cylinders_{n}_d{dia:g}".replace(".", "p"),
                     "kind": "cylinder", "diameter": dia, "tol": 0.1,
                     "axis": axis, "type": ftype, "count_min": count,
                     "unresolved": True})

    draft = {
        "schema": "part-spec/1",
        "part_name": (params or {}).get("part_name", part_dir.name),
        "units": "mm",
        "solid_count": len(solids),
        "dimensions": dims,
        "validators": [],
        "assumptions": [
            "DRAFT generated by lib.evaluate --init-spec from measured geometry "
            "-- it proves nothing until each value is reviewed against the "
            "actual requirements and its unresolved flag removed."
        ],
        "unresolved": ["every dimension entry is pending review"],
    }
    spec_path.write_text(json.dumps(draft, indent=4), encoding="utf-8")
    if not quiet:
        print(f"  draft spec ({len(dims)} dimension entries, "
              f"{len(solids)} solid(s)) -> {_rel(spec_path)}")
        print("  review each entry, delete the ones that aren't requirements, "
              "and remove its 'unresolved' flag")
    return spec_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build, export, re-import, validate, render, and report a part.")
    ap.add_argument("part", help="part directory, or a name under parts/custom|vendor")
    ap.add_argument("--json", dest="json_out", help="also write the report JSON here")
    ap.add_argument("--views", default=",".join(DEFAULT_VIEWS),
                    help="comma-separated render views (default: iso,front,top)")
    ap.add_argument("--size", type=int, default=900, help="render size in px")
    ap.add_argument("--no-render", action="store_true", help="skip renders")
    ap.add_argument("--no-promote", action="store_true",
                    help="evaluate only; never touch accepted exports")
    ap.add_argument("--init-spec", action="store_true",
                    help="measure the part and write a DRAFT spec.json, then exit")
    ap.add_argument("--force", action="store_true",
                    help="with --init-spec: overwrite an existing spec.json")
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
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
