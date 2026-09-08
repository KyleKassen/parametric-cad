# ADRS maritime layout, compact — Saginaw SCE-20H2010LP interior (v3)

Same enclosure and the same six components as
[`adrs-maritime-layout`](../adrs-maritime-layout/DESIGN_NOTES.md), packed tighter to make
room for two more devices and a DIN rail:

* **Brainboxes ES-511** — Ethernet-to-serial, on the rail.
* **Advanced Navigation Certus Mini D** — dual-antenna INS, on a solid pedestal.
* **290 mm of TS35 rail** bolted flat to the subpanel, with the ES-511 on it and about ten
  module widths spare — six of them clear to the full 99 mm module height, the rest good
  for ordinary 45–60 mm accessories. See *Spare capacity, honestly* below.

The two Zonu OZ510 transmitters from the SolidWorks assembly are represented by our own
`oz51x-dual-tx-housing-vertical-gpt-5-6-sol`, which contains both of them.

```bash
uv run python parts/custom/adrs-maritime-layout-compact/make_placement.py
uv run python parts/custom/adrs-maritime-layout-compact/layout.py --drawings --export --render
```

> **Environment note.** In this OneDrive checkout the in-tree `.venv` cannot import OCP —
> `ImportError: DLL load failed while importing OCP: The filename or extension is too long`.
> The path to `OCP.cp311-win_amd64.pyd` is 225 characters before Windows adds its own, which
> overruns MAX_PATH inside the DLL loader. It is not specific to this part; nothing in the
> repo will run from here until the venv lives somewhere shorter:
>
> ```bash
> UV_PROJECT_ENVIRONMENT=C:/venvs/cadquery uv sync --all-extras
> ```
>
> The layout above was built and verified against an existing short-path environment.
> `layout.py` also now takes its STEP cache directory from `ADRS_STEP_CACHE` instead of the
> hard-coded scratch path v2 carried, defaulting to `~/.cache/adrs-stepcache`.

## Getting it into SolidWorks

**The default export path does not work here.** This repo sits 173 characters deep, so
`exports/adrs-maritime-layout-compact_v1.step` comes out at **exactly 260 characters** —
one over the Win32 `MAX_PATH` of 259 plus terminator. SolidWorks still uses the legacy API
regardless of the `LongPathsEnabled` registry key, so it reports the file as *"invalid, not
found, locked or of an incompatible type."* The STEP itself is fine; only the path is.

Export somewhere short instead:

```bash
# just our metal — brackets, rail, end stops, 62 fasteners. ~2 MB, opens instantly.
uv run python parts/custom/adrs-maritime-layout-compact/layout.py --export \
    --scaffold-only --out C:/ADRS-CAD

# everything, including the vendor models and the Saginaw shell. ~320 MB.
uv run python parts/custom/adrs-maritime-layout-compact/layout.py --export --out C:/ADRS-CAD
```

`--scaffold-only` is the one to use day to day. Every vendor model in the full export is
already in the SolidWorks assembly, and dropping them takes the file from ~320 MB — which
SolidWorks will chew on for a long time — to a couple of megabytes.

**Everything is written in the Saginaw SCE-20H2010LP STEP's own frame**, so insert the
scaffold at the assembly origin and fix it; it lands correctly against the enclosure and
every device you already have placed. No re-datuming, no mates to guess at.

