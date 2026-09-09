# Fresh Tile / one-bank geometry audit

This is geometric evidence for a preliminary mounting design. It does not establish physical thread fit, permitted screw penetration, preload, enclosure strength, thermal performance or a vendor-configured one-bank assembly.

## Reproduction and source identity

Run `audit_tile_hybrid.py`, then `finalize_geometry_views.py`, with CadQuery 2.7 / OpenCascade in `C:/venvs/cadquery/Scripts/python.exe`. The original vendor STEP is read without modification. Source SHA256 is `80714a02ccf0ba999e2d004db3d40b22f86bf4f631081086a0ba262754f6b8b2`; before/after hashes agree. Units are millimetres. `solidrun_geometry_audit.json` contains fresh source and face records; `critical_dimensions.json` is the concise, corrected result. `axis_material_intervals.json` resolves disconnected wall pieces explicitly.

The source contains 22 solids, including three overlaid enclosure variants. XCAF component-name matching identifies source indices 19 Tile, 20 60 W and 21 30 W. Indices are **zero-based**. Indices 0-14 are named Internal and 15-18 Antennas. Old local index and open-hole claims are not used.

Normalize by `(X,Y,Z) = (vendor Y, vendor Z - 80, vendor X + 14.5)`. This is a rigid, right-handed transformation. The flat Tile mating face is Z=0; the computer extends into positive Z. The Tile-only envelope is X=-65.762..65.000, Y=-80..80, Z=0..29 mm, within numerical tolerances.

## Six mounting holes: blind, with modeled helices

| Hole | X (mm) | Y (mm) |
|---|---:|---:|
| 1 | -60 | -70 |
| 2 | 60 | -70 |
| 3 | 0 | -40 |
| 4 | 0 | 30 |
| 5 | -50 | 70 |
| 6 | 50 | 70 |

All axes were independently verified from coaxial analytic cylindrical faces. Each entry mouth is diameter 4.500 mm, with a 45-degree half-angle entry cone extending from Z=0 to 0.584 mm. Helical geometry spans approximately Z=0.584..3.500 mm. Cylindrical minor/root patches measure diameter 3.332 /4.1095 mm, and repeated root features are spaced approximately 0.700 mm axially. These are consistent with an M4 x0.7 geometric hypothesis; actual thread designation, fit and useful engagement require the physical part or an applicable vendor drawing.

Each hole has a 59-degree half-angle drill cone from Z=3.500 to 4.501034 mm. This is a **blind** hole. A radius-0.015 mm axial probe intersects two disconnected material intervals: Z=4.492021..5.000 and Z=24.000..24.507979 mm. The broad intersection bounding box must not be interpreted as continuous solid between these intervals: the cavity lies at Z=5..24. The near drill apex remains closed by a nominal 0.498966 mm web before that cavity. The probe first touches the cone slightly before its exact apex.

The fresh blind-hole geometry agrees with the official Tile brief described by the research team. It contradicts the old local claim of an open 22 mm cavity accessible through the mounting bore. Neither the drill apex at 4.501 mm nor the helical-region end at 3.500 mm is an allowable screw-penetration specification. The 2.916 mm modeled helical span is not guaranteed complete engagement. No selected external fastener has yet been physically gauged. At 2.85-3.00 mm projection, deducting the modeled 0.584 mm entry leaves only 2.266-2.416 mm before incomplete screw-tip threads, fit and tolerance losses.

No auxiliary source component occupies the near-side mounting holes. Shared auxiliary geometry begins at Z>=5.246842 mm, behind the wall. This does not establish safe penetration or thread capacity.

## Contact face, protrusions and derived fin-bank reference

The single flat Tile mating face has measured area 20,410.101855 mm2, with planar-face bounds X=+/-64.485936 and Y=+/-79.500 mm. No body in the derived reference protrudes below Z=0 beyond approximately 1e-7 mm numerical tolerance. Actual finish, flatness, recesses and thermal contact must be checked on the user's computer.

The normalized 60 W body was mathematically clipped at Z>=29 mm to produce one opposite fin-bank region. This is not evidence that a corresponding detachable manufactured component exists. The clipped bank is valid, has volume 131,922.909203 mm3, and spans X=+/-64.843597, Y=+/-80, Z=29..51 mm. Tile/bank solid overlap is zero. Their coincident planar area at Z=29 is only 7,132.892850 mm2, compared with the bank cut-face area 7,337.683379 mm2 and Tile plane area 20,410.101855 mm2. No fastening, pressure, TIM, thermal resistance, assembly compatibility or 60 W thermal rating follows from this geometric coincidence.

The exported `derived_tile_plus_one_60W_bank_REFERENCE_ONLY.step` contains the Tile, clipped bank and 19 shared auxiliary solids, kept distinct. It reopens valid with 21 solids and the same 132.957016 x170 x51 mm bounding envelope: X=-67.957016..65, Y=-80..90, Z=0..51. The complex STEP round trip changes reported aggregate volume by 1.885845 mm3 (about 5.2 ppm), recorded transparently; no device mass is inferred from modeled solid volume.

## Connector and service directions

Main I/O occupies the new -X side, whose nominal chassis plane is X=-65 mm; the furthest auxiliary module reaches X=-67.957016 mm. Four bodies named Antennas extend from Y=80 to 90 mm, approximately Z=10.252..20.452 mm. Their X centres are 48.586528, 23.586528, -1.413472 and -26.413472 mm. Auxiliary body 8 also reaches Y=81.581856 mm. These are source-body envelopes, not mating-plug or bend-space envelopes. Actual connectors, latches, cable bends and tool access remain to be verified with selected cables.

The derived fins run along new Y, with channel openings at the Y ends. Preserve these openings and follow the applicable vendor cooling/orientation requirements. No thermal rating or permissible operating orientation is derived from appearance.

## Completed checks and limitations

Fresh import, units, source hash, assembly identity, all six hole axes and local faces, blind-hole sections, disconnected axial material intervals, planar contact, bank clipping, zero Tile/bank overlap and exported STEP reimport were completed. Seven geometry context views and seven true section/enlargement views support visual inspection. The section vectors use equal X/Z scales; no dimensions are taken from screenshot pixels.

Before an installation release, verify the actual Tile/one-bank configuration, all six thread identities and usable depths, selected screw heads/tips and effective engagement, allowable preload, closed-wall condition, mass, thermal-face flatness/finish, fin attachment and thermal performance. The audit does not validate a vehicle, airborne, outdoor or overhead application.
