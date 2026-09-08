# OZ51x Dual-RX Vertical Housing — Opus 5 production refinement

Independent redesign of `oz51x-dual-rx-housing-vertical`, authored by Claude
(**Opus 5**). The TX peer is `../oz51x-dual-tx-housing-vertical-opus-5/` and
carries its own copy of this document; the two parts are symmetric — their
`model.py` files differ by four lines of docstring and their `params.json`
files by an `_extends` target and three prose strings.

```bash
uv run python parts/custom/oz51x-dual-rx-housing-vertical-opus-5/model.py      # build + export
uv run python parts/custom/oz51x-dual-rx-housing-vertical-opus-5/fit_check.py  # 7 real-geometry checks
uv run python parts/custom/oz51x-dual-rx-housing-vertical-opus-5/make_views.py # renders
uv run pytest tests/test_oz51x_housings.py tests/test_oz51x_vertical_opus5.py
```

| File | What it is |
|---|---|
| `../oz510-dual-housing/refine_opus5.py` | The refinement layer. Calls the canonical family builder and layers on top of it. |
| `model.py` | Thin wrapper. Identical to the TX peer's apart from the docstring. |
| `params.json` | Everything variant-specific. Every derived number carries its derivation. |
| `exports/*_base_v2.step`, `*_cover_v2.step` | The two printable parts, separately. `*_v2.step` is the assembly. |

---

## Architecture: a layer, not a fork and not an edit

The two prior refinement attempts took the only two obvious routes, and each
paid for it:

- `gpt-5-6-sol` added a `refinement{}` branch **inside the shared builder**, so
  every future variant of the family now carries that attempt's code.
- `fable5-extra` **forked** a 941-line private builder into its own part dir,
  against REQUIREMENTS §9, and made RX the builder host with TX its dependant.

This attempt takes a third route. `refine_opus5.py` lives in family space
beside the canonical builder, imports it, calls its `_create_base_canonical` /
`_create_lid_canonical`, and applies the refinement as explicit boolean
operations on the result. `oz510-dual-housing/model.py` is not modified.

The payoff is not tidiness. It is that **"all interfaces preserved" becomes a
property of the construction rather than a claim in a document** — the bay
pitch, stud and boss pattern, SMA hole and relief pocket, fiber pass-slots,
SC/APC ports, mated-connector corridors, spool radius, lid lip and wire
headroom are produced by literally the same code path as v1. RX and TX are
peers, and the shared suite and the canonical `fit_check.py` run against both
unchanged.

---

## The headline change: the rear panel is re-datumed

v1 counter-rotates *both* rear connector families on the vertical variant so
their long axes stay horizontal once installed. For the SC/APC adapters that is
correct — their 22 mm flange is longer than the **horizontal** variant's back
panel is tall, which is the constraint REQUIREMENTS §4 describes. For the DE-9
it is wrong, and one line of arithmetic says so:

```
usable canonical z, floor top (3.0) to parting face (29.72)  =  26.72 mm
DE-9 needs, jackscrew span 25.0 + jackscrew hole dia 3.2     =  28.20 mm
```

**It does not fit.** Forcing it produces four coupled defects, all four of
which are present in `oz51x-dual-*-housing-vertical`, `-gpt-5-6-sol` and
`-fable5-extra` alike:

1. the upper jackscrew leaves a **0.12 mm ligament** to the parting face — no
   process makes that; MJF fuses it into a random web, FDM makes a sliver that
   snaps, a mill breaks the cutter;
2. the lower jackscrew sits **exactly on the interior floor plane**, so 42.75
   mm³ of its nut envelope is solid floor and it cannot be nutted from inside;
3. the 24 mm rear keep-out spans **neither** jackscrew (it covers canonical z
   3.5 … 27.5; the jackscrews are at 3.0 and 28.0), so the test proving the
   keep-out empty proved nothing about the hardware that lives there;
4. the connector flange lands **0.10 mm** from the wall-mount plane and crosses
   the parting face by 1.18 mm.

`fable5-extra` found defect 1 and fixed it with a capture slot — a good fix for
one symptom. Defects 2, 3 and 4 are still open everywhere, and all four share
one cause: a 25 mm jackscrew span forced across the enclosure's *narrow* axis.

On a vertical housing the back panel is **92.2 mm tall and 32.7 mm wide**. The
roomy axis is the height. Leaving the DE-9 footprint **un**-rotated puts its
long axis along that axis and resolves all four at once:

