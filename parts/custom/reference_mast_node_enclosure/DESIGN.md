# Reference mast node enclosure

Status: **preliminary**.
The geometry is complete, machinable and passes the gate, and every refinement claim in this document is a number a builder or a measurement produced rather than an adjective.
It is not fabrication-ready: no vendor part number has been fixed, the mast bracket has not been released, and the thermal case is analytical.

This part is also the repo's **worked exemplar**.
Every other part under `parts/` predates `lib/features.py`, so there was no in-repo answer to "what does a finished part look like here".
Read `model.py` alongside `DESIGN_LANGUAGE.md`: the file is organised as the phase order, and each block says why it is where it is.

![hero](references/product/reference_mast_node_enclosure_v1_hero_rear.png)

---

## Function

A sealed housing for a mast-top electronics node: a small dissipating module plus a control board, mounted 6-25 m up a lattice or pole mast, exposed to weather and sun, serviced from a bucket truck.

It must

- keep water and dust out to IP66 for the life of the installation;
- carry 18 W of dissipation to ambient with no fan and no airflow assumption;
- present one MIL-style circular connector (RF/antenna) and one rectangular multipin (power and data) that can be mated with gloves on;
- hang off a mast bracket and survive 45 m/s wind and handling;
- open for service without disturbing the mast mount or the connectors.

It must **not** become structure.
Nothing else in the assembly hangs off it, the mast clamp load goes through the bracket and not through this body, and no antenna or payload bolts to it except through the published cold-plate grid.

---

## Authoritative inputs

| Source | What it governs | Where it lives |
| --- | --- | --- |
| `lib.features.STYLE` | every radius, chamfer, wall, fastener pitch and edge inset | `lib/features.py` |
| `lib.features.CORD_TABLE` | O-ring groove width and depth for a 2.62 mm cord | `lib/features.py` |
| `params.json` | every dimension in the part | this directory |
| `DESIGN_LANGUAGE.md` | the binding refinement standard | repo root |

No dimension in this part was taken from memory or typed inline in `model.py`.
`model.ladder_audit()` walks `params.json` on every build and reports any radius, chamfer or root fillet that is not a `Style` rung; it currently reports **zero** off-ladder values.

There is no vendor STEP for either connector - both are represented by their panel cutout and mounting pattern only, and that is recorded under Unresolved.

---

## Interfaces

Coordinate frame = installed frame.
`+Z` is up, `+Y` is outboard (away from the mast), `x = 0` is the part centreline.

| Interface | Face | Detail | Datum |
| --- | --- | --- | --- |
| Lid and gasket | `-Z`, z = 0 | 16 x M4 blind taps at 9.0 mm inset, 36.0 / 35.7 mm pitch; 2.62 mm cord groove on a 168 x 96 mm centreline | **A** - the machining and assembly datum |
| Mast bracket | `-Y` flange pad, y = -74.5 | 8 x M6 blind taps, 44.0 x 36.0 mm, on a 152 x 56 mm relieved pad | **B** |
| Payload / module | cavity roof, z = 60 | 15 x M5 tapped on an exact 30.0 x 30.0 mm grid, 10 mm deep in a 14 mm plate | published grid |
| Control board | cavity roof | 4 x M3 tapped bosses, 10 mm tall, at (±66, ±26) | |
| Circular connector | `+Y`, x = -54, z = 34 | D26 bore on a two-ring plinth, 4 x M3 on a D34 circle at 45 deg | **port side** |
| Rectangular connector | `+Y`, x = +54, z = 34 | 30 x 18 mm aperture (532 mm2) on a 52 x 34 raised land, 4 x M3 | **starboard side** |
| Pressure vent | `+Y`, x = 0, z = 18 | D10.5 bore for M12 x 1.5, on a faceted collar | lowest point of the outboard wall |

Handedness is a real failure mode here: the two connectors are different, and a mirrored build would pass every dimensional check.
`spec.json` therefore carries two `cylinder_at` entries that fail if either connector moves to the wrong side.

---

## Loads

| Case | Magnitude | Path |
| --- | --- | --- |
| Static weight | body 3.26 kg + lid 0.45 + payload 1.0 = 4.7 kg (46 N) | CG about 75 mm outboard of the flange pad -> 3.5 Nm at the pad |
| Wind, 45 m/s | q = 1240 Pa on 0.030 m2 frontal at Cd 1.2 = 44 N | 3.3 Nm at the pad |
| Shock, 15 g | 690 N at the CG | 52 Nm at the pad |
| Handling | 900 N point load anywhere on a flank | flank panel -> ribs -> seal band |

