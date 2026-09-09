# SCE-20 aluminum mounting system — R1

This design replaces the supplied Saginaw enclosure SUBPANEL with a 431.8 mm
square aluminum plate. Its R6.35 outline and all six factory holes are derived
from the actual STEP, not nominal enclosure dimensions. Finished thickness is
6 mm. The original rear seating plane remains fixed; the component face moves
2.825 mm toward the door. Units throughout are millimeters.

The enclosure is upright and external cables enter below, as confirmed by the
user. Layout priority is: valid mounting interfaces, enclosure and factory
fastener clearance, access to mounting nuts, component cooling and cable
reservations, then spacing and short signal paths. The search evaluates a
bounded family of layouts; its best feasible result is not a proof of global
optimality over arbitrary custom brackets or unselected cable hardware.

The new part is a **plate**: its functional faces and hole/hardware pattern are
its purpose. Existing component geometry is retained as reference. B210 and
Bedrock adapter revisions use 4 and 6 mm stock, with deeper conical screw seats
to preserve the original screw penetration. Original source designs are intact.
The Mean Well N2 side-tab adapter retains its source geometry. The OZ printed
housing and router use their integral mounting ears directly.

FPD front is the accessible component side. Positive CAD Z points toward the
door. FPD XY uses the lower-left corner; the enclosure STEP uses the panel
center. Transform from FPD to enclosure is (x-215.9,y-215.9,z-106.395), where
z=0 is the component face. Reverse-side adapter machining uses the same XY
coordinates without mirroring.

Loads pass through device screws/ears, adapter plates or spacers, native FPE
hardware and panel, then four factory enclosure studs. This package verifies
nominal geometry and assembly access. It does not assign shock/vibration
ratings to bonded hardware. Actual device power, ambient conditions, enclosure
heat rejection, cable models and actual Bedrock hybrid configuration remain
unverified. The existing 100 mm PSU airflow reservations are geometric planning
zones; they do not establish cooling in a closed enclosure.

Bare aluminum preserves conductive contact faces. Standard FPE alloys and
stock tolerances differ from the original 6061 prototype specifications.
Finished adapter thicknesses, recessed screw seating, both Bedrock 0.050 mm
thermal pockets, flatness and surface condition are mandatory special drawing
requirements to resolve with FPE before ordering. Native FPD files encode
nominal geometry; their existence does not establish these process tolerances.

CAD, native-file checks, layout search evidence and source audits accompany the
four aluminum manufacturing files in the FPE delivery folder.
