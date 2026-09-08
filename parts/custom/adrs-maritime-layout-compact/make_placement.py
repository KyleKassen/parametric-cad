"""
Generate placement.json for the COMPACT arrangement, from interfaces.json plus
the layout decisions below.

Same rules as the v2 layout it descends from: hole positions are never retyped,
they are pulled straight out of interfaces.json and carried through the same
transform the component gets, and every connector, vent, drain and service
cover is declared as a keep-out that the verifier enforces.

Two components and one rail are new here:

  * a Brainboxes ES-511, which has NO bolted fixings at all and can only be
    hung on a TS35 rail;
  * an Advanced Navigation Certus Mini D INS, whose base is both its only
    fixing face and its alignment datum;
  * a 290 mm TS35 rail bolted flat to the subpanel, sized for the ES-511 plus
    about ten more module widths of growth.

    uv run python parts/custom/adrs-maritime-layout-compact/make_placement.py
"""

from __future__ import annotations

import json
from pathlib import Path

PART_DIR = Path(__file__).resolve().parent
IFACE = json.loads((PART_DIR / "interfaces.json").read_text(encoding="utf-8"))

CAD = "C:/Users/KyleKassen/Documents/Projects/ADRS/CAD"
REPO = PART_DIR.parent.parent.parent          # the CadQuery models repo root

STEP = {
    "tec": f"{CAD}/Hoffman/te121024010.stp",
    "psu": f"{CAD}/MeanWell/NSP-1600_0417.stp",
    "bedrock": f"{CAD}/Solidrun/Bedrock V3000 Basic 3D model.step",
    "ubr": f"{CAD}/Peplink/UBR_Plus.stp",
    "b210": f"{CAD}/Ettus/Ettus_USRP_B210_Full_Unit.step",
    "oz51x": str(REPO / "parts/custom/oz51x-dual-tx-housing-vertical-gpt-5-6-sol"
                        "/exports/oz51x-dual-tx-housing-vertical-gpt-5-6-sol_v1.step"),
    "es511": str(REPO / "parts/vendor/Brainboxes - ES-511 Cased PCB 3D Model.step"),
    "certus": str(REPO / "parts/vendor/advanced-navigation-imu"
                         "/Certus-Mini-D-Rugged-3D-model-v1.0.STEP"),
}

PLATE_T = 3.0
STANDOFF = 12.0        # equipment standoff off the subpanel
Z_PANEL = -109.22      # subpanel mounting face
Z_PLATE = -97.22       # bracket plates live here .. Z_PLATE + PLATE_T
Z_EQUIP = -94.22       # everything bolted to a bracket starts here
GREY = [0.62, 0.64, 0.67, 1.0]
STEEL = [0.72, 0.73, 0.75, 1.0]

# --- DIN rail ---------------------------------------------------------------
# TS35 bolted FLAT to the subpanel, not up on the 12 mm standoff plane: it needs
# the depth back, it is nowhere near the four proud corner collars, and a rail
# on standoffs is a spring.
RAIL_Y = 160.0         # rail centreline (enclosure Y)
RAIL_X0, RAIL_X1 = -105.0, 185.0
RAIL_H = 7.5
RAIL_W = 35.0
RAIL_T = 1.0
RAIL_LIP_Z = Z_PANEL + RAIL_H          # -101.72, where a clipped module bears
ES511_PANEL_OFFSET = 0.9               # part Y -62.1 vs its own panel plane -63.0


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


def panel_bolts(x0, x1, y0, y1, inset=9.0, size="M5", cols=2, rows=2,
                z=None, screw_len=18.0):
    """
    Bolt pattern through a Z-normal plate into the subpanel.

    Marked into_subpanel so the engine also writes these out as a drilling
    schedule — the subpanel is a purchased part, so the holes in it have to be
    handed to whoever preps it rather than modelled.
    """
    z = Z_PLATE + PLATE_T / 2 if z is None else z
    xs = [(x0 + x1) / 2] if cols == 1 else [
        x0 + inset + i * (x1 - x0 - 2 * inset) / (cols - 1) for i in range(cols)]
    ys = [(y0 + y1) / 2] if rows == 1 else [
        y0 + inset + j * (y1 - y0 - 2 * inset) / (rows - 1) for j in range(rows)]
    return [{"id": f"PNL-{i}{j}", "x": x, "y": y, "z": z,
             "axis": "Z", "size": size, "screw_len": screw_len, "screw_dir": -1,
             "into_subpanel": True}
            for i, x in enumerate(xs) for j, y in enumerate(ys)]


