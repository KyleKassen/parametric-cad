# AM59 cold-wall outdoor enclosure (V2)

Redesign of the AM59 outdoor enclosure from first principles, replacing the
V3 four-Seifert sealed thermoelectric concept
(`parts/custom/am59_sealed_tec_enclosure`). The controlling requirements:

- complete-assembly **IP66 target** (driving rain, dust, all normal weather;
  no immersion requirement);
- minimize **weight, cost, wind area, and especially CG height** above the
  rotator;
- the AM59 heatsink shall **not** be inside the conditioned enclosure;
- cooling sized only for the **heat remaining inside** the enclosure, with
  passive, filtered, closed-loop Hoffman, fan, and Seifert options compared
  and no thermoelectric assumption;
- **accessible DIN-rail space** reserved for future power/control/protection;
- connector ports, RF feedthroughs, pressure vent, mast adapter, and rotator
  hardware **deliberately not designed yet**;
- heavy components as **low and close to the rotator axis** as practical.

## 1. First-principles heat recalculation

From the model-specific specification `AM59-005D.pdf` (authoritative) and the
exact vendor STEP:

| Quantity | Value | Source |
|---|---:|---|
| Average DC input (+50 V x 4 A, -8 V x 80 mA) | 200.6 W | datasheet |
| Peak RF output, +64 dBm typ | 2 512 W | datasheet |
| Maximum duty (30 us nom / 100 us max, 1 kHz, 3 %) | 3 % | datasheet |
| Average RF output leaving via cable | 75.4 W | computed |
| **Matched dissipation (all inside the amplifier)** | **~125 W** | computed |
| **Severe full-reflection dissipation** (circulator termination is internal) | **~200 W** | computed |
| Case rating / OEM trip | -10..+70 C / 75 C off, 55 C autoreset | datasheet |
| Amplifier mass | 2.5 kg nominal | datasheet |

The STEP shows the vendor's own solution: a 320 x 180 mm fin field (44
channels, 45 mm fins, 10 mm outer plate) with **three integral 60 mm fans**
blowing axially. The amplifier is *already engineered* for forced-air cooling
to a 70 C case. Every watt is generated in the chassis; nothing else in the
system dissipates more than a few watts.

**Consequence:** if the amplifier's heat crosses the enclosure boundary by
conduction and rejects to outdoor air, the conditioned volume carries only
future DIN electronics (25 W design / 50 W max gate), net solar (~25 W with a
white finish and standoff shield), and chassis leakage (~15 W): **65-90 W
total — passively rejectable**. No thermoelectric or closed-loop cooler is
required, and the entire V3 problem (300 W through four TECs) disappears.

## 2. Architecture comparison

Five architectures were evaluated (A/B/C quantified; D/E bounding):

| | **A: amplifier fully outside** | **B: cold-wall split (selected)** | **C: all-inside + closed-loop (V3 incumbent)** |
|---|---|---|---|
| Concept | Complete OEM amp under a rain hood; small sealed aux box | Modular (heatsink-less) chassis sealed inside on a penetration-free cold floor; OEM-equivalent fin/fan stack outside under the hood | Whole amp + 300 W basis inside; 4x Seifert 3050303 (or 2x Hoffman TE16) |
| Heat inside dry volume | ~30 W | 65-90 W | 300 W basis |
| Cooling hardware | none | none (passive walls) | 4 TECs, 264 W input (TE16 pair: 590 W) |
| Parasitic power | 0 W | 0 W | 264 W continuous |
| Total mass (with amp + DIN allowance) | ~13 kg | **16.8 kg** (computed) | ~34 kg operating |
| CG height above base | ~110 mm | **122 mm** (computed) | ~180 mm |
| CG moment about base | ~1.4 kg m | **2.05 kg m** | ~6.1 kg m |
| Side wind area | ~0.09 m2 | **0.123 m2** (bbox incl. visors/shield) | >0.2 m2 |
| Electronics weather exposure | SMA/N/D-sub, fan wiring, chassis seams all in outside air — **no vendor outdoor rating** | Only anodized fins, duct, fans wetted; every connector and board IP66 | All inside, but 4 cooler cutouts, condensate management, interlocks |
| IP66 outlook | Aux box yes; amplifier itself unrated | **Best: zero dry-boundary penetrations** (no floor holes at all) | Component IP66 coolers; complex boundary |
| Serviceability | Best (amp exposed) | Top lid: amp, clamps, DIN all from one plane; heatsink drops with cradle | Worst (cartridge, baffles, caps, 4 gaskets) |
| ROM hardware cost | ~$1.3 k | **~$2.0-2.6 k** | ~$7-9 k + 24 V/20 A support equipment |
| Key risk | Long-term corrosion of unrated connectors/D-sub in mist, dust, salt | Modular-variant interface is a vendor gate | Violates heatsink-outside requirement; mass/CG/power |

