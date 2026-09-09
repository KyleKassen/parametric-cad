# Router and OZ panel interfaces — 8 September 2026

All coordinates are millimetres. `interfaces.json` is produced by `audit_interfaces.py` from the supplied STEP and the current OZ v2 STEP. The normalized STEP files have component mount faces at Z=0 and the main wired I/O aimed toward panel -Y (bottom). They are layout reference components, not manufactured aluminum plates.

## Peplink UBR Plus

The STEP contains four genuine unthreaded Ø4.5 mm through holes in its external side mounting ears. Their normalized centers are (±80.9, ±41.35), a 161.8 × 82.7 mm pattern. Ear thickness is 2.5 mm. The mounting interface is not a presumed thread in the router case. It requires no custom adapter plate.

Selected mounting hardware, as coordinated with the main task: four native Front Panel Express WGO40 M4 female load standoffs, 6 mm body length. Mount the router 6 mm above the new panel. An M4 × 8 screw, 1 mm washer and 2.5 mm ear leave 4.5 mm nominal thread engagement. Use washer OD ≤9 mm, ID about 4.3 mm. The selected catalog standoff body OD is 5 mm. Main-task native FPD verification remains the authority for catalog selection and length semantics.

Measured envelope: 171.800 × 166.229584 × 29.300 mm. Including the standoffs: 35.300 mm above panel. STEP normalization is rotate +90° about X, then translate (-15.137822530062, -40.970067179885, -7.239482215666). Normalized bounds are X [-85.9,85.9], Y [-81.799573,84.430011], Z [0,29.3]. Ethernet, power and two Wi-Fi antenna interfaces are at -Y; cellular/GPS antenna ports and the SIM access panel are at +Y. Therefore all connector plugs cannot face downward simultaneously; route the upper-side coax in the adjacent wiring channel.

The official [Peplink UBR Plus datasheet](https://download.peplink.com/resources/peplink_ubr_plus_datasheet.pdf), page 4, specifies 24 W maximum, 10–30 VDC input, 720 g weight, -40 to65 °C operation, four cellular SMA, two Wi-Fi RP-SMA, and one GPS SMA ports. Its overall dimensions differ from the supplied model; cabinet packing uses the actual supplied STEP. The current [Peplink technical specifications](https://www.peplink.com/compare/tech-specs/ubr-plus.pdf) also state24 W maximum and166.2 mm overall depth. The older [manufacturer FAQ](https://download.peplink.com/resources/peplink_ubr_plus_faq.pdf) says18 W; use the higher24 W for thermal planning. An electrically closed metal cabinet requires external antenna routing for the intended radio links.

Reserve40 mm beyond each connector end and10 mm at each side as chosen layout allowances. These are not vendor minimums. They assume appropriate patch-cable/coax assemblies rather than long rigid antennas screwed directly to the router. Actual plugs, boot lengths, bend radii and SIM cover service access need comparison against the final cable selection. Vertical heat-sink fins remain aligned with vertical panel Y after normalization.

## OZ51x dual TX snap housing

The existing base and cover are three-dimensional unfilled MJF PA12 parts, including snap beams and integral mounting ears. They are not aluminum mounting plates that can be reproduced as planar FPD files. Direct backpanel mounting uses their four retained4.5 ×9 mm slots. Slot pitch is106.2 ×96 mm; the ears are3 mm thick.

The source installed STEP has its wall mounting plane normal to +X, despite its narrow-looking global XY footprint. Undo its installation transform by translate(16.36,0,-46.1) then rotate -90° about Y. Canonical slot centers are(±53.1,-22) and(±53.1,74). For fiber/DE-9 I/O down, then translate(0,-32.2,0) and rotate180° about Z. Final slot centers are(±53.1,54.2) and(±53.1,-41.8). The32.2 datum deliberately gives clean mounting coordinates; tiny raised labels put the geometric bounding-box center0.0005 mm off it.

Normalized housing envelope including mounting ears and labels:116.200 ×138.099 ×32.720 mm. Use four M3 male studs with source-specified9 ×3.2 ×0.8 mm washers centered in the slots and M3 nuts. Main task selected native WGU30 M3 ×12 mm studs. The3 mm ear plus0.8 mm washer plus a2.4 mm full nut nominally requires6.2 mm; verify actual usable threads and nut retention. Avoid excessive torque on the printed ears.

The source README documents approximately47 mm additional outward space for30° cover opening plus hand access. The initial source assembly remains a prototype requiring actual latch/module/connector qualification. Reserve40 mm at the lower fiber/DE-9 face and30 mm at the upper SMA face as chosen layout allowances. Source internal spool radius is15 mm; it does not qualify the actual external fiber bend radius. Turning the I/O downward rotates the original gravity drains into a different attitude; this internal housing is not an environmental boundary and no ingress rating is implied.

## Geometry verification

The audit checks imported STEP geometry against nominal shafts,9 mm OD washers, and10 mm OD ×40 mm axial tool-access cylinders at every mounting point. All recorded overlap volumes are0.0 mm³. Router standoff bodies are modeled as5 mm cylinders below the mounting ears; OZ12 mm stud shafts are tested through the ears. These checks establish nominal CAD clearance; they do not determine adhesive hardware rated capacity, screw tightening torque or vibration qualification.

Normalized artifact STEP files are exported for use in the final cabinet assembly. The primary source STEP and original component files were not changed. Source copy `peplink_source.stp` has been included solely to make this audit reproducible with the short Q: drive alias.

### Source STEP validity limit

`vendor_validity_audit.json` identifies inherited Peplink source defects:4 of36 source solids fail B-rep validity (two have negative signed volume). The normalized STEP re-import has3 invalid small connector solids. Both main case solids, the2.5 mm mounting-ear solid, and the main board remain valid; the mounting-ear body volume agrees across export/re-import to within0.00001 mm³. The complete Peplink vendor assembly is therefore retained as a visual and dimensional reference, not represented as an all-valid manufacturing solid. Final inter-component verification should use conservative connector/service envelopes around the router in addition to nominal B-rep intersection checks. OZ re-import is valid and retains2 solids.
