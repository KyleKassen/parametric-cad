"""Command-line geometry and thermal sanity check for the V3 TEC enclosure."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "am59_sealed_tec_enclosure_model",
    PART_DIR / "model.py",
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def _bbox_text(workplane) -> str:
    bb = workplane.val().BoundingBox()
    return (
        f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm; "
        f"min=({bb.xmin:.2f}, {bb.ymin:.2f}, {bb.zmin:.2f}), "
        f"max=({bb.xmax:.2f}, {bb.ymax:.2f}, {bb.zmax:.2f})"
    )


def main() -> int:
    pressure_body = model.create_pressure_body()
    amplifier = model.create_amplifier_reference()
    coolers = model.create_seifert_cooler_bank()
    baffles = model.create_internal_air_management()
    caps = model.create_immersion_caps()
    cap_gaskets = model.create_immersion_cap_gaskets()
    cartridge = model.create_internal_cartridge()
    supports = model.create_cartridge_support_structure()
    retainers = model.create_cartridge_retainers()
    controller = model.create_controller_reference()
    assessment = model.thermal_assessment()
    mass = model.mass_assessment()
    params = model.load_params()

    print(f"pressure body: {_bbox_text(pressure_body)}")
    print(f"AM59:         {_bbox_text(amplifier)}")
    print(f"cooler bank:  {_bbox_text(coolers)}")
    print(f"caps:         {_bbox_text(caps)}")
    print(
        "AM59/cooler clearance: "
        f"{clearance(amplifier, coolers):.2f} mm; "
        f"interference {interference(amplifier, coolers):.3f} mm3"
    )
    print(
        "AM59/baffle clearance: "
        f"{clearance(amplifier, baffles):.2f} mm; "
        f"interference {interference(amplifier, baffles):.3f} mm3"
    )
    print(
        "cap/body clearance: "
        f"{clearance(caps, pressure_body):.2f} mm; "
        f"interference {interference(caps, pressure_body):.3f} mm3"
    )
    print(
        "AM59/support clearance: "
        f"{clearance(amplifier, supports):.2f} mm; "
        f"interference {interference(amplifier, supports):.3f} mm3"
    )
    print(
        "single cap mass: "
        f"{mass['single_immersion_cap_mass_kg_approx']:.2f} kg; "
        "known operating/immersion masses: "
        f"{mass['operating_known_mass_excluding_am59_gaskets_fasteners_wiring_kg']:.1f}/"
        f"{mass['immersion_known_mass_excluding_am59_gaskets_fasteners_wiring_kg']:.1f} kg"
    )
    for name, result in assessment["modes"].items():
        print(
            f"{name}: capacity={result['capacity_w']:.1f} W, "
            f"required={result['required_w']:.1f} W, "
            f"margin={result['margin_w']:.1f} W, "
            f"passes={result['passes']}"
        )

    failures: list[str] = []
    if interference(amplifier, coolers) > 0.5:
        failures.append("AM59 intersects a Seifert cooler")
    if clearance(amplifier, coolers) < 35.0:
        failures.append("AM59-to-cooler clearance is below 35 mm")
    if interference(amplifier, baffles) > 0.5:
        failures.append("AM59 intersects an airflow baffle")
    if interference(caps, pressure_body) > 0.5:
        failures.append("An immersion cap intersects the pressure body")
    if not 0.75 <= clearance(caps, pressure_body) <= 0.85:
        failures.append("Immersion cap seating gap is not 0.8 +/- 0.05 mm")
    if interference(amplifier, supports) > 0.5:
        failures.append("AM59 intersects the welded cartridge supports")
    if clearance(amplifier, supports) < 5.0:
        failures.append("AM59-to-cartridge-support clearance is below 5 mm")
    if interference(cartridge, supports) > 0.5:
        failures.append("Cartridge penetrates its support rails/stops")
    if clearance(cartridge, supports) > 0.05:
        failures.append("Cartridge does not contact its support rails/stops")
    if interference(cartridge, retainers) > 0.5:
        failures.append("Cartridge penetrates its removable retainers")
    if clearance(cartridge, retainers) > 0.05:
        failures.append("Cartridge retainers do not contact the tray")
    if interference(controller, baffles) > 0.5:
        failures.append("Controller envelope intersects an airflow baffle")
    if clearance(controller, baffles) < 3.0:
        failures.append("Controller-to-baffle clearance is below 3 mm")
    if clearance(cap_gaskets, pressure_body) > 0.05:
        failures.append("Immersion-cap gaskets do not contact the coamings")
    if clearance(cap_gaskets, caps) > 0.05:
        failures.append("Immersion-cap gaskets do not contact the cap flanges")

    lid = params["service_lid"]
    enclosure = params["sealed_enclosure"]
    gasket_inner_y = lid["seal_ring_outer_width_y"] - 2 * lid["seal_ring_width"]
    gasket_inner_z = lid["seal_ring_outer_height_z"] - 2 * lid["seal_ring_width"]
    opening_z_min = enclosure["flange_opening_center_z"] - enclosure["flange_opening_height_z"] / 2
    opening_z_max = enclosure["flange_opening_center_z"] + enclosure["flange_opening_height_z"] / 2
    gasket_z_min = lid["seal_ring_center_z"] - gasket_inner_z / 2
    gasket_z_max = lid["seal_ring_center_z"] + gasket_inner_z / 2
    if gasket_inner_y - enclosure["flange_opening_width_y"] < 10.0:
        failures.append("Service gasket has under 5 mm Y support per edge")
    if (
        min(
            opening_z_min - gasket_z_min,
            gasket_z_max - opening_z_max,
        )
        < 5.0
    ):
        failures.append("Service gasket has under 5 mm Z support")
    lid_fastener_radius = lid["fastener_diameter"] / 2
    service_fastener_web = min(
        lid["outer_width_y"] / 2 - lid["fastener_edge_y"] - lid_fastener_radius,
        lid["fastener_edge_y"] - lid_fastener_radius - lid["seal_ring_outer_width_y"] / 2,
        lid["fastener_edge_z_bottom"]
        - (lid["seal_ring_center_z"] - lid["outer_height_z"] / 2)
        - lid_fastener_radius,
        lid["seal_ring_center_z"]
        - lid["seal_ring_outer_height_z"] / 2
        - lid["fastener_edge_z_bottom"]
        - lid_fastener_radius,
    )
    if service_fastener_web < 5.0:
        failures.append("Service-lid fasteners have under 5 mm seal/edge web")

    cap_params = params["immersion_caps"]
    cap_volumes = [
        sum(abs(solid.Volume()) for solid in cap.solids().vals())
        for cap in model.immersion_cap_components(params).values()
    ]
    if any(volume > 1.1e6 for volume in cap_volumes):
        failures.append("An immersion cap exceeds the 1.1 L material-volume limit")
    if mass["single_immersion_cap_mass_kg_approx"] > 3.0:
        failures.append("A modeled aluminum immersion cap exceeds 3.0 kg")
    if len(model.immersion_cap_fastener_locations(params)) != 64:
        failures.append("Immersion-cap fastener pattern is not 32 per cap")
    fastener_radius = cap_params["fastener_hole_diameter"] / 2
    cap_edge_web = min(
        cap_params["coaming_outer_width_x"] / 2
        - cap_params["fastener_edge_abs_x"]
        - fastener_radius,
        cap_params["coaming_outer_height_z"] / 2
        - cap_params["fastener_edge_abs_z"]
        - fastener_radius,
    )
    gasket_web = min(
        cap_params["fastener_edge_abs_x"]
        - fastener_radius
        - cap_params["gasket_outer_width_x"] / 2,
        cap_params["fastener_edge_abs_z"]
        - fastener_radius
        - cap_params["gasket_outer_height_z"] / 2,
    )
    if min(cap_edge_web, gasket_web) < 5.0:
        failures.append("Cap fastener holes have under 5 mm seal/edge web")
    if not assessment["modes"]["four_healthy_300w"]["passes"]:
        failures.append("Four coolers do not meet the 300 W + 15% basis")
    if not assessment["modes"]["three_healthy_200w"]["passes"]:
        failures.append("Three coolers do not meet the 200 W + 15% basis")
    if not assessment["modes"]["two_healthy_125w"]["passes"]:
        failures.append("Two coolers do not meet the 125 W + 15% basis")
    if assessment["modes"]["one_healthy_125w"]["passes"]:
        failures.append("One cooler unexpectedly passes the 125 W basis")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
