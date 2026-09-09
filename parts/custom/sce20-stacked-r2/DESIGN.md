# SCE-20 aluminum mounting system — R2 stacked

This revision compacts the components below the unused upper-left area. The
431.8 x 431.8 x 6 mm aluminum main panel retains the original Saginaw SUBPANEL
R6.35 outline and all six factory holes measured from the supplied STEP. The
rear seating plane remains at enclosure Z-112.395. The component face moves
2.825 mm toward the door to enclosure Z-106.395. Dimensions are millimeters.

The Bedrock computer remains on its 6 mm adapter directly against the main
panel, preserving the intended conductive interface. A removable 180 x 210 x
4 mm carrier places the Peplink router above it. The carrier underside is
70 mm above the main panel, and its 146 x 160 R5 opening reduces obstruction
above the Bedrock. Four 20 mm FPE female standoffs plus 50 mm M3 hex extensions
support the carrier. The router sits on four 6 mm FPE standoffs above the
carrier. The Bedrock thermal geometry and its two 0.050 mm pocket interfaces
are unchanged from the R1 adapter revision; thermal performance is unqualified.

The B210 uses its R1 4 mm adapter, raised to underside Z50 above the OZ housing
on four 20 mm FPE female standoffs plus 30 mm M3 hex extensions. This compact
height requires removing the upper B210 assembly before the documented OZ
cover motion. Independent cover access would require a taller stack. The OZ
housing mounts through its integral ears directly to the main panel.

The Mean Well N2 side-tab adapter remains parallel to the main panel at the
right. Its center X379.9 and Y65.6 preserve both full 100 mm source airflow
reservations. Those corridors retain nominal 1.075 mm lateral clearance to
the right factory nuts and 1.795 mm clearance to the enclosure end walls.
These are geometric planning zones. Enclosure heat rejection, side-orientation
derating and operating temperature remain outside this geometric review.

The final placements, expressed as XY centers and mounting-face height, are
Bedrock (122,107,0), Peplink (122,90,80), B210 (282,106,50), OZ (282,107,0), and
Mean Well (379.9,65.6,0). B210 and Mean Well rotate 180 degrees about Z. The
explicitly reserved region X0..215.9 and Y250..431.8 contains no components or
declared cable/air envelopes. Existing factory fasteners and their tool access
remain part of that region. This is a bounded feasible compact arrangement,
not a mathematical proof of global optimality over arbitrary replacement parts.

FPD front is the accessible component side. CAD positive Z points toward the
door. FPD XY uses the lower-left corner. Transform from these coordinates to
the enclosure STEP is (x-215.9,y-215.9,z-106.395). Reverse-side adapter machining
uses the same XY coordinates without mirroring. The four original panel nuts
move forward 2.825 mm; the enclosure studs remain fixed. Independent exact
source-solid checks confirm the installed components and stepped support
envelopes clear the enclosure and four diameter-30 by 60 mm socket probes.
The tallest component is 109.300 mm above the main panel, leaving 128.235 mm
to the nearest closed-door pocket.

Load paths run through device fasteners, plates or ears, native FPE anchors,
the main panel and four factory studs. The raised carriers also use separate
hex extensions. These references establish nominal fit and service access;
they do not assign shock, vibration or bonded-anchor load ratings. Recessed
anchor flanges may share a zero-volume boundary with a neighboring adapter
underside. The installed shafts and plates must retain positive clearance.

Bare aluminum preserves the intended conductive faces. Finished thickness,
flatness, alloy, surface condition, screw penetration and both Bedrock thermal
pocket depths remain drawing requirements for supplier acceptance. Native FPD
hardware objects define production cavity machining; the integration STEP
contains catalog envelopes and simplified threads.

The repository design role remains `plate` and its hard score threshold
remains 70. Mechanical evaluation and design-language scoring are reported
separately. Factory interfaces, the thermal contact face and the deliberately
unused area constrain decorative changes. A score below 70 remains a failed
repository design gate; the functional constraints are documented rather than
lowering the threshold or adding features only to raise that score.

The full R2 evaluation measured **48.7/100, grade D**, below the unchanged
70-point hard threshold. All ten build, export, reimport and mechanical checks
passed. The main score penalties are the empty rear seating face, factory
holes outside a shared pattern, and component-specific anchor spacing. The
suggested deep rear relief, extra features and relocated mounting patterns
would conflict with the preserved seating/thermal interfaces or selected
component patterns. `exports/repository_full_evaluation.json` records this
failed design gate explicitly; no automated promotion was performed.
