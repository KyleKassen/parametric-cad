"""Fresh, read-only audit of the supplied B210 STEP underside interfaces.

Run: C:/venvs/cadquery/Scripts/python.exe under_feet_audit.py
Outputs JSON, STEP-derived section SVGs and a section DXF beside this source.
Model geometry is evidence of nominal geometry, not usable thread engagement.
"""
from pathlib import Path
import argparse, hashlib, json, re, math
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label, TDF_LabelSequence, TDF_Tool
from OCP.TDataStd import TDataStd_Name
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TopLoc import TopLoc_Location
from OCP.IFSelect import IFSelect_RetDone

HERE=Path(__file__).resolve().parent
SOURCE=Path(r'C:/Users/KyleKassen/OneDrive - Ataero/Shared Documents - Ataero San Antonio/06 R&D Products/NEW R&D/04 Shared Engineering/02 Component Library/Software-Defined Radios/Ettus Research/Ettus - USRP B210 Full Unit 3D Model.step')
FOOT_IDS=[174,175,176,177]

def norm(s):
    return s.rotate((0,0,0),(1,0,0),90).rotate((0,0,0),(0,0,1),180).translate((58.5005,80.6355,1.210))

def bb(s):
    b=s.BoundingBox()
    return {a:[round(getattr(b,a+'min'),7),round(getattr(b,a+'max'),7)] for a in 'xyz'}

def label_name(label):
    attr=TDataStd_Name()
    return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(),attr) else ''

def xcaf_product_map(source, solids):
    doc=TDocStd_Document(TCollection_ExtendedString('XCAF'))
    reader=STEPCAFControl_Reader(); reader.SetNameMode(True)
    assert reader.ReadFile(str(source))==IFSelect_RetDone
    assert reader.Transfer(doc)
    st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels=TDF_LabelSequence(); st.GetFreeShapes(labels)
    records=[]
    signatures=[(s.Center(),s.Volume()) for s in solids]
    def walk(label, loc, path):
        name=label_name(label)
        if st.IsReference_s(label):
            target=TDF_Label(); st.GetReferredShape_s(label,target)
            walk(target,loc.Multiplied(st.GetLocation_s(label)),path+[name])
        elif st.IsAssembly_s(label):
            children=TDF_LabelSequence(); st.GetComponents_s(label,children)
            for i in range(1,children.Length()+1): walk(children.Value(i),loc,path+[name])
        else:
            raw=st.GetShape_s(label)
            if raw.IsNull(): return
            shape=norm(cq.Shape.cast(raw.Moved(loc)))
            for s in shape.Solids():
                c,v=s.Center(),s.Volume()
                matches=[i for i,(c2,v2) in enumerate(signatures) if (c-c2).Length<1e-5 and abs(v-v2)<max(1e-4,abs(v)*1e-7)]
                records.append({'product':name,'assembly_path':path,'matched_import_solid_ids':matches,'bbox_mm':bb(s),'volume_mm3':round(v,7)})
    for i in range(1,labels.Length()+1): walk(labels.Value(i),TopLoc_Location(),[])
    return records

def face_records(s):
    records=[]
    for fi,f in enumerate(s.Faces()):
        surf=BRepAdaptor_Surface(f.wrapped); typ=surf.GetType()
        rec={'face':fi,'type':str(typ),'bbox_mm':bb(f),'area_mm2':round(f.Area(),7)}
        if typ==GeomAbs_Cylinder:
            c=surf.Cylinder(); a=c.Axis(); l=a.Location(); d=a.Direction()
            rec.update(diameter_mm=round(2*c.Radius(),7),axis_location_mm=[l.X(),l.Y(),l.Z()],axis_direction=[d.X(),d.Y(),d.Z()])
        elif typ==GeomAbs_Cone:
            c=surf.Cone(); rec['half_angle_degrees']=math.degrees(c.SemiAngle())
        elif typ==GeomAbs_Plane:
            n=f.normalAt(); rec['normal']=[n.x,n.y,n.z]
        records.append(rec)
    return records

def true_section(s,y):
    plane=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0))
    return cq.Workplane(plane).add(s).section().val()

