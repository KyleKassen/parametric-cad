"""P2 B210 mount analytical screening; standard-library Python, N/mm/MPa.

Run this file with --write to regenerate engineering_checks.md and
engineering_results.json beside the source. No P1 file is changed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# Named engineering inputs are assumptions or drawing acceptance limits, NOT
# measurements of the radio, a property certificate, or approved installation.
INPUTS = dict(
    g=9.81, device_mass_kg=1.0, package_mass_kg=2.2,
    cable_force_N=20.0, cable_arm_mm=50.0, incidental_inertia_g=3.0,
    frame_yield_MPa=240.0, frame_E_MPa=70000.0, frame_G_MPa=26300.0,
    yield_factor_target=3.0, proof_axis_force_N=150.0,
    handling_axis_force_N=110.0, proof_couple_Nmm=1500.0,
    handling_couple_Nmm=1000.0, cg_height_limit_mm=120.0,
    cg_offset_limit_mm=50.0, local_bar_total_N=150.0,
    foot_bolt_screen_N=400.0, web_bolt_local_screen_N=100.0,
    bar_min_t_mm=4.9, floor_min_t_mm=3.9, base_min_t_mm=7.9,
    channel_web_min_t_mm=5.9, channel_rib_min_t_mm=2.9,
    channel_return_min_depth_mm=7.9, channel_min_width_mm=35.8,
    channel_max_width_mm=36.2, max_hole_d_mm=5.6,
    hole_position_allowance_mm=0.15,
    root_stress_factor=1.5, web_hole_stress_factor=3.0,
    installed_film_bound_mm=0.2, fitted_gap_min_mm=0.2,
    fitted_gap_max_mm=0.3, retention_extra_tolerance_mm=0.2,
    device_end_extent_mm=80.0, bolt_proof_reference_MPa=970.0,
    M5_stress_area_mm2=14.2, full_thread_engagement_min_mm=7.5,
    retainer_external_prying_screen_N=400.0,
    spacer_OD_min_mm=9.87, spacer_ID_max_mm=5.43,
    spacer_length_max_mm=30.13, spacer_E_assumption_MPa=60000.0,
    candidate_preload_ceiling_N=500.0,
    foot_boss_total_t_min_mm=9.9,foot_boss_OD_mm=20.0,foot_boss_OD_min_mm=19.8,
    effective_head_bearing_width_min_mm=8.0,
    foot_top_washer_OD_accept_min_mm=14.9,
    standard_washer_OD_screen_min_mm=9.8,
)


def rectangle(b, t):
    return b*t, b*t*t/6, b*t**3/12


def composite(rects):
    """Exact centroid and second moment for signed non-overlapping rectangles.

    Each tuple is (width, thickness along bending coordinate, coordinate of
    centroid). A negative width removes a rectangular hole strip.
    """
    area = sum(b*t for b,t,c in rects)
    center = sum(b*t*c for b,t,c in rects)/area
    inertia = sum(b*t**3/12 + b*t*(c-center)**2 for b,t,c in rects)
    return dict(area_mm2=area, centroid_mm=center, I_mm4=inertia)


def bar_point_deflection(P, a, L, x, E, I):
    """Exact simply-supported Euler-Bernoulli point-load displacement."""
    b = L-a
    if x <= a:
        return P*b*x*(L*L-b*b-x*x)/(6*L*E*I)
    y = L-x
    return P*a*y*(L*L-a*a-y*y)/(6*L*E*I)


def calculate(p, a):
    q = INPUTS.copy()
    E, G, Sy = q['frame_E_MPa'], q['frame_G_MPa'], q['frame_yield_MPa']
    P, F, C = q['local_bar_total_N'], q['proof_axis_force_N'], q['proof_couple_Nmm']
    # Core final geometry is checked against the root CAD at report generation.
    span, contact_x = 136.3, 41.8  # adverse screw pitch and inward pad-edge allowance
    arm = span/2-contact_x
    bbar = 18.8  # 20 nominal, two .5 edge breaks, .2 width allowance
    _, Zbar, Ibar = rectangle(bbar,q['bar_min_t_mm'])
    bar_M = P*arm*(span-arm)/span
    bar_sigma = bar_M/Zbar
    # A nonnegative distribution anywhere on either contact patch is a convex
    # combination of point loads. The nearest-to-center inner edge is worst.
    bar_pad_delta = bar_point_deflection(P,arm,span,arm,E,Ibar)
    opposite_delta = bar_point_deflection(P,arm,span,span-arm,E,Ibar)
    x_max = span-math.sqrt((span*span-arm*arm)/3)
    bar_global_delta = bar_point_deflection(P,arm,span,x_max,E,Ibar)
    # Small edge-torque allowance: both end sections rotationally seated against
    # their hard posts. This assumption requires the qualified assembly process.
    tbar = q['bar_min_t_mm']
    Jbar = bbar*tbar**3/3*(1-.63*tbar/bbar+.052*(tbar/bbar)**5)
    torque_arm = 10.1
    T = P*torque_arm
    bar_edge_twist = T*arm*(span-arm)/(G*Jbar*span)*torque_arm
    T_internal = T*(span-arm)/span
    torsion_tau = T_internal/(.24*bbar*tbar*tbar)
    bar_vm = math.sqrt(bar_sigma**2+3*torsion_tau**2)
    # Floor contact inner edge includes .2 mm adverse datum/location allowance.
    floor_arm = 19.7
    _, Zfloor, Ifloor = rectangle(18.0,q['floor_min_t_mm'])
    floor_sigma = P*floor_arm/Zfloor
    floor_delta = P*floor_arm**3/(3*E*Ifloor)
    # Whole rail net section and enlarged hole pitch, no credit for intermediate
    # contact with the installation plate. Common base motion would cancel.
    rail_width, rail_span = 12.75, 140.3
    _, Zrail, Irail = rectangle(rail_width,q['base_min_t_mm'])
    rail_sigma = P*rail_span/4/Zrail
    rail_delta = P*rail_span**3/(48*E*Irail)
    # Both channel sections: a main web plus two narrow returns, same section
    # rotated 90 degrees. Signed rectangle removal represents maximum hole strip.
    bw, tw = q['channel_min_width_mm'],q['channel_web_min_t_mm']
    tr, dr = q['channel_rib_min_t_mm'],q['channel_return_min_depth_mm']
    web_rects = [(bw,tw,-tw/2),(tr,dr,-tw-dr/2),(tr,dr,-tw-dr/2)]
    foot_rects = [(bw,tw,tw/2),(tr,dr,tw+dr/2),(tr,dr,tw+dr/2)]
    web = composite(web_rects)
    foot = composite(foot_rects)
    web_net = composite(web_rects+[(-q['max_hole_d_mm'],tw,-tw/2)])
    foot_net = composite(foot_rects+[(-q['max_hole_d_mm'],tw,tw/2)])
    H, offset = q['cg_height_limit_mm'],q['cg_offset_limit_mm']
    Mroot = (F*H+F*offset+C)/2
    root_z, low_z, high_z = 12.1,25.85,166.15
    Mlow = Mroot-(F/2)*(low_z-root_z)
    foot_hole_M = (F*H+F*(offset-19.85)+C)/2
    web_cmax = max(abs(web['centroid_mm']),abs(-tw-dr-web['centroid_mm']))
    foot_cmax = max(foot['centroid_mm'],tw+dr-foot['centroid_mm'])
    root_sigma = q['root_stress_factor']*Mroot*web_cmax/web['I_mm4']
    root_vm = math.sqrt((root_sigma+F/2/web['area_mm2'])**2
                        +3*(F/2/web['area_mm2'])**2)
    foot_root_sigma = q['root_stress_factor']*Mroot*foot_cmax/foot['I_mm4']
    web_hole_fiber = max(abs(web_net['centroid_mm']),abs(-tw-web_net['centroid_mm']))
    foot_hole_fiber = max(abs(foot_net['centroid_mm']),abs(tw-foot_net['centroid_mm']))
    web_hole_sigma = (q['web_hole_stress_factor']*Mlow*web_hole_fiber/web_net['I_mm4']
                      +F/2/web_net['area_mm2'])
    foot_hole_sigma = q['web_hole_stress_factor']*foot_hole_M*foot_hole_fiber/foot_net['I_mm4']
    web_return_sigma = Mlow*max(abs(web_net['centroid_mm']),abs(-tw-dr-web_net['centroid_mm']))/web_net['I_mm4']
    foot_return_sigma = foot_hole_M*max(foot_net['centroid_mm'],tw+dr-foot_net['centroid_mm'])/foot_net['I_mm4']
    bolt_span_min=34.7
    foot_bolt_demand=(F*H+F*(offset-19.85)+C)/(2*bolt_span_min)
    web_bolt_demand=F/4+(F*offset+C)/(2*139.7)
    # Local transverse strip between returns. The full hole diameter is removed
    # from the entire strip width, and washer force is a central point load.
    # This overstates a distributed washer-ring load; no additional notch factor
    # is imposed on this already reduced-strip local bending screen.
    clear_span=q['channel_max_width_mm']-2*tr
    foot_local_width=q['effective_head_bearing_width_min_mm']-q['max_hole_d_mm']
    foot_local_t=q['foot_boss_total_t_min_mm']
    foot_local_sigma=q['foot_bolt_screen_N']*clear_span/4/rectangle(foot_local_width,foot_local_t)[1]
    # True circular-boss boundary across the entire8 mm longitudinal load strip.
    # Beyond it, discard remaining partial boss thickness and apply factor3.
    boss_full_width_y=math.sqrt((q['foot_boss_OD_min_mm']/2)**2
        -(q['effective_head_bearing_width_min_mm']/2)**2)
    transition_M=q['foot_bolt_screen_N']/2*(clear_span/2-boss_full_width_y)
    transition_sigma=3.0*transition_M/rectangle(q['effective_head_bearing_width_min_mm'],tw)[1]
    small_washer_width=q['standard_washer_OD_screen_min_mm']-q['max_hole_d_mm']
    rejected_small_washer_sigma=q['foot_bolt_screen_N']*clear_span/4/rectangle(small_washer_width,tw)[1]
    web_local_sigma=q['web_bolt_local_screen_N']*clear_span/4/rectangle(small_washer_width,tw)[1]
    # Virtual-work stepped beam: outer portions are plain foot; the entire
    # central full-width boss region uses NET width, even outside the actual hole.
    Lhalf=clear_span/2
    plain_length=Lhalf-boss_full_width_y
    Ifootlocal=rectangle(q['effective_head_bearing_width_min_mm'],tw)[2]
    Ibosslocal=rectangle(foot_local_width,foot_local_t)[2]
    local_foot_delta=q['foot_bolt_screen_N']/(2*E)*(plain_length**3/(3*Ifootlocal)
        +(Lhalf**3-plain_length**3)/(3*Ibosslocal))
    local_web_delta=q['web_bolt_local_screen_N']*clear_span**3/(48*E*rectangle(small_washer_width,tw)[2])
    # Channel web / foot bending and foot rotation, using whole-length net inertia.
    L, hlow=high_z-root_z,low_z-root_z
    xa, xs=20.15,35.0
    def deflection(Fh,Fv,couple):
        EIweb,EIf=E*web_net['I_mm4'],E*foot_net['I_mm4']
        def tipload(load,x): return load*x*x*(3*L-x)/(6*EIweb)
        M=(Fh*H+Fv*offset+couple)/2
        web_d=tipload(Fh/4,L)+tipload(Fh/4,hlow)
        eccentric_d=((Fv/2)*offset+couple/2)*L*L/(2*EIweb)
        theta=(M*(xa+xs/3)+(Fv/2)*(xa*xa/2+xa*xs/3))/EIf
        dz=(M*(xa*xa/2+xa*xs/3)+(Fv/2)*(xa**3/3+xa*xa*xs/3))/EIf
        # Additional local support compliance: opposing foot displacements create
        # support rotation; two web-hole movements are added as a simple bound.
        foot_demand=(Fh*H+Fv*(offset-19.85)+couple)/(2*34.7)
        web_demand=Fh/4+(Fv*offset+couple)/(2*139.7)
        foot_scale=min(1.0,foot_demand/q['foot_bolt_screen_N'])
        web_scale=min(1.0,web_demand/q['web_bolt_local_screen_N'])
        local_d=(local_foot_delta*(1+2*L/34.7)*foot_scale
                 +2*local_web_delta*web_scale)
        return web_d+eccentric_d+theta*L+dz+local_d
    severe_delta=deflection(F,F,C)
    handling_delta=deflection(110,110,1000)
    normal_delta=deflection(20,q['package_mass_kg']*q['g']+20,1000)
    # Positive-retention sweep input: a intentionally additive compliance budget.
    up=(q['fitted_gap_max_mm']+q['installed_film_bound_mm']+bar_pad_delta
        +bar_edge_twist+floor_delta+rail_delta)
    down=q['installed_film_bound_mm']
    support_pitch=76.0
    pitch_factor=(q['device_end_extent_mm']-support_pitch/2)/support_pitch
    end_rise=up+pitch_factor*(up+down)
    overlap=2.1
    side_rise=up+(61.5-50)/100*(up+down)
    # Screw proof capacity is sourced for property class 12.9. Spacer yield is not.
    At=q['M5_stress_area_mm2']
    screw_vm=math.sqrt((400/At)**2+3*(150/At)**2)
    strip_area=.25*math.pi*4*q['full_thread_engagement_min_mm']
    strip_allowed=strip_area*Sy/(math.sqrt(3)*3)
    spacer_area=math.pi/4*(q['spacer_OD_min_mm']**2-q['spacer_ID_max_mm']**2)
    spacer_I=math.pi/64*(q['spacer_OD_min_mm']**4-q['spacer_ID_max_mm']**4)
    spacer_euler=math.pi**2*q['spacer_E_assumption_MPa']*spacer_I/q['spacer_length_max_mm']**2
    spacer_total=q['retainer_external_prying_screen_N']+q['candidate_preload_ceiling_N']
    stresses=dict(bar_bending_and_torsion=bar_vm,local_floor_strip=floor_sigma,
        base_rail_flexure=rail_sigma,channel_web_root=root_vm,
        channel_foot_root=foot_root_sigma,channel_web_hole_local=web_hole_sigma,
        channel_foot_hole_local=foot_hole_sigma,web_return_at_hole=web_return_sigma,
        foot_return_at_hole=foot_return_sigma,foot_local_transverse_strip=foot_local_sigma,
        foot_boss_transition=transition_sigma,
        web_local_transverse_strip=web_local_sigma)
    factors={k:Sy/v for k,v in stresses.items()}
    return dict(status='P2 PRELIMINARY ANALYTICAL SCREENING; not physically validated',
        inputs=q,section_properties=dict(web=web,foot=foot,web_net=web_net,foot_net=foot_net),
        loads=dict(device_4g_plus_cable_N=4*q['device_mass_kg']*q['g']+20,
            package_4g_plus_cable_N=4*q['package_mass_kg']*q['g']+20,
            root_moment_per_support_Nmm=Mroot,foot_bolt_axial_demand_N=foot_bolt_demand,
            web_bolt_normal_demand_N=web_bolt_demand),
        bar=dict(support_span_mm=span,load_inner_edge_x_mm=contact_x,
            load_distance_from_support_mm=arm,stress_bending_MPa=bar_sigma,
            pad_deflection_mm=bar_pad_delta,opposite_pad_deflection_mm=opposite_delta,
            maximum_span_deflection_mm=bar_global_delta,bar_torsion_edge_movement_mm=bar_edge_twist,
            torsional_shear_screen_MPa=torsion_tau),
        stresses_MPa=stresses,yield_safety_factors=factors,
        minimum_yield_SF=min(factors.values()),
        machined_frame_strength_screen_pass=min(factors.values())>=3,
        deflections_mm=dict(floor=floor_delta,base_rail=rail_delta,
            local_foot_at_400N=local_foot_delta,local_web_at_100N=local_web_delta,
            upright_normal=normal_delta,upright_handling=handling_delta,upright_proof=severe_delta),
        capture=dict(upper_motion_bound_mm=up,lower_motion_bound_mm=-down,
            support_station_pitch_mm=support_pitch,
            pitch_angle_deg=math.degrees(math.atan((up+down)/support_pitch)),
            end_tip_rise_mm=end_rise,end_overlap_nominal_mm=overlap,
            end_residual_before_tolerance_mm=overlap-end_rise,
            end_residual_after_0p2mm_reserve_mm=overlap-end_rise-.2,
            side_residual_before_tolerance_mm=2.3-side_rise),
        hardware=dict(screw_external_equivalent_MPa=screw_vm,
            screw_external_proof_SF=q['bolt_proof_reference_MPa']/screw_vm,
            thread_strip_surrogate_area_mm2=strip_area,
            thread_allowed_N_at_SF3=strip_allowed,
            preload_budget_after_400N_external_N=strip_allowed-400,
            spacer_min_annulus_mm2=spacer_area,
            spacer_external_400N_pressure_MPa=400/spacer_area,
            spacer_900N_pressure_MPa=spacer_total/spacer_area,
            spacer_yield_strength_required_for_900N_SF3_MPa=3*spacer_total/spacer_area,
            spacer_yield_status='NOT VERIFIED; no spacer material yield SF assigned',
            spacer_Euler_N_assuming_E60GPa=spacer_euler,
            foot_local_with_rejected_OD9p8_washer_MPa=rejected_small_washer_sigma,
            boss_full_8mm_strip_halfwidth_y_mm=boss_full_width_y,
            minimum_thread_engagement_mm=7.5,minimum_screw_tip_recess_mm=.5,
            nominal_gap_with_0p6508_shims_and_0p2_films_mm=.2508,
            nominal_gross_thread_entry_mm=45-(5+1+30+.6508),
            nominal_screw_tip_recess_mm=9.2-(45-(5+1+30+.6508)),
            maximum_unshimmed_gap_assumed_tolerances_mm=(9.25+30.13-.1143-(5.45+.1143+33.5)),
            minimum_unshimmed_gap_assumed_tolerances_mm=(9.15+29.87-.2-(5.55+.2+33.9)),
            label_stop_gap_with_min_catalog_film_and_shop_tolerances_mm=(5.45+.1143+2.531-7.85)))


def render(r, audit):
    q=r['inputs']; bar=r['bar']; d=r['deflections_mm']; c=r['capture']; h=r['hardware']
    rows='\n'.join(f"| {k.replace('_',' ')} | {v:.2f} | {r['yield_safety_factors'][k]:.2f} |" for k,v in r['stresses_MPa'].items())
    return f'''# P2 engineering checks — thinner sections with positive retention

P2 uses an 8 mm base with a 4 mm floor, 5 mm top bars, and upright supports with 6 mm main webs/feet and 3 mm returns. It preserves P1 as a separate revision. This note is a reproducible analytical screen, not FEA, certification, physical testing, or installation approval. **Only the certified machined 6061 frame has a calculated yield safety factor.** The purchased spacer alloy/yield strength is unverified, and the actual enclosure and supporting installation remain unqualified.

Run `python references/engineering/engineering_calculations.py --write` from P2 to regenerate this note and `engineering_results.json`. CAD parameter comparison at generation: **{audit['status']}**. The numerical source has named engineering inputs and checks the core CAD dimensions; revise/review both when changing the design. Source hashes are recorded in the JSON. P1 remains unchanged.

## Load basis and material

The device mass allowance is 1.0 kg and complete upright package allowance remains 2.2 kg. These are assumptions requiring actual weighing, not STEP-derived masses. Gravity is 9.81 m/s². The device envelope is `(3+1)mg+20={r['loads']['device_4g_plus_cable_N']:.2f} N`; the package envelope is `{r['loads']['package_4g_plus_cable_N']:.2f} N`. The 3g term is assumed incidental inertia and the 1g term adds gravity conservatively. It is not a shock spectrum. Cable force is 20 N at 50 mm; route a separate strain relief so connectors do not form the mount load path.

The handling screen is 110 N on each of two axes simultaneously plus 1 N m. The mount-only proof sizing screen is 150 N on each axis simultaneously plus 1.5 N m. These combinations exceed a single acceleration vector. Upright CG bounds are z≤120 mm and x≤50 mm from the support datum; verify balance. Root moment per support is `(150×120+150×50+1500)/2=13,500 N mm`. A separate 150 N total contact load sizes one retainer bar and one local floor land. No real-device proof load at 150 N is authorized through an unverified shell.

Certified unwelded 6061-T6/T651 stock uses minimum yield 240 MPa, E=70,000 MPa and G=26,300 MPa from the [thyssenkrupp supplier data](https://d2zo35mdb530wx.cloudfront.net/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf). Yield SF target is 3 for the declared equivalent static loads and preliminary production. Local stress factors are selected screening assumptions, not measured/calibrated notch solutions. This does not establish fatigue or enclosure capacity.

## Changes from P1

| Feature | P1 | P2 |
|---|---:|---:|
| Main base thickness |12 mm|8 mm|
| Pocket floor |6 mm|4 mm|
| Retainer bar |8 mm|5 mm|
| Main upright web/foot |8 mm|6 mm|
| Upright section stiffening |Plain L|3 mm returns and continuous foot ribs|
| Foot bolt support |Uniform8 mm|Local10 mm integral bosses|
| Retainer screw pitch X |140 mm|136 mm|
| Contact/bar station pitch Y |70 mm|76 mm|
| Final fitted device gap |0.20–0.40 mm|0.20–0.30 mm|

The thinner visible plates require more machining features and selective fit shims. P1's plain nominal36×8 mm section has I=1536 mm⁴; the nominal P2 channel has I≈2828 mm⁴ with a6 mm main wall. The channel places material farther from its centroid. Both versions preserve the device and use removable retainers. P1's top-bar calculation used a central point load; P2 uses actual pad-edge loads, so those bar deflection values reflect geometry and a refined load model. Full mass/envelope comparisons come from the separate CAD report.

## Top bars and floor: why the thinner sections work

Both top contact regions are supported by aluminum lands at x±50 mm. Each is16 mm wide. The beam load may concentrate at the **inner edge x±42**, not just its center. Nominal screw locations are x±68, giving L=136 mm and a=26 mm. Adverse drawing allowances enlarge the screw pitch to136.3 mm and move the loaded inner edge to x=41.8 mm. The bar uses **4.9 mm minimum thickness** and18.8 mm effective width after edge/width allowances. Contacts are unilateral; any nonnegative150 N total distribution over those pads is a convex combination of point loads. Putting all150 N at one inner edge bounds stress and that contact's displacement.

`Mmax=Pab/L`; `I=bt³/12`; at the load, `δ=P a² b²/(3 E I L)`. For other points the source evaluates the exact simply supported point-load equation. Calculated bending stress is {bar['stress_bending_MPa']:.2f} MPa; loaded-pad displacement is **{bar['pad_deflection_mm']:.3f} mm**. The maximum span displacement is {bar['maximum_span_deflection_mm']:.3f} mm at an unloaded position, not the contact constraint. The bar center must remain clear of the enclosure.

An additional **{bar['bar_torsion_edge_movement_mm']:.3f} mm** allows a150 N load at a pad edge10.1 mm from the screw line, including width allowance, to twist the bar. The rectangular torsion constant uses `J≈bt³/3[1−0.63(t/b)+0.052(t/b)^5]`; end rotation is restrained by qualified hard-post seating. The calculation uses `θ=T ab/(GJL)` and adds edge motion. The torsional shear screen uses a deliberately reduced rectangular coefficient0.24. Bar installation must seat on hard posts with locking and controlled preload; freely rocking or loose bar joints do not meet this boundary condition.

The floor calculation uses a 19.7 mm adverse cantilever arm from the outer-rail support to the inner land edge, 18 mm effective contact width and **3.9 mm minimum floor**: `σ=Pa/Z`, `δ=Pa³/(3EI)`. Floor displacement is {d['floor']:.3f} mm. The outer base rail uses a 12.75 mm whole-length net width, 7.9 mm minimum thickness and 140.3 mm free span, with no intermediate plate-contact credit: displacement {d['base_rail']:.3f} mm. Reducing the window alone would not shorten the physical land-to-rail cantilever. Adding two center plate bolts would not benefit the two-support upright arrangement without another support.

Four-millimeter bars were rejected because their pad motion consumes too much end-capture clearance even though static strength can pass. Five millimeters with a fitted 0.20–0.30 mm gap provides the selected compromise. P1's central-point beam bound is intentionally replaced by this geometry-specific pad-edge load model; it is not valid for loads applied at an arbitrary bar center.

## Upright supports: returns carry bending

The main web is 6 mm thick. Two 3 mm wide returns project rearward 8 mm beyond it, outside the cradle. The 6 mm foot has two continuous 3 mm edge ribs rising 8 mm above it, from the rear heel through the root and both foot-bolt stations to the foot end. Nominal rib top is z=14 mm, below the cradle's z=16 mm lower edge. A bare 6 mm L support would be inadequate at this load basis; the returns are structural.

Each channel section is evaluated as three non-overlapping rectangles using `A=ΣA_i`, `c=ΣA_i c_i/A`, `I=Σ[I_i+A_i(c_i−c)²]`. Worst sections use web/foot **5.9 mm minimum**, ribs **2.9 mm minimum**, return projection **7.9 mm minimum**, width 35.8 mm, and maximum 5.6 mm holes. Root factor 1.5 applies to the most distant channel fiber. The hole strip is explicitly subtracted, and factor 3 applies at the **main-web fiber where the hole exists**. It does not multiply stress in the remote unperforated return. Return stress at the net section is checked separately.

Worst channel gross I is {r['section_properties']['web']['I_mm4']:.1f} mm⁴; centroid is {r['section_properties']['web']['centroid_mm']:.3f} mm behind the web face. The foot is the same section reflected/rotated. Whole-length net inertia conservatively screens stiffness. Returns must remain continuous through the root; ribs starting only at x=20 would leave an inadequate bare root. Blend junctions with the specified tool radii, preserve minimum wall sizes after finish, and verify tool access. This is a one-piece machined construction, with no welding or sheet-metal flat-pattern assumption.

| Member/local check | Stress (MPa) | Yield SF |
|---|---:|---:|
{rows}

Minimum machined-frame yield SF: **{r['minimum_yield_SF']:.2f}**. Screen **{'passes' if r['machined_frame_strength_screen_pass'] else 'does not pass'}** for these assumptions. These are selected beam and local-section checks; no fatigue, shock collision, detailed joint distortion, or support-plate global analysis is claimed.

## Local foot load and integral bosses

Calculated worst foot-bolt axial demand is {r['loads']['foot_bolt_axial_demand_N']:.1f} N; the local screen rounds it to400 N. An integralØ20 mm boss raises total foot thickness locally to10.0 mm, minimum9.9 mm. Model a simply supported transverse strip of clear span30.4 mm and **net width(8.0−5.6)=2.4 mm**, applying the full400 N as a central point load. This removes the hole diameter from the entire loaded strip and takes **no credit for the large washer spreading load**. Effective bearing width from screw head into the seated joint must be≥8.0 mm; verify it on received hardware. The thin washer receives no structural load-spreading or yield-strength credit.

The boss-center screen gives **{r['stresses_MPa']['foot_local_transverse_strip']:.2f} MPa / SF {r['yield_safety_factors']['foot_local_transverse_strip']:.2f}**. At the transition, minimum boss diameter19.8 mm gives the full8 mm longitudinal strip out to `|y|=sqrt(9.9²−4²)={h['boss_full_8mm_strip_halfwidth_y_mm']:.4f} mm`. Beyond that point, discard remaining partial boss material, use the full8 mm plain-foot strip with5.9 mm thickness, and apply factor3 to its remaining bending moment. Transition stress is {r['stresses_MPa']['foot_boss_transition']:.2f} MPa / SF {r['yield_safety_factors']['foot_boss_transition']:.2f}. The small R0.2–0.5 root blend adds material to the idealized boss and avoids a burr; no stiffness credit is taken for it. Factor3 is a selected screening assumption, not a calibrated notch solution.

Web-bolt normal demand is only {r['loads']['web_bolt_normal_demand_N']:.1f} N; a100 N local screen with a conservatively reduced standard-washer strip passes. The unbossed6 mm foot and soft large washer alone were not released as a verified load spreader. McMaster91100A140 is zinc steel, hardnessB56, thickness1.0–1.4 mm, with no published yield class or diameter tolerance in the inspected catalog. Its nominal15 mm diameter fits the boss and provides a seating/protection surface. Inspect OD≥14.9 mm as a drawing acceptance criterion, not a supplier guarantee; inspect for dishing and permanent set. The foot-bottom washer may remain standard on the assumed rigid metal supporting plate. Foot screws are M5×30; use actual washer/plate/nut dimensions to confirm complete locking engagement and nut-side clearance.

## Movement and positive capture

| Load/location | Movement bound |
|---|---:|
| Upright normal service: 1g +20 N, +1 N m | {d['upright_normal']:.3f} mm |
| Upright handling: 110 N each axis +1 N m | {d['upright_handling']:.3f} mm |
| Upright mount-only proof:150 N each axis +1.5 N m | {d['upright_proof']:.3f} mm |

Upright deflection includes web bending, eccentric moment, foot bending, foot rotation between its two bolts and foot vertical movement. It uses channel net inertia for the whole member. Additional local boss/foot flexure is calculated by virtual work for a stepped beam; outer plain-foot portions use5.9 mm thickness, and the entire central boss region conservatively uses2.4 mm net width. Local foot movement at400 N is {d['local_foot_at_400N']:.4f} mm and local web movement at100 N is {d['local_web_at_100N']:.4f} mm. Opposing local movements are converted into support rotation and added to the global bound. Bolt stretch and installation-plate translation remain outside the model. Retain P1 prototype criteria: ≤0.75 mm normal, ≤1.5 mm handling, ≤2.0 mm proof and ≤0.10 mm residual. These are selected functional limits, not manufacturer limits. Preserve at least2 mm extra moving-envelope clearance pending physical results.

The retention audit must use **upper travel {c['upper_motion_bound_mm']:.4f} mm and lower travel {c['lower_motion_bound_mm']:.4f} mm** at opposite support stations. Upper travel adds the0.30 mm gap, total0.20 mm upper-film loss, bar pad bending, bar edge twist, floor flexure and rail flexure. Lower travel allows complete bottom-film loss onto hard lands. The corresponding pitch bound is {c['pitch_angle_deg']:.4f}°. P2 stations are y=C±38, giving76 mm separation: `u_end=u_up+(80−38)/76×(u_up+0.2)={c['end_tip_rise_mm']:.3f} mm`. The outer-rail screen retains the older central-point load bound and takes no stiffness credit from moving a contact closer to an installation bolt.

Nominal end overlap remains2.1 mm, leaving **{c['end_residual_before_tolerance_mm']:.3f} mm** before dimensional variation and **{c['end_residual_after_0p2mm_reserve_mm']:.3f} mm** after a further0.20 mm reserve. Side overlap starts at2.3 mm; analogous roll retains {c['side_residual_before_tolerance_mm']:.3f} mm before reserve. This small end margin requires the exact pan-only pose/escape witness and physical testing. It is not a continuous configuration-space search or dynamic impact calculation. Do not chamfer the retaining edge by the general0.5 mm amount; preserve its critical height and ≤0.10 mm burr break. The source STEP enclosure's local crushing/denting capacity is unknown.

## Purchased hardware, fitted stack and unresolved spacer properties

McMaster class12.9 ISO4762 screws use a **970 MPa proof reference** and M5 stress area14.2 mm² from the [NBK fastener-property table](https://static.nbk1560.com/en-US/resources/other/article/technical-29-mechanical-properties-of-fasteners-made-of-carbon-steel-and-alloy-steel/). Require delivered property-class conformity. The400 N axial/150 N shear external screen gives {h['screw_external_equivalent_MPa']:.2f} MPa equivalent stress and proof SF {h['screw_external_proof_SF']:.1f}. Do not use a generic class12.9 tightening torque in the aluminum threads. Nut class10 and complete locking-element engagement must match the BOM; this is not a full nut proof qualification.

The retainer uses an M5×45 screw,5 mm bar,1 mm washer,30 mm purchased spacer and nominal0.6508 mm shim stack over the9.20 mm boss. Nominal gross entry is {h['nominal_gross_thread_entry_mm']:.4f} mm; tip recess {h['nominal_screw_tip_recess_mm']:.4f} mm. Purchased tolerances, bolt runout and actual selected shims govern. Inspect **≥7.5 mm complete female/male thread engagement** and **≥0.5 mm screw-tip recess** above the base underside. Through taps do not provide blind-hole bottoming protection if a screw protrudes into the mounting plate.

Conservative aluminum-thread surrogate `A_s=0.25π×4×7.5` gives {h['thread_allowed_N_at_SF3']:.0f} N allowable at SF3. A400 N external/prying reserve leaves **{h['preload_budget_after_400N_external_N']:.0f} N** for preload within this surrogate. A500 N candidate maximum seating preload is therefore only an engineering limit for qualification, not an approved torque or a proven assembly procedure. The shop must establish repeatable seating/locking against actual finish, thread friction, inserts if used, and spacer behavior. The device itself receives no intentional clamp preload.

Purchased [McMaster94669A146](https://www.mcmaster.com/94669A146/) is cataloged aluminum with30±0.13 mm length,10±0.13 mm OD and5.3±0.13 mm ID. **Its alloy/temper/yield strength is not specified by the inspected catalog evidence; do not call it6061.** Minimum annulus is {h['spacer_min_annulus_mm2']:.2f} mm². External400 N gives {h['spacer_external_400N_pressure_MPa']:.2f} MPa average compression;900 N including the candidate500 N preload gives {h['spacer_900N_pressure_MPa']:.2f} MPa. To support SF3 at900 N would require compressive yield≥{h['spacer_yield_strength_required_for_900N_SF3_MPa']:.1f} MPa, which remains unverified. The Euler screen is {h['spacer_Euler_N_assuming_E60GPa']:.0f} N using an explicitly assumed E60 GPa and pin-ended30.13 mm column; its very high result merely shows slender-column buckling is unlikely to govern the assumed metal. It does not prove crushing capacity. Obtain material confirmation or qualify spacer compression/permanent set and joint seating before release.

The thin shim's maximum ID6.6294 mm and minimum OD9.4742 mm can govern bearing contact area; verify concentric, flat seating, retention of the thin shim and no edge overhang. Final BOM shim dimensions and hardness/material data take precedence over nominal CAD rings. Check permanent set during joint qualification. Shims belong under hard spacers, not between a loaded bar and the radio.

The [PET film8689K65](https://www.mcmaster.com/8689K65/) catalog nominal is0.127±0.0127 mm, with acrylic adhesive; whether the displayed thickness includes adhesive is unresolved. Measure installed total thickness and keep it≤0.20 mm per contact. The CAD uses that upper bound, not a claim that the product is exactly0.20 mm. The stock shim stack is only a nominal assembly example. With actual thinner films the gap increases: select shims by measured cold/warm gap at every contact, keeping **0.20–0.30 mm** and maintaining screw engagement/recess. No pad/friction/adhesive retention credit is taken.

For stack screening only, assume enclosure height33.7±0.2 mm, boss9.20±0.05, hard-land top5.50±0.05, spacer30±0.13 and installed film0.1143–0.20 mm. These give an unshimmed gap from **{h['minimum_unshimmed_gap_assumed_tolerances_mm']:.3f} to {h['maximum_unshimmed_gap_assumed_tolerances_mm']:.3f} mm**, before bar flatness and unverified enclosure variation. Stock shims up to about1.1 mm may be required; the example0.6508 mm stack is not a universal setting. Recheck thread entry and tip recess independently for the selected stack. Reject/select/rework any combination that cannot satisfy all criteria; never tighten the gap away by clamping the enclosure.

With catalog-minimum film0.1143 mm, land-top minimum5.45, measured STEP lower-label datum2.531 above the pan, and stop maximum7.85, the calculated label-to-stop gap is **{h['label_stop_gap_with_min_catalog_film_and_shop_tolerances_mm']:.4f} mm**. Actual label placement and enclosure variation are unverified. Inspect **≥0.20 mm actual label clearance** at both ends with the fitted device, including warm operation; the numeric stack does not replace that check.

## Remaining release work

Physical fit, device mass/CG, actual supporting plate and nut-side tool access, spacer compression, shim seating, controlled preload, local enclosure pressure, powered thermal performance in the real box, and repeated removal remain open. The original feet, labels, connectors and original fasteners must remain untouched. No improvement in heat rejection, grounding, vibration life or shock rating is claimed. Use the geometry audit for actual exported-solid validity, interference, connector envelopes and pan contact witnesses. Prototype proof uses a representative rigid dummy; real-device checks use limited forces and then powered thermal/service tests. Inspect for loosening, thread damage, permanent distortion, film wear and enclosure marking before releasing beyond preliminary stationary indoor use.
'''


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--write',action='store_true')
    args=ap.parse_args()
    pfile,afile=PROJECT/'params.json',PROJECT/'adapter_params.json'
    p,a=json.loads(pfile.read_text()),json.loads(afile.read_text())
    expected_p=dict(base_thickness=8.0,pocket_floor_z=4.0,bar_thickness=5.0,
        base_width=160.0,base_length=180.0,pocket_width=123.0,
        support_x=50.0,support_land_width=16.0,support_land_length=20.0,
        panel_bolt_x=70.0,panel_bolt_y_pitch=140.0,bar_width_y=20.0,
        device_height=33.7,film_thickness=.2,edge_break=.5,
        support_y_pitch=76.0,thread_boss_top=9.2,thread_boss_od=12.0,
        retainer_bolt_x=68.0,end_stop_top=7.8,device_pan_z=5.7,
        top_gap_target=[.2,.3],spacer_od=10.0,spacer_id=5.3,retainer_bolt_length=45.0)
    expected_a=dict(web_t=6.0,foot_t=6.0,strip_width=36.0,inside_radius=6.0,
        foot_bolt_boss_od=20.0,foot_bolt_boss_top=10.0,
        rib_width=3.0,rear_return_depth=8.0,foot_rib_height=8.0,pocket_corner_radius=3.0,
        web_hole_z=[26.0,166.0],foot_hole_x=[20.0,55.0])
    mismatches=[]
    for label,actual,expected in [('cradle',p,expected_p),('support',a,expected_a)]:
        for key,value in expected.items():
            if actual.get(key)!=value: mismatches.append(f'{label}.{key}: CAD={actual.get(key)!r}; screened={value!r}')
    audit=dict(status='MATCHED core parameters' if not mismatches else 'PENDING / MISMATCH',
        mismatches=mismatches,
        params_sha256=hashlib.sha256(pfile.read_bytes()).hexdigest(),
        adapter_params_sha256=hashlib.sha256(afile.read_bytes()).hexdigest())
    r=calculate(p,a)
    if p.get('retention_up_screen',0)<r['capture']['upper_motion_bound_mm']:
        audit['mismatches'].append('CAD retention motion is smaller than analytical upper bound')
        audit['status']='PENDING / MISMATCH'
    r['cad_parameter_crosscheck']=audit
    if args.write:
        (HERE/'engineering_results.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
        (HERE/'engineering_checks.md').write_text(render(r,audit),encoding='utf-8')
    print(json.dumps(r,indent=2))
    if not r['machined_frame_strength_screen_pass']: raise SystemExit(1)
    if audit['mismatches']: raise SystemExit(2)


if __name__=='__main__': main()
