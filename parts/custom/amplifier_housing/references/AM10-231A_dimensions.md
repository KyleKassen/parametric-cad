# AM10-231A Amplifier — Dimensional Reference

> **Source:** AM10-06-231 RA datasheet (PDF in `datasheets/AM10-231A.pdf`)
> **Model:** AM10-2.9-3.3-60-60
> **Manufacturer:** Microwave Amplifiers Ltd
> **Drawing Number:** AM10-06-002 Latest issue
> **Extracted:** 2026-06-02

---

## 1. Overall Enclosure Dimensions

| Parameter | Value | Source |
|-----------|-------|--------|
| **Length** | 250 mm | Spec text (page 2) + drawing (page 3) |
| **Width** | 120 mm | Spec text + drawing |
| **Height** | 50 mm | Spec text |
| **Weight** | 1500 g | Spec text |

---

## 2. Mounting Hole Pattern (Top/Plan View)

All dimensions measured from the **bottom-left corner** of the plan view.
X = rightward (along length), Y = upward (along width).

### Mounting hole grid:

**Bottom edge row (Y = 10 mm):**
- X = 5, 65, 125, 185, 245 mm → **5 holes**

**Middle row (Y = 60 mm):**
- X = 65, 125, 185 mm → **3 holes** (interior only, no edge holes)

**Top edge row (Y = 110 mm):**
- X = 5, 65, 125, 185, 245 mm → **5 holes**

**Total: 13 mounting holes**

> **⚠ ASSUMED: M4 clearance holes (Ø4.5 mm)**
> The drawing does not dimension the hole diameter. M4 is assumed based on the
> amplifier weight (1.5 kg) and typical RF module mounting practice. Verify
> against the physical unit or by contacting Microwave Amplifiers Ltd before
> final production.

---

## 3. Left End Panel (RF Input Side)

| Feature | Value | Notes |
|---------|-------|-------|
| SMA Female (RF Input) | Centered on panel face | Y ≈ 60 mm from bottom, Z ≈ mid-height |
| Panel dimensions | 120 mm wide × 50 mm tall | |
| SMA position from front face | 32.5 mm | Dimension from drawing |

---

## 4. Right End Panel (Output/Control Side)

Connector Y-center positions measured from the **bottom** of the right end panel:

| Connector | Type | Y-Center | Notes |
|-----------|------|----------|-------|
| REV (Reverse Monitor) | SMA Female | 13 mm | Bottom-most |
| O/P (RF Output) | N-Type Female | 29 mm | Second from bottom |
| FWD (Forward Monitor) | SMA Female | 45 mm | Third from bottom |
| DC/CONTROL | 7W2 D-Sub Plug | 90 mm | Near top of panel |

### Right end panel dimensions:
| Dimension | Value | Notes |
|-----------|-------|-------|
| Panel width | 120 mm | Full width |
| Connector cluster X-center | 32.5 mm from front face | Mirrors left end |
| "28" dimension on drawing | 28 mm | Height to center of 7W2 connector from top edge (90mm from bottom = 120-90 = 30mm from top — close to 28mm accounting for measurement reference) |
| "33" dimension on drawing | 33 mm | Appears to reference the baseplate/body height section |

---

## 5. Connector Protrusion Estimates

These are educated estimates based on standard connector specifications. **Not from the datasheet.**

| Connector | Mating protrusion (front) | Behind-panel depth | Notes |
|-----------|--------------------------|-------------------|-------|
| **SMA Female** (bulkhead) | ~8–10 mm | ~10–12 mm | 1/4"-36 thread body, typical overall length 17–22 mm |
| **N-Type Female** (panel mount) | ~12–16 mm | ~15–20 mm | Larger body, 4-hole flange ~19 mm depth typical |
| **7W2 D-Sub** (Shell A) | ~10–13 mm | ~12–15 mm | Shell Size A (same as DA-15), typical mating depth ~10 mm |

> These estimates are for planning housing clearances. The actual protrusion
> depends on the specific parts used by Microwave Amplifiers Ltd. Build in
> at least 20–25 mm clearance beyond each end panel to be safe.

---

## 6. Connector Pinout (7W2 D-Sub)

| Pin | Description | Specification |
|-----|-------------|---------------|
| A1 | GND | 0V (Ground) |
| A2 | +50V Supply | +48 to +50V DC |
| 1 | NC | Not connected |
| 2 | NC | Not connected |
| 3 | Over Temp Alarm | +12V = Alarm active |
| 4 | TTL Control | HIGH (3.2V) = ON, LOW = OFF |
| 5 | -8V Input | -7 to -10V DC |

---

## 7. Electrical Summary

| Parameter | Value |
|-----------|-------|
| Frequency | 2.9–3.3 GHz (S-band) |
| Peak Output Power | +59 dBm min, +60 dBm typ (~800W–1kW) |
| RF Input Drive | +5 dBm nominal |
| Input Drive (survival) | +15 dBm max (CW) |
| Duty Cycle | 10% max |
| Max Pulse Width | 200 µs |
| RF Rise/Fall Time | 15 ns typ, 30 ns max |
| Harmonics | -40 dBc typ |
| Non-Harmonic Spurious | -80 dBc min |
| I/O Return Loss | 14 dB min, 17 dB typ |
| RF Monitors | -30 dBc ±1 dB |
| Remote Control | TTL 3.2V HIGH = ON, LOW = OFF |
| TTL Rise/Fall Time | 2 µs typ, 5 µs max |
| Standby Current | 100 mA nominal |
| Power Supply | +50V DC, -8V DC |
| Over-Temp Protection | OFF @ 75°C case, auto-reset @ 55°C |

---

## 8. Environmental

| Parameter | Value |
|-----------|-------|
| Operating Temperature | -10 to +70°C (case temperature) |
| Storage Temperature | -40 to +90°C |

---

## 9. Protection Features

- **Reverse polarity protection** — Reversed supply will not damage the amplifier
- **Reverse power protection** — Circulator directs reverse power into a termination
- **Duty limiter** — Prevents continuous operation at excessive duty
- **TTL capacitive coupling** — Restricts pulse length to prevent excessive duty
- **Over temperature protection & alarm** — Case temp monitored, alarm output provided

---

## 10. Housing Design Intent

**Purpose:** Mounting cradle/tray to hold the AM10-231A amplifier module on the head
of an antenna rotator. The housing must:

1. **Securely hold the amplifier** using the 13-hole mounting pattern
2. **Allow side-to-side airflow** (left-to-right) across the top surface/heatsink
3. **Provide clearance above the amplifier** for the heatsink fins (height TBD — build
   in a parametric tolerance above the 50 mm body height)
4. **Mount to a flat metal plate** (the rotator head mounting surface) via the housing bottom
5. **Not obstruct connector access** on either end panel

**Airflow direction:** Left-to-right (side-to-side), across the width of the amplifier.
The top surface has integral cooling. The housing walls should be open or louvered
on the sides to allow air passage.
