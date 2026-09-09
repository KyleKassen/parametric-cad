# Mean Well NSP-1600 fresh source audit

Scope: original STEP inspection and mounting-interface evidence only. No adapter geometry, manufacturing release, physical fit, electrical safety, thread strength or thermal qualification is produced by this audit.

## Source, units, identities and datums

The user component-library STEP has SHA256 `d421a1e7fb7a3b5fd2e12588484a2e970456301955c0a17f55be6d56324dd8a0`, identical to the existing vendor copy. The original was preserved. Fresh import yields 19 valid solids in millimetres. XCAF names were mapped to source solids; all numeric identities below are zero-based. These differ from the older volume-sorted local analysis and must not be interchanged.

| Source index | Interpretation supported by geometry / matching manufacturer drawing | Source product name |
|---|---|---|
| 0 | Fan guard/bracket and its bottom mounting spine | Encoded source name recorded in JSON |
| 1 | AC terminal-block assembly reference | FFFF_1_1 |
| 10 | PCB-shaped reference body | SS |
| 12 /13 | Two output busbar references | Encoded source names recorded in JSON |
| 14 /15 | Two fan bodies | Same source UUID, distinct placements |
| 16 | Top cover | P1-T |
| 17 | Main casing / bottom sheet | 1600-CASE |
| 18 | Terminal end panel | Encoded source name recorded in JSON |

Normalized coordinates retain the original axis directions and translate by `(-66.7869113,-354.1518617,-1.4999997)` mm. X=0 is the body width centre, Y=0 is the terminal chassis plane, and Z=0 is the lower contact plane. The assembly extends X=-42.5000001..42.5000001, Y=-300.6000008..37.9999995, Z=0..41 mm. Thus the complete STEP envelope, including protruding output blades, is 85 x338.6 x41 mm.

The manufacturer drawing specifies a nominal 300 x85 x41 mm chassis, general tolerance +/-0.5 mm. The STEP's outermost fan-guard relief extends 300.6 mm behind the terminal datum; its main front guard plane is Y=-299.1 mm and cover reaches Y=-298.2 mm. Record this envelope difference rather than shifting the mounting pattern to force 300 mm. The mounting dimensions themselves agree with the drawing. Reserve space from the actual 300.6 mm source extent until checked on the unit.

## Bottom mounting interface

The user-supplied `NSP-1600-spec.pdf`, mechanical specification page6, Case296A, dated2025-08-19, explicitly identifies three bottom M3 mounting holes. Its instruction gives **maximum intrusion4 mm** and **recommended mounting torque6-8 kgf cm**. These are manufacturer inputs; bore appearance does not establish them. The drawing dimension16.1 mm from the terminal plane and264.7 mm longitudinal spacing match the source.

| ID | Nominal normalized X/Y (mm) | Owning source body | Actual local geometry | First other modeled component on axis |
|---|---|---|---|---|
| H1 | -35, -16.1 | Main case17 | Rolled entry Z0..0.72; DIA2.65 cylinder Z0.72..2.10 | PCB reference at Z4.4999998 |
| H2 | +35, -16.1 | Main case17 | Same as H1 | PCB reference at Z4.4999998 |
| H3 | 0, -280.8 | Fan bracket0 | Rolled entry Z0..0.48; DIA2.65 cylinder Z0.48..1.70 | Cover at Z40.4 |

The measured fan-hole X coordinate is -0.0000428 mm, a negligible source-model difference from the drawing centreline. Terminal hole Y coordinates differ from nominal by about0.000001 mm. Use the nominal manufacturer pattern for the new part and retain the measured frame for assembly checks.

The local features contain toroidal rolled entries and cylindrical bores, not complete modeled helical threads. Cylindrical spans of1.38 mm at H1/H2 and1.22 mm at H3 are geometric observations, **not guaranteed effective engagement**. Do not import a2 mm full-engagement criterion from another product. Manufacturer thread/pitch, available engagement, received screws, head seating and the permitted intrusion must be checked together. No material strength or thread capacity follows from the extrusion appearance.

Axial probes of radius0.01 mm and radius1.5 mm both first encounter the PCB reference4.5 mm above the bottom at H1/H2. There is no other source body in those bores below that height. At H3, the probes pass between the fans before reaching the cover. The latter long geometric clearance does not override the4 mm manufacturer limit. The PCB is only a reference body; source clearances do not prove safe spacing to actual circuitry or solder joints.

