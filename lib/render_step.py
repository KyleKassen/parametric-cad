"""
Headless renders for STEP files / CadQuery shapes (offscreen VTK), in two modes.

VERIFICATION MODE (render_scene / render_file, unchanged)
    The visual-inspection layer of the part pipeline (lib/analyze_step.py is the
    measurement layer). Generates the six orthographic views (top, bottom,
    front, back, left, right) plus an isometric view as PNGs. Projection is
    orthographic, so each view is a true silhouette projection - no perspective
    distortion, and what you see lines up with the analysis numbers. An RGB axis
    triad (X=red, Y=green, Z=blue) is drawn beside the model so orientation and
    handedness are unambiguous across views - mirrored vendor variants (e.g. the
    OZ510 TX vs RX) are caught by looking, not assumed away.

PRODUCT MODE (render_product_scene / render_product_file)
    The verification path deliberately renders flat: it answers "is the geometry
    where I think it is". It cannot answer "is this refined", because flat
    headlight shading on white hides exactly the things refinement consists of -
    edge breaks, fillet continuity, recessed panels, contact shading. An agent
    looking at a verification render cannot tell a crude part from a good one,
    so it never self-corrects. Product mode exists to make refinement VISIBLE:
    PBR materials, a three-point studio rig, a procedural environment for image
    based lighting, screen-space ambient occlusion, a studio sweep backdrop,
    fine tessellation and a long-lens three-quarter camera.

    Read the output. A part that looks bad here looks bad in real life.

What is on, and what is deliberately off (all measured on this machine, VTK
9.3.1, macOS/OpenGL, offscreen - every claim below came from a rendered image,
not from documentation):
  ON   PBR + image based lighting from a procedurally generated cubemap; SSAO
       (contact shading); FXAA; 2x supersampling; per-vertex surface normals
       from OCC (CadQuery defaults these OFF, which is why every render this
       repo produced before now shaded off facet normals).
  OFF  vtkShadowMapPass. It does work - but only for a directional key, and it
       then lays a straight-edged dark band across the curved sweep that no
       resolution or light angle removes. Selectable via shading="shadows"
       for flat-floor scenes; not the default. See _build_pass_chain.
  OFF  tessellation crack fill. See _crack_fill_actor.
Note that SSAO and FXAA are silently ignored if a render pass is installed the
naive way, so the shadow modes chain them explicitly instead.

Section cuts: --section AXIS:STATION (e.g. --section "Z:11" or "X:-20")
removes all material on the positive side of that plane before rendering, so
interior features - bosses, corridors, lid lips - become visible. Cut renders
are suffixed _secZ11 etc. so they never overwrite whole-part views.

Usage:
    uv run python -m lib.render_step FILE.step [MORE.step ...]
        [-o OUTDIR] [--views iso,front,top] [--size 1100] [--no-axes]
        [--section Z:11]
    uv run python -m lib.render_step FILE.step --product
        [--views hero,hero_left] [--size 1600] [--material anodised]
        [--background dark|light] [--shading ssao|shadows|both|none]
        [--no-ground] [--supersample 2]

Default output is a references/ directory BESIDE THE FILE BEING RENDERED, never
the part directory: <step>/../references/views/ (verification) or
<step>/../references/product/ (product), whenever any component of the path is
named "parts", else ./renders/. Keeping the two modes in sibling directories is
why a hero render can never overwrite a verification view.

Rendering a source STEP at parts/vendor/<v>/<v>.STEP therefore lands in
parts/vendor/<v>/references/, while rendering a PROMOTED artifact at
parts/<group>/<part>/exports/<part>_v1.step lands in
parts/<group>/<part>/exports/references/ - which .gitignore covers, because that
whole tree is derived. Pass -o to write somewhere else. Units: mm.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq
import vtk

# view name -> (camera direction from origin, view-up)
VIEWS: dict[str, tuple[tuple, tuple]] = {
    "top": ((0, 0, 1), (0, 1, 0)),
    "bottom": ((0, 0, -1), (0, 1, 0)),
    "front": ((0, -1, 0), (0, 0, 1)),
    "back": ((0, 1, 0), (0, 0, 1)),
    "left": ((-1, 0, 0), (0, 0, 1)),
    "right": ((1, 0, 0), (0, 0, 1)),
    "iso": ((1, -1, 0.8), (0, 0, 1)),
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
    for prop in (
        axes.GetXAxisShaftProperty(),
        axes.GetYAxisShaftProperty(),
        axes.GetZAxisShaftProperty(),
    ):
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

    items : list of (shape, (r, g, b), opacity) - opacity < 1 draws a shape
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


def section_cut(
    shape: cq.Shape, axis: str = "Z", station: float = 0.0, margin: float = 5.0
) -> cq.Shape:
    """
    Remove all material on the positive side of the plane axis=station, so a
    render looks INTO the part. Raises if the cut produces nothing - a cut
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
        raise ValueError(
            f"section {axis}:{station} is beyond the part (bbox {axis} max {hi[i] - margin:.2f})"
        )
    cutter = cq.Solid.makeBox(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], cq.Vector(*lo))
    result = shape.cut(cutter)
    # NB: volume, not Solids() - cutting a Compound can yield a result whose
    # solid enumeration is empty even though real material remains.
    if abs(result.Volume()) < 1e-9:
        lo_bound = (bb.xmin, bb.ymin, bb.zmin)[i]
        raise ValueError(
            f"section {axis}:{station} removed the entire part (bbox {axis} min {lo_bound:.2f})"
        )
    return result


