"""B210 mount P1 analytical screening, N/mm/MPa, Python standard library only.

Run: python references/engineering/engineering_calculations.py --write-note
The source reads the delivered CAD parameter files. It does not import CadQuery,
change CAD, infer device mass, or perform finite element analysis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


def section(b: float, t: float) -> tuple[float, float, float]:
    return b * t, b * t**2 / 6.0, b * t**3 / 12.0


def calculate(p: dict, a: dict) -> dict:
    if p.get('units') != 'mm' or a.get('units') != 'mm':
        raise ValueError('This calculation source accepts millimetres only.')
    if '6061' not in p.get('material', '') or '6061' not in a.get('material', ''):
        raise ValueError('Revise and substantiate material properties before changing from 6061.')
    # These are design allowances, not measured device or installation properties.
    E, Sy, proof, sf, g = 70000.0, 240.0, 450.0, 3.0, 9.81
    mass_device, mass_package = 1.0, 2.2
    cable, lever, F, P, bolt_N = 20.0, 50.0, 150.0, 150.0, 400.0
    force_device = 4 * g * mass_device + cable
    force_package = 4 * g * mass_package + cable
    # One normal reaction plus the complete moment divided by the smaller support
    # separation bounds the local retainer reaction; apply to ONE member/fastener.
    device_moment = 4 * g * mass_device * 50 + cable * lever
    reaction = force_device + device_moment / p['support_y_pitch']
    bbar = p['bar_width_y'] - 2 * p['edge_break']
    _, Zbar, Ibar = section(bbar, p['bar_thickness'])
    Lbar = 2 * p['retainer_bolt_x']
    bar_stress = P * Lbar / 4 / Zbar
    bar_deflection = P * Lbar**3 / (48 * E * Ibar)
    floor_arm = (p['pocket_width'] - p['window_width']) / 2
    floor_width = p['support_land_length'] - 2.0  # exclude rounded pad corners
    _, Zfloor, Ifloor = section(floor_width, p['pocket_floor_z'])
    floor_stress = P * floor_arm / Zfloor
    floor_deflection = P * floor_arm**3 / (3 * E * Ifloor)
    rail_width = (p['base_width'] - p['pocket_width']) / 2 - p['clearance_hole']
    _, Zrail, Irail = section(rail_width, p['base_thickness'])
    Lrail = p['panel_bolt_y_pitch']
    rail_stress = P * Lrail / 4 / Zrail
    rail_deflection = P * Lrail**3 / (48 * E * Irail)
    # End lip: deliberately small contact patch, and remove 1 mm from nominal
    # minimum thickness to screen local relief/finish; CAD must confirm that land.
    endlip_t = min(p['pocket_ymin'] - (p['center_y']-p['base_length']/2),
                   p['center_y']+p['base_length']/2-p['pocket_ymax']) - 1
    lip_h = p['end_stop_top'] - p['pocket_floor_z']
    lip_stress = P * lip_h / section(4, endlip_t)[1]
    lip_shear = P / (4 * endlip_t)
    lip_vm = math.sqrt(lip_stress**2 + 3 * lip_shear**2)
    # Threads: two deliberately conservative reductions (thread tooth area and
    # nonuniform first-thread loading). This is a screening surrogate, not ISO
    # thread-stripping analysis or a fastener supplier's installation rating.
    Le, dcore = 8.0, 4.0
    Astrip = 0.25 * math.pi * dcore * Le
    strip_allowed = Astrip * Sy / (math.sqrt(3) * sf)
    At, nominal_d, edge = 14.2, 5.0, 7.0
    fastener_vm = math.sqrt((bolt_N / At)**2 + 3*(P / At)**2)
    shear_allow = Sy / math.sqrt(3) / sf
    tear_allowed = 2 * edge * 6.0 * shear_allow
    bearing_panel = bolt_N / (nominal_d * 6.0)
    washer_area = math.pi / 4 * (10.0**2 - 5.3**2)
    washer_pressure = bolt_N / washer_area
    spacer_area = math.pi/4*(p['spacer_od']**2-p['spacer_id']**2)
    spacer_pressure = P / spacer_area
    support_area = p['support_land_width']*p['support_land_length']
    # Clearances are screened with rigid enclosure plus simple member flexure.
    # They are NOT a contact mechanics or transient impact solution.
    gap = max(p['top_gap_target'])
    top_travel = (gap + p['film_thickness'] + bar_deflection
                  + floor_deflection + rail_deflection)
    bottom_loss = p['film_thickness']
    end_extent = 80.0  # bounding half extent about center_y, not measured COM
    pitch_factor = (end_extent-p['support_y_pitch']/2)/p['support_y_pitch']
    end_rise = top_travel + pitch_factor*(top_travel+bottom_loss)
    end_overlap = p['end_stop_top']-p['device_pan_z']
    side_factor = (p['pocket_width']/2-p['support_x'])/(2*p['support_x'])
    side_rise = top_travel+side_factor*(top_travel+bottom_loss)
    # Machined upright adapter, two identical members. The moment components are
    # deliberately simultaneous, so this exceeds a single acceleration vector.
    t_nom = a.get('web_thickness', a.get('web_t', a.get('sheet_t', 8.0)))
    t_nom = a.get('thickness', t_nom)
    t = t_nom - 0.05  # critical drawing requirement: finished thickness +/-0.05
    b = a['strip_width'] - a.get('machined_general_tolerance', 0.2)
    hole_d_max = a['clearance_hole_d'] + a.get('hole_diameter_tolerance', 0.1)
    hole_position = a.get('hole_position_tolerance', 0.15)
    radius = a['inside_radius']
    root_z = t_nom + 0.05 + radius
    zlow, zhigh = a['web_hole_z']
    zlow -= hole_position
    zhigh += hole_position
    xnear, xfar = a['foot_hole_x']
    xnear -= hole_position
    xfar += hole_position
    H, offset, M_cable = 120.0, 50.0, 1500.0
    Mroot = (F*H+F*offset+M_cable)/2
    A, Z, I = section(b,t)
    netA, netZ, netI = section(b-hole_d_max,t)
    root_bending = 1.5*Mroot/Z
    root_vm = math.sqrt((root_bending+(F/2)/A)**2+3*((F/2)/A)**2)
    Mlow = Mroot-(F/2)*(zlow-root_z)
    hole_stress = 2*Mlow/netZ+(F/2)/netA
    Mfoot = (F*H+F*abs(offset-xnear)+M_cable)/2
    foot_hole_stress = 2*Mfoot/netZ
    # Hole stress factors are selected screening assumptions; neither notch
    # factors nor the fillet factor are calibrated to mesh/contact or fatigue.
    foot_span = xfar-xnear
    min_bolt_span = a['foot_hole_x'][1]-a['foot_hole_x'][0]-2*hole_position
    bolt_required = max(
        abs((sx*F*H+sz*F*(offset-xnear)+sc*M_cable)/(2*min_bolt_span))
        for sx in (-1,1) for sz in (-1,1) for sc in (-1,1))
    # Beam deflection includes upright web and foot rotation. Net section used
    # along the whole beam is conservative for isolated clearance holes.
    L = zhigh-root_z
    hlow = zlow-root_z
    def tip_point(q, x):
        return q*x*x*(3*L-x)/(6*E*netI)
    web_delta = tip_point(F/4,L)+tip_point(F/4,hlow)
    eccentric_delta = ((F/2)*offset+M_cable/2)*L**2/(2*E*netI)
    # Two point supports for foot. Absolute-value envelope overstates some
    # simultaneously compatible load directions and includes foot translation.
    foot_arm = a['foot_hole_x'][0] + hole_position
    foot_span_deflection = a['foot_hole_x'][1]-a['foot_hole_x'][0]
    root_slope = (Mroot*(foot_arm+foot_span_deflection/3)
                  +(F/2)*(foot_arm**2/2+foot_arm*foot_span_deflection/3))/(E*netI)
    foot_delta = (Mroot*(foot_arm**2/2+foot_arm*foot_span_deflection/3)
                  +(F/2)*(foot_arm**3/3+foot_arm**2*foot_span_deflection/3))/(E*netI)
    adapter_deflection = web_delta+eccentric_delta+root_slope*L+foot_delta
    # Exact same linear beam bound at normal loads. Counting cable force in both
    # horizontal and vertical components simultaneously is conservative.
    normal_H, normal_V, normal_couple = cable, mass_package*g+cable, 1000.0
    normal_M = (normal_H*H+normal_V*offset+normal_couple)/2
    normal_web = tip_point(normal_H/4,L)+tip_point(normal_H/4,hlow)
    normal_eccentric = ((normal_V/2)*offset+normal_couple/2)*L**2/(2*E*netI)
    normal_slope = (normal_M*(foot_arm+foot_span_deflection/3)
                   +(normal_V/2)*(foot_arm**2/2+foot_arm*foot_span_deflection/3))/(E*netI)
    normal_foot = (normal_M*(foot_arm**2/2+foot_arm*foot_span_deflection/3)
                  +(normal_V/2)*(foot_arm**3/3+foot_arm**2*foot_span_deflection/3))/(E*netI)
    normal_delta = normal_web+normal_eccentric+normal_slope*L+normal_foot
    stresses = {
        'bar_bending_MPa': bar_stress,
        'floor_local_bending_MPa': floor_stress,
        'base_rail_bending_MPa': rail_stress,
        'end_lip_von_mises_MPa': lip_vm,
        'adapter_root_von_mises_MPa': root_vm,
        'adapter_lower_web_hole_local_MPa': hole_stress,
        'adapter_near_foot_hole_local_MPa': foot_hole_stress,
    }
    return {
        'status': 'PRELIMINARY ANALYTICAL SCREENING; physical validation outstanding',
        'units': {'length':'mm','force':'N','moment':'N mm','stress':'MPa'},
        'inputs': {'E_MPa':E,'yield_MPa':Sy,'fastener_proof_MPa':proof,'target_yield_SF':sf,
            'device_mass_allowance_kg':mass_device,'complete_package_mass_allowance_kg':mass_package,
            'gravity_m_s2':g,'handling_inertia_g':3,'gravity_added_g':1,
            'cable_force_N':cable,'cable_lever_mm':lever,
            'component_screen_load_N':P,'upright_each_axis_screen_N':F,
            'upright_CG_height_limit_mm':H,'upright_CG_offset_limit_mm':offset,
            'upright_added_cable_couple_Nmm':M_cable,'adapter_nominal_thickness_mm':t_nom,
            'adapter_thickness_screen_min_mm':t,'adapter_width_screen_min_mm':b,
            'adapter_hole_screen_max_mm':hole_d_max,
            'thread_completed_engagement_min_mm':Le},
        'derived_loads': {'device_resultant_envelope_N':force_device,
            'complete_package_component_envelope_N':force_package,
            'device_overturning_moment_Nmm':device_moment,
            'local_reaction_upper_bound_N':reaction,
            'upright_root_moment_per_support_Nmm':Mroot,
            'upright_foot_bolt_axial_bound_N':bolt_required,
            'foot_bolt_screen_axial_N':bolt_N},
        'stresses':stresses,
        'yield_safety_factors':{name.removesuffix('_MPa'):Sy/value for name,value in stresses.items()},
        'deflections_mm':{'bar':bar_deflection,'local_floor':floor_deflection,
            'base_rail_flexure':rail_deflection,'upright_severe_envelope':adapter_deflection,
            'upright_handling_envelope':adapter_deflection*110/150,
            'upright_normal_service_bound':normal_delta},
        'fasteners':{'M5_stress_area_mm2':At,'combined_external_stress_MPa':fastener_vm,
            'external_proof_SF':proof/fastener_vm,'thread_surrogate_area_mm2':Astrip,
            'thread_external_allowed_at_SF3_N':strip_allowed,
            'remaining_preload_budget_after_150N_N':strip_allowed-P,
            'assumed_6mm_support_bearing_MPa':bearing_panel,
            'conservative_two_plane_edge_tearout_allowed_N':tear_allowed,
            'washer_average_pressure_MPa':washer_pressure,
            'spacer_external_pressure_MPa':spacer_pressure},
        'contact_and_retention':{'one_pad_average_at_150N_MPa':P/support_area,
            'four_pad_gravity_average_MPa':mass_device*g/(4*support_area),
            'top_travel_including_film_loss_and_member_flex_mm':top_travel,
            'opposed_bottom_film_loss_mm':bottom_loss,'end_pitch_factor':pitch_factor,
            'end_tip_rise_mm':end_rise,'nominal_end_overlap_mm':end_overlap,
            'residual_end_overlap_before_tolerance_mm':end_overlap-end_rise,
            'after_additional_0p2mm_tolerance_reserve_mm':end_overlap-end_rise-0.2,
            'residual_side_overlap_before_tolerance_mm':p['base_thickness']-p['device_pan_z']-side_rise},
        'strength_screen_pass': all(Sy/v >= sf for v in stresses.values()) and bolt_required<=bolt_N,
    }


def report(r: dict, hashes: dict) -> str:
    i,d,s,df,f,c = (r[k] for k in ('inputs','derived_loads','stresses','deflections_mm','fasteners','contact_and_retention'))
    rows = '\n'.join(f"| {name.replace('_',' ').removesuffix(' MPa')} | {value:.2f} | {240/value:.2f} |" for name,value in s.items())
    return f'''# B210 P1 engineering checks — preliminary

This is an analytical screening of the delivered machined 6061 mount and upright supports. It is not FEA, a certification, an installation approval, or evidence of a physical test. The device mass, center of mass, shell capacity, cable selection, supporting plate, and actual shop process remain unverified. Positive enclosure capture has a small end-stop margin and requires the specific fit and retention tests in the prototype plan. Both flat and upright stationary indoor configurations are provisional; no vehicle, airborne, outdoor, overhead, shock-spectrum, or vibration qualification is established.

Reproduce with `python references/engineering/engineering_calculations.py --write-note` from the design folder. Standard-library Python 3.10+ suffices. The script reads `params.json` and `adapter_params.json`; changing those files changes these calculations. SHA-256 used: cradle `{hashes['params']}`, adapter `{hashes['adapter']}`. Source CAD hashes and the original STEP are handled by the separate geometry audit.

## Inputs and their status

| Input | Value | Basis |
|---|---:|---|
| Device mass allowance | 1.00 kg | Design assumption; weigh actual configured radio |
| Complete upright package allowance | 2.20 kg | Includes radio, cradle, supports, and hardware; weigh complete assembly |
| Gravity | 9.81 m/s² | Calculation convention |
| Incidental handling | 3g inertia, plus 1g gravity | Conservative static-equivalent assumption; not a shock test specification |
| Cable load | 20 N at 50 mm | Assumed accidental load; use separate strain relief so connectors are not structural restraints |
| Metal yield / modulus | 240 MPa / 70,000 MPa | Certified unwelded 6061-T6/T651 stock; supplier minimum yield and reference modulus [1] |
| Minimum yield safety factor | 3.0 | Chosen for preliminary loading, small quantities, and dimensional uncertainty; does not cover missing enclosure properties |
| A2-70 screw proof / stress area | 450 MPa / 14.2 mm² | Property-class reference and M5 coarse-thread stress area [2,3]; require traceable full-load ISO 4762 hardware |
| Upright CG bounds | z ≤120 mm; x ≤50 mm from upright web datum | Conservative assumed limits; verify actual assembly balance before release |
| Supporting structure | Rigid flat metal plate; worked example 6 mm 6061 | Assumed for hardware and local bearing only; actual plate span/edge distances/attachments must be reviewed |

None of the device mass, materials, shell strength, threads, or allowable screw penetration is inferred from STEP appearance. Device threads are unused. All fasteners attach mount components or the supporting structure.

## Load path and load envelopes

The four integral aluminum lands carry normal gravity from the enclosure pan into the pocket floor, outer base rails, four plate bolts, and the rigid installation plate. Bottom 0.2 mm films protect finish; their complete loss is included in the capture screen. The low end lips and higher side lips oppose translation. Two separated top bars oppose lift and roll/pitch after the checked assembly gap closes. Screws and hard spacers connect those bars to the base, without intentionally clamping the device. In upright service the rotated cradle transmits loads through four through bolts into the machined L supports, then four foot bolts into the plate. Retention takes no friction credit. Films and their adhesive take no retention or preload credit. Small bounded rattle/free movement is possible.

Static gravity on the 1 kg device is 9.81 N. The deliberately additive device handling envelope is `F = (3+1)mg + 20 = {d['device_resultant_envelope_N']:.2f} N`. Its combined overturning moment is `M = 4mg×50 + 20×50 = {d['device_overturning_moment_Nmm']:.1f} N mm`. A conservative single-member reaction is `F + M/70 = {d['local_reaction_upper_bound_N']:.2f} N`; round upward to **150 N applied to one bar, land, lip, base rail, or retainer screw**. This treats complete applied force and overturning reaction as simultaneous on one member, rather than dividing equally among four contacts.

The complete 2.2 kg package has `4mg+20 = {d['complete_package_component_envelope_N']:.2f} N`. The upright handling envelope is 110 N horizontally and 110 N vertically plus 1,000 N mm. The **mount-only proof screen applies 150 N horizontally and 150 N vertically simultaneously**, with an additional 1,500 N mm cable couple. These components exceed the assumed single acceleration vector and add a sizing reserve. They are assumed equivalent static loads, not measured dynamic loads. Upright root moment per support is `(150×120 + 150×50 + 1500)/2 = {d['upright_root_moment_per_support_Nmm']:.0f} N mm`. Recalculate if package mass, CG bounds, cable forces, or support geometry exceed these values.

## Member strength

For a rectangular section, `A=bt`, `Z=bt²/6`, `I=bt³/12`. For a simply supported beam with a central point load, `Mmax=PL/4`, `σ=M/Z`, and `δ=PL³/(48EI)`. For a short cantilever, `M=Pa` and `δ=Pa³/(3EI)`. These classical small-deflection beam equations screen the mount members; they do not calculate local enclosure response.

The 140 mm span top bar is screened with a central 150 N load. Its effective width is 19 mm to conservatively remove the two 0.5 mm edge treatments; actual device contacts nearer the supports reduce the central-load bound. The local floor strip uses a 21.5 mm cantilever, 18 mm effective width excluding land corner radii, and 6 mm floor thickness. The outer base rail uses 140 mm span and net width with one hole removed for its whole length. The lip uses only a 4 mm long contact patch and minimum end-wall thickness reduced by 1 mm. The manufacturing drawing must preserve those ligaments and the end-stop retaining edge.

For the upright supports, the nominal straight section is 36×8 mm. The calculations reduce it to **35.8×7.95 mm**, enlarge the hole to 5.6 mm, and apply adverse 0.15 mm hole-position shifts. This requires the critical **8.00±0.05 mm finished web and foot thickness**; a general ±0.20 mm thickness tolerance is insufficient for the stated target. A factor 1.5 is applied to gross-section bending at the R6 root. A factor 2 is applied to bending at a whole-width net section excluding the maximum hole at the lower web attachment and near foot attachment. These are **selected engineering screening factors**, not calibrated or formally bounded stress-concentration/fatigue solutions. The quoted minimum safety factor is conditional on them; a larger local factor reduces that margin. Axial stress and root transverse shear are included. The foot-hole moment uses the nominal 30 mm remaining vertical-load lever from x=20 to the assumed CG x=50, adjusted adversely for hole position.

| Check | Screening stress (MPa) | Yield safety factor |
|---|---:|---:|
{rows}

Calculated minimum member yield SF: **{min(r['yield_safety_factors'].values()):.2f}**, target 3.0. Strength screen: **{'PASS for the declared assumptions' if r['strength_screen_pass'] else 'DOES NOT PASS — revise before release'}**. Gross bending, net sections, and selected local factors are checked; shell buckling, detailed plate torsion, fatigue, contact singularities, manufacturing defects, and support-structure global flexure are not resolved by this model. The generous member margins do not establish enclosure strength.

## Deflection and clearance

| Location/load | Calculated bound |
|---|---:|
| Top bar, 150 N central load | {df['bar']:.3f} mm |
| Local floor strip, 150 N | {df['local_floor']:.3f} mm |
| Base rail, 150 N flexural screen | {df['base_rail_flexure']:.3f} mm |
| Upright upper attachment, simultaneous severe envelope | {df['upright_severe_envelope']:.3f} mm |
| Upright handling, 110 N each axis +1 N m (conservative scaled bound) | {df['upright_handling_envelope']:.3f} mm |
| Upright normal service, 1g+20 N and 1 N m | {df['upright_normal_service_bound']:.3f} mm |

Upright deflection combines net-section web bending, the eccentric moment, elastic rotation of the foot between its two bolt supports, and foot vertical motion. It treats bolt/plate translations as fixed; actual bolt, plate, and enclosure compliance add to this. Foot rotation uses `θ=[M(a+s/3)+V(a²/2+as/3)]/(EI)` with nominal a=20 mm overhang, s=35 mm bolt spacing, adverse position tolerance, and absolute contributions added. The normal-service bound is evaluated independently with 20 N horizontal, `(2.2g+20)=41.582 N` vertical, and 1,000 N mm couple; counting the complete cable force on both axes is conservative. Handling deflection uses the 110/150 scaled proof bound, which also includes 1,100 N mm couple and therefore exceeds the required 1,000 N mm handling couple.

Recommended prototype limits are **2.0 mm elastic movement at the 150 N simultaneous severe mount-only proof screen**, **1.5 mm at the 110 N handling screen**, **0.75 mm in the normal 1g+20 N service test**, and **0.10 mm residual displacement** after unloading. These are selected functional acceptance limits, not manufacturer limits. The analytical proof bound is close to 2 mm and does not include real plate compliance; increase stiffness or allowance if prototype results exceed it. Reserve at least 2 mm extra moving-assembly clearance inside the box, in addition to measured plug/bend/tool clearance, until measured results justify less.

The end-capture screen includes maximum final assembly gap, complete top-film loss, bar/floor/rail elastic deflections added in the unfavorable direction, and opposite bottom-film loss: `u_top = gap_max + film + δ_bar + δ_floor + δ_rail = {c['top_travel_including_film_loss_and_member_flex_mm']:.3f} mm`. The pan can drop {c['opposed_bottom_film_loss_mm']:.3f} mm onto the opposite hard land. For a conservative end extent 80 mm about the device datum and 70 mm bar spacing, `u_end = u_top + (80−35)/70 × (u_top+0.2) = {c['end_tip_rise_mm']:.3f} mm`. Initial end overlap is {c['nominal_end_overlap_mm']:.3f} mm, leaving **{c['residual_end_overlap_before_tolerance_mm']:.3f} mm** before the actual pan contour and tolerances. Reserving another 0.20 mm for stop/pan height variation leaves **{c['after_additional_0p2mm_tolerance_reserve_mm']:.3f} mm**. Side overlap remains about {c['residual_side_overlap_before_tolerance_mm']:.3f} mm in the analogous roll screen. Adding floor/rail deflection to upper travel is deliberately conservative; common rigid motion of the base itself does not consume capture.

This narrow end margin is **provisional**, not a rated retention result. General 0.5 mm deburring must not be applied to the retaining edge: use ≤0.10 mm there. The exact CAD contour/tilt audit and the physical retention test govern, including rocking in both directions with films removed, worst allowed cold/warm gap, and applied loads. Check differential base bending; whole-base motion alone is not loss of retention. If clearance, temperature, or deflection permits escape, reduce the fitted gap/film thickness or revise the end stop before use. No impact factor for collision across the free gap is implied by the 3g static-equivalent load.

## Fasteners, holes, and contact

| Check | Result |
|---|---:|
| Worst upright foot-bolt axial demand from moment distribution | {d['upright_foot_bolt_axial_bound_N']:.1f} N |
| Selected individual foot-bolt external axial/shear screen | 400 N / 150 N |
| M5 equivalent external stress `sqrt((N/At)²+3(V/At)²)` | {f['combined_external_stress_MPa']:.2f} MPa |
| External proof safety factor, 450 MPa reference | {f['external_proof_SF']:.2f} |
| 6 mm aluminum plate transverse bearing, conservatively `400/(dt)` | {f['assumed_6mm_support_bearing_MPa']:.2f} MPa |
| Two-plane edge tear-out capacity, 7 mm clear ligament ×6 mm | {f['conservative_two_plane_edge_tearout_allowed_N']:.0f} N at SF3 |
| ISO 7089-size washer average external bearing pressure | {f['washer_average_pressure_MPa']:.2f} MPa |
| Spacer pressure from 150 N external load | {f['spacer_external_pressure_MPa']:.2f} MPa |
| One 16×20 mm land/film average at 150 N | {c['one_pad_average_at_150N_MPa']:.3f} MPa |
| Four lands, 1 kg static gravity average | {c['four_pad_gravity_average_MPa']:.4f} MPa |

These are external-load checks. Contact pressure is an average; it does not establish allowable enclosure pressure, label strength, film life, or resistance to denting at hard stops. Mount-only loads can be introduced with a rigid dummy. Do not proof-load the real radio through connectors or unverified shell features.

Retainer hardware is M5×50 ISO 4762 A2-70, M5 coarse pitch 0.8 mm, with a 1 mm washer, 8 mm bar, and 30 mm hard spacer: grip 39 mm, nominal entry 11 mm into the 12 mm base, nominal tip clearance 1 mm. Verify **≥8 mm fully formed thread engagement** and **≥0.5 mm tip clearance above the base underside** on actual purchased hardware and completed parts, allowing chamfers/runout/finish/tolerances. Through-tapped holes prevent blind-hole bottoming; screws must remain inside the base. Do not use the device's original screws or threads.

The conservative thread-stripping surrogate is `A_s=0.25π d_core L_e`, with d_core=4 mm and L_e=8 mm, giving {f['thread_surrogate_area_mm2']:.2f} mm². `F_allow=A_s Sy/(√3×3) = {f['thread_external_allowed_at_SF3_N']:.0f} N`. Against a 150 N external increment, that leaves only **{f['remaining_preload_budget_after_150N_N']:.0f} N** as an approximate preload ceiling at the same screening factor. This is not an approved tightening specification. Installation preload can dominate external forces; the fastening shop must establish and qualify seating/locking with the actual threads, lubricant/locking product, and finish, or test the joint. Do not adopt a generic steel-joint M5 torque. No torque is invented here. Seat bars against hard spacers while preserving device gap. Use the specified removable locking product to its supplier process; witness-mark and inspect. Repeated service and galling can reduce thread capacity.

The upright cradle bolts pass through metal members and use washers and prevailing-torque nuts. Complete hardware specifications and lengths are in the BOM; actual locknut thickness, coating, and plate thickness govern usable engagement. Require at least two complete threads through the locking element and accessible nut faces. The worked plate has through bolts, so no plate-tap pullout is assumed. Global plate bending, pull-through to a thin/soft/unsupported surface, local plate buckling, edge distances, and the plate's own attachments remain the installer's responsibility. If the actual supporting plate is not the assumed rigid metal plate, these local checks do not release the installation.

## Release limitations and validation

Confirm configured mass/CG, body dimensions, pan/stop contact, completed fit gap at every land, film thickness, and support flatness. Use the geometry report for STEP validity, export reopening, connector/tool envelopes, and nominal interference; this file does not claim those operations. Check all actual USB/power/RF plugs and cable bend radii, ensure cooling openings remain usable in both orientations, and conduct a powered thermal comparison in the actual box. No heat-sink or improved-cooling claim is made; anodize/films are not a verified grounding system. Review intended grounding and protect contact surfaces/corrosion appropriately.

Run mount-only static strength/retention tests with a representative dummy, then real-device fit, low-force retention, connector access, service removal, and thermal tests. Witness-mark screws and inspect for loosening, permanent distortion, thread damage, denting, and film wear. Application acceleration spectra, fatigue life, shipping shock, and repeated-removal life require separate requirements and validation. Follow the delivered prototype plan and record actual results before releasing P1 beyond prototype work.

## Sources

[1] [thyssenkrupp EN AW-6061 data sheet, June 2018](https://d2zo35mdb530wx.cloudfront.net/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf), sheet/plate T6/T651 minima and reference modulus; require certified matching stock. [2] [NBK stainless strength comparison](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/stainlessscrew/SNSX-88/?SelectedLanguage=en-US), A2-70 comparison values. [3] [NBK fastener mechanical-properties reference](https://static.nbk1560.com/en-US/resources/other/article/technical-29-mechanical-properties-of-fasteners-made-of-carbon-steel-and-alloy-steel/), metric coarse-thread stress areas. Accessed 2026-09-08. These references are not guarantees for untraceable purchased parts.
'''


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write-note', action='store_true')
    args = ap.parse_args()
    paths = {'params':PROJECT/'params.json', 'adapter':PROJECT/'adapter_params.json'}
    raw = {k:path.read_bytes() for k,path in paths.items()}
    p,a = (json.loads(raw[k]) for k in ('params','adapter'))
    r = calculate(p,a)
    if args.write_note:
        hashes = {k:hashlib.sha256(value).hexdigest() for k,value in raw.items()}
        (HERE/'engineering_checks.md').write_text(report(r,hashes),encoding='utf-8')
    print(json.dumps(r,indent=2))
    if not r['strength_screen_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
