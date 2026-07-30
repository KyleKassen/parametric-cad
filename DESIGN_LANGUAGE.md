# Industrial design language

This is the executable design standard for every custom part in this repo.
It exists because the failure mode here is not bad engineering, it is unfinished engineering: knife-edged extrusions, blank slab faces, scattered fasteners, abrupt prism-to-cylinder butt joints.
Those parts function and read as first drafts, and they score it.
Measured on 2026-07-27 by `uv run python -m tests.design_corpus`, which reviews four real artifacts from this repo on every run: the three that predate the design system score **22.1, 45.7 and 51.5**, while `parts/custom/reference_mast_node_enclosure/`, the one part built to this standard, scores **90.2**.

The standard is distilled from the reference set the owner supplied on 2026-07-24: six product photographs of TRIYOSYS-class pan-tilt positioners and ruggedised enclosures.
Those are the quality bar, not designs to copy.

Everything below is a number or a checkable assertion.
If you find yourself choosing a radius, a chamfer, a wall, a screw pitch or a panel depth by judgement, you have left the standard: the number is in section 3, and the builder that applies it is in section 4.

---

## 1. Intent, and the rule that outranks all the others

**Engineering function is never traded for appearance.**
Seal planes, thermal paths, clearances, structural section, tolerance stack and manufacturability outrank every rule in this document.
A recess that thins a wall below its structural minimum is not a style choice, it is a defect, and `lib/features.py` will refuse to cut it.

The vocabulary in section 4 was selected so that this conflict almost never arises.
Nearly every element earns its place mechanically:

| Element | What it looks like | What it actually does |
| --- | --- | --- |
| Plan-corner radius | Softer silhouette | Removes the stress riser, cuts faster with a larger cutter, protects the anodising |
| Rim chamfer | Machined finish | Removes the burr, stops edge chipping, gives a lead-in for assembly |
| Recessed panel with a proud frame | Deliberate surface | The frame is a stiffening perimeter beam and a protected land for screws and labels |
| Rib field | Composition inside the recess | Restores the panel stiffness the recess removed |
| Constant-pitch fins | Product texture | Wetted area: the worked example gains 4904 mm2 measured |
| Louver with a shed angle | Detail at the vent | Ventilation area that sheds water instead of admitting it |
| Screw column, boss | Interior detail | Full-height columns react the lid screw torque into the roof |
| Step ring at a diameter change | Turned look | Removes the stress concentration at a butt joint and gives a machining datum |

Where an element genuinely earns nothing, it is not applied.
The one exception is the identity mark in R11, which is limited to one per face at 1 mm maximum relief precisely because it is the only purely visual element in the language.

---

## 2. How the standard is enforced

Three modules make this document mechanical rather than aspirational.

**`lib/features.py`** carries the numbers.
Every ladder in section 3 lives in the frozen `Style` object (`features.STYLE`), and every rule in section 4 has a builder.
Do not retype the numbers into a part: call `STYLE.plan_radius(...)`, `STYLE.wall(...)`, `STYLE.fastener(...)`, so a change to the style propagates.

**`lib/design_review.py`** measures the result on the re-imported STEP and scores it 0-100.
It measures ORGANISATION, not the presence of geometric events.
That distinction is the whole point of the module: an earlier version counted holes, fillets and faces, and a lumpy pile of overlapping rounded boxes with scattered oversized countersinks therefore scored 96.7 while a textbook sealed cover scored 50.2.
Every metric below asks whether the geometry is regular, aligned and coherent, so scatter is punished and a bolt pattern, a rib field, a louver bank and a framed recessed panel are rewarded.

The eight metrics, with the weights the default `enclosure` role gives them:

| Metric | Weight | What it measures |
| --- | --- | --- |
| `edge_break_coverage` | 0.21 | Fraction of convex EXTERIOR edge length a fillet or chamfer has broken, split into a body term (the silhouette a human reads) and a secondary term - bore and boss rims plus detail edges - worth 0.15 of it. Concave blend runouts earn nothing, and a countersink is credited once |
| `face_composition` | 0.19 | The largest EMPTY region on the exterior planar faces: the inscribed circle of the face once every inner wire with real relief is removed, normalised by the silhouette that face looks at. Three scattered holes leave a large empty circle and buy almost nothing |
| `feature_composition` | 0.16 | Organisation of the feature CENTRES. Features are keyed into families by axis direction and diameter rung, then scored on the fraction of centres sharing a line or sitting in a constant-pitch run, times the line economy - how many features each shared line has to show for itself. Adding an unrelated hole LOWERS it, and so does explaining the same holes with more lines |
| `pattern_discipline` | 0.12 | Pitch regularity, centreline mirror fraction and edge-inset consistency of the fastener families, with the bore, counterbore and countersink of one screw merged into one feature |
| `radius_vocabulary` | 0.11 | Do the fillet radii and chamfer legs sit on the `Style` ladder, or is every corner a different size |
| `symmetry` | 0.07 | Symmetric difference against the mirror about each principal plane, scored on the difference VOLUME and on its spatial EXTENT, so a thin wide asymmetry cannot hide |
| `sharp_edge_length` | 0.07 | Absolute mm of unbroken convex edge per bbox diagonal |
| `proportion` | 0.07 | Bbox aspect against slab-like and stick-like extremes |

There were nine.
`form_discipline` - a surface budget over planar area, normal-direction count and plane-position repetition - was removed on 2026-07-25.
It carried weight 0.14 and scored the naive extrusion in section 5.1 **94.0** against the refined part's 85.7, so a seventh of every score was a term that ranked the worst case in this document above the best.
Where sections 4 and 5 used to cite it, they now cite what actually catches the defect.

Bands: **A >= 88, B >= 70, C >= 55, D >= 38, F below 38.**
Report schema `design-review/2`.

**`lib/evaluate.py`** is the gate that runs the review as part of build, export, re-import, validate, render, report, promote.

Run the review directly at any time:

```
make design-review FILE="parts/custom/<part>/exports/<part>_v1.step" ROLE=enclosure MIN=70
uv run python -m lib.design_review parts/custom/<part>/exports/<part>_v1.step --role enclosure --top 8
```

`--role` defaults to `enclosure`, and `--min-score N` makes the module exit 1 below the bar, 0 at or above it and 2 when the review could not run at all.
`make design-review` passes `ROLE`, `MIN`, `JSON` and `SPEC` through; `SPEC="parts/custom/<part>/spec.json"` feeds the part's own `"design"` block in, which is the only way to see on the command line exactly the number the gate will use.

### 2.1 The role system

Three part types were being failed by an enclosure's rubric for doing their job: a cover, a plate and a sheet-metal bracket are all SUPPOSED to be thin, and two of them are supposed to have one big flat mounting face.
A part therefore declares a **role** in its `spec.json` `"design"` block, and the role selects which metrics apply, how they are weighted, and where the role-sensitive thresholds sit.

A role is a **claim about what the part is**, and the only thing a claim may buy is relief from a metric the part's function genuinely contradicts.

**A guard must measure everything its role relaxes.**
That is the rule, and it took four audits to state because each of the first three found one instance and fixed it without naming the species.
A rubric can be lighter than the default in exactly four ways - it can drop a metric, loosen the empty-region knots, loosen the proportion knots, or delete an edge population - and every one of them has to be paid for by a quantity the guard actually reads.
`lib.design_review.rubric_relaxations()` derives that list **from the rubric itself**, and `tests/test_role_guards.py` fails until every entry has a probe proving the guard refuses a part that helps itself to it, so a new role or a new exclusion cannot be added without one.

| Role | The claim it makes | What that buys | Not required | The guard that has to agree |
| --- | --- | --- | --- | --- |
| `enclosure` | A housing. Every exterior face is a product surface | nothing - the strictest empty-region thresholds in the system, and all eight metrics apply | nothing | none, because it claims nothing. It is the default and the fallback |
| `cover` | A lid. Thin by function, and its sealing face is flat by function | Empty-region thresholds roughly doubled (0.55/0.95 worst, 0.30/0.65 mean); `pattern_discipline` raised to 0.19 because a lid IS its screw ring | `proportion` | thinnest dimension <= **0.25** of the longest **AND <= 0.25 of the second longest**, because `proportion` is a max/min ratio and a long bar is slender without being thin |
| `plate` | An interface. Thin by function, and it IS its hole pattern | Empty-region thresholds 0.30/0.70 and 0.22/0.55; `pattern_discipline` 0.23 and `feature_composition` 0.19; `face_composition` cut to 0.11 because a mounting underside is legitimately bare | `proportion` | the same two ratios as `cover` |
| `bracket` | Solid material, not a shell, so every free edge genuinely can be broken | Empty-region thresholds 0.40/0.80 and 0.25/0.58; `edge_break_coverage` 0.20 and `radius_vocabulary` 0.13 | nothing | at most **20%** of face area faces an enclosed void |
| `sheet` | Formed from flat stock, enclosing no void. The blanked perimeter cannot carry a break | The blanked perimeter leaves the edge population entirely; `edge_break_coverage` falls to 0.13 and `feature_composition`, `pattern_discipline` and `face_composition` carry the weight instead | `proportion`, `sharp_edge_length` | derived stock thickness <= **10%** of the longest dimension, **<= 6 mm in absolute millimetres**, at most **15%** of face area facing an enclosed void, **AND at least one real bend** - see below |
| `structural` | A sculpted member, legitimately long | `proportion` knots move from 3.0/16.0 to 5.0/25.0, so a 5:1 arm is still perfect | nothing | longest dimension >= **4.0 x** the shortest **AND >= 2.0 x the second longest**, because any slab is long against its thinnest side |

`bracket` used to drop `proportion` as well, on the strength of a claim about its interior - which bounds no bounding-box ratio at all.
Measured 2026-07-27, a 160 x 100 x 6 lid scored 0 on `proportion` as an enclosure and simply was not asked as a `bracket`, worth +14.7 and band A.
Every other role that drops `proportion` has a guard that pins the same ratio (`_guard_thin` forces max/min >= 4, `_guard_sheet` >= 10), so on those the exclusion is the geometry's own doing.
`bracket` now scores `proportion` like everything else.

