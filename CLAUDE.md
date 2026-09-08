# CadQuery parametric CAD - project instructions

## What this repo is

Parametric mechanical CAD written in Python with CadQuery.
The `model.py` script is the source of truth; every STEP, STL and PNG is a derived artifact that can be deleted and rebuilt.
When a dimension changes you change the parameter and rebuild - you never edit the exported solid.

Everything runs from the repo root with `uv run`.
All units are millimetres, everywhere, with no exceptions.

## Non-negotiables

1. **The artifact is what is tested.** `lib/evaluate.py` builds, exports, re-imports the STEP and validates *that file*, never the in-memory `Workplane`. Trust the report, not the builder.
2. **Exterior geometry is built from `lib/features.py`.** A visible part assembled from raw `.box()` / `.extrude()` with a late `.fillet()` is a defect, not a starting point. The builders exist so the whole repo shares one radius, wall and fastener vocabulary.
3. **`DESIGN_LANGUAGE.md` is binding** for any surface a human will ever see. It is the distilled reference standard, not a mood board.
4. **Never hand-measure a vendor part, and never assume two vendor files are the same part.** Use `make analyze` and `make compare`; mirrored L/R variants have shipped here under near-identical names.
5. **Nothing is finished until you have looked at it.** Render the exported artifact and read the PNG back. An agent that never looks at its own work ships first drafts.
6. **Refinement is measured, not asserted.** `lib/design_review.py` scores the exported B-rep 0-100 against the rubric for the part's declared **role**.
   Record the score and the role, and do not describe the part as "professional" without one.
7. **A role is a claim about what the part is, not a way to be judged more kindly.** Picking a lighter rubric than the part deserves is dishonest and it is invisible in the number.
   Every role but `enclosure` has a geometric guard that must measure everything its role relaxes, so the obvious lies are refused - but a part near a guard's boundary still profits, and only you know.

## Anatomy of a part

```
parts/custom/<name>/            # parts/vendor/<name>/ for parts we buy
  model.py       create_part(params=None) -> cq.Workplane, plus build_stages()
  params.json    build inputs: dimensions, features, material, process, version
  spec.json      acceptance contract for lib/evaluate.py (dimensions, validators, fit, design{role,min_score})
  DESIGN.md      design intent - required for anything anyone will see
  fit_check.py   optional validator script
  datasheets/    vendor PDFs and drawings (the authority for every number)
  references/    analysis JSON, verification views, product renders, notes
  exports/       generated artifacts and eval attempts (git-ignored)
```

`lib/render_step.py` and `lib/analyze_step.py` write BESIDE the file they read, not into the part directory.
So rendering or analysing a PROMOTED artifact under `exports/` creates `exports/references/{product,views}/` rather than adding to the committed `references/` above; `.gitignore` covers it.
Pass `OUT=` / `-o` when you want the output somewhere specific.

`parts/custom/am59_mast_head/DESIGN.md` is the exemplar for the depth a DESIGN.md is expected to reach; it predates the design system, so it has no design-review section.
`parts/custom/reference_mast_node_enclosure/` is the worked exemplar for the whole loop - `model.py` written in phase order, a `spec.json` that gates hard on refinement (`"role": "enclosure"`, `"min_score": 80`, `"severity": "hard"`, `"metric_severity": "hard"`), and a `DESIGN.md` that records its score, its role, its rubric floors, its `config_delta` and the findings it did not fix.
Its `DESIGN.md` is the pattern to copy for recording a review: it records the score and prints the whole lineage of that number (86.6 under the nine-metric gate, 83.1 after `form_discipline` was retired, 89.9 once `radius_vocabulary` and `symmetry` stopped charging for richness and for having an interface, 90.1 after the reference-frame port, 90.2 once conical chamfer lands were measured at all), and says explicitly which of them must not be quoted.
Measured through `make eval` on 2026-07-26 it reads **90.2, band A** against its hard bar of 80, `config_delta` 0.0, both rubric floors met.
`parts/_template/` is the scaffold `make new-part` copies, and it is a working enclosure rather than a placeholder: a 150 x 90 x 34 mm body that measures 153 mm over its connector land, built entirely from `lib/features.py`, **86.0, band B** as the `enclosure` its `spec.json` declares.

## The libraries that decide quality

