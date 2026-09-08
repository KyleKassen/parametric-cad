# ADRS maritime layout — Saginaw SCE-20H2010LP interior (v2)

Compact, **fastened** interior arrangement. Every bracket is a 3 mm 6061 plate with a
real hole pattern, every joint has a real screw, and every connector, vent, drain and
service cover on every component is declared as a keep-out that the verifier enforces.

```bash
uv run python parts/custom/adrs-maritime-layout/make_placement.py     # regenerate the layout
uv run python parts/custom/adrs-maritime-layout/layout.py --drawings --export --render
```

| File | What it is |
|---|---|
| `interfaces.json` | Measured mounting holes + connector keep-outs for all 6 components, in each part's own frame. The source of truth. |
| `make_placement.py` | Layout decisions. Pulls holes out of `interfaces.json` — never retypes them. |
| `placement.json` | Generated. Do not hand-edit. |
| `layout.py` | Places, drills, fastens, verifies, exports. |
| `exports/plates/*.dxf` | 1:1 flat patterns, outline + holes. |
| `exports/subpanel_drilling.csv` | The 31 holes to put in the 431.8 mm subpanel. |

## Coordinate frame

Saginaw's own STEP frame, so imported geometry needs no re-datuming:
**X** = width ±252.09 · **Y** = height ±252.10, **+Y up** · **Z** = depth, **+Z toward the door**.
Subpanel mounting face **Z = −109.22**; door inner clear **Z = +131.10**; 240.3 mm of stack depth.
Four subpanel corner collars stand proud to Z = −100.69 at (±193.68, ±193.68) — keep-out.
All brackets sit on a 12 mm standoff plane (plates at Z = −97.22…−94.22), which clears them.

## What actually drove the layout

Not the boxes — the **cable volumes**. Three measured facts set everything:

1. **The TE12 needs 50 mm of plenum in front of its Ø120 intake grille**, which reaches
   X = −111.05. Nothing solid lives left of that in the band it sweeps. Its discharge is
   two bands at the top and bottom of the fin stack hugging the wall, so it runs a cold
   curtain up and down that wall and returns at mid-height.
2. **The UBR Plus needs 55 mm off its cellular SMA face and 60 mm off its port bank**; the
   B210 needs 55 mm off its USB-B. These volumes are far larger than the devices.
3. **The OZ51x has connectors on both ±Y faces, a service cover on +X and drains on −Z** —
   exactly one mountable face, −X, and it has no fixings at all.

## Placement

| Item | X | Y | Z | Mount |
|---|---|---|---|---|
| TE12 cooler | −343.4…−161.1 | −112.3…192.3 | −80.1…79.4 | left wall, 6× M6 on 142 × 286, cutout 125 × 232 |
| NSP-1600 | −180.0…158.6 | −195.0…−154.0 | −94.2…−9.2 | 3× M3 into `psu_shelf` |
| Bedrock V3000 | −105.0…−32.0 | −140.0…30.0 | −94.2…38.8 | 2× M3 into `bedrock_spine` + 1× M4 into `bedrock_shelf` |
| UBR Plus | −5.0…24.3 | −40.0…126.2 | −94.2…77.6 | 4× M4 through its cast flange into `ubr_bracket` |
| OZ51x dual-TX | 45.0…178.5 | −140.0…−47.8 | −94.2…−61.5 | clamped to `oz51x_cradle` by two hold-down clips |
| Ettus B210 | 60.0…182.3 | 0.0…177.6 | −94.2…−57.0 | 4× M3 into `b210_bracket` |

**366 × 395 mm of subpanel bounding footprint (78%)**, 193 mm of the 240 mm stack depth.