def render_file(
    step_path: str | Path,
    out_dir: str | Path | None = None,
    views: tuple[str, ...] | None = None,
    size: int | None = None,
    axes: bool = True,
    section: tuple[str, float] | None = None,
    quality: str = "verify",
    **product_kwargs,
) -> list[Path]:
    """
    Render one STEP file to per-view PNGs. Returns the written paths.
    section=("Z", 11.0) cuts away material above z=11 before rendering.

    quality="verify" (default) is the orthographic inspection render.
    quality="product" is the hero render - see render_product_scene() for the
    extra keyword arguments (material, background, shading, ground, ...).
    """
    step_path = Path(step_path)
    product = quality == "product"
    if quality not in ("verify", "product"):
        raise ValueError(f"quality must be 'verify' or 'product', got {quality!r}")
    if out_dir is None:
        if "parts" in [p.lower() for p in step_path.parts]:
            out_dir = step_path.parent / "references" / ("product" if product else "views")
        else:
            out_dir = Path("renders")
    shape = cq.importers.importStep(str(step_path)).val()
    prefix = step_path.stem.replace(" ", "_")
    if section is not None:
        axis, station = section
        shape = section_cut(shape, axis, station)
        prefix += f"_sec{axis}{station:g}".replace(".", "p").replace("-", "m")
    if product:
        material = product_kwargs.pop("material", "anodised")
        return render_product_scene(
            [(shape, material, 1.0)],
            out_dir,
            prefix,
            views=views or DEFAULT_PRODUCT_VIEWS,
            size=size or 1600,
            **product_kwargs,
        )
    if product_kwargs:
        raise TypeError(
            f"unexpected keyword(s) for quality='verify': {', '.join(sorted(product_kwargs))}"
        )
    return render_scene(
        [(shape, GRAY, 1.0)],
        out_dir,
        prefix,
        views=views or DEFAULT_VIEWS,
        size=size or 1100,
        axes=axes,
    )


# ---------------------------------------------------------------------------
# product mode
# ---------------------------------------------------------------------------

# Hero cameras. Three-quarter angles from slightly above, the way the reference
# product photographs are shot: high enough to read the top face and its panel
# work, low enough that the side elevation and its edge breaks stay legible.
PRODUCT_VIEWS: dict[str, tuple[tuple, tuple]] = {
    "hero": ((0.82, -1.00, 0.46), (0, 0, 1)),
    "hero_left": ((-0.82, -1.00, 0.46), (0, 0, 1)),
    "hero_rear": ((-0.78, 0.95, 0.42), (0, 0, 1)),
    "hero_high": ((0.60, -0.75, 1.05), (0, 0, 1)),
    "hero_low": ((0.90, -1.00, 0.16), (0, 0, 1)),
}
DEFAULT_PRODUCT_VIEWS = ("hero",)

# Tessellation. Verification uses (1e-3, 0.2 rad = 11.5 deg): a 6 mm fillet
# gets 8 facets over 90 deg and reads as a bevel, not a radius. Product uses
# 0.04 rad = 2.3 deg, which is ~39 facets over the same arc.
VERIFY_TESSELLATION = (1e-3, 0.2)
PRODUCT_TESSELLATION = (5e-3, 0.04)

# vtkShadowMapBakerPass exposes resolution and nothing else - no depth bias, no
# polygon offset - so resolution is the only lever against shadow acne.
SHADOW_MAP_RESOLUTION = 4096

# SSAO self-occlusion bias, as a fraction of the AO radius. Measured: at the
# 0.008 that reads as "a small bias" the AO rings a corner fillet with visible
# concentric scallops - a smooth radius rendered as if it were turned on a
# lathe, which is precisely the wrong signal to send about surface quality.
# 0.05 clears it; 0.08 leaves margin without flattening the contact shading.
SSAO_BIAS_FRACTION = 0.08


@dataclass(frozen=True)
class Material:
    """A PBR surface. base_color is linear-ish sRGB in 0-1, as VTK wants it."""

    base_color: tuple[float, float, float]
    metallic: float
    roughness: float
    opacity: float = 1.0