| Module | Job |
|---|---|
| `lib/features.py` | The design language as code: `rounded_box`, `recessed_panel`, `rib_field`, `bolt_pattern`, `connector_land`, `step_shoulder`, `oring_groove`, `fin_bank`, plus the `Style` ladders and the `Build` phase guard. Read it before writing geometry. |
| `lib/design_review.py` | Measures refinement on the exported STEP and scores it 0-100 with ranked findings, under one of six role rubrics. It measures organisation - alignment, pitch regularity, empty area, radius vocabulary - never the mere presence of a hole or a fillet. |
| `lib/render_step.py` | Verification views (orthographic, axis triad) and `--product` hero renders (PBR, studio lighting, SSAO). |
| `lib/evaluate.py` | The gate: build, export, re-import, validate, score, render, report, promote. |
| `lib/housing.py` | `silhouette()`, `keepout_prism()`, `clearance()`, `interference()` - derive cavities from the vendor solid instead of from numbers you typed. |
| `lib/analyze_step.py` | Exact STEP measurement and identity/mirror comparison. |
| `lib/fit.py` | Declarative assembly fit engine driven by the `spec.json` `"fit"` block. |
| `lib/debug_build.py` | Stage bisection over `build_stages()` when the kernel fails. |
| `lib/diff_step.py` | Geometric diff of two STEP artifacts. |
| `lib/frame.py` | The reference frame every dimensional quantity in the review is taken in: an orthonormal triad fitted to the part's OWN surfaces, so a rotated or translated copy of a file measures the same. `reference_frame(shape)` and the `basis` it reports (`faces`, `axis`, `obb`) are what makes the score a property of the part rather than of the file. |
| `tests/design_corpus.py` | The gate's own regression corpus: 31 labelled cases - 27 synthetic (a 5-rung refinement ladder whose top rung doubles as the `enclosure` reference, 13 deliberately gamed parts, more good parts covering the other 5 roles, and a turned good/crude/gamed set) plus 4 built from this repo's own artifacts - and 9 contracts over their **ranking**, not their absolute scores. `uv run python -m tests.design_corpus` prints the table and the contract result. Read it to see what the gate rewards. |
| `tests/test_invariance.py` | The executable contract that the same solid measures the same however it is held, over nine SYNTHETIC probe solids under 13 rotations, 5 translations, all 65 PAIRS of the two, and 3 re-partitions, with a meta-test per defect that restores the pre-fix basis and requires the contract to fail on it. Uniform scale is deliberately not contracted here. Its probe set is the scope of the tight bound below, and it does not contain a real part - see the invariance table for what the two real exemplars measure. |

## Where the design score can and cannot be trusted

The score is a coaching signal, not proof.
It was hardened over eight adversarial passes and these limits are the ones that survived, measured rather than assumed.
Every figure below was re-measured against the exported STEP, never against the builder - the corpus and the two exemplars on 2026-07-26, and the whole invariance section again on 2026-07-27 after the axis fold was fixed.

**How the part is held barely changes what it measures - but read the SCOPE of that claim before you repeat it.**
Every dimensional quantity is taken in the frame `lib/frame.py` fits to the part's own surfaces, never in the world axes of whatever file arrived.

**Scope, because a bound without one is the error this section keeps making - and the last edition of this table got the scope wrong and hid a live defect behind it.**
Re-measured 2026-07-27 over ELEVEN probe solids, held 83 ways each: thirteen rotations from 1 to 131 degrees about four axes, five translations out to (5000, -5000, 5000) mm, and ALL 65 PAIRS of the two.
The nine synthetic probes in `tests/test_invariance.py` are measured on the IN-MEMORY solid (plus three re-partitions), every run of the suite.
`parts/_template` and `parts/custom/reference_mast_node_enclosure` are measured on their PROMOTED STEP, re-exported and re-imported once per motion, so those two rows are through a real file.

The two paths are not nested and both have to be quoted.
Measured on the exemplar at 45 degrees about Z with the pre-fix code restored: in memory 90.2 -> 92.6, through a STEP write and re-import 90.2 -> 88.1 - and 88.1 is exactly what the FIXED code returns there, because the round trip perturbed the tie the fold was deciding on and the defect simply did not fire.
A defect decided by round-off can be masked by a round trip, so a bound taken only through the file is not a bound on the scorer.

