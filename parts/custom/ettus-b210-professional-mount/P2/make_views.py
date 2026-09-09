"""Actual CAD assembly views and sections; does not rewrite checked STEP exports."""
from pathlib import Path
import argparse,json
import model as m
from render_support import render_scene,section_cut

def make(out,sections_only=False):
    p=m.load_params();flat=m.flat_items(p);up=m.upright_items(p,flat)
    exploded=[(n,s.translate((0,0,45 if (k not in ('base','device') and not n.startswith(('lower','flat_panel'))) else 0)),k) for n,s,k in flat]
    for name,scene,views in [('flat',flat,('iso','top','front','back','left','right','bottom')),
                             ('upright',up,('iso','front','right')),
                             ('exploded',exploded,('iso',))]:
        if not sections_only:
            render_scene([(s,m.COLORS[k],1) for n,s,k in scene],out/'views',name,views=views,size=1500,axes=False)
    section_checks=[]
    for axis,station in [('Y',m.stations(p)[0]),('X',0)]:
        clipped=[]
        for _,s,k in flat:
            b=s.BoundingBox()
            if getattr(b,axis.lower()+'min')>=station-1e-6:continue
            cut=s if getattr(b,axis.lower()+'max')<=station+1e-6 else section_cut(s,axis,station)
            clipped.append((cut,m.COLORS[k],1))
        from OCP.BRepTools import BRepTools
        for s,_,_ in clipped:
            BRepTools.Clean_s(s.wrapped)
        bb=[s.BoundingBox() for s,_,_ in clipped]
        upper=max(getattr(b,axis.lower()+'max') for b in bb)
        section_checks.append({'axis':axis,'station':station,'maximum_remaining_coordinate_before_display_mesh':upper,'status':'PASS' if upper<=station+.001 else 'FAIL'})
        render_scene(clipped,out/'views','section_'+axis,views=('iso','front' if axis=='Y' else 'left'),size=1500,axes=False)
    (out/'section_verification.json').write_text(json.dumps(section_checks,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=m.HERE/'exports');ap.add_argument('--sections-only',action='store_true');args=ap.parse_args();make(args.out,args.sections_only)
