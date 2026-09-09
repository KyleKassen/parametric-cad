# SCE-20H2010LP compact stacked panel set

**R2 quote/prototype package — 9 September 2026.** Bedrock remains directly against the aluminum backpanel, with Peplink on a removable windowed carrier above it. B210 mounts above the OZ housing; the PSU stays at the right. The cabinet is upright and cable entry is at the bottom.

The reserved upper-left rectangle is **X0–215.9, Y250–431.8 mm**, excluding the original enclosure hardware and its tool space. The lower part of the upper-left quadrant contains Bedrock cable allowance; the entire quadrant is not an empty mounting area.

## Front Panel Express quote

Quote **one of each** native design. Obtain supplier acceptance of the special machining, finished tolerances and material before ordering.

| Native design | Aluminum plate, mm | Included native hardware |
|---|---|---|
| `Backpanel_R2.fpd` | 431.8 ×431.8 ×6; original R6.35 outline and six enclosure holes | 12 M3 male LOAD studs, 12 mm; 8 M3 female LOAD standoffs, 20 mm |
| `Peplink_Carrier_R2.fpd` | 180 ×210 ×4; 146 ×160 R5 through-window | 4 M4 female LOAD standoffs, 6 mm |
| `B210_R2.fpd` | 150 ×148 ×4 | None |
| `Bedrock_R3.fpd` | 166 ×184 ×6; thermal pockets on both faces | None |
| `MeanWell_R2.fpd` | 72 ×316.8 ×6 maximum outlined envelope | None |

The three existing adapters are copied unchanged, with their native STEP audit evidence. The new backpanel and carrier are being verified separately; the final native verification report records their acceptance. The OZ base and cover remain PA12 printed parts and are not additional aluminum plates.

## Installation information

- `LAYOUT_R2.png` / `.svg`: front-view placement, mounting points and reserved cable/air space.
- `SIDE_VIEW_R2.png` / `.svg`: stack heights and removable upper assemblies.
- `HARDWARE_BOM.csv`: five plates, included FPE hardware, purchased extensions, screws and retained printed parts.
- `MOUNTING_COORDINATES.csv`: 34 through-hole and 24 native-hardware locations across the five plates. Drawing origins are each plate's lower-left corner; front is the component side. The through-window and thermal-region paths remain in the native source inputs.
- `ORDERING_NOTES.md`: supplier requirements, screw stacks, installation sequence and service limits.

The carrier underside is **70 mm** above the backpanel; Peplink mounting ears are at **80 mm**, and its top reaches **109.3 mm**. The B210 adapter underside is **50 mm** high, above the closed OZ housing at **32.72 mm**. **Remove the B210/adapter assembly before opening OZ.** Remove Peplink and its carrier together for Bedrock service; removing the carrier does not disturb the lower thermal interfaces.

The independent component/support study passes 153 pair checks for the selected arrangement, plus factory-socket and upper-carrier tool checks. Use a **2.5 mm hex key/bit with an outside envelope ≤8 mm** for the first 40 mm above the carrier washers. Details and reused-adapter hashes are in `verification/`.

This is a compact arrangement selected under the stated orientations, access and cable allowances; no global optimum is claimed. The increased support heights, bonded anchors, enclosure heat removal and stacked-device temperatures require qualification. The Bedrock process exceptions and PSU installation conditions remain in `ORDERING_NOTES.md`.