| Quantity | Worst move | Where |
|---|---|---|
| overall score, the nine synthetic probes, in memory | **0.1000 points** | `turned_hub`, rot/z1 |
| overall score, `parts/_template`, through STEP | **0.0000** | exact over all 83 motions |
| overall score, the exemplar, through STEP | **2.1000 points** | `reference_mast_node_enclosure`, 90.2 -> 88.1, rot/z5 |
| overall score, the exemplar, in memory | 2.1000 points | same part, same flip, rot/z10 |
| every metric but `face_composition`, the nine synthetic probes | **0.0000** | exact, asserted as an equality |
| every metric but `face_composition` and `feature_composition`, the two real parts | **< 0.000001** | - |
| `face_composition`, the nine synthetic probes | 0.4050 | `tapered_arm`, rot/z45 |
| `face_composition`, `parts/_template` | 0.0444 | comb/oblique1+t_2000 |
| `face_composition`, the exemplar | 11.9770 | 97.3700 -> 85.3930 |
| `feature_composition`, the exemplar | 1.4399 | rot/z5, and only through the file - see below |
| TRANSLATION alone, every metric, all eleven, out to 5000 mm | **0.0000** | exact, including the exemplar |
| band, metric status, and either rubric floor | **no change anywhere** | A and B held, one status set per part, both floors met everywhere |

**The 2.1 points are one part and two metrics, a discrete flip rather than noise - and it is not fixed.**
On the exemplar `face_composition` takes exactly two values under rotation, 97.370 and 85.393, with nothing in between across the whole matrix.
`feature_composition` adds 1.4399 in the same direction as the rotation that flips it, and only through a real write and re-import: the same rotation applied in memory leaves it bit-identical, so that term is the file round trip nudging one feature centre across a clustering threshold, which is an exposure of the same kind and not a separate excuse.
The frame is bit-identical up to the applied rotation (same `size_mm`, axes exactly rotated), the face population and `examined_fraction` 0.6251 are identical in both states, and the whole difference is ONE face: the -Y flank at 5165 mm2, which reads nine inner wires as features and a largest empty circle of R11.05 at rest, and eight and R25.93 after a 5 degree Z rotation.
One inner wire out of nine changes classification in `_feature_wires`, and the empty-circle term more than doubles.

**That claim was previously written as "one part, one metric, 2.1 points" while it was none of those things, and the way it was wrong is worth more than the number.**
A SECOND defect was live at the same time - the axis fold, fixed 2026-07-27 - worth 2.4 points on the same part in memory at exactly 45 degrees about Z, and on two different metrics: `feature_composition` +7.09 and `pattern_discipline` +10.99, both UPWARD, so the reading it produced was the flattering one.
It survived because the scope above was too narrow in three separate ways: the probe set had no part drilled on more than one axis, the combined-motion case was a single hand-picked pair rather than the cross product, and the real-part rows were taken only through a STEP round trip, which happened to mask it.
`lib/analyze_step.py` folded an axis direction onto one hemisphere by the sign of its largest component, with the tie left to `max()` - and there is no largest component on an axis at 45 degrees in a plane, so the fold came out of round-off: the 4-decimal `dir` on a merged feature folded one way and the face's own full-precision axis the other.
Every comparison of a feature against its own faces then failed, `cylinder_wrap` summed no area, and 20 of 90 feature centres and 19 of 54 screws were deleted while the raw cylinder census stayed bit-identical.
The fold now falls back to a fixed order inside `analyze_step.DOMINANT_TIE`, and every direction comparison takes the magnitude of the dot product so no fold decides a measurement at all; either half alone is sufficient, which `test_the_contract_detects_a_round_off_decided_axis_fold` asserts by restoring each on its own and requiring 0.000000.

Do not quote 0.1000 as a bound over real parts, and do not describe the invariance as exact.

That holds for the turned hub too - `lib/frame.py` gives a body of revolution `basis == "axis"` rather than falling back to an oriented box, and it measures 0.1000 overall like everything else.
Before this, restoring the world-aligned basis moves a 15 degree rotation by **26.70 points**, restoring the world-bbox axial length moves a 77 degree rotation by **28.00**, an uncanonical face partition moves one coplanar split by **8.40**, the round-off decided axis fold moves a multi-axis drilled box by **16.90** at 45 degrees (and `feature_composition` by 77.31), and a degenerate tangent-convexity test moves a formed sheet bracket by **6.80** while flipping `edge_break_coverage`'s rubric floor between met and unmet.
Each of those is a meta-test that puts the defect back and requires the contract to fail on it.

