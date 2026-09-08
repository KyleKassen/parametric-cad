# Part brief template

The brief comes before the geometry.
This file is the skeleton for that brief and for the two JSON documents every part carries.

**The workflow itself lives in the `cad-part-design` skill** (`.claude/skills/cad-part-design/SKILL.md`).
Read that first: it has the loop, the design-review rubric and a worked end-to-end command sequence with real numbers.
This page only says *what to write down*, not *how to build*.

Why a brief at all: an agent handed dimensions will produce a box with those dimensions.
An agent handed a function, a load path, a thermal path and a service story produces a part.
The best parts in this repo were written this way - see `parts/custom/am59_mast_head/DESIGN.md` for the depth expected, and `parts/custom/oz510-dual-housing/REQUIREMENTS.md` for a dimension-free family spec.

---

## 1. The engineering brief -> `parts/custom/<name>/DESIGN.md`

Fill this in before `model.py` exists.
Every heading is mandatory; "none" and "unresolved" are valid answers, invented numbers are not.

```markdown
# <Part name>

Status: <concept | preliminary | fabrication-ready>, and what makes it that.

## Function
What the part does, what it mates to, where it sits in the assembly.
What it must NOT do (carry rotator load, block the exhaust, become structure).

## Authoritative inputs
| Source | What it governs | Where it lives |
|---|---|---|
| <vendor datasheet PDF> | electrical + mechanical limits | datasheets/ |
| <vendor STEP> | packaging envelope, hole positions | parts/vendor/<x>/ |
| <survey / photo> | an existing interface nobody has drawings for | references/ |
Never a number from memory. Measured with `make analyze`, or cited to a page.

## Interfaces
Every mating pattern, datum, connector, cable exit and keep-out, each with its source
and its handedness. Which face is the datum, which is the "front".

## Loads
Static, dynamic, wind, shock, handling. The load path through the part, member by
member. What is structural and what is a cover.

## Thermal
Watts in, path out, ambient and solar, target margin. Wet air or dry air, and where
the boundary between them is.

## Environment and sealing
IP target, the seal plane, the gasket or O-ring cord, drainage, drip paths,
condensation, corrosion and bonding.

## Service
What has to come out, how often, in which direction, and what must not be disturbed
to do it. Access clearance, captive hardware, torque marks.

## Materials and process
Alloy/temper, process (machined / cast / sheet / printed), finish, and therefore the
wall ladder: `Style.wall("<process>", span)`.

## Industrial design intent
The massing and silhouette. Parting lines. Which faces get recessed panels and what
goes in them. The fastener grid: size, pitch, inset, symmetry. Where the single
emblem goes. What the part should look like from three metres away.

## Alternatives considered
| Architecture | Benefits | Problems | Decision |
Say why the rejected ones were rejected.

## Unresolved
Every number you do not have, every approval you need, every test that must pass.
This list is a deliverable, not an embarrassment.

## Design review
Score, band, **role**, date and the STEP it was measured on.
Why that role, if the part could plausibly be read as more than one.
Every unfixed `high` finding with the engineering reason it stands.
Every metric in state `absent_defect`, and what is actually missing.
Every metric in state `not_required`, and whether the role or a written waiver excused it.
Every rubric floor, its required level and the measured margin.
The `config_delta`, and what bought it - 0.0 means the part configured nothing.
The `"design"` block opted into, and why the bar sits where it sits.

## Verification plan
The tests and surveys that would move this part from concept to released.
```

---

## 2. Build inputs -> `params.json`

The *what*, kept separate from the *how*.
Anything a reviewer might want to change without reading code belongs here.

```json
{
    "part_name": "AM59 mast head cartridge",
    "version": "v1",
    "description": "Removable amplifier cartridge for the centred bridge pedestal.",
    "units": "mm",
    "material": "6061-T6 aluminium",
    "process": "machined-aluminium",

    "dimensions": {
        "length": 340.0,
        "width": 210.0,
        "thickness": 6.0
    },

    "features": {
        "amp_mounting": {
            "description": "12 x M4 clearance, AM59 flange pattern (AM59-005D sheet 2)",
            "hole_diameter": 4.5,
            "countersink_diameter": 8.4,
            "pitch_x": 60.0,
            "rows_y": 190.0
        }
    },

    "notes": [
        "Datum: underside of the cartridge frame, flush to the support bars.",
        "Handedness verified against the vendor STEP with `make compare`."
    ]
}
```

