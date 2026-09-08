# SolidRun Bedrock V3000 — vendor STEP

`Bedrock V3000 Basic 3D model.step`, as shipped by SolidRun. Purchased part: we do not
fabricate anything here. It lives in the repo so brackets can be cut against exact vendor
B-rep instead of transcribed numbers.

## The trap: three chassis in one file

The file contains **22 solids**, and the three largest are **three different chassis
variants superimposed at a single origin**. Import it naively and you get all three nested
inside one another, plus one shared set of connector/antenna solids that belongs to all of
them. Tell them apart by X half-width — every other dimension is shared:

| Variant | \|X\| | Shell volume | ~Mass (Al) | Sides | Side fixings |
|---|---|---|---|---|---|
| **60 W** | 36.5 | 470 741 mm³ | 1271 g | 13 fins/side, 10.15 mm pitch, tips 0.395 mm × 146 mm | none |
| **30 W** | 22.5 | 267 463 mm³ | 722 g | 11 fins/side, tips 0.200 mm × 152 mm | none |
| **Tile** | 14.5 | 206 453 mm³ | 557 g | flat, 20 410 mm² clean flat each side | 6× M4×0.7 |
| **hybrid** *(derived)* | −14.5…36.5 | 338 376 mm³ | 914 g | flat one side, 60 W bank the other | 6× M4×0.7 on the flat side |

### And a fourth the file supports but does not ship

Measured, the **60 W is a Tile core with two identical fin banks on it**, separable at
|X| = 14.5:

* clipping the 60 W to |X| <= 14.5 gives 206 896 mm3 against the Tile's 206 454 — the
  442 mm3 difference is exactly the six M4 bores the Tile has and the 60 W does not;
* a 539-point sweep through that band agrees 535/539, with all four disagreements inside
  one of those bores;
* the material outboard is 131 921.4 mm3 on **each** side, mirror-identical.

And the Tile core's six M4x0.7 are tapped from **both** ends (thread |X| 11.000..13.916 a
side, 22 mm of cavity between) — a heatsink attachment pattern, usable from both ends at
once. So a **hybrid** is a real configuration: Tile core + ONE bank, flat 20 410 mm2 side
one way and a 60 W fin bank the other, 51 mm wide, 914 g of aluminium.

`split_variants.hybrid()` builds it from this file's own geometry, and refuses if the bank
ever stops measuring 131 921.4 mm3. It is *derived* — no hybrid body ships in the STEP.

`split_variants.py` writes each variant out on its own, plus the shared connectors, three
"unit" compounds (chassis + connectors) and both handednesses of hybrid:

```bash
UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv run python parts/vendor/solidrun-bedrock-v3000/split_variants.py --out C:/work/bedrock
```

## Frame

**X** across the unit (fin direction) · **Y** fore/aft, **−Y is the I/O panel**, **+Y is
the bare back wall** · **Z** up the long axis, 0 = bottom end cap, 160 = top end cap,
SMA barrels to 170.

## What you can actually bolt to

Measured, not assumed. Ring and axial probes; see `references/`.

| | Where | Size |
|---|---|---|
| **2× M3×0.5** blind tapped | +Y back wall, (0, 65, 50) and (0, 65, 110), 60.000 mm apart, **collinear on X=0** | hole runs Y 65.000→62.000 = **3.000 mm**, 1.0 mm of wall behind, then internal cavity |
| **1× M4×0.7** blind tapped | −Z bottom cap, (+6, 0, 0) | void Z 0→8.95, thread faces 0→8.09 |
| ~~1× M4×0.7~~ | −Z bottom cap, (−6, 0, 0) | **occupied** — vendor screw shank solid Z 0.6→6.0 |
| **6× M4×0.7** (Tile **core** — Tile and hybrid, not 30 W / 60 W) | X axis at (Y,Z) = (−60,10) (60,10) (0,40) (0,110) (−50,150) (50,150) | tapped both ends, 3.5 mm max penetration per side, both ends usable at once |

**That is the entire external fixing set on a 30 W or 60 W.** There are no holes on ±X,
none on −Y, none on +Z. A Tile core — bare Tile or hybrid — additionally has the six side
M4 above. The eight full-length Ø4 "holes" visible in the 60 W fin bank are not bores — each
is a single concave cylindrical face of 64.6° or 95.3° sweep (an R2.0 fin-root fillet),
open to the fin channel along its whole length.

**Hard penetration limits.** A screw more than **3.0 mm** past the bracket at the +Y M3s
bottoms out and jacks the bracket off the face. Keep the −Z M4 under **8.0 mm**.

## Faces you must not mount to

* **−Y** — the I/O panel. The flat is only X −10…+10 and connector windows occupy
  Z 4.4…153.3 of it. One module stands **2.957 mm proud** (to Y = −67.957) and seven panel
  screw heads stand 0.292 mm proud. Allow 55 mm of cable clearance.
* **+Z** — four SMA bulkheads Ø10.2 standing to Z = 170, a recessed DC/GPIO connector and
  an aux header proud to Z = 161.582. Allow 45 mm.
* **±X (60 W / 30 W)** — fin banks. 407.3 mm² of bearing on the 60 W, in seven strips
  0.395 mm wide. Nothing can bear on that, and covering it kills half the convection area.

## Cooling, and why orientation is not free

Fins are thin plates in the X–Z plane, stacked along Y at 10.15 mm pitch. **The channels
between them run along Z and are open at both the top and the bottom.** The unit is a
vertical chimney: **+Z up is the only orientation in which natural convection works as
designed.** Both ±X banks are live — they are mirror-identical, 407.30 mm² of tip flats
each — so neither may be shadowed.

## The +Y bearing land is narrower than it looks

The continuous flat at Y = 65.000 is **only 20 mm wide** (X −10…+10, Z 1…159). Scanlines
just below it:

```
y = 64.90   material at X −13.25…−11.0 and +11.0…+13.25   ← blend ridges, 0.1 mm low
y = 64.50   material X −18.25…+18.25
y = 64.00   material beyond ±20
```

A flat pad wider than X ±10 rocks on those two ridges. Relieve anything wider by ≥ 0.6 mm.

## Reproducing the measurements

```bash
UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv run python -m lib.analyze_step \
    "parts/vendor/solidrun-bedrock-v3000/Bedrock V3000 Basic 3D model.step" --save
```

`references/Bedrock V3000 Basic 3D model_analysis.json` — 22 solids, 1892 cylindrical
features. `references/views/` — rendered verification views of all three variants.

Set `BEDROCK_V3000_STEP` to an absolute path if you would rather not keep the 44 MB file
in your checkout.