**What counts as a bend**, since it is the whole payment for the `sheet` exclusions.
A bend is a coaxial PAIR of partial cylindrical faces one material thickness apart - inner `ri`, outer `ri + t` - which additionally **span the same extent along their shared axis**, **overlap over it**, and **run out tangentially into a planar face far wider than the stock**.
The last two are not decoration.
"Coaxial and one stock apart" is arithmetic, and the derived stock is an average, so any constant-wall tray can be walked onto the coincidence by choosing its wall: measured, an ordinary 200 x 120 x 5 milled tray with a 1 mm pocket inset 4 mm reported four bends and took the `sheet` claim from refused to accepted - 46.2/D honest with the `edge_break_coverage` floor UNMET, 75.3/B as sheet with every floor met.
Its plan corners span the plate's full 5 mm and its pocket corners the pocket's 1 mm, where a real fold spans the same 70.0 mm on both faces.
Cut that pocket THROUGH and the extents become equal, which is why the flange test exists: both cylinders then run out into the 5 mm thickness band of the blank rather than into flat stock, which is the geometric way of saying the axis is normal to the sheet instead of lying in it.

One thing the guard cannot yet do: a genuinely formed 2 mm U-channel is refused because 21% of its face area reads as facing an enclosed void against a 15% bar.
That is a false negative in the safe direction - the part is judged as an `enclosure`, the strictest rubric - and it is not worth relaxing, because a 2.5 mm walled shelled box measures 28% on the same test and must stay out.

The full weight matrix, which is what actually decides a score:

| Metric | `enclosure` | `cover` | `plate` | `bracket` | `sheet` | `structural` |
| --- | --- | --- | --- | --- | --- | --- |
| `edge_break_coverage` | 0.21 | 0.19 | 0.19 | 0.20 | 0.13 | 0.21 |
| `face_composition` | 0.19 | 0.19 | 0.11 | 0.13 | 0.20 | 0.14 |
| `feature_composition` | 0.16 | 0.16 | 0.19 | 0.15 | 0.22 | 0.14 |
| `pattern_discipline` | 0.12 | 0.19 | 0.23 | 0.15 | 0.22 | 0.12 |
| `radius_vocabulary` | 0.11 | 0.11 | 0.12 | 0.13 | 0.13 | 0.14 |
| `symmetry` | 0.07 | 0.08 | 0.08 | 0.08 | 0.10 | 0.07 |
| `sharp_edge_length` | 0.07 | 0.08 | 0.08 | 0.09 | n/r | 0.08 |
| `proportion` | 0.07 | n/r | n/r | 0.07 | n/r | 0.10 |
| **total** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |

Every column sums to 1.00 by construction, and the module refuses to load a rubric that does not.
A role can therefore excuse a metric, but it can never lighten the total bar: the weight an excused metric carried is redistributed onto the ones that remain.

#### How to choose one

Choose from the function you wrote in `DESIGN.md`, before the geometry exists, and in this order:

1. `enclosure` if it contains something and its exterior faces are surfaces a user sees.
2. `cover` if it is a lid or a door, thin because it closes something else.
3. `plate` if it is an interface whose hole pattern IS the part - a breadboard, a payload plate, an adapter.
4. `bracket` if it is machined or cut from solid material, with no cavity to speak of.
5. `sheet` if it is folded from flat stock, so its perimeter is a blanked edge nobody can chamfer.
6. `structural` if it is a long load-carrying member - an arm, a strut, a mast section.

If two of those fit, take the earlier one.
If the part is arguable, write the argument in `DESIGN.md` rather than leaving the reader to guess.

#### Choosing a role to escape scrutiny is dishonest

It is one word in a JSON file, it is invisible in the resulting number, and it is worth points.
That is exactly why it has to be said out loud, and why every role is now guarded.

A guard is checked **before** the rubric is honoured.
When the measured geometry contradicts the claim, the report carries a `role_error` naming the contradiction and the part is re-judged under `enclosure` - the only rubric that asserts nothing about the geometry and therefore the only one that cannot be wrong.
Measured on the refined enclosure from section 5 and on `parts/custom/reference_mast_node_enclosure/`:

| Reviewed as | Section 5 refined | Exemplar |
| --- | --- | --- |
| `enclosure` (what both are) | 92.5 A | 90.2 A |
| `cover` | refused | refused |
| `plate` | refused | refused |
| `bracket` | refused | refused |
| `sheet` | refused | refused |
| `structural` | refused | refused |

Every lie about the exemplar is refused, where the gate before the guards paid 88.2 for calling it `sheet` against 86.6 as the `enclosure` it is.

The section 5 part used to be the counterexample and no longer is, which is worth recording because it is the same defect three roles carried.
It is 169 x 102 x 42 mm.
Against its longest dimension it is 0.248 thin, a hair inside the 0.25 `cover` and `plate` bar, and 4.02 times as long as it is thin, a hair over the 4.0 `structural` bar - so it used to slip past all three and collect up to 2.3 points.
Against its SECOND longest it is 0.41 thin and only 1.66 times as long, and both of those are now measured too.
A single ratio against the single most flattering dimension was what every one of these guards had in common.

The guards are still not a substitute for honesty, and this document will not pretend they are.
They bound the lie; they do not remove it.
A part genuinely near a boundary can still profit, and only the author knows.
Declare what the part IS, and if the role is arguable, say which one you chose and why in `DESIGN.md`.

### 2.2 A metric that does not apply is not a free pass

Reporting "not applicable" used to be worth more than reporting a bad number, which meant a part could improve its score by making its geometry worse.
Every metric now reports one of four states, and only one of them is free:

| State | Meaning | Effect on the score |
| --- | --- | --- |
| `scored` | A real 0-100 number | Enters the weighted mean |
| `not_required` | The ROLE genuinely excludes it, or `spec.json` waived it with a written reason | Renormalised OUT, and it cuts `coverage`; no check is emitted |
| `absent_defect` | The geometry implies the metric SHOULD apply and it does not - holes exist but form no pattern, no break geometry exists at all | **Scores 0.0 at full weight**, never renormalised, and always emits a FAIL naming the evidence |
| `error` | It could not be measured | **Contributes zero at full weight** - it stays in the denominator - and is reported as an ERROR check |

A knife-edged box does not escape `edge_break_coverage` by having no chamfers anywhere: it scores `absent_defect` at 0.0, and so does `radius_vocabulary`.
Measured on the naive extrusion in section 5.1, those two states hold 0.32 of the rubric at zero, which is **32 points** of the 42.5 it does not have.

`not_required` is the only free state, so it is the only one with a budget: **at most 0.25 of the rubric** may be excused by assertion, counting waivers and disabled metrics together, and every one of them needs a written reason.

### 2.3 A measurement that did not happen never produces a number

Every metric tracks the fraction of its own population it could not classify, and above that metric's threshold it becomes `error` with score `None` rather than a number.

Two invariants hold, and the second one is the one that was missing:

- a failure path can never produce a score **higher** than the same geometry measured successfully - an errored metric is scored zero at full weight, not renormalised away, so `score(errored) <= score(measured)` always;
- an errored metric does not count towards `coverage`, so enough of it drives the report to `insufficient` and the review refuses to be a verdict at all.

If the overall report says `insufficient`, or lists metrics under `unmeasured metrics`, the score is not a verdict and must not be quoted as one - below 60% measured weight the module says so itself.
Failing to measure buys silence, never points.

### 2.4 The configuration surface is part of the standard

`spec.json`'s `"design"` block configures the review, and a configuration knob that can raise a score is a knob that will be turned.
Everything the block accepts is therefore validated through one front door, and every rejected key is a `config_error` in the report and an ERROR check out of the gate - never a silent fallback.

What it can do:

- `role` picks a rubric, and the geometry has to agree with the claim (section 2.1).
- `min_score` sets the overall bar, and writing it is what opts the part in and makes the check hard.
- `waivers` moves a metric to `not_required`, capped at 0.25 of the rubric in total, each with a written reason.
- `metrics.<id>.min_score` / `max_value` / `min_value` add per-metric bars, and they can only ever make the bar **higher**.
- `metrics.<id>.enabled: false` is a waiver by another name, so it needs a `reason` alongside it and counts against the same 0.25 budget.
- `symmetry_max_faces` is a **cost** guard, not an exemption: tripping it makes `symmetry` an ERROR, which under 2.3 costs its full weight at zero.
- `enabled: false` skips the review entirely.
- `severity` and `metric_severity` say whether the overall bar and the per-metric bars gate the build or only warn.

That is the whole surface.
Two keys that used to be on it are **retired**, and both were the same defect: a part declaring the standard it is measured against.

| Retired key | What it did | What it measured out at |
| --- | --- | --- |
| `design.weights` | set the metric weights per part | a crude knife-edged box: 27.7/F honestly, 100.0/A with six weights zeroed, 425.5/A with two of them negative |
| `design.style.radius_ladder` | replaced the `Style` radius ladder per part | an unchanged STEP whose one plan radius was off-ladder: `radius_vocabulary` 0.0 to 100.0, the part 57.3/C to 69.3/C, +12.0 points of pure configuration |

Both are in `lib.design_review.RETIRED_CONFIG_KEYS`, matched as dotted paths, so a nested knob retires exactly like a top-level one.
Writing either is a `config_error` in the report and a **hard** spec ERROR out of `lib/evaluate.py` - hard whatever the part's own `severity` says, because a part that wrote a key which no longer exists has not opted in to anything.
It is never a silent ignore: an agent that writes a retired key and hears nothing would believe it worked, and the whole point of retiring a knob is that the belief is wrong.

`style.radius_ladder` in particular was validated for the SHAPE of the ladder - at least 5 increasing rungs spanning at least 4:1, plus a written reason - and never for the only thing that mattered, which is whether those rungs were anything but a transcription of the part's own measured radii.
**The supported alternative is to edit `lib.features.Style`.**
The ladder lives in one frozen object, `features.STYLE`, and changing it is one reviewed edit that moves every part in the repo together, which is what makes a design language a language.
A part that wants its own ladder does not want a different ladder; it wants to not be measured, and that is a different conversation.

### 2.5 Rubric floors: the metrics no average may launder

Everything in 2.1 to 2.4 is a contribution to a weighted mean, and a mean is arbitrable.
Pick the role whose column is lightest where the part is weak, spend one waiver, and the remaining metrics carry it over the bar.
The measured worst part that could still clear a hard 70 gate was a flat 220 x 150 x 9 slab with three sunken pockets and ten border holes on which **not one edge is broken anywhere** - pocket walls meeting the top face as raw knife edges, raw hole mouths, raw top and bottom rims - scoring `edge_break_coverage` 0.0 and landing 85.6/B.

