"""Independent reopened native-FPD STEP geometry audit against the CAD variant.

Run only after native STEP export exists. Samples actual metal around thermal
lands and compares complete thin slices, so a bounding-box/depth-only success
cannot conceal removed islands or diagonal machining bridges.
"""
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
NATIVE=Path("C:/Users/KyleKassen/Documents/FPE_SCE20_20260908_R1/Bedrock_R3_native.step")
EXPECTED=Path("C:/tmp/sce_adapters/Bedrock_FPE_R1/Bedrock_FPE_R1_plate.step")
OUT=HERE/"native_bedrock_R3_step_audit.json"


def bbox(s):
    b=s.BoundingBox()
    return {a:[getattr(b,a+"min"),getattr(b,a+"max")] for a in "xyz"}


def ivol(a,b):
    return sum(s.Volume() for s in a.copy().intersect(b.copy()).Solids())


def main():
    if not NATIVE.exists(): raise SystemExit("Native STEP does not yet exist; run after export.")
    staged=Path("C:/tmp/sce_fpd_thermal_clean/Bedrock_native_audit.step")
    shutil.copyfile(NATIVE,staged)
    source=cq.importers.importStep(str(staged)).val()
    expected=cq.importers.importStep(str(EXPECTED)).val()
    sb=source.BoundingBox()
    assert abs(sb.xlen-166)<.02 and abs(sb.ylen-184)<.02 and abs(sb.zlen-6)<.02, bbox(source)
    translation=(-(sb.xmin+sb.xmax)/2,-(sb.ymin+sb.ymax)/2,-sb.zmin)
    native=source.translate(translation)
    checks=[]
    def ck(n,ok,value=None,criterion=None):checks.append({"check":n,"pass":bool(ok),"measured":value,"criterion":criterion})
    ck("native valid single plate",native.isValid() and len(native.Solids())==1,len(native.Solids()),1)
    # Full-solid comparison makes no assumption about tessellation or native
    # pocket island handling. Preserve the simple bounds normalization first.
    ov=ivol(native,expected)
    delta={"native_extra_metal_mm3":max(0,native.Volume()-ov),"native_missing_metal_mm3":max(0,expected.Volume()-ov)}
    # Mirror alternatives are only diagnostic; never silently alter a handed
    # native export to manufacture agreement with expected coordinates.
    diagnostic=[]
    if sum(delta.values())>5:
        for label,axis,base in [("Z_flip","XY",(0,0,3)),("Y_flip","XZ",(0,0,0)),("X_flip","YZ",(0,0,0))]:
            mirrored=native.mirror(axis,base)
            overlap=ivol(mirrored,expected)
            diagnostic.append({"transform":label,"symmetric_difference_mm3":mirrored.Volume()+expected.Volume()-2*overlap})
    ck("whole native/source symmetric difference",sum(delta.values())<3,delta,"<3 mm3; allows source bore deburr absent from native, native0.001mm quantization and tiny CAM corner offsets")
    planes={}
    cylinders=[]
    cones=[]
    for f in native.Faces():
        if f.geomType()=="PLANE" and abs(f.normalAt().z)>.99999:
            z=round(f.Center().z,5)
            planes[z]=planes.get(z,0)+f.Area()
        elif f.geomType()=="CYLINDER":
            cy=BRepAdaptor_Surface(f.wrapped).Cylinder()
            ax=cy.Axis().Direction();loc=cy.Axis().Location()
            if abs(ax.Z())>.9999:cylinders.append({"xy":[loc.X(),loc.Y()],"radius_mm":cy.Radius(),"bbox":bbox(f)})
        elif f.geomType()=="CONE":cones.append({"bbox":bbox(f),"area_mm2":f.Area()})
    for z,label in [(.05,"bottom pocket floor"),(5.95,"top pocket floor")]:
        matching=sum(area for zz,area in planes.items() if abs(zz-z)<.0011)
        ck(label+" at actual0.05depth",matching>18000,matching,">18000mm2 horizontal floor at specifiedZ")
    pts=[(-60,-70),(60,-70),(0,-40),(0,30),(-50,70),(50,70)]
    sample_mismatch=[]; sample_count=0
    for side,z,radii in [("top",5.975,[3.0,3.9,4.1,4.5]),("bottom",.025,[5.0,5.9,6.1,6.5])]:
        for i,(x,y) in enumerate(pts):
            for r in radii:
                for k in range(16):
                    a=2*math.pi*k/16
                    q=(x+r*math.cos(a),y+r*math.sin(a),z)
                    e=expected.isInside(cq.Vector(*q),1e-7)
                    n=native.isInside(cq.Vector(*q),1e-7)
                    sample_count+=1
                    if e!=n:sample_mismatch.append({"side":side,"housing_hole":i+1,"radius_mm":r,"angle_deg":k*22.5,"xyz":q,"expected_metal":e,"native_metal":n})
    ck("all six exact land diameters and surrounding pockets",not sample_mismatch,{"samples":sample_count,"mismatches":sample_mismatch},"metal ring and adjacent pocket classifications agree")
    slices=[]
    for z,label in [(.025,"bottom half-pocket"),(5.975,"top half-pocket")]:
        slab=cq.Solid.makeBox(180,200,.002,cq.Vector(-90,-100,z-.001))
        ns=native.copy().intersect(slab.copy());es=expected.copy().intersect(slab.copy())
        v=ivol(ns,es)
        extra=max(0,ns.Volume()-v)/.002;missing=max(0,es.Volume()-v)/.002
        sl={"name":label,"z":z,"native_metal_area_mm2":ns.Volume()/.002,"expected_metal_area_mm2":es.Volume()/.002,"extra_metal_area_mm2":extra,"missing_metal_area_mm2":missing}
        # Source CAD includes <=0.1mm bore-mouth deburr geometry; FPD carries
        # that as a production remark. Exclude bore/deburr interiors only from
        # the thermal-region comparison. The metal land annuli remain tested
        # both by full slices and by the separate exact radial samples.
        radius=5.3 if z<1 else 2.5
        exclusions=[cq.Solid.makeCylinder(radius,8,cq.Vector(x,y,-1)) for x,y in pts]
        exclusions += [cq.Solid.makeCylinder(2.1,8,cq.Vector(x,y,-1)) for x in(-76,76) for y in(-82,82)]
        mask=cq.Compound.makeCompound(exclusions)
        nn=ns.copy().cut(mask.copy());ee=es.copy().cut(mask.copy())
        vv=ivol(nn,ee)
        mex=max(0,nn.Volume()-vv)/.002;mmi=max(0,ee.Volume()-vv)/.002
        sl["outside_bore_deburr_exclusions"]={"housing_radius_excluded_mm":radius,"stud_radius_excluded_mm":2.1,"extra_metal_area_mm2":mex,"missing_metal_area_mm2":mmi}
        slices.append(sl)
        ck(label+" thermal planar geometry outside bore deburr",mex+mmi<5,sl,"<5mm2 difference outside bore/deburr interiors; land annuli, field and real diagonal bridges remain checked")
    for family,points,r in [("stud",[(x,y) for x in (-76,76) for y in (-82,82)],1.9),("device",pts,2.25)]:
        for i,(x,y) in enumerate(points):
            matches=[c for c in cylinders if math.dist(c["xy"],[x,y])<.002 and abs(c["radius_mm"]-r)<.001]
            ck(family+" through-bore axis "+str(i+1),bool(matches),matches,"correct radius and XY")
    report={"native_file":str(NATIVE),"native_sha256":hashlib.sha256(NATIVE.read_bytes()).hexdigest(),"source_expected":str(EXPECTED),"units":"mm","normalization":{"translation":translation,"native_original_bbox":bbox(source),"normalized_bbox":bbox(native),"rule":"center XY; put lowestZ at0. No silent mirrors."},"status":"PASS" if all(c["pass"] for c in checks) else "FAIL","checks":checks,"horizontal_plane_area_by_z_mm":planes,"native_cylindrical_faces":cylinders,"native_conical_faces":cones,"diagnostic_mirror_comparisons":diagnostic,"scope":"actual nativeSTEP geometry; does not establish supplier tolerance, thread fit, contact flatness, toolpath sequencing or load/thermal capacity"}
    OUT.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(report["status"],len(checks),delta,"sample mismatches",len(sample_mismatch),flush=True)
    print(json.dumps(slices,indent=2),flush=True)
    print("planes",planes,flush=True)
    print("diagnostics",diagnostic,flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--native",type=Path,default=NATIVE)
    NATIVE=parser.parse_args().native
    main()