# One product reads as one product only if the palette is shared. Body values
# sit at 0.16-0.22 grey per the reference standard: matte dark anodised
# aluminium, low metallic (anodising is a dielectric film over metal), mid-high
# roughness. Contrast is carried by connectors and gaskets alone.
MATERIALS: dict[str, Material] = {
    "anodised": Material((0.185, 0.190, 0.200), 0.05, 0.42),
    "anodised_light": Material((0.360, 0.365, 0.375), 0.05, 0.46),
    "machined": Material((0.620, 0.635, 0.660), 0.90, 0.30),
    "cast": Material((0.300, 0.305, 0.315), 0.08, 0.72),
    "gasket": Material((0.045, 0.045, 0.048), 0.00, 0.88),
    "connector": Material((0.300, 0.310, 0.235), 0.65, 0.42),
    "fastener": Material((0.560, 0.575, 0.600), 0.95, 0.25),
    "glass": Material((0.070, 0.085, 0.100), 0.10, 0.08, 0.55),
    "reference": Material((0.480, 0.520, 0.580), 0.00, 0.60, 0.28),
}
DEFAULT_MATERIAL = "anodised"


@dataclass(frozen=True)
class Backdrop:
    """
    Studio environment. `bottom`/`top` are the gradient seen when ground=False;
    `sweep`/`sweep_top` are the cyclorama's floor and wall tones (reflectance,
    so they get lit); `sky`/`ground` build the environment cubemap.
    """

    bottom: tuple[float, float, float]
    top: tuple[float, float, float]
    sweep: tuple[float, float, float]
    sweep_top: tuple[float, float, float]
    sky: tuple[float, float, float]
    ground: tuple[float, float, float]
    exposure: float = 1.0


BACKDROPS: dict[str, Backdrop] = {
    "dark": Backdrop(
        bottom=(0.030, 0.032, 0.038),
        top=(0.085, 0.090, 0.102),
        sweep=(0.015, 0.016, 0.020),
        sweep_top=(0.004, 0.004, 0.006),
        sky=(0.55, 0.59, 0.68),
        ground=(0.05, 0.05, 0.056),
        exposure=1.0,
    ),
    "light": Backdrop(
        bottom=(0.700, 0.710, 0.725),
        top=(0.880, 0.885, 0.900),
        sweep=(0.720, 0.728, 0.742),
        sweep_top=(0.480, 0.490, 0.510),
        sky=(0.95, 0.96, 1.00),
        ground=(0.42, 0.43, 0.45),
        exposure=1.0,
    ),
}
DEFAULT_BACKDROP = "dark"


