---
name: cad-part-design
description: Design, model or refine a mechanical part in this CadQuery repo - a housing, enclosure, bracket, mount, plate, pod, cover, flange or pedestal. Use whenever a part under parts/ is being created, restyled, sculpted, made to fit a vendor STEP, or pushed to a professional industrial-design standard, and whenever someone asks for a design review, a refinement pass or a product render.
---

# Designing a refined part in this repo

A part is not done when it builds.
It is done when the exported STEP passes the gate, the design review scores it, the hero render looks like a product photograph, and the intent is written down.
This skill is the loop that gets there.

The failure this skill exists to prevent: an agent reads the requirement, writes a `.box()`, drills some holes, sees `make eval` pass, and reports success.
That part is mechanically sound and visually unfinished, and it costs the owner a manual rework pass every time.

## Before you write any geometry

Read, in this order:

1. `DESIGN_LANGUAGE.md` - the binding standard for anything anyone will see.
2. `references/features-catalog.md` in this skill - what `lib/features.py` already builds for you, with real signatures. Almost everything you are about to hand-roll is in there.
3. `references/traps.md` in this skill - the kernel and API failures that cost the most time, each one measured rather than guessed.
4. The exemplars: `parts/custom/reference_mast_node_enclosure/` is a real part built to this standard - read its `model.py` for the phase order, its `spec.json` for an acceptance contract that gates hard on refinement, and its `DESIGN.md` for how a score, a role, the rubric floors, the `config_delta` and the findings that were not fixed get recorded.
   It measures 83.1, band B, as the `enclosure` it is, and its `spec.json` gates on `"min_score": 80` - 3.1 points of margin, deliberately, because the previous bar of 83 was set when the part scored 86.6 under the nine-metric gate and survived the rubric rework by 0.12 points.
   Its `DESIGN.md` records 83.1 throughout and states that 86.6 must not be quoted.
   **Copy that document's structure when you record your own review.**
   `parts/_template/` is the second exemplar and the one you will actually start from: `make new-part` copies its `model.py`, `params.json` and `spec.json` verbatim, and what it copies is a working cast enclosure, a 150 x 90 x 34 mm body measuring 153 mm over its connector land, that scores 85.9, band B, as the `enclosure` its spec declares.
   Read it before you delete it.
   `parts/custom/am59_mast_head/DESIGN.md` shows the depth a design brief reaches, and `parts/custom/oz510-dual-housing/REQUIREMENTS.md` a dimension-free family spec; both predate the design system, so neither records a score.
5. `tests/design_corpus.py` if you want to see what the gate rewards and what it refuses to reward.
   It builds twenty-two synthetic parts - a five-rung refinement ladder whose top rung doubles as the `enclosure` reference, twelve deliberately gamed parts, and five more good parts covering the other five roles - plus four real ones, and asserts nine contracts over their **ranking** rather than their absolute scores.
   `uv run python -m tests.design_corpus` prints the table and the contract result.

## The loop

### 1. Gather ground truth

Never hand-measure and never trust a filename.

```bash
make analyze FILE="parts/vendor/<vendor>/<part>.STEP"          # exact bbox, solids, holes/bosses with true axes
make compare A="parts/vendor/a.STEP" B="parts/vendor/b.STEP"   # identity vs mirror - run it on every pair
make views   FILE="parts/vendor/<vendor>/<part>.STEP"          # 6-view + iso with an axis triad, then LOOK
```

`make compare` on the OZ510 receiver against the OZ510 transmitter reports identity 82.4%, mirror_x 71.9%, verdict "similar but NOT identical".
Two files with the same envelope, the same feature count and mirrored I/O.
A bbox comparison cannot see that; feature positions can.

Datasheets in `datasheets/` are the authority for every number that is not measured off a solid.
When a cavity must fit a vendor part, derive it from that part's own B-rep with `lib.housing.silhouette()` / `keepout_prism()` rather than typing dimensions - then handedness cannot be modelled wrong.

