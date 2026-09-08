"""
Generate placement.json from interfaces.json + the layout decisions below.

Hole positions are never retyped — they are pulled straight out of
interfaces.json (measured from each vendor STEP) and carried through the same
transform the component gets, so a bracket cannot drift out of line with the
part it holds. Same for connector keep-outs: they are declared on the part
surface in part coordinates and the engine transforms them.

    uv run python parts/custom/adrs-maritime-layout/make_placement.py
"""

from __future__ import annotations

import json
from pathlib import Path

PART_DIR = Path(__file__).resolve().parent
IFACE = json.loads((PART_DIR / "interfaces.json").read_text(encoding="utf-8"))

STEP = {
    "tec": "C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/Hoffman/te121024010.stp",
    "psu": "C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/MeanWell/NSP-1600_0417.stp",
    "bedrock": "C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/Solidrun/Bedrock V3000 Basic 3D model.step",
    "ubr": "C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/Peplink/UBR_Plus.stp",
    "b210": "C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/Ettus/Ettus_USRP_B210_Full_Unit.step",
    "oz51x": "C:/Users/KyleKassen/Documents/Projects/parametric-cad/parts/custom"
             "/oz51x-dual-tx-housing-vertical-gpt-5-6-sol/exports"
             "/oz51x-dual-tx-housing-vertical-gpt-5-6-sol_v1.step",
}

PLATE_T = 3.0
STANDOFF = 12.0        # equipment standoff off the subpanel
Z_PLATE = -97.22       # bracket plates live here .. Z_PLATE + PLATE_T
Z_EQUIP = -94.22       # everything bolted to a bracket starts here
GREY = [0.62, 0.64, 0.67, 1.0]


def holes(key: str, ids: list[str], size: str, screw_len: float) -> list[dict]:
    """Pull named holes out of interfaces.json, in part coordinates."""
    src = {h["id"]: h for h in IFACE[key]["mounting_holes"]}
    out = []
    for i in ids:
        h = src[i]
        out.append({"id": i, "x": h["x"], "y": h["y"], "z": h["z"],
                    "axis": h["axis"], "size": size, "screw_len": screw_len})
    return out


def keepouts(key: str, names: list[str] | None = None, drop: list[str] | None = None):
    """Connector/vent/service patches, in part coordinates."""
    out = []
    for k in IFACE[key]["connector_keepouts"]:
        if names is not None and k["name"] not in names:
            continue
        if drop and k["name"] in drop:
            continue
        out.append({"name": k["name"], "face": k["face"],
                    "xmin": k["xmin"], "xmax": k["xmax"],
                    "ymin": k["ymin"], "ymax": k["ymax"],
                    "zmin": k["zmin"], "zmax": k["zmax"],
                    "clear_out_mm": k["clear_out_mm"]})
    return out


def box(x0, x1, y0, y1, z0, z1):
    return {"xmin": x0, "xmax": x1, "ymin": y0, "ymax": y1, "zmin": z0, "zmax": z1}


def panel_bolts(x0, x1, y0, y1, inset=9.0, size="M5", cols=2, rows=2):
    """
    Bolt pattern through a Z-normal plate into the subpanel.

    Marked into_subpanel so the engine also writes these out as a drilling
    schedule — the subpanel is a purchased part, so the holes in it have to be
    handed to whoever preps it rather than modelled.
    """
    xs = [x0 + inset] if cols == 1 else [
        x0 + inset + i * (x1 - x0 - 2 * inset) / (cols - 1) for i in range(cols)]
    ys = [y0 + inset] if rows == 1 else [
        y0 + inset + j * (y1 - y0 - 2 * inset) / (rows - 1) for j in range(rows)]
    return [{"id": f"PNL-{i}{j}", "x": x, "y": y, "z": Z_PLATE + PLATE_T / 2,
             "axis": "Z", "size": size, "screw_len": 18.0, "screw_dir": -1,
             "into_subpanel": True}
            for i, x in enumerate(xs) for j, y in enumerate(ys)]