A **floor** is a hard minimum on a SINGLE metric, checked outside the mean and independent of it.
That is what makes it different from a weight, and why the answer to "this metric matters more" is sometimes a floor rather than a heavier weight.
A floor **cannot be renormalised out, averaged away, waived, disabled, lowered, or shifted by a role choice.**
Concretely, in `lib/design_review.py`:

- `design.waivers.<id>` and `metrics.<id>.enabled: false` on a floored metric are **rejected as config errors**, not honoured, because a waiver renormalises a metric out of the mean and so pays most exactly when it is least deserved.
- `metrics.<id>.min_score` **below** the floor is rejected too, rather than quietly outranked, because a number the spec.json can state and the module ignores reads like a floor the author chose - a spec may raise a floor and cannot express lowering one.
- A metric that is `absent_defect` **fails** its floor - that is the defect the floor is named after, not an escape from it.
- A metric that is `error` fails its floor as well, so breaking a measurement is never cheaper than passing it.
- A **role exclusion** is the one thing that legitimately removes a floor, because a role's weights already sum to 1.00 and a metric the role does not use buys the part nothing - and every role's claim is guarded against the geometry first (2.1).

Two metrics carry a floor.
`lib.design_review.RUBRIC_FLOORS` is the authority for the levels and carries the calibration sentence behind each one; the table below is what it currently holds.

| Metric | Floor | Held against | Why this one, and not the others |
| --- | --- | --- | --- |
| `edge_break_coverage` | 10 | `body_score`, **not** the metric's own score | a part on which essentially no BODY corner is broken has not had a refinement pass at all. 10 is a body coverage of about 23%, and the metric's body term is zero at or below 15% and 100 at 92% |
| `sharp_edge_length` | 25 | its score | the same defect measured in absolute length rather than as a fraction, which is the only way to see a part that holds a passable break FRACTION on a small edge population while carrying a whole prism of raw edge |

**A floor names the quantity it reads, and that is not decoration.**
`edge_break_coverage` is a COMPOSITE - 0.85 body plus 0.15 bore/detail rim - so flooring the composite floored the wrong thing: the rim term alone is worth 15.0 against a floor of 10.0, and a part on which not one body corner was broken cleared the floor named after exactly that defect simply by deburring its bore mouths.
The two terms measure different things and must not substitute for each other, so `Floor` carries a `key` and this one reads `body_score`.
If a metric scores but the floored quantity is missing from its report, the floor is **not** cleared: an unreported number is a measurement that did not happen, held to the same rule as any other.

The other six carry none on purpose, and the reasons are in `RUBRIC_FLOORS`' own commentary: `face_composition` because a legitimately plain bolted box scores in the low teens on it, `radius_vocabulary` because its reference standard lives outside the part, `feature_composition` and `pattern_discipline` because "no features at all" and "two functionally placed holes" are both legitimate, `symmetry` because handedness is a real design decision, and `proportion` because it does not discriminate.
A floor that fires on a good part is worse than no floor, because it teaches agents the gate is noise.

What an unmet floor does, at **every** severity:

1. the reported **band** is capped at `D`, below the advisory gate of 70, so an unmet floor can never read as a pass.
   The score itself is left exactly as measured; hiding the mean would be its own dishonesty.
2. `design_review.score` **fails**, so nobody reads "refinement score 85.6 ... PASS" on a part with no broken edge anywhere.
3. a `design_review.floor.<id>` check fails at the review's **overall** severity.
   `metric_severity` never reaches it: "this metric does not matter to me" is precisely the claim a floor exists to refuse.
   So whenever the design gate is hard, the floor is hard, and a part that predates the gate still only warns.

The floors are reported whether or not they are met - the console report ends with a `rubric floors met:` or a failing line, and `report["floors"]` carries every one with its measured score - because a bar nobody can see is a bar nobody is held to.

### 2.6 `config_delta`: how much of the score is the spec.json

Every knob above is accounted for individually, and until recently nothing added them up.
The review therefore scores the **same measurements** a second time under the default `enclosure` rubric with nothing excused, and reports the difference as `report["config_delta"]`:

```
"config_delta": {"default_score": <same geometry, default rubric, nothing excused>,
                 "configured_score": <the score this part is reported at>,
                 "delta": <the difference>, "cap": <MAX_CONFIG_DELTA>,
                 "within_cap": true, "knobs": ["role=sheet", "waiver:symmetry"]}
```

It is one extra scoring pass over the same topology, the same extracted features and the same symmetry booleans - a re-scoring, not a second geometric analysis, measured at 1 to 4% of the review's own cost - and it is skipped entirely when there is no configuration to account for.
Both numbers are real weighted means over real metrics; they simply answer different questions.
`knobs` names what moved it: the role, if it is not the default, and one entry per waiver that actually took effect.

Read it as the sentence "this much of the verdict is the spec.json rather than the part".
A part that declares `enclosure` and waives nothing reports a delta of **exactly 0.0** by construction, which is the honest reading of a part that configured nothing - the exemplar does exactly that.
A legitimate role still buys something real, and the widest of them is `sheet`, whose role exists precisely because a formed blank judged as an enclosure is asked to break a perimeter it cannot break.
Past `MAX_CONFIG_DELTA` the delta is itself a `config_error` and an ERROR check, on the same surface a retired key lands on.
It is a **backstop that notices the next knob**, not a substitute for validating the knobs that exist: the right response to a large delta is to ask whether the role is what the part is, never to trim the waivers until the number fits.

### Target

A new custom part should reach **B (>= 70)** before it is promoted, and the intent is A.
Note honestly what an A means: it clears every bar this module can hold up.
Nothing in the review can see whether a structural member is sculpted, whether an emblem is well placed, or whether a connector sits on a proper land.
Sections 4 and 9 cover what the score cannot.

Calibration, re-measured on 2026-07-27 by `uv run python -m tests.design_corpus`, which builds twenty-seven synthetic parts plus four real ones and prints this table:

| Part | Role | Score | Band |
| --- | --- | --- | --- |
| Optical interface plate, M6 grid at exactly 25 mm | `plate` | 95.1 | A |
| `reference_mast_node_enclosure` v1, the exemplar | `enclosure` | 90.2 | A |
| Sculpted structural arm, step-stack pivot boss | `structural` | 89.7 | A |
| Sealed cover, lapped face, O-ring groove, locating spigot | `cover` | 82.6 | B |
| 2 mm sheet-metal Z-bracket, two formed bends | `sheet` | 82.0 | B |
| Filleted, chamfered, panelled, ribbed box with a solved bolt pattern | `enclosure` | 80.3 | B |
| Machined angle bracket, pocketed legs | `bracket` | 76.6 | B |
| Best of twelve deliberately gamed parts (the soap bar) | `enclosure` | 59.8 | C |
| Plain sharp box | `enclosure` | 15.3 | F |

The corpus is a contract, not a demo.
Its nine assertions are that every case scores at all, that the refinement ladder is monotonic, that the plain sharp box is the floor, that no gamed case reaches 70, that every good case clears 70 under its own role, that every gamed case and every crude case sits at least 5 points below every good one, that no gamed case outranks the exemplar, and that the exemplar outranks every other real part by 5 while no other real part reaches the gate.
All nine hold; the run prints `contract: 9 hold, 0 FAIL, 0 unevaluated of 9`.

Read the table as calibration and the contract as the standard.
Absolute scores move whenever a metric is retuned, and the ORDERING is the thing that must not - which is exactly why the contract asserts the ordering and not the numbers.
**The table above is generated, not written.** When a metric changes, regenerate it rather than editing the prose:

```
uv run python -m tests.design_corpus
```

The same applies to the section 5 numbers below and to every score quoted in `CLAUDE.md`, `README.md` and the `cad-part-design` skill: re-measure, do not adjust by hand.

---

## 3. The ladders

Every number below is read out of `features.STYLE`, not typed by hand.
Regenerate this whole section with the snippet in the appendix if `Style` ever changes.

### 3.1 Plan-corner radii

The governing dimension is the **smaller** of the two plan dimensions.
`STYLE.plan_radius(length, width)` quantises `0.12 x governing` onto the ladder `(3, 5, 8, 12, 16, 24)` mm and caps the result at 45% of the governing dimension so the rounded rectangle stays buildable.

| Governing plan dim (mm) | Plan radius (mm) |
| --- | --- |
| 20 | 3 |
| 30 | 3 |
| 40 | 5 |
| 60 | 8 |
| 80 | 8 |
| 100 | 12 |
| 120 | 16 |
| 160 | 16 |
| 200 | 24 |
| 260 and above | 24 |

A 160 x 100 mm enclosure therefore gets **R12**, not R16: the 100 mm width governs.

### 3.2 Edge breaks (rim chamfers)

`STYLE.edge_break(size, wall)` quantises `0.015 x size` onto the ladder `(0.4, 0.6, 1.0, 1.5, 2.5, 4.0)` mm, then clamps to 40% of the wall it sits on.
A break larger than that stops being a break and becomes a knife edge from the other side.

Unclamped, by part size:

| Part size (mm) | Break (mm) |
| --- | --- |
| 20-30 | 0.4 |
| 40 | 0.6 |
| 60-80 | 1.0 |
| 100-120 | 1.5 |
| 160-200 | 2.5 |
| 260 and above | 4.0 |

Clamped by wall, which is what you will actually get:

| Wall (mm) | 40 mm part | 100 mm part | 200 mm part | 400 mm part |
| --- | --- | --- | --- | --- |
| 1.6 | 0.6 | 0.6 | 0.6 | 0.6 |
| 2.0 | 0.6 | 0.6 | 0.6 | 0.6 |
| 2.5 | 0.6 | 1.0 | 1.0 | 1.0 |
| 3.2 | 0.6 | 1.0 | 1.0 | 1.0 |
| 4.0 | 0.6 | 1.5 | 1.5 | 1.5 |
| 6.0 | 0.6 | 1.5 | 1.5 | 1.5 |
| 8.0 | 0.6 | 1.5 | 2.5 | 2.5 |

### 3.3 Wall thickness by process