> Honest note on compactness: v1 of this layout claimed 52%. That number was wrong —
> it ignored connector clearance. Once the real cable volumes are respected the footprint
> grows to 78%. The boxes still occupy only about a third of the panel; the rest is the
> space their plugs and cables need. If you want it tighter, the lever is relaxing a
> specific clearance (say the UBR's 60 mm port bank), not rearranging the boxes.

## Fabrication — 16 plates, all 3 mm 6061, saw + drill + brake

| Plate | Flat size | Holes | Carries |
|---|---|---|---|
| `psu_shelf` + `psu_shelf_flange` | 306 × 95 / 306 × 17.9 | 3 × M3, 5 × M5 | NSP-1600. One folded part, bend at Z = −94.22 |
| `psu_gusset_l/r` | 92 × 17.9 | — | shelf bracing |
| `bedrock_spine` | 164 × 20 | 2 × M3, 2 × M5 | 20 mm wide to match the Bedrock's only flat land |
| `bedrock_shelf` + flange | 79 × 66 / 79 × 18 | 1 × M4, 2 × M5 | takes the 1.6 kg in shear. One folded part |
| `ubr_bracket` + flange | 178 × 152 / 152 × 34 | 4 × M4, 4 × M5 | full-contact thermal spreader. One folded part |
| `b210_bracket` | 181 × 126 | 4 × M3, 6 × M5 | pattern is symmetric in X, offset 3.05 mm in Z |
| `oz51x_cradle` | 137.5 × 96 | 6 × M5 | bears on the housing's only feature-free face |
| `oz51x_clip_top/bot` (foot + lip) | 137.5 × 17.8 etc. | 6 × M5 | hold-downs; bottom lip is split to clear the drains |

**45 fasteners total: 9 × M3, 5 × M4, 31 × M5.** Subpanel drilling: 31 × Ø5.5 — see
`exports/subpanel_drilling.csv`.

## Assembly notes

1. **Peel the four adhesive rubber feet off the B210** — they are concentric with its
   mounting bores and it cannot seat without removing them.
2. **Bedrock screw depth is 3.0 mm maximum** into the back wall (2.515 mm of thread). Longer
   screws bottom out and jack the chassis off the spine.
3. **B210 screw penetration 3.574 mm maximum** — the internal PCB screw tip is right behind.
4. **NSP-1600 max 4 mm** into the chassis bottom.
5. The OZ51x is **clamped, not bolted** — it has no fixings. Torque the clips to just nip it;
   it is a printed part. Keep both drain outlets (enclosure X = 101.25 and 125.5) clear.
6. Shroud the NSP-1600's **bare ±Vo busbar blades** — 38 mm of exposed DC at +X.

## Open items

1. **Which Bedrock chassis?** The vendor STEP superimposes three mutually exclusive
   enclosures at one origin — Tile (29 mm), 30W (45 mm), 60W (73 mm). This reserves the
   73 mm / 60 W worst case.
2. **B210 bores tapped or clearance?** Modelled as Ø2.90 unthreaded; the extraction reads
   them as tapped M3×0.5 from the PEM SOS-M3-10 standoff profile. Confirm before cutting.
3. **NSP-1600 hole positions are derived, not re-measured.** Verify the 3× M3 before drilling
   `psu_shelf` — it is the one plate whose pattern did not come from a fresh measurement.
4. **NSP-1600 variant (12/24/36/48 V)** — geometry identical across the series, efficiency
   and busbar current are not.
5. **Condensate pan** (TEC100WCMSS4, 159 × 64 × 19) not modelled; space is reserved.
6. **A better OZ51x mount exists.** We own that part. Adding two mounting ears to its −X face
   in `parts/custom/oz51x-dual-tx-housing-vertical` would replace the clamp with a proper
   bolted joint — a much better answer for shock and vibration. Say the word.

## Thermal budget

| Source | W |
|---|---|
| Bedrock V3000 (60 W finned variant) | 60 |
| NSP-1600 conversion losses | 40 |
| Peplink UBR Plus | 25 |
| Ettus B210 | 15 |
| Two Zonu OZ51x TX modules | 10 |
| **Total** | **≈150** |

The TE121024010 removes **94 W at ΔT = 0**, ~147 W at ΔT = +15 °C. The box settles near
**ambient + 15 °C** — on a 40 °C deck that is ~55 °C inside, the cooler's own maximum.
**The TE12 is undersized.** The TE162024020 (200 W) is already in `ADRS/CAD/Hoffman/` and
fits the same wall (400 × 180 against 504 × 256 available, same ~89 mm intrusion); it needs
the PSU shifted ~10 mm right and a 155 × 352 cutout, 6× Ø6 on 168 × 300.