# ---------------------------------------------------------------------------
# THE LAYOUT
#
# Driven by three hard facts the interface extraction turned up:
#   * the TE12 needs 50 mm of plenum in front of its intake grille, which
#     reaches X = -111.05 — so no equipment lives left of that in the band it
#     sweeps;
#   * the UBR Plus needs 55 mm off its cellular SMA face and 60 mm off its port
#     bank, and the B210 needs 55 mm off its USB end. These cable volumes, not
#     the boxes, are what actually sets the packing;
#   * the OZ51x has connectors on BOTH +/-Y faces, a service cover on +X and
#     drains on -Z, leaving exactly one mountable face: -X.
# ---------------------------------------------------------------------------
P: list[dict] = []

# --- TE12 cooler, left wall, raised 40 mm so its condensate pan clears the PSU
P.append({
    "name": "tec_te121024010", "step": STEP["tec"], "mounted_to": "left_wall",
    "protrudes_wall": True, "ignores_keepouts": True,
    "rotate": [{"axis": "X", "degrees": -90}, {"axis": "Y", "degrees": 90}],
    "box": box(-343.37, -161.05, -112.34, 192.34, -80.11, 79.35),
    "keepouts": keepouts("te121024010", names=[
        "interior_fan_intake_finger_guard",
        "interior_top_discharge_louver_band",
        "interior_bottom_discharge_louver_band"]),
    "color": [0.30, 0.62, 0.80, 1.0],
    "note": "91.0 mm intrudes, 89.4 mm outboard. Wall cutout 125x232, 6x M6 on 142 x 286.",
})

# --- NSP-1600, bottom, horizontal, below the cooler so it can run full width
P.append({
    "name": "nsp1600_psu", "step": STEP["psu"], "mounted_to": "psu_shelf",
    "rotate": [{"axis": "X", "degrees": -90}, {"axis": "Y", "degrees": -90}],
    "box": box(-180.0, 158.6, -195.0, -154.0, Z_EQUIP, -9.22),
    "may_touch": ["psu_shelf"],
    # 3x M3 in the chassis bottom, max 4 mm penetration (part Pz=1.500 face)
    "mount_holes": [
        {"id": "BOT-1", "x": 31.787, "y": 338.05, "z": 1.5, "axis": "Z", "size": "M3", "screw_len": 7.0},
        {"id": "BOT-2", "x": 101.787, "y": 338.05, "z": 1.5, "axis": "Z", "size": "M3", "screw_len": 7.0},
        {"id": "BOT-3", "x": 66.787, "y": 73.35, "z": 1.5, "axis": "Z", "size": "M3", "screw_len": 7.0},
    ],
    "keepouts": [
        {"name": "PSU rear terminal panel + fan INTAKE louvres", "face": "+Y",
         "xmin": 24.287, "xmax": 109.287, "ymin": 354.15, "ymax": 354.15,
         "zmin": 1.5, "zmax": 42.5, "clear_out_mm": 60.0},
        {"name": "PSU fan EXHAUST face", "face": "-Y",
         "xmin": 24.287, "xmax": 109.287, "ymin": 53.552, "ymax": 53.552,
         "zmin": 1.5, "zmax": 42.5, "clear_out_mm": 60.0},
        {"name": "bare +/-Vo DC busbar blades", "face": "+Y",
         "xmin": 24.287, "xmax": 109.287, "ymin": 354.15, "ymax": 392.152,
         "zmin": 1.5, "zmax": 42.5, "clear_out_mm": 25.0},
    ],
    "color": [0.85, 0.70, 0.25, 1.0],
    "note": "Horizontal — the only qualified attitude. Terminals and bare busbars "
            "at +X away from the cold wall; fan exhaust at -X. Hole positions DERIVED "
            "from the first-pass analysis, not yet re-measured — verify before drilling.",
})

