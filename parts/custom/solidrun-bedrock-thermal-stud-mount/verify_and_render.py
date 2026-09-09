"""Nominal CAD verification and actual B-rep renders. No physical validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cadquery as cq
import model as m

HERE = Path(__file__).resolve().parent


def vol(a, b):
    return sum(s.Volume() for s in a.intersect(b).Solids())


def verify(p, shapes, items, work):
    checks = []

    def ck(n, ok, v=None, criterion=None):
        checks.append(dict(check=n, passed=bool(ok), measured=v, criterion=criterion))
        if not ok:
            print("FAIL", n, v, flush=True)

    ck(
        "Input SHA256 preserved",
        hashlib.sha256((HERE / "references/input_device.step").read_bytes()).hexdigest()
        == p["input_step_sha256"],
    )
    ck("21 derived configuration source components", sum(k == "device" for _, _, k in items) == 21)
    ck(
        "All component solids valid and distinct",
        all(s.isValid() and len(s.Solids()) == 1 for _, s, _ in items),
    )
    mappings = {
        "plate_T1.step": [i for i in items if i[2] == "plate"],
        "assembled_device_mount_T1.step": items,
        "device_adapter_T1.step": [
            i for i in items if i[2] in {"plate", "device", "screw", "tim_top"}
        ],
        "mount_hardware_T1.step": [
            i for i in items if i[2] in {"plate", "screw", "stud", "washer", "nut"}
        ],
        "FPE_interface_REFERENCE_ONLY.step": [i for i in items if i[2] in {"panel", "stud"}],
        "vertical_fin_installation_REFERENCE.step": [
            (n, s.rotate((0, 0, 0), (1, 0, 0), 90), k) for n, s, k in items
        ],
        "TIM_top_NOMINAL_POCKET_VOLUME.step": [i for i in items if i[2] == "tim_top"],
        "TIM_bottom_NOMINAL_POCKET_VOLUME.step": [i for i in items if i[2] == "tim_bottom"],
    }
    for name, expected in mappings.items():
        print("Reopen", name, flush=True)
        dest = work / name
        shutil.copyfile(HERE / "exports" / name, dest)
        actual = cq.importers.importStep(str(dest)).val()
        reference = cq.Compound.makeCompound([s for _, s, _ in expected])
        ck(
            name + " valid complete solids",
            actual.isValid() and len(actual.Solids()) == len(expected),
            len(actual.Solids()),
            len(expected),
        )
        ab, rb = m.bbox(actual), m.bbox(reference)
        ck(
            name + " mm scale and coordinates",
            all(abs(ab[a][i] - rb[a][i]) < 1e-4 for a in "xyz" for i in (0, 1)),
            ab,
            rb,
        )
        relative = abs(actual.Volume() - reference.Volume()) / max(1, reference.Volume())
        ck(
            name + " volume roundtrip",
            relative < 1e-5,
            relative,
            "<10 ppm; complex source helices show ~5 ppm STEP reserialization drift",
        )
    plate = items[0][1]
    panel = next(s for _, s, k in items if k == "panel")
    device = cq.Compound.makeCompound([s for _, s, k in items if k == "device"])
    t = p["plate_thickness"]
    ck(
        "Adapter/device nominal interference",
        vol(plate, device) < 1e-5,
        vol(plate, device),
        "No volumetric overlap; nominal contact allowed",
    )
    ck("Adapter/panel nominal interference", vol(plate, panel) < 1e-5)
    for side in ("top", "bottom"):
        field = m.thermal_field(p, side)
        ck(
            side + " TIM vs metal overlap",
            vol(field, plate) + vol(field, device) + vol(field, panel) < 1e-5,
        )
        ck(
            side + " TIM exact nominal pocket gap",
            abs(field.BoundingBox().zlen - p["thermal_pocket_depth"]) < 1e-6,
        )
    for n, s, k in items:
        if k not in {"screw", "stud", "washer", "nut"}:
            continue
        overlap = vol(s, plate)
        ck(n + " vs adapter", overlap < 1e-5, overlap)
        if k == "screw":
            # Real source female helices necessarily overlap a smooth male major-diameter proxy.
            # Only the specified blind thread zone may contain that expected proxy overlap.
            x, y = s.Center().x, s.Center().y
            mask = m.cyl(4.5, p["full_diameter_blind_limit_source"], x, y, t)
            unexpected = vol(s.cut(mask), device)
            ck(
                n + " outside expected thread engagement zone",
                unexpected < 1e-5,
                unexpected,
                "Does NOT verify thread fit, preload, real screw tip or seat",
            )
            ck(
                n + " nominal depth to full-diameter limit",
                t + 3.5 - s.BoundingBox().zmax >= 0.5 - 1e-6,
                t + 3.5 - s.BoundingBox().zmax,
            )
            ck(
                n + " nominal head recess",
                abs(s.BoundingBox().zmin - 0.05) < 1e-6,
                s.BoundingBox().zmin,
                "Ideal proxy only; physical head gauge is mandatory",
            )
        else:
            ck(n + " vs actual device", vol(s, device) < 1e-5)
    for i, (x, y) in enumerate(m.stud_points(p), 1):
        tool = m.cyl(p["tool_socket_envelope_diameter"], p["tool_socket_envelope_height"], x, y, t)
        gap = tool.distance(device)
        ck(
            f"Stud {i} socket OD10 device clearance",
            gap > 0.5,
            gap,
            ">0.5 mm nominal; socket internal depth >=8 mm",
        )
    movable = cq.Compound.makeCompound(
        [s for _, s, k in items if k in {"plate", "device", "screw", "tim_top"}]
    )
    fixed = cq.Compound.makeCompound([s for _, s, k in items if k in {"panel", "stud"}])
    for dz in (0, 0.1, 1, 6, 12, 13, 20):
        overlap = vol(movable.translate((0, 0, dz)), fixed)
        ck(
            f"Normal removal path sample {dz} mm",
            overlap < 1e-5,
            overlap,
            "Washers/nuts removed; grease released; straight aligned studs",
        )
    # Explicit design reservations, not purchased plug CAD. Actual cables require fit tests.
    corridors = [
        (
            "IO side 50mm plug reservation",
            cq.Workplane("XY").box(50, 150, 45).translate((-92.96, 0, t + 22.5)).val(),
        ),
        (
            "SMA end 50mm plug reservation",
            cq.Workplane("XY").box(116, 50, 45).translate((0, 115, t + 22.5)).val(),
        ),
    ]
    hardware = cq.Compound.makeCompound([s for _, s, k in items if k in {"stud", "washer", "nut"}])
    for n, s in corridors:
        overlap = vol(s, hardware)
        ck(
            n + " vs added hardware",
            overlap < 1e-5,
            overlap,
            "Reserved generic corridor; connector-specific mating and bend envelope not validated",
        )
    report = dict(
        status="PASS" if all(c["passed"] for c in checks) else "FAIL",
        count=len(checks),
        checks=checks,
        limitations=[
            "Analytical nominal CAD only; no physical test.",
            "Derived Tile/fin-bank reference does not verify product configuration or 60W cooling.",
            (
                "Major-diameter screw proxies exempt only the blind thread zone; "
                "real head/tip fit and supplier engagement limits remain mandatory."
            ),
            (
                "Generic plug reservations require actual-cable check; thermal contact, preload, "
                "plate flatness, FPE anchoring and TEC capacity remain unqualified."
            ),
        ],
    )
    (HERE / "exports/cad_verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(report["status"], len(checks), "CAD checks", flush=True)
    return report


def orthographic_renders(items: list) -> None:
    from render_support import render_scene

    views = HERE / "references/views"
    render_scene(
        [(items[0][1], (0.66, 0.72, 0.78), 1)],
        views,
        "plate",
        views=("top", "bottom", "front", "iso"),
        size=1300,
        axes=False,
    )
    render_scene(
        [(s, m.COLORS[k], 1) for _, s, k in items],
        views,
        "installed",
        views=("top", "bottom", "front", "right"),
        size=1400,
        axes=False,
    )
    render_scene(
        [
            (s, m.COLORS[k], 1)
            for _, s, k in items
            if k in {"device", "plate", "screw", "tim_top", "tim_bottom"}
        ],
        views,
        "device_adapter",
        views=("bottom", "front"),
        size=1400,
        axes=False,
    )


def renders(p: dict, shapes: list, items: list) -> None:
    from render_support import Material, render_product_scene, render_scene

    prod = HERE / "references/product"
    views = HERE / "references/views"
    prod.mkdir(parents=True, exist_ok=True)
    views.mkdir(parents=True, exist_ok=True)
    mats = {
        "tim_top": Material((0.08, 0.48, 0.61), 0.0, 0.6),
        "tim_bottom": Material((0.08, 0.48, 0.61), 0.0, 0.6),
        "plate": Material((0.61, 0.65, 0.70), 0.8, 0.34),
        "device": "anodised",
        "panel": "anodised_light",
        "screw": Material((0.09, 0.095, 0.1), 0.3, 0.4),
        "stud": "fastener",
        "washer": "fastener",
        "nut": "fastener",
    }

    # Preserve actual shape geometry while color-coding gold connector bodies.
    def material(n, s, k):
        if k == "device":
            b = s.BoundingBox()
            if b.ymin < -80 or b.ymax > 85:
                return "connector" if b.zlen < 14 and b.xlen < 20 else "anodised"
        return mats[k]

    print("Rendering assembled CAD...", flush=True)
    render_product_scene(
        [(s.rotate((0, 0, 0), (0, 0, 1), 180), material(n, s, k), 1) for n, s, k in items],
        prod,
        "assembled",
        views=("hero",),
        size=1800,
        background="light",
        ground=True,
    )
    plate = items[0][1]
    # Turn the underside upward for a useful manufactured-part view.
    render_product_scene(
        [(plate.rotate((0, 0, 0), (1, 0, 0), 180), mats["plate"], 1)],
        prod,
        "plate_bottom",
        views=("hero",),
        size=1500,
        background="light",
        ground=True,
    )
    exploded = []
    for n, s, k in items:
        dz = {
            "panel": 0,
            "stud": 0,
            "plate": 22,
            "screw": 12,
            "device": 60,
            "tim_top": 43,
            "tim_bottom": 13,
            "washer": 42,
            "nut": 48,
        }[k]
        exploded.append(
            (s.translate((0, 0, dz)).rotate((0, 0, 0), (0, 0, 1), 180), material(n, s, k), 1)
        )
    render_product_scene(
        exploded, prod, "exploded", views=("iso",), size=1800, background="light", ground=True
    )
    # True B-rep section at one housing fastener, clipped locally in X/Z.
    x, y = m.housing_points(p)[0]
    clip = cq.Workplane("XY").box(17, 0.05, 17).val().translate((x, y, 5))
    section = []
    for n, s, k in items:
        if k not in {"device", "plate", "screw", "tim_top", "tim_bottom", "panel"}:
            continue
        local = s.intersect(clip)
        if local.Solids():
            color = {
                "device": (0.38, 0.55, 0.48),
                "plate": (0.35, 0.55, 0.75),
                "screw": (0.78, 0.46, 0.15),
                "panel": (0.70, 0.72, 0.76),
                "tim_top": (0.08, 0.48, 0.61),
                "tim_bottom": (0.08, 0.48, 0.61),
            }[k]
            section.append((local, color, 1))
    paths = render_scene(
        section, views, "section_fastener", views=("front",), size=1500, axes=False
    )
    shutil.copyfile(paths[0], views / "section_fastener.png")
    for side in ("top", "bottom"):
        field = m.thermal_field(p, side)
        pair = [(plate, mats["plate"], 1), (field, mats["tim_top"], 1)]
        if side == "bottom":
            pair = [(s.rotate((0, 0, 0), (1, 0, 0), 180), mat, op) for s, mat, op in pair]
        render_product_scene(
            pair,
            prod,
            f"thermal_{side}",
            views=("hero",),
            size=1500,
            background="light",
            ground=True,
        )
    render_scene(
        [(s.rotate((0, 0, 0), (1, 0, 0), 90), m.COLORS[k], 1) for _, s, k in items],
        views,
        "vertical_fins",
        views=("front", "right", "iso"),
        size=1400,
        axes=False,
    )
    orthographic_renders(items)
    print("CAD renders complete.", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--work-dir", type=Path, default=Path("C:/b210work/solidrun_verify"))
    args = ap.parse_args()
    p = m.load_params()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    shapes = m.load_device(HERE / "references/input_device.step", p, args.work_dir)
    items = m.components(p, shapes)
    if not args.render_only and verify(p, shapes, items, args.work_dir)["status"] != "PASS":
        raise SystemExit("Fix verification failures")
    if not args.no_render:
        renders(p, shapes, items)


if __name__ == "__main__":
    main()
