from pathlib import Path
import itertools,json,math,time
import cadquery as cq

OUT=Path(__file__).resolve().parent
FINAL_ROOT=OUT.parents[1]
ROOT=FINAL_ROOT.parent/'sce20-layout'
OUT.mkdir(exist_ok=True)
placements={'bedrock':((122,107,0),0),'peplink':((122,90,80),0),'b210':((282,107,50),180),'oz':((282,107,0),0),'meanwell':((391,65.6,0),180)}
def bb(s):
 b=s.BoundingBox();return [b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
def sep(a,b):
 gaps=[max(a[i]-b[i+1],b[i]-a[i+1],0) for i in (0,2,4)]
 return math.sqrt(sum(g*g for g in gaps))
def ov(a,b):
 return all(min(a[i+1],b[i+1])-max(a[i],b[i])>1e-6 for i in (0,2,4))
def load(name):
 shape=cq.Shape.importBrep(str(ROOT/'references/enclosure'/f'candidate_{name}_fpe_source.brep'))
 pos,angle=placements[name]
 shape=shape.rotate((0,0,0),(0,0,1),angle).translate(pos)
 print('loaded',name,flush=True)
 return shape
models={name:load(name) for name in placements}
models['carrier']=cq.importers.importStep(str(FINAL_ROOT/'carrier/exports/Peplink_Carrier_R2_frame.step')).val().translate((122,107,70))
carrier_posts=[(122+x,107+y) for x,y in itertools.product([-70,70],[-97,97])]
b210_posts=[(282+x,107+y) for x,y in itertools.product([-68,68],[-60.0075,60.0075])]
for group,points,h in [('carrier',carrier_posts,70),('b210',b210_posts,50)]:
 for i,(x,y) in enumerate(points):models[f'{group}_support_{i+1}']=cq.Solid.makeCylinder(3.5,h,cq.Vector(x,y,0))
for i,(x,y) in enumerate(itertools.product([-80.9,80.9],[-41.35,41.35])):
 models[f'router_standoff_{i+1}']=cq.Solid.makeCylinder(2.5,6,cq.Vector(122+x,90+y,74))
solidsets={name:[(i,s,bb(s)) for i,s in enumerate(shape.Solids())] for name,shape in models.items()}
results=[]
for name_a,name_b in itertools.combinations(models,2):
 candidates=[];minimum=float('inf');penetrations=[]
 for ia,a,ba in solidsets[name_a]:
  for ib,b,bb_ in solidsets[name_b]:
   minimum=min(minimum,sep(ba,bb_))
   if ov(ba,bb_):candidates.append((ia,a,ib,b))
 for ia,a,ib,b in candidates:
  v=a.intersect(b).Volume()
  if abs(v)>1e-6:penetrations.append({'solid_a':ia,'solid_b':ib,'signed_volume_mm3':v})
 results.append({'a':name_a,'b':name_b,'minimum_solid_bbox_clearance_lower_bound_mm':minimum,'candidate_solid_intersections':len(candidates),'penetrations':penetrations,'pass':not penetrations})
report={'status':'PASS' if all(r['pass'] for r in results) else 'FAIL','scope':'Candidate component/support geometric collision audit; solid-bounds proof with exact BREP intersections for overlapping candidate boxes; actual windowed carrier STEP included; no physical qualification','placements':placements,'components':{n:{'bbox':bb(s),'solids':len(s.Solids())} for n,s in models.items()},'pair_checks':results,'carrier_supports':carrier_posts,'b210_supports':b210_posts}
report['factory_socket_checks']=[]
for group,points in [('carrier',carrier_posts),('b210',b210_posts)]:
 for x,y in points:
  gap=min(math.hypot(x-fx,y-fy)-15-3.5 for fx,fy in itertools.product([22.225,409.575],repeat=2))
  report['factory_socket_checks'].append({'group':group,'xy':[x,y],'OD30_tool_clearance_to_OD7_post':gap,'pass':gap>0})
report['notes']=['M3 load-hardware flange cavities must remain flush/below panel front, not modeled as full-height 12.1mm columns.','OZ service requires removing B210 upper assembly first at 50mm underside elevation.','Carrier underside70 leaves13mm over Bedrock57; router ears80 and top109.3.','B210 underside50 leaves17.28 over OZ32.72; B210 top87.7.','Physical upper-left quadrant is clear, but Bedrock SMA allowance reachesY247; reserve the smaller [0,215.9] x [250,431.8] rectangle excluding factory tools.']
(OUT/'final_candidate_collision_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DONE',report['status'],len(results),'pair checks',flush=True)
for r in results:
 if not r['pass']:print('COLLISION',r,flush=True)
