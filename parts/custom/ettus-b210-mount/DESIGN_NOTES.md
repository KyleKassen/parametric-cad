# Ettus USRP B210 — mount family

Three mounts for one radio. All three are built from one parametric model in one
shared frame, and all three are gated by the same geometric checks against the
vendor solid.

| Variant | Attitude | Uses the four M3 bores | Material | Process | Mass | Panel | Depth |
|---|---|---|---|---|---|---|---|
| `flat_plate` | lying flat | yes | 6061-T6, 3 mm | laser blank + drill | 214 g | 158 × 169 mm | 36.7 mm |
| `edge_bracket` | on edge | yes | 5052-H32, 4 mm | laser blank + drill + **1 bend** | 361 g | 37.7 × 206 mm | 139 mm |
| `clamp_cradle` | lying flat | **no** | 5052-H32, 4 mm tray + 3 mm bridges | laser + tap + **4 bends ×2** | 431 g | 188 × 169 mm | 43.7 mm |

## Running it

> **Environment.** The in-tree `.venv` cannot import OCP from this checkout —
> the path to `OCP.cp311-win_amd64.pyd` overruns `MAX_PATH` inside the DLL
> loader. Use a venv at a short path, and write exports somewhere short or
> SolidWorks will refuse to open them (this repo sits 173 characters deep).
>
> ```bash
> UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv sync --all-extras
> ```
>
> `make eval` / `make export-all` go through `uv run python`, so they pick the
> in-tree venv and will not work from here. Call the interpreter directly.

```bash
# all three variants: STEP + 1:1 DXF flat patterns + the bend/fastener pack
C:/venvs/cadquery/Scripts/python.exe parts/custom/ettus-b210-mount/model.py \
    --dxf --shop-pack --out C:/ADRS-CAD/b210-mount

# one variant only
C:/venvs/cadquery/Scripts/python.exe parts/custom/ettus-b210-mount/model.py edge_bracket

# the gate: build -> export -> re-import -> validate -> fit-check -> render -> promote
C:/venvs/cadquery/Scripts/python.exe -m lib.evaluate parts/custom/ettus-b210-mount

# just the 19 geometric assertions against the vendor solid (faster to iterate on)
C:/venvs/cadquery/Scripts/python.exe parts/custom/ettus-b210-mount/fit_check.py

# product views: each variant with the radio sitting in it
C:/venvs/cadquery/Scripts/python.exe parts/custom/ettus-b210-mount/render_variants.py

# parametric invariants
C:/venvs/cadquery/Scripts/python.exe -m pytest tests/test_ettus_b210_mount.py
```

### What lands where

All three variants are exported every run, and the default is written **twice** —
once under its own name and once under the bare part name:

```
ettus-b210-mount_v1.step                 <- THE ONE TO BUILD (= flat_plate)
ettus-b210-mount-flat-plate_v1.step         identical geometry, named variant
ettus-b210-mount-edge-bracket_v1.step       the alternative
ettus-b210-mount-clamp-cradle_v1.step       the alternative
plates/*.dxf                                one 1:1 blank per fabricated piece
shop_pack_v1.json                           blanks, bends, fasteners, finish
```

`<part>_<version>.step` is the name `lib.export` and `lib.evaluate` already use
for a part's accepted artifact, and `PART_NAME` is taken from the directory name
so the two cannot drift apart. So "the main STEP" always means the variant this
family went with, and the three suffixed files sit beside it as the
alternatives. `lib.diff_step` confirms the canonical file and
`…-flat-plate_v1.step` are identical to 0.00 mm³.

**To make a different variant the main one**, change `default_variant` in
`params.json` — the canonical export, `create_part()`, and therefore what
`lib.evaluate` gates and `make export-all` writes all follow it. Note that
`spec.json`'s bbox and hole checks are written against the flat plate, so they
need updating in the same commit.

What a shop gets, per variant: the formed **STEP**, a 1:1 **DXF** flat pattern
with every hole and slot in it, and `shop_pack_v1.json` — blank sizes,
quantities, bend table (angle, inside radius, K-factor, bend allowance, bend
deduction, bend-line position), material, finish, the full fastener schedule,
and a `files` manifest naming which STEP is which.

---

## 1. The situation each variant exists for

Only three situations are actually distinct, and each variant owns one:

* **`flat_plate` — you have panel area and you want the best thermal and service
  case.** The radio lies on a plate that is also its heat spreader, bolted flat
  with no cantilever anywhere. The cheapest part in the family and the only one
  with no bends at all.
