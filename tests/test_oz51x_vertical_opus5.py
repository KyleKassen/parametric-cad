"""
New-feature probes for the Opus 5 vertical OZ51x housings.

The shared suite (tests/test_oz51x_housings.py) already proves this variant
keeps every family interface.  This file proves the things the refinement
*adds*, and — more importantly — the defects it claims to fix.

Every probe uses lib.housing.interference, which RAISES on a failed boolean.
A local try/except returning 0.0 would read a kernel error as perfect
clearance, which is exactly the failure mode these probes exist to catch.

Technique, so the assertions are readable:
  material must be ABSENT  -> undersized probe of the real feature, < 0.05
                              (through-hole) or < 0.5 (large cutout)
  material must be PRESENT -> undersized probe inside it, > 1.0 .. > 50.0
  feature on the RIGHT FACE only -> mirrored control probe that must be solid
  partial removal (text)   -> skin probe bracketed by two fractions of the
                              ideal full volume
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PARTS = [
    "oz51x-dual-rx-housing-vertical-opus-5",
    "oz51x-dual-tx-housing-vertical-opus-5",
]

_CACHE: dict = {}


def _housing(part: str):
    if part not in _CACHE:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            part.replace("-", "_"),
            PROJECT_ROOT / "parts" / "custom" / part / "model.py",
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        params = m.load_params()
        L = m.layout(params)
        _CACHE[part] = {
            "m": m,
            "params": params,
            "L": L,
            "p": L["production"],
            "base": m.create_base(params),
            "lid": m.create_lid(params),
        }
    return _CACHE[part]


def _overlap(a, b) -> float:
    from lib.housing import interference

    return interference(a, b)


def _orient(H, shape):
    return H["m"].orient_to_mounting(shape, H["params"])


def _box(w, d, h, centre, centered=(True, True, True)):
    import cadquery as cq

    return cq.Workplane("XY").box(w, d, h, centered=centered).translate(centre)


def _cyl(r, origin, direction, length):
    import cadquery as cq

    solid = cq.Solid.makeCylinder(r, length, cq.Vector(*origin), cq.Vector(*direction))
    return cq.Workplane("XY").newObject([solid])


@pytest.fixture(params=PARTS)
def part(request):
    return request.param


# ---------------------------------------------------------------------------
# The rear panel re-datum — the four defects this variant exists to fix
# ---------------------------------------------------------------------------
def test_legacy_de9_arrangement_genuinely_does_not_fit(part):
    """
    The premise, as arithmetic: a DE-9 counter-rotated onto the width axis
    needs more canonical z than exists between the floor and the parting face.
    If this ever stops being true the re-datum is no longer justified.
    """
    H = _housing(part)
    L, pc, h = H["L"], H["params"]["panel_connector"], H["params"]["housing"]
    available = L["interior_top_z"] - h["floor"]
    needed = pc["screw_spacing"] + pc["screw_hole_dia"]
    assert needed > available, (
        f"the legacy width-axis arrangement now fits ({needed:.2f} <= {available:.2f}) "
        "— re-examine whether footprint_axis='height' is still the right call"
    )
    assert pc.get("footprint_axis") == "height"


def test_de9_jackscrews_open_with_real_wall_around_them(part):
    """
    Both jackscrew holes pass the wall, and — the v1 defect — there is solid
    wall above AND below each of them.  v1 leaves a 0.12 mm ligament above the
    upper one, which no process can make.
    """
    H = _housing(part)
    L, base = H["L"], H["base"]
    pc, h = H["params"]["panel_connector"], H["params"]["housing"]
    pc_z = L["panel_connector_z"]
    wall_mid = L["plenum_y1"] + h["wall"] / 2.0
    r = pc["screw_hole_dia"] / 2.0

    for off in (-pc["screw_spacing"] / 2.0, +pc["screw_spacing"] / 2.0):
        px = pc["x"] + off
        hole = _cyl(r - 0.1, (px, L["plenum_y1"] - 0.5, pc_z), (0, 1, 0), h["wall"] + 1.0)
        v = _overlap(base, _orient(H, hole))
        assert v < 0.05, f"jackscrew at x={px:+.1f} blocked by {v:.2f} mm^3"

        for side, dz in (("above", +1.0), ("below", -1.0)):
            band = _box(3.0, h["wall"] - 0.4, 1.5, (px, wall_mid, pc_z + dz * (r + 0.75)))
            v = _overlap(base, _orient(H, band))
            assert v > 8.0, (
                f"only {v:.2f} mm^3 of wall {side} the jackscrew at x={px:+.1f} "
                "— this is the 0.12 mm ligament defect"
            )


def test_de9_nut_zones_are_reachable_from_inside(part):
    """
    A DE-9's jackscrews need female hardware on the plenum side.  In v1 the
    lower jackscrew sits on the interior floor plane and 42.75 mm^3 of its nut
    envelope is solid floor.
    """
    H = _housing(part)
    L, base = H["L"], H["base"]
    pc = H["params"]["panel_connector"]
    pc_z = L["panel_connector_z"]
    for off in (-pc["screw_spacing"] / 2.0, +pc["screw_spacing"] / 2.0):
        px = pc["x"] + off
        nut = _cyl(6.35 / 2.0, (px, L["plenum_y1"] - 3.0, pc_z), (0, 1, 0), 3.0)
        v = _overlap(base, _orient(H, nut))
        assert v < 0.05, f"nut envelope at x={px:+.1f} obstructed by {v:.2f} mm^3"


def test_rear_keepout_actually_spans_the_jackscrews(part):
    """
    v1's 24 mm keep-out spans neither jackscrew, so proving it empty proved
    nothing about the hardware that lives there.  Pure arithmetic — it must
    hold before any probe is meaningful.
    """
    H = _housing(part)
    pc = H["params"]["panel_connector"]
    half = pc["rear_keepout_w"] / 2.0
    need = pc["screw_spacing"] / 2.0 + 6.35 / 2.0
    assert half >= need, (
        f"keep-out half-width {half:.2f} does not reach the jackscrew hardware at {need:.2f}"
    )


def test_de9_flange_clears_both_mount_plane_and_parting_face(part):
    """The flange must not land on the wall-mount plane or cross the seam."""
    H = _housing(part)
    L, p = H["L"], H["p"]
    pc = H["params"]["panel_connector"]
    pc_z = L["panel_connector_z"]
    rp = p["rear_panel"]
    # With footprint_axis "height" the long axis runs along canonical X; the
    # canonical-z extent is the short axis.  That swap is the whole point.
    span = (
        rp["de9_flange_long"]
        if pc.get("footprint_axis", "width") == "width"
        else rp["de9_flange_short"]
    )
    half = span / 2.0
    lo, hi = pc_z - half, pc_z + half
    assert lo > 2.0, f"flange reaches canonical z={lo:.2f}, too near the mount plane"
    assert hi < L["interior_top_z"] - 2.0, (
        f"flange reaches canonical z={hi:.2f} against a parting face at {L['interior_top_z']:.2f}"
    )


def test_de9_flange_clears_the_sc_adapter_flanges(part):
    """The re-datumed footprint shares the back panel with two SC ports."""
    H = _housing(part)
    L, p = H["L"], H["p"]
    ad = H["params"]["sc_adapter"]
    de9_half = p["rear_panel"]["de9_flange_long"] / 2.0
    sc_inner = min(abs(ax) for ax in L["adapter_x"]) - ad["flange_wide"] / 2.0
    assert sc_inner - de9_half > 2.0, (
        f"only {sc_inner - de9_half:.2f} mm between the DE-9 and SC flanges"
    )


# ---------------------------------------------------------------------------
# Mount interface
# ---------------------------------------------------------------------------
def test_mount_flanges_present_with_open_slots_and_gussets(part):
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    f = p["mount_flange"]
    assert L["has_flanges"]
    t = f["thickness"]

    for sgn in (-1.0, +1.0):
        mid_x = sgn * (L["outer_half_x"] + f["extension"] / 2.0)
        plate = _box(f["extension"] - 4.0, 40.0, t - 0.6, (mid_x, 30.0, t / 2.0))
        v = _overlap(base, _orient(H, plate))
        assert v > 50.0, f"mount flange missing at x={mid_x:+.1f} ({v:.1f} mm^3)"

        # A point that is empty unless the gusset exists.
        probe = _box(1.0, 1.0, 1.0, (sgn * (L["outer_half_x"] + 1.2), -30.0, t + 1.2))
        v = _overlap(base, _orient(H, probe))
        assert v > 0.2, f"gusset missing at x={mid_x:+.1f} ({v:.2f} mm^3)"

        for sy in f["slot_y"]:
            import cadquery as cq

            slot = (
                cq.Workplane("XY")
                .center(sgn * (L["outer_half_x"] + f["extension"] / 2.0 + 1.0), sy)
                .slot2D(f["slot_length"] - 0.3, f["slot_width"] - 0.3, 90)
                .extrude(t + 1.0)
                .translate((0.0, 0.0, -0.5))
            )
            v = _overlap(base, _orient(H, slot))
            assert v < 0.05, f"mount slot at y={sy} blocked by {v:.2f} mm^3"


def test_flanges_grow_only_the_height_and_stay_flush(part):
    """
    Two invariants the canonical fit check depends on: the flanges must appear
    in envelope_height, and envelope_width must stay exactly the canonical
    value or the fit check places the SC adapters off-face.
    """
    H = _housing(part)
    L, params = H["L"], H["params"]
    assert abs(L["envelope_height"] - (2 * L["outer_half_x"] + 2 * L["flange_ext"])) < 1e-6
    assert (
        abs(L["envelope_width"] - (L["interior_top_z"] + params["housing"]["lid_thickness"])) < 1e-6
    )
    # Embossed labels stand proud of the front wall, so they belong in the
    # envelope too — but on the depth axis only, never on the body.
    assert abs(L["envelope_depth"] - (L["total_depth"] + L["label_relief"])) < 1e-6

    bb = H["m"].create_part(params).val().BoundingBox()
    assert abs(bb.xmin - (-L["envelope_width"] / 2.0)) < 0.01, (
        "something protrudes past the wall-mount face"
    )
    assert abs(bb.zlen - L["envelope_height"]) < 0.2
    assert abs(bb.ylen - L["envelope_depth"]) < 0.2


# ---------------------------------------------------------------------------
# Drainage
# ---------------------------------------------------------------------------
def test_upper_bay_drains_all_the_way_out(part):
    """
    The strongest single check in this file.  Canonical +X is down; the upper
    bay's low point is the top of the central rib, 45 mm above the finished
    bottom face, and the partition pass-slot sills sit 5.18 mm above both bay
    floors.  So the only way out is through the rib, and a bottom-face slot
    alone (the fable5-extra approach) cannot empty this volume.  One
    continuous probe from the upper bay floor to outside must be clear.
    """
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    d = p["drains"]
    r = d["dia"] / 2.0 - 0.15
    for dy in d["rib_cross_y"]:
        # Y is horizontal once installed, so water crossing the rib at this y
        # cannot travel along Y to find an outlet.  Every cross-drain needs an
        # outlet directly beneath it.
        assert dy in d["outlet_y"], (
            f"cross-drain at y={dy} has no wall outlet below it — water reaching "
            "the lower bay there has nowhere to go"
        )
        path = _cyl(r, (-2.5, dy, d["z"]), (1, 0, 0), L["outer_half_x"] + 3.0)
        v = _overlap(base, _orient(H, path))
        assert v < 0.05, f"upper-bay drain path at y={dy} blocked by {v:.2f} mm^3"


def test_every_drain_is_open(part):
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    h = H["params"]["housing"]
    d = p["drains"]
    r = d["dia"] / 2.0 - 0.15
    for dy in d["rib_cross_y"]:
        probe = _cyl(r, (-h["bay_gap"] / 2.0 - 0.5, dy, d["z"]), (1, 0, 0), h["bay_gap"] + 1.0)
        v = _overlap(base, _orient(H, probe))
        assert v < 0.05, f"rib cross-drain at y={dy} blocked by {v:.2f} mm^3"
    for dy in d["outlet_y"]:
        probe = _cyl(r, (L["interior_half_x"] - 0.5, dy, d["z"]), (1, 0, 0), h["wall"] + 1.0)
        v = _overlap(base, _orient(H, probe))
        assert v < 0.05, f"wall outlet at y={dy} blocked by {v:.2f} mm^3"


def test_finished_top_face_is_never_breached(part):
    """
    The mirrored control.  Every drain is a hole through the canonical +X wall,
    which is the finished BOTTOM.  The same probe on the canonical -X wall must
    hit a full plug of material — a mirrored-feature bug cannot pass this.
    """
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    h = H["params"]["housing"]
    d = p["drains"]
    r = d["dia"] / 2.0 - 0.15
    for dy in d["outlet_y"]:
        control = _cyl(r, (-L["outer_half_x"] - 0.5, dy, d["z"]), (1, 0, 0), h["wall"] + 1.0)
        v = _overlap(base, _orient(H, control))
        assert v > 15.0, (
            f"the finished TOP face is open at y={dy} ({v:.2f} mm^3 of material, "
            "expected a full plug)"
        )


def test_mount_face_grooves_run_downhill_and_do_not_breach_the_floor(part):
    """
    The grooves must run along canonical X — the vertical direction once
    installed — and must not cut into any pilot that starts inside the floor
    slab.  A groove along Y would be a horizontal trap, not a drain.
    """
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    h, m = H["params"]["housing"], H["params"]["module"]
    md = p["mount_drainage"]

    # Open at the mount face.  The section is a V, so the probe has to fit
    # inside the wedge rather than inside its mouth.
    probe_h = 0.25
    probe_w = md["groove_width"] * (1.0 - probe_h / md["groove_depth"]) - 0.4
    assert probe_w > 0.3, "groove section too shallow to probe meaningfully"
    for gy in md["groove_y"]:
        probe = _box(20.0, probe_w, probe_h, (0.0, gy, probe_h / 2.0))
        v = _overlap(base, _orient(H, probe))
        assert v < 0.5, f"mount groove at y={gy} not cut ({v:.2f} mm^3)"

    # And the floor above them is still solid — no breach into a bay.
    for gy in md["groove_y"]:
        if not (-L["interior_half_y"] < gy < L["interior_half_y"]):
            continue
        for cx in L["bay_cx"]:
            solid = _box(
                10.0,
                md["groove_width"],
                h["floor"] - md["groove_depth"] - 0.2,
                (cx, gy, md["groove_depth"] + 0.1),
                centered=(True, True, False),
            )
            v = _overlap(base, _orient(H, solid))
            full = 10.0 * md["groove_width"] * (h["floor"] - md["groove_depth"] - 0.2)
            assert v > 0.9 * full, (
                f"groove at y={gy} thinned the floor under bay {cx} ({v:.1f} of {full:.1f} mm^3)"
            )

    # No groove may sit on a module screw-boss pilot.
    pilot_ys = {-m["screw_hole_front"]["z"], -m["screw_hole_back"]["z"]}
    for gy in md["groove_y"]:
        for py in pilot_ys:
            assert abs(gy - py) > (md["groove_width"] / 2.0 + h["screw_boss_pilot_dia"] / 2.0), (
                f"groove at y={gy} runs across the boss pilot at y={py}"
            )


# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------
def test_cover_screw_pattern_is_complete_and_symmetric(part):
    """
    Eight counterbores, all open, and the pattern mirror-symmetric about the
    cover's own centreline in the finished attitude.  DESIGN_LANGUAGE rule 3.
    """
    H = _housing(part)
    L, lid = H["L"], H["lid"]
    m = H["params"]["housing"]
    z_top = L["base_height"] + m["lid_thickness"]

    assert len(L["lid_screw_xy"]) == 8
    for px, py in L["lid_screw_xy"]:
        probe = _cyl(
            m["lid_screw_clear_dia"] / 2.0 - 0.15,
            (px, py, z_top - m["lid_thickness"] - 0.5),
            (0, 0, 1),
            m["lid_thickness"] + 1.0,
        )
        v = _overlap(lid, _orient(H, probe))
        assert v < 0.05, f"cover screw hole at ({px}, {py}) blocked by {v:.2f} mm^3"

    # finished z = outer_half_x - canonical x; symmetry about the cover centre
    zs = sorted({round(L["outer_half_x"] - px, 3) for px, _ in L["lid_screw_xy"]})
    centre = L["outer_half_x"]
    assert all(any(abs((2 * centre - z) - other) < 1e-6 for other in zs) for z in zs), (
        f"cover fastener columns are not symmetric about the centreline: {zs}"
    )


def test_cover_field_is_printable_on_its_own_bed_face(part):
    """
    The cover prints outer-face-down, so anything recessed into the show face
    is a pocket opening onto the bed.  A reveal groove bridges its own width; a
    recessed field bridges its whole span.  Whichever style is selected, the
    unsupported span must stay inside what FDM will bridge and the residual
    wall must stay structural.

    There is also no head counterbore.  An ISO 4762 M3 cap head is Dia5.5 x 3.0
    and would stand 1.4 mm proud of a 1.6 mm bore, and its standard counterbore
    is Dia6.5 x 3.0 — the whole cover.  An ISO 7380-1 button head bears on the
    outer face instead, which is the bed face and therefore the flattest,
    squarest seat on the part.  That seat must be full thickness.
    """
    H = _housing(part)
    L, lid, p = H["L"], H["lid"], H["p"]
    m = H["params"]["housing"]
    c = p["cover"]

    if c["field_style"] == "groove":
        residual = m["lid_thickness"] - c["groove_depth"]
        assert residual >= 2.0, f"only {residual:.2f} mm of cover under the groove"
        assert c["groove_width"] <= 15.0, (
            f"a {c['groove_width']:.1f} mm unsupported span on the bed face"
        )
    else:
        residual = m["lid_thickness"] - c["recess_depth"]
        assert residual >= 2.0, f"only {residual:.2f} mm of cover under the recess"

    z_top = L["base_height"] + m["lid_thickness"]
    head_r = m["lid_screw_head_dia"] / 2.0
    clr_r = m["lid_screw_clear_dia"] / 2.0
    import cadquery as cq

    for px, py in L["lid_screw_xy"]:
        ring = (
            cq.Workplane("XY")
            .circle(head_r + 0.4)
            .circle(clr_r + 0.2)
            .extrude(0.4)
            .translate((px, py, z_top - 0.4))
        )
        v = _overlap(lid, _orient(H, ring))
        full = 3.14159 * ((head_r + 0.4) ** 2 - (clr_r + 0.2) ** 2) * 0.4
        assert v > 0.85 * full, (
            f"screw seat at ({px}, {py}) is not full thickness ({v:.2f} of {full:.2f} mm^3)"
        )


def test_cover_lip_low_segment_is_relieved(part):
    """
    The registration lip hangs 0.30 mm above each bay floor along its whole
    length, at the lowest point of the bay in the finished attitude — a
    capillary slot no drain can empty, because it is the low point.
    """
    H = _housing(part)
    L, lid, p = H["L"], H["lid"], H["p"]
    refine = H["params"].get("refinement", {})
    lip_gap = refine.get("registration_clearance", 0.3)
    lip_depth = refine.get("registration_lip_depth", 2.0)
    rel = p["cover"]["lip_drain_relief"]
    z0 = L["base_height"]
    for cx in L["bay_cx"]:
        x_edge = cx + L["bay_w"] / 2.0 - lip_gap
        probe = _box(
            rel - 0.3,
            L["bay_d"] - 8.0,
            lip_depth - 0.3,
            (x_edge - rel / 2.0, 0.0, z0 - lip_depth / 2.0),
        )
        v = _overlap(lid, _orient(H, probe))
        assert v < 0.5, f"lip drain relief missing in bay {cx} ({v:.1f} mm^3)"


# ---------------------------------------------------------------------------
# Structure, spool, connectors, marking
# ---------------------------------------------------------------------------
def test_added_posts_clear_every_keepout(part):
    """
    Arithmetic first, so a later param edit that walks a post into a corridor
    fails loudly rather than silently.
    """
    H = _housing(part)
    L, p = H["L"], H["p"]
    ad, pc = H["params"]["sc_adapter"], H["params"]["panel_connector"]
    h = H["params"]["housing"]
    post_r = h["corner_post_dia"] / 2.0

    for px, py in p["posts"]["extra_lid_posts"]:
        assert abs(px) + post_r < L["interior_half_x"], "post outside the interior"
        for ax in L["adapter_x"]:
            reach = (
                (ad["body_len"] - ad["flange_thickness"]) / 2.0
                - h["wall"]
                + ad["mated_connector_clear"]
            )
            if py + post_r > L["plenum_y1"] - reach:
                gap = abs(px - ax) - post_r - ad["body_short"] / 2.0
                assert gap > 1.0, f"post ({px}, {py}) is {gap:.2f} mm from an SC corridor"
        if py + post_r > L["plenum_y1"] - pc["rear_keepout_depth"]:
            gap = abs(px - pc["x"]) - post_r - pc["rear_keepout_w"] / 2.0
            assert gap > 1.0, f"post ({px}, {py}) is {gap:.2f} mm from the DE-9 keep-out"


def test_cover_anchors_are_insert_bosses(part):
    """
    Every cover screw lands in a heat-set insert, not a formed thread.

    The reason is torque, not pull-out.  Measured in PETG, a screw formed
    directly into the plastic and a brass insert pull out at the same load
    (118 vs 119 kg), but the formed thread strips at ~1 Nm against the insert's
    3 Nm — and ~1 Nm is about the minimum sensible assembly torque for M3.  A
    formed FDM thread therefore has no torque margin on FIRST assembly, before
    service life is even considered.
    """
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    cf = p["cover_fastening"]
    if cf["mode"] != "heat_set":
        pytest.skip("variant uses formed threads")

    boss_r = cf["boss_dia"] / 2.0
    hole_r = cf["hole_dia"] / 2.0
    z_top = L["base_height"]
    import cadquery as cq

    # Arithmetic first.  ruthex state W min 1.6 for M3 and Tappex 1.70; the
    # "boss OD >= 2x insert OD" rule is not from any insert manufacturer.
    wall = (cf["boss_dia"] - cf["hole_dia"]) / 2.0
    assert wall >= 1.6, f"only {wall:.2f} mm of boss wall around the insert"
    assert cf["boss_dia"] >= 7.4, "under Tappex's stated D1 min for M3"
    assert cf["hole_depth"] >= cf["insert_length"] + 0.5, (
        "no relief well under the insert — displaced melt has nowhere to go"
    )

    for px, py in L["lid_screw_xy"]:
        ring = (
            cq.Workplane("XY")
            .circle(boss_r - 0.2)
            .circle(hole_r + 0.2)
            .extrude(0.6)
            .translate((px, py, z_top - 0.8))
        )
        v = _overlap(base, _orient(H, ring))
        full = 3.14159 * ((boss_r - 0.2) ** 2 - (hole_r + 0.2) ** 2) * 0.6
        assert v > 0.8 * full, (
            f"insert boss missing or undersized at ({px}, {py}) ({v:.1f} of {full:.1f} mm^3)"
        )

        hole = _cyl(
            hole_r - 0.2,
            (px, py, z_top - cf["hole_depth"] + 0.3),
            (0, 0, 1),
            cf["hole_depth"] - 0.4,
        )
        v = _overlap(base, _orient(H, hole))
        assert v < 0.05, f"insert hole at ({px}, {py}) blocked by {v:.2f} mm^3"

        below = _cyl(hole_r - 0.2, (px, py, z_top - cf["hole_depth"] - 1.2), (0, 0, 1), 0.8)
        v = _overlap(base, _orient(H, below))
        full = 3.14159 * (hole_r - 0.2) ** 2 * 0.8
        assert v > 0.8 * full, (
            f"insert hole at ({px}, {py}) is not blind ({v:.2f} of {full:.2f} mm^3)"
        )


def test_insert_bosses_flare_above_the_can(part):
    """
    The module cans cap a centreline boss at Dia7.0 — but only up to the can
    top.  The boss may reach insert size only above that, and the transition
    must be a 45 deg cone: a radial step there prints in mid-air.
    """
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    h, mod = H["params"]["housing"], H["params"]["module"]
    cf = p["cover_fastening"]
    if cf["mode"] != "heat_set":
        pytest.skip("variant uses formed threads")

    can_top = L["plate_bottom_z"] + mod["can_height_y"]
    assert cf["boss_flare_z"] >= can_top - 0.01, (
        f"flare starts at z={cf['boss_flare_z']}, below the can top at {can_top:.2f}"
    )

    post_r = h["corner_post_dia"] / 2.0
    boss_r = cf["boss_dia"] / 2.0
    rise = boss_r - post_r

    for px, py in L["lid_screw_xy"]:
        # Only the three rib posts are constrained by a module can.  The
        # spool shares their x but its hub is already Dia8, and the plenum
        # posts have no module anywhere near them.
        if abs(px) > 1.0 or abs(py) >= L["interior_half_y"]:
            continue
        # Probe the lobes outboard of the 4 mm central rib the post sits in —
        # inside the rib there is always material, boss or no boss.
        for sx in (-1.0, +1.0):
            lobe_x = px + sx * (post_r + (boss_r - post_r) / 2.0)
            below = _box(0.8, 0.8, 0.6, (lobe_x, py, cf["boss_flare_z"] - 0.8))
            v = _overlap(base, _orient(H, below))
            assert v < 0.05, (
                f"boss at ({px}, {py}) is already full width below the flare "
                f"({v:.2f} mm^3) — it would foul a module can"
            )
            # ...and the same probe above the flare must be solid, or the boss
            # never grew at all.
            above = _box(0.8, 0.8, 0.6, (lobe_x, py, L["base_height"] - 1.0))
            v = _overlap(base, _orient(H, above))
            assert v > 0.30, f"boss at ({px}, {py}) did not flare ({v:.2f} mm^3 above it)"
        mid_r = post_r + rise / 2.0 + 0.25
        mid = _cyl(mid_r, (px, py, cf["boss_flare_z"] + rise / 2.0 - 0.15), (0, 0, 1), 0.3)
        v = _overlap(base, _orient(H, mid))
        full = 3.14159 * mid_r**2 * 0.3
        assert 0.5 * full < v < full, (
            f"flare at ({px}, {py}) is not a 45 deg cone ({v:.2f} of {full:.2f} mm^3)"
        )


def test_module_boss_pilot_leaves_a_printable_web(part):
    """0.5 mm is under MJF's 0.7 mm minimum wall; the mount face needs more."""
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    h, m = H["params"]["housing"], H["params"]["module"]
    start = p["posts"]["boss_pilot_start"]
    assert start >= 0.7
    assert L["plate_bottom_z"] - start >= 4.4, "less than an M3x6 needs"

    r = h["screw_boss_pilot_dia"] / 2.0 - 0.2
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        for hole in (m["screw_hole_front"], m["screw_hole_back"]):
            x, y = cx + sign * hole["x"], -hole["z"]
            web = _cyl(r, (x, y, 0.1), (0, 0, 1), start - 0.3)
            v = _overlap(base, _orient(H, web))
            full = 3.14159 * r * r * (start - 0.3)
            assert v > 0.9 * full, (
                f"boss web at ({x:.2f}, {y:.2f}) is bored through ({v:.2f} of {full:.2f} mm^3)"
            )


