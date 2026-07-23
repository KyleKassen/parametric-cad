"""
Bulk export utility — discovers all parts and assemblies, builds and exports them.

Usage:
    python -m lib.export              # Export all parts as STEP
    python -m lib.export --stl        # Also export STL
    python -m lib.export --part NAME  # Export only a specific part
"""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PARTS_DIR = PROJECT_ROOT / "parts"


def discover_parts() -> list[Path]:
    """
    Find all parts that have a model.py with a create_part() function.

    Layout: parts/custom/* are parts we design and fabricate; parts/vendor/*
    are purchased parts (vendor STEPs, or datasheet-derived stand-in models).
    parts/_template/ is the new-part scaffold and is deliberately excluded.
    """
    parts = []
    for group in ("custom", "vendor"):
        parts.extend(sorted((PARTS_DIR / group).glob("*/model.py")))
    return parts


def load_part_module(model_path: Path):
    """Dynamically import a part's model.py and return the module."""
    part_name = model_path.parent.name
    spec = importlib.util.spec_from_file_location(f"parts.{part_name}.model", model_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_all(formats: list[str] | None = None, part_filter: str | None = None) -> int:
    """
    Discover all parts, build them, and export to parts/<name>/exports/.

    Returns an exit code: 0 only if at least one part was exported and none
    failed. Any build/export error, a part producing no solids, or zero parts
    exported is a failure — errors are reported, never silently absorbed.
    Files are written via a temp name + atomic replace so a failed export can
    never leave a corrupt file where an accepted artifact used to be.

    Parameters
    ----------
    formats : list[str], optional
        File extensions to export. Defaults to ["step"].
    part_filter : str, optional
        If set, only export the part whose directory name matches.
    """
    import os

    import cadquery as cq

    if formats is None:
        formats = ["step"]

    parts = discover_parts()
    if not parts:
        print("No parts found in parts/*/model.py")
        return 1

    print(f"\n{'='*60}")
    print("  CadQuery Bulk Export")
    print(f"  Formats: {', '.join(f.upper() for f in formats)}")
    print(f"{'='*60}\n")

    exported_count = 0
    failures: list[str] = []
    for model_path in parts:
        part_name = model_path.parent.name

        if part_filter and part_name != part_filter:
            continue

        print(f"  ▸ {part_name}")

        try:
            module = load_part_module(model_path)

            if not hasattr(module, "create_part"):
                print("    ⚠ No create_part() function found, skipping")
                continue

            # Read version from params.json
            import json
            params_path = model_path.parent / "params.json"
            version = "v1"
            if params_path.exists():
                with open(params_path) as pf:
                    params_data = json.load(pf)
                    version = params_data.get("version", "v1")

            print(f"    version: {version}")

            result = module.create_part()

            if hasattr(result, "solids") and result.solids().size() == 0:
                raise RuntimeError("create_part() produced no solids")

            part_exports = model_path.parent / "exports"
            part_exports.mkdir(parents=True, exist_ok=True)

            for fmt in formats:
                out_path = part_exports / f"{part_name}_{version}.{fmt}"
                tmp_path = part_exports / f"{part_name}_{version}.{fmt}.tmp"
                cq.exporters.export(result, str(tmp_path))
                os.replace(tmp_path, out_path)
                print(f"    ✓ {out_path.relative_to(PROJECT_ROOT)}")

            exported_count += 1

        except Exception as e:
            print(f"    ✗ Error: {e}")
            failures.append(part_name)

    print(f"\n  Done — {exported_count} part(s) exported"
          + (f", {len(failures)} FAILED: {', '.join(failures)}" if failures else "")
          + ".\n")

    if failures:
        return 1
    if exported_count == 0:
        print("  ✗ Nothing exported"
              + (f" (no part matched {part_filter!r})" if part_filter else "")
              + " — that is a failure, not a success.\n")
        return 1
    return 0


if __name__ == "__main__":
    formats = ["step"]
    part_filter = None

    if "--stl" in sys.argv:
        formats.append("stl")
    if "--part" in sys.argv:
        idx = sys.argv.index("--part")
        if idx + 1 < len(sys.argv):
            part_filter = sys.argv[idx + 1]

    sys.exit(export_all(formats=formats, part_filter=part_filter))
