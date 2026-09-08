# MEAN WELL NSP-1600 — mount family

Two generations of hardware for the one attitude the unit is qualified in, all built from
one parametric model in one frame and all gated by the same checks against the vendor
solid. **v2 is the current design**; v1 is kept, still builds, and is exported alongside.

| Kit | Ver. | Host surface | Pieces | Metal | Into the unit |
|---|---|---|---|---|---|
| **`deck_tab_kit`** (default) | v2 | horizontal deck | 4× `side_tab` + `terminal_box` | **28 g** | 4× M4, flush |
| **`bulkhead_strap_kit`** | v2 | vertical bulkhead | 2× `bulkhead_strap` + 2× `side_tab` + `terminal_box` | **138 g** | 2× M4, flush |
| `deck_tray_kit` | v1 | horizontal deck | `deck_tray` + 4× `spacer_ring` + `busbar_hood` | 442 g | 4× M4 + 3× M3 opt. |
| `bulkhead_shelf_kit` | v1 | vertical bulkhead | `bulkhead_shelf` + 2× `spacer_ring` + `busbar_hood` | 584 g | 2× M4 + 3× M3 |

| Part | Ver. | Material | Process | Blank | Mass |
|---|---|---|---|---|---|
| `side_tab` | v2 | 5052-H32, 3 mm | laser + **1 bend** | 47.7 × 20 mm | 7 g |
| `bulkhead_strap` | v2 | 5052-H32, 3 mm | laser + **1 bend** + tap 2× M3 | 172.2 × 45 mm | 62 g |
| `terminal_box` | v2 | PC, UL94 V-0 | FDM, no supports | 90.5 × 79 × 47 mm | ~55 g |
| `bulkhead_shelf` | v1 | 5052-H32, 3 mm | laser + 2 bends + tap | 188.4 × 412 mm | 583 g |
| `deck_tray` | v1 | 5052-H32, 3 mm | laser + 2 bends + tap | 152.4 × 412 mm | 440 g |
| `busbar_hood` | v1 | PC, UL94 V-0 | FDM | 90.5 × 74.5 × 47 mm | ~40 g |
| `spacer_ring` | v1 | 5052-H32, 3 mm | laser | Ø10 / Ø4.5 | 0.5 g |

```bash
# every variant as STEP (short names), the default again under the part name, STL for the printed parts
C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/model.py --out C:/work/nsp

# 1:1 DXF blanks for the four folded parts and the ring, bend table, 59-row fastener schedule
C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/flat_patterns.py --out C:/work/nsp

# the gate: build -> export -> re-import -> geometry checks -> 30 fit cases -> 2 validators -> promote
C:/venvs/cadquery/Scripts/python.exe -m lib.evaluate parts/custom/nsp1600-mount

# the geometric assertions against the placed vendor solid, every kit, on their own
C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/fit_check.py --verbose

# product and fit views -> references/views/
C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/render_variants.py

# parametric invariants
C:/venvs/cadquery/Scripts/python.exe -m pytest tests/test_nsp1600_mount.py
```

> **Environment.** The in-tree `.venv` cannot import OCP from this checkout (the path to
> `OCP.cp311-win_amd64.pyd` overruns `MAX_PATH`), so `make eval` / `make test` do not work
> from here. Use the short-path venv (`UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv sync
> --all-extras`) and call its interpreter directly. **Export to a short directory** — this
> repo sits 173 characters deep and SolidWorks refuses a STEP whose path passes 259.
> `model.py` warns before writing one.

---

## 1. What this unit actually is

Nothing here was taken from `interfaces.json` or from the compact layout's notes; both
said the NSP-1600's numbers were derived, not measured. Everything below was re-measured
from `parts/vendor/meanwell-nsp-1600/NSP-1600_0417.stp` with `lib/analyze_step.py` plus
axial and ring probes, and then checked against the Case No. 296A drawing in the
datasheet (2026-06-15, in `parts/vendor/meanwell-nsp-1600/datasheets/`). The vendor
folder's README carries the full face-by-face account.

**The frame.** Vendor frame translated by **(−66.787, −354.15, −1.5)**: origin on the
unit's bottom face, centred on its width, at the terminal plate; +Y along the blades
(the body is at Y ≤ 0); +Z up. A pure translation — no rotation, so no handedness trap.
In this frame the datasheet's hole dimensions appear verbatim, and every measured hole
agrees with the drawing to 0.002 mm:

```
body                 X ±42.5   Y −300.598 … 0   Z 0 … 41         (datasheet 300 × 85 × 41)
bottom  3× M3        (±35, −16.1)  (0, −280.8)                    drawing: 70 × 264.7, 16.1 from the end, 7.5 from the sides
sides   2× M4/side   (±42.5, −5.8, 22.8)  (±42.5, −257.8, 22.8)  drawing: 252 apart, 22.8 up, 5.8 from the end
blades  2 mm thick   long  X 12.5…14.5  to Y +38.0  hole Ø6.5 at (Y 30.0, Z 21.95)
                     short X 33.0…35.0  to Y +28.0  hole Ø6.5 at (Y 20.0, Z 29.95)
AC block             X −36.7…−2.3  proud to Y +8.0  Z 6…21
```

**What each face is.**

* **−Z bottom** — flat, 22 450 mm² of steel, nothing proud, three M3. A bearing face.
* **±X sides** — flat 1.2 mm walls carrying only flush countersunk vendor screws and the
  M4s. **No vents.** They may be covered.
* **+Z top** — the removable cover, 24 462 mm², zero holes. Never drilled.
* **−Y** — two 40 × 40 × 28 fans behind a guard. **Exhaust.**
* **+Y** — the terminal plate: fourteen 8 × 5.5 intake louvres, the AC terminal block,
  the two bare DC blades standing 38 and 28 mm proud, CN1/CN2 headers, LED, trim pot.

**Air goes in at the terminal face and out through the fans** — the datasheet's air-flow
arrow, with no top, side or bottom vents to argue with it. So the two end faces are the
only air paths, and the terminal face is simultaneously the intake, the live-parts face
and the cable face.

### The M4s: two are real, two are a promise

The terminal-end pair (Y = −5.8) is a Ø4.54 threaded cross-tube (minor Ø3.1) running
right across the chassis — probed, real, and the reason the datasheet allows 5 mm. The
fan-end pair (Y = −257.8) is **a Ø5.0 clearance opening in each wall with nothing behind
it**. The datasheet draws M4 there and MEAN WELL's own bracket kit (PGG2MHS013A, "M4×4
combination screw") uses all four, so the thread almost certainly exists on the product
and was left out of the model. It is recorded as `SIDE_M4_FAN_END_VERIFIED = False`.
Until a screw has been run into a real unit, drill the deck for the three bottom M3 as
well when building the deck tab kit; the strap kit does not depend on the fan-end pair
for anything but location.

### Penetration limits

| | Datasheet | Measured behind the hole | v2 | v1 |
|---|---|---|---|---|
| side M4 | **5 mm max**, 7–10 kgf·cm | threaded tube (terminal end); unknown (fan end) | M4×8 + 0.8 washer through 3.0 tab → **4.2** | M4×10 through wall + ring → 3.2 |
| bottom M3 | **4 mm max**, 6–8 kgf·cm | PCB underside at 4.5 | not used | M3×6 csk through 3.0 → 3.0 |

Both are enforced in code: `interface.check_side_screw()` and `check_bottom_screw()`
raise during the build, so a schedule that bottoms out never reaches a fit check.

## 2. One attitude, and why there is no vertical variant

The datasheet's derating curve is labelled **(HORIZONTAL)** and no other curve is
published. MEAN WELL's enclosed-type installation manual, item 3: "Mounting orientations
other than standard orientation … will require a de-rating in output current. Please refer
to the specification sheets" — which has nothing to refer to. So the unit is qualified
bottom-down with its fan axis horizontal, full stop, and a mount that stood it on end or on
its side would be a thermal claim nobody can back. Every kit keeps it horizontal; they
differ only in what the host surface is.

## 3. v2 — the tab kits

### Why v2 exists

v1 put a full-length folded channel under and beside the unit: 440–580 g of aluminium, a
412 mm blank, two long bends, spacer rings, and drain slots — a bearing floor engineered
for a unit that already has one. **MEAN WELL's own answer is four small L-tabs on the
side M4s**, and it is the right one for a deck: the unit's bottom is a 22 450 mm² flat
that bears on the deck directly, the four M4s in shear are the vendor's own load path,
and each tab is one bend, one hole and one slot. v2 is that pattern, drawn from the
measured interface rather than the vendor's drawing, plus the smallest thing that can do
the one job four tabs cannot — hold the unit horizontal off a *vertical* bulkhead — and a
terminal cover that no longer needs a pan under it.