**Prismatic parts - trust it.**
The refinement ladder is monotonic (15.3 -> 22.6 -> 53.9 -> 59.8 -> 80.3), the floors catch the real defect, and the findings name the exact edge run, its length, its location and the fix.
Across the corpus the worst good part scores 74.8 (`good_machined_bracket`) and the best gamed part 59.8 (`gamed_soap_bar`), so the two populations sit 15.0 points apart against a required margin of 5.0.
The cheapest score that is not good design is still a filleted and chamfered box with a constant-pitch hole grid, and it lands low band B - `ladder_5_bolted`, the top rung, is exactly that plus recessed panels and rib fields, and reaches 80.3.

**Bodies of revolution - measured now, but cheaply satisfied.**
`face_composition` develops cylinders, cones, tori and surfaces of revolution into true metric (u,v) space, so a barrel is read as the blank panel a render shows it to be, and `feature_composition` and `pattern_discipline` score the meridian profile rather than being excused.
Quote the corpus cases rather than a tube you built in a scratch file, because those are the ones anyone can re-run: `good_turned_gland` 88.6/A, `good_turned_spool` 87.6/B, `gamed_turned_blank_tube` 58.3/C and `crude_turned_billet` 39.8/D.
The plain tube that used to score 100/A with coverage 1.00 is the `gamed_turned_blank_tube` case and it now reads 58.3/C with `face_composition` 0.0 and `pattern_discipline` 0.0, so the blind spot this section used to warn about is closed.
What has NOT changed is how little a turned part has to do to bank most of the rubric.
On that blank tube `edge_break_coverage`, `sharp_edge_length`, `radius_vocabulary`, `symmetry` and `proportion` all read 100.0 - which is 0.53 of the enclosure rubric - for one `.chamfer()` over every circular edge.
Only `face_composition` (0.19), `pattern_discipline` (0.12) and `feature_composition` (0.16) are then left to say anything about the shape.
On a turned part read those three metrics and the render; do not read the composite.

**Read `examined_fraction` and not only the score.**
Every metric that works over a population reports the fraction of the relevant exterior it actually examined, and below its floor it degrades to an ERROR instead of returning a number.
`face_composition` refuses to compose ON curved chamfer and fillet skin - a chamfer band develops to a long thin strip that always scores a perfect void, so counting it would pay for styling - but that skin stays in its denominator, so on a heavily rounded body the metric judges a minority of the exterior and says how much.
Corpus range 0.375 (the soap bar, half of whose exterior is blend) to 1.00, exemplar 0.625, scaffold 0.717, floor 0.35.

**`symmetry` scores the best mirror plane, so a one-sided lump can be invisible.**
Measured: a 100 x 60 x 30 box with a 20 x 20 x 16 boss welded to one end is 15.9% asymmetric about X and exactly symmetric about the other two, and scores 100.0.
That is not a defect that can be scored away - re-measured 2026-07-26 the scaffold reads [X 2.7%, Y 0.0%, Z 32.7%] and the exemplar [axis1 0.9%, axis2 15.7%, axis3 36.9%], which is one connector end and one mounting face, and no rule over three numbers tells that apart from the welded boss.
Both still score 100.0.
So the metric names the worst plane and its own score beside the best one; read the message before taking a 100 for "this part is symmetric".
Note the axis labels: a part modelled on the world axes gets `X`/`Y`/`Z`, and one whose fitted frame is oblique to them gets `axis1`/`axis2`/`axis3` rather than a world axis name that would be a lie.

**Two old warnings are gone - stop repeating them.**
`radius_vocabulary` no longer charges for richness: six on-ladder sizes cost exactly what two do, only a SPLIT RUNG (two sizes closer than one ladder step) is charged, and the exemplar moved 48.5 -> 94.2.
`symmetry` no longer charges an enclosure for having a connector end: the extent term is sliver-weighted, and the exemplar moved 75.5 -> 100.0.
The scaffold no longer outranks the exemplar either - measured today the exemplar is **90.2/A** and the scaffold **86.0/B**, the exemplar ahead by 4.2.

A third is gone with the frame port: **"a score is only comparable between parts modelled on the same axes" is no longer true and should not be repeated.** See the invariance table above.

