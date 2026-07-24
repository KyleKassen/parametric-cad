"""Build/export the AM59 IP66 low-CG passive enclosure assembly."""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_ip66_passive_enclosure" / "model.py"

spec = importlib.util.spec_from_file_location(
    "am59_ip66_passive_enclosure_model",
    MODEL_PATH,
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def create_assembly(
    service_open: bool = False,
    show_airflow: bool = False,
    show_din_reserves: bool = True,
    weather_exploded: bool = False,
):
    return model.create_assembly(
        service_open=service_open,
        show_airflow=show_airflow,
        show_din_reserves=show_din_reserves,
        weather_exploded=weather_exploded,
    )


if __name__ == "__main__":
    output_dir = MODEL_PATH.parent / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if "--open" in sys.argv:
        suffix += "_service_open"
    if "--airflow" in sys.argv:
        suffix += "_airflow"
    if "--no-reserves" in sys.argv:
        suffix += "_no_reserves"
    if "--exploded" in sys.argv:
        suffix += "_exploded"
    output_path = output_dir / f"am59_ip66_passive_enclosure_v4_context{suffix}.step"
    create_assembly(
        service_open="--open" in sys.argv,
        show_airflow="--airflow" in sys.argv,
        show_din_reserves="--no-reserves" not in sys.argv,
        weather_exploded="--exploded" in sys.argv,
    ).save(str(output_path))
    print(output_path)