### Why a tab lies flush and a channel wall could not

This is the whole geometric difference between v1 and v2, and it is one line: **the tab's
foot bends outward, away from the unit.** A 90° bend in 3 mm 5052 has a 3 mm inside
radius. Bend a wall *up from under* the unit and that fillet sits in the unit's bottom
corner, so v1 had to stand every wall 3 mm off and fill the gap with a ring. Bend a foot
*outward* from a leg that stands against the side wall and the fillet occupies
X 42.5…48.5, Z 0…6 — outside the unit's corner. The leg's inner face is flat against the
wall from Z = 6 to the top, the unit's R1.3 corner clears the tab's R6 outer arc by
2.5 mm, and the M4 clamps steel to aluminium with nothing between. `fit_check.py`
measures the bearing by pushing the unit sideways into each tab in turn.

### `side_tab` — the default
*3 mm 5052-H32, one bend. 20 wide, 30 tall, 20 mm foot. 7 g.*

* Ø4.5 through the leg at Z = 22.8; 10 × 5.5 slot in the foot running **across** the
  unit, so ±2.25 mm absorbs the unit's ±0.5 width tolerance, the bend tolerance and the
  host's drilling. Tighten the M4 flush first, the host bolt second.
* Identical at both stations and on both sides — an L is its own mirror image — so one
  part number, quantity four, no handedness.
* The M4 is 5.8 mm from the terminal end, so a symmetric 20 mm tab overhangs the terminal
  plate by 4.2 mm at that station. The vendor's does too. Measured bearing is about
  450 mm² per tab at the fan station and 320 at the terminal station, against an M4 at
  0.8 N·m that needs a few square millimetres; `fit_check.py` asserts 250.
* **Deck kit load path.** Weight into the deck over the unit's whole footprint. Sideways
  and fore-aft shock (353 N at 20 g) into four M4 in shear, each good for roughly 1 kN in
  friction before the shank touches a hole. Lift-off into the M4s in shear too, since the
  tab leg is vertical — the only load that puts them in tension is tip-over, which the
  unit's 85 mm base on the deck reacts before the screws see it.
* Deck drilling: 4× M5 on 112 × 252 (slotted), 4× M3 for the box.

### `bulkhead_strap`
*3 mm 5052-H32, one bend. 45 wide; shelf 108 mm, flange 63 mm down. 62 g. Two per unit.*

Four tabs cannot hang a horizontal unit off a vertical wall: the M4s on the wall side face
the wall and the feet would need a floor. The smallest floor that works is two strips,
one at each M4 station, each an L with the shelf under the unit and the flange **down**
the bulkhead like a shelf bracket, and each carrying one of the deck tabs bolted to its
tip through the tab's own slot.

* **Flange down, not up.** The bolt heads land below the shelf where nothing else is, so
  no head is ever in the gap beside the unit and both are reachable with the unit fitted;
  the cantilever moment goes into the lower bolt in tension and the bend line in
  compression — the classic shelf-bracket load path. v1's up-flange needed keyholes and a
  bolt row above the unit to achieve the same reachability.
* The bend's outer arc is tangent to the shelf top at X = −42.5, the unit's corner, so the
  unit bears on the shelf's full width. Each strap sits 5.8 mm +Y of its M4 station so
  its 45 mm covers the tab (Y −15.8…4.2) and, on the terminal strap, the box's near
  screws at Y = +14. Same part both ends; the fan strap's two box taps go unused, which
  is cheaper than a second part number. The terminal strap therefore has only 22.5 mm
  of its width under the unit; measured bearing for the pair is **5 410 mm²**, four times
  what the Bedrock family accepted for a 1.6 kg unit.
* The tab bolts to the strap's shelf tip with an M5 and a nut underneath — the tab's slot
  faces the same way and absorbs the same tolerances.
