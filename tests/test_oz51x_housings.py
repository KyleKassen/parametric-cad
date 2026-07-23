"""
Tests for the OZ51x housing family — every test runs against all variants:

  oz510-dual-housing     RX + TX  (the original mixed pair)
  oz51x-dual-tx-housing  RF TX + TTL TX, rear DE-9, no front wiring slots
  oz51x-dual-rx-housing  RF RX + TTL RX, rear DE-9, no front wiring slots
  oz51x-dual-*-housing-vertical  same interfaces, bays stacked upward
  oz51x-dual-*-housing-vertical-gpt-5-6-sol  production refinements

All variants share one parametric builder (the oz510-dual-housing model);
each bay's handedness and vendor STEP come from that part's params.json.
Run with: make test  (or: pytest tests/)
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VENDOR = PROJECT_ROOT / "parts" / "vendor"
PARTS = [
    "oz510-dual-housing",
    "oz51x-dual-tx-housing",
    "oz51x-dual-rx-housing",
    "oz51x-dual-tx-housing-vertical",
    "oz51x-dual-rx-housing-vertical",
    "oz51x-dual-tx-housing-vertical-gpt-5-6-sol",
    "oz51x-dual-rx-housing-vertical-gpt-5-6-sol",
    "oz51x-dual-tx-housing-vertical-fable5-extra",
    "oz51x-dual-rx-housing-vertical-fable5-extra",
]

_CACHE: dict = {}


def _housing(part: str):
    """Load (model, params, layout, base) for a part, cached across tests."""
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
        _CACHE[part] = {"m": m, "params": params, "L": L, "base": m.create_base(params)}
    return _CACHE[part]


@pytest.fixture(params=PARTS)
def part(request):
    return request.param


def _overlap(a, b) -> float:
    """
    Boolean intersection volume between two shapes/workplanes, in mm^3.

    Delegates to lib.housing.interference, which RAISES on a failed boolean —
    an exception must surface as a test error, never read as 0.0 clearance.
    """
    from lib.housing import interference

    return interference(a, b)


def _orient(H, shape):
    """Apply the housing's final mounting attitude to canonical probe geometry."""
    return H["m"].orient_to_mounting(shape, H["params"])


def test_base_is_solid(part):
    """The base tray builds and has positive volume."""
    assert _housing(part)["base"].val().Volume() > 0


def test_lid_is_solid(part):
    """The lid builds and has positive volume."""
    H = _housing(part)
    assert H["m"].create_lid(H["params"]).val().Volume() > 0


def test_envelope_matches_layout(part):
    """The assembled bounding box should match the computed outer envelope."""
    H = _housing(part)
    L, params = H["L"], H["params"]
    bb = H["m"].create_part(params).val().BoundingBox()

    tol = 0.2
    assert abs(bb.xlen - L["envelope_width"]) < tol
    assert abs(bb.ylen - L["envelope_depth"]) < tol
    assert abs(bb.zlen - L["envelope_height"]) < tol


def test_io_cutouts_clear_per_bay(part):
    """
    Push a probe solid through each bay's SMA hole (and wiring slot, where the
    variant has front slots): it must meet no wall material. Handedness-aware
    (reads bays[].mirror_x) — catches mirrored/misplaced panel cutouts, the
    v1 bug where the TX bay's cutouts were placed receiver-handed.
    """
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    mod = H["params"]["module"]
    h = H["params"]["housing"]

    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0

        # SMA probe: barrel-diameter cylinder along -Y through the front wall
        x = cx + sign * mod["sma_axis_x"]
        z = L["plate_bottom_z"] + mod["sma_axis_y"]
        probe = cq.Solid.makeCylinder(
            mod["sma_barrel_dia"] / 2.0,
            h["wall"] + 1.0,
            cq.Vector(x, -L["outer_half_y"] - 0.5, z),
            cq.Vector(0, 1, 0),
        )
        v = _overlap(base, _orient(H, cq.Workplane("XY").newObject([probe])))
        assert v < 0.5, f"{bay['label']}: SMA blocked by {v:.1f} mm^3 of wall"

        if not h.get("front_wiring_slots", True):
            continue
        # Header probe: box the size of the header footprint through the wall
        hx0, hx1 = mod["header_x_min"], mod["header_x_max"]
        bx0 = -hx1 if bay.get("mirror_x") else hx0
        probe = (
            cq.Workplane("XY")
            .box(
                hx1 - hx0, h["wall"] + 1.0, mod["header_top_y"] - 1.0, centered=(False, True, False)
            )
            .translate((cx + bx0, -L["outer_half_y"] + h["wall"] / 2.0, L["plate_bottom_z"] + 0.5))
        )
        v = _overlap(base, _orient(H, probe))
        assert v < 0.5, f"{bay['label']}: header slot blocked by {v:.1f} mm^3"


