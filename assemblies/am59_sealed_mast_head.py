"""Build/export the AM59 sealed mast-head V2 context assembly."""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_sealed_mast_head" / "model.py"

spec = importlib.util.spec_from_file_location(
    "am59_sealed_mast_head_model",
    MODEL_PATH,
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def create_assembly(service_open: bool = False, thermal_exploded: bool = False):
    return model.create_assembly(
        service_open=service_open,
        thermal_exploded=thermal_exploded,
    )


if __name__ == "__main__":
    output_dir = MODEL_PATH.parent / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if "--open" in sys.argv:
        suffix += "_service_open"
    if "--exploded" in sys.argv:
        suffix += "_thermal_exploded"
    output_path = output_dir / f"am59_sealed_mast_head_v2_context{suffix}.step"
    create_assembly(
        service_open="--open" in sys.argv,
        thermal_exploded="--exploded" in sys.argv,
    ).save(str(output_path))
    print(output_path)