def _norm(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _resolve_view(name: str) -> tuple[tuple, tuple]:
    if name in PRODUCT_VIEWS:
        return PRODUCT_VIEWS[name]
    if name in VIEWS:
        return VIEWS[name]
    raise KeyError(f"unknown view {name!r}; known: {', '.join(list(PRODUCT_VIEWS) + list(VIEWS))}")


def _coerce_material(spec) -> Material:
    """Accept a Material, a MATERIALS key, or a plain (r,g,b) for convenience."""
    if isinstance(spec, Material):
        return spec
    if isinstance(spec, str):
        try:
            return MATERIALS[spec]
        except KeyError:
            raise KeyError(f"unknown material {spec!r}; known: {', '.join(MATERIALS)}") from None
    r, g, b = spec  # a verification-mode colour tuple, given a plausible finish
    return Material((r, g, b), 0.25, 0.55)


def _product_polydata(shape: cq.Shape) -> vtk.vtkPolyData:
    """
    Fine tessellation carrying OCC's own per-face point normals.

    normals=True is the whole game: CadQuery defaults it to False, so every
    render this repo has ever produced shaded off facet normals and every
    fillet looked like a chain of bevels. OCC evaluates the true surface normal
    per vertex, which is exact rather than averaged.

    Do NOT post-process this with vtkCleanPolyData + vtkPolyDataNormals to weld
    the per-face vertex duplicates. Measured here: the weld collapses 19478
    points to 4254 and vtkPolyDataNormals then declines to re-split them at any
    feature angle, so every chamfer, counterbore and panel step smears into a
    soft pillow. The duplicated boundary vertices are what keeps edges crisp.
    """
    linear, angular = PRODUCT_TESSELLATION
    return shape.toVtkPolyData(linear, angular, True)


def _crack_fill_actor(poly: vtk.vtkPolyData, mat: Material) -> vtk.vtkActor:
    """
    Draw every per-face mesh boundary as a hairline in the surface's own
    material, to fill OCC's tessellation cracks.

    OCC meshes each face separately and the two meshes meeting at a
    tangent-continuous boundary are not T-junction free, so the rasteriser
    leaks background through a sub-pixel dashed line down the middle of every
    fillet-to-flat transition - the exact place a refined part is trying to
    look seamless, and it survives finer tessellation, supersampling and FXAA.
    Overdrawing those boundary polylines with the same lit PBR material closes
    them. Line width 1 (in the supersampled buffer) is the working value: at 2
    the line starts darkening real silhouette edges.

    OFF BY DEFAULT, because it is a trade and not a win: a boundary line is
    shaded from one adjacent face's normals, so on a sharp concave rim - a
    counterbore mouth, a panel step - it lands on the wall of the feature at
    the wrong brightness and reads as stitching. Measured side by side, the
    stitching is more objectionable than the seam it removes, and the seam is
    barely visible against the dark backdrop at all. Turn it on for light
    backdrops on parts that are mostly large tangent blends.
    """
    edges = vtk.vtkFeatureEdges()
    edges.SetInputData(poly)
    edges.BoundaryEdgesOn()
    edges.FeatureEdgesOff()
    edges.ManifoldEdgesOff()
    edges.NonManifoldEdgesOff()
    edges.ColoringOff()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(edges.GetOutputPort())
    mapper.ScalarVisibilityOff()
    mapper.SetResolveCoincidentTopologyToPolygonOffset()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    _apply_material(actor.GetProperty(), mat)
    actor.GetProperty().SetLineWidth(1.0)
    return actor


def _apply_material(prop, mat: Material) -> None:
    prop.SetInterpolationToPBR()
    prop.SetColor(*mat.base_color)
    prop.SetMetallic(mat.metallic)
    prop.SetRoughness(mat.roughness)
    prop.SetOpacity(mat.opacity)
    prop.SetOcclusionStrength(1.0)


def _environment_texture(bd: Backdrop, n: int = 48) -> vtk.vtkTexture:
    """
    A procedural studio environment as a cubemap - no external asset files.

    Sky-to-ground vertical ramp with one broad softbox high on the +X side.
    Diffuse IBL is what keeps a dark grey body from going to mud in shadow, and
    the softbox is what puts a moving highlight along a fillet so the eye can
    read its curvature at all.
    """
    # face index -> (direction at texel (u, v)), OpenGL cubemap convention
    face_dirs = (
        lambda u, v: (1.0, -v, -u),
        lambda u, v: (-1.0, -v, u),
        lambda u, v: (u, 1.0, v),
        lambda u, v: (u, -1.0, -v),
        lambda u, v: (u, -v, 1.0),
        lambda u, v: (-u, -v, -1.0),
    )
    tex = vtk.vtkTexture()
    tex.CubeMapOn()
    tex.MipmapOn()
    tex.InterpolateOn()
    tex.UseSRGBColorSpaceOn()
    for f, dirfn in enumerate(face_dirs):
        img = vtk.vtkImageData()
        img.SetDimensions(n, n, 1)
        arr = vtk.vtkUnsignedCharArray()
        arr.SetNumberOfComponents(3)
        arr.SetNumberOfTuples(n * n)
        i = 0
        for y in range(n):
            v = 2.0 * (y + 0.5) / n - 1.0
            for x in range(n):
                u = 2.0 * (x + 0.5) / n - 1.0
                d = _norm(dirfn(u, v))
                t = 0.5 * (d[1] + 1.0)  # 0 at nadir, 1 at zenith
                horizon = t**0.65
                col = [bd.ground[k] + (bd.sky[k] - bd.ground[k]) * horizon for k in range(3)]
                # softbox: a broad, soft rectangle up and to the +X/-Z side
                s = max(0.0, d[0] * 0.55 - d[2] * 0.45 + d[1] * 0.70)
                col = [min(1.0, c + 0.85 * s**4) for c in col]
                arr.SetTuple3(i, *(int(255 * min(1.0, c * bd.exposure)) for c in col))
                i += 1
        img.GetPointData().SetScalars(arr)
        tex.SetInputDataObject(f, img)
    return tex


def _sweep_actor(
    bounds, direction, up, dist: float, view_angle: float, aspect: float, bd: Backdrop
) -> vtk.vtkActor:
    """
    A studio cyclorama: floor that curves up into a back wall, oriented so the
    wall always sits behind the part relative to the current camera azimuth.
    A flat ground plane gives a hard horizon line that reads as CAD; a sweep
    reads as a photograph.

    The sweep fills the frame, so it - not renderer.SetBackground - is what the
    viewer sees behind the part. Its vertical gradient therefore has to be
    carried by the surface itself: per-vertex colours, ramping from the floor
    tone up the wall, which VTK's PBR shader takes as the base colour.

    Sized from the camera, not from an arbitrary multiple of the part. An
    oversized sweep is not free: vtkShadowMapBakerPass fits its light frustum
    to the whole scene, so a 3 m backdrop around a 120 mm part spends the
    entire 2048 shadow map on empty floor and the part's own shadow vanishes
    into the depth bias.
    """
    cx = 0.5 * (bounds[0] + bounds[1])
    cy = 0.5 * (bounds[2] + bounds[3])
    cz = 0.5 * (bounds[4] + bounds[5])
    z0 = bounds[4]
    span = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])

    _, _, fwd = _camera_basis(direction, up)
    a = (
        _norm((direction[0], direction[1], 0.0))
        if (direction[0] or direction[1])
        else (0.0, -1.0, 0.0)
    )  # horizontal, toward the camera
    p = _cross((0.0, 0.0, 1.0), a)  # across the frame

    back, radius = 1.5 * span, 1.7 * span
    tan_half = math.tan(math.radians(view_angle) / 2.0)
    # half-frame at the wall, with headroom for the sweep's own curvature
    hh = (dist + back + radius) * tan_half * 1.30
    wall = max(1.6 * span, cz + (back + radius) * fwd[2] + hh - z0)
    half = max(1.8 * span, hh * aspect)
    front = min(0.9 * dist, 5.0 * span)

    profile = [(front, 0.0), (-back, 0.0)]
    steps = 16
    for k in range(1, steps + 1):
        ang = 0.5 * math.pi * k / steps
        profile.append((-back - radius * math.sin(ang), radius * (1.0 - math.cos(ang))))
    profile.append((-back - radius, wall))

    top = profile[-1][1]
    pts = vtk.vtkPoints()
    cols = vtk.vtkUnsignedCharArray()
    cols.SetNumberOfComponents(3)
    cols.SetName("sweep")
    quads = vtk.vtkCellArray()
    for k, (s, h) in enumerate(profile):
        t = (h / top) ** 0.55 if top > 0 else 0.0
        rgb = tuple(bd.sweep[i] + (bd.sweep_top[i] - bd.sweep[i]) * t for i in range(3))
        for side in (-1.0, 1.0):
            pts.InsertNextPoint(
                cx + a[0] * s + p[0] * half * side, cy + a[1] * s + p[1] * half * side, z0 + h
            )
            cols.InsertNextTuple3(*(int(255 * min(1.0, max(0.0, c))) for c in rgb))
        if k:
            base = 2 * (k - 1)
            quad = vtk.vtkQuad()
            for j, pid in enumerate((base, base + 1, base + 3, base + 2)):
                quad.GetPointIds().SetId(j, pid)
            quads.InsertNextCell(quad)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(quads)
    pd.GetPointData().SetScalars(cols)

    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(pd)
    normals.SetFeatureAngle(90.0)
    normals.ConsistencyOn()
    normals.SplittingOff()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    mapper.ScalarVisibilityOn()
    mapper.SetColorModeToDirectScalars()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetInterpolationToPBR()
    prop.SetColor(1.0, 1.0, 1.0)
    prop.SetMetallic(0.0)
    prop.SetRoughness(0.95)
    prop.BackfaceCullingOff()
    return actor


