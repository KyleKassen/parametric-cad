# Worked example

Every command and every number below was run on this repo on 2026-07-25, against the reworked gate (`design-review/2`).
The part is a throwaway 140 x 100 x 45 mm enclosure body built only to exercise the pipeline; it lived in `tmp/scratch/`, which is why the paths look like that.
For a real part, substitute `parts/custom/<name>/`.

Everything is reviewed under the default `enclosure` role, because that is what this part is.
Every number was re-measured on 2026-07-25 after `form_discipline` was retired and the weights were redistributed across the remaining eight metrics.

## 0. The baseline this is measured against

The box an agent writes without the design system:

```python
body = cq.Workplane("XY").box(140, 100, 45, centered=(True, True, False))
body = body.faces(">Z").workplane().rect(120, 80, forConstruction=True).vertices().hole(4.5)
```

```
$ uv run python -m lib.design_review .../naive_v1.step

  edge_break_coverage   ABSENT    0.21  0.0% of convex body edge length is broken (0 of 1140 mm),
                                        body term 0.0; 0% of bore/boss rim length is broken
  face_composition         3.0    0.19  largest empty region spans 0.85 of the silhouette scale
                                        on the +Z face (empty circle R50.0 mm); area-weighted
                                        mean 0.74 over 6 exterior face(s)
  feature_composition    100.0    0.16  100% of 4 feature centres sit on a shared centreline or
                                        a constant-pitch run, across 1 family(ies)
  pattern_discipline     100.0    0.12  1 fastener family(ies), 4 of 4 screws patterned
  radius_vocabulary     ABSENT    0.11  no fillet or chamfer geometry anywhere - every corner
                                        is a knife edge
  symmetry               100.0    0.07  best mirror plane is normal-X: 0.0% asymmetric volume
  sharp_edge_length        8.5    0.07  1140 mm of unbroken convex edge (6.41 x bbox diagonal)
  proportion              99.1    0.07  bbox 140 x 100 x 45 mm, max/min 3.1 (balanced)

  OVERALL 43.1/100  band D (draft - needs a refinement pass)   measured weight 100%
  RUBRIC FLOOR UNMET: edge_break_coverage absent where the geometry requires it ...
  RUBRIC FLOOR UNMET: sharp_edge_length scored 8.5 against a floor of 25
    band capped at D (measured band D) - a floor is a hard minimum on one metric and
    cannot be waived, disabled or averaged away
  absent where required: edge_break_coverage, radius_vocabulary
```

(The `detail` column is wrapped here for width; it is one line per metric on a terminal.)
Re-run and re-checked 2026-07-26.

Both floors are unmet here, and both say the same thing the two `absent_defect` states say: nothing on this part is broken.
The band would have been `D` anyway, so the cap changes nothing visible - which is the point of showing it on the honest baseline rather than on a part that was trying to hide.

**43.1 is not a mistake, and it is worth understanding before you read anything else.**
Four holes at a constant pitch on one centreline are a genuine pattern, and a plain box really is symmetric and well proportioned.
The gate scores eight specific properties and a raw box legitimately has three of them outright, plus `proportion` at 99.
What it has is no break geometry at all, and the two `absent_defect` zeroes, at a combined weight of 0.32, are what hold it in band D.

For contrast, `tests/design_corpus.py`'s plain sharp box - same idea, no holes at all - scores 15.3 (F).
The gap between a hole-less raw box and this one is what four tidy holes are worth, and it is as much as four tidy holes deserve and no more.
Scattering the same four holes buys nothing: holes that form no family of three report `absent_defect` on `pattern_discipline` and score 0 at full weight.

Note also that this raw box scores a flat 100 on three metrics.
Passing metrics do not make a part good; the weighted total, the states and the findings do.

## 1. The first attempt, built with lib/features.py

This is v1 exactly as it was written, before any review.
The version table at the end lists what each later revision changed and what it bought.