`STYLE.wall(process, span)` returns `max(nominal, per_span x span)`, rounded to 0.1 mm.
The span is the **unsupported** span of that wall, not the part size.
`minimum` is the absolute floor and is also the guard that every material-removing builder checks (`STYLE.min_wall` = 1.6 mm).

| Process | Minimum | Nominal | Per span | span 80 | span 160 | span 300 | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `machined-aluminium` | 1.5 | 2.5 | 2.0% | 2.5 | 3.2 | 6.0 | 3-axis milled 6061/7075; 1.5 is cutter-deflection limited |
| `cast-aluminium` | 3.0 | 4.0 | 3.0% | 4.0 | 4.8 | 9.0 | A356 sand or gravity cast; needs draft and generous fillets |
| `sheet-metal` | 1.0 | 1.5 | 0.8% | 1.5 | 1.5 | 2.4 | Formed sheet; bend radius >= thickness |
| `printed-fdm` | 1.2 | 2.4 | 2.0% | 2.4 | 3.2 | 6.0 | 0.4 nozzle, 6 perimeters at 2.4 |
| `printed-sls` | 0.8 | 2.0 | 1.5% | 2.0 | 2.4 | 4.5 | PA12; thin walls warp on long spans |

A wall can also be set by a fastener rather than by a span.
A wall that must accept a tapped hole needs the boss diameter of section 3.4, and that usually means a local boss rather than a thicker wall.

### 3.4 Fasteners

All metric socket head cap screws, ISO 4762 heads, coarse-pitch taps.
Get these from `STYLE.fastener("M4")`, never from memory.
Minimum thread engagement in aluminium is `2 x nominal` (`Fastener.min_tap_depth`).

| Screw | Clearance | Head dia | Cbore dia | Cbore depth | Tap drill | Boss OD | Min edge | Pitch band | Default pitch | Edge inset | Min tap depth |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M3 | 3.4 | 5.5 | 6.5 | 3.4 | 2.5 | 8.0 | 5.0 | 18-32 | 25.0 | 7.0 | 6.0 |
| M4 | 4.5 | 7.0 | 8.0 | 4.4 | 3.3 | 10.0 | 6.5 | 24-45 | 34.5 | 9.0 | 8.0 |
| M5 | 5.5 | 8.5 | 10.0 | 5.4 | 4.2 | 12.0 | 8.0 | 30-55 | 42.5 | 11.0 | 10.0 |
| M6 | 6.6 | 10.0 | 11.0 | 6.4 | 5.0 | 14.0 | 9.5 | 36-65 | 50.5 | 12.0 | 12.0 |
| M8 | 9.0 | 13.0 | 15.0 | 8.4 | 6.8 | 18.0 | 12.5 | 48-90 | 69.0 | 16.5 | 16.0 |

"Edge inset" is the recommended hole-centre to part-edge distance, and it is larger than "min edge" on purpose: a counterbore wants visible material around it, and a constant inset is what makes a bolt pattern read as a frame.

Two derived rules that are easy to get wrong:

- A counterbored screw on a framed panel needs `frame >= edge_inset + cbore_dia / 2`.
  M4 at inset 9.0 with an 8.0 cbore needs a 13 mm frame, so the default 8 mm frame will straddle the panel mouth.
  The worked example passes `frame=16.0` for exactly this reason.
- A tapped hole needs `boss OD` of material around it, so an M4 tap wants a 10 mm boss.
  A 3.2 mm wall cannot be tapped; add a `tapped_boss`.

### 3.5 Recessed panels

`STYLE.recess(wall)` returns `min(1.8, 0.45 x wall)`.
`STYLE.frame(length, width)` returns `max(8.0, 0.07 x governing)` where governing is again the smaller dimension.

| Wall (mm) | Recess depth (mm) | Wall left (mm) | Guard |
| --- | --- | --- | --- |
| 1.6 | 0.72 | 0.88 | raises `WallGuardError` |
| 2.0 | 0.90 | 1.10 | raises `WallGuardError` |
| 2.5 | 1.12 | 1.38 | raises `WallGuardError` |
| 3.0 | 1.35 | 1.65 | ok |
| 3.2 | 1.44 | 1.76 | ok |
| 4.0 | 1.80 | 2.20 | ok |
| 6.0 and above | 1.80 | 4.20+ | ok |

**A wall thinner than 3.0 mm cannot carry a recessed panel.**
That is not a bug to work around, it is the guard doing its job: below 3.0 mm the remaining wall falls under the 1.6 mm structural minimum.
The fix is to size the wall from its span (section 3.3) before styling it, which for a 160 mm span gives 3.2 mm and clears the guard.

Frame width by governing face dimension:

| Governing face dim (mm) | Frame (mm) |
| --- | --- |
| up to 100 | 8.0 |
| 120 | 8.4 |
| 160 | 11.2 |
| 200 | 14.0 |
| 260 | 18.2 |
| 320 | 22.4 |
| 400 | 28.0 |

### 3.6 Ribs

| Parameter | Value | Source |
| --- | --- | --- |
| Thickness | 2.0 mm | `STYLE.rib_thickness` |
| Draft | 2.0 deg per side | `STYLE.rib_draft_deg` |
| Crest relief below the outer face | 0.4 mm | `STYLE.rib_relief` |
| Default pitch | 14.0 mm | `STYLE.rib_pitch` |
| Height | pocket depth minus relief | derived |

Patterns: `chevron`, `x`, `triangulated`, `parallel`, `diagonal-grid`.
Ribs are always clipped to the pocket they live in, so they cannot spill onto the frame.

### 3.7 Fins

| Parameter | Value | Source |
| --- | --- | --- |
| Thickness | 2.0 mm | `STYLE.fin_thickness` |
| Pitch | 6.0 mm | `STYLE.fin_pitch` |
| Draft | 1.5 deg | `STYLE.fin_draft_deg` |
| Tip | radiused, in the revolved or extruded profile | `fin_bank` |

Fins are specified by `count` or by `span`, and the builder solves the other.
Measured in the worked example: 14 fins at 5.85 mm pitch over a 76 mm span, 6 mm tall, adding **4904 mm2 of net wetted area** after subtracting the root footprint twice.
Quote `FinBank.added_area_mm2` in DESIGN.md rather than claiming a thermal benefit.

### 3.8 Louvers

| Parameter | Value | Source |
| --- | --- | --- |
| Blade angle | 35 deg | `STYLE.louver_angle_deg` |
| Pitch | 7.0 mm | `STYLE.louver_pitch` |
| Orientation | outer mouth is the LOW end | `louver_bank` |

Measured on a 90 x 40 mm window in a 12 mm wall:

| Count | Pitch | Gap | Free area | Throat area | Free area as % of window |
| --- | --- | --- | --- | --- | --- |
| 5 | 8.00 | 4.40 | 2413 mm2 | 1977 mm2 | 67.0% |
| 7 | 5.71 | 3.14 | 2414 mm2 | 1978 mm2 | 67.1% |

Free area is measured off the cut geometry in the wall plane, so it is a number you can put in a spec.
Target 50-70% of the window for a convection path; below 30% the louvers are decoration and fail R6.

### 3.9 O-ring grooves

Static face seals, sized by cord diameter, from `CORD_TABLE`.
All values measured by `oring_groove()` on a 120 x 80 rounded-rect path:

| Cord dia | Groove width | Groove depth | Squeeze | Fill |
| --- | --- | --- | --- | --- |
| 1.02 | 1.40 | 0.73 | 28.4% | 80.0% |
| 1.27 | 1.75 | 0.91 | 28.3% | 79.5% |
| 1.78 | 2.40 | 1.30 | 27.0% | 79.8% |
| 2.62 | 3.55 | 1.93 | 26.3% | 78.7% |
| 3.53 | 4.70 | 2.62 | 25.8% | 79.5% |
| 5.33 | 7.10 | 4.00 | 25.0% | 78.6% |
| 6.99 | 9.30 | 5.28 | 24.5% | 78.1% |

Acceptance band for a static face seal: **squeeze 20-30%, fill 75-85%**.
A rectangular groove clamps its corner radius up to at least the groove width so the groove can turn its own corner.

Layout consequence to plan for early: a sealed lid rim must carry the outer edge break, the groove, and the screw circle outside the seal.
For a 2.62 cord that is about 1.0 + 3.55 + margin + the screw inset, so a sealed flange lands near 16 mm wide.
Decide this before the wall thickness, not after.

### 3.10 Identity marks

| Parameter | Value | Source |
| --- | --- | --- |
| Default relief | 0.6 mm | `STYLE.emblem_relief` |
| Maximum relief | 1.0 mm | `STYLE.emblem_relief_max` |
| Count | one per face | R11 |

Negative relief engraves.
`emblem()` raises above the 1.0 mm limit; `text_mark()` degrades to a warning and returns the part unchanged if the font is missing, unless you pass `strict=True`.

---

## 4. The vocabulary, rule by rule

Each rule is a checkable assertion, the builder that implements it, and the metric that will catch you.

### R1 - No raw extrusions

**Assertion:** every exterior plan corner carries a ladder radius from 3.1, and no exterior convex edge is left sharp.
**Build with:** `rounded_box(l, w, h, radius, top_break=..., bottom_break=...)`, `rounded_prism(profile, height, radius)`.
**Measured by:** `edge_break_coverage` (weight 0.21) and `sharp_edge_length` (0.07).
The metric scores two populations separately: the BODY silhouette carries 0.85 of it and reaches 100 at 92% of convex body edge broken, and the bore/boss RIM term carries the remaining 0.15 and reaches 100 at 90% of rim length broken.
Target `edge_break_coverage >= 90`, which needs the body essentially fully broken **and** roughly 45% of the rims given a lead-in chamfer.
A part with no break geometry anywhere does not escape this metric: it reports `absent_defect` and scores 0 at full weight.
The plan radii come from the 2D profile, so no 3D fillet ever runs on a prism.

### R2 - Every pocket mouth is broken

