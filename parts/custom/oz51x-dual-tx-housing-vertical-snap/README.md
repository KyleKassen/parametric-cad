# OZ51x dual TX — snap service cover

**Prototype candidate, v2 — 8 September 2026.** A new sibling of
`oz51x-dual-tx-housing-vertical-opus-5`; the original is unchanged.

![Front I/O and snap cover, with simplified reference connectors](references/product/with_reference_connectors_front_io.png)

## What changed

- **v2 fiber access:** the spool retaining rim now clears the module partition by
  **8 mm**, up from 0.5 mm. The drum moves 7.5 mm toward the front I/O, preserving
  its 15 mm contact radius. The fiber bay grows 4 mm to retain connector/harness room.
- **M3 plate fasteners:** keep the original **4.5 × 9 mm slots** and all four
  mounting positions for hardware flexibility. Use washers with M3 screws;
  the checked washer envelope is 9 mm OD × 3.2 mm ID × 0.8 mm thick.
- Two fixed locating hooks and two release tabs replace eight cover screws and
  heat-set inserts. Press the two lower-edge buttons upward toward the cover
  centre, then swing the lower edge outward to release.
- The four plate/standoff slots and their mounting datums are preserved.
- Two SC/APC fiber outputs flank a central, vertically oriented **DE-9** (often
  called DB9). Its opening is D-shaped. The mating flange sits outside the wall.
- RF and TTL SMA signal inputs remain on the opposite end. The DE-9 carries
  shared DC power and control/monitoring; it is a custom harness, not RS-232.
- Cleaner framed cover, raised identification, rounded buttons and deburred
  service rims. Unneeded cover towers are removed.
- CAD material volume is **7.49% lower** than the original Opus 5 v2 assembly
  (136.83 cm³ versus 147.91 cm³). This is volume saving, not a measured print-time saving.

Envelope including mounting ears and labels: **32.72 × 138.10 × 116.20 mm**.
The renders use simplified connector references; purchased hardware is not included
in the printable CAD or assembly STEP.

## Files to use

| File | Purpose |
|---|---|
| `exports/prototype-print-package-v2.zip` | Current print/review handoff, including instructions, coupons and reports |
| `exports/oz51x-dual-tx-housing-vertical-snap_v2.step` | Named base/cover assembly for CAD review |
| `exports/base_v2.step`, `exports/cover_v2.step` | Separate parts for the print supplier |
| `exports/base_print_v2.stl`, `exports/cover_print_v2.stl` | Separate STL files with flat print datums; millimetres |
| `exports/base_v2.stl`, `exports/cover_v2.stl` | Installed-coordinate meshes for layout review |
| `exports/coupons/` | Small latch and DE-9 fit tests, STEP + STL |
| `CONNECTOR.md` | Specific module research, candidate connector, electrical limitations |
| `DESIGN.md` | Mechanical rationale, validation and remaining qualification |
| `references/evaluation.json` | Export/re-import, fit, dimensional and style-gate results |
| `model.py`, `params.json` | Parametric source; reuses the existing family builder |

The v1 CAD and ZIP are retained for comparison; use matching v2 base and cover.

![Interior with increased spool access](references/product/open_housing_interior_elevation.png)

## Print and assembly recommendation

Order **unfilled MJF PA12 nylon, black dyed**, base and cover separately. PA12 is
the starting material selection for this housing; the supplier must confirm the
snap features and tolerances. Do not substitute glass/carbon-filled material
without testing its flexure. MJF avoids the FDM orientation/support compromises
of the recessed cover. FDM versions are fit prototypes; the cover's recessed
outer face may need support when placed down.

1. Print the latch pair and DE-9 coupon using the intended material/process.
2. Test the ordered connector (candidate **Amphenol L177SDE09S**) with its actual
   jackposts, nuts and mating plug. Coupon dimensions include design allowances;
   they are not a certified manufacturer panel drawing.
