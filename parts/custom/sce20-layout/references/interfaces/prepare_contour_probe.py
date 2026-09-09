"""Create a bounded FPD diagnostic script; never drives the FPD UI."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/"thermal_native_paths.json").read_text())
js=r'''// Bounded diagnostic only; no production files saved or visible tabs added.
Print("SCE20_CONTOUR_PROBE_BEGIN\n");
var probeOwner=new Frontpanel("CONTOUR_PROBE_ONLY",6,400,400,alu_raw,elox_natural);
function info(e,label) {
  try { Print(label+" B="+e.BoundingBox()+" X="+e.X()+" Y="+e.Y()+" scale="+e.Scale()+" ref="+e.RefPoint()+"\n"); }
  catch(err) { Print(label+" INFO_ERROR "+err+"\n"); }
}
function attach(e,label) {
  info(e,label+" preAttach");
  probeOwner.AddElement(e,83,92);
  info(e,label+" postAttach83_92");
}
function construct(id,omitScale) {
  if(omitScale) return new DxfContour(id,"",refpoint_file);
  return new DxfContour(id,"",refpoint_file,100,false);
}
function rect(e) {
  e.Start(-63,-78);e.LineTo(82.65,-78);e.LineTo(82.65,78);e.LineTo(-63,78);e.LineTo(-63,-78);e.Finish();
}
function circle(e,tag) {
  e.Start(54,70);
  e.ArcToMP(50,66,50,70,-1);info(e,tag+" arc1");
  e.ArcToMP(46,70,50,70,-1);info(e,tag+" arc2");
  e.ArcToMP(50,74,50,70,-1);info(e,tag+" arc3");
  e.ArcToMP(54,70,50,70,-1);info(e,tag+" arc4");
  e.Finish();info(e,tag+" Finish");
}
try {
 var r=construct("RECT_EXPLICIT100",false);rect(r);attach(r,"RECT_EXPLICIT100");
 var ro=construct("RECT_OMIT_SCALE",true);rect(ro);attach(ro,"RECT_OMIT_SCALE");
 var q=construct("QUARTER_ENDPOINT_FIRST",false);
 q.Start(10,20);q.ArcToMP(20,30,10,30,1);q.Finish();attach(q,"QUARTER_ENDPOINT_FIRST expectedLocal10_20_20_30");
 var c=construct("CIRCLE_OFFSET",false);circle(c,"CIRCLE_OFFSET expectedLocal46_66_54_74");attach(c,"CIRCLE_OFFSET");
 var m=construct("RECT_PLUS_CIRCLE",false);rect(m);info(m,"MULTIPATH outerFinish");circle(m,"MULTIPATH inner");attach(m,"RECT_PLUS_CIRCLE");
} catch(err) { Print("BASIC_PROBE_ERROR "+err+"\n"); }
'''
js+='\nvar actualTop='+json.dumps(data["contours"]["top"],separators=(",",":"))+';\n'
js+=r'''
try {
 var e=construct("ACTUAL_TOP_EXPLICIT100",false);
 e.SetTool(cutter_0_6mm);
 info(e,"ACTUAL initial");
 for(var i=0;i<actualTop.paths.length;i++) {
   var p=actualTop.paths[i];
   Print("ACTUAL path="+i+" start="+p.start+"\n");
   e.Start(p.start[0],p.start[1]);
   for(var j=0;j<p.segments.length;j++) {
     var s=p.segments[j];
     if(s.type=="LINE") e.LineTo(s.end[0],s.end[1]);
     else {
       e.ArcToMP(s.end[0],s.end[1],s.center[0],s.center[1],s.dir);
       Print("ACTUAL p"+i+" s"+j+" ARC end="+s.end+" center="+s.center+" dir="+s.dir+"\n");
       info(e,"ACTUAL p"+i+" s"+j);
     }
   }
   e.Finish();info(e,"ACTUAL path"+i+" Finish");
 }
 e.SetAsCavity(true);info(e,"ACTUAL SetAsCavity");
 attach(e,"ACTUAL");
 e.SetTool(cutter_0_6mm);e.SetDepth(.05);info(e,"ACTUAL final depth005");
} catch(err) {Print("ACTUAL_PROBE_ERROR "+err+"\n");}
Print("SCE20_CONTOUR_PROBE_END\n");
'''
paths=[LAYOUT for LAYOUT in [HERE.parents[1]/"FPE/SCE20_CONTOUR_PROBE.fpjs",Path("C:/Users/KyleKassen/AppData/Roaming/FrontDesign/Scripts/SCE20_CONTOUR_PROBE.fpjs")]]
for path in paths:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(js,encoding="utf-8")
    print(path)