`"process"` should name a `lib.features.WALLS` key so the wall ladder can be looked up:
`machined-aluminium`, `cast-aluminium`, `sheet-metal`, `printed-fdm`, `printed-sls`.

---

## 3. Acceptance contract -> `spec.json`

`params.json` is the build input; `spec.json` is what the exported artifact must prove.
Draft it from measured geometry with `make spec-init PART=parts/custom/<name>`, then **edit it** - every drafted entry arrives with `"unresolved": true` and a hard unresolved value errors the gate on purpose.

```json
{
    "schema": "part-spec/1",
    "part_name": "AM59 mast head cartridge",
    "units": "mm",
    "solid_count": 1,

    "dimensions": [
        { "id": "envelope_x", "kind": "bbox", "axis": "x", "expected": 340.0, "tol": 0.2 },
        { "id": "material_volume", "kind": "volume", "min": 120000, "max": 165000,
          "severity": "soft" },
        { "id": "amp_clearance_holes", "kind": "cylinder", "diameter": 4.5, "tol": 0.1,
          "axis": "Z", "type": "hole", "count_min": 12 },
        { "id": "output_land_screws", "kind": "cylinder_at", "diameter": 3.4, "tol": 0.1,
          "at": [128.0, -74.0, 6.0], "pos_tol": 0.5 }
    ],

    "validators": [
        { "id": "vendor_fit_check", "script": "fit_check.py", "timeout": 900 }
    ],

    "design": {
        "role": "enclosure",
        "min_score": 70,
        "severity": "hard",
        "metric_severity": "soft",
        "metrics": {
            "edge_break_coverage": { "min_score": 60 }
        },
        "waivers": {
            "symmetry": "handed part - the mirrored variant is a separate release"
        }
    },

    "assumptions": [
        "The TTL bay borrows the RF vendor STEP as a stand-in - verify against a real unit."
    ],
    "unresolved": []
}
```

Notes that matter:

- `cylinder_at` is the **handedness check**: a hole of the right size on the wrong side fails it. Use it on every interface that has a left and a right.
- `severity` is `hard` (gates promotion) or `soft` (reported as a warning). Default hard.
- The `"design"` block gates refinement (`lib/design_review.py`).
  An absent block still runs the review, at soft severity against a bar of 70 under the `enclosure` rubric.
  **Writing `min_score` is what opts the part in, and that alone makes the check hard** unless you also write `"severity"`.
  Every waiver needs a written reason; a waiver without one is a hard spec ERROR.
- `"role"` is the rubric the part is judged under: `enclosure` (the default and the strictest), `cover`, `plate`, `bracket`, `sheet`, `structural`.
  It decides which of the eight metrics apply, how they are weighted and where the thresholds sit.
  An unknown role is a hard spec ERROR, because a typo must never quietly buy a part a different standard.
  - Declare the role the part **is**, not the one that scores best.
    Every role's weights sum to 1.00, so a role can excuse a metric that the part's function genuinely contradicts, but it can never lighten the total bar.
    Every role but `enclosure` also carries a geometric guard - thinness for `cover` and `plate`, no enclosed void for `bracket`, both for `sheet`, a 4:1 aspect for `structural` - checked before the rubric is honoured, so a claim the B-rep contradicts is reported as a `role_error` and the part is re-judged as an `enclosure`.
    That refuses the obvious lies and no more: a part sitting near a guard's boundary still profits by a couple of points, and only you know.
    If the role is arguable, say which you chose and why in `DESIGN.md`.
  - `proportion` does not apply to `cover`, `plate`, `bracket` or `sheet`; a part whose function is to be thin is not penalised for being thin.
    A `sheet` part additionally has its blanked perimeter removed from the edge population, because 2 mm stock cannot carry a chamfer there, and `sharp_edge_length` does not apply to it either.
  - Full weight matrix, per-role thresholds and the guards: `DESIGN_LANGUAGE.md` section 2.1.
