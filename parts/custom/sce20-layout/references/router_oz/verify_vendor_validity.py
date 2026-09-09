from pathlib import Path
import json,cadquery as cq
p=Path('Q:/parts/custom/sce20-layout/references/router_oz')
r={}
for filename in ['peplink_source.stp','peplink_normalized.step']:
 a=cq.importers.importStep(str(p/filename)).val()
 solids=[]
 for i,s in enumerate(a.Solids()):
  b=s.BoundingBox()
  solids.append({'index':i,'valid':s.isValid(),'volume':s.Volume(),'bbox_min':[b.xmin,b.ymin,b.zmin],'bbox_max':[b.xmax,b.ymax,b.zmax]})
 r[filename]={'compound_valid':a.isValid(),'solids_count':len(solids),'invalid_solids':[s for s in solids if not s['valid']],'largest_solids':sorted(solids,key=lambda s:-s['volume'])[:3]}
(p/'vendor_validity_audit.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r,indent=2))
