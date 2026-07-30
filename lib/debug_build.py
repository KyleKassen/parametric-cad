"""
Build-stage bisection — turn opaque kernel errors into "stage X broke".

CadQuery failures ("BRep_API: command not done") carry no hint of WHICH
feature operation failed. This tool runs a part's build stage by stage and
reports the first failure with the last stage that succeeded, optionally
rendering every good stage so you can see the part grow.

The convention: model.py MAY define, next to create_part():

    def build_stages(params=None):
        wp = cq.Workplane("XY").box(...)
        yield "stock", wp
        wp = wp.faces(">Z").workplane().cboreHole(...)
        yield "corner_holes", wp
        ...

i.e. a generator yielding (name, workplane_or_shape) after each meaningful
operation. CadQuery is lazy-ish but each yielded value has been built, so an
exception during iteration localizes to "after the last yielded stage".
The final yielded shape should equal create_part()'s result (checked when
both exist, as a drift guard).

Without build_stages() the tool still runs create_part() under a full
traceback and tells you to add stages for bisection.

Usage:
    uv run python -m lib.debug_build PART [--render] [-o OUTDIR] [--size 700]

    PART resolves like lib.evaluate: a part directory or a bare name.
    --render writes <n>_<stage>_iso.png per completed stage
    (default OUTDIR: <part>/exports/debug/).

Exit status: 0 = all stages built; 1 = a stage failed.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT)) if str(PROJECT_ROOT) not in sys.path else None

from lib.evaluate import load_part_module, resolve_part_dir  # noqa: E402


def _shape_of(obj):
    return obj.val() if hasattr(obj, "val") else obj


def _stat(obj) -> str:
    shape = _shape_of(obj)
    try:
        solids = shape.Solids()
        vol = sum(abs(s.Volume()) for s in solids)
        faces = len(shape.Faces())
        return f"{len(solids)} solid(s), {faces} faces, {vol:.1f} mm^3"
    except Exception:
        return "no solid geometry yet"


def debug_build(
    part: str | Path,
    render: bool = False,
    out_dir: str | Path | None = None,
    size: int = 700,
    quiet: bool = False,
) -> dict:
    """
    Run the staged build. Returns {"ok": bool, "stages": [...], "failed_after":
    str|None, "error": str|None, "renders": [paths]}.
    """

    def say(line: str) -> None:
        if not quiet:
            print(line)

    part_dir = resolve_part_dir(str(part))
    module = load_part_module(part_dir)
    params = module.load_params() if hasattr(module, "load_params") else None

    result: dict = {
        "part": part_dir.name,
        "stages": [],
        "failed_after": None,
        "error": None,
        "renders": [],
        "ok": False,
    }

    if not hasattr(module, "build_stages"):
        say(
            f"== debug-build: {part_dir.name} == (no build_stages() -- running create_part() whole)"
        )
        try:
            t0 = time.perf_counter()
            whole = module.create_part(params)
            say(f"  [PASS ] create_part(): {_stat(whole)} in {time.perf_counter() - t0:.1f}s")
            say(
                "  hint: add a build_stages() generator to model.py to enable "
                "stage-by-stage bisection"
            )
            result["ok"] = True
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            say(f"  [ERROR] create_part(): {result['error']}")
            say(traceback.format_exc(limit=8))
            say(
                "  hint: add a build_stages() generator to model.py so the "
                "failing operation can be localized"
            )
        return result

    say(f"== debug-build: {part_dir.name} ==")
    out = Path(out_dir) if out_dir else part_dir / "exports" / "debug"
    last_good = None
    gen = module.build_stages(params)
    n = 0
    while True:
        try:
            t0 = time.perf_counter()
            name, wp = next(gen)
        except StopIteration:
            break
        except Exception as e:
            result["failed_after"] = last_good
            result["error"] = f"{type(e).__name__}: {e}"
            say(
                f"  [ERROR] stage {n + 1} (after "
                + (f"'{last_good}'" if last_good else "the start")
                + f") -- {result['error']}"
            )
            say("".join(traceback.format_exception(e, limit=8)))
            if last_good is not None:
                say(
                    f"  last good stage: '{last_good}'"
                    + (f" -- rendered in {out}" if render else " -- re-run with --render to see it")
                )
            return result

        n += 1
        dt = time.perf_counter() - t0
        stat = _stat(wp)
        result["stages"].append({"name": name, "stat": stat, "seconds": round(dt, 2)})
        say(f"  [PASS ] stage {n} '{name}': {stat} in {dt:.1f}s")
        last_good = name
        if render:
            from lib.render_step import render_scene

            shape = _shape_of(wp)
            try:
                written = render_scene(
                    [(shape, (0.62, 0.66, 0.72), 1.0)],
                    out,
                    f"{n:02d}_{name}",
                    views=("iso",),
                    size=size,
                )
                result["renders"] += [str(p) for p in written]
            except Exception as e:
                say(f"       (stage render failed: {e})")

    result["ok"] = True

    # drift guard: the last stage should be what create_part() ships
    if hasattr(module, "create_part") and result["stages"]:
        try:
            final = _shape_of(module.create_part(params))
            staged = _shape_of(wp)
            dv = abs(final.Volume() - staged.Volume())
            if dv > 1e-6 * max(1.0, abs(final.Volume())):
                say(
                    f"  [WARN ] create_part() volume differs from last stage "
                    f"by {dv:.3f} mm^3 -- build_stages() has drifted"
                )
                result["drift_mm3"] = round(dv, 3)
        except Exception:
            pass

    say(
        f"  all {n} stage(s) built"
        + (f", renders in {out}" if render and result["renders"] else "")
    )
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build a part stage by stage; localize the first failure."
    )
    ap.add_argument("part", help="part directory, or a name under parts/custom|vendor")
    ap.add_argument(
        "--render", action="store_true", help="render an iso view of every completed stage"
    )
    ap.add_argument("-o", "--out", help="stage render directory (default: <part>/exports/debug/)")
    ap.add_argument("--size", type=int, default=700, help="render size in px")
    args = ap.parse_args(argv)

    try:
        result = debug_build(args.part, render=args.render, out_dir=args.out, size=args.size)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
