"""Normalize exact thermal contour geometry to five closed 2D polylines.

Analytic LINE/ARC geometry and all four circular islands are preserved. No
corner or pocket geometry is changed. All polylines use the original XY datum.
"""
from pathlib import Path
import json
import math
import shutil
import ezdxf

HERE=Path(__file__).resolve().parent
LAYOUT=HERE.parents[1]
SHORT=Path("C:/tmp/sce_fpd_thermal_clean"); SHORT.mkdir(parents=True,exist_ok=True)


def xy_at(e,a):
    return (e.dxf.center.x+e.dxf.radius*math.cos(a),e.dxf.center.y+e.dxf.radius*math.sin(a))


def area(vertices):
    result=0
    for i,(x,y,b) in enumerate(vertices):
        xx,yy,_=vertices[(i+1)%len(vertices)]
        result+=(x*yy-xx*y)/2
        if b:
            theta=4*math.atan(b)
            radius=math.hypot(xx-x,yy-y)/(2*abs(math.sin(theta/2)))
            result+=radius*radius*(theta-math.sin(theta))/2
    return result


report={"units":"mm","geometry_changes":False,"source_origin_preserved":True,"files":{}}
for side in ("top","bottom"):
    src=LAYOUT/"exports"/("Bedrock_FPE_R1_thermal_"+side+"_contour.dxf")
    edges=[]; circles=[]
    for e in ezdxf.readfile(src).modelspace():
        if e.dxftype()=="LINE":
            edges.append(((e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y),0))
        elif e.dxftype()=="ARC":
            a0=math.radians(e.dxf.start_angle); a1=math.radians(e.dxf.end_angle)
            sweep=(a1-a0)%(2*math.pi)
            edges.append((xy_at(e,a0),xy_at(e,a1),math.tan(sweep/4)))
        elif e.dxftype()=="CIRCLE":
            circles.append((e.dxf.center.x,e.dxf.center.y,e.dxf.radius))
        else: raise ValueError(e.dxftype())
    pending=list(edges); chains=[]; gaps=[]
    while pending:
        start,end,b=pending.pop(0); chain=[(*start,b)]; anchor=start; current=end
        while math.dist(current,anchor)>1e-6:
            matches=[]
            for i,(p,q,bb) in enumerate(pending):
                if math.dist(current,p)<1e-6: matches.append((i,p,q,bb))
                if math.dist(current,q)<1e-6: matches.append((i,q,p,-bb))
            assert len(matches)==1,(side,current,matches)
            i,p,q,bb=matches[0]; pending.pop(i)
            gaps.append(math.dist(current,p)); chain.append((*current,bb));current=q
        gaps.append(math.dist(current,anchor))
        if area(chain)<0:
            chain=[(chain[j][0],chain[j][1],-chain[(j-1)%len(chain)][2]) for j in range(len(chain)-1,-1,-1)]
        chains.append(chain)
    assert len(chains)==1
    for cx,cy,r in circles:
        b=-math.tan(math.pi/8)
        chains.append([(cx+r,cy,b),(cx,cy-r,b),(cx-r,cy,b),(cx,cy+r,b)])
    doc=ezdxf.new("R2010")
    doc.units=ezdxf.units.MM
    doc.header["$MEASUREMENT"]=1
    doc.header["$INSBASE"]=(0,0,0)
    for chain in chains: doc.modelspace().add_lwpolyline(chain,format="xyb",close=True)
    filename="bedrock_"+side+"_clean.dxf"
    short=SHORT/filename;doc.saveas(short)
    dest=LAYOUT/"exports"/("Bedrock_FPE_R1_thermal_"+side+"_clean.dxf")
    shutil.copyfile(short,dest)
    check=list(ezdxf.readfile(short).modelspace())
    assert len(check)==5 and all(e.dxftype()=="LWPOLYLINE" and e.closed for e in check)
    report["files"][side]={"short_path":str(short),"workspace_path":str(dest),"closed_polyline_count":len(check),"vertices_per_polyline":[len(e) for e in check],"signed_loop_areas_mm2":[area(v) for v in chains],"net_area_mm2":sum(area(v) for v in chains),"maximum_original_endpoint_gap_mm":max(gaps),"radii_unchanged":True}
(HERE/"clean_thermal_dxf_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
