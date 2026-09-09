"""Additional P2 pan-only capture, purchased-part clashes and CAD mass screen."""
from pathlib import Path
import argparse,json,math
import model as m
import vertical_adapter as va

def box(s):
    b=s.BoundingBox();return [b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax]

def run(out):
    p=m.load_params();flat=m.flat_items(p);upright=m.upright_items(p,flat);checks=[]
    def ck(n,ok,data):
        checks.append(dict(id=n,status='PASS' if ok else 'FAIL',measured=data));print(checks[-1],flush=True)
    base=m.create_base(p);pan=m.get_device(p).Solids()[0]
    up=p['retention_up_screen'];down=-p['film_thickness'];cy=p['center_y'];zpan=p['device_pan_z']
    tilt=math.degrees(math.atan((up-down)/p['support_y_pitch']));zm=(up+down)/2
    rows=[]
    for sign in [-1,1]:
        pose=pan.rotate((0,cy,zpan),(1,cy,zpan),sign*tilt).translate((0,sign*3,zm))
        region=m.block(80,18,p['end_stop_top']-p['pocket_floor_z'],0,
            p['pocket_ymax']+9 if sign>0 else p['pocket_ymin']-9,p['pocket_floor_z'])
        hit=pose.intersect(base.intersect(region));v=hit.Volume()
        rows.append(dict(sign=sign,pan_only_obstruction_mm3=v,contact_bbox_mm=box(hit) if v else None))
    ck('pan_only_positive_end_capture',min(r['pan_only_obstruction_mm3'] for r in rows)>.1,
       dict(up=up,down=down,tilt_deg=tilt,escape_y_mm=3,rows=rows))
    # Exact component clashes, excluding only nominal shank vs female thread pairs.
    for label,scene in [('flat',flat),('upright',upright)]:
        nondev=[(n,s,k) for n,s,k in scene if k!='device'];hits=[];expected=[]
        for i,(n,s,k) in enumerate(nondev):
            b=s.BoundingBox()
            for nn,ss,kk in nondev[i+1:]:
                bb=ss.BoundingBox()
                if any(getattr(b,a+'max')<=getattr(bb,a+'min')+.00001 or getattr(bb,a+'max')<=getattr(b,a+'min')+.00001 for a in 'xyz'):continue
                v=s.intersect(ss).Volume()
                if v<.001:continue
                pair=n+' '+nn
                threaded=('retainer_' in pair and ('M01_base' in pair)) or ('locknut' in pair and ('M5x25' in pair or 'M5x30' in pair))
                (expected if threaded else hits).append([n,nn,v])
        ck(label+'_nondevice_component_clashes',not hits,dict(unintended=hits,intended_thread_regions=expected))
    # Nominal body volume only, with explicit density assumptions; not weighed mass.
    masses={}
    for label,scene in [('flat',flat),('upright',upright)]:
        rows=[]
        for n,s,k in scene:
            if k in ('device','film'):continue
            rho=8e-6 if k=='hardware' else 2.7e-6
            rows.append(dict(name=n,kind=k,volume_mm3=s.Volume(),assumed_density_kg_mm3=rho,mass_kg=s.Volume()*rho))
        masses[label]=dict(parts=rows,estimated_mount_mass_kg=sum(r['mass_kg'] for r in rows))
    masses['P1_upright_baseline_mass_kg']=1.1151635338671697
    masses['upright_mass_reduction_percent']=100*(1-masses['upright']['estimated_mount_mass_kg']/masses['P1_upright_baseline_mass_kg'])
    masses['limitation']='CAD volume with aluminum2700 and hardware8000kg/m3 assumptions; films/coatings omitted, threads simplified. Purchased aluminum spacer alloy unknown. Actual weighing required.'
    (out/'mass_screen.json').write_text(json.dumps(masses,indent=2))
    result=dict(status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',checks=checks,
       limitations=['Pan obstruction is a quasistatic witness, not contact capacity, impact or continuous6DOF escape validation.',
                    'Helical threads not modeled; intended male/female engagement excluded explicitly.'])
    (out/'additional_verification.json').write_text(json.dumps(result,indent=2))
    if result['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=m.HERE/'exports');run(ap.parse_args().out)
