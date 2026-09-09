"""Fresh source STEP audit. Distances mm; no material/thread/strength inference.

Run with C:/venvs/cadquery/Scripts/python.exe inspection.py [--render]
The source is never modified. Normalized frame: pan underside Z=0; +Y RF face.
"""
from pathlib import Path
import sys, json, hashlib, re, argparse
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
SOURCE=Path(r"C:/Users/KyleKassen/OneDrive - Ataero/Shared Documents - Ataero San Antonio/06 R&D Products/NEW R&D/04 Shared Engineering/02 Component Library/Software-Defined Radios/Ettus Research/Ettus - USRP B210 Full Unit 3D Model.step")
VENDOR=ROOT/'parts/vendor/ettus-usrp-b210/Ettus_USRP_B210_Full_Unit.step'

def bbox(s):
    b=s.BoundingBox()
    return {a:[round(getattr(b,a+'min'),6),round(getattr(b,a+'max'),6)] for a in 'xyz'}

def vec(v): return [round(v.x,6),round(v.y,6),round(v.z,6)]
def norm(s):
    return s.rotate((0,0,0),(1,0,0),90).rotate((0,0,0),(0,0,1),180).translate((58.5005,80.6355,1.210))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--render',action='store_true'); args=ap.parse_args()
    data=SOURCE.read_bytes(); txt=data.decode('utf-8',errors='replace')
    print('Importing original source STEP',flush=True)
    original=cq.importers.importStep(str(SOURCE)).val()
    shape=norm(original); solids=shape.Solids()
    report={'source':str(SOURCE),'source_sha256':hashlib.sha256(data).hexdigest(),
            'vendor_sha256':hashlib.sha256(VENDOR.read_bytes()).hexdigest() if VENDOR.exists() else None,
            'step_unit_declarations': sorted(set(re.findall(r'[^;\n]*SI_UNIT\([^;]+;',txt))),
            'step_product_records':re.findall(r'#[0-9]+=PRODUCT\([^;]+;',txt),
            'transform':'rotate X +90 deg about origin; rotate Z +180 deg about origin; translate (58.5005,80.6355,1.210) mm',
            'source_bbox_mm':bbox(original),'normalized_bbox_mm':bbox(shape),
            'solid_count':len(solids),'face_count':len(shape.Faces()),'shape_valid':shape.isValid(),
            'evidence_type':'measured BREP geometry; configuration identification also requires visual audit',
            'no_inference':'No mass, center of gravity, material, thread, screw penetration or structural capacity is established by this audit.'}
    bodies=[]; planes=[]; cylinders=[]
    for si,s in enumerate(solids):
        bodies.append({'solid':si,'bbox':bbox(s),'volume_mm3':round(s.Volume(),6),'valid':s.isValid(),'centroid_geometric':vec(s.Center())})
        for fi,f in enumerate(s.Faces()):
            surf=BRepAdaptor_Surface(f.wrapped)
            if surf.GetType()==GeomAbs_Plane:
                n=f.normalAt(); nv=vec(n); i=max(range(3),key=lambda k:abs(nv[k]))
                if abs(nv[i])<.999: continue
                fb=bbox(f)
                planes.append({'solid':si,'face':fi,'axis':'xyz'[i],'normal':nv,'coordinate':fb['xyz'[i]][0],
                    'area_mm2':round(f.Area(),5),'bbox':fb,
                    'wires':[bbox(w) for w in f.Wires()]})
            elif surf.GetType()==GeomAbs_Cylinder:
                c=surf.Cylinder(); axis=c.Axis(); d=axis.Direction(); loc=axis.Location()
                cylinders.append({'solid':si,'face':fi,'radius':round(c.Radius(),6),
                    'axis_direction':[round(d.X(),6),round(d.Y(),6),round(d.Z(),6)],
                    'axis_location':[round(loc.X(),6),round(loc.Y(),6),round(loc.Z(),6)],'bbox':bbox(f)})
    report.update({'bodies':bodies,'axis_aligned_planes':planes,'cylinders':cylinders})
    report['invalid_solids']=[b['solid'] for b in bodies if not b['valid']]
    report['exterior_planes_over_100_mm2']=[p for p in planes if p['area_mm2']>100 and
        ((p['axis']=='z' and (p['coordinate']<.01 or p['coordinate']>31.0)) or
         (p['axis']=='x' and abs(p['coordinate'])>59.0) or
         (p['axis']=='y' and abs(p['coordinate'])>75.0))]
    report['feet_candidates_below_pan']=[b for b in bodies if b['bbox']['z'][0]<-1]
    (HERE/'fresh_geometry_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['source_sha256','vendor_sha256','source_bbox_mm','normalized_bbox_mm','solid_count','face_count','shape_valid','invalid_solids','feet_candidates_below_pan']},indent=2),flush=True)
    cq.exporters.export(shape,str(HERE/'source_normalized.step'))
    if args.render:
        sys.path.insert(0,str(ROOT))
        from lib.render_step import render_scene
        colors=[(.58,.62,.67),(.66,.70,.75),(.42,.46,.52)]
        items=[(s, colors[i%3] if s.Volume()>1000 else (.57,.58,.57),1) for i,s in enumerate(solids)]
        render_scene(items,HERE/'views','device',size=1200)
        print('Rendered 7 views',flush=True)

if __name__=='__main__': main()
