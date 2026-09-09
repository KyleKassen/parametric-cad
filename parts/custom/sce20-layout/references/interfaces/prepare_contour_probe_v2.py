"""Write diagnostic using one final Error(message), avoiding hidden Print output."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
data=json.loads((HERE/"thermal_native_paths.json").read_text())
js=r'''// Diagnostic only. Final Error intentionally exposes measurements.
var rows=["SCE20 PROBE V2: bbox xmin,ymin,xmax,ymax"];
var owner=new Frontpanel("PROBE_V2_ONLY",6,400,400,alu_raw,elox_natural);
function n(x){return Math.round(x*1000)/1000;}
function info(e,label){try{var b=e.BoundingBox();rows.push(label+": "+n(b[0])+","+n(b[1])+","+n(b[2])+","+n(b[3])+" S="+e.Scale());}catch(err){rows.push(label+" ERR "+err);}}
function fresh(id,omit){if(omit)return new DxfContour(id,"",refpoint_file);return new DxfContour(id,"",refpoint_file,100,false);}
function rect(e){e.Start(-63,-78);e.LineTo(82.65,-78);e.LineTo(82.65,78);e.LineTo(-63,78);e.LineTo(-63,-78);e.Finish();}
function circle(e){e.Start(54,70);e.ArcToMP(50,66,50,70,-1);e.ArcToMP(46,70,50,70,-1);e.ArcToMP(50,74,50,70,-1);e.ArcToMP(54,70,50,70,-1);e.Finish();}
try{
var r=fresh("RECT100",false);rect(r);info(r,"Rect100 local");owner.AddElement(r,83,92);info(r,"Rect100 placed");
var ro=fresh("RECTOMIT",true);rect(ro);info(ro,"Rect omitScale local");
var q=fresh("QEND",false);q.Start(10,20);q.ArcToMP(20,30,10,30,1);q.Finish();info(q,"Arc end-first expected10,20,20,30");
var c=fresh("CIRC",false);circle(c);info(c,"Circle expected46,66,54,74");
var m=fresh("MULTI",false);rect(m);circle(m);info(m,"Rect+circle local");
}catch(err){rows.push("BASIC ERR "+err);}
'''
js+='\nvar a='+json.dumps(data["contours"]["top"],separators=(",",":"))+';\n'
js+=r'''
try{
var e=fresh("ACTUALTOP",false);e.SetTool(600);
for(var i=0;i<a.paths.length;i++){
var p=a.paths[i];e.Start(p.start[0],p.start[1]);
for(var j=0;j<p.segments.length;j++){
var s=p.segments[j];if(s.type=="LINE")e.LineTo(s.end[0],s.end[1]);
else e.ArcToMP(s.end[0],s.end[1],s.center[0],s.center[1],s.dir);
}
e.Finish();info(e,"Top path"+i+" Finish");
}
e.SetAsCavity(true);info(e,"Top cavity beforeAttach");
owner.AddElement(e,83,92);info(e,"Top placed83,92");
e.SetTool(600);e.SetDepth(.05);info(e,"Top depth005");
}catch(err){rows.push("ACTUAL ERR "+err);}
rows.push("END intentionally reported via Error");
Error(rows.join("\n"));
'''
for path in [HERE.parents[1]/"FPE/SCE20_CONTOUR_PROBE_V2.fpjs",Path("C:/Users/KyleKassen/AppData/Roaming/FrontDesign/Scripts/SCE20_CONTOUR_PROBE_V2.fpjs")]:
    path.write_text(js,encoding="utf-8");print(path)