**A chamfer that crosses a rounded corner is a CONE, and until 2026-07-26 it was not measured at all.**
`_chamfer_leg` returned `None` for every conical land and the caller subtracted its area from the population, so the loss was invisible to `unmeasured_fraction` and to the degradation contract - it could only ever flatter, and it flattered turned and cone-broken parts specifically.
On `good_structural_arm`, whose builder chamfers 1.5 mm over a body with R12 plan corners, that hid eight of its sixteen 1.5 mm chamfer faces and reported "3 sizes, 100 % coherent, 100.0".
A cone's leg is now `slant width * cos(semi-angle)`, and the slant width is read off the face's own v-parameter range, which is exact.
It must NOT be read off the stored `rec["width"]`: that is `area / (perimeter / 2)`, which under-reads a curved band badly, and on this arm it turned those eight 1.5 mm lands into a manufactured off-ladder "1.35" size and took `radius_vocabulary` from 100.0 to 81.6 and the part from 89.7/A to 87.1/B.
Both numbers are measured; the 87.1 is the one that is wrong.
PartSmith still computes the cone leg the second way and still reports 87.1 for this part.

Also new: `radius_vocabulary` now reports `reclassified_faces` and `reclassified_mm2` - the narrow planar lands that failed the strip test and left the population. That subtraction is legitimate (they are not breaks) but it used to be silent, and a denominator that shrinks without saying so is how the cone hole stayed hidden.

A low score is nearly always a real finding.
The two cases to be suspicious of are a high composite on a turned part, and any metric reporting an `examined_fraction` well below 1.0.

## The gate

```bash
make eval PART="parts/custom/<name>"
```

Build -> export -> re-import -> validate -> design review -> render -> `report.json` -> promote.
Exit 0 = every hard check passed, 1 = a hard check failed, 2 = a hard check errored or could not be evaluated.
Only a fully passing attempt is promoted to `exports/<part>_<version>.step`; failures stay in `exports/attempts/<attempt-id>/` with their evidence.

Read `report.json` (schema `part-eval/2`), not the console.
The full design review lands under its `"design"` key (a `design-review/2` document plus the `"gate"` it was held to) with every metric, value and finding.
The design bar is 70/100, advisory and soft by default; writing `"design": {"min_score": N}` in `spec.json` is what opts a part in, and that alone makes the check hard unless you also write `"severity"`.

Bands: **A >= 88, B >= 70, C >= 55, D >= 38, F below 38.**
The eight metrics are `edge_break_coverage` (0.21), `face_composition` (0.19), `feature_composition` (0.16), `pattern_discipline` (0.12), `radius_vocabulary` (0.11), `symmetry` (0.07), `sharp_edge_length` (0.07) and `proportion` (0.07), weights shown for the default `enclosure` role.
A ninth, `form_discipline`, was retired on 2026-07-25; anything still naming it is stale.

Each metric reports one of four states, and only one of them is free:

| State | Meaning | Effect |
|---|---|---|
| `scored` | a real number | enters the weighted mean |
| `not_required` | the role excludes it, or `spec.json` waived it with a written reason | renormalised out, no check emitted |
| `absent_defect` | the geometry says it should apply and it does not | 0.0 at full weight, always a FAIL |
| `error` | it could not be measured | scores 0 at full weight - it stays in the denominator - AND is reported as ERROR |

A kernel failure never reads as a passing score, and a metric that could not be measured never becomes a number.
If the report says `insufficient`, the score is not a verdict, and the report says so structurally rather than in prose: `band` and `band_label` are both `null`.
A score is still printed, because it is the honest arithmetic of what was measured, and the message calls it indicative.
**Check `band is None` before you quote a score** - the band is the verdict, and on an insufficient report there is not one.

Every metric that works over a population also carries `examined`, `relevant` and `examined_fraction`: how much of the exterior it claims to measure it actually looked at.
Below the metric's floor in `EXAMINED_MIN` - `face_composition` 0.35, `edge_break_coverage` and `sharp_edge_length` 0.40 - it leaves as an `error` rather than returning a number, because a metric may not score a part it did not look at.
`symmetry` and `proportion` have no population of their own and carry none.

Two metrics also carry a **rubric floor** - a hard minimum checked *outside* the weighted mean, so it cannot be renormalised out, averaged away, waived, disabled, lowered or shifted by a role choice:

