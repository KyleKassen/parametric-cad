"""Render colored engineering views of the AM59 IP66 concept."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
MODEL_PATH = PART_DIR / "model.py"
OUT_DIR = PART_DIR / "references" / "views"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.render_step import render_scene  # noqa: E402


def _load_model():
    spec = importlib.util.spec_from_file_location(
        "am59_ip66_passive_render_model",
        MODEL_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _item(
    workplane: cq.Workplane,
    color: tuple[float, float, float],
    opacity: float,
):
    return (workplane.val(), color, opacity)


def closed_items(model) -> list[tuple[cq.Shape, tuple, float]]:
    params = model.load_params()
    items = [
        _item(model.create_pressure_body(params), (0.65, 0.72, 0.78), 0.24),
        _item(model.create_service_door(params), (0.78, 0.82, 0.85), 0.45),
        _item(model.create_amplifier_reference(params), (0.18, 0.20, 0.23), 1.0),
        _item(
            model.create_amplifier_boundary_gasket(params),
            (0.05, 0.45, 0.28),
            0.85,
        ),
        _item(
            model.create_amplifier_clamp_frames(params),
            (0.18, 0.45, 0.70),
            0.85,
        ),
        _item(
            model.create_din_carrier_and_rails(params),
            (0.92, 0.55, 0.12),
            0.8,
        ),
        _item(
            model.create_din_reserve_envelopes(params),
            (0.12, 0.55, 0.92),
            0.14,
        ),
        _item(model.create_rain_hood(params), (0.84, 0.86, 0.88), 0.20),
        _item(model.create_sun_shield(params), (0.92, 0.94, 0.95), 0.42),
    ]
    return items


def service_items(model) -> list[tuple[cq.Shape, tuple, float]]:
    params = model.load_params()
    items = [
        _item(model.create_pressure_body(params), (0.65, 0.72, 0.78), 0.18),
        _item(model.create_amplifier_reference(params), (0.18, 0.20, 0.23), 1.0),
        _item(
            model.create_amplifier_boundary_gasket(params),
            (0.05, 0.45, 0.28),
            0.9,
        ),
        _item(
            model.create_amplifier_clamp_frames(params),
            (0.18, 0.45, 0.70),
            0.9,
        ),
        _item(
            model.create_service_gasket(params).translate((0.0, 260.0, 0.0)),
            (0.05, 0.30, 0.18),
            0.9,
        ),
        _item(
            model.create_service_door(params).translate((0.0, 260.0, 0.0)),
            (0.78, 0.82, 0.85),
            0.75,
        ),
        _item(
            model.create_din_carrier_and_rails(params).translate((0.0, 145.0, 0.0)),
            (0.92, 0.55, 0.12),
            0.9,
        ),
        _item(
            model.create_din_reserve_envelopes(params).translate((0.0, 145.0, 0.0)),
            (0.12, 0.55, 0.92),
            0.18,
        ),
    ]

    explode = {
        "wet_back_wall": (0.0, -110.0, 0.0),
        "wet_roof": (0.0, 0.0, 90.0),
        "inlet_turning_wall": (-90.0, 0.0, 0.0),
        "exhaust_turning_wall": (90.0, 0.0, 0.0),
        "central_splash_floor": (0.0, 0.0, -70.0),
    }
    for name, part in model.rain_hood_components(params).items():
        items.append(
            _item(
                part.translate(explode[name]),
                (0.84, 0.86, 0.88),
                0.35,
            )
        )
    items.append(
        _item(
            model.create_sun_shield(params).translate((0.0, 0.0, 140.0)),
            (0.92, 0.94, 0.95),
            0.5,
        )
    )
    airflow_colors = {
        "ambient_inlet_keepout": (0.10, 0.45, 0.95),
        "ambient_exhaust_keepout": (0.95, 0.25, 0.10),
    }
    for name, part in model.airflow_reference_components(params).items():
        items.append(_item(part, airflow_colors[name], 0.2))
    return items


def main() -> None:
    model = _load_model()
    render_scene(
        closed_items(model),
        OUT_DIR,
        "am59_ip66_passive_v4_transparent",
        views=("iso", "front", "back", "right", "top"),
        size=1600,
    )
    render_scene(
        service_items(model),
        OUT_DIR,
        "am59_ip66_passive_v4_service_exploded",
        views=("iso", "front", "back", "right", "top"),
        size=1800,
    )
    print(OUT_DIR)


if __name__ == "__main__":
    main()
