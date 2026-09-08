"""Independent re-verification of every B210 claim this mount design relies on."""
import json
import sys
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

STEP = r"C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/Ettus/Ettus_USRP_B210_Full_Unit.step"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("b210_verify.json")

print("importing STEP ...", flush=True)
wp = cq.importers.importStep(STEP)
shape = wp.val()
solids = wp.solids().vals()
print("  %d solids" % len(solids), flush=True)

bb = shape.BoundingBox()
report = {
    "source": STEP,
    "solid_count": len(solids),
    "bbox": {
        "xmin": round(bb.xmin, 3), "xmax": round(bb.xmax, 3),
        "ymin": round(bb.ymin, 3), "ymax": round(bb.ymax, 3),
        "zmin": round(bb.zmin, 3), "zmax": round(bb.zmax, 3),
    },
}

# ---------------------------------------------------------------- planar faces
planes = []
faces = shape.Faces()
print("  %d faces" % len(faces), flush=True)
for f in faces:
    s = BRepAdaptor_Surface(f.wrapped)
    if s.GetType() != GeomAbs_Plane:
        continue
    n = f.normalAt()
    v = (n.x, n.y, n.z)
    i = max(range(3), key=lambda k: abs(v[k]))
    if abs(v[i]) < 0.999:
        continue
    fb = f.BoundingBox()
    coord = (fb.xmin, fb.ymin, fb.zmin)[i]
    planes.append({
        "axis": "XYZ"[i], "sign": 1 if v[i] > 0 else -1,
        "coord": round(coord, 3), "area": f.Area(),
        "bb": (fb.xmin, fb.xmax, fb.ymin, fb.ymax, fb.zmin, fb.zmax),
    })


def plane_group(axis, coord, tol=0.002):
    g = [p for p in planes if p["axis"] == axis and abs(p["coord"] - coord) < tol]
    if not g:
        return None
    return {
        "n_faces": len(g),
        "total_area": round(sum(p["area"] for p in g), 1),
        "extent_x": [round(min(p["bb"][0] for p in g), 3), round(max(p["bb"][1] for p in g), 3)],
        "extent_y": [round(min(p["bb"][2] for p in g), 3), round(max(p["bb"][3] for p in g), 3)],
        "extent_z": [round(min(p["bb"][4] for p in g), 3), round(max(p["bb"][5] for p in g), 3)],
    }


report["planes_of_interest"] = {
    "bottom_pan_outer_Y_-1.210": plane_group("Y", -1.210),
    "top_cover_outer_Y_32.490": plane_group("Y", 32.490),
    "front_panel_outer_Z_0.914": plane_group("Z", 0.914),
    "rear_panel_outer_Z_-156.460": plane_group("Z", -156.460),
    "left_wall_X_-2.674": plane_group("X", -2.674),
    "right_wall_X_119.674": plane_group("X", 119.674),
}

ylevels = {}
for p in planes:
    if p["axis"] == "Y" and p["sign"] < 0:
        k = round(p["coord"], 3)
        ylevels[k] = ylevels.get(k, 0.0) + p["area"]
report["minus_Y_facing_plane_levels"] = sorted(
    [{"y": k, "area": round(v, 1)} for k, v in ylevels.items() if v > 20],
    key=lambda d: d["y"])[:12]

# ------------------------------------------------------------- cylinders
cyl = []
for f in faces:
    s = BRepAdaptor_Surface(f.wrapped)
    if s.GetType() != GeomAbs_Cylinder:
        continue
    c = s.Cylinder()
    ax = c.Axis()
    d = ax.Direction()
    loc = ax.Location()
    dv = (d.X(), d.Y(), d.Z())
    i = max(range(3), key=lambda k: abs(dv[k]))
    if abs(dv[i]) < 0.99:
        continue
    fb = f.BoundingBox()
    cyl.append({
        "axis": "XYZ"[i], "r": c.Radius(),
        "loc": (loc.X(), loc.Y(), loc.Z()),
        "bb": (fb.xmin, fb.xmax, fb.ymin, fb.ymax, fb.zmin, fb.zmax),
    })


def near(a, b, t=0.05):
    return abs(a - b) < t


bores = []
for c in cyl:
    if c["axis"] != "Y" or not near(c["r"], 1.5, 0.06):
        continue
    if c["bb"][2] < -1.0:
        bores.append({
            "dia": round(2 * c["r"], 4),
            "x": round(c["loc"][0], 3), "z": round(c["loc"][2], 3),
            "y_from": round(c["bb"][2], 3), "y_to": round(c["bb"][3], 3),
        })
bores.sort(key=lambda b: (b["z"], b["x"]))
report["bottom_M3_bores_dia3"] = bores

