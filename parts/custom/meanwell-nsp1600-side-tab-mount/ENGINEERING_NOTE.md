# NSP-1600 N2 — engineering note

**Preliminary side-mount prototype. Frame screening passes; countersunk-seat contact remains on HOLD. No complete-assembly strength or side-orientation power rating is established.** No fabrication, FEA, physical load test or powered thermal test was performed.

## Configuration and selection

The machined 6061-T6/T651 adapter has a 45 mm central spine, 72 mm maximum width, two 44 mm tab stations and 6.00±0.05 mm thickness. Four FPE M3 studs lie on a 57×252 mm pattern. Two McMaster 91294A190 M4×0.7×10 countersunk screws use the manufacturer's side mounting points at X2.3/Y−5.8 and −257.8 mm. Local tabs remove the continuous wide sides of N1. The CAD plate mass is 0.26746 kg at 2700 kg/m³; the manufacturer specifies a 1.8 kg supply. Use a provisional 2.2 kg complete-package allowance and verify by weighing.

## Loads and frame calculation

Assume stationary indoor service, 1g gravity plus 3g incidental acceleration, 50 N cable force and a separate 5 N·m couple from 50 N at 100 mm. Device force is 1.8×4×9.81+50=120.632 N, rounded to125 N. Package force is 2.2×4×9.81+50=136.328 N, rounded to140 N. These are resultants, not simultaneous full forces on every axis. Force-position bounds cover the body plan and heights85/91 mm above the device/panel interfaces.

Two collinear M4 screws alone cannot resist roll. The load path requires screw tension plus unilateral compression on verified metal side contacts, then plate bending into the studs. No friction, plastic or connector support is credited. A conservative15 mm contact lever gives maximum roll16.0006 N·m, contact reaction R=(1000M)/15=1066.7 N, with M in N·m and lever in mm and screw-tension bound1238.7 N. Carry1250 N tension/175 N shear per M4 into joint qualification. Allow all roll moment at either station; exact equal sharing is not assumed.

For each transverse frame, use span57.3 mm, minimum thickness5.95 mm and35 mm net width after a9 mm hole/seat deduction. With I=bt³/12 and Z=bt²/6, the correlated force/couple envelope gives maximum bending moment9.5276 N·m. Using N=172.03 N maximum net station-normal force and V=175 N in-plane shear, σ=1.5M/Z+V/(bt), τ=[1.5(R+|N|)+V]/(bt), and σVM=√(σ²+3τ²) give72.06 MPa. Here M is in N·mm; the1.5 bending multiplier is a selected modeling allowance, not a validated notch factor. Certified yield240 MPa gives **frame factor3.331** against the selected target3. E=70 GPa is approximate supplier guidance. Effective-strip and contact assumptions require prototype correlation.

The FPE station-frame demand reaches354.31 N tension. Proposed supplier/coupon qualification is500 N tension/250 N shear per stud, including prying and operating temperature; these are not supplier allowables.

## Contact HOLD and screw fit

At1250 N, the effective Ø7.6/Ø4.6 projected annular seat area is28.75 mm² and average bearing43.5 MPa. A3× contact-concentration sensitivity gives130.5 MPa and **yield ratio1.84**, below target3. Therefore **do not claim all plate checks pass factor3**. Seat pressure, reduced-head capacity, preload and chassis contact crushing require qualification. Verified toe patches alone would see approximately133–148 MPa if carrying the entire contact bound; actual loaded area and chassis strength are unverified. A failed coupon requires revised verified hardware/contact geometry, not a reduced acceptance target.

Gauge full seating, head flush to0.10 mm recessed, drawing boreØ4.5+0.1/0, countersink mouth≤8.2/angle≥89°, upper deburr≤0.10 and straight ligament≥3.90 mm. Ø4.4–4.6 is the conservative analytical bore envelope, not receiving tolerance. Worst calculated ligament is3.9165 mm. Nominal screw intrusion4.05 mm; assumed tolerances give3.75–4.35 mm against the manufacturer's5 mm maximum. The rear STEP has no modeled threaded receiver: inspect the real unit. Published side torque7–10 kgf·cm (0.6865–0.9807 N·m) does not independently qualify this head/seat/locking combination.

## Manufacture and validation

Machine certified1/4-inch or thicker stock; retain R4 tab transitions, specified finish and flat seating faces. Survey the actual pattern before countersinking. Preserve the designated FG connection and airflow. Side orientation requires manufacturer derating guidance and powered enclosure testing; horizontal ratings do not transfer. The provisional12 V rated-load example produces185.4 W typical conversion loss, with no panel-cooling or TEC-capacity credit.

Initial proof uses a surrogate reproducing paired screw-uplift/toe-download reactions, not isolated1250 N on an unsupported plate. Proposed1.5× proof limits:0.30 mm local elastic displacement,0.40 mm combined,0.10 mm residual. Qualify actual case, seats, FPE anchors and panel before complete-assembly proof. Follow the separate prototype plan; physical fit, contact integrity, retention and thermal release remain pending.
