# Peplink removable upper carrier - R2

Status: preliminary mechanical design with exported reference CAD and actual native FPD geometry verified; physical load and thermal qualification remain open.
The declared role is `plate`: a thin removable interface between four carrier supports and the router's measured mounting ears.

## Function and interfaces

The 180 x 210 x 4 mm R8 aluminum frame places the Peplink over a Bedrock that remains directly thermally coupled to the main backpanel.
Its centered 146 x 160 mm R5 through-window leaves 17 mm side rails and 25 mm end rails, opening the central region above the Bedrock fins.
Both external and window rims have 0.4 mm 45-degree breaks.
The frame datum is centered XY with its underside Z=0; installed underside Z=70 mm above the backpanel component face.
Four diameter-3.8 support holes lie at X=+/-70, Y=+/-97 mm.
The router is translated Y=-17 mm relative to the frame, retaining its measured hole pattern X=+/-80.9, Y=-17+/-41.35 mm.
These four positions receive native FPE WGO40 M4 female load standoffs, 6 mm long and zero depth offset, on the upper face.
Ordinary holes or duplicate cavities are not added under native FPE hardware in the FPD input.
The standalone frame STEP deliberately excludes FPD-owned anchor machining; catalog envelopes in the support assembly are not a substitute for actual native geometry.

The main-panel supports are native WGO30 M3 female load standoffs of 20 mm, plus purchased 50 mm male/female extensions, making 70 mm shoulder-to-shoulder height.
Wurth 971500321 is a documented steel, gloss-zinc candidate: 5.5 mm hex flats, 6 mm M3 male thread, 7 mm M3 female thread.
An M3x10 socket screw through the 4 mm carrier and nominal 0.55 mm washer inserts 5.45 mm into the extension, leaving 1.55 mm nominal female-depth clearance.
The 6 mm extension male inserts into 10 mm usable thread in WGO30 at length20, leaving 4 mm nominal bottom clearance.
These are nominal compatibility checks, not torque or load ratings.

## Loads, thermal, environment, service

Load passes from router ears through four M4 standoffs into the frame, four M3 support screws, extension columns, native backpanel anchors and the enclosure supports.
Router mass, transport loads, cable loads and anchor capacities remain to be qualified; no vibration or shock rating is claimed.
The Bedrock's original Tile-to-adapter and adapter-to-backpanel thermal interfaces remain unchanged.
The frame underside is 13 mm above the existing Bedrock assembly's 57 mm upper bound; its central window avoids a solid plate immediately over most of the fins.
Keep the local-Y fin channels and their end passages open; the router above still affects airflow, requiring operating-temperature validation.
This internal frame adds no enclosure sealing function and makes no IP claim.
Disconnect the router cables and remove four accessible M3 carrier screws to lift the router and carrier together before servicing the lower Bedrock.
No lower TIM interface needs to be disturbed for routine upper-router removal.
Use a 2.5 mm hex key or long bit with a maximum 8 mm shaft envelope for at least the first 40 mm above the support screw.
Keep any larger bit holder above the router; a 10 mm nut socket is not the appropriate tool for these socket-cap screws and has no conservative connector-envelope margin at the two lower support positions.

## Material, manufacturing and deliberate form

Use 4 mm aluminum compatible with FPE's installed material catalog; required alloy and finished tolerances remain supplier-confirmed.
The large through-window and symmetric frame serve airflow and weight reduction; no decorative pockets or markings are added.
R8 outer corners, R5 window corners and 0.4 mm rim breaks retain the existing adapter radius vocabulary.
Deburr the four support bores to no more than 0.1 mm.
Nominal native load-anchor machining retains 1.85 mm in-plane web to the window and 3.05 mm to the external boundary before the adjacent edge breaks.
The four native anchor cavities use their native FPD manufacturing definition.

## Sources and unresolved items

Router mounting geometry is retained from `sce20-layout/references/router_oz/interfaces.json` and the normalized vendor STEP.
Bedrock envelope and thermal interfaces are retained from the verified Bedrock_FPE_R1 CAD variant.
Installed FPD `Config/Bolt.d/10-Base.ini` defines native codes, lengths and usable threads.
The extension specification is from [Wurth's 971500321 drawing](https://www.we-online.com/components/products/datasheet/971500321.pdf).
Actual FPD file validation, finished alloy/tolerance acceptance, column/anchor load and torque qualification, received fastener dimensions, cable bend radii and operating temperatures remain open.

## Verification and visual review

The frame STEP reopens as one valid solid with exact 180 x 210 x 4 mm bounds and a volume of 57225.481 mm3, corresponding to 0.154509 kg at 2700 kg/m3.
All 40 exported-frame/interface checks pass, including actual support bores, window throat and bevel, complete containment of nominal native anchor machining lands, 1.7 mm backing below the anchor-cavity envelope, and four diameter-7 column envelopes clear of the lower Bedrock by at least 1.5 mm.
The standalone frame and catalog-envelope assembly are distinct exports; only the final native export proves actual anchor machining and native hardware bodies.

The repository evaluation on 2026-09-09 passed for `exports/attempts/20260909-133014-af4544/carrier_R2.step`.
Its frame-only design review is 100.0, band A, role `plate`, with no waivers and full measured weight.
The role's proportion exemption is justified by the 4 mm-thick mounting interface; it is the only `not_required` metric.
The body edge-break floor measured 100 against 10 required, and sharp-edge floor measured 100 against 25 required.
Configuration delta is +7.0 points (default enclosure 93.0 to plate 100.0), within the cap; no metric is in error or absent-defect state.
The hard design bar was declared at 70 before the review.
The sole low finding is 96 mm of bare bore-rim edge; the manufacturing instruction limits bore deburr to 0.1 mm instead of applying the scorer's generic 0.4 mm lead-in.
No high finding remains.

The exported hero, top and isometric images were inspected: the frame has continuous inner and outer rim breaks, uniform side rails, symmetric support holes and no hole breakout or unintended geometry.
The empty center is functional airflow clearance; no blank slab or decorative texture was added.
These images and this score describe the bare frame, not the final native hardware or structural/thermal qualification.

## Actual native FPD export

The enclosing task saved and reloaded the native panel, verifying nine elements including four WGO40 M4 female load standoffs on the front at length6 and zero offset.
The resulting actual native file `C:/Users/KyleKassen/Desktop/Peplink_Carrier_R2_verified.stp` passed 45 independent geometry checks.
Its plate has a 146 x 160 R5 throat with corner-cylinder axes (+/-68,+/-75), and the correct 0.4 mm bevels on both window mouths.
FPD's width/height getters return the widened 146.8 x 160.8 mm bevel-mouth dimensions while its corner-radius getter remains5; this API convention did not change the exported throat.
The full native/reference plate symmetric difference is 1.205695 mm3 (1.150035 extra native metal and0.055660 missing), consistent with native 0.001 mm parameter quantization.
All four support bores, four anchor cavities and backing depths, four standoff axes, diameter-5 body envelopes and6 mm shoulders pass.
The native STEP represents each female thread as a 3.7 mm internal cylinder extending6 mm; native WGO40 identity governs actual M4 thread semantics, which cannot be certified by that simplified cylinder.
The actual-native hero render was inspected and shows the intended four posts, continuous frame/window bevels and no hole breakout.
The complete native audit, source SHA-256 hashes and actual-native views are retained under `references/`.