D (everything inside, passive only) fails immediately: 250-285 W across ~4.6
W/K of passive wall conductance is a >54 K cabin rise. E (filter-fan
flow-through) cools easily but is IP54-at-best with loaded filters at a mast
head and fails IP66 — both rejected as bounding cases.

**Selection: B.** It keeps every unrated electronic surface inside an IP66
boundary that has *no penetrations at all* in its wetted floor, keeps the OEM
thermal design (fins + three fans) essentially intact outside, cuts total
mass by ~50 % and the CG moment by ~66 % versus the incumbent, and eliminates
264 W of parasitic cooler power. A is retained as the documented fallback if
Microwave Amps refuses the modular variant: the same tub works with a deeper
skirt, no pad, and the complete OEM amp hung below the floor.

## 3. Selected design description

Coordinates: X = amp airflow (fans -X), Y across (DIN bay +Y), Z up, Z=0 at
the hood-skirt bottom. Overall: **446 x 356 mm plan, 210 mm tall** (224 mm
with solar shield), plus visor overhangs.

Stack-up (bottom to top):

1. **Z 0-83 — hooded air tunnel (wet zone).** Open-bottom 2.5 mm skirt around
   the relocated heatsink: 10 mm baseplate up, fins down, closed underneath by
   a 1.5 mm duct sheet so the 44 channels stay ducted; three OEM 60 mm fans at
   -X blow +X. Both skirt ends have >=200 x 70 mm apertures with stainless
   mesh screens and 25-degree sloped visors. A two-rail cradle lifts the
   baseplate's 3.2 mm side ledges against the lower TIM and bolts to blind
   bosses in the floor underside, bottoming out as the TIM compression stop.
2. **Z 73-89 — cold floor (the dry boundary).** 6 mm continuous floor with a
   machined 330 x 190 x 10 mm pad under the amp bay. Heat path: chassis base →
   1 mm TIM → floor+pad (16 mm Al) → 1 mm TIM → baseplate → fins → fan air.
   **No hole, screw, or weld penetration crosses this boundary anywhere.**
3. **Z 89-141 — amplifier bay (dry).** Modular AM59 chassis (320 x 180 x 48 +
   357 x 200 x 3 flange) sits base-down on the upper TIM. Two clamp bars bear
   on the OEM flange overhang and bottom out on six blind Ø12 bosses at
   nominal TIM compression. All five RF/DC connectors face the ±X interior
   plenums (51/40 mm free) for future feedthrough pigtails.
4. **Z 89-200 — DIN bay (+Y, dry).** Vertical panel with a 300 mm EN 60715
   rail and a reserved 300 x 90 x 100 mm component keep-out, lift-out
   serviceable through the lid. Future components must be rated >=70 C.
5. **Z 205-209 — lid.** 4 mm plate, 28 captive M5 screws (<=58 mm pitch) into
   rim inserts outside a continuous EPDM gasket seated in a machined groove
   with hard compression stops.
