# B210 direct-stud mount — preliminary engineering screen

This report covers the machined adapter plate. It does **not** rate the radio's clinched standoffs, screw heads, FPE bonded studs, main panel, or completed assembly. No physical test or FEA was performed. The standard-library source and JSON beside this report reproduce the arithmetic.

## Geometry and evidence

Final working layout: 150 ×148 ×3.5 mm full 6061 plate; thickness 3.50 ±0.05 mm, R8 outside corners and 0.4 mm rim breaks. Four housing axes are X ±46.7995/Y ±60.0075 mm, measured from the supplied STEP. Four FPE stud axes are X ±68/Y ±60.0075 mm, selected for this mount. No window or housing-face relief is credited. The four flush standoff end faces must bear directly against the plate. Physical coplanarity and full contact must be confirmed.

The STEP identifies SOS-M3-10 standoffs; the user confirms M3 and approximately 4 mm available depth. The modeled opposing PCB screw tips are 3.5738 mm above the pan underside. Neither approximate physical depth nor that CAD coordinate is an allowable penetration. Actual screw interference, lead/chamfer and thread capacity remain inspection items. The flat-head screw candidate is McMaster 91294A126, M3×0.5×6, 90°, DIN 7991. Its received geometry controls the countersink.

The FPE interface should use its documented flush cavity installation. **Default: no relief in the adapter around the stud bases.** Inspect the stud base and adhesive flush or below the main-panel seating plane. A Ø12.6×0.3 adapter relief would remove local nut support and is outside this analysis; revise the preload/contact model before adding it. Do not force a rocking plate down with nuts.

## Loads and support assumptions

Radio mass allowance 1.0 kg; complete package allowance 1.3 kg including this plate and hardware. Neither is a measured device mass. The uncut rectangular plate mass upper bound is 0.2098 kg; the root CAD volume 77,078.860 mm³ corresponds to 0.2081 kg at 2,700 kg/m³. The package allowance leaves approximately 0.09 kg for hardware after the radio allowance. Weigh the assembly before accepting it.

With g=9.81 m/s², 3 g incidental inertia plus 1 g gravity and 20 N cable force, F_device=(3+1)×1.0×9.81+20=59.24 N. The package equivalent is 71.01 N. Screen 60 N resultant at the housing and 75 N at the panel studs. Add a separately bounded 1 Nm free couple; 20 N×50 mm=1 Nm motivates it. Including both a 50 mm force height and the additional couple is deliberately conservative. Force and couple may act in any direction, each within its resultant bound; this is not a 60 N-per-axis requirement. The CG/load height ≤50 mm is an assumption requiring confirmation.

The rigid main panel supports compression; positive screw/stud geometry transfers shear and uplift. Friction receives no retention credit. The four-point groups restrain translation and rotation when fully seated and retained. Hole clearance permits small motion before bearing, so cable strain relief and properly qualified locking/preload are still needed. This is stationary indoor equipment, not a vibration, vehicle, outdoor or overhead qualification.

## Bolt-group forces

For points(±a,±b), Σx²=4a², Σy²=4b² and J=4(a²+b²). Elastic normal reaction is N_i=F_z/4+M_x y_i/Σy²−M_y x_i/Σx². For a force at height h and independent free-couple magnitude C, N_max=F/4 sqrt[1+(h/a)²+(h/b)²]+C/4 sqrt[1/a²+1/b²]. Shear is bounded by V_max=F/4+C/(4 sqrt[a²+b²]).

- Housing handling reaction: tension ≤32.03 N and shear ≤18.29 N at any point.
- FPE handling reaction: tension ≤33.59 N and shear ≤21.51 N at any point.
- Plate/housing local screen: 60 N axial and 60 N shear, a reserve above the elastic group result.
- Required FPE supplier/qualified-joint envelope: 150 N tension with 75 N shear per stud. This is a **demand reserve**, not an FPE allowable or a proven prying bound. It is 4.47× the elastic tension and 3.49× the elastic shear.

These group reactions omit preload and prying. Panel contact outside a stud can increase stud tension. The complete contact/preload geometry and FPE adhesive performance must be qualified. Main-panel global bending, stud bond failure, nut pull-through and pan/clinch pullout are not proved by the plate calculation.

Cable routing may give a larger lever arm than the 50 mm baseline assumption. As a sensitivity check, a 2 Nm free couple (20 N at 100 mm) raises the housing tension/shear bounds to 38.81/21.57 N and FPE bounds to 39.14/24.26 N. These remain below the selected local demands. Measure the actual plug/strain-relief force lever; the 1 Nm baseline is an assumption, not a measurement of connector geometry.