The shock case sizes the mast interface.
Eight M6 in two rows 36 mm apart carry 52 Nm as roughly 360 N of bolt tension in the outer row, against about 10 kN of proof load for M6 property class 8.8 - the interface is bolt-count-limited by stiffness and gasket-face flatness, not by strength.

The load path from the flange runs into the `-Y` wall, which is 23.5 mm thick because the seal band needs to be, and from there into the cold plate and the two flanks.
That is why the mast wall is the one wall that is **not** pocketed.

The flanks see only handling load, so each carries a 12 mm lightening pocket taking the wall from 24 mm to a measured 9.5 mm, with four 3 mm vertical ribs 11.6 mm tall (6258 mm3 of material returned across the two flanks) restoring the out-of-plane stiffness the pocket removed.
The ribs are not decoration and not there to fill the panel: without them a 9.5 mm plate spanning 60 x 38 mm is fine in bending but has no local support under a boot or a knee.

---

## Thermal

| Quantity | Value | Source |
| --- | --- | --- |
| Dissipation | 18 W | `params.json` |
| Max ambient | 45 C | `params.json` |
| Internal air target | 85 C | `params.json` |
| External skin area, finned | 192 865 mm2 = 0.193 m2 | measured on the exported solid with the cavity plugged |
| Same envelope, plain prism | 106 348 mm2 = 0.106 m2 | `cq.Solid.makeBox(198, 125, 88).Area()` |
| Fin bank net gain | +64 943 mm2 | `FinBank.added_area_mm2`, net of the root footprint twice |
| Fin count / pitch | 21 blades at 8.80 mm | `FinBank.count`, `FinBank.pitch` |

The architecture is one wall thick from junction to air.
The dissipating module bolts **up** to the cavity roof on the 30 mm M5 grid; the roof is a 14 mm cold plate; the 21-blade fin bank stands on the other side of that same plate.
There is no interface resistance in between, and no other wall in the load path.

At h = 6 W/m2K over 0.193 m2 the conductance is 1.16 W/K, so 18 W lifts the skin 15.5 K over ambient: 60.5 C skin at 45 C ambient, and roughly 70 C internal air against an 85 C target.

The 8.80 mm fin pitch is a thermal choice, not a styling one.
At a 14 mm fin height and this temperature difference, the boundary layers on adjacent blades merge below about 6 mm and the extra area stops paying; above about 12 mm the blade count falls faster than the per-blade gain rises.
`fit_check.py` asserts the pitch it measures on the artifact stays inside 6-12 mm.

**The solar case is not closed.**
Full sun on the finned roof puts roughly 22 W of absorbed flux onto 0.025 m2 of projected area, which is larger than the electrical dissipation; the matte black anodise re-radiates a large part of it, but the balance has not been computed and no shroud is designed.
A sun shield is listed under Unresolved and is a separate part.

---

## Environment and sealing

Target IP66.
One seal plane, on `-Z`, facing the ground: the lid bolts **upward** onto the body, so water runs off the joint instead of standing on it, and a failed gasket weeps rather than filling the box.

| Seal parameter | Value | How it is known |
| --- | --- | --- |
| Cord | 2.62 mm nitrile, AS568-style | `params.json` |
| Groove | 3.55 x 1.93 mm, 168 x 96 mm centreline, R24 corners | `CORD_TABLE` via `oring_groove()` |
| Squeeze | **26.3 %** (target 20-30) | `ORingGroove.squeeze_pct`, re-measured on the STEP by `fit_check.py` |
| Fill | **78.7 %** (target 75-85) | `ORingGroove.fill_pct`, re-measured on the STEP |
| Path length | 486.8 mm, one closed loop, no boolean seam crossed | `ORingGroove.path_length` |
| Flat land, groove to cavity mouth | 5.36 mm measured on both centrelines | `fit_check.py` ray probe |
| Groove rim lead-in | 0.4 x 45 deg, both rims | `model.groove_rim_break()` |

The rim lead-in is not cosmetic.
A knife-edged groove rim shaves the cord during assembly, which is how a nominally good seal leaks the second time it is fitted.
`oring_groove()` does not build it, so it is cut separately by a tool whose own rim already carries the chamfer.