| | v1 / gpt-5-6-sol / fable5-extra | this variant |
|---|---|---|
| wall above the upper jackscrew | 0.12 mm ligament | **11.70 mm³ of solid wall** |
| wall below the lower jackscrew | — (it is in the floor) | **11.70 mm³ of solid wall** |
| nut envelope, lower jackscrew | 42.75 mm³ of solid floor | **0.00 mm³ — clear** |
| keep-out spans the jackscrews | neither | **both** (widened 24 → 32 mm) |
| flange to the mount plane | 0.10 mm | **10.08 mm** |
| flange vs the parting face | crosses by 1.18 mm | **7.09 mm clear** |
| gap to the SC adapter flanges | — | **6.70 mm** |

All measured on the built solid, not derived. The choice is parametric —
`panel_connector.footprint_axis: "width"` restores the v1 arrangement.

**The SC/APC adapters are deliberately left alone.** They have no defect: the
22 mm flange fits the 32.7 mm face, the M2 pilots are blind and self-tapping so
no interior access is needed, and the mated corridors verify clear. Rotating
them would buy only a larger mount-face edge radius, and would change the
canonical fit check's hard-coded adapter placement. Not a trade worth making.
The cost of leaving them is real and stated: their flange reaches canonical
z = 0.64, which caps any mount-face edge break at ~0.5 mm.

### One shared-file change, and why it is a generalisation

`tests/test_oz51x_housings.py::test_panel_connector_cutout_and_keepout`
hard-coded `if vertical: swap the footprint`. It now reads
`panel_connector.footprint_axis`, defaulting to `"width"` — the legacy
behaviour — so all nine pre-existing parts are untouched. Verified: that test
returns 8 passed / 1 skipped before and after, identically.

---

## What else changed, against the brief

**Structural integrity.** The two plenum corner posts were Ø6 × 29.72 mm
free-standing tubes with a 1.75 mm annular wall, clearing both walls by exactly
1.0 mm and braced by nothing, loaded in bending by the cover screws. That gap
is now webbed into the corner. Mount-flange gussets carry the wall load into
the flange. Two added cover posts halve the unsupported cover span over the
plenum.

**Material efficiency.** Measured, base + cover:

| variant | total mm³ | vs v1 | envelope H |
|---|---|---|---|
| v1 | 141 200 | — | 92.2 |
| `-gpt-5-6-sol` | 134 305 | −4.9 % | 92.2 |
| `-fable5-extra` | 147 889 | +4.7 % | 114.2 |
| **this variant** | **142 128** | **+0.7 %** | 116.2 |
| this variant, mount interface disabled | 133 110 | **−5.7 %** | 92.2 |

The body is 5.7 % lighter than v1 — slightly better than the best prior result,
and spread across the spool, the cover recess and the filled pilot bores rather
than concentrated in one feature. The wall-mount interface then costs 9 018 mm³,
which is what a capability v1 did not have is worth. The **cover is the
lightest of all four** at 32 365 mm³, 15 % under v1.

**Process — v2 respec.** v1 was drawn for **MJF PA12**. This is drawn for a
**standard desktop FDM printer: ASA, 0.4 mm nozzle, 0.20 mm layer, enclosed
chamber**, with ABS as the fallback and **PETG explicitly ruled out** — its HDT
is ~70 °C against a cabinet the repo's own note says settles at ambient + 15 °C.
MJF is still reachable: set `production.cover_fastening.mode` to `thread_form`
and `production.cover.field_style` to `recess`.

Everything below moved because the process moved:

