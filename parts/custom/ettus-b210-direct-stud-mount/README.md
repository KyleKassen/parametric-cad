# B210 direct stud plate - D1

**Preliminary fit prototype.**
A separate, thin metal adapter for the four user-confirmed M3 holes beneath the B210 adhesive feet.
The 150 x 148 x 3.5 mm plate uses four M3 x 6 underside countersunk screws and mounts over four FPE M3 x 12 load studs on a 136 x 120.015 mm pattern.
The adapter's underside seats directly on the supporting plate; all four screw heads must be flush to 0.10 mm recessed.

Start with the dimensioned PDF in `drawings`, `BOM.md`, and `ASSEMBLY.md`.
Manufacture only after closing the physical fit and supplier checks listed in `PROTOTYPE_VALIDATION.md`.
The final supporting-panel outline, its attachment to the box, FPE stud capacity and radio insert capacity remain unconfirmed.

## Files

| File | Purpose |
| --- | --- |
| `model.py` + `params.json` + `lib/features.py` | Editable parametric CadQuery source and independent stud-interface dimensions |
| `spec.json` | Nominal custom-part CAD acceptance contract; not a production release |
| `exports/plate_D1.step` | Machined adapter solid, mm |
| `exports/assembled_device_mount_D1.step` | Device, adapter, hardware and reference FPE panel, distinct components |
| `exports/device_adapter_D1.step` | Radio plus adapter and four screws; supporting panel omitted |
| `exports/mount_hardware_D1.step` | Mount plus hardware proxies for inspection |
| `exports/FPE_interface_REFERENCE_ONLY.step` | Panel/stud coupon for layout; NOT the final panel order |
| `exports/plate_profile_mm.dxf` | Closed R8 outline and actual drill circles, mm |
| `exports/plate_underside_machining_mm.dxf` | Same XY view from +Z with additional CSK reference circles; DO NOT mirror coordinates |
| `exports/FPE_stud_pattern_mm.dxf` + coordinate CSV | Stud placement markers; NOT ordinary holes or pockets to duplicate below native FPE elements |
| `exports/plate_D1_preview.stl` | Preview only; a printed copy has no metal load rating |
| `references/input_device.step` | Unmodified copy of supplied vendor assembly, original units/coordinates |
| `references/geometry` | Fresh component identity audit, dimensions and true CAD sections |
| `references/research` | Manufacturer/catalog evidence, BOM data, finish and locking discussion |
| `references/engineering` | Reproducible calculations, input sources, equations and limits |
| `verify_and_render.py` | Export reopen, nominal assembly, tool/cable envelopes and removal checks |
| `make_documents.py` | Reproducible dimensioned PDF/SVG drawing source |

All hardware geometry is simplified.
The screw's ideal conical CAD proxy is not a complete or conservative head envelope and cannot establish real seating or helical-thread fit.
The supplied radio model has smooth rather than helical M3 bores; physical thread inspection remains necessary.
Four adhesive feet are suppressed only in installed copies; original internal screws are retained.

## Regeneration

Use Python3.11 and the pinned dependencies in `requirements.txt`.
On Windows, extract the design bundle to a short path such as `C:\b210d` and keep the virtual environment at a short path such as `C:\venvs\cadquery` to avoid native DLL and STEP path-length limits.
This project was generated using Python3.11.4, CadQuery2.7.0 and VTK9.3.1 on Windows.

```powershell
python -m venv C:\venvs\b210d
C:\venvs\b210d\Scripts\python.exe -m pip install -r requirements.txt
C:\venvs\b210d\Scripts\python.exe model.py --work-dir C:\b210work\direct_stud_mount
C:\venvs\b210d\Scripts\python.exe verify_and_render.py --work-dir C:\b210work\direct_stud_mount
C:\venvs\b210d\Scripts\python.exe verify_manufacturing.py
C:\venvs\b210d\Scripts\python.exe references\engineering\engineering_calculations.py --write
C:\venvs\b210d\Scripts\python.exe make_documents.py
```

Run commands from this design folder.
`model.py` defaults to the local preserved input STEP; `--source` selects a replacement, but an unmatched input SHA stops generation until component identities are audited again.
The portable `lib/features.py` is copied from the project's geometry library without edits.
For an independent CAD session, `import model; part = model.create_part()` returns the editable parameter-driven custom part.
`model.build_stages()` returns the named feature history.
The optional fresh device audit is regenerated with `python references/geometry/under_feet_audit.py --source references/input_device.step`.
In the parent repository, `python -m lib.evaluate parts/custom/ettus-b210-direct-stud-mount --no-render` also runs the local design gate.

Change `stud_pitch_x/y`, `stud_pattern_rotation_deg`, or `stud_pattern_center_x/y` to revise the panel interface.
Change housing dimensions only after fresh device measurement.
Changing thickness requires reselecting screw length, rechecking protrusion and countersink ligament, and rerunning all engineering and fit checks.
Drawing source intentionally guards the released D1 dimensions; update its dimension checks and the engineering inputs when making a new revision.

The plate is CNC machined aluminum, with no bends or sheet development.
There is no native FPD panel file or supplier quote in this package.
Use native FPE load-stud elements at the supplied positions, inspect FPE's regenerated panel STEP, and confirm factory acceptance before ordering.

No fabrication, physical fit, thermal operation or load testing was performed.