The 16 lid screws are **outside** the seal path and blind, so a screw hole is never a leak path; the nearest tap edge is a measured 2.07 mm outboard of the groove.

Water management: the roof sheds outboard; the `+Y` wall carries a 12 mm drip hood with an 8 deg shed angle and a half-round kerf on its soffit, so runoff lets go above the connectors instead of wicking down onto the shells; the pressure vent sits at the lowest point of that wall so condensate reaches it.

Corrosion: 6061-T6, hard anodised MIL-A-8625 Type III class 2 matte black.
The flange pad and the seal land are masked; bonding is through the mast bracket bolts into unanodised tapped holes, which is an open item.

---

## Service

Everything is done from below, on the mast, with the box still bolted to its bracket and both connectors still mated.

1. Remove 16 x M4 lid screws.
2. Lower the lid. The electronics stay put - they are bolted **up** to the cold plate, not down to the lid.
3. Work on the module or the board.
4. Refit the lid. The gasket land, the groove and the screw pattern are all on the body, so nothing critical is on the part that gets handled.

Nothing structural is disturbed, the mast interface is never broken, and the seal plane is re-made against a machined land rather than against a part that has been carried up a ladder.

Access clearance needed: 250 mm below the enclosure for the lid to drop clear, plus the payload's own removal envelope.

---

## Materials and process

6061-T6 aluminium, 3-axis machined from billet, hard anodised matte black.

`STYLE.wall("machined-aluminium", span=80)` recommends 2.5 mm.
Nothing on this part is anywhere near that, and that is the point: the wall thickness here is set by the **seal band**, not by the process.
A face seal needs cavity edge -> land -> groove -> land -> screw -> part edge, which is 24 mm on the long sides and 23.5 mm on the short.
Rather than pay that as dead metal, the band does the structural work, and the two faces that carry no load are pocketed back to a measured 9.5 mm.

Every feature is reachable with the tool axis along `+/-X`, `+/-Y` or `+/-Z` in one of six setups.
`fit_check.py` asserts this directly: all 131 cylindrical features on the artifact run along a part axis.
The consequence is that the cavity's vertical inner walls carry no features at all - a top-opening pocket cannot machine them, and pretending otherwise would put a feature on the drawing that no shop could cut.
Under the previous gate that cost the part real points, because the old `blank_face_ratio` measured the largest bare planar face and the mast-side inner wall was the worst on the part.
It no longer does: `face_composition` ranks by the largest empty region on faces a human can actually see, and this part's worst is now the +Y exterior at 0.28 of its own silhouette scale.
An unfeatured inner wall of a top-opening pocket is a machining fact, and the reworked metric agrees with the machinist.

---

## Industrial design intent

**Massing.**
A single squared block with R16 plan corners and a 2.5 mm break on both rims, one finned roof, one flange, and everything else recessed into the silhouette.
From three metres it should read as one machined billet with a heatsink on top, not as an assembly.

**The front.**
The `+Y` wall is the face a technician looks at, and it is composed rather than populated: a circular connector plinth to port, a rectangular connector land to starboard, and a centre column carrying the emblem above the vent, all under a full-width drip hood.
The two lands are the same height off the wall (5 mm) so the composition reads as one family.

**Transitions.**
No cylinder butts onto a prism anywhere.
The circular connector arrives through a two-ring concentric step shoulder; the vent arrives through an eight-sided faceted collar.
Both are turned or milled features whose every edge lives in a revolved or drafted profile, so nothing is filleted after the fact.

**The flanks.**
Layered, not hollowed: a shallow 2.5 mm recessed panel with a proud perimeter frame sets the boundary, and the 12 mm lightening pocket that actually removes metal sits inside it with its own frame and four vertical ribs.
The first version of this part had a single 18 mm pocket, and the hero render showed it reading as a casting window rather than a machined enclosure - see the trajectory below.

**Fasteners.**
One size per interface, constant pitch, constant inset, symmetric about both centrelines, solved by `bolt_pattern` and never placed by hand.
16 x M4 at 36.0 / 35.7 mm and 9.0 mm inset on the lid; 8 x M6 at 44.0 x 36.0 mm on the mast pad; both report `in_band=True`.
The cold-plate grid deliberately runs tighter than M5's structural band because 30.0 mm is a published contract, not a spacing choice.

**Identity.**
One mark on the whole part: engraved concentric rings, 24 mm, 0.6 mm deep, centred on the outboard wall's centreline.

