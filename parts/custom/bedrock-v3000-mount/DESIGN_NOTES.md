# SolidRun Bedrock V3000 — mount family

**v2.** Five mounts for the Bedrock V3000 across two interfaces. Parametric
CadQuery is the source of truth; every STEP, DXF and CSV under `exports/` is
derived.

> **v1 → v2 → v3.** v2 added the *hybrid* chassis — a Tile core carrying one
> 60 W fin bank, flat on the other side — and `hybrid_cold_plate`, the mount that
> uses it. **v3 gives that plate a mounting border**: v2's plate stopped 1.5 mm
> outboard of the chassis footprint, so its only host interface was twelve blind
> tapped holes. That is right for a VESA arm and useless for bolting it flat to
> another plate you cannot reach behind. The three folded variants and
> `tile_side_plate` are geometrically unchanged across all three versions.

### Which file is which

`lib.evaluate` promotes **one** artifact — whatever `create_part()` returns,
which is the `upright_deck` bracket. That is what
`exports/bedrock-v3000-mount_v3.step` is, and it is *not* the whole family. The
five variants are separate files, written by `model.py`:

| File in `exports/` | What it is |
|---|---|
| `bdrk_mnt_v3_upright_deck.step` | folded bracket, unit upright on a deck |
| `bdrk_mnt_v3_upright_bulkhead.step` | folded bracket, unit upright off a bulkhead |
| `bdrk_mnt_v3_low_profile_side.step` | folded cradle, unit on its side |
| `bdrk_mnt_v3_tile_side_plate.step` | light plate for a bare Tile |
| **`bdrk_mnt_v3_hybrid_cold_plate.step`** | **the cold plate — the one with the border** |
| `bedrock-v3000-mount_v3.step` | the evaluate gate's promoted copy of `upright_deck` only |
| `bedrock-v3000-mount_v1.step`, `_v2.step` | earlier promotions, kept per the repo's versioning rule |

Run `model.py` with no `--out` and all five land in `exports/`; the longest path
is 249 characters, inside the Win32 limit. `--out` is only needed if you move the
repo deeper.

```bash
UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv run python parts/custom/bedrock-v3000-mount/model.py --out C:/work/bdrk
UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv run python parts/custom/bedrock-v3000-mount/flat_patterns.py --out C:/work/bdrk
UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv run python -m lib.evaluate parts/custom/bedrock-v3000-mount
```

> **Environment.** The in-tree `.venv` cannot import OCP in this checkout — the
> path to `OCP.cp311-win_amd64.pyd` overruns `MAX_PATH` inside the DLL loader.
> Use a short-path venv (`UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv sync
> --all-extras`). Export to a **short directory** too: this repo sits 173
> characters deep, so `exports/bedrock-v3000-mount_v1_upright_bulkhead.step`
> lands past the Win32 limit and SolidWorks reports the file as invalid even
> though the STEP is fine. `model.py` and `flat_patterns.py` both take `--out`,
> and `model.py` warns before writing anything a legacy API cannot open.

---

## 1. Which unit is this actually for

**The vendor STEP contains three chassis superimposed at a single origin.**
Import it naively and you get all three nested inside one another, plus one set
of connector solids shared by all of them. Measured:

| Variant | X extent | Shell volume | ~Mass (Al) | Sides |
|---|---|---|---|---|
| **60 W** | ±36.5 | 470 741 mm³ | 1271 g | 13 fins/side, 10.15 mm pitch, tips 0.395 × 146 mm |
| **30 W** | ±22.5 | 267 463 mm³ | 722 g | 11 fins/side, tips 0.200 × 152 mm |
| **Tile** | ±14.5 | 206 453 mm³ | 557 g | flat — 20 410 mm² clean flat each side, 6× M4 |
| **hybrid** *(derived)* | −14.5…+36.5 | 338 376 mm³ | 914 g | flat 20 410 mm² one side, 60 W bank the other |

All of them share Y (−65.762…65.0) and Z (0…160) exactly, and share the same
connectors, the same two M3 back-wall tappings and the same bottom-cap M4.

**The three folded variants are designed for the 60 W** — widest envelope, worst
thermal case. Because they touch *only* the +Y back wall and the −Z end cap,
which every chassis shares, they take the 30 W, the Tile and either handedness
of hybrid unchanged; the fin clearance just becomes generous. `fit_check.py`
asserts that on every build.

