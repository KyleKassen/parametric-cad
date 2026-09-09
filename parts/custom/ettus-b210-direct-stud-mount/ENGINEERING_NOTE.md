# D1 engineering note - direct B210 mounting plate

**Preliminary fit prototype, with analytical plate checks; no physical validation performed.**
This separate design implements the user's requested under-foot M3 attachment and flush underside for an FPE studded plate.
The selected adapter is one150 x148 x3.5 mm machined6061-T6/T651 aluminum part, approximately0.208 kg from CAD using2700 kg/m3 density.
The device's maximum modeled sides are X=-61.1735/+61.1745 mm, so the adapter extends about13.83 mm beyond each side for accessible stud nuts.
The adapter stops atY=+/-74 mm to preserve the connector ends.

## Evidence, configuration and fit

The supplied STEP was freshly imported in mm, with196 valid solids and a full enclosed radio configuration, including pan, cover, end panels, PCB, connectors, internal screws, four standoffs and adhesive feet.
Original source SHA256 is `c59b649ccc6a4c128885fd9e64acfd74d756b23bbcff7f119e21a4acb426c912`.
The source coordinate normalization is X rotation+90 degrees, then Z+180 degrees, translation(58.5005,80.6355,1.21) mm, giving radio pan undersideZ=0 before assembly translation.
The normalized original overall envelope, including feet/connectors, is122.348 x177.6476 x37.256 mm, spanningZ=-3.556 to33.7.
The mount assembly raises pan underside toZ=3.5, with adapter undersideZ=0.
The reference main panel isZ=-6 to0 and is not the completed enclosure structure.

