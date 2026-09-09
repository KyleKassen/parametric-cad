# Peplink removable carrier

The new 180 x 210 x 4 mm aluminum frame holds the Peplink above the Bedrock, leaving the Bedrock's original backpanel thermal contact intact.
Its 146 x 160 mm central window opens the region above the fins.
The carrier underside is 70 mm above the main panel, and the installed router reaches 109.3 mm.

- `params.json`, `model.py`: editable dimensions and source geometry.
- `fpd_input.json`: nine native features for the enclosing layout's FPD generator, including four WGO40 M4 female load standoffs at 6 mm height.
- `exports/Peplink_Carrier_R2_frame.step`: frame reference before native anchor machining.
- `exports/Peplink_Carrier_R2_catalog_envelopes.step`: frame plus four explicitly simplified standoff-body envelopes.
- `references/interface_verification.json`: 40 passing reference/frame/interface checks.
- `references/evaluation.json`: passing repository geometry/design evaluation.
- `references/product/carrier_R2_hero.png`: inspected exported-frame render.
- `audit_native.py`: independent check of the actual native STEP after FPD export.
- `references/native_carrier_geometry_audit.json`: 45 passing checks of the actual native export.
- `references/native_views/Peplink_Carrier_R2_native_hero.png`: inspected actual-native render with all four standoffs.

Use four Wurth 971500321 50 mm M3 male/female extensions above the main panel's 20 mm WGO30 standoffs.
Four M3x10 socket-cap screws with 7 mm OD x 0.55 mm washers retain the frame; nominal insertion into the extension is 5.45 mm.
Use a 2.5 mm hex key or long bit whose shaft envelope is at most 8 mm for the first 40 mm above the screw, keeping larger holders above the router.
Remove the router and carrier together before servicing the lower Bedrock.

The reference CAD does not constitute load, torque, vibration, thermal or supplier machining qualification.
The actual native export `Peplink_Carrier_R2_verified.stp` passed 45 geometry checks, including the window throat and bevels, support holes, anchor cavities and all four standoff positions and shoulder heights.
Native panel comparison differs by only 1.20570 mm3 from the reference, consistent with native 0.001 mm rounding.
The native STEP displays a simplified 3.7 mm internal bore for WGO40; the saved/reloaded WGO40 native hardware code specifies M4, and the visual cylinder is not a thread-size specification.
The original layouts and adapters are preserved.
