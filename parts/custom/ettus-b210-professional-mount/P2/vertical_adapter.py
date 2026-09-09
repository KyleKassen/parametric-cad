"""Editable upright option: two identical one-piece machined 6061-T6 angles.

build_adapter() -> one cq.Shape centered Y0 in installed coordinates.
build_adapter_pair() -> dict of two placed shapes.
transform_cradle(shape) -> flat-cradle part rotated Y+90 then translated Z96.
adapter_metrics() -> drawing/verification dimensions.

Run with CadQuery 2.7 and ezdxf to regenerate exports/adapter_* files.
Profile DXF is a side outline, not a sheet metal flat pattern. Source device untouched.
"""
from pathlib import Path
import json, math, sys
import cadquery as cq

HERE=Path(__file__).resolve().parent
PARAMS=json.loads((HERE/'adapter_params.json').read_text())
def _p(p): return dict(PARAMS if p is None else p)

def transform_cradle(shape,p=None):
    p=_p(p)
    return shape.rotate((0,0,0),(0,1,0),p['cradle_rotation_y_deg']).translate(tuple(p['cradle_translation']))

def adapter_metrics(p=None):
    p=_p(p);t=p['web_t'];ft=p['foot_t'];r=p['inside_radius'];d=p['clearance_hole_d'];h=p['overall_height']
    return {'units':'mm','material':p['material'],'web_t':t,'foot_t':ft,'inside_radius':r,
      'web_and_foot_thickness_tolerance':p['web_and_foot_thickness_tolerance'],
      'minimum_web_and_foot_t_after_finish':p['minimum_web_and_foot_t_after_finish'],
      'finish':p['finish'],
      'root_center_xz':[r,ft+r],'root_tangent_z':ft+r,'root_tangent_x':r,
      'web_lower_hole_edge_to_root_tangent':min(p['web_hole_z'])-d/2-ft-r,
      'web_upper_hole_edge_to_end':h-max(p['web_hole_z'])-d/2,
      'foot_first_hole_edge_to_root_tangent':min(p['foot_hole_x'])-d/2-r,
      'foot_last_hole_edge_to_end':p['foot_tip_x']-max(p['foot_hole_x'])-d/2,
      'hole_edge_to_strip_side':(p['strip_width']-d)/2,
      'cradle_lower_edge_z':p['cradle_translation'][2]-80,
      'cradle_lower_edge_to_root':p['cradle_translation'][2]-80-ft-r,
      'overall_bbox_one':{'x':[-t-p['rear_return_depth'],p['foot_tip_x']],'y':[-p['strip_width']/2,p['strip_width']/2],'z':[0,h]},
      'rib_width':p['rib_width'],'rear_return_depth':p['rear_return_depth'],'foot_rib_height':p['foot_rib_height'],
      'foot_bolt_boss_od':p['foot_bolt_boss_od'],'foot_bolt_boss_top':p['foot_bolt_boss_top'],
      'finished_web_hole_centers':[[0,y,z] for y in p['bracket_y_centers'] for z in p['web_hole_z']],
      'finished_foot_hole_centers':[[x,y,0] for y in p['bracket_y_centers'] for x in p['foot_hole_x']],
      'manufacturing_route':p['manufacturing_route']}