| | v1 (MJF) | v2 (FDM) | why |
|---|---|---|---|
| cover fastening | thread-formed Ø2.5 pilots | **M3 heat-set inserts** | see below |
| `registration_clearance` | 0.40 | **0.50** /side | FDM general tol is ±0.67 mm at 133.5 mm, 1.7× MJF's; and below the screws' own float the lip fights them |
| `cover.lip_lead_in` | 0.8 | **1.2** | more misalignment to swallow, and it is on the last-printed face |
| `screw_boss_pilot_dia` | 2.50 | **2.70** | ASA splits rather than flows; thread-form wants 0.85–0.88 d as-printed |
| `sc_adapter.screw_pilot_dia` | 1.60 | **1.75** | the MJF change is *reversed* — 1.60 modelled lands ~1.40 in FDM, a splitting pilot |
| `sc_adapter.cutout_clearance` | 0.3 | **0.5** | the 9.9 mm aperture roof is a bridge; droop exceeded the clearance |
| `panel_connector.cutout_h` | 11.0 | **11.6** | 19.8 mm bridge, droops 0.3–0.6 mm |
| `panel_connector.screw_hole_dia` | 3.2 | **3.6** | horizontal hole, droops to ~2.9 and binds the jackscrew |
| `lid_screw_clear_dia` | 3.4 | **3.7** | prints ~3.2; 0.1 mm/side across eight screws on 133 mm in two separately-printed parts will not line up |
| drain weeps | round Ø3.0 | **hex, 3.0 across flats, vertex up** | a round crown is an unsupported arch that droops and hangs strands — in the one hole whose whole job is not retaining water |
| cover field | 0.8 mm recessed fields + lands | **1.5 mm reveal groove** | see below |
| RF / TTL labels | engraved 3.6 mm | **embossed 6.5 mm** | 3.6 mm Arial gives a 0.48 mm stroke; engraved FDM needs ~1.0 mm |
| RX / TX identity | engraved 6.0 mm | engraved **8.0 mm** | stays engraved — the cover's outer face is the bed face, so a raised glyph would hit the bed |

Two of those deserve their own paragraph.

**The cover field.** The cover prints outer-face-down — the only orientation
that does not put a 92 × 133 mm plate on supports. That makes a recessed field
a pocket opening *onto the bed*: 5 958 mm² of unsupported 0.8 mm bridging with
spans to 28 mm, on the face people look at, and bed contact on the part most
likely to curl drops to 47 %. A **1.5 mm reveal groove** on the same
rounded-rectangle path gives the same framed read, bridges 1.5 mm, and costs
5 % of the bed contact. The full-thickness lands existed only to give the
counterbores a seat; with no recess every screw is on full thickness by
construction.

**The drain outlet chamfer was modelled backwards** — and this was a defect in
v1 too, not just an FDM issue. The cone was built Ø4.0 *inside* and Ø3.0 at the
exit face, which is a re-entrant lip: water has to climb a 0.5 mm ledge to
leave, precisely the bead the feature exists to prevent. Probed at y = 22.0 it
read open to r = 1.45, then 1.95, then 1.45 again at the face. Now it opens
outward.

**Assembly and serviceability.** Base and cover export as **separate STEPs** as
well as the assembly — a fused compound is not something a shop can quote or a
slicer can lay out. Lead-in chamfers on the lip. Cable tie-down anchors on the
plenum floor, verified clear of both connector corridors and the DE-9 keep-out.

**Mounting — a capability v1 did not have at all.** Two flanges coplanar with
the canonical floor plane, which is both the wall-mount face and the natural
print-bed face, so they lie flat on the bed and reduce warp on a 133 mm part.
Slots run along the depth so hole-position error is absorbed by sliding rather
than reaming; four points cannot rock. Gussets are self-supporting in the print
orientation because every layer is smaller than the one below it. The flanges
never protrude past the mount face — asserted, because `envelope_width` must
stay exactly `interior_top_z + lid_thickness` or the canonical fit check places
the SC adapters off-face. All growth goes onto the height axis: 92.2 → 116.2.

**Drainage.** Canonical +X is down once installed. The three interior volumes
are connected bay ↔ plenum ↔ bay through the partition pass-slots, but:

- the **upper bay's low point is the top of the central rib**, 45.1 mm above
  the finished bottom face — a slot in the bottom face cannot reach it, which
  is how `fable5-extra` came to have an undrained upper bay;
- the **pass-slot sills sit 5.18 mm above both bay floors**, so water can never
  route bay → plenum either.

The only way out of the upper bay is *through* the rib. Cross-drains at
y = ±22.0 carry it into the lower bay; wall outlets at y = −22.0, +22.0 and
+44.25 take the lower bay and the plenum outside. All Ø3.0 at canonical
z = 4.45 — which undercuts the interior floor face by 0.05 mm so the
floor-to-wall corner drains with no retained film, and keeps the crown 0.05 mm
below the module plate. Outlets are chamfered so water sheds off an edge.

The third outlet at y = −22.0 exists because a test caught its absence: Y is
horizontal once installed, so water crossing the rib at y = −22 could not
travel along Y to reach the y = +22 outlet. Every cross-drain now has an outlet
directly beneath it, and `test_upper_bay_drains_all_the_way_out` asserts that
pairing rather than assuming it.

