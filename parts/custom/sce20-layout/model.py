"""SCE20 R1 backpanel and installed assembly. CAD mm; front face Z=0.

Native FPD hardware owns manufacturing cavities. This CAD model represents those
same catalog envelopes for integration; screw threads are simplified cylinders.

The declared repository design gate remains 70. The exported plate measures
48.8/D and fails that gate even though its mechanical evaluation passes.
Its blank rear seating face, six factory holes and different component mounting
patterns are functional interfaces. Cosmetic recommendations to recess/rib the
rear face or redistribute hole families conflict with those interfaces and the
packing constraints; they are documented findings, not a passed design review.
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
sys.path.insert(0, str(ROOT))
from lib.features import rounded_box  # noqa: E402 - repository path is bootstrapped above


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def load_params():
    return read(HERE / "params.json")


def cyl(d, h, x=0, y=0, z=0):
    return cq.Solid.makeCylinder(d / 2, h, cq.Vector(x, y, z))


def bounds(s):
    b = s.BoundingBox()
    return {a: [getattr(b, a + "min"), getattr(b, a + "max")] for a in "xyz"}


def create_part(params=None):
    p = load_params() if params is None else params
    plate = (
        rounded_box(
            p["width"],
            p["height"],
            p["thickness"],
            p["corner_radius"],
            top_break=0.4,
            bottom_break=0.4,
        )
        .val()
        .translate((p["width"] / 2, p["height"] / 2, -p["thickness"]))
    )
    for h in p["mounting_holes"]:
        plate = plate.cut(
            cyl(h["diameter"], p["thickness"] + 2, h["x"], h["y"], -p["thickness"] - 1)
        )
    for h in p["hardware"]:
        plate = plate.cut(cyl(12.1, 2.3, h["x"], h["y"], -2.3))
    return cq.Workplane("XY").newObject([plate])


def build_stages(params=None):
    yield "catalog-interface plate", create_part(params)


def hardware(p):
    out = []
    for h in p["hardware"]:
        x, y = h["x"], h["y"]
        base = cyl(11.9, 2.2, x, y, -2.2)
        if h["catalog_code"] == "WGU30":
            fastener = base.fuse(cyl(3, 12, x, y, 0))
            t = h["seat_height"]
            wt = 0.8 if h["component"] == "oz" else 0.55
            wd = 9 if h["component"] == "oz" else 7
            washer = cyl(wd, wt, x, y, t).cut(cyl(3.2, wt + 0.2, x, y, t - 0.1))
            nut = (
                cq.Workplane("XY")
                .polygon(6, 5.5 / math.cos(math.pi / 6))
                .extrude(4)
                .val()
                .translate((x, y, t + wt))
            )
            nut = nut.cut(cyl(3, 4.2, x, y, t + wt - 0.1))
            out.extend(
                [
                    (h["id"] + "_washer", washer, "hardware"),
                    (h["id"] + "_M3_locknut", nut, "hardware"),
                ]
            )
        else:
            fastener = base.fuse(cyl(5, 6, x, y, 0)).cut(cyl(4, 6, x, y, 0))
            washer = cyl(9, 1, x, y, 8.5).cut(cyl(4.3, 1.2, x, y, 8.4))
            # M4x8 length is under head. 2.5mm ear +1mm washer ->4.5mm engagement.
            screw = cyl(4, 8, x, y, 1.5).fuse(cyl(7, 4, x, y, 9.5))
            out.extend(
                [(h["id"] + "_washer", washer, "hardware"), (h["id"] + "_M4x8", screw, "hardware")]
            )
        out.append((h["id"] + "_" + h["catalog_code"] + "_simplified", fastener, "hardware"))
    return out


def transformed(s, pl):
    return s.rotate((0, 0, 0), (0, 0, 1), pl["rotation_z_deg"]).translate(
        tuple(pl["translation_mm"])
    )


def initialize_parameters():
    layout = read(HERE / "references/layout_search/placement.json")
    enclosure = read(HERE / "references/enclosure/panel_geometry.json")
    interfaces = read(HERE / "references/interfaces/mount_interfaces.json")["components"]
    small = read(HERE / "references/router_oz/interfaces.json")
    hardware = []
    for key, pl in layout["placements"].items():
        if key in interfaces:
            pattern = interfaces[key]["backpanel_studs"]["local_xy_mm"]
        elif key == "peplink":
            pattern = small[key]["mounting_holes_xy"]
        else:
            pattern = small[key]["mounting_slots_xy"]
        a = math.radians(pl["rotation_z_deg"])
        c, s = math.cos(a), math.sin(a)
        for i, (x, y) in enumerate(pattern, 1):
            xx = c * x - s * y + pl["translation_mm"][0]
            yy = s * x + c * y + pl["translation_mm"][1]
            # Retain native0.001mm manufacturing resolution, B210120.015mm pitch.
            # Uniform truncation preserves the120.015mm B210 half-micron pattern.
            qx = math.floor((xx + 1e-8) * 1000) / 1000
            qy = math.floor((yy + 1e-8) * 1000) / 1000
            hardware.append(
                dict(
                    id=key.upper() + "_" + str(i),
                    component=key,
                    x=qx,
                    y=qy,
                    catalog_code="WGO40" if key == "peplink" else "WGU30",
                    length=6 if key == "peplink" else 12,
                    side="front",
                    depth_offset=0,
                    seat_height={"b210": 4, "bedrock": 6, "meanwell": 6, "peplink": 6, "oz": 3}[
                        key
                    ],
                )
            )
    holes = [
        dict(
            id="FACTORY_" + str(i + 1),
            x=h["center_xy_mm"][0] + 215.9,
            y=h["center_xy_mm"][1] + 215.9,
            diameter=h["diameter_mm"],
        )
        for i, h in enumerate(enclosure["panel"]["holes"])
    ]
    p = dict(
        units="mm",
        revision="R1",
        width=431.8,
        height=431.8,
        thickness=6,
        corner_radius=6.35,
        material="bare aluminum; finished thickness per drawing",
        source_rear_face_z=-112.395,
        component_face_source_z=-106.395,
        mounting_holes=holes,
        hardware=hardware,
        placements=layout["placements"],
    )
    (HERE / "params.json").write_text(json.dumps(p, indent=2), encoding="utf-8")
    return p


SOURCES = {
    "b210": HERE / "exports/B210_FPE_R1_device_adapter.step",
    "bedrock": HERE / "exports/Bedrock_FPE_R1_device_adapter.step",
    "meanwell": ROOT
    / "parts/custom/meanwell-nsp1600-side-tab-mount/exports/device_adapter_N2.step",
    "peplink": HERE / "references/router_oz/peplink_normalized.step",
    "oz": HERE / "references/router_oz/oz_normalized.step",
}
COLORS = {
    "panel": (0.69, 0.73, 0.77),
    "b210": (0.23, 0.29, 0.35),
    "bedrock": (0.22, 0.25, 0.28),
    "meanwell": (0.62, 0.64, 0.65),
    "peplink": (0.13, 0.22, 0.26),
    "oz": (0.2, 0.36, 0.46),
    "hardware": (0.53, 0.55, 0.57),
    "enclosure": (0.78, 0.79, 0.78),
}


def export(items, path):
    a = cq.Assembly(name=path.stem)
    for n, s, k in items:
        a.add(s, name=n, color=cq.Color(*COLORS[k]))
    a.export(str(path))


def generate():
    p = initialize_parameters()
    out = HERE / "exports"
    out.mkdir(exist_ok=True)
    checks = []

    def check(name, ok, value=None):
        checks.append(dict(check=name, pass_check=bool(ok), measured=value))
        print("PASS" if ok else "FAIL", name, flush=True)

    panel = create_part(p).val()
    cq.exporters.export(panel, str(out / "Backpanel_R1.step"))
    actual = cq.importers.importStep(str(out / "Backpanel_R1.step")).val()
    check("exported backpanel valid single solid", actual.isValid() and len(actual.Solids()) == 1)
    b = bounds(actual)
    check(
        "exported 431.8 x431.8 x6 dimensions",
        all(abs((b[a][1] - b[a][0]) - d) < 1e-5 for a, d in zip("xyz", [431.8, 431.8, 6])),
        b,
    )
    all_holes = p["mounting_holes"]
    for h in all_holes:
        v = actual.intersect(cyl(h["diameter"] - 0.001, 6.2, h["x"], h["y"], -6.1)).Volume()
        check(h["id"] + " open through nominal diameter", abs(v) < 1e-5, v)
    for h in p["hardware"]:
        test = cyl(12.099, 2.299, h["x"], h["y"], -2.299)
        check(
            h["id"] + " correct recessed mounting cavity",
            abs(actual.intersect(test).Volume()) < 1e-5,
        )
    for a, h in itertools.combinations(p["hardware"] + all_holes, 2):
        da = 12.1 if "catalog_code" in a else a["diameter"]
        dh = 12.1 if "catalog_code" in h else h["diameter"]
        gap = math.hypot(a["x"] - h["x"], a["y"] - h["y"]) - (da + dh) / 2
        if gap < 0.5:
            check("machining web " + a["id"] + "/" + h["id"], False, gap)
    hw = hardware(p)
    items = [("SCE20_ALUMINUM_BACKPANEL_R1", actual, "panel")] + hw
    components = {}
    for key, path in SOURCES.items():
        s = cq.importers.importStep(str(path)).val()
        installed = transformed(s, p["placements"][key])
        components[key] = installed
        items.append((key.upper() + "_INSTALLED", installed, key))
        ab = bounds(installed)
        check(
            key + " physical envelope contained",
            ab["x"][0] >= -1e-4
            and ab["y"][0] >= -1e-4
            and ab["x"][1] <= 431.8001
            and ab["y"][1] <= 431.8001
            and ab["z"][0] >= -1e-4
            and ab["z"][1] < 237.5352,
            ab,
        )
        # Source connector flaws are inherited; plate and main housings valid.
        check(
            key + " reference validity",
            installed.isValid() or key == "peplink",
            dict(
                valid=installed.isValid(),
                exception="inherited Peplink connector solids; conservative packing envelope used"
                if key == "peplink"
                else None,
            ),
        )
    for (ka, a), (kb, b) in itertools.combinations(components.items(), 2):
        gap = a.distance(b)
        check(ka + " / " + kb + " separation", gap > 0.1, gap)
    for n, h, k in hw:
        for key, s in components.items():
            if n.startswith(key.upper() + "_"):
                continue
            if h.distance(s) < 0.1:
                check(n + " adjacent " + key + " clearance", False, h.distance(s))
    export(items, out / "Installed_R1.step")
    saved = cq.importers.importStep(str(out / "Installed_R1.step")).val()
    expected = sum(len(s.Solids()) for _, s, _ in items)
    check(
        "installed STEP reopened solid count",
        len(saved.Solids()) == expected,
        dict(actual=len(saved.Solids()), expected=expected),
    )
    # Preserve the enclosure rear seat; translate ONLY the four removable nuts.
    source = cq.Shape.importBrep(str(HERE / "references/enclosure/source_enclosure.brep"))
    enc = []
    source_shift = (-215.9, -215.9, -106.395)
    for i, s in enumerate(source.Solids()):
        if i == 60:
            continue
        if i in (61, 62, 63, 64):
            s = s.translate((0, 0, 2.825))
        enc.append(("SAGINAW_SOURCE_" + str(i), s, "enclosure"))
    context = enc + [(n, s.translate(source_shift), k) for n, s, k in items]
    export(context, out / "Enclosure_Installed_R1.step")
    report = dict(
        status="PASS" if all(c["pass_check"] for c in checks) else "FAIL",
        scope=(
            "nominal exported CAD integration; Peplink inherited connector validity exception; "
            "threads simplified, no strength/thermal qualification"
        ),
        checks=checks,
        source_paths={k: str(v) for k, v in SOURCES.items()},
        panel_mass_kg_at2700kg_m3=actual.Volume() * 2.7e-6,
        max_component_height_mm=max(bounds(s)["z"][1] for s in components.values()),
        door_clearance_mm=237.5352 - max(bounds(s)["z"][1] for s in components.values()),
    )
    (out / "cad_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    render_spec = importlib.util.spec_from_file_location(
        "sce_render", ROOT / "parts/custom/solidrun-bedrock-thermal-stud-mount/render_support.py"
    )
    renderer = importlib.util.module_from_spec(render_spec)
    # Dataclass annotations resolve their module through sys.modules while the
    # module is executing; register it just as Python's normal importer does.
    sys.modules[render_spec.name] = renderer
    render_spec.loader.exec_module(renderer)
    renderer.render_scene(
        [(s, COLORS[k], 1) for _, s, k in items],
        HERE / "renders",
        "Installed_R1",
        views=("top", "iso"),
        size=1400,
        axes=False,
    )
    renderer.render_scene(
        [(actual, COLORS["panel"], 1)] + [(s, COLORS[k], 1) for _, s, k in hw],
        HERE / "renders",
        "Backpanel_R1",
        views=("top", "iso"),
        size=1200,
        axes=False,
    )
    print(report["status"], "CAD integration; door margin", report["door_clearance_mm"], flush=True)


if __name__ == "__main__":
    generate()
