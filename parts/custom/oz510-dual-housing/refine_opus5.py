"""
Production refinement layer for the vertical OZ51x housings — Opus 5 edition
===========================================================================

A *layer*, not a fork and not an edit.

`model.py` in this directory is the family's canonical builder and stays byte
for byte unchanged.  This module imports it, asks it for the canonical tray and
cover, and then applies the refinement as explicit boolean operations on top.
Every interface dimension — bay pitch, stud and boss pattern, SMA hole and
relief pocket, fiber pass-slots, SC/APC ports, mated-connector corridors, spool
radius, lid lip and wire headroom — is therefore produced by the *same code
path* as v1.  Interface preservation is a property of the construction rather
than a claim in a document.

The two consumers are symmetric peers:

    parts/custom/oz51x-dual-rx-housing-vertical-opus-5/
    parts/custom/oz51x-dual-tx-housing-vertical-opus-5/

whose `model.py` files are identical apart from a docstring.  Everything that
differs between them is `params.json` — which is the rule REQUIREMENTS.md §9
states, and the reason this module lives here in family space rather than
inside one of the two part directories.


The headline change: the rear panel is re-datumed
-------------------------------------------------
v1 counter-rotates *both* rear connector families on the vertical variant, so
their long axes stay horizontal in the finished attitude.  That is correct for
the SC/APC adapters — their 22 mm flange is longer than the *horizontal*
variant's back panel is tall, which is the constraint REQUIREMENTS.md §4 is
describing.  It is wrong for the DE-9, and the arithmetic says so:

    usable canonical z, floor top (3.0) to parting face (29.72) = 26.72 mm
    DE-9 needs, jackscrew span 25.0 + hole dia 3.2               = 28.20 mm

It does not fit, and forcing it produces four coupled defects that every
existing variant carries:

  1. the upper jackscrew leaves a 0.12 mm ligament to the parting face —
     unmanufacturable in any process;
  2. the lower jackscrew sits exactly on the interior floor plane, so 42.75 mm³
     of its nut envelope is solid floor and it cannot be nutted from inside;
  3. the 24 mm rear keep-out spans neither jackscrew, so the test that proves
     the keep-out is empty proves nothing about the hardware;
  4. the connector flange lands 0.10 mm from the wall-mount plane and crosses
     the parting face by 1.18 mm.

On a vertical housing the back panel is 92.2 mm tall and only 32.7 mm wide, so
the roomy axis is the height.  Leaving the DE-9 footprint *un*-rotated puts its
long axis along that axis and resolves all four at once, with 6.70 mm to the SC
adapter flanges.  The choice is parametric (`panel_connector.footprint_axis`);
`"width"` restores the v1 arrangement.

The SC/APC adapters are deliberately *not* re-datumed.  They have no defect:
their flange fits, their M2 pilots are blind and self-tapping so no interior
access is needed, and their corridors verify clear.  Rotating them would buy
only a larger mount-face edge radius, at the cost of changing the canonical
fit check's adapter placement — not a trade worth making.


Thermal position, stated honestly
---------------------------------
This housing is **closed, not vented**.  There is no Zonu datasheet anywhere in
this repository, so no module dissipation figure in it is sourced; the two that
exist disagree by 2.5x.  Rather than size louvers against an invented number:

  * buoyancy over the connected interior is ~0.076 Pa (~0.18 m/s) — a passive
    louver moves no useful heat at this scale;
  * the cover's registration gap is already ~150 mm² of uncontrolled open area
    and produces no measurable benefit, which is the empirical refutation;
  * ~70% of the thermal resistance is getting heat off the can *inside* the
    box, which venting cannot touch;
  * these are SC/APC ferrules, and a louver aimed at a bay is a dust path to an
    angled endface.

Sealed conduction-cooled, drained, is the coherent answer.  The measured
sensitivity is ~13 K/W module-case-to-ambient; see DESIGN.md.  Measure the
supply current before committing to any thermal claim.

Units: mm throughout.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import cadquery as cq

FAMILY_DIR = Path(__file__).parent
CANONICAL_MODEL = FAMILY_DIR / "model.py"


def _load_canonical():
    spec = importlib.util.spec_from_file_location("oz51x_canonical_model", CANONICAL_MODEL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_canon = _load_canonical()

# Re-exported unchanged.  orient_to_mounting in particular must stay identical:
# every probe in the shared suite is built in the canonical frame and pushed
# through it, and the canonical fit check hard-codes a transform that mirrors
# it using envelope_width and outer_half_x.
load_params_file = _canon.load_params_file
orient_to_mounting = _canon.orient_to_mounting


# ---------------------------------------------------------------------------
# Refinement parameters
# ---------------------------------------------------------------------------
# Defaults live here so the geometry is complete without them; every value is
# overridable from params.json under "production".  Numbers are justified in
# DESIGN.md — the ones that came out of a solver rather than a preference are
# marked.
DEFAULTS = {
    "edges": {
        # Canonical |Z edges are the four corners of the finished front
        # silhouette — the dominant view.  2.0-2.5 is the right scale on a
        # 32.7 mm-wide part (DESIGN_LANGUAGE's R8-R16 is calibrated to
        # enclosure-scale parts like the am59 family).
        "plan_radius": 2.5,
        # Matched chamfers either side of the parting line read as a
        # deliberate V-groove reveal instead of a raw butt joint.
        "parting_reveal": 0.6,
        # Capped by the SC/APC adapter flange, whose lower edge reaches
        # canonical z = 0.64 on the back wall.  0.4 keeps 0.24 mm clear and
        # still breaks the bed-face edge.
        "mount_face_break": 0.4,
        "cover_perimeter_chamfer": 1.2,
    },
    "mount_flange": {
        "enabled": True,
        "extension": 12.0,  # past +/-outer_half_x, canonical X
        "thickness": 3.0,
        "corner_radius": 6.0,
        "edge_chamfer": 1.0,
        "slot_width": 4.5,  # M4 / #8 pan head
        "slot_length": 9.0,  # runs along depth, to absorb hole-position error
        "slot_y": [-22.0, 74.0],
        "gusset_height": 9.0,
        "gusset_thickness": 2.5,
        "gusset_inset": 6.0,  # from each flange end
    },
    "mount_drainage": {
        "enabled": True,
        # Grooves MUST run along canonical X: that is the vertical direction in
        # the finished attitude.  A groove along Y would be horizontal, i.e. a
        # trap rather than a drain.  V-section so it self-supports and does not
        # hold a meniscus.
        "groove_width": 2.6,
        "groove_depth": 0.7,
        # Chosen clear of every pilot that starts inside the floor slab: the
        # M3 module bosses sit at y = -27.43 and +28.07 in each bay.
        "groove_y": [-10.0, 10.0, 50.0, 76.0],
    },
    "rear_panel": {
        "flange_recess_depth": 0.8,
        "flange_recess_clearance": 0.4,
        "de9_flange_long": 30.8,
        "de9_flange_short": 12.55,
        "sc_flange_corner_radius": 1.5,
        # Restores the M2 thread engagement the flange well costs, on the
        # four screws that are the fiber ports' entire retention.  The Z
        # extent is capped by the SC body corridor (canonical z 5.24..18.04)
        # against pads at z 2.64 and 20.64 — 4.2 leaves 0.5 mm.  The X
        # extent is free, so the pad is a racetrack rather than a peg.
        "sc_pilot_boss_dia": 4.2,
        "sc_pilot_boss_length": 8.0,
        "sc_pilot_boss_height": 3.0,
    },
    "cover": {
        # "groove"  a reveal groove on a rounded-rectangle path (FDM answer)
        # "recess"  a recessed field with full-thickness lands (the v1 answer)
        #
        # The cover prints outer-face-down, so a recessed field is a pocket
        # opening onto the bed: 5 958 mm2 of unsupported 0.8 mm bridging with
        # spans to 28 mm, on the show face, and bed contact on the part most
        # likely to curl drops to 47%.  A 1.5 mm groove on the same path reads
        # as the same framed panel, bridges 1.5 mm, and costs 5% of the contact.
        "field_style": "groove",
        "groove_width": 1.5,
        "groove_depth": 0.8,
        "recess_margin": 6.0,
        "recess_corner_radius": 3.0,
        # recess mode only
        "recess_depth": 0.8,
        "land_width": 9.0,
        "lip_lead_in": 1.2,
        # The lip's lowest segment in the finished attitude hangs above each bay
        # floor over its whole length — a 66 mm capillary slot that no drain
        # placement can empty.  Relieve it.
        "lip_drain_relief": 1.2,
        # The insert bosses are wider than the posts the canonical lid builder
        # scalloped for.  A round scallop big enough leaves a 0.75 mm sliver of
        # lip pad standing in the build direction, three times per bay — so cut
        # the pad's rib-side run away locally instead of leaving splinters.
        "boss_relief_margin": 0.8,
    },
    "posts": {
        # (+/-39.10, +53.25): the only addition that makes the cover pattern
        # symmetric while staying legal.  Solver clearance +3.696 mm to the SC
        # corridors; wall slack 1.000 mm, matching the existing rear pair.
        "extra_lid_posts": [[-39.10, 53.25], [39.10, 53.25]],
        # A Dia2.5 x 26.72 blind bore is L/D 10.7 — over the powder-evacuation
        # limit, and 17 mm of it is bore no screw ever reaches.  Fill from the
        # floor up, leaving this much thread depth below the parting face.
        "pilot_thread_depth": 10.0,
        # The 1.0 mm dead gap between each plenum post and the wall it sits
        # against serves nothing.  Web it in — on a powder bed it was a powder
        # trap; on FDM it is worse, because a free-standing tower goes soft
        # around the boss while a heat-set insert is being pressed into it.
        "corner_web": True,
        # The M3 module-boss pilots start at z = 0.5, leaving a 0.5 mm web on
        # the mount face — thinner than any process here will hold.
        "boss_pilot_start": 1.0,
    },
    "cover_fastening": {
        # "heat_set"    brass inserts, screws from the cover side (FDM answer)
        # "thread_form" screws formed directly into printed pilots (the v1
        #               answer; correct for MJF PA12, not for FDM)
        "mode": "heat_set",
        # ruthex RX-M3x5.7 / CNC Kitchen M3x5.7 — dimensionally interchangeable.
        # OD is the knurl diameter; the hole is NOT the OD.
        "insert_family": "ruthex RX-M3x5.7 (CNC Kitchen M3x5.7 interchangeable)",
        "insert_od": 4.6,
        "insert_length": 5.7,
        # 4.0 is the manufacturer's drilled-hole figure (ruthex D3, and their
        # drill set ships one 4.0 mm bit for M2.5/M3).  For an AS-PRINTED FDM
        # hole CNC Kitchen measured ~0.25 mm undersize and recommend modelling
        # 4.2, which pre-seats the insert and avoids the burr that forms under
        # it at 4.0 — at ~90% of peak pull-out.  Across all insert families the
        # hole ranges 3.7-5.2, so this number belongs to the family named above.
        "hole_dia": 4.2,
        # Insert length + 1.0 relief well.  The melt is displaced downward; with
        # no well it clogs the thread or holds the insert proud, and the parting
        # face is a registration face so proud is not survivable.
        "hole_depth": 6.7,
        # 8.5 - 4.2 = 2.15 mm wall.  Clears ruthex W min 1.6 and Tappex 1.70,
        # and exceeds Tappex's stated D1 min of 7.4 for M3.  ("Boss OD >= 2x
        # insert OD" is web folklore — no insert maker states it.)
        "boss_dia": 8.5,
        # The module cans cap a centreline boss at Ø7.0 up to z = 16.72.  Flare
        # above that, as a 45 deg cone so it is self-supporting rather than a
        # 0.75 mm radial step printed in mid-air.
        "boss_flare_z": 16.72,
        "thread_depth": 10.0,  # thread_form mode only
        "screw": "ISO 7380-1 M3x8 button head, A2 stainless",
    },
    "spool": {
        "lighten": True,
        "inner_dia": 21.0,
        "hub_dia": 8.0,
        "web_count": 4,
        "web_thickness": 2.4,
        # Retention flange on the cover side only: that is the side wraps
        # escape from when the cover is off.  A floor-side flange retains
        # nothing and is pure mass.
        "flange_overhang": 1.5,
        "flange_thickness": 1.2,
    },
    "drains": {
        "enabled": True,
        # Every drain's axis lies in the bed plane, so a round bore's crown is
        # an unsupported arch: it stays open at Ø3 but droops 0.2-0.3 mm and
        # hangs strands inside the bore.  These are the one set of holes on the
        # part whose entire job is to NOT retain water.  A hexagon with a vertex
        # up is self-supporting and carries more area (7.79 vs 7.07 mm2).
        "profile": "hex",
        "dia": 3.0,
        # floor + r - 0.05: the mouth undercuts the interior wall face by
        # 0.05 mm so the floor-to-wall corner drains with no retained film,
        # and the crown stays 0.05 mm below the module plate at z = 6.0.
        "z": 4.45,
        "rib_cross_y": [-22.0, 22.0],  # solver: 1.501 mm to both modules
        "outlet_y": [-22.0, 22.0, 44.25],
        "outlet_chamfer": 0.5,
    },
    "anchors": {
        "enabled": True,
        "dia": 3.0,
        "height": 6.0,
        "xy": [[-33.0, 42.0], [33.0, 42.0]],
    },
    "labels": {
        "enabled": True,
        # Arial's stem is ~0.133 of cap height, so a 3.6 mm cap gives a 0.48 mm
        # stroke — under half the ~1.0 mm an engraved FDM stroke needs before
        # the perimeters either side merge and the letter fills in.  Sizes below
        # are set from that ratio, not from taste.
        "font": "Arial",
        "depth": 0.6,
        # The cover's outer face is the bed face, so a raised glyph there would
        # collide with the bed: the identity must stay engraved, and gets bigger
        # instead.  8.0 mm cap -> 1.06 mm stroke.
        "identity_size": 8.0,
        # The front wall is vertical in the print, where an embossed stroke can
        # go much finer than an engraved one — a single extrusion renders it.
        # 6.5 mm cap -> 0.86 mm stroke, and 0.6 mm proud is 1.5 extrusions.
        "port_style": "emboss",
        "port_size": 6.5,
        "port_relief": 0.6,
        # canonical +Z from the SMA axis = horizontally beside the port once
        # installed; clears the Dia7 barrel hole (crown at z+3.5).
        "port_offset": 11.0,
        "mark_size": 5.0,
        # Provenance marking, off by default: it is branding on a part that
        # carries no other branding, and the identity + port labels are the
        # only markings that do a job.  Set a string to re-enable.
        "mark": "",
    },
}


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def production(params: dict) -> dict:
    """Resolved refinement parameters."""
    return _merge(DEFAULTS, params.get("production", {}))


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def layout(params: dict) -> dict:
    """
    The canonical layout plus this refinement's derived values.

    Every canonical key is passed through untouched with one exception:
    `envelope_height` grows to include the mount flanges, because the shared
    suite asserts the built bounding box against these numbers.

    `envelope_width` is deliberately NOT touched.  The canonical fit check
    places the SC adapters using `fiber_z - envelope_width/2`, so any growth on
    the width axis lands them off-face and reports phantom interference.  All
    refinement growth goes onto the height axis.
    """
    L = _canon.layout(params)
    p = production(params)
    L["production"] = p

    flange = p["mount_flange"]
    L["has_flanges"] = bool(flange["enabled"])
    L["flange_ext"] = flange["extension"] if L["has_flanges"] else 0.0
    if L["has_flanges"] and L["mounting_orientation"] == "vertical":
        L["envelope_height"] = 2.0 * L["outer_half_x"] + 2.0 * L["flange_ext"]

    # Embossed port labels stand proud of the front wall, so they are part of
    # the envelope.  Note this grows envelope_depth ONLY — total_depth is the
    # body and every geometry call still uses that.
    lb = p["labels"]
    L["label_relief"] = (
        lb["port_relief"]
        if lb["enabled"] and lb.get("port_style", "engrave") == "emboss"
        else 0.0
    )
    L["envelope_depth"] = L["total_depth"] + L["label_relief"]

    # Canonical (x, y) of every cover screw, in one place, so the base posts,
    # the cover counterbores and the tests all read the same list.
    post_r = params["housing"]["corner_post_dia"] / 2.0
    L["lid_screw_xy"] = [
        (0.0, -(L["interior_half_y"] - post_r - 1.0)),
        (0.0, 0.0),
        (0.0, +(L["interior_half_y"] - post_r - 1.0)),
        (0.0, L["spool_y"]),
        (-(L["interior_half_x"] - post_r - 1.0), L["plenum_y1"] - post_r - 1.0),
        (+(L["interior_half_x"] - post_r - 1.0), L["plenum_y1"] - post_r - 1.0),
    ] + [tuple(xy) for xy in p["posts"]["extra_lid_posts"]]
    return L


# ---------------------------------------------------------------------------
# Small geometry helpers
# ---------------------------------------------------------------------------
def _z_cyl(r: float, x: float, y: float, z0: float, h: float) -> cq.Workplane:
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))


def _x_cyl(r: float, x0: float, y: float, z: float, length: float) -> cq.Workplane:
    solid = cq.Solid.makeCylinder(r, length, cq.Vector(x0, y, z), cq.Vector(1, 0, 0))
    return cq.Workplane("XY").newObject([solid])


def _y_cyl(r: float, x: float, z: float, y0: float, length: float) -> cq.Workplane:
    solid = cq.Solid.makeCylinder(r, length, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))
    return cq.Workplane("XY").newObject([solid])


def _rounded_slab(w: float, d: float, h: float, r: float, origin) -> cq.Workplane:
    """Axis-aligned slab with radiused vertical edges, bottom face at origin[2]."""
    s = cq.Workplane("XY").box(w, d, h, centered=(True, True, False)).translate(origin)
    return s.edges("|Z").fillet(r) if r > 0 else s


def _rounded_plate_yz(w: float, h: float, t: float, r: float, centre) -> cq.Workplane:
    """A plate in the Y-Z plane (normal +X), radiused corners, centred on `centre`."""
    s = cq.Workplane("XY").box(w, h, t, centered=(True, True, True))
    if r > 0:
        s = s.edges("|Z").fillet(r)
    return s.rotate((0, 0, 0), (0, 1, 0), 90).translate(centre)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
def _canonical_without_rear_connector(params: dict) -> dict:
    """
    Params with `panel_connector` removed.

    The canonical builder cuts the rear connector with the vertical
    counter-rotation baked in.  Suppressing it there and cutting our own
    re-datumed footprint here keeps the shared builder untouched — the
    alternative would be editing shared code that eight other variants use.
    """
    bare = {k: v for k, v in params.items() if k != "panel_connector"}
    return bare


def _trim_solid(L: dict, p: dict) -> cq.Workplane:
    """
    The body's outer envelope with its edge treatment, as one simple solid.

    Intersecting with this is how the exterior gets its edge language.  A late
    `.edges().fillet()` on the finished tray would also catch every interior
    vertical edge — the bay cavities, the posts, the partition — and is the
    kernel-failure mode DESIGN_LANGUAGE warns about.  A single intersect
    against a simple prism touches only the four outer corners.
    """
    e = p["edges"]
    trim = _rounded_slab(
        2.0 * L["outer_half_x"],
        L["total_depth"],
        L["base_height"],
        e["plan_radius"],
        (0.0, (L["back_outer_y"] - L["outer_half_y"]) / 2.0, 0.0),
    )
    if e["parting_reveal"] > 0:
        trim = trim.edges(">Z").chamfer(e["parting_reveal"])
    if e["mount_face_break"] > 0:
        trim = trim.edges("<Z").chamfer(e["mount_face_break"])
    return trim


def _cut_rear_connector(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """The re-datumed DE-9: body cutout, jackscrews, and a flange well."""
    pc = params.get("panel_connector")
    if not pc:
        return base
    h = params["housing"]
    rp = p["rear_panel"]
    pc_z = L["panel_connector_z"]
    swapped = (
        L["mounting_orientation"] == "vertical" and pc.get("footprint_axis", "width") == "width"
    )
    cut_w = pc["cutout_h"] if swapped else pc["cutout_w"]
    cut_h = pc["cutout_w"] if swapped else pc["cutout_h"]

    base = base.cut(
        cq.Workplane("XY")
        .box(cut_w, h["wall"] + 2.0, cut_h, centered=(True, True, True))
        .translate((pc["x"], L["plenum_y1"] + h["wall"] / 2.0, pc_z))
    )
    for off in (-pc["screw_spacing"] / 2.0, +pc["screw_spacing"] / 2.0):
        px = pc["x"] if swapped else pc["x"] + off
        pz = pc_z + off if swapped else pc_z
        base = base.cut(
            _y_cyl(pc["screw_hole_dia"] / 2.0, px, pz, L["plenum_y1"] - 1.0, h["wall"] + 2.0)
        )

    # Flange well: locates the connector flange and gives water an edge to
    # leave by instead of a flat face to sit on.
    depth = rp["flange_recess_depth"]
    clr = rp["flange_recess_clearance"]
    long_ax = rp["de9_flange_long"] + 2 * clr
    short_ax = rp["de9_flange_short"] + 2 * clr
    well_w = short_ax if swapped else long_ax
    well_h = long_ax if swapped else short_ax
    base = base.cut(
        cq.Workplane("XY")
        .box(well_w, depth + 0.1, well_h, centered=(True, True, True))
        .translate((pc["x"], L["back_outer_y"] - depth / 2.0 + 0.05, pc_z))
    )
    return base


def _sc_flange_wells(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """Recess each SC/APC flange, and put the M2 thread engagement back."""
    h, ad = params["housing"], params["sc_adapter"]
    rp = p["rear_panel"]
    depth = rp["flange_recess_depth"]
    clr = rp["flange_recess_clearance"]
    vertical = L["mounting_orientation"] == "vertical"

    well_w = (ad["flange_wide"] if vertical else ad["flange_len"]) + 2 * clr
    well_h = (ad["flange_len"] if vertical else ad["flange_wide"]) + 2 * clr
    for ax in L["adapter_x"]:
        well = cq.Workplane("XY").box(well_w, well_h, depth + 0.1, centered=(True, True, True))
        well = well.edges("|Z").fillet(rp["sc_flange_corner_radius"])
        well = well.rotate((0, 0, 0), (1, 0, 0), 90).translate(
            (ax, L["back_outer_y"] - depth / 2.0 + 0.05, L["fiber_z"])
        )
        base = base.cut(well)

        # The well costs 0.8 mm of the 3.0 mm wall, taking M2 engagement to
        # 2.2 mm (1.1 d) on the four screws that are the fiber ports' entire
        # retention.  A pad on the interior face restores it to ~5.2 mm.
        #
        # A racetrack rather than a round peg: elongating along canonical X is
        # free (the two adapters are 56 mm apart and the DE-9 keep-out only
        # spans x +/-16), while elongating along canonical Z is not — the SC
        # body corridor runs z 5.24..18.04 and the pads sit at z 2.64 and
        # 20.64.  The underside is chamfered at 45 deg so the pad does not
        # print as an unsupported ledge hanging off the wall.
        bh = rp["sc_pilot_boss_height"]
        bz = rp["sc_pilot_boss_dia"]
        bx = rp.get("sc_pilot_boss_length", bz)
        if bz > 0 and bh > 0:
            for off in (-ad["screw_spacing"] / 2.0, +ad["screw_spacing"] / 2.0):
                px = ax if vertical else ax + off
                pz = L["fiber_z"] + off if vertical else L["fiber_z"]
                # XZ workplane: local x -> canonical X, local y -> canonical Z,
                # extruding along -Y, i.e. inboard from the wall's inner face.
                pad = (
                    cq.Workplane("XZ")
                    .slot2D(bx, bz, 0)
                    .extrude(bh)
                    .translate((px, L["plenum_y1"], pz))
                )
                base = base.union(pad)
                # 45 deg relief under the pad: its depth grows from zero at the
                # bottom edge to full at 45 deg, so every layer is carried by
                # the wall or by the layer below it rather than hanging.
                z_lo = pz - bz / 2.0
                y1 = L["plenum_y1"]
                wedge = (
                    cq.Workplane("YZ")
                    .polyline([(y1, z_lo), (y1 - bh, z_lo), (y1 - bh, z_lo + bh)])
                    .close()
                    .extrude(bx + 2.0)
                    .translate((px - (bx + 2.0) / 2.0, 0.0, 0.0))
                )
                base = base.cut(wedge)
                base = base.cut(
                    _y_cyl(
                        ad["screw_pilot_dia"] / 2.0,
                        px,
                        pz,
                        L["plenum_y1"] - rp["sc_pilot_boss_height"] - 0.5,
                        h["wall"] + rp["sc_pilot_boss_height"] + 1.0,
                    )
                )
    return base


def _mount_flanges(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    Wall-mount flanges, coplanar with the canonical floor plane.

    v1 has no way to attach the enclosure to anything at all.  The flanges sit
    flush with the mount face (they never protrude past it, so the finished
    width is untouched), lie flat on the print bed in the natural orientation,
    and carry slotted holes running along the depth so hole-position error is
    absorbed by sliding rather than by reaming.
    """
    f = p["mount_flange"]
    if not f["enabled"] or L["mounting_orientation"] != "vertical":
        return base
    t = f["thickness"]
    ext = f["extension"]
    y0 = -L["outer_half_y"]
    depth = L["total_depth"]

    for sgn in (-1.0, +1.0):
        # Plate spans from just inside the wall out to outer_half_x + ext, so
        # it fuses to the body rather than merely touching it.
        inner = sgn * (L["outer_half_x"] - 2.0)
        outer = sgn * (L["outer_half_x"] + ext)
        cx = (inner + outer) / 2.0
        w = abs(outer - inner)
        plate = _rounded_slab(w, depth, t, f["corner_radius"], (cx, y0 + depth / 2.0, 0.0))
        if f["edge_chamfer"] > 0:
            # Break the outboard edge of the flange — the one a hand meets.
            plate = plate.faces(">Z").edges().chamfer(f["edge_chamfer"])
        base = base.union(plate)

        # Gusset: a triangular web from the flange up to the wall.  In the
        # print orientation every layer is smaller than the one below it, so
        # it is self-supporting.
        gh = f["gusset_height"]
        gt = f["gusset_thickness"]
        gy0 = y0 + f["gusset_inset"]
        gy1 = y0 + depth - f["gusset_inset"]
        tri = (
            cq.Workplane("XZ")
            .polyline(
                [
                    (sgn * L["outer_half_x"], t),
                    (sgn * (L["outer_half_x"] + ext - 1.0), t),
                    (sgn * L["outer_half_x"], t + gh),
                ]
            )
            .close()
            .extrude(gt)
            .translate((0.0, gy0 + gt / 2.0, 0.0))
        )
        base = base.union(tri)
        tri2 = tri.translate((0.0, gy1 - gy0 - gt, 0.0))
        base = base.union(tri2)

        for sy in f["slot_y"]:
            slot = (
                cq.Workplane("XY")
                .center(sgn * (L["outer_half_x"] + ext / 2.0 + 1.0), sy)
                .slot2D(f["slot_length"], f["slot_width"], 90)
                .extrude(t + 2.0)
                .translate((0.0, 0.0, -1.0))
            )
            base = base.cut(slot)
    return base


