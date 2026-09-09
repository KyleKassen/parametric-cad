"""Consolidate source profiles and standard-stock overlays for native FPD use."""
from copy import deepcopy
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
LAYOUT=HERE.parents[1]
source=json.loads((HERE/"mount_interfaces.json").read_text())
out={"units":"mm","scope":"Exact nominal feature specification; native FPD save/reload and supplier special-process acceptance remain required","panels":{}}
for key in ("b210","meanwell","bedrock"):
    old=source["components"][key]
    adapter=deepcopy(old["adapter"])
    if key=="meanwell":
        name="MeanWell_N2"
        params_path=LAYOUT.parents[0]/"meanwell-nsp1600-side-tab-mount/params.json"
    else:
        name="B210_FPE_R1" if key=="b210" else "Bedrock_FPE_R1"
        params_path=LAYOUT/"adapters"/(name+"_params.json")
    p=json.loads(params_path.read_text())
    adapter["thickness_mm"]=p["plate_thickness"]
    csk=adapter["housing_holes"]["countersink"]
    csk["mouth_diameter_mm"]=p["countersink_diameter_reference"]
    csk["depth_mm"]=(p["countersink_diameter_reference"]-p["housing_clearance_diameter"])/2
    csk["depth_mm_definition"]="Geometric cone height, NOT FPD SinkDepth/additional axial recess"
    csk["fpd_sink_depth_additional_recess_mm"]=0
    adapter["countersunk_screw_head_recess_nominal_mm"]=p["screw_head_recess_nominal"]
    adapter["screw_projection_nominal_mm"]=p["screw_length_overall"]+p["screw_head_recess_nominal"]-p["plate_thickness"]
    adapter["no_panel_studs_on_this_adapter"]=True
    adapter["feature_side_convention"]="Designate upper/device side FPD front; underside/backpanel contact side reverse. All coordinates use same XY, no extra mirror."
    if key=="bedrock":
        adapter["thermal_fields"]["underside_hard_land_diameter_mm"]=12
        for side in ("top","bottom"):
            adapter["thermal_fields"]["source_"+side+"_contour_dxf"]=str(LAYOUT/"exports"/(name+"_thermal_"+side+"_contour.dxf"))
    if key!="meanwell":
        adapter["source_planar_dxf"]=str(LAYOUT/"exports"/(name+"_plate_profile_mm.dxf"))
    out["panels"][name]={"component":key,"params_file":str(params_path),"adapter":adapter,"native_hardware_count":0,"countersink_face":"reverse","catalog_holes":"ordinary through clearance bores; device countersinks reverse only","manufacturing_remarks":"Preliminary fit prototype. Actual finished stock thickness +/-0.05 and conical seating must meet screw projection acceptance. No physical qualification implied. Aluminum alloy, finish, tolerances and any 0.05mm thermal pockets require supplier capability confirmation."}
(HERE/"fpd_adapter_specs.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print("Wrote",HERE/"fpd_adapter_specs.json")
