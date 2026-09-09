"""NSP-1600 adapter: reproducible preliminary analytical checks, not test/FEA.

Standard-library Python. Run this file with --write to regenerate the adjacent
JSON calculation record and Markdown engineering note. CAD is owned separately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
Q = {
    "plate_x_mm":125.0,"plate_y_mm":300.6,"plate_t_mm":5.0,
    "plate_t_tolerance_mm":0.05,"plate_center_y_mm":-150.3,
    "outer_corner_R_mm":8.0,"outer_edge_break_mm":0.4,
    "fan_relief_depth_mm":0.5,"fan_relief_depth_tolerance_mm":0.05,
    "fan_relief_x_intervals_mm":[[-40.0,-2.85],[2.85,40.0]],
    "fan_relief_y_interval_mm":[-299.1,-269.5],"fan_relief_R_mm":0.5,
    "fan_frame_physical_gap_accept_min_mm":0.2,
    "housing_points_mm":[[-35.0,-16.1],[35.0,-16.1],[0.0,-280.8]],
    "stud_points_mm":[[-55.0,-16.1],[55.0,-16.1],[-55.0,-280.8],[55.0,-280.8]],
    "housing_hole_min_mm":3.3,"housing_hole_max_mm":3.5,
    "stud_hole_max_mm":3.9,"stud_location_allowance_mm":0.15,
    "countersink_mouth_max_mm":6.2,"countersink_angle_min_deg":89.0,
    "upper_bore_deburr_max_mm":0.1,"straight_throat_accept_min_mm":3.3,
    "effective_head_seat_OD_accept_min_mm":5.7,
    "screw_overall_length_mm":8.0,"screw_length_assumed_tolerance_mm":0.2,
    "screw_head_recess_min_mm":0.0,"screw_head_recess_max_mm":0.1,
    "vendor_max_penetration_mm":4.0,"M3_tensile_area_mm2":5.03,
    "vendor_M3_mount_torque_kgf_cm":[6.0,8.0],
    "kgf_cm_to_Nm":0.0980665,"torque_K_sensitivities":[0.1,0.2,0.3],
    "plate_yield_MPa":240.0,"E_MPa":70000.0,
    "aluminum_density_kg_mm3":2.7e-6,"plate_yield_factor_target":3.0,
    "device_mass_manufacturer_kg":1.8,"package_mass_allowance_kg":2.4,
    "gravity_m_s2":9.81,"incidental_acceleration_g":3.0,
    "cable_force_assumption_N":50.0,"cable_lever_assumption_mm":100.0,
    "device_handling_resultant_N":125.0,"package_handling_resultant_N":145.0,
    "device_load_height_mm":41.0,"package_load_height_mm":46.0,
    "CG_plan_half_x_envelope_mm":42.5,"CG_plan_half_y_envelope_mm":150.3,
    "front_housing_local_tension_N":240.0,"rear_housing_local_tension_N":160.0,
    "front_housing_local_shear_N":100.0,"rear_housing_local_shear_N":150.0,
    "FPE_tension_qualification_demand_N":250.0,
    "FPE_shear_qualification_demand_N":150.0,
    "rear_strip_gross_width_mm":35.0,"rear_strip_net_width_mm":28.0,
    "front_strip_gross_width_mm":30.0,"front_strip_net_width_mm":23.0,
    "support_span_allowance_mm":0.3,"front_arm_allowance_mm":0.3,
    "selected_bending_stress_factor":1.5,"local_proof_multiplier":1.5,
    "reference_main_panel_thickness_mm":6.0,
    "variants":[{"model":"NSP-1600-12","rated_output_W":1500,"typical_efficiency":0.89},
                {"model":"NSP-1600-24","rated_output_W":1608,"typical_efficiency":0.91},
                {"model":"NSP-1600-36","rated_output_W":1602,"typical_efficiency":0.915},
                {"model":"NSP-1600-48","rated_output_W":1608,"typical_efficiency":0.925}],
}


def inverse3(a):
    m=[list(a[i])+[float(i==j) for j in range(3)] for i in range(3)]
    for k in range(3):
        pivot=max(range(k,3),key=lambda i:abs(m[i][k]))
        m[k],m[pivot]=m[pivot],m[k]
        if abs(m[k][k])<1e-12:
            raise ValueError("Mounting group cannot restrain a normal force and two moments")
        v=m[k][k];m[k]=[x/v for x in m[k]]
        for i in range(3):
            if i!=k:
                v=m[i][k];m[i]=[m[i][j]-v*m[k][j] for j in range(6)]
    return [r[3:] for r in m]


def group_screen(points, force, couple, h, rx, ry):
    """Rigid elastic group, coordinates relative to the center of the CG box.

    N=B(B'B)^-1[Fz,-My,Mx]. Exact per-fastener tension extrema over independent
    resultant force/couple balls and the rectangular XY application-point box.
    Shear is a conservative direct-plus-torsion triangle inequality. These
    separate extrema need not occur together. No preload or prying is included.
    """
    B=[[1.0,x,y] for x,y in points]
    A=[[sum(b[i]*b[j] for b in B) for j in range(3)] for i in range(3)]
    inv=inverse3(A);n=len(points)
    cx=sum(p[0] for p in points)/n;cy=sum(p[1] for p in points)/n
    J=sum((x-cx)**2+(y-cy)**2 for x,y in points)
    application_radius=math.hypot(rx+abs(cx),ry+abs(cy))
    rows=[]
    for p,b in zip(points,B):
        c=[sum(b[k]*inv[k][j] for k in range(3)) for j in range(3)]
        fz=abs(c[0])+rx*abs(c[1])+ry*abs(c[2])
        N=force*math.sqrt((h*c[1])**2+(h*c[2])**2+fz*fz)+couple*math.hypot(c[1],c[2])
        V=force/n+(couple+force*application_radius)*math.hypot(p[0]-cx,p[1]-cy)/J
        rows.append({"point_relative_to_body_center_mm":p,"max_tension_N":N,
                     "max_shear_N":V,"normal_wrench_coefficients":c})
    return {"points":rows,"centroid_relative_to_body_center_mm":[cx,cy],
            "polar_sum_mm2":J,"max_tension_N":max(r["max_tension_N"] for r in rows),
            "max_shear_N":max(r["max_shear_N"] for r in rows)}


def strip_check(name, P, V, t, q):
    b=q[name+"_strip_net_width_mm"];E=q["E_MPa"]
    xs=[x for x,y in q["stud_points_mm"]]
    L=max(xs)-min(xs)+q["support_span_allowance_mm"]
    a=max(abs(x) for x in xs)-max(abs(x) for x,y in q["housing_points_mm"][:2])+q["front_arm_allowance_mm"]
    I=b*t**3/12;Z=b*t*t/6
    if name=="rear":
        M=P*L/4
        delta=P*L**3/(48*E*I)
        shape="central point load between two simple supports"
    else:
        # Equal +/- envelopes applied independently. Both front loads at their
        # positive bound produce M=P*a; opposite signs produce smaller maxima.
        M=P*a
        delta=P*a*(3*L*L-4*a*a)/(24*E*I)
        shape="two symmetric equal loads P, each a from its nearer support"
    # Conservative addition of in-plane direct stress and transverse shear.
    # These component peaks are not spatially coincident in the real plate.
    sigma=q["selected_bending_stress_factor"]*M/Z+V/(b*t)
    tau=1.5*(P+V)/(b*t)
    vm=math.sqrt(sigma*sigma+3*tau*tau)
    return {"idealization":shape,"P_each_N":P,"V_local_N":V,"net_width_mm":b,
            "thickness_mm":t,"span_mm":L,"front_arm_mm":a,"I_mm4":I,"Z_mm3":Z,
            "M_Nmm":M,"normal_stress_screen_MPa":sigma,"shear_screen_MPa":tau,
            "VM_MPa":vm,"yield_factor":q["plate_yield_MPa"]/vm,
            "free_bending_deflection_max_mm":delta,
            "surrogate_proof_deflection_mm":q["local_proof_multiplier"]*delta}


def calculate(q=Q):
    Sy=q["plate_yield_MPa"];E=q["E_MPa"]
    t=q["plate_t_mm"]-q["plate_t_tolerance_mm"]
    tc=t-q["fan_relief_depth_mm"]-q["fan_relief_depth_tolerance_mm"]
    C=q["cable_force_assumption_N"]*q["cable_lever_assumption_mm"]
    def centered(points):
        return [[x,y-q["plate_center_y_mm"]] for x,y in points]
    rx=q["CG_plan_half_x_envelope_mm"];ry=q["CG_plan_half_y_envelope_mm"]
    housing=group_screen(centered(q["housing_points_mm"]),q["device_handling_resultant_N"],C,q["device_load_height_mm"],rx,ry)
    studs=group_screen(centered(q["stud_points_mm"]),q["package_handling_resultant_N"],C,q["package_load_height_mm"],rx,ry)
    housing_centered=group_screen(centered(q["housing_points_mm"]),q["device_handling_resultant_N"],C,q["device_load_height_mm"],0,0)
    front=strip_check("front",q["front_housing_local_tension_N"],q["front_housing_local_shear_N"],t,q)
    rear=strip_check("rear",q["rear_housing_local_tension_N"],q["rear_housing_local_shear_N"],tc,q)
    alternatives=[]
    for nominal in [3.5,4.5,5.0]:
        land=nominal-q["plate_t_tolerance_mm"]
        core=land-q["fan_relief_depth_mm"]-q["fan_relief_depth_tolerance_mm"]
        f=strip_check("front",q["front_housing_local_tension_N"],q["front_housing_local_shear_N"],land,q)
        r=strip_check("rear",q["rear_housing_local_tension_N"],q["rear_housing_local_shear_N"],core,q)
        alternatives.append({"nominal_plate_t_mm":nominal,"front_yield_factor":f["yield_factor"],
                             "rear_yield_factor":r["yield_factor"],"rear_free_bending_mm":r["free_bending_deflection_max_mm"]})
    # Longitudinal plate self-load only: PSU external loads enter at the three
    # OEM holes next to the stud rows; they are not a midspan adapter point load.
    mass=q["plate_x_mm"]*q["plate_y_mm"]*q["plate_t_mm"]*q["aluminum_density_kg_mm3"]
    acceleration_factor=1+q["incidental_acceleration_g"]
    self_F=mass*acceleration_factor*q["gravity_m_s2"]
    ys=[y for x,y in q["stud_points_mm"]]
    Llong=max(ys)-min(ys)+q["support_span_allowance_mm"];blong=100.0
    Iglobal=blong*tc**3/12;Zglobal=blong*tc*tc/6
    Mglobal=self_F*Llong/8
    sigma_global=q["selected_bending_stress_factor"]*Mglobal/Zglobal
    delta_global=5*self_F*Llong**3/(384*E*Iglobal)
    # In-plane plate compressive load stability, hypothetical unsupported full
    # length, pinned K=1 and deliberately narrow 100mm effective section.
    buckling=math.pi**2*E*Iglobal/(Llong*Llong)
    cs_depth=(q["countersink_mouth_max_mm"]-q["housing_hole_min_mm"])/(2*math.tan(math.radians(q["countersink_angle_min_deg"]/2)))
    straight=t-cs_depth-q["upper_bore_deburr_max_mm"]
    P=max(q["front_housing_local_tension_N"],q["rear_housing_local_tension_N"])
    V=q["FPE_shear_qualification_demand_N"]
    punch_area=math.pi*q["housing_hole_min_mm"]*q["straight_throat_accept_min_mm"]
    seat_area=math.pi/4*(q["effective_head_seat_OD_accept_min_mm"]**2-q["housing_hole_max_mm"]**2)
    edge=q["plate_x_mm"]/2-max(abs(x) for x,y in q["stud_points_mm"])-q["stud_location_allowance_mm"]
    tear_t=t-2*q["outer_edge_break_mm"]
    tear_area=2*(edge-q["stud_hole_max_mm"]/2)*tear_t
    stud_bearing=2*V/(2.4*t)
    local_checks={
        "front_strip":{"stress_equivalent_MPa":front["VM_MPa"],"yield_factor":front["yield_factor"]},
        "rear_relief_strip":{"stress_equivalent_MPa":rear["VM_MPa"],"yield_factor":rear["yield_factor"]},
        "longitudinal_self_load":{"stress_equivalent_MPa":sigma_global,"yield_factor":Sy/sigma_global},
        "countersink_external_punching":{"stress_equivalent_MPa":math.sqrt(3)*P/punch_area,"yield_factor":Sy*punch_area/(math.sqrt(3)*P)},
        "countersink_external_bearing_factor3":{"stress_equivalent_MPa":3*P/seat_area,"yield_factor":Sy*seat_area/(3*P)},
        "stud_hole_bearing_factor2":{"stress_equivalent_MPa":stud_bearing,"yield_factor":Sy/stud_bearing},
        "stud_hole_edge_tearout":{"stress_equivalent_MPa":math.sqrt(3)*V/tear_area,"yield_factor":Sy*tear_area/(math.sqrt(3)*V)},
        "stud_external_plate_punching":{"stress_equivalent_MPa":math.sqrt(3)*q["FPE_tension_qualification_demand_N"]/(math.pi*3.7*t),"yield_factor":Sy*math.pi*3.7*t/(math.sqrt(3)*q["FPE_tension_qualification_demand_N"])},
        "housing_hole_shear_bearing_factor2":{"stress_equivalent_MPa":2*q["rear_housing_local_shear_N"]/(2.4*tc),"yield_factor":Sy*2.4*tc/(2*q["rear_housing_local_shear_N"])},
    }
    projection_min=q["screw_overall_length_mm"]-q["screw_length_assumed_tolerance_mm"]-(q["plate_t_mm"]+q["plate_t_tolerance_mm"])+q["screw_head_recess_min_mm"]
    projection_max=q["screw_overall_length_mm"]+q["screw_length_assumed_tolerance_mm"]-t+q["screw_head_recess_max_mm"]
    torques=[v*q["kgf_cm_to_Nm"] for v in q["vendor_M3_mount_torque_kgf_cm"]]
    torque_sensitivity=[]
    for K in q["torque_K_sensitivities"]:
        preload=[T/(K*.003) for T in torques]
        torque_sensitivity.append({"assumed_K":K,"illustrative_preload_N":preload,
            "nominal_projected_cone_bearing_MPa":[F/seat_area for F in preload],
            "shank_axial_MPa":[F/q["M3_tensile_area_mm2"] for F in preload]})
    shanks={name:math.sqrt(N*N+3*Vv*Vv)/q["M3_tensile_area_mm2"] for name,N,Vv in
            [("front_M3",q["front_housing_local_tension_N"],q["front_housing_local_shear_N"]),
             ("rear_M3",q["rear_housing_local_tension_N"],q["rear_housing_local_shear_N"]),
             ("FPE_M3_external_demand",q["FPE_tension_qualification_demand_N"],q["FPE_shear_qualification_demand_N"]) ]}
    return {"status":"PRELIMINARY_ANALYTICAL_PLATE_SCREEN; NO_ASSEMBLY_RATING",
        "inputs":q,"loads":{"device_derived_N":acceleration_factor*q["device_mass_manufacturer_kg"]*q["gravity_m_s2"]+q["cable_force_assumption_N"],
            "package_derived_N":acceleration_factor*q["package_mass_allowance_kg"]*q["gravity_m_s2"]+q["cable_force_assumption_N"],
            "cable_couple_Nmm":C,"housing":housing,"FPE":studs,"housing_centered_CG_sensitivity":housing_centered},
        "plate":{"minimum_land_mm":t,"minimum_relief_floor_mm":tc,"uncut_mass_upper_bound_kg":mass,
            "front":front,"rear":rear,"thickness_comparison":alternatives,
            "self_load_4g_N":self_F,"longitudinal_self_load_deflection_mm":delta_global,
            "unsupported_inplane_Euler_N":buckling,"Euler_to_145N_ratio":buckling/q["package_handling_resultant_N"],
            "checks":local_checks,"minimum_screen_yield_factor":min(c["yield_factor"] for c in local_checks.values()),
            "screen_target_met":all(c["yield_factor"]>=q["plate_yield_factor_target"] for c in local_checks.values())},
        "countersink":{"cone_depth_max_screen_mm":cs_depth,"material_above_cone_min_mm":t-cs_depth,
            "straight_cylinder_min_stack_mm":straight,"straight_cylinder_used_mm":q["straight_throat_accept_min_mm"],
            "effective_seat_projected_area_mm2":seat_area,"external_punching_area_mm2":punch_area,
            "stud_edge_tear_area_mm2":tear_area},
        "screw_fit":{"nominal_projection_mm":q["screw_overall_length_mm"]-q["plate_t_mm"]+.05,
            "assumed_tolerance_projection_min_mm":projection_min,"assumed_tolerance_projection_max_mm":projection_max,
            "published_max_penetration_margin_at_tolerance_max_mm":q["vendor_max_penetration_mm"]-projection_max},
        "unrated_joints":{"manufacturer_M3_mount_torque_Nm":torques,
            "torque_K_sensitivity_NOT_preload_prediction":torque_sensitivity,
            "external_shank_VM_MPa_NO_head_or_thread_rating":shanks},
        "heat":{"method":"P_loss=P_output*(1/eta_typical-1); not a worst-case loss specification",
            "variants":[dict(v,typical_input_W=v["rated_output_W"]/v["typical_efficiency"],
                             typical_loss_W=v["rated_output_W"]*(1/v["typical_efficiency"]-1)) for v in q["variants"]]}}


def audit_inputs():
    audit={"critical_CAD_parameters_status":"not_yet_available","mismatches":[],"files":{}}
    expected={"plate_width":Q["plate_x_mm"],"plate_length":Q["plate_y_mm"],"plate_thickness":Q["plate_t_mm"],
              "plate_center_y":Q["plate_center_y_mm"],"plate_thickness_tolerance":Q["plate_t_tolerance_mm"],
              "corner_radius":Q["outer_corner_R_mm"],"edge_break":Q["outer_edge_break_mm"],"bore_deburr":Q["upper_bore_deburr_max_mm"],
              "housing_points":Q["housing_points_mm"],"housing_clearance_diameter":3.4,
              "countersink_diameter_reference":6.1,"countersink_angle_deg":90,
              "screw_length_overall":8,"screw_pitch":.5,"screw_head_recess_nominal":.05,
              "screw_projection_accept_min":2.75,"screw_projection_accept_max":3.35,
              "manufacturer_max_penetration":4,"manufacturer_bottom_torque_kgf_cm":[6,8],
              "fan_relief_width":37.15,"fan_relief_length":29.6,
              "fan_relief_centers_x":[-21.425,21.425],"fan_relief_center_y":-284.3,
              "fan_relief_radius":.5,"fan_relief_depth":.5,
              "fan_relief_depth_tolerance":.05,"minimum_physical_fan_gap":.2,
              "stud_pitch_x":110,"stud_pitch_y":264.7,"stud_pattern_center_x":0,
              "stud_pattern_center_y":-148.45,"stud_pattern_rotation_deg":0,
              "stud_clearance_diameter":3.8,"stud_diameter":3,"stud_projection":12,
              "panel_reference_thickness":6}
    path=PROJECT/"params.json"
    if path.exists():
        p=json.loads(path.read_text(encoding="utf-8-sig"))
        # Shared root parameter naming is explicitly checked, never guessed.
        audit["checked_parameters"]=expected
        audit["mismatches"]=[{"key":k,"expected":v,"actual":p.get(k)} for k,v in expected.items() if p.get(k)!=v]
        audit["critical_CAD_parameters_status"]="matched" if not audit["mismatches"] else "MISMATCH"
    for relative in ["params.json","datasheets/NSP-1600-spec_USER.pdf",
                     "references/geometry/mounting_interface.json","references/geometry/fan_bottom_contact_geometry.json",
                     "exports/cad_build_metadata.json"]:
        f=PROJECT/relative
        if f.exists():
            audit["files"][relative]={"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size}
    metadata=PROJECT/"exports/cad_build_metadata.json"
    if metadata.exists():
        m=json.loads(metadata.read_text(encoding="utf-8-sig"))
        audit["CAD_reported_plate"]={"volume_mm3":m["plate_volume_mm3"],
            "mass_kg_at_2700_kg_m3":m["plate_mass_kg_at_2700_kg_m3"],
            "density_recalculated_mass_kg":m["plate_volume_mm3"]*Q["aluminum_density_kg_mm3"]}
    return audit


def report(r):
    q=r["inputs"];p=r["plate"];c=r["countersink"];s=r["screw_fit"]
    comparison="\n".join(f"| {v['nominal_plate_t_mm']:.1f} | {v['front_yield_factor']:.2f} | {v['rear_yield_factor']:.2f} | {v['rear_free_bending_mm']:.3f} |" for v in p["thickness_comparison"])
    checks="\n".join(f"| {k.replace('_',' ')} | {v['stress_equivalent_MPa']:.2f} | {v['yield_factor']:.2f} |" for k,v in p["checks"].items())
    heat="\n".join(f"| {v['model']} | {v['rated_output_W']} | {100*v['typical_efficiency']:.1f}% | {v['typical_loss_W']:.1f} |" for v in r["heat"]["variants"])
    torque="\n".join(f"| {v['assumed_K']:.1f} | {v['illustrative_preload_N'][0]:.0f}–{v['illustrative_preload_N'][1]:.0f} | {v['nominal_projected_cone_bearing_MPa'][0]:.1f}–{v['nominal_projected_cone_bearing_MPa'][1]:.1f} |" for v in r["unrated_joints"]["torque_K_sensitivity_NOT_preload_prediction"])
    cad_mass=r["input_audit"].get("CAD_reported_plate",{}).get("mass_kg_at_2700_kg_m3")
    cad_mass_sentence=f"The exported plate volume gives {cad_mass:.4f} kg at the same assumed stock density; the actual supply mass is taken from its manufacturer, not from CAD density. " if cad_mass is not None else ""
    return f'''# Mean Well NSP-1600 stud adapter — engineering note

This is a preliminary machined adapter for horizontal, stationary indoor mounting on a rigid metal panel inside the proposed cooled enclosure. The selected **5 mm plate passes the stated analytical plate yield screens**, with a minimum calculated factor of {p['minimum_screen_yield_factor']:.2f} against certified material yield. This is not an assembled-system safety factor. The countersunk screw heads, PSU mounting bosses, FPE stud attachment, preload, complete supporting panel and powered enclosure still require the qualifications below. No FEA, fabrication, physical load test or thermal test was performed.

## Evidence, concept and geometry

The user-supplied Mean Well specification dated 2025-08-19 gives a 1.8 kg supply, nominal body 300×85×41 mm and three authorized bottom M3 mounting holes. Its page 6 limits external bottom-screw penetration to 4 mm and recommends 6–8 kgf·cm for those mounting screws. The separately specified side M4 holes and terminal screws have different limits. Current manufacturer documents inspected by the research agent retain the bottom mounting instructions.

The supplied STEP was freshly audited. Its normalized bottom interface is Z=0, terminal end Y=0, body approximately Y=−300.6 to 0 and X±42.5 mm. Bottom axes are X±35/Y−16.1 and X0/Y−280.8 mm. Small differences between source-coordinate measurements and these normalized drawing values are recorded by the geometry audit. The source includes fan-frame geometry reaching the nominal bottom plane. The adapter must therefore avoid loading the plastic frames. The apparent thread-bearing regions are short (about 1.38 mm near the terminals and 1.22 mm at the fan end); this is geometric evidence, not a full-thread or strength specification. No 2 mm engagement requirement from earlier unrelated designs is imposed.

The chosen route is one machined 6061-T6/T651 plate, 125×300.6×5.00±0.05 mm, R8 corners and consistent 0.4 mm outer edge breaks. Four verified-type FPE WGU30 M3 studs lie at X±55/Y−16.1 and −280.8 mm. Two 0.50±0.05 mm top reliefs span X−40..−2.85 and +2.85..+40, Y−299.1..−269.5, with R0.5 corners. These retain a full-height central metal contact strip and outer metal contacts. Preserve the shallow pocket edges and central land dimensions; remove burrs without a large pocket-mouth chamfer. Require at least 0.2 mm actual gap to both plastic fan frames after tightening and under normal service.

A folded tray or side-ear bracket could use the published side M4 holes, but adds parts/bends and occupies lateral service space. A bottom plate uses the three manufacturer-authorized attachment points, keeps the unit removable, and places the fastener heads flush underneath for the panel interface. A 3.5 mm plate was rejected because its narrow rear strip fails the selected factor-3 handling screen. The 5 mm plate gives useful margin without ribs beneath the seating face. The uncut plate mass upper bound is {p['uncut_mass_upper_bound_kg']:.4f} kg. {cad_mass_sentence}A 2.4 kg package allowance covers the 1.8 kg supply, this plate and nominal hardware, subject to weighing the built package.

## Load path and load cases

Normal horizontal gravity passes from the metal chassis contacts into the adapter and the supporting panel. Reverse handling and overturning pass through the three M3 screws and their conical plate seats, across the local plate strips, through four M3 stud/nut joints and the FPE bonded/load-stud interfaces into the main panel. In-plane translation is restrained by screw/countersink and stud-hole bearing; no friction, fan-frame or incidental connector support is credited. Clearance at the studs permits small movement before bearing and must be acceptable to the cable installation. The three separated device points and four separated panel points restrain unintended rotation when their joints are intact.

Inputs are explicit preliminary assumptions: 3g incidental acceleration added to 1g gravity, 50 N cable force and a 100 mm cable lever. The cable couple is **5 N·m**, not 1 N·m. Device force is 1.8×4×9.81+50={r['loads']['device_derived_N']:.3f} N, rounded to a 125 N resultant. Package force is 2.4×4×9.81+50={r['loads']['package_derived_N']:.3f} N, rounded to 145 N. Each is a resultant with arbitrary direction, not simultaneous full loading on all three axes. The free couple has arbitrary direction; adding it independently to the force/height moment is conservative. Cable routing must prevent loads exceeding these assumptions. These cases do not qualify vehicle, airborne, seismic, outdoor or overhead service, or a shock/vibration spectrum.

The unknown force/CG position is allowed anywhere in the 85×300.6 mm body plan. The force height is conservatively bounded by 41 mm above the supply interface and 46 mm above the panel interface. This is a bounding envelope, not a measured center of gravity. A rigid elastic group is solved with B rows [1,x,y] and N=B(BᵀB)⁻¹[Fz,−My,Mx]. The script takes the exact individual tension maximum over the rectangular application-point box and force/couple balls. Shear is bounded by F/n+(C+F·r_application)r_i/Σr². Preload, joint separation and local prying are outside this model.

Maximum front M3 demand is {r['loads']['housing']['points'][0]['max_tension_N']:.2f} N tension and {r['loads']['housing']['points'][0]['max_shear_N']:.2f} N shear; rear M3 demand is {r['loads']['housing']['points'][2]['max_tension_N']:.2f} N tension and {r['loads']['housing']['points'][2]['max_shear_N']:.2f} N shear. Local screens round these to 240/100 N at the front and 160/150 N at the rear. The maximum FPE rigid-group demand is {r['loads']['FPE']['max_tension_N']:.2f} N tension/{r['loads']['FPE']['max_shear_N']:.2f} N shear. A proposed qualification demand of 250 N tension/150 N shear per stud is carried into the plate-hole screen; it is neither an FPE allowable nor proof that prying is bounded by that value.

## Plate checks and thickness selection

Use certified unwelded 6061-T6/T651 stock with minimum yield 240 MPa. E=70 GPa is an approximate supplier guidance value for deflection calculations, not a guaranteed minimum. The screening target is 3 against metal yield because loads, effective strip widths and contact distribution are uncertain. A separately chosen 1.5 bending stress allowance addresses local geometry approximately; it is not a validated notch factor. There is no polymer structural credit.

The rear screw loads a transverse strip between the 110 mm stud spacing. A 35 mm gross strip fits inside the 19.8 mm rear end margin; deduct 7 mm for the hole/seat to use only 28 mm net width. Conservatively reduce this entire net strip to the minimum 4.40 mm pocket-floor thickness even though the central bridge and portions outside the relief retain 4.95 mm. Span is increased to 110.3 mm for location/clearance. Use I=bt³/12, Z=bt²/6, M=PL/4 and δ=PL³/(48EI). This is an effective-strip idealization requiring physical correlation, not an exact two-dimensional plate/contact solution.

The front holes are 20 mm inward from their respective studs. The 16.1 mm front edge distance allows a symmetric 30 mm gross strip; deduct 7 mm for a 23 mm net strip. Use the minimum unrelieved 4.95 mm thickness, a 20.3 mm arm, and the conservative equal pair of 240 N loads. M=P·a. The maximum free beam deflection is P·a(3L²−4a²)/(24EI). Normal stress combines 1.5M/Z with V/(bt), and shear is conservatively 1.5(P+V)/(bt); σ_VM=√(σ²+3τ²). Peak stresses are added despite not necessarily occurring together. These checks do not transfer device loads into an imaginary unsupported plate-center point: device forces enter at the three actual OEM holes near the stud rows. The remaining longitudinal plate carries its own inertia, screened as a uniformly loaded simply supported strip 100 mm wide across 265 mm using the minimum pocket-floor thickness. Its 4g deflection is {p['longitudinal_self_load_deflection_mm']:.3f} mm. A pinned-strip Euler stability sensitivity gives {p['unsupported_inplane_Euler_N']:.0f} N, {p['Euler_to_145N_ratio']:.1f} times the 145 N package load; local sheet/contact imperfections still need inspection.

| Nominal plate mm | Front yield factor | Rear yield factor | Rear free deflection mm |
|---|---:|---:|---:|
{comparison}

| Check | Equivalent stress MPa | Yield factor |
|---|---:|---:|
{checks}

Selected free bending predictions are {p['front']['free_bending_deflection_max_mm']:.3f} mm at the front and {p['rear']['free_bending_deflection_max_mm']:.3f} mm at the rear. Full-panel compression support makes the normal seated case stiffer, but is not credited for reverse handling. At 1.5 times the local external loads, predicted free elastic deflections are {p['front']['surrogate_proof_deflection_mm']:.3f}/{p['rear']['surrogate_proof_deflection_mm']:.3f} mm. These are analytical predictions. Do not infer screw preload, case deformation, actual frame gap or system stiffness from them.

## Countersinks, screw fit and unqualified joints

Select McMaster 91294A128, M3×0.5×8 DIN 7991 countersunk screws with nominal 90°/Ø6 head and 2 mm hex drive, through the 5 mm adapter. Gauge the manufactured seat with received screws: the head must fully seat without rocking and be flush to 0.10 mm recessed. Reference machining dimensions do not alone guarantee flushness. The seat screen uses mouth≤6.2 mm, throat≥3.3 mm, angle≥89°, an upper bore deburr≤0.10 mm, and an effective conical head-seat diameter≥5.7 mm. Maximum cone depth is {c['cone_depth_max_screen_mm']:.4f} mm. Minimum material above the cone is {c['material_above_cone_min_mm']:.4f} mm; after the upper deburr, the straight cylindrical ligament is {c['straight_cylinder_min_stack_mm']:.4f} mm. Require a measured minimum 3.30 mm straight ligament. External pull-through uses A=πd·3.30 and shear yield Sy/√3. Average conical-seat bearing uses projected annular area {c['effective_seat_projected_area_mm2']:.3f} mm² with a factor 3 on external average pressure. These are external-load plate screens, not a countersunk screw-head rating.

Nominal projection is {s['nominal_projection_mm']:.2f} mm at 0.05 mm head recess. An explicitly assumed screw length tolerance ±0.20 mm, plate ±0.05 and head recess 0–0.10 gives {s['assumed_tolerance_projection_min_mm']:.2f}–{s['assumed_tolerance_projection_max_mm']:.2f} mm, leaving {s['published_max_penetration_margin_at_tolerance_max_mm']:.2f} mm below Mean Well's published 4.00 mm maximum. The screw-length tolerance is not a verified catalog tolerance. Measure all three installed projections; **4.00 mm is the hard maximum**, and confirm the received screw engages the actual short boss correctly and reaches clamp-up without internal obstruction. Do not use the approximate CAD thread region to invent a female alloy, a minimum complete engagement or pullout strength. Do not drill, retap or replace case features by default.

Mean Well's bottom-mount torque range converts to {r['unrated_joints']['manufacturer_M3_mount_torque_Nm'][0]:.4f}–{r['unrated_joints']['manufacturer_M3_mount_torque_Nm'][1]:.4f} N·m. It is published installation guidance, **not a tensile/pullout capacity or a tested rating for this specific DIN 7991 head, finish and aluminum seat**. Obtain confirmation that the selected head/seat and any locking treatment are suitable, or qualify a representative joint before production tightening. Do not invent a different torque or assume a threadlocker is neutral to friction.

For scale only, the uncalibrated relation T=KFd with d=3 mm gives:

| Assumed K | Illustrative clamp force N | Average projected cone pressure MPa |
|---|---:|---:|
{torque}

These wide ranges are sensitivity calculations, not preload predictions, torque settings or accepted loads. The clamp path closes locally from cone through the plate into the chassis contact/boss. Preload cannot simply be equated to the external free-strip load, yet local contact pressure, countersink wedging, chassis bearing and screw-head strength still require qualification. The short extruded/threaded boss, case material, head reduced loadability and mounting-joint strength remain unverified. No thread stripping factor is assigned. M3 tensile area 5.03 mm² gives nominal external shank stresses recorded in the JSON; those values do not certify the head or female thread.

FPE WGU30 M3 load studs use the known catalog geometry, but axial/shear, bond cure, temperature and torque capacities were not found. Their supplier qualification and the actual main-panel design are required. A 6 mm main-panel thickness is reference geometry only. The plate hole-bearing screen uses a conservative 2.4 mm screw-root bearing diameter and factor 2; edge tearout uses the reduced edge thickness after both outer breaks. Washers/nuts and full thread engagement must match the verified BOM, and enough stud tail must remain for the selected nut. Define locking and tightening from the qualified hardware/FPE process; no unsupported torque is assigned. A flat plate cannot compensate for a warped, contaminated or insufficiently stiff panel.

The additional stud plate-punching screen uses the 250 N external tensile demand around a 3.7 mm hole perimeter through the 4.95 mm minimum plate. It assumes the intact specified nut/washer physically bridges the hole; it does not assign a washer bending capacity or a stud-head/bond rating. Inspect received nut/washer dimensions, seating and permanent deformation in the joint qualification. Housing-hole in-plane bearing is additionally screened at 150 N, using the conservative 4.40 mm relief floor and 2.4 mm root-bearing diameter.

## Manufacturing, fit and electrical/service requirements

Machine from traceable 6061 stock, with both seating planes finished to the drawing. Use conventional face milling, drilling and 90° countersinking, then shallow relief milling. R0.5 pocket corners require a suitably small cutter or a shop-agreed larger radius that still clears the measured fan outline and preserves the contact spine; cutter access is open from the top. Protect the thin full-height central contact land during clamping and deburring. Finish dimensions are after any coating. Do not count paint, oxide or an anodized interface as a reliable protective-earth connection or as thermally helpful contact. Specify surface treatment/grounding with the enclosure design and retain the PSU's designated earth connection.

The specification's general ±0.5 mm tolerance is larger than fixed countersinks can absorb by self-centering. The 1:1 fit template and actual measurement of all three hole positions are therefore release requirements. Revise the named CAD coordinates to the received supply if necessary; do not force-fit screws or substitute elongated countersinks with line contact. Check the actual fan contour against the 0.1 mm nominal lateral pocket margins and confirm the full metal contact land remains. Pocket depth is chosen for ≥0.2 mm physical fan-frame clearance, not as a cooling improvement.

Mount the supply to its adapter before placing the adapter over the four panel studs. All three screw heads must remain below the adapter underside and must not hold the plate off the panel. Install the verified washers/nuts using the specified compact socket envelope and lock method. Remove the complete supply/adapter from the studs for service; the device screws become accessible once lifted. The panel stud pattern is parametric. Provide independent cable strain relief and verify actual lug, terminal-cover, bend, insulation and tool envelopes. Maintain the manufacturer's fan intake/exhaust and installation clearances. No mount surface may obstruct the airflow path, touch a fan or become an electrical shorting path.

## Enclosure heat budget

No TIM or conductive cooling function is specified for this supply. It has factory forced-air cooling; no panel cooling credit is used. The user is considering the 12 V variant, with 24 V also possible. At rated output, the published typical efficiencies imply the following conversion losses, using P_loss=P_out(1/η−1):

| Variant | Rated output W | Typical efficiency | Calculated typical supply loss W |
|---|---:|---:|---:|
{heat}

These are not worst-case heat-loss specifications. Input voltage, load, setpoint, inlet temperature and fan behavior change loss and derating. Heat from loads located inside the same enclosure, wiring, other supplies and the TEC electrical input/hot side must be included separately. A TEC air-temperature target does not establish heat removal capacity. The 12 V case alone is approximately {r['heat']['variants'][0]['typical_loss_W']:.0f} W of supply conversion heat at rated output, before any other in-box losses. Confirm the actual variant and operating load, applicable derating and airflow, then size and test the complete enclosure. Do not block the fan path or claim a safe full-power temperature from this mount calculation.

## Prototype and release plan

1. Inspect the actual supply, model/variant, mounting pattern, fan outline, case contact regions and threads. Gauge every screw projection and seat. Confirm no internal interference and obtain head/seat/torque suitability for the manufacturer's short M3 mounting bosses. Weigh the package against the 2.4 kg allowance.
2. Inspect machined thicknesses, relief positions, straight countersink ligaments, finish, flatness and burrs. Assemble with received hardware, verify ≥0.2 mm fan-frame gap, no head proudness, full metal seating and no plastic contact. Check actual terminal covers, lugs, cable bend radii, compact socket access and removal path.
3. Use representative supported metal surrogates for initial plate/joint checks. Apply the 240/100 N front and 160/150 N rear local demands, with tension/shear combinations appropriate to the load path; correlate displacement to the strip assumptions. A separate 1.5× plate proof may use 360 N front/240 N rear with matched shear increments on surrogate attachments. Do not apply that proof to unqualified PSU bosses or FPE studs. Proposed acceptance: no fracture/loosening or permanent set above 0.10 mm; free-strip elastic movement below 0.70 mm at the 1.5× local proof, with fixture compliance removed. If longitudinal plate self-load is applied concurrently, use 0.85 mm combined elastic movement. These displacement criteria are separate from the actual ≥0.2 mm normal-service fan gap; check no fan-frame contact through the qualified handling cases as well.
4. Qualify the FPE bonded stud/panel interface at the specified temperature, cure and tightening conditions, including the 250 N tension/150 N shear proposed per-stud demand and any measured prying. Qualify the final case, screw and countersink joint at the approved mounting torque. Record witness marks, seating and post-cycle loosening; no capacity is assumed from appearance or the CAD.
5. Perform a complete assembly handling/strain-relief check using the stated force/couple envelope after joints are qualified. Verify repeated removal, reinstallation and witness-mark stability. Reassess if acceleration, cable forces, orientation or support changes.
6. Operate the actual 12/24 V configuration at intended input/output and worst expected enclosure ambient. Measure supply inlet/exhaust and enclosure temperatures, output load, electrical input and hot-side TEC conditions; verify manufacturer derating and no recirculation/blocked airflow. Include noncondensing humidity requirements and enclosure condensation behavior. Record results without equating fan noise or air setpoint with adequate cooling.

## Reproduction and sources

Run `python -B references/engineering/engineering_calculations.py --write` from this design folder. The script regenerates this note and `engineering_results.json`, checks its arithmetic/equilibrium and records source hashes. It is separate from CAD generation. Critical CAD parameters must match; changes to geometry, material, load basis or interfaces require rerunning and reviewing the calculations. All numerical records remain preliminary until correlated with the physical assembly.

- User-supplied manufacturer PDF: `datasheets/NSP-1600-spec_USER.pdf`, 2025-08-19, pp.2 and6. Current primary specification: [Mean Well NSP-1600 specification](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-SPEC.PDF). The research archive records the inspected current revision and installation instructions.
- [thyssenkrupp 6061 material data](https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf): certified T6/T651 plate strength selection is 240 MPa; elastic modulus is approximate guidance. The research archive contains the working manufacturer-document URL if this legacy link moves.
- [Bossard metric tensile stress areas](https://www.bossard.com/global-en/-/media/bossard-group/website/documents/technical-resources/en/f-004-en.pdf): M3 area5.03 mm². [Bossard countersunk-head guidance](https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/2103/) notes reduced head loadability; ordinary shank properties are not a head rating.
- Exact screw, washer, nut and FPE catalog evidence is retained by the procurement/research agent in this design's references. No alloy/strength or adhesive-capacity claim is inferred from their rendered geometry.
'''


def self_checks(r):
    q=r["inputs"]
    assert r["plate"]["screen_target_met"], "Plate yield target failed"
    assert r["countersink"]["straight_cylinder_min_stack_mm"]>=q["straight_throat_accept_min_mm"]
    assert r["screw_fit"]["assumed_tolerance_projection_max_mm"]<q["vendor_max_penetration_mm"]
    assert r["loads"]["device_derived_N"]<=q["device_handling_resultant_N"]
    assert r["loads"]["package_derived_N"]<=q["package_handling_resultant_N"]
    for index,N,V in [(0,240,100),(1,240,100),(2,160,150)]:
        row=r["loads"]["housing"]["points"][index]
        assert row["max_tension_N"]<=N and row["max_shear_N"]<=V
    for grp in [r["loads"]["housing"],r["loads"]["FPE"]]:
        # Wrench equilibrium for an asymmetric sample independent of envelopes.
        applied=[89.0,-4321.0,1234.0]
        reactions=[sum(c*w for c,w in zip(row["normal_wrench_coefficients"],applied)) for row in grp["points"]]
        recovered=[sum(reactions),sum(N*row["point_relative_to_body_center_mm"][0] for N,row in zip(reactions,grp["points"])),sum(N*row["point_relative_to_body_center_mm"][1] for N,row in zip(reactions,grp["points"]))]
        assert all(abs(a-b)<1e-7 for a,b in zip(applied,recovered))
    assert not r["input_audit"]["mismatches"], "CAD parameter mismatch"
    if "CAD_reported_plate" in r["input_audit"]:
        m=r["input_audit"]["CAD_reported_plate"]
        assert abs(m["mass_kg_at_2700_kg_m3"]-m["density_recalculated_mass_kg"])<1e-10
        assert m["mass_kg_at_2700_kg_m3"]<=r["plate"]["uncut_mass_upper_bound_kg"]
    return {"status":"passed","checks":["plate target","screw stack","ligament","load rounding","individual joint demand envelopes","group force/moment equilibrium","critical CAD parameters when available"]}


def brief_report(r):
    p=r["plate"];s=r["screw_fit"];g=r["loads"]
    return f'''# NSP-1600 adapter N1 — engineering summary

**Preliminary fit prototype, not a rated complete mounting system.** The selected machined 6061-T6/T651 adapter is 125×300.6×5.00±0.05 mm with two 0.50±0.05 mm fan-frame clearance pockets. It uses three authorized bottom M3 joints with flush McMaster 91294A128 M3×8 heads and four FPE WGU30 M3 panel studs. The existing case, covers, side screws and fan hardware are preserved. No TIM or panel-cooling function is selected.

The full reproducible [engineering calculations](references/engineering/engineering_checks.md) give equations, evidence, assumptions, tolerance stacks and limitations. The [JSON record](references/engineering/engineering_results.json) and [Python source](references/engineering/engineering_calculations.py) are the numerical authority; run the source with `--write` to regenerate these notes.

## Selection and completed analytical checks

- A single machined bottom plate has fewer unique parts than side brackets or a formed tray and leaves the factory top and side service features exposed. The 3.5 and 4.5 mm candidates fail the selected factor-3 local strip screen after deducting the countersink and fan reliefs. The 5 mm plate retains a 4.40 mm minimum relief floor and no protrusions beneath its panel seating face.
- Manufacturer supply mass 1.8 kg; package allowance 2.4 kg includes the {p['uncut_mass_upper_bound_kg']:.4f} kg uncut plate upper bound and hardware. The actual CAD plate is approximately 0.5021 kg, calculated from exported volume at 2700 kg/m³. Weigh the finished package.
- 1 g gravity + 3 g incidental acceleration and a 50 N cable force give 125 N device and 145 N package resultant design forces after rounding. An independently applied 5 N·m cable couple corresponds to 50 N at 100 mm. Conservative force-position bounds cover the body plan and 41/46 mm load heights. These are preliminary stationary handling assumptions, not an acceleration-spectrum qualification.
- Rigid-group demand: front M3 {g['housing']['points'][0]['max_tension_N']:.1f} N tension/{g['housing']['points'][0]['max_shear_N']:.1f} N shear; rear {g['housing']['points'][2]['max_tension_N']:.1f}/{g['housing']['points'][2]['max_shear_N']:.1f} N. Local plate screens use 240/100 N front and 160/150 N rear. FPE rigid-group maximum {g['FPE']['max_tension_N']:.1f}/{g['FPE']['max_shear_N']:.1f} N; 250/150 N per stud is a proposed qualification demand, not a verified allowable or prying bound.
- Certified 6061 yield 240 MPa and approximate E = 70 GPa are used. The minimum calculated plate yield factor is **{p['minimum_screen_yield_factor']:.2f}**, controlled by the front strip. Front/rear free-strip deflections are {p['front']['free_bending_deflection_max_mm']:.3f}/{p['rear']['free_bending_deflection_max_mm']:.3f} mm. Hole bearing, tearout, external countersink punching/bearing and longitudinal self-load screens also pass. Effective strips/stress allowances require prototype correlation; no FEA or physical test was performed.
- Nominal screw projection is {s['nominal_projection_mm']:.2f} mm. Assumed screw-length/plate/recess tolerances give {s['assumed_tolerance_projection_min_mm']:.2f}–{s['assumed_tolerance_projection_max_mm']:.2f} mm, below the published 4.00 mm maximum. Gauge all screws, verify actual boss engagement and obstruction clearance, and use received screws to finish flush seats. Straight cylindrical ligament≥3.30 mm, effective conical seat diameter≥5.7 mm and complete seating are required.

## Manufacturing and physical release gates

Machine from traceable nominal 6 mm or 1/4-inch 6061 stock using supported face/drill/countersink and shallow-pocket setups. Final drawing dimensions include finish. Preserve the 5.7 mm central contact land and shallow relief boundaries; do not apply the outside 0.4 mm chamfer to them. Clear conversion finish and a designated protective-earth connection require the enclosure's approved process; plate contact alone is not a protective-earth assurance.

Measure the actual three-hole pattern and use the 1:1 template before final machining: the manufacturer's general ±0.5 mm tolerance exceeds what three fixed countersinks can accommodate. Confirm the received case/PCB/boss and fan profiles, ≥0.20 mm normal-service fan-frame clearance, no plastic contact during qualified handling, plate flatness and metal seating. Verify actual lugs, terminal covers, cable bends, compact sockets, airflow reservations and removal path. Revise the parametric pattern when measurements require it; do not force screws or use improvised slotted cones.

Mean Well specifies 6–8 kgf·cm (0.5884–0.7845 N·m) for bottom mounting. That is not a tensile rating or a demonstrated torque for this specific countersunk head/finish/seat combination. Confirm or qualify the complete joint before production tightening. Short female bosses, countersunk-head reduced loadability, preload, locking method, washer/nut integrity, FPE bond/cure/temperature capacity and final panel support remain unqualified. No minimum 2 mm full engagement, case alloy or thread capacity is invented.

The [prototype plan](PROTOTYPE_VALIDATION.md) separates surrogate plate checks from the unqualified actual joints. Proposed local 1.5× proof uses 360 N front and 240 N rear tension with corresponding shear increments, only on suitable surrogate attachments initially. Elastic criteria are 0.70 mm local / 0.85 mm with concurrent longitudinal self-load, residual≤0.10 mm; normal fan clearance remains a separate requirement. Only apply complete-assembly proof after its OEM and FPE joints are qualified. Include repeated removal, loosening checks and realistic cable strain relief.

## Thermal limitation

The provisional 12 V variant is 1500 W rated output at 89% typical efficiency, implying **185.4 W typical supply conversion heat** at rated load. The 24 V alternative gives 159.0 W at 1608 W/91%. These are calculated typical losses, not guaranteed worst-case values. Factory airflow, manufacturer derating, actual input/load/ambient and recirculation must be checked in the final enclosure. Other in-box loads and TEC hot-side capacity add to the budget. The adapter receives no cooling credit, and the TEC setpoint alone does not establish adequate heat removal.

CAD solid validity, exported geometry, clearances and drawing checks are recorded separately by the CAD/geometry audit. This engineering summary claims only the calculations stated above; manufacture, load proof, joint qualification and powered thermal validation remain outstanding.
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--write",action="store_true")
    args=parser.parse_args();r=calculate();r["input_audit"]=audit_inputs();r["calculation_self_checks"]=self_checks(r)
    if args.write:
        HERE.mkdir(parents=True,exist_ok=True)
        (HERE/"engineering_results.json").write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
        (HERE/"engineering_checks.md").write_text(report(r),encoding="utf-8")
        (PROJECT/"ENGINEERING_NOTE.md").write_text(brief_report(r),encoding="utf-8")
    print(json.dumps(r,indent=2))


if __name__=="__main__":
    main()
