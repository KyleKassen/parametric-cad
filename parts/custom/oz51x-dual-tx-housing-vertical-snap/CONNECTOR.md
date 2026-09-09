# Front power and control connector

This prototype places one DE-9 electrical connector between the two SC/APC
fiber ports. The DE-9 carries DC power, enables, and monitoring for both
transmitters. The RF and TTL signal inputs stay on their existing SMA
connectors on the opposite end of the enclosure.

Research checked 8 September 2026. The references below distinguish
manufacturer dimensions and electrical specifications from the allowances
chosen for this printed prototype.

## Installed modules and evidence

The intended TX pair supplied for this design is:

| Bay | Optical Zonu part number | Evidence and remaining checks |
| --- | --- | --- |
| RF | A13-Z516-D31-AS-SL | The manufacturer's OZ51x V4.0 ordering table identifies A13 as transmitter, Z516 as 30-6000 MHz, D31 as 1310 nm, A as 50-ohm SMA, S as SC/APC, S as single-mode fiber, and L as LNA. |
| TTL | A13-Z510TTL-D31-AS-S | The official TTL product information confirms 12 V operation, SMA signal input, and a ten-pin header for monitoring/alarm. The exact SKU's complete header pinout, current specification, and mechanical outline have not been independently verified. |

The user's receiver pair, A23-Z516-00-AS-S and A23-Z510TTL-00-AS-S, is context
for a future matching RX enclosure. This part is the TX enclosure. Do not
assume a TX enable connection has a function on an RX module.