upper = [{"dia": round(2 * c["r"], 4), "x": round(c["loc"][0], 3), "z": round(c["loc"][2], 3),
          "y_from": round(c["bb"][2], 3), "y_to": round(c["bb"][3], 3)}
         for c in cyl if c["axis"] == "Y" and near(c["r"], 1.6, 0.03)
         and 3.0 < c["bb"][2] < 6.0]
upper.sort(key=lambda b: (b["z"], b["x"]))
report["bottom_bores_upper_dia3p2"] = upper

sheet = [{"dia": round(2 * c["r"], 4), "x": round(c["loc"][0], 3), "z": round(c["loc"][2], 3),
          "y_from": round(c["bb"][2], 3), "y_to": round(c["bb"][3], 3)}
         for c in cyl if c["axis"] == "Y" and near(c["r"], 2.0955, 0.05)]
sheet.sort(key=lambda b: (b["z"], b["x"]))
report["bottom_sheet_openings"] = sheet

feet = [{"dia": round(2 * c["r"], 3), "x": round(c["loc"][0], 3), "z": round(c["loc"][2], 3),
         "y_from": round(c["bb"][2], 3), "y_to": round(c["bb"][3], 3)}
        for c in cyl if c["axis"] == "Y" and near(c["r"], 6.35, 0.05)]
feet.sort(key=lambda b: (b["z"], b["x"]))
report["rubber_feet"] = feet

# ------------------------------- what limits screw penetration into each bore
limits = []
for b in bores:
    px, pz = b["x"], b["z"]
    best = None
    for sol in solids:
        sb = sol.BoundingBox()
        if not (sb.xmin - 0.2 <= px <= sb.xmax + 0.2 and sb.zmin - 0.2 <= pz <= sb.zmax + 0.2):
            continue
        if sb.ymin < 0.5 or sb.ymin > 9.0:
            continue
        hit = None
        y = max(sb.ymin, 0.0) + 1e-3
        while y < min(sb.ymax, 12.0):
            if sol.isInside(cq.Vector(px, y, pz), 1e-4):
                hit = y
                break
            y += 0.02
        if hit is not None and (best is None or hit < best[0]):
            best = (round(hit, 3), round(sb.ymin, 3), round(sb.ymax, 3), round(sol.Volume(), 1))
    limits.append({
        "x": px, "z": pz,
        "first_material_on_axis_y": best[0] if best else None,
        "obstructing_solid_ybox": [best[1], best[2]] if best else None,
        "obstructing_solid_volume": best[3] if best else None,
        "free_depth_from_outer_face_mm": round(best[0] + 1.210, 3) if best else None,
    })
report["screw_penetration_limits"] = limits

# ------------------------------------------------------------ side-wall slots
# A through-slot shows up as a gap in the wall plane; find wall-plane faces whose
# inner boundary brackets Y 15..18, and report the wall face bboxes directly.
for lbl, axis, coord in (("left_-X", "X", -2.674), ("right_+X", "X", 119.674)):
    g = [p for p in planes if p["axis"] == axis and abs(p["coord"] - coord) < 0.002]
    report.setdefault("wall_faces", {})[lbl] = [
        {"area": round(p["area"], 1),
         "y": [round(p["bb"][2], 3), round(p["bb"][3], 3)],
         "z": [round(p["bb"][4], 3), round(p["bb"][5], 3)]} for p in g]

# ------------------------------------------------- connector protrusion extremes
zmin_solid = min(solids, key=lambda s: s.BoundingBox().zmin)
zmax_solid = max(solids, key=lambda s: s.BoundingBox().zmax)
report["extremes"] = {
    "most_negative_Z_solid": {"zmin": round(zmin_solid.BoundingBox().zmin, 3),
                              "vol": round(zmin_solid.Volume(), 1)},
    "most_positive_Z_solid": {"zmax": round(zmax_solid.BoundingBox().zmax, 3),
                              "vol": round(zmax_solid.Volume(), 1)},
}

# bare sheet-metal envelope: ignore solids that are only feet or only protruding
# connector bodies, by taking the union bbox of solids that touch Y in [-1.3, 32.6]
xs, ys, zs = [], [], []
for sol in solids:
    sb = sol.BoundingBox()
    if sb.ymin < -1.3:
        continue
    xs += [sb.xmin, sb.xmax]
    ys += [sb.ymin, sb.ymax]
    zs += [sb.zmin, sb.zmax]
report["envelope_excluding_feet"] = {
    "x": [round(min(xs), 3), round(max(xs), 3)],
    "y": [round(min(ys), 3), round(max(ys), 3)],
    "z": [round(min(zs), 3), round(max(zs), 3)],
}

# total mass estimate is not derivable; report material volume of the case parts
report["total_modelled_volume_mm3"] = round(sum(s.Volume() for s in solids), 1)

OUT.write_text(json.dumps(report, indent=1))
print(json.dumps(report, indent=1))
print("\n-> %s" % OUT)