**A drainage defect found here and not previously reported:** the cover's
registration lip hangs **0.30 mm above each bay floor along its whole 66 mm
length**, at the lowest point of the bay in the finished attitude. That is a
capillary slot no drain placement can empty, because it *is* the low point.
`cover.lip_drain_relief` removes that segment.

Finally, V-section grooves in the mount face give water between the enclosure
and the wall somewhere to go. They run along **canonical X** — the vertical
direction once installed — and continue out across the flanges so they
actually daylight. A groove along Y would have been a horizontal trap.

**Environmental protection — by declaring what this is not.** IP20 / IP2X
sub-enclosure. The cover seats on a lip with no gasket or compression stop, the
SMA passes a 0.8 mm open annulus, the SC/APC adapters are retained by screws
through a clearance cutout with no O-ring, and the DE-9 is a bare panel cutout.
The environmental boundary is the host cabinet — `adrs-maritime-layout` places
this housing on the subpanel of a Saginaw SCE-20H2010LP. Compare the house
standard for a real boundary (`am59_sealed_tec_enclosure` carries a 5.33 mm
seal section, a 4.5 mm gland and an Ra 0.8 seal land): this part has none of
it, and pretending otherwise would be the actual failure.

**Edge treatment, proportion, symmetry.** One coherent scheme, applied by
intersecting the body with a simple trimmed prism rather than by a late fillet
on the finished tray — the kernel-failure mode `DESIGN_LANGUAGE.md` warns
about, and the reason a late `.edges().fillet()` here would also catch every
interior vertical edge. R2.5 on the four corners of the finished front
silhouette; matched 0.6 mm reveal chamfers either side of the parting line, so
the seam is a deliberate V-groove; 1.2 mm on the cover perimeter; 0.4 mm break
on the mount face, capped by the SC flange at z = 0.64.

**Fastener rhythm.** `DESIGN_LANGUAGE.md` rule 3 says visible fasteners are
part of the composition, never scattered — and the inherited six-screw pattern
is four on the centreline plus a lone pair at the far end, which is a scatter.
A solver over the real forbidden volumes (both vendor STEPs grown 1 mm, both SC
corridors, the widened DE-9 keep-out, spool and wrap annulus, pass-slots,
existing posts) found that **the structure admits exactly three fastener
columns** — finished z = 7.0, 46.1, 85.2 — because the bays are full to the
interior wall and the front two-thirds of the cover can only ever carry the
centreline. Two posts at canonical (±39.10, +53.25) are the only legal
addition, with **+3.696 mm** to the SC corridors, and they complete a symmetric
three-column grid.

**Cover surface.** One recessed panel with a proud perimeter frame, and the
lands unioned back inside it — so every land exists because a fastener needs a
full-thickness seat, and every fastener sits on a land. Depth is capped at
**0.8 mm** against the design language's 1.5–2 mm: that rule is calibrated to
enclosure-scale parts with 4.5 mm walls (`am59_cold_wall_enclosure` keeps 3.0
mm under a 1.5 mm recess). This cover is 3.0 mm total — a 1.5 mm recess would
leave 1.0–1.5 mm and the Ø6 × 1.6 counterbores would break through.

**Identification.** `RX`/`TX` on the cover spine, centred on the enclosure's
long axis, engraved into a full-thickness land. `RF`/`TTL` engraved beside each
SMA on the front face, at the port's own height — the two ports are otherwise
identical. The offset runs along canonical Z, which is handedness-independent,
so RX and TX mark up identically instead of the label flipping to the other
side of the port with the module. Provenance
(`OPUS-5 V1`) goes on the finished bottom face, present but off every face
anyone looks at, keeping to one emblem per visible face.

---

## How the cover is held on

This is the question v2 exists to answer, so here is the whole reasoning.

**What the holes were.** Ø2.5 thread-forming pilots in Ø6 posts — a screw cuts
its own thread in the plastic. Not insert bosses. v1 considered heat-set
inserts and rejected them, on the grounds that an M3 insert is Ø4.0–4.6 and the
"boss OD ≥ 2× insert OD" rule wants 8.0–9.2 mm against the family's Ø6.0 posts.

**That rejection was wrong, twice over.**

