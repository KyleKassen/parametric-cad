"""Read-only fresh audit of the Mean Well NSP-1600 source STEP.

Run with C:/venvs/cadquery/Scripts/python.exe audit_nsp1600.py
The original vendor assembly remains unmodified. No thread capacity, permitted
penetration, mass or electrical safety claim is inferred from model appearance.
All reported solid indices are zero-based. Dimensions are nominal millimetres.
"""
from pathlib import Path
import json, hashlib, re, math, argparse
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TopLoc import TopLoc_Location
from OCP.IFSelect import IFSelect_RetDone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
SOURCE=Path(r'C:/Users/KyleKassen/OneDrive - Ataero/Shared Documents - Ataero San Antonio/06 R&D Products/NEW R&D/04 Shared Engineering/02 Component Library/Power Supplies/Mean Well/Mean Well - NSP-1600 0417 3D Model.stp')
VENDOR_COPY=ROOT/'parts/vendor/meanwell-nsp-1600/NSP-1600_0417.stp'
def bb(s):
    b=s.BoundingBox()
    return {a:[round(getattr(b,a+'min'),7),round(getattr(b,a+'max'),7)] for a in 'xyz'}
def vec(v): return [round(v.x,7),round(v.y,7),round(v.z,7)]
def record(s,i=None): return {'source_solid_index_zero_based':i,'bbox_mm':bb(s),'volume_mm3':round(s.Volume(),7),'valid':s.isValid(),'face_count':len(s.Faces())}

def surface_records(s):
    records=[]
    for i,f in enumerate(s.Faces()):
        a=BRepAdaptor_Surface(f.wrapped); typ=a.GetType(); b=bb(f)
        r={'face_index_zero_based':i,'type':str(typ),'bbox_mm':b,'area_mm2':round(f.Area(),7)}
        if typ==GeomAbs_Plane:
            r['normal']=vec(f.normalAt())
            r['wire_bboxes_mm']=[bb(w) for w in f.Wires()]
        elif typ==GeomAbs_Cylinder:
            c=a.Cylinder(); l=c.Axis().Location(); d=c.Axis().Direction()
            r.update(diameter_mm=round(2*c.Radius(),7),axis_location_mm=[round(l.X(),7),round(l.Y(),7),round(l.Z(),7)],axis_direction=[round(d.X(),7),round(d.Y(),7),round(d.Z(),7)],u_span_radians=round(a.LastUParameter()-a.FirstUParameter(),7))
        elif typ==GeomAbs_Cone:
            c=a.Cone(); r['semi_angle_degrees']=round(math.degrees(c.SemiAngle()),7)
        records.append(r)
    return records

def product_map(source,solids):
    doc=TDocStd_Document(TCollection_ExtendedString('XCAF')); reader=STEPCAFControl_Reader(); reader.SetNameMode(True)
    assert reader.ReadFile(str(source))==IFSelect_RetDone; assert reader.Transfer(doc)
    st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()); labels=TDF_LabelSequence(); st.GetFreeShapes(labels)
    signatures=[(s.Center(),s.Volume()) for s in solids]; records=[]
    def name(label):
        attr=TDataStd_Name(); return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(),attr) else ''
    def walk(label,loc,path):
        nm=name(label)
        if st.IsReference_s(label):
            target=TDF_Label(); st.GetReferredShape_s(label,target); walk(target,loc.Multiplied(st.GetLocation_s(label)),path+[nm])
        elif st.IsAssembly_s(label):
            cs=TDF_LabelSequence(); st.GetComponents_s(label,cs)
            for j in range(1,cs.Length()+1): walk(cs.Value(j),loc,path+[nm])
        else:
            raw=st.GetShape_s(label)
            if raw.IsNull(): return
            for s in cq.Shape.cast(raw.Moved(loc)).Solids():
                c,v=s.Center(),s.Volume()
                ids=[i for i,(cc,vv) in enumerate(signatures) if (c-cc).Length<1e-5 and abs(v-vv)<max(.001,abs(v)*1e-7)]
                records.append({'product':nm,'assembly_path':path,'matched_source_solid_indices_zero_based':ids,'source_bbox_mm':bb(s)})
    for j in range(1,labels.Length()+1): walk(labels.Value(j),TopLoc_Location(),[])
    return records


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=SOURCE);args=ap.parse_args()
    data=args.source.read_bytes();sha=hashlib.sha256(data).hexdigest();raw=data.decode('utf8',errors='replace')
    shape=cq.importers.importStep(str(args.source)).val();solids=shape.Solids()
    r={'source':str(args.source),'source_sha256':sha,'vendor_copy_sha256':hashlib.sha256(VENDOR_COPY.read_bytes()).hexdigest(),
       'units':'mm','source_unit_declarations':sorted(set(re.findall(r'[^;\n]*SI_UNIT\([^;]+;',raw))),
       'product_records':re.findall(r'#[0-9]+=PRODUCT\([^;]+;',raw),'source_solid_count':len(solids),'source_bbox_mm':bb(shape),
       'source_solids':[record(s,i) for i,s in enumerate(solids)],'product_map':product_map(args.source,solids),
       'all_source_face_records':[{'source_solid_index_zero_based':i,'faces':surface_records(s)} for i,s in enumerate(solids)]}
    bottom=shape.BoundingBox().zmin
    r['bottom_plane_source_z_mm']=bottom
    r['bottom_planar_faces']=[];r['near_bottom_axial_cylinder_candidates']=[]
    for body in r['all_source_face_records']:
        for f in body['faces']:
            if f['type']==str(GeomAbs_Plane) and abs(f['bbox_mm']['z'][0]-bottom)<1e-6 and abs(f['bbox_mm']['z'][1]-bottom)<1e-6:
                r['bottom_planar_faces'].append({'source_solid_index_zero_based':body['source_solid_index_zero_based'],**f})
            if f.get('diameter_mm',999)<9 and abs(f.get('axis_direction',[0,0,0])[2])>.999 and f['bbox_mm']['z'][0]<bottom+2 and f['bbox_mm']['z'][1]>bottom:
                r['near_bottom_axial_cylinder_candidates'].append({'source_solid_index_zero_based':body['source_solid_index_zero_based'],**f})
    r['source_preserved_sha256']=hashlib.sha256(args.source.read_bytes()).hexdigest();assert sha==r['source_preserved_sha256']
    (HERE/'nsp1600_source_audit.json').write_text(json.dumps(r,indent=2),encoding='utf8')
    print(json.dumps({'sha256':sha,'vendor_copy_match':sha==r['vendor_copy_sha256'],'solid_count':len(solids),'bbox':r['source_bbox_mm'],
        'solids':r['source_solids'],'bottom_faces':[{'solid':f['source_solid_index_zero_based'],'area':f['area_mm2'],'bbox':f['bbox_mm'],'wires':len(f['wire_bboxes_mm'])} for f in r['bottom_planar_faces']],
        'axial_candidates':[{'solid':f['source_solid_index_zero_based'],'dia':f['diameter_mm'],'axis':f['axis_location_mm'],'z':f['bbox_mm']['z']} for f in r['near_bottom_axial_cylinder_candidates']]},indent=2),flush=True)


if __name__=='__main__':main()


