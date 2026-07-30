"""
Reference mast node enclosure - the worked exemplar for this repo.

WHY THIS PART EXISTS
    Every other part under parts/ predates lib/features.py, so there was no
    in-repo answer to "what does a finished part look like here". This is that
    answer: a sealed, mast-mounted electronics body built entirely out of the
    design-language builders, in the kernel-safe phase order, with every
    refinement claim backed by a number the builder measured rather than a
    number the author asserted. Copy the shape of this file, not its numbers.

WHAT THE PART IS
    A 6061-T6 billet tub, 198 x 149 x 88 mm inside a 200 x 150 x 90 envelope,
    that hangs off a mast bracket on its -Y flange. The cavity opens DOWNWARD
    and a gasketed lid (a separate part) bolts up onto the -Z seal land, so the
    seal plane faces the ground and water can never stand on it. The roof of
    the cavity is a 14 mm cold plate: the dissipating modules bolt up to its
    inner face and the fin bank stands on its outer face, so the thermal path
    is one wall thick. Both connectors sit on their own lands on the outboard
    +Y wall, under a drip hood. Service is from below - undo the lid and the
    electronics stay bolted to the cold plate above it.

THE THREE CONSTRAINTS THAT SHAPED IT
    1. 3-axis machinable. Every feature is reachable along +/-X, +/-Y or +/-Z
       with the part in one of six setups. That is why the cavity is a straight
       prismatic pocket with no undercut, and why there are no features on the
       cavity's vertical inner walls - a top-opening pocket cannot machine them.
    2. The seal band IS the wall. A face seal needs cavity edge -> land ->
       groove -> land -> screw -> part edge, which is 24 mm here. Rather than
       pay that as dead metal, the band carries the structure: it stays thick
       where it is loaded (the +Y wall spreads heat into the fins, the -Y wall
       carries the flange moment) and is pocketed back to 9.5 mm on the +/-X
       flanks, where nothing but handling load reaches it.
    3. Nothing decorative. The rib fields restore what the flank pockets
       removed, the fins carry the 18 W, the hood keeps runoff off the
       connectors, the vent equalises pressure. Each one reports its number.

ORDER OF OPERATIONS
    lib.features.Build enforces base -> boolean -> pocket -> rib -> hole ->
    break and this part never needs the break phase: every radius and every rim
    chamfer is baked into a 2D profile while the solid it belongs to is still a
    lone simple prism. A blanket late chamfer over the rib fields is the one
    move known to take OCCT down with SIGSEGV rather than an exception.

Units: mm throughout.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PART_DIR.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.features import (  # noqa: E402
    STYLE,
    Build,
    base_flange,
    blend_transition,
    bolt_pattern,
    connector_land,
    drip_edge,
    emblem,
    fastener_holes,
    fin_bank,
    lightening_pocket,
    oring_groove,
    recessed_panel,
    rib_field,
    rounded_box,
    step_shoulder,
    tapped_boss,
    tapped_hole_grid,
)

PARAMS_FILE = PART_DIR / "params.json"
EXPORTS_DIR = PART_DIR / "exports"

# Every measurement a builder handed back while the part was being built, so
# DESIGN.md can quote proof instead of adjectives. Rebuilt on every create_part.
MEASURED: dict[str, object] = {}


def load_params(path: Path = PARAMS_FILE) -> dict:
    """The build inputs. params.json is the only place a dimension is written."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# frames
#
# Every builder in lib/features.py works in a face's own frame, so the frames
# are declared once, up front, from the STOCK solid - before any feature exists
# that a ">Z" or "+Y" selector could latch onto by mistake. Each plane's origin
# sits on the part centreline of that face at the datum end, so a feature's
# (u, v) reads as a real coordinate rather than an offset from a bbox centre.
# --------------------------------------------------------------------------- #


def _plane(origin, x_dir, normal) -> cq.Plane:
    return cq.Plane(origin=cq.Vector(*origin), xDir=cq.Vector(*x_dir), normal=cq.Vector(*normal))