* **Stiffness, honestly.** Two 45 × 3 strips cantilevered ~48 mm to the unit's CG are
  worth about 370 N/mm together, a first mode near **70 Hz** with the 1.8 kg on them —
  above the 13–50 Hz maritime sweep, but not by the margin v1's full shelf had (~160 Hz,
  and the unit stiffened that shelf). At a Q of 10 on the 0.7 g endurance level the strap
  root sees about 45 MPa, well inside 5052's fatigue strength. If a rig test finds the
  mode, a 12 mm down-turned lip along one edge of each strap — one more bend on the
  same brake — makes it roughly 20× stiffer. Recorded rather than pre-empted, because
  the point of v2 is to carry no more metal than the job needs.
* Saw-cut 3 mm 6061 unequal-leg angle and a drill make the same part with no brake at all.
* Bulkhead drilling: 4× M5 (two per strap, Z = −18 and −50 below the shelf line), 2× M5
  for the box ears.

### `terminal_box`
*Polycarbonate UL94 V-0, 2.5 mm walls, printed floor-down. ~55 g.*

v1's hood was open at the bottom and finger-safe only because a channel's pan closed it.
With four tabs there is no pan, and on a bulkhead there is nothing under the terminal end
at all. So the box carries its own floor and its cable exits are **closed holes**: thread
the cables through, crimp the lugs, bolt them, slide the box back over. That is how
terminal covers with grommets are always fitted, and it makes the box finger-safe on any
host.

* Five walls, open only toward the unit, **8 mm** off the terminal plate — inside IP2X's
  12.5 mm probe, and clear of the terminal-end tab's 4.2 mm overhang.
* Far wall: two Ø18 grommet holes at the lug barrels, a Ø12 for the AC lead, a 21 × 8.5
  slot that passes the CN1/CN2 DF11 housings, and the 6 × 17 window through which the LED
  is seen and the trim pot reached straight along −Y. Every fixed opening is ≤ 6 mm.
* Louvres as v1: about 2 850 mm² of 5 mm slot on the top and both sides against the
  unit's ~680 mm² of intake. It is a plenum, not a lid.
* Four Ø3.4 floor holes on the same 77.5 × 48 pattern as v1's hood: into the deck (deck
  kit), or the near pair into the terminal strap's M3 taps (strap kit). Two ears past the
  far wall reach the bulkhead plane at X = −48.5 with M5s whose heads are in free space.
* Cable holes are parametric: Ø18 clears a 2 AWG lead with a grommet; a 12 V / 125 A
  build with 1/0 per pole needs Ø22.

### Assembly