### 2. Write the design intent before the geometry

Create `parts/custom/<name>/DESIGN.md` and write it before `model.py` exists.
`PART_TEMPLATE.md` in the repo root is the brief template.
It must state:

- **Function** - what the part does, what it mates to, where it sits in the assembly.
- **Interfaces** - every mating pattern, datum, connector, cable exit, keep-out, with its source (datasheet page, vendor STEP, surveyed).
- **Loads** - static, dynamic, wind, shock, and the load path through the part.
- **Thermal** - watts in, the path out, the ambient, whether the airflow is wet or dry.
- **Environment and sealing** - IP target, the seal plane, drainage, the drip path.
- **Service** - what has to come out, how often, and what must not be disturbed to do it.
- **Materials and process** - and therefore the wall ladder (`Style.wall(process, span)`).
- **Deliberate ID choices** - the massing, the parting line, where the recessed panels go, where the one emblem goes.
- **Unresolved** - every number you do not have. Unresolved is a first-class state here; `spec.json` can hold a hard unresolved flag that errors the gate until it is settled.

An open question written down is worth more than a plausible number invented.

### 3. Architect, do not extrude

Decide before any code:

- the massing and the silhouette, including which face is the "front";
- the load path, and which members are structural (those get sculpted sections, tapers, ribs and lightening pockets - not slabs);
- the parting lines and the seal plane, and which side carries the groove;
- the service strategy, and therefore which panel is removable;
- the fastener grid: one size, one pitch, one edge inset, symmetric about the centrelines;
- where the connectors land, and on what raised or recessed flat.

If a decision is arbitrary, take it from the ladder rather than inventing a number: `Style.plan_radius`, `Style.edge_break`, `Style.wall`, `Style.pitch`, `Style.edge_inset`, `Style.frame`, `Style.recess`.
That is what makes a repo of parts read as one product family.

#### Decide the design ROLE here, before the geometry

The role goes in `spec.json`'s `"design"` block and it decides which of the eight review metrics apply, how they are weighted, and where the thresholds sit.
Decide it from the function you just wrote down, not from the score you get later.

| Role | Choose it when the part | Not required | The guard the geometry must pass |
|---|---|---|---|
| `enclosure` | is a housing: it contains something, and every exterior face is a product surface | nothing - all eight apply | none; it claims nothing |
| `cover` | is a lid or a door: thin by function, with a flat sealing face by function | `proportion` | thinnest bbox dimension <= 0.25 of the longest |
| `plate` | is an interface: thin by function, and its hole pattern IS the part | `proportion` | thinnest bbox dimension <= 0.25 of the longest |
| `bracket` | is machined from solid, so every free edge genuinely can be broken | `proportion` | at most 20% of face area faces an enclosed void |
| `sheet` | is formed from flat stock, so its blanked perimeter cannot carry a chamfer | `proportion`, `sharp_edge_length` | stock thickness <= 10% of the longest dimension, and at most 15% of face area facing an enclosed void |
| `structural` | is a sculpted load-carrying member, legitimately long | nothing | longest bbox dimension >= 4.0 x the shortest |

Absent means `enclosure`, which is deliberately the strictest, so claiming anything else is always a deliberate act.

**Picking a role to escape scrutiny is dishonest.**
Say that to yourself before you type it, because it is one word in a JSON file and it is invisible in the resulting number.

Each guard is checked BEFORE its rubric is honoured, and a claim the geometry contradicts puts a `role_error` in the report and re-judges the part as an `enclosure`.
That bounds the lie; it does not remove it.
Measured on the refined enclosure in `DESIGN_LANGUAGE.md` section 5: 92.5 as the `enclosure` it is, `bracket` and `sheet` refused outright, and `cover` 94.2 / `plate` 93.3 / `structural` 94.8 honoured because a 169 x 102 x 42 mm box scrapes past a 0.25 thinness limit at 0.248 and a 4.0 aspect limit at 4.02.
On the boxier exemplar every one of the five lighter roles is refused.
If a part could honestly be read two ways, pick the stricter one and write the reasoning into `DESIGN.md`.
A role you have to argue for in writing is a role you can defend in review; a role you picked because it scored better is a lie about what the part is.

