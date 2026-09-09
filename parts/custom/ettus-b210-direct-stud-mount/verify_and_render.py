"""Independent exported-geometry, assembly, tool and service-path checks for D1.

No physical fit, load or thermal testing is performed by this program.
Use --no-render to repeat checks only; --render-only for visual regeneration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cadquery as cq
import ezdxf
import model as m

HERE = Path(__file__).resolve().parent


def intersect_volume(a: cq.Shape, b: cq.Shape) -> float:
    return sum(s.Volume() for s in a.intersect(b).Solids())


def verify(p: dict, shapes: list, items: list, work: Path) -> dict:
    checks = []

    def check(name, passed, measured=None, limit=None):
        checks.append(
            {"check": name, "pass": bool(passed), "measured": measured, "criterion": limit}
        )
        if not passed:
            print(f"FAIL: {name}: {measured}", flush=True)

    check(
        "Original input SHA256 preserved",
        hashlib.sha256((HERE / "references/input_device.step").read_bytes()).hexdigest()
        == p["input_step_sha256"],
    )
    check(
        "192 installed source bodies after removal of exactly four feet",
        len([i for i in items if i[2] == "device"]) == 192,
    )
    check(
        "All component solids valid", all(s.isValid() and len(s.Solids()) == 1 for _, s, _ in items)
    )
    exports = {
        "plate_D1.step": 1,
        "assembled_device_mount_D1.step": 210,
        "device_adapter_D1.step": 197,
        "mount_hardware_D1.step": 17,
        "FPE_interface_REFERENCE_ONLY.step": 5,
        "removed_feet_REFERENCE_ONLY.step": 4,
    }
    for name, count in exports.items():
        print(f"Reopening {name}...", flush=True)
        staged = work / name
        if not staged.exists():
            shutil.copyfile(HERE / "exports" / name, staged)
        s = cq.importers.importStep(str(staged)).val()
        check(
            f"{name} solid validity and completeness",
            s.isValid() and len(s.Solids()) == count,
            {"solids": len(s.Solids()), "bbox_mm": m.bbox(s)},
            f"valid; {count} distinct solids",
        )
        if name == "plate_D1.step":
            orig = items[0][1]
            b = s.BoundingBox()
            check(
                "Plate exported units/scale",
                abs(b.xlen - 150) < 1e-5 and abs(b.ylen - 148) < 1e-5 and abs(b.zlen - 3.5) < 1e-5,
            )
            check(
                "Plate export volume preserved",
                abs(s.Volume() - orig.Volume()) < 1e-4,
                s.Volume(),
                orig.Volume(),
            )
            check(
                "Plate exported symmetric difference",
                intersect_volume(s, orig) > orig.Volume() - 0.001,
            )
        if name == "assembled_device_mount_D1.step":
            expected = m.bbox(cq.Compound.makeCompound([s for _, s, _ in items]))
            check(
                "Assembly export coordinate scale",
                all(abs(m.bbox(s)[a][i] - expected[a][i]) < 1e-5 for a in "xyz" for i in (0, 1)),
            )
    plate = items[0][1]
    device = cq.Compound.makeCompound([s for _, s, k in items if k == "device"])
    panel = next(s for _, s, k in items if k == "panel")
    check(
        "Adapter to actual device interference",
        intersect_volume(plate, device) < 1e-5,
        intersect_volume(plate, device),
        "<=0.00001 mm3; nominal touching permitted",
    )
    check("Adapter to reference panel interference", intersect_volume(plate, panel) < 1e-5)
    for n, s, k in items:
        if k in {"screw", "stud", "washer", "nut"}:
            v = intersect_volume(s, plate)
            check(n + " vs adapter", v < 1e-5, v, "<=0.00001 mm3")
            v = intersect_volume(s, device)
            check(n + " vs original device", v < 1e-5, v, "<=0.00001 mm3; smooth thread envelopes")
    internal = cq.Compound.makeCompound(
        [
            shapes[i].translate((0, 0, p["plate_thickness"]))
            for i in p["device_internal_screw_indices_zero_based"]
        ]
    )
    for n, s, k in items:
        if k == "screw":
            gap = s.distance(internal)
            check(
                n + " nominal internal screw separation",
                gap > 0.5,
                gap,
                "nominal CAD >0.5 mm; actual measure required",
            )
            check(
                n + " ideal proxy head below seating plane",
                abs(s.BoundingBox().zmin - 0.05) < 1e-6,
                s.BoundingBox().zmin,
                "proxy Z=+0.05; actual received head must be gauged",
            )
    tools = []
    for i, (x, y) in enumerate(m.stud_points(p), 1):
        socket = m.cyl(
            p["tool_socket_envelope_diameter"],
            p["tool_socket_envelope_height"],
            x,
            y,
            p["plate_thickness"],
        )
        tools.append(socket)
        check(
            f"Stud {i} 10 mm OD socket to device clearance",
            socket.distance(device) > 0.5,
            socket.distance(device),
            ">0.5 mm envelope; actual socket verify",
        )
    movable = cq.Compound.makeCompound(
        [s for _, s, k in items if k in {"device", "plate", "screw"}]
    )
    fixed = cq.Compound.makeCompound([s for _, s, k in items if k in {"panel", "stud"}])
    for z in (0, 0.1, 2, 6, 12, 13, 20):
        v = intersect_volume(movable.translate((0, 0, z)), fixed)
        check(
            f"Vertical removal sample Z lift {z} mm",
            v < 1e-5,
            v,
            "nuts and washers removed; <=0.00001 mm3",
        )
    # Through holes are straight; these samples supplement, not replace, axis checks.
    corridors = []
    for sign in (-1, 1):
        length = p["connector_corridor_length"]
        cy = sign * (80 + length / 2)
        corridor = (
            cq.Workplane("XY")
            .box(
                p["connector_corridor_width"],
                length,
                p["connector_corridor_height"],
                centered=(True, True, False),
            )
            .val()
            .translate((0, cy, p["plate_thickness"] + p["connector_corridor_bottom_pan_z"]))
        )
        corridors.append(corridor)
        mount = cq.Compound.makeCompound([s for _, s, k in items if k != "device"])
        v = intersect_volume(corridor, mount)
        check(
            f"{'RF' if sign > 0 else 'USB/DC/ref'} connector planning corridor vs mount",
            v < 1e-5,
            v,
            "110 W × 60 outboard × 32 H envelope; actual plugs/cable bends not modeled",
        )
    check(
        "Nominal stud thread tail",
        p["stud_projection"]
        - p["plate_thickness"]
        - p["washer_thickness_nominal"]
        - p["nut_height_nominal"]
        >= 1,
        p["stud_projection"]
        - p["plate_thickness"]
        - p["washer_thickness_nominal"]
        - p["nut_height_nominal"],
        ">=1 mm / two M3 pitches beyond nut",
    )
    for name in (
        "plate_profile_mm.dxf",
        "plate_underside_machining_mm.dxf",
        "FPE_stud_pattern_mm.dxf",
    ):
        d = ezdxf.readfile(HERE / "exports" / name)
        a = d.audit()
        check(
            name + " reopens in mm without repair",
            d.units == ezdxf.units.MM and not a.errors and not a.fixes,
            {
                "units": d.units,
                "entities": len(d.modelspace()),
                "errors": len(a.errors),
                "fixes": len(a.fixes),
            },
        )
    report = {
        "revision": p["revision"],
        "status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "check_count": len(checks),
        "limits": [
            "No helical thread fit, actual plugs, actual screw-head form/tolerance, real FPE "
            "anchor thread/adhesive or panel support are simulated. Ideal cone is not a complete "
            "or conservative screw-head envelope.",
            "Original vendor internal intersections are not altered or interpreted "
            "as mount defects.",
            "Clearance samples and envelope distances do not constitute physical validation.",
        ],
    }
    (HERE / "references/cad_verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(f"Verification {report['status']}: {len(checks)} checks", flush=True)
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
        [(s, m.COLORS[k], 1) for _, s, k in items if k in {"device", "plate", "screw"}],
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
        [(s, material(n, s, k), 1) for n, s, k in items],
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
            "device": 55,
            "washer": 42,
            "nut": 48,
        }[k]
        exploded.append((s.translate((0, 0, dz)), material(n, s, k), 1))
    render_product_scene(
        exploded, prod, "exploded", views=("iso",), size=1800, background="light", ground=True
    )
    # True B-rep section at one housing fastener, clipped locally in X/Z.
    x, y = m.housing_points(p)[0]
    clip = cq.Workplane("XY").box(17, 0.05, 17).val().translate((x, y, 5))
    section = []
    for n, s, k in items:
        if k not in {"device", "plate", "screw", "panel"}:
            continue
        local = s.intersect(clip)
        if local.Solids():
            color = {
                "device": (0.38, 0.55, 0.48),
                "plate": (0.35, 0.55, 0.75),
                "screw": (0.78, 0.46, 0.15),
                "panel": (0.70, 0.72, 0.76),
            }[k]
            section.append((local, color, 1))
    paths = render_scene(
        section, views, "section_fastener", views=("front",), size=1500, axes=False
    )
    shutil.copyfile(paths[0], views / "section_fastener.png")
    orthographic_renders(items)
    print("CAD renders complete.", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--orthos-only", action="store_true")
    ap.add_argument("--work-dir", type=Path, default=Path("C:/b210work/direct_stud_mount"))
    args = ap.parse_args()
    p = m.load_params()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    shapes = m.load_device(HERE / "references/input_device.step", p, args.work_dir)
    items = m.components(p, shapes)
    if args.orthos_only:
        orthographic_renders(items)
        return
    if not args.render_only:
        report = verify(p, shapes, items, args.work_dir)
        if report["status"] != "PASS":
            raise SystemExit("Fix failed checks before delivery.")
    if not args.no_render:
        renders(p, shapes, items)


if __name__ == "__main__":
    main()