def _frames(d: dict) -> dict[str, cq.Plane]:
    """The six working frames, plus the cavity roof, in world coordinates."""
    hl, hw, h = d["body_length"] / 2, d["body_depth"] / 2, d["body_height"]
    return {
        # -Z seal face. u = +X, v = -Y, origin on the face.
        "seal": _plane((0, 0, 0), (1, 0, 0), (0, 0, -1)),
        # +Z roof. u = +X, v = +Y.
        "roof": _plane((0, 0, h), (1, 0, 0), (0, 0, 1)),
        # +Y outboard wall. u = -X, v = +Z measured from the seal face.
        "front": _plane((0, hw, 0), (-1, 0, 0), (0, 1, 0)),
        # -Y mast wall. u = +X, v = +Z measured from the seal face.
        "rear": _plane((0, -hw, 0), (1, 0, 0), (0, -1, 0)),
        # -X and +X flanks. u runs toward the mast on -X and outboard on +X, so
        # one local layout produces a mirror-symmetric pair.
        "left": _plane((-hl, 0, 0), (0, -1, 0), (-1, 0, 0)),
        "right": _plane((hl, 0, 0), (0, 1, 0), (1, 0, 0)),
        # cavity roof, seen from inside: normal points down into the cavity.
        "coldplate": _plane((0, 0, d["cavity_depth"]), (1, 0, 0), (0, 0, -1)),
    }


def _front_uv(centre) -> tuple[float, float]:
    """params.json states outboard-face features in world (x, z); the frame is (-x, z)."""
    return (-centre[0], centre[1])


_LADDER_KEYS = ("radius", "break", "fillet")


def ladder_audit(params: dict) -> dict:
    """
    Prove that every radius, chamfer and root fillet in params.json is a Style rung.

    Holding the numbers in params.json is what lets a reviewer change them
    without reading code. It is also exactly how a repo drifts into eleven
    one-off radii, because nothing stops someone typing 13.5. This walks the
    file and reports anything that is not on `STYLE.radius_ladder` or
    `STYLE.break_ladder`, so drift shows up in the build log instead of in a
    design review six months later.

    Returns the rung list and every off-ladder value it found, as
    (json path, value) pairs. An empty list is the pass condition.
    """
    rungs = sorted(set(STYLE.radius_ladder) | set(STYLE.break_ladder))
    off: list[tuple[str, float]] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else key)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            leaf = path.rsplit(".", 1)[-1]
            if leaf.endswith(_LADDER_KEYS) and not any(abs(node - r) < 1e-9 for r in rungs):
                off.append((path, float(node)))

    walk(params.get("dimensions", {}), "dimensions")
    walk(params.get("features", {}), "features")
    return {"rungs": rungs, "off_ladder": off}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def break_mouth(solid, pocket, plane: cq.Plane, c: float):
    """
    Chamfer a pocket mouth by CUTTING a tool that already carries the chamfer.

    A pocket mouth is a convex rim, and an unbroken one undoes most of what the
    pocket bought: the part reads as a hole punched in a slab. The chamfer
    cannot be added afterwards (a late 3D chamfer over boolean-built geometry
    is the repo's main kernel failure), so it is built into a lone rounded
    prism whose bottom edge is already broken, sunk `c` below the face so its
    chamfer band spans exactly the mouth.
    """
    sunk = cq.Plane(origin=plane.origin - plane.zDir * c, xDir=plane.xDir, normal=plane.zDir)
    tool = rounded_box(
        pocket.length + 2 * c,
        pocket.width + 2 * c,
        20.0,
        pocket.radius + c,
        bottom_break=c,
        plane=sunk,
    )
    offset = plane.xDir * pocket.plane.origin.sub(plane.origin).dot(plane.xDir) + plane.yDir * (
        pocket.plane.origin.sub(plane.origin).dot(plane.yDir)
    )
    return solid.cut(tool.translate(offset.toTuple()))