## Plate bending and failure screens

Use certified unwelded 6061-T6/T651 stock matching the supplier's thickness range: minimum yield 240 MPa. E=70,000 MPa is a room-temperature reference input, not a guaranteed lower bound. A sensitivity check at 68,300 MPa increases every deflection by 2.49%, without changing static stress. Target factor 3 against material yield accounts for the preliminary service loads and a simplified beam model; it does not cover unknown joints. No elevated-temperature or fatigue allowable is assigned.

At each row, an assumed 35 mm effective continuous band is reduced to 28 mm over the entire span for holes and breaks. The effective width is a simplified plate-to-beam idealization requiring physical correlation, not a solved plate contact result. Minimum thickness is 3.45 mm; span L=136.300 mm and transfer arm a=21.4005 mm include position allowances. I=bt³/12=95.815 mm⁴ and Z=bt²/6. Two internal forces each ≤P=60 N give M≤Pa=1284.03 Nmm without assuming fixed stud rotations. Apply a selected 1.5 bending stress factor, add a simultaneous axial P/(bt), and conservatively add two 1.5V/A shear screens in the von Mises combination. This factor is an engineering screening choice, not a notch-factor simulation or test.

For equal forces, loaded-point deflection δ=P a²(3L−4a)/(6EI)=0.221 mm; the unrestrained beam center is 0.430 mm. Full plate action, the rigid radio and compression contact can reduce displacement; none is credited. These are ideal-beam estimates, not guaranteed bounds for joint prying or contact redistribution.

| Plate failure screen | Yield factor |
|---|---:|
| plate bending combined | 6.77 |
| countersink punching | 43.10 |
| countersink average bearing with factor 3 | 21.20 |
| plate stud hole bearing with factor 2 | 13.25 |
| plate stud hole tearout | 62.46 |

Minimum screened plate factor=6.77; target 3 is met for these assumptions. It is **not a minimum assembly safety factor**. Stud-hole tear-out uses two minimum edge ligaments, t_min and the 75 N shear reserve. Bearing uses a conservative 2.4 mm effective stud width and a selected factor 2. Deburr all holes and preserve the continuous bands; any notch/window/relief requires regeneration and reassessment.

## Countersink, end-face bearing and preload

Screen the countersink mouth ≤6.2 mm, throat ≥3.3 mm and included angle ≥89°. The maximum conical depth is (D−d)/(2 tan[α/2])=1.476 mm, leaving ≥1.974 mm of material above the cone. Deducting the upper 0.10 mm bore deburr leaves a calculated straight cylindrical throat ≥1.874 mm; nominal straight length is 2.05 mm. The drawing/receiving minimum is **1.80 mm actual straight throat after all cuts**, and the punching calculation conservatively uses that lower acceptance thickness. Manufacture the nominal Ø6.1/90° seat using received hardware to achieve **flush to 0.10 mm recessed; never proud**. Mouth size alone does not guarantee flushness. Inspect angle, actual head seating and ligament; do not deepen the cone beyond the screened envelope to repair wrong hardware.

The bearing screen requires actual effective cone seating diameter ≥5.7 mm and throat ≤3.5 mm. Its projected area is 15.896 mm², giving 6.291 MPa per 100 N of total screw force. Punching uses π d_min×1.80=18.661 mm²; these are simple average-stress screens, not a resolved contact analysis. The plate's top opening can reach 3.70 mm including the deburr. After subtracting this opening, each modeled 4.8 mm-across-flat hex end face has approximately 9.201 mm² available bearing area, or 10.868 MPa per 100 N. The 4.8 mm end-face dimension is nominal model evidence, not an inspected tolerance.

The screw clamp-load path should close through screw head→plate→flush standoff end face→standoff thread. Recessed or noncoplanar standoffs can instead bend the thin pan; reject that condition or redesign with measured bearing geometry. Preload is **not** included in the 60 N external-force plate table. Supplier-approved installation preload/torque must also satisfy head seating, aluminum bearing, female thread, clinch and FPE limits. No torque value is invented here. Use the approved locking method and verify it after removal cycles; torque alone does not establish preload.

## Screw penetration and unknown joint strength

