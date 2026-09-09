"""Check positive end retention against the bottom pan alone, not labels/screws."""
from pathlib import Path
import sys,json,math
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from model import load_params,create_base,get_device,block
from inspection import bbox
p=load_params();base=create_base(p);dev=get_device(p);pan=dev.Solids()[0]
up=.4+.2+.151+.022+.065;down=-.2;cy=p['center_y'];zpan=p['device_pan_z']
tilt=math.degrees(math.atan((up-down)/70));zm=(up+down)/2;rows=[]
for sign in [-1,1]:
    pose=pan.rotate((0,cy,zpan),(1,cy,zpan),sign*tilt).translate((0,sign*3,zm))
    end=block(80,18,p['end_stop_top']-6,0,p['pocket_ymax']+9 if sign>0 else p['pocket_ymin']-9,6)
    hit=pose.intersect(base.intersect(end));v=hit.Volume()
    rows.append({'end_sign':sign,'tilt_deg':tilt,'intentional_escape_shift_y_mm':sign*3,
        'pan_only_intersection_volume_mm3':v,'contact_bbox':bbox(hit) if v>0 else None,'pass':v>.1})
result={'units':'mm, deg, mm3','params':p,'pan_solid_index':0,'upward_support_envelope_mm':up,
    'downward_support_envelope_mm':down,'results':rows,'all_pass':all(r['pass'] for r in rows),
    'limitations':'Static geometric obstruction witnesses at bounded extreme pose, not contact stress, continuous path search, impact simulation or physical validation.'}
(HERE/'pan_capture_check.json').write_text(json.dumps(result,indent=2));print(json.dumps(rows,indent=2))