* **`edge_bracket` — you have depth and you do not have width.** This is the
  compact maritime layout's situation exactly: the enclosure had 240 mm of depth
  and was using 193, while panel width was the scarce resource. Standing the
  radio up costs 139 mm of depth and returns roughly 190 cm² of panel.
* **`clamp_cradle` — you cannot, or will not, put a screw in the radio.** It
  touches none of the four bores, is fully reversible, and is the only mount
  that still works if the standoff risk in §9 turns out to be real.

Everything else in the option space collapsed into one of those three, or into
§8. A fourth variant would have been a fourth spelling of one of these.

---

## 2. The frame, and the one trap

Origin at the centre of the four-hole pattern, on the plane the bottom pan seats
against. **+Y** at the RF front panel, **+Z** up out of the pan, **+X** completing
a right-handed set.

That choice does one useful thing: it makes the hole pattern symmetric about both
axes — the four bores land at (±46.7995, ±60.0075) — and it isolates the whole
problem into a single asymmetry, **where the body sits relative to those holes**:

```
front (RF) overhang   82.3115 mm
rear  (I/O) overhang  76.2055 mm
                      -------
difference             6.106 mm
```

The pattern centre is 3.05 mm off the enclosure centre. A bracket drawn symmetric
about the *body* misses all four holes by 2.86 mm — inside the eye's tolerance and
well outside a Ø3.4 clearance hole. It will not go on, and it will not be obvious
why.

**Every part in this family is symmetric in Y — the axis the asymmetry lives on —
and carries the holes at their true positions.** That is not decoration: it means the radio can be fitted
either way round on any of them and all four bores still line up, so the failure
mode above cannot happen and no witness mark or orientation arrow is needed. It
costs 6.1 mm of length on the flat plate. That is the whole price.

(The flat plate and the cradle tray are symmetric in X as well. The edge bracket
deliberately is not: its flange side needs 10.8 mm of standoff to clear a vent
slot and its free side needs 1.8 mm, so squaring it up would cost 9 mm of
enclosure depth for nothing. The radio's own footprint is symmetric in X either
way, so reversibility is unaffected.)

### The transform is a rotation, not a reflection

Getting from the vendor STEP's frame to this one is `rotate +90° about X`, then
`180° about Z`, then translate by `(58.5005, 80.6355, 1.210)`.

The obvious-looking map — send the pan normal to +Z and keep +X — is
`(x, y, z) → (x, z, y)`, which has determinant −1. It is a **mirror**. Using it
would have silently handed the vendor solid in every fit check, and because the
hole pattern is symmetric in X, nothing would have complained. The X axis is
flipped instead, which costs nothing except that it swaps which side wall carries
which vent slot — so the slot keep-outs are written in mount coordinates and
`fit_check.py` probes the placed solid to prove the handedness rather than
assuming it.

---

## 3. What was re-verified, and what it changed

`interfaces.json` was not trusted. Everything below was re-measured from
`Ettus_USRP_B210_Full_Unit.step` with the OpenCASCADE kernel; the scripts and
their JSON output live in
[`parts/vendor/ettus-usrp-b210/references/`](../../vendor/ettus-usrp-b210/references).

| Claim | Measured | Verdict |
|---|---|---|
| Overall bbox 122.348 × 37.256 × 177.648 | identical | confirmed |
| Four Ø3.000 bores at (11.701/105.300, −20.628/−140.643) | identical, Y −1.210 → +4.790 | confirmed |
| Bore opens to Ø3.200 from Y +4.790 to +8.790 | identical | confirmed |
| Pan flat face at Y −1.210, X[0,117] Z[−153.126,−2.420] | identical, 17 628 mm² of −Y-facing plane | confirmed |
| **Max screw penetration 3.574 mm** | **3.575 mm** — first material on each bore axis at Y +2.365 | **independently confirmed** |
| Feet Ø12.700, 3.556 proud, concentric with the bores | identical | confirmed |
| Feet contact face | **Ø8.37 flat, 55.0 mm² each** — the feet taper, they are not cylinders | new |
| Side slots 3.000 × 7.000, diagonally opposite | identical, found as the inner wire of each wall face | confirmed |
| Side wall stepped 0.254 mm | identical: lower band 121.840 wide vs 122.348 | confirmed |
| Top cover: zero holes, four 1.000 mm dimples | identical | confirmed |
| USB shell protrudes to Z −158.308 | **−158.008** | 0.3 mm disagreement, immaterial inside a 55 mm keep-out |
| — | **Ø9.24 SMA nuts reach Z −159.038**, deeper than the USB | new, inside the SMA keep-out |

