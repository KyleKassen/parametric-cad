"""Renders: dark product shots plus translucent engineering views.

Product shots follow DESIGN_LANGUAGE.md presentation rules: matte dark
palette, no axis triad.  Engineering views keep translucency and axes for
verification.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.render_step import render_scene  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "am59_cold_wall_enclosure_model",
    PART_DIR / "model.py",
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)

# Matte "black anodize" reads correctly in the flat headlight renderer at
# mid-gray values; true 0.15-0.2 grays crush to silhouette.
BODY = (0.42, 0.43, 0.445)
BODY_LIGHT = (0.50, 0.51, 0.52)
ACCENT = (0.56, 0.57, 0.58)


def _add(scene, workplane, rgb, opacity=1.0):
    for shape in workplane.vals():
        scene.append((shape, rgb, opacity))


def build_product_scene() -> list:
    """Everything opaque, matte dark — the reference-style product shot."""
    params = model.load_params()
    scene: list = []
    _add(scene, model.create_enclosure_tub(params), BODY)
    _add(scene, model.create_lid(params), BODY_LIGHT)
    _add(scene, model.create_solar_shield(params), ACCENT)
    _add(scene, model.create_air_tunnel_hood(params), BODY)
    _add(scene, model.create_mesh_screens_reference(params), (0.22, 0.22, 0.24))
    _add(scene, model.create_relocated_heatsink_reference(params), (0.47, 0.48, 0.49))
    _add(scene, model.create_heatsink_duct_sheet(params), (0.44, 0.45, 0.46))
    _add(scene, model.create_heatsink_cradle(params), BODY_LIGHT)
    return scene


def build_engineering_scene(*, with_lid: bool = True) -> list:
    """Translucent shell revealing the split boundary and reservations."""
    params = model.load_params()
    scene: list = []
    _add(scene, model.create_enclosure_tub(params), (0.72, 0.76, 0.80), 0.30)
    if with_lid:
        _add(scene, model.create_lid(params), (0.80, 0.83, 0.86), 0.25)
        _add(scene, model.create_solar_shield(params), (0.93, 0.94, 0.95), 0.35)
    _add(scene, model.create_lid_gasket_reference(params), (0.10, 0.12, 0.10))
    _add(scene, model.create_amplifier_chassis_reference(params), (0.30, 0.31, 0.34))
    _add(scene, model.create_relocated_heatsink_reference(params), (0.55, 0.58, 0.62))
    _add(scene, model.create_tim_references(params), (0.65, 0.18, 0.18))
    _add(scene, model.create_flange_clamp_bars(params), (0.18, 0.38, 0.68))
    _add(scene, model.create_heatsink_cradle(params), (0.24, 0.42, 0.66))
    _add(scene, model.create_heatsink_duct_sheet(params), (0.45, 0.50, 0.55))
    _add(scene, model.create_air_tunnel_hood(params), (0.88, 0.89, 0.91), 0.30)
    _add(scene, model.create_mesh_screens_reference(params), (0.25, 0.25, 0.28), 0.75)
    _add(scene, model.create_din_provision(params), (0.15, 0.48, 0.26))
    _add(scene, model.create_din_keepout_reference(params), (0.25, 0.70, 0.40), 0.20)
    return scene


if __name__ == "__main__":
    out_dir = PART_DIR / "references" / "views"
    version = model.load_params()["version"]
    written = []
    written += render_scene(
        build_product_scene(),
        out_dir,
        f"am59_cold_wall_enclosure_{version}_product",
        views=("iso", "front", "right"),
        size=1400,
        axes=False,
    )
    written += render_scene(
        build_engineering_scene(with_lid=True),
        out_dir,
        f"am59_cold_wall_enclosure_{version}_concept",
        views=("iso", "front"),
        size=1400,
        axes=False,
    )
    written += render_scene(
        build_engineering_scene(with_lid=False),
        out_dir,
        f"am59_cold_wall_enclosure_{version}_open",
        views=("iso", "top"),
        size=1400,
        axes=False,
    )
    for path in written:
        print(path)