First, the Ø6.0 limit is not a limit. It is set by the module plates, whose
inner edges sit at |x| = 3.50 — and a plate is 1.575 mm thick with a can only
9.1 mm above it. Measured:

```
z band                          max boss dia on the rib centreline
 3.00 ..  6.00  below the plate            Ø15.4
 6.00 .. 16.72  plate + can band           Ø7.0     <- the only tight band
16.72 .. 29.72  above the can              Ø25.8
```

An insert lives in the **top ~6 mm** of the post. A Ø8.5 boss flared above the
can is clear at all eight posts, against both vendor STEPs, both SC corridors
and the DE-9 keep-out. So the constraint was applied to a band the insert never
occupies.

Second, **"boss OD ≥ 2× insert OD" is not a rule anyone publishes.** No insert
manufacturer states it; it traces to injection-moulding boss guidance. The
figures that do exist are *wall* minima: ruthex **W min 1.6 mm**, Tappex
**1.70 mm** with a stated **D1 min of 7.4 mm** for M3. Ø8.5 around a Ø4.2 hole
gives **2.15 mm** and clears all three.

**Why not the alternatives.**

*Snap-fit* — the honest case for it is strong: this joint carries no service
load (no gasket, no pressure), the cover hangs vertically so its 39 g is in
shear on the lip, and tool-free release means no dropped screws inside a box
containing bare fiber. It fails on print orientation. The base prints
canonical-floor-down, which makes the build axis the same axis any parting-plane
cantilever must run along, so a snap arm is loaded in pure interlayer tension at
its root — the one case every snap-fit guide names. Sized in the only space
available (the 1.5 mm gap between the module plate edge and the bay wall, above
the can): at a repeatable 0.8 % strain the arm deflects **0.72 mm**, and after
subtracting the 0.5 mm/side registration clearance the cover already needs,
**~0.3 mm of net undercut remains — smaller than the part's own ±0.2–0.3 mm
tolerance band.** Half the units would jam and half would rattle. Retention was
never the problem. Release is a second problem: you would pry at the parting
line, which is a deliberate 0.6 mm V-reveal, four of the eight sites are in the
plenum where a 900 µm pigtail is coiled at 15 mm bend radius against two mated
SC/APC connectors, and a scored APC endface is permanent and invisible until
you test it.

*Printed threads* — right to doubt. M3×0.5 is finer than a 0.4 mm nozzle
resolves. A coarse form (M6+, or a bayonet) would print, and there is room for
one, but it needs a mating thread on the cover at each of eight positions on a
133 mm part with ±0.67 mm general tolerance, and it gives up the flat-seat
clamping the design uses.

*Thread-forming, as v1 had it* — this survives longer than expected and the
reason I originally gave for dropping it **was wrong**. v1's DESIGN.md said a
formed thread "survives roughly 5–10 cycles". **There is no published cycle test
of thread-forming screws in FDM bosses.** That figure is folklore paraphrased
from injection-moulding guidance and it should not have been cited as data.
What is measured cuts the other way: CNC Kitchen, PETG, M3 — direct screw
**118 kg** pull-out vs heat-set insert **119 kg**. Pull-out is a wash.

The argument that survives is **torque**, and it is decisive: the same test
gives direct-screw torque-out at **1 Nm** against the insert's **3 Nm**, and
1 Nm on an M3 is about the *minimum sensible assembly torque*. A thread-formed
FDM boss therefore has essentially **no torque margin on first assembly**,
before service life is discussed at all. Add cross-threading: the cover is
fitted blind and sideways, a formed thread must be restarted in its own helix,
and a missed start cuts a second helix that consumes the material the first one
needed. Eight blind sideways starts per service.

**So: M3 heat-set inserts.** Specified, not hand-waved:

| | |
|---|---|
| insert | **ruthex RX-M3x5.7** (CNC Kitchen M3×5.7 is dimensionally interchangeable) — OD 4.6, length 5.7 |
| modelled hole | **Ø4.2** — ruthex's own figure is 4.0, but that is for a *drilled* hole; CNC Kitchen measured as-printed FDM holes ~0.25 mm undersize and recommend modelling 4.2, which pre-seats the insert and avoids the burr that forms under it at 4.0, at ~90 % of peak pull-out |
| hole depth | **6.7** = insert + 1.0 mm relief well, so displaced melt has somewhere to go instead of clogging the thread or holding the insert proud |
| hole form | **straight, no mouth chamfer** — Tappex specify a chamfer only from M4 up |
| boss | **Ø8.5**, flared from the post by a **45° cone above the can top**, so nothing prints in mid-air |
| seating | **flush to −0.1 mm.** The parting face is a registration face; a proud insert holds the cover off across 133 mm |
| screw | **ISO 7380-1 M3×8 button head, A2** — 5.0 mm engagement, 0.7 mm short of bottoming |