Two things changed the design:

* **3.575 mm is real and it was measured on the bore axis**, not read off a note.
  It is the hardest constraint on the whole part and it drives §4.
* **The feet taper to a Ø8.37 flat.** That is what made the cradle's foot-pocket
  scheme worth checking: the pocket has to swallow the Ø12.7 base, not the
  contact face.

---

## 4. The screw-length rule, and why plate thickness is free

The radio allows a screw to travel **3.5 mm** past its pan before the tip meets
the internal M3×8 PCB screw and starts jacking the board off its standoffs. That
is a silent failure: it torques up normally and lifts the PCB.

So the four M3 holes are **relieved from the underside**, and the relief is what
absorbs plate thickness. Engagement stays pinned at 3.0 mm and the screw stays an
**M3×6** on both bolted variants, whatever the plate is:

| | `flat_plate` | `edge_bracket` |
|---|---|---|
| Plate | 3 mm | 4 mm |
| Head | **countersunk**, DIN 7991 | socket / button |
| Relief | Ø6.0 × 90° countersink, 1.30 mm deep | Ø6.5 counterbore, 1.00 mm deep |
| Engagement | length − plate thickness = 3.0 | length − grip = 6 − 3.0 = 3.0 |

Those figures are dry. With the 0.5 mm interface pad fitted the screw also has
to cross the pad, so engagement falls to about 2.6 mm once it compresses — still
five threads, and the error is in the safe direction: the pad can only ever move
the tip *further* from the PCB screw, never closer.

That is what let the edge bracket go to 4 mm in §6 without touching the fastener
schedule.

**The flat plate's screws are countersunk for a reason, not for looks.** They
enter from the plate's underside — which is the face that mates to the panel — so
a 3.0 mm socket-cap head would stand proud of it and the plate could not sit
flat. A DIN 7991 head sinks flush in 1.30 mm and leaves 1.70 mm of parallel
material. The edge bracket keeps socket heads because its web's underside faces
into open air; nothing mates to it.

The same rule caught the cradle: **M4×6, not ×10.** The bridge foot is 3 mm and
the tray is 4 mm, so a 10 mm screw would stand 3 mm proud of the tray's underside
— again, the panel mating face. And torque it to **1.0 N·m, not 1.5**: 3.0 mm of
M4 thread in 5052 strips at about 2 830 N, 1.0 N·m preloads to about 1 250 N
(a 2.3× margin) and 1.5 N·m to 1 875 N (only 1.5×). 1 250 N per bolt is already
48× the 26 N of uplift a bridge has to resist at 15 g.

---

## 5. Thermal — the honest version

**A mount cannot fix this radio, and this family does not pretend to.**

The PCB stands 8.79 mm off the bottom pan on four standoffs. That gap is *below*
the critical Rayleigh number for a heated horizontal layer, so it does not
convect — it is conduction plus a little radiation, roughly **6.3 K/W board to
pan**. Hold the pan at 40 °C with an infinite heat sink and a 90 °C board still
pushes about **8 W** through it.

So **any bottom-pan mount is capped at 6–8 W of the 15 W peak.** Anyone promising
more from the −Y face is selling something.

What follows from that, and what is actually in the design:

* **The TIM is not the bottleneck and never will be.** 0.5 mm of ordinary
  3 W/mK pad over 17 576 mm² is 0.0095 K/W — about 660× smaller than the air gap
  feeding it. The spec says the cheap pad on purpose. Not putty: every removal
  would become a scrape-and-reapply, and a technician who skips it silently
  halves the path.
* **Emissivity is the cheapest watt.** Black anodise takes ε from ~0.09 to ~0.85,
  roughly doubling radiative transfer per unit area. Hence the finish spec — with
  **masked bare lands**, because anodise is an insulator and a fully anodised
  mount breaks the chassis bond in an enclosure full of RF.
* **The overhang is deliberate.** A bare, flush, radio-sized plate is a small net
  *loss*: it covers pan area that was already working and returns less than it
  takes. The plate only pays with the anodise *and* the overhang *and* ≥15 mm of
  clear convection channel. In a 4 mm lane the channel Nusselt number collapses
  and the face is decoration.