def _camera_basis(direction, up):
    """Orthonormal (right, up, forward) with forward pointing at the subject."""
    d = _norm(direction)
    fwd = (-d[0], -d[1], -d[2])
    right = _cross(fwd, up)
    if max(abs(c) for c in right) < 1e-9:
        right = _cross(fwd, (0.0, 1.0, 0.0))
    right = _norm(right)
    true_up = _norm(_cross(right, fwd))
    return right, true_up, fwd


def _frame_camera(
    cam, bounds, direction, up, width, height, view_angle: float, margin: float
) -> float:
    """
    Tight framing: project the eight bbox corners onto the camera axes and
    solve for the distance that just fits them, then back off by `margin`.
    vtkRenderer.ResetCamera fits the bounding SPHERE, which leaves a flat wide
    part swimming in whitespace - the exact "lost in the frame" failure the
    hero render is supposed to avoid.
    """
    right, true_up, fwd = _camera_basis(direction, up)
    cx = 0.5 * (bounds[0] + bounds[1])
    cy = 0.5 * (bounds[2] + bounds[3])
    cz = 0.5 * (bounds[4] + bounds[5])
    hw = hh = hd = 0.0
    for x in (bounds[0], bounds[1]):
        for y in (bounds[2], bounds[3]):
            for z in (bounds[4], bounds[5]):
                o = (x - cx, y - cy, z - cz)
                hw = max(hw, abs(sum(o[i] * right[i] for i in range(3))))
                hh = max(hh, abs(sum(o[i] * true_up[i] for i in range(3))))
                hd = max(hd, abs(sum(o[i] * fwd[i] for i in range(3))))
    half = math.radians(view_angle) / 2.0
    aspect = width / height
    dist = margin * max(hh / math.tan(half), hw / (math.tan(half) * aspect)) + hd

    cam.ParallelProjectionOff()
    cam.SetViewAngle(view_angle)
    cam.SetFocalPoint(cx, cy, cz)
    cam.SetPosition(cx - fwd[0] * dist, cy - fwd[1] * dist, cz - fwd[2] * dist)
    cam.SetViewUp(*up)
    return dist