**The two plates work a flat side**, which only the Tile core has:
`tile_side_plate` for a bare Tile, `hybrid_cold_plate` for the hybrid. Neither
fits a 30 W or 60 W — both of those are fin tips on both sides, and
`interface.flat_side_x()` raises rather than hand you one.

`parts/vendor/solidrun-bedrock-v3000/split_variants.py` writes each chassis out
separately if you want to look at them one at a time.

## 2. The hybrid — and a correction I got wrong first time

The brief said the unit has *"a heatsink on one side and a bare plate on the
other."* v1 of this file answered that no such thing exists, because measured on
the 60 W:

```
X = +36.500   7 fin-tip flats, total 407.30 mm2, y-centres [-30.516 -20.3 -10.15 0 10.15 20.3 30.516], z 7..153
X = -36.500   7 fin-tip flats, total 407.30 mm2, identical y-centres, identical z
```

The measurement is right — the two banks are mirror-identical to three decimal
places, and so are the 30 W's (152.00 mm² each). **The conclusion drawn from it
was wrong.** No *body in the file* is finned on one side, but the file's own
architecture is a one-sided unit waiting to be asked for, and three independent
measurements say so:

* **Volume.** Clip the 60 W to \|X\| ≤ 14.5 and it measures 206 896 mm³ against
  the Tile's 206 454 mm³. The 442 mm³ difference is precisely the six M4 bores
  the Tile has and the 60 W does not — 6 × π × 2.05² × 5.83 = 462 mm³.
* **Point sweep.** 539 points through that band agree 535/539, and all four
  disagreements sit inside one of those bores.
* **What is outboard.** 131 921.4 mm³ on each side, with mirror-identical
  bounding boxes. Two identical banks, separable at exactly \|X\| = 14.5.

So the 60 W **is** a Tile core with two fin banks on it, and the Tile core
carries six M4×0.7 **tapped from both ends** — thread \|X\| 11.000…13.916 each
side with 22 mm of open cavity between. That pattern only makes sense as a
heatsink attachment: a screw retaining a bank on one side and a screw mounting
the unit on the other use the same bore from opposite ends and never meet.

```
hybrid  =  Tile core  +  ONE fin bank   ->  338 375.7 mm3, 914 g of aluminium
           X -14.5 .. +36.5 (51 mm wide, against the 60 W's 73)
           flat 20 410 mm2 side one way, 60 W fin bank the other
```

`split_variants.hybrid()` builds it from the file's own geometry and raises if
the bank ever stops measuring 131 921.4 mm³, so a changed vendor file cannot
quietly redefine what `hybrid_cold_plate` is bolted to. Rendered, it is the unit
in the photographs: six bores in a plain flat face on one side, fin bank on the
other. It is *derived*, not a body SolidRun ships — that distinction is worth
keeping, but it is a real configuration and it is by far the best one to mount.

**What it costs.** Half the fin area went with the missing bank. §5 and §6 do not
treat the flat side's conduction path as a bonus; it is the replacement.

The remaining asymmetry, which drives the three folded variants, is **along Y**:

* **−Y is the I/O panel.** Its nominal flat is only 20 × 158 mm and connector
  windows occupy Z = 4.4…153.3 of it. One module stands **2.957 mm proud** (to
  Y = −67.957) and seven panel screw heads stand 0.292 mm proud. Nothing can
  bear on it and nothing may cover it.
* **+Y is a bare, flat back wall** carrying the only purpose-made external
  fixings on the whole part.

And the second asymmetry is along Z: **the fin channels run along Z and are open
at both ends.** Fins are thin plates in the X–Z plane stacked along Y, so each
channel is a 146 mm vertical flue. With +Z up the unit is a chimney. Lay it down
and that stops being true — see §6.

## 3. What you are allowed to bolt to

Everything below was re-measured off the vendor B-rep with `lib/analyze_step.py`
plus axial and ring probes. It is not transcribed from `interfaces.json` or from
a datasheet, and where it disagrees with either, this is what the kernel says.