3. Check the actual RF `A13-Z516-D31-AS-SL` and TTL `A13-Z510TTL-D31-AS-S` modules.
   Both bays currently use the repository's OZ510 TX STEP as a mechanical reference.
4. Mount the modules and adapters, secure the harness, and route fibers around
   the spool without crossing the latch regions. Preserve the fiber's required
   bend radius; this model inherits a 15 mm spool contact radius.
   The 8 mm rim gap improves routing access; it does not provide full fingertip
   access or certify the complete fiber route. Check the actual pigtail and boot.
5. Engage the cover's upper fixed hooks with the lower edge tilted out about
   **30 degrees**, then swing inward and press each lower release-tab region until
   seated. The joint is designed to relax after engagement.
6. To open, push both lower-edge buttons toward the cover centre approximately
   **1.3 mm**, lift the lower edge outward, then withdraw at about 30 degrees.
   Keep fiber loops and harness wires outside the hook and button paths.

The cover needs **zero metal fasteners**. Module mounting screws, SC adapter screws,
DE-9 jackpost hardware and four plate/standoff fasteners are still required.
The original module pilot sizes and engagement are retained; qualify installation
torque on the printed material. Cover opening needs approximately 47 mm extra
outward space at 30 degrees, plus hand access.
Centre each M3 screw/washer in its slot. The checked washers bear on both sides
of each slot; confirm the ordered washers and standoff faces before assembly.

## Is a snap cover the better choice?

For this internal, ungasketed service cover, it reduces hardware and assembly work.
Putting the springs in the cover makes them printable in a favourable orientation
and replaceable with the cover. Eight heat-set inserts are unnecessary for that
specific objective. Inserts or captive nuts remain preferable where a defined
clamp load, gasket compression, shock/vibration retention or certified service life
is required. None of those requirements has been established for this prototype.

## Verification and release status

**66/66 mechanical CAD checks pass**, including seated fit, sampled rigid opening
motion, latch release travel/stops, reference modules, SC hardware, DE-9 wiring/nut
space, unchanged mounting slots, M3 washer seating/bearing, measured spool gaps
and partition-facing fiber routing clearance. Base and cover each export and
re-import as one valid solid. Python lint passes. All seven delivered STL meshes
pass edge-manifold and watertightness checks. Packaging normalizes export seams
on a 0.00001 mm grid and removes collapsed triangles; STEP geometry is untouched.

The **automated style gate remains below target: 50.0/100, role enclosure,
threshold 70**. Both mandatory edge-score floors pass. The retained interface
patterns score poorly, and the symmetry estimate has a documented sensitivity to
small frame errors. The unchanged gate therefore reports FAIL and this candidate
has **not been promoted to a production-accepted part**. See the complete report
and `references/design_review_audit.md`; no scoring rules were changed or waived.

Before a production order, test snap force, repeated opening, vibration/retention
as applicable and temperature at full operation in the intended cabinet. Confirm
the exact TTL pinout before making or energizing the shared harness. No IP,
thermal, fatigue or electrical rating is claimed by the CAD checks.

## Rebuild

From the repository root with its CadQuery Python environment:

```powershell
python parts/custom/oz51x-dual-tx-housing-vertical-snap/model.py
python parts/custom/oz51x-dual-tx-housing-vertical-snap/make_coupons.py
python parts/custom/oz51x-dual-tx-housing-vertical-snap/fit_check.py
python parts/custom/oz51x-dual-tx-housing-vertical-snap/make_views.py
python -m lib.evaluate parts/custom/oz51x-dual-tx-housing-vertical-snap --no-promote
python parts/custom/oz51x-dual-tx-housing-vertical-snap/build_package.py
```

The evaluation command intentionally preserves the style bar and returns nonzero
until that gate passes; packaging retains that prototype status. On Windows, this repository's long OneDrive path may
require a short drive alias for loading OCP DLLs; generation here used `Q:`.
