# Standard-stock FPE adapter variants

These are separate preliminary integration revisions. Original D1, N2 and T1
designs stay unchanged. Geometry role is `plate`: the prescribed mounting axes
and the broad device/panel contact surfaces define the part. All dimensions mm.

The new B210_FPE_R1 uses 4.00 +/-0.05 aluminum instead of D1's 3.50. Its underside
90 degree countersink grows from diameter 6.1 to 7.1, lowering the M3x6 head by
0.50 within the plate. Nominal head recess is now 0.55 and screw projection into
the radio stays 2.55. The bore's 2.05 straight throat after the upper 0.10 deburr
is preserved. Housing and four supporting-panel stud axes stay unchanged.

Bedrock_FPE_R1 uses 6.00 +/-0.05 aluminum instead of T1's 5.10. Its underside
90 degree countersink grows from diameter 8.1 to 9.9. Nominal head recess is now
0.95 and M4x8 projection into the Tile stays 2.95. Its 3.20 straight throat after
the upper deburr stays unchanged. The lower thermal-field dry lands grow from
diameter 10 to 12, leaving 1.05 radial land beyond each 9.9 mouth. Top diameter-8
contact lands, 126x156 R5 thermal fields, both-face depth 0.050 +/-0.010, and the
two 1-wide outlet grooves stay at the T1 interface dimensions. The larger lower
lands modestly reduce compound area; actual contact and thermal tests remain
necessary. All six housing and four panel axes stay unchanged.

The deeper recessed heads intentionally replace the old 0..0.10 head-recess
criterion. Gauge actual screw projection and full thread engagement at assembly;
the catalog screw-length label does not control the real conical head seating.
B210 acceptance remains 2.4..2.9 projection; Bedrock 2.85..3.00, at least 2.00
complete threads and at least 0.50 to the actual blind obstruction. Existing
physical joint, housing, FPE anchor, panel-support, load and thermal release
items are carried forward. No fresh rated load capacity is claimed.

Both variants reuse WGU30 M3 load studs of 12 projection with zero depth offset.
With nominal 0.55 washers and 4.0 locknuts, studs extend 3.45 beyond the B210 nut
and 1.45 beyond the Bedrock nut. Verify actual engagement through the nylon ring.
The reference panel in the full assembly exports remains an interface coupon;
use the `device_adapter` exports in the final enclosure layout.

FPD nominal stock selection alone does not establish the source material/finish
or tolerance requirements. Request the actual aluminum alloy and thickness
tolerances from FPE; the original design basis was certified 6061-T6/T651 and
clear chemical conversion, with dimensions applying after finish. The thermal
variant additionally requires Ra<=1.6 micrometres at the fields and assembled
filled gaps below 0.10. Native representation of a 0.05 pocket is a machining
instruction, not confirmation of FPE's tolerance/process capability.

Mean Well remains the current N2 72x316.8x6 side-tab adapter, with its existing
45-wide spine, R4 outline, housing bores and countersinks. It needs a native FPD
conversion but no thickness variant. Its unresolved physical rear M4 feature,
local countersink-seat strength screening HOLD and side-orientation power
derating remain carried forward.

`model.py` loads the original source builders and writes isolated parameter
overlays, plate/assembly/device STEP files, machining DXFs and targeted fitting
reports. It stages native geometry at short paths because the workspace path
can exceed Windows importer limits. The generated actual plates are reopened
before dimensions, geometry and device/hardware fitting are checked. Source
input hashes are checked. Nominal hardware is simplified as in the originals.

Appearance was measured on the exported plates with the plate rubric:
B210_FPE_R1 89.1/A and Bedrock_FPE_R1 67.4/C. The Bedrock score remains below the
original 70 target. The prescribed source hole pattern and the 50 micrometre
thermal-field boundaries retain the source T1's documented functional exception;
those boundaries must not be widened into cosmetic chamfers or deeper pockets.
Detailed scores, floor results and configuration effects are in the adjacent
`*_design_review.json` files, unaltered.

Completed fitting checks pass: B210 65/65 and Bedrock 77/77. B210 nominal internal
screw clearance is 1.0238 and minimum OD10 socket clearance is 1.8255. Bedrock
nominal blind-end tip clearance is 0.55 and minimum socket clearance is 6.40175.
Both assemblies clear their normal 20 mm sampled service lift with nuts/washers
removed. Original source device SHA256 checks pass. Actual exported plate bottom
views and Bedrock isometric view were inspected; see `visual_review.json`.

Bedrock lower primary compound field is now 19001.09 square mm and upper primary
field is 19340.20 square mm, excluding escape grooves. Both remain 0.05 deep.
The current Bedrock rubric body-edge floor is 46.5 versus 10; sharp-edge floor
58.061 versus 25. Configuration adds 9.5 points (plate role only, no waiver) over
the default score 58.0. These floor passes do not turn the below-target score
67.4 into an appearance pass.

Actual native STEP inspection identified an important FPD API convention:
`SetCountersinkWithParameters(coneDiameter, boreDiameter, sinkDepth, 90)` uses
its third argument as an additional straight axial recess before the cone.
It must be **zero** for these adapters. The cone height is already determined
by the two diameters and angle. Entering cone height again there adds an
unintended large-diameter counterbore and increases screw penetration. Native
readback of the stored number alone does not prove geometric intent. Final
native STEP audits must verify each cone begins at underside Z0 and ends at
its geometric height (B210 1.85, Mean Well 1.80, Bedrock 2.70).
