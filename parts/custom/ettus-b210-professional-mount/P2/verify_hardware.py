"""Supplementary purchased-hardware clearance and export/scale checks."""
from pathlib import Path
import argparse,json
import cadquery as cq
import model as m
import vertical_adapter as va


def main(out):
    p=m.load_params(); flat=m.flat_items(p); upright=m.upright_items(p,flat); checks=[]
    def ck(n,ok,data):
        checks.append({'id':n,'status':'PASS' if ok else 'FAIL','measured':data})
        print(checks[-1],flush=True)
    # Spatial filtering excludes distant hardware before exact BREP intersection.
    for name,scene in [('flat',flat),('upright',upright)]:
        device=next(s for n,s,k in scene if k=='device'); db=device.BoundingBox()
        collisions=[]
        for n,s,k in scene:
            if k!='hardware':continue
            b=s.BoundingBox()
            if any(getattr(b,a+'max')<getattr(db,a+'min') or getattr(b,a+'min')>getattr(db,a+'max') for a in 'xyz'):
                continue
            v=s.intersect(device).Volume()
            if v>.001:collisions.append([n,v])
        ck(name+'_hardware_vs_device',not collisions,collisions)
    # Check exact declared scale after STEP import, against drawing dimensions.
    for n,expected in [('B210_M01_base_P2',[160,180,9.2]),('B210_M02_retainer_P2',[160,20,5]),
                       ('B210_M03_spacer_P2',[10,10,30]),('B210_M04_film_P2',[16,20,.2])]:
        s=cq.importers.importStep(str(out/(n+'.step'))).val();b=s.BoundingBox();v=[b.xlen,b.ylen,b.zlen]
        ck(n+'_mm_scale',max(abs(a-b) for a,b in zip(v,expected))<.001,v)
    # Upright foot holes are installed before the cradle; sockets 14mm OD.
    adapters=list(va.build_adapter_pair().values())
    for y in va.PARAMS['bracket_y_centers']:
        for x in va.PARAMS['foot_hole_x']:
            tool=m.cylinder(14,80,x,y,va.PARAMS['foot_bolt_boss_top']+6.4)
            vv=sum(tool.intersect(s).Volume() for s in adapters)
            ck(f'foot_driver_preinstall_{x}_{y}',vv<.001,vv)
    # Web screw driver approaches from the rear; front nut uses14mm socket.
    obstacles=[s for n,s,k in upright if k!='hardware']
    for y in va.PARAMS['bracket_y_centers']:
        for z in va.PARAMS['web_hole_z']:
            rear=m.cylinder(14,60).rotate((0,0,0),(0,1,0),-90).translate((-12,y,z))
            front=m.cylinder(14,30).rotate((0,0,0),(0,1,0),90).translate((p['base_thickness']+1,y,z))
            for label,tool in [('rear',rear),('nut',front)]:
                # Bbox before boolean to speed detailed source assembly checks.
                tb=tool.BoundingBox();total=0
                for s in obstacles:
                    b=s.BoundingBox()
                    if any(getattr(b,a+'max')<getattr(tb,a+'min') or getattr(b,a+'min')>getattr(tb,a+'max') for a in 'xyz'):continue
                    total+=tool.intersect(s).Volume()
                ck(f'web_{label}_tool_{y}_{z}',total<.001,total)
    result={'status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL','checks':checks,
            'limitations':['Threads are represented as clearance/minor bores and nominal shanks; expected engaged-thread intersections are not treated as clashes.',
                           'Purchased head/socket/nut envelopes are nominal; substitute hardware requires recheck.']}
    (out/'hardware_verification.json').write_text(json.dumps(result,indent=2))
    if result['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=m.HERE/'exports');main(ap.parse_args().out)
