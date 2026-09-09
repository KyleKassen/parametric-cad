"""Independent geometry gates and recorded limitations; failures are not promoted."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import cadquery as cq
import model as m

HERE=Path(__file__).resolve().parent


def run(out):
    p=m.load_params(); checks=[]
    def check(name, ok, measured, requirement):
        checks.append(dict(id=name,status="PASS" if ok else "FAIL",measured=measured,requirement=requirement))
        print(checks[-1],flush=True)
    dev=m.get_device(p); base=m.create_base(p)
    items=m.flat_items(p,panel_hardware=False)
    custom=[(n,s) for n,s,k in items if k in ("base","bar","spacer","film")]
    check("source_sha256",hashlib.sha256((HERE/'references/input_device.step').read_bytes()).hexdigest()==p['source_sha256'],p['source_sha256'],"original input bytes preserved")
    for n,s in custom:
        v=s.intersect(dev).Volume()
        check(n+"_vs_device",v<0.001,round(v,8),"unintended overlap <0.001 mm3; nominal film touches allowed")
    for n in ["B210_M01_base","B210_M02_retainer","B210_M03_spacer","B210_M04_film"]:
        path=out/f"{n}_P2.step"; s=cq.importers.importStep(str(path)).val(); bb=s.BoundingBox()
        check(n+"_export",s.isValid() and len(s.Solids())==1,{"solids":len(s.Solids()),"bbox_mm":[bb.xlen,bb.ylen,bb.zlen]},"reopened STEP, one valid solid")
    # Full end connector corridors include assumed plug bodies AND bend allowance.
    # Based on metal end planes, deliberately cover entire face width/height above lip.
    corridors={"RF_plug_and_bend":m.block(124,60,42,0,112.3115,10.5),
               "USB_DC_ref_plug_and_bend":m.block(124,70,42,0,-111.2055,10.5),
               "Kslot_front":m.block(20,17,13,71.1745,68.7295,16.91),
               "Kslot_rear":m.block(20,17,13,-71.1735,-62.8645,16.91)}
    for name,ko in corridors.items():
        v=sum(s.intersect(ko).Volume() for n,s in custom)
        check(name,v<.001,v,"zero bracket intrusion into assumed corridor; actual cables/lock must be checked")
    # Assembly path with retainers, spacers and screws removed: straight +Z lift.
    path=[]
    for lift in [0,.2,.5,1,2,3,5,8,12,20,50]:
        v=dev.translate((0,0,lift)).intersect(base).Volume(); path.append([lift,v])
    check("device_vertical_removal",max(v for _,v in path)<.001,path,"11 positions; straight extraction from monotonic open pocket; cables disconnected")
    # Cylinder driver/socket envelopes, referenced to actual fastener axes.
    tool_checks=[]
    for x in [-p['retainer_bolt_x'],p['retainer_bolt_x']]:
        for y in m.stations(p):
            tool=m.cylinder(14,60,x,y,m.bar_z(p)+p['bar_thickness']+1+5)
            tool_checks.append(tool.intersect(dev).Volume())
    check("retainer_driver_access",max(tool_checks)<.001,tool_checks,"14 mm driver envelope, 60 mm above screw head")
    tool_checks=[]
    for x in [-p['panel_bolt_x'],p['panel_bolt_x']]:
        for sy in [-1,1]:
            tool=m.cylinder(14,90,x,p['center_y']+sy*70,p['base_thickness']+6)
            tool_checks.append(sum(tool.intersect(s).Volume() for n,s,k in items if k!='hardware'))
    check("flat_panel_driver_access",max(tool_checks)<.001,tool_checks,"14 mm driver envelope; hardware itself excluded")
    # Capture checks: film loss + permitted gap + analytically bounded beam deflection.
    # Intentional intersections after imposed translation demonstrate positive stops.
    zpan=p['device_pan_z']; cy=p['center_y']; up=p.get('retention_up_screen',1.03); down=-p['film_thickness']
    tilt=math.degrees(math.atan((up-down)/p['support_y_pitch'])); zm=(up+down)/2
    witnesses=[]
    for sign in [-1,1]:
        pose=dev.rotate((0,cy,zpan),(1,cy,zpan),sign*tilt).translate((0,sign*3,zm))
        end=m.block(80,18,p['end_stop_top']-p['pocket_floor_z'],0, p['pocket_ymax']+9 if sign>0 else p['pocket_ymin']-9,p['pocket_floor_z'])
        v=pose.intersect(base.intersect(end)).Volume(); witnesses.append([sign,tilt,v])
    check("end_stop_capture_extreme_pose",min(row[2] for row in witnesses)>.1,witnesses,"both end stops obstruct 3 mm escape under bounded film-loss/pitch pose; not a dynamic simulation")
    rollw=[]
    for sign in [-1,1]:
        pose=dev.translate((sign*2,0,up))
        rollw.append(pose.intersect(base).Volume())
    check("lateral_stop_capture",min(rollw)>.1,rollw,"both side stops obstruct 2mm lateral escape at elevated pose")
    import vertical_adapter as va
    upright=m.upright_items(p,items); adapters=va.build_adapter_pair()
    others=[(n,s) for n,s,k in upright if k in ('base','bar','spacer','device','film')]
    for n,a in adapters.items():
        vs=[(bn,a.intersect(bs).Volume()) for bn,bs in others]
        check(n+"_fit",max(v for _,v in vs)<.001,vs,"zero interference with transformed cradle; bearing face contact permitted")
    # Screws only intentionally intersect unmodeled thread regions.
    grip=p['bar_thickness']+1+p['spacer_length']+sum(q['thickness'] for q in p['nominal_shims'])
    entry=p['retainer_bolt_length']-grip;tip=p['thread_boss_top']-entry
    check("retainer_screw_stack",entry>=7.5 and tip>=.5,
          {"under_head_length":p['retainer_bolt_length'],"grip":grip,"nominal_entry":entry,"nominal_tip_above_base":tip},
          "shop gauge >=7.5mm complete threads and >=0.5mm tip recess after actual tolerances; nominal only")
    for name in ('B210_flat_assembly_P2','B210_upright_assembly_P2'):
        s=cq.importers.importStep(str(out/f'{name}.step')).val(); b=s.BoundingBox()
        expected=len(dev.Solids())+(len(m.flat_items(p)) if 'flat' in name else len(upright))-1
        check(name+"_reopened",all(q.isValid() for q in s.Solids()) and len(s.Solids())==expected,
              {"solids":len(s.Solids()),"expected":expected,"bbox_mm":[b.xlen,b.ylen,b.zlen]},
              "all parts and device solids present; scale mm; no fused assembly")
    report={"units":"mm", "checks":checks,"status":"PASS" if all(c['status']=='PASS' for c in checks) else "FAIL",
      "limitations":["Rigid ideal CAD only; not FEA, fatigue, thermal or physical qualification.",
      "Cable keepouts are explicit assumptions, not CAD of purchased cables. K-slot lock body unspecified.",
      "Threads are ideal minor/shank geometry; intentional thread engagement is excluded from collision assertion.",
      "Device internal original assembly overlaps preserved; original has duplicate front overlays.",
      "Endstop capture pose is bounded quasistatic screening, not proof of arbitrary six-axis motion or impact."]}
    (out/'verification_report.json').write_text(json.dumps(report,indent=2))
    if report['status']!='PASS': raise SystemExit(1)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,default=HERE/'exports')
    run(ap.parse_args().out)
