"""
ADRS maritime layout — placement engine for the Saginaw SCE-20H2010LP.

Everything lives in the enclosure vendor STEP's native frame:

    X = width   interior walls at -252.09 .. +252.09
    Y = height  interior walls at -252.10 .. +252.10   (+Y is up)
    Z = depth   back wall inner -125.09, subpanel mounting face -109.22,
                door inner clear plane +131.10

`placement.json` is the source of truth for *where things go*; this module is
the machinery that puts them there and then refuses to believe itself.

Three things it will not let you get wrong:

  1. A part's translation is DERIVED from its declared target box, so a wrong
     rotation shows up immediately as a size mismatch rather than quietly
     sliding the part somewhere plausible.
  2. A bracket's holes are DERIVED from the mating component's real mounting
     holes, transformed through that component's own placement. The plate and
     the part it carries cannot drift out of line, because they are the same
     numbers.
  3. Every connector, vent, grille and service cover is declared as a keep-out
     patch on the part surface plus the free distance it needs. Anything that
     lands in one is an error, not a detail spotted later in a render.

Usage:
    uv run python parts/custom/adrs-maritime-layout-compact/layout.py            # verify
    uv run python parts/custom/adrs-maritime-layout-compact/layout.py --export   # + STEP
    uv run python parts/custom/adrs-maritime-layout-compact/layout.py --render   # + PNGs
    uv run python parts/custom/adrs-maritime-layout-compact/layout.py --drawings # + plate DXFs

Export options:
    --out DIR         write the STEP here instead of exports/. Use it: this repo sits
                      173 characters deep, so exports/<part>_v1.step is exactly 260
                      characters and SolidWorks cannot open it.
    --scaffold-only   export only the fabricated metal, the rail, the end stops and the
                      fasteners — no vendor models, no enclosure. ~2 MB instead of ~320.
    --no-enclosure    drop the Saginaw shell but keep the devices.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import cadquery as cq

# Windows consoles default to cp1252, which cannot encode the report glyphs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PART_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PLACEMENT_FILE = PART_DIR / "placement.json"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PART_DIR))

# Big vendor STEPs cost 6-16 s each to parse; BREP round-trips in well under a
# second, so the first load pays the toll and every later run is cheap.
CACHE_DIR = Path(os.environ.get("ADRS_STEP_CACHE", Path.home() / ".cache" / "adrs-stepcache"))

# ---------------------------------------------------------------------------
# Enclosure frame — measured from SCE-20H2010LP.stp, not from the sales drawing
# ---------------------------------------------------------------------------
ENCLOSURE = {
    "step": "C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/Saginaw"
            "/sce-20h2010lp/SCE-20H2010LP.stp",
    "x_min": -252.09, "x_max": 252.09,
    "y_min": -252.10, "y_max": 252.10,
    "z_back": -125.09,          # inner face of the rear wall
    "z_panel": -109.22,         # subpanel mounting face — the datum
    "z_door": 131.10,           # door inner clear plane
    "panel_half": 215.90,       # subpanel is 431.8 mm square
    "panel_thickness": 3.17,
    "stud_pitch": 193.68,       # 4 corner collars, 15.25" square pattern
    "stud_size": 18.92,
    "stud_z_max": -100.69,
}

AXES = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


# ---------------------------------------------------------------------------
# Geometry plumbing
# ---------------------------------------------------------------------------
def load_step(path: str | Path) -> cq.Shape:
    """Import a STEP, caching the kernel result as BREP for fast re-runs."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"STEP not found: {path}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = f"{path.stem}_{path.stat().st_size}_{int(path.stat().st_mtime)}.brep"
    cached = CACHE_DIR / key
    if cached.exists():
        return cq.Shape.importBrep(str(cached))
    shape = cq.importers.importStep(str(path)).val()
    shape.exportBrep(str(cached))
    return shape


def apply_rotations(shape: cq.Shape, ops: list[dict]) -> cq.Shape:
    """Rotate about the global origin, in the order given."""
    for op in ops:
        deg = float(op["degrees"])
        if deg % 360 == 0:
            continue
        shape = shape.rotate(cq.Vector(0, 0, 0), cq.Vector(*AXES[op["axis"]]), deg)
    return shape