def _mount_face_drainage(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    V-grooves in the mount face so water between the enclosure and the wall has
    somewhere to go.

    They run along canonical X, which is the *vertical* direction once the
    housing is installed; a groove along Y would be horizontal and would hold
    water rather than shed it.  They continue out across the flanges so they
    actually daylight.
    """
    md = p["mount_drainage"]
    if not md["enabled"] or L["mounting_orientation"] != "vertical":
        return base
    half_w = md["groove_width"] / 2.0
    d = md["groove_depth"]
    reach = L["outer_half_x"] + p["mount_flange"]["extension"] + 2.0
    for gy in md["groove_y"]:
        # V-section: a 90 deg wedge, so it self-supports and breaks the
        # meniscus a flat-bottomed groove would hold.
        wedge = (
            cq.Workplane("YZ")
            .polyline([(-half_w, -0.01), (half_w, -0.01), (0.0, d)])
            .close()
            .extrude(2.0 * reach)
            .translate((-reach, gy, 0.0))
        )
        base = base.cut(wedge)
    return base


def _post_reinforcement(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """Add the two new posts, then web every plenum post into its wall."""
    h = params["housing"]
    po = p["posts"]
    post_r = h["corner_post_dia"] / 2.0

    for px, py in po["extra_lid_posts"]:
        base = base.union(_z_cyl(post_r, px, py, 0.0, L["base_height"]))

    if po["corner_web"]:
        # Every plenum post clears the side wall by exactly 1.0 mm.  That gap
        # braces nothing: on a powder bed it was a powder trap, and on FDM it
        # is worse — pressing a heat-set insert momentarily softens the boss,
        # and a free-standing tower bulges, tilts or shears at the root while
        # a webbed one is held by the wall.  All four plenum posts get webbed,
        # not just the two rear corners.
        keep = cq.Workplane("XY").box(
            2.0 * L["interior_half_x"],
            2.0 * L["plenum_y1"],
            4.0 * L["base_height"],
            centered=(True, True, True),
        )
        rear_y = L["plenum_y1"] - post_r - 1.0
        sites = [(sgn * (L["interior_half_x"] - post_r - 1.0), rear_y) for sgn in (-1.0, 1.0)]
        sites += [tuple(xy) for xy in po["extra_lid_posts"]]
        for px, py in sites:
            sgn = 1.0 if px > 0 else -1.0
            x_reach = L["interior_half_x"] - abs(px) + post_r
            # A post sitting against the back wall gets webbed to that too.
            y_hi = max(py + post_r, L["plenum_y1"] if py + post_r + 1.5 >= L["plenum_y1"] else 0.0)
            web = (
                cq.Workplane("XY")
                .box(
                    x_reach,
                    y_hi - (py - post_r),
                    L["base_height"] - h["floor"],
                    centered=(False, False, False),
                )
                .translate((px if sgn > 0 else px - x_reach, py - post_r, h["floor"]))
            )
            base = base.union(web.intersect(keep))
    return base


def _cover_anchors(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    How the cover is held on.

    The canonical builder bores a Ø2.5 pilot the full 26.72 mm interior height
    at every cover-screw post and expects a screw to form its own thread in it.
    That is right for MJF PA12 and wrong for FDM, and the reason is torque, not
    pull-out: measured in PETG, a screw formed directly into the plastic and a
    brass heat-set insert pull out at the same load (118 vs 119 kg), but the
    formed thread strips at ~1 Nm against the insert's 3 Nm — and 1 Nm is about
    the minimum sensible assembly torque for M3.  A formed FDM thread therefore
    has no torque margin on FIRST assembly, before service life is even
    considered.  Add that the cover is fitted blind and sideways onto a
    wall-mounted unit, where restarting a formed thread in its own helix is
    exactly the cross-threading case, and the insert wins.

    So: fill the canonical pilot solid, flare the post above the can to carry an
    insert, and bore the insert's own hole.  `mode: "thread_form"` restores the
    original behaviour for anyone printing this in a powder bed.
    """
    h = params["housing"]
    po = p["posts"]
    cf = p["cover_fastening"]
    pilot_r = h["corner_post_pilot_dia"] / 2.0
    z_top = L["base_height"]

    # 1. Fill every canonical pilot.  Each mode re-cuts its own.
    for px, py in L["lid_screw_xy"]:
        base = base.union(_z_cyl(pilot_r - 0.001, px, py, h["floor"], z_top - h["floor"] + 0.6))

    if cf["mode"] == "heat_set":
        boss_r = cf["boss_dia"] / 2.0
        post_r = h["corner_post_dia"] / 2.0
        flare_z = cf["boss_flare_z"]
        rise = max(boss_r - post_r, 0.0)  # 45 deg, so rise == radial growth
        for px, py in L["lid_screw_xy"]:
            # 2. Flare: a 45 deg cone off the post, then a straight boss to the
            #    parting face.  Cone rather than step so nothing prints in air.
            if rise > 0:
                cone = cq.Solid.makeCone(
                    post_r, boss_r, rise, cq.Vector(px, py, flare_z), cq.Vector(0, 0, 1)
                )
                base = base.union(cq.Workplane("XY").newObject([cone]))
            base = base.union(_z_cyl(boss_r, px, py, flare_z + rise, z_top - flare_z - rise))
            # 3. The insert's hole: straight, no mouth chamfer (Tappex specify a
            #    chamfer only from M4 up; CNC Kitchen say none), bottomed on a
            #    relief well so displaced melt has somewhere to go.
            base = base.cut(
                _z_cyl(
                    cf["hole_dia"] / 2.0,
                    px,
                    py,
                    z_top - cf["hole_depth"],
                    cf["hole_depth"] + 0.5,
                )
            )
    else:
        for px, py in L["lid_screw_xy"]:
            base = base.cut(
                _z_cyl(
                    pilot_r,
                    px,
                    py,
                    z_top - cf["thread_depth"],
                    cf["thread_depth"] + 0.5,
                )
            )

    # M3 module-boss pilots start at z = 0.5, leaving a 0.5 mm web on the
    # mount face — thinner than any process here will hold.
    start = po["boss_pilot_start"]
    if start > 0.5:
        m = params["module"]
        sb_pilot_r = h["screw_boss_pilot_dia"] / 2.0
        for bay, cx in zip(L["bays"], L["bay_cx"]):
            sign = -1.0 if bay.get("mirror_x") else 1.0
            for hole in (m["screw_hole_front"], m["screw_hole_back"]):
                base = base.union(
                    _z_cyl(
                        sb_pilot_r - 0.001,
                        cx + sign * hole["x"],
                        -hole["z"],
                        0.5,
                        start - 0.5,
                    )
                )
    return base


def _lighten_spool(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    Hollow the slack spool into a drum on webs.

    The fiber-contact radius, the lid-screw hub and the spool's position are
    untouched; only dead material inside the drum goes.  The single retention
    flange is on the cover side, which is the side wraps leave from when the
    cover is off — a floor-side flange retains nothing.
    """
    sp = p["spool"]
    if not sp["lighten"]:
        return base
    fb = params["fiber_bay"]
    h = params["housing"]
    outer_r = fb["spool_dia"] / 2.0
    inner_r = sp["inner_dia"] / 2.0
    hub_r = sp["hub_dia"] / 2.0
    if inner_r <= hub_r:
        return base

    void = _z_cyl(inner_r, 0.0, L["spool_y"], h["floor"], L["base_height"] - h["floor"] + 1.0)
    keep = _z_cyl(hub_r, 0.0, L["spool_y"], h["floor"], L["base_height"] - h["floor"] + 1.0)
    for i in range(sp["web_count"]):
        ang = i * 180.0 / sp["web_count"]
        web = (
            cq.Workplane("XY")
            .box(
                2.0 * inner_r,
                sp["web_thickness"],
                L["base_height"] - h["floor"] + 1.0,
                centered=(True, True, False),
            )
            .rotate((0, 0, 0), (0, 0, 1), ang)
            .translate((0.0, L["spool_y"], h["floor"]))
        )
        keep = keep.union(web)
    base = base.cut(void.cut(keep))

    if sp["flange_overhang"] > 0 and sp["flange_thickness"] > 0:
        ft = sp["flange_thickness"]
        flange = _z_cyl(
            outer_r + sp["flange_overhang"], 0.0, L["spool_y"], L["base_height"] - ft, ft
        )
        flange = flange.cut(_z_cyl(hub_r, 0.0, L["spool_y"], L["base_height"] - ft - 0.5, ft + 1.0))
        base = base.union(flange)
    return base


def _drains(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    Gravity drainage for the finished attitude, where canonical +X is down.

    The upper bay's low point is the top of the central rib, 45.1 mm above the
    finished bottom face, and the partition pass-slot sills sit 5.18 mm above
    both bay floors — so neither a bottom-face slot nor the pass-slots can
    empty it.  The only path out is *through* the rib.  Cross-drains carry the
    upper bay into the lower bay; wall outlets take the lower bay and the
    plenum outside.  Everything sits below the module plate.
    """
    d = p["drains"]
    if not d["enabled"] or L["mounting_orientation"] != "vertical":
        return base
    h = params["housing"]
    r = d["dia"] / 2.0
    z = d["z"]

    def bore(x0: float, dy: float, length: float) -> cq.Workplane:
        if d.get("profile", "round") != "hex":
            return _x_cyl(r, x0, dy, z, length)
        # Regular hexagon, `dia` across the flats, one vertex up in canonical
        # +Z.  The YZ workplane puts local x on canonical Y and local y on
        # canonical Z, extruding along +X — which is the drain axis.
        rc = d["dia"] / math.sqrt(3.0)  # circumradius from across-flats
        pts = [
            (rc * math.cos(math.radians(a)), rc * math.sin(math.radians(a)))
            for a in (90, 150, 210, 270, 330, 30)
        ]
        return cq.Workplane("YZ").polyline(pts).close().extrude(length).translate((x0, dy, z))

    for dy in d["rib_cross_y"]:
        base = base.cut(bore(-h["bay_gap"] / 2.0 - 1.0, dy, h["bay_gap"] + 2.0))
    for dy in d["outlet_y"]:
        base = base.cut(bore(L["interior_half_x"] - 1.0, dy, h["wall"] + 2.0))
        # A chamfered mouth sheds water off an edge instead of beading on the
        # flat exit face.  The cone opens OUTWARD: built the other way round it
        # is a re-entrant lip that water has to climb to leave — which is
        # exactly the bead it is supposed to prevent.
        c = d["outlet_chamfer"]
        if c > 0:
            cone = cq.Solid.makeCone(
                r,
                r + c,
                c,
                cq.Vector(L["outer_half_x"] - c, dy, z),
                cq.Vector(1, 0, 0),
            )
            base = base.cut(cq.Workplane("XY").newObject([cone]))
    return base


def _cable_anchors(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """Tie-down posts on the plenum floor for the pigtails and the DE-9 harness."""
    a = p["anchors"]
    if not a["enabled"]:
        return base
    h = params["housing"]
    for ax, ay in a["xy"]:
        base = base.union(_z_cyl(a["dia"] / 2.0, ax, ay, h["floor"], a["height"]))
    return base


def _engrave(solid: cq.Workplane, text_wp: cq.Workplane) -> cq.Workplane:
    """
    Cut engraved text.

    Deliberately not wrapped in try/except: a swallowed boolean failure would
    silently ship a part with no marking, which is the same class of mistake as
    reading a failed intersection as zero interference.
    """
    return solid.cut(text_wp)


def _text_blank(txt: str, size: float, depth: float, font: str) -> cq.Workplane:
    """A text solid lying in XY, baseline along +X, extruded +Z, centred on the origin."""
    return cq.Workplane("XY").text(txt, size, depth, font=font, halign="center", valign="center")


def _base_labels(base: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    Port identification beside each SMA, on the front face.

    Oriented to read horizontally in the finished attitude: baseline along
    canonical Z, glyph up along canonical -X (which is finished up).
    """
    lb = p["labels"]
    if not lb["enabled"]:
        return base
    m = params["module"]
    y_face = -L["outer_half_y"]
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        sma_x = cx + sign * m["sma_axis_x"]
        txt = "RF" if abs(cx - L["bay_cx"][0]) < 1e-6 else "TTL"
        emboss = lb.get("port_style", "engrave") == "emboss"
        relief = lb["port_relief"] if emboss else lb["depth"]
        blank = _text_blank(txt, lb["port_size"], relief, lb["font"])
        # baseline -> canonical +Z, cap height -> canonical -X (finished up),
        # extrusion -> +Y (into the front wall from outside).
        blank = blank.rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 1, 0), -90)
        # Offset along canonical Z, i.e. horizontally beside the port in the
        # finished attitude, at the port's own height.  Deliberately NOT along
        # canonical X: an X offset has to follow the handed SMA inboard, which
        # would put the label below the port on RX and above it on TX.  A Z
        # offset is handedness-independent, so the two housings mark up
        # identically — which is what "consistency between RX and TX" means
        # for a marking.
        # On a vertical FDM wall an engraved stroke needs ~1.0 mm before the
        # perimeters either side merge and the letter fills in; an embossed one
        # renders as a single extrusion and goes much finer.  So these are
        # raised, not cut — and the wall is vertical in the print, so a raised
        # glyph has no overhang.
        placed = blank.translate(
            (
                sma_x,
                y_face + (0.001 if emboss else relief - 0.001),
                L["plate_bottom_z"] + m["sma_axis_y"] + lb["port_offset"],
            )
        )
        base = base.union(placed) if emboss else _engrave(base, placed)

    # Optional provenance marking on the finished bottom face.  Empty by
    # default — see labels.mark.
    if lb.get("mark"):
        mark = _text_blank(
            f"{lb['mark']} {params.get('version', 'v1').upper()}",
            lb["mark_size"],
            lb["depth"],
            lb["font"],
        )
        mark = mark.rotate((0, 0, 0), (0, 0, 1), 90).rotate((0, 0, 0), (0, 1, 0), 90)
        base = _engrave(
            base,
            mark.translate((L["outer_half_x"] - lb["depth"] + 0.001, 70.0, 14.86)),
        )
    return base


def _create_base_canonical(params: dict) -> cq.Workplane:
    L = layout(params)
    p = production(params)

    base = _canon._create_base_canonical(_canonical_without_rear_connector(params))
    base = base.intersect(_trim_solid(L, p))
    base = _cut_rear_connector(base, params, L, p)
    base = _sc_flange_wells(base, params, L, p)
    base = _lighten_spool(base, params, L, p)
    base = _post_reinforcement(base, params, L, p)
    base = _cover_anchors(base, params, L, p)
    base = _cable_anchors(base, params, L, p)
    base = _drains(base, params, L, p)
    base = _mount_flanges(base, params, L, p)
    base = _mount_face_drainage(base, params, L, p)
    base = _base_labels(base, params, L, p)
    return base


def create_base(params: dict) -> cq.Workplane:
    return orient_to_mounting(_create_base_canonical(params), params)


# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------
def _cover_fields(lid: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    The framed-panel read on the cover's show face, and the screw pattern.

    The cover prints outer-face-down, which is the only orientation that does
    not put a 92 x 133 mm plate on supports.  That makes a recessed field a
    pocket opening onto the bed — 5 958 mm2 of unsupported 0.8 mm bridging with
    spans to 28 mm, on the face people look at, and bed contact on the part
    most likely to curl drops to 47%.  A 1.5 mm reveal groove on the same
    rounded-rectangle path gives the same framed read, bridges 1.5 mm, and
    costs 5% of the bed contact.  `field_style: "recess"` restores the pocket
    version for a powder bed.

    The head counterbore is gone.  A Ø6.0 x 1.6 bore fits no M3 head that
    exists: an ISO 4762 socket cap head is Ø5.5 x 3.0 and would stand 1.4 mm
    proud, and its standard counterbore is Ø6.5 x 3.0, which is the whole
    cover.  An ISO 7380-1 button head (Ø5.7 x 1.65) bearing directly on the
    outer face is the honest answer at this thickness — and that face is the
    bed face, so it is the flattest, squarest seat on the part.
    """
    c = p["cover"]
    m = params["housing"]
    z_top = L["base_height"] + m["lid_thickness"]
    margin = c["recess_margin"]
    field_w = 2.0 * L["outer_half_x"] - 2.0 * margin
    field_d = L["total_depth"] - 2.0 * margin
    y_mid = (L["back_outer_y"] - L["outer_half_y"]) / 2.0

    if c["field_style"] == "recess" and c["recess_depth"] > 0:
        d = c["recess_depth"]
        lw = c["land_width"]
        lid = lid.cut(
            _rounded_slab(
                field_w, field_d, d + 1.0, c["recess_corner_radius"], (0.0, y_mid, z_top - d)
            )
        )
        lands = [
            cq.Workplane("XY")
            .box(lw, field_d, d, centered=(True, True, False))
            .translate((0.0, y_mid, z_top - d))
        ]
        for ly in sorted({y for _, y in L["lid_screw_xy"]}):
            lands.append(
                cq.Workplane("XY")
                .box(field_w, lw, d, centered=(True, True, False))
                .translate((0.0, ly, z_top - d))
            )
        pad_r = m["lid_screw_head_dia"] / 2.0 + 2.0
        for px, py in L["lid_screw_xy"]:
            lands.append(_z_cyl(pad_r, px, py, z_top - d, d))
        for land in lands:
            lid = lid.union(land)
    elif c["groove_depth"] > 0:
        gw = c["groove_width"]
        gd = c["groove_depth"]
        outer = _rounded_slab(
            field_w, field_d, gd + 1.0, c["recess_corner_radius"], (0.0, y_mid, z_top - gd)
        )
        inner = _rounded_slab(
            field_w - 2 * gw,
            field_d - 2 * gw,
            gd + 2.0,
            max(c["recess_corner_radius"] - gw, 0.5),
            (0.0, y_mid, z_top - gd - 0.5),
        )
        lid = lid.cut(outer.cut(inner))

    # One screw pattern, cut once, so the canonical six and the two added ones
    # are guaranteed identical.  Clearance is oversized for FDM: a modelled
    # Ø3.4 prints ~3.2, which leaves ~0.1 mm/side on an M3 across an
    # eight-screw pattern spanning 133 mm in two separately-printed parts.
    lip_depth = params.get("refinement", {}).get("registration_lip_depth", 2.0)
    clr_r = m["lid_screw_clear_dia"] / 2.0
    z0 = L["base_height"]
    # Fill the canonical head counterbores first — this design does not use one.
    head_r = m["lid_screw_head_dia"] / 2.0
    for px, py in L["lid_screw_xy"]:
        lid = lid.union(_z_cyl(head_r - 0.001, px, py, z_top - 1.6, 1.6))
    for px, py in L["lid_screw_xy"]:
        lid = lid.cut(
            _z_cyl(clr_r, px, py, z0 - lip_depth - 0.5, m["lid_thickness"] + lip_depth + 1.5)
        )
    return lid


def _cover_lip_details(lid: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """
    Lead-in chamfer on the lip, and a relief at its lowest segment.

    The cover is fitted blind and sideways onto a wall-mounted unit, so the lip
    needs to self-centre.  Separately, the lip's lowest run in the finished
    attitude hangs 0.30 mm above each bay floor along its whole 66 mm length —
    a capillary slot that no drain placement can empty, because it is the
    lowest thing in the bay.  Relieving that one segment removes the trap.
    """
    c = p["cover"]
    m = params["housing"]
    refine = params.get("refinement", {})
    lip_depth = refine.get("registration_lip_depth", 2.0)
    lip_gap = refine.get("registration_clearance", 0.3)
    z0 = L["base_height"]

    if c["lip_lead_in"] > 0:
        li = c["lip_lead_in"]
        for cx in L["bay_cx"]:
            hw = (L["bay_w"] - 2 * lip_gap) / 2.0
            hd = (L["bay_d"] - 2 * lip_gap) / 2.0
            zt = z0 - lip_depth  # the lip's leading (lowest) face
            # Four 45 deg wedges along the pad's leading edges.  The corners
            # are left square, which is what a blind push actually needs — the
            # long flanks do the centring.
            for sx in (-1.0, +1.0):
                wedge = (
                    cq.Workplane("XZ")
                    .polyline(
                        [
                            (cx + sx * hw, zt),
                            (cx + sx * (hw - li), zt),
                            (cx + sx * hw, zt + li),
                        ]
                    )
                    .close()
                    .extrude(2.0 * hd)
                    .translate((0.0, hd, 0.0))
                )
                lid = lid.cut(wedge)
            for sy in (-1.0, +1.0):
                wedge = (
                    cq.Workplane("YZ")
                    .polyline(
                        [
                            (sy * hd, zt),
                            (sy * (hd - li), zt),
                            (sy * hd, zt + li),
                        ]
                    )
                    .close()
                    .extrude(2.0 * hw)
                    .translate((cx - hw, 0.0, 0.0))
                )
                lid = lid.cut(wedge)

    # The canonical lid scallops each rib-post out of the lip pads at the post's
    # own radius.  The insert bosses are wider, and a scallop big enough to
    # clear one leaves a ~0.75 mm sliver of pad standing in the build direction,
    # three times per bay.  Cut the pad's rib-side run away locally instead —
    # the outboard run and the two ends still locate the cover in both axes.
    cf = p["cover_fastening"]
    boss_r = (cf["boss_dia"] if cf["mode"] == "heat_set" else m["corner_post_dia"]) / 2.0
    ring_w = refine.get("registration_ring_width", 3.0)
    relief = c["boss_relief_margin"]
    for px, py in L["lid_screw_xy"]:
        if abs(py) >= L["interior_half_y"]:
            continue  # plenum posts: no lip pad there to clash with
        lid = lid.cut(
            cq.Workplane("XY")
            .box(
                2.0 * (boss_r + ring_w + relief),
                2.0 * (boss_r + relief),
                lip_depth + 1.0,
                centered=(True, True, False),
            )
            .translate((px, py, z0 - lip_depth - 0.5))
        )

    if c["lip_drain_relief"] > 0 and L["mounting_orientation"] == "vertical":
        # Canonical +X is down: the lowest lip run in each bay is its +X side.
        rel = c["lip_drain_relief"]
        for cx in L["bay_cx"]:
            x_edge = cx + L["bay_w"] / 2.0 - lip_gap
            lid = lid.cut(
                cq.Workplane("XY")
                .box(
                    rel + lip_gap + 1.0,
                    L["bay_d"],
                    lip_depth + 1.0,
                    centered=(False, True, False),
                )
                .translate((x_edge - rel, 0.0, z0 - lip_depth - 0.5))
            )
    return lid


def _cover_labels(lid: cq.Workplane, params: dict, L: dict, p: dict) -> cq.Workplane:
    """Identity centred on the cover, plus one small maker mark."""
    lb = p["labels"]
    if not lb["enabled"]:
        return lid
    m = params["housing"]
    z_top = L["base_height"] + m["lid_thickness"]
    ident = "TX" if any(b.get("mirror_x") for b in L["bays"]) else "RX"

    # On the spine land, not in a recessed field: the spine is full thickness,
    # so 0.6 mm of engraving leaves 2.4 mm of cover, and sitting on the
    # centreline keeps the one emblem symmetric about the cover's long axis.
    # Baseline runs along canonical Y, which is horizontal once installed.
    blank = _text_blank(ident, lb["identity_size"], lb["depth"], lb["font"])
    blank = blank.rotate((0, 0, 0), (0, 0, 1), 90).translate(
        (0.0, -14.6, z_top - lb["depth"] + 0.001)
    )
    return _engrave(lid, blank)


def _create_lid_canonical(params: dict) -> cq.Workplane:
    L = layout(params)
    p = production(params)
    m = params["housing"]
    e = p["edges"]

    lid = _canon._create_lid_canonical(_canonical_without_rear_connector(params))

    # Edge language, applied by intersection for the same reason as the base.
    z0 = L["base_height"]
    trim = _rounded_slab(
        2.0 * L["outer_half_x"],
        L["total_depth"],
        m["lid_thickness"],
        e["plan_radius"],
        (0.0, (L["back_outer_y"] - L["outer_half_y"]) / 2.0, z0),
    )
    if e["cover_perimeter_chamfer"] > 0:
        trim = trim.edges(">Z").chamfer(e["cover_perimeter_chamfer"])
    if e["parting_reveal"] > 0:
        trim = trim.edges("<Z").chamfer(e["parting_reveal"])
    # Keep everything below the parting plane (the lip) untouched by the trim.
    below = (
        cq.Workplane("XY")
        .box(
            4.0 * L["outer_half_x"], 4.0 * L["total_depth"], 4.0 * z0, centered=(True, True, False)
        )
        .translate((0.0, 0.0, -4.0 * z0 + z0))
    )
    lid = lid.intersect(trim.union(below))

    # _cover_fields re-cuts the whole screw pattern, added posts included.
    lid = _cover_fields(lid, params, L, p)
    lid = _cover_lip_details(lid, params, L, p)
    lid = _cover_labels(lid, params, L, p)
    return lid


def create_lid(params: dict) -> cq.Workplane:
    return orient_to_mounting(_create_lid_canonical(params), params)


# ---------------------------------------------------------------------------
# Assembly / debug
# ---------------------------------------------------------------------------
def create_part(params: dict | None = None) -> cq.Workplane:
    if params is None:
        raise ValueError("create_part needs resolved params (the part wrapper supplies them)")
    base = create_base(params)
    lid = create_lid(params)
    explode = params["housing"].get("explode_gap", 0.0)
    if explode:
        lid = lid.translate((explode, 0, 0))
    return cq.Workplane("XY").newObject([cq.Compound.makeCompound([base.val(), lid.val()])])


def build_stages(params: dict | None = None):
    """Stage-by-stage build so a styling failure bisects (DESIGN_LANGUAGE)."""
    L = layout(params)
    p = production(params)
    base = _canon._create_base_canonical(_canonical_without_rear_connector(params))
    yield "canonical_base", base
    base = base.intersect(_trim_solid(L, p))
    yield "edge_language", base
    base = _cut_rear_connector(base, params, L, p)
    yield "rear_connector", base
    base = _sc_flange_wells(base, params, L, p)
    yield "sc_wells", base
    base = _lighten_spool(base, params, L, p)
    yield "spool", base
    base = _post_reinforcement(base, params, L, p)
    yield "posts", base
    base = _cover_anchors(base, params, L, p)
    yield "cover_anchors", base
    base = _cable_anchors(base, params, L, p)
    yield "anchors", base
    base = _drains(base, params, L, p)
    yield "drains", base
    base = _mount_flanges(base, params, L, p)
    yield "flanges", base
    base = _mount_face_drainage(base, params, L, p)
    yield "mount_drainage", base
    base = _base_labels(base, params, L, p)
    yield "base_labels", base
    yield "lid", _create_lid_canonical(params)