def test_spool_is_lightened_without_moving_the_fiber_surface(part):
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    fb, h = H["params"]["fiber_bay"], H["params"]["housing"]
    sp = p["spool"]
    outer_r = fb["spool_dia"] / 2.0
    assert outer_r >= fb["min_bend_radius"], "spool no longer enforces the bend radius"

    # A void exists between hub and drum, in a place no web crosses.
    ang = 180.0 / sp["web_count"] / 2.0
    import math as _m

    rad = (sp["hub_dia"] / 2.0 + sp["inner_dia"] / 2.0) / 2.0
    vx = rad * _m.cos(_m.radians(ang))
    vy = rad * _m.sin(_m.radians(ang))
    void = _cyl(1.2, (vx, L["spool_y"] + vy, h["floor"] + 1.0), (0, 0, 1), 6.0)
    v = _overlap(base, _orient(H, void))
    assert v < 0.5, f"spool is still solid at the sampled void ({v:.2f} mm^3)"

    # The fiber-contact surface itself is untouched.
    import cadquery as cq

    band = (
        cq.Workplane("XY")
        .circle(outer_r - 0.1)
        .circle(outer_r - 0.8)
        .extrude(4.0)
        .translate((0.0, L["spool_y"], h["floor"] + 6.0))
    )
    v = _overlap(base, _orient(H, band))
    full = 3.14159 * ((outer_r - 0.1) ** 2 - (outer_r - 0.8) ** 2) * 4.0
    assert v > 0.8 * full, f"spool drum wall eroded ({v:.1f} of {full:.1f} mm^3)"

    # Retention flange present, on the cover side.
    ft = sp["flange_thickness"]
    ring = (
        cq.Workplane("XY")
        .circle(outer_r + sp["flange_overhang"] - 0.2)
        .circle(outer_r + 0.2)
        .extrude(ft - 0.4)
        .translate((0.0, L["spool_y"], L["base_height"] - ft + 0.2))
    )
    v = _overlap(base, _orient(H, ring))
    assert v > 1.0, f"spool retention flange missing ({v:.2f} mm^3)"


