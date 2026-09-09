"""Isolate stale ArcToMP start cache and compare bounded line fallback."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
data=json.loads((HERE/"thermal_native_paths.json").read_text())
js=r'''// Diagnostic only, one deliberate final Error, no production saves.
var rows=["V4 exact expected bbox -63,-78,82.65,78"];
function n(x){return Math.round(x*1000)/1000;}
function snap(e,label){var b=e.BoundingBox();rows.push(label+":"+n(b[0])+","+n(b[1])+","+n(b[2])+","+n(b[3]));}
'''
js+='\nvar a='+json.dumps(data["contours"]["top"],separators=(",",":"))+';\n'
js+=r'''
function test(label,zeroLine,flushEach,chordLen,allLines){try{
 var e=new DxfContour(label,"",refpoint_file,100,false);e.SetTool(600);
 var lines=0;
 for(var i=0;i<a.paths.length;i++){
  var p=a.paths[i];e.Start(p.start[0],p.start[1]);
  if(zeroLine)e.LineTo(p.start[0],p.start[1]);
  var current=[p.start[0],p.start[1]];
  if(chordLen>0 && p.segments[0].type=="ARC"){
   var s=p.segments[0];var aa=Math.atan2(current[1]-s.center[1],current[0]-s.center[0]);
   var da=s.dir*chordLen/s.radius_mm;
   current=[s.center[0]+s.radius_mm*Math.cos(aa+da),s.center[1]+s.radius_mm*Math.sin(aa+da)];
   e.LineTo(current[0],current[1]);
  }
  for(var j=0;j<p.segments.length;j++){
   var s=p.segments[j];
   if(s.type=="LINE"){e.LineTo(s.end[0],s.end[1]);lines++;}
   else if(allLines){
    var aa=Math.atan2(current[1]-s.center[1],current[0]-s.center[0]);
    var sweep=s.sweep_deg*Math.PI/180;
    var nn=Math.ceil(Math.abs(sweep)/(2*Math.acos(1-0.0003/s.radius_mm)));
    for(var k=1;k<=nn;k++){
     if(k==nn)e.LineTo(s.end[0],s.end[1]);
     else e.LineTo(s.center[0]+s.radius_mm*Math.cos(aa+sweep*k/nn),s.center[1]+s.radius_mm*Math.sin(aa+sweep*k/nn));
     lines++;
    }
   }else e.ArcToMP(s.end[0],s.end[1],s.center[0],s.center[1],s.dir);
   current=s.end;
  }
  e.Finish();if(flushEach)e.SetAsCavity(true);
 }
 e.SetAsCavity(true);snap(e,label+(allLines?" nLines="+lines:""));
}catch(err){rows.push(label+" ERR "+err);}}
test("ZERO_LINE_EXACT",true,false,0,false);
test("FLUSH_EACH_EXACT",false,true,0,false);
test("ZERO_AND_FLUSH_EXACT",true,true,0,false);
test("FIRST_CHORD0005",false,false,.0005,false);
test("FIRST_CHORD002",false,false,.002,false);
test("FIRST_CHORD01",false,false,.01,false);
test("ALL_LINES_SAG0003",false,false,0,true);
rows.push("Arc argument order unchanged; exact data unchanged");
Error(rows.join("\n"));
'''
for path in [HERE.parents[1]/"FPE/SCE20_CONTOUR_PROBE_V4.fpjs",Path("C:/Users/KyleKassen/AppData/Roaming/FrontDesign/Scripts/SCE20_CONTOUR_PROBE_V4.fpjs")]:
    path.write_text(js,encoding="utf-8");print(path)