* **I rejected the premise that every watt into the subpanel is a win.** The
  subpanel is *inside* the sealed enclosure and rejects to the same interior air
  the cooler must pump. Conduction into it is a lateral move, not an export.

The change that would actually matter is a gap filler under the PCB — it takes
board-to-pan from 6.3 K/W to about 0.35 K/W. That means opening a sealed unit
with un-surveyed internals, so it is out of scope here and logged in §9.

---

## 6. Shock and vibration

Design load: **0.35 kg × 15 g = 51.5 N**, stated in `params.shock` so it can be
argued with. Reference sweeps (IEC 60945 / IACS UR E10) stop at 33–50 Hz.

`flat_plate` and `clamp_cradle` bolt flat to the panel with no cantilever; their
first mode is the panel's, not theirs. **`edge_bracket` is the only variant where
this is a real question**, and it is the one dimension in the family chosen by
arithmetic rather than by fit.

The radio hangs off two bolt columns, 25.2 mm and 118.8 mm from the bend line,
with its CG exactly midway. Modelling the web as a cantilever plate with the radio
rigid across both columns:

| Web | Only the bolt-pattern width participates | Full 206 mm width |
|---|---|---|
| 3 mm | 119 N/mm → **93 Hz** | 205 N/mm → 122 Hz |
| **4 mm** | 283 N/mm → **143 Hz** | 485 N/mm → 187 Hz |

3 mm clears the sweep, but by under 2× at the pessimistic end and before any
joint compliance. 4 mm buys 1.54× in frequency for 90 g and one extra drill hit,
and thanks to §4 it costs nothing in thread engagement. **4 mm.**

Two notes on the numbers. A point mass at the free edge of the full 135 mm
cantilever gives 57 Hz and would have argued for a much heavier part — that model
is wrong here, because the radio is bolted at *two* columns and the near one is
only 25 mm from the root. And the flange peel case is the reason the flange gets
**two bolt rows** rather than one; six M5 at working preload against a 3.2 N·m
overturning moment is not close to any limit.

The cradle is **a clamp, not an isolator**. Two 3 mm 60-Shore-A pads over
7 250 mm² are stiff in compression (order 10⁴ N/mm); they do not lower the
frequency into anything. Shear is taken by form-lock — the feet in their pockets —
not by friction, which is the part that matters when a preload relaxes.

---

## 7. Materials and process

**Every bent part is 5052-H32, not 6061-T6.** 6061-T6 needs a 2.5–3 t inside bend
radius; a standard punch forms at 1 t and will orange-peel or crack the outer
fibre. 5052-H32 forms at 1 t without complaint, costs slightly less, and is the
better alloy in salt air. It gives up yield strength that is irrelevant at 0.35 kg.
The flat plate stays 6061-T6 because it is never bent and 6061 conducts ~21 %
better.

> This applies beyond this part. The repo's standing spec — *"Everything is 3 mm
> 6061 plate, saw + drill + brake"* — is wrong for every braked plate it covers,
> and any blank computed from a bend radius the shop will not use is wrong by
> 5–12 mm per bend. Worth a sweep of the existing `exports/plates/*.dxf`.

**Flat patterns are developed from the same numbers that build the solid.** The
bend quadrants in the 3D model and the bend allowance in the DXF both come from
one inside radius and one K-factor, so the blank cannot disagree with the part.
`shop_pack_v1.json` carries the bend table:

| Part | Blank | Bends | BA | BD |
|---|---|---|---|---|
| `flat_plate` | 158.0 × 169.0 × 3 | 0 | — | — |
| `edge_bracket` | 164.92 × 206.0 × 4 | 1 @ R4 | 8.922 | 7.078 |
| `clamp_cradle` tray | 188.0 × 169.0 × 4 | 0 | — | — |
| `clamp_cradle` bridge (×2) | 247.17 × 25.0 × 3 | 4 @ R3 | 6.692 | 5.308 |

Fasteners are A4-70 stainless throughout, with stainless or nylon washers under
the heads — aluminium mount, salt air, no plain steel. Sizes and torques are in
`params.fasteners` and repeated in the shop pack; the two that matter are in §4.

