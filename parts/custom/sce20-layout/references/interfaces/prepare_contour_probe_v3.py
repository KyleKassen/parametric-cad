"""Force native bbox computation for path/arc/import isolation."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
data=json.loads((HERE/"thermal_native_paths.json").read_text())
js=r'''// Diagnostic; final Error exposes all results; no files saved.
var rows=["V3 LOCAL BOUNDS after SetAsCavity (no placement)"];
function n(x){return Math.round(x*1000)/1000;}
function info(e,label){var b=e.BoundingBox();rows.push(label+":"+n(b[0])+","+n(b[1])+","+n(b[2])+","+n(b[3])+" S"+e.Scale());}
function fresh(id){return new DxfContour(id,"",refpoint_file,100,false);}
function arc(e,s,mode){
 if(mode==1)e.ArcToMP(s.end[0],s.center[0],s.end[1],s.center[1],s.dir);
 else if(mode==2)e.ArcToMP(s.center[0],s.center[1],s.end[0],s.end[1],s.dir);
 else e.ArcToMP(s.end[0],s.end[1],s.center[0],s.center[1],s.dir);
}
function paths(id,pp,mode,oneFinish){
 try{var e=fresh(id);e.SetTool(600);
 for(var i=0;i<pp.length;i++){var p=pp[i];e.Start(p.start[0],p.start[1]);
 for(var j=0;j<p.segments.length;j++){var s=p.segments[j];if(s.type=="LINE")e.LineTo(s.end[0],s.end[1]);else arc(e,s,mode);}
 if(!oneFinish)e.Finish();}
 if(oneFinish)e.Finish();e.SetAsCavity(true);info(e,id);
 }catch(err){rows.push(id+" ERR "+err);}
}
'''
js+='\nvar actual='+json.dumps(data["contours"]["top"],separators=(",",":"))+';\n'
js+=r'''
var quarter={start:[10,20],segments:[{type:"ARC",end:[20,30],center:[10,30],dir:1}]};
paths("Q_EP_expect10,20,20,30",[quarter],0,false);
paths("Q_INTERLEAVE",[quarter],1,false);
paths("Q_CENTERFIRST",[quarter],2,false);
paths("C_EP_expect46,66,54,74",[actual.paths[4]],0,false);
paths("C_INTERLEAVE",[actual.paths[4]],1,false);
for(var i=0;i<actual.paths.length;i++)paths("PATH"+i+"_EP",[actual.paths[i]],0,false);
paths("ALL_EP",actual.paths,0,false);
paths("ALL_INTERLEAVE",actual.paths,1,false);
paths("ALL_ONEFINISH",actual.paths,0,true);
function imp(side){try{
 var e=new DxfContour("IMP_"+side,"C:/tmp/sce_fpd_thermal_clean/bedrock_"+side+"_clean.dxf",refpoint_file,100,false);
 e.SetTool(600);e.SetAsCavity(true);e.SetDepth(.05);info(e,"IMPORT_FALSE_"+side);
}catch(err){rows.push("IMPORT_FALSE_"+side+" ERR "+err);}}
imp("top");imp("bottom");
rows.push("Expected ALL -63,-78,82.65,78");
Error(rows.join("\n"));
'''
for path in [HERE.parents[1]/"FPE/SCE20_CONTOUR_PROBE_V3.fpjs",Path("C:/Users/KyleKassen/AppData/Roaming/FrontDesign/Scripts/SCE20_CONTOUR_PROBE_V3.fpjs")]:
    path.write_text(js,encoding="utf-8");print(path)
