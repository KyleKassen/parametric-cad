"""CAD volume screen, not measured device mass. Density assumptions explicit."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from model import load_params,create_base,create_bar,create_spacer,cap_screw,washer,nut
from vertical_adapter import build_adapter
p=load_params();rho_al=2.7e-6;rho_hardware=8.0e-6
parts=[('base',create_base(p),1),('retainer',create_bar(p),2),('spacer',create_spacer(p),4),('adapter',build_adapter(),2)]
metal=[{'part':n,'qty':q,'one_volume_mm3':s.Volume(),'one_mass_kg_at_assumed_density':s.Volume()*rho_al,'total_mass_kg':s.Volume()*rho_al*q} for n,s,q in parts]
hardware=[('retainer_M5x50',cap_screw(50),4),('web_M5x30',cap_screw(30),4),('foot_M5x25',cap_screw(25),4),('washer',washer(),20),('locknut',nut(),8)]
hw=[{'part':n,'qty':q,'one_envelope_volume_mm3':s.Volume(),'total_mass_estimate_kg':s.Volume()*rho_hardware*q} for n,s,q in hardware]
total=sum(r['total_mass_kg'] for r in metal);hwt=sum(r['total_mass_estimate_kg'] for r in hw)
result={'units':'mm and kg','aluminum_density_assumed_kg_per_mm3':rho_al,'hardware_density_assumed_kg_per_mm3':rho_hardware,
  'metal_parts':metal,'hardware_simplified_envelopes':hw,'structural_metal_mass_kg':total,'hardware_envelope_mass_estimate_kg':hwt,
  'mount_without_device_mass_estimate_kg':total+hwt,'device_mass_design_allowance_kg':1.0,'total_with_1kg_device_allowance_kg':1+total+hwt,
  'recommended_rounded_assembly_mass_design_allowance_kg':2.2,
  'limitations':'CAD volume and assumed densities, not weighed mass. Simplified hardware contains unmodeled threads/lock elements. Films and coatings omitted. Device mass allowance1kg is unconfirmed; no device CAD volume-to-mass inference.'}
(HERE/'mass_screen.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
