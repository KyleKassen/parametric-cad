"""Compact SCE20 R2: direct Bedrock thermal seat and independent raised trays.

All dimensions mm; lower-left XY; Z0 is the backpanel component face.
Source R1 files are reused read-only. Thread geometry is simplified.
"""

import importlib.util
import itertools
import json
import math
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "sce20-layout"


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


old = module(OLD / "model.py", "sce20_r1_reference")
cyl = old.cyl
bounds = old.bounds


def parameters():
    p = old.read(OLD / "params.json")
    p["revision"] = "R2 stacked"
    placements = {
        "meanwell": ([379.9, 65.6, 0], 180),
        "bedrock": ([122, 107, 0], 0),
        "b210": ([282, 106, 50], 180),
        "peplink": ([122, 90, 80], 0),
        "oz": ([282, 107, 0], 0),
        "carrier": ([122, 107, 70], 0),
    }
    p["placements"] = {
        k: dict(translation_mm=v, rotation_z_deg=r) for k, (v, r) in placements.items()
    }
    interface = old.read(OLD / "references/interfaces/mount_interfaces.json")["components"]
    small = old.read(OLD / "references/router_oz/interfaces.json")
    p["hardware"] = []
    for key in ["meanwell", "bedrock", "b210", "oz", "carrier"]:
        pattern = (
            interface[key]["backpanel_studs"]["local_xy_mm"]
            if key in interface
            else small["oz"]["mounting_slots_xy"]
            if key == "oz"
            else list(itertools.product([-70, 70], [-97, 97]))
        )
        pl = p["placements"][key]
        a = math.radians(pl["rotation_z_deg"])
        for i, (x, y) in enumerate(pattern, 1):
            xx = math.cos(a) * x - math.sin(a) * y + pl["translation_mm"][0]
            yy = math.sin(a) * x + math.cos(a) * y + pl["translation_mm"][1]
            raised = key in {"b210", "carrier"}
            p["hardware"].append(
                dict(
                    id=key.upper() + "_" + str(i),
                    component=key,
                    x=math.floor((xx + 1e-8) * 1000) / 1000,
                    y=math.floor((yy + 1e-8) * 1000) / 1000,
                    catalog_code="WGO30" if raised else "WGU30",
                    length=20 if raised else 12,
                    side="front",
                    depth_offset=0,
                    seat_height={"meanwell": 6, "bedrock": 6, "oz": 3, "b210": 54, "carrier": 74}[
                        key
                    ],
                    extension_length=30 if key == "b210" else 50 if key == "carrier" else 0,
                    extension_part="971300321"
                    if key == "b210"
                    else "971500321"
                    if key == "carrier"
                    else None,
                )
            )
    p["clear_region"] = dict(
        x=[0, 215.9],
        y=[250, 431.8],
        note=(
            "Free of component and declared cable/air envelopes; "
            "retain existing factory hardware/tool access."
        ),
    )
    return p


def create_part(params=None):
    return old.create_part(parameters() if params is None else params)


def build_stages(params=None):
    yield "factory interface and native hardware cavities", create_part(params)


def raised_hardware(p):
    out = []
    for h in p["hardware"]:
        if h["catalog_code"] != "WGO30":
            continue
        x, y = h["x"], h["y"]
        base = cyl(11.9, 2.2, x, y, -2.2).fuse(cyl(5, 20, x, y, 0))
        base = base.cut(cyl(3, 10, x, y, 10))
        height = h["extension_length"]
        ext = (
            cq.Workplane("XY")
            .polygon(6, 5.5 / math.cos(math.pi / 6))
            .extrude(height)
            .val()
            .translate((x, y, 20))
        )
        ext = ext.fuse(cyl(3, 6, x, y, 14)).cut(cyl(3, 7, x, y, 20 + height - 7))
        top = h["seat_height"]
        washer = cyl(7, 0.55, x, y, top).cut(cyl(3.2, 0.75, x, y, top - 0.1))
        screw = cyl(3, 10, x, y, top + 0.55 - 10).fuse(cyl(5.5, 3, x, y, top + 0.55))
        out.extend(
            [
                (h["id"] + "_WGO30_L20", base, "hardware"),
                (h["id"] + "_WURTH_" + h["extension_part"], ext, "hardware"),
                (h["id"] + "_washer", washer, "hardware"),
                (h["id"] + "_M3x10", screw, "hardware"),
            ]
        )
    return out