### 4. Build with lib/features.py, in phase order

`lib.features.Build` enforces the only ordering the kernel tolerates:

```
base -> boolean -> pocket -> rib -> hole -> break
```

```python
from lib.features import (STYLE, Build, bolt_pattern, connector_land, face_plane,
                          fastener_holes, lightening_pocket, recessed_panel,
                          rib_field, rounded_box)

def break_mouth(solid, pocket, c=0.6):
    """Chamfer a pocket mouth by CUTTING a tool that ALREADY carries the break."""
    p = pocket.plane          # sits on the pocket FLOOR: lift it back to the face
    sunk = cq.Plane(origin=p.origin + p.zDir * (pocket.depth - c), xDir=p.xDir, normal=p.zDir)
    tool = rounded_box(pocket.length + 2*c, pocket.width + 2*c, 40.0, pocket.radius + c,
                       bottom_break=c, plane=sunk)
    return solid.cut(tool)

b = Build(rounded_box(L, W, H, STYLE.plan_radius(L, W),
                      top_break=STYLE.edge_break(L, wall)), "stock")

cav = b.pocket(lambda s: lightening_pocket(s, "-Z", size=(L - 2*wall, W - 2*wall),
                                           depth=H - wall), "cavity")
b.pocket(lambda s: break_mouth(s, cav), "cavity_mouth")

panel = b.pocket(lambda s: recessed_panel(s, "+Z", wall=wall), "top_panel")
b.pocket(lambda s: break_mouth(s, panel), "top_panel_mouth")

b.rib(lambda s: s.union(rib_field(panel, "chevron", height=1.2).solid), "top_ribs")
b.hole(lambda s: connector_land(s, "+Y", length=34, width=26, aperture=(20, 14)).solid, "land")

top = face_plane(b.result, "+Z")
pat = bolt_pattern("perimeter", length=L, width=W, fastener="M4",
                   inset=STYLE.edge_inset("M4"), plane=top)
b.hole(lambda s: fastener_holes(s, pat.points, plane=top, fastener="M4", kind="cbore"), "screws")

part = b.result
```

That snippet was run as written on 2026-07-25 at `L, W, H, wall = 140, 100, 45, 3.2`: 1 solid, 285 faces, `isValid()` True, and it scores **71.2, band B** (`edge_break_coverage` 86.6, `sharp_edge_length` 95.5).
It clears the gate on its first build, and the reason is the two `break_mouth` calls - without them the same geometry sits in the high 50s.
`break_mouth` takes the `Pocket`, not a captured face plane, because `Pocket.plane` already knows where the pocket is - which is also the only version that works when the panel is off-centre.
Where you do need a face plane, as with `top` for the bolt pattern here, read it with `"+Z"` rather than `">Z"`: `">Z"` means *highest*, so one boss silently redirects it (trap 2).

Then wire the two required entry points:

```python
def create_part(params=None):    return _build(params).result
def build_stages(params=None):   yield from _build(params).stages()
```

`build_stages()` is not optional.
It is what `make debug-build` bisects when the kernel fails, and it costs one line when the part is built with `Build`.

Use `"+Z"` / `"-Y"` (the widest planar face pointing that way) for anything that must land on a main surface.
`">Z"` means *highest*, so one boss silently redirects it.

### 5. Evaluate

```bash
make eval PART="parts/custom/<name>"
```

Then read `exports/attempts/<attempt-id>/report.json`, not the console tail.
Fix, rebuild, repeat until exit 0.

If the build dies inside the kernel:

```bash
make debug-build PART="parts/custom/<name>"     # localises the failure to one stage
```