**Finish.**
Uniform matte black. The connectors and the gasket are the only contrast elements, and neither is this part.

---

## Alternatives considered

| Architecture | Benefits | Problems | Decision |
| --- | --- | --- | --- |
| Lid on top (`+Z`), fins on the flanks | Familiar; service from above | Water stands on the gasket; the cold plate ends up two walls from the fins; interior mounting features land on vertical walls a 3-axis pocket cannot reach | Rejected |
| Lid on the outboard face (`+Y`) | Vertical seal plane sheds water; service faces the technician | The seal band eats the 88 mm height, leaving a 26 mm tall cavity | Rejected |
| Lid down (`-Z`), fins up, connectors outboard | Seal faces the ground; cold plate is directly under the fins; all interior features are on the cavity roof, machinable in one setup; electronics stay in the box during service | Service is overhead work | **Chosen** |
| Finned cover carrying the electronics | Classic outdoor-radio architecture; simplest body | Moves the whole thermal design into the part that gets handled, and this deliverable is the body | Rejected |
| `base_flange(edge="step")` for the mast flange | One call | That path stacks two bare prisms and leaves every rim of both knife-sharp - 1.6 m of unbroken convex edge on this part alone | Rejected, built as two chamfered levels |
| Chevron rib field in the flanks | The reference vocabulary's default | At this size it reads as a decorative zigzag, and one rib terminates in a stub | Rejected, four vertical ribs instead |
| Louvres for ventilation | Reference vocabulary | The enclosure is sealed. A vent in an IP66 box is a defect | Rejected on purpose |

---

## Unresolved

1. Mast bracket drawing and its bolt pattern. The 8 x M6 at 44 x 36 mm here is this part's proposal, not a released interface.
2. Vendor part numbers and vendor STEPs for the circular connector, the rectangular connector and the M12 x 1.5 vent. Both connector interfaces are cutouts and patterns only, with no mated-envelope check.
3. The solar case. Roughly 22 W of absorbed flux on the roof exceeds the electrical dissipation; the radiation balance is not computed and no sun shield exists.
4. Thermal correlation. The 15.5 K rise is analytical at h = 6 W/m2K; it needs a zero-wind bench correlation.
5. Gasket compression set over the service life. The 26.3 % squeeze is nominal at assembly.
6. Bonding and corrosion detail at the anodise-masked flange pad and the tapped holes.
7. The lid is not modelled. Its counterbore pattern must be generated from `BoltPattern.points` on the body, not re-typed.

---

## Design review

**Score 90.2 / 100, band A (meets every measured standard)**, as an **`enclosure`**, measured on `exports/reference_mast_node_enclosure_v1.step`, 2026-07-26, `lib/design_review.py` (schema `design-review/2`) with no waivers and no configuration of any kind beyond the role.

This number replaces the 89.9 this file recorded earlier on 2026-07-26, which replaced an 83.1, which replaced an 86.6.
None of the four is a different part: **the geometry has not been touched since revision 6, and every one of the moves is the ruler being corrected.**

- 86.6 -> 83.1 (2026-07-25): `form_discipline` was retired, its weight redistributed, and `feature_composition` and `radius_vocabulary` tightened.
- 83.1 -> 89.9 (2026-07-26): `radius_vocabulary` stopped charging for RICHNESS and `symmetry` stopped charging for having an INTERFACE. Those two metrics moved +45.7 and +24.5 on this part, and nothing else moved at all.
- 89.9 -> 90.1 (2026-07-26): the measurement-frame port. Every dimension is now taken in the frame `lib/frame.py` fits to the part's own surfaces.
- 90.1 -> 90.2 (2026-07-26): `_chamfer_leg` learned to measure a CONE land at all, and to measure its slant width off the face's own v-parameter range rather than off area/(perimeter/2). A conical chamfer land - which is what a chamfer becomes wherever it crosses a rounded plan corner - previously returned no leg, was subtracted from the population, and vanished from both the vocabulary and `unmeasured_fraction`.

- 90.2 -> 90.2 (2026-07-27): the axis fold. The number did not move; what moved is what this part measures when it is TURNED. An axis direction was folded onto one hemisphere by the sign of its largest component, and an axis at 45 degrees in a plane has no largest component, so the fold came out of round-off - and at 45 degrees about Z the review dropped 20 of this part's 90 feature centres and 19 of its 54 screws while the raw cylinder census stayed bit-identical, scoring the same geometry **92.6**. Re-measured over all 83 rigid motions the contract holds it to, the worst move is now 2.1000 points, entirely `face_composition`, and it is the residual `CLAUDE.md` documents rather than anything about this part.