**Assertion:** a recess, cavity or aperture mouth is never a knife edge.
**Build with:** cut an oversized rounded prism whose own bottom edge already carries the chamfer, as in the `break_mouth` helper in section 5.
**Measured by:** `edge_break_coverage` and `sharp_edge_length`.
This is the single cheapest large gain in the whole language.
Measured on the skill's worked example, adding `break_mouth` to the cavity and to all four recessed panels and changing nothing else took the part from **59.8 (C) to 76.7 (B)**: `edge_break_coverage` 25.2 to 90.1 and `sharp_edge_length` 39.1 to 100.0, because 761 mm of unbroken convex edge became zero.
Nothing else in this document is worth 16.9 points for one helper.
Note that `recessed_panel` and `lightening_pocket` do **not** break the mouth for you today, so this is your job.

### R3 - No blank slab faces

**Assertion:** no exterior planar face contains a large empty region.
Every large face carries a recessed panel with a proud frame, a bolt pattern, a rib field, a fin bank, a connector land or exactly one emblem.
**Build with:** `recessed_panel(solid, "+Z")`, then `rib_field(pocket, "chevron")`.
**Measured by:** `face_composition` (weight 0.19).
It is a graded measure, not a has-a-hole test: it discretises each large exterior planar face, subtracts every inner wire that has **more than 1 mm of real relief**, and measures the largest circle that still fits in what is left, normalised by the silhouette that face looks at.
For an `enclosure`, the worst face reaches 100 at 0.25 of its own silhouette scale and reaches zero at 0.60; the area-weighted mean over all large faces reaches 100 at 0.18 and zero at 0.50.
Three scattered holes leave a large empty circle between them and buy almost nothing.
A scribed outline buys nothing at all: measured on the corpus, decorative scribe grooves read 0.5 to 0.9 mm deep and are filtered out, where the exemplar's real features read 10.0 mm.
Interior faces count when they are open to air, because a human can see into an open cavity; a sealed void is not measured at all.
Section 5.3 shows what that costs a hollow part and why it is correct.

### R4 - Fastener rhythm, not scattered holes

**Assertion:** visible screws are counterbored socket heads at a constant pitch inside the fastener's pitch band, at a constant inset from the edge, symmetric about both part centrelines.
**Build with:** `bolt_pattern("perimeter", length=..., width=..., fastener="M4", target_pitch=...)`, then `counterbore_at(solid, pattern.points, plane=...)`.
Check `BoltPattern.in_band` before you accept the pattern.
**Measured by:** `pattern_discipline` (weight 0.10 for an `enclosure`, 0.20 for a `plate`), scored per family as 45% pitch regularity, 35% centreline mirror fraction, 20% inset consistency.
A family is three or more holes sharing one diameter rung and one axis direction, and the bore, counterbore and countersink of a single screw are merged before grouping, so a counterbored pattern is counted once rather than twice.
Two things that used to be free now cost:

- **Loose holes dilute.** The family scores are averaged by hole count and then multiplied by `patterned / (patterned + loose)`, so a good pattern plus a scattering of one-offs is not a good pattern.
- **Scatter is a defect, not an exemption.** Holes that form no family of three report `absent_defect` and score 0 at full weight.
  Enlarging bad holes past a diameter cap no longer removes the penalty; there is no diameter cap.

Solved examples, all `in_band=True`:

| Face | Screw | Count | Pitch | Inset |
| --- | --- | --- | --- | --- |
| 160 x 100 | M4 | 12 | 35.5 | 9.0 |
| 300 x 200 | M6 | 16 | 55.2 | 12.0 |
| 90 x 60 | M3 | 10 | 25.3 | 7.0 |

### R5 - Counterbores land on flat lands only

**Assertion:** every counterbore sits on a planar face that exists before the hole is cut, and never on a curved, ribbed or recessed surface.
**Build with:** `connector_land(...)` or a frame from `recessed_panel(...)`, then `counterbore_at(...)`.
**Measured by:** nothing in `design_review.py` catches this, so it is on you.
A counterbore on a curve gives a crescent seat that no screw head sits on, and it will only be found at assembly.
No metric sees it; the hero render sees it instantly, which is why section 7 makes looking mandatory.

### R6 - Functional texture only

**Assertion:** ribs, fins, louvers and drip edges appear only where they stiffen, cool, ventilate or shed water, and each one reports a measured number.
**Build with:** `rib_field`, `fin_bank`, `louver_bank`, `drip_edge`.
**Measured by:** `feature_composition` (weight 0.16), which does not reward mere presence.
`feature_composition` scores the fraction of feature CENTRES that share a centreline with another centre or sit in a constant-pitch run, so a constant-pitch fin bank or louver bank scores well **because it is regular** and one unrelated hole added beside it scores zero and drags the part down.
The old metric counted faces, which meant meaningless detail bought score directly; the corpus's forty-random-holes slab now measures 22.9 (band F).
The justification is still the builder's own measurement: `FinBank.added_area_mm2`, `LouverBank.free_area_mm2`, `ORingGroove.squeeze_pct`.
Put those numbers in the part's DESIGN.md.

### R7 - No butt joints between a cylinder and a prism

**Assertion:** every diameter change or prism-to-cylinder transition is a concentric step ring, a faceted collar, or a tangent blend shoulder.
**Build with:** `step_shoulder(lower_dia, upper_dia, height, steps=2)` or `blend_transition(lower_dia, upper_dia, height, kind="fillet" | "cone" | "facet")`.
**Measured by:** `radius_vocabulary` sees the result indirectly, because a step ring and a blend shoulder both put their radii on the ladder while a butt joint puts nothing there.
There is no direct check: this rule is enforced on the hero render.
Every edge in these builders lives in a revolved profile, so nothing is ever filleted after the fact.
`kind="fillet"` is a single tangent arc, tangent at the upper diameter only; stack two calls for a true S-curve.

### R8 - Connectors sit on dedicated lands

**Assertion:** a connector aperture is never punched straight through a curved, ribbed or textured wall.
It sits on a raised or recessed flat land with a chamfered boundary and its own 4-screw pattern.
**Build with:** `connector_land(solid, "+X", length=..., width=..., raised=3.0, fastener="M3")`, which drills its own four screws.
Then cut the aperture with a tool of known length, because `connector_land(aperture=...)` sizes its cutter to clear the WHOLE solid and so punches a matching hole through the opposite wall of a hollow part.
The `wall_window` helper in section 5.2 is the pattern.
**Measured by:** `face_composition` improves, because the land and its aperture break up the largest empty circle on that wall.
Be aware of the honest cost: a connector aperture is a **lone** feature of its own diameter, and `feature_composition` scores a lone feature zero.
Measured on the section 5 example, the land plus the window plus one identity mark are worth **+5.9 points** overall, and `feature_composition` still pays 97.9 to 90.8 for the lone aperture.
That is both halves of the metric doing their job: put the land's own four screws on a real pattern, keep its radii on the ladder, and the composition it buys outweighs the family of one.
Do not delete the connector to protect a number, and record the trade in `DESIGN.md`.

### R9 - Interface plates carry a regular tapped grid

**Assertion:** a payload or mounting interface is a constant-pitch grid of tapped holes, and the pitch is exact because the pitch is the published contract.
**Build with:** `tapped_hole_grid(solid, "+Z", pitch=25.0, fastener="M6")`.
Leftover space goes to the margin, never to the pitch.
**Measured by:** `pattern_discipline` (weight 0.23 under the `plate` role) and `feature_composition` (0.19).
Declare `"role": "plate"` for such a part: the plate rubric is the one that stops charging it for being thin and for having a bare mounting underside, and instead makes its grid the biggest single term in its score.
Expect `in_band=False` for the common M6-at-25 mm breadboard grid: 25 mm is tighter than M6's structural band of 36-65, and that is correct for an interface grid.
Measured on a 200 x 150 plate: 48 holes on an 8 x 6 grid, every step exactly 25.000 mm in both axes.
The corpus's optical interface plate, built to exactly this rule, is the highest-scoring part in the whole corpus at **95.1, band A**.

### R10 - Base flanges are radiused and stepped

**Assertion:** a floor-standing or mast-mounted assembly ends in a rectangular flange with ladder corner radii, a chamfered or stepped edge, and corner or perimeter bolt holes.
**Build with:** `base_flange(length, width, thickness, edge="chamfer" | "step", holes="corners" | "perimeter" | "none")`.
**Measured by:** `edge_break_coverage` and `pattern_discipline`.
Use `holes="none"` until the mating pattern is actually released, and be aware that this is one of the few places where doing the honest thing costs score: a flange with no holes contributes no fastener family, and if the part has no other family at all `pattern_discipline` reports `absent_defect` at 0. Say so in `DESIGN.md`; do not invent a pattern to fix a number.

### R11 - One identity mark per face

**Assertion:** at most one emblem or wordmark per face, at 1.0 mm relief or less, centred on a panel.
**Build with:** `emblem(solid, pocket.plane, motif="rings", diameter=24.0, relief=-0.6)` or `text_mark(...)`.
**Measured by:** nothing scores taste, but `symmetry` will punish an off-centre mark, and `radius_vocabulary` will punish an off-ladder relief.
Place the mark on `pocket.plane` rather than on `">Z"`, so it lands on the panel floor and not on whatever the highest face happens to be.

### R12 - Structural members are sculpted, not slabs

**Assertion:** a load-carrying arm or bracket is thick where it is loaded and thin where it is not, with ribs following the load path, lightening pockets with ladder corner radii, and a circular bearing cover with a bolt circle at each pivot.
**Build with:** `rounded_prism(profile, height, radius)` for the tapered outline, `lightening_pocket(...)` for the mass removal, `rib_field(...)` inside the pockets, `bolt_pattern("circle", diameter=..., count=...)` at pivots.
**Measured by:** `face_composition` catches the unsculpted flank, and `feature_composition` catches lightening pockets that follow no line.
Declare `"role": "structural"` for such a part: `proportion` is then judged against 5:1 rather than 3:1, so a genuinely long arm is not penalised for being long.
That claim is guarded - the longest dimension has to measure at least 4.0 times the shortest - so a boxy part cannot borrow the relaxation.
This is the rule the review understands least and the eye understands best.
The corpus's sculpted structural arm scores 89.7 (band A) as `structural`, and it is worth reading `tests/design_corpus.py` for how it is built.

### R13 - One radius vocabulary across the part