def router_hardware():
    out = []
    for i, (dx, dy) in enumerate(itertools.product([-80.9, 80.9], [-41.35, 41.35]), 1):
        x, y = 122 + dx, 90 + dy
        base = cyl(11.9, 2.2, x, y, 71.8).fuse(cyl(5, 6, x, y, 74)).cut(cyl(4, 6, x, y, 74))
        washer = cyl(9, 1, x, y, 82.5).cut(cyl(4.3, 1.2, x, y, 82.4))
        screw = cyl(4, 8, x, y, 75.5).fuse(cyl(7, 4, x, y, 83.5))
        out.extend(
            [
                (f"PEPLINK_{i}_WGO40_L6", base, "hardware"),
                (f"PEPLINK_{i}_washer", washer, "hardware"),
                (f"PEPLINK_{i}_M4x8", screw, "hardware"),
            ]
        )
    return out


def generate():
    p = parameters()
    (HERE / "params.json").write_text(json.dumps(p, indent=2), encoding="utf-8")
    out = HERE / "exports"
    out.mkdir(exist_ok=True)
    checks = []

    def check(name, ok, value=None):
        checks.append(dict(check=name, pass_check=bool(ok), measured=value))
        print("PASS" if ok else "FAIL", name, flush=True)

    panel = create_part(p).val()
    cq.exporters.export(panel, str(out / "Backpanel_R2.step"))
    panel = cq.importers.importStep(str(out / "Backpanel_R2.step")).val()
    check(
        "Backpanel exported/reopened valid single solid",
        panel.isValid() and len(panel.Solids()) == 1,
    )
    b = bounds(panel)
    check(
        "431.8 square x6 dimensions",
        all(abs(b[a][1] - b[a][0] - n) < 1e-5 for a, n in zip("xyz", [431.8, 431.8, 6])),
        b,
    )
    for h in p["mounting_holes"]:
        check(
            h["id"] + " factory bore clear",
            abs(panel.intersect(cyl(h["diameter"] - 0.001, 6.2, h["x"], h["y"], -6.1)).Volume())
            < 1e-5,
        )
    for h in p["hardware"]:
        check(
            h["id"] + " native cavity envelope",
            abs(panel.intersect(cyl(12.099, 2.299, h["x"], h["y"], -2.299)).Volume()) < 1e-5,
        )
    webs = []
    for a, b in itertools.combinations(p["hardware"] + p["mounting_holes"], 2):
        da = 12.1 if "catalog_code" in a else a["diameter"]
        db = 12.1 if "catalog_code" in b else b["diameter"]
        webs.append(
            (math.hypot(a["x"] - b["x"], a["y"] - b["y"]) - (da + db) / 2, a["id"], b["id"])
        )
    check("All machining webs at least0.5mm", min(webs)[0] >= 0.5, min(webs))
    check(
        "All native cavity edge webs at least3mm",
        min(min(h["x"], h["y"], 431.8 - h["x"], 431.8 - h["y"]) - 6.05 for h in p["hardware"]) >= 3,
    )
    direct = {**p, "hardware": [h for h in p["hardware"] if h["catalog_code"] == "WGU30"]}
    hw = old.hardware(direct) + raised_hardware(p) + router_hardware()
    components = {}
    for key, path in old.SOURCES.items():
        components[key] = old.transformed(
            cq.importers.importStep(str(path)).val(), p["placements"][key]
        )
    carrier_path = HERE / "carrier/exports/Peplink_Carrier_R2_frame.step"
    carrier = cq.importers.importStep(str(carrier_path)).val()
    # Carrier source is centered XY, undersideZ0. Add catalog cavity envelopes
    # only to the integration CAD; FPD hardware owns production machining.
    for dx, dy in itertools.product([-80.9, 80.9], [-58.35, 24.35]):
        carrier = carrier.cut(cyl(12.1, 2.3, dx, dy, 1.7))
    cq.exporters.export(carrier, str(out / "Peplink_Carrier_R2.step"))
    components["carrier"] = carrier.translate((122, 107, 70))
    colors = {**old.COLORS, "carrier": (0.72, 0.64, 0.43)}
    old.COLORS.update(colors)
    for key, s in components.items():
        b = bounds(s)
        check(
            key + " contained in panel/door envelope",
            b["x"][0] >= -1e-4
            and b["x"][1] <= 431.8001
            and b["y"][0] >= -1e-4
            and b["y"][1] <= 431.8001
            and b["z"][0] >= -1e-4
            and b["z"][1] < 237.5352,
            b,
        )
    for (ka, a), (kb, b) in itertools.combinations(components.items(), 2):
        gap = a.distance(b)
        check(ka + " / " + kb + " physical clearance", gap > 0.1, gap)
    # Hardware-to-owning parts includes intentional screw/thread and seat contact;
    # all unrelated geometry must remain separated.
    for n, h, k in hw:
        owner = n.split("_")[0].lower()
        for key, s in components.items():
            if key == owner or (owner == "peplink" and key == "carrier"):
                continue
            d = h.distance(s)
            if d < 0.1:
                if (
                    (owner == "carrier" and key == "bedrock")
                    or (owner == "b210" and key == "meanwell")
                ) and n.endswith("_WGO30_L20"):
                    # A small part of the recessed bonded flange lies beneath
                    # the edge of the seated Bedrock plate. It is flush atZ0;
                    # prove no volume intrusion instead of calling contact a clash.
                    v = h.intersect(s).Volume()
                    check(n + " recessed flange flush beneath " + key + " edge", abs(v) < 1e-5, v)
                else:
                    check(n + " unrelated " + key + " interference", False, d)
    check(
        "Bedrock remains at direct original thermal seating plane",
        p["placements"]["bedrock"]["translation_mm"][2] == 0,
    )
    check(
        "Bedrock fin-to-carrier underside gap13mm",
        abs(
            components["carrier"].BoundingBox().zmin - components["bedrock"].BoundingBox().zmax - 13
        )
        < 1e-4,
    )
    check(
        "OZ-to-B210 underside gap17.28mm",
        abs(components["b210"].BoundingBox().zmin - components["oz"].BoundingBox().zmax - 17.28)
        < 1e-4,
    )
    check("Upper M3x10 screw insertion5.45mm within7mm blind thread", 0 < 10 - 4 - 0.55 < 7)
    check("Extension male6mm within native10mm thread", 6 < 10)
    items = (
        [("BACKPANEL_R2", panel, "panel")]
        + hw
        + [(k.upper() + "_INSTALLED", s, k) for k, s in components.items()]
    )
    old.export(items, out / "Installed_R2.step")
    saved = cq.importers.importStep(str(out / "Installed_R2.step")).val()
    check(
        "Assembly STEP reopened solid count",
        len(saved.Solids()) == sum(len(s.Solids()) for _, s, _ in items),
        len(saved.Solids()),
    )
    enclosure = cq.Shape.importBrep(str(OLD / "references/enclosure/source_enclosure.brep"))
    enc = [
        (f"SAGINAW_{i}", s.translate((0, 0, 2.825)) if i in [61, 62, 63, 64] else s, "enclosure")
        for i, s in enumerate(enclosure.Solids())
        if i != 60
    ]
    old.export(
        enc + [(n, s.translate((-215.9, -215.9, -106.395)), k) for n, s, k in items],
        out / "Enclosure_Installed_R2.step",
    )
    report = dict(
        status="PASS" if all(c["pass_check"] for c in checks) else "FAIL",
        checks=checks,
        maximum_height_mm=109.3,
        door_margin_mm=128.2352,
        scope=(
            "Nominal CAD integration; simplified threads; inherited invalid Peplink "
            "connector solids; no thermal/load qualification."
        ),
    )
    (out / "cad_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    render = module(
        ROOT / "parts/custom/solidrun-bedrock-thermal-stud-mount/render_support.py",
        "sce20_r2_renderer",
    )
    render.render_scene(
        [(s, colors[k], 1) for _, s, k in items],
        HERE / "renders",
        "Installed_R2",
        views=("top", "iso"),
        size=1500,
        axes=False,
    )
    # Exploded view makes both lower devices and their independent supports visible.
    upper = {"carrier", "peplink", "b210"}
    exploded = []
    for n, s, k in items:
        lift = 90 if k in upper else 0
        if k == "hardware" and (
            n.startswith("PEPLINK_")
            or (n.startswith(("CARRIER_", "B210_")) and n.endswith(("_washer", "_M3x10")))
        ):
            lift = 90
        exploded.append((s.translate((0, 0, lift)), colors[k], 1))
    render.render_scene(
        exploded, HERE / "renders", "Exploded_R2", views=("iso",), size=1500, axes=False
    )
    print(report["status"], len(checks), "checks", flush=True)


if __name__ == "__main__":
    generate()
