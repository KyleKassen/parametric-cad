# Traps

Failure modes that cost the most time here.
Everything marked **measured** was reproduced on this machine while writing this skill; everything marked **documented** comes from the module that owns the behaviour.

## 1. A late chamfer over boolean-built geometry fails, and it fails cleanly (measured, 2026-07-25)

**Correction.** An earlier version of this file said this operation kills the interpreter with SIGSEGV and exit 139.
That is wrong, and it was wrong in a way that sends agents chasing ghosts - hunting for a crash that never comes instead of reading the exception they actually got.
Reproduced from a clean script on this machine: it raises a normal, catchable exception, prints a full traceback and the process exits 0.

The script builds the enclosure from the worked example - `rounded_box` -> cavity -> recessed panel -> chevron `rib_field` -> `connector_land` -> counterbores, 227 faces, 1 solid - then runs `s.faces(">Z").edges().chamfer(0.6)` in the `break` phase:

```
CHAMFER RAISED: Standard_Failure: BRep_API: command not done
Traceback (most recent call last):
  ...
  File ".../cadquery/occ_impl/shapes.py", line 3768, in chamfer
    return self.__class__(chamfer_builder.Shape())
OCP.OCP.Standard.Standard_Failure: BRep_API: command not done
reached the end of the script normally
EXIT=0
```

Three further things were checked, because the old claim implied all three:

- **Without the rib field it fails identically.** The old text said the same chamfer succeeded on the same part minus the ribs and was worth points.
  It is not the ribs.
  The same part built with `with_ribs=False` (123 faces) raises the same `Standard_Failure`.
- **A STEP round trip does not change the answer.** Export, re-import, chamfer again: same exception.
- **Nothing in this repo currently reproduces a segfault at all.** A per-edge fillet sweep over a union of five rotated lumps - the one operation another author reported as exit 139 - ran all 311 edges to completion: 180 filleted, 131 raised `Standard_Failure: There are no suitable edges for chamfer or fillet`, exit 0.

What actually distinguishes success from failure is the **selector**, not the ribs.
On the 620-face refined part from `DESIGN_LANGUAGE.md` section 5, re-measured 2026-07-25:

```
s.edges("|Z").fillet(1.0)          -> Standard_Failure: BRep_API: command not done  (1.5 s)
s.faces(">Z").chamfer(0.5)         -> OK, 642 faces                                 (0.1 s)
s.faces(">Z").edges().chamfer(0.6) -> Standard_Failure: BRep_API: command not done  (0.2 s)
```

`|Z` selects a mixture of original prism edges, pocket-mouth edges, boss tangents and fin roots, and OCCT cannot build a consistent chain across them.
Chamfering the FACE still works; chamfering that same face's EDGES no longer does, and it did on the earlier, simpler revision of this part.
The margin is thinner than it looks, and it narrows as a part gains features - which is the whole argument for baking breaks into the profile rather than adding them at the end.

Rules that follow, unchanged by the correction:

- Put every radius and rim break you can into the base profile (`rounded_box`, `rounded_prism`, `step_shoulder`, `base_flange`), where the solid is still simple.
- A `break`-phase chamfer is for edges no boolean created, and it must be tried on the simplest region that needs it - never a blanket sweep across a face whose edges came from four different booleans.
- **Catch it.** Because it is an ordinary exception, a `break`-phase attempt can be wrapped and fallen back on.
  That is not true of a crash, which is why the difference matters.
- If a run ever does die with no output, do not re-run it hoping for a traceback.
  Go straight to `make debug-build PART=...`, which localises the failure to the last good stage.

## 2. `">Z"` is not "the top face" (measured)

`">Z"` selects the *highest* face. `"+Z"` selects the *widest planar face pointing that way*.

```
plain box       >Z origin: (0.0, 0.0, 40.0)
box + one boss  >Z origin: (0.0, 0.0, 50.0)     <- now the boss crown
box + one boss  +Z origin: (0.0, 0.0, 40.0)     <- still the main surface
```

The failure is silent and plausible: the panel, the bolt pattern or the emblem lands on a 10 mm boss at a believable height and everything still builds.
Use `"+Z"` / `"-Y"` for anything that must land on the main surface.
Both forms, plus a `cq.Face` and a `cq.Plane`, are accepted everywhere `lib/features.py` takes a face.

## 3. The wall guard measures; do not argue with it (measured)

