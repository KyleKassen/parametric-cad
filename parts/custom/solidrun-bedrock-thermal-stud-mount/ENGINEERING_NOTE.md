# T1 engineering note

**Preliminary fit and thermal prototype; no complete-system load or cooling rating.** The custom adapter is ready for machining review and controlled prototype qualification. The original computer STEP and previous mount designs are preserved.

## Concept selection

| Concept | Retention / service | Thermal / manufacturing tradeoff |
|---|---|---|
| Direct metal plate, dry joint | Six screws and four removable stud nuts; one custom part | Few operations, but unknown dry contact resistance and face flatness |
| Metal plate with full soft pads | Same fasteners; forgiving larger gaps | Pad pressure and creep burden shallow unverified threads; a 130×160 mm pad at only 10 psi requires about 1.43 kN |
| **Machined plate with thin grease fields and solid lands — selected** | Positive bolted retention; grease does not set grip; remove four panel nuts for service | Two precision shallow recesses require flatness/coverage inspection; avoids relying on a thick compressible pad |

The selected **166×184×5.10 mm** certified 6061-T6/T651 plate weighs **0.412 kg** in nominal CAD. Thickness provides countersink ligament, stiffness and heat spreading while accommodating the stock M4×8 overall screw length. It is a two-sided machined part with no bending or sheet-metal development. R8 corners, aligned exposed stud ears and consistent 0.4 mm external edge breaks define the visible form.

## Geometry and evidence

Measured from the actual STEP: 22 valid bodies include three alternative chassis, with Tile body index 19 and 60 W body 20 (zero based). Coordinate normalization gives the Tile at Z0..29, X[-65.762,65], Y[-80,80] mm. Six attachment axes are (-60,-70), (60,-70), (0,-40), (0,30), (-50,70), (50,70) mm. Entry cones extend 0.584 mm, the modeled thread region ends 3.500 mm, and the drill tip reaches 4.501 mm. A thin wall closes each bore before the internal cavity; the drill tip is not usable full-diameter engagement.

Official SolidRun documentation describes Tile cold-plate attachment and cooling from either side, but recovered guidance does not establish allowable penetration/preload for these six side holes. The user's M4/~4 mm observation remains approximate. Manufacturer dimensions distinguish Tile 29×160×130 and the original two-bank 60W73×160×130 mm variants. The requested model uses actual Tile geometry plus **one clipped opposite fin bank** and 19 source auxiliary bodies. Its 132.957×170×51 mm derived envelope verifies spatial representation only, not physical bank interchangeability or a 60 W rating.

Adapter datums: A is the lower seating plane Z0; B is X=-83; C is Y=-92. Stud axes are X±76,Y±82, a 152×164 mm pattern. The reference main panel is 200×220×6 mm; its material, full size, supports and TEC coupling require final FPE/enclosure design. All delivered STEP coordinates are millimetres.

## Loads and results

Inputs are assumptions unless stated otherwise:1.5 kg computer,2.1 kg package,9.81 m/s² gravity plus 3 g incidental handling,20 N cable force and an independent 1 N·m couple (20 N at 50 mm). The force screen is 80 N at the device and 110 N at the package; force/couple direction is unrestricted within those resultant bounds. CG position is bounded anywhere in X±65/Y±80 with device height 51 mm and package height 60 mm. These are stationary indoor handling screens, not a vibration/shock qualification.

The device transfers compression through the hard lands and surrounding plate into the main panel. Six M4 screw joints and four M3 stud joints carry uplift and in-plane force after clearance take-up; no friction or grease adhesion is credited. Connectors and fins are outside the load path.

The asymmetric six-point elastic group balances force and moments using N=B(BᵀB)⁻¹[Fz,-My,Mx]ᵀ, B rows=[1,x,y]. Maximum screened M4 demand is 68.74 N tension/38.13 N shear; local plate checks use 75 N in each direction. FPE maximum demand is 87.77 N tension/55.09 N shear before unresolved prying/preload effects. Supplier/representative-joint qualification is proposed at 200 N tension with 100 N shear per stud; this is a demand, not a catalog rating.

With certified room-temperature yield≥240 MPa, E≈70 GPa, minimum plate core 4.93 mm and target factor 3, local strip bending is governing at **4.28 yield factor**. Whole-plate strip, countersink punching/bearing and stud bearing/tear-out screens also exceed 3. The conservative free-strip displacement estimate is 0.896 mm at 75 N; the actual seated plate/contact joint was not solved, so hot interface gap must be measured independently. No assembly factor is claimed from this plate-only result. Preload, female-thread stripping, reduced screw-head capacity, FPE anchorage/pullout/prying and panel support remain unqualified.

The adjacent detailed report records equations, inputs, tables and sensitivities, including thread shear, local crushing and combined stress. No FEA was used: missing contacts, materials and joint allowables would make a nominal simulation misleading.

## Screws and tolerance stack

McMaster 91294A188 is the selected candidate M4×0.7×8 DIN7991,90° flat head. Nominal projection is 8+0.05-5.10=**2.95 mm**. Assumed stock length±0.20, plate±0.05 and head recess 0..0.10 give 2.65..3.25 mm; therefore nominal size alone does not prove fit.