- Per-metric gates take `min_score` on the 0-100 sub-score, or `max_value` / `min_value` on the raw measurement (the units differ per metric, so read the `value` field in the report before writing one).
  They can only ever make the bar HIGHER.
  `{"enabled": false}` on a metric makes it `not_required` and renormalises it out, so it is a waiver by another name and needs a `"reason"` alongside it.
  Waivers and disabled metrics together may excuse at most **0.25** of the rubric.
- The rest of the block: `enabled` (false skips the review), `metric_severity` and `symmetry_max_faces` (a cost guard - tripping it makes `symmetry` an ERROR at full weight; it is range-checked, so a typo cannot disable the metric).
  That is the whole surface.
- **Two keys are retired, and writing either is a hard spec ERROR** whatever this block's own `severity` says: `weights` and `style.radius_ladder`.
  Both were the same defect, a part declaring the standard it is measured against, and both are now in `lib.design_review.RETIRED_CONFIG_KEYS` with the measurement that killed them.
  `style.radius_ladder` used to be accepted with at least 5 increasing rungs spanning at least 4:1 plus a written `reason`; that validated the *shape* of the ladder and never whether the rungs were anything but a transcription of the part's own radii, which is why declaring one could take `radius_vocabulary` from 0.0 to 100.0 on unchanged geometry.
  **If a part genuinely needs different radii, edit `lib.features.Style`** - one reviewed change to one frozen object, which moves every part in the repo together.
  That is the difference between a design language and a per-part preference.
- A metric can come back `absent_defect` - the geometry says it should apply and it does not.
  That is scored 0 at full weight and always FAILs; it is not something to waive, it is something to build.
  A metric in state `error` also costs its full weight at zero, so breaking a measurement is never cheaper than taking the score.
- **Rubric floors outrank this whole block.** `edge_break_coverage` and `sharp_edge_length` each carry a hard minimum from `lib.design_review.RUBRIC_FLOORS`, checked outside the weighted mean.
  A floor also names *which* number it reads: `edge_break_coverage`'s is held against the metric's **body term**, not its `0.85 body + 0.15 rim` composite, so deburring bore mouths cannot pay for a body whose corners are raw.
  A floored metric cannot be waived or disabled (either is rejected as a config error), and a per-metric `min_score` *below* its floor is rejected rather than quietly outranked: **a spec may raise a floor and cannot express lowering one.**
  An unmet floor caps the reported band at `D`, fails `design_review.score` at every severity, and emits its own failing check at the block's **overall** `severity` - `metric_severity` never reaches a floor.
- `report["config_delta"]` prices this whole block in points: the same measurements re-scored under the default rubric with nothing excused, and the difference.
  It is 0.0 for a part that declares `enclosure` and waives nothing, and past the cap it is itself an ERROR.
  Write a `"design"` block you would be happy to see priced.
- Floors and `config_delta` in full: `DESIGN_LANGUAGE.md` sections 2.5 and 2.6.
- `"fit"` turns `fit_check.py` into data - see the README section on declarative fit checks.

---

## 4. Then follow the skill

```bash
make new-part NAME=<name>                       # scaffold: copies parts/_template/'s params.json,
                                                # spec.json and a WORKING example model.py
# write DESIGN.md, then params.json, then model.py with lib/features.py, then spec.json
make eval PART="parts/custom/<name>"            # the gate + the design score, under the spec's role
make product-render FILE="parts/custom/<name>/exports/<name>_v1.step"
#   -> read the render back and critique it against DESIGN_LANGUAGE.md
make design-review FILE="parts/custom/<name>/exports/<name>_v1.step" \
                   SPEC="parts/custom/<name>/spec.json" JSON=review.json
#   -> prints exactly the number the gate uses, because it reads the same "design" block.
#      ROLE=<role> and MIN=<n> override it for a what-if.
#   -> iterate, then record the score, the band and the role in DESIGN.md
```

The scaffold is a real part, not a placeholder: as copied it builds a 150 x 90 x 34 mm cast-aluminium enclosure and scores 85.9, band B, as the `enclosure` its `spec.json` declares.
The exported artifact measures 153 mm in X because the connector land stands 3.0 mm proud of the +X face, which is why the drafted `spec.json` asserts 153.0 and says so in its assumptions - a bounding box measures the artifact, not the intent.
That is deliberate: the first geometry an agent reads in this repo should be geometry that meets the standard.
Replace it, do not extend it.