```
WallGuardError: lightening pocket 41.00 mm deep into a 4.00 mm wall leaves -37.00 mm,
below the 1.60 mm minimum - reduce depth, thicken the wall, or lower min_wall deliberately
```

That error came from passing `wall=4.0` to a pocket that was cutting the *cavity* of a 45 mm tall box.
`wall=` does not mean "the wall of this enclosure" - it means "the material under this pocket, which I am telling you because the ray cannot".
Dropping the argument let `wall_at()` measure the real 45 mm and the cut succeeded.

`wall_at()` returning `None` means unmeasurable, never "thick enough".
Treat an override as what it is: switching off a safety check.

## 4. Counterbores must land on a flat land, and the land has to be wide enough (measured)

A perimeter M4 pattern at the recommended inset ate through a recessed panel's rim:

```
frame width            8.0 mm   (STYLE.frame(140, 100))
bolt inset             9.0 mm   (STYLE.edge_inset("M4"))
M4 counterbore dia     8.0 mm
counterbore outer edge 13.0 mm from the part edge   ->  5 mm past the frame
```

The design score barely noticed (`pattern_discipline` 91.6) because the holes really were on a constant pitch and a constant inset.
The hero render showed it instantly: crescent-shaped screw seats chewing into the panel boundary.

The fix is not to move the screws inboard - that would drop below the M4 minimum edge distance.
Size the frame from the fastener instead:

```python
frame = STYLE.edge_inset("M4") + STYLE.fastener("M4").cbore_dia / 2 + margin   # 14 mm here
panel = b.pocket(lambda s: recessed_panel(s, "+Z", wall=wall, frame=frame), "top_panel")
```

The counterbores then sit clean on the frame - and **the score went down**, because the wider frame left more unbroken pocket-mouth edge (`sharp_edge_length` 67.1 -> 39.1).
Re-measured against the current gate the same two versions read 61.7 and 59.8.
Do not undo a fix because a number fell.
The right response is to break the mouths, which is trap 5 and is worth far more than either move: the same part with `break_mouth` on every pocket scores 76.7.

## 5. Rib fields used to collapse `edge_break_coverage`. They no longer do (measured)

**Corrected.** Under the previous gate every millimetre of rib crest was weighed directly against the part silhouette, so a rib field cost 7.4 points on the `DESIGN_LANGUAGE.md` worked example and this file recommended writing the loss up as a trade.
The edge metric now runs two populations: the BODY silhouette a human reads carries 0.85, and a SECONDARY population - bore and boss rims, plus detail edges where both sides are narrow feature strips such as a rib crest, a fin root or a louver blade - carries 0.15.
Leaving detail raw still costs; it can no longer swamp the thing the eye reads.

Same enclosure, same panels, ribs on and off, `DESIGN_LANGUAGE.md` section 5 geometry, re-measured 2026-07-25:

| | edge_break_coverage | overall |
|---|---|---|
| three recessed panels, mouths broken, no ribs | 100.0 | 58.1 |
| the same, plus a parallel rib field in each | 88.9 | 55.7 |

2.4 points, not 7.4 - and the whole of it is the secondary population, because the body silhouette stays fully broken.
Where the ribs are actually needed the sign flips: the same field on the cavity CEILING, which is the largest empty region on that part, is worth **+6.4**.
The corpus's refinement ladder moves 53.9 to 59.9 across its own panels-plus-ribs step, and that ordering is asserted as a contract (`ladder_monotonic`) so it cannot silently regress again.

Ribs are right when they are structural.
What is wrong is adding a rib field to chase a number - and note that under the reworked gate a rib field bought purely for decoration scores *worse*, because `feature_composition` scores the regularity of feature centres and an arbitrary lattice has none.

## 6. Coplanar additive geometry can fuse into disjoint solids (documented)

A pad placed exactly on a face can produce two bodies that still pass `isValid()` and re-import as loose solids.
`lib/features.py` sinks additive features `EMBED = 0.2` mm below the face for exactly this reason; anything you build by hand needs the same treatment.
`Build` warns with a `RuntimeWarning` when a step raises the solid count, and `spec.json` `"solid_count"` catches it at the gate.
A single coplanar union tried while writing this fused cleanly, so treat this as a hazard that shows up under conditions you cannot predict, not one you can test your way out of.

## 7. `Workplane.val()` returns only the first stack item (documented)

Never use it for a boolean on a part built by these builders.
Use the `Workplane`-level `.cut()` / `.union()`, or `lib.features._shape()`.

## 8. `text_mark` fails silently by design (documented)

