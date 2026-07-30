# lib/features.py catalogue

The design language as code.
Every builder takes `style: Style = STYLE` and returns either a `cq.Workplane` or a record carrying `.solid` plus the measurements that make a refinement claim checkable.

Import what you need:

```python
from lib.features import (STYLE, Build, bolt_pattern, connector_land, face_plane,
                          fastener_holes, recessed_panel, rib_field, rounded_box)
```

## The ladders

`Style` is frozen, hashable and shared.
Copy it with `STYLE.tuned(**changes)`; never mutate it.

| Call | Returns | Verified value |
|---|---|---|
| `STYLE.plan_radius(size, other=None)` | plan-corner radius from the ladder `(3, 5, 8, 12, 16, 24)` | `plan_radius(140, 100)` -> `12.0` |
| `STYLE.edge_break(size, wall=None)` | rim chamfer from `(0.4, 0.6, 1.0, 1.5, 2.5, 4.0)`, clamped to 40% of the wall | `edge_break(140, 4)` -> `1.5` |
| `STYLE.wall(process, span)` | recommended wall over an unsupported span | `wall("machined-aluminium", 100)` -> `2.5` |
| `STYLE.wall_spec(process)` | the full `WallSpec` | processes: `machined-aluminium`, `cast-aluminium`, `sheet-metal`, `printed-fdm`, `printed-sls` |
| `STYLE.fastener(name)` | the `Fastener` record | `M4` -> clearance 4.5, cbore 8.0 x 4.4, tap drill 3.3, boss 10.0, min edge 6.5, pitch band 24-45 |
| `STYLE.pitch(name)` | mid-band fastener pitch | `pitch("M4")` -> `34.5` |
| `STYLE.edge_inset(name)` | hole-centre inset from an edge | `edge_inset("M4")` -> `9.0` |
| `STYLE.recess(wall)` | panel recess depth for that wall | proportional, then clamped |
| `STYLE.frame(size, other=None)` | proud perimeter frame width | |

Hardware table: `FASTENERS` (M3, M4, M5, M6, M8, ISO 4762 heads, coarse taps).
Seal table: `CORD_TABLE` (7 AS568-style cords -> groove width and depth, all landing at 24.5-28.4% squeeze and 78.1-80.0% fill, measured).
`EMBED = 0.2` is how far additive features sink below the face they sit on so the fuse is a real overlap.

## Primitives

```python
rounded_box(length, width, height, radius=None, *, centered=(True, True, False),
            top_break=None, bottom_break=None, plane="XY", style=STYLE) -> cq.Workplane
rounded_prism(profile, height, radius=None, *, plane="XY", style=STYLE) -> cq.Workplane
base_flange(length, width, thickness, *, radius=None, edge="chamfer"|"step",
            edge_size=None, step_height=None, fastener="M6", inset=None,
            holes="corners"|"perimeter"|"none", target_pitch=None, plane="XY") -> Plate
```

`rounded_box` bakes the plan radii into the profile and chamfers the rims while the solid is still simple - that is why it is safe as a base for anything.
`top_break` / `bottom_break` default to the style rung; pass `0.0` to suppress.
Base sits at the origin by default because enclosures stack upward from a mounting face.

## Faces and walls

```python
face_plane(solid, face=">Z") -> cq.Plane      # origin at the face bbox centre, +Z outward
wall_at(solid, plane, uv=(0.0, 0.0)) -> float | None
```

`face` accepts `">Z"` (the *extreme* face), `"+Z"` (the *widest planar face pointing that way*), a `cq.Face` or a `cq.Plane`.
Use `"+Z"` / `"-Y"` for anything that must land on the main surface.

`wall_at` shoots a real ray through the B-rep.
`None` means unmeasurable, never "thick enough".

## Sculpting a face

```python
recessed_panel(solid, face=">Z", *, size=None, frame=None, depth=None, radius=None,
               center=(0, 0), wall=None, min_wall=None) -> Pocket
lightening_pocket(solid, face=">Z", *, size, depth, radius=None, center=(0, 0),
                  wall=None, min_wall=None) -> Pocket
rib_field(pocket, pattern="chevron", *, thickness=None, height=None, pitch=None,
          count=None, draft_deg=None, relief=None, margin=0.0) -> RibField
```