def _add_studio_lights(
    renderer, bounds, direction, up, dist: float, shadows: bool, exposure: float = 1.0
) -> None:
    """
    Key / fill / rim, placed in world space from the camera basis so the rig
    follows the view. World space (not camera lights) because the shadow map
    baker needs a real positional light with a cone.
    """
    right, true_up, fwd = _camera_basis(direction, up)
    cx = 0.5 * (bounds[0] + bounds[1])
    cy = 0.5 * (bounds[2] + bounds[3])
    cz = 0.5 * (bounds[4] + bounds[5])

    def place(w_right, w_up, w_fwd, scale=1.0):
        return (
            cx + dist * scale * (right[0] * w_right + true_up[0] * w_up + fwd[0] * w_fwd),
            cy + dist * scale * (right[1] * w_right + true_up[1] * w_up + fwd[1] * w_fwd),
            cz + dist * scale * (right[2] * w_right + true_up[2] * w_up + fwd[2] * w_fwd),
        )

    renderer.AutomaticLightCreationOff()
    renderer.RemoveAllLights()

    key = vtk.vtkLight()
    key.SetLightTypeToSceneLight()
    key.SetPosition(*place(-0.62, 1.55, -0.55))
    key.SetFocalPoint(cx, cy, cz)
    key.SetColor(1.0, 0.985, 0.955)
    key.SetIntensity(0.95 * exposure)
    # The key stays DIRECTIONAL even when it is the shadow caster. Measured
    # here: vtkShadowMapBakerPass reports HasShadows=True for a positional spot
    # light and then casts nothing at any cone angle or shadow attenuation,
    # while a directional light casts a correct, correctly-placed shadow. This
    # is the reverse of the usual VTK advice, so it is easy to "fix" back into
    # a silent no-op - do not.
    key.SetPositional(False)
    if shadows:
        key.SetShadowAttenuation(0.22)
    renderer.AddLight(key)

    fill = vtk.vtkLight()
    fill.SetLightTypeToSceneLight()
    fill.SetPosition(*place(1.15, 0.20, -0.70))
    fill.SetFocalPoint(cx, cy, cz)
    fill.SetColor(0.86, 0.90, 1.0)
    fill.SetIntensity(0.30 * exposure)
    fill.SetPositional(False)
    renderer.AddLight(fill)

    rim = vtk.vtkLight()
    rim.SetLightTypeToSceneLight()
    rim.SetPosition(*place(0.55, 0.85, 1.05))
    rim.SetFocalPoint(cx, cy, cz)
    rim.SetColor(0.95, 0.97, 1.0)
    rim.SetIntensity(0.60 * exposure)
    rim.SetPositional(False)
    renderer.AddLight(rim)


def _build_pass_chain(renderer, shading: str, ssao_radius: float) -> None:
    """
    Install the render pass chain for `shading`.

    Measured on this machine (VTK 9.3.1, macOS OpenGL, offscreen):
      - renderer.SetUseSSAO / SetUseFXAA work, but ONLY while the renderer is
        on its default pass. Installing a shadow pass with SetPass() makes both
        flags no-ops - a shadow+SSAO image was bit-identical to shadow alone.
        Hence "shadows"/"both" chain the passes explicitly instead.
      - vtkShadowMapPass bakes and casts, but only for a DIRECTIONAL key (see
        _add_studio_lights), and it lays a straight-edged dark band across the
        curved sweep that no shadow-map resolution (2048/4096/8192) or key
        elevation removes. That band is why "ssao" and not "both" is the
        default: SSAO alone delivers the contact shading that makes refinement
        legible, with no artifact. Shadow modes stay selectable for flat-floor
        scenes, where the band does not appear.
    """
    if shading in ("ssao", "none"):
        renderer.SetUseFXAA(True)
        if shading == "ssao":
            renderer.SetUseSSAO(True)
            renderer.SetSSAORadius(ssao_radius)
            renderer.SetSSAOBias(SSAO_BIAS_FRACTION * ssao_radius)
            renderer.SetSSAOKernelSize(128)
            renderer.SetSSAOBlur(True)
        return

    baker = vtk.vtkShadowMapPass()
    baker.GetShadowMapBakerPass().SetResolution(SHADOW_MAP_RESOLUTION)
    seq = vtk.vtkSequencePass()
    coll = vtk.vtkRenderPassCollection()
    coll.AddItem(baker.GetShadowMapBakerPass())
    coll.AddItem(baker)
    seq.SetPasses(coll)
    cam_pass = vtk.vtkCameraPass()
    cam_pass.SetDelegatePass(seq)

    tail = cam_pass
    if shading == "both":
        ssao = vtk.vtkSSAOPass()
        ssao.SetRadius(ssao_radius)
        ssao.SetBias(SSAO_BIAS_FRACTION * ssao_radius)
        ssao.SetKernelSize(128)
        ssao.BlurOn()
        ssao.SetDelegatePass(cam_pass)
        tail = ssao
    fxaa = vtk.vtkOpenGLFXAAPass()
    fxaa.SetDelegatePass(tail)
    renderer.SetPass(fxaa)


