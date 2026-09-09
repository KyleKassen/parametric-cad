# SolidRun Bedrock thermal stud adapter - T1

Status: preliminary fit and thermal prototype; actual housing, thread, thermal contact and FPE joint qualification remain open.
This is a new sibling design and does not revise the previous B210 or Bedrock mounting studies.

## Function and selected concept

Fasten the six threaded holes on the flat Tile side of the user's Bedrock V3000 to a metal adapter with recessed countersunk screws.
Attach that adapter to the main FPE panel over four factory-installed studs, keeping both interfaces thermally conductive.
The user specifies one 60 W heatsink on the opposite side and a thermoelectric enclosure cooler.
The cooler model, setpoint, computer load, airflow and direct cold-side connection are not confirmed.
The preliminary system model therefore includes heat transfer from the main plate into TEC-cooled enclosure air; no direct cold-face coupling or total cooling capacity is assumed.

A bare bolted plate gives the fewest operations but uncontrolled thermal contact.
A full-area soft pad accommodates gaps but its compression pressure can impose substantial force on six shallow housing threads.
The selected plate uses two shallow grease fields with hard metal contact lands, separating structural grip from the nonstructural thermal compound.
McMaster Dow 340 compound is selected conditionally for measured gaps below 0.10 mm; this is a precision-fit interface, not a large-gap filler.

The design role is `plate`: two functional mating faces and their attachment pattern define this thin interface.
Broad unbroken metal and thermal fields are functional; decorative ribs or lightening windows would interrupt the requested conduction path.

## Ground truth and datums

Source `Bedrock V3000 Basic 3D model.step` contains 22 solids, including three overlaid alternative chassis.
The component-library and project copies have identical SHA256 `80714a02ccf0ba999e2d004db3d40b22f86bf4f631081086a0ba262754f6b8b2`.
Fresh audit identifies Tile index 19, 60 W index 20 and 30 W index 21, with 19 shared auxiliary bodies; numeric indices are zero-based and guarded by the exact input hash.
The user's requested one-bank assembly is derived from the Tile and the actual positive-X bank of the 60 W body; it is not a separately supplied vendor configuration or a proven 60 W cooling rating.

The normalized device frame is (X,Y,Z)=(vendor Y, vendor Z-80, vendor X+14.5), with Tile mating face Z=0 and the opposite fin bank extending to Z=51.
Six measured hole axes in this plane are (-60,-70),(60,-70),(0,-40),(0,30),(-50,70),(50,70) mm.
Entry cones run 0-0.584 mm inward; modeled thread features extend to 3.500 mm; drill-point tips reach about 4.501 mm.
The drill point is not full-diameter screw space.
The user reports likely M4 and approximately 4 mm depth; physical thread/engagement and blind-end checks remain required.

Adapter datum A is its lower main seating plane Z=0; B is its left edge X=-83; C is lower edge Y=-92.
The Tile rests at Z=5.10 on hard lands; grease occupies recessed fields, not an added structural spacer.
Four FPE stud axes are X=+/-76,Y=+/-82; the pattern is parameterized independently.
The 200 x 220 x 6 mm FPE panel is a reference interface coupon, not the customer's final plate.

## Load path, thermal path and service

Six M4 screws close clamp load through screw heads, adapter hard lands and the Tile's actual threaded wall.
The adapter transfers load into four exposed stud ears, washers/nuts, FPE anchors and the final panel support.
No friction-only retention or thermal-compound adhesion is credited.
Initial load assumptions are a 1.5 kg computer allowance, 2.1 kg package allowance, gravity plus 3 g handling, 20 N cable force and 1 Nm independent cable moment.
Unknown screw-head, shallow female-thread, FPE anchorage and main-panel capacities are not replaced by a plate-only calculation.

Heat crosses Tile -> top compound -> aluminum adapter -> bottom compound -> main plate -> actual cooling boundary.
The opposite fins remain unobstructed and form a parallel heat path; their contribution is not assumed equal to the original two-bank product's rating.
Cases of 10/30/60 W through the plate will be screened, including unknown contacts, spreading and plate-to-air resistance.
Install with the fin channels vertical for the manufacturer's preferred natural-convection orientation, or validate forced-air operation for another orientation.

For service, disconnect cables, remove four stud nuts/washers and lift computer plus adapter off the studs.
Inspect and renew the exposed lower compound layer before reinstallation.
Separate the computer and adapter on the bench by removing the six underside screws; renew the upper compound afterward.
Thermal grease is not an electrical safety barrier, ground bond or permanent locking mechanism.

