# B210 P1 engineering checks — preliminary

This is an analytical screening of the delivered machined 6061 mount and upright supports. It is not FEA, a certification, an installation approval, or evidence of a physical test. The device mass, center of mass, shell capacity, cable selection, supporting plate, and actual shop process remain unverified. Positive enclosure capture has a small end-stop margin and requires the specific fit and retention tests in the prototype plan. Both flat and upright stationary indoor configurations are provisional; no vehicle, airborne, outdoor, overhead, shock-spectrum, or vibration qualification is established.

Reproduce with `python references/engineering/engineering_calculations.py --write-note` from the design folder. Standard-library Python 3.10+ suffices. The script reads `params.json` and `adapter_params.json`; changing those files changes these calculations. SHA-256 used: cradle `7166e33ea6a62431a7bf1a5ff53078ac2b7557a93d3eadcbc67003c517e96bb9`, adapter `9421e30ad9b02d26e210b903455e44e2b98a5fd2031a309f7355ed4ae4830b1a`. Source CAD hashes and the original STEP are handled by the separate geometry audit.

## Inputs and their status

| Input | Value | Basis |
|---|---:|---|
| Device mass allowance | 1.00 kg | Design assumption; weigh actual configured radio |
| Complete upright package allowance | 2.20 kg | Includes radio, cradle, supports, and hardware; weigh complete assembly |
| Gravity | 9.81 m/s² | Calculation convention |
| Incidental handling | 3g inertia, plus 1g gravity | Conservative static-equivalent assumption; not a shock test specification |
| Cable load | 20 N at 50 mm | Assumed accidental load; use separate strain relief so connectors are not structural restraints |
| Metal yield / modulus | 240 MPa / 70,000 MPa | Certified unwelded 6061-T6/T651 stock; supplier minimum yield and reference modulus [1] |
| Minimum yield safety factor | 3.0 | Chosen for preliminary loading, small quantities, and dimensional uncertainty; does not cover missing enclosure properties |
| A2-70 screw proof / stress area | 450 MPa / 14.2 mm² | Property-class reference and M5 coarse-thread stress area [2,3]; require traceable full-load ISO 4762 hardware |
| Upright CG bounds | z ≤120 mm; x ≤50 mm from upright web datum | Conservative assumed limits; verify actual assembly balance before release |
| Supporting structure | Rigid flat metal plate; worked example 6 mm 6061 | Assumed for hardware and local bearing only; actual plate span/edge distances/attachments must be reviewed |

None of the device mass, materials, shell strength, threads, or allowable screw penetration is inferred from STEP appearance. Device threads are unused. All fasteners attach mount components or the supporting structure.

## Load path and load envelopes

The four integral aluminum lands carry normal gravity from the enclosure pan into the pocket floor, outer base rails, four plate bolts, and the rigid installation plate. Bottom 0.2 mm films protect finish; their complete loss is included in the capture screen. The low end lips and higher side lips oppose translation. Two separated top bars oppose lift and roll/pitch after the checked assembly gap closes. Screws and hard spacers connect those bars to the base, without intentionally clamping the device. In upright service the rotated cradle transmits loads through four through bolts into the machined L supports, then four foot bolts into the plate. Retention takes no friction credit. Films and their adhesive take no retention or preload credit. Small bounded rattle/free movement is possible.

Static gravity on the 1 kg device is 9.81 N. The deliberately additive device handling envelope is `F = (3+1)mg + 20 = 59.24 N`. Its combined overturning moment is `M = 4mg×50 + 20×50 = 2962.0 N mm`. A conservative single-member reaction is `F + M/70 = 101.55 N`; round upward to **150 N applied to one bar, land, lip, base rail, or retainer screw**. This treats complete applied force and overturning reaction as simultaneous on one member, rather than dividing equally among four contacts.

The complete 2.2 kg package has `4mg+20 = 106.33 N`. The upright handling envelope is 110 N horizontally and 110 N vertically plus 1,000 N mm. The **mount-only proof screen applies 150 N horizontally and 150 N vertically simultaneously**, with an additional 1,500 N mm cable couple. These components exceed the assumed single acceleration vector and add a sizing reserve. They are assumed equivalent static loads, not measured dynamic loads. Upright root moment per support is `(150×120 + 150×50 + 1500)/2 = 13500 N mm`. Recalculate if package mass, CG bounds, cable forces, or support geometry exceed these values.

## Member strength

For a rectangular section, `A=bt`, `Z=bt²/6`, `I=bt³/12`. For a simply supported beam with a central point load, `Mmax=PL/4`, `σ=M/Z`, and `δ=PL³/(48EI)`. For a short cantilever, `M=Pa` and `δ=Pa³/(3EI)`. These classical small-deflection beam equations screen the mount members; they do not calculate local enclosure response.