# ---------------------------------------------------------------------------
# THE LAYOUT
#
# What changed from v2, and why:
#
#   * The B210 is stood on edge as a blade instead of lying flat. Its only
#     fixing face is the 117 x 150.7 base sheet, and that face works just as
#     well vertical. It costs 85 mm of depth we were not using and gives back
#     85 mm of panel width we badly needed.
#   * The UBR blade was dropped 28 mm and the Bedrock 10 mm, which frees the
#     whole top band of the panel.
#   * That top band takes a 290 mm TS35 rail bolted straight to the subpanel,
#     with the ES-511 on it and about ten module widths spare.
#   * The Certus Mini D goes in the right-hand column, on a solid 8 mm pedestal
#     in the dead 12 mm layer under the standoff plane — the stiffest mount in
#     the enclosure, and it costs no depth at all.
#
# The three facts that set everything are unchanged:
#   * the TE12 needs 50 mm of plenum in front of its intake — measured, that is
#     the prism X[-167.05,-111.05] x Y[-20,100] x Z[-60,60], and the cooler
#     body itself owns everything left of X = -161.05 between Y = -112.34 and
#     Y = +192.34;
#   * the UBR needs 55 mm off its cellular SMA face and 60 mm off its port
#     bank, and the B210 needs 55 mm off its USB end;
#   * the OZ51x has connectors on BOTH +/-Y faces, a service cover on +X and
#     drains on -Z, leaving exactly one mountable face: -X. Its orientation is
#     LOCKED — putting the fibre on the other side is a reflection, not a
#     rotation, so it would stand the drains on their head.
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
        {"id": "BOT-1", "x": 31.787, "y": 338.05, "z": 1.5,
         "axis": "Z", "size": "M3", "screw_len": 7.0},
        {"id": "BOT-2", "x": 101.787, "y": 338.05, "z": 1.5,
         "axis": "Z", "size": "M3", "screw_len": 7.0},
        {"id": "BOT-3", "x": 66.787, "y": 73.35, "z": 1.5,
         "axis": "Z", "size": "M3", "screw_len": 7.0},
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

