# MEAN WELL NSP-1600 — vendor STEP

`NSP-1600_0417.stp`, as shipped by MEAN WELL. Purchased part: we fabricate nothing here.
It lives in the repo so mounts can be cut against exact vendor B-rep instead of
transcribed numbers. The datasheet (2026-06-15) and the enclosed-type installation manual
are in `datasheets/`, decrypted so tooling can read them.

```bash
C:/venvs/cadquery/Scripts/python.exe -m lib.analyze_step "parts/vendor/meanwell-nsp-1600/NSP-1600_0417.stp"
C:/venvs/cadquery/Scripts/python.exe -m lib.render_step  "parts/vendor/meanwell-nsp-1600/NSP-1600_0417.stp"
```

## Frame (the vendor's own)

**X** across the unit, 24.287…109.287 · **Y** along it, fan guard at 53.552, terminal
plate at 354.15, blade tips at 392.152 · **Z** up, bottom face at 1.5, cover at 42.5.
Body **85.000 × 300.598 × 41.000**; datasheet says 300 × 85 × 41 (±0.5).

Mounts use this frame translated by **(−66.787, −354.15, −1.5)** — bottom-face centre at
the terminal plate — because the datasheet's hole dimensions then read off directly.

## What each face is

| Face | What it is | Mount to it? |
|---|---|---|
| **−Z bottom** | flat steel, 21 819 mm² shell + 630 mm² fan bracket, nothing proud | **yes** — 3× M3 |
| **±X sides** | flat 1.2 mm walls, only flush countersunk vendor screws; **no vents** | **yes** — 2× M4 each |
| **+Z top** | removable cover, 24 462 mm², zero holes | no fixings; may be strapped, never drilled |
| **−Y fan end** | two 40 × 40 × 28 fans behind a guard. **Exhaust.** | never — keep 60 mm clear |
| **+Y terminal end** | 14 intake louvres, AC terminal block (proud 8 mm), two 2 mm DC blades proud **38 / 28 mm** with Ø6.5 lug holes, CN1/CN2 headers, LED, trim pot | never — intake, live parts, cables |

Air: **in at the terminal-face louvres, out through the fans** (datasheet arrow).

## What you can actually bolt to

Measured with axial and ring probes; see `references/NSP-1600_0417_analysis.json`.

| | Where (vendor frame) | Measured | Datasheet |
|---|---|---|---|
| **3× M3×0.5** | bottom, (31.787, 338.052), (101.787, 338.052), (66.787, 73.352) | extruded holes, minor Ø2.65, ~2 mm of thread; PCB underside 4.5 mm above the face | M3, **L = 4 mm max**, 6–8 kgf·cm |
| **2× M4×0.7 per side**, terminal end | (Y 348.352, Z 24.3), both walls | Ø4.54 threaded cross-tube (minor Ø3.1) right across the width — **real** | M4, **L = 5 mm max**, 7–10 kgf·cm |
| **2× M4×0.7 per side**, fan end | (Y 96.352, Z 24.3), both walls | **Ø5.0 clearance opening, nothing behind it** — the thread is not in the file | same |
| ~~2× Ø2.8 per side~~ | (Y 348.352 / 96.352, Z 18.3) | vendor assembly features | not fixings |

The side M4 pattern is what MEAN WELL's own bracket kit (PGG2MHS013A, "M4×4 combination
screw") hangs the unit from, so it is a load-bearing pattern by the vendor's own use. But
**run a screw into the fan-end holes on a real unit** before a design depends on them.

## Qualified attitude

**Horizontal only.** The derating curve is labelled *(HORIZONTAL)* and no other curve is
published. The installation manual (item 3): other orientations "will require a
de-rating in output current" and refer you to the spec sheet — which has none.

## Mass and qualification

1.8 kg. Vibration 10–500 Hz, 2 G, 60 min per axis. −20…+70 °C, full load to 50 °C.
