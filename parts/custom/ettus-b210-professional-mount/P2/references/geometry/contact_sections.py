"""Exact narrow BREP slab bounds of the lower pan; preserve source."""
from inspection import SOURCE,HERE,bbox,norm
import cadquery as cq
import json
s=norm(cq.importers.importStep(str(SOURCE)).val())
pan=s.Solids()[0]
rows=[]
for z in [0.01,0.5,1.0,1.5,1.8,2.0,2.3,2.419,2.5,5.0]:
    sl=cq.Workplane('XY').box(300,300,0.002).translate((0,0,z)).val()
    cut=pan.intersect(sl)
    rows.append({'z_mm':z,'slab_thickness_mm':0.002,'pan_bbox_mm':bbox(cut) if cut.Solids() else None,'valid':cut.isValid()})
result={'source':str(SOURCE),'datum':'same as inspection.py','pan_solid_index':0,'sections':rows}
(HERE/'pan_contact_sections.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
