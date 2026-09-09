"""B210 P2: reproducible, millimetre-based CadQuery source.

Feature order: blank > pocket/end relief > window/feet > hard lands > holes.
No source device geometry is modified. Mating coordinates are named in params.json.
Run with Python 3.11 + cadquery==2.7.0. See README.md for portable regeneration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import cadquery as cq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def load_params():
    return json.loads((HERE / "params.json").read_text())


def block(w, d, h, x=0, y=0, z=0, r=0):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r:
        wp = wp.edges("|Z").fillet(r)
    return wp.val().translate((x, y, z))


def cylinder(d, h, x=0, y=0, z=0):
    return cq.Solid.makeCylinder(d / 2, h, cq.Vector(x, y, z))


def stations(p):
    return [p["center_y"] + s*p["support_y_pitch"]/2 for s in (-1, 1)]


def mill_rect(w, d, h, x, y, z, radius):
    """Rectangular clearance pocket with dog-bone corner relief for a 6mm cutter.
    Relief centers at corners allow a square envelope and no internal sharp corner.
    """
    # Tangent quarter-round pockets extended with corner circles: manufacturable
    # by the stated cutter, with explicit relief overcuts outside the nominal box.
    s = block(w, d, h, x, y, z, radius)
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = s.fuse(cylinder(2*radius, h, x+sx*(w/2-radius/2),
                                y+sy*(d/2-radius/2), z))
    return s.clean()


def create_base(p):
    cy, t = p["center_y"], p["base_thickness"]
    s = block(p["base_width"], p["base_length"], t, y=cy,
              r=p["base_corner_radius"])
    s = cq.Workplane(obj=s).edges("#Z").chamfer(p["edge_break"]).val()
    py0, py1 = p["pocket_ymin"], p["pocket_ymax"]
    s = s.cut(mill_rect(p["pocket_width"], py1-py0, t,
                       0, (py0+py1)/2, p["pocket_floor_z"], p["cutter_radius"]))
    # Above the low metal-pan stops the larger enclosure labels have clear space.
    s = s.cut(mill_rect(p["pocket_width"],
                       p["label_relief_ymax"]-p["label_relief_ymin"], t,
                       0, (p["label_relief_ymax"]+p["label_relief_ymin"])/2,
                       p["end_stop_top"], p["cutter_radius"]))
    s = s.cut(block(p["window_width"], p["window_length"], t+2,
                    y=cy, z=-1, r=5))
    for x in (-p["foot_x"], p["foot_x"]):
        for y in (-p["foot_y"], p["foot_y"]):
            s = s.cut(cylinder(p["foot_relief_diameter"], t+2, x, y, -1))
    # Integral aluminum lands carry load even if the anti-mar film disappears.
    for x in (-p["support_x"], p["support_x"]):
        for y in stations(p):
            s = s.fuse(block(p["support_land_width"], p["support_land_length"],
                            p["support_land_height"], x, y, p["pocket_floor_z"], 1))
    for x in (-p["retainer_bolt_x"], p["retainer_bolt_x"]):
        for y in stations(p):
            s = s.fuse(cylinder(p["thread_boss_od"], p["thread_boss_top"]-t, x, y, t))
            s = s.cut(cylinder(p["tap_minor_representation"], p["thread_boss_top"]+2, x, y, -1))
    for x in (-p["panel_bolt_x"], p["panel_bolt_x"]):
        for sign in (-1, 1):
            s = s.cut(cylinder(p["clearance_hole"], t+2, x,
                               cy+sign*p["panel_bolt_y_pitch"]/2, -1))
    return s.clean()


def create_bar(p):
    s = block(p["base_width"], p["bar_width_y"], p["bar_thickness"],
              r=p["bar_corner_radius"])
    s = cq.Workplane(obj=s).edges("#Z").chamfer(p["edge_break"]).val()
    for x in (-p["retainer_bolt_x"], p["retainer_bolt_x"]):
        s = s.cut(cylinder(p["clearance_hole"], p["bar_thickness"]+2, x, 0, -1))
    return s.clean()


def create_spacer(p):
    s = cylinder(p["spacer_od"], p["spacer_length"])
    return s.cut(cylinder(p["spacer_id"], p["spacer_length"])).clean()


def film(p):
    return block(p["support_land_width"], p["support_land_length"],
                 p["film_thickness"], r=1)


def washer():
    return cylinder(10, 1).cut(cylinder(5.3, 1))


def foot_washer():
    """McMaster91100A140 nominal envelope; actual thickness1.0-1.4mm."""
    return cylinder(15, 1.2).cut(cylinder(5.3, 1.2))


def shim(od, id_, thickness):
    return cylinder(od, thickness).cut(cylinder(id_, thickness))


def bar_z(p):
    return p["thread_boss_top"] + sum(q["thickness"] for q in p["nominal_shims"]) + p["spacer_length"]


def cap_screw(length):
    """Simplified M5 ISO4762 envelope; no helical thread or certification geometry."""
    s = cylinder(5, length, z=-length).fuse(cylinder(8.5, 5))
    key = cq.Workplane("XY").polygon(6, 4/0.8660254038).extrude(3).val().translate((0,0,2))
    return s.cut(key)


def nut():
    s = cq.Workplane("XY").polygon(6, 8/0.8660254038).extrude(5).val()
    return s.cut(cylinder(4.2, 5))


def get_device(p, source=None):
    path = Path(source) if source else HERE / "references" / "input_device.step"
    if not path.exists():
        raise FileNotFoundError(f"Supply --source ORIGINAL.step; missing {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != p["source_sha256"]:
        raise ValueError("Source STEP hash differs; remeasure the device before regeneration")
    s = cq.importers.importStep(str(path)).val()
    return (s.rotate((0,0,0),(1,0,0),90).rotate((0,0,0),(0,0,1),180)
            .translate(tuple(p["source_frame_translation"]))
            .translate((0,0,p["device_pan_z"])))


COLORS = {"base": (0.14,0.18,0.23), "bar": (0.14,0.18,0.23),
          "spacer": (0.50,0.54,0.60), "film": (0.15,0.5,0.58),
          "device": (0.72,0.74,0.78), "hardware": (0.72,0.76,0.81),
          "adapter": (0.28,0.32,0.38)}


def flat_items(p, source=None, panel_hardware=True):
    items = [("B210_device", get_device(p, source), "device"),
             ("B210_M01_base", create_base(p), "base")]
    zbar = bar_z(p)
    for j,y in enumerate(stations(p)):
        items.append((f"B210_M02_bar_{j+1}", create_bar(p).translate((0,y,zbar)), "bar"))
        for i,x in enumerate((-p["retainer_bolt_x"], p["retainer_bolt_x"])):
            tag=f"{j+1}_{i+1}"
            zshim = p["thread_boss_top"]
            for a,q in enumerate(p["nominal_shims"]):
                items.append((f"shim_{q['part_number']}_{tag}",shim(q["od"],q["id"],q["thickness"]).translate((x,y,zshim)),"hardware"))
                zshim += q["thickness"]
            items += [(f"B210_M03_spacer_{tag}", create_spacer(p).translate((x,y,zshim)), "spacer"),
                      (f"M5_washer_{tag}", washer().translate((x,y,zbar+p["bar_thickness"])), "hardware"),
                      (f"M5x45_retainer_{tag}", cap_screw(p["retainer_bolt_length"]).translate((x,y,zbar+p["bar_thickness"]+1)), "hardware")]
        for i,x in enumerate((-p["support_x"], p["support_x"])):
            tag=f"{j+1}_{i+1}"
            items += [(f"lower_film_{tag}", film(p).translate((x,y,p["device_pan_z"]-p["film_thickness"])), "film"),
                      (f"upper_film_{tag}", film(p).translate((x,y,zbar-p["film_thickness"])), "film")]
    if panel_hardware:
        for i,x in enumerate((-p["panel_bolt_x"], p["panel_bolt_x"])):
            for j,y in enumerate([p["center_y"]+s*p["panel_bolt_y_pitch"]/2 for s in (-1,1)]):
                tag=f"{i+1}_{j+1}"
                items += [(f"flat_panel_M5x25_{tag}", cap_screw(25).translate((x,y,p["base_thickness"]+1)),"hardware"),
                          (f"flat_panel_upper_washer_{tag}", washer().translate((x,y,p["base_thickness"])),"hardware"),
                          (f"flat_panel_lower_washer_{tag}", washer().translate((x,y,-7)),"hardware"),
                          (f"flat_panel_locknut_{tag}", nut().translate((x,y,-12)),"hardware")]
    return items


def upright_items(p, items=None):
    import vertical_adapter as va
    items = flat_items(p, panel_hardware=False) if items is None else items
    out=[(n,va.transform_cradle(s),k) for n,s,k in items if not n.startswith("flat_panel")]
    for n,s in va.build_adapter_pair().items():
        out.append((n,s,"adapter"))
    for i,y in enumerate(va.PARAMS["bracket_y_centers"]):
        for j,z in enumerate(va.PARAMS["web_hole_z"]):
            tag=f"{i+1}_{j+1}"
            out += [(f"upright_web_M5x25_{tag}", cap_screw(25).rotate((0,0,0),(0,1,0),-90).translate((-va.PARAMS['web_t']-1,y,z)),"hardware"),
                    (f"upright_web_rear_washer_{tag}",washer().rotate((0,0,0),(0,1,0),90).translate((-va.PARAMS['web_t']-1,y,z)),"hardware"),
                    (f"upright_web_front_washer_{tag}",washer().rotate((0,0,0),(0,1,0),90).translate((p['base_thickness'],y,z)),"hardware"),
                    (f"upright_web_locknut_{tag}",nut().rotate((0,0,0),(0,1,0),90).translate((p['base_thickness']+1,y,z)),"hardware")]
        for j,x in enumerate(va.PARAMS["foot_hole_x"]):
            tag=f"{i+1}_{j+1}"
            out += [(f"upright_foot_M5x30_{tag}",cap_screw(30).translate((x,y,va.PARAMS['foot_bolt_boss_top']+1.2)),"hardware"),
                    (f"upright_foot_upper_washer_{tag}",foot_washer().translate((x,y,va.PARAMS['foot_bolt_boss_top'])),"hardware"),
                    (f"upright_foot_lower_washer_{tag}",washer().translate((x,y,-7)),"hardware"),
                    (f"upright_foot_locknut_{tag}",nut().translate((x,y,-12)),"hardware")]
    return out


def assembly(items, name):
    a=cq.Assembly(name=name)
    for label,s,kind in items:
        a.add(s, name=label, color=cq.Color(*COLORS[kind]))
    return a


def export_all(p, source, out):
    out.mkdir(parents=True, exist_ok=True)
    parts={"B210_M01_base":create_base(p), "B210_M02_retainer":create_bar(p),
           "B210_M03_spacer":create_spacer(p), "B210_M04_film":film(p)}
    for name,shape in parts.items():
        assert shape.isValid() and len(shape.Solids())==1, name
        cq.exporters.export(shape, str(out/f"{name}_P2.step"))
    items=flat_items(p,source)
    assembly(items,"B210_FLAT_P2").save(str(out/"B210_flat_assembly_P2.step"))
    # Exploded service state: remove screw/washer/spacer/bar units above device.
    exploded=[]
    for n,s,k in items:
        dz=0 if k in ("base", "device") or n.startswith("lower") else 45
        exploded.append((n,s.translate((0,0,dz)),k))
    assembly(exploded,"B210_SERVICE_P2").save(str(out/"B210_exploded_P2.step"))
    try:
        import vertical_adapter as va
        upright=upright_items(p,items)
        assembly(upright,"B210_UPRIGHT_P2").save(str(out/"B210_upright_assembly_P2.step"))
    except ImportError:
        upright=[]
    metadata={"units":"mm", "revision":p["revision"], "parts":{}}
    for n,s in parts.items():
        b=s.BoundingBox()
        metadata["parts"][n]={"volume_mm3":s.Volume(), "bbox_mm":[b.xlen,b.ylen,b.zlen],
                                "valid":s.isValid(), "solids":len(s.Solids())}
    (out/"part_metadata.json").write_text(json.dumps(metadata,indent=2))
    return items, upright, exploded


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--out",type=Path,default=HERE/"exports")
    ap.add_argument("--render",action="store_true")
    args=ap.parse_args()
    p=load_params()
    items,upright,exploded=export_all(p,args.source,args.out)
    if args.render:
        from render_support import render_scene, section_cut
        for name,scene,views in (("flat",items,("iso","top","front","back","left","right","bottom")),
                                  ("upright",upright,("iso","front","right")),
                                  ("exploded",exploded,("iso",))):
            if scene:
                render_scene([(s,COLORS[k],1) for _,s,k in scene], args.out/"views",name,views=views,size=1500)
        for axis,station in (("Y",stations(p)[0]),("X",0)):
            clipped=[]
            for _,s,k in items:
                bb=s.BoundingBox()
                if getattr(bb,axis.lower()+'min') >= station-1e-6:
                    continue
                clipped.append((s if getattr(bb,axis.lower()+'max') <= station+1e-6
                                else section_cut(s,axis,station),COLORS[k],1))
            render_scene(clipped,
                         args.out/"views",f"section_{axis}",views=("iso",),size=1500)
    print(f"Exported P2 to {args.out}")


if __name__=="__main__":
    main()
