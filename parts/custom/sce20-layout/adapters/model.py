"""FPE standard-stock integration revisions using the preserved source builders.

Run with C:/venvs/cadquery/Scripts/python.exe model.py b210|bedrock.
Original components are immutable inputs. Units mm. Plate role declared before
build: two device/panel seating faces and prescribed fastener patterns.
"""
from pathlib import Path
import argparse
import importlib.util
import hashlib
import json
import sys

import cadquery as cq

HERE=Path(__file__).resolve().parent
LAYOUT=HERE.parent
ROOT=LAYOUT.parents[2]
CONFIGS={
    "b210":{"source":"ettus-b210-direct-stud-mount","name":"B210_FPE_R1","old_revision":"D1","changes":{"plate_thickness":4.0,"countersink_diameter_reference":7.1,"screw_head_recess_nominal":.55}},
    "bedrock":{"source":"solidrun-bedrock-thermal-stud-mount","name":"Bedrock_FPE_R1","old_revision":"T1","changes":{"plate_thickness":6.0,"countersink_diameter_reference":9.9,"screw_head_recess_nominal":.95,"underside_countersink_land_diameter":12.0}},
}


def load_file_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def vol(a,b):
    return sum(s.Volume() for s in a.intersect(b).Solids())


def build(key):
    cfg=CONFIGS[key]; name=cfg["name"]
    base=ROOT/"parts/custom"/cfg["source"]
    # Source-specific lib/features.py is used exactly as in the original model.
    sys.path.insert(0,str(base))
    m=load_file_module("source_mount_model",base/"model.py")
    original=m.load_params()
    p=dict(original); p.update(cfg["changes"]); p["revision"]=name+" preliminary standard-stock fit variant"
    params_path=HERE/(name+"_params.json")
    params_path.write_text(json.dumps(p,indent=2),encoding="utf-8")
    stage=Path("C:/tmp/sce_adapters")/name; stage.mkdir(parents=True,exist_ok=True)
    dest=LAYOUT/"exports"; dest.mkdir(parents=True,exist_ok=True)
    shapes=m.load_device(base/"references/input_device.step",p,stage)
    items=m.components(p,shapes)
    items=[(n.replace("adapter_"+cfg["old_revision"],name),s,k) for n,s,k in items]
    plate=items[0][1]
    files={"plate":[items[0]],"assembly":items,"device_adapter":[i for i in items if i[2] in {"plate","device","screw","tim_top"}]}
    reopened={}; checks=[]
    def check(n,ok,value=None,criterion=None):
        checks.append({"check":n,"pass":bool(ok),"measured":value,"criterion":criterion})
        if not ok: print("FAIL",n,value,flush=True)
    for suffix,components in files.items():
        fn=name+"_"+suffix+".step"
        m.export_step(components,stage/fn)
        actual=cq.importers.importStep(str(stage/fn)).val()
        expected=cq.Compound.makeCompound([s for _,s,_ in components])
        check(suffix+" reopened valid/component count",actual.isValid() and len(actual.Solids())==len(components),len(actual.Solids()),len(components))
        ab,eb=m.bbox(actual),m.bbox(expected)
        check(suffix+" reopened mm bounds",all(abs(ab[a][j]-eb[a][j])<1e-4 for a in "xyz" for j in (0,1)),ab,eb)
        check(suffix+" reopened volume",abs(actual.Volume()-expected.Volume())/max(expected.Volume(),1)<1e-5,actual.Volume(),"<10 ppm to source geometry")
        reopened[suffix]=actual
        (dest/fn).write_bytes((stage/fn).read_bytes())
    plate=reopened["plate"]
    device=cq.Compound.makeCompound([s for _,s,k in items if k=="device"])
    fixed=cq.Compound.makeCompound([s for _,s,k in items if k in {"panel","stud"}])
    check("exported plate/device interference",vol(plate,device)<1e-5,vol(plate,device),"<=0.00001 mm3")
    check("source input SHA256 preserved",hashlib.sha256((base/"references/input_device.step").read_bytes()).hexdigest()==p["input_step_sha256"])
    projection=p["screw_length_overall"]+p["screw_head_recess_nominal"]-p["plate_thickness"]
    old_projection=original["screw_length_overall"]+original["screw_head_recess_nominal"]-original["plate_thickness"]
    check("housing screw penetration preserved",abs(projection-old_projection)<1e-9,projection,old_projection)
    throat=p["plate_thickness"]-(p["countersink_diameter_reference"]-p["housing_clearance_diameter"])/2-p["bore_deburr"]
    old_throat=original["plate_thickness"]-(original["countersink_diameter_reference"]-original["housing_clearance_diameter"])/2-original["bore_deburr"]
    check("minimum straight bore throat preserved",abs(throat-old_throat)<1e-9,throat,old_throat)
    stud_above_nut=p["stud_projection"]-p["plate_thickness"]-p["washer_thickness_nominal"]-p["nut_height_nominal"]
    check("stud exits full nominal locknut",stud_above_nut>=1,stud_above_nut,">=1 mm above4mm nut; physical nylon engagement required")
    internal=None
    if key=="b210": internal=cq.Compound.makeCompound([shapes[i].translate((0,0,p["plate_thickness"])) for i in p["device_internal_screw_indices_zero_based"]])
    for n,s,k in items:
        if k not in {"screw","stud","washer","nut"}: continue
        check(n+" vs reopened adapter",vol(s,plate)<1e-5,vol(s,plate))
        if k=="screw":
            check(n+" deliberately recessed head",abs(s.BoundingBox().zmin-p["screw_head_recess_nominal"])<1e-6,s.BoundingBox().zmin,p["screw_head_recess_nominal"])
            if key=="b210":
                check(n+" vs source device",vol(s,device)<1e-5,vol(s,device))
                check(n+" to internal original screws",s.distance(internal)>.5,s.distance(internal),">0.5 mm")
            else:
                x,y=s.Center().x,s.Center().y
                mask=m.cyl(4.5,p["full_diameter_blind_limit_source"],x,y,p["plate_thickness"])
                check(n+" outside expected female-thread zone",vol(s.cut(mask),device)<1e-5,vol(s.cut(mask),device))
                gap=p["plate_thickness"]+3.5-s.BoundingBox().zmax
                check(n+" blind-end tip clearance",gap>=.5-1e-6,gap,">=0.5 mm nominal full-diameter limit")
        else: check(n+" vs source device",vol(s,device)<1e-5,vol(s,device))
    for i,(x,y) in enumerate(m.stud_points(p),1):
        socket=m.cyl(10,p["tool_socket_envelope_height"],x,y,p["plate_thickness"])
        gap=socket.distance(device)
        check("stud socket OD10 clearance "+str(i),gap>.5,gap,">0.5 mm")
    movable=cq.Compound.makeCompound([s for _,s,k in items if k in {"plate","device","screw","tim_top"}])
    for z in (0,.1,1,6,12,13,20):
        overlap=vol(movable.translate((0,0,z)),fixed)
        check("normal lift "+str(z),overlap<1e-5,overlap,"nuts and washers removed")
    # Manufacturing DXFs remain source-frame mm; use only contour layers in FPD.
    m.planar_files(p,stage)
    for f in stage.glob("*.dxf"):
        (dest/(name+"_"+f.name)).write_bytes(f.read_bytes())
    thermal={}
    if key=="bedrock":
        for side in ("top","bottom"):
            field=m.thermal_field(p,side)
            check(side+" field/plate interference",vol(field,plate)<1e-5,vol(field,plate))
            check(side+" thermal pocket depth",abs(field.BoundingBox().zlen-.05)<1e-6,field.BoundingBox().zlen,.05)
            face=max([f for f in field.Faces() if f.geomType()=="PLANE" and abs(f.normalAt().z)>.99],key=lambda f:f.Area())
            planar=cq.Compound.makeCompound(face.Wires()).translate((0,0,-face.Center().z))
            fn=name+"_thermal_"+side+"_contour.dxf"
            cq.exporters.export(planar,str(stage/fn))
            (dest/fn).write_bytes((stage/fn).read_bytes())
            thermal[side]={"nominal_field_area_mm2":field.Volume()/.05,"primary_field_area_mm2":m.thermal_field(p,side,False).Volume()/.05,"depth_mm":.05,"hard_land_diameter_mm":p["tile_contact_land_diameter"] if side=="top" else p["underside_countersink_land_diameter"],"dxf":str(dest/fn)}
    report={"name":name,"status":"PASS" if all(c["pass"] for c in checks) else "FAIL","scope":"nominal CAD only; no thread certification, thermal performance or assembly load rating", "checks":checks,"changes":cfg["changes"],"integration_step":str(dest/(name+"_device_adapter.step")),"bbox_mm":m.bbox(reopened["device_adapter"]),"thermal_fields":thermal,"physical_acceptance":{"screw_projection_mm": [2.4,2.9] if key=="b210" else [2.85,3.0],"minimum_complete_thread_engagement_mm":2,"minimum_actual_tip_gap_mm":.5,"head_recess_nominal_mm":p["screw_head_recess_nominal"],"note":"Gauge actual installed protrusion/complete threads. Original <=0.10 underside recess criterion is intentionally superseded; recess is now functionally deeper to preserve penetration with stock thickness."}}
    (HERE/(name+"_verification.json")).write_text(json.dumps(report,indent=2),encoding="utf-8")
    # Inspect the reopened manufactured adapter, not an unexported builder body.
    render=load_file_module("adapter_render_support",base/"render_support.py")
    render.render_scene([(plate,(.7,.73,.78),1)],HERE/"renders",name,views=("iso","bottom"),size=900,axes=False)
    print(name,report["status"],len(checks),report["bbox_mm"],flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("component",choices=list(CONFIGS));args=parser.parse_args();build(args.component)
