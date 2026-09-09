# OZ51x dual transmitter housing — snap service cover

## Intent, v2 — 8 September 2026

Create a separate, serviceable variant of the Opus 5 vertical housing. Preserve the
four slotted plate/standoff mounting points, module locations, SMA interfaces,
SC/APC adapter locations, internal wiring passage and 15 mm fiber spool radius.
Call the +Y face with two fibers and the central electrical connector **FRONT I/O**;
the inherited source calls this face rear. The RF and TTL SMA inputs remain opposite.

The intended modules are Optical Zonu A13-Z516-D31-AS-SL (RF transmitter with LNA)
and A13-Z510TTL-D31-AS-S (TTL transmitter). The repository has an OZ510 TX STEP,
used as the mechanical reference for both. Exact SKU geometry and the TTL header
pinout remain to be checked against the supplied hardware.

## v2 fiber access and M3 mounting revision

The v1 spool flange had only 0.5 mm between it and the module partition, making
fiber wrapping impractical. Move the complete spool 7.5 mm toward FRONT I/O.
The continuous drum contact radius stays 15 mm and the retaining flange radius
stays 16.5 mm. The actual exported flange now has **8.0 mm clear to the partition**;
the drum itself has 9.5 mm. A solid access probe and a 6 mm routing annulus on the
partition-facing half of the drum have zero intersection with the housing.

Extend the fiber bay from 58 to 62 mm to preserve wiring space: the DE-9 rear
reservation begins at canonical Y = 80.25 mm. It clears the full flange's planar
envelope by 3.0 mm and the actual spool B-rep by 4.5 mm. The checked fiber band
clears it by 3.3 mm. Each fitted SC connector reference clears the spool by
11.715 mm. This is routing access, not full fingertip clearance. The complete
fiber path and actual cable/boot bend limits still need a physical check.

The overall envelope including labels is now **32.72 × 138.10 × 116.20 mm**.
Only the front I/O end moves outward 4 mm; module and mounting datums stay fixed.
Keep all four **4.5 × 9 mm** mounting slots at canonical X = ±53.1,
Y = −22 / 74. The user intends M3 screws into plate standoffs, while preserving
the larger slot size for other hardware. Use washers; the checked representative
envelope is **9 OD × 3.2 ID × 0.8 mm**. At each slot centre, the washer fits with
zero interference and about 26.31 mm² total contact area, with 22.64% and 24.71%
of its annular area supported on opposite sides of the slot. Some outer overhang
is present at the flange chamfer. This geometric bearing check does not establish
load capacity or tightening torque. Verify the ordered washer and standoff faces.

![v2 interior and spool access](references/product/open_housing_interior_elevation.png)

Use the v2 base and cover together. The v1 STEP files and print package remain
available; the previous design record is archived as `references/DESIGN_v1.md`.

## Architecture and service

Two rigid locating hooks engage one long edge. Two long cantilevers integral to
the cover retain the opposite edge and release from outside. Flexure runs along
the cover plane. Separate locating pads carry shear. No heat-set inserts and no
cover screws. Module screws and connector mounting screws are still needed.
The cover removes without detaching the housing from the mounting plate.

The structural base retains the established module and flange geometry. Cover-only
columns are removed; the fiber spool remains. A framed recessed cover replaces
the eight visible screw holes. A D-shaped, manufacturer-derived DE-9 panel opening
replaces the assumed rectangular opening. Keep its long dimension vertical in
the installed housing: the narrow cross-section cannot accommodate horizontal
jackscrews with adequate edge material.

## Material and manufacturing

Preferred: unfilled MJF PA12 nylon, black dyed, supplier standard smoothing only
away from snap mating surfaces. This is selected for repeatable snaps and freedom
from FDM support/orientation constraints. Supply base and cover as separate parts.
FDM is a fit prototype option, not the qualified production process. Print the
cover outer face down so cantilever strain runs in the layer plane; recessed
show-face details may need support or be omitted for an FDM prototype.

Nominal fit clearance is 0.5 mm. Latch strain calculation is a first-order elastic
beam estimate, not fatigue qualification. Print the included latch coupon first,
then test a complete enclosure for seating, release, retention, and service cycles
at the actual maximum cabinet temperature. Do not use filled brittle materials
for these flexures without redesign and testing.

## Loads, thermal and environment

The mounting flanges and base carry the modules and external cable forces; the
cover only closes the cavity. There is no gasket or pressure load. A snap cover
is appropriate for an internal service cover, subject to physical retention tests.
For specified shock, vibration or frequent high-temperature service, a screwed
cover with two captive nuts is a sensible alternative; no such load spectrum was
provided. No shock/vibration, IP, fire, or thermal rating is claimed.

