"""
Split the vendor Bedrock V3000 STEP into its chassis variants — including the
hybrid, which the file supports but does not ship as a body.

SolidRun ships one file containing THREE chassis at a single origin — 60 W (|X|=36.5),
30 W (|X|=22.5) and Tile (|X|=14.5) — plus 19 connector/antenna solids shared by all
three. Importing it naively gives you all three nested inside one another, which is
how a bracket ends up designed against the wrong envelope.

The architecture underneath, measured rather than assumed:

    60 W chassis  =  Tile core  +  two identical fin banks, separable at |X| = 14.5

  * clipping the 60 W to |X| <= 14.5 gives 206 896 mm3 against the Tile's
    206 454 mm3 — a 442 mm3 difference, which is exactly the volume of the six
    M4 bores the Tile has and the 60 W does not (6 x pi x 2.05^2 x 5.83 = 462);
  * a 539-point classification sweep over that band agrees 535/539, and all four
    disagreements sit inside one of those bores;
  * the material outboard of |X| = 14.5 is 131 921.4 mm3 on each side, with
    mirror-identical bounding boxes.

So a **hybrid** — the Tile core carrying ONE fin bank — is a real configuration:
flat 20 410 mm2 side one way, 60 W fin bank the other. `hybrid()` builds it from
the file's own geometry. It is a two-solid compound on purpose: that is what the
thing is, a core with a bank attached, and fusing two 1000-face solids across
coincident faces takes minutes and gains nothing.

Note the flat side keeps the Tile's six M4x0.7 bores, tapped from BOTH ends
(thread |X| 11.000..13.916 each side, 22 mm of open cavity between). Screws
retaining the fin bank on one side and screws mounting the unit on the other use
the same six bores from opposite ends without meeting.

Usage:
    uv run python parts/vendor/solidrun-bedrock-v3000/split_variants.py [--out DIR]

Units: mm.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
DEFAULT_STEP = PART_DIR / "Bedrock V3000 Basic 3D model.step"

# variant key -> nominal X half-width of that chassis
VARIANTS = {"60w": 36.5, "30w": 22.5, "tile": 14.5}

# Where the 60 W chassis separates into its Tile core and its two fin banks.
# Measured, not chosen: it is the Tile's own outer face and the 60 W's own
# internal wall, and both fin banks start exactly there.
FIN_SPLIT_X = 14.5
FIN_BANK_VOLUME = 131921.4      # mm^3, each bank, measured
FIN_SIDES = ("+X", "-X")


def vendor_step() -> Path:
    """The vendor file: $BEDROCK_V3000_STEP if set, else the copy in this directory."""
    override = os.environ.get("BEDROCK_V3000_STEP")
    path = Path(override) if override else DEFAULT_STEP
    if not path.is_file():
        raise FileNotFoundError(
            f"Bedrock V3000 STEP not found at {path}. Put it in {PART_DIR} or set "
            f"BEDROCK_V3000_STEP to its absolute path."
        )
    return path


def load_solids(path: Path | None = None) -> list[cq.Shape]:
    """Every solid in the vendor file, unsorted."""
    return cq.importers.importStep(str(path or vendor_step())).solids().vals()


def chassis(variant: str = "60w", solids: list[cq.Shape] | None = None) -> cq.Shape:
    """
    The bare chassis shell of one variant.

    Selected by measured X half-width, not by index — solid ordering in a STEP file
    is not a contract, but 36.5 / 22.5 / 14.5 mm are.
    """
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {sorted(VARIANTS)}, got {variant!r}")
    half = VARIANTS[variant]
    candidates = [
        s for s in (solids if solids is not None else load_solids())
        if abs(s.BoundingBox().xmax - half) < 0.05 and s.Volume() > 100_000
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly 1 chassis at |X|={half}, found {len(candidates)} — "
            "the vendor file has changed; re-run lib.analyze_step before trusting anything."
        )
    return candidates[0]


def connectors(solids: list[cq.Shape] | None = None) -> cq.Shape:
    """The connector / antenna solids, shared by all three chassis variants."""
    solids = solids if solids is not None else load_solids()
    rest = [s for s in solids if s.Volume() < 100_000]
    return cq.Compound.makeCompound(rest)


def unit(variant: str = "60w", solids: list[cq.Shape] | None = None) -> cq.Shape:
    """One chassis plus the shared connectors — the thing that actually sits on a shelf."""
    solids = solids if solids is not None else load_solids()
    return cq.Compound.makeCompound([chassis(variant, solids)] + list(connectors(solids).Solids()))


def _clip(shape: cq.Shape, x0: float, x1: float) -> cq.Shape:
    """The part of `shape` between two X planes."""
    cutter = (cq.Workplane("XY").box(x1 - x0, 240, 260, centered=False)
              .translate((x0, -120, -40)).val())
    return shape.intersect(cutter)


def fin_bank(side: str = "+X", solids: list[cq.Shape] | None = None) -> cq.Shape:
    """
    One 60 W fin bank on its own — the 60 W chassis outboard of FIN_SPLIT_X.

    Both banks measure 131 921.4 mm3 with mirror-identical bounding boxes, so
    either one is the same part; `side` only says where it sits.
    """
    if side not in FIN_SIDES:
        raise ValueError(f"side must be one of {FIN_SIDES}, got {side!r}")
    c60 = chassis("60w", solids)
    bank = (_clip(c60, FIN_SPLIT_X, 40.0) if side == "+X"
            else _clip(c60, -40.0, -FIN_SPLIT_X))
    got = sum(abs(s.Volume()) for s in bank.Solids())
    if abs(got - FIN_BANK_VOLUME) > 0.02 * FIN_BANK_VOLUME:
        raise RuntimeError(
            f"the {side} fin bank measures {got:.1f} mm3, not the expected "
            f"{FIN_BANK_VOLUME:.1f} — the vendor file has changed, so re-measure "
            "the split plane before trusting anything built on it.")
    return bank


def hybrid(fin_side: str = "+X", solids: list[cq.Shape] | None = None) -> cq.Shape:
    """
    Tile core plus ONE fin bank: flat 20 410 mm2 side one way, 60 W fins the other.

    Returned as a two-solid compound rather than a fused solid — that is what the
    configuration physically is, and fusing across the coincident faces at
    |X| = 14.5 costs minutes of kernel time for no geometric gain.
    """
    solids = solids if solids is not None else load_solids()
    return cq.Compound.makeCompound(
        [chassis("tile", solids)] + list(fin_bank(fin_side, solids).Solids()))


def hybrid_unit(fin_side: str = "+X", solids: list[cq.Shape] | None = None) -> cq.Shape:
    """The hybrid chassis plus the shared connectors."""
    solids = solids if solids is not None else load_solids()
    return cq.Compound.makeCompound(
        list(hybrid(fin_side, solids).Solids()) + list(connectors(solids).Solids()))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", default=str(PART_DIR / "exports"),
                    help="output directory (default: this part's exports/)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    src = vendor_step()
    print(f"  reading {src}")
    solids = load_solids(src)
    print(f"  {len(solids)} solids")

    conn = connectors(solids)
    cq.exporters.export(cq.Workplane(obj=conn), str(out / "bedrock_connectors.step"))
    print(f"  ok {out / 'bedrock_connectors.step'}  ({len(conn.Solids())} solids)")

    for key, half in VARIANTS.items():
        ch = chassis(key, solids)
        cq.exporters.export(cq.Workplane(obj=ch), str(out / f"bedrock_chassis_{key}.step"))
        cq.exporters.export(cq.Workplane(obj=unit(key, solids)),
                            str(out / f"bedrock_unit_{key}.step"))
        print(f"  ok {key:>4}  |X|={half:<5}  vol={ch.Volume():>10.1f} mm^3  "
              f"-> bedrock_chassis_{key}.step + bedrock_unit_{key}.step")

    for side in FIN_SIDES:
        tag = "posX" if side == "+X" else "negX"
        hyb = hybrid(side, solids)
        bb = hyb.BoundingBox()
        cq.exporters.export(cq.Workplane(obj=hyb), str(out / f"bedrock_chassis_hybrid_{tag}.step"))
        cq.exporters.export(cq.Workplane(obj=hybrid_unit(side, solids)),
                            str(out / f"bedrock_unit_hybrid_{tag}.step"))
        print(f"  ok hybrid fins {side}   vol={hyb.Volume():>10.1f} mm^3   "
              f"X {bb.xmin:.1f}..{bb.xmax:.1f}  -> bedrock_chassis_hybrid_{tag}.step "
              f"+ bedrock_unit_hybrid_{tag}.step")


if __name__ == "__main__":
    main()
