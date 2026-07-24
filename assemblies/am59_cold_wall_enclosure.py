"""Build/export the AM59 cold-wall outdoor enclosure context assembly."""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_cold_wall_enclosure" / "model.py"

spec = importlib.util.spec_from_file_location(
    "am59_cold_wall_enclosure_model",
    MODEL_PATH,
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def create_assembly(service_open: bool = False, with_shield: bool = True):
    return model.create_assembly(
        service_open=service_open,
        with_shield=with_shield,
    )


if __name__ == "__main__":
    output_dir = MODEL_PATH.parent / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if "--open" in sys.argv:
        suffix += "_service_open"
    if "--no-shield" in sys.argv:
        suffix += "_no_shield"
    output_path = output_dir / f"am59_cold_wall_enclosure_v1_context{suffix}.step"
    create_assembly(
        service_open="--open" in sys.argv,
        with_shield="--no-shield" not in sys.argv,
    ).save(str(output_path))
    print(output_path)
