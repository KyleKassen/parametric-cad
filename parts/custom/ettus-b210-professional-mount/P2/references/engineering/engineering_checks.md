# P2 engineering checks — thinner sections with positive retention

P2 uses an 8 mm base with a 4 mm floor, 5 mm top bars, and upright supports with 6 mm main webs/feet and 3 mm returns. It preserves P1 as a separate revision. This note is a reproducible analytical screen, not FEA, certification, physical testing, or installation approval. **Only the certified machined 6061 frame has a calculated yield safety factor.** The purchased spacer alloy/yield strength is unverified, and the actual enclosure and supporting installation remain unqualified.

Run `python references/engineering/engineering_calculations.py --write` from P2 to regenerate this note and `engineering_results.json`. CAD parameter comparison at generation: **MATCHED core parameters**. The numerical source has named engineering inputs and checks the core CAD dimensions; revise/review both when changing the design. Source hashes are recorded in the JSON. P1 remains unchanged.

## Load basis and material

The device mass allowance is 1.0 kg and complete upright package allowance remains 2.2 kg. These are assumptions requiring actual weighing, not STEP-derived masses. Gravity is 9.81 m/s². The device envelope is `(3+1)mg+20=59.24 N`; the package envelope is `106.33 N`. The 3g term is assumed incidental inertia and the 1g term adds gravity conservatively. It is not a shock spectrum. Cable force is 20 N at 50 mm; route a separate strain relief so connectors do not form the mount load path.

The handling screen is 110 N on each of two axes simultaneously plus 1 N m. The mount-only proof sizing screen is 150 N on each axis simultaneously plus 1.5 N m. These combinations exceed a single acceleration vector. Upright CG bounds are z≤120 mm and x≤50 mm from the support datum; verify balance. Root moment per support is `(150×120+150×50+1500)/2=13,500 N mm`. A separate 150 N total contact load sizes one retainer bar and one local floor land. No real-device proof load at 150 N is authorized through an unverified shell.

