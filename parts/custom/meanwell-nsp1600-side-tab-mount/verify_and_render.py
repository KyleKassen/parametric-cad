"""Reopen exports, check nominal geometry, render real CAD. No physical tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cadquery as cq
import model as m

HERE = Path(__file__).resolve().parent


def volume(a, b):
    return sum(s.Volume() for s in a.intersect(b).Solids())


def verify(p, shapes, items, work):
    checks = []

    def ck(n, ok, value=None, criterion=None):
        checks.append(dict(check=n, passed=bool(ok), measured=value, criterion=criterion))
        if not ok:
            print("FAIL", n, value, flush=True)

    ck(
        "Original source preserved",
        hashlib.sha256((HERE / "references/input_device.step").read_bytes()).hexdigest()
        == p["input_step_sha256"],
    )
    ck("All19original PSU solids retained", sum(k == "device" for _, _, k in items) == 19)
    ck(
        "35valid distinct solid components",
        len(items) == 35 and all(s.isValid() and len(s.Solids()) == 1 for _, s, _ in items),
    )
    maps = {
        "plate_N2.step": [i for i in items if i[2] == "plate"],
        "assembled_device_mount_N2.step": items,
        "device_adapter_N2.step": [i for i in items if i[2] in {"plate", "device", "screw"}],
        "mount_hardware_N2.step": [
            i for i in items if i[2] in {"plate", "screw", "stud", "washer", "nut"}
        ],
        "FPE_interface_REFERENCE_ONLY.step": [i for i in items if i[2] in {"panel", "stud"}],
    }
    for name, expected in maps.items():
        path = work / name
        shutil.copyfile(HERE / "exports" / name, path)
        actual = cq.importers.importStep(str(path)).val()
        ref = cq.Compound.makeCompound([s for _, s, _ in expected])
        ck(
            name + "valid complete solids",
            actual.isValid() and len(actual.Solids()) == len(expected),
            len(actual.Solids()),
            len(expected),
        )
        a, b = m.bbox(actual), m.bbox(ref)
        ck(
            name + "millimeter scale/coordinates",
            all(abs(a[k][i] - b[k][i]) < 1e-4 for k in "xyz" for i in (0, 1)),
            a,
            b,
        )
        drift = abs(actual.Volume() - ref.Volume()) / ref.Volume()
        limit = 3e-5 if any(k == "device" for _, _, k in expected) else 1e-8
        ck(name + "STEP volume drift", drift < limit, drift, limit)
    t = p["plate_thickness"]
    plate = items[0][1]
    panel = next(s for _, s, k in items if k == "panel")
    device = cq.Compound.makeCompound([s for _, s, k in items if k == "device"])
    ck(
        "Side-mounted body width41height85",
        abs(device.BoundingBox().xlen - 41) < 1e-4 and abs(device.BoundingBox().zlen - 85) < 1e-4,
        m.bbox(device),
    )
    ck("Adapter/PSU no interference", volume(plate, device) < 1e-5, volume(plate, device))
    ck("Adapter/panel no interference", volume(plate, panel) < 1e-5, volume(plate, panel))
    for idx in (p["device_shell_index"], p["device_fan_bracket_index"]):
        contact = volume(plate.translate((0, 0, 0.001)), shapes[idx].translate((0, 0, t))) / 0.001
        ck(
            f"Metal{idx} planar support contact",
            contact > 100,
            contact,
            "Approximate mm2 by1micron intersection; not load capacity",
        )
    for idx in p["device_fan_indices"]:
        gap = plate.distance(shapes[idx].translate((0, 0, t)))
        ck(f"Fan{idx} clear of plate", gap > 0.5, gap, "Nominal mm, not thermal proof")
    for n, s, k in items:
        if k not in {"screw", "stud", "washer", "nut"}:
            continue
        ck(n + " vs adapter", volume(s, plate) < 1e-5, volume(s, plate))
        if k == "screw":
            x, y = s.Center().x, s.Center().y
            is_front = y > -100
            mask = m.cyl(4.4, p["front_thread_zone_depth"] + 0.01, x, y, t) if is_front else None
            unexpected = volume(s.cut(mask) if mask is not None else s, device)
            ck(
                n + "expected geometry only",
                unexpected < 1e-5,
                unexpected,
                "Front minor-bore proxy overlap only; rear thread absent from STEP "
                "and must be physically confirmed",
            )
            projection = s.BoundingBox().zmax - t
            ck(
                n + "nominal intrusion",
                abs(projection - 4.05) < 1e-6 and projection < 5,
                projection,
                "OEM5max; received3.75..4.35mm",
            )
            ck(
                n + "proxy head recess",
                abs(s.BoundingBox().zmin - 0.05) < 1e-6,
                s.BoundingBox().zmin,
                "Actual DIN7991 head not fully modeled; physical gauge mandatory",
            )
        else:
            ck(n + " vs PSU", volume(s, device) < 1e-5, volume(s, device))
    x, y = m.housing_points(p)[0]
    tip = m.cyl(4, 0.001, x, y, t + p["screw_projection_accept_max"] - 0.001)
    tipgap = tip.distance(device)
    ck(
        "Front maximum accepted tip disc has positive material clearance",
        tipgap > 1e-5,
        tipgap,
        "Nearest distance includes lateral case material; it is not axial screw clearance",
    )
    extension = m.cyl(
        4, 7.4 - p["screw_projection_accept_max"], x, y, t + p["screw_projection_accept_max"]
    )
    ck(
        "Front axial screw envelope clear through 7.4mm inward",
        volume(extension, device) < 1e-5,
        volume(extension, device),
        "Measured first axial obstruction7.5mm; OEM5mm intrusion cap still governs",
    )
    x, y = m.housing_points(p)[1]
    probe = m.cyl(4, 5, x, y, t)
    ck(
        "Rear expected STEP thread absence documented",
        volume(probe, device) < 1e-5,
        volume(probe, device),
        "Evidence discrepancy only. DOES NOT establish rear attachment or justify assembly release",
    )
    for i, (x, y) in enumerate(m.stud_points(p), 1):
        tool = m.cyl(p["tool_socket_envelope_diameter"], p["tool_socket_envelope_height"], x, y, t)
        ck(
            f"S{i} socketOD10 clearance",
            tool.distance(device) > 1,
            tool.distance(device),
            "mm;10mm internal depth/60mm approach",
        )
    moving = cq.Compound.makeCompound([s for _, s, k in items if k in {"plate", "device", "screw"}])
    fixed = cq.Compound.makeCompound([s for _, s, k in items if k in {"panel", "stud"}])
    for lift in (0, 0.1, 1, 5, 10, 12, 13, 20):
        v = volume(moving.translate((0, 0, lift)), fixed)
        ck(
            f"Normal removal sample{lift}mm",
            v < 1e-5,
            v,
            "Nuts/washers removed; straight bores and normal path",
        )
    added = cq.Compound.makeCompound(
        [s for _, s, k in items if k in {"plate", "screw", "stud", "washer", "nut"}]
    )
    for name, y, ln in [
        ("intake", 0, p["intake_reservation_length"]),
        (
            "exhaust",
            p["source_fan_extreme_y"] - p["exhaust_reservation_length"],
            p["exhaust_reservation_length"],
        ),
    ]:
        corridor = cq.Solid.makeBox(41, ln, 85, cq.Vector(-20.5, y, t))
        v = volume(added, corridor)
        ck(
            name + "airflow planning corridor",
            v < 1e-5,
            v,
            "100mm assumption, actual cable/plug/guard clearance still required",
        )
    hw = [(n, s, k) for n, s, k in items if k in {"screw", "stud", "washer", "nut"}]
    bad = []
    for i, (n, s, k) in enumerate(hw):
        for nn, ss, kk in hw[i + 1 :]:
            if s.distance(ss) < 1e-7 and volume(s, ss) > 1e-5:
                bad.append((n, nn, volume(s, ss)))
    ck("Hardware pairs no unintended interference", not bad, bad)
    tail = p["stud_projection"] - t - p["washer_thickness_nominal"] - p["nut_height_nominal"]
    ck(
        "Nominal stud tail",
        tail >= 1,
        tail,
        "Actual>=1mm beyond nut plus complete nylon engagement",
    )
    gate = HERE / "exports/meanwell-nsp1600-side-tab-mount_v1.step"
    if gate.exists():
        shutil.copyfile(gate, work / "gate.step")
        g = cq.importers.importStep(str(work / "gate.step")).val()
        diff = plate.cut(g).Volume() + g.cut(plate).Volume()
        ck("Evaluated STEP equals delivered plate", abs(diff) < 1e-4, diff)
    outline = m.rounded_prism(m.outline_vertices(p), 1, p["corner_radius"]).val().Volume()
    old_outline = 125 * 300.6 - (4 - __import__("math").pi) * 8**2
    comparison = {
        "N1_max_width_mm": 125,
        "N2_max_width_mm": p["plate_width"],
        "maximum_width_reduction_percent": 100 * (1 - p["plate_width"] / 125),
        "N2_waist_mm": p["spine_width"],
        "N1_outline_area_mm2": old_outline,
        "N2_outline_area_mm2": outline,
        "outline_area_reduction_percent": 100 * (1 - outline / old_outline),
        "N1_adapter_device_height_mm": 46,
        "N2_adapter_device_height_mm": t + 85,
        "N2_plate_mass_kg": plate.Volume() * 2.7e-6,
        "scope": "Unperforated rounded outline, excludes cables/tools/mainpanel; "
        "maxwidth differs from occupied area",
    }
    report = {
        "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
        "scope": "Nominal CAD only; rearM4 thread and sideorientation power unverified",
        "params_sha256": hashlib.sha256((HERE / "params.json").read_bytes()).hexdigest(),
        "checks": checks,
        "check_count": len(checks),
        "passed_count": sum(c["passed"] for c in checks),
        "N1_comparison": comparison,
        "limitations": [
            "Rear sideM4 is specified by OEM but absent from STEP; "
            "physical thread/hardware confirmation mandatory",
            "Two-screw roll restraint relies on qualified finite metal contact and joint seating; "
            "no thread/anchor rating from CAD",
            "Sideorientation output-current derating unresolved; "
            "no full-power or enclosure thermal qualification",
            "Actual screw heads, plugs/lugs/guards/cables and finalpanel "
            "are not supplier-validated assembly geometry",
        ],
    }
    (HERE / "quality").mkdir(exist_ok=True)
    (HERE / "quality/cad_verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(report["status"], len(checks), "nominal CAD checks", flush=True)
    return report


def renders(p, shapes, items):
    from render_support import Material, render_product_scene, render_scene

    product, views = HERE / "references/product", HERE / "references/views"
    product.mkdir(parents=True, exist_ok=True)
    views.mkdir(parents=True, exist_ok=True)
    materials = {
        "plate": Material((0.64, 0.69, 0.74), 0.8, 0.34),
        "panel": "anodised_light",
        "device": "aluminium",
        "screw": Material((0.09, 0.10, 0.11), 0.3, 0.4),
        "stud": "fastener",
        "washer": "fastener",
        "nut": "fastener",
    }

    def material(n, k):
        if k == "device":
            index = int(n.rsplit("_", 1)[1])
            if index in p["device_fan_indices"]:
                return Material((0.05, 0.055, 0.06), 0.05, 0.6)
            if index == p["device_pcb_index"]:
                return Material((0.07, 0.28, 0.14), 0.1, 0.6)
            return Material((0.6, 0.62, 0.65), 0.75, 0.36)
        return materials[k]

    def spin(s):
        return s.rotate((0, 0, 0), (0, 0, 1), 90)

    render_product_scene(
        [(spin(s), material(n, k), 1) for n, s, k in items],
        product,
        "assembled",
        views=("hero",),
        size=1800,
        background="light",
        ground=True,
    )
    plate = items[0][1]
    for side in ("top", "bottom"):
        s = plate if side == "top" else plate.rotate((0, 0, 0), (1, 0, 0), 180)
        render_product_scene(
            [(spin(s), materials["plate"], 1)],
            product,
            "plate_" + side,
            views=("hero",),
            size=1600,
            background="light",
            ground=True,
        )
    exploded = []
    for n, s, k in items:
        dz = {
            "panel": 0,
            "stud": 0,
            "plate": 25,
            "screw": 15,
            "device": 65,
            "washer": 42,
            "nut": 50,
        }[k]
        exploded.append((spin(s.translate((0, 0, dz))), material(n, k), 1))
    render_product_scene(
        exploded, product, "exploded", views=("iso",), size=1800, background="light", ground=True
    )
    render_scene(
        [(plate, m.COLORS["plate"], 1)],
        views,
        "plate",
        views=("top", "bottom", "front", "iso"),
        size=1400,
        axes=False,
    )
    render_scene(
        [(s, m.COLORS[k], 1) for _, s, k in items],
        views,
        "installed",
        views=("top", "front", "right", "bottom"),
        size=1400,
        axes=False,
    )
    for label, x, y, width, height in [
        ("front_side_mount", 2.3, -5.8, 30, 18),
        ("rear_side_mount", 2.3, -257.8, 30, 18),
    ]:
        clip = cq.Solid.makeBox(width, 0.05, height, cq.Vector(x - width / 2, y - 0.025, -1))
        section = []
        for n, s, k in items:
            if k not in {"plate", "panel", "screw", "device"}:
                continue
            local = s.intersect(clip)
            if local.Solids():
                col = {
                    "plate": (0.32, 0.52, 0.75),
                    "panel": (0.72, 0.75, 0.78),
                    "screw": (0.86, 0.49, 0.13),
                    "device": (0.38, 0.55, 0.43),
                }[k]
                section.append((local, col, 1))
        render_scene(section, views, "section_" + label, views=("front",), size=1600, axes=False)
    print("Actual CAD render set complete", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--work-dir", type=Path, default=Path("C:/b210work/nsp1600_side_verify"))
    args = ap.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    p = m.load_params()
    shapes = m.load_device(HERE / "references/input_device.step", p, args.work_dir)
    items = m.components(p, shapes)
    if not args.render_only and verify(p, shapes, items, args.work_dir)["status"] != "PASS":
        raise SystemExit("Fix CAD verification failures")
    if not args.no_render:
        renders(p, shapes, items)


if __name__ == "__main__":
    main()
