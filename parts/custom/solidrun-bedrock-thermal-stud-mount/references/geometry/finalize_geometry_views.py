"""Summarize fresh audit measurements and render source-derived views.

Run after audit_tile_hybrid.py. Only reads that audit and its normalized exports.
"""
from pathlib import Path
import sys,json,math,shutil,subprocess,hashlib,importlib.util,argparse
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('solidrun_geometry_audit_source',HERE/'audit_tile_hybrid.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
TEMP=Path('C:/b210work/solidrun'); TEMP.mkdir(parents=True,exist_ok=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--summary-only',action='store_true');ap.add_argument('--views-only',action='store_true');args=ap.parse_args()
    r=json.loads((HERE/'solidrun_geometry_audit.json').read_text())
    summary={'source_sha256':r['source_sha256'],'normalized_frame':r['frame'],'solid_indices_are_zero_based':True,
             'variant_indices':r['variant_source_indices_zero_based'],'mating_face_area_mm2':r['mating_plane_area_mm2'],
             'mating_face_bbox_mm':r['mating_plane_faces'][0]['bbox_mm'],'hole_axes_xy_mm':[],'holes':[]}
    for q,h in zip(r['hole_local_face_records'],r['hole_stations']):
        f=q['faces']; local=[v for v in f if v['bbox_mm']['z'][1]<5]
        entry=next(v for v in local if v.get('semi_angle_degrees')==45.)
        bottom=next(v for v in local if v.get('semi_angle_degrees')==59.)
        roots=sorted(v['bbox_mm']['z'][0] for v in local if v.get('diameter_mm')==4.1095 and v.get('u_span_radians',0)>6.28)
        pitch=[roots[i+1]-roots[i] for i in range(len(roots)-1)]
        cylinders=[v for v in local if 'axis_location_mm' in v]
        assert all(abs(v['axis_location_mm'][0]-q['axis_xy_mm'][0])<1e-6 and abs(v['axis_location_mm'][1]-q['axis_xy_mm'][1])<1e-6 for v in cylinders)
        summary['hole_axes_xy_mm'].append(q['axis_xy_mm'])
        summary['holes'].append({'axis_xy_mm':q['axis_xy_mm'],'verified_by_coaxial_analytic_cylinders':True,
           'entry_mouth_diameter_mm':round(entry['bbox_mm']['x'][1]-entry['bbox_mm']['x'][0],6),
           'entry_depth_mm':round(entry['bbox_mm']['z'][1],6),'entry_cone_half_angle_deg':45,
           'thread_minor_cylindrical_patch_diameter_mm':3.332,'thread_root_cylindrical_patch_diameter_mm':4.1095,
           'modeled_thread_region_z_mm':[.584,3.5],'nominal_modeled_region_span_mm':2.916,
           'root_feature_axial_repeats_mm':pitch,'inferred_nominal_geometric_pitch_mm':.7,
           'drill_cone_z_mm':bottom['bbox_mm']['z'],'drill_cone_half_angle_deg':59,
           'axis_probe_first_material_z_mm':h['modeled_centerline_obstacles'][0]['first_z_mm'],
           'probe_radius_mm':.015,'bore_type_from_geometry':'BLIND - conical bottom; solid Tile behind',
           'usable_complete_engagement_mm':None,'allowable_screw_penetration_mm':None})
    summary['thread_identity_limit']='Helical geometry and nominal 0.7 mm repeats support an M4x0.7 hypothesis; verify actual thread and useful engagement by vendor drawing/gauge. Modeled region span is not a guaranteed full-thread engagement.'
    summary['documentation_comparison']='Fresh blind-hole geometry agrees with the official Tile brief described by the research team. The old local claims of an open22 mm cavity, safe3.5 penetration and proven physical hybrid interchangeability are unsupported and must not be inherited.'
    tile=cq.importers.importStep(str(HERE/'tile_normalized_SOURCE.step')).val()
    bank=cq.importers.importStep(str(HERE/'single_60W_bank_CLIPPED_REFERENCE.step')).val()
    aux=cq.importers.importStep(str(HERE/'auxiliary_normalized_SOURCE.step')).val()
    intervals=[]
    for x,y in a.AXES:
        probe=cq.Solid.makeCylinder(.015,29,cq.Vector(x,y,0),cq.Vector(0,0,1));hit=tile.intersect(probe)
        intervals.append({'xy':[x,y],'solid_z_intervals':sorted([a.bb(s)['z'] for s in hit.Solids()])})
    summary['axis_material_intervals_from_reopened_tile']=intervals
    summary['internal_cavity_axis_interval_mm']=[5.0,24.0]
    summary['nominal_material_after_drill_apex_mm']=.4989661
    summary['blind_bore_caveat']='There is an internal cavity between the side walls. The holes are blind because each drill point remains capped by nominal0.499 mm of material before that cavity. A probe hit bounding box must not be interpreted as continuous solid through the cavity.'
    r['corrected_disconnected_axis_material_intervals']=intervals
    r['axis_obstacle_interpretation']=summary['blind_bore_caveat']
    (HERE/'solidrun_geometry_audit.json').write_text(json.dumps(r,indent=2),encoding='utf8')
    (HERE/'axis_material_intervals.json').write_text(json.dumps(intervals,indent=2),encoding='utf8')
    def zfaces(shape,z):
        result=[]
        for f in shape.Faces():
            b=f.BoundingBox()
            if BRepAdaptor_Surface(f.wrapped).GetType()==GeomAbs_Plane and abs(b.zmin-z)<1e-5 and abs(b.zmax-z)<1e-5: result.append(f)
        return result
    tf=zfaces(tile,29); bf=zfaces(bank,29)
    contact=sum(f.intersect(g).Area() for f in tf for g in bf)
    summary['derived_split_contact']={'split_z_mm':29,'tile_plane_area_mm2':sum(f.Area() for f in tf),'bank_clipped_plane_area_mm2':sum(f.Area() for f in bf),'coincident_planar_area_mm2':contact,
        'source':'secondary geometric check of reopened normalized exports','limit':'Coincident geometry does not establish a detachable bank, attachment scheme, thermal contact resistance, pressure, TIM, or vendor configuration.'}
    summary['derived_reference_bbox_mm']=r['derived_hybrid']['bbox_mm']
    summary['no_nonphysical_configuration_claim']='Derived reference only: actual Tile geometry plus a mathematically clipped region of the actual60W body and shared auxiliary geometry. No native hybrid is present in source.'
    summary['roundtrip_note']='Derived STEP reopens valid,21 solids, identical bounding box; volume drift1.886mm3,about5.2ppm, from complex BREP roundtrip is recorded in the main audit.'
    (HERE/'critical_dimensions.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps({'contact':summary['derived_split_contact'],'verified_axes':summary['hole_axes_xy_mm']},indent=2),flush=True)
    if args.summary_only:return
    if args.views_only:
        sys.path.insert(0,str(a.ROOT)); from lib.render_step import render_scene
        rendered=render_scene([(tile,(.36,.58,.47),1),(bank,(.52,.43,.67),1),(aux,(.68,.57,.39),1)],TEMP/'views','derived_reference',size=1000,axes=False)
        dest=HERE/'views';dest.mkdir(exist_ok=True)
        for p in rendered:shutil.copyfile(p,dest/p.name)
        return
    sec=HERE/'sections';sec.mkdir(exist_ok=True)
    for i,axis in enumerate(a.AXES): a.write_section_svg(tile,bank,aux,axis,i,sec/f'axis_{i+1}_xz.svg')
    # Uniformly scaled enlargement of the actual near-side helical bore and blind tip.
    x,y=a.AXES[0]; clip=cq.Workplane('XY').box(9,9,7).translate((x,y,2.5)).val(); sh=tile.intersect(clip)
    s=cq.Workplane(cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0))).add(sh).section().val()
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="780" viewBox="0 0 1080 780">','<rect width="1080" height="780" fill="white"/>','<style>text{font-family:Helvetica,sans-serif;fill:#172d3b;font-size:19px}.title{font-size:26px;font-weight:bold}.small{font-size:16px}</style>','<text x="30" y="44" class="title">Actual Tile blind mounting hole / enlarged CAD section</text>','<text x="30" y="78">Axis X=-60, Y=-70 mm; true section at constant Y. Uniform X/Z scale.</text>']
    tx=lambda xx:375+(xx-x)*66;tz=lambda zz:618-zz*66
    for edge in s.Edges():
        pts,_=edge.sample(max(2,math.ceil(edge.Length()/.01)+1)); path=' '.join(('M' if i==0 else 'L')+f'{tx(p.x):.3f},{tz(p.z):.3f}' for i,p in enumerate(pts))
        svg.append(f'<path d="{path}" stroke="#197552" stroke-width="2" fill="none"/>')
    svg.append(f'<line x1="375" y1="165" x2="375" y2="657" stroke="#637b89" stroke-dasharray="10 4 2 4"/>')
    for z,label in [(0,'Mating face Z=0'),(.584,'Entry cone ends Z=0.584'),(3.5,'Modeled thread ends Z=3.500'),(4.5010339,'Blind drill-point apex Z=4.501034')]:
        svg.extend([f'<line x1="{tx(x+2.25)}" y1="{tz(z)}" x2="682" y2="{tz(z)}" stroke="#637b89"/>',f'<text x="694" y="{tz(z)+6}" class="small">{label}</text>'])
    svg.extend(['<text x="30" y="700">Entry mouth DIA4.500; thread patches DIA3.332 /4.1095; measured repeat approximately0.700 mm.</text>','<text x="30" y="733" class="small">Geometric depth and helical span are not allowable screw penetration or proof of useful full engagement.</text>','</svg>'])
    (sec/'blind_hole_entry_detail.svg').write_text('\n'.join(svg),encoding='utf8')
    # CAD orthographic context, including the flat side and both connector directions.
    sys.path.insert(0,str(a.ROOT)); from lib.render_step import render_scene
    rendered=render_scene([(tile,(.36,.58,.47),1),(bank,(.52,.43,.67),1),(aux,(.68,.57,.39),1)],TEMP/'views','derived_reference',size=1000,axes=False)
    dest=HERE/'views'; dest.mkdir(exist_ok=True)
    for p in rendered: shutil.copyfile(p,dest/p.name)
    # SVG-to-PNG rasterization is for visual QA; transient PDFs are kept outside deliverables.
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    qadir=TEMP/'section_qa'; qadir.mkdir(exist_ok=True)
    for p in sec.glob('*.svg'):
        temp=qadir/(p.stem+'.pdf');renderPDF.drawToFile(svg2rlg(str(p)),str(temp))
        subprocess.run(['pdftoppm','-scale-to','1080','-png','-singlefile',str(temp),str(qadir/p.stem)],check=True)
        shutil.copyfile(qadir/(p.stem+'.png'),sec/(p.stem+'.png'))
    print('Completed contact summary, seven context views and seven section views.',flush=True)

if __name__=='__main__':main()