Certified unwelded 6061-T6/T651 stock uses minimum yield 240 MPa, E=70,000 MPa and G=26,300 MPa from the [thyssenkrupp supplier data](https://d2zo35mdb530wx.cloudfront.net/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf). Yield SF target is 3 for the declared equivalent static loads and preliminary production. Local stress factors are selected screening assumptions, not measured/calibrated notch solutions. This does not establish fatigue or enclosure capacity.

## Changes from P1

| Feature | P1 | P2 |
|---|---:|---:|
| Main base thickness |12 mm|8 mm|
| Pocket floor |6 mm|4 mm|
| Retainer bar |8 mm|5 mm|
| Main upright web/foot |8 mm|6 mm|
| Upright section stiffening |Plain L|3 mm returns and continuous foot ribs|
| Foot bolt support |Uniform8 mm|Local10 mm integral bosses|
| Retainer screw pitch X |140 mm|136 mm|
| Contact/bar station pitch Y |70 mm|76 mm|
| Final fitted device gap |0.20–0.40 mm|0.20–0.30 mm|

The thinner visible plates require more machining features and selective fit shims. P1's plain nominal36×8 mm section has I=1536 mm⁴; the nominal P2 channel has I≈2828 mm⁴ with a6 mm main wall. The channel places material farther from its centroid. Both versions preserve the device and use removable retainers. P1's top-bar calculation used a central point load; P2 uses actual pad-edge loads, so those bar deflection values reflect geometry and a refined load model. Full mass/envelope comparisons come from the separate CAD report.

## Top bars and floor: why the thinner sections work

Both top contact regions are supported by aluminum lands at x±50 mm. Each is16 mm wide. The beam load may concentrate at the **inner edge x±42**, not just its center. Nominal screw locations are x±68, giving L=136 mm and a=26 mm. Adverse drawing allowances enlarge the screw pitch to136.3 mm and move the loaded inner edge to x=41.8 mm. The bar uses **4.9 mm minimum thickness** and18.8 mm effective width after edge/width allowances. Contacts are unilateral; any nonnegative150 N total distribution over those pads is a convex combination of point loads. Putting all150 N at one inner edge bounds stress and that contact's displacement.

`Mmax=Pab/L`; `I=bt³/12`; at the load, `δ=P a² b²/(3 E I L)`. For other points the source evaluates the exact simply supported point-load equation. Calculated bending stress is 42.38 MPa; loaded-pad displacement is **0.239 mm**. The maximum span displacement is 0.345 mm at an unloaded position, not the contact constraint. The bar center must remain clear of the enclosure.

An additional **0.020 mm** allows a150 N load at a pad edge10.1 mm from the screw line, including width allowance, to twist the bar. The rectangular torsion constant uses `J≈bt³/3[1−0.63(t/b)+0.052(t/b)^5]`; end rotation is restrained by qualified hard-post seating. The calculation uses `θ=T ab/(GJL)` and adds edge motion. The torsional shear screen uses a deliberately reduced rectangular coefficient0.24. Bar installation must seat on hard posts with locking and controlled preload; freely rocking or loose bar joints do not meet this boundary condition.

The floor calculation uses a 19.7 mm adverse cantilever arm from the outer-rail support to the inner land edge, 18 mm effective contact width and **3.9 mm minimum floor**: `σ=Pa/Z`, `δ=Pa³/(3EI)`. Floor displacement is 0.061 mm. The outer base rail uses a 12.75 mm whole-length net width, 7.9 mm minimum thickness and 140.3 mm free span, with no intermediate plate-contact credit: displacement 0.235 mm. Reducing the window alone would not shorten the physical land-to-rail cantilever. Adding two center plate bolts would not benefit the two-support upright arrangement without another support.

Four-millimeter bars were rejected because their pad motion consumes too much end-capture clearance even though static strength can pass. Five millimeters with a fitted 0.20–0.30 mm gap provides the selected compromise. P1's central-point beam bound is intentionally replaced by this geometry-specific pad-edge load model; it is not valid for loads applied at an arbitrary bar center.

## Upright supports: returns carry bending

The main web is 6 mm thick. Two 3 mm wide returns project rearward 8 mm beyond it, outside the cradle. The 6 mm foot has two continuous 3 mm edge ribs rising 8 mm above it, from the rear heel through the root and both foot-bolt stations to the foot end. Nominal rib top is z=14 mm, below the cradle's z=16 mm lower edge. A bare 6 mm L support would be inadequate at this load basis; the returns are structural.

Each channel section is evaluated as three non-overlapping rectangles using `A=ΣA_i`, `c=ΣA_i c_i/A`, `I=Σ[I_i+A_i(c_i−c)²]`. Worst sections use web/foot **5.9 mm minimum**, ribs **2.9 mm minimum**, return projection **7.9 mm minimum**, width 35.8 mm, and maximum 5.6 mm holes. Root factor 1.5 applies to the most distant channel fiber. The hole strip is explicitly subtracted, and factor 3 applies at the **main-web fiber where the hole exists**. It does not multiply stress in the remote unperforated return. Return stress at the net section is checked separately.

Worst channel gross I is 2643.6 mm⁴; centroid is -4.180 mm behind the web face. The foot is the same section reflected/rotated. Whole-length net inertia conservatively screens stiffness. Returns must remain continuous through the root; ribs starting only at x=20 would leave an inadequate bare root. Blend junctions with the specified tool radii, preserve minimum wall sizes after finish, and verify tool access. This is a one-piece machined construction, with no welding or sheet-metal flat-pattern assumption.

| Member/local check | Stress (MPa) | Yield SF |
|---|---:|---:|
| bar bending and torsion | 46.67 | 5.14 |
| local floor strip | 64.76 | 3.71 |
| base rail flexure | 39.67 | 6.05 |
| channel web root | 73.98 | 3.24 |
| channel foot root | 73.69 | 3.26 |
| channel web hole local | 65.84 | 3.65 |
| channel foot hole local | 63.10 | 3.80 |
| web return at hole | 47.26 | 5.08 |
| foot return at hole | 45.52 | 5.27 |
| foot local transverse strip | 77.54 | 3.10 |
| foot boss transition | 79.43 | 3.02 |
| web local transverse strip | 31.19 | 7.69 |

Minimum machined-frame yield SF: **3.02**. Screen **passes** for these assumptions. These are selected beam and local-section checks; no fatigue, shock collision, detailed joint distortion, or support-plate global analysis is claimed.

## Local foot load and integral bosses

Calculated worst foot-bolt axial demand is 346.1 N; the local screen rounds it to400 N. An integralØ20 mm boss raises total foot thickness locally to10.0 mm, minimum9.9 mm. Model a simply supported transverse strip of clear span30.4 mm and **net width(8.0−5.6)=2.4 mm**, applying the full400 N as a central point load. This removes the hole diameter from the entire loaded strip and takes **no credit for the large washer spreading load**. Effective bearing width from screw head into the seated joint must be≥8.0 mm; verify it on received hardware. The thin washer receives no structural load-spreading or yield-strength credit.

The boss-center screen gives **77.54 MPa / SF 3.10**. At the transition, minimum boss diameter19.8 mm gives the full8 mm longitudinal strip out to `|y|=sqrt(9.9²−4²)=9.0559 mm`. Beyond that point, discard remaining partial boss material, use the full8 mm plain-foot strip with5.9 mm thickness, and apply factor3 to its remaining bending moment. Transition stress is 79.43 MPa / SF 3.02. The small R0.2–0.5 root blend adds material to the idealized boss and avoids a burr; no stiffness credit is taken for it. Factor3 is a selected screening assumption, not a calibrated notch solution.

Web-bolt normal demand is only 69.7 N; a100 N local screen with a conservatively reduced standard-washer strip passes. The unbossed6 mm foot and soft large washer alone were not released as a verified load spreader. McMaster91100A140 is zinc steel, hardnessB56, thickness1.0–1.4 mm, with no published yield class or diameter tolerance in the inspected catalog. Its nominal15 mm diameter fits the boss and provides a seating/protection surface. Inspect OD≥14.9 mm as a drawing acceptance criterion, not a supplier guarantee; inspect for dishing and permanent set. The foot-bottom washer may remain standard on the assumed rigid metal supporting plate. Foot screws are M5×30; use actual washer/plate/nut dimensions to confirm complete locking engagement and nut-side clearance.

## Movement and positive capture

| Load/location | Movement bound |
|---|---:|
| Upright normal service: 1g +20 N, +1 N m | 0.266 mm |
| Upright handling: 110 N each axis +1 N m | 0.863 mm |
| Upright mount-only proof:150 N each axis +1.5 N m | 1.185 mm |

Upright deflection includes web bending, eccentric moment, foot bending, foot rotation between its two bolts and foot vertical movement. It uses channel net inertia for the whole member. Additional local boss/foot flexure is calculated by virtual work for a stepped beam; outer plain-foot portions use5.9 mm thickness, and the entire central boss region conservatively uses2.4 mm net width. Local foot movement at400 N is 0.0177 mm and local web movement at100 N is 0.0116 mm. Opposing local movements are converted into support rotation and added to the global bound. Bolt stretch and installation-plate translation remain outside the model. Retain P1 prototype criteria: ≤0.75 mm normal, ≤1.5 mm handling, ≤2.0 mm proof and ≤0.10 mm residual. These are selected functional limits, not manufacturer limits. Preserve at least2 mm extra moving-envelope clearance pending physical results.

The retention audit must use **upper travel 1.0554 mm and lower travel -0.2000 mm** at opposite support stations. Upper travel adds the0.30 mm gap, total0.20 mm upper-film loss, bar pad bending, bar edge twist, floor flexure and rail flexure. Lower travel allows complete bottom-film loss onto hard lands. The corresponding pitch bound is 0.9464°. P2 stations are y=C±38, giving76 mm separation: `u_end=u_up+(80−38)/76×(u_up+0.2)=1.749 mm`. The outer-rail screen retains the older central-point load bound and takes no stiffness credit from moving a contact closer to an installation bolt.

Nominal end overlap remains2.1 mm, leaving **0.351 mm** before dimensional variation and **0.151 mm** after a further0.20 mm reserve. Side overlap starts at2.3 mm; analogous roll retains 1.100 mm before reserve. This small end margin requires the exact pan-only pose/escape witness and physical testing. It is not a continuous configuration-space search or dynamic impact calculation. Do not chamfer the retaining edge by the general0.5 mm amount; preserve its critical height and ≤0.10 mm burr break. The source STEP enclosure's local crushing/denting capacity is unknown.

## Purchased hardware, fitted stack and unresolved spacer properties

McMaster class12.9 ISO4762 screws use a **970 MPa proof reference** and M5 stress area14.2 mm² from the [NBK fastener-property table](https://static.nbk1560.com/en-US/resources/other/article/technical-29-mechanical-properties-of-fasteners-made-of-carbon-steel-and-alloy-steel/). Require delivered property-class conformity. The400 N axial/150 N shear external screen gives 33.59 MPa equivalent stress and proof SF 28.9. Do not use a generic class12.9 tightening torque in the aluminum threads. Nut class10 and complete locking-element engagement must match the BOM; this is not a full nut proof qualification.

The retainer uses an M5×45 screw,5 mm bar,1 mm washer,30 mm purchased spacer and nominal0.6508 mm shim stack over the9.20 mm boss. Nominal gross entry is 8.3492 mm; tip recess 0.8508 mm. Purchased tolerances, bolt runout and actual selected shims govern. Inspect **≥7.5 mm complete female/male thread engagement** and **≥0.5 mm screw-tip recess** above the base underside. Through taps do not provide blind-hole bottoming protection if a screw protrudes into the mounting plate.

Conservative aluminum-thread surrogate `A_s=0.25π×4×7.5` gives 1088 N allowable at SF3. A400 N external/prying reserve leaves **688 N** for preload within this surrogate. A500 N candidate maximum seating preload is therefore only an engineering limit for qualification, not an approved torque or a proven assembly procedure. The shop must establish repeatable seating/locking against actual finish, thread friction, inserts if used, and spacer behavior. The device itself receives no intentional clamp preload.

Purchased [McMaster94669A146](https://www.mcmaster.com/94669A146/) is cataloged aluminum with30±0.13 mm length,10±0.13 mm OD and5.3±0.13 mm ID. **Its alloy/temper/yield strength is not specified by the inspected catalog evidence; do not call it6061.** Minimum annulus is 53.35 mm². External400 N gives 7.50 MPa average compression;900 N including the candidate500 N preload gives 16.87 MPa. To support SF3 at900 N would require compressive yield≥50.6 MPa, which remains unverified. The Euler screen is 276035 N using an explicitly assumed E60 GPa and pin-ended30.13 mm column; its very high result merely shows slender-column buckling is unlikely to govern the assumed metal. It does not prove crushing capacity. Obtain material confirmation or qualify spacer compression/permanent set and joint seating before release.

The thin shim's maximum ID6.6294 mm and minimum OD9.4742 mm can govern bearing contact area; verify concentric, flat seating, retention of the thin shim and no edge overhang. Final BOM shim dimensions and hardness/material data take precedence over nominal CAD rings. Check permanent set during joint qualification. Shims belong under hard spacers, not between a loaded bar and the radio.

The [PET film8689K65](https://www.mcmaster.com/8689K65/) catalog nominal is0.127±0.0127 mm, with acrylic adhesive; whether the displayed thickness includes adhesive is unresolved. Measure installed total thickness and keep it≤0.20 mm per contact. The CAD uses that upper bound, not a claim that the product is exactly0.20 mm. The stock shim stack is only a nominal assembly example. With actual thinner films the gap increases: select shims by measured cold/warm gap at every contact, keeping **0.20–0.30 mm** and maintaining screw engagement/recess. No pad/friction/adhesive retention credit is taken.

For stack screening only, assume enclosure height33.7±0.2 mm, boss9.20±0.05, hard-land top5.50±0.05, spacer30±0.13 and installed film0.1143–0.20 mm. These give an unshimmed gap from **-0.830 to 0.201 mm**, before bar flatness and unverified enclosure variation. Stock shims up to about1.1 mm may be required; the example0.6508 mm stack is not a universal setting. Recheck thread entry and tip recess independently for the selected stack. Reject/select/rework any combination that cannot satisfy all criteria; never tighten the gap away by clamping the enclosure.

With catalog-minimum film0.1143 mm, land-top minimum5.45, measured STEP lower-label datum2.531 above the pan, and stop maximum7.85, the calculated label-to-stop gap is **0.2453 mm**. Actual label placement and enclosure variation are unverified. Inspect **≥0.20 mm actual label clearance** at both ends with the fitted device, including warm operation; the numeric stack does not replace that check.

## Remaining release work

Physical fit, device mass/CG, actual supporting plate and nut-side tool access, spacer compression, shim seating, controlled preload, local enclosure pressure, powered thermal performance in the real box, and repeated removal remain open. The original feet, labels, connectors and original fasteners must remain untouched. No improvement in heat rejection, grounding, vibration life or shock rating is claimed. Use the geometry audit for actual exported-solid validity, interference, connector envelopes and pan contact witnesses. Prototype proof uses a representative rigid dummy; real-device checks use limited forces and then powered thermal/service tests. Inspect for loosening, thread damage, permanent distortion, film wear and enclosure marking before releasing beyond preliminary stationary indoor use.
