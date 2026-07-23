"""
Feature tests for the Fable 5 Extra vertical housings — everything the
redesign ADDED on top of the verified family interfaces. The inherited
interfaces (bays, studs, bosses, SMA, fiber, SC/APC, DE-9, corridors,
keep-outs, lid seating, wire headroom) are covered by the shared suite in
test_oz51x_housings.py, which also runs against these two parts.

Probes are built in the canonical tray frame and pushed through
orient_to_mounting, exactly like the shared suite.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PARTS = [
    "oz51x-dual-rx-housing-vertical-fable5-extra",
    "oz51x-dual-tx-housing-vertical-fable5-extra",
]

_CACHE: dict = {}


def _housing(part: str):
    if part not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            part.replace("-", "_"),
            PROJECT_ROOT / "parts" / "custom" / part / "model.py",
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        params = m.load_params()
        L = m.layout(params)
        _CACHE[part] = {"m": m, "params": params, "L": L,
                        "base": m.create_base(params),
                        "lid": m.create_lid(params)}
    return _CACHE[part]


@pytest.fixture(params=PARTS)
def part(request):
    return request.param


def _overlap(a, b) -> float:
    a = a.val() if hasattr(a, "val") else a
    b = b.val() if hasattr(b, "val") else b
    try:
        return abs(a.intersect(b).Volume())
    except Exception:
        return 0.0


def _orient(H, shape):
    return H["m"].orient_to_mounting(shape, H["params"])


def _flange_slot_centers(H):
    """Canonical-frame (x, y) centers of the four mount-flange slots."""
    L = H["L"]
    fl = L["industrial"]["mount_flanges"]
    xs = [-(L["outer_half_x"] + fl["protrusion"] / 2.0),
          +(L["outer_half_x"] + fl["protrusion"] / 2.0)]
    ys = [-L["outer_half_y"] + fl["slot_from_ends"],
          L["back_outer_y"] - fl["slot_from_ends"]]
    return [(x, y) for x in xs for y in ys]


def test_mount_flanges_present_with_open_slots(part):
    """Both flanges exist (material mid-span), and all four screw slots pass
    cleanly through them."""
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    fl = L["industrial"]["mount_flanges"]
    assert L["has_flanges"], "vertical Fable5 variants must have mount flanges"
    t = fl["thickness"]

    for s in (-1.0, 1.0):
        probe = (
            cq.Workplane("XY")
            .box(fl["protrusion"] - 2.0, 12.0, t - 0.4, centered=(True, True, True))
            .translate((s * (L["outer_half_x"] + fl["protrusion"] / 2.0),
                        0.0, t / 2.0))
        )
        v = _overlap(base, _orient(H, probe))
        assert v > 50.0, f"flange material missing on side {s:+.0f} ({v:.1f} mm^3)"

        # gusset root blends the flange into the wall (support-free print)
        g = (
            cq.Workplane("XY")
            .box(1.0, 12.0, 1.0, centered=(True, True, True))
            .translate((s * (L["outer_half_x"] + 0.7), 0.0, t + 0.7))
        )
        v = _overlap(base, _orient(H, g))
        assert v > 1.0, f"gusset missing on side {s:+.0f} ({v:.2f} mm^3)"

    for x, y in _flange_slot_centers(H):
        slot_probe = (
            cq.Workplane("XY")
            .slot2D(fl["slot_length"] - 0.2, fl["slot_width"] - 0.2, 90)
            .extrude(t + 1.0)
            .translate((x, y, -0.5))
        )
        v = _overlap(base, _orient(H, slot_probe))
        assert v < 0.05, f"flange slot at ({x:.1f}, {y:.1f}) blocked by {v:.2f} mm^3"


def test_bottom_face_vents_open_top_face_solid(part):
    """The finished bottom face (canonical +X wall) has open intake/weep
    slots; the finished top face (canonical -X wall) must stay solid —
    upward-facing openings would collect dust and drips."""
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    vents = L["industrial"]["vents"]
    h = H["params"]["housing"]
    wall_mid = (L["interior_half_x"] + L["outer_half_x"]) / 2.0

    for zc in vents["wall_slot_z"]:
        # slot ends must stay inside the bay (never breach the plenum)
        assert (abs(vents["wall_slot_y"]) + vents["wall_slot_length"] / 2.0
                < L["interior_half_y"])
        probe = (
            cq.Workplane("XY")
            .box(h["wall"] + 1.0, vents["wall_slot_length"] - 0.4,
                 vents["slot_width"] - 0.4, centered=(True, True, True))
            .translate((wall_mid, vents["wall_slot_y"], zc))
        )
        v = _overlap(base, _orient(H, probe))
        assert v < 0.05, f"bottom vent at z={zc} blocked by {v:.2f} mm^3"

        control = probe.translate((-2 * wall_mid, 0, 0))  # mirrored: -X wall
        v = _overlap(base, _orient(H, control))
        assert v > 50.0, f"top face breached at z={zc} ({v:.1f} mm^3)"


def test_cover_louvers_open(part):
    """Both cover louver groups (low intake over the lower bay, high exhaust
    over the upper bay) pass through the lid."""
    import cadquery as cq

    H = _housing(part)
    L, lid = H["L"], H["lid"]
    vents = L["industrial"]["vents"]
    h = H["params"]["housing"]
    z0 = L["base_height"]

    for s in (-1.0, 1.0):
        for xc in vents["cover_slot_x"]:
            probe = (
                cq.Workplane("XY")
                .box(vents["slot_width"] - 0.4,
                     vents["cover_slot_length"] - 0.4,
                     h["lid_thickness"] + 1.0, centered=(True, True, True))
                .translate((s * xc, vents["cover_slot_y"],
                            z0 + h["lid_thickness"] / 2.0))
            )
            v = _overlap(lid, _orient(H, probe))
            assert v < 0.05, f"cover louver at x={s * xc:.1f} blocked by {v:.2f} mm^3"


def test_sc_adapter_recess_pockets(part):
    """Each SC adapter flange seats in a shallow recess: the pocket volume is
    empty, and the wall directly behind it is still solid (the pocket must
    not eat the whole panel)."""
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    ad = H["params"]["sc_adapter"]
    rc = L["industrial"]["connector_recess"]

    pocket_w = ad["flange_wide"] + 2 * rc["clearance"] - 0.3
    pocket_h = ad["flange_len"] + 2 * rc["clearance"] - 0.3
    for ax in L["adapter_x"]:
        pocket = (
            cq.Workplane("XY")
            .box(pocket_w, rc["sc_depth"] - 0.1, pocket_h,
                 centered=(True, False, True))
            .edges("|Y").fillet(rc["corner_radius"])
            .translate((ax, L["back_outer_y"] - rc["sc_depth"] + 0.05, L["fiber_z"]))
        )
        v = _overlap(base, _orient(H, pocket))
        assert v < 0.5, f"SC recess at x={ax} not clear ({v:.2f} mm^3)"

        # solid wall must remain behind the pocket floor: probe the band
        # inside the flange footprint but outside the body cutout, offset
        # sideways so it misses both M2 pilots (which sit at x = ax)
        sgn = 1.0 if ax >= 0 else -1.0
        behind = (
            cq.Workplane("XY")
            .box(1.0, 0.8, 2.0, centered=(True, True, True))
            .translate((ax + sgn * 5.6,
                        L["back_outer_y"] - rc["sc_depth"] - 0.6,
                        L["fiber_z"]))
        )
        v = _overlap(base, _orient(H, behind))
        assert v > 1.2, f"no wall behind SC recess at x={ax} ({v:.2f} mm^3)"


def test_de9_top_jackscrew_capture_slot(part):
    """The DE-9's top jackscrew opening is a deliberate slot to the parting
    face (v1 left a 0.12 mm ligament that would break unpredictably); the
    bottom jackscrew stays a closed hole."""
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    pc = H["params"]["panel_connector"]
    h = H["params"]["housing"]
    pc_z = L["panel_connector_z"]
    top_z = pc_z + pc["screw_spacing"] / 2.0
    bot_z = pc_z - pc["screw_spacing"] / 2.0

    slot = (
        cq.Workplane("XY")
        .box(pc["screw_hole_dia"] - 0.4, h["wall"] + 1.0,
             L["base_height"] - top_z + 0.4, centered=(True, True, False))
        .translate((pc["x"], L["plenum_y1"] + h["wall"] / 2.0, top_z - 0.2))
    )
    v = _overlap(base, _orient(H, slot))
    assert v < 0.05, f"top jackscrew capture slot blocked by {v:.2f} mm^3"

    # closed bottom hole: material must exist immediately left/right of it
    # (above it sits the DE-9 body cutout, which is correctly open)
    for dx in (-pc["screw_hole_dia"], +pc["screw_hole_dia"]):
        ring = (
            cq.Workplane("XY")
            .box(1.0, h["wall"] - 0.4, 2.0, centered=(True, True, True))
            .translate((pc["x"] + dx, L["plenum_y1"] + h["wall"] / 2.0, bot_z))
        )
        v = _overlap(base, _orient(H, ring))
        assert v > 1.0, f"bottom jackscrew not a closed hole (dx={dx}, {v:.2f})"


def test_harness_anchors_present_and_clear(part):
    """Tie-down post pairs exist on the plenum floor and stay clear of the
    DE-9 rear keep-out and both SC connector corridors."""
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    ha = L["industrial"]["harness_anchors"]
    ad = H["params"]["sc_adapter"]
    pc = H["params"]["panel_connector"]
    h = H["params"]["housing"]

    anchor_y = L["plenum_y1"] - ha["y_from_back_wall"]
    pitch = ha["post_gap"] + ha["post_dia"]
    for axc in ha["x"]:
        # clearance by construction: outside DE-9 keep-out, inside corridors
        outer = abs(axc) + pitch / 2.0 + ha["post_dia"] / 2.0
        inner = abs(axc) - pitch / 2.0 - ha["post_dia"] / 2.0
        assert inner > pc["rear_keepout_h"] / 2.0
        for ax in L["adapter_x"]:
            assert outer < abs(ax) - ad["body_short"] / 2.0
        for dxp in (-pitch / 2.0, +pitch / 2.0):
            probe = (
                cq.Workplane("XY")
                .circle(ha["post_dia"] / 2.0 - 0.2)
                .extrude(ha["height"] - 1.0)
                .translate((axc + dxp, anchor_y, h["floor"] + 0.2))
            )
            v = _overlap(base, _orient(H, probe))
            assert v > 5.0, f"anchor post missing at ({axc + dxp:.1f}) ({v:.1f})"


def test_identity_label_engraved(part):
    """A thin skin probe over the identity text zone on the front face must
    meet LESS than full material (glyphs removed) but more than none (the
    panel is still there) — catches both a missing engrave and a wrong-face
    engrave."""
    import cadquery as cq

    H = _housing(part)
    L, base = H["L"], H["base"]
    lab = L["industrial"]["labels"]

    w_z = lab["identity_size"] * 1.4   # text runs along canonical Z
    h_x = lab["identity_size"] * 1.1
    skin = 0.3
    probe = (
        cq.Workplane("XY")
        .box(h_x, skin, w_z, centered=(True, False, True))
        .translate((0.0, -L["outer_half_y"], lab["identity_z"]))
    )
    full = h_x * skin * w_z
    v = _overlap(base, _orient(H, probe))
    assert v < 0.93 * full, f"no engraving detected ({v:.1f} of {full:.1f} mm^3)"
    assert v > 0.30 * full, f"front panel missing at label zone ({v:.1f} mm^3)"


def test_flanges_extend_envelope_and_stay_flush(part):
    """The flanges extend the finished height by exactly 2x protrusion and
    lie flush with the mount face (canonical z=0)."""
    H = _housing(part)
    L = H["L"]
    fl = L["industrial"]["mount_flanges"]
    assert abs(L["envelope_height"]
               - (2 * L["outer_half_x"] + 2 * fl["protrusion"])) < 1e-6

    bb = H["base"].val().BoundingBox()
    # finished frame: mount face at x = -envelope_width/2
    assert abs(bb.xmin - (-L["envelope_width"] / 2.0)) < 0.01, \
        "flange must not protrude past the mount face"
