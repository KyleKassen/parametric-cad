"""Inspect actual bottom mounting features; export a rigidly normalized source.

Run after audit_nsp1600.py. Source identities are guarded by the exact hash.
All dimensional output is nominal CAD evidence, not an allowable penetration.
"""
from pathlib import Path
import importlib.util,json,hashlib,math,sys,shutil,subprocess
import cadquery as cq

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nsp_audit',HERE/'audit_nsp1600.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
TEMP=Path('C:/b210work/nsp1600');TEMP.mkdir(parents=True,exist_ok=True)

def main():
    r=json.loads((HERE/'nsp1600_source_audit.json').read_text())
    assert hashlib.sha256(a.SOURCE.read_bytes()).hexdigest()==r['source_sha256']=='d421a1e7fb7a3b5fd2e12588484a2e970456301955c0a17f55be6d56324dd8a0'
    original=cq.importers.importStep(str(a.SOURCE)).val();bodies=original.Solids();assert len(bodies)==19
    translation=(-66.7869113,-354.1518617,-1.4999997)
    n=[s.translate(translation) for s in bodies];whole=cq.Compound.makeCompound(n)
    axes=[(-35.,-16.100001),(35.,-16.100001),(-.0000428,-280.800001)]
    owners=[17,17,0]
    report={'source_sha256':r['source_sha256'],'translation_mm':translation,'frame':'X width centre; Y=0 terminal chassis plane; Z=0 bottom contact plane; original axis directions retained.',
      'normalized_bbox_mm':a.bb(whole),'source_solid_indices_zero_based':{'main_shell':17,'fan_bracket':0,'PCB_reference':10,'fans':[14,15],'cover':16,'terminal_panel':18},
      'nominal_mounting_axes_mm':[[-35,-16.1],[35,-16.1],[0,-280.8]],'measured_mounting_axes_mm':axes,'holes':[]}
    for i,((x,y),owner) in enumerate(zip(axes,owners),1):
        candidates=[]
        for f in a.surface_records(n[owner]):
            bb=f['bbox_mm']
            if bb['x'][0]>=x-3 and bb['x'][1]<=x+3 and bb['y'][0]>=y-3 and bb['y'][1]<=y+3 and bb['z'][0]<5:candidates.append(f)
        bores=[f for f in candidates if f.get('diameter_mm')==2.65 and abs(f.get('axis_direction',[0,0,0])[2])>.999]
        assert bores and all(abs(f['axis_location_mm'][0]-x)<1e-6 and abs(f['axis_location_mm'][1]-y)<1e-6 for f in bores), 'Re-identify actual mounting axes from source analytic cylinders.'
        observations={}
        for radius in [.01,1.5]:
            probe=cq.Solid.makeCylinder(radius,43,cq.Vector(x,y,0),cq.Vector(0,0,1));hits=[]
            for j,s in enumerate(n):
                if j==owner:continue
                h=s.intersect(probe)
                if h.Volume()>1e-9:hits.append({'source_solid_index_zero_based':j,'material_z_intervals_mm':sorted(a.bb(t)['z'] for t in h.Solids())})
            hits.sort(key=lambda h:h['material_z_intervals_mm'][0][0]);observations[str(radius)]=hits
        report['holes'].append({'hole_id':f'H{i}','owning_source_solid_index_zero_based':owner,'axis_mm':[x,y],'local_source_faces':candidates,'other_component_axial_material_by_probe_radius_mm':observations,
          'manufacturer_limit_separate_from_geometry':{'recommended_thread':'M3','maximum_penetration_mm':4,'mounting_torque_kgf_cm':[6,8],'source':'User supplied NSP-1600-spec.pdf page6, Case296A mounting instruction;2025-08-19'},
          'geometry_does_not_establish':'thread class, effective engagement, sheet strength, permitted substitute torque, electrical clearances or physical installation condition'})
    report['source_faces_at_normalized_z0']=[]
    for j,s in enumerate(n):
        for f in a.surface_records(s):
            if f['type'].endswith('GeomAbs_Plane') and max(abs(v) for v in f['bbox_mm']['z'])<1e-5:report['source_faces_at_normalized_z0'].append({'source_solid_index_zero_based':j,**f})
    cq.exporters.export(whole,str(HERE/'NSP1600_normalized_ORIGINAL_REFERENCE.step'))
    reopened=cq.importers.importStep(str(HERE/'NSP1600_normalized_ORIGINAL_REFERENCE.step')).val()
    report['normalized_step_roundtrip']={'valid':reopened.isValid(),'solids':len(reopened.Solids()),'bbox_mm':a.bb(reopened),'relative_volume_difference':(reopened.Volume()-whole.Volume())/whole.Volume()}
    report['source_hash_after_export']=hashlib.sha256(a.SOURCE.read_bytes()).hexdigest();assert report['source_hash_after_export']==r['source_sha256']
    (HERE/'mounting_interface.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({'bbox':report['normalized_bbox_mm'],'translation':translation,'axes':axes,'holes':[{'id':h['hole_id'],'owner':h['owning_source_solid_index_zero_based'],'internal_hits':h['other_component_axial_material_by_probe_radius_mm']} for h in report['holes']],'roundtrip':report['normalized_step_roundtrip']},indent=2),flush=True)
    # True section curves through each mounting axis.
    secdir=HERE/'sections';secdir.mkdir(exist_ok=True)
    for i,((x,y),owner) in enumerate(zip(axes,owners),1):
        s=['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="760" viewBox="0 0 1080 760">','<rect width="1080" height="760" fill="white"/>','<style>text{font-family:Helvetica,sans-serif;font-size:18px;fill:#173343}.title{font-size:25px;font-weight:bold}</style>',f'<text x="28" y="43" class="title">NSP-1600 bottom H{i} / true source section</text>',f'<text x="28" y="77">X={x:.5f}, Y={y:.5f} mm; contact plane Z=0. Uniform X/Z scale.</text>']
        tx=lambda xx:400+(xx-x)*13;tz=lambda zz:647-zz*13
        clip=cq.Workplane('XY').box(22,14,43).translate((x,y,20.5)).val()
        for j,body in enumerate(n):
            local=body.intersect(clip)
            if local.Volume()<1e-8:continue
            plane=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0));section=cq.Workplane(plane).add(local).section().val()
            color='#187752' if j==owner else '#a36924' if j==10 else '#48688d'
            for e in section.Edges():
                pts,_=e.sample(max(2,math.ceil(e.Length()/.025)+1));d=' '.join(('M' if k==0 else 'L')+f'{tx(p.x):.3f},{tz(p.z):.3f}' for k,p in enumerate(pts));s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        s.extend([f'<line x1="190" x2="615" y1="{tz(0)}" y2="{tz(0)}" stroke="#718998" stroke-dasharray="8 4"/>','<line x1="400" x2="400" y1="108" y2="672" stroke="#718998" stroke-dasharray="10 4 2 4"/>','<text x="695" y="154" fill="#187752">Green: mounting sheet / bracket</text>','<text x="695" y="187" fill="#a36924">Ochre: source PCB reference</text>','<text x="695" y="220" fill="#48688d">Blue: other source components</text>','<text x="28" y="707">M3 maximum intrusion4 mm is from manufacturer mounting instruction, not this section.</text>','<text x="28" y="739">Model geometry does not verify thread capacity, electrical clearances or a received screw stack.</text>','</svg>'])
        (secdir/f'bottom_H{i}_section.svg').write_text('\n'.join(s),encoding='utf8')
    sys.path.insert(0,str(a.ROOT));from lib.render_step import render_scene
    renderparts=[(s, (.37,.56,.47) if i in [0,17,18] else (.6,.62,.66) if i==16 else (.23,.28,.32) if i in [14,15] else (.68,.5,.25),1) for i,s in enumerate(n)]
    results=render_scene(renderparts,TEMP/'views','NSP1600_source',size=1100,axes=False);out=HERE/'views';out.mkdir(exist_ok=True)
    for p in results:shutil.copyfile(p,out/p.name)
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    qa=TEMP/'section_qa';qa.mkdir(exist_ok=True)
    for f in secdir.glob('*.svg'):
        pdf=qa/(f.stem+'.pdf');renderPDF.drawToFile(svg2rlg(str(f)),str(pdf));subprocess.run(['pdftoppm','-scale-to','1080','-png','-singlefile',str(pdf),str(qa/f.stem)],check=True);shutil.copyfile(qa/(f.stem+'.png'),secdir/(f.stem+'.png'))
    print('Normalized source, three sections and seven context views complete.',flush=True)


if __name__=='__main__':main()