| Floored metric | Floor | Held against | What removes it |
|---|---|---|---|
| `edge_break_coverage` | 10 | `body_score`, **not** the composite metric score | only a role exclusion. A waiver or `enabled: false` is a config ERROR; a per-metric `min_score` below the floor is a config ERROR; `absent_defect` and `error` both FAIL the floor rather than escaping it |
| `sharp_edge_length` | 25 | its score | the same, and the `sheet` role is the only rubric that excludes it |

`edge_break_coverage` is `0.85 * body + 0.15 * rim`, so the rim term alone is worth 15.0 and flooring the composite at 10 let a part with no broken body corner clear it by deburring its bore mouths.
Its floor therefore reads the **body term**; if the floored quantity is missing from the metric's report the floor is not cleared.
A spec may raise a floor and cannot express lowering one.
An unmet floor caps the reported band at `D` at every severity, fails `design_review.score`, and fails `design_review.floor.<id>` at the review's **overall** severity - so whenever the design gate is hard the floor is hard, and `metric_severity` never reaches it.

`report["config_delta"]` prices the configuration itself: the same measurements re-scored under the default rubric with nothing excused, and the difference.
It is 0.0 for a part that declares `enclosure` and waives nothing; past `MAX_CONFIG_DELTA` it is itself a config ERROR.
Quote it whenever you quote a score under a non-default role.

The **role** in `spec.json`'s `"design"` block picks the rubric: `enclosure` (default and strictest), `cover`, `plate`, `bracket`, `sheet`, `structural`.
It decides which metrics apply, their weights and their thresholds; every role's weights sum to 1.00, so a role can excuse a metric but never lighten the bar.
Every role except `enclosure` carries a geometric guard, checked before the rubric is honoured: a claim the B-rep contradicts puts a `role_error` in the report and re-judges the part as an `enclosure`.
**A guard must measure everything its role relaxes.**
That is the rule, and it is now enforced structurally rather than by review: `lib.design_review.rubric_relaxations()` derives each role's relaxations **from the rubric** - dropped metrics, loosened void knots, loosened proportion knots, an excluded edge population - and `tests/test_role_guards.py` fails until every one has a probe showing the guard refuses a part that helps itself to it. A new role, or a new exclusion on an old one, cannot be added without one.
What each guard now requires:

| Role | Guard | Requires, on the measured B-rep |
|---|---|---|
| `cover`, `plate` | `_guard_thin` | `min/max <= 0.25` **and** `min/mid <= 0.25` - thin against both dimensions it spans |
| `bracket` | `_guard_solid` | interior face area `<= 20%` - solid material, not a shell |
| `structural` | `_guard_long` | `max/min >= 4.0` **and** `max/mid >= 2.0` - long against its whole cross-section |
| `sheet` | `_guard_sheet` | all four: derived stock `<= 10%` of the longest dimension, **and** `<= 6.0 mm` absolute, **and** interior face area `<= 15%`, **and** at least one real **bend** |

