"""
Example Mounting Plate
======================
A parametric mounting plate demonstrating the project workflow:
  1. Dimensions are loaded from params.json (populated from datasheets)
  2. Model is built with CadQuery using selectors (not hardcoded positions)
  3. Exports to the project-level exports/ directory as STEP
  4. Optionally displays in OCP CAD Viewer for live preview in VS Code

Units: mm (all dimensions)
"""

import json
import sys
from pathlib import Path

import cadquery as cq

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"


def load_params(path: Path = PARAMS_FILE) -> dict:
    """Load the part parameters from its JSON engineering brief."""
    with open(path) as f:
        return json.load(f)


def create_part(params: dict | None = None) -> cq.Workplane:
    """
    Build the mounting plate from parameters.

    Parameters
    ----------
    params : dict, optional
        Override the default params.json. Useful for tests and batch generation.

    Returns
    -------
    cq.Workplane
        The finished solid.
    """
    if params is None:
        params = load_params()

    # --- Unpack dimensions ---------------------------------------------------
    dims = params["dimensions"]
    length = dims["length"]
    width = dims["width"]
    thickness = dims["thickness"]

    corners = params["features"]["corner_holes"]
    hole_d = corners["hole_diameter"]
    cb_d = corners["counterbore_diameter"]
    cb_depth = corners["counterbore_depth"]
    inset_x = corners["inset_x"]
    inset_y = corners["inset_y"]

    center = params["features"]["center_bore"]
    center_d = center["diameter"]

    fillets = params["features"]["edge_fillets"]
    fillet_r = fillets["radius"]

    # --- Build the model -----------------------------------------------------
    # Start with a rectangular plate
    result = cq.Workplane("XY").box(length, width, thickness)

    # Add the four corner counterbore holes
    # Use a construction rectangle inset from the edges to locate them
    hole_pattern_x = length - 2 * inset_x
    hole_pattern_y = width - 2 * inset_y

    result = (
        result
        .faces(">Z")
        .workplane()
        .rect(hole_pattern_x, hole_pattern_y, forConstruction=True)
        .vertices()
        .cboreHole(hole_d, cb_d, cb_depth)
    )

    # Add the central through-hole
    result = (
        result
        .faces(">Z")
        .workplane()
        .hole(center_d)
    )

    # Fillet all vertical edges (edges parallel to Z)
    result = result.edges("|Z").fillet(fillet_r)

    return result


def build_stages(params: dict | None = None):
    """
    The same build as create_part(), yielded one feature operation at a time
    for `lib.debug_build` bisection: when a stage throws, the tool reports the
    last stage that succeeded instead of an opaque kernel error. Keep the
    final stage identical to create_part()'s result (drift is warned about).
    """
    if params is None:
        params = load_params()
    dims = params["dimensions"]
    corners = params["features"]["corner_holes"]
    center = params["features"]["center_bore"]
    fillets = params["features"]["edge_fillets"]

    result = cq.Workplane("XY").box(dims["length"], dims["width"], dims["thickness"])
    yield "stock_plate", result

    result = (
        result.faces(">Z")
        .workplane()
        .rect(dims["length"] - 2 * corners["inset_x"],
              dims["width"] - 2 * corners["inset_y"], forConstruction=True)
        .vertices()
        .cboreHole(corners["hole_diameter"], corners["counterbore_diameter"],
                   corners["counterbore_depth"])
    )
    yield "corner_counterbores", result

    result = result.faces(">Z").workplane().hole(center["diameter"])
    yield "center_bore", result

    result = result.edges("|Z").fillet(fillets["radius"])
    yield "edge_fillets", result


def export_part(
    result: cq.Workplane,
    name: str = "example_part",
    version: str = "v1",
    formats: list[str] | None = None,
) -> list[Path]:
    """
    Export the part to the part's exports/ directory with version in filename.

    Parameters
    ----------
    result : cq.Workplane
        The built CadQuery solid.
    name : str
        Base filename (without version or extension).
    version : str
        Version string from params.json (e.g. "v1", "v2").
    formats : list[str], optional
        File extensions to export. Defaults to ["step"].

    Returns
    -------
    list[Path]
        Paths to the exported files.
    """
    if formats is None:
        formats = ["step"]

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    exported = []

    for fmt in formats:
        out_path = EXPORTS_DIR / f"{name}_{version}.{fmt}"
        cq.exporters.export(result, str(out_path))
        print(f"  ✓ Exported {out_path.relative_to(PROJECT_ROOT)}")
        exported.append(out_path)

    return exported


# ---------------------------------------------------------------------------
# Entry point — run directly to export and/or preview
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    params = load_params()
    part = create_part(params)

    # Export STEP (primary) and optionally STL
    export_formats = ["step"]
    if "--stl" in sys.argv:
        export_formats.append("stl")

    print(f"\n  Building: {params['part_name']} ({params.get('version', 'v1')})")
    print(f"  Material: {params.get('material', 'N/A')}")
    print(f"  Envelope: {params['dimensions']['length']} × "
          f"{params['dimensions']['width']} × "
          f"{params['dimensions']['thickness']} mm\n")

    version = params.get("version", "v1")
    export_part(part, name="example_part", version=version, formats=export_formats)

    # Show in OCP CAD Viewer if available (VS Code extension)
    try:
        from ocp_vscode import show

        show(part)
        print("\n  📐 Model displayed in OCP CAD Viewer")
    except ImportError:
        print("\n  ℹ  Install ocp-vscode to preview in VS Code: pip install ocp-vscode")