def rotate_point(p: tuple, ops: list[dict]) -> tuple:
    """
    Apply the same rotation sequence to a bare point.

    This is what keeps bracket holes honest: the hole travels through exactly
    the transform its component did, so the two land on the same axis.
    """
    x, y, z = p
    for op in ops:
        a = math.radians(float(op["degrees"]))
        c, s = math.cos(a), math.sin(a)
        if op["axis"] == "X":
            y, z = y * c - z * s, y * s + z * c
        elif op["axis"] == "Y":
            x, z = x * c + z * s, -x * s + z * c
        else:
            x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


def rotated_axis(axis: str, ops: list[dict]) -> str:
    """Which enclosure axis a part-frame axis becomes after the rotations."""
    v = rotate_point(AXES[axis], ops)
    i = max(range(3), key=lambda k: abs(v[k]))
    return "XYZ"[i]


# id() is only unique among LIVE objects — CPython recycles the number as soon
# as a temporary is collected, so an id-keyed cache will happily hand one shape
# another shape's bounding box. Both caches therefore keep a strong reference to
# the key object, which pins the id for the lifetime of the entry.
_BBOX_CACHE: dict[int, tuple] = {}


def bbox_of(shape: cq.Shape) -> dict:
    """
    Bounding box, memoised.

    OCC recomputes this from scratch every call, and the verifier asks for the
    same boxes hundreds of times while pruning candidate pairs — uncached it
    dominates the entire run.
    """
    key = id(shape)
    hit = _BBOX_CACHE.get(key)
    if hit is None:
        b = shape.BoundingBox()
        hit = (shape, {"xmin": b.xmin, "xmax": b.xmax, "ymin": b.ymin,
                       "ymax": b.ymax, "zmin": b.zmin, "zmax": b.zmax})
        _BBOX_CACHE[key] = hit
    return hit[1]


def box_size(box: dict) -> tuple[float, float, float]:
    return (box["xmax"] - box["xmin"],
            box["ymax"] - box["ymin"],
            box["zmax"] - box["zmin"])


def place(shape: cq.Shape, spec: dict) -> tuple[cq.Shape, tuple]:
    """
    Orient a part and land it on its declared target box.

    Returns the placed shape and the translation that was applied, so the same
    transform can be replayed on hole positions and keep-out prisms.
    """
    shape = apply_rotations(shape, spec.get("rotate", []))
    actual = bbox_of(shape)
    target = spec["box"]

    anchor = spec.get("anchor", "min")
    if anchor == "min":
        t = (target["xmin"] - actual["xmin"],
             target["ymin"] - actual["ymin"],
             target["zmin"] - actual["zmin"])
    elif anchor == "center":
        t = ((target["xmin"] + target["xmax"]) / 2 - (actual["xmin"] + actual["xmax"]) / 2,
             (target["ymin"] + target["ymax"]) / 2 - (actual["ymin"] + actual["ymax"]) / 2,
             (target["zmin"] + target["zmax"]) / 2 - (actual["zmin"] + actual["zmax"]) / 2)
    else:
        raise ValueError(f"unknown anchor {anchor!r}")

    return shape.translate(cq.Vector(*t)), t


def transform_hole(h: dict, ops: list[dict], t: tuple) -> dict:
    """
    Map a mounting hole from part coordinates into the enclosure frame.

    The bracket's hole diameter is the clearance for the screw that goes
    through it, not whatever the component's own bore happens to be — those
    are different numbers (the B210's bore is a tapped M3, its bracket needs
    a 3.4 mm clearance hole).
    """
    import model as scaffold

    x, y, z = rotate_point((h["x"], h["y"], h["z"]), ops)
    size = h.get("size", "M4")
    out = dict(h)
    out.update({
        "x": x + t[0], "y": y + t[1], "z": z + t[2],
        "axis": rotated_axis(h.get("axis", "Z"), ops),
        "dia": h.get("dia", scaffold.clearance_dia(size)),
        "size": size, "id": h.get("id", ""),
    })
    return out


