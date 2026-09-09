"""Source-derived side reference, true sections and metal-contact patch checks."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys
import importlib.util
import cadquery as cq

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('side_audit',HERE/'audit_side_mount.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
TEMP=Path('C:/b210work/nsp1600_side');TEMP.mkdir(parents=True,exist_ok=True)


def transform(s):
    return s.rotate((0,0,0),(0,1,0),90).translate((-20.5,0,42.5))


def main():
    assert hashlib.sha256(a.SOURCE.read_bytes()).hexdigest()==a.SHA
    raw=cq.importers.importStep(str(a.SOURCE)).val().Solids()
    n=[s.translate(a.TR) for s in raw];side=[transform(s) for s in n]
    whole=cq.Compound.makeCompound(side)
    output=HERE/'NSP1600_PLUS_X_SIDE_ORIGINAL_REFERENCE.step'
    cq.exporters.export(whole,str(output));back=cq.importers.importStep(str(output)).val()
    info={'source_sha256':a.SHA,'chosen_side':'Original normalized +X face','side_transform':'Xnew=Zold-20.5;Ynew=Yold;Znew=42.5-Xold. RotationY+90 then translation(-20.5,0,42.5). Original source first translates by(-66.7869113,-354.1518617,-1.4999997).',
      'side_bbox_mm':a.bb(whole),'nominal_mount_axes_xy_mm':[[2.3,-5.8],[2.3,-257.8]],'reimport':{'valid':back.isValid(),'solids':len(back.Solids()),'bbox_mm':a.bb(back),'relative_volume_difference':(back.Volume()-whole.Volume())/whole.Volume()},'contact_patches':[]}
    contact=[]
    for i in [0,17]:
        for f in side[i].Faces():
            b=a.bb(f)
            if max(abs(v) for v in b['z'])<1e-5 and abs(f.normalAt().z)>.999:contact.append((i,f))
    patches=[('front_full_station',[-20.5,20.5],[-21.8,0]),('rear_full_station',[-20.5,20.5],[-273.8,-241.8]),
      ('front_interior_negative_band',[-16,-12.5],[-9.8,-1.8]),('front_interior_positive_band',[7.5,9.5],[-9.8,-1.8]),
      ('front_outer_positive_band',[19.1,20],[-9.8,-1.8]),('rear_interior_negative_band',[-16,-12.5],[-261.8,-253.8]),
      ('rear_interior_positive_band',[7.5,9.5],[-251.8,-243.8]),
      ('front_requested_right_toe',[17.3,18.3],[-9.8,-1.8]),('front_requested_left_toe',[-13.7,-12.7],[-9.8,-1.8]),
      ('rear_requested_right_toe',[17.3,18.3],[-261.8,-253.8]),('rear_requested_left_toe',[-13.7,-12.7],[-261.8,-253.8]),
      ('front_alternate_right_toe',[17.3,18.3],[-11.8,-9.8]),('rear_alternate_right_toe',[17.3,18.3],[-254.8,-252.8]),
      ('rear_outer_positive_band',[19.1,20],[-261.8,-253.8])]
    for name,x,y in patches:
        clip=cq.Workplane('XY').box(x[1]-x[0],y[1]-y[0],2).translate(((x[0]+x[1])/2,(y[0]+y[1])/2,0)).val()
        parts=[]
        for i,f in contact:
            hit=f.intersect(clip)
            if hit.Area()>1e-8:parts.append({'source_solid_index_zero_based':i,'area_mm2':hit.Area(),'bbox_mm':a.bb(hit)})
        area=sum(v['area_mm2'] for v in parts);gross=(x[1]-x[0])*(y[1]-y[0])
        info['contact_patches'].append({'id':name,'rect_x_mm':x,'rect_y_mm':y,'geometric_rect_area_mm2':gross,'actual_coplanar_metal_area_mm2':area,'full_rectangle_supported':abs(area-gross)<1e-5,'metal_parts':parts,'minimum_lever_to_hole_line_x2p3_mm':min(abs(v-2.3) for v in x) if not(x[0]<=2.3<=x[1]) else 0})
    (HERE/'side_reference_and_contacts.json').write_text(json.dumps(info,indent=2),encoding='utf8')
    print(json.dumps({'reimport':info['reimport'],'contact_patches':[{'id':r['id'],'area':r['actual_coplanar_metal_area_mm2'],'full':r['full_rectangle_supported']} for r in info['contact_patches']]},indent=2),flush=True)
    # Actual section curves at each designated hole, for both candidate sides.
    secdir=HERE/'sections';secdir.mkdir(exist_ok=True)
    for sign in [-1,1]:
        for station,y in [('front',-5.8),('rear',-257.8)]:
            svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="720" viewBox="0 0 1500 720">','<rect width="1500" height="720" fill="white"/>','<style>text{font-family:Helvetica,sans-serif;font-size:20px;fill:#173343}.title{font-size:27px;font-weight:bold}</style>',f'<text x="30" y="42" class="title">NSP-1600 {sign:+d}X side / {station} designated M4 station / true source section</text>',f'<text x="30" y="79">Y={y:.1f}, Z=22.8 mm. Horizontal: inward depth from side face. Vertical: original Z. Uniform scale.</text>']
            tx=lambda x:300+(42.5-sign*x)*30;tz=lambda z:115+(32-z)*30
            clip=cq.Workplane('XY').box(14,8,16).translate((sign*38.5,y,24)).val()
            for i,s in enumerate(n):
                loc=s.intersect(clip)
                if loc.Volume()<1e-8:continue
                plane=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0));section=cq.Workplane(plane).add(loc).section().val()
                for edge in section.Edges():
                    pts,_=edge.sample(max(2,math.ceil(edge.Length()/.02)+1));d=' '.join(('M' if j==0 else 'L')+f'{tx(p.x):.3f},{tz(p.z):.3f}' for j,p in enumerate(pts))
                    svg.append(f'<path d="{d}" fill="none" stroke="{("#187752" if i==17 else "#ac6b27")}" stroke-width="2"/>')
            for depth in [0,2.1,5,7.5]:
                xx=300+depth*30;svg.append(f'<line x1="{xx}" x2="{xx}" y1="110" y2="615" stroke="#718998" stroke-dasharray="7 5"/><text x="{xx}" y="647" text-anchor="middle">{depth:g}</text>')
            svg.append(f'<line x1="245" x2="650" y1="{tz(22.8)}" y2="{tz(22.8)}" stroke="#718998" stroke-dasharray="10 4 2 4"/>')
            notes=['Green: main side casing. Ochre: other source component.','Manufacturer group 2: M4, penetration max 5 mm.','Recommended mounting torque 7-10 kgf cm.','Model is not evidence of thread capacity or electrical spacing.']
            if station=='front':notes+=['Entry surface: depth 0..0.72.','Nominal DIA3.1 cylinder: depth 0.72..2.10.','No modeled helical thread or full engagement guarantee.']
            else:notes+=['Source is DIA5 through a 1.20 mm wall.','No rear female thread or underlying insert is modeled.','Confirm rear mounting feature on the received PSU.']
            for i,line in enumerate(notes):svg.append(f'<text x="760" y="{160+i*43}">{line}</text>')
            svg.append('<text x="30" y="698">Depth labels are nominal millimetres from actual source surfaces, not accepted screw lengths. No physical test performed.</text></svg>')
            (secdir/f'{"plus" if sign>0 else "minus"}_X_{station}.svg').write_text('\n'.join(svg),encoding='utf8')
    sys.path.insert(0,str(a.ROOT));from lib.render_step import render_scene
    center=whole.BoundingBox().center
    parts=[(s.translate((-center.x,-center.y,-center.z)), (.37,.56,.47) if i in [0,17,18] else (.6,.62,.66) if i==16 else (.23,.28,.32) if i in [14,15] else (.68,.5,.25),1) for i,s in enumerate(side)]
    paths=render_scene(parts,TEMP/'views','NSP1600_side_source',size=1100,axes=False)
    out=HERE/'views';out.mkdir(exist_ok=True)
    for f in paths:shutil.copyfile(f,out/f.name)
    # SVG rasterization creates temporary conversion PDFs only, no PDF deliverable.
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg
    import subprocess
    for f in secdir.glob('*.svg'):
        pdf=TEMP/(f.stem+'.pdf');renderPDF.drawToFile(svg2rlg(str(f)),str(pdf));subprocess.run(['pdftoppm','-scale-to','1500','-png','-singlefile',str(pdf),str(TEMP/f.stem)],check=True);shutil.copyfile(TEMP/(f.stem+'.png'),secdir/(f.stem+'.png'))
    assert hashlib.sha256(a.SOURCE.read_bytes()).hexdigest()==a.SHA
    print('Reference STEP, actual sections and context views completed.',flush=True)


if __name__=='__main__':main()