6. **Z 209-224 — standoff solar shield.** White ventilated plate; not an
   ingress barrier.

Heavy items sit low: the tub floor/pad (6.5 kg) centers at 108 mm, the
heatsink at 50 mm, the hood at 38 mm; only the 1.9 kg lid and 1.2 kg shield
are high.

### Industrial design (V2 styling layer)

V2 applies the project design language (`DESIGN_LANGUAGE.md`, distilled from
the reference positioner set) without moving any engineering plane:

- **Radiused plan corners** (R12 outer / R9 cavity) on tub, lid, hood, and
  shield; rounded rim opening and pad.
- **Recessed wall panels** (1.5 mm, R8 boundaries) on all four faces; the
  long faces carry proud **chevron X-ribs** (0.3 mm below the face for a
  shadow line), the +X panel carries an embossed **concentric-ring emblem**.
  Minimum structural wall under every recess is 3.0 mm.
- **Crowned lid**: a chamfered frame band inside the fastener line, with all
  28 M5 screws **counterbored** (Ø10 x 2) on the flat perimeter band.
- **Louvered apertures**: three angled slats per hood opening under the
  sloped visor (now with triangular side cheeks) — rain shedding that also
  supplies the reference louver texture; stainless mesh sits behind.
- **Radiused base flange** (12 mm, R16) grounding the skirt and reserving
  the rotator-adapter land (adapter itself still deliberately undesigned).
- Clamp bars get rounded ends and counterbored hardware.

The styling pass costs ~1.0 kg and does not change CG height; all fit,
thermal, and mass gates re-verified after the pass.

## 4. Thermal budget (computed by `thermal_assessment()`)

Amplifier conduction path: R = 0.0216 (interposer: 2 TIMs + 16 mm Al +
spreading) + 0.105 (fin/fan stack, estimate) = **0.127 K/W**.

| Case | 25 C amb | 35 C | 40 C | 45 C | Limit |
|---|---:|---:|---:|---:|---|
| Matched 125 W case temp | 40.8 | 50.8 | 55.8 | **60.8** | 64 C derate begin |
| Severe 200 W case temp | 50.3 | 60.3 | **65.3** | 70.3 | 67 C RF inhibit / 70 C vendor |

Matched full power closes with 3.2 K margin to the derate threshold at the
45 C design ambient. Sustained full reflection (a fault condition) closes to
40 C ambient; above that the controller ladder (derate 64 C, RF inhibit 67 C,
+50 V removal 68 C) limits duty ahead of the vendor's 70 C limit and 75 C OEM
trip — the same protective posture as V3, now with hardware margin instead of
cooler capacity as the backstop.

Cabin (dry volume), passive rejection through ~0.37 m2 of walls/lid (8.5
W/m2K combined) plus ~0.1 m2 of floor coupled to the fan-washed tunnel (15
W/m2K): **4.6 W/K**.

| Internal load | Rise | Cabin air at 45 C ambient |
|---|---:|---:|
| Design 65 W (25 DIN + 25 solar + 15 leak) | 14.1 K | 59.1 C |
| Max gate 90 W (50 W DIN) | 19.6 K | 64.6 C |

Both below the 70 C DIN-component floor with >=5 K margin. **Cooling-option
comparison for this residual load:**

| Option | Capacity | Input power | Added mass | Verdict |
|---|---:|---:|---:|---|
| **Passive walls (selected)** | 90 W @ <=19.6 K rise | 0 W | 0 kg | Meets budget; zero failure modes, zero cutouts |
| Hoffman TE09 (24 V) | 52 W @ 35/35 | 89 W | 2.7 kg | Growth provision only (>50 W DIN); IP65 caps assembly below IP66 |
| Hoffman TE12 / TE16 | 94 / 166 W | 162 / 295 W | 3.9 / 6.7 kg | Oversized; only relevant to all-inside architecture |
| Seifert 3050303 x4 | 364 W @ 45/55 | 264 W | 13.2 kg | Incumbent V3; rejected with the split |
| Filter fans | ample | ~20 W | ~1 kg | Fails IP66 — rejected |