def transform_prism(k: dict, ops: list[dict], t: tuple) -> dict:
    """
    Map a keep-out patch from part coordinates into the enclosure frame, then
    grow it outward by the clearance the connector needs.

    Rotations here are multiples of 90 degrees, so an axis-aligned prism stays
    axis-aligned; transforming the eight corners and re-boxing is exact.
    """
    corners = [
        rotate_point((x, y, z), ops)
        for x in (k["xmin"], k["xmax"])
        for y in (k["ymin"], k["ymax"])
        for z in (k["zmin"], k["zmax"])
    ]
    box = {
        "xmin": min(c[0] for c in corners) + t[0],
        "xmax": max(c[0] for c in corners) + t[0],
        "ymin": min(c[1] for c in corners) + t[1],
        "ymax": max(c[1] for c in corners) + t[1],
        "zmin": min(c[2] for c in corners) + t[2],
        "zmax": max(c[2] for c in corners) + t[2],
    }
    # grow along the outward normal by the required free distance
    face = k.get("face", "+Z")
    out = rotate_point(
        tuple(v * (1 if face[0] == "+" else -1) for v in AXES[face[1]]), ops)
    clear = float(k.get("clear_out_mm", 0.0))
    i = max(range(3), key=lambda n: abs(out[n]))
    key = "xyz"[i]
    if out[i] > 0:
        box[f"{key}max"] += clear
    else:
        box[f"{key}min"] -= clear
    box["name"] = k.get("name", "keepout")
    box["clear"] = clear
    return box


def box_shape(b: dict) -> cq.Shape:
    dx, dy, dz = box_size(b)
    return (cq.Workplane("XY")
            .box(dx, dy, dz, centered=False)
            .translate((b["xmin"], b["ymin"], b["zmin"]))).val()


# ---------------------------------------------------------------------------
# Verification — the part that is allowed to say "no"
# ---------------------------------------------------------------------------
SIZE_TOL = 1.5      # mm — declared box vs measured envelope
OVERLAP_TOL = 50.0  # mm^3 — below this is kernel noise on touching faces


def _boxes_disjoint(a: dict, b: dict, gap: float = 0.0) -> bool:
    return (a["xmax"] < b["xmin"] + gap or b["xmax"] < a["xmin"] + gap or
            a["ymax"] < b["ymin"] + gap or b["ymax"] < a["ymin"] + gap or
            a["zmax"] < b["zmin"] + gap or b["zmax"] < a["zmin"] + gap)


_SOLID_CACHE: dict[int, list] = {}


def solids_of(shape: cq.Shape) -> list[tuple]:
    """(solid, bbox) pairs, cached — vendor parts have up to 196 solids."""
    key = id(shape)
    if key not in _SOLID_CACHE:
        _SOLID_CACHE[key] = [(s, bbox_of(s)) for s in shape.Solids()] or \
                            [(shape, bbox_of(shape))]
    return _SOLID_CACHE[key]


def overlap_volume(a: cq.Shape, b: cq.Shape) -> float:
    """
    Intersection volume, pruned solid-by-solid.

    A full boolean between two 200-solid vendor imports is minutes of work and
    almost all of it is wasted on solid pairs that are nowhere near each other.
    Bounding boxes settle those for free; only genuine candidates get a boolean.
    """
    total = 0.0
    for sa, ba in solids_of(a):
        for sb, bb in solids_of(b):
            if _boxes_disjoint(ba, bb):
                continue
            try:
                inter = sa.intersect(sb)
            except Exception:
                continue  # a failed boolean is not evidence of clearance
            total += sum(abs(s.Volume()) for s in inter.Solids())
    return total


