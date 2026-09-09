"""Read-only audit of D1/N2/T1 into enclosure integration data; run from repo root.

CAD uses each adapter's existing frame. New backpanel FPD XY = translation +
rotation * local XY. Z=0 is the component-facing backpanel seating surface.
This file never edits the supplied component designs.
"""
from pathlib import Path
import configparser
import hashlib
import json
import math
import shutil
import tempfile

import cadquery as cq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PARTS = ROOT / "parts/custom"
NAMES = {
    "b210": ("ettus-b210-direct-stud-mount", "D1"),
    "meanwell": ("meanwell-nsp1600-side-tab-mount", "N2"),
    "bedrock": ("solidrun-bedrock-thermal-stud-mount", "T1"),
}


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(shape):
    bb = shape.BoundingBox()
    return {a: [round(getattr(bb, a + "min"), 7), round(getattr(bb, a + "max"), 7)] for a in "xyz"}


def union_bbox(entries):
    return {a: [min(e["bbox_mm"][a][0] for e in entries), max(e["bbox_mm"][a][1] for e in entries)] for a in "xyz"}


def filleted_outline(vertices, r):
    result = []
    for i, (x, y) in enumerate(vertices):
        prev, nxt = vertices[i-1], vertices[(i+1) % len(vertices)]
        ll, rr = math.dist((x,y), prev), math.dist((x,y), nxt)
        u = ((x-prev[0])/ll, (y-prev[1])/ll)
        v = ((nxt[0]-x)/rr, (nxt[1]-y)/rr)
        turn = u[0]*v[1]-u[1]*v[0]
        result += [[x-u[0]*r, y-u[1]*r, turn*math.tan(math.pi/8)], [x+v[0]*r, y+v[1]*r, 0]]
    return result


def meanwell_outline(p):
    a,w,h = p["spine_width"]/2,p["plate_width"]/2,p["tab_length"]/2
    rear,front = p["tab_stations_y"]
    low,high = p["plate_fan_end_y"],p["plate_terminal_end_y"]
    v = [(-a,low),(a,low),(a,rear-h),(w,rear-h),(w,rear+h),(a,rear+h),(a,front-h),(w,front-h),(w,high),(-w,high),(-w,front-h),(-a,front-h),(-a,rear+h),(-w,rear+h),(-w,rear-h),(-a,rear-h)]
    return {"type":"closed_xy_bulge_polyline", "vertices_before_fillet":v, "vertices_xyb":filleted_outline(v,p["corner_radius"]),"corner_radius_mm":p["corner_radius"]}