```python
from lib.features import (STYLE, Build, bolt_pattern, connector_land, face_plane,
                          fastener_holes, lightening_pocket, recessed_panel,
                          rib_field, rounded_box)

def _build(params=None):
    d = params["dimensions"]
    L, W, H, wall = d["length"], d["width"], d["height"], d["wall"]   # 140, 100, 45, 3.2
    r = STYLE.plan_radius(L, W)                                    # -> 12.0

    b = Build(rounded_box(L, W, H, r, top_break=STYLE.edge_break(L, wall)), "stock")
    b.pocket(lambda s: lightening_pocket(s, "-Z", size=(L - 2*wall, W - 2*wall),
                                         depth=H - wall), "cavity")
    panel = b.pocket(lambda s: recessed_panel(s, "+Z", wall=wall), "top_panel")
    b.rib(lambda s: s.union(rib_field(panel, "chevron").solid), "top_ribs")
    b.hole(lambda s: connector_land(s, "+Y", length=34, width=26, aperture=(20, 14),
                                    raised=1.5, wall=wall).solid, "connector_land")

    top = face_plane(b.result, "+Z")
    pat = bolt_pattern("perimeter", length=L, width=W, fastener="M4",
                       inset=STYLE.edge_inset("M4"), plane=top)
    b.hole(lambda s: fastener_holes(s, pat.points, plane=top, fastener="M4", kind="cbore"),
           "lid_screws")
    return b

def create_part(params=None):   return _build(params).result
def build_stages(params=None):  yield from _build(params).stages()
```

Nothing in there is a magic number except the part's own envelope and the connector's aperture.
Every radius, chamfer, inset and frame width came off the ladders.

One thing the ladders do **not** hand you: the wall has to be 3.2 mm, not the 2.8 mm that `STYLE.wall("machined-aluminium", span=140)` returns for this part's length.
At 2.8 the recessed panel is refused, correctly:

```
WallGuardError: recessed panel 1.26 mm deep into a 2.80 mm wall leaves 1.54 mm,
                below the 1.60 mm minimum
```

The unsupported span that governs this wall is the 160 mm diagonal run, not the 140 mm length.
See trap 3: the guard is measuring, and the fix is the engineering, never `min_wall`.

## 2. Does it build

```
$ uv run python parts/custom/<name>/model.py
wrote .../exports/demo_bracket_v1.step
```

Stage bisection, which `Build.stages()` provides for free (this is the final v7 build, so it has the mouth breaks from section 5):

```
$ make debug-build PART="..."
== debug-build: demo_bracket ==
  [PASS ] stage 1 'stock': 1 solid(s), 26 faces, 623695.6 mm^3 in 1.9s
  [PASS ] stage 2 'cavity': 1 solid(s), 35 faces, 106155.2 mm^3 in 0.0s
  [PASS ] stage 3 'cavity_mouth': 1 solid(s), 43 faces, 106076.9 mm^3 in 0.0s
  [PASS ] stage 4 'top_panel': 1 solid(s), 52 faces, 95068.0 mm^3 in 0.0s
  [PASS ] stage 5 'top_panel_mouth': 1 solid(s), 60 faces, 95005.4 mm^3 in 0.0s
  [PASS ] stage 6 'panel_+Y': 1 solid(s), 69 faces, 91200.5 mm^3 in 0.0s
  [PASS ] stage 7 'mouth_+Y': 1 solid(s), 77 faces, 91155.7 mm^3 in 0.0s
  [PASS ] stage 8 'panel_-Y': 1 solid(s), 86 faces, 87350.8 mm^3 in 0.0s
  [PASS ] stage 9 'mouth_-Y': 1 solid(s), 94 faces, 87306.0 mm^3 in 0.0s
  [PASS ] stage 10 'panel_-X': 1 solid(s), 103 faces, 85027.5 mm^3 in 0.0s
  [PASS ] stage 11 'mouth_-X': 1 solid(s), 111 faces, 84997.1 mm^3 in 0.0s
  [PASS ] stage 12 'top_ribs': 1 solid(s), 213 faces, 86226.9 mm^3 in 0.0s
  [PASS ] stage 13 'connector_land': 1 solid(s), 244 faces, 86587.5 mm^3 in 0.0s
  [PASS ] stage 14 'lid_screws': 1 solid(s), 260 faces, 84643.3 mm^3 in 0.0s
  all 14 stage(s) built
```

Solid count stays at 1 through every stage - that is the coplanar-fusion check, done for free.
Note stage 12: the rib field ADDS 1230 mm^3 back, and stage 13 adds again.
Volume going up in the `rib` phase is correct; volume going up in a `pocket` or `hole` phase is a bug.

## 3. The gate

Run on the naive box from section 0, which has no `spec.json` at all:

```
$ uv run python -m lib.evaluate <part> --no-promote --no-render
== evaluate: demo_naive ==
   [PASS ] build: create_part() ok in 0.0s
   [PASS ] export: .../attempts/<id>/demo_naive_v1.step (33 KB)
   [PASS ] reimport: 1 solid(s), volume 627137.2 mm^3, bbox 140.00 x 100.00 x 45.00 mm
   [PASS ] brep_valid: BRepCheck_Analyzer passed
   [PASS ] non_empty: 1 solid(s), volume 627137.2 mm^3
   [FAIL ] design_review.score: refinement score 43.1 (D - draft - needs a refinement pass)
           as an enclosure, threshold 70 (soft)
   [FAIL ] design_review.edge_break_coverage: absent where the geometry requires it:
           0.0% of convex body edge length is broken (0 of 1140 mm) (soft)
   [FAIL ] design_review.radius_vocabulary: absent where the geometry requires it:
           no fillet or chamfer geometry at all - every corner is a knife edge (soft)
   overall: PASS (promotion disabled)
```

Run without `--no-promote` and the same attempt promotes: `overall: PASS -- promoted to .../exports/demo_naive_v1.step`, exit 0.
The design check is soft until a part opts in, so a draft still promotes with a warning.
Do not read that as permission to stop.

The two `absent_defect` FAILs are the useful part of that output: they are a list of what the part does not have, at full weight, and they cannot be waived away.

Draft the acceptance contract, then edit it:

```
$ make spec-init PART="..."        # run on the finished v7
  draft spec (8 dimension entries, 1 solid(s)) -> .../spec.json
  review each entry, delete the ones that aren't requirements, and remove its 'unresolved' flag
  design refinement today: 76.7/100 (band B) against a drafted bar of 70
```

The drafted `"design"` block arrives as `{"enabled": true, "role": "enclosure", "min_score": 70, "severity": "soft", "metric_severity": "soft", "metrics": {"edge_break_coverage": {"min_score": 60}}, "waivers": {}}`.
Two things to change deliberately: the `role`, if this part is not an enclosure, and `"severity": "hard"` once it clears its bar.

Running the gate against the untouched draft:

```
$ make eval PART="..." ; echo $?
   [ERROR] dim:cylinders_0_d24: unresolved value -- resolve the spec before acceptance
   ...
   overall: ERROR -- NOT promoted
2
```

Exactly right. Every drafted value carries `"unresolved": true`, and a hard unresolved value errors the gate until a human decides it is a requirement.

## 4. Look at it

```
$ make product-render FILE=".../demo_bracket_v2.step" VIEWS=hero SIZE=1200
  ok renders/demo_bracket_v2_hero.png
```

(For a STEP under `parts/`, the render lands in a `references/product/` directory beside the STEP file instead.)

Read the PNG back and critique it line by line.
The real critique of that render:

- **Defect, fix now.** The counterbore mouths chew through the recessed-panel rim: the screw seats read as crescents and bumps rather than clean bores. Cause: the perimeter pattern at a 9.0 mm inset with an 8.0 mm counterbore reaches 13.0 mm from the edge, but the default frame is 8.0 mm wide. Fix: size the frame from the fastener (`frame = edge_inset + cbore_dia/2 + margin` = 14 mm). Re-rendered, the seats sit clean on the frame.
- **Weak.** The chevron rib field reads as an arbitrary zigzag lattice rather than a deliberate stiffening pattern, and one rib terminates in a stub. A rib field should follow the load path; this one has no load path because the demo has no loads.
- **Weak.** The connector land at `raised=1.5` is barely legible - the aperture reads as a hole punched in a wall. Either raise it further, or recess it, and give the boundary a visible break.
- **Good.** Plan corners, rim chamfers, side panels and the proud frame all read correctly. The silhouette is a product, not a block.

None of the first three is visible in the metrics.
That version scored a respectable `pattern_discipline` 91.6 while the screw seats were crescents.
**This is why looking is mandatory.**

And it gets worse than "the metric cannot see it".
Fixing the defect properly - widening the frame to 14 mm so the counterbores land clean - moved the score **down**, because the wider frame left more unbroken pocket-mouth edge.
If you had been steering by the number you would have reverted the correct fix.

## 5. Score, iterate, record

```
$ make design-review FILE=".../demo_bracket_v6.step" MIN=70

  edge_break_coverage     25.2    0.21  37.9% of convex body edge length is broken
                                        (464 of 1225 mm); 17% of bore/boss rim length is broken
  sharp_edge_length       39.1    0.07  761 mm of unbroken convex edge (4.28 x bbox diagonal)
  face_composition        27.9    0.19  largest empty region spans 0.67 of the silhouette scale
                                        on the -Z face (empty circle R39.62 mm); area-weighted
                                        mean 0.38 over 13 exterior face(s)
  feature_composition     78.0    0.16  82% of 22 feature centres sit on a shared centreline or
                                        a constant-pitch run, across 7 family(ies); weakest is
                                        1x D39.8 on +X (0%)
  pattern_discipline      91.6    0.12  2 fastener family(ies), 16 of 16 screws patterned;
                                        weakest is 12x D8.0 on Z (score 89)
  radius_vocabulary       91.7    0.11  5 distinct break sizes, 100% of exterior blend/chamfer
                                        area on the ladder
  symmetry                84.9    0.07  best mirror plane is normal-Y: 1.6% asymmetric volume,
                                        spread over 24% of the bbox diagonal
  proportion              99.1    0.07  bbox 140 x 100 x 45 mm, max/min 3.1 (balanced)

  OVERALL 59.8/100  band C (acceptable - visible roughness)
make: *** [design-review] Error 1
```