def verify(placed: dict, specs: dict, keepouts: dict) -> tuple[list, list]:
    """Return (problems, notes). A non-empty problems list means do not build."""
    problems: list[str] = []
    notes: list[str] = []

    # 1. Does each part actually fill the box it claimed?
    for name, shape in placed.items():
        got, want = bbox_of(shape), specs[name]["box"]
        gs, ws = box_size(got), box_size(want)
        drift = max(abs(a - b) for a, b in zip(gs, ws))
        if drift > SIZE_TOL and not specs[name].get("drilled"):
            problems.append(
                f"{name}: declared {ws[0]:.1f}x{ws[1]:.1f}x{ws[2]:.1f} but measures "
                f"{gs[0]:.1f}x{gs[1]:.1f}x{gs[2]:.1f} (off by {drift:.1f} mm)")

    # 2. Inside the enclosure?
    E = ENCLOSURE
    for name, shape in placed.items():
        if specs[name].get("protrudes_wall"):
            continue  # the TEC deliberately hangs outside
        b = bbox_of(shape)
        for label, lo, hi in (("X", E["x_min"], E["x_max"]),
                              ("Y", E["y_min"], E["y_max"]),
                              ("Z", E["z_panel"], E["z_door"])):
            k = label.lower()
            if b[f"{k}min"] < lo - 0.5:
                problems.append(f"{name}: {label}min {b[f'{k}min']:.1f} past limit {lo:.1f}")
            if b[f"{k}max"] > hi + 0.5:
                problems.append(f"{name}: {label}max {b[f'{k}max']:.1f} past limit {hi:.1f}")

    # 3. Pairwise solid interference — real booleans, not box maths
    names = sorted(placed)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if b in specs[a].get("may_touch", []) or a in specs[b].get("may_touch", []):
                continue
            if _boxes_disjoint(bbox_of(placed[a]), bbox_of(placed[b])):
                continue
            vol = overlap_volume(placed[a], placed[b])
            if vol > OVERLAP_TOL:
                problems.append(f"INTERFERENCE {a} <-> {b}: {vol / 1000:.1f} cm3")
            elif vol > 0:
                notes.append(f"{a} <-> {b}: {vol:.0f} mm3 grazing contact")

    # 4. Subpanel corner collars are keep-out
    half, s, zmax = E["stud_pitch"], E["stud_size"] / 2, E["stud_z_max"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * half, sy * half
            for name, shape in placed.items():
                if specs[name].get("protrudes_wall"):
                    continue
                b = bbox_of(shape)
                if (b["xmin"] < cx + s and b["xmax"] > cx - s and
                        b["ymin"] < cy + s and b["ymax"] > cy - s and
                        b["zmin"] < zmax):
                    problems.append(
                        f"{name} clashes with the subpanel corner collar at ({cx:.0f}, {cy:.0f})")

    # 5. Connector / vent / service keep-outs — nothing may sit in front of one
    for owner, klist in keepouts.items():
        for k in klist:
            kshape = None
            for name, shape in placed.items():
                if name == owner:
                    continue
                if specs[name].get("ignores_keepouts"):
                    continue
                if _boxes_disjoint(k, bbox_of(shape)):
                    continue
                if kshape is None:
                    kshape = box_shape(k)
                vol = overlap_volume(kshape, shape)
                if vol > OVERLAP_TOL:
                    problems.append(
                        f"BLOCKED CONNECTOR: {name} intrudes {vol / 1000:.1f} cm3 into "
                        f"'{k['name']}' on {owner} (needs {k['clear']:.0f} mm clear)")
    return problems, notes


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def load_placement(path: Path = PLACEMENT_FILE) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build(placement: dict | None = None, with_enclosure: bool = True,
          with_fasteners: bool = True):
    """Place every part, drill every bracket, fit every screw."""
    import model as scaffold

    placement = placement or load_placement()
    items = placement["placements"]
    specs = {it["name"]: it for it in items}

    placed: dict[str, cq.Shape] = {}
    keepouts: dict[str, list] = {}
    holes_for: dict[str, list] = {}   # bracket name -> holes in enclosure coords
    screws: list = []

    # --- pass 1: components from STEP -------------------------------------
    for it in items:
        if it.get("source") == "scaffold":
            continue
        ops = it.get("rotate", [])
        shape, t = place(load_step(it["step"]), it)
        placed[it["name"]] = shape

        keepouts[it["name"]] = [transform_prism(k, ops, t)
                                for k in it.get("keepouts", [])]

        target = it.get("mounted_to")
        for h in it.get("mount_holes", []):
            eh = transform_hole(h, ops, t)
            eh["owner"] = it["name"]
            if target:
                holes_for.setdefault(target, []).append(eh)

    # --- pass 2: brackets, drilled from the holes their component gave them -
    for it in items:
        if it.get("source") != "scaffold":
            continue
        shape, t = place(scaffold.build_member(it), it)
        drills = list(holes_for.get(it["name"], []))
        drills += [dict(h, owner=it["name"],
                        dia=h.get("dia", scaffold.clearance_dia(h.get("size", "M4"))))
                   for h in it.get("own_holes", [])]
        if drills:
            shape = scaffold.drill(
                shape, [{**h, "dia": scaffold.clearance_dia(h.get("size", "M4"))}
                        for h in drills])
            it["drilled"] = True
        placed[it["name"]] = shape
        holes_for[it["name"]] = drills

    # --- pass 3: fasteners -------------------------------------------------
    if with_fasteners:
        for bracket, drills in holes_for.items():
            if bracket not in placed:
                continue
            for h in drills:
                size = h.get("size", "M4")
                length = h.get("screw_len", 16.0)
                d = AXES[h["axis"]]
                sign = h.get("screw_dir", -1)
                scr = scaffold.socket_head_screw(size, length).val()
                # default axis is +Z; rotate onto the hole axis
                if h["axis"] == "X":
                    scr = scr.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90)
                elif h["axis"] == "Y":
                    scr = scr.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90)
                if sign < 0:
                    ax = (0, 1, 0) if h["axis"] in ("X", "Z") else (1, 0, 0)
                    scr = scr.rotate(cq.Vector(0, 0, 0), cq.Vector(*ax), 180)
                off = h.get("screw_offset", 0.0)
                scr = scr.translate(cq.Vector(
                    h["x"] + d[0] * off * sign,
                    h["y"] + d[1] * off * sign,
                    h["z"] + d[2] * off * sign))
                screws.append(scr)

    asm = cq.Assembly(name="adrs-maritime-layout")
    if with_enclosure:
        asm.add(load_step(ENCLOSURE["step"]), name="enclosure",
                color=cq.Color(0.72, 0.74, 0.76, 0.25))
    for name, shape in placed.items():
        rgba = specs[name].get("color", [0.55, 0.58, 0.62, 1.0])
        asm.add(shape, name=name, color=cq.Color(*rgba))
    for i, s in enumerate(screws):
        asm.add(s, name=f"screw_{i:03d}", color=cq.Color(0.25, 0.26, 0.28, 1.0))

    return asm, placed, specs, keepouts, screws, holes_for