def test_modules_clear_the_tray(part):
    """
    Each bay's real vendor module (bays[].step), placed on its studs, must not
    significantly interfere with the base tray. Threshold is deliberately
    tight: a 5.6 mm^3 "acceptable" overlap turned out to be the SMA base block
    bearing on the front wall (fixed in v4 by the relief pocket) — loose
    thresholds hide real contact.
    """
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]

    for bay, cx in zip(L["bays"], L["bay_cx"]):
        module = _orient(
            H,
            cq.importers.importStep(str(VENDOR / bay["step"]))
            .rotate((0, 0, 0), (1, 0, 0), 90)
            .translate((cx, 0, L["plate_bottom_z"])),
        )
        inter = base.intersect(module)
        v = inter.val().Volume() if inter.solids().size() else 0.0
        assert v < 2.0, f"{bay['label']} interferes with tray by {v:.1f} mm^3"


def test_modules_clear_the_lid(part):
    """Real modules must also clear cover lips, baffles, and other lid features."""
    import cadquery as cq

    H = _housing(part)
    L = H["L"]
    lid = H["m"].create_lid(H["params"])
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        module = _orient(
            H,
            cq.importers.importStep(str(VENDOR / bay["step"]))
            .rotate((0, 0, 0), (1, 0, 0), 90)
            .translate((cx, 0, L["plate_bottom_z"])),
        )
        v = _overlap(lid, module)
        assert v < 2.0, f"{bay['label']} interferes with lid by {v:.1f} mm^3"


def test_screw_bosses_under_free_holes(part):
    """
    Each bay must have a screw boss (with an open pilot) directly under the
    module's two FREE 3.175mm plate holes — front inner hole (handed: the TX's
    front pair is mirrored, verified in the vendor analyses) and back center
    hole. Also checks the pilot bore is actually open.
    """
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    mod = H["params"]["module"]
    h = H["params"]["housing"]

    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        for hole in (mod["screw_hole_front"], mod["screw_hole_back"]):
            x = cx + sign * hole["x"]
            y = -hole["z"]
            # boss material present just under the plate (annular probe ring)
            ring = (
                cq.Workplane("XY")
                .circle(h["screw_boss_dia"] / 2.0 - 0.1)
                .circle(h["screw_boss_pilot_dia"] / 2.0 + 0.1)
                .extrude(0.5)
                .translate((x, y, L["plate_bottom_z"] - 0.5))
            )
            v = _overlap(base, _orient(H, ring))
            assert v > 1.0, (
                f"{bay['label']}: no screw boss at ({x:.1f}, {y:.1f}) (ring overlap {v:.2f} mm^3)"
            )
            # pilot bore open (a thin probe inside it meets no material)
            probe = (
                cq.Workplane("XY")
                .circle(h["screw_boss_pilot_dia"] / 2.0 - 0.15)
                .extrude(L["plate_bottom_z"] - h["floor"] - 0.2)
                .translate((x, y, h["floor"] + 0.1))
            )
            v = _overlap(base, _orient(H, probe))
            assert v < 0.05, f"{bay['label']}: pilot blocked by {v:.2f} mm^3"


