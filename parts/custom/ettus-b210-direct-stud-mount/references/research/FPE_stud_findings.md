# Front Panel Express stud interface — preliminary direct mount

Research date: 2026-09-08. No order, supplier contact, physical measurement or load test was performed. FPE stud catalog geometry is available; a rated assembly capacity is not established.

## Selected interface

Specify **four Front Panel Express load studs, M3, 12 mm geometric length, catalog identifier WGU30, reverse side, depth offset 0, factory-installed on the proposed 6 mm panel**. WGU30 is the Front Panel Designer catalog identifier, not a McMaster part number or a standalone purchase SKU. The stud coordinates proposed by the design task are X = ±68.000 mm, Y = ±60.0075 mm, a 136.000 × 120.015 mm pattern. The final supporting panel and its boundary restraints remain to be designed; a 6 mm interface coupon does not qualify the complete installation.

The [official FPE 6.5.1 download page](https://www.frontpanelexpress.com/front-panel-designer/download) links the [Linux Debian package](https://assets.frontpanelexpress.com/fpd/Version-6.5.1/FrontDesign-US-6.5.1-amd64.deb). The package was downloaded for reading its catalog files; it was neither installed nor run. Its SHA-256 is `a9969415df52668fd9b0d85ff47d838c34b109c0b650978006e9e482d184bb1a`. The extracted `Bolt.d/10-Base.ini`, local manifest and reproducible inspection script are retained here.

## Catalog dimensions and fit interpretation

The following dimensions are parsed/interpreted from that manufacturer's catalog configuration. Values of 1000 internal units per millimeter are corroborated by the M3 thread diameter and the independently documented 1.1/2.3 mm pocket depths. These are nominal display/manufacturing parameters, not a toleranced hardware drawing.

| Item | Standard M3 stud | Selected M3 load stud |
| --- | --- | --- |
| Catalog identifier / type | GU30 / GLSU | WGU30 / WGLSU |
| Available geometric lengths, mm | 6, 7, 8, 10, 12, 14, 16, 18, 20 | 6, 12, 20 |
| `PlateDiameter` parameter, interpreted cavity diameter | 7.0 mm | 12.1 mm |
| `SocketHeight`, pocket depth | 1.1 mm | 2.3 mm |
| Base diameter from `DrawPath`: PD − 0.2 mm | 6.8 mm | 11.9 mm |
| Base axial thickness from `DrawPath` | 1.0 mm | 2.2 mm |
| Stud nominal projection at zero depth offset | Selected geometric length | 12 mm |
| Base top in zero-offset drawing | At panel reverse surface | At panel reverse surface |

The drawing paths put the stud base below the panel surface, with a nominal 0.1 mm axial difference between base thickness and pocket depth. They do not require a proud flange below the adapter. **Flush seating is therefore the intended nominal geometry, subject to inspection.** The actual installed projection, thread lead, base flushness, surrounding adhesive and tolerances are not specified by these paths. Inspect them before relying on flush adapter contact or thread engagement. Do not remove material from an installed stud or its bond to correct fit.

The catalog contains a name M4 for a load-stud entry whose `ThreadSize` value remains 3000; the product page also has an incomplete thread summary. This inconsistency is a further reason to use the consistent M3 entry here and confirm the exact production variant in Front Panel Designer. No M4 geometry is selected.

## Installation and panel rules

[Current FPE stud/standoff help](https://docs.frontpanelexpress.com/elements/studs_standoffs.html) identifies standard and load versions; standard types can be bonded or pressed. It gives required cavities of 1.1 mm standard and 2.3 mm load, with at least 0.5 mm material between cavity edges and a panel edge or through-cut, and 0.5 mm remaining depth to an opposing cavity. Additional depth offset moves a stud deeper and must leave at least 0.5 mm rear material. Load elements require a panel at least 3 mm thick. Select reverse-side placement and zero offset for this interface; do not manually add duplicate pockets under a native stud element.

For a 6 mm panel, the load pocket alone leaves a **calculated nominal 3.7 mm** floor. From a 12.1 mm cavity diameter, the stated 0.5 mm in-plane rule implies a **calculated 6.55 mm** minimum stud-center distance to a panel edge or through-cut. These minimum fabrication distances do not establish structural capacity or permissible adjacent-pocket interaction. Check all other panel holes, engravings and pockets against the full installed geometry.

The [FPE 6.2 release notice](https://www.frontpanelexpress.com/newsletter/fpe/10/newsletter.html) describes load studs as using a short anchoring thread screwed into the panel. The current help describes bonding broadly, and the 6.5.1 catalog still assigns both variants to `System=GLUE`; the load drawing includes an anchoring-thread representation with a 0.5 mm pitch parameter. Specify the native **load stud WGU30**, which conveys the manufacturer's intended installation, rather than a generic adhesive stud. The exact anchoring-thread size, material, adhesive, cure and installation process have not been independently established. Do not substitute a plain bonded or self-clinching stud and retain the same engineering claim.

## Capacity, temperature and ordering limitations

No numeric axial, shear, torque-out, bending, fatigue, vibration, adhesive-creep or temperature rating was found in the inspected FPE pages or catalog file. A descriptive “load” category is not an allowable design load. Engineering must state required forces and moments, obtain or physically demonstrate the selected installed joint's performance, and include installation preload and locknut prevailing torque. Neither the screw nor the nut strength class establishes the FPE anchorage strength. The nylon nut's temperature limit also does not establish the stud adhesive's temperature rating.

The [FPE aluminum data sheet](https://www.frontpanelexpress.com/downloads/FPE/Aluminum-Datasheet.pdf?v2=) identifies its 5–10 mm stock as EN AW-5754 H22, minimum listed yield 110 MPa, not 6061-T6. Its listed raw-stock thickness tolerance is 0.8 mm in that range, with the stated whole-sheet qualification; manufacturing tolerance is ±0.1 mm. The 1–4 mm range is AW-5005 H14/24. Reconfirm actual material, finished thickness and local pocket floor before manufacturing. A separately specified machined 6061 adapter is a different part/material.

Use Front Panel Designer's **Insert > Studs/standoffs** native load-stud element at the four coordinates, then inspect the program's 3D view and exported STEP. [FPE ordering guidance](https://www.frontpanelexpress.com/faq) accepts uploaded FPD files in the webshop; conversion from other CAD through its design service incurs a fee. The current [software page](https://www.frontpanelexpress.com/front-panel-designer) lists STEP, DXF, SVG and PDF exports. No FPD file, price quote or actual supplier acceptance has been produced by this research. Keep the panel and stud placement parameters editable until installation requirements are fixed.

## Ettus attachment status

The [official Ettus enclosure kit](https://www.ettus.com/all-products/usrp-b200-enclosure/) identifies a full steel enclosure for green B200/B210 boards with USB-B, adhesive feet and 8 mm kit screws. The [current UHD manual](https://files.ettus.com/manual/page_usrp_b200.html) says the B200/210 enclosure assembly instructions are a printed kit insert. Neither page specifies an approved external mounting penetration or chassis attachment capacity.

The root geometry task freshly identified the four modeled under-foot components as SOS_M3-10 and the opposing PCB screws as M3 × 8. The [official PEM SOS-M3-10 page](https://www.pemnet.com/products/product-finder/sos-m3-10/) identifies an M3 × 0.5 **through-hole** standoff, not a blind insert. The root task has retained the official PEM section drawing and resolved the counterbore as being on the free barrel/PCB side. These findings support the thread identity but do not grant the unobstructed 10 mm engagement that a through standoff alone might suggest: the opposite screw occupies it.

The user has physically reported M3 threads with roughly 4 mm available depth. The current design task limits actual external screw penetration to 2.4–2.9 mm, with separation from the opposing screw checked at all four positions. That is a task-specific acceptance limit pending direct assembled measurement, **not an Ettus allowable penetration specification**. Inspect thread condition, full engagement, PCB screw separation and metal-to-metal seating with power disconnected; do not change the radio's internal fastener length by default.
