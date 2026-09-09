"""N2 preliminary station-frame/contact screens; standard-library Python.

Run --write to regenerate engineering_results.json. This does not authorize
physical tests or establish contact, fastener, chassis or FPE anchor capacity.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
Q={
 "plate_thickness_mm":6.0,"thickness_tolerance_mm":.05,
 "tab_length_mm":44.0,"net_strip_width_mm":35.0,"spine_width_mm":45.0,
 "plate_max_width_mm":72.0,"plate_length_mm":316.8,
 "stud_span_mm":57.0,"span_allowance_mm":.3,"station_pitch_mm":252.0,
 "housing_x_mm":2.3,"housing_y_mm":[-5.8,-257.8],"body_center_y_mm":-150.3,
 "CG_half_x_mm":20.5,"CG_half_y_mm":150.3,
 "device_height_mm":85.0,"package_height_mm":91.0,
 "device_mass_manufacturer_kg":1.8,"package_mass_allowance_kg":2.2,
 "gravity_m_s2":9.81,"gravity_plus_handling_factor":4.0,
 "cable_force_N":50.0,"cable_lever_mm":100.0,
 "device_force_N":125.0,"package_force_N":140.0,
 "minimum_contact_lever_mm":15.0,"roll_share_bound":1.0,
 "M4_joint_tension_demand_N":1250.0,"M4_joint_shear_demand_N":175.0,
 "toe_compression_qualification_N":1070.0,
 "FPE_tension_qualification_N":500.0,"FPE_shear_qualification_N":250.0,
 "Sy_MPa":240.0,"E_MPa":70000.0,"density_kg_mm3":2.7e-6,
 "yield_factor_target":3.0,"bending_stress_allowance":1.5,
 "deflection_allowance":1.5,"proof_multiplier":1.5,
 "M4_tensile_area_mm2":8.78,"M3_tensile_area_mm2":5.03,
 "head_seat_effective_OD_min_mm":7.6,"housing_bore_max_mm":4.6,
 "housing_bore_min_mm":4.4,"countersink_mouth_max_mm":8.2,
 "countersink_angle_min_deg":89.0,"upper_bore_deburr_max_mm":.1,
 "straight_ligament_accept_min_mm":3.9,"contact_pressure_factor_sensitivity":3.0,
 "screw_length_mm":10.0,"screw_length_assumed_tolerance_mm":.2,
 "head_recess_min_mm":0.0,"head_recess_max_mm":.1,
 "vendor_max_penetration_mm":5.0,"vendor_side_torque_kgf_cm":[7.0,10.0],
 "verified_toe_patch_areas_mm2":{"left":8.0,"right":7.2},
 "local_proof_elastic_limit_mm":.30,"combined_proof_elastic_limit_mm":.40,
 "residual_limit_mm":.10,
}


def station_coefficients(q):
    y1,y2=[y-q["body_center_y_mm"] for y in q["housing_y_mm"]]
    pitch=y1-y2
    return [("front",-y2/pitch,1/pitch),("rear",y1/pitch,-1/pitch)]


def linear_envelope(kN,kM,a,b,F,h,q):
    """Upper bound of kN*Nstation + kM*Mroll, with either roll sign.

    Nstation=(a+b*y)Fz-h*b*Fy+b*Cx.
    Mroll=h*Fx-(x-xbolt)*Fz+Cy. Force/couple vectors are independently
    bounded by their Euclidean norms. Contact-sign restrictions are relaxed,
    so this remains an upper bound, not an asserted achievable load case.
    """
    C=q["cable_force_N"]*q["cable_lever_mm"]
    values=[]
    for x in [-q["CG_half_x_mm"],q["CG_half_x_mm"]]:
        for y in [-q["CG_half_y_mm"],q["CG_half_y_mm"]]:
            for sign in [-1,1]:
                km=sign*kM
                cf=[km*h,-kN*b*h,kN*(a+b*y)-km*(x-q["housing_x_mm"])]
                values.append(F*math.sqrt(sum(v*v for v in cf))+C*math.hypot(kN*b,km))
    return max(values)


def calculate(q=Q):
    F=q["device_force_N"];h=q["device_height_mm"]
    C=q["cable_force_N"]*q["cable_lever_mm"]
    L=q["stud_span_mm"]+q["span_allowance_mm"]
    left=L/2+q["housing_x_mm"];right=L/2-q["housing_x_mm"]
    K=left*right/L;share=q["roll_share_bound"]
    rows=[]
    for name,a,b in station_coefficients(q):
        net=linear_envelope(1,0,a,b,F,h,q)
        # Both unilateral toe choices. A beam has linear moment between loads;
        # its maxima occur at the bolt/toe stations, checked explicitly here.
        d=q["minimum_contact_lever_mm"]
        moments={
          "bolt_right_toe":linear_envelope(K,left/L*share,a,b,F,h,q),
          "bolt_left_toe":linear_envelope(K,right/L*share,a,b,F,h,q),
          "right_toe":linear_envelope(left*(right-d)/L,(right-d)/L*share,a,b,F,h,q),
          "left_toe":linear_envelope(right*(left-d)/L,(left-d)/L*share,a,b,F,h,q)}
        fpe=max(linear_envelope(v/L,share/L,a,b,q["package_force_N"],q["package_height_mm"],q) for v in [left,right])
        rows.append({"station":name,"normal_coefficients":[a,b],"net_normal_max_N":net,
          "correlated_screw_tension_bound_N":linear_envelope(1,share/d,a,b,F,h,q),
          "moment_bounds_Nmm":moments,"max_M_Nmm":max(moments.values()),
          "FPE_frame_tension_bound_N":fpe})
    roll=F*math.hypot(h,q["CG_half_x_mm"]+abs(q["housing_x_mm"]))+C
    toe=share*roll/q["minimum_contact_lever_mm"]
    netmax=max(r["net_normal_max_N"] for r in rows)
    # Conservative triangle bound retained in stress and qualification inputs.
    screw=toe+netmax;M=max(r["max_M_Nmm"] for r in rows)
    t=q["plate_thickness_mm"]-q["thickness_tolerance_mm"];b=q["net_strip_width_mm"]
    I=b*t**3/12;Z=b*t*t/6;V=q["M4_joint_shear_demand_N"]
    sigma=q["bending_stress_allowance"]*M/Z+V/(b*t)
    tau=(1.5*screw+V)/(b*t)
    vm=math.hypot(sigma,math.sqrt(3)*tau)
    delta=M*L*L/(8*q["E_MPa"]*I)
    massupper=q["plate_max_width_mm"]*q["plate_length_mm"]*q["plate_thickness_mm"]*q["density_kg_mm3"]
    Llong=q["station_pitch_mm"]+q["span_allowance_mm"]
    Ilong=q["spine_width_mm"]*t**3/12
    selfload=massupper*q["gravity_plus_handling_factor"]*q["gravity_m_s2"]
    long_delta=5*selfload*Llong**3/(384*q["E_MPa"]*Ilong)
    long_sigma=q["bending_stress_allowance"]*selfload*Llong/8/(q["spine_width_mm"]*t*t/6)
    seatA=math.pi/4*(q["head_seat_effective_OD_min_mm"]**2-q["housing_bore_max_mm"]**2)
    seatP=q["M4_joint_tension_demand_N"]/seatA
    cone=(q["countersink_mouth_max_mm"]-q["housing_bore_min_mm"])/(2*math.tan(math.radians(q["countersink_angle_min_deg"]/2)))
    straight=t-cone-q["upper_bore_deburr_max_mm"]
    punchA=math.pi*q["housing_bore_min_mm"]*q["straight_ligament_accept_min_mm"]
    corner_edge=7.5-.15 # Stud edge7.5, position allowance0.15.
    tearA=2*(corner_edge-3.9/2)*(t-.8)
    frame_checks={
      "transverse_frame_combined":{"VM_MPa":vm,"yield_factor":q["Sy_MPa"]/vm},
      "spine_self_load":{"VM_MPa":long_sigma,"yield_factor":q["Sy_MPa"]/long_sigma},
      "external_cone_punching":{"VM_MPa":math.sqrt(3)*q["M4_joint_tension_demand_N"]/punchA,"yield_factor":q["Sy_MPa"]*punchA/(math.sqrt(3)*q["M4_joint_tension_demand_N"])},
      "stud_hole_bearing_factor2":{"VM_MPa":2*q["FPE_shear_qualification_N"]/(2.4*t),"yield_factor":q["Sy_MPa"]*2.4*t/(2*q["FPE_shear_qualification_N"])},
      "stud_edge_tearout":{"VM_MPa":math.sqrt(3)*q["FPE_shear_qualification_N"]/tearA,"yield_factor":q["Sy_MPa"]*tearA/(math.sqrt(3)*q["FPE_shear_qualification_N"])}}
    seat_ratio=q["Sy_MPa"]/(q["contact_pressure_factor_sensitivity"]*seatP)
    jx=q["housing_x_mm"];cy=sum(q["housing_y_mm"])/2-q["body_center_y_mm"]
    radius=math.hypot(q["CG_half_x_mm"]+abs(jx),q["CG_half_y_mm"]+abs(cy))
    shear=F/2+(C+F*radius)/q["station_pitch_mm"]
    projection_min=q["screw_length_mm"]-q["screw_length_assumed_tolerance_mm"]-(q["plate_thickness_mm"]+q["thickness_tolerance_mm"])+q["head_recess_min_mm"]
    projection_max=q["screw_length_mm"]+q["screw_length_assumed_tolerance_mm"]-t+q["head_recess_max_mm"]
    return {"status":"PRELIMINARY_FRAME_SCREEN_PASS_CONTACT_HOLD_NO_ASSEMBLY_RATING","inputs":q,
      "loads":{"device_derived_N":1.8*4*9.81+50,"package_derived_N":2.2*4*9.81+50,
        "roll_bound_Nmm":roll,"toe_compression_bound_N":toe,"M4_tension_triangle_bound_N":screw,
        "M4_shear_bound_N":shear,"stations":rows,"FPE_max_tension_N":max(r["FPE_frame_tension_bound_N"] for r in rows)},
      "plate":{"minimum_thickness_mm":t,"net_width_mm":b,"span_mm":L,"I_mm4":I,"Z_mm3":Z,
        "max_bending_moment_Nmm":M,"normal_stress_MPa":sigma,"shear_stress_MPa":tau,
        "frame_VM_MPa":vm,"minimum_frame_yield_factor":min(v["yield_factor"] for v in frame_checks.values()),
        "frame_target_met":all(v["yield_factor"]>=3 for v in frame_checks.values()),
        "screen_target_met":False,"all_contact_checks_factor3":False,"contact_status":"HOLD",
        "minimum_screen_yield_factor":min(q["Sy_MPa"]/vm,seat_ratio),"frame_checks":frame_checks,
        "uncut_rectangle_mass_upper_kg":massupper,"spine_self_load_4g_N":selfload,
        "curvature_deflection_bound_mm":delta,"service_deflection_with_allowance_mm":delta*q["deflection_allowance"],
        "local_proof_deflection_bound_mm":delta*q["deflection_allowance"]*q["proof_multiplier"],
        "longitudinal_self_deflection_mm":long_delta,
        "combined_proof_deflection_bound_mm":(delta*q["deflection_allowance"]+long_delta)*q["proof_multiplier"]},
      "contacts":{"status":"HOLD_REQUIRES_JOINT_QUALIFICATION","seat_projected_area_mm2":seatA,
        "seat_average_external_bearing_MPa":seatP,"seat_average_yield_ratio":q["Sy_MPa"]/seatP,
        "seat_pressure_factor3_MPa":q["contact_pressure_factor_sensitivity"]*seatP,
        "seat_pressure_factor3_yield_ratio":seat_ratio,
        "toe_patch_pressure_sensitivities_MPa":{k:toe/A for k,A in q["verified_toe_patch_areas_mm2"].items()},
        "toe_note":"Verified patches are geometric witnesses, not measured loaded areas or a chassis strength specification. No toe-contact safety factor is assigned.",
        "preload_note":"External-only screens. Manufacturer torque does not define preload or establish seat/head/chassis/FPE capacity."},
      "screw_fit":{"cone_depth_max_mm":cone,"straight_ligament_min_stack_mm":straight,
        "straight_ligament_accept_min_mm":q["straight_ligament_accept_min_mm"],
        "nominal_projection_mm":q["screw_length_mm"]-q["plate_thickness_mm"]+.05,
        "assumed_projection_min_mm":projection_min,"assumed_projection_max_mm":projection_max,
        "manufacturer_max_penetration_mm":q["vendor_max_penetration_mm"],
        "manufacturer_side_torque_Nm":[v*.0980665 for v in q["vendor_side_torque_kgf_cm"]],
        "rear_thread_status":"UNMODELED_IN_STEP_PHYSICAL_CONFIRMATION_REQUIRED"},
      "thermal":{"status":"SIDE_ORIENTATION_DERATING_AND_ENCLOSURE_TEST_REQUIRED_NO_PANEL_CREDIT",
        "12V_typical_loss_W":1500*(1/.89-1),"24V_typical_loss_W":1608*(1/.91-1)}}


def audit():
    path=PROJECT/"params.json";p=json.loads(path.read_text(encoding="utf-8-sig"))
    expected={"plate_width":72,"plate_length":316.8,"plate_center_y":-142.2,
      "plate_thickness":6,"plate_thickness_tolerance":.05,"spine_width":45,"tab_length":44,
      "tab_stations_y":[-257.8,-5.8],"plate_fan_end_y":-300.6,"plate_terminal_end_y":16.2,
      "corner_radius":4,"edge_break":.4,"bore_deburr":.1,
      "housing_points":[[2.3,-5.8],[2.3,-257.8]],"housing_clearance_diameter":4.5,
      "countersink_diameter_reference":8.1,"countersink_angle_deg":90,"screw_pitch":.7,
      "screw_length_overall":10,"screw_head_diameter":8,"screw_head_recess_nominal":.05,
      "screw_projection_accept_min":3.75,"screw_projection_accept_max":4.35,
      "manufacturer_max_penetration":5,"manufacturer_side_torque_kgf_cm":[7,10],
      "stud_pitch_x":57,"stud_pitch_y":252,"stud_pattern_center_x":0,
      "stud_pattern_center_y":-131.8,"stud_pattern_rotation_deg":0,
      "stud_clearance_diameter":3.8,"stud_projection":12,"case_width_side":41,"case_height_side":85}
    bad=[{"key":k,"expected":v,"actual":p.get(k)} for k,v in expected.items() if p.get(k)!=v]
    files={}
    for name in ["params.json","exports/cad_build_metadata.json","references/geometry/side_reference_and_contacts.json","datasheets/NSP-1600-spec_USER.pdf"]:
        f=PROJECT/name
        if f.exists():files[name]={"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size}
    return {"status":"matched" if not bad else "MISMATCH","mismatches":bad,"checked":expected,"files":files,
      "params_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--write",action="store_true");args=ap.parse_args()
    r=calculate();r["input_audit"]=audit();r["params_sha256"]=r["input_audit"]["params_sha256"]
    assert not r["input_audit"]["mismatches"],"CAD parameters changed; review calculations"
    assert r["plate"]["frame_target_met"]
    assert r["contacts"]["seat_pressure_factor3_yield_ratio"]<3 and not r["plate"]["screen_target_met"]
    assert r["loads"]["M4_tension_triangle_bound_N"]<=Q["M4_joint_tension_demand_N"]
    assert r["loads"]["M4_shear_bound_N"]<=Q["M4_joint_shear_demand_N"]
    assert r["screw_fit"]["straight_ligament_min_stack_mm"]>=3.9
    assert r["screw_fit"]["assumed_projection_max_mm"]<5
    assert r["plate"]["local_proof_deflection_bound_mm"]<.3
    assert r["plate"]["combined_proof_deflection_bound_mm"]<.4
    # Independent statics check for each unilateral contact side.
    L=57.3;xb=L/2+2.3
    for side in [-1,1]:
        toe=xb+side*15;N=100.;R=500.;U=N+R
        RA=(-U*(L-xb)+R*(L-toe))/L;RB=(-U*xb+R*toe)/L
        assert abs(RA+RB-(-U+R))<1e-9
        assert abs(RB*L-(-U*xb+R*toe))<1e-9
    r["calculation_self_checks"]={"status":"passed","scope":"Arithmetic, station equilibrium, CAD parameter consistency and explicit retention of contact HOLD; not physical validation"}
    meta=PROJECT/"exports/cad_build_metadata.json"
    if meta.exists():
        m=json.loads(meta.read_text(encoding="utf-8"));r["CAD_plate_mass_kg"]=m["plate_mass_kg_at_2700_kg_m3"]
        assert abs(r["CAD_plate_mass_kg"]-m["plate_volume_mm3"]*2.7e-6)<1e-9
    if args.write:
        HERE.mkdir(parents=True,exist_ok=True)
        (HERE/"engineering_results.json").write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"frame_factor":r["plate"]["minimum_frame_yield_factor"],
      "seat_factor3_ratio":r["contacts"]["seat_pressure_factor3_yield_ratio"],"params_sha256":r["params_sha256"]},indent=2))


if __name__=="__main__":main()
