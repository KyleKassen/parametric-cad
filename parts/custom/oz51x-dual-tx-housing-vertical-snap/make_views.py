"""Reproducible product/fit views from exported CAD, with labelled reference hardware."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).absolute().parent
ROOT = PART_DIR.parents[2]
sys.path.insert(0, str(ROOT))
from lib.render_step import PRODUCT_VIEWS, Material, render_product_scene  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    m = load(PART_DIR / "model.py", "snap_render_model")
    p, out = m.load_params(), PART_DIR / "references" / "product"
    L = m.layout(p)
    version = p["version"]
    base = cq.importers.importStep(str(PART_DIR / f"exports/base_{version}.step")).val()
    cover = cq.importers.importStep(str(PART_DIR / f"exports/cover_{version}.step")).val()
    plastic = Material((0.16, 0.18, 0.20), 0, 0.7)
    metal = Material((0.49, 0.52, 0.55), 0.7, 0.35)
    green = Material((0.07, 0.30, 0.17), 0, 0.6)
    PRODUCT_VIEWS["front_io"] = ((0.90, 1.10, 0.50), (0, 0, 1))
    PRODUCT_VIEWS["open"] = ((1.3, 0.9, 0.75), (0, 0, 1))
    PRODUCT_VIEWS["interior_elevation"] = ((1, 0, 0), (0, 0, 1))
    PRODUCT_VIEWS["front_elevation"] = ((0, 1, 0), (0, 0, 1))
    PRODUCT_VIEWS["cover_inside"] = ((-0.3, -0.5, -1), (0, 1, 0))
    common = dict(size=1500, background="dark", fill_cracks=False)
    bare = [(base, plastic, 1), (cover, plastic, 1)]
    render_product_scene(bare, out, "housing", views=("front_io", "hero"), **common)

    family = load(PART_DIR.parent / "oz510-dual-housing/fit_check.py", "render_family_fit")
    am = load(ROOT / "parts/vendor/sc-apc-simplex-adapter/model.py", "render_adapter")
    adapter, ap = am.create_part(), am.load_params()["dimensions"]
    hw = []
    for ax in L["adapter_x"]:
        placed = family.place_adapter(adapter, ap, L, ax).translate((0, -0.8, 0)).val()
        hw.append((placed, green, 1))

    # DE-9 is a simplified presentation reference, not a supplier STEP or fit proof.
    pc = p["panel_connector"]
    zc, yf = L["panel_connector_z"], L["back_outer_y"] - pc["flange_recess"]
    flange = m.rounded_box(30.81, 12.55, 0.9, 1.5, top_break=0.1, bottom_break=0.1)
    flange = flange.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, yf + 0.9, zc))
    q = copy.deepcopy(p)
    q["panel_connector"].update(cutout_w=16.33, cutout_h=7.9, cutout_radius=2.0)
    shell = m.d_profile(q, 4.5)
    q["panel_connector"].update(cutout_w=14.8, cutout_h=6.4, cutout_radius=1.4)
    core = m.d_profile(q, 5)
    shell = shell.cut(core).rotate((0, 0, 0), (1, 0, 0), 90).translate((0, yf + 5.4, zc))
    insert = m.d_profile(q, 4).rotate((0, 0, 0), (1, 0, 0), 90).translate((0, yf + 5.1, zc))
    for zs, xs in ((1.42, (-5.54, -2.77, 0, 2.77, 5.54)), (-1.42, (-4.155, -1.385, 1.385, 4.155))):
        for x in xs:
            insert = insert.cut(m._refine._y_cyl(0.55, x, zc + zs, yf + 3.8, 2))
    for dx in (-12.495, 12.495):
        flange = flange.union(m._refine._y_cyl(2.3, dx, zc, yf + 0.5, 4.0))
    for part, color in (
        (flange, metal),
        (shell, metal),
        (insert, Material((0.04, 0.045, 0.05), 0, 0.6)),
    ):
        hw.append((m.orient_to_mounting(part, p).val(), color, 1))
    render_product_scene(
        bare + hw, out, "with_reference_connectors", views=("front_io", "front_elevation"), **common
    )
    modules = []
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        v = family.place_module(ROOT / "parts/vendor" / bay["step"], cx, L["plate_bottom_z"])
        modules.append((m.orient_to_mounting(v, p).val(), metal, 1))
    render_product_scene(
        [(base, plastic, 1)] + hw + modules,
        out,
        "open_housing",
        views=("open", "interior_elevation"),
        **common,
    )
    render_product_scene(
        [(base, plastic, 1), (cover.translate((38, 0, 0)), plastic, 1)] + hw,
        out,
        "exploded",
        views=("front_io",),
        **common,
    )
    canonical_cover = m._create_lid_canonical(p).val()
    render_product_scene(
        [(canonical_cover, plastic, 1)],
        out,
        "cover_detail",
        views=("cover_inside",),
        ground=False,
        **common,
    )


if __name__ == "__main__":
    main()