def test_studs_on_bare_plate(part):
    """
    The four support studs per bay must sit clear of the vendor corner
    hardware, which protrudes 1.5mm below the plate in a ~4.3mm square at
    (±16.51, ∓18.92) — a stud under that would rock the module.
    """
    H = _housing(part)
    h = H["params"]["housing"]
    mod = H["params"]["module"]

    stud_r = h["stud_dia"] / 2.0
    for sx in (-h["stud_dx"], +h["stud_dx"]):
        for sz in h["stud_z"]:
            for hz in mod["corner_hole_z"]:
                dx = abs(abs(sx) - mod["corner_hole_dx"])
                dz = abs(sz - hz)
                # hardware half-extent ~2.2mm; require the stud edge clear of it
                clear = max(dx, dz) - stud_r - 2.2
                assert clear > 0, (
                    f"stud ({sx}, {sz}) under corner hardware at z={hz} (clearance {clear:.2f})"
                )


def test_lid_seats_on_base(part):
    """
    Lid and base must not overlap when assembled (explode_gap 0). The v2 lid
    failed this: its registration lip was a full-interior box that ran over
    the central rib and its screw posts, holding the lid 2mm proud.
    """
    H = _housing(part)
    assert H["params"]["housing"].get("explode_gap", 0.0) == 0.0
    v = _overlap(H["base"], H["m"].create_lid(H["params"]))
    assert v < 0.5, f"lid interferes with base by {v:.1f} mm^3"


def test_fiber_pass_slots_not_mirrored(part):
    """
    Probe through the partition at each module's true fiber-exit X. The fiber
    exit is NOT mirrored on the TX (both modules exit at bay-local +7.37 —
    verified in the vendor analyses), so a TX-handed bay's probe sits at
    cx + 7.37; a mirror_x-style implementation would leave wall there and fail.
    """
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    h = H["params"]["housing"]
    nub_r = H["params"]["module"]["fiber_nub_dia"] / 2.0

    for bay, fx in zip(L["bays"], L["fiber_x"]):
        probe = (
            cq.Workplane("XY")
            .box(2 * nub_r, h["wall"] + 1.0, 2 * nub_r, centered=(True, True, True))
            .translate((fx, (L["interior_half_y"] + L["plenum_y0"]) / 2.0, L["fiber_z"]))
        )
        v = _overlap(base, _orient(H, probe))
        assert v < 0.5, f"{bay['label']}: fiber pass-slot blocked by {v:.1f} mm^3"


def test_adapter_cutouts_and_pilots(part):
    """
    Each bay's back-panel port must pass the adapter body (probe the cutout)
    and both M2 flange-screw pilots through the wall.
    """
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    h = H["params"]["housing"]
    ad = H["params"]["sc_adapter"]
    wall_mid = L["plenum_y1"] + h["wall"] / 2.0

    vertical = L["mounting_orientation"] == "vertical"
    for bay, ax in zip(L["bays"], L["adapter_x"]):
        body = (
            cq.Workplane("XY")
            .box(
                ad["body_short"] if vertical else ad["body_long"],
                h["wall"] + 1.0,
                ad["body_long"] if vertical else ad["body_short"],
                centered=(True, True, True),
            )
            .translate((ax, wall_mid, L["fiber_z"]))
        )
        v = _overlap(base, _orient(H, body))
        assert v < 0.5, f"{bay['label']}: adapter cutout blocked by {v:.1f} mm^3"

        for offset in (-ad["screw_spacing"] / 2.0, +ad["screw_spacing"] / 2.0):
            px = ax if vertical else ax + offset
            pz = L["fiber_z"] + offset if vertical else L["fiber_z"]
            pilot = cq.Solid.makeCylinder(
                ad["screw_pilot_dia"] / 2.0 - 0.1,
                h["wall"] + 1.0,
                cq.Vector(px, L["plenum_y1"] - 0.5, pz),
                cq.Vector(0, 1, 0),
            )
            pilot_wp = cq.Workplane("XY").newObject([pilot])
            v = _overlap(base, _orient(H, pilot_wp))
            assert v < 0.05, f"{bay['label']}: screw pilot blocked by {v:.2f} mm^3"


