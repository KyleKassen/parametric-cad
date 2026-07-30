"""
Tests for lib/render_step.py product mode - and for the verification mode it
was bolted onto.

Two jobs. First, prove the hero render actually renders: a non-empty PNG at the
requested pixel size with the part visibly in it, not a blank frame that
happens to be the right shape. Second, and more important, prove the
VERIFICATION path is untouched. Every existing part in this repo has committed
reference views produced by that path; if adding PBR quietly changed a default,
a filename or the orthographic framing, the whole reference set silently goes
stale. So the constants, the filenames, the sizes and the pixels are all pinned
here against their pre-change values.
Run with: make test  (or: pytest tests/)
"""

import struct
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import lib.render_step as rs  # noqa: E402

# Small part, small images: rendering is the one thing here that is not free.
PART = cq.Workplane("XY").box(20, 14, 8).edges("|Z").fillet(2.0).faces(">Z").chamfer(0.6)
SHAPE = PART.val()


def png_size(path: Path) -> tuple[int, int]:
    """(width, height) straight out of the IHDR - no image library needed."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", data[16:24])


def assert_real_image(path: Path, width: int, height: int, min_bytes: int = 500):
    assert path.is_file(), f"{path} was not written"
    assert path.stat().st_size > min_bytes, f"{path.name} is {path.stat().st_size} bytes"
    assert png_size(path) == (width, height)


def pixels(path: Path):
    # Pillow arrives transitively with VTK rather than as a declared dependency,
    # so the pixel-level checks skip rather than error if it ever goes away. The
    # filename/size/byte-identity regressions above do not need it.
    image = pytest.importorskip("PIL.Image", reason="pillow not installed")
    return image.open(path).convert("RGB")


def distinct_colours(path: Path) -> int:
    im = pixels(path)
    return len(im.getcolors(maxcolors=1 << 20) or [])


def mean_luminance(path: Path) -> float:
    im = pixels(path).convert("L")
    data = list(im.tobytes())
    return sum(data) / len(data)


@pytest.fixture(scope="module")
def step_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("render") / "widget.step"
    cq.exporters.export(PART, str(path))
    return path


# ---------------------------------------------------------------------------
# REGRESSION: the verification path must be exactly what it always was
# ---------------------------------------------------------------------------
def test_verification_constants_are_unchanged():
    """Pinned literals, not references - a rename must fail here, loudly."""
    assert rs.VIEWS == {
        "top": ((0, 0, 1), (0, 1, 0)),
        "bottom": ((0, 0, -1), (0, 1, 0)),
        "front": ((0, -1, 0), (0, 0, 1)),
        "back": ((0, 1, 0), (0, 0, 1)),
        "left": ((-1, 0, 0), (0, 0, 1)),
        "right": ((1, 0, 0), (0, 0, 1)),
        "iso": ((1, -1, 0.8), (0, 0, 1)),
    }
    assert rs.DEFAULT_VIEWS == ("top", "bottom", "front", "back", "left", "right", "iso")
    assert rs.GRAY == (0.62, 0.66, 0.72)
    assert rs.VERIFY_TESSELLATION == (1e-3, 0.2), (
        "verification tessellation must stay coarse so old views stay comparable"
    )


def test_render_scene_filenames_and_square_size(tmp_path):
    written = rs.render_scene(
        [(SHAPE, rs.GRAY, 1.0)], tmp_path, "smoke", views=("front", "top"), size=220
    )
    assert [p.name for p in written] == ["smoke_front.png", "smoke_top.png"]
    for p in written:
        assert_real_image(p, 220, 220)


def test_render_scene_defaults_are_all_seven_views_at_1100px(tmp_path):
    written = rs.render_scene([(SHAPE, rs.GRAY, 1.0)], tmp_path, "def")
    assert [p.name for p in written] == [f"def_{v}.png" for v in rs.DEFAULT_VIEWS]
    assert png_size(written[0]) == (1100, 1100)


def test_verification_render_is_white_backed_and_deterministic(tmp_path):
    a = rs.render_scene([(SHAPE, rs.GRAY, 1.0)], tmp_path / "a", "v", views=("iso",), size=180)[0]
    b = rs.render_scene([(SHAPE, rs.GRAY, 1.0)], tmp_path / "b", "v", views=("iso",), size=180)[0]
    assert a.read_bytes() == b.read_bytes(), (
        "verification renders must be reproducible or reference views churn"
    )
    im = pixels(a)
    assert im.getpixel((1, 1)) == (255, 255, 255), "the white background is the contract"
    assert im.getpixel((im.size[0] - 2, 1)) == (255, 255, 255)
    assert distinct_colours(a) > 3, "something must actually be drawn"


def test_verification_axis_triad_toggles(tmp_path):
    on = rs.render_scene([(SHAPE, rs.GRAY, 1.0)], tmp_path / "on", "v", views=("iso",), size=180)[0]
    off = rs.render_scene(
        [(SHAPE, rs.GRAY, 1.0)], tmp_path / "off", "v", views=("iso",), size=180, axes=False
    )[0]
    assert on.read_bytes() != off.read_bytes(), "axes=False must change the image"


def test_render_file_verify_defaults_and_naming(tmp_path, step_file):
    written = rs.render_file(step_file, out_dir=tmp_path, views=("iso",), size=250)
    assert [p.name for p in written] == ["widget_iso.png"]
    assert_real_image(written[0], 250, 250)
    defaults = rs.render_file(step_file, out_dir=tmp_path / "d")
    assert [p.name for p in defaults] == [f"widget_{v}.png" for v in rs.DEFAULT_VIEWS]
    assert png_size(defaults[0]) == (1100, 1100), "the verify default size is still 1100"


def test_render_file_section_suffix_is_unchanged(tmp_path, step_file):
    written = rs.render_file(
        step_file, out_dir=tmp_path, views=("iso",), size=200, section=("Z", 2.5)
    )
    assert [p.name for p in written] == ["widget_secZ2p5_iso.png"]
    assert_real_image(written[0], 200, 200)


def test_render_file_default_out_dir_stays_references_views(tmp_path, step_file):
    part = tmp_path / "parts" / "custom" / "thing" / "exports"
    part.mkdir(parents=True)
    step = part / "thing_v1.step"
    step.write_bytes(step_file.read_bytes())
    written = rs.render_file(step, views=("iso",), size=180)
    assert written[0] == part / "references" / "views" / "thing_v1_iso.png"


def test_verify_mode_rejects_product_only_keywords(tmp_path, step_file):
    with pytest.raises(TypeError, match="unexpected keyword"):
        rs.render_file(step_file, out_dir=tmp_path, views=("iso",), size=180, background="dark")
    with pytest.raises(ValueError, match="quality must be"):
        rs.render_file(step_file, out_dir=tmp_path, quality="hologram")


def test_section_cut_still_guards_its_inputs():
    with pytest.raises(ValueError, match="beyond the part"):
        rs.section_cut(SHAPE, "Z", 99.0)
    with pytest.raises(ValueError, match="axis must be"):
        rs.section_cut(SHAPE, "Q", 1.0)


# ---------------------------------------------------------------------------
# product mode
# ---------------------------------------------------------------------------
def test_product_scene_writes_a_real_image_at_the_requested_size(tmp_path):
    written = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)], tmp_path, "hero", views=("hero",), size=320
    )
    assert [p.name for p in written] == ["hero_hero.png"]
    assert_real_image(written[0], 320, 240, min_bytes=2000)
    # a blank frame is the failure this test exists to catch
    assert distinct_colours(written[0]) > 50, (
        "a hero render with fewer than 50 colours is an empty backdrop"
    )


def test_product_size_is_width_and_aspect_sets_the_height(tmp_path):
    for aspect, expected in ((4 / 3, (240, 180)), (1.0, (240, 240)), (16 / 9, (240, 135))):
        out = rs.render_product_scene(
            [(SHAPE, "anodised", 1.0)],
            tmp_path,
            f"a{expected[1]}",
            views=("hero",),
            size=240,
            aspect=aspect,
        )[0]
        assert png_size(out) == expected


def test_product_writes_one_file_per_view(tmp_path):
    views = ("hero", "hero_low", "iso")
    written = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)], tmp_path, "v", views=views, size=200, supersample=1
    )
    assert [p.name for p in written] == [f"v_{v}.png" for v in views]
    assert all(p.stat().st_size > 1000 for p in written)
    assert len({p.read_bytes() for p in written}) == 3, "each view must differ"


def test_product_backdrops_change_the_image(tmp_path):
    dark = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)], tmp_path, "dark", views=("hero",), size=200, background="dark"
    )[0]
    light = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)], tmp_path, "light", views=("hero",), size=200, background="light"
    )[0]
    assert dark.read_bytes() != light.read_bytes()
    assert mean_luminance(dark) < mean_luminance(light) - 40.0, (
        "the dark studio must actually be darker than the light one"
    )


def test_product_render_is_deterministic(tmp_path):
    a = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)], tmp_path / "a", "p", views=("hero",), size=200
    )[0]
    b = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)], tmp_path / "b", "p", views=("hero",), size=200
    )[0]
    assert a.read_bytes() == b.read_bytes()


@pytest.mark.parametrize("shading", ["ssao", "shadows", "both", "none"])
def test_every_shading_mode_renders(tmp_path, shading):
    out = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)],
        tmp_path,
        shading,
        views=("hero",),
        size=180,
        shading=shading,
        supersample=1,
    )[0]
    assert_real_image(out, 180, 135, min_bytes=1000)


@pytest.mark.parametrize("material", ["anodised", "machined", "cast", "glass"])
def test_every_named_material_renders(tmp_path, material):
    out = rs.render_product_scene(
        [(SHAPE, material, 1.0)], tmp_path, material, views=("hero",), size=180, supersample=1
    )[0]
    assert_real_image(out, 180, 135, min_bytes=1000)


def test_material_may_be_a_dataclass_or_a_plain_rgb_tuple(tmp_path):
    for name, spec in (("mat", rs.MATERIALS["fastener"]), ("rgb", (0.8, 0.2, 0.2))):
        out = rs.render_product_scene(
            [(SHAPE, spec, 1.0)], tmp_path, name, views=("hero",), size=180, supersample=1
        )[0]
        assert_real_image(out, 180, 135, min_bytes=1000)


def test_product_supports_translucency_and_multiple_items(tmp_path):
    payload = cq.Workplane("XY").box(8, 6, 4).val()
    out = rs.render_product_scene(
        [(SHAPE, "anodised", 0.45), (payload, "connector", 1.0)],
        tmp_path,
        "assembly",
        views=("hero",),
        size=200,
    )[0]
    assert_real_image(out, 200, 150, min_bytes=1500)


def test_product_file_defaults_to_references_product(tmp_path, step_file):
    part = tmp_path / "parts" / "custom" / "thing" / "exports"
    part.mkdir(parents=True)
    step = part / "thing_v1.step"
    step.write_bytes(step_file.read_bytes())
    written = rs.render_product_file(step, views=("hero",), size=200)
    assert written[0] == part / "references" / "product" / "thing_v1_hero.png", (
        "hero renders must never land where verification views live"
    )
    assert_real_image(written[0], 200, 150, min_bytes=1000)


def test_product_via_render_file_with_a_section(tmp_path, step_file):
    written = rs.render_file(
        step_file,
        out_dir=tmp_path,
        views=("hero",),
        size=200,
        quality="product",
        material="machined",
        section=("Z", 2.0),
    )
    assert [p.name for p in written] == ["widget_secZ2_hero.png"]
    assert_real_image(written[0], 200, 150, min_bytes=1000)


def test_product_tables_and_defaults():
    assert rs.DEFAULT_PRODUCT_VIEWS == ("hero",)
    assert set(rs.PRODUCT_VIEWS) >= {"hero", "hero_left", "hero_rear", "hero_high", "hero_low"}
    assert set(rs.BACKDROPS) == {"dark", "light"}
    assert "anodised" in rs.MATERIALS
    # product tessellation must be materially finer, or fillets read as bevels
    assert rs.PRODUCT_TESSELLATION[1] < rs.VERIFY_TESSELLATION[1] / 4
    for name, mat in rs.MATERIALS.items():
        assert 0.0 <= mat.metallic <= 1.0 and 0.0 <= mat.roughness <= 1.0, name
        assert 0.0 < mat.opacity <= 1.0, name


def test_product_error_paths_name_what_is_valid(tmp_path):
    args = ([(SHAPE, "anodised", 1.0)], tmp_path, "err")
    with pytest.raises(KeyError, match="unknown background"):
        rs.render_product_scene(*args, views=("hero",), size=120, background="purple")
    with pytest.raises(ValueError, match="shading must be"):
        rs.render_product_scene(*args, views=("hero",), size=120, shading="glitter")
    with pytest.raises(KeyError, match="unknown material"):
        rs.render_product_scene(
            [(SHAPE, "unobtainium", 1.0)], tmp_path, "err", views=("hero",), size=120
        )
    with pytest.raises(KeyError, match="unknown view"):
        rs.render_product_scene(*args, views=("nosuchview",), size=120)


def test_product_and_verification_are_visibly_different_renders(tmp_path):
    verify = rs.render_scene([(SHAPE, rs.GRAY, 1.0)], tmp_path, "v", views=("iso",), size=240)[0]
    product = rs.render_product_scene(
        [(SHAPE, "anodised", 1.0)], tmp_path, "p", views=("iso",), size=240, aspect=1.0
    )[0]
    assert png_size(verify) == png_size(product) == (240, 240)
    assert pixels(verify).getpixel((1, 1)) == (255, 255, 255)
    assert pixels(product).getpixel((1, 1)) != (255, 255, 255), (
        "product mode must not inherit the verification white background"
    )
    assert distinct_colours(product) > distinct_colours(verify), (
        "PBR + supersampling should produce a richer image than flat shading"
    )
