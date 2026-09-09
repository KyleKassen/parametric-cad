"""Stage portable FPD scripts; execute them in Front Panel Designer to create .fpd.

Only Python's standard library is required. Existing targets are never replaced.
The adjacent *_inputs.json files supply geometry; their .fpjs templates retain
the verified native API calls. This helper does not launch Front Panel Designer.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys


SOURCE_DIR = Path(__file__).resolve().parent
GROUPS = (
    ("SCE20_BACKPANEL_R1", ("Backpanel_R1",)),
    ("SCE20_ADAPTERS_FINAL_R3", ("B210_R2", "MeanWell_R2", "Bedrock_R3")),
)
CALL = re.compile(r"^createPanel\((.+)\);[ \t]*$", re.MULTILINE)


def prepare(output_dir: Path) -> list[tuple[Path, bytes]]:
    """Validate all sources/targets before returning any bytes for writing."""
    if output_dir == SOURCE_DIR:
        raise ValueError("Choose a separate staging folder, not this delivery folder.")

    plans: list[tuple[Path, bytes]] = []
    native_targets: list[Path] = []
    for stem, expected_names in GROUPS:
        input_path = SOURCE_DIR / f"{stem}_inputs.json"
        script_path = SOURCE_DIR / f"{stem}.fpjs"
        specs = json.loads(input_path.read_text(encoding="utf-8-sig"))
        if not isinstance(specs, list) or tuple(spec.get("name") for spec in specs) != expected_names:
            raise ValueError(f"Unexpected specification names/order in {input_path.name}.")
        staged_specs = copy.deepcopy(specs)
        for spec in staged_specs:
            name = spec["name"]
            native_target = output_dir / f"{name}.fpd"
            if len(str(native_target)) > 240:
                raise ValueError(f"Use a shorter output directory for Front Panel Designer: {native_target}")
            spec["save"] = native_target.as_posix()
            native_targets.append(native_target)

            if name == "MeanWell_R2":
                dxf_name = "MeanWell_R2_outline.dxf"
                plans.append((output_dir / dxf_name, (SOURCE_DIR / dxf_name).read_bytes()))
                spec["outline_dxf"] = (output_dir / dxf_name).as_posix()

        script = script_path.read_text(encoding="utf-8-sig")
        calls = list(CALL.finditer(script))
        if tuple(json.loads(call.group(1)).get("name") for call in calls) != expected_names:
            raise ValueError(f"Unexpected creation calls in {script_path.name}.")
        if "SaveFrontpanel(p,s.save,false);" not in script:
            raise ValueError(f"Expected overwrite-disabled native save in {script_path.name}.")
        creations = iter(
            "createPanel(" + json.dumps(spec, ensure_ascii=True, separators=(",", ":")) + ");"
            for spec in staged_specs
        )
        staged_script = CALL.sub(lambda _: next(creations), script)
        plans.append((output_dir / f"{stem}.fpjs", staged_script.encode("utf-8")))
        plans.append((output_dir / f"{stem}_inputs.json", (json.dumps(staged_specs, indent=2) + "\n").encode("utf-8")))

    manifest = {
        "purpose": "Scripts staged only; execute in Front Panel Designer to create native .fpd files.",
        "source_directory": str(SOURCE_DIR),
        "output_directory": str(output_dir),
        "native_targets": [str(path) for path in native_targets],
        "staged_files": [
            {"name": path.name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            for path, data in plans
        ],
    }
    plans.append((output_dir / "staging_manifest.json", (json.dumps(manifest, indent=2) + "\n").encode("utf-8")))
    all_targets = [path for path, _ in plans] + native_targets
    if len(set(all_targets)) != len(all_targets):
        raise ValueError("Duplicate staging targets.")
    conflicts = [str(path) for path in all_targets if path.exists()]
    if conflicts:
        raise FileExistsError("Existing targets are protected. Choose a new output directory:\n" + "\n".join(conflicts))
    return plans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output-dir", required=True, type=Path, help="Short staging folder, e.g. C:\\FPE_SCE20_R3")
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    try:
        plans = prepare(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for path, data in plans:
            # Exclusive creation also protects against targets appearing after preflight.
            with path.open("xb") as stream:
                stream.write(data)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Cannot stage FPD scripts: {exc}\n")
    print(f"Staged two scripts and inputs for four panels in {output_dir}")
    print("No native .fpd files were created or changed.")
    print("In Front Panel Designer: Edit > Scripts > Add; select and execute each staged .fpjs.")
    print("Require PASS SAVED+RELOADED, inspect native features and 2D/3D views, then export and verify STEP.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