**Do not source a tapered-vane insert** (McMaster 94180A331 / E-Z LOK) — it
needs a 5.23/5.05 mm *tapered* hole and a Ø11.1 mm boss, 2.6 mm more than the
modules allow. And if M3 ever will not fit, **the step down is M2, not M2.5**:
ruthex and Tappex M2.5 use the same body and the same 4.0 mm hole as M3.

**The head counterbore is deleted.** A Ø6.0 × 1.6 bore fits no M3 head that
exists — an ISO 4762 cap head is Ø5.5 × 3.0 and would stand 1.4 mm proud, and
its standard counterbore is Ø6.5 × 3.0, which is the entire cover. The button
head bears on the outer face instead, which is the bed face and therefore the
flattest, squarest seat on the part.

**Two knock-ons that the geometry forced:**

- A Ø8.5 boss at the three rib posts fouls the cover's registration lip pad —
  the pad's rib-side run starts at |x| = 2.40, and a round scallop big enough
  to clear the boss leaves a **0.75 mm sliver** of pad standing in the build
  direction, three times per bay. Those snap off in the box. The pad's rib-side
  run is now cut away locally instead; the outboard run and the two ends still
  locate the cover in both axes.
- The two added posts at (±39.10, +53.25) were free-standing towers. Pressing
  an insert momentarily softens the boss, and a free-standing tower bulges,
  tilts or shears at the root. **All four plenum posts are now webbed into
  their wall**, not just the two rear corners.

**Envelope.** 32.72 (W) × **134.10** (D) × 116.20 (H) mm. The body is 133.50
deep; the embossed RF/TTL labels stand 0.60 mm proud of the front wall, and
`layout()` folds that into `envelope_depth` — the shared suite asserts the
built bounding box against these numbers, so every protrusion has to be
declared. `envelope_width` stays untouched by anything: the canonical fit check
places the SC adapters using `fiber_z − envelope_width/2`, so growth on that
axis would land them off-face and report phantom interference. All refinement
growth goes onto depth (labels) or height (mount flanges).

**Assembly note.** Temperature-controlled soldering iron with an insert tip —
not a heat gun. Print temperature + 10–20 °C. Press square, melt ~90 %, then
press the last of it flush against a flat plate and hold 6–10 s. Do the two
plenum posts first, while the rest of the part is cold.

---

## Thermal: closed, not vented — and the wattage is unknown

**There is no Zonu datasheet anywhere in this repository.** Not a failed
search: `git log --all --name-only` lists 20 Zonu paths, all STEP/analysis/PNG,
and no Zonu PDF was ever committed. REQUIREMENTS §5 cites datasheets that
whoever wrote it had outside the repo. So no module dissipation figure in this
codebase is sourced, and **the two that exist disagree by 2.5×**:

- 5 W/module — `adrs-maritime-layout/DESIGN_NOTES.md` thermal budget, uncited;
- 1–2 W/bay — `oz51x-dual-rx-housing-vertical-fable5-extra/DESIGN.md`, uncited,
  and used there to justify the louvers it was invented alongside.

Rather than size louvers against an invented number:

- buoyancy over the connected interior is **0.076 Pa** (~0.18 m/s). Carrying a
  useful 1.4 W would need ~440 mm² of free area per path, inlet and outlet —
  ~16 % open on a bay face. That is a grille, not a louver.
- the cover's registration gap is **already ~150 mm²** of uncontrolled open
  area with no measurable thermal benefit. If 150 mm² of existing gap does
  nothing, another 150 mm² of louvers will not either. That is the empirical
  refutation of both prior attempts, from geometry already in the model.
- **~70 % of the thermal resistance is getting heat off the can inside the
  box**, which venting cannot touch. Modelled: ~13 K/W module-case to ambient,
  ~3.7 K/W shell to ambient, sealed and wall-mounted, with 31 % of the external
  area blocked by the wall. Venting generously buys ~20 %; bonding both
  baseplates to an aluminium spreader buys ~57 %.
