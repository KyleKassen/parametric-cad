"""A removable open frame preserves lower Bedrock contact and upper router access.

Units mm. Native FPE anchor machining is owned by FPD and is omitted from the
frame reference. The reference is the panel/window/support-hole geometry;
hardware bodies in the optional assembly are labelled catalog envelopes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).absolute().parent
ROOT = HERE.parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.features import Build, rounded_box  # noqa: E402


def load_params() -> dict:
    return json.loads((HERE / "params.json").read_text())


def _build(params: dict | None = None) -> Build:
    p = load_params() if params is None else params
    w, h, t, c = p["width"], p["height"], p["thickness"], p["edge_break"]
    b = Build(
        rounded_box(w, h, t, p["corner_radius"], top_break=c, bottom_break=c), "rounded_stock"
    )
    ww, wh, r = p["window_width"], p["window_height"], p["window_radius"]
    through = rounded_box(ww, wh, t + 2, r, top_break=0, bottom_break=0).translate((0, 0, -1))
    b.boolean(lambda s: s.cut(through), "central_through_window")
    # Each mouth cutter carries its own bevel before the Boolean operation.
    for side, plane in [
        ("upper", cq.Plane(origin=(0, 0, t - c), normal=(0, 0, 1))),
        ("lower", cq.Plane(origin=(0, 0, c), normal=(0, 0, -1))),
    ]:
        mouth = rounded_box(
            ww + 2 * c, wh + 2 * c, t + 2, r + c, bottom_break=c, top_break=0, plane=plane
        )
        b.boolean(lambda s, tool=mouth: s.cut(tool), side + "_window_edge_break")
    for i, (x, y) in enumerate(p["support_points"], 1):
        bore = cq.Solid.makeCylinder(p["support_hole_diameter"] / 2, t + 2, cq.Vector(x, y, -1))
        b.hole(lambda s, tool=bore: s.cut(tool), "support_bore_" + str(i))
    return b


def create_part(params: dict | None = None) -> cq.Workplane:
    return _build(params).result


def build_stages(params: dict | None = None):
    yield from _build(params).stages()


def fpd_input(p: dict) -> dict:
    tx, ty = p["width"] / 2, p["height"] / 2
    elements = [
        {
            "id": "AIR_WINDOW",
            "kind": "rect_hole",
            "x": tx,
            "y": ty,
            "width": p["window_width"],
            "height": p["window_height"],
            "radius": p["window_radius"],
            "bevel_front": p["edge_break"],
            "bevel_reverse": p["edge_break"],
            "side": "front",
        }
    ]
    elements += [
        {
            "id": "SUPPORT_" + str(i),
            "kind": "hole",
            "x": x + tx,
            "y": y + ty,
            "diameter": p["support_hole_diameter"],
            "side": "front",
        }
        for i, (x, y) in enumerate(p["support_points"], 1)
    ]
    a = p["router_native_hardware"]
    elements += [
        {
            "id": "ROUTER_" + str(i),
            "kind": "bolt",
            "x": x + tx,
            "y": y + ty,
            "catalog": a["catalog"],
            "length": a["length"],
            "depth_offset": a["depth_offset"],
            "side": a["side"],
        }
        for i, (x, y) in enumerate(p["router_mount_points"], 1)
    ]
    return {
        "name": p["name"],
        "width": p["width"],
        "height": p["height"],
        "thickness": p["thickness"],
        "radius": p["corner_radius"],
        "bevel": p["edge_break"],
        "material_id": 5,
        "color_id": 1,
        "elements": elements,
        "remark": (
            "Removable Peplink carrier: upper router shifted17mm toward negativeY. "
            "Four WGO40 M4 female LOAD standoffs,6mm,front,zero offset. "
            "Four plainD3.8 support holes. Central146x160R5 through-window;"
            "0.4mm45deg edge breaks on both faces of window and outer rim; bore deburr<=0.1mm. "
            "Fit design requires final alloy/tolerance, hardware/anchor "
            "and operating-temperature acceptance."
        ),
        "datum": {
            "local_to_fpd": [tx, ty],
            "installed_underside_z": p["installed_carrier_underside"],
        },
        "native_notes": [
            "Use new RectHole(id,width,height,radius), "
            "then SetEdgeMachining(bevel_45,0.4,bevel_45,0.4).",
            "Native hardware objects define their own machining; "
            "do not add duplicate ordinary holes or cavities.",
        ],
    }


if __name__ == "__main__":
    params = load_params()
    out = HERE / "exports"
    out.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(create_part(params), str(out / (params["name"] + "_frame.step")))
    (HERE / "fpd_input.json").write_text(json.dumps(fpd_input(params), indent=2), encoding="utf-8")
    print(out / (params["name"] + "_frame.step"))
