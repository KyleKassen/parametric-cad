# Constrained mounting-layout search

The final, clean-coordinate candidate is `placement.json`. The PNG/SVG are plotted from that same file and the PNG has been visually inspected. Coordinates use the panel lower-left origin; the front, component-facing panel surface is Z=0. Referenced device STEP models are already normalized. Apply only the listed Z rotation and translation.

| Component | X | Y | Mount-face Z | Rotation Z |
|---|---:|---:|---:|---:|
| MEAN WELL NSP1600 | 371.5 | 65.6 | 0 | 180° |
| SolidRun Bedrock | 92 | 297 | 0 | 0° |
| Ettus B210 | 254 | 318 | 0 | 180° |
| Peplink UBR Plus | 126.5 | 89 | 6 | 0° |
| OZ51x dual TX snap housing | 274 | 76 | 0 | 0° |

The method distinguishes thin adapter plates from raised electronics, so planned cable space may pass over another low plate where their height intervals do not overlap. It reserves the actual case inner bounds [-36.195,467.995] mm on both axes, rather than treating the panel edge as the enclosure wall. It uses the current B210 4 mm and Bedrock 6 mm adapter revisions. Peplink is conservatively bounded because small connector solids in the supplied vendor STEP are invalid.

The second search ran20 fixed-seed, bounded SLSQP starts. It found a best minimum clearance of3.412996 mm for this orientation/topology. The final clean coordinates retain3.375 mm minimum additional clearance to physical components, cable fields against other components, and the specified Ø30 factory-nut socket envelope. This is the best-found constrained layout; it does not prove a universal optimum over every possible orientation or a different cable strategy.

The limiting horizontal chain is independently explainable: lower-left factory socket -> router -> OZ housing -> PSU lower mounting tab -> lower-right factory socket. If the desired additional clearance is m, these bounds require router X >=123.125+m, OZ X >=router X+144+m, and PSU X >=OZ X+94.1+m. The lower-right socket further requires hypot(389.075-PSU X,5.375)>=15+m. Substitution yields an upper bound of approximately3.413 mm in this arrangement. The numeric search attains that bound before rounding.

Actual nominal margins for the selected coordinates:

- Router envelope to lower-left Ø30 factory socket:3.375 mm.
- PSU device/terminals to lower-right Ø30 factory socket:3.379 mm.
- OZ housing to lower PSU mounting tab:3.400 mm.
- Router to OZ housing:3.500 mm.
- Router upper cable reservation to Bedrock device:3.570 mm. The low Bedrock adapter can overlap this cable field in XY because the field starts at Z=10 mm and the plate ends at Z=6 mm.
- B210 and Bedrock adapters:4.000 mm.
- B210 lower RF cable reservation to router:4.570 mm.
- Both complete100 mm PSU end corridors to the inner case walls:1.795 mm. The intake corridor begins at the terminal face, not at the end of its38 mm terminal protrusions; those are not double counted.
- OZ lower fiber cable field to case wall:3.145 mm.
- Router lower cable field to case wall:3.395 mm.

`selected_clearances.hard_constraints` stores residuals AFTER subtracting each criterion (0.5 mm required wall margin,2 mm required body-to-panel edge,6 mm mounting-axis edge margin). Therefore the raw values in that list are not the actual wall gaps quoted above.

The original candidate could not retain generous Ø30 factory-nut socket clearance at the lower corners, and the B210 downward cable field clipped the router. Raising B210 and shifting the lower row solved those constraints. `initial_search_unaccepted.json` preserves that earlier unsuccessful search/rounding state for traceability; it must not be used for manufacture. The final file's clearance assertions pass after clean-coordinate selection.

Cable fields for different components are allowed to cross each other: a real harness may cross at different heights, and cable selection/routing remains part of integration. Router40 mm and OZ40/30 mm fields are design allowances, not manufacturer minima. The internal OZ cover also needs47 mm extra outward swing plus hand access. The enclosure door/document pocket is over237 mm above the new panel, so this service motion fits the depth envelope.

This is a nominal mechanical packing check. Exact enclosure and assembly B-rep verification is performed independently by the enclosure/main task using these final coordinates. Open space at the fan faces does not demonstrate sufficient heat removal from the closed steel enclosure or validate adhesive-stud loads.

Reproduce without changing the repository environment:

```powershell
uv run --no-project --link-mode copy --with scipy --with matplotlib --with numpy python Q:/parts/custom/sce20-layout/references/layout_search/optimize_layout.py
```