On a missing font, a failed boolean or a failed weld it warns and returns the part **unchanged**, so one machine's missing font cannot destroy an enclosure.
Pass `strict=True` wherever the mark is contractual, and check the render.

## 9. The design gate is advisory until a part opts in (measured)

`lib/evaluate.py` runs `lib/design_review.py` on every part with a default bar of 70 under the `enclosure` rubric, at **soft** severity, so a low score lands in `report["warnings"]` and still exits 0.
Run on a raw box with four holes and no `spec.json` at all:

```
[FAIL ] design_review.floor.edge_break_coverage: rubric floor unmet: edge_break_coverage
        absent where the geometry requires it, which is the defect this floor names ... (soft)
[FAIL ] design_review.floor.sharp_edge_length: rubric floor unmet: sharp_edge_length
        scored 8.5 against a floor of 25 ... (soft)
[FAIL ] design_review.score: refinement score 43.1 (D - draft - needs a refinement pass)
        as an enclosure, threshold 70 -- rubric floor unmet (edge_break_coverage,
        sharp_edge_length), band capped at D (soft)
[FAIL ] design_review.edge_break_coverage: absent where the geometry requires it:
        0.0% of convex body edge length is broken (0 of 1140 mm), body term 0.0;
        0% of bore/boss rim length is broken (soft)
[FAIL ] design_review.radius_vocabulary: absent where the geometry requires it:
        no fillet or chamfer geometry anywhere - every corner is a knife edge (soft)
overall: PASS -- promoted to .../exports/demo_naive_v1.step
$ echo $?
0
```

(Re-run 2026-07-26; the detail strings are elided for width.)
The last two lines are metrics in state `absent_defect`, which always emits a FAIL naming the evidence and scores 0 at full weight.
They are not waivable and they are not "not applicable" - they are a list of what the part is missing.
The first three are the floors, and note what they do at **soft** severity: the band is capped at `D` and `design_review.score` fails, yet `overall` is still PASS and the exit code is still 0.
An advisory review reports honestly and does not break the build; it just cannot print a passing band.

Writing `"design": {"min_score": 70}` into `spec.json` is what makes it gate - presence of `min_score` is the opt-in, and severity then defaults to `hard` **unless you also write `"severity"`**, which is the one thing that trips people up here.
`make spec-init` drafts the block for you with `"severity": "soft"` written explicitly, `"role": "enclosure"` and `edge_break_coverage` already called out, so a drafted block does *not* gate until you change that one word.
A finished part should opt in and set the role it actually is.

**Two things are NOT advisory, whatever the severity.**
A rejected config key - `design.weights` or `design.style.radius_ladder`, both retired - is a HARD spec ERROR out of `lib/evaluate.py`, because a part that never set a `min_score` would otherwise be told about a dead key in a soft voice.
And an unmet **rubric floor** caps the reported band at `D` and fails `design_review.score` at every severity, so an advisory review can still never print a passing band.
What severity does control is whether the `design_review.floor.<id>` check breaks the build: it is emitted at the review's *overall* severity, so a part that predates the gate warns and a part that opted in fails hard.
`metric_severity` never reaches a floor at all.

## 10. A drafted spec proves nothing until you edit it (measured)

`make spec-init` writes every entry with `"unresolved": true`, and a hard unresolved value **errors** the evaluation:

```
overall: ERROR -- NOT promoted        # exit 2
```

That is deliberate.
A spec transcribed from the model would only prove the model equals itself.
Delete the entries that are not requirements, resolve the ones that are, and keep the rest in the top-level `"unresolved"` list where they are visible.

## 11. `make design-review` needs the part's own config to print the gate's number (measured)

The recipe used to be `python -m lib.design_review "$(FILE)" $(if $(MIN),--min-score $(MIN))` with no way to pass a role, so every run judged under the `enclosure` rubric whatever the part's `spec.json` said.
It now passes four variables through:

```bash
make design-review FILE="<part>.step" SPEC="parts/custom/<name>/spec.json"   # exactly what the gate uses
make design-review FILE="<part>.step" ROLE=cover MIN=70 JSON=review.json     # or spell it out
```

`SPEC` feeds the whole `"design"` block - role, bar, per-metric gates and waivers - so the console number is the gate's number.
`ROLE` and `MIN` are applied after `SPEC`, so they override it for a what-if.
Verified exit codes: the module returns 0 at or above the bar, 1 below it, 2 when the review could not run at all; `make` wraps that and exits 2 on any recipe failure, so test the module directly when you need the distinction.
`make views` and `make product-render` take `VIEWS`, `SIZE` and `OUT` the same way, and `make views` also takes `SECTION=Z:11`.