The housing is an internal cabinet part, not a weather boundary. Preserve drains,
avoid decorative vents aimed at fiber ends. Polymer does not provide an engineered
heat path to the plate. RF dissipation is approximately 2.2 W as a conservative
family-reference allowance; TTL dissipation and host ambient are unresolved.
Measure both module case temperatures at full operation in the intended cabinet.

## Interfaces and unresolved items

- Mount slots: original 4.5 × 9.0 mm, canonical X = ±53.1, Y = -22 / 74.
- Base/module interfaces: inherited family B-rep; real OZ510 TX reference used in fit checks.
- Fiber adapters: inherited SC/APC simplex adapter and mating corridors, reference model in repository.
- DE-9: shared DC power, enables, monitors and alarms; it is a custom harness, not RS-232.
- Exact TTL electrical pinout/current, ordered connector/jackscrew hardware, real module
  mechanical fit, fiber bend requirement, temperature and latch endurance require qualification.

## Validation and visual review — v2 candidate

![Candidate with reference connectors](references/product/with_reference_connectors_front_io.png)

On 8 September 2026 the named assembly and separate STEP exports were re-imported:
base 107,912.908 mm³ and cover 28,917.651 mm³, one valid solid each. Total material
volume is 136,830.558 mm³ against 147,913.679 mm³ in the original Opus 5 v2 STEP: **7.49%
less material**. Geometry checks pass; no print time or measured mass is claimed.

`fit_check.py` passes **66/66** checks on the exported solids. Seated overlap,
both reference module placements, DE-9 body/harness envelope, nut access, mounting
slots, fiber-wrap space, sampled 30° closing, 10 mm angled lowering and 1.3 mm
release travel all pass. The additional checks measure the partition gap, connector
separation, routing access, fixed mounting-slot contracts and M3 washer seating
and bilateral bearing. Each SC adapter has a 0.010 mm³ reference-model overlap,
below the declared 0.05 mm³ boolean tolerance. This is not proof of exact purchased
hardware fit. Latch coupon and DE-9 coupon exports are each valid single solids.

All seven delivered STL meshes pass boundary-edge and nonmanifold-edge checks.
OCCT export produced a few degenerate float32 seam triangles. Packaging normalizes
vertices on a 0.00001 mm grid (5,000 times finer than the 0.05 mm tessellation
tolerance), removes collapsed faces and recomputes normals. It does not patch holes
or alter STEP solids. Final files and checksums are listed in the package manifest.

The original fixed-hook roof obstructed rotation by 0.598 mm³. An additional
0.7 mm of roof relief at the two fixed hooks clears the sampled motion. The fixed
roof now leaves 1.52 mm to the seam and 1.7 mm of outer wall behind its pocket.
Flexible-hook pockets retain their original roof and 0.4 mm relaxed clearance.
The 26 × 1.6 × 3 mm beams screen at 0.462% nominal bending strain for 1.3 mm
release travel using 1.5*t*deflection/L². Root concentration, manufacturing defects,
creep and fatigue are not covered by this calculation. The modeled overtravel
stop is independently detected when translating the tip 1.8 mm inward.

### Repository appearance review: below target, not promoted

The final evaluation (`references/evaluation.json`, attempt
`20260908-131845-f77911`) scores **50.0/100, band D, role enclosure**, on
`exports/attempts/20260908-131845-f77911/oz51x-dual-tx-housing-vertical-snap_v2.step`, below the
unchanged hard bar of 70. Role is enclosure because this assembly houses electronics
and all exterior faces are product surfaces. `status=ok`, all eight metrics scored,
no metric errors, absent defects or not-required states, no role error and
**config_delta=0.0**, within cap. The face-composition metric leaves 1.85 mm²
unmeasured (fraction rounds to 0.0); measured weight is 100%.
Both floors pass: body edge-break term **64.0 against 10**, margin 54.0;
sharp-edge score **52.53 against 25**, margin 27.53. Composite edge coverage is
62.3, above the repository's separate 60-point expectation.

All build/export/re-import, validity, dimensional and mechanical-validator checks
pass. The overall evaluation exits **1 solely because the style score fails**.
Promotion was explicitly disabled and no threshold, weight or waiver was changed.
This remains a prototype candidate, not a production-accepted or grade-qualified part.
The retained spec block is `{"role":"enclosure","min_score":70,"severity":"hard"}`:
70 is the repository's enclosure acceptance bar, unchanged by this revision.

Remaining findings:

- **High: feature composition, 18.9.** Independent module, mounting, SC, connector,
  cable and drainage interfaces are not one regular feature family. Moving them
  to an arbitrary common grid would change the required interfaces. Retained.
