# B210 direct stud plate - D1

Status: preliminary fit prototype; dimensioned geometry, not a released equipment installation.
This is a separate design from ettus-b210-professional-mount and its P2 revision.

## Function and concept decision

Attach the enclosed B210 directly to a thin metal adapter through the four under-foot housing inserts, then lower the adapter over four factory-installed Front Panel Express studs.
The user confirms M3 threads and estimates roughly 4 mm hole depth.
Short countersunk screws enter from underneath; their heads sit flush to 0.10 mm below the adapter's panel seating face.

An external cradle avoids reliance on case threads but adds retainers, height and parts.
Two separate mounting strips use less stock but are less convenient to align, handle and remove as one radio assembly.
The selected one-piece flat plate keeps the four housing and four panel interfaces registered, supports the flush insert ends, and has no bends, inserts or separate clamps.
The broad flat surfaces are functional contact faces; ribs, recesses and decorative features would impair this requested interface.
The role is `plate`: this is a thin interface whose hole patterns define its function, not an enclosure or a formed sheet bracket.

## Interfaces and datums

Units are mm.
The adapter is centered on X/Y, underside at Z=0 and radio pan underside at Z=3.5.
Datum A is the lower seating face; B the left edge X=-75; C the lower edge Y=-74.
The four radio axes are X=+/-46.7995, Y=+/-60.0075, measured by a fresh import and XCAF component audit of the supplied STEP.
The four FPE stud axes are X=+/-68, Y=+/-60.0075; their pattern is independently parameterized.
The 150 x 148 outline extends 13.8255 mm beyond each maximum case side; it stops inside the connector-bearing case ends.
The 6 mm supporting-panel coupon is reference geometry for this interface, not the user's complete FPE panel.
FPE stud bases and adhesive must be flush or below the supporting-panel seating surface.

## Evidence and limits

The original assembly has 196 valid solids; only the four named adhesive feet are omitted from the installed copy.
The four SOS_M3-10 inserts have flush end faces at the pan underside.
Original internal PCB screw tips begin 3.5738 mm above that datum.
That distance is a nominal CAD obstruction distance, not an allowable screw depth.
The selected M3 x 6 overall-length screw produces nominal 2.55 mm penetration with a 0.05 mm recessed head.
Actual accepted protrusion is 2.4-2.9 mm, provided every hole has at least 0.5 mm tip clearance and at least 2.0 mm effective complete thread engagement after both entry and tip incomplete threads.
No removal or modification of existing internal screws is authorized by this design.

## Loads and load path

Preliminary stationary indoor service inside the user's box is assumed pending application loads.
A 1.0 kg radio allowance, gravity plus a 3g handling increment, 20 N cable force, 50 mm load height, and 1 Nm free cable couple are analytical screening assumptions.
The device transfers load through its four inserts and screws, through the aluminum plate to its exposed ears, washers/nuts, FPE studs and the supporting panel.
No friction-only retention is credited; shear is ultimately carried by bearing against screw/stud shanks after clearance take-up.
Insert attachment strength, FPE stud anchorage and the support panel's ultimate load path need supplier data or physical qualification.
Stationary plate-facing-up operation is the initial intended orientation; other orientations require joint verification and application load review.

## Thermal, environment and service

No heat-transfer credit is assigned to metal contact.
The mount preserves connector ends and lateral features; cable space remains an installation envelope, not verified actual cable geometry.
Official B2xx limits of 0-40 C ambient and noncondensing service govern the preliminary environment, subject to the actual assembled configuration.
There is no outdoor/IP, vehicle, airborne, overhead or vibration certification.
No electrical isolation is provided and the contact is not a qualified grounding connection.
Remove four exposed nuts and lift radio plus adapter off the studs; remove the four underside screws on a bench to separate the radio.
Removal frequency is unconfirmed; this is an occasional-service interface.

## Material, manufacture and finish

