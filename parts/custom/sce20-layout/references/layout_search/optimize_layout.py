"""Bounded, reproducible cabinet packing search in lower-left panel coordinates.

Orthogonal orientations and topology are intentional installation constraints.
Conservative 3D boxes distinguish thin plates from elevated devices. Cable
reservations can overlap low plates where their Z intervals do not overlap.
"""
from pathlib import Path
import json,itertools,time
import numpy as np
from scipy.optimize import minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle

HERE=Path(__file__).absolute().parent
NAMES=['meanwell','bedrock','b210','peplink','oz']
ROT=[180,0,180,0,0]
BASE=np.array([373,65.6,91.5,297.5,255,315.5,127,88,275,76],float)
BOUNDS=[(362,390),(65.6,65.6),(85,105),(280,312),(238,278),(275,326),(112,145),(86.105,99),(258,292),(73.355,100)]
FACTORY=np.array(list(itertools.product([22.225,409.575],repeat=2)))
CASE=(-36.195,467.995)
PANEL=431.8
body=[];service=[]

def box(target,owner,name,x,y,z):
    a=np.array([x,y,z],float)
    if ROT[owner]==180:a[:2]=-a[:2,::-1]
    target.append(dict(owner=owner,name=name,bounds=a))

# Supplied current normalized source geometry. Thin adapter plate bounding
# boxes are separate from elevated electronics and protruding connectors.
box(body,0,'PSU center plate',[-22.5,22.5],[-300.6,16.2],[0,6])
box(body,0,'PSU upper tab',[-36,36],[-279.8,-235.8],[0,6])
box(body,0,'PSU lower tab',[-36,36],[-27.8,16.2],[0,6])
box(body,0,'PSU device/terminals',[-20.5,20.5],[-300.6,38],[6,91])
box(body,1,'Bedrock adapter',[-83,83],[-92,92],[0,6])
box(body,1,'Bedrock device',[-67.9570157,65],[-80,90],[6,57])
box(body,2,'B210 adapter',[-75,75],[-74,74],[0,4])
box(body,2,'B210 device/connectors',[-61.1735001,61.1745001],[-85.9663,91.6813],[4,37.7])
box(body,3,'Peplink conservative complete envelope',[-85.9,85.9],[-81.7995728612,84.4300114103],[6,35.3])
box(body,4,'OZ complete envelope',[-58.1,58.1],[-69.05,69.05],[0,32.72])

# PSU manufacturer corridor starts at intake face Y=0, not the end of its
# terminal features at Y=38. Therefore those features are not double counted.
box(service,0,'PSU intake 100 mm',[-20.5,20.5],[0,100],[6,91])
box(service,0,'PSU exhaust 100 mm',[-20.5,20.5],[-400.6,-300.6],[6,91])
box(service,1,'Bedrock IO 50 mm',[-117.96,-67.96],[-75,75],[6,51])
box(service,1,'Bedrock SMA 50 mm',[-58,58],[90,140],[6,51])
box(service,2,'B210 RF cable envelope',[-55,55],[80,140],[10.4,42.4])
box(service,2,'B210 USB/DC cable envelope',[-55,55],[-140,-80],[10.4,42.4])
box(service,3,'Peplink lower cable 40 mm',[-75,75],[-121.7995728612,-81.7995728612],[10,45])
box(service,3,'Peplink upper coax/SIM 40 mm',[-75,75],[84.4300114103,124.4300114103],[10,45])
box(service,4,'OZ lower fiber/DE9 40 mm',[-46.1,46.1],[-109.05,-69.05],[8,40])
box(service,4,'OZ upper SMA 30 mm',[-42,42],[69.05,99.05],[8,40])

mounts=[np.array(list(itertools.product([-28.5,28.5],[-257.8,-5.8]))),
        np.array(list(itertools.product([-76,76],[-82,82]))),
        np.array(list(itertools.product([-68,68],[-60.0075,60.0075]))),
        np.array(list(itertools.product([-80.9,80.9],[-41.35,41.35]))),
        np.array(list(itertools.product([-53.1,53.1],[-41.8,54.2])))]
for i in [0,2]:mounts[i]=-mounts[i]

def boxes_at(records,v):
    return [r['bounds']+np.array([v[r['owner']*2],v[r['owner']*2+1],0])[:,None] for r in records]

def overlap_z(a,b):return min(a[2,1],b[2,1])-max(a[2,0],b[2,0])>1e-5
def sep(a,b):
    g=np.maximum(a[:2,0]-b[:2,1],b[:2,0]-a[:2,1])
    return float(np.linalg.norm(np.maximum(g,0))) if np.any(g>0) else float(np.max(g))
def circle_sep(a,p,r):return float(np.linalg.norm(np.maximum(np.maximum(a[:2,0]-p,p-a[:2,1]),0))-r)

