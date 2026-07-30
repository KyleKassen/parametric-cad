"""
Exact STEP analysis via the OpenCASCADE kernel - no text parsing, no pixels.

The measurement layer of the part pipeline. A STEP file's thousands of lines
are just serialization; the kernel loads them into an exact B-rep that we can
query analytically: bounding boxes, volumes, and cylindrical features (holes,
bosses, connector barrels) with their true axes, radii, and extents.

Every part gets analyzed INDIVIDUALLY - never assume two vendor files are
identical or symmetric. `compare()` checks two files for identity or a mirror
relationship (left-hand / right-hand vendor variants, e.g. the OZ510
Transmitter's I/O is mirrored across X relative to the Receiver).

Usage:
    uv run python -m lib.analyze_step FILE.step [--save | -o out.json]
    uv run python -m lib.analyze_step --compare A.step B.step

--save writes JSON into a references/ directory BESIDE THE FILE BEING ANALYSED,
never into the part directory: <step>/../references/<stem>_analysis.json,
whenever any component of the path is named "parts", else next to the file as
<stem>.analysis.json. Analysing a source STEP at parts/vendor/<v>/<v>.STEP
therefore lands in parts/vendor/<v>/references/, while analysing a PROMOTED
artifact at parts/<group>/<part>/exports/<part>_v1.step lands in
parts/<group>/<part>/exports/references/ - which .gitignore covers, because
that whole tree is derived. Pass -o to write somewhere else.

compare() assumes both files share a coordinate frame (true for same-vendor
exports).

Units: mm (as imported by OpenCASCADE).
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.TopAbs import TopAbs_REVERSED

MATCH_DIST = 0.6  # mm — max axis-endpoint distance for two features to match
MATCH_RADIUS = 0.15  # mm — max radius difference for a match

# Feature-set transforms tried by compare(): point scale factors per axis
_TRANSFORMS = {
    "identity": (1, 1, 1),
    "mirror_x": (-1, 1, 1),
    "mirror_y": (1, -1, 1),
    "mirror_z": (1, 1, -1),
}


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
#: How close two components must be before "which one is dominant" is treated as
#: having no answer and the fold falls back to a fixed order. It has to be
#: comfortably larger than every rounding a direction passes through before it is
#: folded a SECOND time - `_cylinder_features` stores `dir` rounded to 4
#: decimals, so 5e-5 - and comfortably smaller than any tilt a designer means.
#: 1e-3 is 0.057 degrees off an exact tie: twenty times the rounding and far
#: below anything modelled on purpose.
DOMINANT_TIE = 1e-3


def _canonical_dir(d: tuple) -> tuple:
    """
    Flip an axis direction so its dominant component is positive.

    THE TIE HAS TO BE DECIDED BY A RULE, NOT BY ROUND-OFF. "Dominant" has no
    answer when two components are equal, and equal components are not an edge
    case - an axis rotated 45 degrees in a plane is the ordinary way a part gets
    held. `max()` over the raw magnitudes then breaks the tie on whichever of
    them the last bit of the arithmetic made larger, and the same direction folds
    one way from `_cylinder_features`'s 4-decimal `dir` and the other way from
    the face's own full-precision axis. The two differ by a SIGN, so every
    comparison of a feature against its own faces failed: on this repo's
    reference enclosure, held at 45 degrees, `cylinder_wrap` summed no area for
    any Y-axis feature, `_feature_centres` dropped 20 of 90 centres and
    `_merge_fasteners` 19 of 54 screws, and the part scored 90.2 as modelled and
    92.6 turned - a 2.4 point gift for holding the file differently.

    Within DOMINANT_TIE the components are treated as equal and the LAST of them
    fixes the sign, which is a property of the direction rather than of the
    arithmetic that produced it. Outside it this is the rule it always was.
    """
    biggest = max(abs(c) for c in d)
    i = max((k for k in range(3) if abs(d[k]) >= biggest - DOMINANT_TIE), default=0)
    return tuple(-c for c in d) if d[i] < 0 else tuple(d)


def _axis_label(d: tuple) -> str:
    ax = [abs(c) for c in d]
    i = ax.index(max(ax))
    return "XYZ"[i] if ax[i] > 0.98 else "oblique"


#: mm. OCCT reports the natural (untrimmed) V bounds of a cylinder as
#: Precision::Infinite(), which is 1e100 and therefore finite to Python. Any V
#: span past this is that sentinel rather than a measurement.
_UNTRIMMED_V = 1e12


def _axial_extent(
    face: cq.Face,
    surf: BRepAdaptor_Surface,
    surf_dir: tuple[float, float, float],
    canon_dir: tuple[float, float, float],
    base: float,
) -> tuple[float, float]:
    """
    A cylindrical face's extent along its own axis, as (min, max) in mm.

    Taken from the face's PARAMETRIC range, because a cylinder's V parameter is
    by definition the signed distance along the axis from the surface placement,
    measured in millimetres. That makes the extent a property of the face, so it
    reads the same however the file happens to be oriented.

    It used to be the span of the face's WORLD axis-aligned bounding box
    projected onto the axis, which is exact only while the axis lies on a world
    axis and inflates otherwise: a D6 hole through a 10 mm plate measured 10.000
    as modelled and 18.303 after a 77 degree rotation. Everything divided by this
    length inherited that error. `Topology.cylinder_wrap` in lib/design_review.py
    divides by it, so an inflated length pushed a full through bore below
    BORE_WRAP_MIN, emptied the fastener population, and left feature_composition
    and pattern_discipline reporting a plate full of holes as a plate with none -
    64.0/C as modelled against 34.5/F rotated 77 degrees, for the same solid.

    The bounding-box projection survives only for a face with no wires, whose
    natural V bounds are the infinite sentinel. No solid this repo builds
    produces one; it is here so an exotic vendor import degrades to the old
    approximation instead of returning a 1e100 length.
    """
    v0, v1 = surf.FirstVParameter(), surf.LastVParameter()
    if math.isfinite(v0) and math.isfinite(v1) and abs(v1 - v0) < _UNTRIMMED_V:
        # canon_dir is surf_dir flipped into canonical form, so the dot product
        # is exactly +1 or -1 and is the sign V runs in along the canonical axis.
        sign = 1.0 if sum(a * b for a, b in zip(surf_dir, canon_dir)) > 0 else -1.0
        lo, hi = base + sign * v0, base + sign * v1
        return (lo, hi) if lo <= hi else (hi, lo)

    bb = face.BoundingBox()
    corners = [
        (x, y, z)
        for x in (bb.xmin, bb.xmax)
        for y in (bb.ymin, bb.ymax)
        for z in (bb.zmin, bb.zmax)
    ]
    ts = [sum(c * dc for c, dc in zip(corner, canon_dir)) for corner in corners]
    return min(ts), max(ts)


def _cylinder_features(shape: cq.Shape) -> list[dict]:
    """
    All cylindrical faces, merged into coaxial features.

    Each feature carries its axis segment endpoints p1/p2 (mm), radius, and a
    type: "hole" (face normals point at the axis — material outside),
    "boss" (normals point away — material inside), or "mixed".
    """
    groups: list[dict] = []
    for f in shape.Faces():
        surf = BRepAdaptor_Surface(f.wrapped)
        if surf.GetType() != GeomAbs_Cylinder:
            continue
        cyl = surf.Cylinder()
        ax = cyl.Axis()
        dd, loc = ax.Direction(), ax.Location()
        d = _canonical_dir((dd.X(), dd.Y(), dd.Z()))
        p = (loc.X(), loc.Y(), loc.Z())
        t = sum(pc * dc for pc, dc in zip(p, d))
        foot = tuple(pc - t * dc for pc, dc in zip(p, d))  # axis point ⊥ origin
        r = cyl.Radius()

        smin, smax = _axial_extent(f, surf, (dd.X(), dd.Y(), dd.Z()), d, t)
        concave = f.wrapped.Orientation() == TopAbs_REVERSED

        for g in groups:  # merge coaxial same-radius faces
            # SIGN-BLIND, because whether two foldings of one axis agree is not
            # a fact about the part - see _canonical_dir. The axial extents are
            # measured ALONG the folded direction, so a group whose fold points
            # the other way is merged with its extents reflected rather than
            # left as a second feature.
            dot = sum(a * b for a, b in zip(g["dir"], d))
            if (
                abs(g["radius"] - r) < 0.02
                and abs(dot) > 0.999
                and sum((a - b) ** 2 for a, b in zip(g["foot"], foot)) < 0.05**2
            ):
                lo, hi = (smin, smax) if dot > 0 else (-smax, -smin)
                g["smin"] = min(g["smin"], lo)
                g["smax"] = max(g["smax"], hi)
                g["faces"] += 1
                g["concave"] += 1 if concave else 0
                break
        else:
            groups.append(
                {
                    "radius": r,
                    "dir": d,
                    "foot": foot,
                    "smin": smin,
                    "smax": smax,
                    "faces": 1,
                    "concave": 1 if concave else 0,
                }
            )

    feats = []
    for g in groups:
        d, foot = g["dir"], g["foot"]
        feats.append(
            {
                "radius": round(g["radius"], 3),
                "diameter": round(2 * g["radius"], 3),
                "axis_label": _axis_label(d),
                "dir": [round(c, 4) for c in d],
                "p1": [round(foot[i] + g["smin"] * d[i], 3) for i in range(3)],
                "p2": [round(foot[i] + g["smax"] * d[i], 3) for i in range(3)],
                "length": round(g["smax"] - g["smin"], 3),
                "faces": g["faces"],
                "type": (
                    "hole"
                    if g["concave"] == g["faces"]
                    else "boss"
                    if g["concave"] == 0
                    else "mixed"
                ),
            }
        )
    feats.sort(key=lambda f: -f["radius"])
    return feats


def analyze(path: str | Path) -> dict:
    """Full exact analysis of one STEP file. Returns a JSON-serializable dict."""
    path = Path(path)
    wp = cq.importers.importStep(str(path))
    comp = wp.val()
    bb = comp.BoundingBox()

    solids = []
    for s in wp.solids().vals():
        sb = s.BoundingBox()
        c = s.Center()
        solids.append(
            {
                "volume_mm3": round(s.Volume(), 1),
                "bbox_min": [round(sb.xmin, 2), round(sb.ymin, 2), round(sb.zmin, 2)],
                "bbox_max": [round(sb.xmax, 2), round(sb.ymax, 2), round(sb.zmax, 2)],
                "center": [round(c.x, 2), round(c.y, 2), round(c.z, 2)],
            }
        )
    solids.sort(key=lambda s: -s["volume_mm3"])

    max_dim = max(bb.xlen, bb.ylen, bb.zlen)
    units_note = (
        f"imported as mm; max dim {max_dim:.1f} mm"
        if max_dim >= 30
        else f"max dim {max_dim:.1f} — small; check source units (inches?)"
    )

    feats = _cylinder_features(comp)
    return {
        "schema": "step-analysis/1",
        "source": str(path),
        "generated": date.today().isoformat(),
        "bbox_min": [round(bb.xmin, 3), round(bb.ymin, 3), round(bb.zmin, 3)],
        "bbox_max": [round(bb.xmax, 3), round(bb.ymax, 3), round(bb.zmax, 3)],
        "bbox_size": [round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)],
        "volume_mm3": round(comp.Volume(), 1),
        "units_note": units_note,
        "solid_count": len(solids),
        "solids": solids,
        "feature_count": len(feats),
        "features": feats,
    }


# ---------------------------------------------------------------------------
# Comparison — identical? mirrored? different?
# ---------------------------------------------------------------------------
def _dist(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _match(fa: list[dict], fb: list[dict], scale: tuple) -> tuple[int, list[dict]]:
    """Greedy-match A's features against transformed B's. Returns (matches, unmatched_a)."""
    tb = [
        (
            g,
            tuple(c * s for c, s in zip(g["p1"], scale)),
            tuple(c * s for c, s in zip(g["p2"], scale)),
        )
        for g in fb
    ]
    used = [False] * len(tb)
    matched, unmatched = 0, []
    for f in fa:
        a1, a2 = tuple(f["p1"]), tuple(f["p2"])
        best, best_d = None, MATCH_DIST
        for i, (g, q1, q2) in enumerate(tb):
            if used[i] or g["axis_label"] != f["axis_label"]:
                continue
            if abs(g["radius"] - f["radius"]) > MATCH_RADIUS:
                continue
            d = min(max(_dist(a1, q1), _dist(a2, q2)), max(_dist(a1, q2), _dist(a2, q1)))
            if d < best_d:
                best_d, best = d, i
        if best is not None:
            used[best] = True
            matched += 1
        else:
            unmatched.append(f)
    return matched, unmatched


def compare(a_path: str | Path, b_path: str | Path) -> dict:
    """
    Compare two STEP files' cylindrical-feature sets under identity and the
    three axis mirrors. Bounding boxes and radius histograms are mirror-blind;
    feature POSITIONS are not — this is what tells an RX from a mirrored TX.
    """
    A, B = analyze(a_path), analyze(b_path)
    fa, fb = A["features"], B["features"]

    scores, unmatched_by = {}, {}
    for name, scale in _TRANSFORMS.items():
        m, unmatched = _match(fa, fb, scale)
        total = len(fa) + len(fb)
        scores[name] = round(2 * m / total, 3) if total else 1.0
        unmatched_by[name] = unmatched

    best = max(scores, key=scores.get)
    if scores["identity"] >= 0.98:
        verdict = "identical within tolerance"
    elif best != "identity" and scores[best] >= scores["identity"] + 0.05 and scores[best] >= 0.6:
        verdict = (
            f"probably a {best} variant "
            f"({scores[best]:.0%} match vs identity {scores['identity']:.0%})"
        )
    elif max(scores.values()) < 0.5:
        verdict = "different parts"
    else:
        verdict = (
            "similar but NOT identical — mixed/partial symmetry; "
            "inspect the unmatched features under each transform"
        )

    return {
        "a": A["source"],
        "b": B["source"],
        "bbox_size_a": A["bbox_size"],
        "bbox_size_b": B["bbox_size"],
        "volume_ratio": round(B["volume_mm3"] / A["volume_mm3"], 4) if A["volume_mm3"] else None,
        "feature_counts": [len(fa), len(fb)],
        "scores": scores,
        "best": best,
        "verdict": verdict,
        "unmatched_under_best": [
            {k: f[k] for k in ("diameter", "axis_label", "type", "p1", "p2")}
            for f in unmatched_by[best][:12]
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _default_json_path(step_path: Path) -> Path:
    if "parts" in [p.lower() for p in step_path.parts]:
        out_dir = step_path.parent / "references"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / f"{step_path.stem}_analysis.json"
    return step_path.with_suffix(".analysis.json")


def _print_analysis(a: dict) -> None:
    print(f"\n===== {a['source']} =====")
    print(
        f"  bbox: {a['bbox_size'][0]} x {a['bbox_size'][1]} x {a['bbox_size'][2]} mm"
        f"   volume: {a['volume_mm3']:.0f} mm^3   ({a['units_note']})"
    )
    print(f"  solids: {a['solid_count']}  (largest first)")
    for s in a["solids"][:6]:
        print(f"    {s['volume_mm3']:>10.1f} mm^3  bbox {s['bbox_min']} .. {s['bbox_max']}")
    print(f"  cylindrical features: {a['feature_count']}  (largest radius first)")
    for f in a["features"][:12]:
        print(
            f"    d={f['diameter']:>7.3f}  {f['axis_label']:>7}-axis {f['type']:<5} "
            f"p1={f['p1']}  p2={f['p2']}"
        )


def _print_compare(r: dict) -> None:
    print(f"\n===== compare =====\n  A: {r['a']}\n  B: {r['b']}")
    print(
        f"  bbox A {r['bbox_size_a']}  B {r['bbox_size_b']}  volume ratio B/A: {r['volume_ratio']}"
    )
    print(f"  features: A={r['feature_counts'][0]}  B={r['feature_counts'][1]}")
    print("  match scores:")
    for name, s in sorted(r["scores"].items(), key=lambda kv: -kv[1]):
        marker = "  <-- best" if name == r["best"] else ""
        print(f"    {name:<10} {s:6.1%}{marker}")
    print(f"  verdict: {r['verdict']}")
    if r["unmatched_under_best"]:
        print(f"  unmatched under {r['best']} (first {len(r['unmatched_under_best'])}):")
        for f in r["unmatched_under_best"]:
            print(
                f"    d={f['diameter']:>7.3f}  {f['axis_label']}-axis {f['type']:<5} p1={f['p1']}"
            )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("files", nargs="+", help="STEP file(s)")
    ap.add_argument(
        "--compare", action="store_true", help="compare exactly two files for identity / mirror"
    )
    ap.add_argument("-o", "--out", help="write analysis JSON to this path")
    ap.add_argument(
        "--save", action="store_true", help="write JSON to the part's references/ directory"
    )
    args = ap.parse_args(argv)

    if args.compare:
        if len(args.files) != 2:
            ap.error("--compare needs exactly two files")
        result = compare(args.files[0], args.files[1])
        _print_compare(result)
        if args.out:
            Path(args.out).write_text(json.dumps(result, indent=2))
            print(f"\n  JSON -> {args.out}")
        return

    for f in args.files:
        a = analyze(f)
        _print_analysis(a)
        if args.out or args.save:
            out = Path(args.out) if args.out else _default_json_path(Path(f))
            out.write_text(json.dumps(a, indent=2))
            print(f"  JSON -> {out}")


if __name__ == "__main__":
    main()