The two separate countersunk assembly features near Y=-262.725 mm are not the requested mounting holes. They join the fan bracket / case region; do not repurpose or remove them by default.

## Bottom contact and fan clearances

The main casing has a continuous lower planar sheet face of21,819.094925 mm2, spanning X=+/-41.2 and Y=-265.8..0. Its four internal wire loops correspond to the two mounting bores and two separate assembly features; there is no field of bottom vents in this main-sheet region.

The fan-bracket bottom is different: approximately630.404566 mm2 of metal planar contact forms edge strips and a central spine around **two open underside regions**. Fan bodies have surfaces coplanar with Z=0 within those regions. The full lower envelope therefore must not be described as a continuous steel plate. The selected mount should preserve fan-frame clearance and qualify the resulting airflow; contact through fan frames is not an established load path.

Both full fan bodies extend Y=-298.300001..-270.300000, Z=0..40 mm. Their X bounds are -41.7..-1.7 and+1.7..+41.7. The lower contact envelopes are narrower than the full-body boxes:

| Source-height interval | Left fan envelope X (mm) | Right fan envelope X (mm) |
|---|---|---|
| Z0..0.001 | -37.7894..-5.6106 | +5.6106..+37.7894 |
| Z0..0.25 | -39.0919..-4.3081 | +4.3081..+39.0919 |
| Z0..0.50 | -39.6365..-3.7635 | +3.7635..+39.6365 |
| Z0..1.00 | -40.3458..-3.0542 | +3.0542..+40.3458 |

These are clipped geometric envelopes, not permitted fan movement or dimensional tolerances. The actual metal central spine is **5.50 mm wide**, X=-2.75..+2.75, across the fan region. At H3 the entry opening leaves bottom-face land intervals approximatelyX=-2.75..-1.77256 and+1.77248..+2.75. Side metal strips are X=-42.5..-41.7 and-41.6..-40.1, mirrored on the right. `fan_bottom_contact_geometry.json` records sections at multiple Y stations to support a relief design without discarding these metal contacts.

## Other interfaces, cooling and service

The manufacturer side-mount pattern is X=+/-42.5, Y=-5.8 and-257.8, Z=22.8 mm, with two M4 points per side and5 mm maximum intrusion /7-10 kgf cm mounting torque. The source terminal-side features are **short local extrusions on the two casing walls**, with DIA3.1 cylinders spanning only1.38 mm per wall. They are not a cross-tube running across the entire body; the earlier local cross-tube description was incorrect. Fan-side M4 locations appear as DIA5 openings in the main wall, and their actual threading is not established by this source. The nearby DIA2.8 features at Z16.8 are separate assembly features, not substitutes for the documented mounting points.

The broad top cover has no mounting-hole field. Its upper plane is Z41 and its main thickness is0.6 mm in the source. It is a removable service component; do not use cover or case screws as mounting hardware without manufacturer evidence.

The fan guard and exhaust occupy the -Y end. The manufacturer arrow on page6 identifies flow from the terminal side toward the fans. The +Y end panel includes multiple rectangular airflow openings, the AC terminal block, two DC blades, control headers, LED and adjustment access. The AC-block envelope projects7.9594 mm beyond Y0; output blades project38.0000 and27.9500 mm. These are source-body envelopes, not lug, cable bend, finger protection or tool allowances. Keep actual lugs/boots, AC protection, control plugs and servicing access in the installation clearance model.

The source and this audit do not establish allowable airflow obstruction, cooling capacity, material strength, grounding capacity, mains-terminal protection, humidity rating or operating orientation. Follow the specific manufacturer installation instructions and actual electrical design. No TIM or benefit from broad contact is assumed.

## Reproduction and completed verification

Run `audit_nsp1600.py`, `inspect_mounting_interface.py`, then `fan_contact_audit.py` with CadQuery2.7 from `C:/venvs/cadquery/Scripts/python.exe`. The source file and vendor-copy hashes are checked. The normalized STEP keeps all19 original solids distinct, reopens valid with unchanged bounding dimensions, and records an aggregate volume drift of18.12 ppm on export/reimport; no density or mass inference is made. Seven context views and three true, uniformly scaled sections were inspected.

Before release, physically confirm the three M3 threads, chosen screw stack and intrusion, rear-spine bearing, fan clearances, bracket/case capacity, FPE studs and supporting panel, wiring protection, actual cable/tool access and cooling under the intended load. This is a source-audit record, not evidence of fabrication or testing.