**Assertion:** every radius and every chamfer leg in the part is a ladder rung, and the part uses at most four distinct sizes.
**Build with:** `STYLE.plan_radius(...)`, `STYLE.edge_break(...)`, and explicit ladder values wherever a builder takes one, for example `tapped_boss(..., base_fillet=1.0)`.
**Measured by:** `radius_vocabulary` (weight 0.11), scored as `100 x on-ladder-area-share x (1 - 0.5 x excess)`, where `excess` ramps from 0 at four distinct sizes to 1 at ten.
Sizes are bucketed by ladder RUNG rather than by raw measurement, with a tolerance of `max(0.06, 8%)`, so a 0.6 mm chamfer that measures 0.55 on one land and 0.60 on another still counts as one design size.
A part with no fillet or chamfer geometry at all reports `absent_defect` and scores 0 at full weight rather than being excused.
Watch the builder defaults: `tapped_boss` defaults its root fillet to `max(1.0, 0.12 x boss OD)`, which is 1.2 mm for M4 and lands off the ladder, so pass `base_fillet=1.0`.
The count is what hurts, not the conformance.
The section 5 example scores a flat 100.0 with 4 distinct sizes at 100% on-ladder area, and it only got there by taking every break off a ladder rung: its lid columns pass `base_fillet=3.0`, because the default 1.2 mm root on an M4 boss reads as a 6.2 mm blend that is on no rung at all.
This is also the one metric where a real part can be doing everything right and still score badly - the exemplar sits at 48.5 with 97% of its area on the ladder and 10 distinct sizes, several of them the module's own derived leg measurement on sloped or short lands rather than numbers anyone typed.
Read the `distinct` list in the report JSON before you change any geometry for it.

### R14 - Uniform finish

**Assertion:** one matte dark-grey or black finish across the assembly; connectors and gaskets are the only contrast elements.
**Build with:** the render palette in section 7 (`material="anodised"`, `"gasket"`, `"connector"`).
**Measured by:** nothing; it is a rendering and specification rule.

---

## 5. Worked example: the same part twice

A 160 x 100 x 42 mm machined-aluminium electronics enclosure body.
Cavity opens downward, a lid screws on from below, one connector on the +X end.
Both versions were built, exported to STEP, re-imported and reviewed on 2026-07-25.

Shared setup, every number taken from the style rather than typed:

```python
from lib.features import STYLE

L, W, H = 160.0, 100.0, 42.0
WALL = STYLE.wall("machined-aluminium", span=L)   # 3.2 mm - span-driven
R    = STYLE.plan_radius(L, W)                    # 12.0 mm - the 100 mm width governs
BRK  = STYLE.edge_break(L, WALL)                  # 1.0 mm - clamped to 40% of the wall
```

### 5.1 Before: the naive extrusion

```python
import cadquery as cq

def naive() -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(L, W, H, centered=(True, True, False))
        .faces("<Z").workplane()
        .rect(L - 2 * WALL, W - 2 * WALL).cutBlind(-(H - WALL))
        .faces("<Z").workplane()
        .rect(L - 14, W - 14, forConstruction=True).vertices().hole(4.5)
        .faces(">X").workplane()
        .rect(30, 16).cutThruAll()
    )
```

22 faces.
It is a correct box with a cavity, four lid screw holes and a connector cutout.
Every requirement is met and nothing about it is finished.

### 5.2 After: the same part in the design language

Two local helpers do the work no builder does for you.
Both build a lone simple solid, break THAT, and only then cut, because a boolean edge is the one thing OCCT will not fillet reliably.

```python
import cadquery as cq
from lib.features import (
    STYLE, Build, bolt_pattern, connector_land, emblem, face_plane, fin_bank,
    lightening_pocket, recessed_panel, rib_field, rounded_box, tapped_boss,
)

def break_mouth(solid, pocket, c: float = 0.6):
    """
    Chamfer the mouth of an already-cut rounded pocket.

    The tool is an oversized rounded prism sunk `c` below the face, and its own
    bottom edge already carries the chamfer, so the band it removes spans
    exactly the mouth. `pocket.plane` sits on the pocket FLOOR, so it is lifted
    back to the face here - which is why an off-centre panel still gets its
    whole mouth broken, and why no face plane has to be captured before the cut.
    """
    p = pocket.plane
    sunk = cq.Plane(origin=p.origin + p.zDir * (pocket.depth - c), xDir=p.xDir, normal=p.zDir)
    tool = rounded_box(pocket.length + 2 * c, pocket.width + 2 * c, 40.0,
                       pocket.radius + c, bottom_break=c, plane=sunk)
    return solid.cut(tool)


def wall_window(solid, plane, length, width, radius, depth, c: float = 0.6):
    """
    Cut a rounded window of KNOWN depth through one wall, mouth broken.

    connector_land(aperture=...) sizes its cutter to clear the whole solid, so
    on a hollow part it punches a matching hole in the opposite wall too. An
    aperture that has to stop at the cavity therefore gets its own tool.
    """
    inward = cq.Plane(origin=plane.origin, xDir=plane.xDir, normal=plane.zDir * -1.0)
    solid = solid.cut(rounded_box(length, width, depth, radius, plane=inward))
    sunk = cq.Plane(origin=plane.origin - plane.zDir * c, xDir=plane.xDir, normal=plane.zDir)
    return solid.cut(rounded_box(length + 2 * c, width + 2 * c, 40.0, radius + c,
                                 bottom_break=c, plane=sunk))


def refined() -> cq.Workplane:
    # 1. BASE - plan radii and rim breaks baked into a lone simple solid
    stock = rounded_box(L, W, H, R, top_break=BRK, bottom_break=BRK)
    roof = face_plane(stock, "+Z")
    bottom = face_plane(stock, "-Z")   # capture while the face is still whole:
    b = Build(stock, "stock")          # once the cavity is cut, "-Z" is its CEILING

    # 3. POCKET - cavity first, then the exterior panels, every mouth broken.
    # The roof panel is deliberately off-centre, leaving a clear land at the +X
    # end for the one identity mark (R11).
    cav = b.pocket(
        lambda s: lightening_pocket(
            s, bottom, size=(L - 2 * WALL, W - 2 * WALL), depth=H - WALL, radius=8.0
        ),
        "cavity",
    )
    b.pocket(lambda s: break_mouth(s, cav, BRK), "cavity_mouth")

    panels = {}
    for face, kw in (("+Z", dict(size=(100.0, 68.0), center=(-14.0, 0.0))),
                     ("+Y", {}), ("-Y", {})):
        pk = b.pocket(
            lambda s, f=(roof if face == "+Z" else face), k=kw: recessed_panel(s, f, **k),
            f"panel_{face}",
        )
        panels[face] = pk
        b.pocket(lambda s, p=pk: break_mouth(s, p), f"mouth_{face}")

    # 4. RIB - additive geometry, clipped to the pocket it lives in
    for face in ("+Z", "+Y", "-Y"):
        b.rib(lambda s, f=face: s.union(rib_field(panels[f], "parallel", count=9).solid),
              f"ribs_{face}")

    # The roof is the largest unsupported span on the part and the lid recess
    # thins it to 1.76 mm, so it is ribbed from inside as well.
    b.rib(lambda s: s.union(rib_field(cav, "parallel", count=9, height=3.0).solid),
          "ceiling_ribs")

    for u, v in [(x, y) for x in (-58.0, 58.0) for y in (-33.0, 33.0)]:
        pl = cq.Plane(origin=(u, v, H - WALL), xDir=(1, 0, 0), normal=(0, 0, -1))
        b.rib(lambda s, p=pl: s.union(tapped_boss(10.0, fastener="M3", base_fillet=1.0, plane=p)),
              "pcb_standoff")

    # Lid screw columns run from the roof DOWN to the seal plane, so they end
    # flush with it. Built the other way up they stand 0.2 mm proud of the
    # sealing face - the builder overlaps additive geometry on purpose - and
    # the lid cannot seat. base_fillet=3.0 keeps the root blend on the ladder:
    # the 1.2 mm default reads as a 6.2 mm blend, which is on no rung.
    pat = bolt_pattern("perimeter", length=L, width=W, inset=7.0, fastener="M4",
                       target_pitch=35.0, plane=bottom)
    for i, (u, v) in enumerate(pat.points):
        pl = cq.Plane(origin=(u, v, H - WALL), xDir=(1, 0, 0), normal=(0, 0, -1))
        b.rib(lambda s, p=pl: s.union(
                  tapped_boss(H - WALL, fastener="M4", base_fillet=3.0, plane=p)),
              f"lid_column_{i}")

    fb = fin_bank(height=6.0, base="flat", length=30.0, span=76.0,
                  plane=cq.Plane(origin=(-L / 2, 0, H / 2), xDir=(0, 1, 0), normal=(-1, 0, 0)))
    b.rib(lambda s: s.union(fb.solid), "fins")

    # 5. HOLE - apertures and marks last
    land = b.hole(
        lambda s: connector_land(s, "+X", length=44.0, width=28.0, raised=3.0, fastener="M3"),
        "connector_land",
    )
    b.hole(lambda s: wall_window(s, land.plane, 30.0, 16.0, 2.5, WALL + 5.0, BRK),
           "connector_window")
    b.hole(lambda s: emblem(s, roof, motif="rings", diameter=22.0, relief=-0.6,
                            center=(50.0, 0.0)),
           "emblem")
    return b.result
```

620 faces, one solid.
Measurements the builders reported while it built: 14 fins at 5.85 mm adding 4904 mm2 of wetted area, 12 M4 screws at 36.5 mm pitch with `in_band=True`, and the lid panel taking the roof from 3.20 mm to 1.76 mm of remaining wall.

### 5.3 The scores

Both from `review_step()` on the re-imported STEP, role `enclosure`, no config, no waivers.

| Metric | Weight | Naive | Refined |
| --- | --- | --- | --- |
| `edge_break_coverage` | 0.21 | 0.0 `absent_defect` | 87.0 |
| `face_composition` | 0.19 | 4.8 | 91.7 |
| `feature_composition` | 0.16 | 100.0 | 90.8 |
| `pattern_discipline` | 0.12 | 100.0 | 90.2 |
| `radius_vocabulary` | 0.11 | 0.0 `absent_defect` | 100.0 |
| `symmetry` | 0.07 | 100.0 | 100.0 |
| `sharp_edge_length` | 0.07 | 0.0 | 100.0 |
| `proportion` | 0.07 | 93.8 | 92.1 |
| **Overall** | | **42.5, band D** | **92.5, band A** |

Two things in that table need saying plainly rather than hiding.

