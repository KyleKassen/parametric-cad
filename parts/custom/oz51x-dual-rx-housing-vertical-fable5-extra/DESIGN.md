# OZ51x Vertical Housings — Fable 5 Extra Edition

Production-refinement redesign of `oz51x-dual-rx-housing-vertical` and
`oz51x-dual-tx-housing-vertical` v1, authored by Claude (**Fable 5 extra**).
This directory hosts the redesigned family builder (`model.py`) and the RX
variant; `../oz51x-dual-tx-housing-vertical-fable5-extra/` is the TX thin
wrapper. Both consume their electrical variant's verified `params.json` via
`_extends` and add only an `industrial` section — no interface dimension was
re-derived or altered.

## What was preserved (unchanged, verified)

Bay layout and pitch, stud/boss patterns and pilot sizes, SMA holes + relief
pockets, fiber pass-slots (not mirrored), SC/APC body cutouts + M2 pilots,
DE-9 cutout + jackscrew positions, mated-connector corridors, DE-9 rear
keep-out, spool position/radius, lid lip ring + wire headroom, and the
canonical frame / `layout()` API — so the family's shared test suite and the
canonical `fit_check.py` run against these parts unchanged. Fit checks show
0.00 mm³ interference for both variants against the real vendor STEPs, the
SC adapter/connector stand-ins, and the lid.

## Major improvements

**Mounting (new capability).** v1 had no way to attach the enclosure to
anything. Two integral flanges, flush with the mount face, extend beyond the
finished top and bottom faces with four slotted holes (M4/#8 pan head; slots
run along the depth to absorb hole-position error, a 4-point pattern that
cannot rock). Triangular gusset roots blend them into the walls and print
support-free in the tray's natural print orientation (mount face down —
flanges lie flat on the bed). Envelope grows from 92.2 to 114.2 mm tall;
width and depth are unchanged.

**Edge language.** One consistent scheme instead of a sawn-off box: R2.5 on
the canonical vertical edges (the finished horizontal edges outlining the
top/bottom faces), R1.2 on the mount-side long edges, a 1.2 mm chamfer
around the service-cover perimeter (reads as a bolted end plate on an
extruded body), and matched 0.6 mm reveal chamfers on both sides of the
parting line so the seam is an intentional V-groove. The mount-side radius
is capped at 1.2 because the SC adapter flange reaches within 0.24 mm of the
floor plane on the back panel — a larger radius would undercut its seat.

**Ventilation & drainage (new).** Each bay gets a convection path sized for
the module's dissipation without opening the enclosure up: downward-facing
2 mm intake slots in the finished bottom face (nothing can fall in; they
double as drainage weeps at the lowest interior point), a low intake louver
group in the cover over the lower bay, and a high exhaust group over the
upper bay. The top face and the fiber plenum are deliberately unvented —
no upward-facing openings, no dust path to the optics.

**Connector presentation.** SC/APC adapter flanges seat in 0.8 mm recessed
rounded-corner pockets — locates the adapter and sits it nearly flush —
while keeping 2.2 mm of M2 pilot engagement. The DE-9 stays surface-mounted:
its 30.8 mm flange spans the lid parting line across the 32.7 mm finished
width, so a base-side recess cannot exist (documented, not accidental).

**DE-9 seam fix.** In v1 the top jackscrew hole cleared the parting face by
0.12 mm — a ligament no printer can produce, which would break into a random
ragged slot. The redesign cuts a deliberate capture slot from that hole to
the parting face; the cover edge closes it and captures the jackscrew
standoff. Deterministic geometry replaces an accidental break-out.

**Serviceability.** Entry chamfers on every thread-forming pilot (lid posts,
spool, module bosses) and the lid counterbores so screws start square;
lead-in chamfers on the lid's lip pads so the side-fitted cover self-aligns
when installed blind on a wall-mounted unit; chamfered stud tops so modules
seat smoothly with pigtails attached; a filleted spool top edge so fiber
coils dress in from the open side without a sharp corner; and harness
tie-down anchor posts on the plenum floor near the DE-9 (strain relief for
solder-cup wiring), placed clear of the rear keep-out and both connector
corridors.

**Identification.** Engraved 0.5 mm panel text, all oriented to read
horizontally in the finished vertical attitude: RF / TTL beside each SMA
(the two ports are otherwise identical), the RX / TX identity centered on
the front face, and a maker/version mark (`FABLE-5X V1`) on the cover.

## Verification

- `tests/test_oz51x_housings.py` — the family's shared interface suite now
  includes both new parts (envelope, per-bay handed probes, module fit
  against vendor STEPs, boss/stud presence, lid seating, wire headroom,
  corridors, keep-outs): green.
- `tests/test_oz51x_vertical_fable5.py` — new-feature probes: flange
  presence + open slots + gussets, bottom vents open with the top face
  proven solid, cover louvers open, SC recess pockets empty with solid wall
  behind them, the DE-9 capture slot open with the bottom jackscrew hole
  proven closed, anchor posts present and clear by construction, engraving
  detected on the front face, flange/envelope consistency: green.
- `fit_check.py` in both part dirs — 0.00 mm³ across all seven checks per
  variant; reference renders regenerated and visually reviewed (open/closed,
  front/top/back, plus opaque right/bottom views for the louvers, vents,
  and flanges).

## Assumptions

- Wall mounting via the flanges is the intended installation (the narrow
  vertical format implies panel/wall placement); flanges are parametric
  (`industrial.mount_flanges.enabled`) if a flush variant is needed.
- Module dissipation is low (~1–2 W per bay), so passive 2 mm louvers are
  adequate; the vent groups are parametric and can be disabled for harsher
  environments.
- Fastener assumptions unchanged from the family: thread-forming screws into
  printed pilots, no inserts. Slotted flange holes assume M4 or #8 pan
  heads.
- All family-level assumptions stand (TTL modules mechanically identical to
  RF, SC hardware datasheet-derived, DE-9 industry-standard footprint —
  verify ordered hardware before fabrication).
- Engraved text uses the OCC default Arial face; on a machine without it,
  substitute via `industrial.labels.font`.
