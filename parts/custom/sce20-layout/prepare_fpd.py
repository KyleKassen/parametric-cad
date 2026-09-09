"""Prepare native FPD scripts. Execute the scripts in FPD to create real .fpd.

The isolated short staging path avoids FrontDesign's Windows MAX_PATH limit.
All saved files are copied unchanged into this design's FPE delivery folder.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "FPE"
STAGE = Path("C:/Users/KyleKassen/Documents/FPE_SCE20_20260908_R1")
CATALOG = Path.home()/"AppData/Local/Programs/FrontDesign/Config"
SKILL = Path.home()/".agents/skills/front-panel-designer/scripts/generate_panel.py"

COMMON_JS = r'''
function near(a,b,label) { if(Math.abs(a-b)>0.0011) Error(label+": "+a+" != "+b); }
function verifyPanel(p,s) {
  near(p.Width(),s.width,"width"); near(p.Height(),s.height,"height");
  near(p.Thickness(),s.thickness,"thickness");
  if(p.Material()!=s.material_id || p.MaterialColor()!=s.color_id) Error("material/color");
  if(p.Elements().length!=s.elements.length) Error("element count "+p.Elements().length);
  for(var i=0;i<s.elements.length;i++) {
    var a=s.elements[i],e=p.FindElement(a.id);
    if(!e) Error("missing "+a.id);
    near(e.X(),a.x,a.id+" X"); near(e.Y(),a.y,a.id+" Y");
    if(e.IsReverseSide() != (a.side=="reverse")) Error("side "+a.id);
    if(a.kind=="bolt") {
      if(e.Type()!=a.catalog) Error("catalog "+a.id);
      near(e.Length(),a.length,a.id+" length");
    } else if(a.kind=="hole") {
      if(!e.IsDrillHole() || e.IsBlindHole()) Error("through hole "+a.id);
      near(e.Diameter(),a.diameter,a.id+" diameter");
      if(a.countersink) {
        if(!e.HasCountersink()) Error("missing countersink "+a.id);
        near(e.ConeDiameter(),a.countersink.diameter,a.id+" cone mouth");
        near(e.DrillHoleDiameter(),a.diameter,a.id+" cone throat");
        near(e.SinkDepth(),a.countersink.recess||0,a.id+" cylindrical recess before cone");
        near(e.ConeAngle(),90,a.id+" cone angle");
      }
    } else if(a.kind=="contour_cavity") {
      if(!e.AsCavity()) Error("not cavity "+a.id);
      near(e.Depth(),a.depth,a.id+" cavity depth");
      var b=e.BoundingBox();
      for(var j=0;j<4;j++) near(b[j],a.bbox[j],a.id+" bbox "+j);
    }
  }
  if(s.name=="Backpanel_R1") {
    var a=p.FindElement("B210_1"),b=p.FindElement("B210_2");
    if(Math.abs(Math.abs(a.Y()-b.Y())-120.015)>0.00001) Error("B210 critical120.015 pitch");
  }
}
function createPanel(s) {
  var p=new Frontpanel(s.name,s.thickness,s.width,s.height,s.material_id,s.color_id);
  p.SetCornerRadii(s.radius,s.radius,s.radius,s.radius);
  p.SetEdgeMachining(bevel_45,s.bevel,bevel_45,s.bevel);
  p.SetRemark(s.remark);
  if(s.outline_dxf) {
    var outline=new DxfContour("OUTLINE",s.outline_dxf,refpoint_file,100,false);
    p.SetBorderContour(outline);
    p.SetEdgeMachining(bevel_45,s.bevel,bevel_45,s.bevel);
  }
  for(var i=0;i<s.elements.length;i++) {
    var a=s.elements[i],e;
    if(a.kind=="bolt") e=new Bolt(a.id,a.catalog,a.length);
    else if(a.kind=="hole") e=new DrillHole(a.id,a.diameter);
    else if(a.kind=="contour_cavity") {
      if(a.paths) {
        if(a.paths.length!=1) Error("Each cavity requires exactly one closed path: "+a.id);
        e=new DxfContour(a.id,"",refpoint_file);
        e.SetTool(a.tool);
        for(var pi=0;pi<a.paths.length;pi++) {
          var path=a.paths[pi];e.Start(path.start[0],path.start[1]);
          for(var si=0;si<path.segments.length;si++) {
            var sg=path.segments[si];
            if(sg.type=="LINE")e.LineTo(sg.end[0],sg.end[1]);
            else e.ArcToMP(sg.end[0],sg.end[1],sg.center[0],sg.center[1],sg.dir);
          }
          e.Finish();
        }
        e.SetAsCavity(true);
      } else e=new DxfContour(a.id,a.dxf,refpoint_file,100,true);
    } else Error("unsupported kind "+a.kind);
    if(a.side=="reverse") e.PutOnReverseSide(); else e.PutOnFrontSide();
    p.AddElement(e,a.x,a.y);
    if(a.kind=="contour_cavity") {
      Print("Attached "+a.id+"\n");
      e.SetTool(a.tool);
      Print("Tool selected "+a.id+"\n");
      e.SetDepth(a.depth);
      Print("Depth selected "+a.id+"\n");
    }
    if(a.kind=="bolt") e.SetDepthOffset(0);
    // SinkDepth is additional cylindrical recess; cone height follows diameters/angle.
    if(a.countersink) e.SetCountersinkWithParameters(a.countersink.diameter,a.diameter,a.countersink.recess||0,90);
  }
  verifyPanel(p,s);
  AddFrontpanel(p);
  SaveFrontpanel(p,s.save,false);
  var reloaded=LoadFrontpanel(s.save,s.name+"_readback");
  verifyPanel(reloaded,s);
  Print("PASS SAVED+RELOADED "+s.name+" | "+s.width+" x "+s.height+" x "+s.thickness+" mm | "+s.elements.length+" native elements\n");
  for(var i=0;i<s.elements.length;i++) {
    var a=s.elements[i];
    if(a.kind=="bolt") {var e=reloaded.FindElement(a.id);Print(a.id+" "+e.Type()+" L"+e.Length()+" FRONT ("+e.X()+", "+e.Y()+")\n");}
  }
}
'''


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def cavity_bbox(dxf, tx, ty):
    import ezdxf
    from ezdxf import bbox
    box=bbox.extents(ezdxf.readfile(dxf).modelspace())
    return [box.extmin.x+tx,box.extmin.y+ty,box.extmax.x+tx,box.extmax.y+ty]


def write_script(specs, stem):
    # Material/stock availability checked against actual installed catalog.
    spec=importlib.util.spec_from_file_location("fpd_skill_generator",SKILL)
    lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
    for s in specs:
        lib.validate_material(s,CATALOG)
        if Path(s["save"]).exists():
            raise FileExistsError("Native target exists; create a new revision: "+s["save"])
    text="// SCE20 R1. Creates new documents; never modifies an existing panel.\n"+COMMON_JS
    for s in specs:
        text+="\ncreatePanel("+json.dumps(s,ensure_ascii=True,separators=(",",":"))+");\n"
    text+='Print("ALL REQUESTED PANELS SAVED AND NATIVE READBACK PASSED\\n");\n'
    (OUT/(stem+".fpjs")).write_text(text,encoding="utf-8")
    (OUT/(stem+"_inputs.json")).write_text(json.dumps(specs,indent=2),encoding="utf-8")
    shutil.copy2(OUT/(stem+".fpjs"),STAGE/(stem+".fpjs"))
    user_scripts=Path.home()/"AppData/Roaming/FrontDesign/Scripts"
    user_scripts.mkdir(parents=True,exist_ok=True)
    shutil.copy2(OUT/(stem+".fpjs"),user_scripts/(stem+".fpjs"))
    print("PREPARED",stem,[s["name"] for s in specs])


def adapters(only=None):
    import ezdxf
    data=load(HERE/"references/interfaces/fpd_adapter_specs.json")
    specs=[]
    names={"B210_FPE_R1":"B210_R2","MeanWell_N2":"MeanWell_R2","Bedrock_FPE_R1":"Bedrock_R3"}
    for key,entry in data["panels"].items():
        if only is not None and names[key]!=only:
            continue
        a=entry["adapter"]; name=names[key];tx,ty=a["local_to_adapter_fpd_translation_mm"]
        remark="R1 FIT DESIGN. Bare aluminum; finished thickness +/-0.05 mm; deburr bores <=0.1 mm. Front=device; reverse=backplate seating face. "
        if key=="B210_FPE_R1": remark+="M3x6 device screws seat 0.55 mm recessed; nominal penetration 2.55 mm."
        elif key=="Bedrock_FPE_R1": remark+="SPECIAL PRECISION MACHINING: BOTH thermal pockets 0.050 +/-0.010 mm, Ra<=1.6um; retain front D8 and reverse D12 hard lands. Keep faces conductive/flat, assembled TIM gap<=0.10 mm. M4x8 heads recessed0.95; nominal penetration2.95. Supplier must confirm tolerances before production."
        else: remark+="M4x10 device screws; nominal penetration4.05 mm, maximum5 mm. Source N2 side-tab geometry."
        s=dict(name=name,width=a["width_mm"],height=a["height_mm"],thickness=a["thickness_mm"],material_id=5,color_id=1,radius=a["outline"]["corner_radius_mm"],bevel=.4,remark=remark,elements=[],save=(STAGE/(name+".fpd")).as_posix())
        if a["outline"]["type"]=="closed_xy_bulge_polyline":
            # Manufacturing-only outline in positive FPD coordinates, no holes.
            doc=ezdxf.new("R2010");doc.units=4
            doc.modelspace().add_lwpolyline([(x+tx,y+ty,b) for x,y,b in a["outline"]["vertices_xyb"]],format="xyb",close=True)
            path=STAGE/(name+"_outline.dxf");doc.saveas(path)
            shutil.copy2(path,OUT/path.name);s["outline_dxf"]=path.as_posix()
        for i,(x,y) in enumerate(a["stud_clearance_holes"]["local_xy_mm"],1):
            s["elements"].append(dict(id=f"P{i}",kind="hole",x=x+tx,y=y+ty,diameter=a["stud_clearance_holes"]["diameter_mm"],side="front"))
        h=a["housing_holes"];c=h["countersink"]
        for i,(x,y) in enumerate(h["local_xy_mm"],1):
            s["elements"].append(dict(id=f"D{i}",kind="hole",x=x+tx,y=y+ty,diameter=h["diameter_mm"],side="reverse",countersink=dict(diameter=c["mouth_diameter_mm"],depth=c["depth_mm"])))
        if "thermal_fields" in a:
            # Exact single-loop decomposition avoids FPD 6.5 multi-path bridges.
            t=load(HERE/"references/interfaces/thermal_single_loop_regions.json")
            for side,k in [("front","top"),("reverse","bottom")]:
                for region in t["contours"][k]["regions"]:
                    assert len(region["paths"])==1
                    s["elements"].append(dict(id=region["id"],kind="contour_cavity",x=tx,y=ty,side=side,depth=.05,tool=600,paths=region["paths"],bbox=region["bbox"]))
        specs.append(s)
    write_script(specs,"SCE20_"+only.upper() if only else "SCE20_ADAPTERS_FINAL_R3")


def backpanel():
    p=load(HERE/"params.json")
    s=dict(name="Backpanel_R1",width=p["width"],height=p["height"],thickness=p["thickness"],material_id=5,color_id=1,radius=p["corner_radius"],bevel=.4,elements=[],save=(STAGE/"Backpanel_R1.fpd").as_posix(),remark="SCE20 R1. 431.8 square / R6.35 original SUBPANEL outline and six original mounting holes. 6mm bare aluminum, finished thickness +/-0.05mm. FRONT=components and all16 M3x12 load studs +4 M4x6 female load standoffs; depth offset0. Bases/adhesive flush or below face. Rear seat unchanged. See layout and ordering notes; verify factory stud engagement and thermal process before ordering.")
    for h in p["mounting_holes"]:
        s["elements"].append(dict(kind="hole",id=h["id"],x=h["x"],y=h["y"],diameter=h["diameter"],side="front"))
    for b in p["hardware"]:
        s["elements"].append(dict(kind="bolt",id=b["id"],x=b["x"],y=b["y"],catalog=b["catalog_code"],length=b["length"],side="front"))
    write_script([s],"SCE20_BACKPANEL_R1")


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("which",choices=["adapters","backpanel","B210_R2","MeanWell_R2","Bedrock_R3"]);args=ap.parse_args()
    OUT.mkdir(exist_ok=True);STAGE.mkdir(exist_ok=True)
    if args.which=="backpanel": backpanel()
    else: adapters(None if args.which=="adapters" else args.which)