def test_connector_corridor_clear(part):
    """
    The mated SC/APC connector + boot needs a straight corridor from the back
    wall into the plenum (adapter inner half + mated_connector_clear). Nothing
    — spool, posts, panel connector keep-out — may encroach on it.
    """
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    h = H["params"]["housing"]
    ad = H["params"]["sc_adapter"]

    inner_protrusion = (ad["body_len"] - ad["flange_thickness"]) / 2.0 - h["wall"]
    reach = inner_protrusion + ad["mated_connector_clear"]
    assert reach < H["params"]["fiber_bay"]["depth"] - 3.0, (
        "plenum too shallow for the mated connector"
    )

    vertical = L["mounting_orientation"] == "vertical"
    for bay, ax in zip(L["bays"], L["adapter_x"]):
        corridor = (
            cq.Workplane("XY")
            .box(
                ad["body_short"] if vertical else ad["body_long"],
                reach,
                ad["body_long"] if vertical else ad["body_short"],
                centered=(True, False, True),
            )
            .translate((ax, L["plenum_y1"] - reach, L["fiber_z"]))
        )
        v = _overlap(base, _orient(H, corridor))
        assert v < 0.5, f"{bay['label']}: connector corridor blocked by {v:.1f} mm^3"


def test_spool_respects_bend_radius(part):
    """The slack spool's radius is the fiber's enforced minimum bend radius."""
    fb = _housing(part)["params"]["fiber_bay"]
    assert fb["spool_dia"] / 2.0 >= fb["min_bend_radius"]


def test_wire_headroom_over_can(part):
    """
    Internal-wiring variants: the header harness runs over the can top to the
    partition pass-slot, so the lid must leave that airspace clear — a solid
    lip pad (the mixed housing's style) would leave ~1mm and pinch the wires.
    Probe the bay's inner airspace between can top and lid underside against
    the LID: only the perimeter ring lip may descend, so the probe (inside the
    ring) must meet nothing.
    """
    import cadquery as cq

    H = _housing(part)
    h = H["params"]["housing"]
    if h.get("front_wiring_slots", True):
        pytest.skip("variant wires out the front, no internal harness")
    L = H["L"]
    mod = H["params"]["module"]
    lid = H["m"].create_lid(H["params"])

    can_top = L["plate_bottom_z"] + mod["can_height_y"]
    refine = H["params"].get("refinement", {})
    ring = (
        refine.get("registration_ring_width", 3.0) + refine.get("registration_clearance", 0.3) + 0.2
    )
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        if refine.get("enabled"):
            # Refined covers place vent baffles on the side opposite the
            # header. Probe the actual header-to-partition harness corridor.
            header_sign = -1.0 if bay.get("mirror_x") else 1.0
            probe_w = 9.0
            probe_x = cx + header_sign * 11.0
        else:
            probe_w = L["bay_w"] - 2 * ring
            probe_x = cx
        probe = (
            cq.Workplane("XY")
            .box(
                probe_w,
                L["bay_d"] - 2 * ring,
                L["base_height"] - 0.1 - (can_top + 0.1),
                centered=(True, True, False),
            )
            .translate((probe_x, 0, can_top + 0.1))
        )
        v = _overlap(lid, _orient(H, probe))
        assert v < 0.5, f"lid intrudes into wire airspace by {v:.1f} mm^3"


