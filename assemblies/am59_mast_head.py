"""Build/export the AM59 centered bridge mast-head context assembly."""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_mast_head" / "model.py"

spec = importlib.util.spec_from_file_location("am59_mast_head_model", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def create_assembly(open_service_panels: bool = False):
    return model.create_assembly(open_service_panels=open_service_panels)


if __name__ == "__main__":
    output_dir = MODEL_PATH.parent / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_open" if "--open" in sys.argv else ""
    output_path = output_dir / f"am59_mast_head_v1_context{suffix}.step"
    create_assembly(open_service_panels="--open" in sys.argv).save(str(output_path))
    print(output_path)
