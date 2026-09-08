"""
Measure the chassis' true cross-section outline at a Z station, fast.

Written to answer one question, and it answered it in the negative — which is
why it is kept. The `low_profile_side` variant originally seated on the chassis'
end flare, the band below Z = 7 (and above Z = 153) where the fin ramps run out
to the end cap and a coarse 0.5 mm scan reads as continuous solid skin. A saddle
there would have carried the unit on real metal with no fin-tip contact.

It is not solid skin. At Z = 4 the outer surface still alternates on the 10.15 mm
fin pitch — fin ramps out at |X| ~ 33.5, root-wall valleys back at |X| ~ 25.4 —
so a saddle would bear on about thirteen fin-ramp edges. The flare seat was
abandoned on this evidence and `low_profile_side` became a bolted joint with a
non-contacting guard instead. See DESIGN_NOTES.md section 7.

Booleans against the 1300-face vendor solid are minutes-slow and point
classification runs at ~0.3 s per point, so this works on the tessellation:
intersect every triangle with the plane, keep the crossing segments, and report
the outer half-width against Y. Chord error at the default tolerance is under
0.05 mm, well below anything it is used to decide.

    uv run python parts/custom/bedrock-v3000-mount/section_profile.py
    uv run python parts/custom/bedrock-v3000-mount/section_profile.py --z 4 --json out.json

Units: mm.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PART_DIR = Path(__file__).parent

# Y stations the saddle profile is sampled at. Dense where the lens is turning.
SAMPLE_Y = (0.0, 10.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0,
            50.0, 55.0, 58.0, 60.0, 62.0, 63.0, 64.0)


def _tess(shape, tol: float = 0.08, ang: float = 0.15):
    verts, tris = shape.tessellate(tol, ang)
    return [(v.x, v.y, v.z) for v in verts], tris


def section_segments(pts, tris, z: float) -> list[tuple]:
    """Every segment where the triangulated surface crosses the plane Z = z."""
    segs = []
    for a, b, c in tris:
        t = (pts[a], pts[b], pts[c])
        d = [p[2] - z for p in t]
        if min(d) > 0 or max(d) < 0:
            continue
        hits = []
        for i in range(3):
            j = (i + 1) % 3
            di, dj = d[i], d[j]
            if di == 0.0:
                hits.append((t[i][0], t[i][1]))
            if (di < 0) != (dj < 0) and di != dj:
                f = di / (di - dj)
                hits.append((t[i][0] + f * (t[j][0] - t[i][0]),
                             t[i][1] + f * (t[j][1] - t[i][1])))
        if len(hits) >= 2:
            segs.append((hits[0], hits[1]))
    return segs


def half_width_profile(shape, z: float, ys=SAMPLE_Y, band: float = 0.6) -> list[tuple]:
    """
    Outer half-width |X| of the chassis at plane Z = z, sampled at each Y in `ys`.

    `band` is how far either side of a sample Y a section point may lie and still
    count, so a Y that falls between two triangle vertices still returns a value.
    """
    pts, tris = _tess(shape)
    segs = section_segments(pts, tris, z)
    flat = [p for s in segs for p in s]
    out = []
    for y in ys:
        xs = [abs(px) for px, py in flat if abs(abs(py) - y) <= band]
        out.append((y, round(max(xs), 3) if xs else None))
    return out


def main(argv: list[str] | None = None) -> None:
    import importlib.util
    import sys

    key = "bedrock_v3000_mount.interface"
    iface = sys.modules.get(key)
    if iface is None:
        spec = importlib.util.spec_from_file_location(key, PART_DIR / "interface.py")
        iface = importlib.util.module_from_spec(spec)
        sys.modules[key] = iface
        spec.loader.exec_module(iface)

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--variant", default="60w", choices=sorted(iface.VARIANTS))
    ap.add_argument("--z", type=float, nargs="+", default=[2.0, 3.0, 4.0, 5.0, 6.0,
                                                           154.0, 156.0, 157.0, 158.0])
    ap.add_argument("--json", help="write the profiles to this path")
    args = ap.parse_args(argv)

    shape = iface.bedrock_chassis(args.variant).val()
    pts, tris = _tess(shape)
    print(f"  {args.variant}: {len(pts)} vertices, {len(tris)} triangles")

    result = {}
    for z in args.z:
        segs = section_segments(pts, tris, z)
        flat = [p for s in segs for p in s]
        prof = []
        for y in SAMPLE_Y:
            xs = [abs(px) for px, py in flat if abs(abs(py) - y) <= 0.6]
            prof.append([y, round(max(xs), 2) if xs else None])
        result[str(z)] = prof
        print(f"  Z={z:6.1f}  |X| by Y: "
              + ", ".join(f"{y:g}:{v}" for y, v in prof))

    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2))
        print(f"  JSON -> {args.json}")


if __name__ == "__main__":
    main()