bpairs=[(i,j) for i,a in enumerate(body) for j,b in enumerate(body[:i]) if a['owner']!=b['owner'] and overlap_z(a['bounds'],b['bounds'])]
spairs=[(i,j) for i,a in enumerate(service) for j,b in enumerate(body) if a['owner']!=b['owner'] and overlap_z(a['bounds'],b['bounds'])]

def evaluate(v,details=False):
    b=boxes_at(body,v);s=boxes_at(service,v)
    variable=[];hard=[]
    def var(n,x):variable.append((n,float(x)))
    def req(n,x):hard.append((n,float(x)))
    for i,j in bpairs:var(body[i]['name']+' / '+body[j]['name'],sep(b[i],b[j]))
    for i,j in spairs:var(service[i]['name']+' / '+body[j]['name'],sep(s[i],b[j]))
    for i,a in enumerate(b):
        # Plates/devices remain at least 2 mm inside the new panel.
        req(body[i]['name']+' panel edge',min(a[0,0],a[1,0],PANEL-a[0,1],PANEL-a[1,1])-2)
        for k,p in enumerate(FACTORY):
            var(body[i]['name']+' factory socket '+str(k+1),circle_sep(a,p,15))
    for i,a in enumerate(s):
        # Reserve complete planning volumes in the measured enclosure. PSU
        # can have only 1.795 mm additional nominal wall margin by geometry.
        req(service[i]['name']+' case wall',min(a[0,0]-CASE[0],a[1,0]-CASE[0],CASE[1]-a[0,1],CASE[1]-a[1,1])-.5)
        if a[2,0]<8.5344:
            for k,p in enumerate(FACTORY):req(service[i]['name']+' factory nut '+str(k+1),circle_sep(a,p,9.4615))
    for i,xy in enumerate(mounts):
        pts=xy+v[i*2:i*2+2]
        req(NAMES[i]+' stud panel-edge margin',min(pts.min(),(PANEL-pts).min())-6)
        for k,p in enumerate(pts):
            for j,a in enumerate(b):
                if body[j]['owner']==i:continue
                var(NAMES[i]+' component socket '+str(k+1)+' / '+body[j]['name'],circle_sep(a,p,5))
    if details:return dict(variable_clearances=sorted(variable,key=lambda x:x[1]),hard_constraints=sorted(hard,key=lambda x:x[1]))
    return np.array([x[1] for x in variable]),np.array([x[1] for x in hard])

calls=0
def constraint(u):
    global calls
    calls+=1
    v,h=evaluate(u[:10]);return np.r_[v-u[10],h]