## Material, manufacture and tolerance plan

Machine certified 6061-T6/T651 flat stock to 5.10 +/-0.05 mm finished thickness, requiring at least 240 MPa certified room-temperature yield.
Use nominal 6 mm or 1/4-inch starting stock with sufficient cleanup and supported two-sided workholding.
Machine a 126 x 156 R5 thermal field 0.050 +/-0.010 mm deep on each face.
Keep six diameter-8 mm hard lands on the Tile side and diameter-10 mm lands around the underside countersinks.
The outer profile is 166 x 184 with R8 corners and 0.4 mm outer rim breaks.
There are no bends or sheet-development allowances.
Use clear chemical conversion MIL-DTL-5541 Type II Class 3; actual gap and dimensions apply after finish.
Require finished thermal-field roughness Ra<=1.6 micrometres and physically verify that assembled gaps remain filled and below 0.10 mm.
Do not remove or abrade the computer's finish by default.
If the actual Tile or FPE panel cannot meet the gap requirement, the selected Dow 340 stack is not acceptable; revise the interface with a qualified gap filler rather than assuming contact.

M4 x 8 overall-length flat-head screws give nominal projection 8+0.05-5.10=2.95 mm.
Proposed physical acceptance is 2.85-3.00 mm projection, at least 2.00 mm complete thread engagement after entry/tip losses, and at least 0.50 mm to the verified full-diameter blind-hole limit.
These conditions must be satisfied together with the received screws; the nominal length alone does not prove compatibility.
Six screws use 2.5 mm hex drives; the panel nuts use a 5.5 AF socket of no more than 10 mm OD.

## Unresolved and required validation

Confirm the actual Tile/one-bank configuration, all six threads and their permitted preload, real screw tips and heads, computer mass, contact flatness and compound spread, FPE stud tolerances/strength/torque, final plate area/support and the TEC cooling boundary.
Quantify actual computer heat and allowable temperatures before assigning total thermal capacity.
No vehicle, airborne, overhead, outdoor, shock-spectrum or vibration qualification is claimed.
Completed CAD, engineering and visual review results are recorded below.

Two 1 mm wide, 0.05 mm deep escape grooves per face connect the thermal field to the +X perimeter at Y=-20,+20. They relieve trapped air and excess compound; no thermal-area credit is assigned outside the primary field. Keep overflow away from I/O, threads and electronics.

## Final verification and appearance review

T1 exports contain 43 distinct assembly components; the adapter is one valid solid, 152561.321 mm³ and 0.411916 kg at 2700 kg/m³. Source SHA256 is unchanged. The 94 nominal CAD checks and 60 independent manufacturing checks pass. Reopened STEP files preserve millimetre scale, component counts and bounds; complex source-body reserialization volume drift stays below 10 ppm. Actual product, exploded, underside, orthographic, vertical and critical screw-section views were reviewed. The 94 checks are functional geometric checks, not physical validation or thread/thermal qualification.

The repository appearance review of the actual exported shape is **67.4/100, band C, role plate**, below the selected hard 70 threshold. The raised edge composite score is 46.6, below 60. Both nonwaivable rubric floors are met: edge body 46.4 versus 10 (margin 36.4), sharp-edge 58.06 versus 25 (margin 33.06). The configuration delta is+9.5 versus default 57.9, entirely the honest plate role; role allowance 28, waiver allowance 25, waiver delta 0.0. No score or floor was changed to manufacture a pass.

Unfixed high finding `scattered_features` is explicitly accepted on functional grounds: all six housing axes come from the actual vendor STEP and user-requested attachment; changing them to constant pitch would destroy fit. The medium sharp-edge runs are 50 µm thermal-recess boundaries and dry-land transitions, held burr-free to preserve the thin gap. A0.4 mm chamfer orR0.4 there is physically inconsistent with the specified 50 µm relief. Low sharp-rim and empty-face recommendations likewise concern the tiny island/recess boundaries and intended continuous thermal field; deeper recesses/ribs would break this conduction interface. These findings remain in the retained report, unhidden and unrescored. This is a documented functional exception to the generic aesthetic heuristic, not a waiver of solid validity, manufacturing inspection or physical acceptance.

The full evaluation is retained at references/quality/appearance_review_T1.json. Its attemptSTEP is geometrically matched to plate_T1.step by the final delivery geometric check; timestamps in STEP headers are not geometry. The prototype remains unreleased until actual threads, screw seats, configuration, FPE anchors, contact coverage and TEC thermal performance are qualified.
