"""Split exact thermal fields into single-loop native cavity regions.

Splits X=-50,0,50 run through all enclosed island centers. The union is the
original cavity; each resulting contour has no inner wire. This avoids native
FPD multi-path links, while preserving all exact circular edges and hard lands.
"""
from pathlib import Path
import importlib.util
import json
import math
import sys

import cadquery as cq
import ezdxf
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

HERE=Path(__file__).resolve().parent
LAYOUT=HERE.parents[1]
ROOT=LAYOUT.parents[2]
BASE=ROOT/"parts/custom/solidrun-bedrock-thermal-stud-mount"
SHORT=Path("C:/tmp/sce_fpd_thermal_regions");SHORT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(BASE))
spec=importlib.util.spec_from_file_location("bedrock_source",BASE/"model.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=json.loads((LAYOUT/"adapters/Bedrock_FPE_R1_params.json").read_text())


def ivol(a,b):return sum(s.Volume() for s in a.intersect(b).Solids())


def area(v):
    result=0
    for i,(x,y,b) in enumerate(v):
        xx,yy,_=v[(i+1)%len(v)]
        result+=(x*yy-xx*y)/2
        if b:
            theta=4*math.atan(b);radius=math.hypot(xx-x,yy-y)/(2*abs(math.sin(theta/2)))
            result+=radius*radius*(theta-math.sin(theta))/2
    return result


def path_from_dxf(file):
    pending=[]
    for e in ezdxf.readfile(file).modelspace():
        if e.dxftype()=="LINE":pending.append(((e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y),0))
        elif e.dxftype()=="ARC":
            a0=math.radians(e.dxf.start_angle);a1=math.radians(e.dxf.end_angle)
            point=lambda a:(e.dxf.center.x+e.dxf.radius*math.cos(a),e.dxf.center.y+e.dxf.radius*math.sin(a))
            pending.append((point(a0),point(a1),math.tan(((a1-a0)%(2*math.pi))/4)))
        else:raise ValueError("Expected single-loop LINE/ARC, got "+e.dxftype())
    j=next(i for i,e in enumerate(pending) if e[2]==0)
    start,end,b=pending.pop(j);chain=[(*start,b)];cur=end
    while math.dist(cur,start)>1e-6:
        matches=[]
        for i,(a,z,bb) in enumerate(pending):
            if math.dist(cur,a)<1e-6:matches.append((i,a,z,bb))
            if math.dist(cur,z)<1e-6:matches.append((i,z,a,-bb))
        assert len(matches)==1,(cur,matches)
        i,a,z,bb=matches[0];pending.pop(i);chain.append((*cur,bb));cur=z
    assert not pending
    if area(chain)<0:chain=[(chain[j][0],chain[j][1],-chain[(j-1)%len(chain)][2]) for j in range(len(chain)-1,-1,-1)]
    # Start with a straight segment, avoiding any native initial-arc state edge case.
    k=next(i for i,v in enumerate(chain) if v[2]==0)
    chain=chain[k:]+chain[:k]
    segments=[]
    for i,(x,y,b) in enumerate(chain):
        xx,yy,_=chain[(i+1)%len(chain)]
        sg={"type":"LINE" if b==0 else "ARC","end":[xx,yy]}
        if b:
            f=(1-b*b)/(4*b);cx=(x+xx)/2-(yy-y)*f;cy=(y+yy)/2+(xx-x)*f
            sg.update({"center":[cx,cy],"dir":1 if b>0 else -1,"radius_mm":math.hypot(x-cx,y-cy),"sweep_deg":math.degrees(4*math.atan(b))})
        segments.append(sg)
    return chain,{"role":"single_outer_boundary_no_islands","start":[chain[0][0],chain[0][1]],"segments":segments,"close_with_finish":True}


out={"units":"mm","representation_revision":"Bedrock_R2 native single-loop decomposition; physical CAD geometry unchanged from Bedrock_FPE_R1","position_on_adapter_fpd_xy":[83,92],"reference_point":"refpoint_file","depth_mm":.05,"tool":600,"split_x_mm":[-50,0,50],"seams":"Exact shared boundaries, no overlap or additional geometry. Native milling regions union to original thermal field.","native_construction":"One new DxfContour per region; one Start/Finish per object, first segment always LINE; never append another path to the same object.","contours":{}}
checks=[]
for side in ("top","bottom"):
    field=m.thermal_field(p,side)
    face=max([f for f in field.Faces() if f.geomType()=="PLANE" and abs(f.normalAt().z)>.9999],key=lambda f:f.Area())
    face=face.translate((0,0,-face.Center().z))
    volume=cq.Shape.cast(BRepPrimAPI_MakePrism(face.wrapped,gp_Vec(0,0,.05)).Shape())
    assert volume.isValid() and abs(volume.Volume()-face.Area()*.05)<1e-6
    reference_path=SHORT/(side+"_reference_prism.step")
    cq.exporters.export(volume,str(reference_path))
    regions=[];solids=[]
    limits=[-100,-50,0,50,100]
    for i in range(4):
        x0,x1=limits[i],limits[i+1]
        cut=cq.Solid.makeBox(x1-x0,200,2,cq.Vector(x0,-100,-1))
        # Reload independent B-rep copies: OCCT splitting on seam/tangent
        # coordinates can mutate shared input TShapes during boolean work.
        seed=cq.importers.importStep(str(reference_path)).val()
        reg=seed.intersect(cut).clean()
        assert reg.isValid() and len(reg.Solids())==1
        f=max([f for f in reg.Faces() if f.geomType()=="PLANE" and abs(f.normalAt().z)>.9999],key=lambda f:f.Area())
        assert len(f.innerWires())==0,(side,i,len(f.innerWires()))
        flat=cq.Compound.makeCompound(f.Wires()).translate((0,0,-f.Center().z))
        dxf=SHORT/(f"{side}_region_{i+1}.dxf")
        cq.exporters.export(flat,str(dxf))
        vertices,path=path_from_dxf(dxf)
        clean=ezdxf.new("R2010");clean.units=ezdxf.units.MM
        clean.modelspace().add_lwpolyline(vertices,format="xyb",close=True)
        clean.saveas(dxf)
        (LAYOUT/"exports"/(f"Bedrock_R2_{side}_region_{i+1}.dxf")).write_bytes(dxf.read_bytes())
        b=f.BoundingBox();bounds=[b.xmin,b.ymin,b.xmax,b.ymax]
        a=area(vertices)
        assert abs(a-f.Area())<1e-6,(a,f.Area())
        regions.append({"id":f"THERMAL_{side.upper()}_{i+1}","native_side":"front" if side=="top" else "reverse","x":83,"y":92,"depth":.05,"tool":600,"local_bbox":bounds,"bbox":[bounds[0]+83,bounds[1]+92,bounds[2]+83,bounds[3]+92],"paths":[path],"path_count":1,"inner_wire_count":0,"exact_area_mm2":a,"clean_dxf":str(dxf)})
        solids.append(reg)
    union=solids[0]
    for s in solids[1:]:union=union.fuse(s)
    union=union.clean()
    volume=cq.importers.importStep(str(reference_path)).val()
    extra=union.Volume()-ivol(union,volume);missing=volume.Volume()-ivol(union,volume)
    print("PRECHECK",side,"face",face.Area(),"volume",volume.Volume(),"regionVolumes",[s.Volume() for s in solids],"areas",[r["exact_area_mm2"] for r in regions],"union",union.Volume(),"errors",extra,missing,flush=True)
    assert abs(extra)<1e-5 and abs(missing)<1e-5,(extra,missing)
    out["contours"][side]={"regions":regions,"region_count":4,"source_face_area_mm2":face.Area(),"sum_region_area_mm2":sum(r["exact_area_mm2"] for r in regions),"union_extra_mm3":extra,"union_missing_mm3":missing,"union_valid":union.isValid(),"original_inner_wires":len(face.innerWires())}
    print(side,"PASS",face.Area(),sum(r["exact_area_mm2"] for r in regions),"union differences",extra,missing,flush=True)
    cq.exporters.export(union,str(SHORT/(side+"_union.step")))
(HERE/"thermal_single_loop_regions.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
(SHORT/"thermal_single_loop_regions.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(SHORT/"thermal_single_loop_regions.json")