A late fillet or chamfer over a boolean-built region is the commonest cause, and it raises `Standard_Failure: BRep_API: command not done` - a normal, catchable exception with a traceback.
If the process ever dies with no traceback at all, that is a segfault in OCCT; nothing in this repo currently reproduces one, so treat it as new information and bisect with `make debug-build`.
See `references/traps.md` item 1.

### 6. Look at it - this step is not optional

```bash
make product-render FILE="parts/custom/<name>/exports/<name>_v1.step" VIEWS=hero SIZE=1200
```

Hero renders land in a `references/product/` directory **beside the STEP file**, not in the part directory.
So rendering a promoted artifact under `exports/` writes into `parts/custom/<name>/exports/references/product/`, and verification views land in `.../exports/references/views/` the same way.
A STEP outside `parts/` renders into `renders/`.
`.gitignore` covers `**/exports/references/`, so those PNGs stay out of `git status` like every other derived artifact; the part's own committed `references/` is untouched.
Pass `OUT=` to put them somewhere else.
**Now read the PNG back into context and critique it against `DESIGN_LANGUAGE.md`, item by item.**
Write the critique down in your response.

This step catches what no metric catches.
In the worked example `pattern_discipline` read a respectable 91.6 while the render showed the counterbore mouths chewing through the recessed-panel rim, because an M4 perimeter pattern at the recommended 9.0 mm inset needs 13.0 mm of land and the default frame is 8.0 mm wide.
The score cannot see that.
Worse: fixing it properly, by widening the frame to 14 mm, moved the overall score **down** - 61.7 to 59.8 re-measured against the current gate - because the wider frame left more unbroken pocket-mouth edge.
The render shows the defect instantly and the number actively misleads you about the fix.

Use `VIEWS=hero,hero_left,hero_rear` when the part has a front, `MATERIAL=` to change the finish and `OUT=` to send the PNGs somewhere other than beside the STEP.
To see inside:

```bash
make views FILE="<part>.step" SECTION=Z:11 VIEWS=iso,top
```

### 7. Self-critique against the rubric, then record the score

Walk the rubric below explicitly - write out each line and your verdict.
Then:

```bash
make design-review FILE="parts/custom/<name>/exports/<name>_v1.step" \
                   SPEC="parts/custom/<name>/spec.json" JSON=review.json
```

`SPEC` feeds the part's whole `"design"` block in - role, bar, per-metric gates, waivers - so what prints is exactly the number `make eval` will use.
`ROLE=` and `MIN=` are applied after it, for a what-if:

```bash
make design-review FILE="<part>.step" ROLE=cover MIN=70
```

The module exits 0 at or above the bar, 1 below it, 2 when the review could not run.
`make` wraps that and exits 2 on any recipe failure, so test the module directly when you need the distinction.

Do not reach for a config knob that no longer exists.
`design.weights` and `design.style.radius_ladder` are both retired, and writing either is a **hard** spec ERROR out of `make eval` whatever severity the block declares - the full accepted surface is in `PART_TEMPLATE.md` section 3 and `DESIGN_LANGUAGE.md` section 2.4.
If a part genuinely needs different radii, that is an edit to `lib.features.Style`, which moves every part in the repo together, and not a line in one `spec.json`.

Before you read the score, read the states:

- Any metric in state **`error`** means the measurement did not happen.
  It contributes zero at full weight and is reported as an ERROR check.
  Do not quote the score until you know why, and never waive an error - a waiver hides a broken measurement.
- Any metric in state **`absent_defect`** is a 0 at full weight, and the message names exactly what is missing.
  It is not something to waive, it is something to build.
- Any metric in state **`not_required`** was excused by the role or by a written waiver, and renormalised out.
  Check that you agree with the excuse.
- If the report's `status` is `insufficient`, under 60% of the metric weight could be measured and the number is not a verdict.

Then read the two things that sit OUTSIDE the weighted mean:

