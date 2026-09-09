# Source geometry audit — measured evidence, 2026-09-08

Original user file was imported directly with CadQuery 2.7 / OpenCascade; it was not modified. Its SHA256 is `c59b649ccc6a4c128885fd9e64acfd74d756b23bbcff7f119e21a4acb426c912`, identical to the pre-existing project vendor copy. STEP declarations explicitly specify millimetres. `inspection.py` reproduces the fresh audit; `fresh_geometry_audit.json` records every solid, axis-aligned planar face/wire, and cylindrical face. `contact_sections.py` reproduces narrow sections of the bottom pan.

**Configuration:** an enclosed assembly, with internal PCB/components, formed bottom pan, formed top cover, separate end panels, four rubber-foot-named solids, seven coaxial connectors, USB3 Type B geometry, DC power socket, end-panel fasteners and overlay solids. Identification combines STEP product metadata and seven inspected orthographic/isometric views; material and mechanical capacity are not inferred. The model is 196 valid solids and 7825 faces; compound validity passed.

**Supplied configuration discrepancy:** product records contain both `OVERLAY_NI_USRP-2901_FRONT` and `OVERLAY_NI_USRP-2900_FRONT`, modeled as successive 0.381 mm layers. Both remain in the reference. Compare the actual device's front panel and hardware against the source before manufacture. Product names mentioning M3 are useful leads, but this audit does not establish usable device attachment threads, thread engagement, or screw penetration.

**Datums:** transform original geometry by X+90°, then Z+180°, both about the original origin, then translate (58.5005,80.6355,1.210) mm. Pan outside base plane is Z=0; +Y is the four-RF-connector face. X is transverse; Z is upward. The model is not exactly symmetric about Y=0 or X=0; preserve these values. All following dimensions are measured in this frame; any mount-added device lift must be added to Z.

| Feature | Measured geometry (mm) |
|---|---|
| Original overall bbox | X −2.674 to 119.674; Y −4.766 to 32.490; Z −166.6018 to 11.0458 |
| Normalized overall bbox | X −61.1735 to 61.1745; Y −85.9663 to 91.6813; Z −3.556 to 33.700 |
| Overall size including connectors and feet | 122.348 × 177.6476 × 37.256 |
| Flat pan underside | Z=0; X −58.4995 to 58.5005; Y −72.4905 to 78.2155; four foot-area openings |
| Pan sheet geometric thickness | 1.210 between flat Z0 and Z1.210 faces |
| Lower pan sides | X=−60.9195 / +60.9205; Y −73.4905 to 79.2155; Z2.420 to 6.550 |
| Top cover outer plane | Z33.700; X −58.7535 to 58.7545; Y −72.4905 to 78.2155 |
| Cover side outer planes | X=−61.1735 / +61.1745; Z9.500 to 31.280 |
| Cover geometric thickness | 1.210 between planar top faces |
| Four top dimples | Centers X=−46.7995/+46.8005, Y=−59.9845/+60.0155; opening diameter12.740086; floor diameter8.26795 at Z32.700 (1.000 below cover) |
| Four foot bodies | Centers X=±46.7995, Y=±60.0075; max Ø12.700; Z−3.556 to 0 |
| Bare pan end planes | Y−74.9105/+80.6355; Z2.420 to 9.500, with holes and connector-related interruptions above |
| Separate end panels | Rear Y−75.8245 to −74.9105; front Y80.6355 to 81.5495; thickness0.914; lower edgeZ2.420 |
| Front overlay stack | Y81.5495 to82.3115; begins at Z2.537554/2.5578 depending layer |
| Rear overlay | Y−76.2055 to−75.8245; begins Z2.53129 |
| Cover slot, −X side | Y−66.3645 to−59.3645; Z16.210 to19.210, nominal7×3 |
| Cover slot, +X side | Y65.2295 to72.2295; Z16.210 to19.210, nominal7×3 |
| Bottom-pan slot beneath +X cover slot | Y65.0895 to72.0895; Z16.210 to19.210 (0.140 offset from cover slot) |

No broad vent array occurs on the modeled cover or bottom. This is a geometric observation, not proof that blocking exterior convection is acceptable. Preserve both side slots; their function has not been established from geometry.

**Historical P1 contact implications (source evidence retained).** The pan underside and top cover are continuous planar surfaces away from the listed feet/dimples; bar/pad stations around Y−31.947 and +38.053 avoid those features. Pads centered at X±50 must stay within the flat pan boundary X±58.5. The cover and pan remain thin device structure of unverified allowable load; test local deformation and inspect for dents.

A broad end lip rising above device Z2.53 would contact a front/rear overlay before the shell. End lips ending at device Z1.8 can contact the bare rounded bottom-pan bend. Narrow BREP slabs (0.002 thick) yield:

| Section Z | Pan Y minimum | Pan Y maximum |
|---|---:|---:|
| 0.500 | −73.964907 | 79.689907 |
| 1.500 | −74.729214 | 80.454214 |
| 1.800 | −74.829996 | 80.554996 |
| 2.000 | −74.873951 | 80.598951 |
| 2.300 | −74.907573 | 80.632573 |
| 2.500 | −74.910500 | 80.635500 |

The end bend's outer cylinder radius is2.420. A low lip contacts a curved surface and can produce uplift; upper retainers must react that component and limit climb. At a 1.8-high lip, 0.3 mm upward device travel shifts the contact to device Z1.5 and adds approximately0.101 mm end travel. This does not quantify local shell stiffness, label adhesion, or load rating.

**Completed:** direct-source import; explicit source unit check; source/vendor identity; body count and validity; bounding boxes; face and wire measurement; pan sections; seven rendered views visually inspected. **Not established:** device mass/CG, alloy or sheet strength, screw specifications/penetration, surface tolerances, thermal behavior, actual plug envelopes, or physical fit. Do not use the model's material volume or geometric centroid as mass/CG.

P2 uses stations Y=-34.947/+41.053,76mm separation. The source-only measurements above remain applicable; all final mount geometry and clearance checks are the P2 export reports. The packaged inspection scripts use the byte-preserved input_device.step; the original vendor-copy hash comparison is retained as historical evidence and is skipped on portable regeneration when that external copy is unavailable.