## 5. Mass / CG (computed by `mass_cg_assessment()`)

| Component | kg | CG-Z mm |
|---|---:|---:|
| Enclosure tub (floor, pad, walls, rim, bosses, panels) | 6.48 | 108 |
| Lid (crowned, counterbored) | 1.86 | 207 |
| Air-tunnel hood + visors, louvers, base flange | 1.15 | 38 |
| Solar shield (lipped) | 1.18 | 222 |
| Clamp bars / cradle / duct sheet | 0.74 | — |
| DIN panel + rail | 0.58 | 147 |
| Mesh screens (304 SS) | 0.26 | 43 |
| AM59 chassis / heatsink+fans | 1.35 / 1.15 | 109 / 50 |
| Future DIN allocation | 2.50 | 145 |
| Hardware, gaskets, TIM | 0.60 | 120 |
| **Total** | **17.8** | **CG (5, 56, 123)** |

CG moment about the base plane: **2.19 kg·m** (V3: ~6.1). Wind areas
(bounding-box, incl. visors and shield): frontal 0.086 m2, side 0.123 m2; at
a 50 m/s survival gust the side drag is ~230 N acting ~123 mm up →
~28 N·m overturning moment at the rotator plane. Mass-reduction options if
needed: thin the non-pad floor to 5 mm and the lid base to 3 mm (-0.7 kg),
delete the shield where shaded (-1.2 kg).

## 6. Airflow / heat-flow design

- Fans draw through the -X mesh + visor, force air through the 44 ducted fin
  channels (duct sheet closes the open fin tips), exhaust through +X. Both
  apertures exceed the 180 x 60 mm fan-bank free area; plenum depths are 25
  mm (inlet) and 70 mm (exhaust).
- The tunnel is orientation-tolerant to wind: both ends are equivalent, and
  the fans only ever see hood-sheltered air. The open bottom provides
  drainage, make-up air, and cleaning access; the fin field is reachable for
  washdown without opening the dry volume.
- Qualification measures installed fan operating points (not free-air
  ratings) and correlates a production pressure/flow limit — same discipline
  as V3, but with one fan bank instead of interacting cooler loops.

## 7. Sealing details (IP66 target)

- **Cold floor:** continuous metal, zero penetrations. All fasteners engage
  blind bosses (clamps inside, cradle outside).
- **Lid:** single continuous gasket in a machined rim groove; 28 M5 captive
  screws outside the seal line at <=58 mm pitch; hard stops set compression;
  production lid crowned 2-3 degrees for drainage. Rim inserts are
  replaceable and blind.
- **Walls:** welded 5052 tub (or machined monolithic), continuous seams only;
  chromate + white polyester powder; gasket and bond lands masked.
- **Deliberately absent this revision** (per requirements): connector ports,
  RF feedthroughs, pressure vent, mast/rotator interfaces. Note: the vent is
  *mandatory* before sealed qualification — a 0.03 m3 sealed volume swinging
  ~60 K breathes several kPa; the blank walls reserve area for an IP68/IP69K
  vent and the +X feedthrough panel.
- Wet zone contains only anodized/coated aluminum, 304 mesh, and the OEM
  fans; fan environmental rating is a vendor gate (drop-in IP68 60 mm fans
  are the identified fallback).

## 8. Preliminary BOM

