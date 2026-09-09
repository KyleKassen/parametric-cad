# Native Front Panel Designer verification

Verified in installed Front Panel Designer 6.5.1 on 8 September 2026. These are genuine application-saved `.fpd` documents. Each was reloaded from its saved filename and checked with the native scripting API before delivery.

| Final native file | Dimensions, mm | Verified native features |
|---|---|---|
| Backpanel_R1.fpd | 431.8 × 431.8 × 6, R6.35 | 26 elements: six enclosure holes, 16 WGU30 M3 male load studs of length 12, four WGO40 M4 female load standoffs of length 6 |
| B210_R2.fpd | 150 × 148 × 4, R8 | Eight holes: four stud-clearance holes and four reverse countersinks |
| MeanWell_R2.fpd | 72 × 316.8 × 6 maximum envelope | Six holes and the original side-tab border contour; two reverse countersinks |
| Bedrock_R3.fpd | 166 × 184 × 6, R8 | 18 elements: ten holes and eight single-loop cavity regions forming the two thermal fields |

Readback checks cover material/color IDs, size and thickness, element identity/count, XY coordinates, side, hole diameters, countersink dimensions and angle, cavity depth/bounds, and hardware catalog type/length. All panels select bare natural aluminum. All hardware is on the component/front side with depth offset zero. Representative hardware dialogs were inspected against the installed catalog. The B210 backpanel stud pattern preserves its critical 120.015 mm pitch after native coordinate quantization. Reverse-side features retain normal drawing XY coordinates.

Panel properties and native 2D/3D geometry were inspected. The native dialogs and export workflow showed no blocking machining error for the final files. Application acceptance does not establish the supplier's process capability; the custom thermal process in `ORDERING_NOTES.md` requires a quote exception.

## Independent exported-solid checks

The three final adapters were exported as STEP by Front Panel Designer itself, then compared against the intended CAD. These exports are retained in `verification/` and are independent of the CAD-generated STEP files beside the native designs.

| Adapter | Geometry checks | Screw projection calculated from actual native seat |
|---|---:|---:|
| B210_R2 | 31/31 pass | 2.549 mm with the specified M3×6 screw |
| MeanWell_R2 | 19/19 pass | 4.049 mm with the specified M4×10 screw |
| Bedrock_R3 | 43/43 pass, plus 17/17 thermal checks | 2.949 mm with the specified M4×8 screw |

The checks include valid single solids, dimensions, hole axes, underside cone extents, absence of unintended cylindrical counterbores, and remaining material. Bedrock additionally passes 768 point classifications at its retained lands and surrounding pockets, both 0.05 mm pocket floors, and shallow sections through both thermal fields.

Native/source solid differences are below 1.804 mm³ for B210, 1.332 mm³ for Mean Well, and 1.838 mm³ for Bedrock. They include native 0.001 mm rounding and the source CAD's small bore deburr, which remains a manufacturing note. B210's coincident-face Boolean required a documented 0.00001 mm translation retry with a conservative error bound; its nominal hole/seat checks pass independently. Detailed methods, exact results and hashes are in the accompanying geometry audit reports.

The final countersinks use zero additional cylindrical recess in the native API. Their cone heights follow mouth diameter, bore diameter and 90° angle. The deliberately oversized cone mouths create the specified screw-head recesses. Bedrock cavities use one closed loop per native object; four adjacent regions on each face union to the original thermal field without cutting through the retained lands.

These results verify the conversion and nominal mechanical fit. They do not qualify received screw tolerances, adhesive-stud strength, vibration retention, electrical bonding, or closed-cabinet thermal performance. The supplier and assembly conditions in `ORDERING_NOTES.md` remain part of the design.
