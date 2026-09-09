"""Check actual native adapter STEP, including real countersink axial geometry."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

HERE=Path(__file__).resolve().parent
LAYOUT=HERE.parents[1]
ROOT=LAYOUT.parents[2]
ORDER=Path("C:/Users/KyleKassen/Documents/FPE_SCE20_20260908_R1")
CONFIG={
 "b210":("B210_R2",LAYOUT/"exports/B210_FPE_R1_plate.step",LAYOUT/"adapters/B210_FPE_R1_params.json"),
 "meanwell":("MeanWell_R2",ROOT/"parts/custom/meanwell-nsp1600-side-tab-mount/exports/plate_N2.step",ROOT/"parts/custom/meanwell-nsp1600-side-tab-mount/params.json"),
 "bedrock":("Bedrock_R3",LAYOUT/"exports/Bedrock_FPE_R1_plate.step",LAYOUT/"adapters/Bedrock_FPE_R1_params.json"),
}

def bbox(s):
 b=s.BoundingBox();return {a:[getattr(b,a+"min"),getattr(b,a+"max")] for a in "xyz"}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("component",choices=CONFIG);ap.add_argument("--native",type=Path);args=ap.parse_args()
 name,expected_path,params_path=CONFIG[args.component];native_path=args.native or ORDER/(name+"_native.step")
 if not native_path.exists():raise SystemExit("Native export not yet present: "+str(native_path))
 p=json.loads(params_path.read_text());stage=Path("C:/tmp/sce_native_adapter_audit")/name;stage.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(native_path,stage/"native.step");shutil.copyfile(expected_path,stage/"expected.step")
 raw=cq.importers.importStep(str(stage/"native.step")).val();expected=cq.importers.importStep(str(stage/"expected.step")).val()
 nb,eb=raw.BoundingBox(),expected.BoundingBox()
 move=((eb.xmin+eb.xmax-nb.xmin-nb.xmax)/2,(eb.ymin+eb.ymax-nb.ymin-nb.ymax)/2,eb.zmin-nb.zmin)
 native=raw.translate(move);checks=[]
 def ck(n,ok,v=None,c=None):checks.append({"check":n,"pass":bool(ok),"measured":v,"criterion":c})
 ck("valid single native plate",native.isValid() and len(native.Solids())==1,len(native.Solids()),1)
 ck("native XYZ size",all(abs(getattr(nb,a+"len")-getattr(eb,a+"len"))<.005 for a in "xyz"),bbox(native),bbox(expected))
 nv,ev=native.Volume(),expected.Volume()
 common=native.copy().intersect(expected.copy());overlap=sum(s.Volume() for s in common.Solids())
 boolean_info={"method":"nominal-coordinate intersection","test_translation_mm":[0,0,0],"conservative_translation_volume_bound_mm3":0}
 if overlap==0 and nv>0 and ev>0:
  # OCCT can return an empty, nominally valid common for coincident faces.
  # Test a 0.00001 mm X displacement, keeping all feature checks at nominal
  # coordinates, and ADD the full area*displacement BV translation bound.
  # This gives an upper bound on the nominal symmetric difference, not an
  # assumption that a numerical perturbation is physically acceptable.
  delta=.00001
  common=native.copy().translate((delta,0,0)).intersect(expected.copy())
  overlap=sum(s.Volume() for s in common.Solids())
  boolean_info={"method":"bounded microscopic-translation retry after empty nominal OCCT common","test_translation_mm":[delta,0,0],"conservative_translation_volume_bound_mm3":native.Area()*delta}
 diff={"extra_native_metal_mm3":max(0,nv-overlap),"missing_native_metal_mm3":max(0,ev-overlap)}
 geometry_upper_bound=sum(diff.values())+boolean_info["conservative_translation_volume_bound_mm3"]
 ck("complete native/reference geometry",geometry_upper_bound<3,{**diff,"nominal_symmetric_difference_upper_bound_mm3":geometry_upper_bound,"boolean":boolean_info},"<3mm3 permits omitted source0.1boredeburr and native0.001machining quantization; not missing islands or misplaced counterbores")
 surfaces=[]
 for face in native.Faces():
  ty=face.geomType()
  if ty not in {"CYLINDER","CONE"}:continue
  a=BRepAdaptor_Surface(face.wrapped);surf=a.Cylinder() if ty=="CYLINDER" else a.Cone()
  axis=surf.Axis();d=axis.Direction();loc=axis.Location()
  if abs(d.Z())<.99999:continue
  b=face.BoundingBox()
  item={"kind":ty,"xy":[loc.X(),loc.Y()],"bbox":bbox(face)}
  if ty=="CYLINDER":item["radius_mm"]=surf.Radius()
  else:item.update({"max_radius_mm":max(b.xlen,b.ylen)/2,"angle_deg":math.degrees(abs(surf.SemiAngle()))})
  surfaces.append(item)
 housing=p.get("housing_points",[[sx*p.get("housing_pitch_x",0)/2,sy*p.get("housing_pitch_y",0)/2] for sx in(-1,1) for sy in(-1,1)])
 studs=[[sx*p["stud_pitch_x"]/2+p["stud_pattern_center_x"],sy*p["stud_pitch_y"]/2+p["stud_pattern_center_y"]] for sx in(-1,1) for sy in(-1,1)]
 for family,pts,r in [("stud",studs,p["stud_clearance_diameter"]/2),("housing",housing,p["housing_clearance_diameter"]/2)]:
  for i,pt in enumerate(pts,1):
   cyl=[s for s in surfaces if s["kind"]=="CYLINDER" and math.dist(s["xy"],pt)<.003 and abs(s["radius_mm"]-r)<.0021]
   ck(family+" bore "+str(i),bool(cyl),cyl,"correct sourceXY/radius")
 cone_depth=(p["countersink_diameter_reference"]-p["housing_clearance_diameter"])/2
 measured_projection=[]
 for i,pt in enumerate(housing,1):
  cones=[s for s in surfaces if s["kind"]=="CONE" and math.dist(s["xy"],pt)<.003]
  ck("housing "+str(i)+" one actual countersink",len(cones)==1,cones,1)
  if len(cones)!=1:continue
  c=cones[0];z0,z1=c["bbox"]["z"]
  ck("countersink "+str(i)+" at UNDERSIDE, no extra recess",abs(z0)<.0021 and abs(z1-cone_depth)<.0031,[z0,z1],[0,cone_depth])
  ck("countersink "+str(i)+" mouth/angle",abs(c["max_radius_mm"]-p["countersink_diameter_reference"]/2)<.0021 and abs(c["angle_deg"]-45)<.01,c,"specified mouth radius;45-degree halfangle")
  def is_expected_thermal_land_wall(s):
   # The Bedrock hard lands have cylindrical outside walls; they are metal,
   # not drilled recesses. Exempt only the exact specified radius and Z span.
   if args.component!="bedrock":return False
   depth=p["thermal_pocket_depth"];thickness=p["plate_thickness"]
   allowed=[(p["underside_countersink_land_diameter"]/2,[0,depth]),(p["tile_contact_land_diameter"]/2,[thickness-depth,thickness])]
   return any(abs(s["radius_mm"]-radius)<.0021 and all(abs(a-b)<.0021 for a,b in zip(s["bbox"]["z"],zspan)) for radius,zspan in allowed)
  counterbores=[s for s in surfaces if s["kind"]=="CYLINDER" and math.dist(s["xy"],pt)<.003 and s["radius_mm"]>p["housing_clearance_diameter"]/2+.1 and s["bbox"]["z"][1]-s["bbox"]["z"][0]>.005 and not is_expected_thermal_land_wall(s)]
  ck("countersink "+str(i)+" no unintended large counterbore",not counterbores,counterbores,"no additional straight recess before cone")
  ideal_head_recess=z0+c["max_radius_mm"]-p["screw_head_diameter"]/2
  projection=p["screw_length_overall"]+ideal_head_recess-p["plate_thickness"]
  intended=p["screw_length_overall"]+p["screw_head_recess_nominal"]-p["plate_thickness"]
  measured_projection.append(projection)
  ck("screw "+str(i)+" nominal penetration from actual native seat",abs(projection-intended)<.005,projection,intended)
 report={"native":str(native_path),"native_sha256":hashlib.sha256(native_path.read_bytes()).hexdigest(),"expected":str(expected_path),"physical_variant":p["revision"],"units":"mm","normalization_translation":move,"raw_native_bbox":bbox(raw),"normalized_bbox":bbox(native),"native_volume_mm3":nv,"expected_volume_mm3":ev,"status":"PASS" if all(c["pass"] for c in checks) else "FAIL","checks":checks,"nominal_screw_projections_from_actual_native_seats_mm":measured_projection,"vertical_cylinders_and_cones":surfaces,"scope":"actual native exported geometry; ideal conical screw-seat calculation still requires received-head/thread/projection measurement; no supplier/physical/load qualification"}
 out=HERE/(name+"_native_geometry_audit.json");out.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(report["status"],name,len(checks),diff,"screw projections",measured_projection,flush=True)
 print(out)

if __name__=="__main__":main()