## 12. A role is a claim the geometry has to support (measured)

A role can excuse a metric, and every role's weights sum to 1.00 so it cannot lighten the total bar - but it can still move a part several points, and picking one to escape scrutiny is one word in a JSON file.

Every role now carries a geometric guard, checked BEFORE the rubric is honoured.
A claim the measured B-rep contradicts puts a `role_error` in the report and the part is re-judged under `enclosure`.

| Role | The guard |
|---|---|
| `enclosure` | none - it claims nothing, and it is the fallback |
| `cover`, `plate` | thinnest bbox dimension <= 0.25 of the longest |
| `bracket` | at most 20% of face area faces an enclosed void |
| `sheet` | derived stock thickness <= 10% of the longest dimension AND at most 15% of face area facing an enclosed void |
| `structural` | longest bbox dimension >= 4.0 x the shortest |

The refined enclosure from `DESIGN_LANGUAGE.md` section 5 (169 x 102 x 42 mm), one solid, unchanged, reviewed six ways:

```
enclosure    92.5 A      <- what it is
cover        94.2 A
plate        93.3 A
structural   94.8 A
bracket      refused -> re-judged as enclosure, 92.5
sheet        refused -> re-judged as enclosure, 92.5
```

The exemplar `parts/custom/reference_mast_node_enclosure` is boxier, and every one of the five lighter roles is refused on it: 83.1 whatever you claim.
The guards bound the lie, they do not remove it.
That part slips past the `cover`, `plate` and `structural` guards by a hair - 0.248 against a 0.25 limit, 4.02 against a 4.0 limit - and collects up to 2.3 points for it.

Declare what the part IS.
If it is arguable, pick the stricter reading and write the argument into `DESIGN.md`.

And whatever you declare, the report now prices it: `report["config_delta"]` re-scores the same measurements under the default `enclosure` rubric with nothing excused and publishes the difference, with `knobs` naming the role and every waiver that moved it.
A part that declares `enclosure` and waives nothing reports exactly 0.0.
Past `MAX_CONFIG_DELTA` the delta is itself a config ERROR, on the same surface a retired key lands on.

## 13. A floor is not a weight, and it is not a target (measured)

`edge_break_coverage` and `sharp_edge_length` each carry a hard minimum in `lib.design_review.RUBRIC_FLOORS`, checked OUTSIDE the weighted mean.
Every other lever in the review is a contribution to a mean, and a mean is exactly what an agent optimising against a gate learns to arbitrage: pick the role whose column is lightest where you are weak, spend one waiver, let the other metrics carry you.
The measured worst part that could still clear a hard 70 gate was a flat 220 x 150 x 9 slab with three pockets and ten border holes on which not one edge is broken anywhere, and it reached 85.6/B.

So a floor refuses every one of those moves rather than out-weighing them:

| Attempted escape | What happens |
|---|---|
| `waivers.edge_break_coverage` | config ERROR - a floored metric cannot be waived |
| `metrics.edge_break_coverage.enabled: false` | config ERROR - the same thing under another name |
| `metrics.edge_break_coverage.min_score: 5` | config ERROR - a spec may RAISE a floor, never lower one |
| a lighter `role` | no effect; the floor applies wherever the role's rubric uses the metric, and the role's own claim is guarded against the geometry first |
| the metric reporting `absent_defect` | FAILS the floor - that is the defect the floor is named after |
| the metric reporting `error` | FAILS the floor - breaking the measurement is never cheaper than passing it |
| chamfering only the bore mouths | does not reach the `edge_break_coverage` floor at all: it is held against the metric's BODY term, not its `0.85 body + 0.15 rim` composite |

That last row is the interesting one, and it is a correction to how the floor used to work.
Flooring the composite floored the wrong number: the rim term alone is worth 15.0 against a floor of 10.0, so a part on which not one body corner was broken cleared the floor named after exactly that defect simply by deburring its bores.
`Floor` therefore carries a `key`, and `edge_break_coverage`'s reads `body_score`.
Breaking bore rims is still worth real points in the mean - it is 0.15 of the metric - it just cannot stand in for breaking the part.

The level is not a target either.
10 on `edge_break_coverage` is far below the 60-90 a promotable part should reach (`DESIGN_LANGUAGE.md` section 9); it is the line below which the metric has stopped describing a design and started describing the absence of one.