**Assembly order matters and is not optional.** The four M3s enter from the
mount's far side and are unreachable once the mount is on the panel, so they are a
*bench* operation: bolt the radio to the mount first, then the assembly to the
panel. Every panel fastener is deliberately placed outboard of the radio's
footprint so it stays reachable with the unit fitted. On the edge bracket the four
flange bolts at y = ±93 are clear of both ends of the radio for exactly this
reason; the pair at y = 0 is a build-time fastener and cannot be reached
afterwards, which is deliberate and stated on the drawing rather than discovered.

---

## 8. Options rejected

**Mounting schemes**

* **Bolt the pan straight to the subpanel — no bracket at all.** This is
  simultaneously the cost floor and the thermal ceiling, and it deserves to be
  written down rather than dismissed: four more holes on a drilling schedule that
  already exists, one $12 interface sheet, zero fabrication. It loses on two
  counts. It eats 176 cm² of subpanel, which the compact layout (largest free
  rectangle 204 × 38 mm) does not have. And **the screw arithmetic depends on the
  panel gauge**: 12 ga leaves 3.09 mm of penetration and 14 ga leaves 3.85 mm,
  which jacks the PCB — a silent failure that must be measured at build, not
  assumed. Fine for a bench rig or a roomier panel.
* **Mount to the eight front/rear case screws.** They have by far the deepest
  thread on the unit (10.96 mm). They also *retain the panels* — removing the
  mount opens the case — and they sit on the two connector faces. Never.
* **Clamp or bond to the top cover alone.** It is the removable cover, with zero
  holes, and its load path is only as good as the eight case screws. The cradle
  presses on it lightly to stop lift; it does not hang anything from it.
* **Locating tabs into the two 3 × 7 side slots.** Nothing is modelled behind
  either slot, so a tab could foul something internal, and because the slots are
  diagonally opposite rather than mirrored any such fixture is handed. Not worth
  it for a feature whose function nobody knows.
* **Grip the 0.254 mm step between the cover skirt and the bottom pan.** Genuinely
  the cleverest unused feature on the unit — rails 121.98 mm apart would form-lock
  the chassis and never load the cover. But it is 0.07 mm of grip per side on
  1.21 mm folded sheet, set by sawn parts on clearance holes. That fit does not
  exist in metal; it is smaller than the noise of every process that would make it.
  The cradle gets its location from the foot pockets instead, at 0.4 mm radial
  clearance — an order of magnitude above process noise.
* **DIN-rail clip adapter.** The rail is already on the panel with spare capacity,
  which makes it tempting. 0.35 kg on a ~122 mm cantilever off 1.0 mm rail hat is
  not a shock mount — the repo's own notes already say so — and it would eat five
  or six of the twelve module widths the rail exists to provide.
* **Keyhole slots so the radio hangs on four pre-fitted screws.** Attractive on a
  vertical panel: the M3 joint is made once on the bench and the clinch never sees
  service tension. It needs a shoulder screw with a controlled standoff, and no
  catalogue metric shoulder screw has a thread short enough for the 3.575 mm
  limit — the standard M3 shoulder screw carries ~5.5 mm and would bottom on the
  PCB screw.
* **Male-female standoffs into the bores.** The same 3.575 mm limit disqualifies
  the entire category: every standard M3 M-F standoff has a 6.0 mm male stud.
* **Two-point mounting** to dodge the asymmetry. Halves the load path on a joint
  whose pushout is already unquantified, and turns the radio into a pendulum. The
  asymmetry costs nothing to accommodate in a CAD-driven flat pattern.
* **Standing the radio on its I/O end** so the front LEDs face the door. It aims
  the 55 mm USB and 45 mm DC keep-outs straight into the subpanel, where the
  cables cannot go.
* **Hinged or swing-out mount.** What stops you reaching the radio is the cable
  bundle and the 55 mm USB volume, not the metal. A hinge adds a bearing that will
  seize in salt air and a moving earth path.

**Features considered and dropped**

* **A return lip on the edge bracket's free edge.** It would raise the section
  stiffness ~65×, and the cantilever does not need it — the load is out of plane,
  where a lip at the tip (zero moment) does nothing useful. Going to 4 mm was the
  cheaper answer to the mode that actually mattered. Two long lips on a 135 mm web
  also camber it, and correcting that is a hidden milling operation on the bearing
  face.
