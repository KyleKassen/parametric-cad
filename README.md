# CadQuery Models

Parametric 3D CAD models built with [CadQuery](https://github.com/cadquery/cadquery). The Python scripts in this repo are the **source of truth** — STEP files are derived artifacts you import into SolidWorks (or any CAD tool).

## Philosophy

> Iterate on the script, not the SolidWorks model. When you need a change, change the Python parameters and re-import. The script is the source, the STEP file is a derived artifact.

Each part lives in its own directory alongside its datasheets and reference materials. Dimensions are extracted from datasheets into a `params.json` file, and the `model.py` script reads those parameters to build geometry. This keeps "what" (data) separate from "how" (modeling logic).

## Project Structure

```
.
├── parts/                          # One sub-directory per component
│   └── example_part/
│       ├── datasheets/             # PDFs, spec sheets, vendor drawings
│       ├── references/             # Photos, notes, URLs
│       ├── exports/                # Generated STEP/STL (git-ignored)
│       ├── params.json             # Dimensions extracted from datasheet
│       └── model.py                # CadQuery Python script
│
├── assemblies/                     # Scripts that combine parts via cq.Assembly
│
├── lib/                            # Shared utilities
│   ├── export.py                   # Bulk export (discovers all parts, exports STEP/STL)
│   └── common.py                   # Reusable geometry helpers (bolt patterns, etc.)
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
make new-part NAME=am59_bracket

# 2. Drop your datasheets
cp ~/Downloads/AM59_drawing.pdf parts/am59_bracket/datasheets/

# 3. Fill in params.json with dimensions from the datasheet
#    (or ask Claude to do it — see PART_TEMPLATE.md)

# 4. Write the model script (or generate it with Claude)
#    See PART_TEMPLATE.md for the prompt template

# 5. Test it
python parts/am59_bracket/model.py

# 6. Export everything
make export-all
```

### AI-Assisted Part Generation

See [`PART_TEMPLATE.md`](PART_TEMPLATE.md) for a structured prompt template. The key is treating AI prompts like engineering drawings — explicit dimensions, feature callouts, and mating surface definitions.

### Exporting

```bash
make export-all      # All parts → parts/<name>/exports/<name>_v1.step
make export-stl      # All parts → STEP + STL

# Single part
python parts/amplifier_housing/model.py          # STEP only
python parts/amplifier_housing/model.py --stl    # STEP + STL
# Exports land in parts/amplifier_housing/exports/
```

### Versioning Convention

Every `params.json` has a `"version"` field (e.g., `"v1"`, `"v2"`). The version is
appended to the export filename:

```
parts/amplifier_housing/exports/
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
make export-all      # Export all parts as STEP
make export-stl      # Export all parts as STEP + STL
make test            # Run pytest
make lint            # Lint + format
make clean           # Remove generated exports
make new-part NAME=x # Scaffold a new part directory
```