def test_sc_pilot_bosses_restore_engagement_without_touching_the_corridor(part):
    """
    The 0.8 mm flange well costs M2 engagement on the four screws that are the
    fiber ports' entire retention.  The bosses that restore it must not enter
    the mated-connector corridor.
    """
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    ad, h = H["params"]["sc_adapter"], H["params"]["housing"]
    rp = p["rear_panel"]
    br = rp["sc_pilot_boss_dia"] / 2.0

    # Arithmetic: the boss must clear the SC body's canonical-z extent.
    body_lo = L["fiber_z"] - ad["body_long"] / 2.0
    body_hi = L["fiber_z"] + ad["body_long"] / 2.0
    for off in (-ad["screw_spacing"] / 2.0, +ad["screw_spacing"] / 2.0):
        pz = L["fiber_z"] + off
        gap = (body_lo - (pz + br)) if pz < L["fiber_z"] else ((pz - br) - body_hi)
        assert gap > 0.2, f"SC pilot boss at z={pz:.2f} is {gap:.2f} mm from the body"

    for ax in L["adapter_x"]:
        for off in (-ad["screw_spacing"] / 2.0, +ad["screw_spacing"] / 2.0):
            pz = L["fiber_z"] + off
            import cadquery as cq

            ring = (
                cq.Workplane("XY")
                .circle(br - 0.15)
                .circle(ad["screw_pilot_dia"] / 2.0 + 0.15)
                .extrude(rp["sc_pilot_boss_height"] - 0.4)
                .rotate((0, 0, 0), (1, 0, 0), -90)
                .translate((ax, L["plenum_y1"] - rp["sc_pilot_boss_height"] + 0.2, pz))
            )
            v = _overlap(base, _orient(H, ring))
            assert v > 1.0, f"SC pilot boss missing at ({ax}, z={pz:.2f}) ({v:.2f} mm^3)"

            pilot = _cyl(
                ad["screw_pilot_dia"] / 2.0 - 0.1,
                (ax, L["plenum_y1"] - rp["sc_pilot_boss_height"] - 0.5, pz),
                (0, 1, 0),
                h["wall"] + rp["sc_pilot_boss_height"] + 1.0,
            )
            v = _overlap(base, _orient(H, pilot))
            assert v < 0.05, f"SC pilot at ({ax}, z={pz:.2f}) blocked by {v:.2f} mm^3"