Machine from certified 6061-T6/T651 aluminum stock of sufficient thickness, nominal 4 mm, face symmetrically to 3.50 +/-0.05 finished thickness.
Use two-sided CNC work with a sacrificial fixture; avoid distortion from clamping a thin unsupported plate.
Contour R8 corners, drill the two hole families, machine four underside 90-degree seats, and apply 0.4 x45-degree outer rim breaks.
Small bore-mouth deburrs are 0.10 mm maximum and must not defeat the controlled countersink seat.
Specify clear chemical conversion to MIL-DTL-5541 Type II Class 3 by a qualified supplier; fit requirements apply after finish.
No bends are needed; the DXF is the planar manufacturing geometry and a formed-sheet flat pattern is not applicable.

## Deliberate form and completed review

The regular two-row patterns share Y stations; rounded outside corners and a continuous aligned finish are the only styling features.
The original vendor STEP and earlier designs remain unchanged.
CAD validity, exported-geometry reopen, section inspection, assembly collision, tool/cable-envelope and removal checks passed; physical fit is still untested.
The design review uses the plate role with no waivers, minimum score 70 and edge-break coverage 60.

### Measured design review - 2026-09-08

The exported `exports/plate_D1.step` measures **89.1, band A, role plate**, with all metric measurements successful and no floor failures.
The identical gate-exported artifact is `exports/ettus-b210-direct-stud-mount_v1.step`; the full report is retained beside it.
The edge-break body floor requires 10 and measures 100, margin 90; sharp-edge floor requires 25 and measures 100, margin 75.
The role configuration contributes +15.1 points relative to the default enclosure score 74.0, within the permitted role cap 28; no waiver contributes points.
This difference is justified by the function: both broad flat faces are mating surfaces and the hole patterns define the adapter.

| Self-critique | Specific result |
| --- | --- |
| Edge treatment and radii | R8 plan corners and 0.4 mm outer breaks; top bore deburr and underside countersink are controlled separately. All body edge lengths and bore rims counted as broken. |
| Face composition | The algorithm reports an empty R73.6 region and scores face composition 0.8. This high finding is intentionally retained: a pocket or rib field would remove required broad contact and add fabrication cost without a validated benefit. No score waiver was used. |
| Pattern discipline | Two symmetric four-hole families, sharing Y stations; measured feature and pattern scores 100. The radio pitch is measured, not forced onto an arbitrary grid. |
| Symmetry and proportions | X/Y symmetric thin interface; proportion is correctly not required for the plate role. |
| Feature transitions and texture | There are no added connector bosses, texture, seals, weather details or structural ribs. They are inapplicable to this flat mating interface. |
| Service | Four exposed stud nuts release the radio/adapter as one unit; hidden housing screws are accessed on a bench. |
| Minimum material | STEP cylinder faces independently measure nominal 2.05 mm straight throat; drawings and calculations require at least 1.80 mm actual after all cuts. |
| Visual review | Actual CAD hero, underside, exploded, section and orthographic views inspected. Corners, finish, screw spacing and accessible stud ears are coherent. Purchased hardware remains visibly simplified and the source radio lacks supplier texture/labels; these are visualization limits, not fabricated product details. |
| Manufacturing crosscheck | The explicit DXF profile plus eight drill operations has zero symmetric difference from the STEP at the straight midsection. |
| Qualification | The appearance score and CAD passes do not validate insert, FPE anchor, preload, vibration or thermal capacity. |

No metric is in error or absent-defect state; only the role's proportion exclusion is not required.
The low face-composition score is retained transparently rather than adding functionless geometry.

## Unresolved release items

Actual useful thread engagement, tip clearance, insert coplanarity, housing attachment strength, received screw head form, actual device mass and cables, FPE stud tolerances/capacity/torque, panel support span, operating heat load and service locking procedure must be confirmed.
These do not prevent producing reviewable prototype CAD, but do prevent a production installation release.
