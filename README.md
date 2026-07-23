# CadQuery Models

Parametric 3D CAD models built with [CadQuery](https://github.com/cadquery/cadquery). The Python scripts in this repo are the **source of truth** — STEP files are derived artifacts you import into SolidWorks (or any CAD tool).

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
│   │       └── model.py            # CadQuery Python script
│   └── vendor/                     # Parts we BUY: vendor STEPs as shipped,
│       └── some_module/            # or datasheet-derived stand-in models
│                                   # (same anatomy; process: "purchased")
│
├── assemblies/                     # Scripts that combine parts via cq.Assembly
│
├── lib/                            # Shared utilities
│   ├── evaluate.py                 # Agent workflow: build → export → re-import →
│   │                               # validate → render → report → promote (+ --init-spec)
│   ├── fit.py                      # Declarative assembly fit engine (spec.json "fit")
│   ├── debug_build.py              # Stage-by-stage build bisection for kernel errors
│   ├── diff_step.py                # Geometric diff between two STEP artifacts
│   ├── export.py                   # Bulk export (discovers all parts, exports STEP/STL)
│   ├── common.py                   # Reusable geometry helpers (bolt patterns, etc.)
│   ├── analyze_step.py             # Exact STEP analysis + identity/mirror compare
│   ├── render_step.py              # Headless 6-view + iso renders (+ --section cuts)
│   └── housing.py                  # Silhouette / keep-out / interference / clearance
│
├── tests/                          # Parametric validation tests
│
├── PART_TEMPLATE.md                # Prompt template for AI-assisted part generation
├── pyproject.toml                  # Python project config & dependencies
└── Makefile                        # Convenience targets
```

## Getting Started

### Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (fast Python package manager) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git LFS** — for tracking binary datasheets: `brew install git-lfs && git lfs install`

### Setup

```bash
# Clone and enter the project
cd /path/to/CadQuery

# Install dependencies (creates .venv automatically)
make install
# — or manually —
uv sync --all-extras

# Verify everything works
make test
```

### VS Code Setup (Recommended)

1. Open this folder in VS Code
2. Install the recommended extensions when prompted (OCP CAD Viewer, Python, Ruff)
3. Select the `.venv` Python interpreter (bottom-left status bar)
4. Open any `model.py`, run it — the 3D preview appears in the OCP CAD Viewer panel

## Workflow

### Adding a New Part

```bash
# 1. Scaffold the directory
make new-part NAME=am59_bracket           # → parts/custom/am59_bracket
# (make new-part NAME=x GROUP=vendor for a purchased-part stand-in)

# 2. Drop your datasheets
cp ~/Downloads/AM59_drawing.pdf parts/custom/am59_bracket/datasheets/

# 3. Fill in params.json with dimensions from the datasheet
#    (or ask Claude to do it — see PART_TEMPLATE.md)

# 4. Write the model script (or generate it with Claude)
#    See PART_TEMPLATE.md for the prompt template

# 5. Test it
python parts/custom/am59_bracket/model.py

# 6. Export everything
make export-all
```

### AI-Assisted Part Generation

See [`PART_TEMPLATE.md`](PART_TEMPLATE.md) for a structured prompt template. The key is treating AI prompts like engineering drawings — explicit dimensions, feature callouts, and mating surface definitions.

### Designing Around Vendor STEP Files

When a housing/bracket must fit an imported vendor part, don't measure by hand
and don't trust two files to be "the same part":

```bash
# 1. MEASURE — exact kernel analysis (bbox, solids, holes/bosses with true axes)
make analyze FILE="parts/vendor/zonu-oz510-receiver/OZ510 Receiver.STEP"

# 2. COMPARE — every file individually; vendors ship mirrored L/R variants!
#    (the OZ510 TX has mirrored I/O vs the RX — bboxes and radius histograms
#    can't see that, feature positions can)
make compare A="parts/.../RX.STEP" B="parts/.../TX.STEP"

# 3. VERIFY BY LOOKING — orthographic 6-view + iso renders with an axis triad
make views FILE="parts/vendor/zonu-oz510-receiver/OZ510 Receiver.STEP"
```

For cavity geometry, prefer deriving it from the part's own solid via
`lib/housing.py` (`silhouette()` / `keepout_prism()`) — the imported B-rep
drives the cutout, so handedness can't be modeled wrong. See
`parts/custom/oz510-dual-housing/` for the full pattern, including `fit_check.py`,
which drops the real vendor solids into the housing and renders/measures the fit,
and its `REQUIREMENTS.md` — a dimension-free spec of the whole OZ51x housing
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

`lib/evaluate.py` is the one-command verification gate for a part — designed so
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
```

The pipeline: **build** `create_part(params)` → **export** to an
attempt-specific `exports/attempts/<attempt-id>/<part>_<version>.step` →
**re-import** that file → **validate** it (BREP validity, non-empty geometry,
expected solid count, dimensional requirements, part-specific validator
scripts) → **render** standardized views of the artifact → write
`report.json` → **promote**.

- **Exit codes:** `0` all hard checks PASS · `1` a hard check FAILed ·
  `2` a hard check ERRORed / could not be evaluated. Errors are never
  converted into passing results.
- **Promotion:** only a fully passing attempt is copied to the accepted
  location `exports/<part>_<version>.step` (plus `_report.json` and
  `_views/`). A failed or crashed attempt can never replace an accepted
  artifact; its evidence stays in `exports/attempts/<attempt-id>/`.
- **Report:** `exports/attempts/<attempt-id>/report.json`
  (schema `part-eval/1`) lists every check as
  `{id, status: PASS|FAIL|ERROR, severity, message, measured…}` plus geometry
  summary, artifact paths, spec assumptions, and the promotion result. Agents
  should read it instead of parsing the console output.

#### spec.json — the acceptance contract

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
    "assumptions": ["TTL bay borrows the RF STEP as a stand-in — verify a real unit."],
    "unresolved": []
}
```

- `dimensions[].kind`: `bbox` (needs `axis` x|y|z), `volume` (mm³),
  `cylinder` (cylindrical features of `diameter`±`tol`, optional `axis`
  X|Y|Z, `type` hole|boss, `count_min`), or `cylinder_at` (like `cylinder`
  plus `at: [x,y,z]` and `pos_tol` — the nearest matching feature's axis
  line must pass within `pos_tol` mm of the point; **this is the handedness
  check**: a hole of the right size on the wrong side fails). Ranges are
  `expected`±`tol` (default tol 0.1 mm) or explicit `min`/`max`.
- `severity`: `hard` (default — gates promotion) or `soft` (reported as a
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
(simple plate) and
[`parts/custom/oz51x-dual-rx-housing/spec.json`](parts/custom/oz51x-dual-rx-housing/spec.json)
(vendor-STEP-driven housing with positioned SMA checks, a declarative fit
block, and the fit-check validator).

#### Declarative fit checks — spec.json `"fit"`

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
`b` allowed outside `a` — containment/keep-out). A kernel failure is an ERROR,
never a passing clearance. With `"render": true` the assembled scene is
rendered into the attempt's views and promoted with them; a solid draws
translucent if its **first** appearance is as an `a` (reference) and opaque
otherwise, so order the cases with your housing solids as `a` first.

#### Drafting a spec from measured geometry

```bash
uv run python -m lib.evaluate parts/custom/my-part --init-spec   # or: make spec-init PART=...
```

Builds, exports, re-imports, and writes a **draft** `spec.json` — measured
bbox/volume/solid-count plus grouped cylinder features — with every entry
marked `"unresolved": true`. The draft deliberately ERRORs the gate until each
value is reviewed against the real requirements and its flag removed: a spec
transcribed blindly would only prove the model equals itself.

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
interior features — bosses, corridors, spool, lid lips — are visible.
Output files carry a `_secZ11` suffix and never overwrite whole-part views.

### Diffing two artifacts (what actually changed?)

```bash
uv run python -m lib.diff_step exports/part_v1.step exports/part_v2.step   # or: make diff A=... B=...
```

Booleans the two solids: added material (green) and removed material (red)
rendered over the new version (translucent), with exact mm³ volumes and a
cylindrical-feature add/remove list. Exit 0 = geometrically identical,
1 = differences found — usable as a review gate before accepting a version
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
3. Re-run — the new export gets a new filename, the old one stays

### Importing to SolidWorks

1. Export from here as STEP (AP214/AP242)
2. In SolidWorks: `File → Open → [select .step file]`
3. Optionally: `Insert → Features → FeatureWorks` to attempt feature recognition
4. Add tolerances, GD&T, and material callouts in SolidWorks (they don't survive the round-trip)

> **Note:** Imported STEP comes in as a "dumb solid" — no feature tree. Feature recognition is hit-or-miss. For iteration, always go back to the Python script.

## File Format Priority

| Format | Use Case | Notes |
|--------|----------|-------|
| **STEP** (.step/.stp) | Always first choice | Lossless B-Rep, full solid geometry |
| **Parasolid** (.x_t) | When available | SolidWorks native kernel |
| **IGES** (.iges) | Legacy fallback | Surfaces may need stitching |
| **STL** (.stl) | 3D printing only | Mesh, not solid — avoid for engineering |

## Testing

```bash
make test            # Run all tests
make lint            # Lint + format with ruff
```

Tests validate that parts build correctly, match declared dimensions, and produce valid solids. See `tests/test_example_part.py` for the pattern.

## Make Targets

```bash
make help            # Show all available targets
make install         # Create venv + install deps
make eval PART=path  # Build → export → validate → render → report → promote
make spec-init PART=path   # Draft a spec.json from measured geometry
make debug-build PART=path # Stage-by-stage build bisection
make diff A=a.step B=b.step # Geometric diff between two STEP files
make export-all      # Export all parts as STEP (nonzero exit on any failure)
make export-stl      # Export all parts as STEP + STL
make test            # Run pytest
make lint            # Lint + format
make clean           # Remove generated exports
make new-part NAME=x # Scaffold a new part directory
```