The 140 mm span top bar is screened with a central 150 N load. Its effective width is 19 mm to conservatively remove the two 0.5 mm edge treatments; actual device contacts nearer the supports reduce the central-load bound. The local floor strip uses a 21.5 mm cantilever, 18 mm effective width excluding land corner radii, and 6 mm floor thickness. The outer base rail uses 140 mm span and net width with one hole removed for its whole length. The lip uses only a 4 mm long contact patch and minimum end-wall thickness reduced by 1 mm. The manufacturing drawing must preserve those ligaments and the end-stop retaining edge.

For the upright supports, the nominal straight section is 36×8 mm. The calculations reduce it to **35.8×7.95 mm**, enlarge the hole to 5.6 mm, and apply adverse 0.15 mm hole-position shifts. This requires the critical **8.00±0.05 mm finished web and foot thickness**; a general ±0.20 mm thickness tolerance is insufficient for the stated target. A factor 1.5 is applied to gross-section bending at the R6 root. A factor 2 is applied to bending at a whole-width net section excluding the maximum hole at the lower web attachment and near foot attachment. These are **selected engineering screening factors**, not calibrated or formally bounded stress-concentration/fatigue solutions. The quoted minimum safety factor is conditional on them; a larger local factor reduces that margin. Axial stress and root transverse shear are included. The foot-hole moment uses the nominal 30 mm remaining vertical-load lever from x=20 to the assumed CG x=50, adjusted adversely for hole position.

| Check | Screening stress (MPa) | Yield safety factor |
|---|---:|---:|
| bar bending | 25.90 | 9.26 |
| floor local bending | 29.86 | 8.04 |
| base rail bending | 16.83 | 14.26 |
| end lip von mises | 9.89 | 24.26 |
| adapter root von mises | 53.96 | 4.45 |
| adapter lower web hole local | 79.62 | 3.01 |
| adapter near foot hole local | 75.51 | 3.18 |

Calculated minimum member yield SF: **3.01**, target 3.0. Strength screen: **PASS for the declared assumptions**. Gross bending, net sections, and selected local factors are checked; shell buckling, detailed plate torsion, fatigue, contact singularities, manufacturing defects, and support-structure global flexure are not resolved by this model. The generous member margins do not establish enclosure strength.

## Deflection and clearance

| Location/load | Calculated bound |
|---|---:|
| Top bar, 150 N central load | 0.151 mm |
| Local floor strip, 150 N | 0.022 mm |
| Base rail, 150 N flexural screen | 0.065 mm |
| Upright upper attachment, simultaneous severe envelope | 1.957 mm |
| Upright handling, 110 N each axis +1 N m (conservative scaled bound) | 1.435 mm |
| Upright normal service, 1g+20 N and 1 N m | 0.449 mm |

Upright deflection combines net-section web bending, the eccentric moment, elastic rotation of the foot between its two bolt supports, and foot vertical motion. It treats bolt/plate translations as fixed; actual bolt, plate, and enclosure compliance add to this. Foot rotation uses `θ=[M(a+s/3)+V(a²/2+as/3)]/(EI)` with nominal a=20 mm overhang, s=35 mm bolt spacing, adverse position tolerance, and absolute contributions added. The normal-service bound is evaluated independently with 20 N horizontal, `(2.2g+20)=41.582 N` vertical, and 1,000 N mm couple; counting the complete cable force on both axes is conservative. Handling deflection uses the 110/150 scaled proof bound, which also includes 1,100 N mm couple and therefore exceeds the required 1,000 N mm handling couple.

Recommended prototype limits are **2.0 mm elastic movement at the 150 N simultaneous severe mount-only proof screen**, **1.5 mm at the 110 N handling screen**, **0.75 mm in the normal 1g+20 N service test**, and **0.10 mm residual displacement** after unloading. These are selected functional acceptance limits, not manufacturer limits. The analytical proof bound is close to 2 mm and does not include real plate compliance; increase stiffness or allowance if prototype results exceed it. Reserve at least 2 mm extra moving-assembly clearance inside the box, in addition to measured plug/bend/tool clearance, until measured results justify less.

The end-capture screen includes maximum final assembly gap, complete top-film loss, bar/floor/rail elastic deflections added in the unfavorable direction, and opposite bottom-film loss: `u_top = gap_max + film + δ_bar + δ_floor + δ_rail = 0.838 mm`. The pan can drop 0.200 mm onto the opposite hard land. For a conservative end extent 80 mm about the device datum and 70 mm bar spacing, `u_end = u_top + (80−35)/70 × (u_top+0.2) = 1.506 mm`. Initial end overlap is 2.100 mm, leaving **0.594 mm** before the actual pan contour and tolerances. Reserving another 0.20 mm for stop/pan height variation leaves **0.394 mm**. Side overlap remains about 3.342 mm in the analogous roll screen. Adding floor/rail deflection to upper travel is deliberately conservative; common rigid motion of the base itself does not consume capture.

