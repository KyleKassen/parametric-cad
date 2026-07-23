"""
Headless verification renders for STEP files / CadQuery shapes (offscreen VTK).

The visual-inspection layer of the part pipeline (lib/analyze_step.py is the
measurement layer). Generates the six orthographic views (top, bottom, front,
back, left, right) plus an isometric view as PNGs. Projection is orthographic,
so each view is a true silhouette projection — no perspective distortion, and
what you see lines up with the analysis numbers.

An RGB axis triad (X=red, Y=green, Z=blue) is drawn beside the model so
orientation and handedness are unambiguous across views — mirrored vendor
variants (e.g. the OZ510 TX vs RX) are caught by looking, not assumed away.

Section cuts: --section AXIS:STATION (e.g. --section "Z:11" or "X:-20")
removes all material on the positive side of that plane before rendering, so
interior features — bosses, corridors, lid lips — become visible. Cut renders
are suffixed _secZ11 etc. so they never overwrite whole-part views.

Usage:
    uv run python -m lib.render_step FILE.step [MORE.step ...]
        [-o OUTDIR] [--views iso,front,top] [--size 1100] [--no-axes]
        [--section Z:11]

Default output: parts/<part>/references/views/ when the file lives under
parts/, else ./renders/. Units: mm.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cadquery as cq
import vtk

# view name -> (camera direction from origin, view-up)
VIEWS: dict[str, tuple[tuple, tuple]] = {
    "top":    ((0, 0, 1), (0, 1, 0)),
    "bottom": ((0, 0, -1), (0, 1, 0)),
    "front":  ((0, -1, 0), (0, 0, 1)),
    "back":   ((0, 1, 0), (0, 0, 1)),
    "left":   ((-1, 0, 0), (0, 0, 1)),
    "right":  ((1, 0, 0), (0, 0, 1)),
    "iso":    ((1, -1, 0.8), (0, 0, 1)),
}
DEFAULT_VIEWS = tuple(VIEWS)

GRAY = (0.62, 0.66, 0.72)


def _add_shape(renderer, shape: cq.Shape, rgb: tuple, opacity: float) -> None:
    """Add one tessellated shape (with feature-edge overlay) to the scene."""
    poly = shape.toVtkPolyData(1e-3, 0.2)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(poly)
    mapper.ScalarVisibilityOff()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*rgb)
    actor.GetProperty().SetOpacity(opacity)
    actor.GetProperty().SetInterpolationToPhong()
    renderer.AddActor(actor)

    edges = vtk.vtkFeatureEdges()
    edges.SetInputData(poly)
    edges.BoundaryEdgesOn()
    edges.FeatureEdgesOn()
    edges.SetFeatureAngle(30)
    edges.ManifoldEdgesOff()
    edges.NonManifoldEdgesOff()
    emap = vtk.vtkPolyDataMapper()
    emap.SetInputConnection(edges.GetOutputPort())
    emap.ScalarVisibilityOff()
    eactor = vtk.vtkActor()
    eactor.SetMapper(emap)
    eactor.GetProperty().SetColor(0.05, 0.05, 0.05)
    eactor.GetProperty().SetOpacity(min(1.0, opacity + 0.2))
    eactor.GetProperty().SetLineWidth(1.2)
    renderer.AddActor(eactor)


def _add_axes(renderer) -> None:
    """RGB axis triad at the scene's min corner (X=red, Y=green, Z=blue)."""
    b = renderer.ComputeVisiblePropBounds()  # xmin,xmax,ymin,ymax,zmin,zmax
    ext = max(b[1] - b[0], b[3] - b[2], b[5] - b[4])
    length = 0.22 * ext
    axes = vtk.vtkAxesActor()
    axes.SetTotalLength(length, length, length)
    for prop in (axes.GetXAxisShaftProperty(), axes.GetYAxisShaftProperty(),
                 axes.GetZAxisShaftProperty()):
        prop.SetLineWidth(3)
    tf = vtk.vtkTransform()
    tf.Translate(b[0] - 0.18 * ext, b[2] - 0.18 * ext, b[4] - 0.18 * ext)
    axes.SetUserTransform(tf)
    renderer.AddActor(axes)