`layout.py` warns before writing if the destination path would exceed 258 characters, and
`exports/` deliberately holds no STEP — anything written there is unopenable from this
checkout. Both files currently sit in `C:\ADRS-CAD\`:

| File | Size | Contents |
|---|---|---|
| `adrs-maritime-layout-compact_scaffold_v1.step` | 1.7 MB | 21 fabricated/purchased members + 62 fasteners, 83 solids |
| `adrs-maritime-layout-compact_v1.step` | 327 MB | the above plus all 8 devices and the Saginaw shell |

The scaffold file re-imports as 83 named solids spanning X −182…210, Y −215.9…200.7,
Z −122.7…83.8 (the Z minimum is the subpanel bolts standing proud behind the panel).

| File | What it is |
|---|---|
| `interfaces.json` | Measured mounting holes + connector keep-outs for all 8 components, in each part's own frame. The source of truth. |
| `make_placement.py` | Layout decisions. Pulls holes out of `interfaces.json` — never retypes them. |
| `placement.json` | Generated. Do not hand-edit. |
| `layout.py` | Places, drills, fastens, verifies, exports. |
| `model.py` | Scaffold primitives, including the TS35 rail section. |
| `exports/plates/*.dxf` | 1:1 flat patterns, outline + holes. |
| `exports/subpanel_drilling.csv` | The holes to put in the 431.8 mm subpanel. |

## Coordinate frame

Unchanged from v2 — Saginaw's own STEP frame, so imported geometry needs no re-datuming:
**X** = width ±252.09 · **Y** = height ±252.10, **+Y up** · **Z** = depth, **+Z toward the door**.
Subpanel mounting face **Z = −109.22**; door inner clear **Z = +131.10**; 240.3 mm of stack depth.
Four subpanel corner collars stand proud to Z = −100.69 at (±193.68, ±193.68).

Two mounting planes now, not one:

* **Z = −97.22 … −94.22** — the 12 mm standoff plane every bracket sits on, which clears
  the corner collars.
* **Z = −109.22** — the subpanel face itself, used by the DIN rail (7.5 mm tall) and the
  INS pedestal (8 mm). Both live *inside* the 12 mm gap the rest of the scaffold stands
  on, so they cost no depth at all. They are both far from the corner collars.

## Did it actually get tighter?

Both placements were run through the same engine and the same metric. A bounding box
around everything is a bad score — adding one device in a corner moves it 100 mm without
the layout getting any fuller — so this rasterises the real XY silhouette twice: once for
metal, once for metal **plus every declared connector, vent and service keep-out**, since
a cable volume is just as unavailable as the box it plugs into.

| | v2 | v3 compact |
|---|---|---|
| Components | 6 | **8** |
| Placed items (incl. scaffold) | 22 | 29 |
| Hardware footprint | 1027 cm² (55%) | 1069 cm² (57%) |
| Committed, keep-outs included | 1250 cm² (67%) | 1257 cm² (67%) |
| Largest free rectangle | 154 × 96 mm | 204 × 38 mm |
| Stack depth used | 193 mm | 193 mm |

**Two more devices, 290 mm of DIN rail and two end stops for +42 cm² of hardware and
+7 cm² of committed panel** — four tenths of a percentage point. The depth budget did not
move either: 193 mm of 240 mm, same as before, because the B210 blade is still shallower
than the UBR blade that already set that number.

What it cost is elbow room: the biggest empty rectangle went from 154 × 96 to 204 × 38.
The panel is genuinely full now, and the growth path is deliberately the rail rather than
bare panel.

## What made room for two more devices

### 1. The B210 was stood on edge

This is the whole trick. The B210's only fixing face is its 117 × 150.7 mm base sheet, and
that face works exactly as well vertical as horizontal. Laid flat it is a **122 × 178 mm**
footprint 37 mm deep; stood up it is a **37 × 178 mm** footprint 122 mm deep. The enclosure
had 240 mm of depth and was using 193, so the depth was free and the width was not.

That single change returns 85 mm of panel width — which is what the rail column is made of.

### 2. The measured TEC plenum turned out to be much smaller than "the left strip"

v2 reserved everything left of X = −111.05 across the cooler's whole height. Running the
real keep-out through the transform gives a prism of
**X[−167.05, −111.05] × Y[−20, 100] × Z[−60, 60]** — the Ø120 intake grille plus 50 mm,
and nothing more. The cooler *body* still owns everything left of X = −161.05 between
Y = −112.34 and Y = +192.34, but below and above that band the panel is full width, and in
front of the intake only the middle third is actually reserved.

### 3. The UBR dropped 28 mm and the Bedrock 10 mm

Which frees the top band of the panel for the rail. The UBR cannot go lower: its cellular
SMA bank wants 55 mm and the keep-out band sits at Z −40…+57, exactly where the PSU's
85 mm of depth is.

## Placement

| Item | X | Y | Z | Mount |
|---|---|---|---|---|
| TE12 cooler | −343.4…−161.1 | −112.3…192.3 | −80.1…79.4 | left wall, 6× M6 on 142 × 286, cutout 125 × 232 |
| NSP-1600 | −180.0…158.6 | −195.0…−154.0 | −94.2…−9.2 | 3× M3 into `psu_shelf` |
| Bedrock V3000 | −108.0…−35.0 | −150.0…20.0 | −94.2…38.8 | 2× M3 into `bedrock_spine` + 1× M4 into `bedrock_shelf` |
| UBR Plus | −5.0…24.3 | −70.0…96.2 | −94.2…77.6 | 4× M4 through its cast flange into `ubr_bracket` |
| OZ51x dual-TX | 45.0…178.5 | −134.0…−41.8 | −94.2…−61.5 | clamped to `oz51x_cradle` by two hold-down clips |
| Ettus B210 | 81.3…118.6 | 20.0…197.6 | −94.2…28.1 | **on edge**, 4× M3 into `b210_bracket` |
| TS35 DIN rail | −105.0…185.0 | 142.5…177.5 | −109.2…−101.7 | 7× M5 straight into the subpanel |
| Brainboxes ES-511 | 150.0…172.6 | 110.5…209.5 | −108.3…6.1 | clipped to the rail, captured by two end stops |
| Certus Mini D | 165.0…195.0 | 26.0…72.6 | −101.2…−67.2 | 4× M2 into `certus_pedestal` |

## The DIN rail

**TS35 / EN 60715, 35 × 7.5 × 1.0, 290 mm long, centreline Y = +160**, bolted flat to the
subpanel. Not raised on standoffs: it needs the depth back, it is nowhere near the corner
collars, and a rail on standoffs is a spring.

Seven M5 stations at 45 mm pitch: **X = −95, −50, −5, 40, 85, 130, 165**. They dodge both
end stops (X 139…149 and 172.6…182.6), whose clamp bodies sit *on* the rail and would rock
on a screw head. The one at X = 165 lands under the ES-511 instead, which is fine — that is
exactly the case the head-height limit exists for.

> **The rail screws must be pan or countersunk head, 3.5 mm maximum.** A device clip
> reaches 3.5 mm into the rail channel and an M5 socket head is 5.0 mm tall. This is the
> one detail on the whole rail that will bite if it is missed.

### How the ES-511 actually mounts

The part has **no fastener features of any kind** — not one hole. The rail is the mount, so
the rail geometry had to be reverse-engineered from the clip jaws rather than looked up:

* a flat back plane at part Y = −55.5 (947 mm²) that lands on the rail lips;
* a **fixed jaw** at part X 16.00…38.84 reaching to Y = −59.5 — 4.0 mm behind the bearing
  plane, hooking 1.5 mm in under the +X lip;
* a **sliding release jaw** at part X −45.30…−15.30 reaching to Y = −62.1 — 6.6 mm behind,
  hooking 2.2 mm under the −X lip. Pull it toward part −X to release.

Both are consistent with — and only with — a 35 mm rail centred on part X = 0 whose lip
faces lie at Y = −55.5. That puts the panel at part Y = −63.0 and makes the module's
projection from the subpanel **115.3 mm**, of which 0.9 mm is the clip nesting inside the
rail hat. Placed, it occupies Z −108.3…+6.1 and the RJ45 wants 45 mm more, to Z ≈ +51.

Orientation follows from the rail being horizontal: the module's louvred faces end up
**up and down**, which is the way the vendor intended, and the RJ45 and both 5-way screw
terminals face **straight at the open door**.

### Spare capacity, honestly

290 mm of rail is about **12 module widths** at the usual 22.5 mm pitch. The ES-511 takes
one and the two end stops take another between them. What is left is not all equal:

* **X −105 … −5 (≈ 4 slots)** — clear to the full 99 mm module height. Nothing above the
  Bedrock reaches this band.
* **X 24 … 44 and X 119 … 139 (≈ 1 slot each)** — clear to full height, short runs.
  That is six full-height slots in total.
* **X −105 … 44 and X 119 … 139 (≈ 7 slots)** — clear for ordinary 45–60 mm DIN accessories
  (terminal blocks, fuse holders, a relay, a small managed switch), which do not reach far
  enough across the rail to meet the B210's bracket flange or the UBR's port-bank
  clearance.

Anything mounted between **X 44 and X 119** must stay below Z = −97.2 or it meets the B210
bracket. Nothing may be hung over the corner collars at (±193.68, ±193.68), which stand
proud to Z = −100.69 — the rail itself stops well short of them.

## The INS mount

The Certus Mini D's base (part −Y, 30 × 41 mm, 1143 mm² of metal) is **both its only fixing
face and its alignment datum**, so whatever it bolts to defines the INS axes. It gets a
**solid 8 mm 6061 pedestal bolted straight to the subpanel**, not 3 mm plate on standoffs —
an INS is only as good as its mount stiffness, and the pedestal costs nothing because it
fits inside the 12 mm gap everything else stands on.

* 4× **M2** clearance (Ø2.200) on a **26 × 37** rectangle, tapped into the pedestal. M2 is
  what the part offers; there is nothing bigger on it.
* The corners above the flange are scalloped R4.0, which is how a driver reaches the heads.
* The four M5 pedestal bolts sit 8.3 mm from the nearest M2 centre, against the
  6.2 mm the two head radii need.
* Connectors (2× GNSS SMA, 1× circular data/power) exit the part's +Z face, which lands
  facing **−Y** here, into the open lane above the OZ51x's fibre side.

Sited in the one column of the panel with no tall neighbour, clear of the TEC plenum and
about 180 mm from the NSP-1600.

## Fabrication

Everything is 3 mm 6061 plate, saw + drill + brake, except the INS pedestal, which is a
sawn 8 mm block, drilled and tapped. Purchased: one 290 mm length of TS35 rail and two
screw-clamp rail end stops.

Flat patterns are in `exports/plates/`, the subpanel drilling schedule in
`exports/subpanel_drilling.csv`.

## Assembly notes

Everything from v2 still applies:

1. **Peel the four adhesive rubber feet off the B210** — they are concentric with its
   mounting bores and it cannot seat without removing them.
2. **Bedrock screw depth is 3.0 mm maximum** into the back wall (2.515 mm of thread).
3. **B210 screw penetration 3.574 mm maximum** — the internal PCB screw tip is right behind.
4. **NSP-1600 max 4 mm** into the chassis bottom.
5. The OZ51x is **clamped, not bolted** — it has no fixings. Torque the clips to just nip
   it; it is a printed part. Keep both drain outlets clear.
6. Shroud the NSP-1600's **bare ±Vo busbar blades** — 38 mm of exposed DC at +X.

New for v3:

7. **Rail screws pan or countersunk, 3.5 mm head maximum** (see above).
8. **Fit both DIN end stops.** A clip alone is not a shock mount and the ES-511 is 99 mm of
   cantilever hanging off one.
9. **Build the B210 bracket before the OZ51x cradle goes on** — its flange runs down the
   lane between the UBR and the OZ51x and there is 4 mm of clearance either side.
10. **The INS pedestal defines the vehicle axes.** Decide which way the Certus's part +X
    points before it is bolted down, and record it.

## Open items

Carried over from v2:

1. **Which Bedrock chassis?** The vendor STEP superimposes three mutually exclusive
   enclosures at one origin — Tile (29 mm), 30 W (45 mm), 60 W (73 mm). This reserves the
   73 mm / 60 W worst case.
2. **B210 bores tapped or clearance?** Modelled as Ø2.90 unthreaded.
3. **NSP-1600 hole positions are derived, not re-measured.** Verify before drilling
   `psu_shelf`.
4. **NSP-1600 variant (12/24/36/48 V)** — geometry identical across the series.
5. **Condensate pan** (TEC100WCMSS4, 159 × 64 × 19) not modelled; space is reserved.
6. **A better OZ51x mount exists.** We own that part; two mounting ears on its −X face
   would replace the clamp with a bolted joint.

New:

7. **Confirm M2 with Advanced Navigation**, and get a torque figure, before any vibration
   qualification. Ø2.200 clearance is what the model shows but the datasheet is not in hand.
8. **INS heading reference.** This is the dual-antenna "D" variant so heading does not rely
   on a magnetometer, which is why 180 mm from the NSP-1600 is acceptable. If a Mini
   *without* dual antenna is ever substituted, this position needs re-thinking.
9. **ES-511 terminal-block wire gauge.** 30 mm of bend allowance is assumed off the two
   5-way blocks; confirm against the loom.
10. **Vertical rail?** Not used here, and it would put the ES-511's louvres on their side.
    If a future module count forces a second rail, keep it horizontal.

## Thermal budget

| Source | W |
|---|---|
| Bedrock V3000 (60 W finned variant) | 60 |
| NSP-1600 conversion losses | 40 |
| Peplink UBR Plus | 25 |
| Ettus B210 | 15 |
| Two Zonu OZ51x TX modules | 10 |
| Brainboxes ES-511 | 3 |
| Certus Mini D | 3 |
| **Total** | **≈156** |

The TE121024010 removes **94 W at ΔT = 0**, ~147 W at ΔT = +15 °C, so the conclusion from v2
is unchanged and now 6 W worse: **the TE12 is undersized.** The TE162024020 (200 W) is
already in `parts/vendor/Hoffman/` and fits the same wall (400 × 180 against 504 × 256
available, same ~89 mm intrusion); it needs the PSU shifted ~10 mm right and a 155 × 352
cutout, 6× Ø6 on 168 × 300. Nothing in this layout depends on which of the two is fitted —
the plenum reservation is sized for the larger one's intake.