| Fixing | Where | Measured |
|---|---|---|
| **2× M3×0.5** blind tapped | +Y back wall, (0, 65, 50) and (0, 65, 110), **collinear on X = 0**, 60.000 mm apart | axial probe: void Y 65.000→62.000, solid 62.000→61.000, cavity beyond. **3.000 mm deep, 1.0 mm of wall behind.** Ring probes: minor Ø2.5 / major Ø3.1 |
| **1× M4×0.7** blind tapped | −Z end cap, (+6, 0, 0) | void Z 0→8.95, thread faces 0→8.09, fully enclosed at r ≥ 2.6 |
| ~~1× M4×0.7~~ | −Z end cap, (−6, 0, 0) | **occupied** — vendor screw shank solid Z 0.6→6.0. Head is *recessed* 0.6 mm, so a flat pad clears it; we put an Ø8 relief over it anyway |
| **6× M4×0.7** (Tile **core** — so the Tile and a hybrid's flat side; NOT the 30 W or 60 W) | X axis at (Y,Z) = (−60,10) (60,10) (0,40) (0,110) (−50,150) (50,150) | thread \|X\| 11.000…13.916 each side, 22 mm of cavity between; **3.5 mm max penetration per side**, and both ends are usable at once |

That is the entire external fixing set. On a 30 W or 60 W there is nothing on
±X, nothing on −Y, nothing on +Z. The eight full-length Ø4 "holes" visible in the 60 W fin bank are
not bores: each is a single concave cylindrical face of 64.6° or 95.3° sweep — an
R2.0 fin-root fillet, open to the channel along its whole length.

**The 3.000 mm limit is the sharpest constraint in the part.** A screw that
reaches the bottom does not simply stop; it jacks the bracket off the bearing
land, and the joint still feels tight while it does it. So the arithmetic is in
code, not in a note: `interface.check_backwall_screw()` raises during the build,
and a bracket whose fastener schedule bottoms out never reaches a fit check.

```
M3x5 through a 2.5 mm grip -> 2.5 mm engagement    (0.5 mm of reserve)
M3x6 through the same grip -> ValueError: ... will bottom out and jack the bracket off the face
```

The 2.5 mm grip comes from a **0.5 mm spotface** in the 3.0 mm plate. Without
it the same screw penetrates 3.5 mm. The spotface is load-bearing, not cosmetic.

### The +Y land is narrower than it looks

The continuous flat at Y = 65.000 is only **20 mm wide** (X −10…+10, Z 1…159).
Scanlines just below it:

```
y = 64.90   material at X -13.25..-11.0 and +11.0..+13.25    <- blend ridges, 0.1 mm low
y = 64.50   material X -18.25..+18.25
y = 64.00   material beyond +/-20
```

The ridges are *recessed*, so a flat plate does bear on the land rather than
rocking on them — but by 0.1 mm, which is inside the flatness you get from a
laser-cut, press-braked plate. Every variant therefore carries **two through
slots at \|X\| 9.5…22**, leaving a 19 mm bearing tongue on the land and picking
structure back up only where the chassis has fallen at least 0.7 mm clear. A
through slot is an unambiguous relief; a milled one would be a second setup.

### The −Z cap is not a plate

It is the largest single flat on the part (4617.2 mm² at Z = 0, spanning
X −29.5…29.5, Y −64…64) but the fin channels are **open through it** outboard of
\|X\| ≈ 14.5. Scanline at Z = 0.5, Y = −30:

```
[(-30.0, -25.5), (-14.5, 14.5), (25.5, 30.0)]     <- void from 14.5 to 25.5: that is the inlet
```

So a solid pan laid across the footprint blanks the chimney inlet. Every variant
that bears on −Z bears **only inside \|X\| ≤ 15** and leaves both inlet bands
open. `fit_check.py` measures the resulting contact area rather than trusting it.

## 4. Loads

Design mass **1.6 kg** (measured 1271 g of aluminium shell plus board, spreader
and internals), CG at roughly (0, 0, 80) — 65 mm out from the mount face and
80 mm above the end cap. Maritime/vehicle service, so **20 g** design shock:
314 N.

The two M3 are collinear on X = 0. By themselves they react **no** moment about
Z and none about Y; only the bracket pad bearing on a 20 mm-wide land does that,
and 20 mm is a 10 mm moment arm. Hanging 1.6 kg off them alone gives, at 20 g:

```
M = 314 N x 65 mm  = 20.4 N.m  about the mount face
reacted across a 20 mm pad  ->  ~1020 N prying each edge, on 2.5 mm of M3 thread
```

That is why nothing here hangs off the M3 pair. In every variant the load goes
into geometry first and the screws take what is left:

| | upright_deck | upright_bulkhead | low_profile_side | tile / cold plate |
|---|---|---|---|---|
| Weight | pan, in compression | shelf, in compression | 3 bolted joints in shear/friction | 6 bolts in shear |
| Fore/aft (Y) | spine in tension + pan shear | web + shelf | end wall bearing | plate bearing |
| Lateral (X) | **shock walls**, 2.0 mm off the fin tips | side flanges + shelf | base + back wall | plate bearing |
| Roll about Z | pan contact couple, ±15 mm | shelf couple | base couple | 6-bolt pattern, ±60 mm |
| Tip-over about X | spine in tension (143 mm arm) | web in tension | end wall + M4 | n/a |
| Lift-off | 2× M3 + optional M4 | 2× M3 + optional M4 | 2× M3 + optional M4 | 6× M4 |

**The −Z M4 is optional in all three general variants.** Its mirror twin already
has a vendor screw in it, which says loudly that it is a bottom-cover assembly
screw and not a customer fixing. Every mount stands up without it; fitting it
only improves the anti-prying reaction. Confirm with SolidRun before relying on it.

Measured bearing, from `fit_check.py` (contact area, not "it touches"):

```
upright_deck        pan on the -Z cap                3346.7 mm2      spine tongue on the +Y land   2456.3 mm2
upright_bulkhead    shelf on the -Z cap              2146.3 mm2      web tongue on the +Y land     2582.9 mm2
low_profile_side    end wall on the -Z cap           4385.8 mm2      back wall tongue              3024.7 mm2
tile_side_plate     plate on the -X side flat       16072.5 mm2
```

## 5. The five variants

All folded variants: **3.0 mm 5052-H32 aluminium, laser cut + press brake**,
Ri 3.0 mm inside, A4-70 stainless fasteners with an isolating washer under the
head. For a salt-spray-critical install substitute **3.0 mm 316L** at the same
geometry and expect about 3× the mass (deck bracket: 160 g in 5052, 478 g in
316L). Every visible edge gets a 0.5 mm break; every plan corner is radiused.

### `upright_deck` — the primary
*+Z up. Bolts down to a horizontal deck or subpanel. One folded part, 4 bends.*

An open pan under the unit, two shock walls, a spine up the back wall.
90 × 161 × 139 mm, 160 g, 8× M5 countersunk into the host.

* The pan bears only on \|X\| ≤ 15; two windows leave both fin inlets open.
* The shock walls stand at \|X\| = 38.5 — **2.0 mm off the fin tips**, so they
  never touch in service. They are the low-Z reaction that lets the M3 pair take
  lateral shock in shear instead of in prying, and they double as fin guards for
  0.4 mm-wide tips that will otherwise be damaged in handling. Five drain/vent
  slots each, so they neither pond water nor blank the inlet's side entry.
* The pan→spine bend has a **relief notch across \|X\| ≤ 30**. This is not
  styling: a 90° bend's inside fillet occupies Y 62…65, Z 0…3, and the chassis
  is *in* that space (its own bottom-rear corner carries only a 1 mm × 45°
  chamfer). No sheet gauge stiff enough to carry 1.6 kg bends tightly enough to
  fit. So the bend survives only in the two ears outboard of the chassis, and
  the pan meets the spine there.
* Host bolts are **countersunk M5**, flush, so four of them can live under the
  chassis footprint. M6 countersunk will not fit in 3.0 mm plate — the head
  sinks 3.35 mm.

### `upright_bulkhead`
*+Z up. Bolts back to a vertical bulkhead. One folded part, 7 bends.*

A top hat: a web on the back wall, two side flanges taking it back, two return
flanges on the bulkhead. 148 × 120 × 158 mm, 247 g, 6× M5 countersunk.

**The 30 mm standoff is the whole point.** A bracket that pins this unit flat to
a bulkhead puts a plate one millimetre from a live fin bank. Weight sits on a
short shelf bent forward under the −Z cap, closed into a channel by a
down-turned front lip that also serves as the drip edge, and stopping at Y = −22
so it never reaches the I/O face.

### `low_profile_side`
*−X down. 89 mm of stack instead of 173. One folded part, 2 bends.*

The honest one. See §6 for the thermal cost.

**There is no fin-free bearing surface anywhere on ±X.** The band below Z = 7
that looks like solid skin — where the fin ramps run out to the end cap — is
still a comb: sectioned at Z = 4 the outer surface alternates between fin ramps
at \|X\| = 33.5 and root-wall valleys at \|X\| = 25.4, on the 10.15 mm fin pitch.
So this variant does not rest the unit on anything. It bolts to the two fin-free
faces and carries the weight the way any bolted joint carries shear — through
preload friction, with the screw shanks as the backstop:

```
314 N at 20 g   vs   ~1.4 kN of friction from three screws at their rated torque
```

The base is a **guard, not a seat**: 9.5 mm below the fin tips, never touching.
If the joint ever slipped, the unit drops 9.5 mm onto a broad frame instead of
hanging on 2.5 mm of M3 thread. Two large windows keep the lower bank open to
ambient rather than boxing it in. `test_low_profile_base_never_touches_the_lower_fin_bank`
fails if anyone parameterises that standoff away.

### `tile_side_plate`
*Tile chassis only. Flat 3.0 mm plate, laser only, no bends.*

The Tile is the one variant whose sides are worth bolting to, and SolidRun put a
six-point M4 pattern there on a 20 410 mm² flat. Six fixings on a big flat beat
two shallow M3 in every direction that matters; the plate lands full-contact so
it is a real conduction path off a fanless unit; and because the load is spread,
no bends are needed at all. Carries VESA 75 and VESA 100 so the unit goes on any
standard arm or wall plate. **M4×6 through 3.0 mm of plate engages exactly
3.0 mm** against the 3.5 mm per-side limit.

This pattern does **not** exist on the 30 W or 60 W. `test_tile_pattern_is_not_carried_onto_the_finned_chassis` exists to stop it migrating.

### `hybrid_cold_plate` — the one the hybrid earns
*Hybrid chassis. The flat side bolts to a structure, the fin bank stays in air.
**5.0 mm 6082-T6**, laser/waterjet profile + CNC drill, countersink and tap. No
bends. 168 × 200 mm, 447 g. Handed — `fin_side` builds either.*

Take one fin bank off a 60 W and the unit gains what no other configuration has:
a **20 410 mm² flat face carrying six M4 on a 120 × 140 mm spread**. Measured
bearing when the plate is clamped to it: **20 424 mm²** — essentially the entire
flat. Against the 2× M3 back-wall pair that is not an incremental improvement:
six fixings instead of two, a 120 mm arm in Y instead of zero, 8× the bearing
area, and 3.0 mm of M4 thread apiece instead of 2.5 mm of M3.

**It is solid, and that is the design.** `tile_side_plate` can be skeletal
because a fanless Tile has little to shed. This cannot: half the fin area left
with the bank, so this plate is the replacement heat path, not a bracket that
happens to touch. 5 mm of 6082 spreads across the whole plate — the thermal
spreading length √(kt/h) is about 290 mm against a 168 mm plate — so the useful
question is not the plate, it is **what the plate is bolted to** — and the border
is 40% more conducting and convecting area than the chassis flat it covers. Bolt it to a
bulkhead or a chassis that conducts and the trade is a good one. Bolt it to a
plastic panel and you have thrown away a fin bank for nothing; use a
double-finned 60 W and one of the upright variants instead.

Fastener direction sets the whole design, and it is worth spelling out because
it is not free choice:

* The unit is a closed box, so the six M4 can only enter from the plate's **outer**
  face — which is the face that has to bed flat against the host. So they are
  **countersunk**: M4×8, 90°, sinking 1.95 mm in 5.0 mm of plate, **3.0 mm
  engagement** against the 3.5 mm per-side limit.
* Host screws can only come from the host's far side, so they thread into the
  plate. Those holes are **blind, never through** — a through-tapped hole lets an
  over-length host screw stand proud on the bearing face and pivot the plate off
  the chassis. `test_cold_plate_host_taps_never_break_through_the_bearing_face`.
* Host interface, two of them, because they answer different questions:
  * **six M6 straight through a border** on a **148 × 180 rectangle**. The plate
    is 168 × 200 mm — 19.5 mm wider than the chassis flat on every side — so a
    10 mm bolt head at Y = ±74 spans 69…79 and clears the unit's own edge at
    64.49 by 4.5 mm. These are the bolts you can still get a key on with the
    Bedrock already fitted, and they are what "bolt it to another plate" needs.
    `host_drilling.csv` is the pattern to put in that other plate.
  * **VESA 75 and VESA 100 in M4**, tapped 4.0 mm blind into the 5.0 mm plate,
    for an arm. Blind, never through — see above.

Use a thin thermal interface material in the joint. Metal-to-metal on six bolts
at 2.5 N·m is respectable, but this joint is now carrying heat the fins used to.

The first cut of this plate put two M5 taps 4.47 mm from an 8.4 mm countersink —
overlapping, with nothing for the tap to cut on one flank. It was invisible in
the assembly view and obvious in a render of the far face, which is not a way to
find things, so `check_feature_spacing()` now refuses any face whose features
are closer than r₁ + r₂ + 1.0 mm.

## 6. Lying down: the honest answer

Fin channels run along Z. Upright, each channel is a 146 mm vertical flue open
at both ends and the unit convects as designed. Any orientation with Z horizontal
turns those flues horizontal, and buoyancy stops driving flow along them.

Of the ways to put it down, **−X down is the best of them, and it is still a
derate.** With one bank facing up its channels open upward and behave like a
conventional upward-facing fin array; the bank underneath is close to dead
whichever way you arrange it. Expect to lose something like a third of the free
convection versus upright. That is an engineering estimate from the geometry, not
a measurement — **we have not run a thermal test and this file should not be read
as one.**

So `low_profile_side` ships with a stated condition: it is for the 30 W and Tile
chassis, or for a 60 W with forced air or a duty cycle that does not sit at 60 W.
If you need 60 W passive, use one of the upright variants. The 9.5 mm plenum and
the open base windows are there to get what is left out of the lower bank, not
to pretend the derate is not real.

The two orientations rejected outright:

* **+Y down (on the back wall).** Structurally excellent — the vendor's own
  mount face becomes the foot, weight goes straight into 3140 mm² of flat, the
  M3 pair sees only lift-off. But it is *taller* than lying on the side (133 mm
  vs 89 mm), so it gives up the one thing lying down is for, and both fin banks
  end up with horizontal channels and horizontal fins. Worst of both.
* **−Y down (on the I/O panel).** Every connector is on that face and one module
  stands 2.957 mm proud of it. Not a candidate.

## 7. Options rejected

| Option | Why not |
|---|---|
| **Clamp or strap over the fin banks** | 407.3 mm² of bearing per side, in seven strips 0.395 mm wide. Clamping crushes fin tips, and any strap across the bank blocks that Z station of every channel it crosses. |
| **Bolt to the ±X faces of the 60 W / 30 W** | There is nothing to bolt to. Zero holes. The eight Ø4 features in the fin bank are R2.0 root fillets open to the channel, not bores — a ring probe at r = 1.8 finds no material at any angle. |
| **Carry the Tile's 6× M4 side pattern to the finned chassis** | It does not exist there. A bracket that assumed it generalised would arrive at a fin bank. |
| **Hang the unit off the 2× M3 alone** (the obvious minimal bracket) | 20.4 N·m of tip-over at 20 g against a 20 mm-wide pad is ~1 kN of prying on 2.5 mm of M3 thread in aluminium. It survives static hand-load and fails a shock spec. |
| **Rely on the −Z M4 as a structural fixing** | Its mirror twin already has a vendor screw fitted, which reads as a bottom-cover assembly screw. Designed in as optional instead, so nothing breaks if SolidRun says hands off. |
| **A single folded L, pan bent straight up into the spine** | Geometrically impossible. A 90° bend in 3.0 mm sheet has a ≥3 mm inside radius and the chassis' own bottom-rear corner carries only a 1 mm chamfer, so the fillet interferes. Thinner sheet gets the radius down but not enough, and is too flimsy for 1.6 kg. Solved with a bend relief notch and two ears. |
| **A joggle (offset bend) to bring a wide back plate onto the 20 mm land** | Works, and is standard aircraft practice, but needs a joggle tool for a 3 mm offset in 3 mm material. Two laser-cut through slots do the same job with no extra tooling and give an unambiguous relief instead of a 1.5 mm one. |
| **A wide flat back plate with no relief at all** | It bears on the land, but with only 0.1 mm to the blend ridges — inside the flatness of a braked plate. Cheap to relieve; expensive to discover on a boat. |
| **A saddle keyed into the chassis' end flare (Z 0…7)** for the side-lying variant | The flare looks like solid skin in a coarse scan and is not: at Z = 4 it is still a fin comb on 10.15 mm pitch. A saddle there bears on ~13 fin-ramp edges. Measured with `section_profile.py`, then abandoned. |
| **Elastomer strips under the lower fin bank** (side-lying) | Spreads load and damps, but puts the whole 1.6 kg on 0.4 mm-wide fin tips through a pad, insulates the bank it sits on, and adds a consumable. The bolted-joint-plus-guard answer needs no rubber. |
| **A close-fitting shroud over the fin tips to duct the chimney** | A real technique for tall vertical arrays, and it might help. But it is a thermal claim we cannot test here, and getting it wrong turns a cooling feature into a blanket. The shock walls are kept to 16 mm at the base where they cannot act as a shroud. |
| **Machined 6061-T6 plate instead of folded sheet** | Buys milled relief lands and more stiffness, and would remove the bend-relief problem entirely. Rejected on cost and mass for a bracket this size — folded sheet solves the same problems with laser features. Worth revisiting if a batch is ever small and the tolerance stack tightens. |
| **M6 host bolts** | An M6 countersunk head sinks 3.35 mm and the plate is 3.0 mm. M5 sinks 2.45 mm and leaves 0.55 mm, and four of the eight host bolts have to be flush because they live under the chassis. |
| **A separate spacer bar between a wide back plate and the unit** | Restores the 20 mm land at the cost of a loose second part to hold during assembly, and pushes the M3 grip to 9 mm where the screw-length arithmetic gets tight. |
| **Lightening the cold plate like `tile_side_plate`** | Saves ~240 g and deletes the reason the variant exists. The hybrid gave up a fin bank; the plate is what replaces it. `test_cold_plate_is_solid_where_the_tile_plate_is_skeletal` fails if someone tries. |
| **A 6 mm cold plate** (better tapping, better spreading) | The M4 arithmetic stops working: M4×8 through 6 mm engages 2.0 mm, M4×10 penetrates 4.0 mm past the 3.5 mm limit. Recovering it needs a counterbore plus a low-head DIN 6912 screw — a specialist fastener to buy a millimetre. 5 mm takes a plain countersunk screw and still spreads across the whole plate. |
| **Through-tapping the cold plate's host holes** | Much easier to make, and it puts a screw tip on the face that beds against the chassis the first time someone fits a long M5. Blind, with the drill depth checked against the plate thickness in code. |
| **An upright bracket that holds the hybrid by its flat side** | Genuinely attractive — six M4 beats two M3 for a deck mount too. But `upright_deck` and `upright_bulkhead` already take the hybrid unedited, and a flat-side upright needs the same bend-relief gymnastics for its base-to-web corner that §7 describes, for a load case the existing parts already handle. Worth building if a hybrid deck mount is ever actually specified; not worth pre-emptively. |
| **Re-cutting `upright_deck`'s shock walls for the hybrid** | On a hybrid the flat-side wall sits 24 mm off the flat face instead of 2.0 mm off a fin tip, so it is a loose stop. It still fits and still works; and anyone mounting a hybrid has the six-M4 flat side available, which is a better answer than a closer wall. Left alone rather than making a good v1 part asymmetric. |

## 8. Shop pack

`flat_patterns.py --out <short dir>` writes:

```
plates/upright_deck_flat.dxf        110.4 x 292.4 mm, 26 holes
plates/upright_bulkhead_flat.dxf    198.8 x 250.1 mm, 18 holes
plates/low_profile_side_flat.dxf    254.7 x 221.7 mm, 14 holes
plates/tile_side_plate.dxf          168.0 x 132.0 mm, 15 holes  (already flat)
plates/hybrid_cold_plate.dxf        168.0 x 132.0 mm,  6 holes  (already flat)
bend_table.csv                      11 bends
machining_ops.csv                   47 secondary features
fastener_schedule.csv               35 screws, every engagement checked against its limit
```

A DXF is the **laser file**: an outline and through holes, taken from the face
that has only those. Everything a laser cannot cut — the spotfaces that set the
M3 grip, every countersink, and the cold plate's twelve blind tapped holes —
lives in `machining_ops.csv` with its tool diameter, depth and the reason it
exists. Ship the DXFs alone and the spotfaces never get cut, which puts the M3
grip at 3.0 mm instead of 2.5 and jacks the first bracket off the chassis.

Blanks are developed from the solids, not drawn: each leg's outer face is lifted
off the built part — holes, slots and countersink mouths included — rotated into
the blank plane and slid to its developed station, with bend-allowance strips
between. Two guards run on every development:

* **the blank must come out as one connected solid** — a leg that does not reach
  its bend strip means a station is wrong;
* **the hole count must match the legs** — fewer means a countersink reached a
  leg's outline and became a bite out of the blank where a screw should go; more
  means a slot or window ran off a leg into its bend tangent, which a press
  brake cannot form across. Both defects were in the first version of this part
  and both were found by that check, not by looking at the render.

**Bend allowance** uses `BA = (π/180)·angle·(Ri + K·t)`; at Ri = t = 3.0 and
K = 0.42 a 90° bend develops 6.692 mm against a 12.000 mm outside dimension, a
bend deduction of 5.308 mm. **K = 0.42 is assumed, not measured** — confirm it
against the shop's own coupon before cutting a batch, or hand them the folded
STEP and the bend table and let them develop it with their own constant. It
affects only the blanks; it can never affect the folded solid or a fit result.

### Assembly sequence — folded variants

1. Bolt the bracket to the host **first** — four of the deck variant's eight
   host screws sit under the chassis footprint.
2. Set the unit down on the pan / shelf / base and slide it back until the back
   wall meets the tongue.
3. Fit the 2× M3×5 into the back wall. **0.5 N·m.** Do not substitute a longer
   screw; M3×6 in this bracket bottoms out.
4. Optionally fit the M4×8 countersunk into the bottom cap. **2.0 N·m**,
   5.0 mm engagement — only if SolidRun confirms that tapping is available.
5. The unit comes out again by removing three screws, with the bracket left in
   place and every host bolt untouched.

### Assembly sequence — `hybrid_cold_plate`

1. Fit the plate to the **unit** first, on the bench: 6× M4×8 countersunk,
   **2.5 N·m**, 3.0 mm engagement. Thin thermal interface material in the joint.
   Do not substitute longer screws — M4×10 here penetrates 4.0 mm past the
   3.5 mm the side bore gives.
2. Offer the assembly up and fix it by its host interface (VESA 75/100 in M4, or
   the four M5), with the screws coming from the host's far side.
3. Keep the fin bank in free air. Nothing about this mount cools the unit; the
   plate only conducts into whatever it is bolted to.
4. If the unit is a Tile core with the bank fitted on the far side, those bank
   screws are in the same six bores from the other end. They do not interfere,
   but do not remove them expecting the mount to hold the bank on.

## 9. What is still open

* **Whether the −Z M4 at (+6, 0, 0) is ours to use.** Its twin has a vendor
  screw in it. Designed around as optional; confirm with SolidRun.
* **Thread pitches are inferred from modelled major/minor diameters**
  (M3×0.5 from 3.086/2.529; M4×0.7 from 4.109/3.332), not from pitch data in the
  file. Gauge a physical unit before committing a batch of screws.
* **Cable clearances are engineering allowances, not measurements.** This is
  SolidRun's "Basic 3D model": connector bodies are simplified blocks with no
  mating-plug geometry. 55 mm in front of −Y covers an RJ45 plug plus Cat6
  minimum bend; 45 mm above +Z covers an SMA plug plus RG316 bend. Check them
  against the actual harness.
* **No thermal test.** Every statement in §6 is reasoned from fin geometry.
  A 60 W unit lying on its side should be instrumented before it is trusted.
* **K-factor**, as above.
* **The 30 W chassis was characterised only to the depth needed** to confirm the
  general variants clear it. It fits; it has not been optimised for.
* **Whether SolidRun sells the hybrid as a SKU, or whether it is assembled from a
  Tile plus a bank, is not determinable from the file.** The geometry is
  unambiguous — the split plane, the identical banks, the double-ended bore
  pattern — and it matches the photographs, but the vendor STEP ships no hybrid
  body and no fin-bank attachment hardware. Confirm the fin-bank retention
  screws before assuming the six bores are free from the far side.
* **How much cooling the hybrid actually loses** is estimated from area, not
  measured. One bank is half the fin surface; how much of that comes back through
  a conducting mount depends entirely on the host. Instrument it before running a
  hybrid at 60 W.
