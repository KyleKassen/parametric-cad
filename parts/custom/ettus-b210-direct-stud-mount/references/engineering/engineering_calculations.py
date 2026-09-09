"""Preliminary B210 direct-stud mount hand calculations, N/mm/MPa.

Standard-library Python. Run with --write to reproduce the adjacent JSON and
Markdown. This is analytical screening, not FEA or physical validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
INPUTS = {
    "plate_x_mm": 150.0, "plate_y_mm": 148.0,
    "plate_t_mm": 3.5, "plate_t_tolerance_mm": 0.05,
    "outer_corner_radius_mm": 8.0, "edge_break_mm": 0.4,
    "housing_x_mm": 46.7995, "housing_y_mm": 60.0075,
    "stud_x_mm": 68.0, "stud_y_mm": 60.0075,
    "countersink_mouth_nominal_mm": 6.1,
    "countersink_mouth_max_mm": 6.2,
    "through_hole_min_mm": 3.3, "through_hole_max_mm": 3.5,
    "stud_hole_max_mm": 3.9,
    "countersink_angle_min_deg": 89.0,
    "upper_bore_deburr_depth_max_mm": 0.1,
    "straight_throat_ligament_accept_min_mm": 1.8,
    "screw_head_seat_diameter_accept_min_mm": 5.7,
    "screw_length_mm": 6.0, "screw_length_assumed_tolerance_mm": 0.2,
    "head_recess_min_mm": 0.0, "head_recess_max_mm": 0.1,
    "full_thread_engagement_accept_min_mm": 2.0,
    "thread_pitch_mm": 0.5, "screw_tip_gap_accept_min_mm": 0.5,
    "STEP_internal_screw_tip_z_mm": 3.5738,
    "g_m_per_s2": 9.81, "device_mass_allowance_kg": 1.0,
    "complete_mass_allowance_kg": 1.3,
    "inertial_acceleration_g": 3.0, "cable_force_N": 20.0,
    "cable_arm_mm": 50.0, "load_height_bound_mm": 50.0,
    "device_handling_resultant_N": 60.0,
    "package_handling_resultant_N": 75.0,
    "handling_free_couple_Nmm": 1000.0,
    "local_plate_attachment_force_N": 60.0,
    "local_plate_attachment_proof_N": 90.0,
    "required_stud_tension_screen_N": 150.0,
    "required_stud_shear_screen_N": 75.0,
    "E_MPa": 70000.0, "yield_MPa": 240.0,
    "target_yield_factor": 3.0,
    "beam_strip_gross_width_mm": 35.0,
    "beam_strip_net_width_mm": 28.0,
    "transfer_arm_allowance_mm": 0.2,
    "support_span_allowance_mm": 0.3,
    "bending_stress_factor": 1.5,
    "M3_tensile_area_mm2": 5.03,
    "thread_shear_diameter_surrogate_mm": 2.5,
    "stud_bearing_diameter_surrogate_mm": 2.4,
    "stud_edge_position_allowance_mm": 0.15,
    "density_kg_per_mm3": 2.7e-6,
    "CAD_plate_volume_mm3": 77078.860,
}


def group_demand(a, b, height, force, couple):
    """Exact elastic four-point extrema for independent resultant balls.

    F has Euclidean magnitude <=force and the free couple has magnitude <=couple.
    The force is applied at (0,0,height). Points are (+/-a,+/-b). No prying,
    preload, panel flexibility, joint separation or contact redistribution.
    """
    normal = force/4*math.sqrt(1+(height/a)**2+(height/b)**2)
    normal += couple/4*math.sqrt(1/a**2+1/b**2)
    shear = force/4 + couple/(4*math.hypot(a,b))
    return {"max_tension_N": normal, "max_shear_N": shear,
            "sum_x2_mm2": 4*a*a, "sum_y2_mm2": 4*b*b,
            "polar_sum_mm2": 4*(a*a+b*b)}


def calculate(q=INPUTS):
    t = q["plate_t_mm"]-q["plate_t_tolerance_mm"]
    E, Sy = q["E_MPa"], q["yield_MPa"]
    device_force = (1+q["inertial_acceleration_g"])*q["g_m_per_s2"]*q["device_mass_allowance_kg"]+q["cable_force_N"]
    package_force = (1+q["inertial_acceleration_g"])*q["g_m_per_s2"]*q["complete_mass_allowance_kg"]+q["cable_force_N"]
    housing = group_demand(q["housing_x_mm"],q["housing_y_mm"],q["load_height_bound_mm"],q["device_handling_resultant_N"],q["handling_free_couple_Nmm"])
    studs = group_demand(q["stud_x_mm"],q["stud_y_mm"],q["load_height_bound_mm"],q["package_handling_resultant_N"],q["handling_free_couple_Nmm"])
    normal_housing = group_demand(q["housing_x_mm"],q["housing_y_mm"],q["load_height_bound_mm"],q["device_mass_allowance_kg"]*q["g_m_per_s2"]+q["cable_force_N"],q["handling_free_couple_Nmm"])
    # Full continuous plate. Two bands at the housing/stud rows. No window.
    # The net strip subtracts a deliberately enlarged 7 mm hole/break envelope
    # over the ENTIRE beam, rather than only where the countersink is present.
    b = q["beam_strip_net_width_mm"]
    L = 2*q["stud_x_mm"]+q["support_span_allowance_mm"]
    a = q["stud_x_mm"]-q["housing_x_mm"]+q["transfer_arm_allowance_mm"]
    I, Z = b*t**3/12, b*t*t/6
    P = q["local_plate_attachment_force_N"]
    # Each of two internal point loads <=P; P*a bounds the maximum moment of
    # the simply supported strip. Equal loads give the displacement formulas.
    bending = q["bending_stress_factor"]*P*a/Z
    axial = P/(b*t)
    shear = 3*P/(b*t)  # two concurrent 1.5 V/A screens, deliberately additive
    vm = math.sqrt((bending+axial)**2+3*shear**2)
    attachment_delta = P*a*a*(3*L-4*a)/(6*E*I)
    middle_delta = P*a*(3*L*L-4*a*a)/(24*E*I)
    depth = (q["countersink_mouth_max_mm"]-q["through_hole_min_mm"])/(2*math.tan(math.radians(q["countersink_angle_min_deg"]/2)))
    ligament = t-depth
    straight_ligament = ligament-q["upper_bore_deburr_depth_max_mm"]
    punching_ligament = q["straight_throat_ligament_accept_min_mm"]
    seat_area = math.pi/4*(q["screw_head_seat_diameter_accept_min_mm"]**2-q["through_hole_max_mm"]**2)
    punching_area = math.pi*q["through_hole_min_mm"]*punching_ligament
    face_opening = q["through_hole_max_mm"]+2*q["upper_bore_deburr_depth_max_mm"]
    face_area = math.sqrt(3)/2*4.8**2-math.pi/4*face_opening**2
    projection_min = q["screw_length_mm"]-q["screw_length_assumed_tolerance_mm"]-(q["plate_t_mm"]+q["plate_t_tolerance_mm"])+q["head_recess_min_mm"]
    projection_max = q["screw_length_mm"]+q["screw_length_assumed_tolerance_mm"]-t+q["head_recess_max_mm"]
    projection_nominal = q["screw_length_mm"]-q["plate_t_mm"]+(q["head_recess_min_mm"]+q["head_recess_max_mm"])/2
    edge = q["plate_x_mm"]/2-q["stud_x_mm"]-q["stud_edge_position_allowance_mm"]
    tear_area = 2*(edge-q["stud_hole_max_mm"]/2)*t
    stud_bearing = q["required_stud_shear_screen_N"]/(q["stud_bearing_diameter_surrogate_mm"]*t)
    stud_tear_tau = q["required_stud_shear_screen_N"]/tear_area
    thread_area = .25*math.pi*q["thread_shear_diameter_surrogate_mm"]*q["full_thread_engagement_accept_min_mm"]
    body_stress = math.sqrt(P*P+3*P*P)/q["M3_tensile_area_mm2"]
    checks = {
        "plate_bending_combined": {"equivalent_stress_MPa":vm,"yield_factor":Sy/vm},
        "countersink_punching": {"shear_stress_MPa":P/punching_area,"yield_factor":Sy/(math.sqrt(3)*P/punching_area)},
        "countersink_average_bearing_with_factor3": {"equivalent_stress_MPa":3*P/seat_area,"yield_factor":Sy/(3*P/seat_area)},
        "plate_stud_hole_bearing_with_factor2": {"equivalent_stress_MPa":2*stud_bearing,"yield_factor":Sy/(2*stud_bearing)},
        "plate_stud_hole_tearout": {"shear_stress_MPa":stud_tear_tau,"yield_factor":Sy/(math.sqrt(3)*stud_tear_tau)},
    }
    return {
        "status":"PRELIMINARY_ANALYTICAL_SCREEN_NOT_ASSEMBLY_RATING",
        "inputs":q,
        "loads":{"derived_device_N":device_force,"derived_package_N":package_force,
                 "normal_housing_group":normal_housing,"housing_handling_group":housing,
                 "FPE_handling_group":studs,
                 "stud_tension_reserve_ratio":q["required_stud_tension_screen_N"]/studs["max_tension_N"],
                 "stud_shear_reserve_ratio":q["required_stud_shear_screen_N"]/studs["max_shear_N"]},
        "sensitivity":{
            "couple_2Nm_housing_group":group_demand(q["housing_x_mm"],q["housing_y_mm"],q["load_height_bound_mm"],q["device_handling_resultant_N"],2000),
            "couple_2Nm_FPE_group":group_demand(q["stud_x_mm"],q["stud_y_mm"],q["load_height_bound_mm"],q["package_handling_resultant_N"],2000),
            "deflection_scale_if_typical_E_is_68300_MPa":E/68300},
        "plate":{"minimum_t_mm":t,"net_beam_width_mm":b,"beam_span_mm":L,
                 "transfer_arm_mm":a,"I_mm4":I,"moment_Nmm":P*a,
                 "attachment_deflection_screen_mm":attachment_delta,
                 "center_deflection_screen_mm":middle_delta,
                 "proof_attachment_deflection_screen_mm":attachment_delta*q["local_plate_attachment_proof_N"]/P,
                 "proof_center_deflection_screen_mm":middle_delta*q["local_plate_attachment_proof_N"]/P,
                 "CAD_nominal_mass_kg":q["CAD_plate_volume_mm3"]*q["density_kg_per_mm3"],
                 "rectangular_stock_mass_upper_bound_kg":q["plate_x_mm"]*q["plate_y_mm"]*q["plate_t_mm"]*q["density_kg_per_mm3"]},
        "countersink":{"max_screen_depth_mm":depth,"remaining_ligament_min_mm":ligament,
                       "straight_ligament_after_upper_deburr_min_mm":straight_ligament,
                       "straight_ligament_used_in_punching_mm":punching_ligament,
                       "nominal_straight_ligament_mm":q["plate_t_mm"]-(q["countersink_mouth_nominal_mm"]-3.4)/2-q["upper_bore_deburr_depth_max_mm"],
                       "seat_projected_area_mm2":seat_area,
                       "punching_area_mm2":punching_area,
                       "average_bearing_per100N_MPa":100/seat_area,
                       "STEP_hex_end_face_projected_area_mm2":face_area,
                       "plate_top_deburr_opening_screen_mm":face_opening,
                       "STEP_hex_end_face_average_bearing_per100N_MPa":100/face_area},
        "screw_fit":{"nominal_projection_mm":projection_nominal,
                     "projection_tolerance_min_mm":projection_min,"projection_tolerance_max_mm":projection_max,
                     "STEP_tip_separation_at_max_projection_mm":q["STEP_internal_screw_tip_z_mm"]-projection_max,
                     "maximum_combined_lead_loss_at_min_projection_for_2mm_full_engagement_mm":projection_min-q["full_thread_engagement_accept_min_mm"]},
        "unrated_joints":{"M3_external_shank_VM_MPa":body_stress,
                          "M3_required_shank_proof_for_factor3_MPa":3*body_stress,
                          "thread_shear_surrogate_area_mm2":thread_area,
                          "female_required_yield_for_factor3_at_60N_and_zero_preload_MPa":3*math.sqrt(3)*P/thread_area,
                          "female_required_yield_MPa_per_added100N_preload":3*math.sqrt(3)*100/thread_area,
                          "FPE_required_combined_tension_N":q["required_stud_tension_screen_N"],
                          "FPE_required_combined_shear_N":q["required_stud_shear_screen_N"]},
        "plate_checks":checks,
        "minimum_screened_plate_yield_factor":min(c["yield_factor"] for c in checks.values()),
        "plate_target_met":all(c["yield_factor"]>=q["target_yield_factor"] for c in checks.values()),
    }


def report(r):
    q,p,c,f,j=r["inputs"],r["plate"],r["countersink"],r["screw_fit"],r["unrated_joints"]
    h,s=r["loads"]["housing_handling_group"],r["loads"]["FPE_handling_group"]
    rows="\n".join(f"| {name.replace('_',' ')} | {v['yield_factor']:.2f} |" for name,v in r["plate_checks"].items())
    text = f'''# B210 direct-stud mount — preliminary engineering screen

This report covers the machined adapter plate. It does **not** rate the radio's clinched standoffs, screw heads, FPE bonded studs, main panel, or completed assembly. No physical test or FEA was performed. The standard-library source and JSON beside this report reproduce the arithmetic.

## Geometry and evidence

Final working layout:150 ×148 ×3.5 mm full6061 plate; thickness3.50 ±0.05 mm, R8 outside corners and0.4 mm rim breaks. Four housing axes are X±46.7995/Y±60.0075 mm, measured from the supplied STEP. Four FPE stud axes are X±68/Y±60.0075 mm, selected for this mount. No window or housing-face relief is credited. The four flush standoff end faces must bear directly against the plate. Physical coplanarity and full contact must be confirmed.

The STEP identifies SOS-M3-10 standoffs; the user confirms M3 and approximately4 mm available depth. The modeled opposing PCB screw tips are3.5738 mm above the pan underside. Neither approximate physical depth nor that CAD coordinate is an allowable penetration. Actual screw interference, lead/chamfer and thread capacity remain inspection items. The flat-head screw candidate is McMaster91294A126, M3×0.5×6,90°, DIN7991. Its received geometry controls the countersink.

The FPE interface should use its documented flush cavity installation. **Default: no relief in the adapter around the stud bases.** Inspect the stud base and adhesive flush or below the main-panel seating plane. AØ12.6×0.3 adapter relief would remove local nut support and is outside this analysis; revise the preload/contact model before adding it. Do not force a rocking plate down with nuts.

## Loads and support assumptions

Radio mass allowance1.0 kg; complete package allowance1.3 kg including this plate and hardware. Neither is a measured device mass. The uncut rectangular plate mass upper bound is{p['rectangular_stock_mass_upper_bound_kg']:.4f} kg; the root CAD volume77,078.860 mm³ corresponds to{p['CAD_nominal_mass_kg']:.4f} kg at2,700 kg/m³. The package allowance leaves approximately0.09 kg for hardware after the radio allowance. Weigh the assembly before accepting it.

With g=9.81 m/s²,3g incidental inertia plus1g gravity and20 N cable force, F_device=(3+1)×1.0×9.81+20={r['loads']['derived_device_N']:.2f} N. The package equivalent is{r['loads']['derived_package_N']:.2f} N. Screen60 N resultant at the housing and75 N at the panel studs. Add a separately bounded1 Nm free couple;20 N×50 mm=1 Nm motivates it. Including both a50 mm force height and the additional couple is deliberately conservative. Force and couple may act in any direction, each within its resultant bound; this is not a60 N-per-axis requirement. The CG/load height≤50 mm is an assumption requiring confirmation.

The rigid main panel supports compression; positive screw/stud geometry transfers shear and uplift. Friction receives no retention credit. The four-point groups restrain translation and rotation when fully seated and retained. Hole clearance permits small motion before bearing, so cable strain relief and properly qualified locking/preload are still needed. This is stationary indoor equipment, not a vibration, vehicle, outdoor or overhead qualification.

## Bolt-group forces

For points(±a,±b), Σx²=4a², Σy²=4b² and J=4(a²+b²). Elastic normal reaction is N_i=F_z/4+M_x y_i/Σy²−M_y x_i/Σx². For a force at height h and independent free-couple magnitude C, N_max=F/4 sqrt[1+(h/a)²+(h/b)²]+C/4 sqrt[1/a²+1/b²]. Shear is bounded by V_max=F/4+C/(4 sqrt[a²+b²]).

- Housing handling reaction: tension≤{h['max_tension_N']:.2f} N and shear≤{h['max_shear_N']:.2f} N at any point.
- FPE handling reaction: tension≤{s['max_tension_N']:.2f} N and shear≤{s['max_shear_N']:.2f} N at any point.
- Plate/housing local screen:60 N axial and60 N shear, a reserve above the elastic group result.
- Required FPE supplier/qualified-joint envelope:150 N tension with75 N shear per stud. This is a **demand reserve**, not an FPE allowable or a proven prying bound. It is{r['loads']['stud_tension_reserve_ratio']:.2f}× the elastic tension and{r['loads']['stud_shear_reserve_ratio']:.2f}× the elastic shear.

These group reactions omit preload and prying. Panel contact outside a stud can increase stud tension. The complete contact/preload geometry and FPE adhesive performance must be qualified. Main-panel global bending, stud bond failure, nut pull-through and pan/clinch pullout are not proved by the plate calculation.

Cable routing may give a larger lever arm than the50 mm baseline assumption. As a sensitivity check, a2 Nm free couple (20 N at100 mm) raises the housing tension/shear bounds to{r['sensitivity']['couple_2Nm_housing_group']['max_tension_N']:.2f}/{r['sensitivity']['couple_2Nm_housing_group']['max_shear_N']:.2f} N and FPE bounds to{r['sensitivity']['couple_2Nm_FPE_group']['max_tension_N']:.2f}/{r['sensitivity']['couple_2Nm_FPE_group']['max_shear_N']:.2f} N. These remain below the selected local demands. Measure the actual plug/strain-relief force lever; the1 Nm baseline is an assumption, not a measurement of connector geometry.

## Plate bending and failure screens

Use certified unwelded6061-T6/T651 stock matching the supplier's thickness range: minimum yield240 MPa. E=70,000 MPa is a room-temperature reference input, not a guaranteed lower bound. A sensitivity check at68,300 MPa increases every deflection by2.49%, without changing static stress. Target factor3 against material yield accounts for the preliminary service loads and a simplified beam model; it does not cover unknown joints. No elevated-temperature or fatigue allowable is assigned.

At each row, an assumed35 mm effective continuous band is reduced to28 mm over the entire span for holes and breaks. The effective width is a simplified plate-to-beam idealization requiring physical correlation, not a solved plate contact result. Minimum thickness is{p['minimum_t_mm']:.2f} mm; span L={p['beam_span_mm']:.3f} mm and transfer arm a={p['transfer_arm_mm']:.4f} mm include position allowances. I=bt³/12={p['I_mm4']:.3f} mm⁴ and Z=bt²/6. Two internal forces each≤P=60 N give M≤Pa={p['moment_Nmm']:.2f} Nmm without assuming fixed stud rotations. Apply a selected1.5 bending stress factor, add a simultaneous axial P/(bt), and conservatively add two1.5V/A shear screens in the von Mises combination. This factor is an engineering screening choice, not a notch-factor simulation or test.

For equal forces, loaded-point deflection δ=P a²(3L−4a)/(6EI)={p['attachment_deflection_screen_mm']:.3f} mm; the unrestrained beam center is{p['center_deflection_screen_mm']:.3f} mm. Full plate action, the rigid radio and compression contact can reduce displacement; none is credited. These are ideal-beam estimates, not guaranteed bounds for joint prying or contact redistribution.

| Plate failure screen | Yield factor |
|---|---:|
{rows}

Minimum screened plate factor={r['minimum_screened_plate_yield_factor']:.2f}; target3 is met for these assumptions. It is **not a minimum assembly safety factor**. Stud-hole tear-out uses two minimum edge ligaments, t_min and the75 N shear reserve. Bearing uses a conservative2.4 mm effective stud width and a selected factor2. Deburr all holes and preserve the continuous bands; any notch/window/relief requires regeneration and reassessment.

## Countersink, end-face bearing and preload

Screen the countersink mouth≤6.2 mm, throat≥3.3 mm and included angle≥89°. The maximum conical depth is (D−d)/(2 tan[α/2])={c['max_screen_depth_mm']:.3f} mm, leaving≥{c['remaining_ligament_min_mm']:.3f} mm of material above the cone. Deducting the upper0.10 mm bore deburr leaves a calculated straight cylindrical throat≥{c['straight_ligament_after_upper_deburr_min_mm']:.3f} mm; nominal straight length is{c['nominal_straight_ligament_mm']:.2f} mm. The drawing/receiving minimum is **1.80 mm actual straight throat after all cuts**, and the punching calculation conservatively uses that lower acceptance thickness. Manufacture the nominalØ6.1/90° seat using received hardware to achieve **flush to0.10 mm recessed; never proud**. Mouth size alone does not guarantee flushness. Inspect angle, actual head seating and ligament; do not deepen the cone beyond the screened envelope to repair wrong hardware.

The bearing screen requires actual effective cone seating diameter≥5.7 mm and throat≤3.5 mm. Its projected area is{c['seat_projected_area_mm2']:.3f} mm², giving{c['average_bearing_per100N_MPa']:.3f} MPa per100 N of total screw force. Punching uses π d_min×1.80={c['punching_area_mm2']:.3f} mm²; these are simple average-stress screens, not a resolved contact analysis. The plate's top opening can reach3.70 mm including the deburr. After subtracting this opening, each modeled4.8 mm-across-flat hex end face has approximately{c['STEP_hex_end_face_projected_area_mm2']:.3f} mm² available bearing area, or{c['STEP_hex_end_face_average_bearing_per100N_MPa']:.3f} MPa per100 N. The4.8 mm end-face dimension is nominal model evidence, not an inspected tolerance.

The screw clamp-load path should close through screw head→plate→flush standoff end face→standoff thread. Recessed or noncoplanar standoffs can instead bend the thin pan; reject that condition or redesign with measured bearing geometry. Preload is **not** included in the60 N external-force plate table. Supplier-approved installation preload/torque must also satisfy head seating, aluminum bearing, female thread, clinch and FPE limits. No torque value is invented here. Use the approved locking method and verify it after removal cycles; torque alone does not establish preload.

## Screw penetration and unknown joint strength

For an overall-length countersunk screw, projection=L−t+recess. Assuming—not sourcing—a6.0±0.2 mm length, t=3.50±0.05 and recess0–0.10 gives projection{f['projection_tolerance_min_mm']:.2f}–{f['projection_tolerance_max_mm']:.2f} mm (nominal{f['nominal_projection_mm']:.2f}). The STEP separation at maximum projection is{f['STEP_tip_separation_at_max_projection_mm']:.4f} mm. **Measure every installed projection and actual internal obstruction**; require≥0.50 mm tip clearance and≥2.0 mm complete, usable thread engagement after both entry and screw-tip lead loss. At the low projection extreme only{f['maximum_combined_lead_loss_at_min_projection_for_2mm_full_engagement_mm']:.2f} mm combined lead loss is available, so the nominal tolerance stack alone cannot guarantee engagement. Select/gauge screws and reject an incompatible stack. Approximately4 mm reported depth is insufficient as a go/no-go penetration measurement.

The2.0 mm full-engagement criterion equals four M3×0.5 pitches. It is a **proposed application criterion**, not a universal standard or a manufacturer-approved housing capacity. A deliberately reduced thread-shear surrogate A_s=0.25π×2.5×2.0={j['thread_shear_surrogate_area_mm2']:.3f} mm² would require female-material yield≥{j['female_required_yield_for_factor3_at_60N_and_zero_preload_MPa']:.1f} MPa for a3× shear-yield factor at60 N and zero preload; each additional100 N preload adds{j['female_required_yield_MPa_per_added100N_preload']:.1f} MPa to that requirement. This is a demand calculation only. Actual material, thread form, lead, clinch and load distribution are unverified, so no female-thread capacity is claimed.

Using the standard M3 tensile area5.03 mm²,60 N tension plus60 N shear gives a shank equivalent stress{j['M3_external_shank_VM_MPa']:.2f} MPa. The selected flat-head product's strength/class listings do not establish its reduced-head capacity; ISO/DIN countersunk screws can have reduced loadability. Thus the shank calculation is not a screw-head or assembled-joint safety factor.

## Required physical validation

1. Inspect material/finish and all critical dimensions. Confirm the selected M3 screw, its usable tip/lead, standoff end-face contact and alignment, effective≥2.0 mm engagement,≥0.50 mm actual tip clearance, and flush/recessed head condition. Check the entire underside on a flat witness surface. Confirm received FPE stud geometry, height, seating plane and supplier allowable loads/torque.
2. Weigh the radio and completed assembly. Confirm the mounting panel is rigid and the load/CG assumptions cover the installation. Obtain housing/clinch and FPE joint approval, or run a qualified representative joint test before accepting service. Do not apply an unexplored stud/insert proof load to the real radio.
3. Prototype the plate with a rigid four-point surrogate and representative panel/studs. Apply the60 N resultant+1 Nm device service wrench in adverse orientations and corresponding75 N package wrench; inspect slip, lift, cracking, contact and loosening. A separate **mount-only** surrogate test may apply90 N at each of two same-row housing points (1.5× the60 N local reserve). The ideal beam predicts loaded-point/center elastic motion{p['proof_attachment_deflection_screen_mm']:.3f}/{p['proof_center_deflection_screen_mm']:.3f} mm for that local proof. Proposed prototype acceptance:loaded-point≤0.5 mm, center≤0.8 mm and residual≤0.10 mm; correlate measured behavior and reassess if contact differs. These are design acceptance proposals, not completed tests.
4. With the real radio under normal operation, verify all plugs mate, cable/tool access, cable bends and strain relief, removal sequence and original enclosure ventilation. Compare temperature/operation against an unmounted baseline at expected indoor ambient and duty cycle. Broad plate contact is not evidence of improved cooling. Confirm grounding/isolation intent; anodized contact is not a qualified protective bond.
5. Repeat removal/reinstallation and inspect threads, seating, countersinks, panel bond and locking. Add application-specific shock/vibration/environmental qualification only after requirements exist.

## Sources and reproducibility

- [thyssenkrupp6061 data sheet](https://d2zo35mdb530wx.cloudfront.net/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf):certified T6/T651 sheet/plate minimum yield240 MPa and modulus70 GPa; room-temperature screening only.
- [Bossard metric fastener materials](https://www.bossard.com/global-en/-/media/bossard-group/website/documents/technical-resources/en/f-004-en.pdf):M3 nominal tensile stress area5.03 mm².
- [Bossard countersunk fastener notice](https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/2103/):head geometry can reduce loadability.
- [McMaster91294A126](https://www.mcmaster.com/91294A126/):selected candidate geometry; see the project procurement evidence for the live product record.
- Supplied STEP and the project's under-feet geometry audit:axis pattern, end-face geometry and opposing internal screw-tip location.
- FPE package/research evidence elsewhere in this project:flush-cavity geometry. No allowable bond strength, shear, torque or environmental rating was found and none is assigned here.

Run `python references/engineering/engineering_calculations.py --write` from the project folder. JSON records inputs, all results and available root parameter-file hashes. This report is preliminary until the unresolved physical dimensions and joint capacities are closed.
'''
    # Keep prose and dimensions legible without changing part numbers/URLs.
    text = re.sub(r"(?<=[a-z]{2})(?=\d)"," ",text)
    text = re.sub(r"\b(a|an|and|at|after|below|by|each|factor|for|four|full|is|its|leaving|minimum|nominal|of|only|per|selected|than|the|to|two|with)(?=\d)",r"\1 ",text,flags=re.I)
    text = re.sub(r"(?<=[a-z])(?=[≥≤Ø])", " ", text)
    text = re.sub(r"([:,;])(?=[A-Za-z0-9])",r"\1 ",text)
    text = re.sub(r"(?<=\d), (?=\d{3}\b)",",",text)
    text = re.sub(r"(?<=\d)g\b"," g",text)
    text = text.replace("AØ", "A Ø").replace("X±", "X ±").replace("Y±", "Y ±")
    text = text.replace("https: //", "https://")
    text = text.replace("McMaster91294A126", "McMaster 91294A126").replace("DIN7991", "DIN 7991").replace("thyssenkrupp6061", "thyssenkrupp 6061")
    return text


def audit_cad_parameters():
    path = PROJECT/"params.json"
    if not path.exists():
        return {"status":"not yet available", "mismatches":[]}
    p=json.loads(path.read_text(encoding="utf-8-sig"))
    expected={
        "plate_width":150,"plate_length":148,"plate_thickness":3.5,
        "plate_thickness_tolerance":.05,"corner_radius":8,"edge_break":.4,
        "housing_pitch_x":93.599,"housing_pitch_y":120.015,
        "housing_clearance_diameter":3.4,"countersink_diameter_reference":6.1,
        "countersink_angle_deg":90,"screw_length_overall":6,
        "screw_head_recess_nominal":.05,"screw_pitch":.5,
        "stud_pitch_x":136,"stud_pitch_y":120.015,
        "stud_clearance_diameter":3.8,"stud_pattern_rotation_deg":0,
        "stud_pattern_center_x":0,"stud_pattern_center_y":0,
    }
    mismatches=[{"parameter":k,"expected":v,"CAD":p.get(k)} for k,v in expected.items()
                if not isinstance(p.get(k),(int,float)) or abs(p[k]-v)>1e-8]
    return {"status":"matched" if not mismatches else "MISMATCH", "mismatches":mismatches,
            "checked_parameters":expected,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    r=calculate()
    r["CAD_parameter_audit"]=audit_cad_parameters()
    r["root_parameter_file_sha256"]={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in PROJECT.glob("*params*.json")}
    # Independent arithmetic/limit checks; not mechanical validation tests.
    assert abs(group_demand(10,20,0,40,0)["max_tension_N"]-10)<1e-12
    assert abs(r["loads"]["derived_device_N"]-59.24)<1e-10
    assert abs(r["screw_fit"]["projection_tolerance_max_mm"]-2.85)<1e-10
    assert r["countersink"]["remaining_ligament_min_mm"]>1.9
    assert r["countersink"]["straight_ligament_after_upper_deburr_min_mm"]>INPUTS["straight_throat_ligament_accept_min_mm"]
    assert r["plate_target_met"]
    assert not r["CAD_parameter_audit"]["mismatches"],"CAD geometry changed: reassess engineering inputs"
    q=INPUTS.copy();q["plate_t_mm"]=1.5
    assert not calculate(q)["plate_target_met"],"Thin-plate negative check failed"
    r["arithmetic_self_checks"]="passed; these do not validate the physical model"
    if args.write:
        (HERE/"engineering_results.json").write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
        (HERE/"engineering_checks.md").write_text(report(r),encoding="utf-8")
    print(json.dumps(r,indent=2))


if __name__=="__main__":
    main()
