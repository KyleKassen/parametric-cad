# B210 supporting plate — F1

Open **F1.fpd** in Front Panel Designer. Created and saved with the installed Front Panel Designer 6.5.1 on 2026-09-08. The short filename keeps the full OneDrive path within this application's Windows path limit.

This plate supports the existing **D1 adapter**, which is 150 x 148 x 3.5 mm. It adopts the 180 x 200 x 6 mm supporting-panel outline from `../params.json`; enclosure attachment holes have not been specified.

| Property | Value |
| --- | --- |
| Material | Natural anodized aluminum |
| Outline | 180 x 200 mm, four R8 corners |
| Thickness | 6 mm |
| Rim edges | 0.4 mm x 45 degrees, both faces |
| Hardware | Four native FPE **WGU30 M3 load studs** |
| Projection | 12 mm, depth offset 0 |
| Side | Reverse (mounting face) |
| Stud spacing | 136.000 x 120.015 mm |

Coordinates are in mm, measured from the panel's lower-left corner in the normal front-side drawing coordinate system. Viewing the reverse face mirrors its appearance; do not mirror these entered coordinates again.

| Stud ID | Nominal X | Nominal Y | Saved X | Saved Y |
| --- | ---: | ---: | ---: | ---: |
| S1 | 22 | 39.9925 | 22 | 39.992 |
| S2 | 158 | 39.9925 | 158 | 39.992 |
| S3 | 22 | 160.0075 | 22 | 160.007 |
| S4 | 158 | 160.0075 | 158 | 160.007 |

FPD stores coordinates at 0.001 mm resolution. The saved pattern retains the exact 136.000 x 120.015 mm spacing, with its center 0.0005 mm below the nominal center. These are stud positions; no duplicate ordinary holes or separate cavities were added underneath the native stud elements.

The D1 adapter seats directly against the stud-side panel surface and is retained by its specified four M3 washers and locknuts. Its underside screw heads, the stud bases and adhesive must be flush or below the mating surface. The nominal adapter + washer + nut stack is 8.05 mm, leaving 3.95 mm of the 12 mm stud projection.

## Verification

- The saved native file was reloaded through `LoadFrontpanel` and inspected with `verify_F1.fpjs`.
- Confirmed 180 x 200 x 6 mm and exactly four WGU30 elements, each 12 mm long, on the reverse side, at the saved positions above.
- Checked the native stud properties dialog: Load stud / M3 / 12 mm / reverse side / depth offset 0.
- Checked panel properties: natural anodized aluminum, R8 corners, 0.4 mm 45-degree bevel on both rim edges.

This is a **fit prototype**, consistent with the source D1 package. Physical fit, joint capacity, and the supporting plate's attachment to the enclosure remain unverified. See `../PROTOTYPE_VALIDATION.md`. No manufacturing order was submitted.

## Editable source

`B210_support_plate_F1.fpjs` recreates the native panel using FPD's scripting API. It saves to the absolute project path written near its end, with overwrite disabled; choose a new output name before generating another revision. A copy is available under FPD's **Edit > Scripts > User scripts**. `verify_F1.fpjs` reads the saved F1 file without changing it.

Manufacturer references: [studs and standoffs](https://docs.frontpanelexpress.com/elements/studs_standoffs.html), [scripting interface](https://docs.frontpanelexpress.com/programming_interface.html). Hardware selection was also checked against the installed `Config/Bolt.d/10-Base.ini` catalog.