`Pocket` carries `.solid`, `.void` (clips rib fields), `.plane` (on the pocket floor, +Z outward), `.wall_before`, `.wall_after`.
Rib patterns: `chevron`, `x`, `triangulated`, `parallel`, `diagonal-grid`.
`rib_field` takes a `Pocket`, not a free-form boundary - that is what buys it free clipping and guaranteed relief below the outer face.

Both pocket builders **measure** the wall and raise `WallGuardError` rather than thinning it.
Pass `wall=<mm>` only when you know the ray cannot measure it, and know that you are overriding a safety check.

**Neither pocket builder breaks its own mouth, and that is the single most valuable thing you can add.**
Measured on the worked example, breaking the cavity mouth and four panel mouths and changing nothing else moved the score 59.8 (C) to 76.7 (B): `edge_break_coverage` 25.2 to 90.1, `sharp_edge_length` 39.1 to 100.0.
The pattern, because a late chamfer on a boolean edge will not build:

```python
def break_mouth(solid, pocket: Pocket, c: float = 0.6):
    """Cut a tool that ALREADY carries the chamfer, sunk `c` below the face."""
    p = pocket.plane                       # sits on the pocket FLOOR: lift it to the face
    sunk = cq.Plane(origin=p.origin + p.zDir * (pocket.depth - c), xDir=p.xDir, normal=p.zDir)
    tool = rounded_box(pocket.length + 2*c, pocket.width + 2*c, 40.0, pocket.radius + c,
                       bottom_break=c, plane=sunk)
    return solid.cut(tool)
```

Taking the plane off the `Pocket` rather than off a face selector is what makes this version safe for an off-centre panel, and it is why nothing has to be captured before the cut.
If you do capture a face plane for something else, capture `plane = face_plane(solid, "+Z")` **before** cutting the pocket: afterwards that selector resolves to the pocket floor.

`connector_land(aperture=...)` has the mirror-image trap.
Its aperture cutter is sized to clear the WHOLE solid (`_through_depth`), so on a hollow part it punches a matching hole in the opposite wall.
Measured on the section 5 example, the 30 x 16 mm aperture on `+X` also opened a 30 x 16 mm hole through the `-X` wall and through the fin bank standing on it.
Cut an aperture that must stop at the cavity with a tool of known length instead - the `wall_window` helper in `DESIGN_LANGUAGE.md` section 5.2.

Every builder that takes a `face` defaults to `">Z"` - the *extreme* face, not the main surface.
Pass `"+Z"` / `"-Y"` explicitly on any part that carries a boss or a raised land. See `traps.md` item 2.

## Fasteners

```python
bolt_pattern(kind="perimeter"|"grid"|"line"|"circle", *, length=0, width=0, diameter=0,
             inset=None, target_pitch=None, count=None, fastener="M4", start_angle=0,
             multiple_of=4, exact_pitch=False, plane="XY", solid=None, hole=None,
             depth=None) -> BoltPattern
fastener_holes(solid, points, *, plane="XY", fastener="M4",
               kind="cbore"|"clearance"|"tap", depth=None, cbore_depth=None)
counterbore_at(solid, points, *, plane="XY", fastener="M4", cbore_depth=None)
tapped_hole_grid(solid, face=">Z", *, pitch=25.0, fastener="M6", size=None,
                 inset=None, depth=None) -> BoltPattern
tapped_boss(height, *, fastener="M4", outer=None, base_fillet=None, depth=None, plane="XY")
standoff_boss(height, *, fastener="M3", outer=None, base_fillet=None,
              counterbore=False, plane="XY")
```