def report_footprint(placed: dict, specs: dict, keepouts: dict,
                     cell: float = 2.0) -> None:
    """
    How much of the subpanel is actually consumed, and how much usable room is
    left in one piece.

    A bounding box around everything is a bad compactness score: adding one
    device in a corner can move it 100 mm without the layout getting any
    fuller. This rasterises the real XY silhouette instead, and does it twice —
    once for metal, once for metal PLUS every declared connector, vent and
    service keep-out. The second grid is the honest one, because a connector's
    cable volume is just as unavailable as the box it plugs into. The largest
    empty rectangle is then measured on it, which is the number that answers
    "will the next device fit".

    The cooler is included even though it hangs through the wall: the 55 mm of
    panel behind it is not free, and a metric that says otherwise is lying.
    """
    half = ENCLOSURE["panel_half"]
    n = math.ceil(2 * half / cell)
    solid = [[False] * n for _ in range(n)]
    grid = [[False] * n for _ in range(n)]

    def cells(lo, hi):
        return (max(0, int((lo + half) / cell)),
                min(n, int((hi + half) / cell) + 1))

    def stamp(target, b) -> bool:
        i0, i1 = cells(b["xmin"], b["xmax"])
        j0, j1 = cells(b["ymin"], b["ymax"])
        if i0 >= i1 or j0 >= j1:
            return False
        for i in range(i0, i1):
            row = target[i]
            for j in range(j0, j1):
                row[j] = True
        return True

    items = 0
    for name, shape in placed.items():
        b = bbox_of(shape)
        if stamp(solid, b):
            items += 1
        stamp(grid, b)
    for klist in keepouts.values():
        for k in klist:
            stamp(grid, k)

    area = cell * cell
    used = sum(1 for col in solid for v in col if v) * area
    committed = sum(1 for col in grid for v in col if v) * area
    total = (2 * half) ** 2
    print(f"\n  subpanel coverage:  {used / 100:.0f} cm2 hardware "
          f"({100 * used / total:.0f}%), {committed / 100:.0f} cm2 committed once "
          f"keep-outs count ({100 * committed / total:.0f}%), {items} items")

    # largest all-free rectangle, by the standard histogram scan
    heights = [0] * n
    best = (0, 0, 0, 0, 0)   # area, i0, i1, j0, j1
    for j in range(n):
        for i in range(n):
            heights[i] = 0 if grid[i][j] else heights[i] + 1
        stack: list[tuple[int, int]] = []      # (start index, bar height)
        for i in range(n + 1):
            h = heights[i] if i < n else 0
            start = i
            while stack and stack[-1][1] >= h:
                s, sh = stack.pop()
                area = sh * (i - s)
                if area > best[0]:
                    best = (area, s, i, j - sh + 1, j + 1)
                start = s
            stack.append((start, h))
    a, i0, i1, j0, j1 = best
    print(f"  largest free box:   {(i1 - i0) * cell:.0f} x {(j1 - j0) * cell:.0f} mm "
          f"at X[{i0 * cell - half:.0f},{i1 * cell - half:.0f}] "
          f"Y[{j0 * cell - half:.0f},{j1 * cell - half:.0f}]")


