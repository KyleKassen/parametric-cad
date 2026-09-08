"""Build/export the standalone AM59 four-Seifert sealed enclosure."""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_sealed_tec_enclosure" / "model.py"

spec = importlib.util.spec_from_file_location(
    "am59_sealed_tec_enclosure_model",
    MODEL_PATH,
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def create_assembly(
    service_open: bool = False,
    immersion_ready: bool = False,
    airflow_exploded: bool = False,
):
    return model.create_assembly(
        service_open=service_open,
        immersion_ready=immersion_ready,
        airflow_exploded=airflow_exploded,
    )


if __name__ == "__main__":
    output_dir = MODEL_PATH.parent / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if "--open" in sys.argv:
        suffix += "_service_open"
    if "--immersion" in sys.argv:
        suffix += "_immersion_ready"
    if "--airflow-exploded" in sys.argv:
        suffix += "_airflow_exploded"
    output_path = output_dir / f"am59_sealed_tec_enclosure_v3_context{suffix}.step"
    create_assembly(
        service_open="--open" in sys.argv,
        immersion_ready="--immersion" in sys.argv,
        airflow_exploded="--airflow-exploded" in sys.argv,
    ).save(str(output_path))
    print(output_path)
