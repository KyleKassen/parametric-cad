"""DXF topology and 2D cutter accessibility screen; never modifies geometry.

The opening calculation samples analytic arcs at <=0.0002 mm sag and estimates
material left by circular tools. It is not FPD's CAM or supplier qualification.
"""
from pathlib import Path
import collections
import hashlib
import json
import math

import ezdxf
from shapely.geometry import LineString, box
from shapely.ops import polygonize, unary_union

HERE=Path(__file__).resolve().parent
LAYOUT=HERE.parents[1]
results={"units":"mm","cutter_catalog":"C:/Users/KyleKassen/AppData/Local/Programs/FrontDesign/Config/Werkzeug.d/10-Base.ini","installed_Cutter06":{"diameter_mm":.6,"max_plunge_mm":.5,"max_breakthrough_mm":.5,"max_depth_mm":.8},"supplier_sources":["https://www.frontpanelexpress.com/faq","https://docs.frontpanelexpress.com/elements/milling_elements/cavity.html","https://docs.frontpanelexpress.com/elements/milling_elements/free_contour.html"],"caveats":["FAQ states smallest cutter1mm and typical production tolerance0.05..0.10mm; catalog0.6mm is not supplier process acceptance.","No minimum blind-pocket depth found in inspected installed catalog or official cavity page.0.05mm is below catalog maximum but +/-0.01 depth capability is not established.","Free-contour help says multiple paths may split/group on import. Native output must preserve all four fully enclosed circular hardlands plus two lands joined to outer perimeter.","2D offset screen is approximate; native FPD toolpath/actual part controls production."],"thermal_contours":{}}

def sampled(e):
    if e.dxftype()=="LINE": return [(e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y)]
    if e.dxftype() not in {"ARC","CIRCLE"}: raise ValueError(e.dxftype())
    r=e.dxf.radius; cx,cy=e.dxf.center.x,e.dxf.center.y
    a0=math.radians(e.dxf.start_angle) if e.dxftype()=="ARC" else 0
    sweep=(math.radians(e.dxf.end_angle)-a0)%(2*math.pi) if e.dxftype()=="ARC" else 2*math.pi
    n=max(12,math.ceil(sweep/(2*math.acos(1-.0002/r))))
    return [(cx+r*math.cos(a0+sweep*i/n),cy+r*math.sin(a0+sweep*i/n)) for i in range(n+1)]

for side in ("top","bottom"):
    path=LAYOUT/"exports"/("Bedrock_FPE_R1_thermal_"+side+"_contour.dxf")
    ents=list(ezdxf.readfile(path).modelspace())
    lines=[LineString([(round(x,5),round(y,5)) for x,y in sampled(e)]) for e in ents]
    polygons=list(polygonize(unary_union(lines)))
    polygon=max(polygons,key=lambda p:p.area)
    data={"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"entity_counts":dict(collections.Counter(e.dxftype() for e in ents)),"arc_radii_mm":sorted(set(e.dxf.radius for e in ents if e.dxftype()=="ARC")),"circle_radii_mm":sorted(set(e.dxf.radius for e in ents if e.dxftype()=="CIRCLE")),"valid_sampled_polygon":polygon.is_valid,"fully_enclosed_islands":len(polygon.interiors),"sampled_area_mm2":polygon.area,"bounds_mm":polygon.bounds,"groove_R0_25_survives_export":any(abs(e.dxf.radius-.25)<1e-8 for e in ents if e.dxftype()=="ARC"),"cutter_screen":{}}
    # The 0.05 pocket floor meets the 0.4x45 outer bevel at x=82.65.
    stock_section=box(-82.65,-91.65,82.65,91.65)
    outside=box(-110,-120,110,120).difference(stock_section)
    accessible_domain=polygon.union(outside)
    for diameter in (.6,1.0):
        # At exactly 1mm the 1mm-wide slot's centerline has zero area and GEOS
        # drops it. A 0.0001 radial numerical offset retains that machinable
        # centerline; this is an approximate screen, not a tool tolerance.
        radius=diameter/2 if diameter<1 else .4999
        swept=accessible_domain.buffer(-radius,quad_segs=128).buffer(radius,quad_segs=128)
        left=polygon.difference(swept)
        pieces=list(left.geoms) if hasattr(left,"geoms") else [left]
        significant=[p for p in pieces if p.area>.0001]
        data["cutter_screen"][str(diameter)]={"effective_radius_for_numerical_screen_mm":radius,"estimated_uncut_area_mm2":left.area,"significant_patches":[{"area_mm2":p.area,"centroid_mm":[p.centroid.x,p.centroid.y],"bounds_mm":p.bounds} for p in significant]}
    results["thermal_contours"][side]=data
(HERE/"thermal_cutter_audit.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
print(json.dumps(results["thermal_contours"],indent=2))