def _bore(plane: cq.Plane, uv: tuple[float, float], diameter: float, depth: float) -> cq.Shape:
    """
    A depth-limited round cutter, started 1 mm proud of the face.

    Depth-limited on purpose: an aperture cut "through" a hollow part exits the
    far wall as well. Every aperture here is told how far to go.
    """
    origin = plane.toWorldCoords(uv) + plane.zDir * 1.0
    return cq.Solid.makeCylinder(diameter / 2, depth + 1.0, origin, plane.zDir * -1.0)


def _slot(
    plane: cq.Plane,
    uv: tuple[float, float],
    length: float,
    width: float,
    radius: float,
    depth: float,
):
    """A depth-limited rounded-rectangular cutter, started 1 mm proud of the face."""
    into = cq.Plane(
        origin=plane.toWorldCoords(uv) + plane.zDir * 1.0,
        xDir=plane.xDir,
        normal=plane.zDir * -1.0,
    )
    return rounded_box(
        length, width, depth + 1.0, radius, top_break=0.0, bottom_break=0.0, plane=into
    )


def groove_rim_break(
    solid, groove, plane: cq.Plane, length: float, width: float, radius: float, c: float
):
    """
    Break both rims of a face-seal groove with a 45 deg lead-in.

    Not cosmetic and not a metric trick: a knife-edged groove rim shaves the
    cord on assembly, which is how a nominally good seal leaks on its second
    fit - the Parker handbook asks for it. oring_groove() does not offer it, so
    it is built the way every other break on this part is: as a tool whose own
    rim already carries the chamfer, cut from a lone simple solid.

    Ring-shaped - an oversized tool with a broken BOTTOM rim, minus a plug that
    protects the inner land and carries the matching break on its TOP rim - so
    the outer and inner groove walls both get their lead-in and the two lands
    either side of the cord are left flat.
    """
    gw = groove.groove_width
    sunk = cq.Plane(origin=plane.origin - plane.zDir * c, xDir=plane.xDir, normal=plane.zDir)
    outer = rounded_box(
        length + gw + 2 * c,
        width + gw + 2 * c,
        20.0,
        radius + gw / 2 + c,
        bottom_break=c,
        plane=sunk,
    )
    plug_base = cq.Plane(
        origin=plane.origin - plane.zDir * (c + 2.0), xDir=plane.xDir, normal=plane.zDir
    )
    plug = rounded_box(
        length - gw,
        width - gw,
        c + 2.0,
        max(radius - gw / 2, 1.0),
        top_break=c,
        bottom_break=0.0,
        plane=plug_base,
    )
    return solid.cut(outer.cut(plug))


def _drip_kerf(plane: cq.Plane, dh: dict) -> cq.Shape:
    """
    The drip groove, cut as its own operation.

    drip_edge() will cut the kerf itself, but its rim chamfer is a blanket
    `edges("|X").chamfer(...)` inside a try/except, and the kerf's own edges
    make that chamfer impossible - so asking for both silently returns a lip
    with FOUR knife edges down its full length. Building the lip with kerf=0
    and cutting the groove here gets both. Half-round rather than square, so
    the groove's rims are tangent instead of sharp; it breaks surface tension
    just as well.
    """
    drop = dh["projection"] * math.tan(math.radians(dh["shed_deg"]))
    z0 = dh["projection"] - dh["kerf_setback"] - dh["kerf"]
    y_soffit = -(dh["thickness"] + drop * z0 / dh["projection"])
    span = dh["span"] + 2.0
    cyl = cq.Solid.makeCylinder(
        dh["kerf"] / 2, span, cq.Vector(-span / 2, y_soffit, z0), cq.Vector(1, 0, 0)
    )
    return cyl.moved(cq.Location(plane))


# --------------------------------------------------------------------------- #
# the build
# --------------------------------------------------------------------------- #