def main():
    result = {"units":"mm", "date":"2026-09-08", "scope":"Integration audit of existing unreleased prototypes; no source modification or physical qualification", "transform":"panel XY = translation_xy + Rz(rotation_deg) * local XY; adapter underside Z0 touches new component-facing backpanel Z0. All selected STEP assemblies already normalized; do not apply vendor normalize transform again.", "components":{}}
    for key,(folder,rev) in NAMES.items():
        base=PARTS/folder
        p=json.loads((base/"params.json").read_text())
        meta=json.loads((base/"exports/cad_build_metadata.json").read_text())
        center=(p["stud_pattern_center_x"],p["stud_pattern_center_y"])
        a=math.radians(p["stud_pattern_rotation_deg"])
        pts=[[sx*p["stud_pitch_x"]/2*math.cos(a)-sy*p["stud_pitch_y"]/2*math.sin(a)+center[0],sx*p["stud_pitch_x"]/2*math.sin(a)+sy*p["stud_pitch_y"]/2*math.cos(a)+center[1]] for sx in (-1,1) for sy in (-1,1)]
        holes=p.get("housing_points",[[sx*p.get("housing_pitch_x",0)/2,sy*p.get("housing_pitch_y",0)/2] for sx in (-1,1) for sy in (-1,1)])
        selected=base/f"exports/device_adapter_{rev}.step"
        plate=base/f"exports/plate_{rev}.step"
        with tempfile.TemporaryDirectory(prefix="sce_interface_",dir="C:/tmp") as td:
            measurements={}
            for name,src in [("device_adapter",selected),("plate",plate)]:
                staged=Path(td)/f"{name}.step"
                shutil.copyfile(src,staged)
                shape=cq.importers.importStep(str(staged)).val()
                measurements[name]={"bbox_mm":bbox(shape),"solid_count":len(shape.Solids()),"valid":shape.isValid(),"volume_mm3":shape.Volume(),"sha256":hash_file(src)}
            if key=="bedrock":
                src=base/"references/geometry/single_60W_bank_CLIPPED_REFERENCE.step"
                staged=Path(td)/"fin.step"; shutil.copyfile(src,staged)
                fin=cq.importers.importStep(str(staged)).val()
                measurements["fin_bank_large_planar_faces"]=[{"area_mm2":f.Area(),"bbox_mm":bbox(f),"normal":f.normalAt().toTuple()} for f in sorted([f for f in fin.Faces() if f.geomType()=="PLANE"],key=lambda f:f.Area(),reverse=True)[:10]]
        relative=lambda x:str(x.relative_to(ROOT)).replace("\\","/")
        d={"source_directory":relative(base),"revision":rev,"source_params_sha256":hash_file(base/"params.json"),"source_model_sha256":hash_file(base/"model.py"),"current_assembly_with_reference_coupon":relative(base/f"exports/assembled_device_mount_{rev}.step"),"integration_step":relative(selected),"plate_step":relative(plate),"integration_step_scope":"adapter, device, housing screws; does not include the reference main panel, panel studs, washers or nuts; add final panel hardware separately", "fresh_reopen":measurements, "device_bbox_from_existing_build_metadata_mm":union_bbox([e for e in meta["components"] if e["kind"]=="device"]),"assembly_excluding_reference_panel_bbox_mm":union_bbox([e for e in meta["components"] if e["kind"]!="panel"]),"backpanel_studs":{"catalog":"WGU30","native_kind":"M3 male load stud","length_mm":12,"native_side_convention":"original support coupon uses reverse side; new backpanel may designate either face consistently, no additional XY mirror", "depth_offset_mm":0,"qty":4,"local_xy_mm":pts,"pitch_xy_mm":[p["stud_pitch_x"],p["stud_pitch_y"]],"base_and_adhesive_seating":"flush or below component-facing supporting panel surface", "do_not_add_ordinary_holes_or_pockets_under_native_studs":True},"adapter":{"width_mm":p["plate_width"],"height_mm":p["plate_length"],"thickness_mm":p["plate_thickness"],"thickness_tolerance_mm":p["plate_thickness_tolerance"],"outline":meanwell_outline(p) if key=="meanwell" else {"type":"centered_rounded_rectangle","corner_radius_mm":p["corner_radius"]},"local_to_adapter_fpd_translation_mm":[p["plate_width"]/2,300.6 if key=="meanwell" else p["plate_length"]/2],"edge_bevel_both_faces_mm":p["edge_break"],"stud_clearance_holes":{"diameter_mm":p["stud_clearance_diameter"],"local_xy_mm":pts},"housing_holes":{"diameter_mm":p["housing_clearance_diameter"],"local_xy_mm":holes,"countersink":{"face":"underside contacting backpanel","included_angle_deg":90,"mouth_diameter_mm":p["countersink_diameter_reference"],"depth_mm":(p["countersink_diameter_reference"]-p["housing_clearance_diameter"])/2},"opposite_bore_deburr_max_mm":p["bore_deburr"]},"source_material_finish":"6061-T6/T651, clear MIL-DTL-5541 Type II Class 3 conversion, dims after finish; supplier material/process capability must be explicitly resolved for FPE", "source_planar_dxf":relative(base/"exports/plate_profile_mm.dxf")},"service":{"socket_od_max_mm":10,"socket_approach_height_mm":p["tool_socket_envelope_height"],"normal_lift_min_mm":p.get("service_lift_min",20)},"housing_screw":{"thread":f'M{p["screw_diameter"]:g}',"pitch_mm":p["screw_pitch"],"overall_length_mm":p["screw_length_overall"],"head_recess_nominal_mm":p["screw_head_recess_nominal"],"nominal_projection_mm":p["screw_length_overall"]+p["screw_head_recess_nominal"]-p["plate_thickness"]},"external_panel_hardware":{"washers":{"part":"McMaster 98688A142","qty":4,"ID_mm":3.2,"OD_mm":7,"nominal_thickness_mm":.55},"nuts":{"part":"McMaster 90576A102","qty":4,"type":"M3 nylon insert locknut","height_mm":4,"across_flats_mm":5.5}}}
        if key=="b210":
            d["reservations"]=[{"name":"RF end cable planning","bbox_mm":{"x":[-55,55],"y":[80,140],"z":[9.9,41.9]}},{"name":"USB/DC/reference cable planning","bbox_mm":{"x":[-55,55],"y":[-140,-80],"z":[9.9,41.9]}}]
            d["orientation_note"]="Original design initial orientation plate-facing-up; vertical enclosure installation needs application load qualification. No geometric restriction to in-plane rotation."
            d["manufacturing_note"]="Existing F1.fpd is a 180x200x6 support coupon, NOT the 150x148x3.5 D1 adapter. Preserve 3.5 thickness or redesign short housing-screw stack."
        elif key=="meanwell":
            d["reservations"]=[{"name":"terminal/intake planning","bbox_mm":{"x":[-20.5,20.5],"y":[0,100],"z":[6,91]}},{"name":"fan/exhaust planning","bbox_mm":{"x":[-20.5,20.5],"y":[-400.6,-300.6],"z":[6,91]}}]
            d["orientation_note"]="Already side-mounted on manufacturer original +X narrow side. Rotating in panel plane changes fan/terminal direction. Original airflow 500.6 overall reservation cannot fit within <500.6 clear dimension when axial; enclosure open volume may exceed subpanel bounds. Side orientation output derating remains unresolved."
            d["manufacturing_note"]="Preserve 6.0 thickness, local-tab R4 contour and underside 8.1 countersinks. Rear M4 source thread absent; actual feature must be verified. Existing conservative countersink-seat strength screen is HOLD."
        else:
            d["reservations"]=[{"name":"IO side cable planning","bbox_mm":{"x":[-117.96,-67.96],"y":[-75,75],"z":[5.1,50.1]}},{"name":"SMA end cable planning","bbox_mm":{"x":[-58,58],"y":[90,140],"z":[5.1,50.1]}}]
            d["orientation_note"]="Original vertical-fin installation rotates assembly about X+90 so local +Y becomes vertical. Preserve fin channels along backpanel vertical (local Y); rotation 0 or 180 deg about panel normal. Device is derived Tile + one clipped fin bank reference, not proven vendor configuration."
            d["adapter"]["thermal_fields"]={"both_faces":True,"field_width_mm":126,"field_height_mm":156,"corner_radius_mm":5,"depth_mm":.05,"depth_tolerance_mm":.01,"hard_lands_local_xy_mm":holes,"top_hard_land_diameter_mm":8,"underside_hard_land_diameter_mm":10,"escape_grooves":{"y_mm":[-20,20],"x_start_mm":62,"x_end_mm":84,"width_mm":1,"corner_radius_mm":.25,"depth_mm":.05,"clip_to_actual_stock":True},"source_top_contour_dxf":relative(base/"exports/thermal_top_pocket_contour_mm.dxf"),"source_bottom_contour_dxf":relative(base/"exports/thermal_bottom_pocket_contour_mm.dxf"),"Ra_max_um":1.6,"assembled_gap_max_mm":.1}
            d["manufacturing_note"]="5.10 +/- .05 stock and 0.050 +/- .010 thermal recesses with islands/grooves on BOTH faces are function-critical. A generic 5/6 mm plate or plain through-hole FPD is not an equivalent adapter. FPE capability acceptance needed; retain exact nominal geometry and explicit remarks."
        result["components"][key]=d
        print(key,measurements["device_adapter"],flush=True)
    catalog=Path("C:/Users/KyleKassen/AppData/Local/Programs/FrontDesign/Config/Bolt.d/10-Base.ini")
    text=catalog.read_text(encoding="utf-8-sig")
    section=text.split("[Bolt:WGU30]",1)[1].split("[",1)[0].strip()
    result["installed_catalog_evidence"]={"path":str(catalog),"sha256":hash_file(catalog),"WGU30_section":section,"dimension_units":"0.001 mm; native API mm","note":"Name=M3 ThreadSize=3000 PlateDiameter=12100 Lengths include12000, load type WGLSU; native properties confirmation remains root execution responsibility."}
    (HERE/"mount_interfaces.json").write_text(json.dumps(result,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