The four feet are identified by XCAF names `FOOT_RUBBER_ADHESIVE_745120-01`; only those bodies are suppressed in installed exports.
Hole axes are measured93.599 x120.015 mm, centered atX=+/-46.7995,Y=+/-60.0075.
STEP metadata identifies four`SOS_M3-10` standoffs; the user physically confirms M3 and estimates roughly4 mm depth.
The modeled insert end faces are flush with the pan; no underside metal protrusion was found.
The actual bores are smooth CAD representations, not a thread specification or capacity test.
Original internal M3 x8 PCB screw tips are3.5738 mm above the pan underside at all four axes.
PEM's official SOS-M3-10 is a through-hole M3 x0.5 standoff with its counterbore on the PCB side, rather than a blind insert.
The opposite installed screws obstruct the through holes.
See the fresh audit and true sections in `references/geometry` and the [official PEM listing](https://www.pemnet.com/products/product-finder/sos-m3-10/).

The [official Ettus enclosure description](https://www.ettus.com/all-products/usrp-b200-enclosure/) matches the steel-enclosure/green-board/USB-B family.
Neither that source nor the [UHD manual](https://files.ettus.com/manual/page_usrp_b200.html) gives an approved external screw depth or chassis attachment capacity.
Published bare-product dimensions and mass must not be substituted for this enclosed STEP assembly.
The known lateral K-slots are anti-theft features, not verified mounting points or cooling vents.
The source contains alternative vendor overlay detail; compare the physical radio revision and every intended cable before manufacture.

## Concept and construction decision

A cradle with removable retainers avoids the under-foot threads but adds height, parts and external clamping.
Two short mounting strips reduce material but split the pattern and make the radio less convenient to handle as a single mounted unit.
The selected one-piece adapter registers all eight holes, keeps the four flush insert contacts supported and requires only two-sided machining.
R8 outer corners, aligned hole rows, small consistent rim breaks and one clear conversion finish provide a coherent appearance without decorative pockets.
This is a plate interface with functional broad contact faces; no ribs, center window or bend development are needed.

The3.5 mm thickness is driven by a short, commercially available M3 x6 countersunk screw and a robust remaining countersink throat as well as plate stiffness.
A thinner plate increases inward screw penetration unless screw length is reduced.
It cannot be changed independently of the internal-screw clearance check.
The head has to be seated before the radio/adapter is placed onto the FPE panel, because those four screws become inaccessible underneath.

## Hardware and tolerance stack

Housing hardware is four[McMaster91294A126](https://www.mcmaster.com/91294A126/) M3 x0.5 x6 mm overall-length,90-degree DIN7991 hex-drive flat-head screws, catalog head diameter6 mm, listed height1.7 mm and2 mm hex.
The CAD uses an ideal conical head proxy; it is not the complete or conservative real screw-head geometry.
Only received-hardware gauging can verify the actual seat.
The nominal hole is3.4 +0.10/0 mm, countersink6.1 REF x90 degrees from underside datum A, with head flush to0.10 mm below A.
The top bore-mouth deburr is0.10 maximum: nominal straight throat is3.50-1.35-0.10=2.05 mm.
Require at least1.80 mm actual straight throat after all cuts; the engineering screen includes mouth<=6.2, throat>=3.3 and angle>=89 degrees.
The actual drawing's minimum3.4 bore is tighter than that conservative3.3 analytical lower screen.

For a countersunk screw, inward protrusion=L-t+r, where L includes the head, t is finished plate thickness and r is head recess.
Nominal6-3.5+0.05=2.55 mm.
An assumed, unverified L=6.0+/-0.2, t=3.50+/-0.05 and r=0-0.10 gives2.25-2.85 mm protrusion; at2.85 the nominal STEP tip separation is0.7238 mm.
Actual acceptance2.4-2.9 mm additionally requires at least0.50 mm to the actual obstruction and at least2.0 mm complete thread engagement after entry and screw-tip incomplete threads.
The low tolerance extreme does not guarantee the engagement criterion, so every screw/seat/hole stack must be gauged and selected.
Neither2.0 mm engagement nor the protrusion range is a manufacturer-approved housing capacity.

FPE interface positions are136 x120.015 mm, four3.8 +0.10/0 mm through holes, nominal0.4 mm radial clearance around M3 studs.
Drawing true position diameter0.10 at the adapter and proposed diameter0.30 at the installed studs consume0.20 mm combined radial location budget, leaving0.20 mm nominal before diameter, straightness and datum errors.
FPE must accept the proposed installed-stud tolerance; no supplier acceptance is claimed.
The four FPE WGU30 M3 x12 load studs use reverse-side native installation with zero depth offset.
Its catalog geometry gives a flush base and nominal12.1 mm diameter x2.3 mm deep cavity; bases/adhesive must actually be flush or below the supporting surface.
The6 mm reference panel has a nominal3.7 mm remaining cavity floor, subject to actual panel tolerances and anchor geometry.
FPE5-10 mm catalog stock is EN AW-5754 H22, which differs from the adapter's6061.
Use the native element in FPD; do not duplicate its pocket or treat the exported stud markers as ordinary drill holes.
See [FPE stud help](https://docs.frontpanelexpress.com/elements/studs_standoffs.html) and the retained manufacturer catalog inspection.

Each stud receives oneMcMaster98688A142 washer,3.2 ID x7 OD x0.5-0.6 mm, and90576A102 M3 nylon locknut,5.5 AF x4 mm nominal height.
Nominal12-3.5-0.55-4=3.95 mm thread tail exceeds two M3 pitches; actual engagement must be checked.
Use a5.5 AF socket<=10 OD with>=9 mm internal clearance depth for the stud tip.
No torque is invented; thread preload, locknut prevailing torque, insert retention and FPE anchor limits need a qualified installation procedure.
Prototype witness marks do not prevent loosening, and the radio screws have no qualified permanent locking process yet.

## Numerical load screen and limitations

Full inputs, source links, equations and calculations are in `references/engineering/engineering_checks.md`, with executable arithmetic and JSON alongside.
Assumed radio mass is1.0 kg; package allowance1.3 kg; gravity9.81 m/s2; handling increment3g; cable force20 N; load height<=50 mm; separate free couple1 Nm.
This gives(3+1)x1x9.81+20=59.24 N at the radio and71.012 N for the package; round to60 N and75 N respectively.
The free couple is additional to the force-height moment and is deliberately conservative.
No specified vehicle shock, vibration spectrum, outdoor or overhead requirements exist.

For a four-point group(+/-a,+/-b), N_i=Fz/4+Mx*y_i/(4b2)-My*x_i/(4a2), and in-plane force is shared with torsional shear proportional to radius.
Conservative resultant maximization gives maximum housing-point tension32.03 N and shear18.29 N; FPE tension33.59 N and shear21.51 N.
The local plate screen uses60 N axial plus60 N shear, with a selected3x yield target and1.5 bending stress multiplier for model uncertainty.
A35 mm continuous strip at each row is reduced to28 mm effective net width; min thickness3.45, span136.3 and transfer arm21.4005 mm include allowances.
I=bt3/12=95.815 mm4 and M=P*a=1284.03 Nmm; room-temperature certified yield>=240 MPa and approximate E=70 GPa are used.
The controlling plate combined-stress estimate is35.44 MPa, giving yield factor6.77; estimated loaded-point movement0.221 mm.
The theoretical free beam center movement0.430 mm is not a guarantee for the actual plate/contact system.
Bearing, punching and edge tear-out screens also exceed the selected3x target; the1.80 mm throat gives punching factor43.10 under the60 N external load screen.

These are **plate-only** analytical checks.
They do not establish the real housing insert/clinch, screw-head, FPE anchorage, preload, main-panel bending, adhesive creep or fatigue capacities.
Prying and clamp loads are not proved by the elastic bolt-group reactions.
A150 N tension plus75 N shear per-stud qualification demand is proposed as a reserve, not an FPE allowable or validated prying bound.
Shear retention is positive bearing after clearance take-up; friction is not credited, but qualified clamping and locking remain necessary to limit motion and loosening.
The nominal load path is enclosure inserts -> M3 screws/adapter contact -> plate ears -> washers/nuts/studs -> main panel -> final box structure.
No connectors, exposed components or original case seams are used as new support points.

## Manufacturing, environment and operation

Start with certified6061-T6/T651 flat stock, nominal4 mm with adequate cleanup, face both sides to3.50+/-0.05 and inspect after unclamping.
Use supported two-sided CNC workholding, contour R8, drill/countersink, deburr and finish; there are no cutter-inaccessible pockets or bends.
The outer rim break is0.4 x45 degrees; bore deburrs are controlled separately.
Specify clear/natural chemical conversion MIL-DTL-5541 TypeII Class3 and retain finishing certificates; all dimensions apply after finish.
Minimum240 MPa yield in the applicable>3-6 mm certified sheet/plate range is supported by the[thyssenkrupp6061 data sheet](https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf).
Its modulus is approximate guidance, not a guaranteed minimum.

No electrical isolation, qualified earth/RF bond or cooling benefit is assigned to metal contact.
Verify intended grounding and mixed-metal finish compatibility in the final box.
The preliminary indoor operating envelope follows the official[B2xx specifications](https://kb.ettus.com/B200/B210/B200mini/B205mini/B206mini):0-40 C and noncondensing operation; actual enclosure and installation must be checked.
The plate replaces open air below the former rubber feet, so baseline-versus-mounted thermal operation inside the actual box is required.
Use actual plugs and strain relief; the modeled connector envelopes are planning allowances only.

## Completed checks and next validation

The custom plate passed the repository export/reimport, solid validity, dimensions and design gate.
The independent script reopened the six STEP deliverables, checked component completeness/scale, original source hash, nominal plate/device/hardware interference, internal screw separation,10 mm socket envelopes, sampled straight-lift removal and connector planning corridors, and reopened the three manufacturing DXFs.
Detailed pass/fail evidence is retained in `references/cad_verification.json`; true geometry and assembly views are retained beside it.
The part's rule-based design score is89.1 as the plate role, with no waivers; this is an organization/edge-quality metric, not a structural validation.
Dimensioned drawing review and final package checks are recorded in the drawing/final manifest files.

Follow `PROTOTYPE_VALIDATION.md` for actual fit, screw-tip clearance, engagement, joint qualification, cable access, thermal operation, service cycles and application-specific loading.
No fabrication, physical testing, FEA, supplier acceptance or installation qualification is claimed.
