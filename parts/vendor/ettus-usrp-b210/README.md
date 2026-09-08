# Ettus USRP B210 — vendor model

`Ettus_USRP_B210_Full_Unit.step` as shipped. Purchased part; nothing here is
fabricated. Copied in from `~/Documents/Projects/ADRS/CAD/Ettus/` so that parts
which mate to it can reference it by a project-relative path — `lib.fit` and
`spec.json` fit cases resolve against the repo root, and a mount cannot be
gated against a file that lives outside it.

196 solids, 11.5 MB. Overall bbox **122.348 × 37.256 × 177.648 mm**, including
the four rubber feet and the SMA bodies protruding from both end panels.

## The one thing to know

**It has exactly four fixings, all on the bottom pan, and a screw may enter them
no more than 3.575 mm.** Beyond that the tip meets the internal M3×8 PCB screw
and jacks the board off its standoffs — a failure that torques up normally and
gives no sign. Every other face is either a connector face, a removable cover,
or has no holes at all.

Consumers: [`parts/custom/ettus-b210-mount`](../../custom/ettus-b210-mount) and
[`parts/custom/adrs-maritime-layout-compact`](../../custom/adrs-maritime-layout-compact).

## references/

Measured with the OpenCASCADE kernel, not read off a drawing. Re-run these two
scripts if the vendor ever reissues the file.

| File | What it is |
|---|---|
| `Ettus_USRP_B210_Full_Unit_analysis.json` | `lib.analyze_step` output: bbox, solids, 753 cylindrical features with true axes |
| `verify_b210.py` → `..._verify_pass1.json` | Bores, sheet openings, face planes, and a **direct measurement of the screw-penetration limit** — it walks each bore axis and reports where material first appears (Y = +2.365, i.e. 3.575 mm of free travel) |
| `verify_b210_pass2.py` → `..._verify_pass2.json` | Rubber-foot geometry, the two side-wall slot wires, the stepped side band, the top-cover dimples, and a centroid proxy for shock loading |

```bash
# both need a venv at a short path — the in-tree .venv cannot import OCP here
cd C:/b210work && C:/venvs/cadquery/Scripts/python.exe verify_b210.py out.json
```

Run them from a short working directory: this checkout sits 173 characters deep
and a Win32 process cannot take it as a current directory.

## Measured interface summary

Full detail, in a mount-friendly frame, is in
[`parts/custom/ettus-b210-mount/params.json`](../../custom/ettus-b210-mount/params.json)
under `b210_interface`.

* **−Y bottom pan** — the only mountable face. Flat at Y = −1.210,
  X[0, 117] × Z[−153.126, −2.420], 17 632 mm² gross. Four Ø3.000 bores in
  clinched PEM SOS-M3-10 standoffs at (11.701 / 105.300, −20.628 / −140.643):
  a **93.599 × 120.015** rectangle, centred in X but **3.05 mm off centre in Z**.
* **Four adhesive rubber feet**, Ø12.700 tapering to a Ø8.37 flat, 3.556 mm
  proud, **exactly concentric with the four bores**. Peel them off to bolt
  anything on — or give them somewhere to go.
* **+Z front (RF)** — 4× SMA protruding 10.132 mm, 4 LED lightpipes that must
  stay visible, a full-face printed label, and the four screws that retain the
  panel. **+Z and −Z are forbidden mounting faces.**
* **−Z rear (I/O)** — 3× SMA, USB 3.0 Standard-B (the deepest keep-out on the
  unit), DC barrel jack, 2 lightpipes, label, four panel screws.
* **±X side walls** — zero holes; stepped 0.254 mm between the cover skirt
  (122.348 across) and the bottom pan band (121.840). Each carries one
  3.000 × 7.000 through-slot with **no identified function**, and the two are
  **diagonally opposite, not mirrored** — the −X slot is near the rear, the +X
  slot near the front.
* **+Y top cover** — flat, 17 198 mm², **zero holes**, and removable. Four
  12.740 × 12.740 × 1.000 deep drawn stacking dimples. Clamp or strap only.

## Open question

PEM catalogues type `SOS` as a **blind**-threaded standoff, while this model
shows the bore open clean through to the outer face. Everything else in the file
says tapped M3 — Ø3.000 against Ø3.200 for every genuine clearance hole in the
same file, an M3×8 with a Ø3.000 shank modelled engaged in it, and the `M3`
thread code in the PEM part name. Nobody has yet run a screw into a real unit.
Five minutes with an M3×6 settles it, and until it is settled, any bolted mount
is provisional.