* **Bent-up stiffening upstands along the web's ±Y edges.** These are the lips
  that would actually work — they run perpendicular to the root, which is the
  direction that closes the section in the cantilever mode, and they are worth
  roughly 19× the second moment. Two objections, and only the second survives.
  Bent toward the radio (+Z) they run straight through the front and rear cable
  keep-outs. Bent away (−Z) they clear everything — every keep-out starts at
  z ≥ 3.61 and the lips would sit at z ∈ [−24, −4] — but they add 20 mm to the
  panel strip, taking it from 37.7 to 57.7 mm. That is a 53 % increase in the
  one dimension this variant exists to protect, bought to improve a frequency
  margin that is already 2.9–3.7× at 4 mm. Rejected on the trade, not on the
  geometry.
* **A relief notch in the flange over the vent slot**, so the bend line could sit
  hard against the radio. Saves about 11 mm of depth and costs handedness plus a
  notch that lands on a bolt station. Standing the bend line off 10.8 mm instead
  is simpler and the depth was available.
* **A separate bolt-on cable ledge.** A good idea that freezes a decision nobody
  has made: only 2 of 4 front SMAs and 2 of 3 rear SMAs are populated and the
  cable set is not chosen. Cable-tie slots in the plate edge do the same job for
  zero parts and commit nothing.
* **A connector-face shield.** It covers the printed port legend — the thing a
  technician actually reads — enters the LED cone, blocks four case screws, and
  has to come off before anything can be unplugged. The cabinet door is the shield.
* **Fins on the flat plate.** The internal air gap caps the whole path at 6–8 W;
  fins behind that bottleneck buy a fraction of a kelvin for a much larger part.
* **Elastomeric isolators under the plate.** Nothing in the radio needs isolating,
  and soft mounts would drop the assembly's frequency toward the excitation band
  rather than away from it.
* **3D printing any of these.** Thermal conductivity ~0.2 % of aluminium, and
  creep under bolt preload. The repo prints housings; this is a heat path.

---

## 9. Open risks

1. **The one that can scrap two of the three variants.** PEM catalogues type
   `SOS` as a **blind**-threaded standoff. This vendor STEP shows the bore open
   clean through to the outer face, and every other line of evidence in the file
   says it is tapped M3 — the Ø3.000 modelling convention against Ø3.200 for every
   genuine clearance hole in the same file, an M3×8 with a Ø3.000 shank engaged in
   it, and the PEM `M3` thread code itself. But **nobody has run a screw into a
   real unit.** Five minutes with an M3×6 retires this. Do it before cutting metal
   for `flat_plate` or `edge_bracket`. `clamp_cradle` exists because it has not
   been done.
2. **Clamp load and torque-out of a clinched PEM SOS in 1.210 mm sheet** are not
   derivable from geometry. Get the PEM figures before any vibration qualification.
3. **The cable clear-outs (40 / 45 / 55 mm) are engineering allowances**, not
   measured geometry. Tighten them when the cable assemblies are chosen; the
   keep-out prisms are data in `params.json` and the checks re-run.
4. **The two 3 × 7 side slots have no identified function.** They are given 10 mm
   as vents. If they turn out to be tooling features, the edge bracket could lose
   about 11 mm of depth.
5. **The serial / regulatory label** is on the bottom pan and is not modelled.
   Both bolted variants cover it. Photograph it at build; the cradle leaves it
   readable by lifting the unit.
6. **The real thermal fix is inside the unit** — a gap filler under the PCB. It
   requires opening a sealed radio whose internal component heights nobody has
   surveyed. Log it as a teardown-gated item, not a mount.

---

## 10. How this is checked

Nothing above is trusted; it is asserted. `spec.json` gates the default variant
through `lib.evaluate`, and `fit_check.py` runs 19 geometric assertions against
the **placed vendor solid** — not against numbers anyone typed:

* the transform lands the radio exactly where `params.json` says, and the probe at
  the front-end vent slot proves it is not mirrored;
* all four bores are open on their axes at the modelled hole positions;
* **every variant reports 0.00 mm³ inside every declared keep-out** — connectors,
  cable bend, LED sight lines, case-screw driver swing, and 10 mm around both vent
  slots;
* every variant reports 0.00 mm³ of interference with the radio (feet peeled for
  the bolted pair, feet on for the cradle);
* the cradle's pockets swallow the feet with zero overlap, and its bridges stand
  exactly 3.000 mm off the top cover — the pad thickness;
* the screw arithmetic closes at M3×6 for both bolted variants.

```
19/19 checks passed
overall: PASS -- promoted to parts/custom/ettus-b210-mount/exports/ettus-b210-mount_v1.step
```