The recipe failed because 59.8 is below the `MIN=70` bar, so the gate works.
Exit codes, verified: the module (`uv run python -m lib.design_review FILE --min-score 70`) returns 0 at or above the bar, 1 below it, 2 if the review could not run.
`make` wraps that and exits 2 on any recipe failure, so test the module's status directly when you need the distinction.
`make design-review` takes `ROLE`, `MIN`, `JSON` and `SPEC`; pass `SPEC="<part>/spec.json"` to see the number the gate itself will use - see trap 11.

Look at that table and ask what is actually wrong.
`edge_break_coverage` 25.2 and `sharp_edge_length` 39.1 are both saying the same thing in different units: **761 mm of this part's convex edge has never been broken**, and almost all of it is pocket mouths.
That is R2, and it is one helper.

### The move that actually clears the bar

```python
def break_mouth(solid, pocket, plane: cq.Plane, c: float = 0.6):
    """Chamfer a pocket mouth by CUTTING a tool that already carries the break."""
    sunk = cq.Plane(origin=plane.origin - plane.zDir * c, xDir=plane.xDir, normal=plane.zDir)
    tool = rounded_box(pocket.length + 2*c, pocket.width + 2*c, 60.0, pocket.radius + c,
                       bottom_break=c, plane=sunk)
    return solid.cut(tool)
```

Capture each face's plane **before** the pocket is cut, then apply it to the cavity and to all four recessed panels.
Nothing else changed:

```
  edge_break_coverage     90.1    0.21  100.0% of convex body edge length is broken (926 of 926 mm);
                                        44% of bore/boss rim length is broken
  sharp_edge_length      100.0    0.07  0 mm of unbroken convex edge (0.00 x bbox diagonal)
  radius_vocabulary       83.3    0.11  6 distinct break sizes, 100% of exterior blend/chamfer area
                                        on the ladder

  OVERALL 76.7/100  band B (good - minor refinement left)
```

The progression across this session, all measured:

| Version | Change | Score | Band |
|---|---|---|---|
| naive | raw box, four holes | 43.1 | D |
| v1 | full feature vocabulary, default frame | 61.7 | C |
| v6 | + side panels, coarser rib pitch, frame sized from the fastener | 59.8 | C |
| v7 | + `break_mouth` on the cavity and all four panels | **76.7** | **B** |

Every row was rebuilt and re-measured on 2026-07-25 against the current eight-metric gate; the intermediate v2 and v4 revisions are gone because they cannot be rebuilt exactly and a table of mixed-provenance numbers is worse than a shorter one.

For calibration: the three real parts in `tests/design_corpus.py` that predate the design system score 22.1, 46.4 and 51.5, and the exemplar `parts/custom/reference_mast_node_enclosure` scores 83.1.
A vocabulary pass gets a simple enclosure to roughly 62.
The last stretch is not more features - v1 to v6 adds three side panels, a coarser rib pitch and a frame sized from the fastener, and is worth **minus 1.9 points** between them.
It is composition: break every pocket mouth, keep the fastener families regular, and cut the biggest empty region that is left.

`face_composition` is still 27.6 on v7, and that is the honest next thing to fix: the open cavity ceiling is a 40 mm empty circle, and this demo has no interior features because it has no interior.

Then write it down in `DESIGN.md`:

```markdown
## Design review

Score 76.7/100 (band B) as an **enclosure** on demo_bracket_v7.step, 2026-07-25.
Role: enclosure - it is a housing with an internal cavity, so no metric is excused.
No metric in state error or absent_defect; measured weight 100%.

Open findings:
- face_composition 27.6: the open cavity ceiling is a 40 mm empty circle. This demo
  has no PCB, so it has no standoffs and no interior features. On a real part this
  is where the screw columns and cable features go.
- feature_composition 78.0: the connector aperture is a lone feature of its own
  diameter and scores zero in its family. Accepted - the part needs one connector.
```