**Deck tab kit.** Drill the deck (4× M5 slotted stations, 4× M3 for the box; optionally
3× M3 for the unit's bottom holes). Set the unit down. Hang a tab on each M4 — **M4×8 +
washer, 0.8 N·m**, thread locker — flush on the wall. Drop an M5 through each slot and
tighten. Thread the cables through the box, terminate the lugs (+X faces, barrels toward
+Y, **M6 at 4 N·m**), plug CN1/CN2, slide the box up to 8 mm from the plate and fit its
four M3.

**Bulkhead strap kit.** Two M5 per strap into the bulkhead, flanges down. Set the unit on
the shelves. Tab on each +X M4 as above; M5 + nut through the tab slot and the shelf tip.
Cables and box as above, near screws into the strap's taps, ears to the bulkhead.

Either way the unit comes out again with the host bolts untouched: box off, two or four
M4, lift.

### What v1 still does that v2 does not

A bearing floor with drain slots under the whole unit; a flush countersunk deck interface
with nothing outboard of the unit's width; the bottom M3s used without drilling the host;
a far stiffer bulkhead shelf. None of that is needed for an NSP-1600 on a deck. On a
bulkhead in a vehicle that will actually see the 2 G qualification sweep, run the strap
kit through a rig before choosing it over the shelf, or fit the lip.

## 4. Loads

1.8 kg (datasheet) at **20 g** design shock — the figure the Bedrock family (1.6 kg) is
worked to — is **353 N**. CG taken at the body's geometric centre, 42.5 mm from either
side wall and 20.5 above the bottom. The vendor's own qualification is 2 G, 10–500 Hz.

| | `deck_tab_kit` | `bulkhead_strap_kit` | `bulkhead_shelf` (v1) | `deck_tray` (v1) |
|---|---|---|---|---|
| Weight | deck, 22 450 mm² | two shelves, 5 410 mm² | shelf, 21 457 mm² | pan, 21 457 mm² |
| Sideways / fore-aft | 4× M4 shear | 2× M4 shear + shelf friction | 2× M4 + 3× M3 shear | 4× M4 (+3× M3) |
| Tip-over | base couple on the deck | strap bending + M4 tension | shelf + M4 tension | two walls |
| Lift-off | 4× M4 shear | 2× M4 shear + 3 opt. M3 | 3× M3 + 2× M4 | 4× M4 (+3× M3) |
| Into the host | 4× M5 | 4× M5 + 2× M5 ears | 7× M5 | 4× M5 csk |

## 5. v1 — the channel kits

Kept as designed; every check still runs on them. See §3's last paragraph for when to
prefer them.

**The one geometric idea.** A channel wall bent up from under the unit puts its bend
fillet in the unit's corner. So every v1 wall stands the unit off by **exactly one sheet
thickness**: with side gap = t = Ri the inside arc's pan tangent lands at X = ±42.5, the
unit's corner, the flat pan runs the full 85 mm under it (21 457 mm² measured), and the
gap at each M4 is filled by a **ring cut from the same sheet**.
`test_side_gap_equals_sheet_thickness_equals_bend_radius` keeps the three numbers together.

**`bulkhead_shelf`** — tall flange on the wall, shelf, short far web taking the two +X M4s
from the open side, so the unit goes in and out with the bracket left on the wall. Seven
M5, every one above the unit (Z = 50 row) or beyond its ends, because the heads sit on the
flange's inner face inside the 3 mm gap; two are keyholes. No standoff from the bulkhead —
the unit's side is blank steel.

**`deck_tray`** — pan under the whole unit, two 30 mm walls taking all four M4s through
rings, four M5 countersunk beyond the unit's ends, drain slots, cable-tie slots.

**`busbar_hood`** — the open-bottom vented hood, screwed to a channel's pan extension,
cable U-slots that drop over terminated cables, the same louvres and LED window.

**`spacer_ring`** — Ø10 / Ø4.5 × 3.0, four per tray, two per shelf.

## 6. Options rejected

| Option | Why not |
|---|---|
| **A vertical-attitude variant** | Not qualified. One derating curve, labelled HORIZONTAL; the manual says anything else needs a derating MEAN WELL has not published. |
| **Bolt the unit to the subpanel through its three M3 only** | 1.8 kg on three M3 with ~2 mm of thread each in 1.2 mm sheet, penetration limited to 4 mm, nothing but those threads reacting a 20 g side load. The vendor's kit does not either. |
| **Buy MEAN WELL's kit** (PGG2MHS013A) | It is the right shape and v2 copies it. Ours is cut from the measured interface on the same sheet as every other part in the box, carries a tolerance slot sized to what we measured, and comes with the strap and the box that the kit does not. Buy theirs if a batch is ever small enough that a nest is not worth it. |
| **Tab foot bent inward, under the unit** | Puts the bend fillet in the unit's corner — the v1 problem — and the foot under a face that should sit on the deck. |
| **A narrower tab, fully on the wall at the terminal station** | Would have to be under 11.6 mm wide to avoid overhanging the plate with the M4 only 5.8 mm from the end. An asymmetric tab avoids it but is then a part that can be fitted backwards. |
| **Four tabs for the bulkhead too** | The wall-side M4s face the wall; the tabs' feet need a floor. Hence the straps. |
| **One wide strap instead of two** | Becomes v1's shelf with a different name. |
| **Straps with the flange up** (v1 style) | Bolt heads in the gap beside the unit → keyholes and a bolt row above it. Down keeps everything reachable and follows the shelf-bracket load path. |
| **Lips on the straps from day one** | One more bend on each for a mode that is already above the sweep. Recorded as the upgrade, not pre-empted. |
| **A hood that hangs off the terminal-end tab or M4** | Puts a printed part in the M4's clamp stack and ties the cover's fit to the tab's position. |
| **Keep v1's open-bottom hood and let the deck close it** | Works on a deck, fails on the bulkhead where nothing is under the terminal end. A floor and grommet holes cost nothing in print and make the cover host-independent. |
| **Cable U-slots in the floored box** | A slot open to the floor is a hole in the floor. Grommet holes are how every terminal cover is fitted. |
| **A metal shroud for the blades** | Earthed metal 1.5 mm from a 125 A lug is a fault waiting for a dropped washer. Insulating, printed, V-0. |
| **Wall hard against the unit's side (v1)** | The channel's bend fillet lands inside the unit's corner: 0.9 mm up the fillet or off the wall. |
| **Machined 6061 instead of folded 5052** | Nothing here needs it, and 6061-T6 wants 2.5–3 t at the bend. |

## 7. Shop pack

`flat_patterns.py --out <short dir>` writes:

```
plates/side_tab_flat.dxf         47.7 x 20.0 mm, 2 holes, 1 bend        cut 4 (deck) or 2 (bulkhead)
plates/bulkhead_strap_flat.dxf  172.2 x 45.0 mm, 5 holes, 1 bend        cut 2
plates/bulkhead_shelf_flat.dxf  188.4 x 412.0 mm, 24 holes, 2 bends     v1
plates/deck_tray_flat.dxf       152.4 x 412.0 mm, 23 holes, 2 bends     v1
plates/spacer_ring.dxf          dia 10 / 4.5                            v1
bend_table.csv                  6 bends: line, direction, Ri, K, BA, BD
fastener_schedule.csv           59 rows over the four kits, every engagement checked
```

and `model.py --out <short dir>` writes `nsp_mnt_v2_<variant>.step` for all seven
variants, `nsp1600-mount_v2.step` (= `side_tab`) and STL for the box and the hood.

Blanks are developed from the solids, not drawn: the convex skin of each leg is lifted off
the built part — holes, slots and countersink mouths included — laid into the blank plane
and pinned to its developed station with a bend-allowance strip between. Two guards run
on every development: the blank must be one connected solid, and its hole count must
equal the legs'. **Bend allowance** is `BA = (π/180)·angle·(Ri + K·t)`; at Ri = t = 3.0
and K = 0.42 a 90° bend develops 6.692 mm, a deduction of 5.308. **K = 0.42 is assumed**
— confirm on the shop's coupon or hand them the folded STEP.

## 8. How this is checked

`spec.json` gates the default (`side_tab`) through `lib.evaluate`: envelope, the M4 by
size and position, the slot's end arcs, both bend radii and the rounded leg corners in the
exported STEP, thirty fit cases over all four kits, and two validators. `fit_check.py`
asserts what a render would not show:

* every tab lies on its wall with zero interference and bears there when the unit is
  pushed into it — measured per tab;
* the straps carry the unit on **5 410 mm²** and the tab feet sit on their tips;
* the box clears the unit by 2.8 mm and the tabs by 3.8, sits on the terminal strap, keeps
  every lug and cable envelope inside with no wall through it, keeps the LED sight line,
  and has no fixed opening over 6 mm;
* no metal in the exhaust plume, in front of the terminal face, or across the LED;
* the v1 channels still do everything §5 says.

```
overall: PASS -- promoted to parts/custom/nsp1600-mount/exports/nsp1600-mount_v2.step
76 passed (tests/test_nsp1600_mount.py)
```

## 9. Open items

1. **The fan-end M4 thread.** Absent from the vendor STEP, present in the datasheet and
   used by the vendor's own kit. One screw into one unit settles it; until then drill the
   deck for the three M3 as well.
2. **Strap stiffness** is a cantilever-strip estimate (~70 Hz loaded), not a measurement.
   Rig-test before a vehicle build, or fit the 12 mm lip.
3. **Blade polarity.** The datasheet labels the 38 mm blade −Vo and the 28 mm blade +Vo;
   read the unit's label before wiring.
4. **K-factor** 0.42, assumed.
5. **Lug hardware envelope** (9.5 mm per side of a blade) is an M6 allowance, not a
   measured lug. Check it before printing the box at size; `interface.LUG_HARDWARE_OUT`
   is the one number to change.
6. **Cable sizes.** Ø18 exits for up to 2 AWG; Ø22 for a 12 V / 125 A build.
7. **AC terminal cover.** If MEAN WELL ships one, fit it as well as the box.
8. **No thermal test** of the box. Louvre area is geometry, not a measurement.
9. **The compact layout** still carries derived NSP-1600 holes and a gusseted shelf. Its
   open item is answered by `interface.py`; its shelf should become the strap kit.
