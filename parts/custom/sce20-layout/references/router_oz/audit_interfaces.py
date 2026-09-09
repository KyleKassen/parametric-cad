from pathlib import Path
import json,sys,importlib.util
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
HERE=Path(__file__).absolute().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT))

def bbox(s):
 b=s.BoundingBox()
 return {'min':[b.xmin,b.ymin,b.zmin], 'max':[b.xmax,b.ymax,b.zmax], 'size':[b.xlen,b.ylen,b.zlen]}
def overlap(a,b):
 return a.intersect(b).Volume()
def cyl(r,h,x,y,z):
 return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))

router=cq.importers.importStep(str(HERE/'peplink_source.stp')).val()
holes=[]
for face in router.Faces():
 ad=BRepAdaptor_Surface(face.wrapped)
 if ad.GetType()!=GeomAbs_Cylinder: continue
 c=ad.Cylinder(); d=c.Axis().Direction(); p=c.Location(); b=face.BoundingBox()
 if abs(c.Radius()-2.25)<1e-7 and abs(d.Y())>0.999 and abs(p.X()-15.1377)>75 and b.ymin<8:
  holes.append({'raw':[p.X(),b.ymin,p.Z()], 'top':b.ymax,'diameter':2*c.Radius()})
cx=sum(h['raw'][0] for h in holes)/len(holes)
cz=sum(h['raw'][2] for h in holes)/len(holes)
by=min(h['raw'][1] for h in holes)
router_norm=router.rotate((0,0,0),(1,0,0),90).translate((-cx,cz,-by))
rholes=[[h['raw'][0]-cx,-h['raw'][2]+cz] for h in holes]
checks=[]
for i,(x,y) in enumerate(rholes):
 checks.append({'part':'peplink','mount':i,'M4_screw_shaft_ear_clearance_overlap_mm3':overlap(router_norm,cyl(2,2.5,x,y,0)), 'female_standoff_body_OD5_overlap_mm3':overlap(router_norm,cyl(2.5,6,x,y,-6)), 'washer_OD9_ID4p3_overlap_mm3':overlap(router_norm,cyl(4.5,1,x,y,2.5).cut(cyl(2.15,1,x,y,2.5))), 'socket_OD10_access_overlap_mm3':overlap(router_norm,cyl(5,40,x,y,3.5))})

spec=importlib.util.spec_from_file_location('oz_snap',ROOT/'parts/custom/oz51x-dual-tx-housing-vertical-snap/model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=m.load_params(); L=m.layout(p)
oz=cq.importers.importStep(str(ROOT/'parts/custom/oz51x-dual-tx-housing-vertical-snap/exports/oz51x-dual-tx-housing-vertical-snap_v2.step')).val()
oz_canon=oz.translate((L['envelope_width']/2,0,-L['outer_half_x'])).rotate((0,0,0),(0,1,0),-90)
oz_bb=bbox(oz_canon)
cy=32.2  # deliberate clean mounting datum; raised labels put envelope centroid 0.0005 mm off this datum
# All optical/fiber +Y I/O facing down. Existing drains designed vertical in canonical X; internal cabin not environmental barrier.
oz_norm=oz_canon.translate((0,-cy,0)).rotate((0,0,0),(0,0,1),180)
oholes=[[-s*53.1,cy-y] for s in [-1,1] for y in [-22,74]]
for i,(x,y) in enumerate(oholes):
 checks.append({'part':'oz','mount':i,'stud_M3x12_overlap_mm3':overlap(oz_norm,cyl(1.5,12,x,y,0)), 'washer_OD9_ID3p2_overlap_mm3':overlap(oz_norm,cyl(4.5,.8,x,y,3).cut(cyl(1.6,.8,x,y,3))), 'socket_OD10_access_overlap_mm3':overlap(oz_norm,cyl(5,40,x,y,3.8))})
output={'schema':'router-oz-panel-interface/1','units':'mm','peplink':{'raw_bbox':bbox(router),'raw_holes':holes,'normalization':{'first_rotate_axis':'X','degrees':90,'then_translate':[-cx,cz,-by]},'normalized_bbox':bbox(router_norm),'mounting_holes_xy':rholes,'mount_face_z':0,'installed_mount_face_above_panel_mm':6,'installed_overall_height_above_panel_mm':35.3,'ear_thickness':2.5,'diameter':4.5,'fastener_selection':'FPE WGO40 M4 female load standoff 6 mm, catalog body OD5 mm; M4x8 screw + 9 mm OD x4.3 ID x1 washer +2.5 ear yields4.5mm thread engagement. Catalog and final native FPD verification performed by main task.','connector_direction':'Ethernet/power/Wi-Fi ports at negative local Y; cellular/GPS/SIM at positive local Y','service_allowance_mm':{'negative_y':40,'positive_y':40,'sides':10,'note':'design allowances for right-angle or flexible cable routing, not manufacturer values; confirm actual connector boots/coax bend radii'}},'oz':{'raw_bbox':bbox(oz),'canonical_bbox':oz_bb,'inverse_installed_first_translate':[L['envelope_width']/2,0,-L['outer_half_x']],'inverse_installed_then_rotate':{'axis':'Y','degrees':-90},'canonical_mount_xy':[[s*53.1,y] for s in [-1,1] for y in [-22,74]],'normalization_after_canonical':{'translate':[0,-cy,0],'rotate_axis':'Z','rotate_degrees':180},'normalized_bbox':bbox(oz_norm),'mounting_slots_xy':oholes,'slot_size':[4.5,9],'ear_thickness':3,'fastener_selection':'M3 male stud with 9 mm OD x3.2 ID x0.8 washer + M3 nut; reference test 12 mm protrusion; actual catalog usable thread length to be checked','service_allowance_mm':{'cover_outward_extra':47,'fiber_front_negative_y':40,'SMA_positive_y':30,'note':'47 mm documented source cover swing; cable allowances chosen not manufacturer values; internal R15 spool does not certify external fiber bend radius'},'manufacturing':'Base+snap cover remain unfilled MJF PA12 printed geometry; no existing planar aluminum mounting plate in this component. Integral ears accept direct backpanel fasteners.'},'geometric_checks':checks}
for name,obj in [('peplink_normalized.step',router_norm),('oz_normalized.step',oz_norm)]: cq.exporters.export(obj,str(HERE/name))
(HERE/'interfaces.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps(output,indent=2))

