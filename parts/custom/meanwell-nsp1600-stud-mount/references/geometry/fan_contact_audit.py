"""Reproduce local fan/body-envelope and metal-contact measurements.

No proposed adapter geometry is produced. Each fan envelope is clipped from
the source at the specified height above the nominal bottom datum.
"""
from pathlib import Path
import importlib.util,json,hashlib
import cadquery as cq

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nsp_audit',HERE/'audit_nsp1600.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def main():
    info=json.loads((HERE/'mounting_interface.json').read_text())
    assert hashlib.sha256(a.SOURCE.read_bytes()).hexdigest()==info['source_sha256']
    n=[s.translate(tuple(info['translation_mm'])) for s in cq.importers.importStep(str(a.SOURCE)).val().Solids()]
    r={'source_sha256':info['source_sha256'],'units':'mm','method':'Original source solids rigidly normalized; clipped from Z0 to the stated height. These are envelopes, not permitted fan motion or manufacturing tolerances.','fans':[],'bracket_sections':[]}
    for i in [14,15]:
        q={'source_id':i,'bbox':a.bb(n[i]),'near_bottom_envelopes':{}}
        for z in [.001,.25,.5,1.0]:
            clip=cq.Workplane('XY').box(100,50,z,centered=(True,True,False)).translate((0,-283.8,0)).val();hit=n[i].intersect(clip)
            q['near_bottom_envelopes'][str(z)]={'bbox':a.bb(hit),'solid_pieces':[a.bb(s) for s in hit.Solids()]}
        r['fans'].append(q)
    for y in [-298.2,-295,-290,-280.8,-274.4,-270.4,-266]:
        probe=cq.Workplane('XY').box(100,.001,.001,centered=(True,True,False)).translate((0,y,.0001)).val();hit=n[0].intersect(probe)
        r['bracket_sections'].append({'y':y,'material_x_intervals':sorted(a.bb(s)['x'] for s in hit.Solids())})
    r['central_metal_spine_nominal_width']=5.5
    r['nominal_sheet_side_strip_x_intervals']=[[-42.5,-41.7],[-41.6,-40.1],[40.1,41.6],[41.7,42.5]]
    r['limits']='A plate may not depend on fan-frame support or assume that filling the two open underside regions preserves fan behavior. Actual clearance, bracket contact and airflow must be checked in the final assembly.'
    (HERE/'fan_bottom_contact_geometry.json').write_text(json.dumps(r,indent=2),encoding='utf8')
    print('Fan envelopes and metal contact intervals regenerated from original source.')

if __name__=='__main__':main()
