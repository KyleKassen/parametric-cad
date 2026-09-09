"""Convert clean exact bulged polylines to FPD programmatic contour paths."""
from pathlib import Path
import json
import math
import ezdxf

HERE=Path(__file__).resolve().parent
LAYOUT=HERE.parents[1]
data={"units":"mm","reference_point":"refpoint_file","position_on_adapter_fpd_xy":[83,92],"depth_mm":.05,"tool":600,"direction_evidence":{"api":"ArcToMP(endX,endY,centerX,centerY,dir)","positive_one":"counterclockwise","negative_one":"clockwise","installed_example":"C:/Users/KyleKassen/AppData/Local/Programs/FrontDesign/Scripts/Demo/RaspberryPiCase.fpjs","logic":"roundedCorner lines~696..722 assigns dir=halfAngle<0?1:-1. CCW path from(0,r) to(r,0) about(r,r) yields+1. Therefore dir=sign(DXFbulge)."},"contours":{}}
for side in ("top","bottom"):
    path=LAYOUT/"exports"/("Bedrock_FPE_R1_thermal_"+side+"_clean.dxf")
    paths=[]
    for i,e in enumerate(ezdxf.readfile(path).modelspace()):
        assert e.dxftype()=="LWPOLYLINE" and e.closed
        vertices=list(e.get_points("xyb"))
        segments=[]
        for j,(x,y,b) in enumerate(vertices):
            xx,yy,_=vertices[(j+1)%len(vertices)]
            segment={"type":"LINE" if abs(b)<1e-12 else "ARC","end":[float(xx),float(yy)]}
            if b:
                dx,dy=xx-x,yy-y
                factor=(1-b*b)/(4*b)
                cx=(x+xx)/2-dy*factor
                cy=(y+yy)/2+dx*factor
                radius=math.hypot(x-cx,y-cy)
                segment.update({"center":[float(cx),float(cy)],"dir":1 if b>0 else -1,"radius_mm":radius,"sweep_deg":math.degrees(4*math.atan(b)),"source_bulge":float(b)})
                assert abs(radius-math.hypot(xx-cx,yy-cy))<1e-9
            segments.append(segment)
        paths.append({"role":"outer" if i==0 else "uncut_island","start":[float(vertices[0][0]),float(vertices[0][1])],"segments":segments,"close_with_finish":True})
    data["contours"][side]={"id":"THERMAL_"+side.upper(),"native_side":"front" if side=="top" else "reverse","source_local_bbox":[-63,-78,82.65,78],"placed_bbox":[20,14,165.65,170],"paths":paths,"path_count":len(paths),"geometry_changed":False}
dest=HERE/"thermal_native_paths.json"
dest.write_text(json.dumps(data,indent=2),encoding="utf-8")
short=Path("C:/tmp/sce_fpd_thermal_clean/thermal_native_paths.json")
short.write_text(json.dumps(data,indent=2),encoding="utf-8")
helper='''// Programmatic paths avoid native DXF file import. Units mm.
// Direction mapping comes from installed RaspberryPiCase.fpjs roundedCorner.
function buildThermalContour(a) {
  var e = new DxfContour(a.id, "", refpoint_file, 100, false);
  for (var i=0;i<a.paths.length;i++) {
    var p=a.paths[i];
    e.Start(p.start[0],p.start[1]);
    for(var j=0;j<p.segments.length;j++) {
      var s=p.segments[j];
      if(s.type=="LINE") e.LineTo(s.end[0],s.end[1]);
      else e.ArcToMP(s.end[0],s.end[1],s.center[0],s.center[1],s.dir);
    }
    e.Finish();
  }
  e.SetAsCavity(true);
  return e;
}
// Attach to 166x184x6 panel at(83,92), select side and tool600, then depth0.05.
// Native save/reload and island preservation still require verification.
'''
(HERE/"thermal_native_helper.fpjs").write_text(helper,encoding="utf-8")
print(dest)
print(short)
print([(s,len(c["paths"]),sum(len(p["segments"]) for p in c["paths"])) for s,c in data["contours"].items()])
