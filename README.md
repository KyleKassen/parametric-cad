# CadQuery Models

Parametric 3D CAD models built with [CadQuery](https://github.com/cadquery/cadquery). The Python scripts in this repo are the **source of truth** - STEP files are derived artifacts you import into SolidWorks (or any CAD tool).

## Philosophy

> Iterate on the script, not the SolidWorks model. When you need a change, change the Python parameters and re-import. The script is the source, the STEP file is a derived artifact.

Each part lives in its own directory alongside its datasheets and reference materials. Dimensions are extracted from datasheets into a `params.json` file, and the `model.py` script reads those parameters to build geometry. This keeps "what" (data) separate from "how" (modeling logic).

## Project Structure

```
.
├── parts/
│   ├── _template/                  # Scaffold copied by `make new-part`
│   ├── custom/                     # Parts WE design and fabricate
│   │   └── some_bracket/
│   │       ├── datasheets/         # PDFs, spec sheets, vendor drawings
│   │       ├── references/         # Photos, notes, analysis JSON, renders
│   │       ├── exports/            # Accepted STEP/STL + eval attempts (git-ignored)
│   │       ├── params.json         # Dimensions extracted from datasheet (build input)
│   │       ├── spec.json           # Acceptance spec for lib/evaluate.py (optional)
│   │       ├── DESIGN.md           # Design intent: function, loads, thermal, ID, review score
│   │       └── model.py            # CadQuery Python script
│   └── vendor/                     # Parts we BUY: vendor STEPs as shipped,
│       └── some_module/            # or datasheet-derived stand-in models
│                                   # (same anatomy; process: "purchased")
│
├── assemblies/                     # Scripts that combine parts via cq.Assembly
│
├── lib/                            # Shared utilities
│   ├── features.py                 # The design language as code: rounded_box,
│   │                               # recessed_panel, rib_field, bolt_pattern,
│   │                               # connector_land, Style ladders, Build phase guard
│   ├── design_review.py            # Measures refinement (organisation, not feature count) on
│   │                               # the exported STEP, scores 0-100 under a per-role rubric
│   ├── evaluate.py                 # Agent workflow: build → export → re-import →
│   │                               # validate → design review → render → report → promote
│   ├── fit.py                      # Declarative assembly fit engine (spec.json "fit")
│   ├── debug_build.py              # Stage-by-stage build bisection for kernel errors
│   ├── diff_step.py                # Geometric diff between two STEP artifacts
│   ├── export.py                   # Bulk export (discovers all parts, exports STEP/STL)
│   ├── common.py                   # Reusable geometry helpers (bolt patterns, etc.)
│   ├── analyze_step.py             # Exact STEP analysis + identity/mirror compare
│   ├── render_step.py              # Verification 6-view + iso renders (+ --section cuts)
│   │                               # and --product studio hero renders (PBR + SSAO)
│   └── housing.py                  # Silhouette / keep-out / interference / clearance
│
├── tests/                          # Parametric validation tests
│
├── .claude/skills/cad-part-design/ # The part-design workflow skill (agents load this)
├── CLAUDE.md                       # Project instructions, auto-loaded every session
├── DESIGN_LANGUAGE.md              # The industrial design standard (binding)
├── PART_TEMPLATE.md                # Engineering brief + params.json / spec.json templates
├── pyproject.toml                  # Python project config & dependencies
└── Makefile                        # Convenience targets
```

## Getting Started

### Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (fast Python package manager) - install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git LFS** - for tracking binary datasheets: `brew install git-lfs && git lfs install`

### Setup

```bash
# Clone and enter the project
cd /path/to/CadQuery

# Install dependencies (creates .venv automatically)
make install
# - or manually -
uv sync --all-extras

# Verify everything works
make test
```

### VS Code Setup (Recommended)

1. Open this folder in VS Code
2. Install the recommended extensions when prompted (OCP CAD Viewer, Python, Ruff)
3. Select the `.venv` Python interpreter (bottom-left status bar)
4. Open any `model.py`, run it - the 3D preview appears in the OCP CAD Viewer panel

## Workflow

### Adding a New Part

```bash
# 1. Scaffold the directory
make new-part NAME=am59_bracket           # → parts/custom/am59_bracket
# (make new-part NAME=x GROUP=vendor for a purchased-part stand-in)

# 2. Drop your datasheets
cp ~/Downloads/AM59_drawing.pdf parts/custom/am59_bracket/datasheets/

# 3. Fill in params.json with dimensions from the datasheet
#    (or ask Claude to do it - see PART_TEMPLATE.md)

# 4. Write the model script (or generate it with Claude)
#    See PART_TEMPLATE.md for the prompt template

# 5. Test it
python parts/custom/am59_bracket/model.py

# 6. Export everything
make export-all
```

### AI-Assisted Part Generation

Agents working in this repo load [`CLAUDE.md`](CLAUDE.md) automatically and should invoke the
**`cad-part-design`** skill (`.claude/skills/cad-part-design/`) for anything that designs, models or
refines a part. The skill carries the loop that actually produces refined geometry: gather ground
truth, write the intent, architect, build with `lib/features.py`, evaluate, look at the render,
critique against the rubric, iterate.

See [`PART_TEMPLATE.md`](PART_TEMPLATE.md) for the engineering brief template and the
`params.json` / `spec.json` shapes. The key is treating the brief like an engineering drawing -
function, interfaces, loads, thermal path, sealing, service access, and the sources every number
came from.

### The design system

[`DESIGN_LANGUAGE.md`](DESIGN_LANGUAGE.md) is the standard for any surface a human will see, and
`lib/features.py` is that standard as executable geometry. It carries a `Style` object holding the
radius, chamfer, wall, fastener-pitch and edge-inset ladders, and builders that produce the
vocabulary directly:

```python
from lib.features import STYLE, Build, recessed_panel, rib_field, rounded_box

b = Build(rounded_box(140, 100, 45, STYLE.plan_radius(140, 100)), "stock")
panel = b.pocket(lambda s: recessed_panel(s, "+Z", wall=4.0), "top_panel")
b.rib(lambda s: s.union(rib_field(panel, "chevron").solid), "top_ribs")
part = b.result
```

- **One vocabulary.** `Style.plan_radius`, `Style.edge_break`, `Style.wall`, `Style.pitch`,
  `Style.edge_inset` quantise onto small ladders, so parts built independently still read as one
  product family.
- **Guarded.** Every material-removing builder measures the remaining wall by ray-casting the real
  B-rep and raises `WallGuardError` rather than thinning it below minimum.
- **Measured.** Builders return their own proof: achieved fastener pitch, louver free area, fin
  wetted-area gain, O-ring squeeze and fill percentages.
- **Kernel-safe by construction.** `Build` enforces the order
  `base → boolean → pocket → rib → hole → break` and refuses to run a step backwards, and
  `Build.stages()` is exactly the `build_stages()` generator `make debug-build` bisects.

Full catalogue: `.claude/skills/cad-part-design/references/features-catalog.md`.

### Designing Around Vendor STEP Files

When a housing/bracket must fit an imported vendor part, don't measure by hand
and don't trust two files to be "the same part":

```bash
# 1. MEASURE - exact kernel analysis (bbox, solids, holes/bosses with true axes)
make analyze FILE="parts/vendor/zonu-oz510-receiver/OZ510 Receiver.STEP"

# 2. COMPARE - every file individually; vendors ship mirrored L/R variants!
#    (the OZ510 TX has mirrored I/O vs the RX - bboxes and radius histograms
#    can't see that, feature positions can)
make compare A="parts/.../RX.STEP" B="parts/.../TX.STEP"

# 3. VERIFY BY LOOKING - orthographic 6-view + iso renders with an axis triad
make views FILE="parts/vendor/zonu-oz510-receiver/OZ510 Receiver.STEP"
```

For cavity geometry, prefer deriving it from the part's own solid via
`lib/housing.py` (`silhouette()` / `keepout_prism()`) - the imported B-rep
drives the cutout, so handedness can't be modeled wrong. See
`parts/custom/oz510-dual-housing/` for the full pattern, including `fit_check.py`,
which drops the real vendor solids into the housing and renders/measures the fit,
and its `REQUIREMENTS.md` - a dimension-free spec of the whole OZ51x housing
family (design intent, constraints, traps, and verification obligations),
written so the parts could be recreated from the vendor files alone.

### Exporting

```bash
make export-all      # All parts → parts/<group>/<name>/exports/<name>_v1.step
make export-stl      # All parts → STEP + STL

# Single part
python parts/custom/amplifier_housing/model.py   # STEP only
python parts/custom/amplifier_housing/model.py --stl   # STEP + STL
# Exports land in parts/custom/amplifier_housing/exports/
```

### Evaluating a Part (the agent workflow)

`lib/evaluate.py` is the one-command verification gate for a part - designed so
a coding agent (or a human) can iterate on `model.py`/`params.json` and get a
deterministic, machine-readable verdict on the **exported artifact**, not just
the in-memory object:

```bash
# by directory or by name (searched under parts/custom and parts/vendor)
uv run python -m lib.evaluate parts/_template
uv run python -m lib.evaluate oz51x-dual-rx-housing
make eval PART="parts/custom/oz51x-dual-rx-housing"

# useful flags
uv run python -m lib.evaluate my-part --no-promote        # dry run, never touches accepted exports
uv run python -m lib.evaluate my-part --no-render         # skip PNG views
uv run python -m lib.evaluate my-part --json report.json  # extra copy of the report
uv run python -m lib.evaluate my-part --views iso,back --size 1200
uv run python -m lib.evaluate my-part --product-render    # add studio hero renders (make eval PRODUCT=1)
uv run python -m lib.evaluate my-part --design-min-score 75   # override the refinement bar
uv run python -m lib.evaluate my-part --no-design         # skip the refinement review
```

The pipeline: **build** `create_part(params)` → **export** to an
attempt-specific `exports/attempts/<attempt-id>/<part>_<version>.step` →
**re-import** that file → **validate** it (BREP validity, non-empty geometry,
expected solid count, dimensional requirements, part-specific validator
scripts) → **review** its refinement with `lib/design_review.py` → **render**
standardized views of the artifact → write `report.json` → **promote**.

- **Exit codes:** `0` all hard checks PASS · `1` a hard check FAILed ·
  `2` a hard check ERRORed / could not be evaluated. Errors are never
  converted into passing results.
- **Promotion:** only a fully passing attempt is copied to the accepted
  location `exports/<part>_<version>.step` (plus `_report.json` and
  `_views/`). A failed or crashed attempt can never replace an accepted
  artifact; its evidence stays in `exports/attempts/<attempt-id>/`.
- **Report:** `exports/attempts/<attempt-id>/report.json`
  (schema `part-eval/2`) lists every check as
  `{id, status: PASS|FAIL|ERROR, severity, message, measured…}` plus geometry
  summary, artifact paths, spec assumptions, and the promotion result. The full
  numeric design review lands under the `"design"` key (a `design-review/2`
  document plus the `"gate"` it was held to, including the resolved `role`), so
  every metric, value and finding is readable without re-running anything.
  Agents should read it instead of parsing the console output.

#### spec.json - the acceptance contract

`params.json` is the *build input*; an optional `spec.json` beside it is the
*acceptance contract* the exported artifact must meet. Without one, only the
baseline hard checks run (build/export/re-import, BREP validity, non-empty).

```json
{
    "schema": "part-spec/1",
    "units": "mm",
    "solid_count": 2,
    "dimensions": [
        { "id": "envelope_width_x", "kind": "bbox", "axis": "x", "expected": 92.2, "tol": 0.2 },
        { "id": "material_volume",  "kind": "volume", "min": 20000, "max": 28800, "severity": "soft" },
        { "id": "sma_holes", "kind": "cylinder", "diameter": 7.0, "tol": 0.15,
          "axis": "Y", "type": "hole", "count_min": 2 },
        { "id": "mystery_bore", "kind": "cylinder", "diameter": 6.0, "unresolved": true }
    ],
    "validators": [
        { "id": "vendor_fit_check", "script": "fit_check.py", "timeout": 900 }
    ],
    "assumptions": ["TTL bay borrows the RF STEP as a stand-in - verify a real unit."],
    "unresolved": []
}
```

- `dimensions[].kind`: `bbox` (needs `axis` x|y|z), `volume` (mm³),
  `cylinder` (cylindrical features of `diameter`±`tol`, optional `axis`
  X|Y|Z, `type` hole|boss, `count_min`), or `cylinder_at` (like `cylinder`
  plus `at: [x,y,z]` and `pos_tol` - the nearest matching feature's axis
  line must pass within `pos_tol` mm of the point; **this is the handedness
  check**: a hole of the right size on the wrong side fails). Ranges are
  `expected`±`tol` (default tol 0.1 mm) or explicit `min`/`max`.
- `severity`: `hard` (default - gates promotion) or `soft` (reported as a
  warning only).
- `unresolved: true` on a value marks it not-yet-derived: a hard unresolved
  value ERRORs the evaluation (exit 2) until resolved; document open
  questions in the top-level `unresolved` list.
- `validators` are part-local scripts (e.g. the OZ51x `fit_check.py`) run
  with the project interpreter; exit 0 = PASS, nonzero = FAIL, missing
  script/timeout = ERROR. They receive `EVAL_STEP_PATH`, `EVAL_PART_DIR`,
  and `EVAL_ATTEMPT_DIR` in the environment, and their full output is saved
  as a log in the attempt directory.

Working examples: [`parts/_template/spec.json`](parts/_template/spec.json)
(the scaffold's enclosure, with a `"design"` block that gates hard) and
[`parts/custom/oz51x-dual-rx-housing/spec.json`](parts/custom/oz51x-dual-rx-housing/spec.json)
(vendor-STEP-driven housing with positioned SMA checks, a declarative fit
block, and the fit-check validator).

#### Declarative fit checks - spec.json `"fit"`

The `fit_check.py` pattern as data: place solids, assert pairwise geometry.
Runs inside `lib.evaluate` (gating promotion) and standalone via
`uv run python -m lib.fit parts/custom/<part>` for fast iteration.

```json
"fit": {
    "render": true,
    "cases": [
        { "id": "rf_module_vs_base",
          "a": { "source": "builder", "builder": "create_base" },
          "b": { "source": "step", "path": "parts/vendor/zonu-oz510-receiver/OZ510 Receiver.STEP",
                 "transform": [ { "rotate": { "axis": "X", "angle": 90 } },
                                { "translate": [-22.55, 0, 6.0] } ] },
          "max_interference": 2.0 },
        { "id": "module_gap", "a": { "...": "..." }, "b": { "...": "..." },
          "min_clearance": 3.0 }
    ]
}
```

Solid sources: `builder` (a function in this part's `model.py`), `step`
(project-relative STEP), `part` (another part dir's builder). Constraints per
case: `max_interference` (mm³ overlap allowed), `min_clearance` (mm minimum
gap, exact kernel extrema via `lib.housing.clearance`), `max_outside` (mm³ of
`b` allowed outside `a` - containment/keep-out). A kernel failure is an ERROR,
never a passing clearance. With `"render": true` the assembled scene is
rendered into the attempt's views and promoted with them; a solid draws
translucent if its **first** appearance is as an `a` (reference) and opaque
otherwise, so order the cases with your housing solids as `a` first.

#### Drafting a spec from measured geometry

```bash
uv run python -m lib.evaluate parts/custom/my-part --init-spec   # or: make spec-init PART=...
```

Builds, exports, re-imports, and writes a **draft** `spec.json` - measured
bbox/volume/solid-count plus grouped cylinder features - with every entry
marked `"unresolved": true`. The draft deliberately ERRORs the gate until each
value is reviewed against the real requirements and its flag removed: a spec
transcribed blindly would only prove the model equals itself.

The draft also includes a `"design"` block (see below), so a new part starts with its refinement bar written down.
It is drafted deliberately **soft**, at the repo bar of 70 rather than wherever this draft happens to land, and with `"role": "enclosure"` - the strictest rubric.
Claiming `cover`, `plate`, `bracket`, `sheet` or `structural` has to be a deliberate edit by someone who knows what the part is, never something a scaffolder guessed from a bounding box.

### The refinement gate (`lib/design_review.py`)

`lib/evaluate.py` proves a part is valid and dimensionally right.
A knife-edged, blank-faced extruded slab passes every one of its checks, which is why agents optimising to that gate produce first drafts.
`lib/design_review.py` adds the missing axis: it measures how *refined* the exported B-rep is and scores it 0-100.

```bash
# exactly the number the gate will use: feed the part's own "design" block in
make design-review FILE="parts/custom/my-part/exports/my-part_v1.step" \
                   SPEC="parts/custom/my-part/spec.json" JSON=review.json
# or spell it out; ROLE and MIN override SPEC
make design-review FILE=".../my-part_v1.step" ROLE=plate MIN=70
uv run python -m lib.design_review FILE.step --role plate --min-score 70 \
    [--config cfg.json] [--json out.json] [--top N] [--quiet]
```

Eight weighted metrics, all of which measure **organisation** rather than the presence of a geometric event, and each of which degrades to an explicit "could not measure" rather than a flattering guess.
Weights below are the default `enclosure` role's: `edge_break_coverage` (0.21), `face_composition` (0.19), `feature_composition` (0.16), `pattern_discipline` (0.12), `radius_vocabulary` (0.11), `symmetry` (0.07), `sharp_edge_length` (0.07), `proportion` (0.07).
A ninth, `form_discipline`, was retired on 2026-07-25 because it scored an unstyled box higher than a fully styled one; anything still naming it is stale.
Bands are A ≥ 88, B ≥ 70, C ≥ 55, D ≥ 38, else F.
Report schema `design-review/2`.
Findings are ranked and name the `lib/features.py` builder to reach for.
Exit 0 at or above the bar, 1 below, 2 if the review could not run.
Two of the eight also carry a hard **rubric floor** that sits outside the weighted mean and cannot be waived, weighted or averaged away - see below.

Why organisation: an earlier version counted holes, fillets and faces, so a lumpy pile of overlapping rounded boxes with scattered oversized countersinks scored 96.7/A while a textbook sealed cover scored 50.2/D.
Random events satisfy presence tests.
`tests/design_corpus.py` is the regression contract that keeps that from coming back - run `uv run python -m tests.design_corpus` to print the ranked table of 22 synthetic and 4 real parts and the nine contracts it asserts.

#### Roles

The `"design"` block names a **role**, and the role selects which metrics apply, their weights and their thresholds:

| Role | The claim | Not required | The geometric guard |
|---|---|---|---|
| `enclosure` | a housing; every exterior face is a product surface | nothing (default, strictest) | none; it claims nothing |
| `cover` | a lid; thin by function, sealing face flat by function | `proportion` | thinnest bbox dimension ≤ 0.25 of the longest |
| `plate` | an interface; thin by function, and it IS its hole pattern | `proportion` | thinnest bbox dimension ≤ 0.25 of the longest |
| `bracket` | solid material, so every free edge really can be broken | `proportion` | ≤ 20% of face area facing an enclosed void |
| `sheet` | formed from flat stock; the blanked perimeter cannot carry a break | `proportion`, `sharp_edge_length` | stock thickness ≤ 10% of the longest dimension, and ≤ 15% of face area facing an enclosed void |
| `structural` | a sculpted member, legitimately long | nothing | longest bbox dimension ≥ 4.0 × the shortest |

Every role's weights sum to 1.00, so a role can excuse a metric but never lighten the total bar.
An unknown role is a hard spec ERROR.
The guard is checked **before** the rubric is honoured: a claim the measured B-rep contradicts puts a `role_error` in the report and the part is re-judged under `enclosure`.
**Declaring a lighter role than the part deserves is still dishonest.**
The guards refuse the obvious lies - every one of the five lighter roles is refused on `parts/custom/reference_mast_node_enclosure`, which measures 83.1 whatever it claims - but a part near a boundary still profits, and only its author knows.
See [`DESIGN_LANGUAGE.md`](DESIGN_LANGUAGE.md) section 2.1.

#### Four states, and only one of them is free

| State | Meaning | Effect on the score |
|---|---|---|
| `scored` | a real 0-100 number | enters the weighted mean |
| `not_required` | the role excludes it, or it was waived with a written reason | renormalised OUT; no check emitted |
| `absent_defect` | the geometry implies it and it is missing | **0.0 at full weight**, never renormalised, always a FAIL |
| `error` | it could not be measured | **0 at full weight** - it stays in the denominator - AND reported as an ERROR check |

Scattered holes that form no family are `absent_defect`, not "not applicable": the old two-state model let a part raise its score by making its geometry worse.
A kernel failure can never produce a score higher than the same geometry measured successfully, and below 60% measured weight the report's status is `insufficient` and the score is not a verdict.
`not_required` is the only free state, so it has a budget: waivers and disabled metrics together may excuse at most 0.25 of the rubric.

#### The `"design"` block

The review runs inside `make eval` automatically.
With no `"design"` block in `spec.json` it is advisory: soft severity against a bar of 70 as an `enclosure`, so an older part reports its number and warns instead of failing.
Writing `min_score` is the opt-in, and that alone makes it hard unless you also write `severity`:

```json
"design": {
    "role": "enclosure",
    "min_score": 70,
    "severity": "hard",
    "metrics": { "edge_break_coverage": { "min_score": 60 } },
    "waivers": { "symmetry": "handed part - mirrored variant by design" }
}
```

Every key it accepts, and what each can do:

| Key | Effect |
|---|---|
| `role` | picks the rubric; the geometry has to support the claim (above) |
| `min_score` | the overall bar. **Writing it is the opt-in**, and that alone makes the check hard unless you also write `severity` |
| `severity` | `hard` gates promotion, `soft` warns |
| `metric_severity` | default severity for the per-metric gates below |
| `metrics.<id>.min_score` / `max_value` / `min_value` | per-metric bars. They can only ever make the bar **higher** |
| `metrics.<id>.enabled: false` | a waiver by another name, so it needs a `"reason"` alongside it |
| `waivers` | `{metric: written reason}`. A waiver without a reason is a hard spec ERROR, and waivers plus disabled metrics may excuse at most 0.25 of the rubric |
| `symmetry_max_faces` | a **cost** guard, not an exemption: tripping it makes `symmetry` an ERROR, which costs its full weight at zero. Range-checked, so a typo cannot disable the metric |
| `enabled: false` | skips the review entirely |

That is the whole surface, and `"design_review"` is accepted as an alias for `"design"`.

**Two keys are retired**, and writing either is a **hard** spec ERROR regardless of the part's own `severity` - never a silent no-op, because an agent that writes a dead key and hears nothing believes it worked.
Both are in `lib.design_review.RETIRED_CONFIG_KEYS`, matched as dotted paths.

- `weights` set the metric weights per part.
  The relative weight of the metrics *is* the standard, so a part that sets its own is not being held to one.
  Measured on a crude knife-edged box: 27.7/F honestly, 100.0/A with six weights zeroed, 425.5/A with two of them negative.
  Use a `role` for a different rubric, a waiver to excuse one metric with a written reason, or `metrics.<id>.min_score` to make a bar higher.
- `style.radius_ladder` replaced the `Style` radius ladder per part.
  It was validated for the *shape* of the ladder (at least 5 increasing rungs spanning at least 4:1, plus a written `reason`) and never for the only thing that mattered, which is whether those rungs were anything but a transcription of the part's own measured radii.
  On an unchanged STEP, declaring a plausible-looking ladder moved `radius_vocabulary` from 0.0 to 100.0 and the part from 57.3/C to 69.3/C.
  **The supported alternative is to edit `lib.features.Style`**: one reviewed change to one frozen object, which moves every part in the repo together.
  That is what makes it a design language rather than a per-part preference.

#### Rubric floors, and `config_delta`

Everything above is a contribution to a weighted mean, and a mean can be arbitraged: pick the role whose column is lightest where the part is weak, spend a waiver, let the rest carry it.
Two mechanisms sit outside the mean for that reason.

**Floors.** `lib.design_review.RUBRIC_FLOORS` sets a hard minimum on a *single* metric, checked independently of the score.
A floor cannot be renormalised out, averaged away, waived, disabled, lowered or shifted by a role choice.
A waiver or `enabled: false` on a floored metric is rejected as a config error, and a per-metric `min_score` *below* the floor is rejected too, so a spec may raise a floor and cannot express lowering one.
`absent_defect` and `error` both *fail* a floor rather than escaping it.
Only a role exclusion removes one, because a metric the role does not use buys the part nothing and the role's claim is guarded against the geometry first.
Two metrics carry a floor today: `edge_break_coverage` (10) and `sharp_edge_length` (25), the same defect measured as a fraction and as an absolute length.
A floor also names *which number* it reads: `edge_break_coverage` is a composite of `0.85 * body + 0.15 * rim`, so its rim term alone is worth 15.0 and flooring the composite at 10 let a part with no broken body corner clear it just by deburring its bore mouths - the floor therefore reads the metric's **body term** rather than its score.
An unmet floor caps the reported **band** at `D` at every severity, fails `design_review.score`, and emits `design_review.floor.<id>` at the review's **overall** severity - so whenever the design gate is hard, the floor is hard.
`metric_severity` never reaches a floor: "this metric does not matter to me" is the one claim a floor exists to refuse.
`report["floors"]` lists every applicable floor whether met or not, because a bar nobody can see is a bar nobody is held to.

**`config_delta`.** Every knob was priced individually and nothing added them up, so the review scores the same measurements a second time under the default rubric with nothing excused and reports the difference as `report["config_delta"]`: `default_score`, `configured_score`, `delta`, `cap`, `within_cap`, and the `knobs` that moved it.
It is a re-scoring rather than a second geometric analysis (1-4% of the review's cost) and it is skipped when there is nothing to account for.
A part that declares `enclosure` and waives nothing reports exactly 0.0.
Past `MAX_CONFIG_DELTA` the delta is itself a config ERROR: the report says out loud how much of the verdict is the `spec.json` rather than the part.

Full treatment of both: [`DESIGN_LANGUAGE.md`](DESIGN_LANGUAGE.md) sections 2.5 and 2.6.

Calibration, measured 2026-07-25 on this repo.
A plain sharp box scores 15.3 (F) and the same box with four tidy holes scores 43.1 (D), because four holes on a constant pitch really are a pattern.
The three pre-design-system parts in `tests/design_corpus.py` score 22.1, 46.4 and 51.5.
One pass of the `lib/features.py` vocabulary on a simple enclosure reaches roughly 62; adding `break_mouth` to every pocket takes the same part to 76.7 (B).
The exemplar `parts/custom/reference_mast_node_enclosure` scores 83.1 (B), the `parts/_template/` scaffold 85.9 (B), and the fully worked example in `DESIGN_LANGUAGE.md` section 5 scores 92.5 (A).

### Debugging a build that won't (stage bisection)

CadQuery kernel errors ("BRep_API: command not done") don't say which feature
failed. Give `model.py` a `build_stages()` generator that yields
`(name, workplane)` after each meaningful operation (see
[`parts/_template/model.py`](parts/_template/model.py)), then:

```bash
uv run python -m lib.debug_build parts/custom/my-part --render   # or: make debug-build PART=...
```

Each completed stage prints solids/faces/volume (and optionally an iso
render); a failure is localized to "after stage '<last-good>'" with the full
traceback. A drift warning fires if the last stage no longer matches
`create_part()`. Exit 0 = all stages build, 1 = a stage failed.

### Seeing inside a part (section cuts)

```bash
uv run python -m lib.render_step FILE.step --section Z:11 --views iso,top
```

Cuts away all material on the positive side of the plane before rendering, so
interior features - bosses, corridors, spool, lid lips - are visible.
Output files carry a `_secZ11` suffix and never overwrite whole-part views.

### Product renders (looking at the part like a customer would)

`lib/render_step.py` has two modes. The verification mode above is unchanged:
orthographic, white background, axis triad, edge overlay - built for checking
geometry. The product mode is built for judging it.

```bash
make product-render FILE="parts/custom/my-part/exports/my-part_v1.step"
# with options:
make product-render FILE="....step" VIEWS=hero,hero_left SIZE=1600
uv run python -m lib.render_step FILE.step --product --material anodised \
    --background dark --shading ssao --supersample 2
```

PBR shading with an environment map, a three-point studio rig, a curved
cyclorama sweep, SSAO, FXAA, supersampling, a long-lens perspective and fine
tessellation (2.3° angular deflection instead of the verification path's 11.5°).
Cameras: `hero`, `hero_left`, `hero_rear`, `hero_high`, `hero_low`, plus every
verification view name. Materials: `anodised`, `anodised_light`, `machined`,
`cast`, `gasket`, `connector`, `fastener`, `glass`, `reference`.

Hero renders land in a `references/product/` directory beside the STEP file -
never in `references/views/`, so they cannot overwrite verification output.
Rendering a promoted artifact therefore writes to
`parts/custom/<part>/exports/references/product/`; pass `-o` to place them
elsewhere. `SIZE` is the
image *width* in product mode (height = width / aspect, default 4:3).
`uv run python -m lib.evaluate <part> --product-render` produces them as part of
the gate and promotes them to `exports/<part>_<version>_product_views/` alongside
the accepted STEP.

Shadows are off by default: `vtkShadowMapPass` works on this build but paints a
straight-edged band across the curved sweep, and SSAO alone delivers the contact
shading that makes refinement legible. `--shading both|shadows|none` remains
selectable.

**Then read the render.** A part is not finished until someone has looked at a
picture of it and compared it to [`DESIGN_LANGUAGE.md`](DESIGN_LANGUAGE.md).
The design score cannot see a counterbore chewing through a panel rim; the
render shows it immediately.

### Diffing two artifacts (what actually changed?)

```bash
uv run python -m lib.diff_step exports/part_v1.step exports/part_v2.step   # or: make diff A=... B=...
```

Booleans the two solids: added material (green) and removed material (red)
rendered over the new version (translucent), with exact mm³ volumes and a
cylindrical-feature add/remove list. Exit 0 = geometrically identical,
1 = differences found - usable as a review gate before accepting a version
bump. `--json` writes the machine-readable diff.

### Versioning Convention

Every `params.json` has a `"version"` field (e.g., `"v1"`, `"v2"`). The version is
appended to the export filename:

```
parts/custom/amplifier_housing/exports/
├── amplifier_housing_v1.step        # Initial U-channel cradle
├── amplifier_housing_v1.stl
├── amplifier_housing_v2.step        # Redesigned with rain hood
├── amplifier_housing_v2.stl
└── amplifier_housing_v2_assembly.step
```

**Old versions are never overwritten.** When you iterate on a design:

1. Bump `"version"` in `params.json` (e.g., `"v1"` → `"v2"`)
2. Modify `model.py` with your changes
3. Re-run - the new export gets a new filename, the old one stays

### Importing to SolidWorks

1. Export from here as STEP (AP214/AP242)
2. In SolidWorks: `File → Open → [select .step file]`
3. Optionally: `Insert → Features → FeatureWorks` to attempt feature recognition
4. Add tolerances, GD&T, and material callouts in SolidWorks (they don't survive the round-trip)

> **Note:** Imported STEP comes in as a "dumb solid" - no feature tree. Feature recognition is hit-or-miss. For iteration, always go back to the Python script.

## File Format Priority

| Format | Use Case | Notes |
|--------|----------|-------|
| **STEP** (.step/.stp) | Always first choice | Lossless B-Rep, full solid geometry |
| **Parasolid** (.x_t) | When available | SolidWorks native kernel |
| **IGES** (.iges) | Legacy fallback | Surfaces may need stitching |
| **STL** (.stl) | 3D printing only | Mesh, not solid - avoid for engineering |

## Testing

```bash
make test            # Run all tests
make lint            # ruff check --fix . AND ruff format . across the WHOLE repo
```

Tests validate that parts build correctly, match declared dimensions, and produce valid solids. See `tests/test_example_part.py` for the pattern.

Ruff is configured in `pyproject.toml`: line length 100, rules `E`, `F`, `I`, `W`, target
`py311`. Note that `make lint` reformats every Python file in the repo, which is not what an
agent working on a few files wants - `CLAUDE.md`'s house style is to run
`uv run ruff check --fix <the files you edited>` and leave everything else alone.

## Make Targets

```bash
make help            # Show all available targets
make install         # Create venv + install deps
make eval PART=path [PRODUCT=1] [MIN=70]   # Build → export → validate → review → render → report → promote
make spec-init PART=path   # Draft a spec.json from measured geometry
make debug-build PART=path # Stage-by-stage build bisection
make diff A=a.step B=b.step # Geometric diff between two STEP files
make design-review FILE=x.step [SPEC=parts/custom/x/spec.json] [ROLE=cover] [MIN=70] [JSON=out.json]
                           # Score design refinement 0-100. SPEC feeds the part's own "design"
                           #   block in, so what prints is what the gate will use.
make product-render FILE=x.step [VIEWS=hero] [SIZE=1600] [MATERIAL=anodised] [OUT=dir]
make analyze FILE=x.step   # Exact STEP measurement → references JSON
make compare A=a.step B=b.step  # Identity / mirror check between two STEPs
make views FILE=x.step [VIEWS=iso,top] [SIZE=900] [SECTION=Z:11] [OUT=dir]
make export-all      # Export all parts as STEP (nonzero exit on any failure)
make export-stl      # Export all parts as STEP + STL
make test            # Run pytest
make lint            # Lint + format the WHOLE repo (see Testing, above)
make clean           # Remove generated exports
make new-part NAME=x # Scaffold a new part directory from parts/_template/
```
