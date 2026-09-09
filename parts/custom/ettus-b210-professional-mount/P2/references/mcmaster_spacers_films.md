# P2 McMaster spacer, shim, and contact-film research

Catalog observations: 2026-09-08. Product detail pages were inspected in the live McMaster Chrome catalog; web-index tables were used to discover products. Prices below are USD, before tax/shipping, and are observations rather than quotes. Each selected product detail page displayed “Delivers tomorrow” in this browser's delivery context. Recheck at ordering. No purchase was made.

## Spacers

| Status | McMaster product | Verified catalog geometry | Material information | Price |
|---|---|---|---|---|
| Preferred catalog candidate | [94669A146 aluminum unthreaded spacer](https://www.mcmaster.com/94669A146/) | Length 30 ±0.13 mm; OD 10 ±0.13 mm; ID 5.300 ±0.13 mm; for M5 | Catalog identifies Aluminum, tensile strength 45,000 psi, Rockwell B50. Alloy, temper, yield strength, and anodized finish are not stated. | $2.14 each for 1–24; $1.81 for 25–99; $1.61 for 100+ |
| Stainless alternative | [92871A227 stainless unthreaded spacer](https://www.mcmaster.com/92871A227/) | Same dimensions and tolerances | 18-8 stainless, ASTM A582, tensile strength 80,000 psi, Rockwell B60. Yield strength not stated. | $5.46 each for 1–9; $4.61 for 10+ |

The aluminum family also lists 30 mm long × 13 mm OD × 5.3 mm ID as **94669A195**; this larger part was verified in the catalog table only and its detailed tolerances were not independently checked. No 32 mm long M5 spacer was found in the inspected aluminum family (30 and 35 mm were present). Absence in this family is not proof that McMaster cannot supply one.

Four 94669A146 spacers cost $8.56 at the observed small-quantity price. Measure and match lengths, then adjust using metal shims and the assembled gap inspection. The ±0.13 mm catalog length tolerance does not meet a ±0.05 mm custom-part length callout. Do not relabel this catalog part 6061-T6 or assume a yield strength. Engineering must screen spacer compression, joint preload, and bearing using suitable material evidence before adopting it. ID minimum 5.17 mm clears nominal M5 thread major diameter but gives less alignment freedom than a 5.5 mm drilled hole.

## Adjustment shims

| Function | McMaster product | Verified geometry and tolerances | Purchase unit / price |
|---|---|---|---|
| Fine, approximately 0.05 mm | [98126A161 stainless ring shim](https://www.mcmaster.com/98126A161/) | 18-8 stainless, ASTM A240; ID 1/4 in, +0/+.011 in; OD 3/8 in ±.002 in; thickness .002 in ±.0005 in | Pack 10, $8.31 |
| 0.10 mm | [98055A095 spring-steel shim](https://www.mcmaster.com/98055A095/) | DIN988; ID 5 mm +.03/+.40; OD 10 mm −.47/−.04; thickness .10 mm −.03/0; minimum Rockwell B85 | Pack 50, $5.52 |
| 0.50 mm | [98055A098 spring-steel shim](https://www.mcmaster.com/98055A098/) | Same ID, OD, DIN988 and hardness; thickness .50 mm −.05/0 | Pack 50, $6.90 |

The fine shim converts to ID 6.350–6.6294 mm, OD 9.4742–9.5758 mm, and thickness .0381–.0635 mm. It is an inch-size substitute, not an exact M5/.05 mm washer. Its minimum annular area is approximately 36.0 mm² before accounting for eccentric placement; the joint's engineering check must account for reduced and possibly uneven bearing. Center it during assembly. No exact .05 mm metric M5 shim was verified.

The metric spring-steel products suit the preliminary dry indoor environment; they are not corrosion-resistant stainless. Inspect for rust and burrs, and keep precision shims dry. Measure the actual stack, use the fewest washers, and do not exceed four stacked shims at one location without redesign. The four-shim caution comes from McMaster's shim guidance. These are adjustment parts, not substitutes for the specified full bearing washers under screw heads and nuts.

## Single-adhesive PET anti-mar film

[8689K65 adhesive-backed polyester film](https://www.mcmaster.com/8689K65/), one 27 × 20 in semi-clear sheet, **$4.00**. Catalog thickness .005 ±.0005 in = **.127 ±.0127 mm**, acrylic adhesive, smooth PET surface. Catalog adhesive and product temperature range **−20 to150°F = −28.9 to65.6°C**; outdoor use is marked No.

The table does not explicitly establish whether the stated film thickness includes adhesive. Use this as a procurement candidate: measure the bonded stack after liner removal, enforce the mount's installed-film maximum of **0.20 mm**, and record the actual thickness before final gap adjustment. Do not assume .20 mm nominal stock. Adhesive bonds to the mount only; the device bears against the exposed PET face. Cut separate patches to the drawing; no double-sided adhesive contacts the device. Clean and fully dry the metal before applying; do not soak the installed film in solvent. The catalog lists isopropyl alcohol and water among chemicals not recommended for this product.

Film has no credited structural, preload, friction, cooling, or grounding function. Verify adhesion, wear, marking, and long-duration temperature in the prototype. The product's mechanical-property values are presented by McMaster for comparison rather than guaranteed design properties. Its catalog temperature limit is not a demonstrated operating limit for this mount. Stop qualification if film temperature approaches that limit; select a better qualified film if needed.

## Adoption status

The P2 design lead selected 94669A146 (four per version), 8689K65 (eight 16 × 20 mm R1 patches per version), and the three listed shim sizes as required. 92871A227 remains an unselected alternative. Parent CAD and engineering calculations must reconcile the 10 mm spacer OD, catalog length variation, measured film stack, shim bearing, and final assembled clearance. No supplier CAD was downloaded and no physical stock was measured.