This narrow end margin is **provisional**, not a rated retention result. General 0.5 mm deburring must not be applied to the retaining edge: use ≤0.10 mm there. The exact CAD contour/tilt audit and the physical retention test govern, including rocking in both directions with films removed, worst allowed cold/warm gap, and applied loads. Check differential base bending; whole-base motion alone is not loss of retention. If clearance, temperature, or deflection permits escape, reduce the fitted gap/film thickness or revise the end stop before use. No impact factor for collision across the free gap is implied by the 3g static-equivalent load.

## Fasteners, holes, and contact

| Check | Result |
|---|---:|
| Worst upright foot-bolt axial demand from moment distribution | 346.1 N |
| Selected individual foot-bolt external axial/shear screen | 400 N / 150 N |
| M5 equivalent external stress `sqrt((N/At)²+3(V/At)²)` | 33.59 MPa |
| External proof safety factor, 450 MPa reference | 13.40 |
| 6 mm aluminum plate transverse bearing, conservatively `400/(dt)` | 13.33 MPa |
| Two-plane edge tear-out capacity, 7 mm clear ligament ×6 mm | 3880 N at SF3 |
| ISO 7089-size washer average external bearing pressure | 7.08 MPa |
| Spacer pressure from 150 N external load | 1.68 MPa |
| One 16×20 mm land/film average at 150 N | 0.469 MPa |
| Four lands, 1 kg static gravity average | 0.0077 MPa |

These are external-load checks. Contact pressure is an average; it does not establish allowable enclosure pressure, label strength, film life, or resistance to denting at hard stops. Mount-only loads can be introduced with a rigid dummy. Do not proof-load the real radio through connectors or unverified shell features.

Retainer hardware is M5×50 ISO 4762 A2-70, M5 coarse pitch 0.8 mm, with a 1 mm washer, 8 mm bar, and 30 mm hard spacer: grip 39 mm, nominal entry 11 mm into the 12 mm base, nominal tip clearance 1 mm. Verify **≥8 mm fully formed thread engagement** and **≥0.5 mm tip clearance above the base underside** on actual purchased hardware and completed parts, allowing chamfers/runout/finish/tolerances. Through-tapped holes prevent blind-hole bottoming; screws must remain inside the base. Do not use the device's original screws or threads.

The conservative thread-stripping surrogate is `A_s=0.25π d_core L_e`, with d_core=4 mm and L_e=8 mm, giving 25.13 mm². `F_allow=A_s Sy/(√3×3) = 1161 N`. Against a 150 N external increment, that leaves only **1011 N** as an approximate preload ceiling at the same screening factor. This is not an approved tightening specification. Installation preload can dominate external forces; the fastening shop must establish and qualify seating/locking with the actual threads, lubricant/locking product, and finish, or test the joint. Do not adopt a generic steel-joint M5 torque. No torque is invented here. Seat bars against hard spacers while preserving device gap. Use the specified removable locking product to its supplier process; witness-mark and inspect. Repeated service and galling can reduce thread capacity.

The upright cradle bolts pass through metal members and use washers and prevailing-torque nuts. Complete hardware specifications and lengths are in the BOM; actual locknut thickness, coating, and plate thickness govern usable engagement. Require at least two complete threads through the locking element and accessible nut faces. The worked plate has through bolts, so no plate-tap pullout is assumed. Global plate bending, pull-through to a thin/soft/unsupported surface, local plate buckling, edge distances, and the plate's own attachments remain the installer's responsibility. If the actual supporting plate is not the assumed rigid metal plate, these local checks do not release the installation.

## Release limitations and validation

Confirm configured mass/CG, body dimensions, pan/stop contact, completed fit gap at every land, film thickness, and support flatness. Use the geometry report for STEP validity, export reopening, connector/tool envelopes, and nominal interference; this file does not claim those operations. Check all actual USB/power/RF plugs and cable bend radii, ensure cooling openings remain usable in both orientations, and conduct a powered thermal comparison in the actual box. No heat-sink or improved-cooling claim is made; anodize/films are not a verified grounding system. Review intended grounding and protect contact surfaces/corrosion appropriately.

Run mount-only static strength/retention tests with a representative dummy, then real-device fit, low-force retention, connector access, service removal, and thermal tests. Witness-mark screws and inspect for loosening, permanent distortion, thread damage, denting, and film wear. Application acceleration spectra, fatigue life, shipping shock, and repeated-removal life require separate requirements and validation. Follow the delivered prototype plan and record actual results before releasing P1 beyond prototype work.

## Sources

[1] [thyssenkrupp EN AW-6061 data sheet, June 2018](https://d2zo35mdb530wx.cloudfront.net/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf), sheet/plate T6/T651 minima and reference modulus; require certified matching stock. [2] [NBK stainless strength comparison](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/stainlessscrew/SNSX-88/?SelectedLanguage=en-US), A2-70 comparison values. [3] [NBK fastener mechanical-properties reference](https://static.nbk1560.com/en-US/resources/other/article/technical-29-mechanical-properties-of-fasteners-made-of-carbon-steel-and-alloy-steel/), metric coarse-thread stress areas. Accessed 2026-09-08. These references are not guarantees for untraceable purchased parts.
