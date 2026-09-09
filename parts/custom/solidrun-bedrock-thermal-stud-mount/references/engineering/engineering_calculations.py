"""Bedrock T1 mechanical/thermal screening. Standard-library Python only.

Run --write to regenerate engineering_results.json and engineering_checks.md.
Geometry/temperature predictions are preliminary, not tests or FEA.
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
    "plate_x_mm":166.0,"plate_y_mm":184.0,"plate_t_mm":5.10,
    "plate_t_tolerance_mm":0.05,"corner_radius_mm":8.0,
    "thermal_field_x_mm":126.0,"thermal_field_y_mm":156.0,
    "thermal_field_radius_mm":5.0,"pocket_depth_mm":0.05,
    "pocket_depth_tolerance_mm":0.01,"assembled_gap_limit_mm":0.10,
    "thermal_area_screen_mm2":19000.0,
    "top_land_OD_mm":8.0,"top_land_OD_min_mm":7.9,
    "bottom_land_OD_mm":10.0,
    "housing_points":[[-60,-70],[60,-70],[0,-40],[0,30],[-50,70],[50,70]],
    "stud_points":[[-76,-82],[76,-82],[-76,82],[76,82]],
    "housing_hole_min_mm":4.4,"housing_hole_max_mm":4.6,
    "stud_hole_max_mm":3.9,"countersink_mouth_max_mm":8.2,
    "countersink_angle_min_deg":89.0,"upper_bore_deburr_max_mm":0.10,
    "straight_throat_accept_min_mm":3.0,
    "effective_head_seat_OD_accept_min_mm":7.6,
    "screw_length_mm":8.0,"screw_length_assumed_tolerance_mm":0.2,
    "head_recess_min_mm":0.0,"head_recess_max_mm":0.1,
    "projection_accept_min_mm":2.85,"projection_accept_max_mm":3.0,
    "full_engagement_accept_min_mm":2.0,"source_entry_cone_mm":0.584,
    "source_full_diameter_end_mm":3.5,"source_drill_tip_mm":4.501034,
    "full_diameter_clearance_screen_mm":0.5,
    "thread_shear_diameter_surrogate_mm":3.3,"M4_tensile_area_mm2":8.78,
    "E_MPa":70000.0,"plate_yield_MPa":240.0,"yield_factor_target":3.0,
    "plate_k_assumption_W_mK":150.0,"panel_k_assumption_W_mK":150.0,
    "TIM_k_typical_W_mK":0.67,"TIM_k_sensitivity_W_mK":0.42,
    "TIM_density_typical_g_cc":2.1,"aluminum_density_kg_mm3":2.7e-6,
    "device_mass_allowance_kg":1.5,"package_mass_allowance_kg":2.1,
    "gravity_m_s2":9.81,"inertial_g":3.0,"cable_force_N":20.0,
    "device_handling_force_N":80.0,"package_handling_force_N":110.0,
    "free_couple_Nmm":1000.0,"device_load_height_mm":51.0,
    "package_load_height_mm":60.0,"load_plan_half_x_mm":65.0,
    "load_plan_half_y_mm":80.0,"local_housing_force_N":75.0,
    "local_surrogate_proof_force_N":112.5,
    "FPE_tension_qualification_demand_N":200.0,
    "FPE_shear_qualification_demand_N":100.0,
    "local_strip_net_width_mm":28.0,"global_strip_net_width_mm":100.0,
    "support_span_allowance_mm":0.3,"selected_bending_factor":1.5,
    "panel_reference_x_mm":200.0,"panel_reference_y_mm":220.0,
    "panel_reference_t_mm":6.0,
    "thermal_powers_W":[10.0,30.0,60.0],
}


def inverse3(a):
    m=[list(a[i])+[float(i==j) for j in range(3)] for i in range(3)]
    for k in range(3):
        pivot=max(range(k,3),key=lambda i:abs(m[i][k]))
        m[k],m[pivot]=m[pivot],m[k]
        if abs(m[k][k])<1e-12:
            raise ValueError("Mounting group does not restrain normal force and both moments")
        v=m[k][k];m[k]=[x/v for x in m[k]]
        for i in range(3):
            if i!=k:
                v=m[i][k];m[i]=[m[i][j]-v*m[k][j] for j in range(6)]
    return [r[3:] for r in m]


def group_screen(points, force, couple, h, rx, ry):
    """Rigid elastic bolt group; exact tension extrema over F/C balls and XY box.

    N=B(B'B)^-1 [Fz,-My,Mx]. No preload, joint compliance or prying.
    Shear uses a conservative direct-plus-torsion triangle inequality.
    """
    B=[[1.0,x,y] for x,y in points]
    A=[[sum(b[i]*b[j] for b in B) for j in range(3)] for i in range(3)]
    inv=inverse3(A)
    n=len(points);cx=sum(p[0] for p in points)/n;cy=sum(p[1] for p in points)/n
    J=sum((x-cx)**2+(y-cy)**2 for x,y in points)
    rg=math.hypot(rx+abs(cx),ry+abs(cy))
    rows=[]
    for p,b in zip(points,B):
        c=[sum(b[k]*inv[k][j] for k in range(3)) for j in range(3)]
        fz=abs(c[0])+rx*abs(c[1])+ry*abs(c[2])
        tension=force*math.sqrt((h*c[1])**2+(h*c[2])**2+fz*fz)+couple*math.hypot(c[1],c[2])
        radius=math.hypot(p[0]-cx,p[1]-cy)
        shear=force/n+(couple+force*rg)*radius/J
        rows.append({"point_mm":p,"max_tension_N":tension,"max_shear_N":shear,
                     "elastic_normal_wrench_coefficients":c})
    return {"points":rows,"centroid_mm":[cx,cy],"polar_sum_mm2":J,
            "max_tension_N":max(r["max_tension_N"] for r in rows),
            "max_shear_N":max(r["max_shear_N"] for r in rows)}


def thermal_stack(q, area_mm2, gap_mm, k_tim):
    """1-D bulk conduction only. Contacts, coating, spreading and air are omitted."""
    A=area_mm2*1e-6
    tim_each=gap_mm*1e-3/(k_tim*A)
    # Use the thicker full plate as the conservative through-thickness length.
    plate=q["plate_t_mm"]*1e-3/(q["plate_k_assumption_W_mK"]*A)
    panel=q["panel_reference_t_mm"]*1e-3/(q["panel_k_assumption_W_mK"]*A)
    total=2*tim_each+plate+panel
    return {"area_mm2":area_mm2,"gap_each_mm":gap_mm,"k_TIM_W_mK":k_tim,
            "R_each_TIM_K_W":tim_each,"R_plate_K_W":plate,"R_panel_K_W":panel,
            "R_bulk_stack_K_W":total,
            "delta_T_bulk_K":{str(int(P)):P*total for P in q["thermal_powers_W"]}}


def calculate(q=Q):
    E,Sy=q["E_MPa"],q["plate_yield_MPa"]
    t_land=q["plate_t_mm"]-q["plate_t_tolerance_mm"]
    t_core=t_land-2*(q["pocket_depth_mm"]+q["pocket_depth_tolerance_mm"])
    device_F=(q["inertial_g"]+1)*q["device_mass_allowance_kg"]*q["gravity_m_s2"]+q["cable_force_N"]
    package_F=(q["inertial_g"]+1)*q["package_mass_allowance_kg"]*q["gravity_m_s2"]+q["cable_force_N"]
    args=[q["free_couple_Nmm"],q["device_load_height_mm"],q["load_plan_half_x_mm"],q["load_plan_half_y_mm"]]
    housing=group_screen(q["housing_points"],q["device_handling_force_N"],*args)
    studs=group_screen(q["stud_points"],q["package_handling_force_N"],q["free_couple_Nmm"],q["package_load_height_mm"],q["load_plan_half_x_mm"],q["load_plan_half_y_mm"])
    housing2=group_screen(q["housing_points"],q["device_handling_force_N"],2000,*args[1:])
    # Full continuous plate: deliberately long diagonal span. Effective widths
    # are engineering idealizations, not exact 2-D plate or contact solutions.
    sx=max(x for x,y in q["stud_points"])-min(x for x,y in q["stud_points"])
    sy=max(y for x,y in q["stud_points"])-min(y for x,y in q["stud_points"])
    L=math.hypot(sx,sy)+q["support_span_allowance_mm"]
    P=q["local_housing_force_N"];b=q["local_strip_net_width_mm"]
    I=b*t_core**3/12;Z=b*t_core*t_core/6
    sigma=q["selected_bending_factor"]*P*L/(4*Z)+P/(b*t_core)
    tau=3*P/(b*t_core)
    vm=math.sqrt(sigma*sigma+3*tau*tau)
    local_delta=P*L**3/(48*E*I)
    bg=q["global_strip_net_width_mm"];Zg=bg*t_core*t_core/6
    radius=math.sqrt(q["load_plan_half_x_mm"]**2+q["load_plan_half_y_mm"]**2+q["device_load_height_mm"]**2)
    M=q["device_handling_force_N"]*L/4+q["free_couple_Nmm"]+q["device_handling_force_N"]*radius
    global_vm=math.sqrt((q["selected_bending_factor"]*M/Zg)**2+3*(3*q["device_handling_force_N"]/(bg*t_core))**2)
    # Stress factors are chosen screening allowances; no sourced notch factor.
    cs_depth=(q["countersink_mouth_max_mm"]-q["housing_hole_min_mm"])/(2*math.tan(math.radians(q["countersink_angle_min_deg"]/2)))
    straight=t_land-cs_depth-q["upper_bore_deburr_max_mm"]
    punch_area=math.pi*q["housing_hole_min_mm"]*q["straight_throat_accept_min_mm"]
    seat_area=math.pi/4*(q["effective_head_seat_OD_accept_min_mm"]**2-q["housing_hole_max_mm"]**2)
    top_open=q["housing_hole_max_mm"]+2*q["upper_bore_deburr_max_mm"]
    land_area=math.pi/4*(q["top_land_OD_min_mm"]**2-top_open**2)
    edge=q["plate_x_mm"]/2-max(abs(x) for x,y in q["stud_points"])-.15
    tear_area=2*(edge-q["stud_hole_max_mm"]/2)*t_land
    V=q["FPE_shear_qualification_demand_N"]
    checks={
        "local_plate_strip":{"VM_MPa":vm,"yield_factor":Sy/vm},
        "whole_plate_strip":{"VM_MPa":global_vm,"yield_factor":Sy/global_vm},
        "countersink_punching":{"shear_MPa":P/punch_area,"yield_factor":Sy/(math.sqrt(3)*P/punch_area)},
        "countersink_average_bearing_factor3":{"VM_MPa":3*P/seat_area,"yield_factor":Sy/(3*P/seat_area)},
        "plate_stud_bearing_factor2":{"VM_MPa":2*V/(2.4*t_land),"yield_factor":Sy/(2*V/(2.4*t_land))},
        "plate_stud_tearout":{"shear_MPa":V/tear_area,"yield_factor":Sy/(math.sqrt(3)*V/tear_area)},
    }
    project_min=q["screw_length_mm"]-q["screw_length_assumed_tolerance_mm"]-(q["plate_t_mm"]+q["plate_t_tolerance_mm"])+q["head_recess_min_mm"]
    project_max=q["screw_length_mm"]+q["screw_length_assumed_tolerance_mm"]-t_land+q["head_recess_max_mm"]
    thread_area=.25*math.pi*q["thread_shear_diameter_surrogate_mm"]*q["full_engagement_accept_min_mm"]
    field=q["thermal_field_x_mm"]*q["thermal_field_y_mm"]-(4-math.pi)*q["thermal_field_radius_mm"]**2
    field_min=field-6*math.pi/4*q["bottom_land_OD_mm"]**2
    kt=q["TIM_k_typical_W_mK"];gmax=q["assembled_gap_limit_mm"]
    stacks=[thermal_stack(q,q["thermal_area_screen_mm2"]*fraction,gap,k)
            for fraction,gap,k in [(1,q["pocket_depth_mm"],kt),(1,gmax,kt),(.25,gmax,kt),(.05,gmax,kt),(1,gmax,q["TIM_k_sensitivity_W_mK"])]]
    # Approximate thin circular-sheet lateral path, deliberately stated as a
    # sensitivity, not an additional verified total resistance or exact bound.
    r_large=math.sqrt(q["thermal_area_screen_mm2"]*1e-6/math.pi)
    r_small=math.sqrt(q["thermal_area_screen_mm2"]*.05*1e-6/math.pi)
    Rspread=math.log(r_large/r_small)/(2*math.pi*q["plate_k_assumption_W_mK"]*(t_core*1e-3))
    panel_A=q["panel_reference_x_mm"]*q["panel_reference_y_mm"]*1e-6
    air=[{"h_assumed_W_m2K":h,"one_face_area_m2":panel_A,"R_air_K_W":1/(h*panel_A),
          "delta_T_panel_air_K":{str(int(P)):P/(h*panel_A) for P in q["thermal_powers_W"]}}
         for h in [5,10,25,50]]
    return {"status":"PRELIMINARY_ANALYTICAL_SCREEN_NO_ASSEMBLY_OR_COOLING_RATING","inputs":q,
        "loads":{"derived_device_N":device_F,"derived_package_N":package_F,
                 "housing":housing,"FPE":studs,"housing_2Nm_sensitivity":housing2,
                 "housing_local_demand_covers_group":P>=max(housing["max_tension_N"],housing["max_shear_N"])},
        "plate":{"minimum_land_t_mm":t_land,"minimum_core_t_mm":t_core,"diagonal_span_mm":L,
                 "local_beam_I_mm4":I,"local_free_bending_deflection_mm":local_delta,
                 "local_proof_free_bending_deflection_mm":local_delta*q["local_surrogate_proof_force_N"]/P,
                 "whole_plate_moment_bound_Nmm":M,
                 "uncut_plate_mass_upper_bound_kg":q["plate_x_mm"]*q["plate_y_mm"]*q["plate_t_mm"]*q["aluminum_density_kg_mm3"]},
        "countersink":{"depth_screen_max_mm":cs_depth,"straight_throat_stack_min_mm":straight,
                       "straight_throat_used_mm":q["straight_throat_accept_min_mm"],
                       "seat_projected_area_mm2":seat_area,"punching_area_mm2":punch_area,
                       "hard_land_area_min_screen_mm2":land_area,
                       "hard_land_bearing_MPa_per100N":100/land_area},
        "screw_fit":{"nominal_projection_mm":q["screw_length_mm"]-q["plate_t_mm"]+.05,
                     "unscreened_tolerance_projection_min_mm":project_min,
                     "unscreened_tolerance_projection_max_mm":project_max,
                     "additional_entry_phase_plus_tip_allowance_min_projection_mm":q["projection_accept_min_mm"]-q["source_entry_cone_mm"]-q["full_engagement_accept_min_mm"],
                     "additional_entry_phase_plus_tip_allowance_max_projection_mm":q["projection_accept_max_mm"]-q["source_entry_cone_mm"]-q["full_engagement_accept_min_mm"],
                     "full_diameter_axial_clearance_at_max_projection_mm":q["source_full_diameter_end_mm"]-q["projection_accept_max_mm"],
                     "drill_tip_axial_difference_at_max_projection_mm":q["source_drill_tip_mm"]-q["projection_accept_max_mm"]},
        "unrated_joints":{"M4_external_shank_VM_MPa":2*P/q["M4_tensile_area_mm2"],
                          "female_thread_shear_surrogate_area_mm2":thread_area,
                          "female_required_yield_at_factor3_zero_preload_MPa":3*math.sqrt(3)*P/thread_area,
                          "female_required_yield_addition_per100N_preload_MPa":3*math.sqrt(3)*100/thread_area},
        "plate_checks":checks,"minimum_plate_screen_yield_factor":min(c["yield_factor"] for c in checks.values()),
        "plate_target_met":all(c["yield_factor"]>=q["yield_factor_target"] for c in checks.values()),
        "thermal":{"rounded_field_gross_area_mm2":field,"field_area_conservative_before_coverage_mm2":field_min,
                   "screen_area_fraction_of_conservative_field":q["thermal_area_screen_mm2"]/field_min,
                   "nominal_gap_volume_each_interface_cc":field_min*q["pocket_depth_mm"]/1000,
                   "nominal_filled_volume_mass_each_interface_g":field_min*q["pocket_depth_mm"]/1000*q["TIM_density_typical_g_cc"],
                   "bulk_only_cases":stacks,"radial_spreading_sensitivity_K_W":Rspread,
                   "radial_spreading_delta_T_at60W_K":60*Rspread,
                   "air_boundary_sensitivity":air,
                   "h_needed_for_20K_panel_air_budget_W_m2K":{str(int(P)):P/(panel_A*20) for P in q["thermal_powers_W"]},
                   "full_130x160_face_force_at10psi_N":68947.5729*.0208,
                   "full_130x160_face_force_at40psi_N":4*68947.5729*.0208,
                   "CTE_10ppm_per_K_50K_160mm_free_movement_mm":10e-6*50*160}}


def audit_params():
    path=PROJECT/"params.json"
    if not path.exists():
        return {"status":"missing","mismatches":[]}
    p=json.loads(path.read_text(encoding="utf-8-sig"))
    expected={"plate_width":166,"plate_length":184,"plate_thickness":5.1,
              "plate_thickness_tolerance":.05,"housing_points":Q["housing_points"],
              "housing_clearance_diameter":4.5,"countersink_diameter_reference":8.1,
              "bore_deburr":.1,"screw_length_overall":8,"screw_pitch":.7,
              "screw_projection_accept_min":2.85,"screw_projection_accept_max":3.0,
              "full_thread_engagement_accept_min":2,"thread_entry_depth_source":.584,
              "full_diameter_blind_limit_source":3.5,"thermal_field_width":126,
              "thermal_field_length":156,"thermal_field_corner_radius":5,
              "thermal_pocket_depth":.05,"thermal_pocket_depth_tolerance":.01,
              "thermal_gap_accept_max":.1,"tile_contact_land_diameter":8,
              "underside_countersink_land_diameter":10,"stud_pitch_x":152,
              "stud_pitch_y":164,"stud_pattern_rotation_deg":0,
              "stud_pattern_center_x":0,"stud_pattern_center_y":0,
              "stud_clearance_diameter":3.8,"panel_reference_thickness":6}
    bad=[{"key":k,"expected":v,"actual":p.get(k)} for k,v in expected.items() if p.get(k)!=v]
    return {"status":"matched" if not bad else "MISMATCH","mismatches":bad,
            "checked":expected,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def report(r):
    q=Q;p=r["plate"];t=r["thermal"];c=r["countersink"];f=r["screw_fit"]
    h=r["loads"]["housing"];s=r["loads"]["FPE"];j=r["unrated_joints"]
    metal_rows="\n".join(f"| {name.replace('_',' ')} | {v['yield_factor']:.2f} |" for name,v in r["plate_checks"].items())
    thermal_rows="\n".join(f"| {v['area_mm2']:.0f} | {v['gap_each_mm']:.2f} | {v['k_TIM_W_mK']:.2f} | {v['R_bulk_stack_K_W']:.4f} | {v['delta_T_bulk_K']['10']:.2f} | {v['delta_T_bulk_K']['30']:.2f} | {v['delta_T_bulk_K']['60']:.2f} |" for v in t["bulk_only_cases"])
    air_rows="\n".join(f"| {v['h_assumed_W_m2K']} | {v['R_air_K_W']:.3f} | {v['delta_T_panel_air_K']['10']:.1f} | {v['delta_T_panel_air_K']['30']:.1f} | {v['delta_T_panel_air_K']['60']:.1f} |" for v in t["air_boundary_sensitivity"])
    return f'''# Bedrock thermal stud mount T1 — engineering screen

This is a preliminary plate and thermal-interface design. The analytical screens meet the selected plate yield target, but **the assembled mounting and cooling system is not rated**. No device mass, mounting-thread capacity, FPE bond capacity, thermal contact resistance, airflow coefficient or TEC capacity was measured. No FEA or physical test was performed. The existing Bedrock mount notes supplied leads only; their depth, torque, mass, material and thermal claims were not adopted.

## Configuration and datums

The new geometry audit separates the superimposed Tile, 30 W and 60 W bodies in the supplied STEP. T1 represents a Tile body plus a derived single opposite fin bank. That CAD construction does not prove that the physical bank is interchangeable or that its internal thermal joint performs as modeled. The manufacturer/file's “60 W” name is not a rating of this derived configuration, and this calculation gives the fin bank no cooling credit.

The Tile mating face is Z=0, with the computer extending toward +Z. Six measured axes are (−60,−70), (60,−70), (0,−40), (0,30), (−50,70), (50,70) mm. Fresh face area is approximately 20,410.10 mm², bounded by X±64.486/Y±79.5 mm. The adapter is 166×184×5.10 mm, with four FPE stud axes X±76/Y±82 mm. The 200×220×6 mm panel is a reference interface, not a confirmed complete enclosure or heat sink.

Both adapter faces have 126×156 mm, R5 TIM fields recessed 0.05±0.01 mm. Six nominal Ø8 upper islands bear on the Tile near its mounting holes. Six Ø10 lower lands retain the countersink seats and provide hard contact against the panel. The surrounding metal rim also seats. Two 1 mm escape grooves on each face, at the same depth and Y±20, run toward +X outside the field. They avoid a sealed grease cavity and give air/excess material an escape path. No thermal area outside the Tile footprint, including those grooves, is credited.

## Construction and TIM selection

The selected construction is a machined 6061 plate with **metal stops defining the grip and a thin, nonstructural grease film**. This keeps the screw clamp path out of a compressible pad. It does not eliminate the need to qualify bolt preload, actual contact and surface flatness. No structural retention or sustained clamp-force credit is assigned to the grease.

The selected TIM is Dow 340, available as McMaster 10405K83. Dow classifies it as a noncuring, thin-bond-line TIM for gaps below 100 µm. Its English manufacturer TDS gives typical k=0.67 W/(m·K); the McMaster listing gives 0.68. The model uses 0.67. An older regional Dow document gives a lower value equivalent to approximately 0.42, so that value is retained as a sensitivity. These are typical inputs, not lot-certified minimum properties. Confirm the current data sheet for the received product.

A full 130×160 mm pad at only 10 psi would require approximately {t['full_130x160_face_force_at10psi_N']:.0f} N total compression; 40 psi would require {t['full_130x160_face_force_at40psi_N']:.0f} N. Therefore the published grease impedance at 40 psi is **not** used as this assembly's thermal resistance, and neither Shore hardness nor a catalog low-pressure statement defines the needed preload. A thick full-face pad was rejected because its force/deflection and long-term compression would load unverified shallow threads. A fixed-gap gel such as Laird Tgel 600 is an alternative if the surfaces cannot meet the Dow 340 thin-gap requirement, but it requires a deliberate TIM/drawing revision and new thermal qualification.

Machine both faces in balanced setups from suitable stock, control free-state flatness, deburr, clean and inspect unclamped. The 0.4 mm edge break belongs only on exposed outer rim edges. Keep the 0.05 mm TIM steps and island perimeters burr-free while preserving their depth and minimum land diameter; a generic 0.4 mm chamfer there would destroy the functional feature. Mask the active TIM fields and hard seating lands from added thick coatings; do not remove the computer's original finish by default. Existing device/panel finishes add unknown contact resistance. The nominal 0.05 mm relief is not proof of a 0.05 mm bond line: with a 0.06 mm maximum cut, less than 0.04 mm remains for combined mating-face departure before the 0.10 mm limit is exceeded. All intended stops must seat without rocking or forcing a bowed part flat through the device screws. Separate drawing flatness/parallelism limits do not by themselves guarantee the assembled gap against an unmeasured Tile or panel.

The calculated cavity estimate is about {t['nominal_gap_volume_each_interface_cc']:.2f} mL per interface, approximately {t['nominal_filled_volume_mass_each_interface_g']:.2f} g using the English TDS density. This is a geometric estimate, **not a prescribed dispense dose**. Establish the dose and pattern on a representative witness assembly, close slowly, allow air/excess to escape and check continuous transfer without persistent dry patches. Do not use bolt torque to force out an excessive charge. Verify actual gaps below 0.10 mm on both interfaces in the installed orientation, under normal cable/gravity load and after warm operation. Renew the grease after separation and inspect for migration or bleed during cycling.

## Mechanical loads and load path

Device mass allowance is 1.5 kg and complete package allowance is 2.1 kg, both unverified. The uncut plate alone is at most {p['uncut_plate_mass_upper_bound_kg']:.4f} kg at 2,700 kg/m³. Weigh the actual configuration; do not derive device mass by assigning aluminum density to the imported assembly.

With g=9.81 m/s², 3g incidental inertia plus 1g gravity and 20 N cable force:

- Device force: 1.5×4×9.81+20={r['loads']['derived_device_N']:.2f} N, rounded to **80 N resultant**.
- Package force: 2.1×4×9.81+20={r['loads']['derived_package_N']:.2f} N, rounded to **110 N resultant**.
- Add an independent **1 N·m free couple**, motivated by 20 N at a 50 mm lever.
- Bound the device load height by 51 mm, package height by 60 mm, and the plan position anywhere inside X±65/Y±80 mm. This is deliberately more conservative than assuming a centered CG.

Each force and couple can act in any direction within its resultant bound; these are not per-axis simultaneous amplitudes. The intended application is stationary indoor equipment in a TEC-cooled enclosure. No vehicle, airborne, overhead, vibration or shock-spectrum suitability is claimed.

The compression path is Tile→upper metal islands/rim→adapter→lower metal lands/rim→main panel. Uplift and in-plane loads pass through the six M4 screw joints, plate and four retained FPE stud/nut joints. Friction is not credited for retention. Hole geometry provides positive shear restraint after clearance is taken up. The separated fastener groups restrain all translations and rotations when correctly seated. Neither connectors nor fins are clamped.

## Bolt-group calculation and unrated joints

For the arbitrary six-point pattern, each row of B is [1,x,y]. The elastic normal-force vector is N=B(BᵀB)⁻¹[Fz,−My,Mx]ᵀ. This preserves force and both moment equilibria and accounts for the group's Y-centroid at −1.6667 mm. The source calculates the exact normal extrema over the independent force/couple balls and the stated load-position rectangle. In-plane demand uses direct F/n plus a conservative torsion term (C+F r_CG) r_i/J about the group centroid.

- Maximum M4 elastic demand: **{h['max_tension_N']:.2f} N tension / {h['max_shear_N']:.2f} N shear**. Use a local **75 N tension and 75 N shear** plate/fastener screen.
- Maximum FPE elastic demand: **{s['max_tension_N']:.2f} N tension / {s['max_shear_N']:.2f} N shear**. Request supplier or representative-joint qualification for **200 N tension with 100 N shear per stud**. These values are demands, not FPE allowable loads.
- A 2 N·m cable-couple sensitivity raises M4 tension to {r['loads']['housing_2Nm_sensitivity']['max_tension_N']:.2f} N, still within the 75 N local screen. Confirm actual plug/cable levers.

These are external-load calculations. Preload, prying, unequal seating, panel flexibility, bond creep and temperature cycling are not resolved by the rigid group. In particular, main-panel contact outside a stud can increase stud tension. No FPE adhesive, stud, nut/washer, device female-thread or enclosure-wall capacity is assigned. Supplier approval or a representative qualified joint test remains necessary. Obtain an installation/locking method consistent with those joint limits; no torque value is invented here.

## Plate screens

Use certified, unwelded 6061-T6/T651 stock matching the supplier's >3–6 mm thickness range, with minimum yield 240 MPa. E=70 GPa is approximate room-temperature guidance. The target is factor 3 against plate yield for the stated service screen. This does not cover unknown joints, thermal stress or elevated-temperature strength reduction.

The minimum hard-land thickness is {p['minimum_land_t_mm']:.2f} mm; deducting both maximum recesses leaves a minimum core of {p['minimum_core_t_mm']:.2f} mm. Two beam idealizations are used to avoid crediting a perfectly supported or rigid plate:

1. A deliberately narrow 28 mm net strip spans the diagonal support distance L={p['diagonal_span_mm']:.3f} mm and carries the local 75 N force at midspan. I=bt³/12={p['local_beam_I_mm4']:.3f} mm⁴; M=PL/4. Apply a selected 1.5 bending factor, add P/(bt) axial stress, and add two 1.5V/A shear screens before the von Mises combination.
2. A 100 mm net strip screens whole-plate loading and simultaneous moment transfer. M_bound=F L/4+C+F sqrt(rx²+ry²+h²)={p['whole_plate_moment_bound_Nmm']:.1f} Nmm, with the same selected bending factor. This deliberately adds overlapping force/moment bounds; it is an engineering screen, not a solved 2-D plate/contact stress distribution.

The chosen effective strip widths and stress factors require prototype correlation. They are not empirical notch factors or proof of exact load sharing. Local bearing/tear-out screens use maximum holes, minimum thickness and adverse edge-position allowance; no washer load-spreading benefit is needed for those average-stress screens.

| Plate screen | Yield factor |
|---|---:|
{metal_rows}

Minimum screened plate factor is **{r['minimum_plate_screen_yield_factor']:.2f}**; target 3 is met within these mechanical assumptions. This is **not an assembly safety factor**. The narrow unsupported strip predicts {p['local_free_bending_deflection_mm']:.3f} mm displacement at 75 N and {p['local_proof_free_bending_deflection_mm']:.3f} mm at a 1.5× local proof load. Those loose free-bending estimates omit the seated main panel and the rigid computer. They do not establish the operating thermal gap. Strength acceptance and hot, loaded thermal-contact acceptance are separate checks; loss of contact requires a stiffer/support-revised design or qualified preload, not an optimistic thermal resistance assumption.

## Countersink and shallow blind threads

Selected candidate screws are McMaster 91294A188, M4×0.7×8 DIN 7991, nominal Ø8 head and 90° cone. The source cone envelope uses mouth≤8.2 mm, throat≥4.4 mm and angle≥89°. Maximum depth is (D−d)/(2 tan[α/2])={c['depth_screen_max_mm']:.4f} mm. After a 0.10 mm upper deburr, the minimum calculated straight throat is {c['straight_throat_stack_min_mm']:.4f} mm. Require **at least 3.00 mm actual straight throat** after all machining; the punching screen uses that acceptance minimum. The nominal straight cylinder is 5.10−1.80−0.10=3.20 mm. Use the received screw as a gauge to hold its underside head flush to 0.10 mm recessed, never proud.

The bearing calculation requires actual effective cone-seat diameter≥7.6 mm and throat≤4.6 mm. A minimum Ø7.9 hard island around the maximum top-deburr opening has {c['hard_land_area_min_screen_mm2']:.3f} mm² net contact area, or {c['hard_land_bearing_MPa_per100N']:.3f} MPa average bearing per 100 N total screw force. The surrounding Tile material/finish capacity remains unknown. Local preload must be assessed in addition to the external loads; the grease cannot carry or preserve it.

Fresh STEP evidence at every Tile hole shows the entry cone from Z=0 to 0.584 mm; the modeled helical region extends to 3.500 mm, followed by a drill cone to 4.501034 mm and a thin blind end wall. The hole is **blind**, not a clear passage through the complete Tile. None of these model coordinates is a manufacturer screw-penetration allowance. The user's approximately 4 mm depth is useful context, not a precision stop gauge.

Projection of an overall-length countersunk screw is L−plate grip+head recess. With assumed length 8.0±0.2 mm, plate 5.10±0.05 and recess 0–0.10, the unscreened range is **{f['unscreened_tolerance_projection_min_mm']:.2f}–{f['unscreened_tolerance_projection_max_mm']:.2f} mm**, nominal **{f['nominal_projection_mm']:.2f} mm**. The narrower **measured receiving window 2.85–3.00 mm** requires selection/gauging and may reject ordinary stock screws.

At that receiving window, subtracting the 0.584 mm geometric entry leaves only 2.266–2.416 mm before additional female-entry phase and screw-tip incomplete threads. To retain the proposed **≥2.00 mm complete engagement**, their combined additional loss must be no more than **{f['additional_entry_phase_plus_tip_allowance_min_projection_mm']:.3f}–{f['additional_entry_phase_plus_tip_allowance_max_projection_mm']:.3f} mm**. That compatibility has not been verified for the stock DIN screw; a modeled helical start is not a gauge of full female-thread engagement. Do not count lead/chamfer as full engagement, relax the criterion to make the arithmetic fit, or adopt a deeper screw without measured bore/tip-envelope clearance and SolidRun approval. The provisional screen maintains ≥0.50 mm to the modeled full-diameter limit, whereas the axial drill-tip difference is {f['drill_tip_axial_difference_at_max_projection_mm']:.3f} mm; these are different quantities.

For context only, a reduced thread-shear surrogate A_s=0.25π×3.3×2.0={j['female_thread_shear_surrogate_area_mm2']:.3f} mm² would require female yield≥{j['female_required_yield_at_factor3_zero_preload_MPa']:.1f} MPa at factor 3 under 75 N and zero preload; every additional 100 N preload adds {j['female_required_yield_addition_per100N_preload_MPa']:.1f} MPa to that demand. This does not establish actual thread strength. No Tile alloy or allowable mounting-face temperature was found in inspected manufacturer documentation. M4 nominal tensile area 8.78 mm² gives {j['M4_external_shank_VM_MPa']:.2f} MPa shank equivalent stress for 75 N tension+75 N shear, but the catalog class/tensile listing does not prove the reduced flat-head capacity.

## Thermal calculations: separate the conduction path from heat rejection

Analyze **10, 30 and 60 W through the entire Tile→TIM→adapter→TIM→main-panel path** as independent numerical cases. These are not measured computer heat loads or approved CPU TDPs. The remaining fin bank receives no credit, and no fraction of heat flow is assumed from its name or partial CAD contact.

For each layer, R=t/(k A), with t in metres and A in m². Use 19,000 mm² effective area in the broad-area case, below the two unvented CAD fields; no area outside the Tile is counted. The simple stack includes two grease layers, the full 5.10 mm adapter and the 6 mm reference panel. Aluminum k=150 W/(m·K) is a selected conservative typical screening value, not a certified bound or an assumption that the unknown panel is necessarily 6061. Revise it for the actual panel material.

The following values are **bulk-only, idealized estimates**. They exclude both real contact interfaces of each grease joint, voids, coatings, spreading and panel-to-air resistance. Reduced-area rows model localized heat flow and do **not** authorize poor grease coverage.

| Effective area mm² | Gap each mm | TIM k W/(m·K) | Bulk R K/W | ΔT at 10 W, K | ΔT at 30 W, K | ΔT at 60 W, K |
|---:|---:|---:|---:|---:|---:|---:|
{thermal_rows}

The unknown additions are material: R_total=R_TIM1_bulk+R_contacts1+R_adapter+R_spreading+R_TIM2_bulk+R_contacts2+R_panel+R_panel_to_air. The English TDS's 0.16°C·cm²/W at 40 psi is not substituted for these contacts. At the specified 0.05 mm grease gap, t/k alone is approximately 0.746°C·cm²/W per joint; this already exceeds that high-pressure test result, showing why its bond line/pressure cannot be carried over.

As a spreading sensitivity, an equivalent circular thin plate carrying all heat radially from 5% to 100% of the area gives R_radial=ln(r₂/r₁)/(2πkt)≈{t['radial_spreading_sensitivity_K_W']:.3f} K/W, or approximately {t['radial_spreading_delta_T_at60W_K']:.1f} K at 60 W. This intentionally simplified alternative path is not an exact rectangular spreading solution and must not be added as a verified system resistance. It demonstrates that a nearly isothermal full face is not assured by high bulk conductivity alone. Actual internal Tile heat-flux distribution is unknown.

## TEC-cooled air remains the unknown boundary

The user confirms TEC enclosure cooling, but no direct mechanical/thermal connection to a TEC cold face is modeled. The panel therefore transfers heat to cooled air with unknown coefficient h and unknown operating air temperature. For one fully exposed reference-panel face A=0.044 m², R_air=1/(hA). The following h values are **assumed sensitivity inputs**, not measurements or a claim about the enclosure fan:

| Assumed h W/(m²·K) | R_air K/W | ΔT panel−air at 10 W, K | at 30 W, K | at 60 W, K |
|---:|---:|---:|---:|---:|
{air_rows}

Large tabulated rises are linear-model warnings of insufficient assumed air-side conductance, not predictions that the real computer will reach those temperatures; radiation, convection and power limiting change with temperature. Additional faces or conduction to the enclosure may help but are not credited without a known geometry/path. For an illustrative 20 K panel-to-air budget, 10/30/60 W would require h≈11.36/34.09/68.18 W/(m²·K) over that one face. The 20 K budget is a design comparison, **not a SolidRun temperature limit**.

Consequently a low calculated TIM/plate resistance does not establish 60 W rejection to the cooled air. Measure airflow/thermal performance in the actual box. The TEC setpoint alone is not the panel temperature, and TEC capacity must cover all enclosure loads at actual hot-side conditions. Its hot side rejects the pumped heat plus electrical input. No TEC cooling capacity, airflow or total enclosure heat load has been provided here.

## Creep, expansion and electrical/finish considerations

Metal stops prevent pad compression/creep from defining the mechanical grip. Grease can still migrate, bleed or redistribute and lose thermal coverage; closed pockets, excessive charge and forced assembly must be avoided. Repeat thermal and removal-cycle checks. A hypothetical CTE mismatch of 10 µm/(m·K), 50 K temperature change and 160 mm span gives 0.08 mm free differential movement. The actual Tile alloy and temperature field are unknown, so similar expansion cannot be claimed. Fully restraining that mismatch would create additional thermal stress not included in the room-temperature plate factors.

The metal stops make this an electrically conductive mechanical interface; neither thin grease nor ordinary anodized contact is a qualified electrical-isolation barrier or protective grounding bond. Confirm the intended grounding scheme separately. Preserve the device finish, control added coatings on the adapter, and inspect exposed contact lands for corrosion consistent with indoor service. Record humidity and minimum surface temperatures in the TEC enclosure to identify condensation during its actual operating cycle.

## Prototype validation and acceptance gates

1. **Fit and receiving:** inspect the original unit, thread identity, actual blind-hole/entry profile and every received screw. Confirm 2.85–3.00 mm projection, ≥2.00 mm complete engagement and the physical no-bottoming clearance. If stock tips cannot satisfy both, hold installation and resolve the joint with SolidRun. Check head flushness/recess, ≥3.00 mm straight countersink throat, metal-stop seating, panel stud flushness, FPE nut/tool engagement and connector/cable clearance. Do not force mismatched six-hole patterns or bowed faces into place.
2. **Mechanical qualification:** weigh the exact computer/configuration and package. Obtain approved joint preload/locking and device/FPE limits. Use a rigid representative six-point surrogate for plate/panel proof work, rather than proof-loading unverified device threads. Apply the 80 N device/110 N package wrenches and 1 N·m couple in adverse orientations; check slip, lift, loosening and local damage. A separate surrogate local proof may apply 112.5 N at each housing point in turn. Proposed screening acceptance: no cracks/loosening, no more than 1.5 mm elastic displacement in that deliberately severe local proof, and ≤0.10 mm residual. Any actual service gap requirement is stricter than this general structural criterion.
3. **Gap and coverage:** qualify dispensing on representative surfaces. Require all intended hard stops to seat, actual TIM gaps <0.10 mm on both faces, continuous transfer with no persistent dry patches and no protruding screws or trapped debris. Repeat under normal gravity/cable force in the installed orientation and warm steady operation. Changes in hot gap, rocking or loss of contact require redesign/rework, not credit from the bulk-only table.
4. **Thermal path test:** first use an instrumented, insulated heater surrogate to impose known 10/30/60 W through the mount path. Insulate/measure parasitic losses and record temperatures near both interfaces, adapter, panel and local cooled air after a defined steady-state criterion. This avoids mistaking the real fin bank's parallel cooling for heat carried by the plate. Demonstrate the allocated temperature rise and gap stability using the actual panel/TEC airflow. Then test the real computer at its expected workload, ambient, enclosure heat load and orientations; compare component temperatures, throttling and operation with an appropriate baseline and obtain the manufacturer's limits. Electrical input power alone does not measure heat through the adapter.
5. **Durability/service:** cycle between actual operating temperatures, inspect grease transfer/migration, preload/locking, screw threads and FPE attachment, and repeat the thermal test after removal/reassembly. Reapply TIM after separation. Application-specific vibration or environmental qualification requires additional requirements; none has occurred.

## Evidence and regeneration

- [Fresh geometry audit](../geometry/solidrun_geometry_audit.json): source coordinates, blind entry and drill geometry; no material/allowable depth inferred.
- [thyssenkrupp 6061 data](https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf): certified-stock yield screening and typical stiffness/thermal context.
- [Dow appliance guide, p29](https://www.dow.com/documents/11/11-3930-01-silicones-from-dow-for-appliances.pdf?iframe=true): Dow 340 classified for thin bond lines below 100 µm.
- [Dow-authored English 340 TDS, distributor-hosted](https://www.ulbrich-group.com/chemical-technical-products/TDS_DOWSIL_340_eng.pdf): typical k=0.67, density and the separately identified 40 psi test. [Older regional Dow TDS](https://www.dow.com/documents/01/01-1641-11-dowsil-340-heat-sink-compound.pdf?iframe=true): lower conductivity sensitivity; confirm the received product's current data.
- [Laird Tgel 600](https://www.laird.com/sites/default/files/2025-11/THR-DS-Tgel%20600%20Data%20Sheet.pdf): documented fixed-gap alternative, not the selected T1 material.
- [Bossard fastener material reference](https://www.bossard.com/global-en/-/media/bossard-group/website/documents/technical-resources/en/f-004-en.pdf): M4 tensile area. [Countersunk-head limitation](https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/2103/): reduced head loadability can apply.
- Project procurement evidence identifies McMaster 10405K83, 91294A188 and the selected FPE WGU30 interface. These product identities do not establish a completed-joint allowable.

Run `python references/engineering/engineering_calculations.py --write` from the project directory. The adjacent JSON records named inputs, individual group reactions, all result tables, arithmetic checks and the audited CAD parameter hash. A changed critical dimension causes the parameter audit to fail rather than silently retain an obsolete calculation. No unresolved acceptance item is waived by a passing script.
'''


def main():
    a=argparse.ArgumentParser();a.add_argument("--write",action="store_true");args=a.parse_args()
    r=calculate();r["CAD_parameter_audit"]=audit_params()
    assert r["plate_target_met"]
    assert r["loads"]["housing_local_demand_covers_group"]
    assert r["countersink"]["straight_throat_stack_min_mm"]>=Q["straight_throat_accept_min_mm"]
    assert not r["CAD_parameter_audit"]["mismatches"]
    assert abs(r["loads"]["derived_device_N"]-78.86)<1e-10
    test=group_screen([[-10,-10],[10,-10],[-10,10],[10,10]],40,0,0,0,0)
    assert abs(test["max_tension_N"]-10)<1e-10
    # An independent statics check on the asymmetric six-point implementation.
    wrench=[37.0,-413.0,617.0]
    reactions=[sum(a*b for a,b in zip(row["elastic_normal_wrench_coefficients"],wrench)) for row in r["loads"]["housing"]["points"]]
    assert abs(sum(reactions)-wrench[0])<1e-10
    assert abs(sum(N*xy[0] for N,xy in zip(reactions,Q["housing_points"]))-wrench[1])<1e-10
    assert abs(sum(N*xy[1] for N,xy in zip(reactions,Q["housing_points"]))-wrench[2])<1e-10
    assert abs(thermal_stack(Q,1000,.1,1)["R_each_TIM_K_W"]-.1)<1e-12
    lower=Q.copy();lower["plate_t_mm"]=2.5
    assert not calculate(lower)["plate_target_met"]
    r["arithmetic_self_checks"]="passed; no physical validation"
    if args.write:
        (HERE/"engineering_results.json").write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
        (HERE/"engineering_checks.md").write_text(report(r),encoding="utf-8")
    print(json.dumps(r,indent=2))


if __name__=="__main__":
    main()
