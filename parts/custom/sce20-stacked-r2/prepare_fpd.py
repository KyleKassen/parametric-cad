"""Create new R2 native scripts; actual FPD execution/save/readback is required."""

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "sce20-layout"
spec = importlib.util.spec_from_file_location("sce20_fpd_reference", OLD / "prepare_fpd.py")
fpd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fpd)
fpd.OUT = HERE / "FPE"
fpd.STAGE = Path("C:/Users/KyleKassen/Documents/FPE_SCE20_20260909_R2")
fpd.OUT.mkdir(exist_ok=True)
fpd.STAGE.mkdir(exist_ok=True)
fpd.COMMON_JS = fpd.COMMON_JS.replace('s.name=="Backpanel_R1"', 's.name=="Backpanel_R2"')
fpd.COMMON_JS = fpd.COMMON_JS.replace(
    "function verifyPanel(p,s)", "function verifyPanel(p,s,isReloaded)"
)
fpd.COMMON_JS = fpd.COMMON_JS.replace("verifyPanel(reloaded,s);", "verifyPanel(reloaded,s,true);")
fpd.COMMON_JS = fpd.COMMON_JS.replace(
    '} else if(a.kind=="contour_cavity") {',
    '} else if(a.kind=="rect_hole") {\n'
    '      if(!e.IsRectHole()) Error("not rectangular through cutout "+a.id);\n'
    "      var cb=isReloaded?a.bevel_front:0;\n"
    '      near(e.Width(),a.width+2*cb,a.id+" native width"); '
    'near(e.Height(),a.height+2*cb,a.id+" native height");\n'
    '      near(e.CornerRadius(),a.radius,a.id+" native radius");\n'
    '    } else if(a.kind=="contour_cavity") {',
    1,
)
fpd.COMMON_JS = fpd.COMMON_JS.replace(
    'else if(a.kind=="hole") e=new DrillHole(a.id,a.diameter);',
    'else if(a.kind=="hole") e=new DrillHole(a.id,a.diameter);\n'
    '    else if(a.kind=="rect_hole") e=new RectHole(a.id,a.width,a.height,a.radius);',
)
fpd.COMMON_JS = fpd.COMMON_JS.replace(
    "p.AddElement(e,a.x,a.y);",
    "p.AddElement(e,a.x,a.y);\n"
    '    if(a.kind=="rect_hole") '
    "e.SetEdgeMachining(bevel_45,a.bevel_front,bevel_45,a.bevel_reverse);",
)
p = json.loads((HERE / "params.json").read_text())
s = dict(
    name="Backpanel_R2",
    width=p["width"],
    height=p["height"],
    thickness=p["thickness"],
    radius=p["corner_radius"],
    bevel=0.4,
    material_id=5,
    color_id=1,
    elements=[],
    save=(fpd.STAGE / "Backpanel_R2.fpd").as_posix(),
    remark=(
        "R2 compact stacked layout. Original431.8square outline/R6.35 and6factoryholes."
        "12M3 LOAD studsL12 +8M3female LOAD standoffsL20,allFRONT,offset0. "
        "Raised supports require separate Wurth971300321(4) and971500321(4) "
        "extension columns. Bedrock remains directly against panel. "
        "See R2 assembly and ordering notes; not load/thermal qualification."
    ),
)
for h in p["mounting_holes"]:
    s["elements"].append(
        dict(kind="hole", id=h["id"], x=h["x"], y=h["y"], diameter=h["diameter"], side="front")
    )
for h in p["hardware"]:
    s["elements"].append(
        dict(
            kind="bolt",
            id=h["id"],
            x=h["x"],
            y=h["y"],
            catalog=h["catalog_code"],
            length=h["length"],
            side="front",
        )
    )
carrier = json.loads((HERE / "carrier/fpd_input.json").read_text())
carrier["save"] = (fpd.STAGE / (carrier["name"] + ".fpd")).as_posix()
parser = argparse.ArgumentParser()
parser.add_argument("--only", choices=["carrier", "backpanel"])
parser.add_argument("--verify-existing", action="store_true")
args = parser.parse_args()
panels = [carrier] if args.only == "carrier" else [s] if args.only == "backpanel" else [s, carrier]
if args.verify_existing:
    import shutil

    script = fpd.COMMON_JS
    for panel in panels:
        script += (
            "\nvar s="
            + json.dumps(panel)
            + ';var p=LoadFrontpanel(s.save,s.name+"_verified");verifyPanel(p,s,true);'
            'AddFrontpanel(p);Print("PASS RELOADED "+s.name+"\\n");\n'
        )
    path = fpd.OUT / "SCE20_VERIFY_R2_V2.fpjs"
    path.write_text(script, encoding="utf-8")
    shutil.copy2(path, Path.home() / "AppData/Roaming/FrontDesign/Scripts" / path.name)
    # Store corrected generation sources alongside verified targets. Saving
    # remains overwrite-disabled when a user executes them in the application.
    script = (
        fpd.COMMON_JS
        + "\n"
        + "\n".join("createPanel(" + json.dumps(panel) + ");" for panel in panels)
    )
    (fpd.OUT / "SCE20_STACKED_R2.fpjs").write_text(script, encoding="utf-8")
else:
    fpd.write_script(
        panels,
        "SCE20_CARRIER_R2"
        if args.only == "carrier"
        else "SCE20_BACKPANEL_R2"
        if args.only == "backpanel"
        else "SCE20_STACKED_R2",
    )
