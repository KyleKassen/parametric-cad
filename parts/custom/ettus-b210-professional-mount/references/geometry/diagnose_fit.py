"""Independent component-by-component base/device interference diagnosis."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from model import load_params,create_base,get_device
from inspection import bbox
p=load_params();base=create_base(p);device=get_device(p);rows=[]
for i,s in enumerate(device.Solids()):
    b=s.BoundingBox()
    if b.zmin>12.001:continue
    hit=base.intersect(s);v=hit.Volume() if hit.Solids() else 0
    if v>1e-7: rows.append({'solid_index':i,'intersection_volume_mm3':v,'intersection_bbox':bbox(hit),'source_solid_bbox':bbox(s)})
result={'params':p,'base_valid':base.isValid(),'intersections':rows,'total_volume_mm3':sum(r['intersection_volume_mm3'] for r in rows)}
(HERE/'fit_interference_diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