def test_panel_connector_cutout_and_keepout(part):
    """
    Variants with a rear signal connector (DE-9): the body cutout and both
    jackscrew holes must pass the back wall, and the rear-shell/solder-cup
    keep-out volume inside the plenum must be empty (spool clear of it).
    """
    import cadquery as cq

    H = _housing(part)
    pc = H["params"].get("panel_connector")
    if not pc:
        pytest.skip("variant has no panel connector")
    L, base = H["L"], H["base"]
    h = H["params"]["housing"]
    vertical = L["mounting_orientation"] == "vertical"
    pc_z = L["panel_connector_z"]

    cutout = (
        cq.Workplane("XY")
        .box(
            (pc["cutout_h"] if vertical else pc["cutout_w"]) - 0.2,
            h["wall"] + 1.0,
            (pc["cutout_w"] if vertical else pc["cutout_h"]) - 0.2,
            centered=(True, True, True),
        )
        .translate((pc["x"], L["plenum_y1"] + h["wall"] / 2.0, pc_z))
    )
    v = _overlap(base, _orient(H, cutout))
    assert v < 0.5, f"panel connector cutout blocked by {v:.1f} mm^3"

    for offset in (-pc["screw_spacing"] / 2.0, +pc["screw_spacing"] / 2.0):
        px = pc["x"] if vertical else pc["x"] + offset
        pz = pc_z + offset if vertical else pc_z
        hole = cq.Solid.makeCylinder(
            pc["screw_hole_dia"] / 2.0 - 0.1,
            h["wall"] + 1.0,
            cq.Vector(px, L["plenum_y1"] - 0.5, pz),
            cq.Vector(0, 1, 0),
        )
        hole_wp = cq.Workplane("XY").newObject([hole])
        v = _overlap(base, _orient(H, hole_wp))
        assert v < 0.05, f"jackscrew hole blocked by {v:.2f} mm^3"

    keepout = (
        cq.Workplane("XY")
        .box(
            pc["rear_keepout_h"] if vertical else pc["rear_keepout_w"],
            pc["rear_keepout_depth"],
            pc["rear_keepout_w"] if vertical else pc["rear_keepout_h"],
            centered=(True, False, True),
        )
        .translate((pc["x"], L["plenum_y1"] - pc["rear_keepout_depth"], pc_z))
    )
    v = _overlap(base, _orient(H, keepout))
    assert v < 0.5, f"panel connector rear keep-out blocked by {v:.1f} mm^3"


def test_vertical_variants_trade_width_for_height(part):
    """The new variants must be materially narrower and taller than originals."""
    H = _housing(part)
    if H["L"]["mounting_orientation"] != "vertical":
        pytest.skip("horizontal baseline variant")
    L = H["L"]
    assert L["envelope_width"] < 0.45 * L["envelope_height"]
    assert L["envelope_height"] > 2 * L["envelope_width"]


def test_refined_spool_is_hollow_and_retains_wraps(part):
    """Refined spool must contain a lightening void and a positive end flange."""
    import cadquery as cq

    H = _housing(part)
    refine = H["params"].get("refinement", {})
    if not refine.get("enabled"):
        pytest.skip("standard solid spool")
    L, base = H["L"], H["base"]
    h = H["params"]["housing"]

    # Point midway between the three radial webs, outside the screw hub.
    void_probe = (
        cq.Workplane("XY")
        .center(6.93, L["spool_y"] + 4.0)
        .circle(0.55)
        .extrude(L["base_height"] - h["floor"] - 3.0)
        .translate((0, 0, h["floor"] + 1.5))
    )
    assert _overlap(base, _orient(H, void_probe)) < 0.05

    # The cover-side flange extends beyond the 15 mm winding drum.
    flange_probe = (
        cq.Workplane("XY")
        .center(15.75, L["spool_y"])
        .circle(0.25)
        .extrude(0.4)
        .translate((0, 0, L["base_height"] - 0.8))
    )
    assert _overlap(base, _orient(H, flange_probe)) > 0.05


