import prepare_fpd as f
s=f.load(f.OUT/'SCE20_BEDROCK_NATIVE3_inputs.json')[0]
f.COMMON_JS=f.COMMON_JS.replace('else e=new DxfContour(a.id,a.dxf,refpoint_file,100,true);','else { e=new DxfContour(a.id,a.dxf,refpoint_file,100,false); e.SetTool(a.tool); e.SetAsCavity(true); }')
f.write_script([s], 'SCE20_BEDROCK_IMPORT5')