def build_adapter(p=None):
    p=_p(p);t=p['web_t'];ft=p['foot_t'];r=p['inside_radius'];w=p['strip_width'];h=p['overall_height'];tip=p['foot_tip_x'];q=math.sqrt(2)
    profile=(cq.Workplane('XZ').moveTo(-t,0).lineTo(tip,0).lineTo(tip,ft).lineTo(r,ft)
      .threePointArc((r-r/q,ft+r-r/q),(0,ft+r)).lineTo(0,h).lineTo(-t,h).close())
    s=profile.extrude(w).translate((0,w/2,0)).val()
    rw=p['rib_width']; rd=p['rear_return_depth']; rh=p['foot_rib_height']; heel=-t-rd
    def box(dx,dy,dz,x,y,z):
        return cq.Solid.makeBox(dx,dy,dz,cq.Vector(x,y,z))
    # Full-width heel and two integral edge returns form an open channel.
    s=s.fuse(box(rd,w,ft,heel,-w/2,0))
    for y in (-w/2,w/2-rw):
        s=s.fuse(box(rd,rw,h,heel,y,0))
        # Ribs continue through the loaded root; no thin unsupported neck.
        s=s.fuse(box(tip-heel,rw,rh,heel,y,ft))
    s=s.clean()
    # Concave channel corners: added material, obtainable with radius tools.
    inner=w/2-rw; chosen=[]
    for e in s.Edges():
        b=e.BoundingBox()
        at_side=abs(abs(b.ymin)-inner)<1e-5 and abs(b.ymax-b.ymin)<1e-5
        rear=abs(b.xmin+t)<1e-5 and abs(b.xmax-b.xmin)<1e-5 and b.zlen>20
        foot=abs(b.zmin-ft)<1e-5 and abs(b.zmax-b.zmin)<1e-5 and b.xlen>20
        if at_side and (rear or foot):chosen.append(e)
    s=s.fillet(p['pocket_corner_radius'],chosen)
    for x in p['foot_hole_x']:
        s=s.fuse(cq.Solid.makeCylinder(p['foot_bolt_boss_od']/2,p['foot_bolt_boss_top']-ft,cq.Vector(x,0,ft)))
    s=s.clean()
    for z in p['web_hole_z']:
        drill=cq.Workplane('YZ').circle(p['clearance_hole_d']/2).extrude(t+4).translate((-t-2,0,z)).val();s=s.cut(drill)
    for x in p['foot_hole_x']:
        drill=cq.Workplane('XY').circle(p['clearance_hole_d']/2).extrude(p['foot_bolt_boss_top']+4).translate((x,0,-2)).val();s=s.cut(drill)
    return s.clean()

def build_adapter_pair(p=None):
    p=_p(p);s=build_adapter(p)
    return {f'upright_adapter_{i+1}':s.translate((0,y,0)) for i,y in enumerate(p['bracket_y_centers'])}

def export_profile_dxf(path,p=None):
    """Actual mid-width machining section; rib profiles require the STEP/drawing."""
    s=build_adapter(p).rotate((0,0,0),(1,0,0),-90)
    sec=cq.Workplane('XY').newObject([s]).section(0)
    cq.exporters.export(sec,str(path))

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=HERE/'exports');args=ap.parse_args()
    out=args.out;out.mkdir(parents=True,exist_ok=True);s=build_adapter();pair=build_adapter_pair();m=adapter_metrics()
    paths={'machined':out/'adapter_machined.step','pair':out/'adapter_pair.step'}
    cq.exporters.export(s,str(paths['machined']));cq.exporters.export(cq.Compound.makeCompound(list(pair.values())),str(paths['pair']))
    export_profile_dxf(out/'adapter_side_profile.dxf')
    checks={'machined_valid':s.isValid(),'machined_solids':len(s.Solids()),'volume_mm3':s.Volume(),
       'pair_intersection_volume_mm3':list(pair.values())[0].intersect(list(pair.values())[1]).Volume(),
       'profile_dxf_units':'millimeters','profile_note':'Actual center section; not rib envelope or sheetmetal flat','metrics':m}
    for k,path in paths.items():
        reopened=cq.importers.importStep(str(path)).val();b=reopened.BoundingBox()
        checks[k+'_reopen']={'valid':reopened.isValid(),'solids':len(reopened.Solids()),'size_mm':[b.xlen,b.ylen,b.zlen]}
    (out/'adapter_verification.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2),flush=True)
    sys.path.insert(0,str(HERE.parents[2]))
    from render_support import render_scene
    render_scene([(s,(.72,.75,.80),1)],out/'views','adapter',size=1100)
    print('Machined adapter exports and seven views complete',flush=True)

if __name__=='__main__':main()