**The naive extrusion scores 42.5, not 0.** Its four lid screws are a genuine constant-pitch family on one centreline, so `feature_composition` and `pattern_discipline` both read 100, and a plain box really is symmetric and well proportioned.
The gate is not measuring "is this good", it is measuring eight specific properties, and a raw box legitimately has three of them outright and a fourth nearly.
What it does not have is any break geometry at all, and the two `absent_defect` zeroes hold 0.32 of the rubric at zero.
For scale, the corpus's plain sharp box - no holes, no cavity, no cutout - scores 15.3, so being a tidy box with a tidy hole pattern is worth roughly 27 points and no more.
Do not read 42.5 as a soft floor: the floor for an unstyled prism is still F, and everything above it here was earned by four screws being on a pitch.

**The refined part scores 92.5, band A, and that is the point of the section.** An earlier revision of this same example scored 67.6, band C, and the document was in the absurd position of presenting a part that failed its own standard as the demonstration of it.
Three things fixed it, and none of them is a trick: the lid columns were built from the roof downwards so they end flush with the seal plane instead of 0.2 mm proud of it, the cavity ceiling and the roof panel got the rib fields their spans need, and the connector aperture stopped being cut with a tool long enough to punch the opposite wall.
Section 5.4 prices each of them.

Read the A honestly.
It means the part clears every bar this module can hold up, on eight measured properties.
It does not mean the part is finished: nothing here can see whether the fin bank is on the face that actually gets the sun, whether the connector is the one the cable loom uses, or whether a service technician can reach the lid screws.

### 5.4 What each move was worth

Built cumulatively on the same geometry, each row is one added move, every number re-measured:

| Step | Score | Delta | Band |
| --- | --- | --- | --- |
| 0. Naive extrusion | 42.5 | | D |
| 1. R12 plan radii, 1.0 mm rim breaks | 53.5 | +11.0 | D |
| 2. Cavity cut and its mouth broken | 53.5 | +0.0 | D |
| 3. Roof and side recessed panels, mouths broken | 58.1 | +4.6 | C |
| 4. Rib fields in all three panels | 55.7 | -2.4 | C |
| 5. Ribs on the cavity ceiling | 62.1 | +6.4 | C |
| 6. PCB standoffs and 12 M4 lid columns, roof to seal plane | 84.6 | +22.5 | B |
| 7. Fin bank | 86.6 | +2.0 | B |
| 8. Connector land, window and emblem | 92.5 | +5.9 | A |

Read this table before you optimise anything.

- **Radii and rim breaks are 11 points for four arguments to `rounded_box`.** There is no excuse for a knife-edged part in this repo.
- **Cutting a cavity is free at best**, even with its mouth broken, because a hollow part exposes a large empty ceiling to the air.
  That is real: an open cavity is a surface a human sees.
- **A rib field on an exterior panel costs 2.4 points and is still right.**
  Ribs add hundreds of millimetres of short crest edge and a stack of narrow floor strips, and the panel they stiffen was already composed by its own mouth.
  Keep them: they are the stiffness the recess removed, and step 5 shows what the same move is worth where it is actually needed.
- **Ribs on the cavity ceiling are worth 6.4 points**, because that ceiling was the single largest empty region on the part - a 41 mm empty circle, 0.64 of its own silhouette scale.
- **Interior features are worth more than everything else combined.**
  Step 6 is +22.5 for four PCB standoffs and for turning twelve lid screw holes into twelve full-height columns that tie the wall to the roof.
  Half of that is composition; the other half is that building the columns downward from the roof removed 415 mm of knife edge and one off-ladder blend, because a column built upward from the seal face stands 0.2 mm proud of it and rings the part with twelve unbroken 37.7 mm circles.
- **The connector land is worth +5.9, not the -5.3 it used to cost.** A connector aperture is still a lone feature of its own diameter and `feature_composition` still charges for it, but a raised land with four patterned screws composes the whole +X face, and the identity mark on its own clear roof land composes what is left of the roof.

### 5.5 What the score still cannot see

The residual weaknesses of this part are all things the report names and none of them is a number:

- `edge_break_coverage` is 87.0, not 100, because 4628 mm of bore and boss rim have no lead-in chamfer.
  On a real part every one of those tapped holes gets one, and it is 4 lines with `counterbore_at`.
- `feature_composition` is 90.8 because the connector window is a family of one.
  That is correct and it is not fixable: the part needs one connector.
- Nothing in the review knows that the fin bank is on the -X end.
  Whether that is the shaded end or the sunny one is an engineering decision the render cannot see either.

### 5.6 When the metric is wrong, waive it in writing

A waiver moves a metric to `not_required` and renormalises it out of the score.
That is a real power - waiving a metric a part scores badly on RAISES its score - so every waiver needs a written reason, `lib/evaluate.py` errors the spec if one is missing, and no more than 0.25 of the rubric may be excused this way in total:

```json
"design": {
  "role": "enclosure",
  "min_score": 70,
  "waivers": {
    "symmetry": "handed part - the mirrored variant is a separate release"
  }
}
```

Waive a metric when the part's function contradicts it, not when the number is inconvenient.
If the right answer is a different rubric rather than a waiver, change the `role` and say why - see section 2.1.
And if a metric reports `error` rather than a low score, do not waive it: an error means the measurement did not happen, it already costs full weight at zero, and the correct response is to find out why.

---

## 6. Kernel-safety execution rules

CadQuery and OCCT fail almost exclusively when a fillet or chamfer is asked for on an edge that a previous boolean created.
`features.Build` enforces the safe order mechanically and raises `BuildOrderError` rather than letting a bad order reach the kernel.

### 6.1 The phase order

```
base -> boolean -> pocket -> rib -> hole -> break
```

| Phase | What belongs here | Why here |
| --- | --- | --- |
| `base` | Each primitive as a lone simple solid with plan radii and rim breaks already baked in | Its edges are still the ones the modeller made, so breaks are safe here and only here |
| `boolean` | Unions and cuts between primitives | Every edge created from here on is a boolean edge: fragile to select, fragile to fillet |
| `pocket` | Recesses and lightening pockets, wall guards | Rounded pocket corners come from the cutter's own 2D profile |
| `rib` | Ribs, fins, bosses, standoffs unioned back in | Ribs go in after the pocket exists so they can be clipped to its boundary |
| `hole` | Counterbores, taps, apertures | Last material removal, so counterbores land on lands that already exist |
| `break` | Late edge breaks on edges you can name precisely | If a break is wanted on a boolean edge, build it into the profile at `base` instead |

`pocket` and `rib` share a rank, so they may interleave: pocket a face, rib it, pocket the next face, rib that.
Everything else is strictly monotonic.

### 6.2 Why late fillets fail, measured

On the finished 620-face refined part from section 5, re-measured 2026-07-25:

```
s.edges("|Z").fillet(1.0)   ->  Standard_Failure: BRep_API: command not done   (after 1.5 s)
s.faces(">Z").chamfer(0.5)  ->  succeeded, 642 faces                           (0.1 s)
```

The fillet fails because `|Z` now selects a mixture of original prism edges, pocket-mouth edges, boss tangents and fin roots, and OCCT cannot build a consistent fillet chain across them.
A chamfer on a single named face still works, which is why `break` exists as a phase at all, but it is the exception rather than the tool.

Rules that follow:

- Bake plan radii into the 2D profile.
  `rounded_box` and `rounded_prism` do this; a `box(...).edges("|Z").fillet(r)` is only safe on a lone simple solid before any boolean.
- Chamfer a lone simple solid before unioning it, not after.
- To break a mouth or a crest, cut a tool that already carries the chamfer.
  The `break_mouth` helper in section 5.2 is the pattern: a rounded prism, oversized by the chamfer leg, with `bottom_break=c`, sunk `c` below the face.
- Never `.fillet()` a compound of many solids.

### 6.3 Face selectors will lie to you

`">Z"` means the **highest** face, not the big flat top.
Add one boss and `">Z"` silently becomes the boss crown, at a plausible height, so it looks deliberate.
`"+Z"` means the **widest planar face pointing +Z**, which is usually what you want, but it moves too.

Measured example from section 5: after the cavity is cut, `face_plane(solid, "-Z")` returns the cavity **ceiling**, not the outer rim, because the ceiling is the wider -Z-facing planar face.
Building the mouth chamfer against that plane silently machined 0.6 mm off the roof and the wall guard then refused the lid panel with `recessed panel 1.17 mm deep into a 2.60 mm wall`.

The fix is one line: capture the plane while the face is still whole and pass the `cq.Plane` afterwards.

```python
bottom = face_plane(stock, "-Z")     # captured before the cavity exists
...
b.pocket(lambda s: lightening_pocket(s, bottom, ...), "cavity")
```

Every builder that takes a face accepts `">Z"`, `"+Z"`, a `cq.Face` or a `cq.Plane`.
Prefer the captured `cq.Plane` for anything structural, and `pocket.plane` for anything that must land on a pocket floor.

### 6.4 Guards are a feature, not an obstacle

Both of these fired while building the worked example, and both were right:

```
WallGuardError: recessed panel 1.12 mm deep into a 2.50 mm wall leaves 1.38 mm,
                below the 1.60 mm minimum
FeatureError:   tap depth 7.5 does not fit in a 6.0 mm boss
```

The correct response is never to lower `min_wall` or shorten the engagement.
It is to fix the engineering: the wall came from `STYLE.wall("machined-aluminium", span=W)` = 2.5 mm when the real unsupported span is the 160 mm length, which gives 3.2 mm and clears the guard.
The boss was 6 mm tall when M3 needs 6 mm of thread plus lead, so it became 10 mm.

### 6.5 Additive geometry must overlap, not touch

Geometry that is exactly coplanar with a face can fuse into disjoint solids that still pass `isValid()` and then re-import as loose bodies.
`features.EMBED` (0.2 mm) handles this inside the module; anything you build by hand needs the same treatment.

`Build` warns when a step raises the solid count:

```
RuntimeWarning: stage 'fins' left 9 disjoint solids (was 1). Something added is only
touching the part, not overlapping it - it will re-import as a loose body.
```

That warning fired for real when a fin bank was placed with its span running off the edge of the face.
Treat any solid-count warning as a build failure.

### 6.6 Other traps

