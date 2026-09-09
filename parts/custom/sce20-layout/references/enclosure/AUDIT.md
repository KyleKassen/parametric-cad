# Supplied SCE-20H2010LP subpanel audit

The supplied vendor STEP imports as 65 valid solids in millimetres.
Its SHA-256 is `53c943f7f13f685a41d3698485beeea6a84635aebf1fdee093479fc0b733d99a`.
Product entity `#108856` is named `SUBPANEL`.
The unique broad, flat panel is import solid 60 (all indices are zero-based).
Its top face is face 0, with source outward normal +Z.

The panel is 431.8 x 431.8 x 3.175 mm (17 x 17 x 1/8 in), with R6.35 mm corners.
The four enclosure mounting holes are round, diameter 12.7 mm, at X = +/-193.675 and Y = +/-193.675 mm.
There are two additional round through holes of diameter 7.1374 mm, at (-193.675, -161.925) and (193.675, 161.925) mm.
No slots occur in this supplied subpanel.
These six holes and the outline were visually confirmed on the exported `candidate_solid_60.step` top view.

Source X points right and source Y points up when viewing the mounting surface through the open enclosure door.
Source Z points from the rear wall toward the door.
The original rear panel seat is Z = -112.395 mm; the original component-facing surface is Z = -109.22 mm.
A replacement plate of thickness T that retains the factory rear seat therefore has its component-facing surface at Z = -112.395 + T mm.

The original panel corner studs extend to source Z = -96.52 mm.
Their projection above a replacement plate retaining the rear seat is 15.875 - T mm.
The original retaining nuts have an 18.923 mm bounding width and extend 8.5344 mm above the original component face.
Use the actual per-solid bounding boxes in `panel_geometry.json` for clearance, since the stud and nut have different depths and widths.

A rectangular cavity test spanning X/Y = +/-215.9 mm and source Z = -109.2199 to 131.1401 mm finds zero positive-volume intersections with the enclosure after excluding the original panel and its four local stud/nut assemblies.
This proves an unobstructed rectangle over the entire panel footprint apart from the separately reported factory corner hardware.
The nearest door accessory over the panel is the document pocket, solid 9, with its nearest surface at source Z = 131.1402 mm.
That gives 240.3602 mm from the original component face to the pocket.
Actual free volume beyond the tested rectangle varies with the enclosure lip, latch, hinges and door pocket.

The supplied Sales Drawing PDF was rendered and visually inspected.
It confirms a 15.25 in / 387.35 mm mounting pitch and labels a nominal 10.29 in usable depth.
The local STEP pocket clearance governs equipment placed in that pocket's projected footprint.

`panel_geometry.json` is the concise machine-readable mounting contract.
`panel_candidates.json` records every panel face and edge, including hole and corner circles.
`solid_inventory.json` lists every source solid with its original index, bounding box and validity result.
`source_analysis.json` is the repository's independent `lib.analyze_step` result.
`source_enclosure.brep` is a cache of the unmodified imported source geometry for faster later fit checks.

Run the two audit scripts with `C:/venvs/cadquery/Scripts/python.exe` from the repository root.
The repository's default `uv run` runtime failed loading OCP because its installed DLL path is too long on Windows; the existing short-path CadQuery runtime successfully imported, analysed and rendered the source.
Python lint passed using `uv run --no-sync --with ruff ruff check --fix` on the two audit scripts only.

The audit establishes geometry, not allowable panel load, fastener engagement requirements, strength, vibration capability or heat rejection.
The screenshot mentioned in the request was not available in the visible message, so identification used the actual supplied STEP product and geometry.

## Layout follow-up

`check_candidate.py` applies integration assemblies to the enclosure and tests fixed hardware plus four declared R15 x 60 mm socket approach envelopes.
It preserves the enclosure stud positions and moves the four factory retaining nuts +2.825 mm in Z for a 6 mm replacement panel retaining the rear seat.
Its original-candidate report is `candidate_fit.json`; those placements include known rejected collisions and must not be mistaken for the final layout.
The rejected Bedrock at (90, 315) mm collides with the upper-left factory stud and nut, and the rejected Peplink at (90, 100) mm collides with the lower-left factory stud and nut.
The other three original candidate positions clear the fixed enclosure and factory hardware.

The follow-up separately proves an expanded rectangular slab bounded by source X/Y = +/-252.094 mm and Z = -106.395 to -6.395 mm has zero intersections with the enclosure's rear and side shell solids 0, 1 and 2.
This slab establishes usable volume beyond the aluminum panel edges through the component height range; separately reported fixed hardware still applies.
Both complete 100 mm PSU planning corridors are free of enclosure, factory hardware and other equipment in the original candidate.
With the PSU at (378, 65.6) mm rotated 180 degrees, those corridors have only 1.795 mm nominal margin at each inner Y wall.
The required straight corridor span is 500.6 mm within 504.19 mm of wall spacing, so translation alone cannot improve the smaller margin.
This is clearance of the planning volumes, not proof of external airflow, allowable temperature or heat rejection through a sealed enclosure.

For revised layouts pass a JSON mapping with the same placement schema using `--placements-json` and write a distinct result using `--out-json`.

## Final optimized candidate

The final candidate in `references/layout_search/placement.json` passes `final_candidate_fit.json`.
This check uses the exported B210 4 mm and Bedrock 6 mm FPE revision integration assemblies, rather than their earlier stock-thickness versions.
All five assemblies have zero positive-volume intersections with fixed enclosure hardware, including the unchanged factory corner studs and the four retaining nuts shifted +2.825 mm.
All four declared R15 x 60 mm factory socket cylinders clear every component.
Both full 100 mm PSU planning corridors clear enclosure, factory hardware and other components, retaining 1.795 mm nominal wall margins.
The expanded enclosure-wall slab proof also passes.

Reproduce the final check from the repository root:

```powershell
& C:/venvs/cadquery/Scripts/python.exe parts/custom/sce20-layout/references/enclosure/check_candidate.py --placements-json parts/custom/sce20-layout/references/layout_search/placement.json --fpe-adapters --out-json parts/custom/sce20-layout/references/enclosure/final_candidate_fit.json
```
