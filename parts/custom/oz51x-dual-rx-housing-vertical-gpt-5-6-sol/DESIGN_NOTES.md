# GPT-5.6 Sol production refinement — dual RX vertical housing

This revision preserves every functional interface inherited from
`oz51x-dual-rx-housing-vertical`: module and boss locations, SMA axes, header
openings, fiber pass-slots and bend radius, SC/APC adapters, DE-9 cutout and
keep-out, service-cover screws, and the 32.72 × 133.50 × 92.20 mm envelope.

## Production improvements

- Taper-rooted module supports and screw bosses reduce local stress without
  changing their mating faces. Screw pilots and cover counterbores have lead-ins.
- A webbed annular spool retains the 15 mm fiber bend radius, adds end flanges,
  preserves the lid-screw hub, and replaces unnecessary solid material.
- Four molded tie saddles retain pigtails and the signal harness without holes
  through the enclosure wall.
- The service cover uses recessed fields, full-thickness stiffening lands,
  radiused corners, and a 0.4 mm registration allowance.
- Horizontal vents use stand-off internal splash baffles. Gravity drains join
  both module bays and discharge the lower bay and fiber plenum downward.
- SC/APC, DE-9, and SMA entrances have shallow assembly lead-ins while their
  controlled through-cut dimensions remain unchanged.

## Manufacturing assumptions

PA12 SLS/MJF is preferred. ASA or PETG-CF FDM is suitable with an enclosed
printer and validated pilot-hole coupons. The vent labyrinth is intended for
drip/debris resistance inside a larger equipment enclosure, not an IP rating.
Verify the real TTL module, ordered panel hardware, screw-forming behavior, and
fiber handling before production release.
