"""
Declarative assembly fit engine — the fit_check.py pattern as data, not code.

A part's spec.json may carry a "fit" block declaring solids to place and
pairwise geometric requirements between them. lib/evaluate.py runs the block
as part of the acceptance gate; this module is also a standalone CLI for fast
iteration on just the fit cases:

    uv run python -m lib.fit parts/custom/oz51x-dual-rx-housing [--render-out DIR]

Fit block shape:

    "fit": {
        "render": true,                      # render the assembled scene
        "cases": [
            {
                "id": "rf_module_vs_base",
                "a": {"source": "builder", "builder": "create_base"},
                "b": {"source": "step",
                      "path": "parts/vendor/zonu-oz510-receiver/OZ510 Receiver.STEP",
                      "transform": [{"rotate": {"axis": "X", "angle": 90}},
                                    {"translate": [-22.55, 0, 6.0]}]},
                "max_interference": 2.0,     # mm^3   interference(a, b) <= v
                "min_clearance": 1.0,        # mm     clearance(a, b) >= v
                "max_outside": 1.0,          # mm^3   volume of b outside a <= v
                "severity": "hard"
            }
        ]
    }

Solid sources:
    {"source": "builder", "builder": "create_base"}      function in THIS part's
                                                         model.py, called with params
    {"source": "step", "path": "parts/vendor/x/y.STEP"}  project-relative STEP
    {"source": "part", "dir": "parts/vendor/x",          another part's builder
     "builder": "create_part"}                           (default create_part)

Transforms apply in order: {"rotate": {"axis": "X"|"Y"|"Z", "angle": deg}}
(about the origin) and {"translate": [x, y, z]}. Omitted "a" defaults to this
part's create_part(). Each present requirement key yields one check
(fit:<case>:<key>) with PASS/FAIL/ERROR status — a kernel failure is an
ERROR, never a passing clearance.

Every case validates the same builder code path that produced the exported
artifact; geometry checks in lib/evaluate.py cover the artifact itself.
Units: mm / mm^3.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import cadquery as cq

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT)) if str(PROJECT_ROOT) not in sys.path else None

from lib.housing import clearance, interference  # noqa: E402

# scene colors: the reference solid, then a cycling palette for placed solids
_A_COLOR = (0.55, 0.60, 0.68)
_B_PALETTE = [
    (0.30, 0.55, 0.85),
    (0.85, 0.45, 0.30),
    (0.20, 0.65, 0.30),
    (0.75, 0.35, 0.65),
    (0.80, 0.70, 0.25),
]

_AXES = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}


def _load_module(part_dir: Path):
    model_path = part_dir / "model.py"
    spec = importlib.util.spec_from_file_location(f"fit.{part_dir.name}.model", model_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _apply_transform(wp: cq.Workplane, steps: list[dict]) -> cq.Workplane:
    for step in steps or []:
        if "rotate" in step:
            r = step["rotate"]
            axis = _AXES.get(str(r.get("axis", "")).upper())
            if axis is None:
                raise ValueError(f"rotate axis must be X|Y|Z, got {r.get('axis')!r}")
            wp = wp.rotate((0, 0, 0), axis, r["angle"])
        elif "translate" in step:
            wp = wp.translate(tuple(step["translate"]))
        else:
            raise ValueError(f"unknown transform step {step!r} (use rotate/translate)")
    return wp


def _build_source(src: dict, part_dir: Path, module, params) -> cq.Workplane:
    kind = src.get("source")
    if kind == "builder":
        fn = getattr(module, src["builder"], None)
        if fn is None:
            raise ValueError(f"model.py has no builder {src['builder']!r}")
        wp = fn(params)
    elif kind == "step":
        path = PROJECT_ROOT / src["path"]
        if not path.is_file():
            raise ValueError(f"STEP not found: {src['path']}")
        wp = cq.importers.importStep(str(path))
    elif kind == "part":
        other_dir = PROJECT_ROOT / src["dir"]
        other = _load_module(other_dir)
        other_params = other.load_params() if hasattr(other, "load_params") else None
        fn = getattr(other, src.get("builder", "create_part"), None)
        if fn is None:
            raise ValueError(f"{src['dir']}/model.py has no builder {src.get('builder')!r}")
        wp = fn(other_params)
    else:
        raise ValueError(f"unknown source {kind!r} (use builder/step/part)")
    return _apply_transform(wp, src.get("transform"))


def run_fit(fit_spec: dict, part_dir: Path) -> tuple[list[dict], list]:
    """
    Execute every fit case. Returns (checks, scene) where checks are
    report-style dicts ({id, status, severity, message, measured?}) and scene
    is [(shape, rgb, opacity), ...] ready for lib.render_step.render_scene.
    """
    module = _load_module(part_dir)
    params = module.load_params() if hasattr(module, "load_params") else None

    checks: list[dict] = []
    cache: dict[str, cq.Workplane] = {}
    scene: list = []
    seen_in_scene: set[str] = set()

    def build(src: dict, role: str) -> cq.Workplane:
        key = json.dumps(src, sort_keys=True)
        if key not in cache:
            cache[key] = _build_source(src, part_dir, module, params)
        wp = cache[key]
        if key not in seen_in_scene:
            seen_in_scene.add(key)
            if role == "a":
                scene.append((wp.val(), _A_COLOR, 0.30))
            else:
                color = _B_PALETTE[(len(seen_in_scene) - 1) % len(_B_PALETTE)]
                scene.append((wp.val(), color, 1.0))
        return wp

    for case in fit_spec.get("cases", []):
        cid = case.get("id", "?")
        severity = case.get("severity", "hard")
        constraints = [k for k in ("max_interference", "min_clearance", "max_outside") if k in case]
        if not constraints:
            checks.append(
                {
                    "id": f"fit:{cid}",
                    "status": "ERROR",
                    "severity": severity,
                    "message": "case has no max_interference/min_clearance/max_outside",
                }
            )
            continue
        try:
            a = build(case.get("a", {"source": "builder", "builder": "create_part"}), "a")
            b = build(case["b"], "b")
        except Exception as e:
            for key in constraints:
                checks.append(
                    {
                        "id": f"fit:{cid}:{key}",
                        "status": "ERROR",
                        "severity": severity,
                        "message": f"could not build solids -- {type(e).__name__}: {e}",
                    }
                )
            continue

        for key in constraints:
            limit = case[key]
            try:
                if key == "max_interference":
                    v = interference(a, b)
                    ok, unit, rel = v <= limit, "mm^3", "<="
                elif key == "min_clearance":
                    v = clearance(a, b)
                    ok, unit, rel = v >= limit, "mm", ">="
                else:  # max_outside: volume of b not contained in a
                    outside = b.val().cut(a.val())
                    v = sum(abs(s.Volume()) for s in outside.Solids())
                    ok, unit, rel = v <= limit, "mm^3", "<="
            except Exception as e:
                checks.append(
                    {
                        "id": f"fit:{cid}:{key}",
                        "status": "ERROR",
                        "severity": severity,
                        "message": f"{type(e).__name__}: {e}",
                    }
                )
                continue
            checks.append(
                {
                    "id": f"fit:{cid}:{key}",
                    "status": "PASS" if ok else "FAIL",
                    "severity": severity,
                    "measured": round(v, 3),
                    "message": f"{v:.3f} {unit} (require {rel} {limit})",
                }
            )
    return checks, scene


def render_fit_scene(
    scene: list, out_dir: Path, views: tuple[str, ...] = ("iso", "top"), size: int = 900
) -> list[Path]:
    """Render the assembled fit scene (reference solid translucent)."""
    from lib.render_step import render_scene

    return render_scene(scene, out_dir, "fit", views=views, size=size)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a part's declarative spec.json fit block.")
    ap.add_argument("part_dir", help="part directory containing spec.json with a fit block")
    ap.add_argument("--render-out", help="also render the fit scene into this directory")
    args = ap.parse_args(argv)

    part_dir = Path(args.part_dir)
    spec_path = part_dir / "spec.json"
    if not spec_path.is_file():
        print(f"ERROR: no spec.json in {part_dir}", file=sys.stderr)
        return 2
    fit_spec = json.loads(spec_path.read_text(encoding="utf-8")).get("fit")
    if not fit_spec:
        print(f"ERROR: {spec_path} has no fit block", file=sys.stderr)
        return 2

    checks, scene = run_fit(fit_spec, part_dir)
    for c in checks:
        print(f"  [{c['status']:<5}] {c['id']}: {c['message']}")
    if args.render_out:
        for p in render_fit_scene(scene, Path(args.render_out)):
            print(f"  view: {p}")

    hard = [c for c in checks if c.get("severity", "hard") == "hard"]
    if any(c["status"] == "ERROR" for c in hard):
        return 2
    if any(c["status"] == "FAIL" for c in hard):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
