# Part Generation Prompt Template

Use this template when asking Claude (or any LLM) to generate a new CadQuery part.
Copy the block below, fill in the specifics, and paste it into your AI conversation.

---

## Template

```
Generate a CadQuery Python script for [PART NAME].

Context:
- This is part of a CadQuery project. The script will live at parts/[part_dir]/model.py
- It must define a `create_part(params=None)` function that returns a `cq.Workplane`
- Dimensions should be loaded from a sibling params.json file
- Units: millimeters throughout

Function: [What the part does, what it mates to, where it goes in the assembly]
Material/process: [e.g. 6061-T6 aluminum, 3-axis CNC milled from plate stock]
Overall envelope: [L × W × H in mm]

Key features (with dimensions):
  1. [feature: e.g. Four M5 clearance holes (Ø5.5) on a 40mm × 60mm rectangular pattern, centered]
  2. [feature: e.g. 3mm fillets on all outside vertical edges]
  3. [feature: e.g. 10mm deep pocket, 30mm × 20mm, centered on top face]
  4. ...

Mating/datum surfaces:
  - [which face mounts to what, e.g. "bottom face (−Z) mounts flush to chassis top panel"]

Parameters to expose in params.json:
  - [list the dimensions that should be tweakable, e.g. length, width, thickness, hole_diameter]

Export: STEP file to exports/[part_name].step

Follow this pattern from the project's example_part/model.py:
  - load_params() reads the sibling params.json
  - create_part(params) builds the geometry
  - export_part(result, name, formats) writes to exports/
  - if __name__ == "__main__" block exports and shows in OCP Viewer
```

---

## Also generate the params.json

```
Also generate a params.json file for this part with the following structure:
{
    "part_name": "...",
    "description": "...",
    "units": "mm",
    "material": "...",
    "process": "...",
    "dimensions": { ... },
    "features": { ... },
    "notes": [ ... ]
}
```

---

## After generating

1. Create the part directory: `mkdir -p parts/[part_name]/{datasheets,references}`
2. Save the generated `model.py` and `params.json` into the new directory
3. Drop any datasheets/spec PDFs into the `datasheets/` subdirectory
4. Test: `python parts/[part_name]/model.py`
5. Verify: `pytest tests/` (after adding a test)
6. Export: `make export-all`