def _capture(window, width: int, height: int, supersample: int, out: Path) -> None:
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(window)
    w2i.ReadFrontBufferOff()
    w2i.SetInputBufferTypeToRGB()
    w2i.Update()
    src = w2i.GetOutputPort()
    if supersample > 1:
        shrink = vtk.vtkImageShrink3D()
        shrink.SetInputConnection(src)
        shrink.SetShrinkFactors(supersample, supersample, 1)
        shrink.AveragingOn()
        src = shrink.GetOutputPort()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(out))
    writer.SetInputConnection(src)
    writer.Write()


def render_product_scene(
    items: list[tuple[cq.Shape, object, float]],
    out_dir: str | Path,
    prefix: str,
    views: tuple[str, ...] = DEFAULT_PRODUCT_VIEWS,
    size: int = 1600,
    aspect: float = 4 / 3,
    background: str | Backdrop = DEFAULT_BACKDROP,
    ground: bool = True,
    shading: str = "ssao",
    supersample: int = 2,
    view_angle: float = 16.0,
    margin: float = 1.14,
    env: bool = True,
    fill_cracks: bool = False,
) -> list[Path]:
    """
    Hero renders to <out_dir>/<prefix>_<view>.png. Returns the written paths.

    items      : list of (shape, material, opacity). material is a MATERIALS
                 key, a Material, or an (r, g, b) tuple. opacity < 1 makes a
                 shape see-through, e.g. a housing over its payload.
    size       : image WIDTH in px; height is size/aspect.
    background : "dark" | "light" | a Backdrop.
    shading    : "ssao" (default: SSAO + FXAA), "shadows", "both", "none".
                 _build_pass_chain records why the shadow modes are not the
                 default on this VTK build.
    supersample: render at N x and box-average down; 2 is enough for clean
                 edges, 3 for print.
    view_angle : vertical FOV in degrees. 16 deg is a ~135 mm lens - the long
                 lens keeps a housing looking rectilinear instead of dramatic.
    fill_cracks: overdraw per-face mesh boundaries to hide OCC tessellation
                 cracks. Off by default - _crack_fill_actor records why.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(background, Backdrop):
        bd = background
    elif background in BACKDROPS:
        bd = BACKDROPS[background]
    else:
        raise KeyError(f"unknown background {background!r}; known: {', '.join(BACKDROPS)}")
    if shading not in ("both", "ssao", "shadows", "none"):
        raise ValueError(f"shading must be both|ssao|shadows|none, got {shading!r}")
    supersample = max(1, int(supersample))

    width = int(size)
    height = int(round(size / aspect))

    polys = []
    for shape, spec, opacity in items:
        mat = _coerce_material(spec)
        if opacity < 1.0:
            mat = Material(mat.base_color, mat.metallic, mat.roughness, opacity)
        polys.append((_product_polydata(shape), mat))

    bounds = [1e30, -1e30, 1e30, -1e30, 1e30, -1e30]
    for poly, _ in polys:
        b = poly.GetBounds()
        for i in (0, 2, 4):
            bounds[i] = min(bounds[i], b[i])
            bounds[i + 1] = max(bounds[i + 1], b[i + 1])
    span = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])

    written: list[Path] = []
    for view in views:
        direction, up = _resolve_view(view)

        renderer = vtk.vtkRenderer()
        renderer.SetBackground(*bd.bottom)
        renderer.SetBackground2(*bd.top)
        renderer.GradientBackgroundOn()
        renderer.SetUseDepthPeeling(False)

        for poly, mat in polys:
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(poly)
            mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            _apply_material(actor.GetProperty(), mat)
            renderer.AddActor(actor)
            if fill_cracks and mat.opacity >= 1.0:
                renderer.AddActor(_crack_fill_actor(poly, mat))
        if env:
            renderer.UseImageBasedLightingOn()
            renderer.SetEnvironmentTexture(_environment_texture(bd))
            renderer.UseSphericalHarmonicsOff()  # cubemap SH is unsupported here
            renderer.SetEnvironmentUp(0.0, 0.0, 1.0)
            renderer.SetEnvironmentRight(1.0, 0.0, 0.0)

        cam = renderer.GetActiveCamera()
        dist = _frame_camera(cam, bounds, direction, up, width, height, view_angle, margin)
        if ground:
            renderer.AddActor(
                _sweep_actor(bounds, direction, up, dist, view_angle, width / height, bd)
            )
        _add_studio_lights(
            renderer,
            bounds,
            direction,
            up,
            dist,
            shadows=shading in ("shadows", "both"),
            exposure=bd.exposure,
        )
        # AO radius tracks feature size, not part size: at 0.16*span a 120 mm
        # box shades its whole top face, which reads as a dirty part rather
        # than as contact shading.
        _build_pass_chain(renderer, shading, ssao_radius=min(max(0.045 * span, 1.5), 10.0))

        window = vtk.vtkRenderWindow()
        window.SetOffScreenRendering(1)
        window.SetMultiSamples(0)  # supersampling does the AA; MSAA on
        window.AddRenderer(renderer)  # top of a pass chain is wasted work
        window.SetSize(width * supersample, height * supersample)
        renderer.ResetCameraClippingRange()
        window.Render()

        out = out_dir / f"{prefix}_{view}.png"
        _capture(window, width, height, supersample, out)
        window.Finalize()
        written.append(out)
    return written


def render_product_file(
    step_path: str | Path,
    out_dir: str | Path | None = None,
    views: tuple[str, ...] = DEFAULT_PRODUCT_VIEWS,
    size: int = 1600,
    material: str | Material = DEFAULT_MATERIAL,
    section: tuple[str, float] | None = None,
    **kwargs,
) -> list[Path]:
    """Hero-render one STEP file. See render_product_scene for the options."""
    return render_file(
        step_path,
        out_dir,
        views=views,
        size=size,
        section=section,
        quality="product",
        material=material,
        **kwargs,
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("files", nargs="+", help="STEP file(s) to render")
    ap.add_argument("-o", "--out", help="output directory (default: references/views/)")
    ap.add_argument(
        "--views",
        default=None,
        help=f"comma-separated subset of: {', '.join(VIEWS)} "
        f"(product mode also: {', '.join(PRODUCT_VIEWS)})",
    )
    ap.add_argument(
        "--size",
        type=int,
        default=None,
        help="image size in px (product mode: width; default 1100/1600)",
    )
    ap.add_argument("--no-axes", action="store_true", help="omit the axis triad")
    ap.add_argument(
        "--section",
        metavar="AXIS:STATION",
        help='cut away material on the + side of a plane, e.g. "Z:11"',
    )
    ap.add_argument(
        "--product",
        action="store_true",
        help="hero render: PBR, studio lighting, AO, sweep backdrop",
    )
    ap.add_argument(
        "--material", default=DEFAULT_MATERIAL, help=f"product material: {', '.join(MATERIALS)}"
    )
    ap.add_argument(
        "--background", default=DEFAULT_BACKDROP, help=f"product backdrop: {', '.join(BACKDROPS)}"
    )
    ap.add_argument(
        "--shading",
        default="ssao",
        choices=("both", "ssao", "shadows", "none"),
        help="product shading effects (default: ssao)",
    )
    ap.add_argument(
        "--no-ground", action="store_true", help="product: omit the studio sweep, float the part"
    )
    ap.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="product: render at N x and average down (default 2)",
    )
    args = ap.parse_args(argv)

    known = dict(PRODUCT_VIEWS) if args.product else {}
    known.update(VIEWS)
    default_views = DEFAULT_PRODUCT_VIEWS if args.product else DEFAULT_VIEWS
    views = (
        tuple(v.strip() for v in args.views.split(",") if v.strip())
        if args.views
        else default_views
    )
    unknown = [v for v in views if v not in known]
    if unknown:
        ap.error(f"unknown view(s): {', '.join(unknown)}")

    section = None
    if args.section:
        try:
            axis, station = args.section.split(":", 1)
            section = (axis.strip().upper(), float(station))
        except ValueError:
            ap.error(f'--section wants AXIS:STATION (e.g. "Z:11"), got {args.section!r}')

    extra = {}
    if args.product:
        extra = dict(
            material=args.material,
            background=args.background,
            shading=args.shading,
            ground=not args.no_ground,
            supersample=args.supersample,
        )

    for f in args.files:
        for path in render_file(
            f,
            args.out,
            views=views,
            size=args.size,
            axes=not args.no_axes,
            section=section,
            quality="product" if args.product else "verify",
            **extra,
        ):
            print(f"  ok {path}")


if __name__ == "__main__":
    main()