For an overall-length countersunk screw, projection=L−t+recess. Assuming—not sourcing—a 6.0±0.2 mm length, t=3.50±0.05 and recess 0–0.10 gives projection 2.25–2.85 mm (nominal 2.55). The STEP separation at maximum projection is 0.7238 mm. **Measure every installed projection and actual internal obstruction**; require ≥0.50 mm tip clearance and ≥2.0 mm complete, usable thread engagement after both entry and screw-tip lead loss. At the low projection extreme only 0.25 mm combined lead loss is available, so the nominal tolerance stack alone cannot guarantee engagement. Select/gauge screws and reject an incompatible stack. Approximately 4 mm reported depth is insufficient as a go/no-go penetration measurement.

The 2.0 mm full-engagement criterion equals four M3×0.5 pitches. It is a **proposed application criterion**, not a universal standard or a manufacturer-approved housing capacity. A deliberately reduced thread-shear surrogate A_s=0.25π×2.5×2.0=3.927 mm² would require female-material yield ≥79.4 MPa for a 3× shear-yield factor at 60 N and zero preload; each additional 100 N preload adds 132.3 MPa to that requirement. This is a demand calculation only. Actual material, thread form, lead, clinch and load distribution are unverified, so no female-thread capacity is claimed.

Using the standard M3 tensile area 5.03 mm², 60 N tension plus 60 N shear gives a shank equivalent stress 23.86 MPa. The selected flat-head product's strength/class listings do not establish its reduced-head capacity; ISO/DIN countersunk screws can have reduced loadability. Thus the shank calculation is not a screw-head or assembled-joint safety factor.

## Required physical validation

1. Inspect material/finish and all critical dimensions. Confirm the selected M3 screw, its usable tip/lead, standoff end-face contact and alignment, effective ≥2.0 mm engagement,≥0.50 mm actual tip clearance, and flush/recessed head condition. Check the entire underside on a flat witness surface. Confirm received FPE stud geometry, height, seating plane and supplier allowable loads/torque.
2. Weigh the radio and completed assembly. Confirm the mounting panel is rigid and the load/CG assumptions cover the installation. Obtain housing/clinch and FPE joint approval, or run a qualified representative joint test before accepting service. Do not apply an unexplored stud/insert proof load to the real radio.
3. Prototype the plate with a rigid four-point surrogate and representative panel/studs. Apply the 60 N resultant+1 Nm device service wrench in adverse orientations and corresponding 75 N package wrench; inspect slip, lift, cracking, contact and loosening. A separate **mount-only** surrogate test may apply 90 N at each of two same-row housing points (1.5× the 60 N local reserve). The ideal beam predicts loaded-point/center elastic motion 0.331/0.645 mm for that local proof. Proposed prototype acceptance: loaded-point ≤0.5 mm, center ≤0.8 mm and residual ≤0.10 mm; correlate measured behavior and reassess if contact differs. These are design acceptance proposals, not completed tests.
4. With the real radio under normal operation, verify all plugs mate, cable/tool access, cable bends and strain relief, removal sequence and original enclosure ventilation. Compare temperature/operation against an unmounted baseline at expected indoor ambient and duty cycle. Broad plate contact is not evidence of improved cooling. Confirm grounding/isolation intent; anodized contact is not a qualified protective bond.
5. Repeat removal/reinstallation and inspect threads, seating, countersinks, panel bond and locking. Add application-specific shock/vibration/environmental qualification only after requirements exist.

## Sources and reproducibility

- [thyssenkrupp 6061 data sheet](https://d2zo 35mdb 530wx.cloudfront.net/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf): certified T6/T651 sheet/plate minimum yield 240 MPa and modulus 70 GPa; room-temperature screening only.
- [Bossard metric fastener materials](https://www.bossard.com/global-en/-/media/bossard-group/website/documents/technical-resources/en/f-004-en.pdf): M3 nominal tensile stress area 5.03 mm².
- [Bossard countersunk fastener notice](https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/2103/): head geometry can reduce loadability.
- [McMaster 91294A126](https://www.mcmaster.com/91294A126/): selected candidate geometry; see the project procurement evidence for the live product record.
- Supplied STEP and the project's under-feet geometry audit: axis pattern, end-face geometry and opposing internal screw-tip location.
- FPE package/research evidence elsewhere in this project: flush-cavity geometry. No allowable bond strength, shear, torque or environmental rating was found and none is assigned here.

Run `python references/engineering/engineering_calculations.py --write` from the project folder. JSON records inputs, all results and available root parameter-file hashes. This report is preliminary until the unresolved physical dimensions and joint capacities are closed.