- these are SC/APC ferrules. A louver aimed at a bay is a dust path to an
  angled endface, and that damage is permanent.

So: **closed, conduction-cooled, drained.** The printed Ø6 × 3 mm studs are
66 K/W and are a mechanical path, not a thermal one — if the wattage turns out
to be high, the lever is a metal spreader to the mount face (a steel subpanel
is a good sink; drywall is not), not louvers.

**Measure the supply current before relying on any of this.** At ~2 W total the
sealed design is comfortable; at 10 W no polymer housing works and the
architecture is wrong. Every other thermal decision is downstream of one number
that a bench meter closes in ten minutes.

---

## Verification

- `tests/test_oz51x_housings.py` — the family's shared suite, both new parts
  registered: **32 passed, 8 skipped** (the skips are the four
  `refinement.enabled`-gated tests that reproduce `gpt-5-6-sol`'s specific
  geometry; `refinement.enabled` is deliberately absent here).
- `tests/test_oz51x_vertical_opus5.py` — 24 new-feature probes × 2 parts,
  **48 passed**. Every probe uses `lib.housing.interference`, which raises on a
  failed boolean; a local `try/except` returning 0.0 would read a kernel error
  as perfect clearance, which is the failure mode the probes exist to catch.
- `fit_check.py` — **0.00 mm³ on all seven checks**, both variants, against the
  real vendor STEPs, the SC adapter and connector stand-ins, and the cover.
- Whole repo: **390 passed, 41 skipped, 0 failed.**
- Renders regenerated and reviewed, product shots with `axes=False` per
  `DESIGN_LANGUAGE.md` — a rule every existing render in this family breaks.

Three probes are worth calling out because they encode the arguments rather
than the geometry:

- `test_legacy_de9_arrangement_genuinely_does_not_fit` asserts the *premise*
  (28.20 > 26.72). If a future param change ever makes the legacy arrangement
  fit, the re-datum stops being justified and this test says so.
- `test_finished_top_face_is_never_breached` is the mirrored control: the same
  probe that must be open on the bottom face must hit a full plug on the top.
  A mirrored-feature bug cannot pass it.
- `test_upper_bay_drains_all_the_way_out` runs one continuous probe from the
  upper bay floor, through the rib, across the lower bay and out.

---

## Open items and honest gaps

1. **Measure the module supply current.** See above. This is the one open
   number that could invalidate the thermal position.
2. **The DE-9 footprint has no datasheet in this repo.** Cutout, flange and
   jackscrew spacing are a self-declared "industry-standard footprint". The
   re-datum makes the design far less sensitive to it than v1 was — v1's legal
   window for `panel_connector.z` was about ±0.3 mm — but verify the ordered
   connector.
3. **`sc_adapter.flange_wide` (11.8) is not dimensioned on the FS drawing.**
   Every other SC adapter number checks out against it; this one is scaled or
   from a vendor table. The DE-9-to-SC flange gap of 6.70 mm depends on it.
4. **Neither ASA nor MJF PA12 is UL94 V-0 as standard**, and the ADRS cabinet
   contains a mains PSU. If V-0 is required inside that enclosure, an FR grade
   is needed and both the pilot sizes and the price change.
5. **No pull-out or torque data exists for heat-set inserts in ASA or ABS.**
   Every published test I could find is PLA or PETG, and every specimen was a
   thick block rather than a Ø8.5 slender boss printed upright. The insert
   choice rests on PETG numbers and on geometry; treat the ASA figures as
   untested rather than interpolated, and pull-test one boss before committing
   a batch.
6. **M3 module-screw engagement is 4.4 mm = 1.47 d**, below the 2 d rule of
   thumb — roughly 500–600 N of pull-out in PA12 against a ~30 g module, which
   is acceptable, but it cannot be improved with a longer screw. Raising
   `housing.floor` to 4.0 or `standoff_height` to 4.5 is the lever if 2 d is
   ever required.
7. **TTL modules still have no STEP** and are assumed mechanically identical to
   the RF modules. Unchanged family-level assumption.
8. **`params.json` inheritance is copy-paste above the vertical level.**
   `oz510-dual-housing/params.json` is not an `_extends` ancestor of anything in
   the OZ51x family — the `module` and `sc_adapter` blocks are duplicated into
   `oz51x-dual-{rx,tx}-housing/params.json` with no test asserting they stay in
   sync. Out of scope here, worth fixing.