# --- Bedrock V3000, upright, right at the edge of the TEC plenum
BEDROCK_BOX = box(-105.0, -32.0, -140.0, 30.0, Z_EQUIP, 38.78)
P.append({
    "name": "bedrock_v3000", "step": STEP["bedrock"], "mounted_to": "bedrock_spine",
    "rotate": [{"axis": "X", "degrees": -90}],
    "box": BEDROCK_BOX,
    "may_touch": ["bedrock_spine", "bedrock_shelf"],
    "mount_holes": holes("solidrun_bedrock_v3000",
                         ["M3_backwall_Z50", "M3_backwall_Z110"], "M3", 6.0),
    "keepouts": keepouts("solidrun_bedrock_v3000",
                         names=["-Y ENVELOPE (use this one)", "+Z ENVELOPE (use this one)"]),
    "color": [0.80, 0.30, 0.25, 1.0],
    "note": "Fins vertical. Left fin bank faces the TEC plenum. Back wall bearing strip "
            "is only 20 mm wide (X +/-10) and the 2x M3 take 3.0 mm MAX penetration.",
})
P.append({
    "name": "bedrock_spine", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 20.0, "dy": 164.0, "dz": PLATE_T, "corner_r": 4.0},
    "box": box(-78.5, -58.5, -120.0, 44.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(-78.5, -58.5, -120.0, 44.0, inset=8.0, cols=1, rows=2),
    "may_touch": ["bedrock_v3000", "bedrock_shelf"], "color": GREY,
    "note": "20 mm wide to match the Bedrock's flat back-wall land — a wider plate "
            "would ride on the fin-root blends instead of bearing.",
})
P.append({
    "name": "bedrock_shelf", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 79.0, "dy": PLATE_T, "dz": 66.0, "corner_r": 3.0},
    "box": box(-106.5, -27.5, -143.0, -140.0, Z_EQUIP, -28.22),
    "may_touch": ["bedrock_v3000", "bedrock_spine"], "color": GREY,
    "own_holes": [{"id": "BEDROCK-M4-FOOT", "x": -62.5, "y": -141.5, "z": -60.0,
                   "axis": "Y", "size": "M4", "screw_len": 10.0, "screw_dir": 1}],
    "may_touch_extra": ["bedrock_shelf_flange"],
    "note": "Carries the 1.6 kg in shear and picks up the M4x8 deep tapping in the "
            "Bedrock's bottom end cap, so the two shallow M3s only locate it.",
})

