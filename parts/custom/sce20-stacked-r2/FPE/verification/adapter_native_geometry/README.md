# Actual native adapter geometry verification

Qualified native revisions in this audit: **B210_R2.fpd, MeanWell_R2.fpd, Bedrock_R3.fpd**. Their actual STEP exports passed 110 geometry checks. This verifies the CAD translation, not supplier process capability, physical assembly, structural load, or operating temperature.

| Native adapter | Generic checks | Actual screw projection | Reference symmetric difference |
|---|---:|---:|---:|
| B210_R2 | 31/31 | 2.549 mm | nominal difference bounded at ≤1.80364 mm³ |
| MeanWell_R2 | 19/19 | 4.049 mm | 1.33168 mm³ |
| Bedrock_R3 | 43/43 | 2.949 mm | 1.83767 mm³ |

Bedrock additionally passed **17/17 thermal checks**. All **768 land/pocket samples** matched the reference. Both pocket floors are 0.05 mm below the exterior face. The upper Ø8 and lower Ø12 hard lands are retained; there are no diagonal bridges or unintended cuts through the lands. Its exact single-loop cavity decomposition exports successfully and preserves the design geometry. The top/bottom pocket floor areas differ from exact reference by less than 0.08 mm².

All specified bore axes, dimensions, plate thicknesses, underside countersinks, countersink diameters/angles, and calculated nominal screw projections passed. The countersink API extra-recess parameter is **zero**; geometric cone depth follows the diameters and angle. No unintended straight counterbore precedes any cone. Legitimate Bedrock thermal land walls are separately classified by their exact specified radius and 0.05 mm Z span.

Small retained-metal differences are consistent with native 0.001 mm parameter quantization and source 0.1 mm bore-edge deburr geometry that is specified as an edge-finishing instruction rather than a native machined cone. For example Bedrock's exported countersink radius is 4.949 mm versus 4.950 mm nominal. Its missing-metal difference is only 0.001414 mm³. These numerical differences do not constitute supplier tolerance acceptance.

B210 required a numerical Boolean fallback: OCCT returned an empty intersection for the coincident nominal faces. A 0.00001 mm X translation of the native solid gave a valid overlap and a 1.33847 mm³ symmetric difference. Adding the conservative native surface-area × translation bound of 0.46517 mm³ bounds the **nominal**, unshifted difference at 1.80364 mm³. Hole and countersink checks use unshifted nominal coordinates. This numerical retry does not alter either deliverable.

The 0.05 ±0.01 mm thermal fields, 1 mm escape channels, exact hard-contact interfaces, specified alloy/finish, and received screw/head/thread dimensions require the source design's supplier/process and assembly checks. The installed native 0.6 mm cutter accepts the geometry; this is not a claim that FPE's standard published tolerances meet the tighter thermal specification.

Older B210_R1, MeanWell_R1, Bedrock_R1 and Bedrock_R2 native revisions are unqualified experiments and must not be ordered. Only the three current native revisions listed above are covered by these reports. The accompanying summary records their SHA-256 hashes and those of the audited STEP exports.