| Qty | Item | Status |
|---:|---|---|
| 1 | AM59-3S-64-64, **modular (heatsink-less) configuration** | Vendor gate 1 |
| 1 | OEM fin/fan stack as loose kit, or released OEM-equivalent heat sink | Vendor gate 2 |
| 1 | Welded 5052 tub, 446 x 356 x 132, with 330 x 190 x 10 machined cold pad and 6 blind clamp bosses | Concept geometry complete |
| 1 | 4 mm lid, 28 captive M5 + blind rim inserts | Concept geometry complete; gasket gland open |
| 1 | Continuous EPDM lid gasket | Supplier data open |
| 2 | Flange clamp bars + hardware | Concept complete; preload calc open |
| 1 | Heatsink cradle (2 rails, 4 pillars) + blind-boss hardware | Concept complete |
| 1 | 1.5 mm fin duct sheet | Concept complete; edge sealing detail open |
| 2 | 1.0 mm >=3 W/mK TIM pads, 320 x 180 | Vendor-approved type open |
| 1 | Hood skirt with 2 sloped visors | Concept complete |
| 2 | 304 stainless mesh screens | Concept complete |
| 1 | DIN panel + 300 mm EN 60715 rail | Concept complete |
| 1 | Standoff solar shield | Concept complete (optional) |
| 1 | Pressure-equalization vent | **Deferred by requirement; mandatory pre-qualification** |
| — | Feedthroughs, mast adapter, rotator hardware | Deferred by requirement |

ROM hardware cost $2.0-2.6 k (machined/welded tub dominates) versus ~$7-9 k
for the V3 cooler-based boundary — and no 24 V / 20 A cooler supply in the
support equipment.

## 9. Qualification sequence

1. **Vendor data closure** — modular interface drawing, TIM approval, fan
   curves, fan environmental rating, case-sensor definition, clamp approval.
2. **Dimensional** — CMM the pad both sides (0.05 mm/100 mm flatness), boss
   heights (TIM stop), rim flatness; verify amp lift-out through the lid
   opening.
3. **Thermal correlation** — 200 W calibrated heater block on the pad (before
   amp availability): verify interposer ~2.7 K at 200 W and sink resistance;
   then amp-powered matched (125 W) and severe (200 W) corners at 45/40 C
   with solar lamp; verify the 64/67/68 C ladder and OEM 75 C backstop; map
   cabin air at 90 W internal budget.
4. **Airflow** — installed fan operating points, tunnel pressure/flow limit,
   adverse-wind (all azimuths) and blocked-screen degradation.
5. **Ingress** — IP6X dust, then IPX6 jets on the populated assembly (with
   temporary sealed blanks where ports are deferred); witness inspection.
6. **Environment** — condensation cycling across dew point (cold-soak the
   floor), salt fog on the wet zone, UV/coating adhesion, gasket compression
   set, thermal cycling with breathing-vent surrogate.
7. **Mechanical** — mast/rotator vibration and shock spectrum (gate), clamp
   preload retention, cradle load path, bond/ground continuity.
8. **Weigh and swing** the complete assembly; confirm mass <=18 kg and CG
   within the computed envelope before rotator loading release.

## 10. Assumptions and unresolved vendor-data gates

Assumptions: modular variant has a flat conduction base at the fin-root
plane; heatsink/fan mass split 1.15/1.35 kg of the 2.5 kg nominal; sink
resistance 0.105 K/W; 45 C design ambient; future DIN load <=50 W at >=70 C
rating; white finish solar allocation 25 W.

Gates (blocking fabrication release):

1. Modular AM59 availability, interface drawing, approved TIM, and warranty
   with third-party cooling (**the** architecture gate — fallback is
   Architecture A on the same tub).
2. OEM heatsink/fan kit as loose parts or equivalent-design release against
   vendor fan curves; calorimetric sink verification.
3. Fan IP/salt/life rating in the hooded wet zone, or approved IP68
   substitution.
4. Vendor case-measurement point for the 70 C limit; reverse-power
   termination location under severe duty.
5. Flange-clamp and vibration-environment approval.
6. Gasket gland data, rim inserts, vent selection (deferred), DIN component
   list, bonding scheme.

Until these close, this is an engineering packaging and test definition —
not an IP certification or production drawing.