Every one of those second conditions closed the same defect: a single ratio taken against the single most flattering dimension.
`_guard_long`'s `max/min` alone is satisfied by any slab the moment it is thin (a 200 x 150 x 42 slab measured 4.76 against a bar of 4.0, +6.9 points as "a long member"), and `_guard_thin`'s `min/max` alone is satisfied by any long bar (a 300 x 40 x 30 bar 80.0/B to 90.5/A as a `cover`, and the repo's own 153 x 90 x 34 scaffold 86.0/B to 91.1/A).
`bracket` no longer drops `proportion` at all: "solid material, not a shell" bounds no bbox ratio, and a 160 x 100 x 6 lid claiming `bracket` was worth +14.7 for exactly that reason.

`_guard_sheet` is the strictest because `sheet` is the only rubric that drops a floored metric, so it is the only guard whose failure can remove a floor.
Its absolute 6 mm test exists because the relative one has no opinion about a big part - a 200 x 120 x 12 milled slab derives 10.18 mm, calls it 5% and passes - and because 12 mm plate carries a chamfer on its own outline perfectly well, which is the exclusion's whole excuse.
Its bend test reads `Topology.bend_pairs()`, and a bend is a coaxial **pair** of partial cylinders separated by the derived stock thickness **which span the same extent along that axis, overlap over it, and run out tangentially into a planar face far wider than the stock**.
The last three matter as much as the first: "coaxial and one stock apart" is arithmetic, and the derived stock is an average, so any constant-wall tray can be walked onto the coincidence by choosing its wall - measured, a plain 200 x 120 x 5 milled tray with a 1 mm pocket inset 4 mm reported four bends, 46.2/D honest with the `edge_break_coverage` floor UNMET against 75.3/B as `sheet` with every floor met.
A milled plan radius is a lone cylinder with no partner, so `Topology.formed_radii()` is **not** evidence of forming, and it is no longer what the guard reads.
Measured over the 31-case corpus plus both exemplars and 60 adversarial probes: `sheet` is claimable by 1 solid, `structural` by 1, and `cover`/`plate` by no bar, no member and no scaffold.
`tests/test_role_guards.py` holds the reproductions and the structural rule that a role dropping a floored metric must declare both a guard and a claim.
**Two config keys are retired and now error the spec, hard:** `design.weights` and `design.style.radius_ladder`.
A part needing different radii edits `lib.features.Style`, which is one reviewed change that moves every part in the repo together.
Waivers and disabled metrics each need a written reason and together may excuse at most 0.25 of the rubric.
`DESIGN_LANGUAGE.md` sections 2.1 and 2.4 have the full matrix, the guards and the honesty rule; 2.5 and 2.6 have the floors and `config_delta`.
**2.1's guard column is stale for `sheet` and `structural`** - it predates the tightening above, and so does its remark that the section 5 part "slips past the `structural` guard by a hair", which no longer holds (169 x 102 x 42 measures 1.66 on max/mid against a bar of 2.0 and is refused).
Until that section is rewritten, the table above is the authority on what a guard requires.

## Commands

```bash
make new-part NAME=x                       # scaffold parts/custom/x from parts/_template (params.json,
                                           # spec.json and a WORKING example model.py - replace all three)
make eval PART="parts/custom/x"            # the gate            [PRODUCT=1] [MIN=70]
make spec-init PART="parts/custom/x"       # draft spec.json from measured geometry
make debug-build PART="parts/custom/x"     # stage bisection when the kernel fails
make design-review FILE="....step" SPEC="parts/custom/x/spec.json"
                                           # score refinement exactly as the gate will
make design-review FILE="....step" ROLE=plate MIN=70 JSON=out.json    # or spell it out
make product-render FILE="....step"        # studio hero render     [VIEWS=] [SIZE=] [MATERIAL=] [OUT=]
make views FILE="....step"                 # 6-view + iso renders   [VIEWS=] [SIZE=] [SECTION=Z:11] [OUT=]
make analyze FILE="....step"               # exact measurement -> JSON
make compare A="a.step" B="b.step"         # identity / mirror check
make diff A="old.step" B="new.step"        # what changed between versions
make test                                  # pytest
```

## Kernel safety

These four rules cause most of the build failures in this repo:

- Bake plan radii into the base profile before any boolean; a late `.fillet()` on a complex union is the main failure mode.
  Measured on the `DESIGN_LANGUAGE.md` section 5 example while it stood at 490 faces: `s.edges("|Z").fillet(1.0)` raises `Standard_Failure: BRep_API: command not done` after 1.6 s, while `s.faces(">Z").chamfer(0.5)` on one named face succeeds.
- Chamfer lone simple solids before unioning them onto the parent.
- Counterbores only on flat lands - never on a curved, ribbed or recessed surface.
- Keep `build_stages()` current so a failure bisects to one operation. `lib.features.Build` gives you that generator for free via `Build.stages()`.

## House style

- Never use the em dash character; use a plain `-`.
- In long Markdown files put each full sentence on its own physical line.
- Module docstrings explain the *why*; see `lib/housing.py` for the tone.
- `from __future__ import annotations`, type hints, mm units stated.
- `uv run ruff check --fix <files>` on Python you write, naming the files you edited.
  Do not run `ruff format` across files you were not asked to touch, and note that `make lint` does exactly that to the whole repo - it is there for a deliberate repo-wide sweep, not for a normal edit.

## Designing, modelling or refining a part

Use the **`cad-part-design`** skill.
It carries the full workflow, the design-review rubric and a worked end-to-end command sequence.
Do not improvise a shortcut around it: the shortcut is how the repo filled up with knife-edged boxes.