def test_identity_is_engraved_on_the_cover(part):
    """
    Skin probe: over the label zone the cover must be partly, but not wholly,
    removed.  Catches a missing engrave and an engrave on the wrong face.
    """
    H = _housing(part)
    L, lid, p = H["L"], H["lid"], H["p"]
    m = H["params"]["housing"]
    lb = p["labels"]
    z_top = L["base_height"] + m["lid_thickness"]
    skin = lb["depth"] * 0.6
    w, d = lb["identity_size"] * 1.1, lb["identity_size"] * 2.0
    probe = _box(w, d, skin, (0.0, -14.6, z_top - skin / 2.0))
    v = _overlap(lid, _orient(H, probe))
    full = w * d * skin
    assert v < 0.95 * full, f"no engraving detected on the cover ({v:.2f} of {full:.2f})"
    assert v > 0.30 * full, f"cover missing at the label zone ({v:.2f} mm^3)"


def test_port_labels_are_marked_beside_each_sma(part):
    """
    RF and TTL are otherwise identical ports on the same face.  Each label sits
    beside its own SMA at the port's own height, offset along canonical Z — a
    handedness-independent direction, so RX and TX mark up identically instead
    of the label flipping sides with the module.

    On a vertical FDM wall an engraved stroke needs ~1.0 mm before the
    perimeters either side merge and the letter fills in; Arial at the old
    3.6 mm cap gave 0.48 mm.  These are embossed instead, so the probe sits
    OUTSIDE the wall face and must find glyphs standing in it — but not a
    solid block.
    """
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    m = H["params"]["module"]
    lb = p["labels"]
    y_face = -L["outer_half_y"]
    emboss = lb.get("port_style", "engrave") == "emboss"
    relief = lb["port_relief"] if emboss else lb["depth"]
    skin = relief * 0.5
    w, d = lb["port_size"] * 2.6, lb["port_size"] * 1.4

    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        sma_x = cx + sign * m["sma_axis_x"]
        yc = y_face - skin / 2.0 if emboss else y_face + skin / 2.0
        probe = _box(
            w,
            skin,
            d,
            (sma_x, yc, L["plate_bottom_z"] + m["sma_axis_y"] + lb["port_offset"]),
        )
        v = _overlap(base, _orient(H, probe))
        full = w * skin * d
        if emboss:
            assert v > 0.03 * full, f"no raised port label for bay {bay['label']} ({v:.2f} mm^3)"
            assert v < 0.70 * full, (
                f"the {bay['label']} label zone is a solid block, not glyphs "
                f"({v:.2f} of {full:.2f} mm^3)"
            )
        else:
            assert v < 0.97 * full, f"no port label for bay {bay['label']}"
            assert v > 0.30 * full, f"front wall missing at the {bay['label']} label"

    # The stroke has to survive the process that makes it.
    stroke = lb["port_size"] * 0.133  # Arial stem / cap height
    floor = 0.8 if emboss else 1.0
    assert stroke >= floor, (
        f"a {lb['port_size']:.1f} mm cap gives a {stroke:.2f} mm stroke, under the "
        f"{floor:.1f} mm floor for this marking style"
    )


def test_maker_mark_is_absent_unless_asked_for(part):
    """Provenance marking is a parameter, and it is off."""
    H = _housing(part)
    L, base, p = H["L"], H["base"], H["p"]
    lb = p["labels"]
    skin = lb["depth"] * 0.6
    w, d = lb["mark_size"] * 1.4, lb["mark_size"] * 6.0
    probe = _box(skin, d, w, (L["outer_half_x"] - skin / 2.0, 70.0, 14.86))
    v = _overlap(base, _orient(H, probe))
    full = w * d * skin
    if lb.get("mark"):
        assert v < 0.97 * full, f"labels.mark is set but nothing is marked ({v:.2f} mm^3)"
        assert v > 0.30 * full, f"bottom face missing at the mark zone ({v:.2f} mm^3)"
    else:
        assert v > 0.97 * full, (
            f"labels.mark is empty but the bottom face is marked ({v:.2f} of {full:.2f} mm^3)"
        )
