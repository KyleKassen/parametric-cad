# Verification record

These reports preserve the measured CAD results and their scope. They are not a thermal, structural or production-process qualification.

| Record | Result and scope |
|---|---|
| `cad_verification.json` | PASS, 49/49 final assembly integration checks. Maximum component height 91.000 mm; conservative door clearance 146.535 mm. |
| `final_candidate_fit.json` | Exact enclosure, factory hardware, four Ø30×60 mm socket envelopes and two complete 100 mm PSU planning corridors pass for the final placement. |
| `repository_mechanical_evaluation.json` | Mechanical repository evaluation PASS. |
| `repository_full_evaluation.json` | Full evaluation FAIL: refinement score 48.8, grade D, required score 70. The gate remains unchanged. |
| `backpanel_design_review.json` | Detailed refinement findings, including hole-pattern/face composition metrics. |
| `B210_FPE_R1_verification.json`, `Bedrock_FPE_R1_verification.json` | Revised adapter geometry and screw-stack checks. |
| `B210_FPE_R1_design_review.json`, `Bedrock_FPE_R1_design_review.json` | Separate adapter refinement reviews. |
| `B210_R2_native_geometry_audit.json` | PASS, 31 native STEP geometry checks. |
| `MeanWell_R2_native_geometry_audit.json` | PASS, 19 native STEP geometry checks. |
| `Bedrock_R3_native_geometry_audit.json`, `native_bedrock_R3_step_audit.json` | PASS, 43 general and 17 thermal-field checks on the actual native STEP export. |
| `B210_R2_native.step`, `MeanWell_R2_native.step`, `Bedrock_R3_native.step` | Actual Front Panel Designer STEP exports used by the native geometry audits. |
| `placement.json` | Final lower-left panel coordinates, orientations, cable/air assumptions and bounded search margins. |
| `vendor_validity_audit.json` | Inherited invalid small Peplink connector solids identified separately from its valid case/mounting interface. |
| `delivery_transfer_manifest.json` | Source locations, sizes and SHA-256 verification for copied CAD, images, all four verified native files and their native STEP evidence. Source CAD paths retain their original revision names; delivered part filenames match the final native designs. |
| `regeneration_helper_audit.json` | PASS, 10 helper-only checks: path rewriting, unchanged feature data/API bodies, JavaScript syntax, matching DXF and protection of existing files. No native application was executed by this test. |
| `native_revision_label_audit.json` | PASS, BOM and coordinate-schedule native revision labels updated; all numeric values unchanged. |
| [Native geometry methods and summary](native_geometry/README.md) | Complete audit bundle: four PASS reports, combined summary and the two audit scripts, copied unchanged from the verification stage. |

Manufacturing exceptions and system constraints are recorded in [Ordering notes](../ORDERING_NOTES.md). Consult [Native FPD verification](../NATIVE_FPD_VERIFICATION.md) for the final application and exported-solid checks, and [the delivery README](../README.md) for package scope.