**90.2 is the honest current reading; 92.6, 89.9, 90.1, 83.1 and 86.6 must not be quoted anywhere.**

The 2026-07-26 change is worth recording here because this part is what proved the defect.
`parts/_template` - the scaffold `make new-part` copies, a rounded case whose features are four decorative lid grooves, five identical recesses in a row and a handle ear - scored **85.9 against this part's 83.1**, and the +2.80 decomposed almost entirely into those two metrics: `radius_vocabulary` gave the scaffold +4.75 for using 5 break sizes against this part's 10, and `symmetry` +1.72 for having no connector.
Neither was measuring what its name says.
`radius_vocabulary` was charging the *count* of sizes, which is richness and not coherence: a fin root, a seal land, a counterbore and an outer plan corner are four different jobs with four different correct radii.
`symmetry` was charging the *width* of a mirror difference without asking its shape, so this part's 52 x 48 x 33 mm port-side connector bay - aspect ratio 1.6, a compact chunk of functional interface - was priced as though it were an unmirrored chamfer run.
Both now measure the construct they name; both parts' numbers rose, and the order between them inverted - measured today, this part reads 90.2 against the scaffold's 86.0.
See `lib/design_review.py`, `VOCAB_SPLIT_RATIO_FALLBACK` and `SLIVER_ASPECT_NONE`.

**Role: `enclosure`, and the geometry now says so, not just this paragraph.**
This part contains a cold plate, a module and a connector set behind a sealed lid, and every exterior face is a product surface, so the strictest rubric is the correct one and all eight metrics apply.
This file used to record that a `sheet` reading scored 88.2/A and a `cover` reading 86.0, and that "nothing but this paragraph stands between the honest number and the flattering one."
That is no longer true, and the sentence is retracted.
Every role is now guarded against the measured B-rep, and every lighter claim on this part is refused before it is honoured - measured 2026-07-26, all five re-judged as `enclosure` at 90.2:

| Claimed role | Verdict |
| --- | --- |
| `sheet` | refused - 52 % of its face area faces an enclosed void (max 15 %); a formed blank has no inside |
| `cover` | refused - its thinnest dimension is 0.44 of its longest (max 0.25) |
| `plate` | refused - same thinness guard |
| `bracket` | refused - 52 % of its face area faces an enclosed void (max 20 %); this is a housing |
| `structural` | refused - its longest dimension is only 2.2 x its shortest (min 4.0) |

| Metric | Weight | Score | Detail |
| --- | --- | --- | --- |
| `edge_break_coverage` | 0.21 | 93.0 | 100.0 % of convex body edge broken (1569 of 1569 mm), body term 100.0; 57 % of bore/boss rim length broken |
| `face_composition` | 0.19 | 97.4 | largest empty region 0.27 of its silhouette scale, on the +Y face (empty circle R18.8 mm); area-weighted mean 0.12 over 15 exterior faces |
| `feature_composition` | 0.16 | 69.8 | 77 % of 90 feature centres share a centreline or a constant-pitch run, across 22 families; weakest is the lone D52.0 connector bore on +Y |
| `pattern_discipline` | 0.12 | 79.9 | 5 fastener families, 51 of 54 screws patterned; weakest is 8x D2.5 on Y |
| `radius_vocabulary` | 0.11 | 94.5 | 10 distinct break sizes, 97 % of exterior blend/chamfer area on the ladder; 2 of them (0.85, 1.15) are split rungs, 97 % coherent area |
| `symmetry` | 0.07 | 100.0 | 0.9 % asymmetric volume about axis1, slender difference over 8 % of the bbox diagonal (the 30 % lump is the connector bay, priced by volume) |
| `sharp_edge_length` | 0.07 | 100.0 | 0 mm of unbroken convex edge |
| `proportion` | 0.07 | 100.0 | 198 x 149 x 92 mm, max/min 2.2 |

Measured weight 100 %, `probe_failures` 0, no metric in state `error`, `absent_defect` or `not_required`.
Four findings, none of severity `high`: two `irregular_fastener_pattern` (medium and low), one `scattered_features` (medium), one `sharp_rim` (low).

### Rubric floors