- **`report["floors"]` and `report["floor_failures"]`.** `edge_break_coverage` and `sharp_edge_length` each carry a hard minimum from `lib.design_review.RUBRIC_FLOORS` - 10 and 25 today - checked independently of the score.
  A floor names the number it reads, and `edge_break_coverage`'s reads the metric's **body term**, not its composite score: the composite is `0.85 * body + 0.15 * rim`, so the rim term alone is worth 15.0 and a part with no broken body corner used to clear a floor of 10 by deburring its bore mouths.
  Breaking bore rims is worth points, and it is not a substitute for breaking the part.
  A floor cannot be renormalised out, averaged away, waived, disabled, lowered or shifted by a role choice: a waiver or `enabled: false` on a floored metric is a config ERROR, a per-metric `min_score` below the floor is a config ERROR, and `absent_defect` or `error` both FAIL the floor rather than escaping it.
  Only a role exclusion removes one, and every role's claim is guarded against the geometry first.
  **A spec may raise a floor and cannot express lowering one.**
  An unmet floor caps the reported band at `D` at every severity, fails `design_review.score`, and fails `design_review.floor.<id>` at the review's *overall* severity - `metric_severity` never reaches it, because "this metric does not matter to me" is exactly the claim a floor exists to refuse.
  A capped band is why a report can read "score 85.6, band D": the mean is real and it is not the verdict.
- **`report["config_delta"]`.** The same measurements re-scored under the default `enclosure` rubric with nothing excused, and the difference.
  It is 0.0 for a part that declares `enclosure` and waives nothing; anything else is your role and your waivers priced in points, with `knobs` naming them.
  Past `MAX_CONFIG_DELTA` it is itself a config ERROR.
  If your delta is large, the question is whether the role is what the part IS - never which waiver to trim until the number fits.

