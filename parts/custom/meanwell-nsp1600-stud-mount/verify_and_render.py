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

    def ck(name, ok, value=None, criterion=None):
        checks.append(dict(check=name, passed=bool(ok), measured=value, criterion=criterion))
        if not ok:
            print("FAIL", name, value, flush=True)

    ck(
        "Original source STEP hash preserved",
        hashlib.sha256((HERE / "references/input_device.step").read_bytes()).hexdigest()
        == p["input_step_sha256"],
    )
    ck("All 19 original PSU solids retained", sum(k == "device" for _, _, k in items) == 19)
    ck(
        "36 components each valid single solid",
        len(items) == 36 and all(s.isValid() and len(s.Solids()) == 1 for _, s, _ in items),
    )
    mappings = {
        "plate_N1.step": [i for i in items if i[2] == "plate"],
        "assembled_device_mount_N1.step": items,
        "device_adapter_N1.step": [i for i in items if i[2] in {"plate", "device", "screw"}],
        "mount_hardware_N1.step": [
            i for i in items if i[2] in {"plate", "screw", "stud", "washer", "nut"}
        ],
        "FPE_interface_REFERENCE_ONLY.step": [i for i in items if i[2] in {"panel", "stud"}],
    }
    for name, expected in mappings.items():
        staged = work / name
        shutil.copyfile(HERE / "exports" / name, staged)
        actual = cq.importers.importStep(str(staged)).val()
        ref = cq.Compound.makeCompound([s for _, s, _ in expected])
        ck(
            name + " valid complete solids",
            actual.isValid() and len(actual.Solids()) == len(expected),
            len(actual.Solids()),
            len(expected),
        )
        ab, rb = m.bbox(actual), m.bbox(ref)
        ck(
            name + " millimeter scale and coordinates",
            all(abs(ab[a][i] - rb[a][i]) < 1e-4 for a in "xyz" for i in (0, 1)),
            ab,
            rb,
        )
        drift = abs(actual.Volume() - ref.Volume()) / ref.Volume()
        limit = 3e-5 if any(k == "device" for _, _, k in expected) else 1e-8
        ck(
            name + " STEP volume roundtrip",
            drift < limit,
            drift,
            f"relative <{limit}; source audit observed18.1ppm vendor reserialization drift",
        )
    plate = items[0][1]
    panel = next(s for _, s, k in items if k == "panel")
    device = cq.Compound.makeCompound([s for _, s, k in items if k == "device"])
    t = p["plate_thickness"]
    ck(
        "Adapter vs PSU interference",
        volume(plate, device) < 1e-5,
        volume(plate, device),
        "mm3; surface contact allowed",
    )
    ck("Adapter vs panel interference", volume(plate, panel) < 1e-5, volume(plate, panel))
    for index in p["device_fan_indices"]:
        fan = shapes[index].translate((0, 0, t))
        gap = plate.distance(fan)
        ck(
            f"Fan {index} to adapter nominal minimum distance",
            gap >= p["minimum_physical_fan_gap"] - 1e-6,
            gap,
            "Nominal >=0.20mm; physical gap must be gauged separately",
        )
    # Probe each metal mounting land with a 0.001mm slab just above the case bottom.
    # This gives a conservative cross-sectional contact footprint, not clamp capacity.
    for index in (p["device_shell_index"], p["device_fan_bracket_index"]):
        metal = shapes[index].translate((0, 0, t))
        contact = volume(plate.translate((0, 0, 0.001)), metal) / 0.001
        ck(
            f"Metal part {index} supported contact footprint",
            contact > 100,
            contact,
            "mm2 approximate from1micron overlap; >100mm2",
        )
    for n, s, k in items:
        if k not in {"screw", "stud", "washer", "nut"}:
            continue
        ck(n + " vs adapter", volume(s, plate) < 1e-5, volume(s, plate))
        if k == "screw":
            x, y = s.Center().x, s.Center().y
            # Only the published mounting boss zone can overlap the smooth major-diameter proxy.
            mask = m.cyl(3.2, 2.11, x, y, t)
            unexpected = volume(s.cut(mask), device)
            ck(
                n + " outside expected female minor-bore zone",
                unexpected < 1e-5,
                unexpected,
                "Not a thread fit or actual-head geometry test",
            )
            ck(
                n + " nominal intrusion",
                s.BoundingBox().zmax - t <= 4,
                s.BoundingBox().zmax - t,
                "OEM max4mm",
            )
            ck(
                n + " ideal proxy head recess",
                abs(s.BoundingBox().zmin - 0.05) < 1e-6,
                s.BoundingBox().zmin,
                "Actual DIN7991 head gauge required: flush to0.10below A",
            )
        else:
            ck(n + " vs PSU", volume(s, device) < 1e-5, volume(s, device))
    pcb = shapes[p["device_pcb_index"]].translate((0, 0, t))
    for i, (x, y) in enumerate(m.housing_points(p)[:2], 1):
        screw = m.housing_screw(p).translate((x, y, 0))
        ck(
            f"H{i} nominal tip to modeled PCB",
            screw.distance(pcb) > 1.0,
            screw.distance(pcb),
            ">1mm CAD; manufacturer4mm cap still governs",
        )
        max_tip = m.cyl(3, p["screw_projection_accept_max"], x, y, t)
        ck(
            f"H{i} maximum accepted protrusion vs PCB",
            volume(max_tip, pcb) < 1e-5,
            max_tip.distance(pcb),
            "2.75..3.35mm physical protrusion acceptance, unverified receiving tolerances",
        )
    for i, (x, y) in enumerate(m.stud_points(p), 1):
        tool = m.cyl(p["tool_socket_envelope_diameter"], p["tool_socket_envelope_height"], x, y, t)
        gap = tool.distance(device)
        ck(
            f"S{i} socket OD10 access",
            gap > 0.5,
            gap,
            "mm; >=10mm internal socket depth,60mm overhead reservation",
        )
    movable = cq.Compound.makeCompound(
        [s for _, s, k in items if k in {"plate", "device", "screw"}]
    )
    fixed = cq.Compound.makeCompound([s for _, s, k in items if k in {"panel", "stud"}])
    for dz in (0, 0.1, 1, 5, 10, 12, 13, 20):
        overlap = volume(movable.translate((0, 0, dz)), fixed)
        ck(
            f"Normal removal sample {dz}mm",
            overlap < 1e-5,
            overlap,
            "Nuts and washers removed first; samples plus straight cylindrical bore path",
        )
    added = cq.Compound.makeCompound(
        [s for _, s, k in items if k in {"plate", "screw", "stud", "washer", "nut"}]
    )
    for name, y, length in [
        ("intake", 0, p["intake_reservation_length"]),
        (
            "exhaust",
            p["source_fan_extreme_y"] - p["exhaust_reservation_length"],
            p["exhaust_reservation_length"],
        ),
    ]:
        corridor = cq.Solid.makeBox(85, length, 41, cq.Vector(-42.5, y, t))
        overlap = volume(added, corridor)
        ck(
            name + " corridor vs added adapter hardware",
            overlap < 1e-5,
            overlap,
            "100mm planning reservation, not plug/cable modeling or universal OEM minimum",
        )
    # Expected shank/female proxy overlap is excluded only above; other purchased pairs are checked.
    hw = [(n, s, k) for n, s, k in items if k in {"screw", "stud", "washer", "nut"}]
    bad_pairs = []
    for i, (n, s, k) in enumerate(hw):
        for nn, ss, kk in hw[i + 1 :]:
            if s.distance(ss) < 1e-7:
                v = volume(s, ss)
                if v > 1e-5:
                    bad_pairs.append((n, nn, v))
    ck("Hardware pair interference excluding nominal contact", not bad_pairs, bad_pairs)
    ck(
        "Stud protrusion past nominal nut",
        p["stud_projection"] - t - p["washer_thickness_nominal"] - p["nut_height_nominal"] >= 1,
        p["stud_projection"] - t - p["washer_thickness_nominal"] - p["nut_height_nominal"],
        ">=1mm nominal, physically verify nylon fully traversed",
    )
    gate = HERE / "exports/meanwell-nsp1600-stud-mount_v1.step"
    if gate.exists():
        staged = work / "evaluated_plate.step"
        shutil.copyfile(gate, staged)
        evaluated = cq.importers.importStep(str(staged)).val()
        difference = plate.cut(evaluated).Volume() + evaluated.cut(plate).Volume()
        ck(
            "Repository evaluated STEP matches deliverable plate",
            abs(difference) < 1e-4,
            difference,
            "symmetric difference mm3",
        )
    report = {
        "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
        "scope": "Nominal CAD analytical checks only; no physical fabrication or testing",
        "params_sha256": hashlib.sha256((HERE / "params.json").read_bytes()).hexdigest(),
        "checks": checks,
        "passed_count": sum(c["passed"] for c in checks),
        "check_count": len(checks),
        "limitations": [
            "Manufacturer general±0.5mm pattern not covered by self-centering CSKs; "
            "fit template and coordinate survey mandatory",
            "Thread material/capacity, real screw seat, FPE anchors "
            "and all physical loads unvalidated",
            "Actual plugs, lugs, terminal covers and cable bend radii not modeled",
            "No cooling capacity, EMC, electrical safety or vibration qualification",
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
        ("front_mount", -35, -16.1, 18, 16),
        ("fan_mount", 0, -280.8, 86, 13),
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
    ap.add_argument("--work-dir", type=Path, default=Path("C:/b210work/nsp1600_verify"))
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
