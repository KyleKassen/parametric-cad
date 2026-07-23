# OZ51x Housing Family — Design Requirements

Dimension-free requirements for the three Zonu OZ51x module enclosures. This
is the document you would hand an engineer (or an AI) to recreate these
housings from scratch. **No dimensions appear here on purpose**: every number
must be derived from the vendor STEP files (`parts/vendor/zonu-oz510-*`) via
`lib/analyze_step.py`, or from the vendor datasheets stored in the relevant
part's `datasheets/` folder. Current derived values live in each variant's
`params.json`; the shared geometry builder is this directory's `model.py`.

## 1. Product definition

Three variants, one parametric builder — a variant is a `params.json`, never a
fork of the model code:

| Variant | Bay A | Bay B | Rear signal connector |
|---|---|---|---|
| `oz510-dual-housing` | RF receiver | RF transmitter | none (front wiring slots) |
| `oz51x-dual-tx-housing` | RF transmitter | TTL transmitter | yes |
| `oz51x-dual-rx-housing` | RF receiver | TTL receiver | yes |

The TX and RX electrical variants also have narrow, vertically stacked layout
options in `oz51x-dual-tx-housing-vertical` and
`oz51x-dual-rx-housing-vertical`. They inherit their electrical variant's
parameters and use the same shared builder. The canonical tray is turned onto
its side so the two bays stack upward and the removable top becomes a side
service cover; rear connector footprints are counter-rotated so SC/APC flange
screws and the DE-9 long axis remain horizontal. The module screws provide
positive retention because the module plates no longer rest in the gravity
direction.

Production-refined derivatives live in
`oz51x-dual-tx-housing-vertical-gpt-5-6-sol` and
`oz51x-dual-rx-housing-vertical-gpt-5-6-sol`. They use the same inherited
interface data and builder, enabling an additive-manufacturing refinement mode
for radiused shells, tapered boss roots, lightened/flanged fiber storage,
cable saddles, baffled ventilation, gravity drains, assembly lead-ins, and a
stiffened service cover. These additions must remain outside every original
module, connector, fiber, screw, and harness keep-out.

Each housing is a two-bay open-top base tray plus a removable screwed-down
lid, holding two Zonu OZ51x-family modules side by side in the canonical
layout, plate-down. A vertical-stack layout may turn that complete architecture
onto its side as described above. Per
module the housing must expose:

- its **SMA connector** through the front panel,
- its **fiber pigtail** as an external **SC/APC bulkhead port** on the back
  panel (a panel-mounted SC/APC simplex adapter; the factory pigtail plugs
  into it from inside, the field cable from outside),
- its **10-pin header signals** — via open front wiring slots on the original
  variant, or consolidated into one rear panel connector (DE-9 class) on the
  TX/RX variants.

Intended fabrication: FDM/SLS print or 3-axis mill. Intended fasteners:
thread-forming screws into printed pilot bores (no inserts assumed).

## 2. Ground rules for deriving geometry

1. **Never hand-measure and never trust a datasheet drawing when a STEP
   exists.** Import the vendor B-rep, query it analytically
   (`lib/analyze_step.py`), and drive every module-related dimension from
   that analysis. Datasheets are the source only for parts with no STEP
   (SC adapter, SC connector, panel connector — see §8).
2. **Analyze every vendor file individually; verify handedness per
   feature.** The transmitter is a mirror of the receiver *only for the front
   I/O* (SMA and header swap sides). The fiber exit on the can's back is
   **not mirrored** — both modules exit at the same module-local X. Bounding
   boxes, volumes, and radius histograms are mirror-blind; only feature
   *positions* reveal this. Any per-bay handedness flag must therefore apply
   to the front I/O cutouts and the module screw bosses, and must **not**
   apply to fiber features. Assume nothing about symmetry that the analysis
   has not confirmed.
3. **Inspect the module's underside and hole occupancy before using any
   hole.** Specific traps this family already hit:
   - The four **corner holes of the baseplate are occupied** by vendor
     press-fit PCB standoffs, whose hardware also protrudes below the plate.
     They cannot take screws, and supports placed under them rock the module.
   - The only free holes are the **three small through-plate holes**: a
     close-spaced pair near the SMA (mirrored on the TX) and one on the back
     centerline. Of the front pair, only the inner one has clear space
     beneath it — the outer sits over the SMA's under-plate body.
   - The **SMA's rectangular base block overhangs the plate's front edge**
     by more than a typical end-clearance, so the front wall needs a local
     relief pocket around the SMA hole or the module cannot seat.
   - Several components protrude below the plate; supports must land on
     verified-bare plate regions only.

## 3. Module retention

- Modules rest plate-down on **pilot-less support studs** (four per bay)
  positioned near the plate corners but offset onto bare plate (see §2.3),
  and are **retained by two screws per module** through the free plate holes
  into bossed pilot bores. Choose the screw size from the free holes'
  diameter; pilot depth must give full thread engagement for an
  off-the-shelf screw length (drill into the floor, leaving a web).
- Stud height must exceed the deepest under-plate protrusion (pins,
  hardware) so nothing touches the floor.
- The two bays share no hardware assumptions: each bay's screw-boss
  placement follows that bay's handedness flag.

## 4. Fiber subsystem

- Each module's pigtail exits the back of its can and terminates in a
  factory-installed SC/APC connector that **cannot be removed or shortened**;
  the housing must store the full slack (assume on the order of a meter of
  0.9 mm fiber).
- Behind the module bays, add a full-width open-top **fiber plenum**. The
  former back wall survives as an internal partition with a **top-open
  pass-slot** above each fiber exit — top-open because a module must drop
  into its bay *with its pigtail already attached*.
