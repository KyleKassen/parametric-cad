"""Pass 2: rubber-foot geometry, side-slot rectangles, label overlays, CG proxy."""
import json
import sys
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane

STEP = r"C:/Users/KyleKassen/Documents/Projects/ADRS/CAD/Ettus/Ettus_USRP_B210_Full_Unit.step"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("b210_verify2.json")

wp = cq.importers.importStep(STEP)
shape = wp.val()
solids = wp.solids().vals()
rep = {}

# ---------------------------------------------------------------- rubber feet
# Solids whose bbox bottoms out at y = -4.766
feet = []
for s in solids:
    b = s.BoundingBox()
    if b.ymin < -4.0:
        feet.append({
            "x": [round(b.xmin, 3), round(b.xmax, 3)],
            "y": [round(b.ymin, 3), round(b.ymax, 3)],
            "z": [round(b.zmin, 3), round(b.zmax, 3)],
            "cx": round((b.xmin + b.xmax) / 2, 3),
            "cz": round((b.zmin + b.zmax) / 2, 3),
            "dia_x": round(b.xmax - b.xmin, 3),
            "dia_z": round(b.zmax - b.zmin, 3),
            "height": round(b.ymax - b.ymin, 3),
            "volume": round(s.Volume(), 1),
        })
feet.sort(key=lambda f: (f["cz"], f["cx"]))
rep["rubber_feet_solids"] = feet

# cone faces of the feet (to get the contact flat)
cones = []
for f in shape.Faces():
    s = BRepAdaptor_Surface(f.wrapped)
    if s.GetType() != GeomAbs_Cone:
        continue
    b = f.BoundingBox()
    if b.ymin < -4.0:
        cones.append({"y": [round(b.ymin, 3), round(b.ymax, 3)],
                      "cx": round((b.xmin + b.xmax) / 2, 3),
                      "cz": round((b.zmin + b.zmax) / 2, 3),
                      "dx": round(b.xmax - b.xmin, 3),
                      "half_angle_deg": round(s.Cone().SemiAngle() * 180 / 3.141592653589793, 2)})
rep["foot_cone_faces"] = cones

# the flat contact faces at y = -4.766
flats = []
for f in shape.Faces():
    s = BRepAdaptor_Surface(f.wrapped)
    if s.GetType() != GeomAbs_Plane:
        continue
    b = f.BoundingBox()
    if abs(b.ymin - (-4.766)) < 0.005 and abs(b.ymax - (-4.766)) < 0.005:
        flats.append({"area": round(f.Area(), 2),
                      "cx": round((b.xmin + b.xmax) / 2, 3),
                      "cz": round((b.zmin + b.zmax) / 2, 3),
                      "dx": round(b.xmax - b.xmin, 3)})
flats.sort(key=lambda d: (d["cz"], d["cx"]))
rep["foot_contact_flats_y_-4.766"] = flats

# ------------------------------------------------------- side-wall slot wires
# The single wall face per side has an outer wire and (if a slot exists) an
# inner wire.  Report every wire's bbox.
for lbl, coord in (("left_-X", -2.674), ("right_+X", 119.674)):
    got = []
    for f in shape.Faces():
        s = BRepAdaptor_Surface(f.wrapped)
        if s.GetType() != GeomAbs_Plane:
            continue
        b = f.BoundingBox()
        if abs(b.xmin - coord) > 0.002 or abs(b.xmax - coord) > 0.002:
            continue
        for w in f.Wires():
            wb = w.BoundingBox()
            got.append({"y": [round(wb.ymin, 3), round(wb.ymax, 3)],
                        "z": [round(wb.zmin, 3), round(wb.zmax, 3)],
                        "dy": round(wb.ymax - wb.ymin, 3),
                        "dz": round(wb.zmax - wb.zmin, 3)})
    rep.setdefault("side_wall_wires", {})[lbl] = got

# also the recessed lower band of each side wall
for lbl, coord in (("left_lower_-2.420", -2.420), ("right_lower_119.420", 119.420)):
    g = []
    for f in shape.Faces():
        s = BRepAdaptor_Surface(f.wrapped)
        if s.GetType() != GeomAbs_Plane:
            continue
        b = f.BoundingBox()
        if abs(b.xmin - coord) > 0.002 or abs(b.xmax - coord) > 0.002:
            continue
        if f.Area() < 100:
            continue
        g.append({"area": round(f.Area(), 1),
                  "y": [round(b.ymin, 3), round(b.ymax, 3)],
                  "z": [round(b.zmin, 3), round(b.zmax, 3)]})
    rep.setdefault("side_wall_lower_band", {})[lbl] = g

# ------------------------------------------------- outermost Z (label overlay)
zext = []
for s in solids:
    b = s.BoundingBox()
    zext.append((round(b.zmin, 3), round(b.zmax, 3), round(s.Volume(), 1)))
rep["z_extremes_sorted_min"] = sorted(set(z[0] for z in zext))[:8]
rep["z_extremes_sorted_max"] = sorted(set(z[1] for z in zext))[-8:]

# --------------------------------------------------------------- CG proxy
# Geometric centroid of ALL modelled solids (mass proxy: the case dominates).
c = shape.Center()
rep["geometric_centroid_all_solids"] = [round(c.x, 3), round(c.y, 3), round(c.z, 3)]

# centroid of just the two big case shells
big = sorted(solids, key=lambda s: -s.Volume())[:3]
tot = sum(s.Volume() for s in big)
cx = sum(s.Center().x * s.Volume() for s in big) / tot
cy = sum(s.Center().y * s.Volume() for s in big) / tot
cz = sum(s.Center().z * s.Volume() for s in big) / tot
rep["centroid_three_largest_solids"] = [round(cx, 3), round(cy, 3), round(cz, 3)]

# ------------------------------------------- top-cover stacking dimple depth
dim = []
for f in shape.Faces():
    s = BRepAdaptor_Surface(f.wrapped)
    if s.GetType() != GeomAbs_Plane:
        continue
    b = f.BoundingBox()
    if abs(b.ymin - 31.49) < 0.01 and abs(b.ymax - 31.49) < 0.01:
        dim.append({"area": round(f.Area(), 2),
                    "cx": round((b.xmin + b.xmax) / 2, 3),
                    "cz": round((b.zmin + b.zmax) / 2, 3),
                    "dx": round(b.xmax - b.xmin, 3),
                    "dz": round(b.zmax - b.zmin, 3)})
dim.sort(key=lambda d: (d["cz"], d["cx"]))
rep["top_stacking_dimple_floors_y_31.49"] = dim

OUT.write_text(json.dumps(rep, indent=1))
print(json.dumps(rep, indent=1))