Physically accept only 2.85..3.00 mm measured projection, ≥2.00 mm complete engagement after all entry/thread-phase/tip losses, ≥0.50 mm axial clearance to the verified full-diameter blind limit and no internal interference. These simultaneous proposed criteria may reject an ordinary stock screw. Require actual headflush 0..0.10 mm belowA,≥3.00 mm straight throat and the section drawing's minimum contact/seat geometry. Do not adopt a deeper screw or machine the computer without measured evidence and manufacturer authorization. No torque value is inferred.

Four M3×12 FPE load studs with 0.55 mm nominal washers and 4 mm nuts leave 2.35 mm nominal exposed tail. Confirm actual nylon engagement and≥two complete exposed threads. The nylon-insert nut catalog limit is 85°C, not an assembly ambient rating. FourØ3.8 holes provide 0.4 mm nominal radial clearance over M3; proposed position controls consume 0.05 mm plate+0.15 mm stud radial error, leaving 0.20 mm nominal for assembly/thermal variation. Actual FPE capability and stud projection must be confirmed.

## Thermal and manufacturing decisions

Use McMaster 10405K83 Dow 340 noncuring compound on both faces. Each 126×156 R5 field is 0.050±0.010 mm deep, withØ8 top hard lands andØ10 underside countersink lands. Two 1 mm wide escape grooves per face atY±20 open to+X. Nominal filled volumes are 0.969/0.961 mL; qualify dispense dose rather than forcing that volume into a closed assembly. Actual bond lines must remain filled, greater than zero and below 0.10 mm. Metal contact defines grip; the grease is not a structural adhesive, electrical isolation barrier or ground bond.

Using 19,000 mm² effective area, greasek=0.67 W/(m·K), aluminumk=150 W/(m·K) as a conservative typical screen and R=t/(kA), both nominal 0.05 mm TIM layers plus 5.10 mm adapter and 6 mm reference panel give **R_bulk=0.01175 K/W**. Drops at 10/30/60 W are 0.118/0.353/0.705 K. At 0.10 mm comparison gaps the 60 W drop is 1.176 K; this boundary case does not relax the actual<0.10 mm requirement. Real contacts, finish, voids, spreading and panel-to-air resistance are excluded. Manufacturer high-pressure grease-impedance values were not substituted for this unknown preload.

The TEC cools the enclosure per the user. No direct cold-side bond is modeled. One fully exposed 200×220 mm panel face would require h≈68.2 W/(m²·K) to reject 60 W within an illustrative 20 K panel-air difference; h, available face area, air temperature and actual TEC capacity are unknown. The plate's small bulk temperature drop does not establish complete-computer cooling. Validate the real workload, all enclosure heat, TEC hot-side rejection and fin airflow. The fin bank's cooling is a parallel path with no assigned credit.

Machine from certified stock with enough cleanup (nominal 6 mm or 1/4 inch), in balanced supported setups; inspect free-state flatness and unclamped dimensions. Face both sides, contour/drill, mill the shallow fields/escape grooves, finish countersinks with received hardware gauges, deburr and clean. Toolpaths must reach around the hard islands and through the 1 mm escape grooves; STEP controls their outer-bevel intersection. Specify Ra≤1.6 µm thermal floors,0.03 mm land flatness and 0.03 mm top-to-A parallelism. These machining limits do not alone guarantee the gap against an unknown Tile/panel. Apply clear MIL-DTL-5541 Type II Class 3 conversion, no thick coating/anodize on thermal lands; gauge after finish and include its contact resistance in thermal tests. No device finish removal is assumed.

## Completed verification and open items

- **94 nominal CAD checks passed:** solid validity, original hash, eight STEP export/reimports with units/count/bounds, nominal fit, expected thread-proxy overlap distinguished from unintended interference, socket envelopes, removal samples and generic cable reservations.
- **60 independent manufacturing checks passed:** STEP geometry/second roundtrip,10 bores/6 countersinks, thermal pocket sections and lands, escape grooves, and DXF coordinates/contours/units.
- Arithmetic and CAD-parameter checks passed in the reproducible calculation source. Actual assembled/underside/exploded/orthographic/vertical/section CAD views were inspected.
- The retained repository **appearance** rubric is 67.4/100, below its initially selected 70 threshold; its raised edge score also failed. It counts 50 µm functional recess steps as sharp body edges and penalizes the manufacturer-fixed six-hole pattern. Outer edges are broken; adding its suggested 0.4 mm chamfers to these steps would destroy the thermal depth/lands. No geometry, score or rubric floor was disguised to claim a pass. See DESIGN.md and `references/quality/appearance_review_T1.json`.

Production remains on hold for actual hybrid configuration, six thread/seat gauges, approved locking/preload, FPE anchor/position/temperature limits, final panel supports, complete-cable fit, thermal contact and actual TEC operating qualification. No fabrication, purchase or physical validation occurred. Follow `PROTOTYPE_VALIDATION.md` and the detailed `references/engineering/engineering_checks.md` before release.