- **High: symmetry, 0.0.** The measured best-plane wording saturates all planes
  at zero and selects a tie by order. Diagnostic work on the earlier candidate
  found significant sensitivity to a 0.084° frame tilt; exact modelling axes
  changed that metric alone from 0 to 84. That was a historical diagnostic, not
  a v2 measurement. The v2 report gives 80.4% Y, 79.6% Z and 28.1% X differences;
  all plane scores saturate at zero. The reported score is retained. The module/
  fiber-bay arrangement and snap-vs-fixed-hook asymmetry are intentional; duplicating
  them solely to obtain a mirror would add material and obstruct the required bays.
- **Medium: raw mount-ear underside/end and partition opening edges.** Main
  service rim crests were deburred by 0.4 mm in the final pass, preserving the
  catch roofs and spool. Remaining edges include mounting contact and inherited
  opening details; a blanket 1 mm bevel would consume useful wall/contact stock.
- **Medium: broad cover field.** It is a 1 mm genuine recess leaving 2 mm skin;
  deeper styling would thin this service cover. No ribs were added solely to
  improve the empty-region score.
- **Medium/low: module and SC fastener pattern irregularity.** These are hardware
  interfaces rather than freely placeable cover screws. Retained with measured
  fit. Sharp bore rims are retained where a chamfer would reduce pilot engagement.

`references/design_review_audit.md` applies to the earlier 47.2-point candidate,
`references/evaluation_v1.json` records snap v1 at 49.8, and `baseline_review.json`
applies to original Opus 5 v2. Do not substitute these numbers for the current
50.0 score. The original has an unmeasured feature population, so its
44.0 score is not a clean quantitative comparison of overall design quality.

### Visual self-critique

The final opaque product renders were opened and inspected. A first render
option exposed wire edges through solid faces; it was removed and the views
regenerated. The final front view reads as a closed housing with two aligned
green fiber adapters, a vertical DE-9 and a continuous cover frame. Connectors
are references; the DE-9 is simplified presentation geometry, not a fit proof.

| CAD workflow criterion | Verdict |
|---|---|
| 1. Exterior edge breaks | Main silhouette and service crests broken; retained interface edges noted above. |
| 2. Face purpose | Recessed cover, mounting face and connector end have distinct functions. |
| 3. Radius vocabulary | 96.8 metric; inherited interface radii retained. |
| 4. Symmetry | Interfaces align; fixed hooks and release tabs deliberately differ. |
| 5. Marking | One centred identity group, 0.4 mm relief, contained below the frame. |
| 6. Fastener arrangement | No cover screws; inherited hardware patterns are unchanged. |
| 7. Boss transitions | No new cover towers; inherited module support bosses retained. |
| 8. Connector lands | Three individual recessed flange seats on the same front plane. |
| 9. Flanges | Original radiused/gusseted slotted mounting ears retained. |
| 10. Interface grid | Original slot and module datums preserved, not regularized artificially. |
| 11. Texture/thermal | No ornamental fins or vents; actual case-temperature test remains necessary. |
| 12. Seal | Not a sealed enclosure; no gasket or environmental rating claimed. |
| 13. Service | Cover removes at 30° without removing mounting screws. |
| 14. Wall | Main walls 3 mm; cover field 2 mm; snap pocket walls/roofs disclosed above. |
| 15. Structure | Gusseted mounting ears, hollow spool and removed dead cover posts. |
| 16. Render | Opaque studio views inspected; minor mesh seam highlights remain a render limitation. |
| 17. Score record | 50.0/D and all retained high/medium findings disclosed. |
| 18. Role | Enclosure, without a lighter-role claim. |
| 19. Metric states | All measured/scored; no error or absent-defect states in final assembly review. |
| 20. Floors | Both pass. |
| 21. Configuration | Delta zero; no score waivers. |
| 22. Full evaluation | Mechanical/dimensional checks pass; appearance gate fails, so no promotion. |

### Sources and fabrication notes

The exact RF ordering code, RF header and supply-current references are recorded
in [CONNECTOR.md](CONNECTOR.md). The connector coupon deliberately separates
manufacturer body dimensions from our print-clearance allowance. Confirm the
actual TTL header before wiring; no contact-number harness assignment is approved.

Material families: [HP polymer material portfolio](https://www.hp.com/us-en/printers/3d-printers/materials.html).
PA12 is the initial rigid-housing choice; PA11 is an alternative if coupon tests
show that higher flexure ductility is needed, with retention stiffness rechecked.
FDM orientation guidance: [Formlabs snap-fit enclosure design](https://formlabs.com/blog/designing-3d-printed-snap-fit-enclosures/).

The test coupons qualify only their local features. They do not establish full
cover warpage, full housing retention or maximum-temperature service behaviour.