def _build(params: dict | None = None) -> Build:
    if params is None:
        params = load_params()
    d = params["dimensions"]
    f = params["features"]
    MEASURED.clear()

    L, W, H = d["body_length"], d["body_depth"], d["body_height"]
    pl = _frames(d)

    audit = ladder_audit(params)
    MEASURED["off_ladder_values"] = audit["off_ladder"]
    MEASURED["process_wall_mm"] = round(
        STYLE.wall(params["process"], span=f["side_panel"]["panel_length"]), 2
    )

    # ---------------------------------------------------------------- 1. base
    # Plan radii and both rim chamfers live in the profile of a lone prism.
    # Nothing later in this file ever asks the kernel for a 3D fillet.
    b = Build(
        rounded_box(
            L,
            W,
            H,
            d["plan_radius"],
            top_break=d["rim_break"],
            bottom_break=d["rim_break"],
        ),
        "stock",
    )

    # ------------------------------------------------------------- 2. boolean
    # The mast flange, built as two chamfered levels rather than with
    # base_flange(edge="step"): that path stacks two bare prisms and leaves
    # every rim of both of them knife-sharp, which is 1.6 m of unbroken convex
    # edge on this part alone. Each level is a lone simple solid when its
    # chamfer is applied, so this stays kernel-safe.
    fl = f["base_flange"]
    flange = base_flange(
        fl["length"],
        fl["width"],
        fl["thickness"],
        radius=fl["radius"],
        edge=fl["edge"],
        edge_size=fl["edge_break"],
        holes="none",
        fastener=fl["screw"],
        plane=cq.Plane(
            origin=pl["rear"].origin + pl["rear"].yDir * (H / 2),
            xDir=pl["rear"].xDir,
            normal=pl["rear"].zDir,
        ),
    )
    b.boolean(lambda s: s.union(flange.solid), "mast_flange")

    pad_plane = cq.Plane(
        origin=flange.plane.origin - flange.plane.zDir * 0.2,
        xDir=flange.plane.xDir,
        normal=flange.plane.zDir,
    )
    b.boolean(
        lambda s: s.union(
            rounded_box(
                fl["pad_length"],
                fl["pad_width"],
                fl["pad_thickness"] + 0.2,
                fl["pad_radius"],
                top_break=fl["edge_break"],
                bottom_break=0.0,
                plane=pad_plane,
            )
        ),
        "mast_pad",
    )
    mate = cq.Plane(
        origin=flange.plane.origin + flange.plane.zDir * fl["pad_thickness"],
        xDir=flange.plane.xDir,
        normal=flange.plane.zDir,
    )

    # -------------------------------------------------------------- 3. pocket
    # The cavity, then its mouth, then the two flank pockets and their mouths.
    # Mouths are broken as they are made, while each rim is still simple.
    cav = b.pocket(
        lambda s: lightening_pocket(
            s,
            pl["seal"],
            size=(d["cavity_length"], d["cavity_width"]),
            depth=d["cavity_depth"],
            radius=d["cavity_radius"],
        ),
        "cavity",
    )
    MEASURED["cavity_wall_after_mm"] = round(cav.wall_after, 2)
    b.pocket(lambda s: break_mouth(s, cav, pl["seal"], d["cavity_mouth_break"]), "cavity_mouth")

    # Relief in the mating pad: only the band carrying the bolt pattern has to
    # be machined flat, so the middle comes out 1 mm. Standard practice, and it
    # stops the largest face on the part reading as a blank slab.
    relief = b.pocket(
        lambda s: recessed_panel(
            s,
            mate,
            size=(fl["relief_length"], fl["relief_width"]),
            depth=fl["relief_depth"],
            radius=fl["relief_radius"],
        ),
        "flange_relief",
    )
    b.pocket(lambda s: break_mouth(s, relief, mate, fl["relief_break"]), "flange_relief_mouth")

    # The flanks are layered rather than a single deep hole: a shallow recessed
    # panel sets the proud frame the reference standard asks for, and the
    # lightening pocket that actually removes the metal sits inside it with its
    # own frame. A single 18 mm pocket in this face reads as a casting window,
    # not as a machined enclosure - which the first hero render showed plainly.
    sp = f["side_panel"]
    panels: dict[str, object] = {}
    flanks: dict[str, object] = {}
    for side in ("left", "right"):
        panels[side] = b.pocket(
            lambda s, k=side: recessed_panel(
                s,
                pl[k],
                size=(sp["panel_length"], sp["panel_height"]),
                depth=sp["panel_depth"],
                radius=sp["panel_radius"],
                center=(0.0, sp["centre_v"]),
            ),
            f"flank_panel_{side}",
        )
        b.pocket(
            lambda s, k=side: break_mouth(s, panels[k], pl[k], sp["mouth_break"]),
            f"flank_panel_mouth_{side}",
        )
        flanks[side] = b.pocket(
            lambda s, k=side: lightening_pocket(
                s,
                panels[k].plane,
                size=(sp["pocket_length"], sp["pocket_height"]),
                depth=sp["pocket_depth"],
                radius=sp["pocket_radius"],
            ),
            f"flank_pocket_{side}",
        )
        b.pocket(
            lambda s, k=side: break_mouth(s, flanks[k], panels[k].plane, sp["mouth_break"]),
            f"flank_pocket_mouth_{side}",
        )
    MEASURED["flank_wall_after_mm"] = round(flanks["left"].wall_after, 2)

    # ----------------------------------------------------------------- 4. rib
    # Everything additive, in one phase, after the pockets it has to sit in.
    rib_volume = 0.0
    for side in ("left", "right"):
        rf = rib_field(
            flanks[side],
            sp["rib_pattern"],
            thickness=sp["rib_thickness"],
            count=sp["rib_count"],
        )
        rib_volume += rf.volume_mm3
        b.rib(lambda s, r=rf: s.union(r.solid), f"flank_ribs_{side}")
        MEASURED["rib_count_per_flank"] = rf.count
        MEASURED["rib_height_mm"] = round(rf.height, 2)
    MEASURED["rib_volume_mm3"] = round(rib_volume, 1)

    fb_p = f["fin_bank"]
    fins = fin_bank(
        height=fb_p["height"],
        base="flat",
        length=fb_p["blade_length"],
        span=fb_p["span"],
        pitch=fb_p["pitch"],
        thickness=fb_p["thickness"],
        plane=pl["roof"],
    )
    b.rib(lambda s: s.union(fins.solid), "fin_bank")
    MEASURED["fin_count"] = fins.count
    MEASURED["fin_pitch_mm"] = round(fins.pitch, 2)
    MEASURED["fin_added_area_mm2"] = round(fins.added_area_mm2, 0)

    # The circular connector never butts onto the wall: it arrives through a
    # concentric step-ring plinth, which is also the machined flat its gasket
    # needs.
    cc = f["circular_connector"]
    cc_uv = _front_uv(cc["centre"])
    cc_plane = cq.Plane(
        origin=pl["front"].toWorldCoords(cc_uv) - pl["front"].zDir * 0.2,
        xDir=pl["front"].xDir,
        normal=pl["front"].zDir,
    )
    b.rib(
        lambda s: s.union(
            step_shoulder(
                cc["plinth_lower_dia"],
                cc["plinth_upper_dia"],
                cc["plinth_height"] + 0.2,
                steps=cc["plinth_steps"],
                break_size=cc["plinth_break"],
                plane=cc_plane,
            )
        ),
        "circular_plinth",
    )

    vt = f["vent"]
    vt_uv = _front_uv(vt["centre"])
    vt_plane = cq.Plane(
        origin=pl["front"].toWorldCoords(vt_uv) - pl["front"].zDir * 0.2,
        xDir=pl["front"].xDir,
        normal=pl["front"].zDir,
    )
    b.rib(
        lambda s: s.union(
            blend_transition(
                vt["lower_dia"],
                vt["upper_dia"],
                vt["height"] + 0.2,
                kind=vt["collar"],
                facets=vt["facets"],
                plane=vt_plane,
            )
        ),
        "vent_boss",
    )

    dh = f["drip_hood"]
    hood_plane = cq.Plane(
        origin=pl["front"].toWorldCoords((0.0, dh["height_z"])) - pl["front"].zDir * dh["embed"],
        xDir=pl["front"].xDir,
        normal=pl["front"].zDir,
    )
    b.rib(
        lambda s: s.union(
            drip_edge(
                length=dh["span"],
                projection=dh["projection"],
                thickness=dh["thickness"],
                shed_deg=dh["shed_deg"],
                kerf=0.0,
                kerf_depth=0.0,
                radius=dh["edge_break"],
                plane=hood_plane,
            )
        ),
        "drip_hood",
    )

    cp = f["cold_plate"]
    for u, v in cp["standoff_positions"]:
        boss_plane = cq.Plane(
            origin=pl["coldplate"].toWorldCoords((u, v)),
            xDir=pl["coldplate"].xDir,
            normal=pl["coldplate"].zDir,
        )
        b.rib(
            lambda s, p=boss_plane: s.union(
                tapped_boss(
                    cp["standoff_height"],
                    fastener=cp["standoff_fastener"],
                    base_fillet=cp["standoff_base_fillet"],
                    plane=p,
                )
            ),
            "pcb_standoff",
        )

    # ---------------------------------------------------------------- 5. hole
    # The seal first, because it is the reason the band is 22 mm wide.
    ls = f["lid_seal"]
    groove = oring_groove(
        cord=ls["cord_diameter"],
        shape="rect",
        length=ls["groove_length"],
        width=ls["groove_width"],
        radius=ls["groove_radius"],
        plane=pl["seal"],
    )
    b.hole(lambda s: s.cut(groove.cut), "oring_groove")
    b.hole(
        lambda s: groove_rim_break(
            s,
            groove,
            pl["seal"],
            ls["groove_length"],
            ls["groove_width"],
            ls["groove_radius"],
            ls["rim_break"],
        ),
        "oring_rim_break",
    )
    MEASURED["seal_squeeze_pct"] = groove.squeeze_pct
    MEASURED["seal_fill_pct"] = groove.fill_pct
    MEASURED["seal_path_mm"] = round(groove.path_length, 1)

    lf = f["lid_fasteners"]
    lid_pat = bolt_pattern(
        "perimeter",
        length=L,
        width=W,
        inset=lf["inset"],
        fastener=lf["size"],
        target_pitch=lf["target_pitch"],
        plane=pl["seal"],
    )
    b.hole(
        lambda s: fastener_holes(
            s,
            lid_pat.points,
            plane=pl["seal"],
            fastener=lf["size"],
            kind="tap",
            depth=lf["tap_depth"],
        ),
        "lid_screws",
    )
    MEASURED["lid_screw_count"] = lid_pat.count
    MEASURED["lid_screw_pitch_mm"] = (lid_pat.pitch, lid_pat.pitch_v)
    MEASURED["lid_screw_in_band"] = lid_pat.in_band

    # Apertures are depth-limited: the front wall is 22 mm and the part behind
    # it is hollow, so a "through" cutter would exit the mast wall as well.
    wall_front = W / 2 - d["cavity_width"] / 2
    cc_top = cq.Plane(
        origin=cc_plane.origin + cc_plane.zDir * (cc["plinth_height"] + 0.2),
        xDir=cc_plane.xDir,
        normal=cc_plane.zDir,
    )
    through_front = cc["plinth_height"] + wall_front + 4.0
    b.hole(lambda s: s.cut(_bore(cc_top, (0.0, 0.0), cc["bore"], through_front)), "circular_bore")
    cc_pat = bolt_pattern(
        "circle",
        diameter=cc["bolt_circle"],
        count=cc["screw_count"],
        fastener=cc["screw"],
        start_angle=cc["screw_start_angle"],
        plane=cc_top,
    )
    b.hole(
        lambda s: fastener_holes(
            s,
            cc_pat.points,
            plane=cc_top,
            fastener=cc["screw"],
            kind="tap",
            depth=cc["screw_depth"],
        ),
        "circular_screws",
    )

    rc = f["rect_connector"]
    rc_uv = _front_uv(rc["centre"])
    land = b.hole(
        lambda s: connector_land(
            s,
            pl["front"],
            length=rc["length"],
            width=rc["width"],
            center=rc_uv,
            raised=rc["raised"],
            aperture=None,
            fastener=rc["screw"],
            screw_inset=rc["screw_inset"],
            screw_kind=None,
            break_size=rc["land_break"],
        ),
        "rect_land",
    )
    b.hole(
        lambda s: s.cut(
            _slot(
                land.plane,
                (0.0, 0.0),
                rc["aperture"][0],
                rc["aperture"][1],
                rc["aperture_radius"],
                rc["raised"] + wall_front + 4.0,
            )
        ),
        "rect_aperture",
    )
    b.hole(
        lambda s: fastener_holes(
            s,
            land.screw_points,
            plane=land.plane,
            fastener=rc["screw"],
            kind="tap",
            depth=rc["screw_depth"],
        ),
        "rect_screws",
    )
    ar = rc["aperture_radius"]
    MEASURED["rect_aperture_mm2"] = round(
        rc["aperture"][0] * rc["aperture"][1] - (4 - math.pi) * ar**2, 1
    )

    vt_top = cq.Plane(
        origin=vt_plane.origin + vt_plane.zDir * (vt["height"] + 0.2),
        xDir=vt_plane.xDir,
        normal=vt_plane.zDir,
    )
    b.hole(
        lambda s: s.cut(_bore(vt_top, (0.0, 0.0), vt["bore"], vt["height"] + wall_front + 4.0)),
        "vent_bore",
    )

    # The published payload interface: pitch held exactly, leftover to the margin.
    grid = b.hole(
        lambda s: tapped_hole_grid(
            s,
            pl["coldplate"],
            pitch=cp["grid_pitch"],
            fastener=cp["grid_fastener"],
            size=tuple(cp["grid_size"]),
            inset=0.0,
            depth=cp["grid_tap_depth"],
        ),
        "coldplate_grid",
    )
    MEASURED["coldplate_grid"] = (grid.count, grid.pitch, grid.pitch_v)

    b.hole(lambda s: s.cut(_drip_kerf(hood_plane, dh)), "drip_kerf")

    flange_pat = bolt_pattern(
        "perimeter",
        length=fl["length"],
        width=fl["width"],
        inset=fl["inset"],
        fastener=fl["screw"],
        target_pitch=fl["target_pitch"],
        plane=mate,
    )
    b.hole(
        lambda s: fastener_holes(
            s,
            flange_pat.points,
            plane=mate,
            fastener=fl["screw"],
            kind="tap",
            depth=fl["tap_depth"],
        ),
        "flange_screws",
    )
    MEASURED["flange_screw_count"] = flange_pat.count
    MEASURED["flange_screw_pitch_mm"] = (flange_pat.pitch, flange_pat.pitch_v)
    MEASURED["flange_screw_in_band"] = flange_pat.in_band

    # One identity mark on the whole part, centred on the outboard face.
    em = f["emblem"]
    b.hole(
        lambda s: emblem(
            s,
            pl["front"],
            motif=em["motif"],
            diameter=em["diameter"],
            relief=em["relief"],
            rings=em["rings"],
            line_width=em["line_width"],
            center=_front_uv(em["centre"]),
        ),
        "emblem",
    )

    return b


def create_part(params: dict | None = None) -> cq.Workplane:
    """The enclosure body. The lid, bracket and connectors are separate parts."""
    return _build(params).result


def build_stages(params: dict | None = None):
    """lib.debug_build's bisection protocol, straight off the Build pipeline."""
    yield from _build(params).stages()


def measurements(params: dict | None = None) -> dict:
    """Rebuild and return every number the builders measured (for DESIGN.md)."""
    _build(params)
    return dict(MEASURED)


if __name__ == "__main__":
    p = load_params()
    part = create_part(p)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = EXPORTS_DIR / f"{PART_DIR.name}_{p.get('version', 'v1')}.step"
    cq.exporters.export(part, str(out))
    shape = part.val()
    bb = shape.BoundingBox()
    print(f"  {p['part_name']} {p.get('version', 'v1')}")
    print(f"  bbox   {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
    print(f"  volume {shape.Volume():.0f} mm^3   mass {shape.Volume() * 2.70e-6:.2f} kg (6061)")
    print(f"  solids {len(shape.Solids())}   faces {len(shape.Faces())}")
    for k, v in MEASURED.items():
        print(f"  {k:28s} {v}")
    print(f"  wrote {out}")
