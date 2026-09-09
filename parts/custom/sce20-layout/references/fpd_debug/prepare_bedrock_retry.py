import prepare_fpd as f
s=f.load(f.OUT/"SCE20_ADAPTERS_R1_inputs.json")[-1]
paths=f.load(f.HERE/"references/interfaces/thermal_native_paths.json")
# Use a unique DXF filename to avoid FPD's previous failed-import cache.
for a in s["elements"]:
    if a["kind"]=="contour_cavity":
        side="top" if a["side"]=="front" else "bottom"
        src=f.Path("C:/tmp/sce_fpd_thermal_clean")/("bedrock_"+side+"_clean.dxf")
        a["dxf"]=src.as_posix()
        a["paths"]=paths["contours"][side]["paths"]
f.COMMON_JS=f.COMMON_JS.replace('e.Start(path.start[0],path.start[1]);', 'e.Start(path.start[0],path.start[1]);e.LineTo(path.start[0],path.start[1]);')
f.write_script([s],"SCE20_BEDROCK_NATIVE6")