The manufacturer-authored [OZ51x V4.0 datasheet, 19 January 2022](https://www.shoshin.co.jp/c/opticalzonu/pdf/OZ5xx%20Datasheet.pdf)
is hosted by distributor Shoshin. Its pages 2, 6, and 11 establish the RF
electrical specification, header functions, and ordering-code interpretation.
An unchanged copy is saved as `datasheets/optical-zonu-oz51x-v4-2022.pdf`.
At 12 V, the with-LNA transmitter specification is 140 mA typical and 160 mA
maximum, or 1.68 W and 1.92 W electrical input. These are family datasheet
values, not measurements of the user's individual unit. Total enclosure
heating also includes the TTL module, whose current remains unverified.

The RF module's documented ten-pin header functions are:

| Module header pin | Function |
| --- | --- |
| 1 | Laser enable: +12 V enables; ground or open circuit disables |
| 3 | Ground |
| 5 | +12 V supply |
| 7 | Analog laser-bias monitor, 0.1 V per 10 mA |
| 9 | Open-collector laser-bias alarm, 25 mA rating |
| 2, 4, 6, 8, 10 | Not connected |

This table describes the RF module header; it does not assign DE-9 contact
numbers. The alarm needs a compatible external receiving circuit. Check the
ordered unit's alarm polarity and controller interface before wiring it.

Official TTL references:

- [OZ510 TTL product page](https://www.opticalzonu.com/products/small-modules/oz510-ttl/)
- [TTL series description](https://www.opticalzonu.com/solutions/special-functions/ttl-series/)
- [Small-module summary confirming 12 V TTL operation](https://www.opticalzonu.com/products/small-modules/)

The public product pages support the general architecture, but they do not
verify the detailed TTL header assignment for this specific part number.

## Proposed harness functions

One DE-9 is sufficient for the following eight functional nets, assuming the
two modules use a common +12 V supply and common return. This is a proposed
functional allocation, not an approved pin assignment or released wiring
drawing.

| Net | Intended connection |
| --- | --- |
| Shared +12 V | Power to both modules |
| Shared 0 V | Power return and signal reference for both modules |
| RF enable | Independent RF transmitter laser enable |
| RF monitor | RF transmitter analog monitor output |
| RF alarm | RF transmitter alarm output |
| TTL enable | Independent TTL transmitter enable, subject to its verified header specification |
| TTL monitor | TTL transmitter monitor output, subject to its verified header specification |
| TTL alarm | TTL transmitter alarm output, subject to its verified header specification |
| Ninth contact | Unassigned spare; decide in the final harness drawing |

Do not copy the inherited housing family's suggested DE-9 contact numbering
as though it were a manufacturer pinout. After checking both physical
modules, issue a harness drawing that specifies contact numbers, connector
gender and viewing direction, module header pin numbers, wire identification,
supply protection, and controller input/output requirements. Verify the
harness against that drawing before applying power.

Label this interface `POWER / CTRL`. A DE-9 connector does not imply RS-232
or compatibility with a computer serial port. Keep its custom cable clearly
identified. Keep the connector shell/shield treatment distinct from the
power-return assignment in the electrical design.

## Candidate connector and manufacturer dimensions

The candidate is the [Amphenol L177SDE09S](https://www.amphenol-cs.com/product/l177sde09s.html),
a nine-contact female straight solder-cup connector. Use separate mounting
hardware through the flange clearance holes; this candidate is not a
connector with integral front screwlocks.

Source: [Amphenol drawing C L177SDXXXS, revision 2](https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/l177sdxxxs.pdf).
The relevant dimensions from the nine-position drawing are:

| Feature | Manufacturer dimension, mm |
| --- | ---: |
| Flange overall length | 30.81 |
| Flange overall height | 12.55 |
| Mounting-hole center spacing | 24.99 |
| Flange clearance-hole diameter | 3.05 |
| Rear body overall length | 19.20 |
| Rear body overall height | 10.72 |
| Rear body depth | 4.1 |
| Solder-cup extension | 3.1 |

Mount the metal flange from outside the enclosure in the shallow printed
seat, with the solder cups and retaining nuts inside. This preserves mating
projection better than putting the flange behind the full printed wall.
Choose jackposts/bolts long enough for the actual flange, remaining wall,
washer, and nut stack. Verify the mating cable hardware's thread, normally
4-40 for this style; do not mix 4-40 and M3 hardware.

## Printed prototype footprint

The following are design allowances for this housing. They are not quoted
from the connector drawing and are not a certified manufacturer footprint.

| Feature | Prototype choice |
| --- | --- |
| Opening maximum extents | 20.8 x 11.8 mm |
| Opening shape | Rounded D profile with 10-degree sides |
| Opening corner radius | 2.1 mm, with geometry compensated to retain the stated outer extents |
| Mounting-hole pitch | 24.99 mm |
| Printed mounting holes | 3.4 mm diameter |
| External flange-seat recess | 0.4 mm |
| Orientation | Connector long axis follows enclosure height |

The long-axis orientation fits the narrow vertical housing while leaving
the electrical connector centered between the two fiber ports. Maintain
clearance behind it for the flange hardware, solder joints, insulation, and
wire bends; this variant reserves a 33 mm wide corridor for this area.

As an independent comparison, the [Amphenol generic D-sub catalog, page 3](https://cdn.amphenol-cs.com/media/wysiwyg/files/documentation/datasheet/inputoutput/io_dsub_hybrid_tw.pdf)
lists an E-shell rear-mount cutout with 20.5 x 11.4 mm extents, 10-degree
sides, R3.4 corners, and 25.0 mm mounting pitch. That generic profile has a
different corner treatment and mounting context. It is a reference, not a
substitute for checking the selected connector and cable in this prototype.

Print the connector fit coupon with the intended material, nozzle, layer
height, and orientation before committing to a complete enclosure. Check
the purchased connector body, flange seating, mounting fasteners, and the
fully mated cable. Confirm that the 0.4 mm recess does not cause the mating
plug/hood to bottom on the printed face before its contacts fully engage.
Allowances can then be adjusted in the part parameters if needed.

Do not infer an enclosure ingress rating from the connector choice or this
fit check. This is a cabinet-mounted printed sub-enclosure.