def arg_value(argv: list[str], flag: str) -> str | None:
    """Read `--flag VALUE` or `--flag=VALUE` out of argv."""
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def main(argv: list[str]) -> int:
    placement = load_placement()
    print(f"\n  {placement.get('title', 'ADRS maritime layout')}")

    asm, placed, specs, keepouts, screws, holes_for = build(
        placement, with_enclosure="--no-enclosure" not in argv)
    print(f"  {len(placed)} placed items, {len(screws)} fasteners\n")

    for name in sorted(placed):
        b = bbox_of(placed[name])
        sx, sy, sz = box_size(b)
        print(f"    {name:<26} {sx:6.1f} x {sy:6.1f} x {sz:6.1f} mm   "
              f"X[{b['xmin']:7.1f},{b['xmax']:7.1f}] "
              f"Y[{b['ymin']:7.1f},{b['ymax']:7.1f}] "
              f"Z[{b['zmin']:7.1f},{b['zmax']:7.1f}]")

    nk = sum(len(v) for v in keepouts.values())
    print(f"\n  checking {nk} connector/vent/service keep-outs")
    problems, notes = verify(placed, specs, keepouts)
    for n in notes:
        print(f"    note: {n}")
    if problems:
        print(f"\n  ✗ {len(problems)} problem(s):")
        for p in problems:
            print(f"      - {p}")
    else:
        print("  ✓ no interference, nothing blocking a connector, all inside limits")

    report_footprint(placed, specs, keepouts)
    allb = [bbox_of(s) for s in placed.values()]
    print(f"  stack depth used:   "
          f"{max(b['zmax'] for b in allb) - ENCLOSURE['z_panel']:.0f} mm of "
          f"{ENCLOSURE['z_door'] - ENCLOSURE['z_panel']:.0f} mm")

    if "--export" in argv:
        # Windows MAX_PATH is 260 including the terminator, and this repo's own
        # path is 173 characters before we add anything. exports/<part>_v1.step
        # lands on exactly 260, so SolidWorks — which still uses the legacy Win32
        # API regardless of the LongPathsEnabled registry key — reports the file
        # as "invalid, not found, locked or of an incompatible type". --out puts
        # it somewhere short instead.
        out_dir = Path(arg_value(argv, "--out") or EXPORTS_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        scaffold_only = "--scaffold-only" in argv
        if scaffold_only:
            # Just the metal we designed, plus the rail, end stops and every
            # fastener. The vendor models are already in the SolidWorks
            # assembly, and leaving them out takes the file from ~320 MB to a
            # size SolidWorks opens in seconds.
            sub = cq.Assembly(name=f"{PART_DIR.name}-scaffold")
            for name, shape in placed.items():
                if specs[name].get("source") != "scaffold":
                    continue
                rgba = specs[name].get("color", [0.55, 0.58, 0.62, 1.0])
                sub.add(shape, name=name, color=cq.Color(*rgba))
            for i, s in enumerate(screws):
                sub.add(s, name=f"screw_{i:03d}", color=cq.Color(0.25, 0.26, 0.28, 1.0))
            target, name = sub, f"{PART_DIR.name}_scaffold_v1.step"
        else:
            target, name = asm, f"{PART_DIR.name}_v1.step"

        out = out_dir / name
        if len(str(out.resolve())) > 258:
            print(f"\n  ! {out} is {len(str(out.resolve()))} characters — over Windows' "
                  f"260-char MAX_PATH. SolidWorks will refuse it; pass --out with a "
                  f"shorter directory.")
        target.save(str(out))
        mb = out.stat().st_size / 1e6
        try:
            shown = out.relative_to(PROJECT_ROOT)
        except ValueError:
            shown = out
        print(f"\n  ✓ {shown}  ({mb:.0f} MB, {len(str(out.resolve()))} char path)")

    if "--drawings" in argv:
        out_dir = PART_DIR / "exports" / "plates"
        out_dir.mkdir(parents=True, exist_ok=True)
        print("\n  flat patterns (outline + drilled holes, 1:1 mm):")
        for name in sorted(placed):
            # Purchased stock — a rail and two clamp-on end stops — has no flat
            # pattern to cut, so it never belongs in the shop pack.
            if specs[name].get("source") != "scaffold" or specs[name].get("purchased"):
                continue
            shp, b = placed[name], bbox_of(placed[name])
            # the plate's thin axis is its thickness; the big face normal to it
            # is the flat pattern the shop cuts
            thin = min(("X", b["xmax"] - b["xmin"]), ("Y", b["ymax"] - b["ymin"]),
                       ("Z", b["zmax"] - b["zmin"]), key=lambda kv: kv[1])[0]
            want = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[thin]
            best, best_area = None, 0.0
            for f in shp.Faces():
                try:
                    n = f.normalAt()
                except Exception:
                    continue
                if abs(abs(n.x * want[0] + n.y * want[1] + n.z * want[2]) - 1) > 1e-3:
                    continue
                if f.Area() > best_area:
                    best, best_area = f, f.Area()
            if best is None:
                print(f"  ! {name}: no face normal to {thin}")
                continue
            # lay the face into XY so the DXF comes out in true size
            flat = best
            if thin == "X":
                flat = flat.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90)
            elif thin == "Y":
                flat = flat.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90)
            fb = bbox_of(flat)
            flat = flat.translate(cq.Vector(-fb["xmin"], -fb["ymin"], -fb["zmin"]))
            path = out_dir / f"{name}.dxf"
            try:
                cq.exporters.export(cq.Workplane(obj=flat), str(path), exportType="DXF")
                holes = len([w for w in flat.Wires()]) - 1
                fb = bbox_of(flat)
                w, h = sorted((fb["xmax"] - fb["xmin"], fb["ymax"] - fb["ymin"],
                               fb["zmax"] - fb["zmin"]), reverse=True)[:2]
                print(f"  ✓ {name:<20} {w:6.1f} x {h:6.1f} mm, "
                      f"{max(holes, 0)} holes  -> {path.name}")
            except Exception as exc:
                print(f"  ! {name}: DXF export failed ({exc})")

    panel_drills = sorted(
        (h for hs in holes_for.values() for h in hs if h.get("into_subpanel")),
        key=lambda h: (round(h["x"], 2), round(h["y"], 2)))
    if panel_drills:
        sched = PART_DIR / "exports" / "subpanel_drilling.csv"
        sched.parent.mkdir(parents=True, exist_ok=True)
        lines = ["x_mm,y_mm,dia_mm,screw,for_bracket"]
        lines += [f"{h['x']:.2f},{h['y']:.2f},{h['dia']:.1f},{h['size']},{h['owner']}"
                  for h in panel_drills]
        sched.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n  subpanel drilling: {len(panel_drills)} holes -> "
              f"{sched.relative_to(PROJECT_ROOT)}")

    if "--render" in argv:
        from lib.render_step import render_scene

        # The enclosure STEP is Y-up; the renderer's named views assume Z-up and
        # put the "front" camera at world -Y. +90 about X sends enclosure +Y (up)
        # to world +Z and enclosure +Z (the door) to world -Y, so "front" really
        # is the view through the open door.
        def zup(s):
            return s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90)

        items = [(zup(load_step(ENCLOSURE["step"])), (0.75, 0.77, 0.80), 0.10)] \
            if "--no-enclosure" not in argv else []
        for name in sorted(placed):
            rgba = specs[name].get("color", [0.55, 0.58, 0.62, 1.0])
            items.append((zup(placed[name]), tuple(rgba[:3]),
                          rgba[3] if len(rgba) > 3 else 1.0))
        for s in screws:
            items.append((zup(s), (0.20, 0.21, 0.23), 1.0))
        out_dir = PART_DIR / "references" / "views"
        for w in render_scene(items, out_dir, "layout",
                              views=("front", "right", "top", "iso"), size=1400):
            print(f"  ✓ {w.relative_to(PROJECT_ROOT)}")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