def test_refined_cable_saddles_have_open_tunnels(part):
    """Tie saddles need a structural bridge and a clear reusable-tie tunnel."""
    import cadquery as cq

    H = _housing(part)
    refine = H["params"].get("refinement", {})
    if not refine.get("enabled"):
        pytest.skip("no production cable saddles")
    L, base = H["L"], H["base"]
    h = H["params"]["housing"]
    saddle_w = refine["cable_saddle_width"]
    saddle_d = refine["cable_saddle_depth"]
    front_x = L["interior_half_x"] - saddle_w / 2.0 - 5.0
    front_y = L["plenum_y0"] + 6.0

    bridge = (
        cq.Workplane("XY")
        .box(saddle_w - 0.4, saddle_d - 0.4, 0.4, centered=(True, True, False))
        .translate((front_x, front_y, h["floor"] + refine["cable_saddle_height"] - 0.5))
    )
    assert _overlap(base, _orient(H, bridge)) > 1.0

    tunnel = (
        cq.Workplane("XY")
        .box(
            refine["cable_saddle_tunnel_width"] - 0.3,
            saddle_d + 0.4,
            refine["cable_saddle_tunnel_height"] - 0.3,
            centered=(True, True, False),
        )
        .translate((front_x, front_y, h["floor"] + 0.1))
    )
    assert _overlap(base, _orient(H, tunnel)) < 0.05


def test_refined_gravity_drains_are_open(part):
    """Upper-to-lower cross-drain and both downward outlets must be unobstructed."""
    import cadquery as cq

    H = _housing(part)
    refine = H["params"].get("refinement", {})
    if not refine.get("enabled"):
        pytest.skip("no gravity-aware drain system")
    L, base = H["L"], H["base"]
    h = H["params"]["housing"]
    r = refine["drain_dia"] / 2.0 - 0.15
    z = h["floor"] + refine["drain_dia"] / 2.0 + 0.25

    probes = [
        cq.Solid.makeCylinder(
            r,
            h["bay_gap"] + 1.0,
            cq.Vector(-h["bay_gap"] / 2.0 - 0.5, 20.0, z),
            cq.Vector(1, 0, 0),
        )
    ]
    for y in (20.0, L["plenum_y0"] + 8.0):
        probes.append(
            cq.Solid.makeCylinder(
                r,
                h["wall"] + 1.0,
                cq.Vector(L["interior_half_x"] - 0.5, y, z),
                cq.Vector(1, 0, 0),
            )
        )
    for probe in probes:
        probe_wp = cq.Workplane("XY").newObject([probe])
        assert _overlap(base, _orient(H, probe_wp)) < 0.05


def test_refined_vents_open_and_baffles_present(part):
    """Vent slots must pass the cover and retain their offset splash baffles."""
    import cadquery as cq

    H = _housing(part)
    refine = H["params"].get("refinement", {})
    if not refine.get("enabled"):
        pytest.skip("standard unvented cover")
    L = H["L"]
    lid = H["m"].create_lid(H["params"])
    bay = L["bays"][0]
    cx = L["bay_cx"][0]
    header_sign = -1.0 if bay.get("mirror_x") else 1.0
    vent_x = cx - header_sign * refine["vent_opposite_header_offset"]

    vent_probe = (
        cq.Workplane("XY")
        .center(vent_x, refine["vent_y"])
        .slot2D(refine["vent_length"] - 0.4, refine["vent_width"] - 0.3, 90)
        .extrude(H["params"]["housing"]["lid_thickness"] + 0.5)
        .translate((0, 0, L["base_height"] - 0.25))
    )
    assert _overlap(lid, _orient(H, vent_probe)) < 0.05

    baffle_z = L["base_height"] - refine["vent_baffle_gap"] - refine["vent_baffle_thickness"]
    baffle_probe = (
        cq.Workplane("XY")
        .box(2.0, 2.0, 0.4, centered=(True, True, False))
        .translate((vent_x, refine["vent_y"], baffle_z + 0.2))
    )
    assert _overlap(lid, _orient(H, baffle_probe)) > 1.0
