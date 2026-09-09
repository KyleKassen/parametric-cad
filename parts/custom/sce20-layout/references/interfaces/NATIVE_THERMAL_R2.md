# Bedrock native cavity representation R2

Use `thermal_single_loop_regions.json` for the final native FPD cavity features.
The earlier multiple-path experiments are diagnostic only. Their native drawing
showed diagonal path links and FPD crashed during STEP export, so passing native
element-count, bounds and depth readback did not qualify those files.

The R2 representation splits each exact thermal cavity at X=-50,0,50. Those
stations pass through the centers of all four enclosed circular hard lands.
Each of the eight resulting native cavity objects has one closed outer path and
zero inner paths. Every path starts with a straight line, uses exact circular
arcs, and calls Start and Finish only once per object. Existing source physical
geometry, depth, hole axes and land diameters remain unchanged.

Each face's four regions were independently checked for validity, absence of
inner wires, analytical area and exact union against a separately reopened
reference B-rep. Top area is 19379.49990966 square mm; bottom area is
19040.39004274 square mm. The 0.05-deep unions agree within 4e-12 cubic mm.
Independent B-rep copies are used because boolean splitting at exact circle
center seams can alter shared OCCT input topology.

The native export still requires `audit_native_bedrock_step.py`. That audit
checks complete shallow slices and hundreds of points around every thermal
land, and will flag real diagonal bridges, unwanted pocket cuts, missing lands,
wrong depths or unannounced changes of coordinate handedness. Merely saving or
reloading a native FPD file does not replace the exported-geometry audit.