def section_svg(solids, station, out):
    x,y=station['axis_xy_mm']; idx=station['foot_solid']; stand=station['standoff_solid']; screw=station['existing_screw_solid']
    clip=cq.Workplane('XY').box(18,18,21).translate((x,y,5.5)).val()
    palette=[(0,'#5b748b','Bottom pan'),(stand,'#18785a','Standoff'),(screw,'#b66312','Existing PCB screw'),(station['pcb_solid'],'#946baf','PCB'),(idx,'#8d969d','Adhesive foot (remove for access)')]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="780" viewBox="0 0 1080 780">', '<rect width="1080" height="780" fill="white"/>', '<style>text{font-family:Arial,sans-serif;fill:#152333} .small{font-size:16px} .note{font-size:19px} .title{font-size:27px;font-weight:bold}</style>']
    def tx(a): return 390+(a-x)*22
    def tz(a): return 545-a*22
    svg += [f'<text x="36" y="44" class="title">B210 underside / foot solid {idx}: true X–Z section</text>',f'<text x="36" y="77" class="note">Section Y = {y:.4f} mm; axis X = {x:.4f} mm. Normalized pan underside datum Z = 0.</text>']
    sec_records=[]
    for si,color,name in palette:
        local=solids[si].intersect(clip)
        if not local.Solids(): continue
        section=true_section(local,y)
        sec_records.append((si,section))
        for e in section.Edges():
            pts,_=e.sample(max(2,int(e.Length()/0.03)+1))
            path=' '.join(('M' if j==0 else 'L')+f'{tx(p.x):.3f},{tz(p.z):.3f}' for j,p in enumerate(pts))
            svg.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2"/>')
        legend_y=140+palette.index((si,color,name))*36
        svg += [f'<line x1="685" y1="{legend_y}" x2="725" y2="{legend_y}" stroke="{color}" stroke-width="4"/>',f'<text x="737" y="{legend_y+6}" class="small">{name} [{si}]</text>']
    svg += [f'<line x1="{tx(x)}" y1="180" x2="{tx(x)}" y2="657" stroke="#405069" stroke-dasharray="10 5 2 5"/>',f'<line x1="100" y1="{tz(0)}" x2="645" y2="{tz(0)}" stroke="#4569a5" stroke-dasharray="5 4"/>',f'<text x="88" y="{tz(0)+24}" class="small">Datum Z = 0</text>']
    for z,label in [(1.21,'Pan top 1.210'),(3.5738,'Screw tip 3.5738'),(6,'Bore step 6.000'),(10,'Standoff top / PCB underside 10.000')]:
        svg += [f'<line x1="{tx(x+2)}" y1="{tz(z)}" x2="647" y2="{tz(z)}" stroke="#738091" stroke-width=".8"/>',f'<text x="657" y="{tz(z)+5}" class="small">{label} mm</text>']
    svg += ['<text x="36" y="706" class="note">3.5738 mm is nominal geometric separation to an existing screw, NOT allowable penetration.</text>', '<text x="36" y="737" class="small">Smooth bore geometry does not establish thread form, accessibility, engagement or structural capacity.</text>', '</svg>']
    out.write_text('\n'.join(svg),encoding='utf8')
    return sec_records

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,default=SOURCE); args=ap.parse_args()
    HERE.mkdir(parents=True,exist_ok=True); sectiondir=HERE/'sections'; sectiondir.mkdir(exist_ok=True)
    data=args.source.read_bytes(); text=data.decode('utf8',errors='replace'); digest=hashlib.sha256(data).hexdigest()
    print('Fresh importing original STEP...',flush=True)
    original=cq.importers.importStep(str(args.source)).val(); model=norm(original); solids=model.Solids()
    report={'source':str(args.source),'source_sha256':digest,'generated_by':'under_feet_audit.py / fresh source STEP import; all lengths mm',
        'frame':'Rotate X +90 deg, then Z +180 deg; translate (58.5005,80.6355,1.210) mm. Pan underside Z=0, +Y RF.',
        'unit_declarations':sorted(set(re.findall(r'[^;\n]*SI_UNIT\([^;]+;',text))),
        'solid_count':len(solids),'model_valid':model.isValid(),'assembly_bbox_mm':bb(model),
        'product_records_related_to_mount':re.findall(r'#[0-9]+=PRODUCT\([^;]*(?:SOS_M3|FOOT_RUBBER|M3X8MM|BOTTOM_CVR|PCB_REV6)[^;]*;',text)}
    assert len(solids)==196, 'Source assembly changed; remap solid identities.'
    ids=[0,5,6,7,8,9,150,151,152,153,174,175,176,177]
    report['inspected_bodies']=[{'solid':i,'bbox_mm':bb(solids[i]),'volume_mm3':round(solids[i].Volume(),7),'valid':solids[i].isValid(),'faces':face_records(solids[i])} for i in ids]
    stations=[]
    for foot,stand,screw in [(174,7,150),(175,5,151),(176,6,152),(177,8,153)]:
        fb=bb(solids[foot]); x=sum(fb['x'])/2; y=sum(fb['y'])/2
        # Find the closest existing solid in a slender coaxial cylinder, excluding rubber and the open standoff.
        probe=cq.Solid.makeCylinder(0.01,15,cq.Vector(x,y,0),cq.Vector(0,0,1))
        obstacles=[]
        for i,s in enumerate(solids):
            b=bb(s)
            if i in FOOT_IDS or b['x'][0]>x or b['x'][1]<x or b['y'][0]>y or b['y'][1]<y or b['z'][0]>15: continue
            inter=s.intersect(probe)
            if inter.Volume()>1e-9: obstacles.append({'solid':i,'first_z_mm':bb(inter)['z'][0],'intersection_volume_mm3':inter.Volume()})
        obstacles.sort(key=lambda o:o['first_z_mm'])
        pcb_candidates=[i for i,s in enumerate(solids) if abs(bb(s)['z'][0]-10)<.001 and abs(bb(s)['z'][1]-11.5748)<.001 and s.Volume()>5000]
        pcb=pcb_candidates[0]
        st={'foot_solid':foot,'standoff_solid':stand,'existing_screw_solid':screw,'pcb_solid':pcb,'axis_xy_mm':[round(x,7),round(y,7)],
            'foot_bbox_mm':fb,'standoff_bbox_mm':bb(solids[stand]),'existing_screw_bbox_mm':bb(solids[screw]),'pan_contact_z_mm':0.0,
            'coaxial_probe_radius_mm':.01,'coaxial_obstacles':obstacles,
            'geometric_screw_tip_height_mm':bb(solids[screw])['z'][0],
            'allowable_penetration_mm':None,'usable_thread_engagement_mm':None,
            'thread_caution':'Product identifiers and smooth bore diameters do not establish actual thread specification, access from below, usable depth, or pullout capacity.'}
        stations.append(st)
    report['stations']=stations
    report['axis_pitch_mm']={'x':round(stations[1]['axis_xy_mm'][0]-stations[0]['axis_xy_mm'][0],7),'y':round(stations[1]['axis_xy_mm'][1]-stations[2]['axis_xy_mm'][1],7)}
    report['nonfoot_bodies_below_pan']=[{'solid':i,'bbox_mm':bb(s)} for i,s in enumerate(solids) if i not in FOOT_IDS and bb(s)['z'][0]<-1e-5]
    report['minimum_nonfoot_z_mm']=min(bb(s)['z'][0] for i,s in enumerate(solids) if i not in FOOT_IDS)
    report['interface_note']='No modeled non-foot body extends below pan Z=0; actual clinch-head proudness, pan flatness and adhesive residue need physical confirmation.'
    report['fresh_source_unchanged']=hashlib.sha256(args.source.read_bytes()).hexdigest()==digest
    (HERE/'under_feet_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({k:report[k] for k in ['source_sha256','solid_count','model_valid','axis_pitch_mm','minimum_nonfoot_z_mm','nonfoot_bodies_below_pan']}),flush=True)
    print(json.dumps(stations,indent=2),flush=True)
    print('Mapping XCAF product definitions to imported solids...',flush=True)
    products=xcaf_product_map(args.source,solids)
    report['product_map_selected']=[p for p in products if any(i in ids for i in p['matched_import_solid_ids'])]
    report['product_map_unmatched_count']=sum(not p['matched_import_solid_ids'] for p in products)
    (HERE/'under_feet_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report['product_map_selected'],indent=2),flush=True)
    import ezdxf
    dxf=ezdxf.new('R2010'); dxf.units=4; msp=dxf.modelspace()
    for st in stations:
        sections=section_svg(solids,st,sectiondir/f"foot_{st['foot_solid']}_xz.svg")
        for si,sec in sections:
            layer=f'FOOT_{st["foot_solid"]}_SOLID_{si}'
            dxf.layers.new(layer)
            for e in sec.Edges():
                pts,_=e.sample(max(2,int(e.Length()/0.03)+1))
                msp.add_lwpolyline([(p.x+35*FOOT_IDS.index(st['foot_solid']),p.z) for p in pts],dxfattribs={'layer':layer})
    dxf.saveas(str(sectiondir/'under_feet_sections_mm.dxf'))
    assert not dxf.audit().errors
    print('Finished fresh evidence and four true CAD sections.',flush=True)

if __name__=='__main__': main()