P.append({
    "name": "bedrock_shelf_flange", "source": "scaffold", "kind": "box",
    "mounted_to": "subpanel",
    "params": {"dx": 79.0, "dy": 18.0, "dz": PLATE_T},
    "box": box(-106.5, -27.5, -143.0, -125.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(-106.5, -27.5, -143.0, -125.0, inset=8.0, rows=1),
    "may_touch": ["bedrock_shelf", "bedrock_spine"], "color": GREY,
    "note": "The shelf and this flange are ONE folded 3 mm part: 66 mm horizontal leg, "
            "18 mm vertical leg, bend line at Z=-94.22.",
})

# --- UBR Plus, on-edge blade, raised clear of the OZ51x below it
P.append({
    "name": "ubr_plus", "step": STEP["ubr"], "mounted_to": "ubr_bracket",
    "rotate": [{"axis": "Z", "degrees": -90}, {"axis": "X", "degrees": -90}],
    "box": box(-5.0, 24.3, -40.0, 126.2, Z_EQUIP, 77.58),
    "may_touch": ["ubr_bracket"],
    "mount_holes": holes("peplink_ubr_plus", ["FLG-1", "FLG-2", "FLG-3", "FLG-4"],
                         "M4", 14.0),
    "keepouts": keepouts("peplink_ubr_plus", drop=[
        "-Y label / foot-pad recess (informational, NOT an obstruction)"]),
    "color": [0.35, 0.70, 0.40, 1.0],
    "note": "Flat cast flange bolts full-contact to the bracket — that face is its main "
            "heat path. Cellular SMA end DOWN (55 mm clear), port bank UP (60 mm).",
})
P.append({
    "name": "ubr_bracket", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": PLATE_T, "dy": 152.0, "dz": 178.0, "corner_r": 6.0},
    "box": box(-8.0, -5.0, -33.0, 119.0, Z_EQUIP, 84.0),
    "may_touch": ["ubr_plus", "ubr_bracket_flange"], "color": GREY,
    "note": "Full-contact spreader — 10,781 mm2 of real metal-to-metal inside the "
            "hole rectangle. Not four isolated standoffs.",
})

P.append({
    "name": "ubr_bracket_flange", "source": "scaffold", "kind": "box",
    "mounted_to": "subpanel",
    "params": {"dx": 34.0, "dy": 152.0, "dz": PLATE_T},
    "box": box(-42.0, -8.0, -33.0, 119.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(-42.0, -8.0, -33.0, 119.0, inset=9.0),
    "may_touch": ["ubr_bracket"], "color": GREY,
    "note": "The web and this flange are ONE folded 3 mm part: 178 mm web, 34 mm "
            "flange, bend line at Z=-94.22. Flange turns to -X into free space.",
})

# --- OZ51x dual-TX housing. Only -X is mountable: both +/-Y carry connectors,
#     +X is the removable service cover, -Z carries the two drains.
P.append({
    "name": "oz51x_dual_tx_housing", "step": STEP["oz51x"], "mounted_to": "oz51x_cradle",
    "rotate": [{"axis": "Z", "degrees": -90}, {"axis": "X", "degrees": -90}],
    "box": box(45.0, 178.5, -140.0, -47.8, Z_EQUIP, -61.5),
    "may_touch": ["oz51x_cradle", "oz51x_clip_top_foot", "oz51x_clip_top_lip", "oz51x_clip_bot_foot", "oz51x_clip_bot_lip_a", "oz51x_clip_bot_lip_b"],
    "keepouts": keepouts("oz51x-dual-tx-housing-vertical-gpt-5-6-sol_v1"),
    "color": [0.62, 0.35, 0.72, 1.0],
    "note": "Mounted on its ONLY connector-free face (-X). Service cover faces the door, "
            "SC/APC + DE-9 face +X, SMA face -X, and local +Z maps to enclosure +Y so "
            "the two drain outlets actually point DOWN — the inverted rotation pair "
            "(Z+90,X+90) looks identical on an axis check but stands it on its head.",
})
P.append({
    "name": "oz51x_cradle", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 137.5, "dy": 96.0, "dz": PLATE_T, "corner_r": 4.0},
    "box": box(43.0, 180.5, -142.0, -46.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(43.0, 180.5, -142.0, -46.0, inset=9.0, cols=3),
    "may_touch": ["oz51x_dual_tx_housing", "oz51x_clip_top_foot", "oz51x_clip_top_lip", "oz51x_clip_bot_foot", "oz51x_clip_bot_lip_a", "oz51x_clip_bot_lip_b"],
    "color": GREY,
    "note": "Bears on the housing's flat -X face (12,305 mm2, zero features). The part "
            "has NO fixings, so it is captured by the two straps rather than bolted.",
})
# The housing has no fixings at all, so it is CLAMPED: two folded 3 mm hold-down
# clips, each a foot bolted flat to the cradle plus a lip that laps onto the
# housing's top / bottom face. The bottom lip is split into two segments because
# the two dia-3 drain outlets exit that face at enclosure X = 113.0 and 137.25
# and must stay open.
# Drain outlets exit the housing's underside at enclosure X = 101.25 and 125.5,
# so the bottom lip is two segments with a gap across that band.
CLIPS = [
    ("oz51x_clip_top_foot", 43.0, 180.5, -47.8, -30.0, Z_PLATE, Z_PLATE + PLATE_T, True),
    ("oz51x_clip_top_lip", 43.0, 180.5, -47.8, -44.8, Z_EQUIP, -66.0, False),
    ("oz51x_clip_bot_foot", 43.0, 180.5, -160.0, -143.0, Z_PLATE, Z_PLATE + PLATE_T, True),
    ("oz51x_clip_bot_lip_a", 43.0, 95.0, -143.0, -140.0, Z_EQUIP, -66.0, False),
    ("oz51x_clip_bot_lip_b", 133.0, 180.5, -143.0, -140.0, Z_EQUIP, -66.0, False),
]
CLIP_KIN = ["oz51x_dual_tx_housing", "oz51x_cradle"] + [c[0] for c in CLIPS]
for nm, x0, x1, y0, y1, z0, z1, is_foot in CLIPS:
    spec = {
        "name": nm, "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
        "params": {"dx": x1 - x0, "dy": y1 - y0, "dz": z1 - z0, "corner_r": 2.0},
        "box": box(x0, x1, y0, y1, z0, z1),
        "may_touch": CLIP_KIN, "color": GREY,
        "note": "Hold-down clip: foot bolts to the cradle, lip laps the housing face. "
                "Foot and lip are one folded part.",
    }
    if is_foot:
        spec["own_holes"] = panel_bolts(x0, x1, y0, y1, inset=10.0, cols=3, rows=1)
    P.append(spec)

# --- Ettus B210, on end, service end up, right-hand column
P.append({
    "name": "ettus_b210", "step": STEP["b210"], "mounted_to": "b210_bracket",
    "rotate": [{"axis": "X", "degrees": 90}],
    "box": box(60.0, 182.35, 0.0, 177.65, Z_EQUIP, -56.96),
    "may_touch": ["b210_bracket"],
    "mount_holes": holes("ettus_usrp_b210", ["BOT-1", "BOT-2", "BOT-3", "BOT-4"],
                         "M3", 6.0),
    # FOOT_*_RUBBER are dropped deliberately: the four feet are adhesive and are
    # peeled off before the bracket seats, so they are an assembly step, not an
    # obstruction. Keeping them would make the checker cry wolf forever.
    "keepouts": keepouts("ettus_usrp_b210", drop=[
        "FRONT_LABEL_OVERLAY", "REAR_LABEL_OVERLAY", "TOP_STACK_RECESSES (4x)",
        "FOOT_1_RUBBER", "FOOT_2_RUBBER", "FOOT_3_RUBBER", "FOOT_4_RUBBER"]),
    "color": [0.95, 0.55, 0.20, 1.0],
    "note": "Hole pattern is symmetric in X but offset 3.05 mm in Z — a Z-symmetric "
            "bracket will NOT fit. Tapped M3x0.5, 3.574 mm MAX penetration. "
            "The four rubber feet must be peeled off so it seats flat.",
})
P.append({
    "name": "b210_bracket", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 126.0, "dy": 181.0, "dz": PLATE_T, "corner_r": 6.0},
    "box": box(58.0, 184.0, -2.0, 179.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(58.0, 184.0, -2.0, 179.0, inset=9.0, rows=3),
    "may_touch": ["ettus_b210"], "color": GREY,
})

# --- PSU shelf: folded 3 mm, flange bolted flat to the subpanel
P.append({
    "name": "psu_shelf", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 306.0, "dy": PLATE_T, "dz": 95.0},
    "box": box(-182.0, 124.0, -198.0, -195.0, Z_PLATE, -2.22),
    "may_touch": ["nsp1600_psu", "psu_shelf_flange", "psu_gusset_l", "psu_gusset_r"],
    "color": GREY, "note": "3 mm 6061, one folded part with the flange below.",
})
P.append({
    "name": "psu_shelf_flange", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 306.0, "dy": 17.9, "dz": PLATE_T},
    "box": box(-182.0, 124.0, -215.9, -198.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(-182.0, 124.0, -215.9, -198.0, inset=8.0, cols=5, rows=1),
    "may_touch": ["psu_shelf", "psu_gusset_l", "psu_gusset_r"], "color": GREY,
})
for nm, xc in (("psu_gusset_l", -178.0), ("psu_gusset_r", 120.0)):
    P.append({
        "name": nm, "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
        "params": {"dx": PLATE_T, "dy": 17.9, "dz": 92.0},
        "box": box(xc - 1.5, xc + 1.5, -215.9, -198.0, Z_PLATE, -5.22),
        "may_touch": ["psu_shelf", "psu_shelf_flange"], "color": GREY,
        "note": "Kept inboard of the PSU ends so it never sits in the fan tunnel.",
    })

doc = {
    "title": "ADRS maritime layout - SCE-20H2010LP interior (v2, fastened)",
    "frame": "Saginaw SCE-20H2010LP vendor STEP native frame: +X right, +Y up, "
             "+Z toward the door. Subpanel mounting face Z=-109.22, door clear Z=+131.10.",
    "generated_by": "make_placement.py from interfaces.json - do not hand-edit",
    "placements": P,
}
out = PART_DIR / "placement.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
nh = sum(len(p.get("mount_holes", [])) + len(p.get("own_holes", [])) for p in P)
nk = sum(len(p.get("keepouts", [])) for p in P)
print(f"wrote {out.name}: {len(P)} items, {nh} fastener holes, {nk} keep-outs")