- Slack storage: a central **spool post** whose radius equals the enforced
  minimum fiber bend radius (use a conservative figure for 900 µm buffered
  fiber). The spool should double as a lid support/screw post.
- Back panel: one **SC/APC simplex adapter mount per bay** — a rectangular
  body cutout plus flange screw pilots, adapter inserted from outside. Two
  consequences to respect:
  - The adapter's snap clips are sized for thin sheet panels; a printed wall
    is thicker, so retention comes from the flange screws (documented, not
    accidental).
  - The adapter's flange is longer than the panel is tall — mount the
    adapter **long-axis horizontal**.
- **Mated-connector corridor:** behind each adapter, reserve a straight
  keep-out for the adapter's inner protrusion plus the mated SC connector
  and boot (derive from the connector datasheet; note a 2–3 mm-jacket
  connector is much longer than a 0.9 mm-pigtail one and does not fit —
  state which is supported). Plenum depth is driven by this corridor, and
  nothing (spool, posts, connector keep-outs) may intersect it.
- Adapter axis height should match the fiber exit height derived from the
  module analysis.

## 5. Signal wiring

- Only the **odd pins** of each module's 10-pin header carry signals (all
  evens are N/C; receivers also leave the enable pin N/C) — see the Zonu RF
  and TTL datasheets. A whole two-module housing therefore needs at most
  eight conductors plus spares, which is why a **9-pin D-sub class panel
  connector** is sufficient and preferred over bare wire pass-throughs.
- Variants with the rear connector:
  - Mount it in the **back panel** between the SC ports (the front panel has
    no interior depth behind it — modules sit almost against it).
  - Reserve a rear keep-out for the connector shell, solder cups, and wire
    bend; deepen the plenum and bias the spool forward to create it.
  - Route the harness from each header **over the can top and down the
    partition pass-slot** (widen the slot to share fiber + wires). The lid
    must leave wire headroom over the can everywhere the harness runs — a
    solid registration lip pad does not (see §6).
  - No front wiring slots on these variants.
  - Keep the connector pin map **identical across TX and RX variants** so a
    single cable design serves both ends of the link; document the map in
    params notes.
- The original variant keeps per-bay open wiring slots in the front panel,
  on each bay's header side (handed).

## 6. Lid

- Flat lid over the full footprint (or full side service opening on a vertical
  stack), screwed to: posts along the central rib,
  the fiber spool, and posts in the plenum's back corners. Screw heads
  counterbored flush.
- **Registration lip constraints** (each earned by a real bug):
  - The lip must nest into the bay cavities only — a single full-interior
    lip collides with the central rib, its screw posts, and the partition,
    and the lid cannot seat. Verify lid∩base ≈ 0 explicitly.
  - Rib-side screw posts bulge into the bay cavities; scallop the lip
    around them.
  - On internal-wiring variants the lip must be a **perimeter ring with a
    gap over the pass-slot**, not a solid pad — a solid pad leaves ~a wire's
    thickness over the can top and pinches the harness.
  - No lip over the plenum: a narrow-gap edge there can pinch a fiber wrap
    against the wall.
- Access openings directly above each header block (handed) so the harness
  can be plugged with the lid on.

## 7. Verification obligations (non-negotiable)

Every variant must pass all of these; they exist because each caught (or
would have caught) a real defect in this family's history:

1. **Per-feature probe tests, handedness-aware**: push probe solids through
   every cutout (SMA, wiring slot, fiber pass-slot, adapter body + screw
   pilots, panel connector + jackscrews) and assert no wall material. An
   overall interference number passes with a wrong-sided cutout; per-feature
   probes do not (the v1 mirrored-TX bug).
2. **Real-geometry fit check**: place the actual vendor STEPs (per
   `bays[].step`) and the adapter/connector stand-in models into the housing;
   assert near-zero intersection with a **tight threshold** — a "small
   acceptable" overlap of a few mm³ turned out to be the SMA base bearing on
   the front wall.
3. **Presence tests**, not just absence: screw bosses exist under the free
   holes with open pilot bores; studs sit clear of the occupied-corner
   hardware footprint.
4. **Lid seating** (lid∩base ≈ 0) and, on internal-wiring variants, **wire
   headroom** over the can inside the lip ring.
5. **Corridor / keep-out clearance** for mated SC connectors and the panel
   connector's rear volume; spool radius ≥ minimum bend radius.
6. **Envelope check** against the computed layout.
7. **Visual verification**: regenerate the fit renders (open + closed, incl.
   top and back views) and actually look at them — numeric checks plus
   renders together, never one alone.

## 8. Assumption registry (verify before committing hardware)

- **TTL modules have no STEP files.** They are assumed mechanically
  identical to the corresponding RF modules based on datasheet photographs;
  the TTL bays borrow the RF STEPs for fit checks. Verify with a real TTL
  unit.
- **SC/APC adapter and SC/APC connector models are datasheet-derived
  stand-ins** (`parts/vendor/sc-apc-*`), not vendor CAD. Check the ordered
  parts' datasheets against their params before printing.
- **Panel connector dims are the industry-standard DE-9 footprint**; verify
  against the ordered connector.
- Module analyses derive from vendor STEPs, not measured units — confirm a
  real module against the analysis before first fabrication.

## 9. Repo conventions that apply

- Parameters in `params.json` (data) separate from geometry logic in
  `model.py` (code); versions bump in params and never overwrite old
  exports. Variants share this directory's builder via thin wrappers.
- Vendor material lives under `parts/vendor/<part>/` with datasheets,
  analyses, and derived reference renders; custom parts under
  `parts/custom/`.
- Document every discovered trap in params `notes` (with version history)
  and keep tests pointing at the incident they guard against.
