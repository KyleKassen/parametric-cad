"""Fresh import and nominal side interface audit of the unchanged NSP-1600 STEP.

All component indices are original import order, zero based. Geometry is not
thread capacity, permitted intrusion, electrical clearance or tested contact.
Run with C:/venvs/cadquery/Scripts/python.exe audit_side_mount.py.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
SOURCE=Path('C:/Users/KyleKassen/OneDrive - Ataero/Shared Documents - Ataero San Antonio/06 R&D Products/NEW R&D/04 Shared Engineering/02 Component Library/Power Supplies/Mean Well/Mean Well - NSP-1600 0417 3D Model.stp')
SHA='d421a1e7fb7a3b5fd2e12588484a2e970456301955c0a17f55be6d56324dd8a0'
TR=(-66.7869113,-354.1518617,-1.4999997)


def bb(s):
    b=s.BoundingBox()
    return {a:[round(getattr(b,a+'min'),8),round(getattr(b,a+'max'),8)] for a in 'xyz'}


def faces(s):
    result=[]
    for i,f in enumerate(s.Faces()):
        a=BRepAdaptor_Surface(f.wrapped);typ=a.GetType()
        r={'face_index_zero_based':i,'type':str(typ),'bbox_mm':bb(f),'area_mm2':f.Area()}
        if typ==GeomAbs_Plane:
            r['normal']=[round(x,7) for x in f.normalAt().toTuple()]
            r['wire_bboxes_mm']=[bb(w) for w in f.Wires()]
        elif typ==GeomAbs_Cylinder:
            c=a.Cylinder();loc=c.Axis().Location();d=c.Axis().Direction()
            r.update(diameter_mm=round(2*c.Radius(),8),axis_location_mm=[loc.X(),loc.Y(),loc.Z()],axis_direction=[d.X(),d.Y(),d.Z()],u_span_radians=a.LastUParameter()-a.FirstUParameter())
        elif typ==GeomAbs_Cone:
            r['semi_angle_deg']=math.degrees(a.Cone().SemiAngle())
        result.append(r)
    return result


def main():
    data=SOURCE.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
    original=cq.importers.importStep(str(SOURCE)).val()
    src=original.Solids();assert len(src)==19 and all(s.isValid() for s in src)
    n=[s.translate(TR) for s in src]
    records=[{'source_solid_index_zero_based':i,'bbox_mm':bb(s),'faces':faces(s)} for i,s in enumerate(n)]
    report={'units':'mm','unit_statements':re.findall(r'[^;\n]*SI_UNIT\([^;]+;',data.decode('utf8',errors='replace')),'source':str(SOURCE),'source_sha256':SHA,'source_count':len(src),'normalization_translation_mm':TR,'normalized_bbox_mm':bb(cq.Compound.makeCompound(n)),'source_solids':records,'sides':[]}
    for sign in [-1,1]:
        side={'outward_normal':[sign,0,0],'contact_plane_x_mm':sign*42.5,'coplanar_faces':[],'other_protrusions':[],'mount_holes':[]}
        for rec,s in zip(records,n):
            for f in rec['faces']:
                if f['type']==str(GeomAbs_Plane) and max(abs(v-sign*42.5) for v in f['bbox_mm']['x'])<1e-5:
                    side['coplanar_faces'].append({'source_solid_index_zero_based':rec['source_solid_index_zero_based'],**f})
            probe=cq.Workplane('XY').box(5,400,70).translate((sign*45, -140,20)).val()
            hit=s.intersect(probe)
            if hit.Volume()>1e-6:side['other_protrusions'].append({'source_solid_index_zero_based':rec['source_solid_index_zero_based'],'bbox_mm':bb(hit),'volume_mm3':hit.Volume()})
        for y in [-5.8,-257.8]:
            z=22.8;local=[]
            for rec in records:
                for f in rec['faces']:
                    b=f['bbox_mm']
                    if b['y'][0]>=y-4 and b['y'][1]<=y+4 and b['z'][0]>=z-4 and b['z'][1]<=z+4 and b['x'][0]<sign*42.5+7 and b['x'][1]>sign*42.5-7:
                        local.append({'source_solid_index_zero_based':rec['source_solid_index_zero_based'],**f})
            hits={}
            for radius in [.01,2]:
                probe=cq.Solid.makeCylinder(radius,85,cq.Vector(sign*42.5,y,z),cq.Vector(-sign,0,0));hh=[]
                for i,s in enumerate(n):
                    h=s.intersect(probe)
                    if h.Volume()>1e-9:
                        intervals=[sorted([(sign*42.5-x)*sign for x in bb(t)['x']]) for t in h.Solids()]
                        hh.append({'source_solid_index_zero_based':i,'inward_material_intervals_mm':sorted(intervals)})
                hits[str(radius)]=sorted(hh,key=lambda h:h['inward_material_intervals_mm'][0][0])
            side['mount_holes'].append({'nominal_axis_xyz_mm':[sign*42.5,y,z],'local_faces':local,'material_by_probe_radius_mm':hits,'manufacturer_limit_mm':5,'manufacturer_recommended_thread':'M4','manufacturer_recommended_torque_kgf_cm':[7,10],'thread_pitch_and_capacity':'Not established by model or mechanical drawing.'})
        side['coplanar_area_mm2']=sum(f['area_mm2'] for f in side['coplanar_faces'])
        report['sides'].append(side)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
    (HERE/'side_geometry_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    quick=[]
    for side in report['sides']:
        quick.append({'plane':side['contact_plane_x_mm'],'contacts':[{'solid':f['source_solid_index_zero_based'],'area':f['area_mm2'],'bbox':f['bbox_mm'],'wires':len(f['wire_bboxes_mm'])} for f in side['coplanar_faces']], 'protrusions':side['other_protrusions'], 'holes':[{'axis':h['nominal_axis_xyz_mm'],'cylinders':[f for f in h['local_faces'] if 'diameter_mm' in f],'hits':h['material_by_probe_radius_mm']} for h in side['mount_holes']]})
    print(json.dumps(quick,indent=2),flush=True)


if __name__=='__main__':main()