`bolt_pattern` solves the count that divides the run evenly and symmetrically, and reports `.pitch`, `.pitch_v` and `.in_band` (is the achieved pitch inside that screw's structural band).
`.points` are plane-local `(u, v)` so the same pattern can be reused for the mating part.

`tapped_hole_grid` holds the pitch *exactly* and gives the leftover to the margin, because a published interface pitch is a contract.
It reports `in_band=False` for the common M6-at-25 mm breadboard grid; that is correct, interface grids run tighter than structural spacing.

Bosses use a **revolved** root fillet, never a late 3D fillet.

## Transitions, seals, weather

```python
step_shoulder(lower_dia, upper_dia, height, *, steps=2, break_size=None, plane="XY")
blend_transition(lower_dia, upper_dia, height, *, kind="fillet"|"cone"|"facet",
                 fillet=None, facets=8, plane="XY")
oring_groove(*, cord=2.62, shape="rect"|"circle", length=0, width=0, diameter=0,
             radius=None, groove_width=None, depth=None, plane="XY") -> ORingGroove
drip_edge(*, length, projection=5.0, thickness=3.0, shed_deg=8.0, kerf=1.2,
          kerf_depth=0.8, radius=None, plane="XY")
fin_bank(*, height, base="flat"|"cylinder", length=0, radius=0, count=None, span=None,
         pitch=None, thickness=None, draft_deg=None, embed=EMBED, plane="XY") -> FinBank
louver_bank(solid, face=">Z", *, width, height, center=(0, 0), count=None, pitch=None,
            gap=None, blade_angle_deg=None, wall=None, shape="blade"|"scallop",
            lip=0.0) -> LouverBank
connector_land(solid, face=">Z", *, length, width, center=(0, 0), raised=1.5,
               radius=None, aperture=None, aperture_radius=None, fastener="M3",
               screw_inset=None, screw_kind="tap", break_size=None, wall=None,
               min_wall=None) -> ConnectorLand
emblem(solid, face=">Z", *, motif="rings"|"crosshair"|"target", diameter=20.0,
       relief=None, rings=3, line_width=0.9, center=(0, 0))
text_mark(solid, face=">Z", *, text, size=8.0, relief=None, center=(0, 0),
          font=None, font_path=None, rotate_deg=0.0, strict=False)
```

These return their own proof:
`ORingGroove.squeeze_pct` / `.fill_pct`, `LouverBank.free_area_mm2` / `.throat_area_mm2`, `FinBank.added_area_mm2` (net of the root footprint), `ConnectorLand.aperture_area_mm2`.
Quote those numbers in `DESIGN.md` instead of asserting that a seal seals or a vent vents.

`louver_bank` tilts blades so the outer mouth is the low end, and cuts horizontal slots only.
`emblem` refuses relief above 1 mm.
`text_mark` degrades by design: on any failure it warns and returns the part unchanged, so a missing font cannot destroy an enclosure. Pass `strict=True` where the mark is contractual.
`blend_transition(kind="fillet")` is tangent at the upper diameter only; stack two calls for a true S-curve.

## The Build pipeline

```python
b = Build(solid, "base")
b.boolean(fn, "name")     # union / cut another solid
b.pocket(fn, "name")      # recesses and lightening pockets
b.rib(fn, "name")         # rib and fin material back in
b.hole(fn, "name")        # counterbores, taps, apertures
b.edge_break(fn, "name")  # late chamfers, only on edges no boolean created
part = b.result
b.stages()                # the build_stages() protocol, free
b.report()                # per-stage volume / faces / solids
```

Phase order is `base -> boolean -> pocket -> rib -> hole -> break` and never runs backwards; `pocket` and `rib` share a rank so faces can be decorated one after another.
A step callable takes the current `Workplane` and returns a `Workplane` or any record with `.solid`, so every builder above drops straight in.
`Build` raises `BuildOrderError` on a backwards move and warns (`RuntimeWarning`) when a step leaves more disjoint solids than it found - the cheapest detector there is for additive geometry that only touched the part instead of overlapping it.

## Errors

`FeatureError` (the message always states the numbers), `WallGuardError` (styling would take the wall below minimum), `BuildOrderError` (a step out of phase order).
All three are `ValueError` subclasses.