# --- Bedrock V3000, upright, hard against the left edge of the TEC plenum
P.append({
    "name": "bedrock_v3000", "step": STEP["bedrock"], "mounted_to": "bedrock_spine",
    "rotate": [{"axis": "X", "degrees": -90}],
    "box": box(-108.0, -35.0, -150.0, 20.0, Z_EQUIP, 38.78),
    "may_touch": ["bedrock_spine", "bedrock_shelf"],
    "mount_holes": holes("solidrun_bedrock_v3000",
                         ["M3_backwall_Z50", "M3_backwall_Z110"], "M3", 6.0),
    "keepouts": keepouts("solidrun_bedrock_v3000",
                         names=["-Y ENVELOPE (use this one)", "+Z ENVELOPE (use this one)"]),
    "color": [0.80, 0.30, 0.25, 1.0],
    "note": "Fins vertical, left fin bank facing the TEC plenum. Back wall bearing strip "
            "is only 20 mm wide (X +/-10) and the 2x M3 take 3.0 mm MAX penetration.",
})
P.append({
    "name": "bedrock_spine", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 20.0, "dy": 164.0, "dz": PLATE_T, "corner_r": 4.0},
    "box": box(-81.5, -61.5, -130.0, 34.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(-81.5, -61.5, -130.0, 34.0, inset=8.0, cols=1, rows=2),
    "may_touch": ["bedrock_v3000", "bedrock_shelf"], "color": GREY,
    "note": "20 mm wide to match the Bedrock's flat back-wall land — a wider plate "
            "would ride on the fin-root blends instead of bearing.",
})
P.append({
    "name": "bedrock_shelf", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": 79.0, "dy": PLATE_T, "dz": 66.0, "corner_r": 3.0},
    "box": box(-109.5, -30.5, -153.0, -150.0, Z_EQUIP, -28.22),
    "may_touch": ["bedrock_v3000", "bedrock_spine", "bedrock_shelf_flange"], "color": GREY,
    "own_holes": [{"id": "BEDROCK-M4-FOOT", "x": -65.5, "y": -151.5, "z": -60.0,
                   "axis": "Y", "size": "M4", "screw_len": 10.0, "screw_dir": 1}],
    "note": "Carries the 1.6 kg in shear and picks up the M4x8 deep tapping in the "
            "Bedrock's bottom end cap, so the two shallow M3s only locate it.",
})
P.append({
    "name": "bedrock_shelf_flange", "source": "scaffold", "kind": "box",
    "mounted_to": "subpanel",
    "params": {"dx": 79.0, "dy": 18.0, "dz": PLATE_T},
    "box": box(-109.5, -30.5, -153.0, -135.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(-109.5, -30.5, -153.0, -135.0, inset=8.0, rows=1),
    "may_touch": ["bedrock_shelf", "bedrock_spine"], "color": GREY,
    "note": "The shelf and this flange are ONE folded 3 mm part: 66 mm horizontal leg, "
            "18 mm vertical leg, bend line at Z=-94.22.",
})

# --- UBR Plus, on-edge blade. Dropped 28 mm from v2 so the top band is free,
#     but no lower: its cellular SMA bank needs 55 mm and below that sits the
#     PSU, whose own 85 mm of depth overlaps the SMA keep-out band exactly.
P.append({
    "name": "ubr_plus", "step": STEP["ubr"], "mounted_to": "ubr_bracket",
    "rotate": [{"axis": "Z", "degrees": -90}, {"axis": "X", "degrees": -90}],
    "box": box(-5.0, 24.3, -70.0, 96.2, Z_EQUIP, 77.58),
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
    "box": box(-8.0, -5.0, -63.0, 89.0, Z_EQUIP, 84.0),
    "may_touch": ["ubr_plus", "ubr_bracket_flange"], "color": GREY,
    "note": "Full-contact spreader — 10,781 mm2 of real metal-to-metal inside the "
            "hole rectangle. Not four isolated standoffs.",
})
P.append({
    "name": "ubr_bracket_flange", "source": "scaffold", "kind": "box",
    "mounted_to": "subpanel",
    "params": {"dx": 24.0, "dy": 152.0, "dz": PLATE_T},
    "box": box(-32.0, -8.0, -63.0, 89.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(-32.0, -8.0, -63.0, 89.0, inset=7.0),
    "may_touch": ["ubr_bracket"], "color": GREY,
    "note": "Web plus flange is ONE folded 3 mm part: 178 mm web, 24 mm flange, bend "
            "line at Z=-94.22. Narrowed from v2's 34 mm so its bolt heads stay clear "
            "of the Bedrock, which now sits 3 mm to its left.",
})

# --- OZ51x dual-TX housing. Only -X is mountable: both +/-Y carry connectors,
#     +X is the removable service cover, -Z carries the two drains.
#     Raised 6 mm from v2 so the bottom hold-down clip's bolt heads clear the PSU.
P.append({
    "name": "oz51x_dual_tx_housing", "step": STEP["oz51x"], "mounted_to": "oz51x_cradle",
    "rotate": [{"axis": "Z", "degrees": -90}, {"axis": "X", "degrees": -90}],
    "box": box(45.0, 178.5, -134.0, -41.8, Z_EQUIP, -61.5),
    "may_touch": ["oz51x_cradle", "oz51x_clip_top_foot", "oz51x_clip_top_lip",
                  "oz51x_clip_bot_foot", "oz51x_clip_bot_lip_a", "oz51x_clip_bot_lip_b"],
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
    "box": box(43.0, 180.5, -136.0, -40.0, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(43.0, 180.5, -136.0, -40.0, inset=9.0, cols=3),
    "may_touch": ["oz51x_dual_tx_housing", "oz51x_clip_top_foot", "oz51x_clip_top_lip",
                  "oz51x_clip_bot_foot", "oz51x_clip_bot_lip_a", "oz51x_clip_bot_lip_b"],
    "color": GREY,
    "note": "Bears on the housing's flat -X face (12,305 mm2, zero features). The part "
            "has NO fixings, so it is captured by the two clips rather than bolted.",
})
# Two folded 3 mm hold-down clips: a foot bolted flat to the subpanel plus a lip
# that laps onto the housing's top / bottom face. The bottom lip is split into
# two segments because the two dia-3 drain outlets exit that face and must stay
# open — at this placement they are at enclosure X = 99.75..127.00.
CLIPS = [
    ("oz51x_clip_top_foot", 43.0, 180.5, -41.8, -24.0, Z_PLATE, Z_PLATE + PLATE_T, True),
    ("oz51x_clip_top_lip", 43.0, 180.5, -41.8, -38.8, Z_EQUIP, -66.0, False),
    ("oz51x_clip_bot_foot", 43.0, 180.5, -154.0, -136.0, Z_PLATE, Z_PLATE + PLATE_T, True),
    ("oz51x_clip_bot_lip_a", 43.0, 95.0, -137.0, -134.0, Z_EQUIP, -66.0, False),
    ("oz51x_clip_bot_lip_b", 133.0, 180.5, -137.0, -134.0, Z_EQUIP, -66.0, False),
]
CLIP_KIN = ["oz51x_dual_tx_housing", "oz51x_cradle"] + [c[0] for c in CLIPS]
for nm, x0, x1, y0, y1, z0, z1, is_foot in CLIPS:
    spec = {
        "name": nm, "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
        "params": {"dx": x1 - x0, "dy": y1 - y0, "dz": z1 - z0, "corner_r": 2.0},
        "box": box(x0, x1, y0, y1, z0, z1),
        "may_touch": CLIP_KIN, "color": GREY,
        "note": "Hold-down clip: foot bolts to the subpanel, lip laps the housing face. "
                "Foot and lip are one folded part.",
    }
    if is_foot:
        spec["own_holes"] = panel_bolts(x0, x1, y0, y1, inset=10.0, cols=3, rows=1)
    P.append(spec)

# --- Ettus B210, ON EDGE. This is the single biggest change from v2: the unit's
#     only fixing face is its 117 x 150.7 base sheet, and that face is just as
#     happy vertical. Standing it up trades 85 mm of unused depth for 85 mm of
#     panel width, which is what makes room for the DIN rail column.
#     Rotation [X-90, Y-90] maps part X -> enclosure Z, part Y -> X, part Z -> Y,
#     so the bracket lands on -X, the front SMA bank points UP and the USB /
#     DC end points DOWN.
P.append({
    "name": "ettus_b210", "step": STEP["b210"], "mounted_to": "b210_bracket",
    "rotate": [{"axis": "X", "degrees": -90}, {"axis": "Y", "degrees": -90}],
    "box": box(81.3, 118.56, 20.0, 197.65, Z_EQUIP, 28.13),
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
            "The four rubber feet must be peeled off so it seats flat. Its -X side "
            "slot faces the subpanel with 15 mm of air under it, which satisfies the "
            "10 mm the slot asks for without a spacer.",
})
P.append({
    "name": "b210_bracket", "source": "scaffold", "kind": "box", "mounted_to": "subpanel",
    "params": {"dx": PLATE_T, "dy": 183.65, "dz": 125.35, "corner_r": 6.0},
    "box": box(78.3, 81.3, 17.0, 200.65, Z_EQUIP, 31.13),
    "may_touch": ["ettus_b210", "b210_bracket_flange"], "color": GREY,
    "note": "Vertical web. The B210's four M3 land on it directly, so the pattern "
            "cannot drift — it is the same numbers the unit was measured with.",
})
P.append({
    "name": "b210_bracket_flange", "source": "scaffold", "kind": "box",
    "mounted_to": "subpanel",
    "params": {"dx": 34.0, "dy": 183.65, "dz": PLATE_T},
    "box": box(44.3, 78.3, 17.0, 200.65, Z_PLATE, Z_PLATE + PLATE_T),
    "own_holes": panel_bolts(44.3, 78.3, 17.0, 200.65, inset=9.0, rows=4),
    "may_touch": ["b210_bracket"], "color": GREY,
    "note": "Web plus flange is ONE folded 3 mm part: 125 mm web, 34 mm flange, bend "
            "line at Z=-94.22. Eight M5 into the subpanel because this one is a "
            "cantilever carrying 0.35 kg at 60 mm.",
})

# --- TS35 DIN rail, bolted flat to the subpanel across the top band.
P.append({
    "name": "din_rail_ts35", "source": "scaffold", "kind": "din_rail",
    "mounted_to": "subpanel", "purchased": True,
    "params": {"length": RAIL_X1 - RAIL_X0, "t": RAIL_T, "width": RAIL_W,
               "height": RAIL_H},
    "box": box(RAIL_X0, RAIL_X1, RAIL_Y - RAIL_W / 2, RAIL_Y + RAIL_W / 2,
               Z_PANEL, Z_PANEL + RAIL_H),
    # Bolt stations dodge the two end stops (X 139..149 and 172.6..182.6), whose
    # clamp bodies sit ON the rail and would rock on a screw head. The one at
    # X = 165 lands under the ES-511 instead, which is fine — that is exactly the
    # case the 3.5 mm head limit exists for.
    "own_holes": [
        {"id": f"RAIL-{i}", "x": float(x), "y": RAIL_Y, "z": Z_PANEL + RAIL_T / 2,
         "axis": "Z", "size": "M5", "screw_len": 14.0, "screw_dir": -1,
         "into_subpanel": True}
        for i, x in enumerate((-95, -50, -5, 40, 85, 130, 165))
    ],
    "may_touch": ["brainboxes_es511", "din_end_stop_l", "din_end_stop_r"],
    "color": STEEL,
    "note": "290 mm of TS35, centreline Y = +160, bolted straight to the subpanel on "
            "7 stations at 45 mm pitch. THE HEADS MUST BE PAN OR COUNTERSUNK, 3.5 mm "
            "MAX: a device clip reaches 3.5 mm into the channel and a socket head is "
            "5 mm. Clear of all four corner collars, which are proud to Z = -100.69 "
            "at (+/-193.68, +/-193.68).",
})
for nm, x0 in (("din_end_stop_l", 139.0), ("din_end_stop_r", 172.6)):
    P.append({
        "name": nm, "source": "scaffold", "kind": "box",
        "mounted_to": "din_rail_ts35", "purchased": True,
        "params": {"dx": 10.0, "dy": RAIL_W, "dz": 26.0, "corner_r": 2.0},
        "box": box(x0, x0 + 10.0, RAIL_Y - RAIL_W / 2, RAIL_Y + RAIL_W / 2,
                   Z_PANEL, Z_PANEL + 26.0),
        "may_touch": ["din_rail_ts35", "brainboxes_es511",
                      "din_end_stop_l", "din_end_stop_r"],
        "color": [0.30, 0.32, 0.36, 1.0],
        "note": "Screw-clamp rail end stop. Not optional here — a DIN clip alone is "
                "not a shock mount, and this module is 99 mm of cantilever.",
    })

# --- Brainboxes ES-511 on the rail. No fixings of any kind on the part, so the
#     rail IS the mount. Rotation [X+90, Z+90] maps part Z (the 22.6 mm rail
#     width) -> enclosure X, part X (99 mm) -> enclosure Y and part +Y (the I/O
#     face) -> +Z, i.e. straight at the door.
ES511_Z0 = Z_PANEL + ES511_PANEL_OFFSET
P.append({
    "name": "brainboxes_es511", "step": STEP["es511"], "mounted_to": "din_rail_ts35",
    "rotate": [{"axis": "X", "degrees": 90}, {"axis": "Z", "degrees": 90}],
    "box": box(150.0, 172.6, RAIL_Y - 49.5, RAIL_Y + 49.5,
               ES511_Z0, ES511_Z0 + 114.425),
    "may_touch": ["din_rail_ts35", "din_end_stop_l", "din_end_stop_r"],
    "keepouts": keepouts("brainboxes_es511"),
    "color": [0.25, 0.45, 0.75, 1.0],
    "note": "Clipped, not bolted — it has no fastener features at all. Its back plane "
            "lands on the rail lips at Z = -101.72 and it projects 115.3 mm from the "
            "subpanel, so the RJ45 and both terminal blocks face the open door. "
            "Louvres end up on the +/-Y faces, which is the right way up for a "
            "horizontal rail.",
})

# --- Certus Mini D INS. Right-hand column, on a solid 8 mm pedestal that lives
#     in the dead 12 mm layer under the standoff plane. Rotation [X+90] puts the
#     base flat on the pedestal and the GNSS / data connectors facing -Y, into
#     the open lane above the OZ51x's fibre side.
#     Y span is 46.617, not 41: the connector barrels stand 5.617 mm proud of
#     the flange ear and they are on the -Y end of the placed box.
CERTUS_PED_T = 8.0
CERTUS = box(165.0, 195.0, 26.0, 72.617,
             Z_PANEL + CERTUS_PED_T, Z_PANEL + CERTUS_PED_T + 34.0)
P.append({
    "name": "certus_mini_d", "step": STEP["certus"], "mounted_to": "certus_pedestal",
    "rotate": [{"axis": "X", "degrees": 90}],
    "box": CERTUS,
    "may_touch": ["certus_pedestal"],
    "mount_holes": holes("advanced_navigation_certus_mini_d",
                         ["IMU-1", "IMU-2", "IMU-3", "IMU-4"], "M2", 6.0),
    "keepouts": keepouts("advanced_navigation_certus_mini_d"),
    "color": [0.20, 0.65, 0.72, 1.0],
    "note": "Its base is BOTH the only fixing face and the alignment datum, so the "
            "pedestal face defines the INS axes. Sited clear of the TEC plenum and "
            "about 180 mm from the NSP-1600, in the one column of the panel with no "
            "tall neighbour. 4x M2 only — that is what the part offers.",
})
P.append({
    "name": "certus_pedestal", "source": "scaffold", "kind": "box",
    "mounted_to": "subpanel",
    "params": {"dx": 60.0, "dy": 66.0, "dz": CERTUS_PED_T, "corner_r": 5.0},
    "box": box(150.0, 210.0, 19.1, 85.1, Z_PANEL, Z_PANEL + CERTUS_PED_T),
    "own_holes": panel_bolts(150.0, 210.0, 19.1, 85.1, inset=10.0,
                             z=Z_PANEL + CERTUS_PED_T / 2, screw_len=16.0),
    "may_touch": ["certus_mini_d"], "color": [0.55, 0.57, 0.60, 1.0],
    "note": "SOLID 8 mm 6061, bolted straight to the subpanel — not 3 mm plate on "
            "standoffs. An INS is only as good as its mount stiffness, and this one "
            "costs nothing because it fits inside the 12 mm gap everything else "
            "stands on. Tapped 4x M2 on 26 x 37; the 4x M5 corner bolts sit 8.3 mm from "
            "the nearest M2 centre, against the 6.2 mm the two head radii need. Its top "
            "edge stops 5.4 mm short of the ES-511's sliding-jaw release zone.",
})

doc = {
    "title": "ADRS maritime layout - SCE-20H2010LP interior (v3, compact + DIN rail)",
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