Iterate on the ranked findings; they name the builder to reach for.
When the part is where it should be, record in `DESIGN.md` (the exemplar's `DESIGN.md` is the model):

- the design-review score, band, **role** and date, and the STEP it was measured on;
- why that role, if the part could plausibly be read as more than one;
- every rubric floor, its required level and the measured margin;
- the `config_delta`, and what bought it;
- every `high` finding you did not fix, with the engineering reason;
- every `absent_defect` and `not_required` metric, and which of the two excused it;
- the `spec.json` `"design"` block you opted into, and why the bar sits where it sits.

A waiver with a reason is respectable. Silence is not.
A waiver is also a real lever - waiving a metric a part scores badly on RAISES the score - so waive on the part's function, never on the number's inconvenience.
And the two metrics where that lever pays most are exactly the two the floors have taken away from you.

## The design review rubric

Walk every line before you call a part done.
Answer each one with the specific geometry, not "yes".
This is the **self-critique** list, for use while you iterate; `DESIGN_LANGUAGE.md` section 9 is the shorter **promotion gate** you walk once at the end, and where the two overlap that file is binding.

What the eight metrics measure, so you know which line each one is behind.
Every one of them measures **organisation**, never the presence of a geometric event: an earlier version counted holes, fillets and faces, and a lumpy pile of overlapping rounded boxes with scattered oversized countersinks therefore beat a textbook sealed cover by 46 points.
Adding a feature is not a way to raise a score; adding a *regular* feature to a *composition* is.

| Metric | Enclosure weight | Floor | The question it asks |
|---|---|---|---|
| `edge_break_coverage` | 0.21 | **10** on its body term | What fraction of the convex silhouette carries a break, and what fraction of the bore rims |
| `face_composition` | 0.19 | - | How big is the largest empty circle left on any exterior face, relative to that face |
| `feature_composition` | 0.16 | - | What fraction of feature centres share a line or a constant pitch with another, and how many features each line has to show for itself |
| `pattern_discipline` | 0.12 | - | Per fastener family: pitch regularity, centreline mirroring, edge-inset consistency |
| `radius_vocabulary` | 0.11 | - | Are the radii and chamfer legs ladder rungs, and how many distinct ones are there |
| `symmetry` | 0.07 | - | How much volume, and how much spatial extent, differs from the best mirror |
| `sharp_edge_length` | 0.07 | **25** | How many bbox diagonals of unbroken convex edge are left |
| `proportion` | 0.07 | - | Is the envelope slab-like or stick-like |

There were nine.
`form_discipline`, a surface budget, was retired on 2026-07-25 because it scored the naive extrusion in `DESIGN_LANGUAGE.md` section 5.1 at 94.0 against the refined part's 85.7.
If you find it named anywhere, that text is stale.

Weights shown are the `enclosure` role's; see the role table above and `DESIGN_LANGUAGE.md` section 2.1 for the rest.
Bands: A >= 88, B >= 70, C >= 55, D >= 38, F below 38.

The **Floor** column is not a second weight, it is a hard minimum checked outside the weighted mean.
A weight can be arbitraged - pick the role whose column is lightest where you are weak, spend a waiver, let the rest carry you - and a floor cannot: it is not a contribution to anything, so it cannot be renormalised out, averaged away, waived, disabled, lowered or moved by a role.
Only a role exclusion removes one, which is why `sheet` is the only rubric with no `sharp_edge_length` floor.
Note that `edge_break_coverage`'s floor is held against its **body term**, not its composite score, so bore-rim chamfers cannot pay for an unbroken body.
An unmet floor caps the reported band at `D` and fails at the review's overall severity whatever the mean says.
Levels and keys live in `lib.design_review.RUBRIC_FLOORS`; full treatment in `DESIGN_LANGUAGE.md` section 2.5, and `config_delta` in 2.6.

**Form**

1. Is every exterior edge broken - plan corners on the ladder, every rim chamfered or stepped, no knife edge anywhere a hand or an eye reaches?
2. Is every large face doing something - a recessed panel with a proud frame, a bolt pattern, a rib field, or exactly one emblem? No blank slabs.
3. Do the fillet radii and chamfer legs sit on the `Style` ladder, or is every corner its own size?
4. Is the part symmetric about its own centrelines unless it is deliberately handed - and if handed, is that stated in `DESIGN.md`?
5. Is there at most one emblem per face, at 1 mm relief or less, centred on a panel?

**Composition**

6. Do the fasteners have a rhythm - one size, constant pitch, constant edge inset, symmetric, counterbored, every one landing on a flat land clear of pocket rims and ribs?
7. Does every prism-to-cylinder transition go through a step ring, a faceted collar or a blend shoulder - never an abrupt butt joint?
8. Does every connector sit on its own raised or recessed flat land with a chamfered boundary and its own screw pattern - never punched through a curved or textured wall?
9. Do base flanges have large corner radii and a chamfered or stepped edge?
10. Are interface and payload plates a regular tapped grid at a published pitch?

**Function**

11. Does every piece of texture earn its place - fins where heat leaves, louvers where air enters, a drip edge over every aperture that faces weather?
12. Is the seal a continuous closed path with real numbers - squeeze 20-30%, fill 75-85% (`ORingGroove` reports both)?
13. Can the serviceable item come out without disassembling structure or breaking the seal plane?
14. Is the minimum wall preserved under every pocket, *measured* through the B-rep rather than assumed? A `wall_at()` of `None` means unknown, never "thick enough".
15. Are structural members sculpted - thick where loaded, thin where not, ribs on the load path, lightening pockets with generous radii?

**Proof**

16. Does the hero render read as a product photograph? If it reads as a CAD screenshot, name why and fix that.
17. Is the design score recorded in `DESIGN.md` with its band, its role, its floors, its `config_delta` and the STEP it was measured on, and is every unfixed `high` finding waived in writing?
18. Is the declared role the one the part actually is, and would you defend that choice to a reviewer who could see the score under every other role?
19. Is every metric either `scored` or excused for a reason you agree with - nothing in `error`, nothing in `absent_defect`, and no `insufficient` overall status?
20. Is `report["floor_failures"]` empty - given that an unmet floor is not a low score to argue about but the statement that the metric has stopped describing a design, and no waiver, role or per-metric bar can move it?
21. Is `report["config_delta"]["delta"]` a number you would defend out loud, and `within_cap` true?
22. Does `make eval` exit 0, with the spec's dimensional checks actually asserting requirements rather than restating the model?

## Worked sequence

The full transcript with real numbers is in `references/worked-example.md`.
The short form:

```bash
make new-part NAME=my_housing                                  # scaffold
# it creates datasheets/, references/, and copies parts/_template/'s params.json,
# spec.json and model.py - a WORKING example enclosure that scores 85.9 as it
# stands. Write DESIGN.md, then replace params.json, then replace the geometry in
# model.py, then make spec.json describe YOUR part.
uv run python parts/custom/my_housing/model.py                 # does it build at all
make debug-build PART="parts/custom/my_housing"                # if it does not
make eval PART="parts/custom/my_housing"                       # the gate + design score
make spec-init PART="parts/custom/my_housing"                  # redraft the contract, then EDIT it
make eval PART="parts/custom/my_housing"                       # again, now against the spec
make product-render FILE="parts/custom/my_housing/exports/my_housing_v1.step"
#   -> read the PNG, critique it against DESIGN_LANGUAGE.md, fix what you see
make design-review FILE="parts/custom/my_housing/exports/my_housing_v1.step" \
                   SPEC="parts/custom/my_housing/spec.json"
#   -> iterate, then record the score, band and role in DESIGN.md
```

Calibration, all measured on this repo on 2026-07-25:

| Reference point | Score | Band |
|---|---|---|
| Plain sharp box, no holes | 15.3 | F |
| Plain sharp box with four tidy holes | 43.1 | D |
| The three pre-design-system parts in the corpus | 22.1, 46.4, 51.5 | F to D |
| One pass of the feature vocabulary on a simple enclosure | 61.7 | C |
| The same part, plus `break_mouth` on every pocket | 76.7 | B |
| `reference_mast_node_enclosure` v1, the exemplar | 83.1 | B |
| `parts/_template/`, what `make new-part` hands you | 85.9 | B |
| `DESIGN_LANGUAGE.md` section 5, the fully worked example | 92.5 | A |
| Best of twelve deliberately gamed parts in the corpus | 59.8 | C |

Those are calibration points, not constants: retuning a metric moves every one of them.
`uv run python -m tests.design_corpus` reprints the corpus rows and re-checks the nine ordering contracts, which are the part that must not move.

Three things that table is trying to tell you.
A raw box with four tidy holes gets 43, because four holes on a constant pitch on one centreline really are a pattern - the gate scores eight specific properties and a raw box legitimately has three of them, but it has no break geometry at all and two metrics report `absent_defect` at 0 for it.
The jump from 61.7 to 76.7 is one helper applied five times: **the single largest lever in this whole skill is breaking pocket mouths.**
And the two top rows are both enclosures with ribbed interiors: past 80, the thing that moves the number is what is INSIDE the cavity and how the big faces are composed, not another chamfer.

## Reference files

- `references/features-catalog.md` - the `lib/features.py` builder catalogue and the `Style` ladders.
- `references/traps.md` - measured failure modes: what a late chamfer over boolean geometry really does, `">Z"` vs `"+Z"`, coplanar fusion, `wall_at()` returning `None`, ribs versus edge-break coverage, how the gate behaves before a part opts in, what a role has to prove, and why a rubric floor is not a weight (item 13).
- `references/worked-example.md` - a real end-to-end transcript with the commands, the numbers they printed and the render critique.
- `tests/design_corpus.py` in the repo root - the gate's own regression corpus, and the fastest way to see what it rewards.
