"""
Geometric diff between two STEP artifacts — a "git diff" for solids.

Booleans B against A to measure exactly what changed:

    added   = B - A   (material the new version gained)     rendered GREEN
    removed = A - B   (material the new version lost)       rendered RED
    B itself                                                translucent gray

plus a cylindrical-feature diff (via lib/analyze_step): features present in
only one file, listed with diameter/axis/position. Use it to answer "did this
change do only what it claimed?" before accepting a new version:

    uv run python -m lib.diff_step OLD.step NEW.step [-o OUTDIR]
        [--views iso,top] [--size 900] [--json out.json]

Renders land in OUTDIR (default ./renders/) as diff_<old>_vs_<new>_<view>.png.
Identical files report zero added/removed volume and no feature changes.
Exit status: 0 = no geometric difference, 1 = differences found,
2 = the diff could not be computed. Units: mm / mm^3.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cadquery as cq

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT)) if str(PROJECT_ROOT) not in sys.path else None

from lib.analyze_step import MATCH_DIST, MATCH_RADIUS, _cylinder_features, _dist  # noqa: E402

GREEN = (0.20, 0.70, 0.30)
RED = (0.85, 0.25, 0.25)
GRAY = (0.62, 0.66, 0.72)

VOL_EPS = 1e-3  # mm^3 below which a boolean residue counts as "no change"


def _import(path: str | Path) -> cq.Shape:
    wp = cq.importers.importStep(str(path))
    vals = wp.vals()
    return vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)


def _volume(shape) -> float:
    return abs(shape.Volume())


def _feature_key(f: dict) -> str:
    return (f"d={f['diameter']:g} {f['axis_label']}-axis {f['type']} "
            f"p1={f['p1']} p2={f['p2']}")


def _unmatched(fa: list[dict], fb: list[dict]) -> list[dict]:
    """Features of A with no positional counterpart in B (identity frame)."""
    used = [False] * len(fb)
    out = []
    for f in fa:
        found = False
        for i, g in enumerate(fb):
            if used[i] or g["axis_label"] != f["axis_label"]:
                continue
            if abs(g["radius"] - f["radius"]) > MATCH_RADIUS:
                continue
            d = min(max(_dist(f["p1"], g["p1"]), _dist(f["p2"], g["p2"])),
                    max(_dist(f["p1"], g["p2"]), _dist(f["p2"], g["p1"])))
            if d <= MATCH_DIST:
                used[i] = True
                found = True
                break
        if not found:
            out.append(f)
    return out


def diff(a_path: str | Path, b_path: str | Path) -> dict:
    """Full geometric diff A -> B. Returns a JSON-serializable dict + shapes."""
    a_path, b_path = Path(a_path), Path(b_path)
    a, b = _import(a_path), _import(b_path)

    added = b.cut(a)
    removed = a.cut(b)
    added_vol = _volume(added)
    removed_vol = _volume(removed)
    if added_vol < VOL_EPS:
        added_vol = 0.0
    if removed_vol < VOL_EPS:
        removed_vol = 0.0

    fa, fb = _cylinder_features(a), _cylinder_features(b)
    removed_feats = _unmatched(fa, fb)
    added_feats = _unmatched(fb, fa)

    return {
        "schema": "step-diff/1",
        "a": str(a_path),
        "b": str(b_path),
        "volume_a_mm3": round(_volume(a), 1),
        "volume_b_mm3": round(_volume(b), 1),
        "added_mm3": round(added_vol, 2),
        "removed_mm3": round(removed_vol, 2),
        "identical": added_vol == 0.0 and removed_vol == 0.0,
        "features_added": [_feature_key(f) for f in added_feats[:20]],
        "features_removed": [_feature_key(f) for f in removed_feats[:20]],
        "_shapes": {"b": b, "added": added if added_vol else None,
                    "removed": removed if removed_vol else None},
    }


def render_diff(result: dict, out_dir: str | Path,
                views: tuple[str, ...] = ("iso", "top"), size: int = 900) -> list[Path]:
    """Render the overlay: B translucent, added green, removed red."""
    from lib.render_step import render_scene

    shapes = result["_shapes"]
    scene = [(shapes["b"], GRAY, 0.25)]
    if shapes["added"] is not None:
        scene.append((shapes["added"], GREEN, 1.0))
    if shapes["removed"] is not None:
        scene.append((shapes["removed"], RED, 0.85))
    prefix = (f"diff_{Path(result['a']).stem}_vs_{Path(result['b']).stem}"
              .replace(" ", "_"))
    return render_scene(scene, out_dir, prefix, views=views, size=size)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Geometric diff between two STEP files.")
    ap.add_argument("a", help="old STEP file")
    ap.add_argument("b", help="new STEP file")
    ap.add_argument("-o", "--out", default="renders", help="render output directory")
    ap.add_argument("--views", default="iso,top", help="comma-separated views")
    ap.add_argument("--size", type=int, default=900, help="render size in px")
    ap.add_argument("--json", dest="json_out", help="write the diff JSON here")
    ap.add_argument("--no-render", action="store_true", help="numbers only")
    args = ap.parse_args(argv)

    try:
        result = diff(args.a, args.b)
    except Exception as e:
        print(f"ERROR: diff failed -- {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(f"  A: {result['a']}  ({result['volume_a_mm3']:.1f} mm^3)")
    print(f"  B: {result['b']}  ({result['volume_b_mm3']:.1f} mm^3)")
    print(f"  added:   {result['added_mm3']:.2f} mm^3")
    print(f"  removed: {result['removed_mm3']:.2f} mm^3")
    for f in result["features_added"]:
        print(f"  + feature {f}")
    for f in result["features_removed"]:
        print(f"  - feature {f}")
    if result["identical"]:
        print("  identical within tolerance")

    if not args.no_render and not result["identical"]:
        views = tuple(v.strip() for v in args.views.split(",") if v.strip())
        for p in render_diff(result, args.out, views=views, size=args.size):
            print(f"  view: {p}")

    if args.json_out:
        clean = {k: v for k, v in result.items() if not k.startswith("_")}
        Path(args.json_out).write_text(json.dumps(clean, indent=2), encoding="utf-8")
        print(f"  json: {args.json_out}")

    return 0 if result["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