def render_scene(
    items: list[tuple[cq.Shape, tuple, float]],
    out_dir: str | Path,
    prefix: str,
    views: tuple[str, ...] = DEFAULT_VIEWS,
    size: int = 1100,
    axes: bool = True,
) -> list[Path]:
    """
    Render shapes to PNGs, one file per view: <out_dir>/<prefix>_<view>.png.

    items : list of (shape, (r, g, b), opacity) — opacity < 1 draws a shape
        see-through, e.g. a housing revealing the modules inside it.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(1, 1, 1)
    for shape, rgb, opacity in items:
        _add_shape(renderer, shape, rgb, opacity)
    if axes:
        _add_axes(renderer)

    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.AddRenderer(renderer)
    window.SetSize(size, size)

    written = []
    cam = renderer.GetActiveCamera()
    cam.ParallelProjectionOn()
    for view in views:
        direction, up = VIEWS[view]
        cam.SetFocalPoint(0, 0, 0)
        cam.SetPosition(*direction)
        cam.SetViewUp(*up)
        renderer.ResetCamera()
        window.Render()
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(window)
        w2i.Update()
        writer = vtk.vtkPNGWriter()
        out = out_dir / f"{prefix}_{view}.png"
        writer.SetFileName(str(out))
        writer.SetInputConnection(w2i.GetOutputPort())
        writer.Write()
        written.append(out)
    return written


def section_cut(shape: cq.Shape, axis: str = "Z", station: float = 0.0,
                margin: float = 5.0) -> cq.Shape:
    """
    Remove all material on the positive side of the plane axis=station, so a
    render looks INTO the part. Raises if the cut produces nothing — a cut
    plane outside the part is an authoring error, not an empty picture.
    """
    if axis not in ("X", "Y", "Z"):
        raise ValueError(f"section axis must be X|Y|Z, got {axis!r}")
    bb = shape.BoundingBox()
    lo = [bb.xmin - margin, bb.ymin - margin, bb.zmin - margin]
    hi = [bb.xmax + margin, bb.ymax + margin, bb.zmax + margin]
    i = "XYZ".index(axis)
    lo[i] = station
    if not lo[i] < hi[i]:
        raise ValueError(f"section {axis}:{station} is beyond the part "
                         f"(bbox {axis} max {hi[i] - margin:.2f})")
    cutter = cq.Solid.makeBox(
        hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], cq.Vector(*lo))
    result = shape.cut(cutter)
    # NB: volume, not Solids() — cutting a Compound can yield a result whose
    # solid enumeration is empty even though real material remains.
    if abs(result.Volume()) < 1e-9:
        lo_bound = (bb.xmin, bb.ymin, bb.zmin)[i]
        raise ValueError(f"section {axis}:{station} removed the entire part "
                         f"(bbox {axis} min {lo_bound:.2f})")
    return result


def render_file(
    step_path: str | Path,
    out_dir: str | Path | None = None,
    views: tuple[str, ...] = DEFAULT_VIEWS,
    size: int = 1100,
    axes: bool = True,
    section: tuple[str, float] | None = None,
) -> list[Path]:
    """
    Render one STEP file to per-view PNGs. Returns the written paths.
    section=("Z", 11.0) cuts away material above z=11 before rendering.
    """
    step_path = Path(step_path)
    if out_dir is None:
        if "parts" in [p.lower() for p in step_path.parts]:
            out_dir = step_path.parent / "references" / "views"
        else:
            out_dir = Path("renders")
    shape = cq.importers.importStep(str(step_path)).val()
    prefix = step_path.stem.replace(" ", "_")
    if section is not None:
        axis, station = section
        shape = section_cut(shape, axis, station)
        prefix += f"_sec{axis}{station:g}".replace(".", "p").replace("-", "m")
    return render_scene([(shape, GRAY, 1.0)], out_dir, prefix,
                        views=views, size=size, axes=axes)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("files", nargs="+", help="STEP file(s) to render")
    ap.add_argument("-o", "--out", help="output directory (default: references/views/)")
    ap.add_argument("--views", default=",".join(DEFAULT_VIEWS),
                    help=f"comma-separated subset of: {', '.join(VIEWS)}")
    ap.add_argument("--size", type=int, default=1100, help="image size in px")
    ap.add_argument("--no-axes", action="store_true", help="omit the axis triad")
    ap.add_argument("--section", metavar="AXIS:STATION",
                    help='cut away material on the + side of a plane, e.g. "Z:11"')
    args = ap.parse_args(argv)

    views = tuple(v.strip() for v in args.views.split(",") if v.strip())
    unknown = [v for v in views if v not in VIEWS]
    if unknown:
        ap.error(f"unknown view(s): {', '.join(unknown)}")

    section = None
    if args.section:
        try:
            axis, station = args.section.split(":", 1)
            section = (axis.strip().upper(), float(station))
        except ValueError:
            ap.error(f'--section wants AXIS:STATION (e.g. "Z:11"), got {args.section!r}')

    for f in args.files:
        for path in render_file(f, args.out, views=views, size=args.size,
                                axes=not args.no_axes, section=section):
            print(f"  ok {path}")


if __name__ == "__main__":
    main()