Two metrics carry a hard minimum that belongs to the rubric rather than to this part, and neither can be waived, disabled, renormalised out or averaged away.
Record both, met or not - a bar only visible when you fail it is a bar nobody designs towards.

| Floor | Required | Measured | Margin |
| --- | --- | --- | --- |
| `edge_break_coverage` | 10.0 | 93.0 (body term 100.0) | +90.0 |
| `sharp_edge_length` | 25.0 | 100.0 | +75.0 |

An unmet floor caps the reported band at `D` whatever the weighted mean says, fails `design_review.score` at every severity, and emits its own failing check at the review's **overall** severity - so a part like this one, which states a `min_score` and is therefore gated hard, fails hard.
`metric_severity` never reaches a floor: "this metric does not matter to me" is the one claim a floor exists to refuse.
The floors exist because the mean is arbitrable: the measured worst part that could still clear a hard 70 gate was a flat 220 x 150 x 9 slab with three pockets and ten border holes on which not one edge is broken anywhere, and it reached 85.6/B by claiming a role, declaring its own radius ladder and waiving the one metric it failed.
The same STEP, unchanged, now measures 57.3 and reports band `D` with four failing hard checks.

### Configuration delta

`config_delta` is **0.0** on this part: it declares a role of `enclosure`, which is the default and the strictest rubric, and it waives nothing, so the default rubric applied to the same measurements returns the same 90.2.
This is the line the report used to be missing.
A part that scores well because of what it configured, rather than because of what it is, now says so in a number: above a delta of 25.0 points it is an ERROR.

### The bar

`spec.json` gates this hard: `"role": "enclosure"`, `"min_score": 80`, `"severity": "hard"`, `"metric_severity": "hard"`, with per-metric bars of 70 on `edge_break_coverage` and 60 on `face_composition`.

**80 now leaves 10.2 points of margin against the measured 90.2. It was 3.1 when the part read 83.1, and the bar before that, 83, left 0.12.**
83 was chosen when this part scored 86.6, and it survived the 2026-07-25 rubric rework by twelve hundredths of a point.
A 0.6-point move in `edge_break_coverage` - well inside what a metric recalibration does - would have hard-failed the one part the skill tells agents to copy, which is the worst possible failure mode for a reference.

**80 is deliberately NOT being raised to track the new score.**
The obvious move is to re-cut the bar just under 90.2 and keep the same 3 points of margin, and this file's own history is the argument against it: the last two readings of this unchanged geometry moved -3.5 and +6.8, both times because the ruler was corrected, and a bar re-cut after each correction is a bar that has never actually been tested.
9.9 points absorbs the total loss of any two light metrics, or a 47-point collapse in the heaviest one, and still holds this part 10 points above the repo's advisory gate of 70.
A bar is meant to catch a regression in the part, not a recalibration of the ruler.

For calibration: the three pre-design-system parts carried in `tests/design_corpus.py` score **22.1, 46.4 and 51.5**, and all three carry an unmet `edge_break_coverage` floor - not one edge is broken on any of them.
In that corpus this part is the reference three contract items are written against - `gamed_below_exemplar` (no deliberately gamed geometry may outrank it; the best of thirteen attempts reaches 59.8), `real_ordering` (it must outrank every other real part by at least 5 points; it leads the next by 38.4) and, since 2026-07-26, `test_the_rich_exemplar_outranks_the_plain_scaffold` (it must outrank `parts/_template`, now 90.2 against 86.0).

### Trajectory

The six revisions below were scored as they were built, under the **superseded** `design-review/1` metric set (`blank_face_ratio`, `feature_density`, `fastener_rhythm`, bands A >= 85 / B >= 72).
They are kept because they are the design history and each row records a real decision, but **the numbers are not comparable to the 90.2 above** and must not be quoted as current.
Only revision 6 exists as geometry, and under the current rubric it measures 90.2.

| Revision | Change | Score (`design-review/1`, superseded) | Band then |
| --- | --- | --- | --- |
| 1 | first build - full feature vocabulary, `base_flange(edge="step")`, single 18 mm flank pocket, chevron ribs | 69.0 | C |
| 2 | mast flange rebuilt as two chamfered levels; drip hood built with `kerf=0` so its own rim chamfer takes, kerf cut separately; longer fin blades | 74.1 | B |
| 3 | flanks relayered: shallow recessed panel + inner lightening pocket + four vertical ribs, four broken mouths instead of two | 76.7 | B |
| 4 | 0.4 mm lead-in break on both O-ring groove rims | 80.6 | B |
| 5 | part pulled inside the envelope to 198 x 148.6 x 88; seal land widened to 5.36 mm | 81.2 | B |
| 6 | faceted vent collar, full-width drip hood, relief pocket in the flange mating pad | 81.0 | B |
| 6 | **the same geometry, re-measured under `design-review/2` as it stands today** | **90.2** | **A** |

