"""
Drop the real vendor modules into an OZ51x-family housing and verify the fit.

Prints interference volumes against the base tray (modules, lid, vendor SC/APC
adapters and their mated pigtail connectors — all should be ~0) and
regenerates the reference renders in references/ (fit_open_*, fit_closed_*).
Which module STEP goes in which bay comes from the part's params.json
(bays[].step, relative to parts/vendor/), so this same script serves every
variant — the dual-TX / dual-RX wrappers call main() with their own part dir:

    uv run python parts/custom/oz510-dual-housing/fit_check.py

This is the visual half of verification; the numeric half lives in
tests/test_oz51x_housings.py. Both exist because a housing can pass an
overall interference check while a cutout sits on the wrong side (the v1
mirror bug escaped exactly that way).
"""

import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cadquery as cq  # noqa: E402

from lib.housing import interference  # noqa: E402
from lib.render_step import render_scene  # noqa: E402

VENDOR = PROJECT_ROOT / "parts" / "vendor"
ADAPTER_DIR = VENDOR / "sc-apc-simplex-adapter"
CONNECTOR_DIR = VENDOR / "sc-apc-connector"

BLUE = (0.30, 0.55, 0.85)  # receiver-handed bays
ORANGE = (0.85, 0.45, 0.30)  # transmitter-handed bays
SHELL = (0.55, 0.60, 0.68)
GREEN = (0.20, 0.65, 0.30)
DARKGREEN = (0.10, 0.45, 0.20)


def _load_model(part_dir: Path = PART_DIR, name: str = "oz510_housing_model"):
    spec = importlib.util.spec_from_file_location(name, part_dir / "model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def place_module(step_path: Path, cx: float, plate_bottom_z: float) -> cq.Workplane:
    """Module local frame -> housing frame: rotate +90 deg about X, translate."""
    return (
        cq.importers.importStep(str(step_path))
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((cx, 0, plate_bottom_z))
    )


def place_adapter(adapter: cq.Workplane, ad: dict, L: dict, ax: float) -> cq.Workplane:
    """
    Install a vendor SC adapter (origin = body/flange center, axis = Y) in the
    back panel: flange seated on the outer wall face, body through the cutout.
    """
    yc = L["back_outer_y"] + ad["flange_thickness"] / 2.0
    if L["mounting_orientation"] == "vertical":
        x = L["fiber_z"] - L["envelope_width"] / 2.0
        z = L["outer_half_x"] - ax
        return adapter.translate((x, yc, z))
    return adapter.translate((ax, yc, L["fiber_z"]))


def place_connector(conn: cq.Workplane, ad: dict, L: dict, ax: float) -> cq.Workplane:
    """
    Mate a vendor SC connector (origin = grip stop face, plug = +Y) into the
    inner port of the adapter at ax: stop face on the adapter's inner end.
    """
    yc = L["back_outer_y"] + ad["flange_thickness"] / 2.0
    inner_end = yc - ad["body_len"] / 2.0
    if L["mounting_orientation"] == "vertical":
        x = L["fiber_z"] - L["envelope_width"] / 2.0
        z = L["outer_half_x"] - ax
        return conn.translate((x, inner_end, z))
    return conn.translate((ax, inner_end, L["fiber_z"]))


def main(part_dir: Path = PART_DIR) -> int:
    m = _load_model(part_dir)
    params = m.load_params()
    L = m.layout(params)
    base = m.create_base(params)
    lid = m.create_lid(params)

    modules = [
        m.orient_to_mounting(place_module(VENDOR / bay["step"], cx, L["plate_bottom_z"]), params)
        for bay, cx in zip(L["bays"], L["bay_cx"])
    ]

    # Real vendor stand-in models (datasheet-derived), placed mated in the
    # back panel — this cross-checks the housing cutout/pilot geometry against
    # the vendor part's own params, not a copy of the housing's numbers.
    adapter_mod = _load_model(ADAPTER_DIR, "sc_adapter_model")
    conn_mod = _load_model(CONNECTOR_DIR, "sc_connector_model")
    ad = adapter_mod.load_params()["dimensions"]
    adapter_part = adapter_mod.create_part()
    conn_part = conn_mod.create_part()
    adapters = [place_adapter(adapter_part, ad, L, ax) for ax in L["adapter_x"]]
    connectors = [place_connector(conn_part, ad, L, ax) for ax in L["adapter_x"]]

    print(f"\n  {params['part_name']} ({params.get('version', '?')}) — fit check\n")
    ok = True
    checks = [(b["label"], mod) for b, mod in zip(L["bays"], modules)]
    checks += [("lid", lid)]
    checks += [(f"SC adapter {b['label']}", a) for b, a in zip(L["bays"], adapters)]
    checks += [(f"SC connector {b['label']}", c) for b, c in zip(L["bays"], connectors)]
    for name, solid in checks:
        # A failed boolean op is an ERROR, never a clearance: interference()
        # raises, and we fail the run rather than reporting a phantom 0.00.
        try:
            v = interference(base, solid)
        except Exception as e:
            ok = False
            print(f"  {name:>28} ∩ base tray:    ERROR   [{type(e).__name__}: {e}]")
            continue
        status = "ok" if v < 2.0 else "INTERFERENCE"
        ok = ok and v < 2.0
        print(f"  {name:>28} ∩ base tray: {v:8.2f} mm^3   [{status}]")

    out = part_dir / "references"
    module_bits = [
        (mod.val(), ORANGE if b.get("mirror_x") else BLUE, 1.0)
        for b, mod in zip(L["bays"], modules)
    ]
    fiber_bits = [(a.val(), GREEN, 1.0) for a in adapters]
    fiber_bits += [(c.val(), DARKGREEN, 1.0) for c in connectors]
    written = render_scene(
        [(base.val(), SHELL, 0.35)] + module_bits + fiber_bits,
        out,
        "fit_open",
        views=("iso", "front", "top", "back"),
    )
    written += render_scene(
        [(base.val(), SHELL, 0.25), (lid.val(), SHELL, 0.25)] + module_bits + fiber_bits,
        out,
        "fit_closed",
        views=("iso", "back"),
    )
    if params.get("refinement", {}).get("enabled"):
        written += render_scene(
            [(base.val(), SHELL, 1.0)],
            out,
            "design_base",
            views=("iso", "right"),
        )
        written += render_scene(
            [(lid.val(), SHELL, 1.0)],
            out,
            "design_cover",
            views=("iso", "right", "left"),
        )
    for p in written:
        print(f"  ✓ {p.relative_to(PROJECT_ROOT)}")

    print(f"\n  {'✓ fit OK' if ok else '✗ FIT PROBLEM — see volumes above'}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