def run():
    started=time.time();rng=np.random.default_rng(82026);results=[]
    # Start with the supplied candidate, then repeat continuous max-min
    # optimization from distinct bounded seeds to find better feasible minima.
    for n in range(20):
        if n==0:v=BASE.copy()
        elif n<15:v=BASE+rng.normal(0,[2,0,1,2,2,2,1,1,1,2])
        else:v=np.array([rng.uniform(a,b) for a,b in BOUNDS])
        v=np.clip(v,[x[0] for x in BOUNDS],[x[1] for x in BOUNDS])
        gap,_=evaluate(v)
        initial=np.r_[v,min(gap.min(),1)]
        result=minimize(lambda u:-u[10],initial,method='SLSQP',bounds=BOUNDS+[(0,30)],constraints=[dict(type='ineq',fun=constraint)],options=dict(maxiter=220,ftol=1e-7))
        vv,hh=evaluate(result.x[:10]);feasible=min(vv.min()-result.x[10],hh.min())>=-1e-4
        row=dict(seed=n,success=bool(result.success),feasible=bool(feasible),minimum_margin_mm=float(vv.min()),hard_margin_mm=float(hh.min()),vector=result.x[:10].tolist(),iterations=int(result.nit),message=result.message)
        results.append(row)
        print(n,feasible,round(vv.min(),5),np.round(result.x[:10],2),flush=True)
    valid=[r for r in results if r['feasible']]
    if not valid:raise RuntimeError('No feasible result; see raw search')
    best=max(valid,key=lambda r:r['minimum_margin_mm'])
    v=np.array(best['vector'])
    # Fixed PSU centerY=65.6 equalizes its two 100 mm end corridors.
    # Round to0.1mm; retain exact source offsets in stud patterns.
    v=np.round(v,1)
    # The optimum has unconstrained vertical/upper-row degrees of freedom.
    # Choose clean coordinates within that feasible family, improving bottom
    # cable-to-wall margins while retaining the same rounded limiting gap.
    v=np.array([371.5,65.6,92,297,254,318,126.5,89,274,76],float)
    d=evaluate(v,True)
    assert min(x[1] for x in d['variable_clearances'])>0
    assert min(x[1] for x in d['hard_constraints'])>=-1e-7
    placed={n:dict(translation_mm=[float(v[2*i]),float(v[2*i+1]),6 if i==3 else 0],rotation_z_deg=ROT[i],mount_points_panel_xy_mm=(mounts[i]+v[2*i:2*i+2]).tolist()) for i,n in enumerate(NAMES)}
    b=boxes_at(body,v);s=boxes_at(service,v)
    result=dict(schema='sce20-layout-search/1',units='mm',datum='lower-left panel origin; panel front Z=0; +Y up; all transforms apply to normalized source files',placements=placed,search=dict(method='20 bounded multi-start SLSQP max-min clearance runs; fixed orthogonal orientations/topology',seed=82026,elapsed_seconds=time.time()-started,constraint_evaluations=calls,runs=results,raw_best=best,rounding_mm=.1),selected_clearances=d,physical_boxes=[dict(name=r['name'],component=NAMES[r['owner']],bounds_mm=a.tolist()) for r,a in zip(body,b)],service_boxes=[dict(name=r['name'],component=NAMES[r['owner']],bounds_mm=a.tolist()) for r,a in zip(service,s)],assumptions=['PSU100mm from terminal face and fan face, not from terminal protrusion; cabinet wall box exact[-36.195,467.995]','Manufacturer/source-prescribed nominal areas: Bedrock50mm, B21060mm source cable planning. Router40mm eachend andOZ40/30mm are selected cable planning allowances, not vendor minimums.','Other-component cable reservations are not forced to be mutually disjoint: routed cable crossings may occur at different elevations; actual harness routing still required.','Complete connector bounds are conservative for invalid source Peplink subsolids.','Factory socket radius15mm,height60; component socketsradius5mm,height40-60. No supplier load/thermal/vibration qualification is established.','This is a best-found constrained layout, not a proof of global optimality over arbitrary orientations.'])
    (HERE/'placement.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    draw(result)
    print('SELECTED',placed,flush=True)
    print('LIMITING',d['variable_clearances'][:12],d['hard_constraints'][:8],flush=True)

def draw(result):
    fig,ax=plt.subplots(figsize=(11,11));colors=['#d49725','#26799e','#7454a8','#468450','#bd6554']
    ax.add_patch(Rectangle((CASE[0],CASE[0]),CASE[1]-CASE[0],CASE[1]-CASE[0],fc='#f3f4f5',ec='#535e68',lw=2))
    ax.add_patch(Rectangle((0,0),PANEL,PANEL,fc='white',ec='black',lw=2))
    for q in result['service_boxes']:
        a=np.array(q['bounds_mm']);idx=NAMES.index(q['component'])
        ax.add_patch(Rectangle(a[:2,0],a[0,1]-a[0,0],a[1,1]-a[1,0],fc=colors[idx],alpha=.10,ec=colors[idx],ls='--',lw=1.2))
    for q in result['physical_boxes']:
        a=np.array(q['bounds_mm']);idx=NAMES.index(q['component']);alpha=.22 if 'adapter' in q['name'] or 'plate' in q['name'] or 'tab' in q['name'] else .50
        ax.add_patch(Rectangle(a[:2,0],a[0,1]-a[0,0],a[1,1]-a[1,0],fc=colors[idx],alpha=alpha,ec=colors[idx],lw=1.2))
    for k,p in enumerate(FACTORY):
        ax.add_patch(Circle(p,15,fill=False,ec='#b42231',ls=':',lw=1.3));ax.add_patch(Circle(p,9.4615,fc='#c4c4c4',ec='#333',lw=1));ax.text(*p,str(k+1),ha='center',va='center',fontsize=8)
    labels={'meanwell':'MEAN WELL\nNSP1600','bedrock':'BEDROCK','b210':'ETTUS B210','peplink':'PEPLINK\nUBR PLUS','oz':'OZ51x\nDUAL TX'}
    for name,q in result['placements'].items():
        x,y,z=q['translation_mm'];ytext=y+145 if name=='meanwell' else y
        ax.text(x,ytext,labels[name],ha='center',va='center',weight='bold',fontsize=11,color='#16232d')
        for xx,yy in q['mount_points_panel_xy_mm']:ax.plot(xx,yy,'+',color='#18212b',ms=6)
    ax.annotate('CABLE ENTRY / BOTTOM',(215,-34),ha='center',va='top',fontsize=10)
    ax.set_xlim(-45,477);ax.set_ylim(-48,485);ax.set_aspect('equal');ax.set_xticks(np.arange(0,451,50));ax.set_yticks(np.arange(0,451,50));ax.grid(alpha=.18);ax.set_xlabel('Panel X (mm)');ax.set_ylabel('Panel Y (mm)')
    ax.set_title('SCE-20H2010LP • best-found constrained layout\n431.8 mm square aluminum panel; dashed fields = cable/air planning',fontsize=14,pad=14)
    fig.text(.5,.025,'Red dotted circles: Ø30 factory-nut socket access. Boxes conservatively bound physical parts.\nClearances are nominal CAD; cable fields can cross at different heights.',ha='center',fontsize=9)
    fig.savefig(HERE/'optimized_layout.png',dpi=160,bbox_inches='tight');fig.savefig(HERE/'optimized_layout.svg',bbox_inches='tight');plt.close(fig)

if __name__=='__main__':run()