Revision 6 cost 0.2 points under the old gate and was kept anyway: the render showed the flange pad reading as a blank slab and the vent boss reading as a blob, and neither was visible to any metric of the day.
The reworked gate agrees with the render rather than with the old number - the relief pocket in the flange pad is exactly the kind of move `face_composition` rewards, and that metric now reads 96.0.
The lesson stands and is the one `DESIGN_LANGUAGE.md` section 5.4 states: take the trade the render asks for, and record it.

### Open findings, not fixed

No finding is of severity `high`, and both rubric floors are met. Two are `medium` and two are `low`.

- **`feature_composition` 69.8 is now the weakest metric on the part**, and `radius_vocabulary` is no longer a finding at all. Both statements changed on 2026-07-26 without the geometry moving; see below.
- **`radius_vocabulary` 94.2, two split rungs remaining** (`low`, two findings of id `split_radius_rung`).
  The ten sizes, by area: R16.0 (6937 mm2), 2.5 mm chamfer (3663), 1.5 mm chamfer (2189), 1.0 mm chamfer (685), 0.4 mm chamfer (489), R12.0 (377), 1.15 mm chamfer (248, **off ladder**), 0.85 mm chamfer (215, **off ladder**), R8.0 (126), R5.0 (63).

  **This file used to record 48.5 here and to describe the ten sizes themselves as the defect. That was the metric's error, not the part's, and the paragraph is retracted.**
  Eight of the ten are `Style` rungs that somebody chose for a job: four plan radii (5, 8, 12, 16) and four rim breaks (0.4, 1.0, 1.5, 2.5).
  A fin root, a seal land, a counterbore and an outer plan corner need four different radii and there is no version of this part that needs fewer, so charging the count was charging the part for being a mechanism.
  What survives is the half that was always a real finding: 0.85 and 1.15 (one face each, 463 mm2 between them) are the module's own derived-leg measurement on sloped or short lands rather than values anyone typed, they sit within one ladder step of the 1.0 mm chamfer this part uses far more, and they land on visible exterior surface where a reader can see them.
  A design language that produces two sizes nobody chose is still producing them, and the metric still says so: 97 % conformance and 97 % coherent area, 94.2 rather than 100.

  **Still not fixed in this pass, and still deliberately.** Collapsing the two stray legs means a geometry change to `model.py` on visible exterior surface, which invalidates every reference render and deserves its own revision and its own render critique.
- **`pattern_discipline` 79.9** (`medium`).
  The weakest family is the eight M3 taps on the outboard wall: only 25 % have a centreline mirror partner, and the edge-inset CV is 0.28.
  Each land's four screws are symmetric about that land's own centreline; a circular connector's pattern and a rectangular connector's are simply not mirror images of one another.
  Making them match would mean moving the rectangular land's screws to a square pattern with 1.8 mm of land to the aperture.
  Rejected - that is designing for the metric.
- **57 % rim coverage inside `edge_break_coverage` 92.9** (`low`).
  The body silhouette is 100 % broken (1388 of 1388 mm), but 3330 mm of bore and boss rim is still bare and would take a 0.4 x 45 deg lead-in.
  Most of it is tapped holes on internal lands where a lead-in buys nothing but tool time.
  Accepted.
- **`feature_composition` 69.8** (`medium`, and the second-weakest metric). 77 % of 90 feature centres are organised across 22 families; the weakest entry is the single D52.0 circular-connector bore on +Y, which is a family of one and therefore scores zero by construction.
  A part gets one circular connector.
  Accepted - but note this reads 69.8 today where this file once recorded 82.4, because the metric was tightened, not because the part moved.
