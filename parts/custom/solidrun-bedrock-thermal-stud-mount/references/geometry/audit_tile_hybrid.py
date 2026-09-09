"""Read-only fresh audit of the SolidRun multi-variant STEP.

Run with C:/venvs/cadquery/Scripts/python.exe audit_tile_hybrid.py
The generated Tile-plus-one-fin-bank assembly is a DERIVED REFERENCE, not a
vendor-configured product or proof of physical/thermal interchangeability.
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
SOURCE=ROOT/'parts/vendor/solidrun-bedrock-v3000/Bedrock V3000 Basic 3D model.step'
AXES=[(-60.,-70.),(60.,-70.),(0.,-40.),(0.,30.),(-50.,70.),(50.,70.)]

def norm(s): return s.rotate((0,0,0),(1,1,1),-120).translate((0,-80,14.5))
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

def nearby_faces(faces,x,y):
    return [r for r in faces if r['bbox_mm']['x'][0]>=x-3.2 and r['bbox_mm']['x'][1]<=x+3.2 and r['bbox_mm']['y'][0]>=y-3.2 and r['bbox_mm']['y'][1]<=y+3.2]

def section(s,x,y,along='x',width=17,zheight=35):
    clip=cq.Workplane('XY').box(width,width,zheight+4).translate((x,y,zheight/2-1)).val()
    local=s.intersect(clip)
    plane=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0)) if along=='x' else cq.Plane(origin=(x,0,0),xDir=(0,1,0),normal=(1,0,0))
    return cq.Workplane(plane).add(local).section().val()

def write_section_svg(tile,bank,aux,axis,index,out):
    x,y=axis; width,height=1080,760
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="1080" height="760" fill="white"/>','<style>text{font-family:Helvetica,sans-serif;fill:#172d3b;font-size:18px}.title{font-size:26px;font-weight:bold}.small{font-size:15px}</style>']
    tx=lambda a:350+(a-x)*10; tz=lambda z:630-z*10
    svg.extend([f'<text x="30" y="43" class="title">SolidRun Tile side: mounting axis {index+1}, true section</text>',f'<text x="30" y="77">X = {x:.4f}, Y = {y:.4f}; mating-face datum Z = 0 mm. View along -Y.</text>'])
    for shape,color,name,ly in [(tile,'#197552','Actual Tile body',131),(bank,'#875ab0','Derived 60W-bank clipping',161),(aux,'#b9651c','Shared auxiliary model bodies',191)]:
        clip=cq.Workplane('XY').box(17,17,56).translate((x,y,26)).val(); local=shape.intersect(clip)
        if local.Volume()>1e-6:
            sec=section(local,x,y,zheight=54)
            for e in sec.Edges():
                pts,_=e.sample(max(2,math.ceil(e.Length()/.03)+1))
                path=' '.join(('M' if i==0 else 'L')+f'{tx(p.x):.3f},{tz(p.z):.3f}' for i,p in enumerate(pts))
                svg.append(f'<path d="{path}" stroke="{color}" fill="none" stroke-width="2"/>')
        svg.extend([f'<line x1="680" y1="{ly}" x2="714" y2="{ly}" stroke="{color}" stroke-width="4"/>',f'<text x="726" y="{ly+5}" class="small">{name}</text>'])
    svg.extend([f'<line x1="{tx(x)}" y1="100" x2="{tx(x)}" y2="660" stroke="#5e7584" stroke-dasharray="10 4 2 4"/>',f'<line x1="125" y1="{tz(0)}" x2="620" y2="{tz(0)}" stroke="#5e7584" stroke-dasharray="5 4"/>',f'<text x="660" y="{tz(0)+5}">Mating face Z = 0</text>',f'<line x1="510" y1="{tz(29)}" x2="640" y2="{tz(29)}" stroke="#5e7584"/>',f'<text x="653" y="{tz(29)+5}">Derived split plane Z = 29</text>','<text x="30" y="700">Geometric bore/cavity evidence only; no allowable screw depth or thread capacity is established.</text>','<text x="30" y="732" class="small">Tile + clipped fin bank is a derived spatial reference, not vendor-configured hardware or a validated thermal joint.</text>','</svg>'])
    out.write_text('\n'.join(svg),encoding='utf8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,default=SOURCE); args=ap.parse_args(); HERE.mkdir(parents=True,exist_ok=True)
    data=args.source.read_bytes(); digest=hashlib.sha256(data).hexdigest(); raw=data.decode('utf8',errors='replace')
    print('Freshly importing original SolidRun multi-variant STEP...',flush=True)
    original=cq.importers.importStep(str(args.source)).val(); originals=original.Solids()
    report={'source':str(args.source),'source_sha256':digest,'units':'mm','step_unit_declarations':sorted(set(re.findall(r'[^;\n]*SI_UNIT\([^;]+;',raw))),
        'product_records':re.findall(r'#[0-9]+=PRODUCT\([^;]+;',raw),'solid_count':len(originals),'source_bbox_mm':bb(original),
        'frame':'(newX,newY,newZ)=(oldY,oldZ-80,oldX+14.5); right-handed. Equivalent rotation -120deg about (1,1,1), translation(0,-80,14.5).',
        'evidence_limit':'No thread specification, usable depth, material, mass, structural rating, thermal capacity or physical bank interchangeability is inferred from geometry.'}
    assert len(originals)==22, 'Source changed; re-identify source bodies.'
    bodies=[record(s,i) for i,s in enumerate(originals)]; report['source_bodies']=bodies
    variants={}
    for nm,half in [('Tile',14.5),('30W',22.5),('60W',36.5)]:
        matches=[i for i,s in enumerate(originals) if abs(s.BoundingBox().xmax-half)<1e-5 and abs(s.BoundingBox().xmin+half)<1e-5 and s.Volume()>100000]
        assert len(matches)==1; variants[nm]=matches[0]
    report['variant_source_indices_zero_based']=variants
    ns=[norm(s) for s in originals]; tile=ns[variants['Tile']]; full60=ns[variants['60W']]; auxids=[i for i in range(22) if i not in variants.values()]; aux=cq.Compound.makeCompound([ns[i] for i in auxids])
    faces=surface_records(tile)
    report['tile_normalized']=record(tile,variants['Tile']); report['tile_face_records']=faces
    planes=[f for f in faces if f['type']==str(GeomAbs_Plane) and abs(f['bbox_mm']['z'][0])<1e-6 and abs(f['bbox_mm']['z'][1])<1e-6]
    report['mating_plane_faces']=planes
    report['mating_plane_area_mm2']=sum(f['area_mm2'] for f in planes)
    report['auxiliary_source_indices_zero_based']=auxids
    report['auxiliary_normalized_bodies']=[record(ns[i],i) for i in auxids]
    report['candidate_hole_axes_xy_mm']=[list(v) for v in AXES]
    report['hole_local_face_records']=[{'axis_xy_mm':list(a),'faces':nearby_faces(faces,*a)} for a in AXES]
    (HERE/'solidrun_geometry_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({k:report[k] for k in ['source_sha256','solid_count','variant_source_indices_zero_based','tile_normalized','mating_plane_area_mm2','candidate_hole_axes_xy_mm']},indent=2),flush=True)
    print('Extracting a single real 60W-bank region for a derived reference...',flush=True)
    cutter=cq.Workplane('XY').box(200,240,31,centered=(True,True,False)).translate((0,0,29)).val()
    bank=full60.intersect(cutter)
    hybrid=cq.Compound.makeCompound([tile,bank]+[ns[i] for i in auxids])
    report['derived_reference_definition']='Normalized Tile source body + region of actual 60W source body at newZ>=29 (oldX>=14.5) + original shared auxiliary bodies; never a native source configuration.'
    report['derived_bank']=record(bank)
    report['derived_hybrid']=record(hybrid)
    report['tile_bank_intersection_mm3']=tile.intersect(bank).Volume()
    # Closest modeled material on each centerline; an empty probe is not evidence of safe intrusion.
    stations=[]
    for x,y in AXES:
        probe=cq.Solid.makeCylinder(.015,56,cq.Vector(x,y,0),cq.Vector(0,0,1)); obs=[]
        for label,shape in [('Tile',tile),('derived_bank',bank),('shared_auxiliary',aux)]:
            hit=shape.intersect(probe)
            if hit.Volume()>1e-8: obs.append({'body_group':label,'first_z_mm':bb(hit)['z'][0],'hit_bbox_mm':bb(hit),
                                           'disconnected_material_z_intervals_mm':sorted([bb(s)['z'] for s in hit.Solids()]),
                                           'bbox_limit':'Overall hit bbox can span voids between disconnected material pieces; use the per-piece intervals.'})
        obs.sort(key=lambda r:r['first_z_mm'])
        local=nearby_faces(faces,x,y)
        axial=[f for f in local if 'axis_direction' in f and abs(f['axis_direction'][2])>.999]
        stations.append({'axis_xy_mm':[x,y],'coaxial_cylinders':axial,'centerline_probe_radius_mm':.015,'modeled_centerline_obstacles':obs,
                         'allowable_penetration_mm':None,'usable_full_thread_engagement_mm':None,
                         'limitation':'No internal populated-board model or installed fin fasteners are established; no-obstacle travel is not a safe screw-depth limit.'})
    report['hole_stations']=stations
    report['derived_bodies_below_mating_face']=[record(s,i) for i,s in enumerate(hybrid.Solids()) if bb(s)['z'][0]<-1e-5]
    report['fresh_source_unchanged']=hashlib.sha256(args.source.read_bytes()).hexdigest()==digest
    (HERE/'solidrun_geometry_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({'bank':report['derived_bank'],'hybrid':report['derived_hybrid'],'overlap':report['tile_bank_intersection_mm3'],
                      'obstacles':[{'axis':s['axis_xy_mm'],'obstacles':s['modeled_centerline_obstacles']} for s in stations]},indent=2),flush=True)
    print('Mapping source product metadata...',flush=True)
    report['xcaf_product_map']=product_map(args.source,originals)
    report['unmatched_xcaf_body_count']=sum(not p['matched_source_solid_indices_zero_based'] for p in report['xcaf_product_map'])
    out=HERE/'derived_tile_plus_one_60W_bank_REFERENCE_ONLY.step'; temp=Path('C:/b210work/solidrun'); temp.mkdir(parents=True,exist_ok=True)
    staged=temp/out.name; cq.exporters.export(hybrid,str(staged)); out.write_bytes(staged.read_bytes())
    reopened=cq.importers.importStep(str(staged)).val()
    report['derived_step_reopen']={'bbox_mm':bb(reopened),'solid_count':len(reopened.Solids()),'valid':reopened.isValid(),'volume_mm3':reopened.Volume(),'volume_difference_mm3':reopened.Volume()-hybrid.Volume()}
    # Separate source-derived components help a reviewer audit the constructed reference.
    for name,shape in [('tile_normalized_SOURCE',tile),('single_60W_bank_CLIPPED_REFERENCE',bank),('auxiliary_normalized_SOURCE',aux)]:
        file=temp/(name+'.step'); cq.exporters.export(shape,str(file)); (HERE/file.name).write_bytes(file.read_bytes())
    secdir=HERE/'sections'; secdir.mkdir(exist_ok=True)
    for i,a in enumerate(AXES): write_section_svg(tile,bank,aux,a,i,secdir/f'axis_{i+1}_xz.svg')
    (HERE/'solidrun_geometry_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('Done: fresh audit, normalized derived-reference STEP reopen and six exact CAD sections.',flush=True)

if __name__=='__main__': main()