- Never use `Workplane.val()` for a boolean on a part built by these builders: it returns only the first stack item.
  Use the Workplane-level `.cut()` / `.union()`.
- `wall_at()` returns `None` when it cannot measure, which means unknown, never "thick enough".
  Pass `wall=<mm>` when you know better than the ray.
- Keep `build_stages()` current, or use `Build.stages()`, which is exactly that protocol, so a styling failure bisects with `lib/debug_build.py`.
- `Style` is frozen and shared: copy with `STYLE.tuned(rib_thickness=2.5)`, never mutate.

---

## 7. Render presentation rules

There are two render modes and they are not interchangeable.

### 7.1 Verification renders

For checking geometry, not for showing anyone.

```python
from lib.render_step import render_scene, render_file, section_cut
render_file("part.step")                                  # orthographic, white, axis triad
render_file("part.step", section=("Z", 11.0))             # cut away material above Z=11
```

Orthographic, white background, axis triad, edge overlay, deliberately faceted.
Use `axes=False` for anything a human will look at outside a debug session.

### 7.2 Product renders

For DESIGN.md, reviews and anything the owner sees.

```python
from lib.render_step import render_product_file, render_product_scene
render_product_file("part.step", views=("hero", "hero_low"), size=1600, material="anodised")
```

or from the shell:

```
uv run python -m lib.render_step part.step --product --material anodised --views hero,hero_low --size 1600
```

Defaults that are already correct: PBR with image-based lighting, a three-point studio rig, SSAO, FXAA, 2x supersampling, a studio sweep backdrop and a 16 degree long-lens perspective.
Product output goes to a `references/product/` directory beside the STEP file and verification output to `references/views/` beside it, so a hero render can never overwrite a verification view.
Rendering a promoted artifact therefore writes to `parts/custom/<part>/exports/references/product/`; pass `out_dir=` (or `-o`) when you want it somewhere else.

| Flag | Values | Notes |
| --- | --- | --- |
| `--material` | `anodised`, `anodised_light`, `machined`, `cast`, `gasket`, `connector`, `fastener`, `glass`, `reference` | R14: body anodised, contrast only on gaskets and connectors |
| `--background` | `dark`, `light` | `dark` is the default and hides the tangent hairline best |
| `--views` | `hero`, `hero_left`, `hero_rear`, `hero_high`, `hero_low`, plus all verification views | `hero` alone is the default |
| `--size` | width in px | In product mode `size` is the image **width**, height is `size / aspect` at 4:3 |
| `--shading` | `ssao`, `shadows`, `both`, `none` | `ssao` is the default and the right choice |
| `--no-ground` | | Only then do `Backdrop.bottom`/`top` show |
| `--supersample` | N | 2 by default |

Shadows are off by default deliberately.
`vtkShadowMapPass` works on this build but paints a straight-edged dark band across the curved sweep at every resolution and key elevation tried, while SSAO alone delivers the contact shading that makes refinement legible.

### 7.3 What to publish

- One `hero` view per part in DESIGN.md, plus `hero_low` if the underside carries the interesting geometry.
- Verification views stay in `references/views/` and out of design discussions.
- Translucency only in fit and engineering views, never in a product shot.

---

## 8. Anti-patterns

These are the specific things that make output read as a first draft.
Each one has a fix in this document.

| Anti-pattern | Why it reads as unfinished | Fix |
| --- | --- | --- |
| Knife-edged extruded prism | No manufactured part looks like this; the eye reads a solid model, not a part | R1, `rounded_box` with `top_break` and `bottom_break` |
| Blank slab face | A large featureless plane has no scale and no purpose | R3, `recessed_panel` then `rib_field` - and note that three scattered holes do not fix it, because the empty region between them is still large |
| Unbroken pocket mouth | A recess whose rim is a knife edge is not more refined than no recess at all | R2, the `break_mouth` pattern |
| Scattered fasteners | Holes placed where they fit rather than on a rhythm | R4, `bolt_pattern` and check `in_band` |
| Counterbore on a curve or a rib | Crescent seat, no bearing surface for the head | R5, build the land first |
| Butt-jointed cylinder on a prism | The transition is where the eye goes and where the stress is | R7, `step_shoulder` or `blend_transition` |
| Connector punched through a textured wall | Reads as an afterthought, and it is not sealable | R8, `connector_land` |
| Arbitrary one-off radii | R7.3 next to R6 next to R9 reads as noise even when nobody can name why | R13, the ladder, at most 4 distinct sizes |
| Decoration with no function | Ribs that stiffen nothing, fins that cool nothing, a chevron on a solid billet | R6, quote the builder's measured number |
| Symmetric-looking but not symmetric | Ten holes at 40 mm and one at 43 mm; a mark 2 mm off centre | R4 and R11; `pattern_discipline` and `symmetry` both catch it |
| Holes aligned only in projection | Two rows that share a coordinate on paper but sit on different faces at different depths | R4; `feature_composition` keys families by axis DIRECTION first, so they never join |
| Every edge blended at one huge radius | A soap bar. It maxes edge coverage, sharp length and vocabulary in a single `fillet()` call | `face_composition` and `feature_composition` see straight through it: the corpus's soap bar scores 59.8 and cannot reach 70 |
| Decorative scribe grooves | A slab wrapped in shallow lines to make faces look busy | R3; relief under 1 mm is filtered out entirely, and the corpus's groove-decorated slab scores 17.8 |
| Plan corners faked with facets | Five short chamfers per corner, each crease under the 20 deg sharpness threshold | R1; each facet crease is under the 20 deg sharpness threshold, so it never registers as a break at all, and the corpus's faceted-corner box scores 16.7 |
| Wall thinned by styling | A recess that eats the structural wall | Section 3.5 and the `WallGuardError` guard |
| Interior left as a raw pocket | Real enclosures have standoffs, columns and cable features | Section 5.4 steps 5 and 6, together the largest single move in the table |
| Late `.fillet()` on the finished part | `BRep_API: command not done`, and no clue which edge | Section 6.1, bake it into the profile |
| Emblem on `">Z"` | Lands on whatever boss is currently highest | R11, place it on `pocket.plane` |

---

## 9. Checklist before a part is promoted

This is the **promotion gate**: what has to be true of the finished artifact before it is accepted.
The `cad-part-design` skill carries a longer, numbered *self-critique* rubric covering the same ground plus the design questions no metric can answer (load path, seal, service, render).
Walk the skill's rubric while you are iterating, and this list once, at the end.
Where the two overlap, they say the same thing; where they differ, this file is binding.

1. The `"design"` block in `spec.json` names the **role** the part actually is, and if the role is arguable, `DESIGN.md` says which one was chosen and why.
   The report carries no `role_error`, which would mean the geometry contradicted the claim and the part was re-judged as an `enclosure`.
2. `make design-review FILE="<part>.step" SPEC="<part-dir>/spec.json"` scores **>= 70 (band B)**, and every finding above `low` severity is either fixed or explained in DESIGN.md.
3. The report's `status` is `ok`, not `insufficient`, and its `unmeasured metrics` list is empty.
   A metric in state `error` is not a low score, it is a measurement that did not happen, and it must be understood before the part is promoted.
4. No metric is in state `absent_defect`. Each one is a 0 at full weight and names exactly what is missing.
5. **Every rubric floor is met.** `report["floor_failures"]` is empty and the console ends `rubric floors met: ...`.
   An unmet floor caps the band at `D` and fails at the review's overall severity whatever the mean says, so a part with one is not promotable and no waiver, role or per-metric bar can change that (2.5).
6. `edge_break_coverage >= 60` at minimum, ideally 90, which needs the body fully broken and roughly 45% of the bore rims chamfered too.
   Three different numbers apply to this one metric and they are not alternatives: the **floor** (10, on the body term) is the disqualification line, this **60** is the promotion expectation, and the per-metric `min_score` a part writes into its own `spec.json` is the bar that part chose to be gated on - `parts/_template/` and the exemplar both write 70, `make spec-init` drafts 60.
   Raise your part's own bar to what it actually achieves once it achieves it.
7. No `WallGuardError` was silenced by lowering `min_wall`.
8. No `RuntimeWarning` about disjoint solids anywhere in the build.
9. Every fastener group reports `in_band=True`, or the exception is an interface grid per R9.
10. Every radius and chamfer in the part is a ladder rung, and there are at most four distinct sizes.
11. Any waived metric names the reason in `spec.json`, in the form shown in 5.6, the excused weight totals no more than 0.25 of the rubric, and the reason is the part's function rather than the number's inconvenience.
    The `"design"` block carries neither of the retired keys, `weights` and `style.radius_ladder`; both now error the spec, hard (2.4).
12. `report["config_delta"]["delta"]` is a number you would defend out loud, and `within_cap` is true.
    It is 0.0 for an `enclosure` that waives nothing; anything larger is the part's role and waivers priced in points (2.6).
13. One `hero` product render exists and has been looked at, not just generated.
14. `build_stages()` or `Build.stages()` is current so a future failure bisects.

---

## Appendix: regenerating every number in section 3

The tables above were generated from `lib.features.STYLE`, not typed.
If `Style` changes, regenerate them rather than editing prose:

```python
from lib.features import STYLE, FASTENERS, WALLS, CORD_TABLE

for gov in (20, 30, 40, 60, 80, 100, 120, 160, 200, 260, 320, 400):
    print(gov, STYLE.plan_radius(gov), STYLE.edge_break(gov), STYLE.frame(gov))
for wall in (1.6, 2.0, 2.5, 3.0, 3.2, 4.0, 6.0, 8.0, 10.0):
    print(wall, STYLE.recess(wall), wall - STYLE.recess(wall))
for name, f in FASTENERS.items():
    print(name, f.clearance, f.cbore_dia, f.cbore_depth, f.tap_drill, f.boss_dia,
          f.min_edge, f.pitch_band, STYLE.pitch(name), STYLE.edge_inset(name),
          f.min_tap_depth)
for name, w in WALLS.items():
    print(name, w.minimum, w.nominal, w.per_span, w.for_span(80), w.for_span(160))
```

The O-ring, louver and fin numbers in 3.7 to 3.9 are **measurements**, not table lookups.
Regenerate them by calling `oring_groove()`, `louver_bank()` and `fin_bank()` and reading `squeeze_pct`, `fill_pct`, `free_area_mm2` and `added_area_mm2` off the returned records.