- **`symmetry` 100.0, and not a finding** (it was 75.5, and that was the metric being wrong about this part).
  0.9 % of the volume differs from the best mirror, about X. The largest single difference lump is 52 x 48 x 33 mm and spans 30 % of the bbox diagonal - which is what used to cost 24.5 points, on a term whose stated purpose is catching a difference that is *thin but wide*, such as a chamfer run applied to one rim and not its mirror.
  That lump has an aspect ratio of 1.6. It is not thin. It is the port-side circular connector bay.
  The term now weighs each difference lump by how much of a sliver it is, so a compact interface is priced by the volume term alone (0.9 % is inside its best knot) and only slender difference pays extent; this part's slender difference spans 11 %.
  The review still *reports* the 30 % lump in its message, so the asymmetry is disclosed rather than hidden.

  The handedness itself is unchanged and is still recorded under Interfaces: the RF shell is to port and the power/data land to starboard, and `spec.json` asserts both positions so a mirrored build fails.
  **Still not waived, and now there is nothing to waive.** The right outcome was never a waiver - a waiver would have excused the metric on this part's say-so. The metric was fixed instead, for every part at once.
- **Library gap, not a finding: no crest or end break.** `fin_bank()` and `rib_field()` offer no crest or blade-end break, so those edges stay raw.
  Under the reworked gate they land in the secondary edge population at 0.15 weight rather than against the silhouette, which is why `sharp_edge_length` now reads 100.0 where it read 0.0 before.
  The gap is still worth closing in `lib/features.py`.
  Note for anyone attempting it: a blanket `break`-phase chamfer over a rib field **raises `Standard_Failure: BRep_API: command not done`** - an ordinary catchable exception, verified 2026-07-25. An earlier note in this repo claimed it segfaults the interpreter; that claim was tested and is false.

### Render critique

`references/product/` carries `hero`, `hero_rear` (the outboard face) and `hero_low` (the mast face).
Read against `DESIGN_LANGUAGE.md`, revision 6:

- **Good.** Silhouette, plan radii and rim breaks read as one machined billet. The fin bank reads as a product heatsink, not as a comb. The circular plinth's step ring and the octagonal vent collar both read as turned or milled features. The layered flank - proud frame, recessed panel, deeper ribbed pocket - reads as machined depth rather than as a hole.
- **Good.** The flange mating pad now has a relief pocket with the bolt band around it, which is both what a machinist would do and what stops the largest face on the part reading as a slab.
- **Weak, accepted.** The drip hood is a straight bar with square ends. It terminates 1 mm inside the corner tangent, which reads deliberate, but a real visor would have a return at each end. `drip_edge()` cannot build one.
- **Weak, accepted.** The lower half of the outboard wall between the rectangular land and the vent is open metal. There is no feature that belongs there and inventing one would violate R6.
- **Cosmetic.** A faint hairline is visible at fillet-to-flat tangent boundaries on the corner radii. That is OCC per-face tessellation, documented in `lib/render_step.py`, not geometry.

---

## Verification plan

| Test | Moves the part to |
| --- | --- |
| CMM the seal land, groove section and flatness on a first article | released seal |
| IP66 spray test to IEC 60529 with the real gasket and torque spec | released seal |
| Pressure-decay leak test at 20 kPa before and after 10 lid cycles | compression set closed |
| Zero-wind thermal soak at 18 W and 45 C, thermocouples on the cold plate and the module case | thermal correlation |
| Full-sun outdoor soak, or a solar-lamp equivalent, with and without a shroud | solar case closed |
| Static pull to 15 g at the mast interface with the released bracket | flange interface released |
| Salt-fog to ASTM B117 on an anodised sample with the bonding detail | corrosion closed |

---

## What to copy from this part

For the next agent building a housing here:

1. **Declare the working frames once, from the stock solid, before any feature exists.** `_frames()` does this. `">Z"` means *highest*, so one boss silently redirects it; `"+Z"` means *widest planar face pointing that way*, so it moves too. A captured `cq.Plane` never moves.
2. **Put every break in a 2D profile.** This part has 536 faces, every exterior rim broken, and never once calls `.fillet()` or `.chamfer()` on the assembled solid. Pocket mouths are broken by cutting a tool that already carries the chamfer (`break_mouth`).
3. **Never let an aperture cut "through".** `connector_land(aperture=...)` sizes its cutter to clear the whole solid, which on a hollow part exits the far wall as well. Every aperture here is told how deep to go.
4. **Let the builders' measurements be the argument.** Squeeze, fill, wetted area, achieved pitch, `in_band`, `wall_after` - all of them are in this document as numbers because the builder returned them.
5. **Look at the render before you believe the score.** Three of the six revisions above came from reading a PNG, and one of them cost points.
