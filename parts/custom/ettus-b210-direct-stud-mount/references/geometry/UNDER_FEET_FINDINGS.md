# Fresh underside interface audit

Status: nominal STEP geometry and product metadata verified on 2026-09-08. This is not a physical inspection or a mounting-load qualification. The user's confirmation that mounting threads are present under the feet is separate evidence; actual thread size, access and usable engagement still require confirmation on the unit.

The original supplied STEP was imported afresh using CadQuery 2.7 / OpenCASCADE and preserved unchanged. SHA-256 before and after the audit was `c59b649ccc6a4c128885fd9e64acfd74d756b23bbcff7f119e21a4acb426c912`. The imported assembly contains 196 solids and is valid. STEP units are millimetres. No measurements in this note are taken from a rendering or inferred from the filename.

## Datums and four interfaces

The normalized frame rotates the source about X by +90 degrees, then about Z by +180 degrees, and translates by `(58.5005, 80.6355, 1.210)` mm. The flat outside face of the bottom pan is datum Z = 0; +Y is the RF connector end. All dimensions below are nominal measured millimetres, without manufacturing tolerances.

| Foot solid | X | Y | Underlying standoff solid | Existing PCB screw solid |
|---|---:|---:|---:|---:|
| 174 | -46.7995 | +60.0075 | 7 | 150 |
| 175 | +46.7995 | +60.0075 | 5 | 151 |
| 176 | +46.7995 | -60.0075 | 6 | 152 |
| 177 | -46.7995 | -60.0075 | 8 | 153 |

The mounting-axis rectangle is **93.599 by 120.015 mm**, centered on `(0, 0)` in this frame. This differs from the pan/enclosure geometric center in Y; do not center the hole pattern on an overall enclosure bounding box. The four feet are nominally coaxial with the standoffs and screws, with maximum diameter 12.700 and height 3.556 below Z = 0.

XCAF assembly/product labels were matched to fresh imported solids using geometric centroids and volumes. There were zero unmatched product bodies. The relevant labels are:

| Solid IDs | Product metadata |
|---|---|
| 0 | `ETTUS_USRP_B2XX_BOTTOM_CVR_WELD` assembly path; leaf `SOLID` |
| 5-8 | `SOS_M3-10` |
| 9 | `ETTUS_B2XX_PCB_REV6` |
| 150-153 | `M3X8MM_BUTTON-HEAD_TORX_SS` |
| 174-177 | `FOOT_RUBBER_ADHESIVE_745120-01` |

## Contact geometry and intrusion limit

| Feature | Freshly measured nominal geometry |
|---|---|
| Bottom-pan outside plane | Z = 0; flat outer face X -58.4995 to +58.5005, Y -72.4905 to +78.2155 |
| Bottom-pan inside plane / sheet thickness | Z = 1.210 / 1.210 mm |
| Four pan openings | Diameter 4.191 through sheet |
| Standoff outer end face | Flush at Z = 0; hexagon 4.800 across flats, 5.542 across corners |
| Hex end thickness | Z = 0 to 1.000, extending inward rather than below the pan |
| Standoff external barrel | Diameter 4.200, Z = 1.000 to 10.000 |
| Smooth bore nearest pan | Diameter 3.000, Z = 0 to 6.000 |
| Smooth bore nearest PCB | Diameter 3.200, Z = 6.000 to 10.000 |
| PCB bearing plane | Z = 10.000; PCB top Z = 11.5748 |
| Existing PCB screw tip | Z = **3.5738** at all four locations |
| Existing screw main shaft | Diameter 2.9972, Z = 3.8278 to 11.5748 |

A coaxial cylinder probe of radius 0.010 mm was intersected against every candidate assembly body at each foot axis. The first material encountered from Z = 0 is the existing PCB screw at Z = 3.5737999. This confirms the collision geometry independently of the screw's bounding box. The internal screws already occupy the same bores from the PCB side.

**3.5738 mm is not allowable screw penetration or usable thread engagement.** It is the nominal separation from the pan datum to an existing modeled screw tip. External screw length, seating position, actual pan/head geometry, entry chamfer, incomplete threads, manufacturing variation and a deliberate no-contact margin must all be included before choosing screw penetration. As arithmetic only, a 2.900 mm projection would leave 0.6738 mm nominal model-to-model tip separation; this does not establish safe fit or two millimetres of full thread engagement.

The STEP has no helical thread or entry chamfer on these standoffs; its lower bore starts sharply at Z = 0. `SOS_M3-10` and the screw name are model metadata, not a measured thread specification. Use the separate manufacturer research to resolve the catalog identity, and verify the actual device before release. The old vendor README's assertion that SOS is blind is not supported by this geometry and should not be carried into the new design as an established fact.

## Flush plate implications

With only solids 174-177 excluded, no remaining body extends below Z = 0. The minimum remaining Z is -0.0000001 mm, which is numerical tolerance. In this STEP, the feet are the only under-pan protrusions. The four standoff hex ends are flush with the pan, so the STEP does not require a plate relief for proud PEM heads.

Physical adhesive residue, pan flatness and actual clinch-head proudness may differ from nominal CAD and must be inspected. Avoid adding a large relief under a flush head without a reason: it removes local plate contact that would otherwise support that end face. The small ideal overlaps between the standoff head/barrel and the pan are the source assembly's simplified clinched joint representation, not a fit validation of the actual formed metal. No pan alloy, insert material, clinch strength, stripping strength, torque or load rating is derived here.

## Completed checks and files

- Original-file hash before/after unchanged; fresh import, millimetre units, 196-solid validity checked.
- Product labels freshly mapped through the STEP assembly tree, with zero unmatched bodies.
- All four axes, bores, end planes and screw-tip obstructions measured; all non-foot bodies scanned for below-pan protrusions.
- Four true CAD X-Z sections generated at the four axes and visually inspected after rasterization; no clipping or unreadable callouts.
- Section DXF reopened by ezdxf audit with zero errors; file units are millimetres. It is reference geometry made of sampled section curves, not a part manufacturing drawing. Each station is separated horizontally for viewing; layers retain station and solid IDs.

Reproduce with:

```powershell
& 'C:/venvs/cadquery/Scripts/python.exe' 'parts/custom/ettus-b210-direct-stud-mount/references/geometry/under_feet_audit.py'
```

The script imports the supplied original path by default; `--source <path>` can select an identical replacement copy. It writes `under_feet_audit.json`, four `sections/foot_*_xz.svg` files, and `sections/under_feet_sections_mm.dxf` into this folder. The JSON includes raw face measurements, product assembly paths and probe results.

Before installing an external screw, confirm the actual thread and its entry, measure each available depth without advancing against the PCB screw, establish permitted full engagement and no-contact margin, and confirm the local shell/insert load path. Do not use fastening torque to detect contact with the existing internal screws.
