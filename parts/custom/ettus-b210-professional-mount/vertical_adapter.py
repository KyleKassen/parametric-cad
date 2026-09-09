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
      'overall_bbox_one':{'x':[-t,p['foot_tip_x']],'y':[-p['strip_width']/2,p['strip_width']/2],'z':[0,h]},
      'finished_web_hole_centers':[[0,y,z] for y in p['bracket_y_centers'] for z in p['web_hole_z']],
      'finished_foot_hole_centers':[[x,y,0] for y in p['bracket_y_centers'] for x in p['foot_hole_x']],
      'manufacturing_route':p['manufacturing_route']}

def build_adapter(p=None):
    p=_p(p);t=p['web_t'];ft=p['foot_t'];r=p['inside_radius'];w=p['strip_width'];h=p['overall_height'];tip=p['foot_tip_x'];q=math.sqrt(2)
    profile=(cq.Workplane('XZ').moveTo(-t,0).lineTo(tip,0).lineTo(tip,ft).lineTo(r,ft)
      .threePointArc((r-r/q,ft+r-r/q),(0,ft+r)).lineTo(0,h).lineTo(-t,h).close())
    s=profile.extrude(w).translate((0,w/2,0)).val();chosen=[]
    for e in s.Edges():
        b=e.BoundingBox()
        if (abs(b.ymax-b.ymin)<1e-6 and abs(abs(b.ymin)-w/2)<1e-5 and
            ((abs(b.zmin-h)<1e-5 and abs(b.zmax-h)<1e-5) or
             (abs(b.xmin-tip)<1e-5 and abs(b.xmax-tip)<1e-5))): chosen.append(e)
    s=s.fillet(p['free_corner_radius'],chosen)
    for z in p['web_hole_z']:
        drill=cq.Workplane('YZ').circle(p['clearance_hole_d']/2).extrude(t+4).translate((-t-2,0,z)).val();s=s.cut(drill)
    for x in p['foot_hole_x']:
        drill=cq.Workplane('XY').circle(p['clearance_hole_d']/2).extrude(ft+4).translate((x,0,-2)).val();s=s.cut(drill)
    return s.clean()

def build_adapter_pair(p=None):
    p=_p(p);s=build_adapter(p)
    return {f'upright_adapter_{i+1}':s.translate((0,y,0)) for i,y in enumerate(p['bracket_y_centers'])}

def export_profile_dxf(path,p=None):
    import ezdxf
    p=_p(p);t=p['web_t'];ft=p['foot_t'];r=p['inside_radius'];h=p['overall_height'];tip=p['foot_tip_x']
    doc=ezdxf.new('R2010');doc.units=ezdxf.units.MM
    for n,c in [('PROFILE',7),('REFERENCE_HOLES',3),('NOTES',5)]:doc.layers.new(n,dxfattribs={'color':c})
    ms=doc.modelspace();a={'layer':'PROFILE'};points=[(-t,0),(tip,0),(tip,ft),(r,ft)]
    for st,en in zip(points,points[1:]):ms.add_line(st,en,dxfattribs=a)
    ms.add_arc((r,ft+r),r,180,270,dxfattribs=a)
    for st,en in [((0,ft+r),(0,h)),((0,h),(-t,h)),((-t,h),(-t,0))]:ms.add_line(st,en,dxfattribs=a)
    for z in p['web_hole_z']:ms.add_line((-t-3,z),(3,z),dxfattribs={'layer':'REFERENCE_HOLES'})
    for x in p['foot_hole_x']:ms.add_line((x,-3),(x,ft+3),dxfattribs={'layer':'REFERENCE_HOLES'})
    notes=['P1 UPRIGHT ADAPTER - QTY 2 IDENTICAL - mm',p['material'],
      f'Side profile XZ extruded width {p["strip_width"]:.1f} along Y. PROFILE layer only.',
      'NOT A SHEETMETAL FLAT. No bend allowance or K-factor.',
      'Four 5.5 THRU holes normal to web/foot; centers Y0; see finished drawing.',
      'Free top and foot end corners R3 across width. Deburr edges 0.2-0.5.',
      'Rough 75 x 180 x 38.1 stock; finish profile including R6 root; finish width 36.',
      'Dimensions after finish; general +/-0.2; hole positions +/-0.15; hole D +0.1/-0.',
      'Web and foot 8.00 +/-0.05; minimum7.95 after finish. Black anodize10-15um.',
      'Web mount face perpendicular to foot datum 0.1 over full height.']
    for i,txt in enumerate(notes):ms.add_text(txt,dxfattribs={'height':2.5,'layer':'NOTES','insert':(80,h-5-5*i)})
    doc.saveas(str(path))

def main():
    out=HERE/'exports';out.mkdir(exist_ok=True);s=build_adapter();pair=build_adapter_pair();m=adapter_metrics()
    paths={'machined':out/'adapter_machined.step','pair':out/'adapter_pair.step'}
    cq.exporters.export(s,str(paths['machined']));cq.exporters.export(cq.Compound.makeCompound(list(pair.values())),str(paths['pair']))
    export_profile_dxf(out/'adapter_side_profile.dxf')
    checks={'machined_valid':s.isValid(),'machined_solids':len(s.Solids()),'volume_mm3':s.Volume(),
       'pair_intersection_volume_mm3':list(pair.values())[0].intersect(list(pair.values())[1]).Volume(),
       'profile_dxf_units':'millimeters','profile_entities':7,'metrics':m}
    for k,path in paths.items():
        reopened=cq.importers.importStep(str(path)).val();b=reopened.BoundingBox()
        checks[k+'_reopen']={'valid':reopened.isValid(),'solids':len(reopened.Solids()),'size_mm':[b.xlen,b.ylen,b.zlen]}
    (out/'adapter_verification.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2),flush=True)
    sys.path.insert(0,str(HERE.parents[2]))
    from render_support import render_scene
    render_scene([(s,(.72,.75,.80),1)],HERE/'references/geometry/adapter_views','adapter',size=1100)
    print('Machined adapter exports and seven views complete',flush=True)

if __name__=='__main__':main()
