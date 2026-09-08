"""
Measure mechanical/visual refinement on an exported part, and score it.

lib/evaluate.py proves a part is VALID and DIMENSIONALLY RIGHT. A knife-edged,
blank-faced extruded slab passes every one of its checks. Agents optimise to
the gate, so the gate is why the output looks like a first draft. This module
adds the missing axis: it measures how REFINED the geometry is, on the exact
B-rep of the exported artifact, and turns "looks professional" into a number
that can fail a build.

WHY THIS FILE WAS REWRITTEN
An adversarial audit proved the first version measured the PRESENCE OF
GEOMETRIC EVENTS - a hole exists, a fillet exists, faces are numerous - rather
than ORGANISATION. Random events satisfy presence tests, so a lumpy pile of
overlapping rounded boxes with scattered oversized countersinks scored 96.7/A
while a textbook sealed cover scored 50.2/D. Every metric below therefore
measures REGULARITY, ALIGNMENT AND COHERENCE. Scatter is the thing being
punished; a bolt pattern, a rib field, a louver bank and a framed recessed
panel are the things being rewarded, and lib/features.py builds all of them.

WHAT IT MEASURES (all on a re-imported STEP, never the in-memory object)

  edge_break_coverage  fraction of convex EXTERIOR edge length a fillet or
                       chamfer has broken, split into a BODY term and a bore/
                       boss RIM term. Concave blend runouts earn nothing (they
                       are invisible), and a countersink is credited once. The
                       two terms are reported separately and the rubric floor is
                       held against the body one: deburring a hole is not
                       breaking a corner, and it may never stand in for one.
  face_composition     the largest EMPTY region on the exterior faces: the
                       inscribed circle of the face polygon once every inner
                       wire with real relief is subtracted, normalised by the
                       silhouette that face looks at. Three scattered holes
                       leave a large empty circle and buy almost nothing.
                       CURVED faces are DEVELOPED and read the same way - a
                       cylinder into (arc length around the axis, distance
                       along it), a cone, torus, sphere or surface of
                       revolution into the rectangle its widest circle sweeps -
                       and a full barrel is periodic, so an empty region wraps
                       the seam instead of being cut by it. Before that, the
                       whole skin of a turned part was invisible to this metric
                       and it scored the two end faces at full weight.
  feature_composition  organisation of the feature CENTRES. Features are keyed
                       into families by (axis direction, diameter rung) and
                       scored on the fraction of centres that share a line with
                       another centre or sit in a constant-pitch run, TIMES the
                       line economy - how many features each shared line has to
                       show for itself. Adding random holes LOWERS it, and so
                       does explaining the same holes with more lines. On a body
                       of revolution the same question is asked of the MERIDIAN
                       PROFILE instead, because that is where a turned part's
                       composition is: how many distinct diameters it is turned
                       to, against a bar of one.
  pattern_discipline   pitch regularity, centreline mirror fraction and edge
                       inset consistency of the fastener families, with the
                       bore/counterbore/countersink of one screw merged. On a
                       body of revolution the repeated feature is the SHOULDER,
                       not the screw: the population is the profile's concave
                       corners and the question is whether they are radiused
                       (full), chamfered (half) or left square (nothing).
  radius_vocabulary    do the fillet radii and chamfer legs sit on the Style
                       ladder, is that set internally COHERENT, and is it
                       actually applied to the part? Coherence is a question
                       about SPLIT RUNGS - two sizes closer together than the
                       ladder's own tightest step - and never about how many
                       sizes a part uses; see VOCAB_SPLIT_RATIO_FALLBACK. The
                       third question is a coverage gate: a vocabulary of one
                       word used once is not a language, and without it a raw
                       billet with a single on-ladder chamfer scored a flat 100.
  symmetry             symmetric difference against the mirror about each
                       principal plane, best plane scored, on the difference
                       VOLUME and on the spatial extent of its SLENDER part, so
                       a thin wide asymmetry cannot hide behind a small volume
                       and a compact interface is not charged twice. See
                       SLIVER_ASPECT_NONE.
  sharp_edge_length    absolute mm of unbroken convex edge per bbox diagonal.
  proportion           bbox aspect against slab-like / stick-like extremes.

Two populations, not one, run through the edge metrics. BODY is the silhouette:
the plane-plane and plane-blend edges a human reads as the corners of the part,
plus - on a body of revolution - the edges of its OD, because the outside of a
turned barrel is silhouette and not a bore. SECONDARY is bore and boss rims plus
the detail edges where BOTH sides are narrow feature strips - a rib crest, a fin
root, a louver blade. Length
weighting is why: a rib field puts hundreds of millimetres of short crest edge
into the population, and folding it into the silhouette made adding a
refinement move LOWER the score. Secondary carries 0.15, so leaving it raw
still costs, but it cannot swamp the thing the eye actually reads.

THE ROLE SYSTEM
Three of the audit's false negatives were legitimate part roles judged by an
enclosure's rubric: a cover, a plate and a sheet-metal bracket are all SUPPOSED
to be thin, and two of them are supposed to have one big flat mounting face.
spec.json's "design" block therefore carries a "role", one of
`enclosure` (the default and the strictest), `cover`, `plate`, `bracket`,
`sheet`, `structural`. The role selects the weights, the face_composition
thresholds and which metrics apply at all - `proportion` does not apply to a
cover, a plate, a bracket or a sheet part, and a sheet part's blanked perimeter
is removed from the edge population because 2 mm material cannot carry a
chamfer there. That last exclusion is paid for by the FORMED radii the part is
judged on instead, so a flat blank - which has none - cannot claim it. See
ROLE_RUBRICS.

THE GEOMETRY DECIDES WHAT IS MEASURED, AND MAY NEVER DECIDE WHAT IS SKIPPED
A role is something the author declares, and the parts that were being judged
worst were the ones whose authors had no idea there was anything to declare. A
TURNED part - a shaft, a spacer, a standoff, a bushing, a knob, a gland, a spool
- carries no bolt pattern, and feature_composition and pattern_discipline both
reported ABSENT on every one of them: 0.0 at full weight, 0.28 of the enclosure
rubric, and the only behaviour that teaches is "add holes you do not need".

The first fix for that was to report the two metrics NOT_REQUIRED on any body of
revolution with nothing off its axis, and it opened a hole bigger than the one it
closed. NOT_REQUIRED RENORMALISES, so 0.28 of the rubric left the weighted mean
outright - and everything that remains is free on a solid of revolution: it is
perfectly symmetric, it has no large empty PLANAR region, its proportion is
ideal, and a single .chamfer() call maxes edge_break_coverage, sharp_edge_length
and radius_vocabulary at once. Measured: a three-line bored cylinder scored
97.8 / band A and outranked this repo's own reference exemplar at 83.1, a bare
stepped cylinder reached 100.0, and the whole class ran at coverage 0.72 against
a MIN_COVERAGE of 0.60.

The rule this module already held, and now holds here too: NOT_REQUIRED means
the part's ROLE excludes the metric - an intent the author declares and a guard
then checks against the B-rep. A metric excused on GEOMETRIC grounds is a scored
number or an absent defect, never a free renormalisation, because geometry is
what the author controls and what the gate exists to judge. So the weight stays
exactly where it was and is asked a question a turned part can answer: both
metrics read the MERIDIAN PROFILE (Topology.revolution_profile) - how many
distinct diameters the part is turned to, and whether its shoulder roots are
relieved. A trivial turned part now scores near zero on both and a finished one
earns them, coverage is back to 1.00, and no turned part is ever told to add a
bolt pattern. Only the part that is ENTIRELY its own profile takes that branch;
an off-axis hole on a turned flange is a layout decision like any other, so
"holes exist but form no pattern" is still a defect and never an exemption.

A ROLE IS A CLAIM ABOUT GEOMETRY, AND THE GEOMETRY IS ASKED
The second audit found role selection rested entirely on author honesty: only
`sheet` had any geometric guard, so one identical STEP could be shopped around
the rubrics for free points. Every role now carries a GUARD in ROLE_GUARDS - a
predicate over the measured B-rep that must agree with the claim, chosen to
cover exactly what that role RELAXES. A cover and a plate relax the emptiness
knots on the strength of being thin, so they must measure thin; a sheet part
excludes a whole edge population AND the only floored metric a role can drop, on
the strength of being formed from thin flat stock, so it must measure thin both
relatively and in absolute millimetres, must not enclose a void, and must carry a
real BEND; a bracket relaxes composition on the strength of being solid material,
so it must not be a shell; a structural member relaxes the proportion knots on
the strength of being long, so it must measure long against its whole
cross-section. A claim the geometry contradicts is a role ERROR and the part is
re-judged under `enclosure`, the strictest rubric - never silently honoured, and
never merely warned about.

A guard that measures ONE of the things its role relaxes is the same defect as no
guard at all, and a third audit found two: `_guard_sheet` accepted a solid
200 x 120 x 12 milled slab, whose 10.18 mm of "stock" is 5% of a 200 mm part and
whose four milled plan radii read as forming, taking it from 70.3/B honest to
89.2/A with the `sharp_edge_length` floor not emitted at all; and `_guard_long`
accepted a 200 x 150 x 42 slab, because max/min alone is satisfied by any slab.
Both are closed above. See tests/test_role_guards.py.

THREE-STATE APPLICABILITY - "inapplicable" must never mean "free"
The old two-state applicable/not_applicable let a part opt out of a metric by
having worse geometry: four scattered holes scored 18/100, the same four holes
enlarged past the diameter cap scored not_applicable and the part scored HIGHER.
Metrics now report one of four states:

  scored        a real 0-100 number; enters the weighted mean.
  not_required  the ROLE genuinely excludes it, or it was waived in spec.json
                with a written reason; renormalised OUT of the score.
  absent_defect the geometry implies the metric SHOULD apply and it does not
                (holes exist but form no pattern, no break geometry exists at
                all). Scores 0.0 at FULL weight and is never renormalised out.
  error         it could not be measured; it contributes ZERO at full weight,
                it does NOT count towards coverage, and it is reported as an
                ERROR check.

THE ERROR INVARIANT
A measurement that did not happen never produces a number, AND BREAKING A
METRIC IS NEVER WORTH MORE THAN SCORING IT. Every metric reports the fraction
of its population it could not classify; above that metric's degradation
threshold it is ERROR with score None.

The first half of that invariant was implemented and the second was not: an
errored metric used to be renormalised out of the weighted mean exactly like a
role exclusion, so breaking a metric paid the same as being excused it, and the
cheapest way to delete the one metric that would catch a sculpted blob was to
sculpt it hard enough that the metric could not read it. An errored metric
therefore now sits in the DENOMINATOR of the weighted mean contributing zero:

    score = sum(w_i * s_i over scored/absent) / (used_weight + errored_weight)

so for any metric and any geometry, score(errored) <= score(measured), with
equality only when the metric would have measured zero anyway. Errored weight
is still excluded from `coverage`, so enough of it drives the report to
`insufficient` and the review refuses to be a verdict at all. Failing to
measure buys silence, never points. Only NOT_REQUIRED - a role exclusion or a
written waiver - is renormalised out.

THE COVERAGE INVARIANT: A METRIC MAY NOT RETURN A SCORE FOR A PART IT DID NOT
LOOK AT
The error invariant above polices the population a metric BUILT. Nothing
policed whether that population was the part, and that is a different failure
with the same shape. face_composition built its population from PLANAR faces
only. On a body of revolution the entire visible skin is one cylinder, so the
metric saw two end annuli - and on a thin-walled turned part those are narrow
rings that can never hold a large empty circle. It therefore reported SCORED,
at its full 0.19 weight, having examined 14% of the exterior - 3.7% on a 2 mm
wall - with `coverage` 1.00, nothing excused and no floor unmet. Measured,
build -> export -> re-import -> review: a six-line tube (bore, counterbore, one
arbitrary ring groove) scored face_composition 100.0 and 94.0/A overall, above
every good case in the corpus and this repo's own exemplar at 83.1; a tube with no
features at all plus one blanket .fillet(1.0) scored 77.3/B and cleared the 70
gate unassisted.

Every metric that works over a population therefore now reports the FRACTION of
the relevant exterior it actually examined, and one below its floor in
EXAMINED_MIN leaves through _degrade as an ERROR - zero at full weight, out of
`coverage` - like any other measurement that did not happen. `examined`,
`relevant` and `examined_fraction` are in the metric's own report either way,
so the reader can always see how much of the part the number is about.

THE AUDIT, metric by metric. Every one was checked for the same exposure:

  face_composition     THE DEFECT. Population widened from planar faces to
                       every developable exterior face; examined / relevant is
                       area, floor 0.35. The tube below reads 0.14 with the
                       skin filtered out and 1.00 with it developed.
  edge_break_coverage  Convex exterior edge length. Its unexamined part is the
                       unresolved length, the creases too shallow for
                       SHARP_MIN_DEG and the tangent joins with no break face
                       beside them - length that leaves the population without
                       being judged. Reported; floor 0.40; corpus low 0.44.
  sharp_edge_length    The same population and the same floor.
  feature_composition  Population is FEATURES, not area, and it already counts
                       and degrades on the ones whose reachability probe fails.
                       It had one scope hole of the same species - its pocket
                       scan read planar faces only, so a recess on a curved
                       skin was silent - and that is now counted as unmeasured
                       population, where DEGRADATION_MAX already governs it. No
                       corpus case carries one, so nothing moved. On a body of
                       revolution it reads the meridian profile, which is the
                       whole of that part's composition and not a sample of it.
  pattern_discipline   Shares that population and that fix.
  radius_vocabulary    Population is break and blend FACES, and it reads them
                       whatever surface they sit on - a cone chamfer and a
                       torus blend both count - so it has no planar filter to
                       be caught by. Its coverage question is a different one,
                       "is this vocabulary applied to the part at all", and
                       VOCAB_APPLIED_FULL already answers it at full weight.
  symmetry             No population: three mirror booleans over the whole
                       solid. It is total or it is an error, and
                       SYMMETRY_MAX_FACES is already a METRIC_ERROR rather than
                       an exemption.
  proportion           No population: three bounding-box numbers.

THE CONFIGURATION SURFACE IS PART OF THE GATE
Everything above is geometry, and an agent optimising against this module finds
the config long before it finds a rib field. The second audit measured a crude
knife-edged box at 27.7/F honestly, 100.0/A with six `design.weights` entries
set to zero, and 425.5/A with two of them negative - no geometry required.
_normalise_config() is the single validated front door for both the spec.json
block and `--config`, and it enforces:

  * there is NO weight override. The relative weight of the metrics IS the
    standard; a part that sets its own weights is not being held to a standard,
    it is publishing one. Roles pick a rubric, waivers excuse a metric for a
    written reason, and per-metric min_score/max_value can only ever make the
    bar HIGHER. Nothing legitimate is left for `weights` to do.
  * every route to NOT_REQUIRED carries a written reason, cuts `coverage`, and
    appears in report["excused"]. `metrics.<id>.enabled: false` is a waiver by
    another name and needs `reason` alongside it; asserted excusal is capped at
    MAX_EXCUSED_WEIGHT of the rubric, tighter than MIN_COVERAGE, because a
    written reason is still an assertion and 40% of a rubric is not a detail.
  * `symmetry_max_faces` is a COST guard, not an exemption: tripping it is a
    METRIC_ERROR, which under the error invariant costs full weight at zero.
  * there is NO ladder override either. `style.radius_ladder` was validated for
    SHAPE - five rungs, a 4:1 span, a written reason - and never for the only
    thing that mattered, which is whether the rungs were a transcription of the
    part's own radii. It is retired by the same route `weights` was.

Every rejected key is a `config_error` in the report and an ERROR check out of
design_review_checks(), never a silent fallback.

FLOORS, AND AGGREGATE CONFIGURATION ACCOUNTING
Two things the per-knob validation above could not do.

A weighted mean is arbitrable: pick the role whose column is lightest where you
are weak, spend one waiver, and the other metrics carry you. RUBRIC_FLOORS is a
hard minimum on a SINGLE metric, checked outside the mean, so it cannot be
renormalised out, averaged away, waived, or shifted by a role choice. A part
with an unmet floor is capped at band FLOOR_BAND_CAP - below the advisory gate -
at every severity, and its floor check fails at the review's overall severity,
so whenever the design gate is hard the floor is hard. A spec may raise a floor
and cannot express lowering one.

A floor also has to be held against the right NUMBER. edge_break_coverage is a
composite, 0.85 body plus 0.15 rim, so its rim term alone was worth 15.0 against
a floor of 10.0 - and a part with not one broken body corner and deburred bore
mouths cleared the floor named after exactly that defect. Floor.key names the
quantity, and this one reads `body_score`.

And every knob was accounted for individually while nothing added them up. The
review now scores the SAME measurements a second time under the default rubric
with nothing excused, and reports the difference as `config_delta` - split into
what the ROLE is worth and what the WAIVERS are worth, because a role is checked
against the B-rep and a waiver is not. Each has its own cap
(ROLE_DELTA_ALLOWANCE and MAX_CONFIG_DELTA); past either it is an ERROR. The
report finally says out loud how much of the score is configuration rather than
geometry, and which kind.

Usage:
    uv run python -m lib.design_review FILE.step [--json out.json]
                  [--min-score N] [--config cfg.json] [--role R]
                  [--top N] [--quiet]

    exit 0 = score at/above the threshold, 1 = below, 2 = could not review.

Units: mm. Report schema: "design-review/2".
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cadquery as cq
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve2d, BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.GeomAbs import (
    GeomAbs_Cone,
    GeomAbs_Cylinder,
    GeomAbs_Plane,
    GeomAbs_Sphere,
    GeomAbs_SurfaceOfRevolution,
    GeomAbs_Torus,
)
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Vec
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_ON, TopAbs_REVERSED
from OCP.TopExp import TopExp
from OCP.TopTools import (
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_IndexedMapOfShape,
)

from lib.analyze_step import _canonical_dir, _cylinder_features
from lib.frame import Frame, frame_record, reference_frame

SCHEMA = "design-review/2"

PASS, FAIL, ERROR = "PASS", "FAIL", "ERROR"

# --- design-language constants ------------------------------------------------
# The radius ladder is the discrete set of break sizes a coherent design is
# allowed to use. lib/features.py owns the canonical ladder; it is imported
# defensively at runtime (see _load_ladder) so this module keeps working while
# that file is still being written.
DEFAULT_RADIUS_LADDER = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0)

SMOOTH_DEG = 1.0  # dihedral below this = tangent (a blend runout, not an edge)
SHARP_MIN_DEG = 20.0  # shallower creases than this are not read as knife edges
CHAMFER_MAX_DEG = 80.0  # a break face meets its neighbours at less than this
MIN_EDGE_LEN = 1e-4  # mm, ignore degenerate edges

# --- the convexity probe ------------------------------------------------------
# How far off the edge the two faces are sampled, in mm, and the floor on the
# normalised signal that decides. See Topology._convex: the signal is +-1 for a
# clean crease AND for a clean tangent runout, so one threshold covers both, and
# 0.02 rejects only the genuinely undecidable.
CONVEX_STEP_MIN = 5.0e-4
CONVEX_STEP_MAX = 0.25
CONVEX_MIN_SIGNAL = 0.02
# Below this the two faces lean the same way to the last bit and the edge between
# them is a partition of one surface, not an edge of the part. At the largest
# step (0.25 mm) a genuine tangent join off a blend of radius R leans by 0.25/R,
# so 1e-9 admits blends out to R = 250 000 mm while rejecting only true C2
# continuation, whose lean is round-off in the normals (about 1e-15).
CONVEX_SEAM_LEAN = 1.0e-9

#: Edge kinds that are facts about the FILE rather than about the part, and are
#: skipped wherever edges are walked or scored: a shared parametric seam, a
#: non-manifold junction, and a split of one smooth surface into two faces.
SKIPPED_EDGE_KINDS = ("seam", "nonmanifold", "smooth_seam")

# The scale caps that decide what counts as a break are RELATIVE to the part.
# The audit found the old absolutes were cliffs: a 4 mm chamfer on a 300 mm box
# stopped registering as a chamfer and its two boundary edges were then scored
# as knife edges (coverage 100.0 -> 0.0 between a 3 mm and a 4 mm break), and a
# plan blend above R40 silently left the vocabulary altogether.
#
# Style.edge_break() quantises 0.015 * size, so a cap at four times the style
# target is deliberately permissive: this predicate's job is to RECOGNISE a
# break, not to police its size - that is radius_vocabulary's job.
BREAK_CAP_FRACTION = 0.06
BREAK_CAP_MIN, BREAK_CAP_MAX = 0.6, 25.0
# Style.plan_radius() caps at 45% of the governing dimension and its ladder
# tops out at 24.0, so a legitimate large blend shoulder is inside this by
# construction. "Is this a blend at all" is a topological question; "is this
# radius on the ladder" is radius_vocabulary's.
BLEND_CAP_FRACTION = 0.25
BLEND_CAP_MIN, BLEND_CAP_MAX = 4.0, 120.0

# A countersink / chamfer cone meets the world between these half-angles. A
# 3 deg draft taper (semi-angle 87) is a body surface, not a break.
CONE_BREAK_MIN_DEG, CONE_BREAK_MAX_DEG = 15.0, 75.0

# How many break-sized faces Topology._corner_sense will step through on its way
# from a profile treatment face to the flank that actually turns the corner. A
# deburred chamfer is one blend per side, so 2 would do; 4 leaves room for the
# runout patches OCC splits out of a tangent join without letting a walk wander
# off across a part.
CORNER_WALK_MAX = 4

# A planar face smaller than this share of the bbox silhouette it faces is
# detail - a chamfer land, a rib flank, a strip of pocket floor between ribs.
# Composition is a statement about the big faces, so only those are judged.
FACE_MIN_SHARE = 0.06
# An inner wire only counts as a feature when it has real relief and real size.
# Measured on the corpus: decorative scribe grooves read 0.5-0.9 mm deep, the
# exemplar's real features 10.0 mm. Style.recess_depth is 1.8 mm.
RELIEF_MIN_MM = 1.0
RELIEF_MIN_AREA_MM2 = 4.0  # Style.min_wall squared, rounded
POLY_CHORD_MM = 0.4  # wire discretisation for the face polygon

# Feature-centre clustering: two centres share a line when their projected
# coordinates agree inside this tolerance.
ALIGN_TOL_MIN = 0.5
ALIGN_TOL_FRACTION = 0.004
PITCH_CV_MAX = 0.05  # a "constant pitch" run may vary by this much

# A cluster of centres is a shared CENTRELINE only at this membership or above.
# One feature on a line of its own is not a line, it is a feature.
MIN_CLUSTER_MEMBERS = 2

# Lattice economy: does a layout OCCUPY the lattice its own centrelines define?
# This is the half of "a small number of common lines" that the first
# implementation left out, and leaving it out is what let a RANDOM scatter
# mirrored about both centrelines read as fully organised - every u became a
# shared u and every v a shared v, on two independently scored axes.
#
# A 6 x 4 bolt grid fills 24 of the 24 sites its 6 u-lines and 4 v-lines cross
# at; a row of five at constant pitch fills 5 of 5 x 1; a 2 x 2 corner pattern
# fills 4 of 4. Mirroring four RANDOM points into four quadrants spends 8 u-lines
# and 8 v-lines to place 16 holes and fills 16 of 64. See _lattice_economy.
LATTICE_FILL_BEST = 0.80
LATTICE_FILL_WORST = 0.30
LINE_ECONOMY_FLOOR = 0.25  # what an aligned but sparse lattice retains, not zero

# A merged cylindrical feature is a real bore or boss only if its faces wrap at
# least this much of a full barrel. A pocket corner fillet covers a quarter turn.
BORE_WRAP_MIN = 0.6

# What radius_vocabulary is worth to a part whose every break is INTERIOR - a
# sealed cavity's fillets, a scribe groove's corners. The vocabulary demonstrably
# exists; nobody can see it. A quarter, so a buried blend is worth a quarter of a
# visible one and can never max the metric, but a part with a coherent invisible
# language still ranks above a plain billet with no radius decision anywhere.
INTERIOR_ONLY_CEILING = 25.0

# How much of the part's convex edge population must actually carry break
# geometry before its vocabulary counts as APPLIED rather than as a coincidence.
#
# radius_vocabulary was area-weighted over the break faces with no coverage
# requirement at all, so ONE chamfer anywhere scored 100.0 - measured, a plain
# 90 x 60 x 30 billet with a single 2.5 mm chamfer on a single edge. At weight
# 0.11-0.14 that was the cheapest block of rubric in the module. The metric
# claims "the break geometry is drawn from a small coherent vocabulary"; a
# vocabulary of one word used once is not a language, and the second half of the
# claim - that it is the vocabulary of THIS PART - is what the coverage term
# measures.
#
# 0.35 rather than a higher bar because this is a GATE on the vocabulary claim,
# not a second edge-coverage metric: past a third of the body silhouette the
# author demonstrably has a break language and radius_vocabulary goes back to
# asking its own question. Calibrated against the corpus (measured 2026-07-26,
# body-only applied fraction): the lowest any `good` case reaches under its own
# role is the sheet bracket's 0.336, then the sealed cover's 0.630 and the
# exemplar's 0.919, against a raw billet with one chamfer at 0.084.
VOCAB_APPLIED_FULL = 0.35

# WHAT THIS METRIC MAY NOT CHARGE FOR: HAVING MORE THAN ONE JOB.
#
# The term that used to sit beside conformance was a COUNT penalty - "beyond ~4
# distinct break sizes a design stops reading as one language", tapering to half
# credit at 10. That is a measure of RICHNESS, not of coherence, and it is the
# wrong construct: a fin root, a seal land, a bolt-hole counterbore and an outer
# plan corner are four different jobs, and the radius that is correct for one is
# wrong for the others. Measured on the two parts the repo tells agents to copy:
# parts/custom/reference_mast_node_enclosure drew 10 sizes, 97% of its break
# area from this repo's own ladder, and was scored 48.5 for it; parts/_template,
# a rounded soap-bar case whose features are decorative grooves and identical
# recesses, drew 5 and scored 91.7. The gate was paying for plainness.
#
# So the count is gone and what replaces it measures an accident instead. Two
# break sizes closer together than any two ADJACENT RUNGS of the shared ladder
# cannot be a deliberate distinction - the ladder is the design language's own
# statement of which sizes are meaningfully different, and nothing in it is
# finer than its own smallest step. A pair that close is a split rung: a
# mistyped parameter, a blend dragged off its target, a land that is not quite
# the chamfer it looks like. The threshold is DERIVED from the ladder in use
# (min over adjacent rungs; 1.20 for lib.features.Style, at 2.5 -> 3.0), never
# typed here, so it moves with the language rather than against it.
#
# The property that matters: no two ON-ladder sizes can ever trip this, because
# every on-ladder pair is at least one full rung apart by construction. A part
# that draws every break from the ladder is never charged, however many rungs it
# needs. Richness is free; only incoherence costs.
VOCAB_SPLIT_RATIO_FALLBACK = 1.20  # used only if the ladder has fewer than 2 rungs

# --- role guards --------------------------------------------------------------
# Stock thicker than this fraction of the part is not sheet metal, whatever the
# spec.json role claims.
SHEET_THICKNESS_MAX_FRACTION = 0.10
# ... and neither is anything that encloses a void. 2 * volume / area recovers
# the wall thickness of a HOLLOW BOX just as well as it recovers the stock
# thickness of a formed blank, so the thickness test alone passed a 3 mm walled
# enclosure as sheet metal (measured: 2.99 mm derived on a 90 mm part). A formed
# sheet part is open on both sides of its own material; an enclosure is not, and
# the interior face area is what tells them apart (measured on the corpus: the
# sheet reference 0.06, three real enclosures 0.52 each).
SHEET_INTERIOR_MAX_FRACTION = 0.15
# ... and neither is a SOLID MACHINED SLAB. The fraction above is relative, and a
# relative test alone has no opinion about a big part: measured here, a
# 200 x 120 x 12 milled slab derives 10.18 mm of "stock" on a 200 mm part, which
# is 5% and passes comfortably. The whole justification for the sheet rubric's
# exclusions is that thin stock CANNOT carry a chamfer on a blanked perimeter,
# and 12 mm plate carries one perfectly well - so the claim also has to hold in
# absolute millimetres. 6 mm is where sheet stops and plate begins in every
# supplier's catalogue; the reference formed bracket derives 1.93 mm, so the
# margin is 3x.
SHEET_STOCK_MAX_MM = 6.0
# --- what a BEND is, as opposed to any small radius ---------------------------
# Bending flat stock produces a coaxial PAIR of cylindrical faces: an inner face
# of radius ri and an outer face of ri + t, sharing one axis. Nothing else on a
# part made of one thickness of material looks like that, and a plan radius
# milled into the outline of a solid slab looks nothing like it - it is a lone
# cylinder with no partner. That distinction is the whole reason these constants
# exist: counting "any small blend cylinder" as evidence of forming let a milled
# slab with four R8 corners claim to be a formed part (measured here: 4 formed
# radii, 0 bend pairs).
BEND_MAX_WRAP_DEG = 300.0  # a bend is a partial cylinder; a bore or boss closes
BEND_THICKNESS_TOL = 0.35  # how far ri+t may drift from the derived stock t
BEND_MAX_RADIUS_STOCK = 8.0  # a bend radius is a few multiples of material, not 50
# ... and "coaxial, one stock apart" is STILL not enough on its own, because a
# machinist can arrange exactly that on purpose. Measured on a plainly
# unremarkable 200 x 120 x 5 milled tray - outer plan R8, a 1 mm deep pocket
# inset 4 mm so its R4 corners are concentric with them, derived stock 3.78 - the
# two radii pair up four times and the part claimed `sheet` at 75.3/B against
# 46.2/D honest, with the edge_break_coverage floor going from UNMET to met and
# sharp_edge_length's floor never emitted. Because the derived stock is an
# average of the whole part, ANY constant-wall tray can be walked onto that
# coincidence by choosing its wall.
#
# Two further properties separate a fold from a milled coincidence, and both are
# properties of forming rather than of arithmetic:
#
#  * A FOLD RUNS THE FULL WIDTH OF WHAT IT JOINS. The inner and the outer face of
#    a real bend span the same extent along the bend axis and coincide over it
#    (measured on the corpus's formed bracket: 70.0 mm and 70.0 mm); the tray's
#    plan corner spans the plate's full 5 mm while its pocket corner spans the
#    1 mm of pocket, and they merely overlap (4.4 mm against 1.4 mm).
#  * A FOLD IS TANGENT TO THE FLANGES IT JOINS. Each face of the pair runs out
#    tangentially into a planar face MUCH wider than the stock - the flange
#    surface. The tray's corners run out into the 5 mm thickness band of the
#    blank instead, which is the geometric statement of "that axis is normal to
#    the sheet, not in its plane": a cylinder is only ever tangent to planes
#    parallel to its own axis, so a bend axis that lies in the plane of the stock
#    is tangent to flanges and one normal to it can only be tangent to bands.
#
# Together they say the pair is a constant-thickness wall that changes direction,
# which is what forming is and what a pocket floor is not. A through-cut window
# inset by exactly one stock thickness - the obvious way to fake equal extents,
# since both cylinders then span the whole blank - is refused by the second: both
# of its runouts are thickness bands.
BEND_EXTENT_MIN_RATIO = 0.60  # shorter axial span / longer, over the pair
BEND_OVERLAP_MIN_RATIO = 0.75  # how much of the shorter span the two share
BEND_FLANGE_MIN_STOCK = 3.0  # a flange is this many stock thicknesses wide, at least
# Tangency is measured, not read off the edge classification. The corpus's own
# formed bracket carries a bend whose inner R3 face reports both of its runout
# edges as `concave` at 180.0 degrees while the identical face on its other bend
# reports `smooth_concave` at 0.0 - the classifier's sign, not the geometry -
# so a flange test built on "smooth" edges saw one of its two real bends. A
# plane sharing an edge with a cylinder and parallel to its axis is tangent iff
# the axis stands exactly one radius off it; a plane a boss is merely embedded
# in stands closer.
BEND_FLANGE_AXIS_TOL = 0.02  # |n . axis| for "this plane is parallel to the axis"
BEND_FLANGE_TANGENT_TOL = 0.05  # fraction of r the runout may miss tangency by
# A cover and a plate relax the emptiness knots because they are thin by
# function. min(bbox) / max(bbox): the corpus's cover reference measures 0.083
# and its plate reference 0.067, while every box-shaped case measures 0.256 or
# more, so this separates the claim from the shape without being a cliff either
# side of anything real.
THIN_MAX_ASPECT = 0.25
# A bracket relaxes composition because it is solid material whose every free
# edge can genuinely carry a break. A shell is not that.
BRACKET_INTERIOR_MAX_FRACTION = 0.20
# A structural member relaxes the proportion knots because it is legitimately
# long. max(bbox) / min(bbox): the corpus's structural reference measures 5.93,
# every ladder box measures 3.00.
STRUCTURAL_MIN_ASPECT = 4.0
# ... and long relative to BOTH cross-section dimensions, not just the thinnest.
# max(bbox) / mid(bbox): a slab is long by the ratio above the moment it is thin,
# so a 200 x 150 x 42 housing measured 4.76 against a threshold of 4.0 and
# collected the relaxed proportion and emptiness knots as "a long member" - worth
# a measured +6.9 points here. A member is long relative to its whole
# cross-section. The corpus's structural reference arm measures 2.67 on this
# ratio and that slab 1.33.
STRUCTURAL_MIN_SLENDERNESS = 2.0
# Share of face area that must be a surface of revolution about ONE axis before
# a part is read as turned. 0.95 rather than 1.0 so a spanner flat, a keyway or
# a single cross-drilling does not disqualify an obviously turned part;
# measured, the corpus's boxes reach 0.44 at best and a plain bored cylinder
# 1.00. See Topology.revolution_axis.
REVOLUTION_MIN_AREA_FRACTION = 0.95
# ... of the surface that is NOT an off-axis drilled feature. Those are removed
# from both sides of the ratio (see Topology.revolution_axis) and capped here,
# so "mostly holes" can never be a route to being read as turned.
REVOLUTION_OFF_AXIS_MAX = 0.25

# How many distinct turned diameters a profile has to carry before it stops
# reading as bar stock. Counted over the BODY walls only - a chamfer cone and a
# blend torus are corner treatments, not diameters - and it counts a taper, a
# crown or any other non-cylindrical body wall as one apiece, because choosing
# to make a band curved is a diameter decision too.
#
# Measured 2026-07-26 over the turned probe set: a plain billet 1, a bored
# spacer 2, a crowned knob 3, a stepped shaft 3, a spool 3, the corpus gland 4.
# Four is where it saturates because four is what a designed turned part
# actually has (an OD, a bore, one step and one register) and because a bar of
# saturation any higher would start paying for steps nobody needs.
PROFILE_ELEMENTS_FULL = 4.0

# What a CHAMFERED shoulder root is worth against a RADIUSED one.
#
# At a shoulder root the design question is what replaces the sharp internal
# corner. A tangent radius removes the stress concentration and gives the mating
# part's own break somewhere to sit; a 45 degree undercut clears the mating part
# and does nothing about the stress, leaving two new hard corners where there
# was one. Both are refinement and neither is nothing, so a chamfer scores half
# - which is also, measured, the whole difference between the corpus gland
# (every root chamfered) and a finished spool (every root radiused).
SHOULDER_CHAMFER_CREDIT = 0.5

# Score at/above -> band. Recalibrated against tests/design_corpus.py: the
# corpus's stated "minimum competent enclosure" (a filleted, chamfered,
# panelled, ribbed box with a solved counterbored bolt pattern) lands in the
# low 70s and the reference exemplar in the low 80s.
#
# The band names claim only what is measured. Nothing here can see whether a
# structural member is sculpted, whether an emblem is well placed, or whether a
# connector sits on a proper land - an A means "clears every bar this module can
# hold up", not "is a finished industrial design".
BANDS = (
    (88.0, "A", "meets every measured standard"),
    (70.0, "B", "good - minor refinement left"),
    (55.0, "C", "acceptable - visible roughness"),
    (38.0, "D", "draft - needs a refinement pass"),
    (0.0, "F", "raw - reads as an unstyled extrusion"),
)
# best -> worst, so max(rank) is the WORSE of two bands. Used to cap a band
# rather than to recompute it, because capping must never raise one.
_BAND_RANK = {band: i for i, (_cut, band, _lbl) in enumerate(BANDS)}
_BAND_LABEL = {band: lbl for _cut, band, lbl in BANDS}

MIN_COVERAGE = 0.60  # fraction of weight that must be measurable for a verdict

# Of that, how much may be excused BY ASSERTION rather than by geometry.
# MIN_COVERAGE alone let 40% of the rubric be waived, disabled or skipped on
# nothing but the author's say-so, which is a wider hole than any single metric.
# A written reason makes an excusal deliberate; it does not make it measured.
MAX_EXCUSED_WEIGHT = 0.25

# Face count above which the mirror booleans are skipped. Skipping is a COST
# decision and is reported as METRIC_ERROR, never as an exemption - see the
# error invariant. The floor exists only to catch a typo, because under the
# error invariant setting this low already costs the author the full weight.
SYMMETRY_MAX_FACES_DEFAULT = 6000
# 24 is below the face count of any part that has had a refinement pass at all
# (a filleted, chamfered box is already 26), so the floor only ever catches a
# typo. It does not need to be higher: under the error invariant a low value
# costs the author the metric's full weight, so the knob polices itself.
SYMMETRY_MAX_FACES_MIN = 24

# WHAT A MIRROR DIFFERENCE IS ALLOWED TO BE: A FUNCTIONAL INTERFACE.
#
# The symmetry metric scores the BEST of three mirror planes, so it has never
# asked a part to be symmetric about the axis its interfaces define. The defect
# was in the second term. Each mirror difference breaks into lumps, and the
# extent term charges the largest lump's bbox diagonal as a fraction of the
# part's - built, by its own docstring, to catch a difference that is "THIN BUT
# WIDE", such as a chamfer run applied to one rim and not its mirror. It only
# ever measured the WIDE half.
#
# Measured on parts/custom/reference_mast_node_enclosure: its best plane (YZ) is
# 0.87% asymmetric by volume - symmetric to the eye and to the number - and its
# largest difference lump is 52.0 x 48.0 x 33.0 mm, an aspect ratio of 1.6. That
# is not a sliver, it is the port-side circular connector bay: a compact chunk
# of functional interface. It spans 29.7% of the bbox diagonal, which cost the
# part 24.5 points on a term that exists to catch unmirrored chamfer runs.
#
# So the extent term now weighs each lump by how much of a SLIVER it is. A
# compact lump is a boss, a bay, a pad, an ear - its whole contribution to
# asymmetry is its volume, and the volume term already prices that at the right
# knots. A sliver is a break, a groove, a fin or a rib that exists on one side
# and not the other, and its volume is negligible by construction, which is
# exactly why a second term is needed for it at all.
#
# The ramp runs on longest / shortest bbox dimension. Measured on the corpus:
# the exemplar's connector bay is 1.6 and its bolt-boss lumps 2.8, while
# gamed_near_symmetry - one rim chamfered, one blade fin, one end notch, and
# built specifically to defeat a volume-only reading - carries lumps at 22 and
# above, and the exemplar's own unmirrored rim runs about its non-free planes
# read 85 and 89. Nothing real sits in the gap, so 3 -> 8 is a ramp across empty
# space rather than a cut through a population.
SLIVER_ASPECT_NONE = 3.0  # at or below: a chunk. The volume term's business.
SLIVER_ASPECT_FULL = 8.0  # at or above: a sliver, and its extent counts in full.

# --- metric status ------------------------------------------------------------
SCORED = "scored"  # a real 0-100 number, enters the weighted mean
NOT_REQUIRED = "not_required"  # the ROLE excludes it; renormalised OUT
ABSENT = "absent_defect"  # geometry implies it and it is missing; 0 at full weight
METRIC_ERROR = "error"  # could not be measured; 0 at full weight, cuts coverage

# Kept as a name because a lot of this module's own logic reads "is this a real
# number". It is the SCORED state; the old NOT_APPLICABLE is gone on purpose,
# because "inapplicable" was the audit's biggest single escape hatch.
OK = SCORED

METRIC_IDS = (
    "edge_break_coverage",
    "face_composition",
    "feature_composition",
    "pattern_discipline",
    "radius_vocabulary",
    "symmetry",
    "sharp_edge_length",
    "proportion",
)

# WHY form_discipline IS GONE
# It asked three questions - how much face area is accounted for, how many
# normal directions cover 90% of the planar area, and whether parallel plane
# positions repeat - and a PLAIN SHARP BOX is the global optimum of all three.
# It scored the corpus floor 100.0 at weight 0.14, the joint-largest in the
# enclosure rubric, and it scored 100.0 for thirteen of the twenty-six corpus
# cases and 87 or above for twenty-two of them. A metric that cannot separate
# the worst case in the corpus from the best is not a metric, it is a constant
# offset added to every part, and a constant that large flatters the floor most
# because the floor has nothing else. Its weight is redistributed across the
# metrics that do discriminate, in each role's own proportions, so no role's
# total bar moved. The one thing it measured that nothing else did - a surface
# made of shapes the reviewer cannot recognise - is now face_composition's
# unmeasured population, where it belongs and where the error invariant is
# already enforced.

# Fraction of a metric's population that may go unclassified before the metric
# is an ERROR rather than a score. Above the threshold the number would be a
# statement about the failure, not about the part.
DEGRADATION_MAX = {
    "edge_break_coverage": 0.10,
    "sharp_edge_length": 0.10,
    "face_composition": 0.15,
    "feature_composition": 0.10,
    "pattern_discipline": 0.10,
    "radius_vocabulary": 0.15,
    "symmetry": 0.0,
}

# THE COVERAGE INVARIANT: how much of the thing a metric CLAIMS to measure it
# must actually have looked at before its number is allowed to be a number.
#
# DEGRADATION_MAX polices the population a metric built. This polices whether
# that population was the part. The two are different failures and only the
# first was implemented: face_composition read planar faces only, so on a body
# of revolution - where the entire visible skin is one cylinder - it built a
# population of two end annuli, classified 100% of it, and reported SCORED at
# full weight having examined 14% of the exterior (3.7% on a 2 mm wall, where
# the end faces are narrower still). Measured, that paid a six-line tube
# 94.0/A. Every metric that works over a population now reports
# `examined_fraction`, and one that is below its floor here leaves through
# _degrade as an ERROR - zero at full weight, out of `coverage` - exactly like
# any other measurement that did not happen.
#
# The floors are calibrated on the corpus (measured 2026-07-26, every case
# rebuilt) and sit well under every reading a legitimate part produces, because
# this is a backstop against a metric being pointed at the wrong population,
# not a second quality bar.
#
#   face_composition    area. Floor 0.35. Corpus range 0.38 (gamed_soap_bar)
#                       to 1.00, exemplar 0.63, and the six-line tube that
#                       started all this reads 0.14 with the curved skin
#                       filtered out and 0.98 with it read.
#                       Re-measured 2026-07-26 after the denominator was fixed
#                       to keep curved break/blend skin - see _composable_faces.
#                       Every reading fell (the widest was gamed_soap_bar,
#                       0.77 -> 0.38, because half its exterior is blend); the
#                       floor stays at 0.35 because it still clears the worst
#                       GOOD case, good_turned_spool at 0.67, by nearly two to
#                       one, and the cases it now sits close to are the blobs
#                       whose exterior really is mostly fillet.
#   edge_break_coverage edge length. Floor 0.40. Corpus range 0.44 to 1.00.
#   sharp_edge_length   shares that population and that floor.
#
# WHY THE EDGE FLOOR IS 0.40 AND NOT HIGHER. The one case anywhere near it is
# gamed_facet_fillet at 0.44 - plan corners faked with five 18 degree facets,
# built to duck SHARP_MIN_DEG - and its unexamined length is real: length that
# ducks a threshold is length that was not judged, so it is reported rather
# than hidden. But the floor is not what catches that part; the metric already
# does, scoring it edge_break_coverage 0.0 because its rims stay knife edges.
# Erroring it as well would put a faceted blob BELOW a plain sharp extrusion,
# which tests/design_corpus.py's `base_is_floor` contract forbids, and rightly:
# the floor of the ladder is "no refinement at all", and an unmeasurable part
# is not worse than that. A many-segment polylined profile on a real part would
# read the same way for an entirely innocent reason.
#
# The metrics with no population of their own - symmetry (the whole solid) and
# proportion (the bounding box) - have nothing to be partial about and carry no
# floor. See the audit table in the module docstring.
EXAMINED_MIN = {
    "face_composition": 0.35,
    "edge_break_coverage": 0.40,
    "sharp_edge_length": 0.40,
}


# ---------------------------------------------------------------------------
# Floors: the metrics no weighted average may launder
# ---------------------------------------------------------------------------
# WHY FLOORS EXIST AT ALL
# Everything else in this module is a contribution to a weighted MEAN, and a
# mean is exactly the thing an agent optimising against a gate learns to
# arbitrage: pick the role whose column is lightest on the metric you fail,
# spend one waiver, and the remaining metrics carry you over the bar. The
# measured worst part that could still pass a hard 70 gate was a flat
# 220 x 150 x 9 slab with three sunken pockets and ten border holes on which NOT
# ONE EDGE IS BROKEN ANYWHERE - pocket walls meeting the top face as raw knife
# edges, raw hole mouths, raw top and bottom rims - scoring edge_break_coverage
# 0.0 and landing 85.6/B.
#
# A floor is immune to every one of those moves, because it is not a
# contribution to anything. It is a hard minimum on a SINGLE metric, checked
# after the mean is computed and independent of it, so it cannot be
# renormalised out, averaged away, waived, or shifted by a role choice. "Not one
# edge on this part is broken" is disqualifying on its own terms, and no
# arithmetic over the other seven metrics should be able to launder it.
#
# WHAT A FLOOR IS NOT
# A floor is not a second opinion about quality, and its level is not a target.
# It is the line below which the metric stops describing a design and starts
# describing the absence of one. A floor that fires on a legitimately good part
# is worse than no floor - it teaches agents that the gate is noise - so each
# one below is calibrated against the LOWEST score any `good` case in
# tests/design_corpus.py reaches under its own role, with the margin stated.
@dataclass(frozen=True)
class Floor:
    """
    One metric's hard minimum, and the sentence that justifies its level.

    `key` is which number in the metric's report the floor is held against.
    It defaults to the metric's own score, and it exists because
    edge_break_coverage is a COMPOSITE - 0.85 body plus 0.15 bore/detail rim -
    and flooring the composite floored the wrong thing. The rim term alone is
    worth 15.0 against a floor of 10.0, so a part on which not one body corner
    is broken cleared the floor named after exactly that defect by deburring its
    bore mouths. The two terms measure different things and must not substitute
    for each other; the floor therefore reads `body_score`.
    """

    metric: str
    score: float
    why: str
    key: str = "score"
    label: str = "scored"


# Only two metrics carry a floor, and the six that do not are listed underneath
# with the reason, because "we floored everything" is how a floor set stops
# being believable.
#
#   measured 2026-07-26 over the 27-case corpus, ON THE QUANTITY THE FLOOR
#   READS (lowest `good` case under its own role, then the exemplar, then this
#   floor):
#
#   edge_break_coverage.body_score  good min 24.2 (sheet bracket)  exemplar 100.0  floor 10
#   sharp_edge_length.score         good min 78.3 (sealed cover)   exemplar 100.0  floor 25
#
#   Re-run of the audit's misfire set at the same time, none of which trips a
#   floor: turned spool 100.0/100.0, turned knob 100.0/100.0, turned spacer
#   100.0/100.0, handed L-bracket 100.0/100.0, 4 mm cover 100.0/100.0.
RUBRIC_FLOORS: dict[str, Floor] = {
    "edge_break_coverage": Floor(
        "edge_break_coverage",
        10.0,
        "a part on which essentially no BODY corner is broken has not had a "
        "refinement pass at all. 10 is a body coverage of about 23% (the term is "
        "zero at or below 15% and 100 at 92%). It is held against the BODY term, "
        "not the 0.85/0.15 composite: the rim term alone is worth 15.0, so "
        "deburring the bore mouths of an otherwise raw box used to clear a floor "
        "of 10 while not one corner of the part was broken. Measured under this "
        "key over the corpus, the lowest body term any good case reaches under "
        "its own role is the sheet bracket's 24.2 - so the margin is 14.2, and "
        "the next lowest is the sealed cover at 63.8",
        key="body_score",
        label="its body term",
    ),
    "sharp_edge_length": Floor(
        "sharp_edge_length",
        25.0,
        "the same defect measured in absolute length rather than as a fraction: "
        "25 is 5.3 bbox diagonals of unbroken convex edge, against the 6.9 a "
        "completely raw rectangular prism measures. A part can hold a passable "
        "break FRACTION on a small edge population while carrying a whole prism "
        "of raw edge, and this is the only metric that sees that. The lowest "
        "good corpus case is the sealed cover at 78.32, so the margin is 53",
    ),
}

# WHY THE OTHER SIX HAVE NO FLOOR
#   face_composition     the good set itself reaches 13.93 (ladder_5_bolted, a
#                        legitimately plain bolted box). There is no level below
#                        that worth having.
#   radius_vocabulary    it is the one metric whose reference standard lives
#                        OUTSIDE the part - lib/features.py's ladder - and with
#                        style.radius_ladder retired there is no longer any
#                        per-part route to declare a different one. A floor here
#                        would hard-fail a part for holding a coherent
#                        vocabulary that is not this repo's, which is a
#                        different complaint from the one a floor should make.
#   feature_composition  ABSENT is legitimate on a part that genuinely has no
#                        features (a blank lid), and the floor could not tell
#                        that from a part that scattered them.
#   pattern_discipline   two functionally-placed holes are not a failed pattern.
#   symmetry             handedness is a real design decision; the good min is
#                        100 only because no corpus case is handed.
#   proportion           it does not discriminate: 93 or above on every case in
#                        the corpus except one. A floor on a constant is theatre.

# The best band a part with an unmet floor may be REPORTED at. "D - draft,
# needs a refinement pass" is not a punishment, it is the literal description of
# a part that has not broken its edges, and it sits below the advisory gate
# (70.0 = band B) so an unmet floor can never read as a pass.
FLOOR_BAND_CAP = "D"

# How far WAIVERS may move the score away from the same measurements scored with
# nothing excused, before that is an ERROR rather than a disclosure.
#
# 25.0 is not a taste. A waiver renormalises a metric out of the mean, so if the
# excused weight is x and the remaining metrics average S, the score goes from
# (1 - x) * S to S and the gain is x * S <= 100 * x. MAX_EXCUSED_WEIGHT caps x at
# 0.25, so 25.0 is the exact arithmetic ceiling on what every waiver a spec is
# allowed to write can be worth put together. A waiver delta past it is not a
# large assertion, it is an impossible one, and means something other than the
# waivers moved the score.
#
# THIS USED TO BE THE CAP ON THE ROLE AND THE WAIVERS TOGETHER, and that was the
# mis-calibration: a bound derived from what waivers can buy was applied to a
# sum that also contains what a role is worth, and the role with the largest
# legitimate delta is `sheet`. Measured on this repo, post-frame-port, on parts
# that are honest sheet metal and declare it:
#
#     part                                as sheet   as enclosure   role delta
#     an ordinary formed 2 mm L-bracket       77.2           44.7        +32.5
#     a 3 mm Z-section bracket                73.7           54.2        +19.6
#     tests/design_corpus good_sheet_bracket  82.0           68.0        +13.9
#
# The first is a correct part making a correct role claim - 2 mm stock, one
# 90 degree bend on a real R2.5 inner radius, a 3 x 2 mounting pattern in the
# base and a 2 x 2 pattern in the leg, a blanked perimeter with nothing broken
# on it because 2 mm stock cannot carry a break there. It clears the 70 gate as
# the sheet part it is, and the old single 25.0 cap made it a configuration
# ERROR - so under a hard design gate the gate failed good work, which is the
# one thing a gate must never do.
#
# The other roles are nowhere near it, which is why one number hid this for so
# long: cover +15.1, plate +9.5, structural +5.7, bracket +4.7, enclosure 0.0.
# See ROLE_DELTA_ALLOWANCE for what replaced the single cap.
MAX_CONFIG_DELTA = 25.0


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rubric:
    """
    One role's rubric: which metrics apply, how they are weighted, and where
    the role-sensitive knots sit.

    A role is a claim about what the part IS FOR, and the only thing it may do
    is excuse a metric that the part's function genuinely contradicts. It is
    never a way to opt out of refinement: every column of `weights` sums to
    1.00, so lightening one metric always makes another heavier.

    `claim` states, in one line, the GEOMETRIC proposition the role asserts.
    ROLE_GUARDS holds the predicate that checks it against the measured B-rep,
    and every relaxation this rubric makes must be paid for by that claim.
    """

    role: str
    weights: dict[str, float]
    # face_composition knots: (worst_best, worst_zero, mean_best, mean_zero)
    void_knots: tuple[float, float, float, float]
    # proportion knots (best, zero)
    proportion_knots: tuple[float, float] = (3.0, 16.0)
    # sheet metal: the blanked perimeter is not a design surface
    exclude_blank_perimeter: bool = False
    note: str = ""
    claim: str = ""

    def applies(self, mid: str) -> bool:
        return mid in self.weights


def _rubric(role, weights, void_knots, **kw) -> Rubric:
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"role {role} weights sum to {total}, not 1.0")
    return Rubric(role=role, weights=weights, void_knots=void_knots, **kw)


ROLE_RUBRICS: dict[str, Rubric] = {
    # The default, and deliberately the strictest: declaring a role must always
    # be a deliberate act of claiming a lighter rubric, never an accident.
    #
    # Every column below is form_discipline's old weight redistributed across
    # the rest of that role's own column, in its own proportions, so no role's
    # total bar moved and no role's internal balance moved either.
    "enclosure": _rubric(
        "enclosure",
        {
            "edge_break_coverage": 0.21,
            "face_composition": 0.19,
            "feature_composition": 0.16,
            "pattern_discipline": 0.12,
            "radius_vocabulary": 0.11,
            "symmetry": 0.07,
            "sharp_edge_length": 0.07,
            "proportion": 0.07,
        },
        (0.25, 0.60, 0.18, 0.50),
        note="a housing: every exterior face is a product surface",
        claim="",  # the fallback rubric asserts nothing, so nothing can be false
    ),
    "cover": _rubric(
        "cover",
        {
            # face_composition is NOT discounted here beyond its relaxed knots.
            # Discounting the weight as well double-excused a blank lid: a plain
            # chamfered slab with four corner counterbores and no surface
            # composition at all measured 89.5 as a cover at weight 0.10.
            "edge_break_coverage": 0.19,
            "face_composition": 0.19,
            "feature_composition": 0.16,
            "pattern_discipline": 0.19,
            "radius_vocabulary": 0.11,
            "symmetry": 0.08,
            "sharp_edge_length": 0.08,
        },
        (0.55, 0.95, 0.30, 0.65),
        note="a lid: thin by function, and its sealing face is flat by function",
        claim="thin by function",
    ),
    "plate": _rubric(
        "plate",
        {
            "edge_break_coverage": 0.19,
            "face_composition": 0.11,
            "feature_composition": 0.19,
            "pattern_discipline": 0.23,
            "radius_vocabulary": 0.12,
            "symmetry": 0.08,
            "sharp_edge_length": 0.08,
        },
        # Calibrated against this role's own good reference rather than guessed:
        # the corpus's optical interface plate, an M6 grid at a constant 25 mm
        # pitch, measures worst 0.253 / mean 0.202. A plate whose largest empty
        # circle is a third of its silhouette scale is not carrying a pattern.
        (0.30, 0.70, 0.22, 0.55),
        note="an interface: thin by function, and IS its hole pattern",
        claim="thin by function",
    ),
    # `bracket` USED TO DROP `proportion`, and that was the last place a role
    # relaxed something its guard says nothing about. "Solid material, not a
    # shell" is a statement about the interior area fraction; `proportion` is
    # max/min of the bounding box, which solidity neither bounds nor implies.
    # Every other role that drops it has a guard that pins the same ratio -
    # `_guard_thin` forces max/min >= 4 and `_guard_sheet` forces >= 10 - so on
    # those the exclusion is the geometry's own doing. On `bracket` it was free:
    # measured, a 160 x 100 x 6 thin cover claiming `bracket` scored 0 on
    # proportion as an enclosure and simply did not have to, worth +14.7 to band
    # A. Restored here at the default role's weight and the default knots, with
    # the other seven scaled by 0.93 and rounded to the hundredth; the column
    # still sums to 1.00, so this lowers no bar.
    "bracket": _rubric(
        "bracket",
        {
            "edge_break_coverage": 0.20,
            "face_composition": 0.13,
            "feature_composition": 0.15,
            "pattern_discipline": 0.15,
            "radius_vocabulary": 0.13,
            "symmetry": 0.08,
            "sharp_edge_length": 0.09,
            "proportion": 0.07,
        },
        (0.40, 0.80, 0.25, 0.58),
        note="solid material, so every free edge genuinely can be broken",
        claim="solid material, not a shell",
    ),
    "sheet": _rubric(
        "sheet",
        {
            # The 0.08 that sharp_edge_length and proportion carry elsewhere is
            # redistributed here, not dropped: a role may excuse a metric, never
            # lighten the total bar.
            "edge_break_coverage": 0.13,
            "face_composition": 0.20,
            "feature_composition": 0.22,
            "pattern_discipline": 0.22,
            "radius_vocabulary": 0.13,
            "symmetry": 0.10,
        },
        (0.45, 0.85, 0.28, 0.62),
        exclude_blank_perimeter=True,
        note="formed from flat stock: the blanked perimeter cannot carry a break",
        claim="formed from flat stock, enclosing no void",
    ),
    "structural": _rubric(
        "structural",
        {
            "edge_break_coverage": 0.21,
            "face_composition": 0.14,
            "feature_composition": 0.14,
            "pattern_discipline": 0.12,
            "radius_vocabulary": 0.14,
            "symmetry": 0.07,
            "sharp_edge_length": 0.08,
            "proportion": 0.10,
        },
        (0.35, 0.75, 0.22, 0.55),
        proportion_knots=(5.0, 25.0),
        note="a sculpted member: legitimately long, and legitimately blended",
        claim="a long member",
    ),
}


# ---------------------------------------------------------------------------
# Role guards: the geometry has to agree with the claim
# ---------------------------------------------------------------------------
def _guard_thin(topo: Topology) -> str | None:
    """
    A cover and a plate relax the emptiness knots - and DROP `proportion`
    outright - for being thin. Thin relative to BOTH of the dimensions it spans,
    not merely to the longest, which is the same defect `_guard_long` carried:
    min/max alone is satisfied by any LONG BAR the moment it is slender, and
    `proportion` is a max/min ratio, so a bar is exactly the shape that profits
    from dropping it.

    Measured before this test existed: a 300 x 40 x 30 bar went 80.0/B honest to
    90.5/A as a `cover`, a 400 x 60 x 40 bar 79.8 to 91.0/A, and THE REPO'S OWN
    SCAFFOLD - parts/_template, a 153 x 90 x 34 enclosure - 86.0/B to 91.1/A.
    All three measure 0.100 or better on min/max and are nowhere near thin.

    min/mid is what a lid has and a bar does not, and it separates the two
    without being a cliff either side of anything real: measured over the corpus
    and both exemplars, the plate reference 0.092, the cover reference 0.114 and
    the repo's example plate 0.100, against the bars at 0.667 and 0.750, the
    structural arm at 0.462 and the scaffold at 0.378.
    """
    dims = sorted(topo.bbox_size())
    if dims[2] <= 1e-9 or dims[1] <= 1e-9:
        return "degenerate bounding box"
    ratio = dims[0] / dims[2]
    if ratio > THIN_MAX_ASPECT:
        return (
            f"its thinnest dimension is {ratio:.2f} of its longest "
            f"(max {THIN_MAX_ASPECT:.2f}), so it is not thin by function"
        )
    across = dims[0] / dims[1]
    if across > THIN_MAX_ASPECT:
        return (
            f"its thinnest dimension is {across:.2f} of its SECOND longest "
            f"(max {THIN_MAX_ASPECT:.2f}), so it is a bar or a body rather than "
            f"something thin by function"
        )
    return None


def _guard_sheet(topo: Topology) -> str | None:
    """
    A sheet part excludes its whole blanked perimeter from the edge population AND
    drops `sharp_edge_length`, which is the only role exclusion in the repo that
    removes a rubric floor. So it has to be thin stock in absolute millimetres,
    open on both sides of that stock, and actually FORMED - all four
    measurements, because each of the first three has been talked past on its
    own:

    * 2 * volume / area recovers the WALL thickness of a hollow enclosure just as
      happily as the stock thickness of a blank (a 3 mm walled 90 x 60 x 30 box
      derives 2.99 mm), so the interior fraction has to answer that;
    * the thickness test is RELATIVE, so a solid 200 x 120 x 12 milled slab
      derives 10.18 mm, calls it 5% of the part and passes - and 12 mm plate
      carries a chamfer on its outline perfectly well, which is the exclusion's
      whole excuse. Measured before this test existed: that slab went 70.3/B
      honest to 89.2/A as `sheet` with the sharp_edge_length floor not emitted at
      all, and its knife-edged sibling went 44.5 with that floor UNMET to 68.4
      with it gone;
    * "carries a small blend radius" is not forming. That same milled slab
      reports four of them, one per plan-radiused corner. A bend is a coaxial
      PAIR of cylinders separated by the material thickness, and it reports zero.

    Measured after all four, over the 31-case corpus plus both exemplars: the
    corpus's own formed bracket passes with 2.00 mm stock, 6% interior and 2 bend
    pairs, and it is the ONLY solid of the 33 that can still claim `sheet` - down
    from five, of which four were solid machined parts.
    """
    size = max(topo.bbox_size())
    if size <= 1e-9:
        return "degenerate bounding box"
    t = topo.sheet_thickness
    if t > SHEET_THICKNESS_MAX_FRACTION * size:
        return (
            f"its derived stock thickness is {t:.1f} mm on a {size:.0f} mm part "
            f"(max {SHEET_THICKNESS_MAX_FRACTION:.0%}), so it is not sheet metal"
        )
    if t > SHEET_STOCK_MAX_MM:
        return (
            f"its derived stock thickness is {t:.1f} mm (max {SHEET_STOCK_MAX_MM:.0f} mm), "
            f"which is plate rather than sheet - and plate carries a chamfer on its own "
            f"outline, so nothing pays for excluding it"
        )
    inner = topo.interior_area_fraction()
    if inner is None:
        return "interior reachability could not be resolved, so the claim cannot be checked"
    if inner > SHEET_INTERIOR_MAX_FRACTION:
        return (
            f"{inner:.0%} of its face area faces an enclosed void "
            f"(max {SHEET_INTERIOR_MAX_FRACTION:.0%}) - a formed blank has no inside"
        )
    # ... and it has to be FORMED. The exclusion is justified by "2 mm stock
    # cannot carry a chamfer on the blanked perimeter, so judge the formed radii
    # instead", and on an unformed part there are none: the role deletes the
    # entire silhouette from the edge population and offers nothing in its place,
    # which is how a raw 120 x 80 x 2 blank with four countersunk rivet holes
    # reached edge_break_coverage 55.6 (100.0 with cleanly chamfered mouths) on a
    # part where NOTHING is broken but the holes. A flat plate is a `plate`, and
    # `plate` does not excuse its own outline. This test reads bend_pairs() and
    # not formed_radii(): the latter counts any small blend cylinder, so four
    # plan radii milled into the outline of a 220 x 140 x 4 knife-edged blank read
    # as four "bends" and carried it to 68.7 with the floor gone against 47.4
    # honestly.
    if topo.bend_pairs() < 1:
        return (
            "it carries no bend at all - no pair of coaxial faces separated by its own "
            "material thickness - so it is a blank or a machined solid rather than a "
            "formed part, and the blanked-perimeter exclusion this role grants is paid "
            "for by the formed radii it would be judged on instead"
        )
    return None


def _guard_solid(topo: Topology) -> str | None:
    """A bracket relaxes composition for being solid material, not a shell."""
    inner = topo.interior_area_fraction()
    if inner is None:
        return "interior reachability could not be resolved, so the claim cannot be checked"
    if inner > BRACKET_INTERIOR_MAX_FRACTION:
        return (
            f"{inner:.0%} of its face area faces an enclosed void "
            f"(max {BRACKET_INTERIOR_MAX_FRACTION:.0%}) - this is a housing, not a bracket"
        )
    return None


def _guard_long(topo: Topology) -> str | None:
    """
    A structural member relaxes the proportion knots - and the emptiness knots -
    for being long. Long relative to its whole CROSS-SECTION, not merely to its
    thinnest dimension: max/min alone is satisfied by any slab the moment it is
    thin, and a 200 x 150 x 42 slab did exactly that at 4.76 against a 4.0 bar,
    collecting a measured +6.9 points as "a long member". max/mid is what a
    member has and a slab does not - the corpus's structural arm measures 2.67
    on it and that slab 1.33.
    """
    dims = sorted(topo.bbox_size())
    if dims[0] <= 1e-9 or dims[1] <= 1e-9:
        return "degenerate bounding box"
    ratio = dims[2] / dims[0]
    if ratio < STRUCTURAL_MIN_ASPECT:
        return (
            f"its longest dimension is only {ratio:.1f} x its shortest "
            f"(min {STRUCTURAL_MIN_ASPECT:.1f}), so it is not a long member"
        )
    slender = dims[2] / dims[1]
    if slender < STRUCTURAL_MIN_SLENDERNESS:
        return (
            f"its longest dimension is only {slender:.1f} x its SECOND longest "
            f"(min {STRUCTURAL_MIN_SLENDERNESS:.1f}), so it is a slab rather than a "
            f"long member"
        )
    return None


# role -> predicate(topo) -> None when the geometry agrees with the claim, or a
# sentence saying how it does not. `enclosure` is the fallback and claims
# nothing, so it needs no guard and can never be contradicted.
ROLE_GUARDS: dict[str, object] = {
    "cover": _guard_thin,
    "plate": _guard_thin,
    "sheet": _guard_sheet,
    "bracket": _guard_solid,
    "structural": _guard_long,
}

ROLES = tuple(ROLE_RUBRICS)
DEFAULT_ROLE = "enclosure"

# Kept as a name because lib/evaluate.py imports it. It is the default role's
# weights; METRIC_IDS is the authoritative set of metric ids.
DEFAULT_WEIGHTS = dict(ROLE_RUBRICS[DEFAULT_ROLE].weights)


def rubric_relaxations(rubric: Rubric) -> tuple[str, ...]:
    """
    Every way this role's rubric is lighter than the default's, named.

    A GUARD MUST MEASURE EVERYTHING ITS ROLE RELAXES, and three separate audits
    found the same defect because that rule was checked by reading the guards
    rather than by enumerating the relaxations: `_guard_sheet` measured
    thickness but not forming, `_guard_long` measured length but not
    slenderness, and `bracket` dropped `proportion` on a claim about its
    interior. Each was invisible because the list of things needing a guard was
    written by hand, and a hand-written list only ever contains what somebody
    remembered.

    So it is derived from the rubric itself. A role that adds an exclusion, or a
    role added from scratch, changes this tuple the moment it is declared, and
    tests/test_role_guards.py fails until a probe exists proving the guard
    refuses a part that helps itself to it. Weight redistribution is deliberately
    NOT a relaxation: every column sums to 1.00, so lightening one metric always
    makes another heavier and the total bar cannot move.

    Names are stable strings rather than an enum because they are dictionary keys
    in the test's probe registry, and a rename should break it loudly.
    """
    default = ROLE_RUBRICS[DEFAULT_ROLE]
    out: list[str] = []
    for mid in default.weights:
        if mid not in rubric.weights:
            out.append(f"drop:{mid}")
    if rubric.void_knots != default.void_knots:
        out.append("relax:void_knots")
    if rubric.proportion_knots != default.proportion_knots:
        out.append("relax:proportion_knots")
    if rubric.exclude_blank_perimeter != default.exclude_blank_perimeter:
        out.append("exclude:blank_perimeter")
    return tuple(out)


def _measures_differently(rubric: Rubric, default: Rubric, mid: str) -> bool:
    """
    Whether this role changes what a metric MEASURES, not merely what it weighs.

    Two metrics can: `edge_break_coverage` reads a different edge population
    when the role excludes the blanked perimeter, and `face_composition` and
    `proportion` are scored against role-sensitive knots. For those the role's
    score and the default's are two different numbers about the same solid, and
    the difference is not bounded by the weight difference.
    """
    if mid == "edge_break_coverage":
        return rubric.exclude_blank_perimeter != default.exclude_blank_perimeter
    if mid == "face_composition":
        return rubric.void_knots != default.void_knots
    if mid == "proportion":
        return rubric.proportion_knots != default.proportion_knots
    return False


def _role_delta_bound(rubric: Rubric) -> float:
    """
    The most a role's own rubric can be worth against the default, on any solid.

    Not a sample. For a metric both rubrics measure the same way the role can
    only move it by the WEIGHT it changed, and only upward when it raised that
    weight, so its contribution is bounded by 100 * max(0, w_role - w_default).
    For a metric the role measures differently the two scores are unrelated and
    the bound is the whole of the role's own weight, 100 * w_role. Summed, that
    is the largest number a correct role claim can possibly produce.

    Why the bound and not the measured maximum. This cap's job is to notice a
    knob that is NOT the role, and the role itself is already checked against
    the B-rep by ROLE_GUARDS - a claim the geometry contradicts never reaches
    here. A cap set from three sheet-metal brackets would refuse the fourth, and
    refusing correct work is a worse failure than a loose backstop on a
    quantity that is separately guarded. Set from the rubric, it can only ever
    fire when the delta is not explicable by the role at all.

    Measured against real parts it is not theatre: `sheet` bounds at 54.0 and
    the widest honest sheet part measured here reaches 32.5, `cover` bounds at
    28.0 against 15.1 measured, `plate` at 28.0 against 9.5, `bracket` at 26.0
    against 4.7, `structural` at 28.0 against 5.7. `enclosure` bounds at exactly
    0.0, because it IS the default rubric and its role delta is identically zero
    - so the default role gets no role budget at all, which is the property the
    single old cap could not express.
    """
    default = ROLE_RUBRICS[DEFAULT_ROLE]
    total = 0.0
    for mid, w in rubric.weights.items():
        if _measures_differently(rubric, default, mid):
            total += w
        else:
            total += max(0.0, w - default.weights.get(mid, 0.0))
    return round(100.0 * total, 1)


#: role -> how much that role's own rubric may be worth, in points, before the
#: delta is not explained by the role. Derived from the weights themselves, so it
#: cannot drift out of step with ROLE_RUBRICS the way a written table would.
ROLE_DELTA_ALLOWANCE: dict[str, float] = {
    role: _role_delta_bound(rubric) for role, rubric in ROLE_RUBRICS.items()
}


def config_delta_caps(role: str) -> tuple[float, float]:
    """(role allowance, waiver allowance) in points, for one role."""
    return ROLE_DELTA_ALLOWANCE.get(role, 0.0), MAX_CONFIG_DELTA


def resolve_rubric(role: str | None) -> tuple[Rubric, str | None]:
    """The rubric for a role name, plus an error string for an unknown one."""
    if role is None:
        return ROLE_RUBRICS[DEFAULT_ROLE], None
    if not isinstance(role, str) or role not in ROLE_RUBRICS:
        return (
            ROLE_RUBRICS[DEFAULT_ROLE],
            f"unknown design role {role!r} (known: {', '.join(ROLES)}) - "
            f"reviewed as {DEFAULT_ROLE}",
        )
    return ROLE_RUBRICS[role], None


def check_role_claim(role: str, topo: Topology) -> str | None:
    """
    Does the measured geometry support what `role` claims about it?

    Returns None when it does, or a sentence saying how it does not. `role` is
    assumed already resolved by resolve_rubric(); an unknown role has no guard
    and reaches this function only as `enclosure`, which claims nothing.
    """
    guard = ROLE_GUARDS.get(role)
    if guard is None:
        return None
    try:
        return guard(topo)
    except Exception as exc:  # a guard that cannot run must not clear the claim
        return f"the {role} claim could not be checked: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# lib/features.py bridge (defensive - that module is written in parallel)
# ---------------------------------------------------------------------------
def _features_module():
    try:
        import lib.features as features  # noqa: PLC0415
    except Exception:
        return None
    return features


_LADDER_ATTRS = ("radius_ladder", "break_ladder", "radii", "fillet_ladder", "chamfer_ladder")


def _load_ladder() -> tuple[tuple[float, ...], str]:
    """
    The set of allowed break sizes, preferring lib/features.py's Style.

    Both ladders are taken and merged: this module measures plan-corner fillet
    radii AND chamfer legs in one vocabulary, so a Style that separates
    `radius_ladder` (plan corners) from `break_ladder` (rim breaks) must
    contribute both or every rim chamfer reads as off-ladder.

    Returns (ladder, provenance). Never raises: an absent or renamed symbol
    falls back to the local default and says so in the report.
    """
    mod = _features_module()
    if mod is None:
        return DEFAULT_RADIUS_LADDER, "lib.design_review default (lib.features not importable)"

    def numeric(val) -> list[float] | None:
        if isinstance(val, (list, tuple)) and val and all(isinstance(v, (int, float)) for v in val):
            return [float(v) for v in val]
        return None

    found: list[float] = []
    sources: list[str] = []
    for name in ("RADIUS_LADDER", "BREAK_LADDER", "RADII", "FILLET_LADDER"):
        vals = numeric(getattr(mod, name, None))
        if vals:
            found += vals
            sources.append(f"lib.features.{name}")

    style_obj = getattr(mod, "STYLE", None) or getattr(mod, "Style", None)
    if style_obj is not None:
        try:
            style_obj = style_obj() if isinstance(style_obj, type) else style_obj
        except Exception:
            pass
        for name in _LADDER_ATTRS:
            vals = numeric(getattr(style_obj, name, None))
            if vals:
                found += vals
                sources.append(f"lib.features.Style.{name}")

    if found:
        return tuple(sorted(set(found))), " + ".join(sources)
    return DEFAULT_RADIUS_LADDER, "lib.design_review default (no ladder found in lib.features)"


def _builder(names: str | tuple[str, ...], fallback: str) -> str:
    """
    Cite lib/features.py builders, but only the ones that actually exist right
    now. That module is authored separately, so a finding must never send an
    agent after a symbol that was renamed - it falls back to plain instructions.
    """
    mod = _features_module()
    if isinstance(names, str):
        names = (names,)
    live = [n for n in names if mod is not None and hasattr(mod, n)]
    if live:
        return " / ".join(f"lib.features.{n}()" for n in live)
    return fallback


def _ray_hits(shape: cq.Shape, origin: cq.Vector, direction: cq.Vector) -> list[float]:
    """
    Sorted ray/solid intersection parameters, via lib/features.py's caster.

    Reused rather than reimplemented so exterior classification, relief probing
    and lib.features.wall_at() all agree about what "the ray hit something"
    means. Falls back to a local copy only if that module cannot be imported.
    """
    mod = _features_module()
    fn = getattr(mod, "_ray_hits", None) if mod is not None else None
    if fn is not None:
        return fn(shape, origin, direction)
    from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter  # noqa: PLC0415
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt  # noqa: PLC0415

    inter = BRepIntCurveSurface_Inter()
    inter.Init(
        shape.wrapped,
        gp_Lin(
            gp_Pnt(origin.x, origin.y, origin.z),
            gp_Dir(direction.x, direction.y, direction.z),
        ),
        1e-6,
    )
    hits: list[float] = []
    while inter.More():
        hits.append(inter.W())
        inter.Next()
    hits.sort()
    out: list[float] = []
    for h in hits:
        if not out or abs(h - out[-1]) > 1e-4:
            out.append(h)
    return out


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _shape(obj) -> cq.Shape:
    """Accept a Workplane or a Shape."""
    return obj.val() if hasattr(obj, "val") else obj


def _canonical_partition(shape: cq.Shape) -> cq.Shape:
    """
    The same solid, with faces that lie on ONE surface written as one face.

    How a B-rep is cut into faces is a property of the file, not of the part. A
    face split into coplanar pieces is the same face; the split is what a
    boolean leaves behind, what a round trip through another kernel produces,
    and what an author can do deliberately because it used to pay. It paid
    because every per-face measurement is computed against the face's own
    extent: halve a face and each half's largest empty region is smaller
    relative to its own silhouette, so `face_composition` rose for nothing.
    Measured before this call existed, cutting and re-fusing the invariance
    probes moved face_composition by up to 44.2 points and ALWAYS upward, and
    `edge_break_coverage` by 7.2.

    `ShapeUpgrade_UnifySameDomain` is the canonical form: it merges only faces
    that share an underlying surface and edges that share an underlying curve,
    so it changes no geometry - a tangent blend and the wall it runs into are
    different surfaces and stay two faces. If it fails or returns something
    unusable the original shape is measured, because a partition that could not
    be canonicalised is still a part.
    """
    shape = _shape(shape)
    try:
        tool = ShapeUpgrade_UnifySameDomain(shape.wrapped, True, True, False)
        tool.Build()
        merged = cq.Shape.cast(tool.Shape())
    except Exception:
        return shape
    if merged is None or not merged.Faces():
        return shape
    return merged


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _article(word: str | None) -> str:
    """ "a" or "an". Every report line and every DESIGN.md copied from one said
    "as a enclosure", which is the first thing a reader sees about the rigour of
    the thing doing the measuring."""
    return "an" if word and word[0].lower() in "aeiou" else "a"


def _lerp_score(value: float, best: float, worst: float) -> float:
    """
    Linear 0-100 score. `best` maps to 100, `worst` maps to 0, monotonic in
    between and clamped outside. Works for both directions (best may be the
    larger or the smaller number).
    """
    if best == worst:
        return 100.0
    return 100.0 * _clamp((value - worst) / (best - worst))


VOID_KNEE = 10.0  # score at the "zero" knot
VOID_TAIL = 0.35  # how far past it the score takes to reach a true zero


def _lerp_void(value: float, best: float, zero: float) -> float:
    """
    0-100 for an emptiness measure, with a graded tail past the zero knot.

    A hard clamp at `zero` is the same cliff the audit found in the metric this
    replaces: every raw face lands on the floor and the measure stops
    distinguishing "bare" from "slightly less bare". So `zero` maps to VOID_KNEE
    rather than to 0, and only VOID_TAIL beyond it does the score run out. That
    keeps a plain box strictly below a plain box with three holes in it, which
    is a real if small difference, without paying a heavily filleted body 10
    points for having no flat left to be empty.
    """
    if value <= zero:
        return _lerp_score(value, best=best, worst=zero) * (100.0 - VOID_KNEE) / 100.0 + VOID_KNEE
    return VOID_KNEE * _clamp(1.0 - (value - zero) / VOID_TAIL)


def _cv(values: list[float]) -> float | None:
    """Coefficient of variation; None when it is not defined."""
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    mean = statistics.fmean(vals)
    if mean <= 1e-9:
        return None
    return statistics.pstdev(vals) / mean


def _metric(mid: str, status: str, score: float | None, message: str, **detail) -> dict:
    return {"id": mid, "status": status, "score": score, "message": message, **detail}


def _degrade(
    metric: dict,
    population: float,
    unmeasured: float,
    reasons: list[str] | None = None,
    *,
    examined: float | None = None,
    relevant: float | None = None,
) -> dict:
    """
    Attach this metric's degradation AND examination accounting, and demote it
    to ERROR when it classified too little of its population or looked at too
    little of the part.

    THE ERROR INVARIANT. The audit's worst finding was that when every
    convexity probe failed, edge_break_coverage reported a perfect 100.0 with
    coverage 1.00 - because unresolved edges were removed from the DENOMINATOR
    instead of from the METRIC. A measurement that did not happen must never
    produce a number, least of all a flattering one.

    THE COVERAGE INVARIANT, which is `examined`/`relevant`, is the same rule
    one level up, and it is the half the first implementation left out. Every
    check above is about the population the metric BUILT; nothing anywhere
    asked whether that population was the part. face_composition built its
    population from planar faces only, so on a turned part it reported SCORED
    at full weight having examined 14% of the exterior - a number, a band
    and a rank, all from a measurement that never happened. `relevant` is what
    the metric claims to measure, `examined` is what it did measure, and below
    EXAMINED_MIN the metric leaves by the same door every other failed
    measurement leaves by. A metric may not return a score for a part it did
    not look at.
    """
    mid = metric["id"]
    frac = (unmeasured / population) if population > 1e-12 else 0.0
    metric["population"] = round(population, 4)
    metric["unmeasured"] = round(unmeasured, 4)
    metric["unmeasured_fraction"] = round(frac, 4)
    if reasons:
        metric["unmeasured_reasons"] = reasons[:3]
    limit = DEGRADATION_MAX.get(mid, 0.10)
    # NOT_REQUIRED is included on purpose: "there was nothing to measure" and
    # "nothing could be measured" look identical from inside a metric, and the
    # audit's worst case is exactly the second wearing the first's clothes.
    # (A role exclusion or a spec waiver never reaches _degrade.)
    scoreable = (SCORED, ABSENT, NOT_REQUIRED)
    if frac > limit and metric["status"] in scoreable:
        why = ("; ".join(reasons[:3])) if reasons else "convexity/geometry probes failed"
        metric["status"] = METRIC_ERROR
        metric["score"] = None
        metric["message"] = (
            f"could not classify {frac * 100:.0f}% of the population "
            f"(limit {limit * 100:.0f}%): {why}"
        )

    if relevant is not None:
        seen = (examined or 0.0) / relevant if relevant > 1e-12 else 0.0
        metric["examined"] = round(examined or 0.0, 4)
        metric["relevant"] = round(relevant, 4)
        metric["examined_fraction"] = round(_clamp(seen), 4)
        floor = EXAMINED_MIN.get(mid)
        # SCORED only, unlike the degradation limit above. ABSENT is already the
        # worst answer a metric can give - 0.0 at full weight, never
        # renormalised - and its message is the finding ("this body has no
        # product surface to compose"). Demoting it to ERROR would buy the part
        # nothing, cost `coverage`, and throw the finding away. The invariant is
        # about a NUMBER that was not earned, and ABSENT is not a number.
        if floor is not None and seen < floor and metric["status"] == SCORED:
            metric["status"] = METRIC_ERROR
            metric["score"] = None
            metric["message"] = (
                f"examined only {seen * 100:.0f}% of the exterior this metric measures "
                f"(floor {floor * 100:.0f}%): a score for the {(1 - seen) * 100:.0f}% it "
                f"never looked at would be a guess"
            )
    return metric


def _round_pt(v) -> list[float]:
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def _axis_key(axis) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """
    (direction, foot) identifying an infinite axis line, in the same canonical
    form lib/analyze_step.py uses so cylindrical FACES here can be matched
    against the merged cylindrical FEATURES it returns.
    """
    d = axis.Direction()
    loc = axis.Location()
    direction = _canonical_dir((d.X(), d.Y(), d.Z()))
    p = (loc.X(), loc.Y(), loc.Z())
    t = sum(pc * dc for pc, dc in zip(p, direction))
    foot = tuple(pc - t * dc for pc, dc in zip(p, direction))
    return direction, foot


def _same_axis(a: tuple, b: tuple, tol: float = 0.05) -> bool:
    """
    Two axis keys naming the same infinite line.

    SIGN-BLIND on the direction. An axis line has two directions and which one a
    key carries is decided by `_canonical_dir`'s fold, which has no answer when
    two components are equal - so requiring the two keys to agree in sign made
    "is this the same line" a question about the arithmetic. The foot is already
    sign-invariant: it is p - (p.d)d, which is unchanged by d -> -d.
    """
    da, fa = a
    db, fb = b
    if abs(sum(x * y for x, y in zip(da, db))) < 0.999:
        return False
    return sum((x - y) ** 2 for x, y in zip(fa, fb)) < tol * tol


#: How far apart two coaxial feature mouths may sit perpendicular to their
#: shared axis and still be one screw. Same 0.05 mm _same_axis has always used.
AXIS_MERGE_TOL = 0.05


def _same_direction(a, b) -> bool:
    """
    Two directions describing the same axis line, sign-blind.

    It said sign-blind and it was not: it folded both onto one hemisphere and
    then demanded they agree, which is only sign-blind while the fold has an
    answer. Taking the magnitude of the dot product needs no fold at all.
    """
    return abs(sum(x * y for x, y in zip(tuple(a), tuple(b)))) >= 0.999


def _perp_offset(point, other, direction) -> float:
    """
    Distance from `point` to the line through `other` along `direction`.

    Both points are FEATURE MOUTHS, so their difference is a local quantity: no
    term in it scales with the part's distance from the world origin, which is
    the whole reason this exists instead of a pair of reconstructed feet.
    """
    d = _canonical_dir(tuple(direction))
    w = tuple(p - o for p, o in zip(point, other))
    along = sum(x * y for x, y in zip(w, d))
    return math.sqrt(max(sum(x * x for x in w) - along * along, 0.0))


def _point_on_axis(point, direction, axis: tuple, tol: float = 0.05) -> bool:
    """
    Is `point` on the axis line `axis`, and is `direction` that line's direction?

    THE FOOT IS NEVER REBUILT. Every caller here holds a feature from
    lib/analyze_step.py, whose `dir` is rounded to 4 decimals and whose `p1` is
    rounded to 3 - and the obvious way to compare them, projecting p1 onto its
    own rounded direction to rebuild a foot and handing that to _same_axis,
    multiplies the direction's rounding error by |p1|. |p1| is the part's
    WORLD POSITION, so the reconstruction error grows with distance from the
    origin and vanishes only when the direction is world-axis-aligned. That is
    precisely why a rotation alone and a translation alone each held the bound
    while their COMBINATION broke it: rotation supplies the oblique direction,
    translation supplies the magnitude, and neither is enough on its own.

    The perpendicular distance from p1 to the candidate's OWN axis line has no
    such term: w = p1 - foot, perp^2 = |w|^2 - (w.d)^2, compared against a fixed
    0.05 mm. It reads the geometry rather than reconstructing it.

    THE DIRECTION TEST IS SIGN-BLIND. It used to fold the feature's direction
    onto one hemisphere and require the result to match the face key's fold, and
    the fold has no answer on an axis lying at 45 degrees in a plane: the two
    foldings of one direction came out opposite, this returned False for a
    feature against its own faces, `cylinder_wrap` summed no area, and the
    feature was deleted as an unwrapped sliver. See `_canonical_dir`.
    """
    d_axis, foot = axis
    if abs(sum(x * y for x, y in zip(tuple(direction), d_axis))) < 0.999:
        return False
    w = tuple(p - f for p, f in zip(point, foot))
    along = sum(x * y for x, y in zip(w, d_axis))
    perp2 = sum(x * x for x in w) - along * along
    return max(perp2, 0.0) < tol * tol


def _perp_basis(direction: tuple[float, float, float]) -> tuple[tuple, tuple]:
    """
    Two directions spanning the plane perpendicular to `direction`.

    The seed is a world axis, so this is only stable if the direction handed in
    is already expressed in the PART's frame - which is what _frame_dir is for.
    Given a world direction it swaps u and v as the part turns past the 0.9
    threshold, and every projected layout measurement swaps with it.
    """
    d = cq.Vector(*direction).normalized()
    seed = cq.Vector(0, 0, 1) if abs(d.z) < 0.9 else cq.Vector(1, 0, 0)
    u = d.cross(seed).normalized()
    v = d.cross(u).normalized()
    return (u.x, u.y, u.z), (v.x, v.y, v.z)


def _frame_dir(topo: "Topology", world_dir) -> tuple[float, float, float]:
    """
    A direction as the PART sees it: canonical, rounded, in frame components.

    Layout metrics group features into families by (direction, diameter), and
    grouping on the direction as it happens to sit in the file makes the family
    membership a property of the file. _canonical_dir folds a direction onto one
    hemisphere by the sign of its dominant component, so a family sitting near
    the fold splits in two the moment the part is turned - and a family of one
    scores nothing at all.

    In the frame the same holes share the same direction whatever the file says,
    so the family survives the rotation and the metric measures the part.
    """
    vec = world_dir if isinstance(world_dir, cq.Vector) else cq.Vector(*world_dir)
    return tuple(round(c, 3) for c in _canonical_dir(topo.frame.to_frame_direction(vec)))


def _frame_point(topo: "Topology", world_point) -> cq.Vector:
    """A point in the part's own frame, measured from the frame box centre."""
    vec = world_point if isinstance(world_point, cq.Vector) else cq.Vector(*world_point)
    return cq.Vector(*topo.frame.to_frame_point(vec))


#: How close two frame axes' |cos| to a feature axis must be before neither of
#: them may be called "the" perpendicular one. A boss standing on a face is
#: exactly perpendicular to TWO frame axes, so the two |cos| values are both
#: zero up to round-off - measured on the scaffold they were 4.7e-20 and 3.9e-06
#: at the origin and 1.3e-05 and 3.9e-06 after a 30 degree rotation, and `min`
#: therefore picked a different axis in the two orientations. Anything above
#: that noise and far below a genuine separation works; 1e-3 is four orders
#: clear of the noise and three clear of the smallest real difference.
PERP_TIE_TOL = 1e-3


def _frame_sides(topo: "Topology", direction: cq.Vector) -> list[cq.Vector]:
    """
    Every WORLD direction a sideways probe may leave `direction` along.

    A LIST, and that is the whole point. This used to return the single frame
    axis least parallel to the feature axis, which is well defined for an
    oblique feature and a COIN FLIP for the ordinary one: a boss standing on a
    face is perpendicular to two frame axes at once, so the winner was decided
    by whichever round-off was smaller. On parts/_template that flipped the
    probe from frame axis2 to axis1 under a 30 degree rotation, which opened one
    connector-land boss that had read blocked, which added a 22nd feature centre
    and a 9th family, and moved the score by 0.90 points on a part that had not
    changed. That is the ruler moving, and it is the defect lib/frame.py exists
    to prevent.

    There is no honest way to break the tie, because there is nothing to break
    it WITH - so it is not broken. Every frame axis as perpendicular as the best
    one is probed, and the feature counts as reachable if ANY of them escapes,
    which is also the better answer to the question being asked: a boss flank is
    exposed if there is any way out to air, not if one arbitrarily nominated way
    out happens to work. The set of near-perpendicular axes is a property of the
    part, so it is the same set however the file is held.

    Each axis is orthogonalised against the feature axis, so the result is
    exactly perpendicular even when the two are only nearly so.
    """
    dots = [abs(a.dot(direction)) for a in topo.frame.axes]
    best = min(dots)
    out: list[cq.Vector] = []
    for axis, dot in zip(topo.frame.axes, dots):
        if dot > best + PERP_TIE_TOL:
            continue
        side = axis - direction * direction.dot(axis)
        if side.Length < 1e-9:  # pragma: no cover - three axes cannot all be parallel
            continue
        out.append(side.normalized())
    if not out:  # pragma: no cover - only if all three axes are parallel to direction
        u, _v = _perp_basis((direction.x, direction.y, direction.z))
        out.append(cq.Vector(*u).normalized())
    return out


@dataclass(frozen=True)
class Organisation:
    """
    What one axis of a layout looks like: how much of it is organised, how many
    distinct positions that takes, and how many independent LINES it costs to
    state them.

    `used` and `lines` are the load-bearing additions. `used` is the number of
    organised cluster positions - the number of centrelines this axis actually
    spends. `lines` is the description length: one line per organised cluster
    that stands on its own, but a whole constant-pitch run counts as ONE line
    however many clusters it spans, because a run is stated by a start and a
    pitch. Unorganised clusters cost nothing because they earn nothing.

    `member` is the per-input mask, in the caller's own index order, so the
    caller can ask which features are organised on BOTH axes at once.
    """

    fraction: float
    clusters: int
    used: int
    lines: int
    member: tuple[bool, ...] = ()


def _organised_fraction(
    values: list[float], weights: list[float] | None, tol: float
) -> Organisation:
    """
    Share of the population that sits on a SHARED position or in a CONSTANT
    PITCH run, which is the whole difference between a pattern and scatter.

    Single-linkage clustering at `tol`, then a cluster is organised when it
    holds MIN_CLUSTER_MEMBERS or more members (a shared centreline) or when it
    belongs to a run of three or more cluster positions whose gaps agree inside
    PITCH_CV_MAX (a constant pitch - a bolt row, a rib field, a fin bank, a
    louver grille).

    A lone feature scores 0, which is why adding one more random hole always
    LOWERS the metric. But "sits on a shared line" is only half of "sits on a
    SMALL NUMBER of common lines", and the missing half is what let a random
    scatter mirrored about both centrelines read as fully organised: mirroring
    n points into four quadrants gives 2n u-clusters of two members each and 2n
    v-clusters of two members each, so the fraction saturates at 1.0 on both
    axes. Hence `used` and `lines`, which the caller combines ACROSS the two
    axes into a lattice-economy factor - see _lattice_economy().
    """
    if not values:
        return Organisation(0.0, 0, 0, 0)
    if weights is None:
        weights = [1.0] * len(values)
    order = sorted(range(len(values)), key=lambda i: values[i])
    clusters: list[list[int]] = [[order[0]]]
    for i in order[1:]:
        if values[i] - values[clusters[-1][-1]] <= tol:
            clusters[-1].append(i)
        else:
            clusters.append([i])
    positions = [statistics.fmean(values[i] for i in c) for c in clusters]

    organised = [len(c) >= MIN_CLUSTER_MEMBERS for c in clusters]
    in_run = [False] * len(clusters)
    runs = 0
    # constant-pitch runs over the CLUSTER positions
    n = len(positions)
    if n >= 3:
        gaps = [positions[i + 1] - positions[i] for i in range(n - 1)]
        i = 0
        while i < len(gaps):
            j = i
            while j + 1 < len(gaps):
                run = gaps[i : j + 2]
                cv = _cv(run)
                if cv is None or cv > PITCH_CV_MAX:
                    break
                j += 1
            if j > i:  # at least two gaps -> three cluster positions
                runs += 1
                for k in range(i, j + 2):
                    organised[k] = True
                    in_run[k] = True
                i = j + 1
            else:
                i += 1

    # one line per organised cluster that is not inside a pitch run, plus one
    # line for each run however long it is
    lines = runs + sum(1 for ci in range(len(clusters)) if organised[ci] and not in_run[ci])
    used = sum(1 for ci in range(len(clusters)) if organised[ci])
    mask = [False] * len(values)
    for ci, c in enumerate(clusters):
        if organised[ci]:
            for i in c:
                mask[i] = True
    total = sum(weights)
    if total <= 1e-12:
        return Organisation(0.0, len(clusters), used, lines, tuple(mask))
    good = sum(weights[i] for ci, c in enumerate(clusters) if organised[ci] for i in c)
    return Organisation(good / total, len(clusters), used, lines, tuple(mask))


def _lattice_economy(count: int, u: Organisation, v: Organisation) -> float:
    """
    0-1 factor: does the layout OCCUPY the lattice its own centrelines define?

    THE TWO AXES ARE ONE LAYOUT. Scored separately and averaged, a 4-fold
    mirrored random scatter is indistinguishable from a rectangular bolt
    pattern - and it should be, because a rectangular bolt pattern IS the 4-fold
    mirror of one point. What separates them is how many SEEDS the mirror was
    given: mirroring one point uses 2 u-lines and 2 v-lines and fills all 4 of
    the sites they cross at, while mirroring four random points uses 8 and 8 and
    fills 16 of 64. Features per line cannot see that difference (both are two
    per line); occupancy of the lattice is exactly it.

        fill = (features organised on BOTH axes) / (u.used * v.used)

    A row of five at constant pitch fills 5 of 5 x 1. A 6 x 4 grid fills 24 of
    24. A ring of eight fills 6 of 3 x 3 once its two apex singletons drop out,
    which is the right answer for a circle judged as a lattice: mostly, but not
    perfectly, organised. A mirrored random scatter fills a quarter.

    The numerator counts only features at a lattice INTERSECTION. Counting every
    member instead let a stray inflate the fill it was supposed to dilute: the
    strays are not on any of the lines, so they raise the numerator without
    raising the site count.

    The floor is LINE_ECONOMY_FLOOR rather than zero: a sparse lattice that is
    nonetheless aligned beats pure scatter, and a hard zero would put the two on
    the same step with no gradient between them.
    """
    sites = max(u.used, 1) * max(v.used, 1)
    if count <= 0 or (u.used == 0 and v.used == 0):
        return 0.0
    on_lattice = sum(1 for a, b in zip(u.member, v.member) if a and b)
    fill = _clamp(on_lattice / sites)
    span = _clamp((fill - LATTICE_FILL_WORST) / (LATTICE_FILL_BEST - LATTICE_FILL_WORST))
    return LINE_ECONOMY_FLOOR + (1.0 - LINE_ECONOMY_FLOOR) * span


# ---------------------------------------------------------------------------
# Topology: one pass over the B-rep, cached for every metric
# ---------------------------------------------------------------------------
_SURF_KIND = {
    GeomAbs_Plane: "plane",
    GeomAbs_Cylinder: "cylinder",
    GeomAbs_Torus: "torus",
    GeomAbs_Cone: "cone",
    GeomAbs_Sphere: "sphere",
    # A crown blend, a barrel taper or any revolved arc that is not an exact
    # torus comes back as GeomAbs_SurfaceOfRevolution. It used to fall through
    # to "other", which is face_composition's UNMEASURED population, so a turned
    # knob with an R8 crown put 25% of its surface into the unclassified bucket
    # and errored the metric outright at full weight (measured: 21.0/F with an
    # unmet edge floor on a part whose only defect was that OCC named its blend
    # differently). It is the most literally recognisable surface there is.
    GeomAbs_SurfaceOfRevolution: "revolution",
}


class Topology:
    """
    Face/edge tables for one solid, computed once.

    Face records carry surface kind, plane normal or blend radius, area,
    effective width (area / half-perimeter - a shape-independent proxy for
    "how narrow is this strip"), inner-wire count and tangent-edge count.

    Edge records carry length, midpoint, the two adjacent face indices, the
    dihedral angle between the outward normals there, and a classification:
      "smooth_convex"   tangent join over material - a fillet runout
      "smooth_concave"  tangent join into a corner - invisible, never credited
      "convex"          material subtends less than a straight angle
      "concave"         an internal corner
      "smooth_seam"     the two faces continue each other to second order: a
                        coplanar split or a split cylinder, which is a fact
                        about how the file was written and not about the part.
                        Skipped exactly like a topological seam. See _convex.
      "unknown"         the convexity test could not be resolved (never scored)

    Note the split of the old "smooth": the audit's single worst defect was
    that convexity was computed lazily AFTER the tangent short-circuit, so a
    concave blend nobody can see banked 0.5 * length twice as broken convex
    edge. Convexity is now decided for every non-seam edge, before SMOOTH_DEG.
    """

    def __init__(self, shape: cq.Shape, frame: Frame | None = None) -> None:
        # THE PARTITION IS A PROPERTY OF THE PART, NOT OF THE FILE either: a
        # face split into coplanar pieces is one face. See _canonical_partition.
        self.shape = _canonical_partition(shape)
        shape = self.shape
        # THE RULER IS A PROPERTY OF THE PART, NOT OF THE FILE. Every size,
        # centre, tolerance and cap below comes off this frame; see lib/frame.py
        # for what a world axis-aligned box was worth (parts/_template moved 22
        # points on a 37 degree rotation about Z).
        self.frame = frame if frame is not None else reference_frame(shape)
        # The WORLD box is still carried, because a few things genuinely are
        # questions about the file rather than about the part - and because a
        # probe that wants to prove the ruler moved needs something to compare
        # the frame against. Nothing that feeds a score reads it.
        self.bb = shape.BoundingBox()
        self.faces: list[dict] = []
        self.edges: list[dict] = []
        self.probe_failures = 0  # _on_face exceptions, fed into the error model
        size = max(self.bbox_size()) if max(self.bbox_size()) > 0 else 1.0
        self.break_cap = _clamp(BREAK_CAP_FRACTION * size, BREAK_CAP_MIN, BREAK_CAP_MAX)
        self.blend_cap = _clamp(BLEND_CAP_FRACTION * size, BLEND_CAP_MIN, BLEND_CAP_MAX)
        self._exterior: dict[int, bool | None] = {}
        self._samples: dict[int, list[cq.Vector]] = {}
        # cylindrical face index -> True bore / False barrel / None undecided
        self._bore: dict[int, bool | None] = {}
        self._revolution: tuple | None | str = "unset"
        self._profile: dict | None = None
        # face index -> (real feature wires, decoration wires, unreadable count).
        # face_composition and feature_composition ask the same question of the
        # same faces, and each answer costs up to ten relief rays.
        self.wire_cache: dict[int, tuple] = {}
        # face index -> (Developed | None, why-not). One CURVED_GRID_N**2 pass
        # over the first fundamental form per face, asked for more than once.
        self._developed: dict[int, tuple] = {}
        # "unset" rather than None: None is a real answer (undecidable), and the
        # role guards must never read "could not decide" as "no interior".
        self._interior_fraction: float | None | str = "unset"
        self._build()
        self.sheet_thickness = self._sheet_thickness()

    def _sheet_thickness(self) -> float:
        """
        Material thickness of a formed sheet part, from volume and surface area.

        NOT min(bbox): a Z-bracket bent out of 2 mm stock has a 58 mm minimum
        bbox dimension, and using that made every planar face on the corpus's
        sheet reference read as blanked perimeter - the whole part was excluded
        from its own edge metric. For sheet, area ~ 2A + perimeter*t and
        V = A*t, so 2V/area recovers t to within a percent or two.
        """
        try:
            volume = abs(self.shape.Volume())
        except Exception:
            volume = 0.0
        area = sum(f["area"] for f in self.faces)
        if area <= 1e-9 or volume <= 1e-9:
            return min(self.bbox_size())
        return _clamp(2.0 * volume / area, 1e-3, min(self.bbox_size()))

    # -- construction --------------------------------------------------------
    def _build(self) -> None:
        fmap = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(self.shape.wrapped, TopAbs_FACE, fmap)
        self._fmap = fmap

        for i in range(1, fmap.Extent() + 1):
            self.faces.append(self._face_record(cq.Shape.cast(fmap.FindKey(i))))

        emap = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(self.shape.wrapped, TopAbs_EDGE, TopAbs_FACE, emap)
        for i in range(1, emap.Extent() + 1):
            rec = self._edge_record(cq.Shape.cast(emap.FindKey(i)), emap.FindFromIndex(i))
            if rec is not None:
                self.edges.append(rec)

        self.face_edges: dict[int, list[dict]] = {i: [] for i in range(len(self.faces))}
        for e in self.edges:
            for fi in e["faces"]:
                if 0 <= fi < len(self.faces):
                    self.face_edges[fi].append(e)
            if e["kind"].startswith("smooth"):
                for fi in e["faces"]:
                    self.faces[fi]["tangent_edges"] += 1

    def _face_record(self, face: cq.Face) -> dict:
        surf = BRepAdaptor_Surface(face.wrapped)
        kind = _SURF_KIND.get(surf.GetType(), "other")
        normal = radius = cone_deg = None
        if kind == "plane":
            try:
                normal = face.normalAt()
            except Exception:
                normal = None
        axis = None
        if kind == "cylinder":
            cyl = surf.Cylinder()
            radius = cyl.Radius()
            axis = _axis_key(cyl.Axis())
        elif kind == "torus":
            torus = surf.Torus()
            radius = torus.MinorRadius()
            # a torus and a cone carry an axis too, and revolution_axis() needs
            # it: a turned part's chamfers and its blend rings are the faces that
            # would otherwise read as "not about this axis" and sink the test.
            axis = _axis_key(torus.Axis())
        elif kind == "cone":
            try:
                cone_deg = abs(math.degrees(surf.Cone().SemiAngle()))
                axis = _axis_key(surf.Cone().Axis())
            except Exception:
                cone_deg = None
        elif kind == "revolution":
            # It carries its axis of revolution by construction, which is
            # exactly what revolution_axis() needs from it.
            try:
                axis = _axis_key(surf.AxeOfRevolution())
            except Exception:
                axis = None

        try:
            area = face.Area()
        except Exception:
            area = 0.0
        perim = 0.0
        for e in face.Edges():
            try:
                perim += e.Length()
            except Exception:
                pass
        width = (area / (0.5 * perim)) if perim > 1e-9 else 0.0
        try:
            inner = len(face.innerWires())
        except Exception:
            inner = 0
        return {
            "face": face,
            "kind": kind,
            "normal": normal,
            "radius": radius,
            "cone_deg": cone_deg,
            "axis": axis,
            "area": area,
            "perimeter": perim,
            "width": width,
            "inner_wires": inner,
            "tangent_edges": 0,
        }

    def _edge_record(self, edge: cq.Edge, face_list) -> dict | None:
        try:
            length = edge.Length()
        except Exception:
            return None
        if length < MIN_EDGE_LEN:
            return None

        idx = [self._fmap.FindIndex(f) - 1 for f in face_list]
        rec = {
            "edge": edge,
            "length": length,
            "faces": idx,
            "kind": "unknown",
            "angle_deg": None,
            "mid": None,
        }
        if len(idx) != 2 or idx[0] == idx[1]:
            # A shared seam (same face twice) or a non-manifold junction; both
            # are structural, not styling. Never scored.
            rec["kind"] = "seam" if len(idx) == 2 else "nonmanifold"
            return rec

        try:
            mid = edge.positionAt(0.5)
            tangent = edge.tangentAt(0.5)
            f0, f1 = self.faces[idx[0]]["face"], self.faces[idx[1]]["face"]
            n0, n1 = f0.normalAt(mid), f1.normalAt(mid)
        except Exception as exc:
            rec["error"] = f"{type(exc).__name__}: {exc}"
            return rec

        rec["mid"] = mid
        rec["normals"] = (n0, n1)
        angle = math.degrees(n0.getAngle(n1))
        rec["angle_deg"] = angle

        # Convexity FIRST, for every edge, tangent or not. The tangent case is
        # exactly the one that decides whether a blend is a visible exterior
        # break or a buried internal corner, so it is the last case that may be
        # allowed to skip the test.
        conv = self._convex(mid, tangent, idx[0], idx[1])
        if conv is None and angle >= SMOOTH_DEG:
            # A CREASE, and only a crease, may fall back to the first-order test
            # at the edge. It needs a probe on ONE face rather than on both, so
            # it still resolves where a periodic or awkwardly trimmed neighbour
            # will not yield an interior point - which on parts/_template is 31
            # edges and 182 mm of otherwise unclassified convex length.
            # A TANGENT edge must never come here: the first-order term is
            # identically zero for it, which is the whole defect.
            conv = self._convex_at_edge(mid, tangent, idx[0], n1)
            if conv is None:
                conv = self._convex_at_edge(mid, tangent, idx[1], n0)
        if conv == "seam":
            rec["kind"] = "smooth_seam"
        elif conv is None:
            rec["kind"] = "unknown"
        elif angle < SMOOTH_DEG:
            rec["kind"] = "smooth_convex" if conv else "smooth_concave"
        else:
            rec["kind"] = "convex" if conv else "concave"
        return rec

    def _convex(self, mid, tangent, i0: int, i1: int) -> bool | str | None:
        """
        Which side of this edge the material is on, decided a short way OFF the
        edge rather than at it.

        The test this replaces asked whether a point a hair inside one face sits
        on the inner side of the OTHER face's tangent plane AT THE EDGE. For a
        crease that is a first-order question with a strong answer. For a
        TANGENT join - a press-brake bend running out into its leg, a fillet
        running out into the wall it blends - the two tangent planes ARE the
        same plane, the answer is identically zero, and the sign came out of
        round-off in the vertex coordinates. So it moved with orientation and
        with position, and it classified the two runouts of a single bend
        differently from each other at identity. Measured on a 2 mm sheet
        bracket with one R3 bend it was worth 27.3 points of
        `edge_break_coverage` and it flipped that metric's rubric floor between
        met and unmet on a ONE degree rotation.

        This asks the same question one order deeper, where tangency still has
        an answer. Take a point p_i strictly inside each face, a short distance
        off the edge, with that face's own outward normal n_i THERE rather than
        at the edge. Then

            (p1 - p0) . (n0 - n1)  <  0   <=>   the material wraps round: convex

        For a crease that is the old first-order test, term for term: it reduces
        to d1 (u1.n0) + d0 (u0.n1), the sum of the two halves the old code chose
        between, and the two halves always agree in sign. For a tangent join the
        first-order terms cancel and what survives is the difference in how the
        two surfaces CURVE away from their shared tangent plane - the blend
        leaning over the material is convex, the blend leaning away from it is
        concave. That is a property of the two surfaces, not of the coordinates
        they are written in.

        Normalised by |p1 - p0| |n0 - n1| the quantity is +-1 for a clean crease
        AND for a clean tangent runout, so one threshold covers both.

        Returns True (convex), False (concave), the string "seam", or None.
        "seam" is the case where |n0 - n1| vanishes: the two faces continue each
        other to second order, so this is a coplanar split or a split cylinder -
        a fact about how the file was written, not about the part - and it is
        skipped like a topological seam rather than guessed at. None means
        unresolved: no interior point could be found, or the edge does not bound
        one of its faces, and an unresolved edge is counted against the metric's
        examined fraction rather than guessed.

        Orientation-free: nothing here consults how the edge is used in either
        face's wire, and every term is a difference of two nearby points, so a
        rigid motion perturbs it in the DIFFERENCE rather than in the coordinate
        magnitude. Verified invariant over 13 orientations and 5 translations to
        (5000, -5000, 5000) mm by tests/test_invariance.py.

        The audit's hand-verified cases are unchanged by the new derivation: an
        L-section (60x60 legs, 15 thick, 40 deep) still measures concave 40.000
        of 40.000 mm and convex 680.000 of 680.000; a 60x40x10 blind pocket
        still measures concave 240.000 and convex 1200.000.
        """
        a = self._off_edge(i0, mid, tangent)
        b = self._off_edge(i1, mid, tangent)
        if a is None or b is None:
            return None
        (p0, n0), (p1, n1) = a, b
        span = p1 - p0
        lean = n0 - n1
        if lean.Length < CONVEX_SEAM_LEAN:
            return "seam"
        scale = span.Length * lean.Length
        if scale < 1e-12:
            return None
        signal = span.dot(lean) / scale
        if abs(signal) < CONVEX_MIN_SIGNAL:
            return None
        return signal < 0.0

    def _convex_at_edge(self, mid, tangent, fi: int, other_normal) -> bool | None:
        """
        The first-order convexity test, for CREASES ONLY.

        A point a hair inside face `fi` measured against the OTHER face's tangent
        plane AT the edge: inside the plane means the material wraps round the
        edge (convex), outside means an internal corner (concave). It needs an
        interior point on only ONE of the two faces, which is why it survives a
        periodic or awkwardly trimmed neighbour that ``_off_edge`` cannot find a
        point on.

        It is EXACTLY ZERO on a tangent join - the probe point lies in the other
        face's tangent plane by definition - so its answer there is round-off,
        and ``_edge_record`` calls it only when the dihedral clears SMOOTH_DEG.
        Do not widen that condition.

        Hand-verified by the audit and unchanged: an L-section (60x60 legs, 15
        thick, 40 deep) measures concave 40.000 of 40.000 mm and convex 680.000
        of 680.000; a 60x40x10 blind pocket measures concave 240.000 and convex
        1200.000.
        """
        rec = self.faces[fi]
        normal = rec["normal"] if rec["kind"] == "plane" else None
        if normal is None:
            try:
                normal = rec["face"].normalAt(mid)
            except Exception:
                return None
        try:
            step = normal.cross(tangent).normalized()
        except Exception:
            return None
        delta = _clamp(1e-3 * math.sqrt(max(rec["area"], 1e-9)), 1e-4, 0.05)
        for sign in (1.0, -1.0):
            probe = mid + step * (sign * delta)
            if self._on_face(rec["face"], probe):
                return (probe - mid).dot(other_normal) < 0
        return None

    def _off_edge(self, fi: int, mid, tangent) -> tuple[cq.Vector, cq.Vector] | None:
        """
        A point strictly inside face `fi` a short way off the edge through
        `mid`, and the face's outward normal there.

        The step runs along n x t, which lies in the surface and crosses the
        edge, and the sign taken is whichever one lands inside the trimmed face
        - so no wire orientation is consulted. The point is then pulled back
        ONTO the surface, which is what matters on a curved face: a straight
        step off an R3 bend leaves the cylinder by d^2/2R, and on a tangent join
        that departure IS the signal.

        Both signs landing inside means the edge does not bound this face - a
        coplanar split, a stray internal seam - and that is reported unresolved
        rather than decided arbitrarily.
        """
        rec = self.faces[fi]
        face = rec["face"]
        try:
            normal = face.normalAt(mid)
            step = normal.cross(tangent).normalized()
        except Exception:
            return None
        span = _clamp(0.02 * math.sqrt(max(rec["area"], 1e-9)), CONVEX_STEP_MIN, CONVEX_STEP_MAX)
        for shrink in (1.0, 0.25, 0.0625, 0.015625):
            delta = span * shrink
            hits = [
                point
                for point in (
                    self._pull_onto_face(face, mid + step * (sign * delta), delta)
                    for sign in (1.0, -1.0)
                )
                if point is not None
            ]
            if len(hits) > 1:
                return None
            if hits:
                try:
                    return hits[0], face.normalAt(hits[0])
                except Exception:
                    return None
            if delta <= CONVEX_STEP_MIN:
                break
        return None

    def _pull_onto_face(self, face: cq.Face, target, delta: float) -> cq.Vector | None:
        """
        `target` projected onto the face's own surface, if it lands strictly
        inside the trimmed boundary without having to travel far to get there.

        The travel cap is what stops a probe that stepped off the END of a face
        being dragged back onto a distant part of a periodic surface and read as
        an interior point.
        """
        try:
            surface = BRep_Tool.Surface_s(face.wrapped)
            proj = GeomAPI_ProjectPointOnSurf(target.toPnt(), surface)
            if proj.NbPoints() < 1 or proj.LowerDistance() > 0.6 * delta:
                return None
            u, v = proj.LowerDistanceParameters()
            cls = BRepClass_FaceClassifier(face.wrapped, gp_Pnt2d(u, v), 1e-7)
            if cls.State() != TopAbs_IN:
                return None
            pnt = proj.NearestPoint()
            return cq.Vector(pnt.X(), pnt.Y(), pnt.Z())
        except Exception:
            self.probe_failures += 1
            return None

    def _on_face(self, face: cq.Face, point) -> bool:
        """
        Is `point` inside this face's trimmed boundary?

        A raised exception used to be swallowed to False, which silently turned
        into an unresolved edge with nobody counting. Failures are now counted
        on `self.probe_failures` and fed into the edge metrics' degradation.
        """
        try:
            surface = BRep_Tool.Surface_s(face.wrapped)
            proj = GeomAPI_ProjectPointOnSurf(point.toPnt(), surface)
            if proj.NbPoints() < 1 or proj.LowerDistance() > 1e-4:
                return False
            u, v = proj.LowerDistanceParameters()
            cls = BRepClass_FaceClassifier(face.wrapped, gp_Pnt2d(u, v), 1e-7)
            return cls.State() in (TopAbs_IN, TopAbs_ON)
        except Exception:
            self.probe_failures += 1
            return False

    # -- sampling and exterior reachability ----------------------------------
    def samples(self, fi: int, want: int = 3) -> list[cq.Vector]:
        """
        Up to `want` points that lie strictly inside face `fi`.

        A UV grid alone is not enough: a narrow strip - a chamfer land, a frame,
        a rib flank, a fin root - can pass between the grid lines entirely, and
        a face that yields no sample reads as "exterior reachability undecided",
        which under the error model takes a whole metric to ERROR. Measured on
        the exemplar: a 5x5 grid left 28% of the candidate area unclassified and
        killed face_composition outright. So the grid densifies, and then falls
        back to stepping inward from the midpoint of each boundary edge, which
        finds an interior point for any non-degenerate face.
        """
        cached = self._samples.get(fi)
        if cached is not None:
            return cached
        face = self.faces[fi]["face"]
        out: list[cq.Vector] = []
        try:
            umin, umax, vmin, vmax = BRepTools.UVBounds_s(face.wrapped)
            surf = BRep_Tool.Surface_s(face.wrapped)
            for n in (5, 11):
                for iu in range(1, n + 1):
                    for iv in range(1, n + 1):
                        if len(out) >= want:
                            break
                        u = umin + (umax - umin) * iu / (n + 1.0)
                        v = vmin + (vmax - vmin) * iv / (n + 1.0)
                        cls = BRepClass_FaceClassifier(face.wrapped, gp_Pnt2d(u, v), 1e-7)
                        if cls.State() == TopAbs_IN:
                            p = surf.Value(u, v)
                            out.append(cq.Vector(p.X(), p.Y(), p.Z()))
                if out:
                    break
        except Exception:
            self.probe_failures += 1
        if not out:
            out = self._edge_inward_samples(fi, want)
        self._samples[fi] = out
        return out

    def _edge_inward_samples(self, fi: int, want: int) -> list[cq.Vector]:
        """Points a hair inside the face, stepped in from its boundary edges."""
        rec = self.faces[fi]
        out: list[cq.Vector] = []
        delta = _clamp(0.02 * math.sqrt(max(rec["area"], 1e-9)), 1e-3, 0.5)
        for e in self.face_edges.get(fi, ()):
            if len(out) >= want or e["mid"] is None:
                break
            try:
                mid = e["mid"]
                tangent = e["edge"].tangentAt(0.5)
                normal = rec["normal"] if rec["kind"] == "plane" else rec["face"].normalAt(mid)
                step = normal.cross(tangent).normalized()
            except Exception:
                self.probe_failures += 1
                continue
            for sign in (1.0, -1.0):
                probe = mid + step * (sign * delta)
                if self._on_face(rec["face"], probe):
                    out.append(probe)
                    break
        return out

    def is_exterior(self, fi: int) -> bool | None:
        """
        Can this face be seen from outside the part?

        A ray leaves the face along its own outward normal: no forward crossing
        means open air. A cavity wall always crosses the far wall, so it reads
        interior - which is the point. A cavity is not a product surface, and
        the audit found that concave fillets buried in a SEALED cavity bought a
        part 30 points of composition and a full 100 on edge breaks.

        None means it could not be decided; callers must treat that as
        unmeasured, never as exterior.
        """
        if fi in self._exterior:
            return self._exterior[fi]
        rec = self.faces[fi]
        # Free answer for the commonest case: a planar face whose outward normal
        # lies on a FRAME axis and which sits on the frame box cannot have
        # anything in front of it. This is most of the area of most parts and it
        # costs no rays at all. Measured in the part's own frame rather than
        # against the world box, so a rotated copy takes the same shortcut.
        if rec["kind"] == "plane" and rec["normal"] is not None:
            comps = self.frame.to_frame_direction(rec["normal"])
            centre = self.frame.to_frame_point(rec["face"].Center())
            half = tuple(0.5 * s for s in self.frame.size)
            # THE BOUNDARY TOLERANCE IS SCALE-RELATIVE, and it has to be. Against
            # the world box an axis-aligned face sits on the boundary EXACTLY, so
            # 1e-6 was free; in the part's own frame the coordinate has been
            # through a rotation, and the round-off is proportional to the part.
            # An absolute 1e-6 therefore fires before a rotation and not after,
            # dropping those faces onto the ray probe instead - which is the exact
            # class of defect the frame exists to remove. 1e-9 of the part is
            # still a thousand times finer than any feature.
            tol = max(1e-6, 1e-9 * max(self.frame.size))
            for k in range(3):
                if abs(comps[k]) > 0.999 and abs(abs(centre[k]) - half[k]) < tol:
                    if (centre[k] > 0) == (comps[k] > 0):
                        self._exterior[fi] = True
                        return True
        verdict: bool | None = None
        pts = self.samples(fi, want=2)
        if pts:
            verdict = False
            for p in pts:
                try:
                    n = rec["normal"] if rec["kind"] == "plane" else rec["face"].normalAt(p)
                    if n is None:
                        continue
                    origin = p + n * 1e-3
                    hits = [h for h in _ray_hits(self.shape, origin, n) if h > 1e-6]
                except Exception:
                    self.probe_failures += 1
                    continue
                if not hits:
                    verdict = True
                    break
        self._exterior[fi] = verdict
        return verdict

    # -- derived predicates --------------------------------------------------
    def is_break_face(self, fi: int) -> bool:
        """
        A face whose whole job is to break a corner: a narrow planar strip
        (chamfer land), a cone at a chamfer-like half-angle (a chamfer that ran
        across a curved corner, or a countersink), or a small tangent blend.

        The width cap is RELATIVE to the part (break_cap): the old absolute
        5.0 mm meant a 4 mm chamfer on a 300 mm part stopped registering and
        its two boundary edges were re-scored as knife edges.
        """
        rec = self.faces[fi]
        if rec["kind"] == "plane":
            return 0.0 < rec["width"] <= self.break_cap
        if rec["kind"] == "cone":
            deg = rec["cone_deg"]
            return (
                0.0 < rec["width"] <= self.break_cap
                and deg is not None
                and CONE_BREAK_MIN_DEG <= deg <= CONE_BREAK_MAX_DEG
            )
        if rec["kind"] in ("cylinder", "torus"):
            return self.is_blend_face(fi)
        return False

    def is_blend_face(self, fi: int) -> bool:
        """
        A tangent blend, as opposed to a functional bore or boss wall.

        Two tangent boundary edges, not one: a real blend runs out tangentially
        on BOTH sides (a plan-corner fillet, a pocket-corner fillet, a sheet
        bend). A bore that happens to graze another bore has exactly one, and
        the audit found those leaking in as "a fillet of half the bore
        diameter" - which also wrongly filtered real holes out of the fastener
        metric. Requiring every non-seam edge to be tangent, as the audit
        proposed, would instead reject the commonest fillet in the repo (a plan
        corner has hard edges at the top and bottom faces), so the rule is two.

        A CYLINDER COAXIAL WITH A BODY OF REVOLUTION IS NEVER ONE. In the
        meridian a cylinder is a straight segment - a diameter - and a blend is
        an arc; but a shaft journal with a fillet at each end has a small radius
        and two tangent runouts, which is the whole of this test. Measured on a
        three-diameter shaft whose two shoulder roots were correctly filleted to
        R1.0: the D18 journal was read as "a fillet of R9", 9.0 is not on the
        ladder, and radius_vocabulary fell from 100.0 to 26.0 - the gate charged
        74 points for making exactly the move it asks for.
        """
        rec = self.faces[fi]
        if rec["kind"] == "cylinder" and rec["axis"] is not None:
            axis = self.revolution_axis()
            if axis is not None and _same_axis(rec["axis"], axis):
                return False
        return (
            rec["kind"] in ("cylinder", "torus")
            and (rec["radius"] or 1e9) <= self.blend_cap
            and rec["tangent_edges"] >= 2
        )

    def cylinder_is_bore(self, fi: int) -> bool | None:
        """
        Does this cylindrical face wrap a HOLE, or is it the outside of a barrel?

        The outward normal answers it in one dot product: on a bore the material
        is outside the cylinder, so the normal points back towards the axis; on
        the OD of a turned part, a boss or a spigot it points away from it.

        THIS IS THE ROOT OF G2. `is_bore_wall` used to mean "any cylindrical
        face that is not a blend", which swept in the OUTER skin of every body of
        revolution - so on a turned part every silhouette corner was filed under
        "bore/boss rim", the body population emptied to zero, and
        edge_break_coverage collapsed onto its 0.15 rim term. Measured on a
        turned knob: body 0 of 0 mm, rim 157.1 of 157.1 mm, score 100.0 for one
        chamfered socket mouth.

        None when no point on the face could be sampled, so an unresolved probe
        is never read as either answer.
        """
        rec = self.faces[fi]
        if rec["kind"] != "cylinder" or rec["axis"] is None:
            return None
        cached = self._bore.get(fi)
        if cached is not None or fi in self._bore:
            return cached
        verdict: bool | None = None
        direction = cq.Vector(*rec["axis"][0])
        foot = cq.Vector(*rec["axis"][1])
        for p in self.samples(fi, want=2):
            try:
                n = rec["face"].normalAt(p)
                rel = p - foot
                radial = rel - direction * rel.dot(direction)
                if radial.Length <= 1e-9 or n is None:
                    continue
                verdict = n.dot(radial.normalized()) < 0.0
                break
            except Exception:
                self.probe_failures += 1
                continue
        self._bore[fi] = verdict
        return verdict

    def is_bore_wall(self, fi: int) -> bool:
        """
        A cylindrical face that is a functional bore or boss, not a blend - and
        not the OD of a turned part, which is silhouette. See is_barrel_face.

        An undecided probe leaves the face here rather than on the silhouette:
        body carries 0.85 of this metric and the floor, rim carries 0.15, so an
        unresolved face is not allowed to quietly shrink the strict population.
        """
        if self.faces[fi]["kind"] != "cylinder" or self.is_blend_face(fi):
            return False
        return not self.is_barrel_face(fi)

    def is_barrel_face(self, fi: int) -> bool:
        """
        The OD of a TURNED part: the outside of a cylinder that is coaxial with
        the axis the whole part is a body of revolution about.

        A silhouette surface, so the edges where it meets an end face or a
        shoulder are body corners - the ones a machinist breaks - not bore rims.

        Deliberately NOT "the outside of any cylinder". A boss or a spigot on a
        prismatic part is a feature standing on a face, and its rim is secondary
        by the same length-weighting argument that puts a rib crest there;
        promoting every one of them to the silhouette was measured to move
        125.7 mm of bend-relief edge into the sheet bracket's body population
        (edge_break_coverage 20.6 -> 0.3) and to drop the exemplar from 92.9 to
        55.6, for a defect neither part has. The claim being made here is only
        the one G2 needs: the outer skin of a body of revolution IS its
        silhouette, so the metric must not report that it has none.
        """
        rec = self.faces[fi]
        if rec["kind"] != "cylinder" or rec["axis"] is None or self.is_blend_face(fi):
            return False
        axis = self.revolution_axis()
        if axis is None or not _same_axis(rec["axis"], axis):
            return False
        return self.cylinder_is_bore(fi) is False

    def is_rim_break_face(self, fi: int) -> bool:
        """
        A break face that belongs to a BORE, not to the body silhouette.

        A countersink cone, or the lead-in chamfer of a hole, breaks a rim -
        not a corner of the part. Crediting it in the body population is how
        drilling used to raise edge_break_coverage on a raw box: the cone
        passed the width test and banked half its length at BOTH of its
        boundary circles while adding nothing to the denominator.
        """
        if not self.is_break_face(fi):
            return False
        for e in self.face_edges.get(fi, ()):
            for other in e["faces"]:
                if other != fi and self.is_bore_wall(other):
                    return True
        return False

    def is_rim_edge(self, f0: int, f1: int) -> bool:
        return any(self.is_bore_wall(f) or self.is_rim_break_face(f) for f in (f0, f1))

    def is_detail_face(self, fi: int) -> bool:
        """
        A narrow strip that is a FEATURE surface, not part of the silhouette:
        a rib crest, a rib or fin flank, a louver blade, a lightening-pocket
        land.
        """
        rec = self.faces[fi]
        return rec["kind"] == "plane" and 0.0 < rec["width"] <= self.break_cap

    def is_detail_edge(self, f0: int, f1: int) -> bool:
        """
        An edge where BOTH sides are narrow feature strips.

        Length-weighting is what makes this necessary. A rib field puts hundreds
        of millimetres of short crest edge into the population, so on the corpus
        ladder adding ribs to a fully broken box drove edge_break_coverage from
        100 to 56 and sharp_edge_length from 100 to 0 - the refinement ladder
        went DOWN when a refinement move was added, which is the inversion the
        corpus contract exists to forbid. A rib crest is not the part's
        silhouette; the box corner it sits inside is. Detail edges are therefore
        scored in the secondary population alongside bore rims, at 0.15 weight,
        so leaving them raw still costs - it just cannot swamp the silhouette.
        """
        return self.is_detail_face(f0) and self.is_detail_face(f1)

    def interior_area_fraction(self) -> float | None:
        """
        Share of face area that faces an ENCLOSED VOID rather than the world.

        This is the difference between a formed blank and a hollow box, and
        between a bracket and a housing - none of which the thickness figure
        can see. None when too much of the surface could not be decided, so
        that an unresolved probe can never be read as "no interior".

        Cached: is_band_face() asks is_sheet_like() once per face, and every
        exterior decision costs rays.
        """
        if self._interior_fraction != "unset":
            return self._interior_fraction
        total = 0.0
        inner = 0.0
        undecided = 0.0
        for i, rec in enumerate(self.faces):
            area = rec["area"]
            if area <= 1e-9:
                continue
            total += area
            ext = self.is_exterior(i)
            if ext is None:
                undecided += area
            elif not ext:
                inner += area
        if total <= 1e-9 or undecided > 0.25 * total:
            self._interior_fraction = None
        else:
            self._interior_fraction = inner / total
        return self._interior_fraction

    def is_sheet_like(self) -> bool:
        """
        Is this actually formed from thin stock, and open on both sides of it?

        The `sheet` rubric excuses a whole edge population, so claiming it must
        not be a way to have a SOLID part's knife edges excused: measured, a
        plain 120x80x40 box declared `sheet` scored 32.9 against 27.1 as an
        enclosure, because its derived 16 mm "thickness" made every face read as
        blanked perimeter. Real sheet stock is a small fraction of the part.

        The thickness test alone was not enough. `sheet_thickness` is
        2 * volume / area, which recovers the WALL thickness of a hollow
        enclosure exactly as well as it recovers the stock thickness of a
        blank - measured, a 3 mm walled 90 x 60 x 30 box derives 2.99 mm and
        passed as sheet metal. A formed blank has no inside; an enclosure is
        mostly inside. is_exterior() already knows the difference.
        """
        size = max(self.bbox_size())
        if size <= 1e-9 or self.sheet_thickness > SHEET_THICKNESS_MAX_FRACTION * size:
            return False
        inner = self.interior_area_fraction()
        return inner is not None and inner <= SHEET_INTERIOR_MAX_FRACTION

    def formed_radii(self) -> int:
        """
        How many small blend radii a sheet-like part carries.

        NOT evidence of forming on its own, and it was used as if it were: this
        was `_guard_sheet`'s "and it has to be formed" test until every plan
        radius milled into the outline of a solid slab was found to land in the
        count. Measured here, a 200 x 120 x 12 knife-edged milled slab with four
        R8 corners reports 4 and a 220 x 140 x 4 blank reports 3, and neither has
        ever been near a press brake. Use `bend_pairs()` for the claim and this
        only as the wider population it is drawn from.
        """
        return sum(
            1
            for i, rec in enumerate(self.faces)
            if rec["kind"] in ("cylinder", "torus")
            and self.is_blend_face(i)
            and (rec["radius"] or 0.0) <= BEND_MAX_RADIUS_STOCK * self.sheet_thickness
        )

    def face_wrap_deg(self, fi: int) -> float | None:
        """
        How far a cylindrical face wraps about its own axis, in degrees.

        OCC parametrises a cylinder with u as the angle, so the face's own
        u-range IS the sweep. A bore or a boss closes on itself at 360; a bend, a
        plan corner or a pocket corner is a partial cylinder.
        """
        try:
            u0, u1, _v0, _v1 = BRepTools.UVBounds_s(self.faces[fi]["face"].wrapped)
        except Exception:
            return None
        return abs(math.degrees(u1 - u0))

    def axial_span(self, fi: int, axis: tuple) -> tuple[float, float] | None:
        """
        How far a face reaches along an axis, as (lo, hi) in millimetres.

        Projected from the face's own vertices rather than from its bounding
        box, because the box is axis-aligned to the world and a bend is not.
        """
        direction = axis[0]
        vals: list[float] = []
        try:
            for v in self.faces[fi]["face"].Vertices():
                p = v.toTuple()
                vals.append(sum(a * b for a, b in zip(p, direction)))
        except Exception:
            return None
        if not vals:
            return None
        return min(vals), max(vals)

    def bend_flange(self, fi: int) -> int | None:
        """
        The FLANGE this cylindrical face runs out into, or None.

        A fold is tangent-continuous with the flat material either side of it,
        and that material is a planar face far wider than the stock. A plan
        radius milled into the outline of a plate also runs out tangentially -
        but into the THICKNESS BAND of the blank, a face one stock wide.

        That is the same statement as "the bend axis lies in the plane of the
        sheet", made in a way that needs no plane to be identified: a cylinder is
        tangent only to planes parallel to its own axis, so an axis lying in the
        stock reaches the flange faces and an axis normal to the stock can only
        ever reach the bands around its edge.
        """
        t = self.sheet_thickness
        cyl = self.faces[fi]
        radius = cyl["radius"] or 0.0
        if t <= 1e-9 or cyl["axis"] is None or radius <= 1e-9:
            return None
        direction, foot = cyl["axis"]
        for e in self.face_edges.get(fi, ()):
            mid = e.get("mid")
            if mid is None:
                continue
            others = [x for x in e["faces"] if x != fi]
            if len(others) != 1:
                continue
            rec = self.faces[others[0]]
            if rec["kind"] != "plane" or rec["normal"] is None:
                continue
            if rec["width"] < BEND_FLANGE_MIN_STOCK * t:
                continue
            normal = (rec["normal"].x, rec["normal"].y, rec["normal"].z)
            if abs(sum(a * b for a, b in zip(normal, direction))) > BEND_FLANGE_AXIS_TOL:
                continue
            offset = (mid.x - foot[0], mid.y - foot[1], mid.z - foot[2])
            standoff = abs(sum(a * b for a, b in zip(offset, normal)))
            if abs(standoff - radius) > BEND_FLANGE_TANGENT_TOL * radius:
                continue
            return others[0]
        return None

    def bend_pairs(self) -> int:
        """
        How many actual BENDS in flat stock this part carries.

        A bend is a coaxial PAIR of partial cylindrical faces whose radii differ
        by the material thickness - the inside of the fold at ri and the outside
        at ri + t, on one axis - which spans the same extent of that axis on both
        faces and runs out tangentially into flange material at both ends. That
        is a property of forming and of nothing else a constant-thickness part
        does, which is exactly what `formed_radii` failed to be: counting any
        small blend cylinder let a SOLID MILLED SLAB present its four
        plan-radiused corners as evidence of forming, and the `sheet` role's
        whole payment for its exclusions is that the breaks being judged are the
        formed radii.

        The five filters are each load-bearing, and each closed a measured
        escape rather than a hypothetical one:

        * without the WRAP cap a bore and its own counterbore pair up whenever
          the step happens to be near t;
        * without the RADIUS cap any two coaxial cylinders of any size qualify;
        * without the BLEND requirement a pair of unrelated turned diameters
          does;
        * without the EXTENT test a milled tray does. Coaxial-and-one-stock-apart
          is arithmetic, and a machinist can arrange it deliberately: a
          200 x 120 x 5 plate with a 1 mm pocket inset by its own derived stock
          reported four pairs and took the `sheet` claim from refused to
          accepted, 46.2/D honest to 75.3/B. A fold runs the full width of what
          it joins - the corpus's formed bracket spans 70.0 mm on both faces of
          the pair - while the tray's plan corner spans the plate's 5 mm and its
          pocket corner the pocket's 1 mm (measured 4.4 against 1.4);
        * without the FLANGE test a through-cut window inset by one stock
          thickness does, which is the obvious way to fake equal extents: both
          of its cylinders span the whole blank. Neither runs out into anything
          but a thickness band. See `bend_flange`.

        It is NOT sufficient by itself, and the guard does not use it that way: a
        SHELLED housing has an inner and an outer corner blend separated by its
        wall, spanning nearly the same height and tangent to its own walls, which
        passes every test here (measured on a 2.5 mm walled 90 x 60 x 30 box: 4
        pairs). What separates those is the interior area fraction, which is why
        `_guard_sheet` requires thin stock in absolute millimetres, no enclosed
        void AND a bend.
        """
        t = self.sheet_thickness
        if t <= 1e-9:
            return 0
        cands: list[tuple[int, dict]] = []
        for i, rec in enumerate(self.faces):
            if rec["kind"] != "cylinder" or rec["axis"] is None or not rec["radius"]:
                continue
            if rec["radius"] > BEND_MAX_RADIUS_STOCK * t:
                continue
            wrap = self.face_wrap_deg(i)
            if wrap is None or wrap > BEND_MAX_WRAP_DEG:
                continue
            cands.append((i, rec))
        pairs = 0
        for a in range(len(cands)):
            ia, ra = cands[a]
            for b in range(a + 1, len(cands)):
                ib, rb = cands[b]
                if not _same_axis(ra["axis"], rb["axis"]):
                    continue
                if not (self.is_blend_face(ia) or self.is_blend_face(ib)):
                    continue
                if abs(abs(ra["radius"] - rb["radius"]) - t) > BEND_THICKNESS_TOL * t:
                    continue
                if self.bend_flange(ia) is None or self.bend_flange(ib) is None:
                    continue
                span_a = self.axial_span(ia, ra["axis"])
                span_b = self.axial_span(ib, ra["axis"])
                if span_a is None or span_b is None:
                    continue
                len_a, len_b = span_a[1] - span_a[0], span_b[1] - span_b[0]
                longest, shortest = max(len_a, len_b), min(len_a, len_b)
                if longest <= 1e-9 or shortest < BEND_EXTENT_MIN_RATIO * longest:
                    continue
                overlap = min(span_a[1], span_b[1]) - max(span_a[0], span_b[0])
                if overlap < BEND_OVERLAP_MIN_RATIO * shortest:
                    continue
                pairs += 1
        return pairs

    def revolution_axis(self) -> tuple | None:
        """
        The axis this part is a body of revolution about, or None.

        A turned part - a shaft, a spacer, a standoff, a bushing, a knob, a
        gland, a spool - is objectively detectable rather than declared: there is
        one axis about which essentially the whole surface is a surface of
        revolution. Cylinders, cones and tori coaxial with it qualify; so do
        planar faces perpendicular to it, because a disc and an annulus are
        surfaces of revolution too. A plane that CONTAINS the axis - a wrench
        flat, a keyway land, the side of a boss on a plate - does not.

        This is the guard the `turned` role would have needed, used directly
        instead of adding a role. See _metric_feature_composition for why: the
        parts being miscoached belong to authors who do not know there is a role
        to claim, and a new lighter rubric is one more thing to shop for.

        Returns (direction, foot) in the same canonical form _axis_key uses.
        """
        if self._revolution != "unset":
            return self._revolution
        total = sum(rec["area"] for rec in self.faces)
        best: tuple | None = None
        if total > 1e-9:
            candidates: list[tuple] = []
            for rec in self.faces:
                if rec["axis"] is None:
                    continue
                if not any(_same_axis(rec["axis"], c) for c in candidates):
                    candidates.append(rec["axis"])
            for key in candidates:
                direction = cq.Vector(*key[0])
                covered = 0.0
                # OFF-AXIS DRILLED FEATURES ARE NOT EVIDENCE EITHER WAY. A turned
                # flange with four cross holes is still a turned flange, and
                # counting the holes' own walls against the test cost it its
                # silhouette outright: measured, four D5-D8 holes in a 80 mm
                # flange took the coverage from 1.00 to 0.94 and the part's whole
                # convex population then read as bore rim. They are removed from
                # BOTH sides of the ratio, and capped, so a part cannot be turned
                # by virtue of being mostly holes.
                feature = 0.0
                for rec in self.faces:
                    if rec["axis"] is not None and _same_axis(rec["axis"], key):
                        covered += rec["area"]
                    elif rec["axis"] is not None:
                        feature += rec["area"]
                    elif rec["kind"] == "plane" and rec["normal"] is not None:
                        if abs(rec["normal"].dot(direction)) > 0.999:
                            covered += rec["area"]
                if feature > REVOLUTION_OFF_AXIS_MAX * total:
                    continue
                judged = total - feature
                if judged > 1e-9 and covered / judged >= REVOLUTION_MIN_AREA_FRACTION:
                    best = key
                    break
        self._revolution = best
        return best

    def is_coaxial(self, direction, point) -> bool:
        """Is a feature at `point` along `direction` on the revolution axis?"""
        axis = self.revolution_axis()
        if axis is None:
            return False
        return _point_on_axis(point, direction, axis, tol=max(0.05, 0.01 * max(self.bbox_size())))

    def revolution_pure(self) -> bool:
        """
        A body of revolution with NOTHING off its axis.

        revolution_axis() tolerates a cross-drilling, a spanner flat or a bolt
        circle (they are removed from both sides of its area ratio), because a
        turned flange with four cross holes is still turned. This is the
        stricter question the profile measurements need: is the WHOLE part its
        meridian profile, so that there is no off-axis layout to read?

        A part that fails this is judged exactly as any other part is - its
        off-axis holes are a layout decision like any other and are scored like
        one - which is what keeps "holes exist but form no pattern" a defect.
        """
        axis = self.revolution_axis()
        if axis is None:
            return False
        return not any(
            rec["axis"] is not None and not _same_axis(rec["axis"], axis) for rec in self.faces
        )

    def _profile_treatment(self, fi: int) -> str | None:
        """
        Is face `fi` a corner TREATMENT on the meridian profile - a chamfer or
        a tangent blend - rather than a piece of the profile itself?

        In the MERIDIAN a corner treatment is an arc or a slant, never a
        straight segment, so only cones and tangent blend surfaces qualify:

        * a narrow annular PLANE is not one. is_break_face() reads a narrow
          planar strip as a chamfer land, which is right on a prismatic part,
          but on a turned profile the narrow annulus between two chamfers is the
          shoulder FACE - the tread of the step - and reading it as a break would
          delete the very corner being judged.
        * a coaxial CYLINDER is not one either, whatever is_blend_face() says.
          That predicate asks for a small radius and two tangent runouts, and a
          shaft journal with a fillet at each end has exactly that: measured, a
          filleted 3-diameter shaft lost its whole middle diameter to the blend
          test, so the profile read as two diameters instead of three and the
          cylinder's own ends could not be given a sense at all (both neighbour
          normals are radial and identical, so the corner has no angle).
        """
        rec = self.faces[fi]
        if rec["kind"] == "torus" and self.is_blend_face(fi):
            return "blend"
        if rec["kind"] == "cone" and self.is_break_face(fi):
            return "chamfer"
        return None

    def revolution_profile(self) -> dict | None:
        """
        The meridian profile of a body of revolution: what diameters it is made
        of, and how each of its corners is made.

        This is the narrow step towards reading composition ALONG the axis
        rather than only in the plane perpendicular to it. Everything a turned
        part's refinement consists of lives here - step transitions, shoulder
        relief, rim breaks, crown blends, groove roots - and none of it is
        visible to a metric that only knows how to arrange feature centres on a
        flat face.

        Returns None when the part is not a body of revolution. Otherwise:
          radii     the distinct body diameters the profile is turned to
          curved    body walls that are not cylinders - a taper, a crown, a
                    formed profile: each one is a diameter decision too
          corners   one record per profile corner, with its sense (convex or
                    concave) and its treatment ("raw", "chamfer", "blend")
          unresolved corners whose sense could not be decided; they are counted,
                    never guessed away
        """
        axis = self.revolution_axis()
        if axis is None:
            return None
        if self._profile is not None:
            return self._profile

        direction = cq.Vector(*axis[0])
        members: dict[int, bool] = {}  # face index -> is a WALL (not an end/shoulder face)
        for i, rec in enumerate(self.faces):
            coaxial = rec["axis"] is not None and _same_axis(rec["axis"], axis)
            perp = (
                rec["kind"] == "plane"
                and rec["normal"] is not None
                and abs(rec["normal"].dot(direction)) > 0.999
            )
            if coaxial or perp:
                members[i] = not perp

        radii: set[float] = set()
        curved = 0
        for fi, is_wall in members.items():
            if not is_wall or self._profile_treatment(fi) is not None:
                continue
            rec = self.faces[fi]
            if rec["kind"] == "cylinder" and rec["radius"]:
                radii.add(round(rec["radius"], 1))
            else:
                curved += 1

        corners: list[dict] = []
        unresolved = 0

        # 1. corners that carry a treatment: one record per chamfer or blend
        for fi in members:
            kind = self._profile_treatment(fi)
            if kind is None:
                continue
            sense = self._corner_sense(fi, members)
            if sense is None:
                unresolved += 1
                continue
            corners.append({"sense": sense, "treatment": kind, "face": fi})

        # 2. corners that carry none: a profile edge between two untreated
        #    profile faces is a raw corner, and its own convexity is well
        #    conditioned because the two faces are not tangent there.
        for e in self.edges:
            if e["kind"] not in ("convex", "concave"):
                continue
            f0, f1 = e["faces"][0], e["faces"][1]
            if f0 not in members or f1 not in members:
                continue
            if self._profile_treatment(f0) or self._profile_treatment(f1):
                continue
            corners.append(
                {
                    "sense": "convex" if e["kind"] == "convex" else "concave",
                    "treatment": "raw",
                    "face": f0,
                    "length_mm": round(e["length"], 2),
                }
            )

        self._profile = {
            "axis": axis,
            "radii": sorted(radii),
            "curved": curved,
            "elements": len(radii) + curved,
            "corners": corners,
            "unresolved": unresolved,
            "faces": len(members),
        }
        return self._profile

    def _corner_sense(self, fi: int, members: dict[int, bool]) -> str | None:
        """
        Convex or concave, measured ACROSS a whole treatment face.

        The per-edge convexity probe steps a fraction of a millimetre off the
        edge and compares against the neighbouring face's normal there, which is
        exactly degenerate for a TANGENT edge: both normals agree at the edge
        and the sign is decided by second-order curvature. Measured on the
        turned spool, that read the convex round-over of a flange corner as
        smooth_CONCAVE - so a part could have banked shoulder relief by rounding
        an outside corner, which is the opposite of the move being asked for.

        Across the treatment face the two neighbours' normals differ by the
        whole corner angle, so the same test is well conditioned:
        (nB - nA) . (mB - mA) > 0 exactly when the normal rotates the way an
        exterior corner turns.

        THE NEIGHBOUR IS NOT ALWAYS THE FLANK, and reading it as one made this
        give up on ordinary turned geometry. A DEBURRED CHAMFER - a shoulder
        chamfer whose own two edges are then broken, which is what a machinist
        hands back - puts a small blend on each side of the cone, so the cone's
        neighbours are treatment faces rather than the cylinder and the annulus
        that actually turn the corner. Measured on a 30 x 32 mm two-diameter
        body whose root chamfer was deburred R0.3: on one side of the cone OCC
        left a torus and on the other an unnamed surface of revolution with no
        axis, so neither was a profile member, `touch` held one entry, the sense
        was None, and pattern_discipline ERRORED at full weight - 0.5 of its
        population unresolved against a 0.10 limit - taking the part to 25.2.
        With the walk the same body reads pattern_discipline 75.0 (one root
        blend and one root chamfer, both concave) and 34.2 overall. Nothing
        about that part was hard to measure; deburring the chamfer was.

        So the walk steps THROUGH anything that is itself corner treatment - a
        break face, or a narrow patch the surface classifier could not name -
        until it reaches the flank that turns. It stops at the first profile
        member that carries no treatment, refuses to walk through anything wider
        than a break, and refuses to guess when the continuation is ambiguous:
        an unresolved corner is still counted rather than invented.
        """
        touch: list[tuple] = []
        for e in self.face_edges[fi]:
            if e["kind"] in SKIPPED_EDGE_KINDS or e["mid"] is None:
                continue
            other = [x for x in e["faces"] if x != fi]
            if len(other) != 1:
                continue
            flank = self._walk_to_flank(fi, e, other[0], members)
            if flank is None:
                continue
            touch.append(flank)
        if len(touch) != 2:
            return None
        (_a, ma, na), (_b, mb, nb) = touch
        span = mb - ma
        if span.Length <= 1e-9:
            return None
        value = (nb - na).dot(span)
        if abs(value) < 1e-9:
            return None
        return "convex" if value > 0 else "concave"

    def _walk_to_flank(
        self, start: int, edge: dict, neighbour: int, members: dict[int, bool]
    ) -> tuple[int, cq.Vector, cq.Vector] | None:
        """
        (flank face, the edge midpoint it was reached at, its outward normal
        there), stepping through corner treatment on the way.

        A flank is a profile MEMBER that carries no treatment of its own: the
        cylinder, the taper or the annulus whose meridian direction the corner
        actually turns between. Everything between it and `start` is more of the
        same corner - the blend on a deburred chamfer, or a runout patch OCC
        produced as a nameless surface of revolution - and stepping through it
        is what keeps the two normals in the sense test a whole corner apart.

        The walk is deliberately timid, because a wrong flank is worse than an
        unresolved corner: it only crosses a face narrower than a break, it only
        continues when exactly one onward edge is available, and it gives up
        after CORNER_WALK_MAX hops.
        """
        seen = {start}
        cur, e = neighbour, edge
        for _hop in range(CORNER_WALK_MAX):
            if cur in members and self._profile_treatment(cur) is None:
                try:
                    return cur, e["mid"], self.faces[cur]["face"].normalAt(e["mid"])
                except Exception:
                    return None
            # Not a flank: either corner treatment, or off the profile entirely.
            # Cross it only if it is break-sized, so a drilled wall or a big
            # unnamed patch stops the walk instead of redirecting it.
            width = self.faces[cur]["width"]
            if not (0.0 < width <= self.break_cap):
                return None
            seen.add(cur)
            onward: list[tuple[int, dict]] = []
            for x in self.face_edges[cur]:
                if x["kind"] in SKIPPED_EDGE_KINDS or x["mid"] is None:
                    continue
                nxt = [y for y in x["faces"] if y != cur]
                if len(nxt) != 1 or nxt[0] in seen:
                    continue
                onward.append((nxt[0], x))
            if len(onward) != 1:
                return None
            cur, e = onward[0]
        return None

    def is_band_face(self, fi: int) -> bool:
        """
        The material-thickness band around a sheet-metal blank.

        2 mm stock cannot carry a chamfer or a plan fillet on its blanked
        perimeter, so for role=sheet those edges are removed from the
        population entirely rather than counted as unbroken forever. Nothing is
        excluded on a part that is not sheet-like, whatever its spec.json says.
        """
        if not self.is_sheet_like():
            return False
        rec = self.faces[fi]
        t = self.sheet_thickness
        return rec["kind"] == "plane" and 0.0 < rec["width"] <= 1.5 * t

    def cylinder_wrap(self, feature: dict) -> float:
        """
        How much of a full barrel a merged cylindrical feature actually covers.

        lib/analyze_step.py groups every coaxial cylindrical face of one radius
        into one feature, so a POCKET CORNER FILLET reports as a hole: on the
        corpus's panel-and-rib rung, eight 2.7 mm2 R3 corner slivers on the two
        flank panels merged into "4 x D6 holes on Y, 58.8 mm long" and scored
        that part 67/100 for fastener rhythm although it has no fastener at all.
        A bore wraps its axis; a corner fillet subtends a quarter turn of it.
        """
        direction = tuple(feature["dir"])
        radius, length = feature["radius"], feature["length"]
        if radius <= 1e-9 or length <= 1e-9:
            return 0.0
        area = sum(
            rec["area"]
            for rec in self.faces
            if rec["kind"] == "cylinder"
            and rec["axis"] is not None
            and abs((rec["radius"] or 0.0) - radius) < 0.02
            and _point_on_axis(feature["p1"], direction, rec["axis"])
        )
        return area / (2.0 * math.pi * radius * length)

    def blend_cylinders(self) -> list[tuple[float, tuple]]:
        """(radius, axis key) of every cylindrical face that is a blend, so a
        pocket's corner fillets are not mistaken for a ring of bolt holes."""
        return [
            (r["radius"], r["axis"])
            for i, r in enumerate(self.faces)
            if r["kind"] == "cylinder" and r["axis"] is not None and self.is_blend_face(i)
        ]

    def bbox_size(self) -> tuple[float, float, float]:
        """
        The part's extents along its OWN axes, longest first.

        Named `bbox_` because that is what it has always been called and every
        caller wants the same thing from it; it is the frame box, not the world
        box, and the two agree exactly on an axis-aligned part.
        """
        return self.frame.size

    def bbox_centre(self) -> tuple[float, float, float]:
        """The frame box centre, in WORLD coordinates."""
        c = self.frame.centre
        return (c.x, c.y, c.z)

    def bbox_surface(self) -> float:
        return self.frame.surface

    def bbox_projected_area(self, normal) -> float:
        """Exact area of the frame box projected onto a plane with this normal."""
        n = normal if isinstance(normal, cq.Vector) else cq.Vector(normal)
        return self.frame.projected_area(n)

    def developed(self, fi: int):
        """
        This face flattened into a plane of true millimetres, or None when it
        cannot be. See _develop_metric and the Developed dataclass.
        """
        if fi not in self._developed:
            rec = self.faces[fi]
            if rec["kind"] not in _DEVELOPABLE_KINDS:
                self._developed[fi] = (None, f"a {rec['kind']} surface is not developable")
            else:
                try:
                    self._developed[fi] = _develop_metric(self, fi)
                except Exception as exc:  # pragma: no cover - kernel defence
                    self.probe_failures += 1
                    self._developed[fi] = (None, f"development failed: {type(exc).__name__}")
        return self._developed[fi][0]

    def develop_failure(self, fi: int) -> str:
        """Why `developed` returned None; empty string when it did not."""
        self.developed(fi)
        return self._developed[fi][1]

    def align_tol(self) -> float:
        return max(ALIGN_TOL_MIN, ALIGN_TOL_FRACTION * max(self.bbox_size()))


# ---------------------------------------------------------------------------
# Metric: edge break coverage + sharp edge length
# ---------------------------------------------------------------------------
def _classify_breaks(topo: Topology, rubric: Rubric) -> dict:
    """
    Split convex EXTERIOR edge length into broken and sharp, in two populations.

    BODY: plane-plane and plane-blend edges - the corners a human reads as the
    silhouette of the part. A corner that has been broken no longer appears as
    one edge; it appears as the two boundary edges of the chamfer land or blend
    face, so each is weighted 0.5 and one design corner contributes its length
    once either way.

    SECONDARY: every edge that belongs to a bore or a boss, including the edges
    of the break faces that serve one, plus the detail edges where both sides
    are narrow feature strips (see is_detail_edge). Scored as its own term at a
    light weight, because a bare bore rim or an unbroken rib crest is a milder
    defect than a knife edge running along a whole face perimeter - which is
    what the old docstring claimed while leaving rim length in a free, unscored
    bucket.

    Three things the audit found are closed here: a concave blend runout earns
    nothing (its convexity is now known before the tangent branch); an edge
    buried inside a sealed cavity is not scored at all; and a countersink is
    credited on the rim term, not the body term, so drilling a raw box can no
    longer raise its body coverage.
    """
    body_broken = body_sharp = 0.0
    rim_broken = rim_bare = 0.0
    unresolved = 0.0
    reasons: list[str] = []
    sharp_edges: list[dict] = []
    rim_edges: list[dict] = []
    excluded_perimeter = 0.0
    # Convex exterior edge length that carries an edge-break decision and was
    # NOT judged: a crease too shallow to read as a knife edge, and a tangent
    # join whose neighbours are not break faces. Neither is a defect, and
    # neither is scored, so both leave the population silently - which is
    # exactly the shape of the coverage illusion Part 2 of the invariant
    # exists to catch. Counted here so the metric can say how much of the
    # part's edge it actually judged. See EXAMINED_MIN.
    shallow = 0.0
    tangent_free = 0.0

    for e in topo.edges:
        kind = e["kind"]
        if kind in SKIPPED_EDGE_KINDS:
            continue
        if kind == "unknown":
            unresolved += e["length"]
            if e.get("error") and len(reasons) < 3:
                reasons.append(e["error"])
            continue
        if kind in ("concave", "smooth_concave"):
            continue

        f0, f1 = e["faces"]
        if rubric.exclude_blank_perimeter and (topo.is_band_face(f0) or topo.is_band_face(f1)):
            excluded_perimeter += e["length"]
            continue

        ext0, ext1 = topo.is_exterior(f0), topo.is_exterior(f1)
        if ext0 is None and ext1 is None:
            unresolved += e["length"]
            if len(reasons) < 3:
                reasons.append("exterior reachability undecided")
            continue
        if not (ext0 or ext1):
            continue  # buried in a cavity: nobody can see it, nobody scores it

        b0, b1 = topo.is_break_face(f0), topo.is_break_face(f1)
        rim = topo.is_rim_edge(f0, f1) or topo.is_detail_edge(f0, f1)

        if kind == "smooth_convex":
            if b0 or b1:
                if rim:
                    rim_broken += 0.5 * e["length"]
                else:
                    body_broken += 0.5 * e["length"]
            else:
                tangent_free += e["length"]
            continue

        angle = e["angle_deg"]
        if angle < SHARP_MIN_DEG:
            shallow += e["length"]
            continue  # a shallow crease, not a knife edge

        # A break face only breaks the edges it meets at a shallow angle. Where
        # it meets a neighbour square-on (a chamfer land crossing a bore wall)
        # the edge is judged on its own merits below.
        broken = angle <= CHAMFER_MAX_DEG and (b0 or b1)
        if rim:
            if broken:
                rim_broken += 0.5 * e["length"]
            else:
                rim_bare += e["length"]
                rim_edges.append(e)
            continue

        if broken:
            body_broken += 0.5 * e["length"]
            continue

        k0, k1 = topo.faces[f0]["kind"], topo.faces[f1]["kind"]
        on_silhouette = (
            (k0 == "plane" and k1 == "plane")
            or topo.is_blend_face(f0)
            or topo.is_blend_face(f1)
            or "cone" in (k0, k1)
            # the OUTSIDE of a barrel is a silhouette surface: where the OD of a
            # turned part meets its end face is a corner a machinist breaks, and
            # filing it under "bore rim" is what emptied the body population on
            # every body of revolution. See Topology.cylinder_is_bore.
            or topo.is_barrel_face(f0)
            or topo.is_barrel_face(f1)
        )
        if on_silhouette:
            body_sharp += e["length"]
            sharp_edges.append(e)
        else:
            rim_bare += e["length"]
            rim_edges.append(e)

    return {
        "body_broken_mm": body_broken,
        "body_sharp_mm": body_sharp,
        "rim_broken_mm": rim_broken,
        "rim_bare_mm": rim_bare,
        "unresolved_mm": unresolved,
        "excluded_perimeter_mm": excluded_perimeter,
        "shallow_mm": shallow,
        "tangent_free_mm": tangent_free,
        "reasons": reasons,
        "sharp_edges": sharp_edges,
        "rim_edges": rim_edges,
    }


def _edge_examination(breaks: dict) -> tuple[float, float]:
    """
    (examined mm, relevant mm) for the two edge metrics.

    RELEVANT is every convex edge a human can see that carries an edge-break
    decision. EXAMINED is the part of it that reached a body or rim term. The
    difference is the unresolved length, the shallow creases and the tangent
    joins with no break face beside them - length that leaves the population
    without ever being judged. The blanked perimeter of a sheet part is not in
    either: a role exclusion is the one legitimate way a metric loses scope,
    and its weights already sum to 1.00 without it.
    """
    examined = (
        breaks["body_broken_mm"]
        + breaks["body_sharp_mm"]
        + breaks["rim_broken_mm"]
        + breaks["rim_bare_mm"]
    )
    relevant = examined + breaks["unresolved_mm"] + breaks["shallow_mm"] + breaks["tangent_free_mm"]
    return examined, relevant


def _group_sharp(topo: Topology, sharp_edges: list[dict], top: int = 6) -> list[dict]:
    """Group unbroken edges by the pair of face normals so findings name rims."""
    groups: dict[tuple, dict] = {}
    for e in sharp_edges:
        n0, n1 = e["normals"]
        key = tuple(
            sorted(
                (
                    tuple(round(c, 1) for c in (n0.x, n0.y, n0.z)),
                    tuple(round(c, 1) for c in (n1.x, n1.y, n1.z)),
                )
            )
        )
        g = groups.setdefault(
            key, {"length_mm": 0.0, "count": 0, "longest": 0.0, "at": None, "normals": key}
        )
        g["length_mm"] += e["length"]
        g["count"] += 1
        if e["length"] > g["longest"]:
            g["longest"] = e["length"]
            g["at"] = _round_pt(e["mid"])
    out = sorted(groups.values(), key=lambda g: -g["length_mm"])[:top]
    for g in out:
        g["length_mm"] = round(g["length_mm"], 1)
        g["longest"] = round(g["longest"], 1)
        g["face_hint"] = _normal_label(g["normals"])
    return out


_AXIS_NAMES = {
    (0, 0, 1): "+Z",
    (0, 0, -1): "-Z",
    (1, 0, 0): "+X",
    (-1, 0, 0): "-X",
    (0, 1, 0): "+Y",
    (0, -1, 0): "-Y",
}


def _normal_label(normals: tuple) -> str:
    names = []
    for n in normals:
        key = tuple(int(round(c)) for c in n)
        names.append(_AXIS_NAMES.get(key, "oblique"))
    return " / ".join(names)


def _frame_axis_labels(frame: Frame) -> tuple[str, str, str]:
    """
    A name for each frame axis, for findings to quote.

    On an axis-aligned part these are "X", "Y" and "Z" and every message reads
    exactly as it always did. On a part modelled at an angle the world letters
    would be a lie, so the axes are named by their rank in the frame - "1" is
    the longest - and the reader can see from the report's own `frame` block
    where they point.
    """
    if not frame.is_world_aligned():
        return ("axis1", "axis2", "axis3")
    world = {0: "X", 1: "Y", 2: "Z"}
    out = []
    for a in frame.axes:
        comps = (abs(a.x), abs(a.y), abs(a.z))
        out.append(world[comps.index(max(comps))])
    return (out[0], out[1], out[2])


BODY_COVERAGE_BEST, BODY_COVERAGE_WORST = 0.92, 0.15
RIM_COVERAGE_BEST, RIM_COVERAGE_WORST = 0.90, 0.20
RIM_WEIGHT = 0.15


def _metric_edge_break(topo: Topology, breaks: dict) -> dict:
    examined, relevant = _edge_examination(breaks)
    body_total = breaks["body_broken_mm"] + breaks["body_sharp_mm"]
    rim_total = breaks["rim_broken_mm"] + breaks["rim_bare_mm"]
    population = body_total + rim_total + breaks["unresolved_mm"]

    if body_total < 1e-6:
        # NEITHER OF THESE IS A FREE PASS, AND THE RIM NEVER STANDS IN FOR THE
        # BODY. The old code fell through to the composite whenever the body
        # population was empty, and the composite then renormalised onto its
        # 0.15 rim term - so a part with no silhouette edges left to judge and
        # one chamfered bore mouth scored 100.0 on the metric whose whole job is
        # to say whether the corners of the part are broken. Two geometries
        # reached it: a body of revolution (whose OD used to be classified as a
        # bore - see Topology.cylinder_is_bore) and a flat blank declared
        # role=sheet, whose blanked-perimeter exclusion removes the entire
        # outline (see _guard_sheet). Both root causes are fixed; this is the
        # backstop, and it reports the honest answer, which is that there is no
        # body edge-break decision to read.
        detail = (
            "no convex exterior edge exists at all - a fully blended body has "
            "made no edge-break decision anywhere"
            if rim_total < 1e-6
            else (
                f"not one convex edge of the silhouette is left to judge - the whole "
                f"convex population is bore/detail rim ({rim_total:.0f} mm), so there "
                f"is no body edge-break decision to read. A chamfered bore mouth is "
                f"not a broken corner"
            )
        )
        return _degrade(
            _metric(
                "edge_break_coverage",
                ABSENT,
                0.0,
                detail,
                value=0.0,
                body_score=0.0,
                rim_score=(
                    None
                    if rim_total < 1e-6
                    else round(
                        _lerp_score(
                            breaks["rim_broken_mm"] / rim_total,
                            RIM_COVERAGE_BEST,
                            RIM_COVERAGE_WORST,
                        ),
                        1,
                    )
                ),
            ),
            population,
            breaks["unresolved_mm"],
            breaks["reasons"],
            examined=examined,
            relevant=relevant,
        )

    body_coverage = breaks["body_broken_mm"] / body_total
    body_score = _lerp_score(body_coverage, BODY_COVERAGE_BEST, BODY_COVERAGE_WORST)
    rim_coverage = None
    rim_score = None
    if rim_total > 1e-6:
        rim_coverage = breaks["rim_broken_mm"] / rim_total
        rim_score = _lerp_score(rim_coverage, RIM_COVERAGE_BEST, RIM_COVERAGE_WORST)
        score = (1.0 - RIM_WEIGHT) * body_score + RIM_WEIGHT * rim_score
    else:
        score = body_score

    # "There are convex edges and NOT ONE of them is broken anywhere" is a
    # defect, not an inapplicable metric: naming it says the part never had a
    # refinement pass. A part whose bores are chamfered but whose body is raw
    # is scored, not declared absent - it did the work, just not where it counts,
    # and RUBRIC_FLOORS reads `body_score` rather than this composite so that
    # deburring can never buy its way over the floor.
    nothing_broken = breaks["body_broken_mm"] < 1e-6 and breaks["rim_broken_mm"] < 1e-6
    status = ABSENT if nothing_broken else SCORED
    if status == ABSENT:
        score = body_score = 0.0

    msg = (
        f"{body_coverage * 100:.1f}% of convex body edge length is broken "
        f"({breaks['body_broken_mm']:.0f} of {body_total:.0f} mm), body term "
        f"{body_score:.1f}"
    )
    if rim_coverage is not None:
        msg += f"; {rim_coverage * 100:.0f}% of bore/boss rim length is broken"
    if breaks["excluded_perimeter_mm"] > 0:
        msg += f"; {breaks['excluded_perimeter_mm']:.0f} mm of blanked perimeter excluded"

    return _degrade(
        _metric(
            "edge_break_coverage",
            status,
            score,
            msg,
            value=round(body_coverage, 4),
            body_score=round(body_score, 1),
            rim_score=None if rim_score is None else round(rim_score, 1),
            body_broken_mm=round(breaks["body_broken_mm"], 1),
            body_sharp_mm=round(breaks["body_sharp_mm"], 1),
            rim_broken_mm=round(breaks["rim_broken_mm"], 1),
            rim_bare_mm=round(breaks["rim_bare_mm"], 1),
            rim_coverage=None if rim_coverage is None else round(rim_coverage, 4),
            worst=_group_sharp(topo, breaks["sharp_edges"]),
        ),
        population,
        breaks["unresolved_mm"],
        breaks["reasons"],
        examined=examined,
        relevant=relevant,
    )


def _metric_sharp_length(topo: Topology, breaks: dict) -> dict:
    diag = math.sqrt(sum(d * d for d in topo.bbox_size()))
    if diag < 1e-6:
        return _metric("sharp_edge_length", METRIC_ERROR, None, "degenerate bounding box")
    examined, relevant = _edge_examination(breaks)
    sharp = breaks["body_sharp_mm"]
    ratio = sharp / diag
    # A fully broken part sits near 0. One unbroken face perimeter on a box is
    # roughly 2.0 diagonals; 3.0 (every edge of a prism) is the floor.
    # 6.9 diagonals, not 2.5, is what a fully raw prism measures (a cube has
    # 12a of edge against a a*sqrt(3) diagonal). The old floor put every raw
    # part on 0 with no resolution left between them, which is the same cliff
    # the audit called out elsewhere.
    score = _lerp_score(ratio, best=0.05, worst=7.0)
    population = breaks["body_broken_mm"] + breaks["body_sharp_mm"] + breaks["unresolved_mm"]
    return _degrade(
        _metric(
            "sharp_edge_length",
            SCORED,
            score,
            f"{sharp:.0f} mm of unbroken convex edge ({ratio:.2f} x bbox diagonal)",
            value=round(sharp, 1),
            per_diagonal=round(ratio, 3),
            bbox_diagonal_mm=round(diag, 1),
        ),
        population,
        breaks["unresolved_mm"],
        breaks["reasons"],
        examined=examined,
        relevant=relevant,
    )


# ---------------------------------------------------------------------------
# Face polygons, relief probes: the geometry behind face_composition
# ---------------------------------------------------------------------------
try:  # shapely is a hard dependency of the repo, but never fail the import
    from shapely import Polygon, maximum_inscribed_circle, union_all

    _SHAPELY = True
except Exception:  # pragma: no cover - only if the environment is broken
    _SHAPELY = False


def _wire_uv(wire: cq.Wire, origin, xdir, ydir, chord: float = POLY_CHORD_MM) -> list[tuple]:
    """
    A wire as an ordered ring of (u, v) points in a face's own plane basis.

    BRepTools_WireExplorer is what makes it ORDERED; Shape.Edges() returns a
    map, and a polygon built from an unordered edge set is nonsense.
    """
    pts: list[tuple[float, float]] = []
    exp = BRepTools_WireExplorer(wire.wrapped)
    while exp.More():
        edge = cq.Edge(exp.Current())
        reverse = edge.wrapped.Orientation() == TopAbs_REVERSED
        try:
            length = edge.Length()
        except Exception:
            length = chord
        n = max(2, min(120, int(math.ceil(length / chord)) + 1))
        ts = [i / (n - 1) for i in range(n)]
        if reverse:
            ts.reverse()
        for t in ts[:-1]:
            p = edge.positionAt(t)
            d = p - origin
            pts.append((d.dot(xdir), d.dot(ydir)))
        exp.Next()
    return pts


def _face_basis(rec: dict) -> tuple:
    normal = rec["normal"]
    seed = cq.Vector(0, 0, 1) if abs(normal.z) < 0.9 else cq.Vector(1, 0, 0)
    xdir = normal.cross(seed).normalized()
    ydir = normal.cross(xdir).normalized()
    return rec["face"].Center(), xdir, ydir, normal


def _relief_mm(topo: Topology, ring, origin, xdir, ydir, normal) -> float:
    """
    How deep is the region this inner wire bounds?

    Rays are fired DOWN the face normal from 0.5 mm above a ring of points just
    inside the wire, and the deepest first hit wins. Deliberately not "the
    extent of the adjacent face along the normal": that version was prototyped
    and reads 0.4 mm for the exemplar's O-ring groove, because the wire's
    immediate neighbour is its 0.4 mm lead-in chamfer - it drops a real feature
    and moves that face's void from 0.223 to 0.625.

    The same trap catches a ring buffered only slightly inward: a recessed panel
    with a 1.0 mm broken mouth is still ON its own mouth chamfer 0.7 mm in, so a
    2.0 mm deep panel measured 0.72 mm and was thrown away as decoration. The
    caller therefore always includes a point deep inside the region, and the
    deepest hit anywhere wins.

    A downward ray alone is not enough either. When the face is a groove FLOOR
    and the region inside its wire is the plateau standing PROUD of it, the
    probe starts inside material and the first hit is the far side of the part:
    the corpus's decorative scribe grooves, 0.9 mm deep, measured 29.1 mm of
    relief on a 30 mm slab and bought a perfect feature_composition score. So a
    deep reading is confirmed with an upward ray, and a region that is proud is
    measured as proud - the magnitude is what counts, in either direction.
    """
    best = 0.0
    for u, v in ring:
        p = origin + xdir * u + ydir * v + normal * 0.5
        try:
            hits = [h for h in _ray_hits(topo.shape, p, normal * -1.0) if h > 1e-6]
        except Exception:
            continue
        if not hits:
            return 1e6  # a through feature: unambiguously real relief
        depth = hits[0] - 0.5
        if depth > 3.0 * RELIEF_MIN_MM:
            try:
                above = [h for h in _ray_hits(topo.shape, p, normal) if h > 1e-6]
            except Exception:
                above = []
            if above:  # material over the probe: the region is proud, not deep
                depth = above[0] + 0.5
        best = max(best, depth)
    return best


def _feature_wires(topo: Topology, fi: int) -> tuple[list, list, int]:
    """
    Inner wires of a planar face, split into (real features, decoration), plus
    a count of the wires that could not be judged.

    "Real" needs BOTH depth (RELIEF_MIN_MM) and size (RELIEF_MIN_AREA_MM2), so
    a wrapped scribe groove - the corpus's decoration gaming case, 0.5-0.9 mm
    deep - never subtracts from the empty region it pretends to fill.
    """
    cached = topo.wire_cache.get(fi)
    if cached is not None:
        return cached
    rec = topo.faces[fi]
    origin, xdir, ydir, normal = _face_basis(rec)
    real: list[list[tuple]] = []
    fake: list[list[tuple]] = []
    failed = 0
    try:
        wires = rec["face"].innerWires()
    except Exception:
        topo.wire_cache[fi] = ([], [], 1)
        return [], [], 1
    for w in wires:
        try:
            ring = _wire_uv(w, origin, xdir, ydir)
        except Exception:
            failed += 1
            continue
        if len(ring) < 3 or not _SHAPELY:
            failed += 1
            continue
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        area = abs(poly.area) if not poly.is_empty else 0.0
        if area < RELIEF_MIN_AREA_MM2:
            fake.append(ring)
            continue
        inset = max(0.3, 0.02 * math.sqrt(area))
        probe = poly.buffer(-inset)
        if probe.is_empty:
            probe = poly
        try:
            ring_geom = probe if hasattr(probe, "exterior") else probe.geoms[0]
            coords = list(ring_geom.exterior.coords)
        except Exception:
            coords = ring
        step = max(1, len(coords) // 10)
        samples = list(coords[::step][:10]) or list(ring[:10])
        try:  # a point guaranteed to be well inside, not on the mouth break
            inner = poly.representative_point()
            samples.append((inner.x, inner.y))
        except Exception:
            pass
        if _relief_mm(topo, samples, origin, xdir, ydir, normal) >= RELIEF_MIN_MM:
            real.append(ring)
        else:
            fake.append(ring)
    topo.wire_cache[fi] = (real, fake, failed)
    return real, fake, failed


def _face_void(topo: Topology, fi: int) -> tuple[float | None, dict]:
    """
    2 * (largest inscribed circle radius) / sqrt(silhouette), on the face
    polygon once every real feature has been punched out of it.

    Normalising by the SILHOUETTE the face looks at, not by the face's own
    area, is what makes a small blank land (a frame, a rib flank, a chamfer
    strip) cheap and a big blank face expensive. It replaces the old
    blank_face_ratio, which asked a yes/no question - does this face own an
    inner wire covering 1% of it - and so had two values in practice: three
    through holes turned a raw knife-edged box from 0 into a perfect 100.
    """
    rec = topo.faces[fi]
    if not _SHAPELY or rec["normal"] is None:
        return None, {"why": "shapely or face normal unavailable"}
    ref = topo.bbox_projected_area(rec["normal"])
    if ref < 1e-6:
        return None, {"why": "degenerate silhouette"}
    origin, xdir, ydir, normal = _face_basis(rec)
    try:
        outer = _wire_uv(rec["face"].outerWire(), origin, xdir, ydir)
    except Exception as exc:
        return None, {"why": f"outer wire: {type(exc).__name__}"}
    if len(outer) < 3:
        return None, {"why": "outer wire too coarse"}
    real, _fake, failed = _feature_wires(topo, fi)
    try:
        poly = Polygon(outer, real)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            return None, {"why": "empty polygon"}
        tol = max(0.05, math.sqrt(ref) / 400.0)
        radius = maximum_inscribed_circle(poly, tol).length
    except Exception as exc:
        return None, {"why": f"inscribed circle: {type(exc).__name__}"}
    void = 2.0 * radius / math.sqrt(ref)
    return void, {
        "lec_radius_mm": round(radius, 2),
        "silhouette_mm2": round(ref, 1),
        "features": len(real),
        "wire_failures": failed,
        "at": _round_pt(rec["face"].Center()),
        "normal": _AXIS_NAMES.get(
            tuple(int(round(c)) for c in (normal.x, normal.y, normal.z)), "oblique"
        ),
    }


# ---------------------------------------------------------------------------
# Developing a curved face: the skin a turned part is actually made of
# ---------------------------------------------------------------------------
# WHY THIS EXISTS
# face_composition built its population from PLANES ONLY. On a body of
# revolution the whole visible skin is a cylinder, so the metric could not see
# it at all and read only the two end faces - and on a THIN-WALLED turned part
# those are narrow annuli that can never contain a large empty circle. So the
# metric returned a flattering number at its full 0.19 weight having examined
# 14% of the exterior (3.7% on a 2 mm wall). Measured, build -> export ->
# re-import -> score: a six-line tube (bore, counterbore, one arbitrary ring
# groove) scored face_composition 100.0 and 94.0/A overall, above every good
# case in the corpus and this repo's own exemplar at 83.1; a bored tube with no
# features at all and one blanket .fillet(1.0) scored 77.3/B and cleared the 70
# gate unassisted. The prismatic analogue never had the defect, because a box
# still has flat outer walls the metric can read: on the same corpus a plain
# broken box measures face_composition 5 and a panelled, ribbed, bolted one 14
# against the exemplar's 96.
#
# The fix is to DEVELOP the face: flatten it into a plane where distances are
# true millimetres and run the SAME largest-empty-region computation there. A
# groove, a flat, a boss or a drilling then punches a real hole in the polygon
# exactly as it does on a plane, and a bare drum reads as the big blank panel a
# human sees.
#
# THE MAP, AND WHERE IT IS APPROXIMATE
# (u, v) -> (su * u, sv * v), with su = max |dP/du| and sv = max |dP/dv| taken
# over the face's own parameter box.
#   cylinder    EXACT.  |dP/du| = R and |dP/dv| = 1 everywhere, so the image is
#               the true development: arc length around the axis against
#               distance along it.
#   cone        EXACT in v (v is arc length along the generatrix); LINEARISED
#               in u, where the true development is an annular sector. The
#               sector is replaced by the rectangle its WIDEST circle sweeps.
#   torus,      APPROXIMATE. |dP/du| is the local radius of revolution and
#   sphere,     varies with v; again the widest circle sets the width. For a
#   revolution  general revolution |dP/dv| may vary too, and the longest
#               meridian step sets the height.
#
# EVERY APPROXIMATION OVER-STATES THE DEVELOPED EXTENT AND NEVER UNDER-STATES
# IT. A wider, taller developed polygon spreads the features further apart and
# lets a LARGER empty circle fit, which lowers the score. That direction is the
# whole point: an approximation that can flatter a part is a hole in the gate,
# and this one can only ever cost points.
#
# Past CURVED_DISTORTION_MAX the stretch is large enough that the answer would
# be a statement about the parametrisation rather than about the part, and the
# face is then reported UNMEASURED - it enters _degrade's population and none
# of its examined area - rather than guessed. That is the coverage invariant,
# not a fallback.

# Samples per parameter direction when reading the first fundamental form.
CURVED_GRID_N = 7
# How far |dP/du| or |dP/dv| may vary across one face before its development is
# too distorted to mean anything. 4.0 admits every cone, torus and crown blend
# measured on the turned probe set; a spherical cap through its own pole, where
# |dP/du| runs to zero, is refused.
CURVED_DISTORTION_MAX = 4.0
# A periodic strip is tiled so an empty region may WRAP the seam instead of
# being cut by it. The tile count is derived (see _curved_face_void); this caps
# the cost for a pathologically long thin rod, which is refused instead.
CURVED_TILE_MAX = 15
# An inner wire whose u-span is nearly the whole period is one that may be
# crossing the seam, where a single closed ring in parameter space cannot
# represent it. Refused rather than mapped into a hole of the wrong size.
CURVED_SEAM_WRAP_MAX = 0.9

_DEVELOPABLE_KINDS = ("cylinder", "cone", "torus", "sphere", "revolution")


@dataclass(frozen=True)
class Developed:
    """
    One curved face flattened into a plane where distances are millimetres.

    `su`/`sv` are the scale factors of the map, `ref_mm2` the silhouette the
    face looks at - the bbox projected area averaged over the outward normals
    the face actually spans, which reduces EXACTLY to the planar branch's
    `bbox_projected_area(normal)` when the normal is constant. `period` is the
    developed circumference when the face wraps a full turn, and None when it
    does not; it is what lets an empty region cross the seam.
    """

    su: float
    sv: float
    ref_mm2: float
    period: float | None
    u_distortion: float
    v_distortion: float
    reversed_face: bool


def _develop_metric(topo: Topology, fi: int) -> tuple[Developed | None, str]:
    """
    The scale factors, the reference silhouette and the periodicity of one
    curved face, from its first fundamental form on a parameter grid.

    The grid INCLUDES the parameter boundary, because the widest circle of a
    cone or a torus is at one end of the v range and nowhere else - sampling
    only the interior read a 6-to-18 mm cone as 16.5 mm wide, which is the one
    direction this map is not allowed to err in. A degenerate row - a pole,
    where |dP/du| is exactly zero - drops out of the grid entirely rather than
    being read as a scale of nothing, so it distorts neither the maximum nor
    the ratio.
    """
    rec = topo.faces[fi]
    face = rec["face"]
    try:
        surf = BRep_Tool.Surface_s(face.wrapped)
        umin, umax, vmin, vmax = BRepTools.UVBounds_s(face.wrapped)
    except Exception as exc:
        return None, f"parameter box: {type(exc).__name__}"
    du_span, dv_span = umax - umin, vmax - vmin
    if not (math.isfinite(du_span) and math.isfinite(dv_span)):
        return None, "unbounded parameter box"
    if du_span <= 1e-12 or dv_span <= 1e-12:
        return None, "degenerate parameter box"

    su_vals: list[float] = []
    sv_vals: list[float] = []
    refs: list[float] = []
    n = CURVED_GRID_N
    # A CLOSED U RANGE HAS ITS FIRST AND LAST SAMPLE AT THE SAME PLACE, and
    # sampling both weighted one point of a full barrel twice. `ref` is the MEAN
    # projected silhouette over the grid, so that bias tilted the mean towards
    # whatever direction the kernel happened to put u = 0 - and this is exactly
    # the class of file-dependence the frame exists to remove, so it only became
    # visible once the ruler stopped moving with it. Measured on a 16 mm barrel
    # with one radial pocket, ref read 1160.8 mm2 with the seam on a frame axis
    # and 1253.7 mm2 with it at 45 degrees to one, moving the empty-region score
    # for a part that had only been turned about its own axis. Dropping the
    # duplicate is the trapezoid rule on a periodic interval: the two half-weight
    # endpoints are one full-weight sample.
    try:
        u_closed = bool(surf.IsUPeriodic()) and du_span >= 2.0 * math.pi - 1e-6
    except Exception:
        u_closed = False
    u_step = du_span / n if u_closed else du_span / (n - 1.0)
    p, d_u, d_v = gp_Pnt(), gp_Vec(), gp_Vec()
    for iu in range(n):
        for iv in range(n):
            u = umin + u_step * iu
            v = vmin + dv_span * iv / (n - 1.0)
            try:
                surf.D1(u, v, p, d_u, d_v)
            except Exception:
                continue
            mu, mv = d_u.Magnitude(), d_v.Magnitude()
            if mu <= 1e-9 or mv <= 1e-9:
                continue
            su_vals.append(mu)
            sv_vals.append(mv)
            cross = d_u.Crossed(d_v)
            if cross.Magnitude() > 1e-12:
                nv = cq.Vector(cross.X(), cross.Y(), cross.Z()).normalized()
                refs.append(topo.bbox_projected_area(nv))
    if not su_vals or not refs:
        return None, "surface derivatives unavailable"

    su, sv = max(su_vals), max(sv_vals)
    u_dist = su / max(min(su_vals), 1e-9)
    v_dist = sv / max(min(sv_vals), 1e-9)
    ref = statistics.fmean(refs)
    if ref < 1e-6:
        return None, "degenerate silhouette"
    if v_dist > CURVED_DISTORTION_MAX:
        return None, f"meridian scale varies {v_dist:.1f}x - not developable"

    period = None
    try:
        if surf.IsUPeriodic() and du_span >= 2.0 * math.pi - 1e-6:
            period = su * float(surf.UPeriod())
    except Exception:
        period = None
    return (
        Developed(
            su=su,
            sv=sv,
            ref_mm2=ref,
            period=period,
            u_distortion=u_dist,
            v_distortion=v_dist,
            reversed_face=face.wrapped.Orientation() == TopAbs_REVERSED,
        ),
        "",
    )


def _uv_ring(
    face: cq.Face, wire: cq.Wire, dev: Developed, chord: float = POLY_CHORD_MM
) -> list[tuple[float, float]]:
    """
    A wire as an ordered ring in the face's DEVELOPED plane.

    The PCURVE, never the 3D curve. On a periodic face the seam edge is used
    twice and only its parameter-space image tells the two uses apart, so
    projecting 3D points would fold the developed rectangle onto a line and
    every cylinder would read as empty.
    """
    pts: list[tuple[float, float]] = []
    exp = BRepTools_WireExplorer(wire.wrapped, face.wrapped)
    while exp.More():
        edge = exp.Current()
        try:
            c2d = BRepAdaptor_Curve2d(edge, face.wrapped)
            a, b = c2d.FirstParameter(), c2d.LastParameter()
            length = cq.Edge(edge).Length()
        except Exception:
            exp.Next()
            continue
        n = max(2, min(240, int(math.ceil(length / chord)) + 1))
        ts = [i / (n - 1) for i in range(n)]
        if edge.Orientation() == TopAbs_REVERSED:
            ts.reverse()
        for t in ts[:-1]:
            try:
                q = c2d.Value(a + (b - a) * t)
            except Exception:
                continue
            pts.append((dev.su * q.X(), dev.sv * q.Y()))
        exp.Next()
    return pts


def _curved_relief_mm(topo: Topology, fi: int, dev: Developed, ring) -> float:
    """
    How deep is the region this inner wire bounds, on a curved face?

    The planar twin of this probe fires down a constant face normal; here the
    normal turns with the surface, so each probe point carries its own. The
    proud/deep disambiguation is the same and is there for the same reason: a
    groove FLOOR whose inner wire encloses the plateau standing over it reads
    as a through feature otherwise.
    """
    face = topo.faces[fi]["face"]
    try:
        surf = BRep_Tool.Surface_s(face.wrapped)
    except Exception:
        return 0.0
    sign = -1.0 if dev.reversed_face else 1.0
    p, d_u, d_v = gp_Pnt(), gp_Vec(), gp_Vec()
    best = 0.0
    for x, y in ring:
        u, v = x / dev.su, y / dev.sv
        try:
            surf.D1(u, v, p, d_u, d_v)
            cross = d_u.Crossed(d_v)
            if cross.Magnitude() <= 1e-12:
                continue
            normal = cq.Vector(cross.X(), cross.Y(), cross.Z()).normalized() * sign
            start = cq.Vector(p.X(), p.Y(), p.Z()) + normal * 0.5
            hits = [h for h in _ray_hits(topo.shape, start, normal * -1.0) if h > 1e-6]
        except Exception:
            continue
        if not hits:
            return 1e6  # a through feature: unambiguously real relief
        depth = hits[0] - 0.5
        if depth > 3.0 * RELIEF_MIN_MM:
            try:
                above = [h for h in _ray_hits(topo.shape, start, normal) if h > 1e-6]
            except Exception:
                above = []
            if above:  # material over the probe: the region is proud, not deep
                depth = above[0] + 0.5
        best = max(best, depth)
    return best


def _curved_feature_wires(topo: Topology, fi: int, dev: Developed) -> tuple[list, int, list[str]]:
    """
    Inner wires of a developed curved face that are REAL features, plus the
    count that could not be judged and why.

    Same two tests as the planar branch - real relief (RELIEF_MIN_MM) and real
    size (RELIEF_MIN_AREA_MM2) - so a scribed decoration wrapped round a barrel
    buys exactly as little as one scribed across a lid.
    """
    face = topo.faces[fi]["face"]
    real: list[list[tuple[float, float]]] = []
    failed = 0
    why: list[str] = []
    try:
        wires = face.innerWires()
    except Exception:
        return [], 1, ["inner wires unreadable"]
    for w in wires:
        ring = _uv_ring(face, w, dev)
        if len(ring) < 3:
            failed += 1
            why.append("inner wire too coarse")
            continue
        if dev.period is not None:
            span = max(x for x, _ in ring) - min(x for x, _ in ring)
            if span > CURVED_SEAM_WRAP_MAX * dev.period:
                failed += 1
                why.append("an inner wire may cross the seam")
                continue
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        area = abs(poly.area) if not poly.is_empty else 0.0
        if area < RELIEF_MIN_AREA_MM2:
            continue  # decoration: too small to be a feature, never subtracted
        inset = max(0.3, 0.02 * math.sqrt(area))
        probe = poly.buffer(-inset)
        if probe.is_empty:
            probe = poly
        try:
            geom = probe if hasattr(probe, "exterior") else probe.geoms[0]
            coords = list(geom.exterior.coords)
        except Exception:
            coords = ring
        step = max(1, len(coords) // 10)
        samples = list(coords[::step][:10]) or list(ring[:10])
        try:
            inner = poly.representative_point()
            samples.append((inner.x, inner.y))
        except Exception:
            pass
        if _curved_relief_mm(topo, fi, dev, samples) >= RELIEF_MIN_MM:
            real.append(ring)
    return real, failed, why[:3]


def _curved_face_void(topo: Topology, fi: int) -> tuple[float | None, dict]:
    """
    The planar `_face_void` question, asked of a developed curved face:
    2 * (largest inscribed circle radius) / sqrt(silhouette).

    The seam is the one thing that is genuinely different. A full barrel is
    PERIODIC, so an empty region is allowed to wrap all the way round rather
    than being cut by an artificial boundary the kernel had to put somewhere.
    The strip is therefore tiled across the period before the circle is
    inscribed: any circle that fits the periodic strip can be translated by a
    whole number of periods to sit in the middle tile, so enough tiles to cover
    the strip's own height reproduce the periodic answer exactly.
    """
    rec = topo.faces[fi]
    if not _SHAPELY:
        return None, {"why": "shapely unavailable"}
    dev = topo.developed(fi)
    if dev is None:
        return None, {"why": topo.develop_failure(fi)}
    face = rec["face"]
    try:
        outer = _uv_ring(face, face.outerWire(), dev)
    except Exception as exc:
        return None, {"why": f"outer wire: {type(exc).__name__}"}
    if len(outer) < 3:
        return None, {"why": "outer wire too coarse"}

    real, failed, why = _curved_feature_wires(topo, fi, dev)
    if failed and not real:
        return None, {"why": why[0] if why else "inner wires unreadable"}
    # The u-scale only changes the answer when something in the u direction
    # bounds the empty region - a real feature, or a boundary that is not the
    # full turn. A plain full band is bounded by its own height whatever the
    # circumference is, so a cone or a crown is measured rather than refused.
    if (real or dev.period is None) and dev.u_distortion > CURVED_DISTORTION_MAX:
        return None, {"why": f"circumferential scale varies {dev.u_distortion:.1f}x"}

    try:
        poly = Polygon(outer, real)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            return None, {"why": "empty polygon"}
        tiles = 1
        if dev.period is not None and dev.period > 1e-9:
            span = max(y for _, y in outer) - min(y for _, y in outer)
            reach = max(1, int(math.ceil(span / (2.0 * dev.period))))
            tiles = 2 * reach + 1
            if tiles > CURVED_TILE_MAX:
                return None, {"why": "developed strip too long to close across its seam"}
            shifted = []
            for k in range(-reach, reach + 1):
                dx = k * dev.period
                shifted.append(
                    Polygon(
                        [(x + dx, y) for x, y in outer],
                        [[(x + dx, y) for x, y in ring] for ring in real],
                    )
                )
            poly = union_all(shifted)
            if not poly.is_valid:
                poly = poly.buffer(0)
        tol = max(0.05, math.sqrt(dev.ref_mm2) / 400.0)
        radius = maximum_inscribed_circle(poly, tol).length
    except Exception as exc:
        return None, {"why": f"inscribed circle: {type(exc).__name__}"}

    void = 2.0 * radius / math.sqrt(dev.ref_mm2)
    return void, {
        "lec_radius_mm": round(radius, 2),
        "silhouette_mm2": round(dev.ref_mm2, 1),
        "features": len(real),
        "wire_failures": failed,
        "at": _round_pt(face.Center()),
        "normal": f"{rec['kind']} skin",
        "developed": True,
        "periodic": dev.period is not None,
        "tiles": tiles,
        "distortion": round(max(dev.u_distortion, dev.v_distortion), 2),
    }


def _composable_faces(topo: Topology, rubric: Rubric) -> tuple[list[int], float, float]:
    """
    (candidate face indices, unreadable exterior area, relevant exterior area).

    A candidate is an exterior PRODUCT surface big enough to compose on: a
    plane or a developable curved skin, at least FACE_MIN_SHARE of the
    silhouette it faces.

    A CURVED break or blend face is refused as a CANDIDATE, where a planar one
    is not. That asymmetry is measured, not stylistic: FACE_MIN_SHARE already
    filters a planar chamfer land out by size, but a chamfer band or a plan
    fillet wrapped round a barrel develops to 2*pi*R * width against a
    silhouette of 2*R * height, so its area passes the same filter for free -
    and being narrow it always scores a perfect void. Left in, adding chamfers
    would dilute a part's own area-weighted mean upwards, which is a metric that
    pays for styling rather than for composition.

    `relevant` is the third return value and the one Part 2 of the coverage
    invariant is built on: ALL exterior product-surface area, whether this
    metric could compose on it or not. examined / relevant is then the fraction
    of the thing the metric claims to measure that it actually looked at.

    THE DENOMINATOR IS NOT THE CANDIDATE LIST, and conflating the two put a hole
    in the invariant's own headline metric. Curved break and blend skin used to
    leave through the same `continue` as everything else, so it was subtracted
    from `relevant` as well as from the candidates - which is the exact move the
    error invariant forbids one level down: removing something from the
    DENOMINATOR instead of from the MEASUREMENT. Measured on the corpus
    (2026-07-26, every case rebuilt): gamed_soap_bar, whose exterior is 51%
    tangent blend, reported examined_fraction 0.77 having composed 0.38 of its
    own skin; good_turned_spool reported a flawless 1.00 having composed 0.67;
    gamed_blob_csk reported 0.58 for 0.45. A reader looking at the render counts
    that blend skin as part of the exterior, so the denominator counts it too,
    and the metric now says out loud how much of the part it did not judge.
    Only a ROLE exclusion still leaves the denominator - `exclude_blank_perimeter`
    on a sheet part, where the blanked thickness band is declared not a design
    surface at all - which is a claim about the part, not about this metric's
    reach.
    """
    candidates: list[int] = []
    unreadable = 0.0
    relevant = 0.0
    for i, rec in enumerate(topo.faces):
        area = rec["area"]
        if area <= 1e-6:
            continue
        kind = rec["kind"]
        # Exterior surface this metric cannot read at all: freeform patches with
        # no plane, no axis and no radius. form_discipline used to notice these
        # and nothing else did; when it went, its one irreplaceable observation
        # came here, where the error invariant already lives. A pebble lofted
        # through four ellipses is not a part with an easy face_composition, it
        # is a part whose face_composition did not happen.
        if kind == "other" and topo.is_exterior(i) is not False:
            unreadable += area
            relevant += area
            continue
        curved = kind in _DEVELOPABLE_KINDS
        if kind != "plane" and not curved:
            continue
        if rubric.exclude_blank_perimeter and topo.is_band_face(i):
            continue
        if topo.is_exterior(i) is False:
            continue  # an interior cavity wall is not a product surface
        relevant += area
        # Out of the CANDIDATES, still inside the denominator: this is exterior
        # the reader sees and the metric declines to compose on. See the
        # docstring - the dilution argument is about the numerator only.
        if curved and (topo.is_break_face(i) or topo.is_blend_face(i)):
            continue
        if not curved:
            if rec["normal"] is None:
                continue
            ref = topo.bbox_projected_area(rec["normal"])
        else:
            dev = topo.developed(i)
            if dev is None:
                continue
            ref = dev.ref_mm2
        if ref < 1e-6 or area < FACE_MIN_SHARE * ref:
            continue
        candidates.append(i)
    return candidates, unreadable, relevant


def _metric_face_composition(topo: Topology, rubric: Rubric) -> dict:
    candidates, unreadable, relevant = _composable_faces(topo, rubric)

    if not candidates:
        # NOT a free pass either. "No face is big enough to compose" is what a
        # fully blended body measures, and renormalising the metric out for it
        # paid the soap bar for having no surface left to compose.
        return _degrade(
            _metric(
                "face_composition",
                ABSENT,
                0.0,
                f"no exterior face reaches {FACE_MIN_SHARE * 100:.0f}% of the silhouette it "
                f"faces - this body has no product surface to compose",
                value=1.0,
            ),
            max(unreadable, 1e-9),
            unreadable,
            ["the exterior is freeform surface, not composable faces"] if unreadable else None,
            examined=0.0,
            relevant=relevant,
        )

    population = sum(topo.faces[i]["area"] for i in candidates) + unreadable
    unmeasured = unreadable
    reasons: list[str] = []
    if unreadable > 0.0:
        reasons.append("exterior freeform surface carries no readable composition")
    scored: list[tuple[float, float, dict]] = []  # (void, area, detail)
    for i in candidates:
        area = topo.faces[i]["area"]
        ext = topo.is_exterior(i)
        if ext is None:
            unmeasured += area
            if len(reasons) < 3:
                reasons.append(f"face {i}: exterior reachability undecided")
            continue
        if topo.faces[i]["kind"] == "plane":
            void, detail = _face_void(topo, i)
        else:
            void, detail = _curved_face_void(topo, i)
        if void is None:
            unmeasured += area
            if len(reasons) < 3:
                reasons.append(f"face {i}: {detail.get('why')}")
            continue
        detail["index"] = i
        detail["area_mm2"] = round(area, 1)
        detail["void"] = round(void, 3)
        scored.append((void, area, detail))

    examined = sum(a for _, a, _ in scored)
    if not scored:
        return _degrade(
            _metric(
                "face_composition",
                ABSENT,
                0.0,
                "no exterior face could be composed - the part shows only "
                "cavity walls or surfaces that will not develop",
                value=1.0,
            ),
            max(population, 1e-9),
            max(unmeasured, population if unmeasured <= 0 else unmeasured),
            reasons,
            examined=0.0,
            relevant=relevant,
        )

    worst_void = max(v for v, _, _ in scored)
    total_area = examined
    mean_void = sum(v * a for v, a, _ in scored) / total_area
    w1, w0, m1, m0 = rubric.void_knots
    # 0.45 / 0.55 rather than the 0.6 / 0.4 the spec proposed: the worst face is
    # a MAX statistic and on a real housing it is always the one big lid or
    # mounting face, so weighting it above the whole-surface mean says more
    # about which face happens to be biggest than about how the part is
    # composed. Both terms still bite; the area-weighted one leads.
    score = 0.45 * _lerp_void(worst_void, w1, w0) + 0.55 * _lerp_void(mean_void, m1, m0)
    worst = max(scored, key=lambda t: t[0])[2]
    curved = sum(1 for _, _, d in scored if d.get("developed"))

    return _degrade(
        _metric(
            "face_composition",
            SCORED,
            score,
            f"largest empty region spans {worst_void:.2f} of the silhouette scale on the "
            f"{worst['normal']} face at {worst['at']} (empty circle R{worst['lec_radius_mm']} mm); "
            f"area-weighted mean {mean_void:.2f} over {len(scored)} exterior face(s), "
            f"{curved} of them developed curved skin",
            value=round(worst_void, 4),
            void_worst=round(worst_void, 4),
            void_mean=round(mean_void, 4),
            knots=[w1, w0, m1, m0],
            developed_faces=curved,
            faces=sorted((d for _, _, d in scored), key=lambda d: -d["void"])[:6],
        ),
        max(population, 1e-9),
        unmeasured,
        reasons,
        examined=examined,
        relevant=relevant,
    )


# ---------------------------------------------------------------------------
# Metric: feature composition
# ---------------------------------------------------------------------------
def _open_to_air(topo: Topology, point: cq.Vector, direction: cq.Vector) -> bool | None:
    """
    Does a ray from `point` along `direction` escape the solid? None = undecided.

    It used to answer False when the ray cast RAISED, which reads as "this
    feature is interior" and drops the feature from the population silently -
    and dropping features always flatters feature_composition, because a lone
    unaligned hole scores zero and vanishing is the best thing it can do. A
    probe that did not run is undecided, and the caller counts it as unmeasured
    so it reaches _degrade() like every other failed measurement.
    """
    try:
        return not [h for h in _ray_hits(topo.shape, point, direction) if h > 1e-6]
    except Exception:
        topo.probe_failures += 1
        return None


def _either_open(*probes: bool | None) -> bool | None:
    """True if any probe escaped, None if none did but one could not be run."""
    if any(p is True for p in probes):
        return True
    if any(p is None for p in probes):
        return None
    return False


def _feature_centres(topo: Topology, features: list[dict]) -> tuple[list[dict], int, list[str]]:
    """
    Every exterior feature centre, keyed into a family by (axis direction,
    diameter rung).

    Keying on DIAMETER as well as direction is what defeats a grid that only
    exists in projection: the corpus's gamed_projected_alignment case reads 1.00
    organised when features are grouped by direction alone and 0.40 when a
    family must also share a diameter, because in the solid it is two unrelated
    families that happen to line up when you squint at the plan view.
    """
    out: list[dict] = []
    unmeasured = 0
    reasons: list[str] = []
    blends = topo.blend_cylinders()

    def is_blend(f: dict) -> bool:
        return any(
            abs(r - f["radius"]) < 0.02 and _point_on_axis(f["p1"], f["dir"], ax)
            for r, ax in blends
        )

    for f in features:
        if is_blend(f) or topo.cylinder_wrap(f) < BORE_WRAP_MIN:
            continue
        if topo.is_coaxial(f["dir"], f["p1"]):
            # A feature on the axis of a body of revolution is part of the
            # TURNED PROFILE, not part of a layout: the through bore of a
            # spacer, the socket of a knob, the register of a gland. There is
            # nothing to arrange it against and nothing it could be arranged
            # with. See _metric_feature_composition.
            continue
        direction = cq.Vector(*f["dir"]).normalized()
        mid = cq.Vector(*[(a + b) / 2 for a, b in zip(f["p1"], f["p2"])])
        if f["type"] == "boss":
            # WHICH WAY THE PROBE LEAVES THE BOSS IS A CHOICE, and it has to be
            # the part's choice: _perp_basis seeds off a world axis and swaps
            # its two outputs as the part turns past 0.9, so a boss sitting
            # beside a rib read reachable in one orientation and blocked in the
            # next. The frame axis most perpendicular to the boss axis turns
            # with the part, so the probe leaves the same way every time.
            probes: list[bool | None] = []
            for side in _frame_sides(topo, direction):
                probes.append(_open_to_air(topo, mid + side * (f["radius"] * 1.05), side))
                probes.append(_open_to_air(topo, mid + side * (-f["radius"] * 1.05), side * -1.0))
            reachable = _either_open(*probes)
        else:
            reachable = _either_open(
                _open_to_air(topo, mid, direction),
                _open_to_air(topo, mid, direction * -1.0),
            )
        if reachable is None:
            # Undecided, not interior: an unrunnable probe used to delete the
            # feature from the population, and deleting features is exactly what
            # a badly-placed one wants.
            unmeasured += 1
            if len(reasons) < 3:
                reasons.append(f"feature at {_round_pt(mid)}: reachability probe failed")
            continue
        if not reachable:
            continue
        out.append(
            {
                "dir": _frame_dir(topo, f["dir"]),
                "rung": round(f["diameter"], 1),
                "centre": _frame_point(topo, mid),
                "kind": f["type"],
                "diameter": f["diameter"],
            }
        )

    # pocket / panel mouths: an inner wire that is not one circle
    for i, rec in enumerate(topo.faces):
        if rec["inner_wires"] == 0:
            continue
        if rec["kind"] != "plane" or rec["normal"] is None:
            # A POCKET ON A CURVED SKIN IS A LAYOUT DECISION THIS SCAN CANNOT
            # READ. It is the same planar-only filter that let face_composition
            # report a score for a turned part it had not looked at, in the
            # other metric - and the coverage invariant says the honest answer
            # is "unmeasured", not silence. No case in tests/design_corpus.py
            # carries one, so this costs nothing today and closes the hole
            # before something does. It routes through the population that
            # DEGRADATION_MAX already governs, which is the door every other
            # failed measurement in this module leaves by.
            if rec["kind"] in _DEVELOPABLE_KINDS and not (
                topo.is_break_face(i) or topo.is_blend_face(i)
            ):
                if topo.is_exterior(i) is not False:
                    unmeasured += rec["inner_wires"]
                    if len(reasons) < 3:
                        reasons.append(f"face {i}: a pocket on curved skin cannot be read")
            continue
        ext = topo.is_exterior(i)
        if ext is None:
            unmeasured += rec["inner_wires"]
            if len(reasons) < 3:
                reasons.append(f"face {i}: exterior reachability undecided")
            continue
        if not ext:
            continue
        real, _fake, failed = _feature_wires(topo, i)
        unmeasured += failed
        if failed and len(reasons) < 3:
            reasons.append(f"face {i}: {failed} inner wire(s) unreadable")
        origin, xdir, ydir, normal = _face_basis(rec)
        n = rec["normal"]
        for ring in real:
            if len(ring) < 8:
                continue  # a circle discretises to many points; keep both anyway
            if not _SHAPELY:
                continue
            poly = Polygon(ring)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                continue
            c = poly.centroid
            span = math.sqrt(abs(poly.area))
            # a bore mouth is already counted as a cylindrical feature
            if _is_circle(ring):
                continue
            out.append(
                {
                    # canonical (sign-blind) direction, the same form
                    # _cylinder_features uses: two mirrored flank panels are ONE
                    # family, not two families of one, and a family of one
                    # scores nothing at all.
                    "dir": _frame_dir(topo, (n.x, n.y, n.z)),
                    "rung": round(span, 1),
                    "centre": _frame_point(topo, origin + xdir * c.x + ydir * c.y),
                    "kind": "pocket",
                    "diameter": round(span, 2),
                }
            )
    return out, unmeasured, reasons


def _is_circle(ring: list[tuple]) -> bool:
    """A discretised ring whose radius is constant to 2% is a circle."""
    cu = statistics.fmean(p[0] for p in ring)
    cv = statistics.fmean(p[1] for p in ring)
    rs = [math.dist((cu, cv), p) for p in ring]
    mean = statistics.fmean(rs)
    if mean <= 1e-9:
        return False
    return (max(rs) - min(rs)) / mean < 0.02


def _metric_profile_composition(topo: Topology, profile: dict) -> dict:
    """
    feature_composition, asked of a body of revolution's PROFILE.

    A turned part has no feature centres to arrange - everything it has is on
    one axis - so the question "is this part's material composed, or is it
    undifferentiated" has to be asked of the meridian profile instead. It is the
    same question: a bar of stock with its corners knocked off is exactly as
    uncomposed as a slab with no feature on it, and the answer is the number of
    distinct turned diameters the profile is actually made of.

    THIS REPLACES A not_required. G4 reported feature_composition and
    pattern_discipline NOT_REQUIRED on any body of revolution with nothing off
    its axis, which renormalised 0.28 of the enclosure rubric OUT of the
    weighted mean - and everything that remained was free on a solid of
    revolution, so a three-line bored cylinder with one chamfer call measured
    97.8/A and outranked this repo's own reference exemplar at 83.1. A metric
    excused on GEOMETRIC grounds is a scored number or an absent defect, never a
    free renormalisation: geometry is what the author controls and what the gate
    exists to judge. The weight stays where it was and has to be earned on the
    profile.
    """
    size = max(topo.bbox_size())
    elements = profile["elements"]
    score = _lerp_score(float(elements), best=PROFILE_ELEMENTS_FULL, worst=1.0)
    listed = ", ".join(f"D{2 * r:g}" for r in profile["radii"][:6]) or "none"
    curved = profile["curved"]
    shaped = f", plus {curved} shaped band(s)" if curved else ""
    return _metric(
        "feature_composition",
        SCORED,
        score,
        f"a {size:.0f} mm body of revolution: its composition is its turned profile, and "
        f"that profile is {elements} distinct diameter(s) ({listed}{shaped}) against a bar of "
        f"{PROFILE_ELEMENTS_FULL:.0f}. There is no bolt pattern here and none is wanted - "
        f"a turned part is composed by its steps, bores, registers and grooves",
        value=elements,
        mode="profile",
        radii=profile["radii"][:8],
        curved=curved,
        families=[],
    )


def _metric_feature_composition(topo: Topology, features: list[dict]) -> dict:
    # THE GATE'S WORST MISCOACHING USED TO LIVE BELOW, AND ITS FIRST FIX OPENED
    # A BIGGER HOLE THAN IT CLOSED. A turned part - a shaft, a spacer, a
    # standoff, a bushing, a knob, a gland, a spool - is a large and entirely
    # legitimate class whose composition IS its profile, and reporting ABSENT
    # (0.0 at full weight, and with pattern_discipline alongside it 0.28 of the
    # enclosure rubric) taught exactly one lesson, which is "add holes you do
    # not need". Excusing the metric instead taught a worse one. It is now
    # MEASURED, on the geometry a turned part actually has: see
    # _metric_profile_composition.
    #
    # Only the part that is ENTIRELY its profile takes that branch. An off-axis
    # hole on a turned flange is a layout decision like any other and is judged
    # like any other, so "holes exist but form no pattern" is still a defect.
    if topo.revolution_pure():
        profile = topo.revolution_profile()
        if profile is not None:
            return _metric_profile_composition(topo, profile)

    centres, unmeasured, reasons = _feature_centres(topo, features)
    population = len(centres) + unmeasured
    size = max(topo.bbox_size())

    if not centres:
        # There used to be a 25 mm exemption here, and it was an ABSOLUTE size
        # threshold on a metric that is otherwise scale free, so shrinking a
        # part below the line RAISED its score. Composition is a property of a
        # layout, not of a length: a featureless part has none at any size.
        return _degrade(
            _metric(
                "feature_composition",
                ABSENT,
                0.0,
                f"a {size:.0f} mm part with no exterior features at all - nothing is "
                "composed because nothing is there",
                value=0.0,
                families=[],
            ),
            max(population, 1.0),
            unmeasured,
            reasons,
        )

    families: dict[tuple, list[dict]] = {}
    for c in centres:
        families.setdefault((c["dir"], c["rung"]), []).append(c)

    tol = topo.align_tol()
    reports = []
    weighted = 0.0
    for (direction, rung), members in families.items():
        u, v = _perp_basis(direction)
        economy = 0.0
        if len(members) < 2:
            value = 0.0
            ou = ov = 0.0
        else:
            us = [m["centre"].dot(cq.Vector(*u)) for m in members]
            vs = [m["centre"].dot(cq.Vector(*v)) for m in members]
            org_u = _organised_fraction(us, None, tol)
            org_v = _organised_fraction(vs, None, tol)
            ou, ov = org_u.fraction, org_v.fraction
            # THE TWO AXES ARE ONE LAYOUT, NOT TWO. Scoring them independently
            # and averaging is what made 4-fold mirroring a random scatter read
            # as fully organised: every u became a shared u and every v a shared
            # v, so both terms saturated at 1.0. The economy factor is a JOINT
            # statistic over both axes, so buying alignment on one axis by
            # spending centrelines on the other buys nothing.
            economy = _lattice_economy(len(members), org_u, org_v)
            value = 0.5 * (ou + ov) * economy
        weighted += value * len(members)
        reports.append(
            {
                "diameter": rung,
                "axis": _AXIS_NAMES.get(tuple(int(round(c)) for c in direction), "oblique"),
                "count": len(members),
                "organised": round(value, 3),
                "per_axis": [round(ou, 3), round(ov, 3)],
                "lattice_economy": round(economy, 3),
            }
        )
    organised = weighted / len(centres)

    if len(centres) < 3 or max(len(m) for m in families.values()) < 2:
        return _degrade(
            _metric(
                "feature_composition",
                ABSENT,
                0.0,
                f"{len(centres)} loose feature(s) in {len(families)} family(ies) - no two "
                "share a direction and a diameter, so there is no composition to read",
                value=round(organised, 4),
                families=sorted(reports, key=lambda r: -r["count"])[:8],
            ),
            max(population, 1.0),
            unmeasured,
            reasons,
        )

    score = _lerp_score(organised, best=0.95, worst=0.35)
    worst = min(reports, key=lambda r: r["organised"])
    return _degrade(
        _metric(
            "feature_composition",
            SCORED,
            score,
            f"{organised * 100:.0f}% of {len(centres)} feature centres sit on a shared "
            f"centreline or a constant-pitch run, across {len(families)} family(ies); "
            f"weakest is {worst['count']}x D{worst['diameter']} on {worst['axis']} "
            f"({worst['organised'] * 100:.0f}%)",
            value=round(organised, 4),
            families=sorted(reports, key=lambda r: -r["count"])[:8],
        ),
        max(population, 1.0),
        unmeasured,
        reasons,
    )


# ---------------------------------------------------------------------------
# Metric: pattern discipline (fastener rhythm, rebuilt)
# ---------------------------------------------------------------------------
def _merge_fasteners(topo: Topology, features: list[dict]) -> list[dict]:
    """
    One record per SCREW, not per cylindrical face group.

    analyze_step reports a bore and its counterbore as two coaxial features. The
    old metric grouped them separately and weighted the mean by hole count, so a
    counterbored pattern carried twice the weight of a plain one and the printed
    count was wrong. Coaxial members are merged and the group is keyed on the
    through (smallest) diameter.
    """
    blends = topo.blend_cylinders()

    def is_blend(f: dict) -> bool:
        return any(
            abs(r - f["radius"]) < 0.02 and _point_on_axis(f["p1"], f["dir"], ax)
            for r, ax in blends
        )

    holes = [
        f
        for f in features
        if f["type"] == "hole"
        and f["diameter"] > 0.5
        and not is_blend(f)
        and topo.cylinder_wrap(f) >= BORE_WRAP_MIN
        # the bore of a turned part is the part, not a fastener - see
        # _metric_pattern_discipline
        and not topo.is_coaxial(f["dir"], f["p1"])
    ]
    merged: list[dict] = []
    for f in holes:
        direction = tuple(f["dir"])
        # Two features are coaxial when one's mouth sits on the other's axis
        # LINE - measured as a perpendicular offset between the two mouths, not
        # by rebuilding both feet at the origin and comparing those. The rebuilt
        # foot carries an error of |p1| times the rounding on `dir`, so two
        # genuinely coaxial features 500 mm from the origin on an oblique axis
        # stopped merging: a bore and its counterbore became two families, and
        # pattern_discipline moved 10.99 points on the exemplar under a motion
        # that changed nothing about the part.
        for m in merged:
            if (
                _same_direction(direction, m["dir"])
                and _perp_offset(f["p1"], m["p1"], m["dir"]) < AXIS_MERGE_TOL
            ):
                m["members"].append(f)
                break
        else:
            merged.append({"p1": tuple(f["p1"]), "members": [f], "dir": direction})
    out = []
    for m in merged:
        through = min(m["members"], key=lambda f: f["diameter"])
        out.append(
            {
                "diameter": through["diameter"],
                "dir": list(m["dir"]),
                "axis_label": through["axis_label"],
                "mid": [(a + b) / 2 for a, b in zip(through["p1"], through["p2"])],
                "stack": len(m["members"]),
            }
        )
    return out


def _metric_profile_discipline(topo: Topology, profile: dict) -> dict:
    """
    pattern_discipline, asked of a body of revolution's PROFILE.

    A turned part repeats shoulders, not screw positions, and the discipline
    question is the same one: is the repeated thing executed the same way every
    time, or left as it fell out of the cut? The population is the profile's
    CONCAVE corners - shoulder roots, groove roots, counterbore floors, register
    steps - because those are the ones nothing else in this module can see:
    edge_break_coverage and sharp_edge_length are convex-only by construction,
    so a stepped shaft with every outside corner chamfered and every root left
    square scores 100 on both of them.

    A radiused root scores full, a chamfered root scores SHOULDER_CHAMFER_CREDIT
    and a square one scores zero. A profile with no concave corner at all scores
    zero and says so: a plain barrel with its ends knocked off has no shoulder,
    no groove and no register anywhere, which is a fact about the part and not a
    reason to excuse it. The score is never renormalised out - see
    _metric_profile_composition for why.

    That case is SCORED 0.0 and not ABSENT deliberately. ABSENT means "the
    geometry implies this metric applies and the thing it measures is missing";
    here the population being empty IS the measurement, because every body of
    revolution has a meridian profile and so the question always has an answer.
    Numerically the two states are identical - both carry the full weight at zero
    - so nothing is bought either way.
    """
    corners = [c for c in profile["corners"] if c["sense"] == "concave"]
    convex = sum(1 for c in profile["corners"] if c["sense"] == "convex")
    size = max(topo.bbox_size())
    credit = {"blend": 1.0, "chamfer": SHOULDER_CHAMFER_CREDIT, "raw": 0.0}

    if not corners:
        return _degrade(
            _metric(
                "pattern_discipline",
                SCORED,
                0.0,
                f"a {size:.0f} mm turned profile with no shoulder, groove, register or "
                f"undercut anywhere - {convex} outside corner(s) and nothing on the inside "
                f"of the cut. There is nothing here to fasten and nothing to be disciplined: "
                f"a bar with its ends broken is stock, not a designed profile",
                value=0.0,
                mode="profile",
                shoulders=0,
                relieved=0,
                chamfered=0,
                raw=0,
                groups=[],
            ),
            max(len(profile["corners"]) + profile["unresolved"], 1.0),
            profile["unresolved"],
            ["a profile corner's sense could not be resolved"] if profile["unresolved"] else [],
        )

    counts = {"blend": 0, "chamfer": 0, "raw": 0}
    for c in corners:
        counts[c["treatment"]] += 1
    value = sum(credit[c["treatment"]] for c in corners) / len(corners)
    score = 100.0 * value
    return _degrade(
        _metric(
            "pattern_discipline",
            SCORED,
            score,
            f"{len(corners)} concave profile corner(s) on a {size:.0f} mm turned body: "
            f"{counts['blend']} radiused, {counts['chamfer']} chamfered, {counts['raw']} left "
            f"square. A shoulder root is a turned part's repeated feature - relieve it with a "
            f"radius off the ladder, or undercut it; a chamfer there is worth "
            f"{SHOULDER_CHAMFER_CREDIT:.0%} because it clears the mating part without "
            f"removing the stress riser",
            value=round(value, 3),
            mode="profile",
            shoulders=len(corners),
            relieved=counts["blend"],
            chamfered=counts["chamfer"],
            raw=counts["raw"],
            groups=[],
        ),
        len(corners) + profile["unresolved"],
        profile["unresolved"],
        ["a profile corner's sense could not be resolved"] if profile["unresolved"] else [],
    )


def _metric_pattern_discipline(topo: Topology, rubric: Rubric, features: list[dict]) -> dict:
    fasteners = _merge_fasteners(topo, features)
    if not fasteners:
        if rubric.role == "structural":
            return _metric(
                "pattern_discipline",
                NOT_REQUIRED,
                None,
                "a structural member with no holes fastens through its ends, not a pattern",
            )
        if topo.revolution_pure():
            # The same miscoaching _metric_feature_composition names, in the
            # other half of the pair, and the same correction. A turned spacer,
            # standoff, bushing or gland is clamped through its own bore or held
            # in a collet, so demanding a bolt pattern of it teaches an agent to
            # drill holes nothing needs - but EXCUSING the metric renormalised
            # the weight out of the mean and handed a plain chamfered bar a free
            # 0.12 of the rubric. What a turned part repeats instead of screw
            # positions is SHOULDERS, and how they are relieved is exactly as
            # disciplined or as raw as a bolt circle is.
            profile = topo.revolution_profile()
            if profile is not None:
                return _metric_profile_discipline(topo, profile)
        return _metric(
            "pattern_discipline",
            ABSENT,
            0.0,
            f"{_article(rubric.role)} {rubric.role} with no holes at all - it has no way "
            "to be fastened to anything, so there is no pattern to be disciplined",
            value=0.0,
            groups=[],
        )

    # EVERY LAYOUT QUESTION IS ASKED IN THE PART'S OWN FRAME. Grouping fasteners
    # by a direction rounded in WORLD components split one family in two the
    # moment the part was turned in the file - and a family of fewer than three
    # is not a pattern at all, so the metric fell to absent_defect on a part that
    # had not changed. The inset term measured each hole against the WORLD box
    # walls, which a rotation moves bodily. In the frame the same holes share the
    # same direction and are inset from the same walls whatever the file says.
    frame = topo.frame
    fasteners = [
        {
            **f,
            "dir": _canonical_dir(frame.to_frame_direction(cq.Vector(*f["dir"]))),
            "mid": frame.to_frame_point(cq.Vector(*f["mid"])),
        }
        for f in fasteners
    ]

    groups: dict[tuple, list[dict]] = {}
    for f in fasteners:
        key = (round(f["diameter"], 1), tuple(round(c, 2) for c in f["dir"]))
        groups.setdefault(key, []).append(f)

    # Frame coordinates are measured FROM the frame centre, so the part's
    # centrelines are the origin and its walls are at plus and minus a half.
    half = tuple(0.5 * s for s in frame.size)
    centre = (0.0, 0.0, 0.0)
    lo = tuple(-h for h in half)
    hi = half

    reports = []
    for (diameter, direction), members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(members) < 3:
            continue
        u, v = _perp_basis(direction)
        pts = []
        for f in members:
            mid = f["mid"]
            pts.append(
                (sum(m * c for m, c in zip(mid, u)), sum(m * c for m, c in zip(mid, v)), mid)
            )
        # nearest-neighbour pitch regularity
        nn = []
        for i, (au, av, _) in enumerate(pts):
            d = [math.dist((au, av), (bu, bv)) for j, (bu, bv, _) in enumerate(pts) if j != i]
            nn.append(min(d))
        cv = _cv(nn)
        pitch_score = 100.0 if cv is None else _lerp_score(cv, best=0.02, worst=0.45)

        # mirror symmetry about the part centrelines in the projection plane
        cu = sum(c * m for c, m in zip(centre, u))
        cvv = sum(c * m for c, m in zip(centre, v))
        tol = max(0.5, 0.005 * max(topo.bbox_size()))
        sym = []
        for axis, (vals, mid_val) in enumerate(
            (([p[0] for p in pts], cu), ([p[1] for p in pts], cvv))
        ):
            other = [p[1] for p in pts] if axis == 0 else [p[0] for p in pts]
            matched = 0
            for a, o in zip(vals, other):
                target = 2 * mid_val - a
                if any(abs(b - target) <= tol and abs(ob - o) <= tol for b, ob in zip(vals, other)):
                    matched += 1
            sym.append(matched / len(pts))
        sym_frac = max(sym)
        sym_score = _lerp_score(sym_frac, best=1.0, worst=0.34)

        # edge-inset consistency: distance to the nearest bbox wall in-plane
        insets = []
        for _, _, mid in pts:
            dists = [
                min(mid[k] - lo[k], hi[k] - mid[k]) for k in range(3) if abs(direction[k]) < 0.9
            ]
            if dists:
                insets.append(min(dists))
        icv = _cv(insets)
        inset_score = 100.0 if icv is None else _lerp_score(icv, best=0.05, worst=0.60)

        group_score = 0.45 * pitch_score + 0.35 * sym_score + 0.20 * inset_score
        reports.append(
            {
                "diameter": diameter,
                "count": len(members),
                "axis": members[0]["axis_label"],
                "pitch_cv": None if cv is None else round(cv, 3),
                "symmetric_fraction": round(sym_frac, 3),
                "inset_cv": None if icv is None else round(icv, 3),
                "mean_inset_mm": round(statistics.fmean(insets), 2) if insets else None,
                "score": round(group_score, 1),
            }
        )

    if not reports:
        # THE defect the audit priced: four scattered D8 holes scored 18.1 and
        # the part 17.7; the same four holes at D24 scored not_applicable and
        # the part 17.9. The gate paid 0.2 points for making the geometry worse.
        return _metric(
            "pattern_discipline",
            ABSENT,
            0.0,
            f"{len(fasteners)} hole(s), but no family of 3 or more shares one diameter and "
            "one direction - they are scattered, not patterned",
            value=0.0,
            holes=len(fasteners),
            groups=[],
        )

    patterned = sum(r["count"] for r in reports)
    loose = len(fasteners) - patterned
    score = sum(r["score"] * r["count"] for r in reports) / patterned
    # Loose holes dilute: a good pattern plus a scattering of one-offs is not a
    # good pattern. They score zero and carry their own weight.
    score = score * patterned / (patterned + loose)
    worst = min(reports, key=lambda r: r["score"])
    return _degrade(
        _metric(
            "pattern_discipline",
            SCORED,
            score,
            f"{len(reports)} fastener family(ies), {patterned} of {len(fasteners)} screws "
            f"patterned; weakest is {worst['count']}x D{worst['diameter']} on {worst['axis']} "
            f"(score {worst['score']:.0f})",
            value=round(score, 1),
            screws=len(fasteners),
            loose=loose,
            groups=reports,
        ),
        len(fasteners),
        0.0,
        [],
    )


# ---------------------------------------------------------------------------
# Metric: radius / break-size vocabulary
# ---------------------------------------------------------------------------
def _cone_slant_width(face) -> float | None:
    """
    How wide a conical band is ALONG ITS SLANT, in mm.

    Read off the face's own v-parameter range, because OCC parametrises a
    conical surface with v as arc length along the slant line - so vmax - vmin
    IS the width, exactly, for a full ring and for a quarter-turn corner alike.

    The stored rec["width"] cannot be used here. It is area / (perimeter / 2),
    which _chamfer_leg's own docstring already records as a 5% under-read on a
    planar strip; on a curved band it is far worse, because the two arcs
    bounding a frustum have very different lengths. Measured: a 1.0 mm chamfer
    run across a 5 mm plan-corner fillet is a 45 degree cone of true slant
    1.414 mm, and the half-perimeter width reads 1.202 - a leg of 0.85 against
    a true 1.00, which is off the ladder by twice its own tolerance. Every
    rounded-and-chamfered part in this repo would have carried a manufactured
    off-ladder size the moment cones started being measured at all.
    """
    try:
        _u0, _u1, v0, v1 = BRepTools.UVBounds_s(face.wrapped)
    except Exception:
        return None
    w = abs(v1 - v0)
    return w if w > 1e-9 else None


def _chamfer_leg(topo: Topology, fi: int) -> float | None:
    """
    Leg length of a chamfer land, from the two LONG boundary edges of the land.

    The old version averaged every convex boundary edge, which on a square plan
    corner sweeps in the mitre edges between adjacent chamfer lands: a textbook
    2.0 mm x 45 deg chamfer on a box measured as three sizes (0.667, 1.95,
    2.059), so a perfectly coherent part was penalised for incoherence.

    Width is taken as area / mean(long edge length) rather than
    area / half-perimeter: for a strip of width w and length L the latter reads
    wL/(w+L), a 5% under-read at the scale of a real chamfer, which is enough
    to fall off the ladder.

    The face must then still LOOK like a strip. area / half-perimeter is small
    for any face with a busy boundary, so a ribbed panel floor slipped through
    the width cap and was measured as a chamfer with a 77.6 mm leg - the
    exemplar reported 21 distinct break sizes with 44% on the ladder, for a part
    built entirely from Style's own ladders. A land is accepted only when it is
    at least three times longer than it is wide and its perimeter is within a
    third of the 2*(span + width) a real strip would have.

    For a CONICAL land the rule is the cone's own half-angle rather than the
    dihedral it makes with its neighbours: leg = slant width * cos(semi-angle).
    A 45 degree rim chamfer of leg L is a cone of semi-angle 45 degrees whose
    slant width is L * sqrt(2), and L * sqrt(2) * cos(45 deg) is L again.
    Without this branch a cone land returns None and the caller SUBTRACTS its
    area from the population, so every exterior non-rim cone break vanishes from
    both the vocabulary and the unmeasured fraction: on good_structural_arm that
    hid eight real chamfers and turned "4 sizes, 90% coherent" into "3 sizes,
    100% coherent, 100.0". The omission only ever flatters, and it flatters
    turned and cone-broken parts specifically.
    """
    rec = topo.faces[fi]
    if rec["kind"] == "cone":
        if rec["cone_deg"] is None:
            return None
        slant = _cone_slant_width(rec["face"])
        if slant is None:
            return None
        return slant * math.cos(math.radians(rec["cone_deg"]))
    edges = [
        e
        for e in topo.face_edges.get(fi, ())
        if e["kind"] in ("convex", "smooth_convex")
        and e["angle_deg"] is not None
        and e["angle_deg"] <= CHAMFER_MAX_DEG
    ]
    if len(edges) < 2:
        return None
    longest = max(e["length"] for e in edges)
    long_edges = [e for e in edges if e["length"] >= 0.9 * longest]
    if len(long_edges) < 2:
        return None
    angle = statistics.fmean(e["angle_deg"] for e in long_edges)
    span = statistics.fmean(e["length"] for e in long_edges)
    if span <= 1e-9:
        return None
    width = rec["area"] / span
    if not (0.0 < width <= topo.break_cap) or span < 3.0 * width:
        return None
    # A break is SMALLER than what it breaks. Without this, the outer side wall
    # of the corpus's sealed cover - an 8.4 mm tall band that happens to be
    # bounded above and below by its own 1.0 and 0.6 mm chamfers, so both its
    # long edges sit at 45 deg - measured as a 5.94 mm chamfer of 3830 mm2 and
    # dragged that part's radius_vocabulary to 27/100 for using two sizes.
    neighbour = 0.0
    for e in long_edges:
        for other in e["faces"]:
            if other != fi:
                neighbour = max(neighbour, topo.faces[other]["area"])
    if neighbour > 0.0 and rec["area"] >= neighbour:
        return None
    perim = rec["perimeter"]
    strip_perimeter = 2.0 * (span + width)
    if perim > 1e-9 and abs(perim - strip_perimeter) > 0.35 * perim:
        return None
    return width * math.cos(math.radians(angle))


def _applied_fraction(breaks: dict | None) -> float | None:
    """
    Share of the BODY silhouette that a break face is responsible for.

    The body population and not the whole convex population, for the same reason
    the floor reads the body term: the rim is a different question, and folding
    it in here would import its answer. It would also misfire on exactly the
    part that cannot help it - measured, the corpus's 2 mm sheet bracket carries
    402 mm of punched hole rim that stock that thin can no more chamfer than it
    can chamfer its blanked outline, which took its applied fraction to 0.07 and
    its radius_vocabulary from 100 to 20 for a defect it does not have. Over the
    body alone it measures 0.34.

    None when the classification did not run or the part has no body population,
    so a missing measurement never manufactures a discount.
    """
    if breaks is None:
        return None
    broken = breaks["body_broken_mm"]
    total = broken + breaks["body_sharp_mm"]
    if total <= 1e-9:
        return None
    return broken / total


def _ladder_min_ratio(ladder: tuple[float, ...]) -> float:
    """
    The finest distinction the shared design language itself makes.

    Adjacent rungs of lib.features.Style's break ladder step by 1.20x at the
    tightest (2.5 -> 3.0), so nothing in the language is finer than that. That
    number is the natural resolution of "these are two different sizes", and
    reading it off the ladder rather than typing it here means a change to the
    ladder moves this with it instead of leaving a stale constant behind.
    """
    rungs = sorted(r for r in ladder if r > 1e-9)
    if len(rungs) < 2:
        return VOCAB_SPLIT_RATIO_FALLBACK
    return min(b / a for a, b in zip(rungs, rungs[1:]))


def _split_rungs(distinct: list[dict], ladder: tuple[float, ...]) -> tuple[list[dict], float]:
    """
    Which break sizes are accidents rather than decisions, and what they cost.

    A size is a SPLIT RUNG when it sits closer than one ladder step to another
    size the part uses MORE than it. Two conditions, and both matter:

    "closer than one ladder step" is the incoherence. Below _ladder_min_ratio
    the two sizes are not distinguishable as design intent - the language never
    draws a distinction that fine, so a part that draws one has drifted rather
    than chosen. Because every on-ladder pair is at least one full rung apart by
    construction, this can only ever fire on an off-ladder size, which is why
    using ten correct rungs is free and using 1.15 beside 1.00 is not.

    "uses MORE than it" is which of the pair is the accident. A vocabulary is
    what a part REPEATS, so the heavier-area size is the language and the
    lighter one is the drift off it. Area rather than face count: four small
    lands and one long seal chamfer are not four votes against one.

    Returns (split buckets in ladder order, their total area). The area is what
    the coherence term charges - so a hairline split rung on one small face
    costs almost nothing, and half the break area drifting off its own rung
    costs half the metric.
    """
    ratio = _ladder_min_ratio(ladder)

    def standing(bucket: dict) -> tuple[float, bool, float]:
        """
        How strong a claim a size has to BE the language, as a total order.

        Area first. Ties are broken so that neither member of a pair can escape
        by matching the other exactly: an on-ladder size outranks an off-ladder
        one of the same area, and beyond that the larger size wins, which is
        arbitrary but deterministic. Without a total order two near-duplicates
        with identical break area would each fail to outrank the other and both
        would go free - a one-line way to buy the metric back.
        """
        return (bucket["area_mm2"], bool(bucket["on_ladder"]), bucket["size"])

    splits: list[dict] = []
    for b in distinct:
        size = b["size"]
        if size <= 1e-9:
            continue
        for other in distinct:
            if other is b or other["size"] <= 1e-9:
                continue
            if standing(other) <= standing(b):
                continue  # the weaker of a pair is the accident, not the stronger
            hi, lo = max(size, other["size"]), min(size, other["size"])
            if lo > 1e-9 and hi / lo < ratio:
                splits.append({**b, "near": other["size"]})
                break
    return splits, sum(s["area_mm2"] for s in splits)


def _metric_radius_vocabulary(
    topo: Topology, rubric: Rubric, ladder: tuple[float, ...], breaks: dict | None = None
) -> dict:
    """
    Do the break sizes sit on the Style ladder, is that set internally
    COHERENT, and is it actually APPLIED to the part?

    The middle question used to be "is it a SMALL set", which is a question
    about richness and not about vocabulary - see VOCAB_SPLIT_RATIO_FALLBACK
    for the two parts that proved it and for what replaced it. Nothing about
    conformance or application changed with it: those two were measuring what
    they claimed, and a part that draws sizes from outside the language still
    pays for exactly that.

    The third question is the one the audit found missing. The metric was
    area-weighted over the break faces alone, with the break faces as their own
    denominator, so conformance was 1.0 for any part whose every break happened
    to be one ladder rung - including a part with exactly one break. A raw billet
    with a single 2.5 mm chamfer scored 100.0 here, which at weight 0.11-0.14
    was the cheapest block of rubric in the module and is most of what let a raw
    body clear a C. See VOCAB_APPLIED_FULL for the shape of the coverage term
    and for why it is a gate rather than a fourth edge metric.

    IT ASKS is_exterior(), AND IT CAN DEGRADE. Alone among the face metrics
    this one never asked, so a single ladder-sized blend buried inside a sealed
    cavity - where no eye can reach - carried the whole vocabulary to 100:
    measured, a plain box with a filleted SEALED internal void scored 100 here
    and 37.1 overall against the same box's 27.1. It also never called _degrade,
    so it was the one metric in the module that could not report that it had
    failed, which is the hole the error invariant exists to close.

    The exterior is what is judged. Interior break geometry is not thrown away,
    though: when a part has NO exterior break at all, its interior geometry
    still shows whether the author has a radius language, so it is scored on
    that at INTERIOR_ONLY_CEILING. Deleting it outright instead made a box with
    a coherent interior vocabulary indistinguishable from a plain billet, which
    is a different falsehood from the one being fixed - and a quarter credit
    still makes a buried blend worth a quarter of a visible one, which is the
    whole of what M8 asked for.
    """
    exterior: list[tuple[float, float, str]] = []  # (size, area weight, kind)
    interior: list[tuple[float, float, str]] = []
    population = 0.0
    unmeasured = 0.0
    reclassified = 0.0
    reclassified_faces = 0
    rim_breaks = 0
    reasons: list[str] = []
    for i, rec in enumerate(topo.faces):
        if rubric.exclude_blank_perimeter and topo.is_band_face(i):
            continue  # a sheet part is judged on its BEND radii
        is_blend = topo.is_blend_face(i)
        # A CONE IS A CHAMFER TOO. The land test used to be "planar and narrow",
        # and on a body of revolution every chamfer is a cone - so a turned
        # spacer with all four of its corners broken to one 1.0 mm rung reported
        # "no fillet or chamfer geometry anywhere", ABSENT, 0.0 at full weight.
        # Bore-rim cones stay out: a countersink's size is set by the screw
        # standard, not by this repo's ladder, and pricing it here would punish
        # correct countersinking.
        rim_cone = rec["kind"] == "cone" and topo.is_break_face(i) and topo.is_rim_break_face(i)
        if rim_cone:
            rim_breaks += 1
        is_land = not is_blend and topo.is_break_face(i) and not rim_cone
        if not (is_blend or is_land):
            continue
        population += rec["area"]
        ext = topo.is_exterior(i)
        if ext is None:
            unmeasured += rec["area"]
            if len(reasons) < 3:
                reasons.append(f"face {i}: exterior reachability undecided")
            continue
        if is_blend:
            entry = (rec["radius"], rec["area"], "fillet")
        else:
            leg = _chamfer_leg(topo, i)
            if leg is None or leg <= 0.05:
                # RECLASSIFICATION, NOT A FAILED MEASUREMENT. _chamfer_leg only
                # returns None for a PLANAR candidate that fails the strip test
                # - is_break_face already guarantees a cone has a usable
                # cone_deg and a positive width, so the cone branch always
                # answers. A face that is not a strip is not a break, so it
                # leaves the population rather than sitting in it as unmeasured.
                # It is counted and REPORTED all the same: subtracting from a
                # denominator with nothing to show for it is exactly how the
                # missing cone branch hid eight real chamfers on
                # good_structural_arm from unmeasured_fraction.
                population -= rec["area"]
                reclassified += rec["area"]
                reclassified_faces += 1
                continue
            entry = (leg, rec["area"], "chamfer")
        (exterior if ext else interior).append(entry)

    sizes = exterior or interior
    ceiling = 100.0 if exterior else INTERIOR_ONLY_CEILING
    if not sizes:
        return _degrade(
            _metric(
                "radius_vocabulary",
                ABSENT,
                0.0,
                (
                    "no fillet or chamfer geometry anywhere - every corner is a knife edge"
                    if not rim_breaks
                    else (
                        f"the only break geometry on this part is {rim_breaks} bore-rim "
                        f"chamfer(s), whose size is set by the fastener standard rather "
                        f"than by a design ladder - not one CORNER carries a break, so "
                        f"there is no radius vocabulary to read"
                    )
                ),
                value=0.0,
                rim_breaks=rim_breaks,
                distinct=[],
            ),
            max(population, 1e-9),
            unmeasured,
            reasons,
        )

    def rung(size: float) -> float | None:
        """The ladder step this size belongs to, or None if it is off-ladder."""
        for t in ladder:
            if abs(size - t) <= max(0.06, 0.08 * t):
                return t
        return None

    # Buckets are keyed by LADDER RUNG, not by the raw measurement: a 0.6 mm
    # chamfer measures 0.55 on one land and 0.60 on another once the effective
    # width is derived from the area, and counting those as two different design
    # sizes would punish a perfectly coherent part.
    buckets: dict[float, dict] = {}
    for size, area, kind in sizes:
        r = rung(size)
        key = r if r is not None else round(size * 20.0) / 20.0
        b = buckets.setdefault(
            key,
            {"size": key, "faces": 0, "area_mm2": 0.0, "kind": kind, "on_ladder": r is not None},
        )
        b["faces"] += 1
        b["area_mm2"] += area

    total_area = sum(a for _, a, _ in sizes)
    good_area = sum(b["area_mm2"] for b in buckets.values() if b["on_ladder"])
    conformance = good_area / total_area if total_area > 1e-9 else 0.0

    distinct = sorted(buckets.values(), key=lambda b: b["size"])

    # COHERENCE, which is not the same question as how many sizes there are.
    # See VOCAB_SPLIT_RATIO_FALLBACK for why the count penalty this replaced was
    # measuring the wrong construct.
    splits, incoherent_area = _split_rungs(distinct, ladder)
    coherence = 1.0 - (incoherent_area / total_area if total_area > 1e-9 else 0.0)

    for b in distinct:
        b["area_mm2"] = round(b["area_mm2"], 1)

    where = "exterior" if exterior else "INTERIOR-ONLY"

    # IS THE VOCABULARY APPLIED? Only asked of an exterior vocabulary: the
    # interior-only case is already held to INTERIOR_ONLY_CEILING, which is a
    # harder statement than this term could make, and its breaks are by
    # definition not on the exterior population the coverage is measured over.
    applied = _applied_fraction(breaks) if exterior else None
    applied_factor = 1.0 if applied is None else _clamp(applied / VOCAB_APPLIED_FULL)

    score = min(ceiling, 100.0 * conformance * coherence * applied_factor)
    msg = (
        f"{len(distinct)} distinct break sizes, {conformance * 100:.0f}% of {where} "
        f"blend/chamfer area on the ladder"
    )
    if splits:
        named = ", ".join("%g" % s["size"] for s in splits[:4])
        msg += (
            f" - but {len(splits)} of them ({named}) sit closer than one ladder step to a size "
            f"this part already uses more, so they are split rungs rather than decisions "
            f"({coherence * 100:.0f}% coherent area)"
        )
    if applied is not None and applied_factor < 1.0:
        msg += (
            f" - but only {applied * 100:.0f}% of the convex BODY edge length carries any "
            f"break at all (full credit at {VOCAB_APPLIED_FULL * 100:.0f}%), so a "
            f"vocabulary this coherent is a coincidence rather than a language"
        )
    if not exterior:
        msg += (
            f" - but not one break is visible from outside, so this is capped at "
            f"{INTERIOR_ONLY_CEILING:.0f}"
        )
    return _degrade(
        _metric(
            "radius_vocabulary",
            SCORED,
            score,
            msg,
            value=round(conformance, 4),
            visible=bool(exterior),
            applied=None if applied is None else round(applied, 4),
            applied_factor=round(applied_factor, 3),
            distinct=distinct,
            off_ladder=[b["size"] for b in distinct if not b["on_ladder"]],
            split_rungs=[
                {"size": s["size"], "near": s["near"], "area_mm2": round(s["area_mm2"], 1)}
                for s in splits
            ],
            coherence=round(coherence, 4),
            split_ratio=round(_ladder_min_ratio(ladder), 4),
            ladder=list(ladder),
            reclassified_faces=reclassified_faces,
            reclassified_mm2=round(reclassified, 1),
        ),
        max(population, 1e-9),
        unmeasured,
        reasons,
    )


# ---------------------------------------------------------------------------
# Metric: symmetry
# ---------------------------------------------------------------------------
def _sliver_weight(dims: list[float]) -> float:
    """
    How much of a SLIVER a mirror-difference lump is, from 0 to 1.

    Longest over shortest bounding-box dimension, ramped across
    SLIVER_ASPECT_NONE -> SLIVER_ASPECT_FULL. A ramp and not a cliff because the
    only honest thing to say about a lump in between is that it is partly one.
    """
    thin = max(dims[2], 1e-9)
    return _clamp((dims[0] / thin - SLIVER_ASPECT_NONE) / (SLIVER_ASPECT_FULL - SLIVER_ASPECT_NONE))


def _diff_extent(solids: list, frame: Frame) -> tuple[float, float]:
    """
    Diagonal of the widest SLIVER-LIKE symmetric-difference lump, and the raw
    diagonal of the largest lump of any shape.

    Not the combined bounding box of all the lumps: that was measured on the
    corpus and saturates at 1.00 for every part with any asymmetry at all,
    because a handful of small scattered differences already spans the part. It
    scored the exemplar and amplifier_housing_v3 - both 2% asymmetric by volume
    and symmetric to the eye - a flat 0. What the term is for is a difference
    that is THIN BUT WIDE: one lump that runs across the part, like a chamfer
    applied to one rim and not its mirror. That is a per-lump question.

    It is also a question about the lump's SHAPE, which is the half this used to
    leave out - see SLIVER_ASPECT_NONE. A compact lump is a functional
    interface and is priced by volume; only a sliver's extent is charged here,
    and it is charged in proportion to how slender it is.

    The second return value is measured but never scored. It is what the report
    prints beside the charged figure, so a part whose largest difference was
    excused as a chunk still SHOWS that difference to whoever reads the review.
    """
    charged = 0.0
    raw = 0.0
    for s in solids:
        # A lump whose bounding box cannot be taken used to be skipped, which
        # can only ever UNDERSTATE the extent and so can only ever flatter
        # symmetry. It is raised instead: _metric_symmetry catches it per axis,
        # DEGRADATION_MAX["symmetry"] is 0.0, and the metric errors out at full
        # weight rather than reporting a number it did not measure.
        # Measured along the PART's axes, not the world's. A lump's aspect ratio
        # is what decides whether it is charged as a sliver or excused as a
        # compact interface, and an aspect taken from the world box is a
        # function of the file: the same slab reads 60 x 40 x 2 as modelled and
        # 71 x 71 x 2 turned 45 degrees, which is a different verdict about the
        # same difference.
        size = frame.extents_of(s)
        diag = math.sqrt(sum(d * d for d in size))
        raw = max(raw, diag)
        dims = sorted(size, reverse=True)
        charged = max(charged, diag * _sliver_weight(dims))
    return charged, raw


def _mirror_difference(
    shape: cq.Shape, mirrored: cq.Shape, frame: Frame | None = None
) -> tuple[float, float, float]:
    """
    (difference volume, charged sliver extent, raw largest extent) between a
    shape and its mirror.

    A null boolean result means the two shapes COINCIDE, not that the
    measurement failed. The audit found a solid that is exactly symmetric to
    the last bit scoring 0.0 - the worst possible score - because
    mirrored.cut(shape) raised on a null TopoDS_Shape, that axis was dropped,
    and a worse axis became "best". The distance check is the arbiter.

    Only ONE of the two cuts is computed. A shape and its mirror have exactly
    the same volume V, so |A minus B| = V - |A and B| = |B minus A| identically,
    and the two difference sets are mirror images of each other, so their
    per-lump extents match too. Halving the booleans took this metric from
    11.5 s to 5.8 s on the 536-face exemplar with no change to either number.

    `frame` is the ruler the lump extents are taken in; it defaults to the
    shape's own frame so this stays callable on its own from a probe or a test.
    """
    if frame is None:
        frame = reference_frame(shape)
    try:
        lumps = shape.cut(mirrored).Solids()
        volume = sum(abs(s.Volume()) for s in lumps)
    except Exception:
        dist = BRepExtrema_DistShapeShape(shape.wrapped, mirrored.wrapped)
        dist.Perform()
        if not dist.IsDone() or dist.Value() > 1e-6:
            raise ValueError("mirror boolean failed and the shapes do not coincide")
        return 0.0, 0.0, 0.0
    charged, raw = _diff_extent(lumps, frame)
    return 2.0 * volume, charged, raw


def _metric_symmetry(
    shape: cq.Shape, frame: Frame | None = None, max_faces: int = SYMMETRY_MAX_FACES_DEFAULT
) -> dict:
    """
    Asymmetric volume about the best mirror plane, and how SLENDER that
    difference is.

    THE CANDIDATE PLANES ARE NORMAL TO THE PART'S OWN AXES, not to the world's.
    Mirroring about the world planes was the single worst rotation-dependence in
    this module: parts/_template is symmetric about two of its own centre planes
    and measured 88 as modelled and 0 after a 37 degree rotation about Z, on a
    part that had not changed. A world plane through a turned part cuts it into
    two pieces that are not each other's mirror at all, so the metric was
    answering a question about the file.

    `frame` defaults to the shape's own frame, so the metric stays callable on
    its own; the review always passes the frame the rest of the report was
    measured in, so the two can never disagree.
    """
    if frame is None:
        frame = reference_frame(shape)
    try:
        volume = abs(shape.Volume())
    except Exception as exc:
        return _metric("symmetry", METRIC_ERROR, None, f"volume unavailable: {exc}")
    if volume < 1e-6:
        return _metric("symmetry", METRIC_ERROR, None, "zero volume - cannot mirror-compare")
    if len(shape.Faces()) > max_faces:
        # A COST decision, not an exemption. This used to return NOT_REQUIRED,
        # which renormalised symmetry out of the score for free and left no
        # reason and no record - an integer knob in spec.json that walked
        # straight past the validator demanding a written justification for
        # every waiver. Under the error invariant the knob still saves the
        # booleans and now costs the weight, so setting it low is never worth
        # anything, and a part that genuinely cannot afford the measurement
        # says so with a waiver like everything else.
        return _metric(
            "symmetry",
            METRIC_ERROR,
            None,
            f"not measured: {len(shape.Faces())} faces exceeds symmetry_max_faces "
            f"({max_faces}) - the mirror booleans were skipped to save time",
        )

    # The mirror plane goes through the FRAME BOX centre, not the centroid.
    # Mirror symmetry about a plane forces the bounding box to be symmetric
    # about that same plane, so the box centre is on it exactly, while the
    # centroid is pulled off it by every hole and boss the part carries. With a
    # centroid plane, an ordinary part with a few holes differs from its own
    # mirror by a thin slab spanning the whole part - measured on the corpus,
    # that made the difference EXTENT read 1.00 for every part with any
    # asymmetry at all, scoring the exemplar and amplifier_housing_v3 a flat 0.
    # It is also what the corpus's own new defect note describes: a solid that
    # is exactly symmetric to the last bit lands its centroid at y = 4e-07 after
    # a STEP round trip, and the difference boolean degenerates.
    base = (frame.centre.x, frame.centre.y, frame.centre.z)
    diag = frame.diagonal
    # A mirror plane is named by its normal's AXIS, unsigned: mirroring about
    # the plane normal to +X and to -X is the same operation. The labels follow
    # the frame axis's nearest world axis so a finding on an axis-aligned part
    # still reads "normal-Z"; on an oblique part they name the frame axis by
    # its rank, because "normal-Z" would be a lie.
    labels = _frame_axis_labels(frame)
    results: dict[str, tuple[float, float]] = {}
    raw_extents: dict[str, float] = {}
    errors: dict[str, str] = {}
    for axis, normal in zip(labels, frame.axes):
        try:
            mirrored = shape.mirror(normal, base)
            vol, extent, raw = _mirror_difference(shape, mirrored, frame)
        except Exception as exc:
            errors[axis] = f"{type(exc).__name__}: {exc}"
            continue
        results[axis] = (vol / (2.0 * volume), (extent / diag) if diag > 1e-9 else 0.0)
        raw_extents[axis] = (raw / diag) if diag > 1e-9 else 0.0

    if not results:
        return _metric(
            "symmetry",
            METRIC_ERROR,
            None,
            "every mirror boolean failed - symmetry unmeasured",
            errors=errors,
        )

    def axis_score(vals: tuple[float, float]) -> float:
        vol_frac, extent = vals
        # BOTH terms must be good, and they answer different questions. Volume
        # prices a CHUNK of asymmetry - an ear, a boss, a bay on one side only.
        # Extent prices a SLIVER of it - the corpus's near-symmetric case is a
        # couple of percent by volume and visibly one-sided, and the extent term
        # is what catches it. So the answer is "be symmetric", not "be thinly
        # asymmetric" - and not, since SLIVER_ASPECT_NONE, "have no interfaces".
        return min(
            _lerp_score(vol_frac, best=0.01, worst=0.12),
            _lerp_score(extent, best=0.15, worst=0.75),
        )

    best_axis = max(results, key=lambda k: axis_score(results[k]))
    vol_frac, extent = results[best_axis]
    raw_extent = raw_extents.get(best_axis, extent)
    score = axis_score(results[best_axis])
    status = METRIC_ERROR if errors and not results else SCORED
    # THE OTHER TWO PLANES ARE PART OF THE ANSWER, and leaving them out of the
    # message let this metric say "0.0% asymmetric volume" about a box with a
    # 20 x 20 x 16 boss welded to one end - 15.9% asymmetric about X, and
    # exactly symmetric about the other two, so the max over planes reads a
    # flawless 100.0 and prints the plane that saw nothing. The SCORE is not
    # wrong: measured on this repo's own artifacts, the scaffold reads
    # [X 18.6%, Y 0.0%, Z 32.7%] and the exemplar [X 0.9%, Y 10.2%, Z 35.9%],
    # which is one connector end and one mounting face and is exactly what the
    # welded boss looks like from inside a B-rep. No rule over these three
    # numbers separates the two, so the max stands and the disclosure is what
    # changes: the worst plane is named next to the best one, and a reader can
    # no longer take a 100 as "this part is symmetric".
    worst_axis = min(results, key=lambda k: axis_score(results[k]))
    msg = (
        f"best mirror plane is normal-{best_axis}: {vol_frac * 100:.1f}% asymmetric "
        f"volume, with slender difference spread over {extent * 100:.0f}% of the bbox diagonal"
    )
    if raw_extent > extent + 1e-6:
        # Disclosure, not a charge. Whoever reads the review should be able to
        # see that a difference this wide exists and was judged an interface.
        msg += (
            f" (the largest difference of any shape spans {raw_extent * 100:.0f}%, but it is a "
            f"compact lump - a functional interface, priced by volume rather than by extent)"
        )
    if worst_axis != best_axis:
        wv, we = results[worst_axis]
        msg += (
            f"; normal-{worst_axis} is the part's least symmetric plane at "
            f"{wv * 100:.1f}% asymmetric volume over {we * 100:.0f}% of the diagonal, "
            f"scoring {axis_score(results[worst_axis]):.0f} - disclosed, not charged, because "
            f"one mirror plane is all this metric asks a part for"
        )
    return _degrade(
        _metric(
            "symmetry",
            status,
            score,
            msg,
            value=round(vol_frac, 4),
            best_axis=best_axis,
            worst_axis=worst_axis,
            worst_axis_score=round(axis_score(results[worst_axis]), 1),
            extent=round(extent, 4),
            raw_extent=round(raw_extent, 4),
            per_axis={k: [round(v[0], 4), round(v[1], 4)] for k, v in results.items()},
            per_axis_raw_extent={k: round(v, 4) for k, v in raw_extents.items()},
            errors=errors or None,
        ),
        3.0,
        float(len(errors)),
        list(errors.values()),
    )


# ---------------------------------------------------------------------------
# Metric: proportion
# ---------------------------------------------------------------------------
def _metric_proportion(topo: Topology, rubric: Rubric) -> dict:
    dims = sorted(topo.bbox_size(), reverse=True)
    if dims[2] < 1e-9:
        return _metric("proportion", METRIC_ERROR, None, "degenerate bounding box")
    long_ratio = dims[0] / dims[2]
    mid_ratio = dims[0] / dims[1]
    stick = mid_ratio >= 6.0
    slab = (not stick) and long_ratio >= 8.0
    best, worst = rubric.proportion_knots
    score = _lerp_score(long_ratio, best=best, worst=worst)
    shape_word = "stick-like" if stick else ("slab-like" if slab else "balanced")
    return _metric(
        "proportion",
        SCORED,
        score,
        f"bbox {dims[0]:.0f} x {dims[1]:.0f} x {dims[2]:.0f} mm, max/min {long_ratio:.1f} "
        f"({shape_word})",
        value=round(long_ratio, 2),
        sorted_dims=[round(d, 2) for d in dims],
        slab=slab,
        stick=stick,
    )


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------
def _severity(score: float | None) -> str:
    if score is None:
        return "info"
    if score < 40:
        return "high"
    if score < 70:
        return "medium"
    return "low"


def _suggest_break(topo: Topology, ladder: tuple[float, ...]) -> float:
    """Break size the part scale asks for: the ladder step nearest 3% of the
    smallest bbox dimension, clamped to a machinist-sane 0.5-3.0 mm."""
    target = _clamp(0.03 * min(topo.bbox_size()), 0.5, 3.0)
    return min(ladder, key=lambda r: abs(r - target))


def _finding(fid: str, metric: str, severity: str, message: str, **extra) -> dict:
    return {"id": fid, "metric": metric, "severity": severity, "message": message, **extra}


def _build_findings(
    topo: Topology,
    metrics: dict,
    ladder: tuple[float, ...],
    floors: list[dict] | None = None,
) -> list[dict]:
    out: list[dict] = []
    brk = _suggest_break(topo, ladder)

    # -- unmet FLOORS lead, always ------------------------------------------
    # A floor is not a suggestion and it is not competing with the other
    # findings for attention: it is the reason the part cannot pass, and it
    # names the fix. Emitted before anything else and at "high" so the sort
    # cannot bury it behind eight edge-break findings.
    for f in floors or []:
        if f["met"]:
            continue
        out.append(
            _finding(
                "floor_unmet",
                f["metric"],
                "high",
                f"RUBRIC FLOOR UNMET - {f['metric']} {f['detail']}. This is a hard minimum "
                f"on a single metric, outside the weighted mean: it cannot be waived, "
                f"disabled, renormalised out or averaged away, and while it is unmet the "
                f"part is capped at band {FLOOR_BAND_CAP} whatever it scores. Why this floor "
                f"exists: {f['why']}",
                floor=f["floor"],
            )
        )

    # -- conditions of the MEASUREMENT, never gated behind a score ----------
    # The audit found the unresolved-edge warning silenced exactly when it
    # mattered: it sat inside "if score < 90", so when unresolved edges pushed
    # coverage to a false 100 the warning could not fire.
    for mid, m in metrics.items():
        if m.get("unmeasured_fraction", 0.0) > 0.02 and m["status"] != METRIC_ERROR:
            out.append(
                _finding(
                    "degraded_measurement",
                    mid,
                    "info",
                    f"{m['unmeasured_fraction'] * 100:.0f}% of {mid}'s population could not be "
                    f"classified; the score is measured on the remainder",
                    reasons=m.get("unmeasured_reasons"),
                )
            )

    m = metrics.get("edge_break_coverage")
    if m and m.get("rim_bare_mm", 0) > 5.0:
        out.append(
            _finding(
                "sharp_rim",
                "edge_break_coverage",
                "low",
                f"{m['rim_bare_mm']:.0f} mm of bare hole/boss rim edge - add a "
                f"0.4 x 45 deg lead-in chamfer at each rim",
                length_mm=m["rim_bare_mm"],
                builder=_builder("counterbore_at", "cut a shallow lead-in cone at each rim"),
            )
        )
    # Say out loud when the composite is being carried by the rim term. A part
    # whose bores are deburred and whose corners are raw used to read as a
    # passable 15/100 with no line anywhere saying which half of the metric that
    # came from, and 15 is what the floor used to be set against.
    if (
        m
        and m["status"] == SCORED
        and isinstance(m.get("body_score"), (int, float))
        and isinstance(m.get("rim_score"), (int, float))
        and m["body_score"] < 40.0
        and m["rim_score"] - m["body_score"] > 25.0
    ):
        out.append(
            _finding(
                "rim_carrying_body",
                "edge_break_coverage",
                "high",
                f"the bore/boss rims are broken ({m['rim_score']:.0f}/100) and the BODY is not "
                f"({m['body_score']:.0f}/100): {m['body_broken_mm']:.0f} of "
                f"{m['body_broken_mm'] + m['body_sharp_mm']:.0f} mm of silhouette edge. "
                f"Deburring a hole is not breaking a corner - the two terms are scored "
                f"separately and the rubric floor is held against the body term alone",
                body_score=m["body_score"],
                rim_score=m["rim_score"],
            )
        )
    if m and m["status"] in (SCORED, ABSENT) and (m["score"] or 0) < 90:
        for g in m.get("worst", [])[:4]:
            out.append(
                _finding(
                    "sharp_edge_run",
                    "edge_break_coverage",
                    _severity(m["score"]),
                    f"{g['length_mm']:.0f} mm of unbroken convex edge where the {g['face_hint']} "
                    f"faces meet, longest run {g['longest']:.0f} mm near {g['at']} - "
                    f"break it with a "
                    f"{brk:g} mm chamfer or an R{brk:g} fillet",
                    at=g["at"],
                    length_mm=g["length_mm"],
                    builder=_builder(
                        ("rounded_box", "rounded_prism"),
                        "bake the radius into the base solid, before any boolean",
                    ),
                )
            )

    m = metrics.get("face_composition")
    if m and m["status"] == SCORED and (m["score"] or 0) < 90:
        worst = (m.get("faces") or [{}])[0]
        out.append(
            _finding(
                "empty_face_region",
                "face_composition",
                _severity(m["score"]),
                f"the {worst.get('normal')} face at {worst.get('at')} carries an empty circle of "
                f"R{worst.get('lec_radius_mm')} mm, {m['void_worst']:.2f} of its own silhouette "
                f"scale - sink a 1.5-2.5 mm recessed panel with a rounded-corner boundary, leave a "
                f"proud perimeter frame, and fill it with a rib field. Only relief deeper than "
                f"{RELIEF_MIN_MM:g} mm counts, so a scribed outline buys nothing",
                at=worst.get("at"),
                builder=_builder(
                    ("recessed_panel", "rib_field", "connector_land"),
                    "cut a rounded-corner pocket 1.5-2.5 mm deep, then rib it",
                ),
            )
        )

    m = metrics.get("feature_composition")
    if m and m["status"] in (SCORED, ABSENT) and (m["score"] or 0) < 90:
        if m.get("mode") == "profile":
            # A turned part must never be told to add a bolt pattern. The
            # advice has to be in the vocabulary the part actually has.
            out.append(
                _finding(
                    "undifferentiated_profile",
                    "feature_composition",
                    _severity(m["score"]),
                    f"{m['message']} - give the profile something to be: a register step for "
                    f"what it locates, a relieved diameter where nothing bears, a bore or a "
                    f"seal groove. Do NOT add a bolt pattern; a turned part is not fastened "
                    f"by one",
                    builder=_builder(
                        ("step_shoulder", "ring_groove"),
                        "turn the profile as a stack of registers rather than one diameter",
                    ),
                )
            )
        else:
            out.append(
                _finding(
                    "scattered_features",
                    "feature_composition",
                    _severity(m["score"]),
                    f"{m['message']} - put features on shared centrelines, at a constant pitch, "
                    f"in families of ONE diameter; a lone feature scores zero, so adding another "
                    f"unrelated one always makes this worse",
                    builder=_builder(
                        ("bolt_pattern", "rib_field", "louver_bank", "fin_bank"),
                        "place holes with a rectangular pattern and ribs on a constant pitch",
                    ),
                )
            )

    m = metrics.get("radius_vocabulary")
    if m and m["status"] in (SCORED, ABSENT) and (m["score"] or 0) < 90:
        off = m.get("off_ladder") or []
        if not m.get("distinct"):
            out.append(
                _finding(
                    "no_breaks",
                    "radius_vocabulary",
                    "high",
                    f"no fillet or chamfer faces exist - every exterior corner is a knife edge; "
                    f"start with R{brk:g} plan radii baked into the base solid before any boolean",
                    builder=_builder(
                        ("rounded_box", "rounded_prism"),
                        "box(...).edges('|Z').fillet(r) BEFORE any boolean",
                    ),
                )
            )
        elif off:
            out.append(
                _finding(
                    "off_ladder_radii",
                    "radius_vocabulary",
                    _severity(m["score"]),
                    f"{len(off)} break size(s) off the ladder: "
                    f"{', '.join(f'{v:g}' for v in off[:8])} "
                    f"- consolidate onto {', '.join(f'{v:g}' for v in ladder[:8])} ...",
                    off_ladder=off,
                )
            )
        # A SPLIT RUNG names the specific pair to merge, which is a different
        # instruction from "you have too many radii" - the finding this replaced
        # told an author with ten correct sizes to delete six of them.
        for s in m.get("split_rungs") or []:
            out.append(
                _finding(
                    "split_radius_rung",
                    "radius_vocabulary",
                    "low",
                    f"R{s['size']:g} sits within one ladder step of R{s['near']:g}, which this "
                    f"part uses more - {s['area_mm2']:.0f} mm2 of break area on a size the design "
                    f"language does not distinguish from one already in use; move it onto "
                    f"R{s['near']:g}",
                    size=s["size"],
                    near=s["near"],
                )
            )
        if m.get("applied") is not None and m.get("applied_factor", 1.0) < 1.0:
            out.append(
                _finding(
                    "vocabulary_not_applied",
                    "radius_vocabulary",
                    _severity(m["score"]),
                    f"the break sizes in use are coherent, but only {m['applied'] * 100:.0f}% of "
                    f"the convex BODY edge length carries any break at all - a vocabulary is a "
                    f"set of repeated decisions, so apply the same rungs to the rest of the "
                    f"silhouette (full credit at {VOCAB_APPLIED_FULL * 100:.0f}%) rather than "
                    f"adding another size",
                    applied=m["applied"],
                )
            )

    m = metrics.get("pattern_discipline")
    if m and m.get("mode") == "profile" and (m["score"] or 0) < 90:
        out.append(
            _finding(
                "unrelieved_shoulders",
                "pattern_discipline",
                _severity(m["score"]),
                f"{m['message']}",
                builder=_builder(
                    ("step_shoulder", "ring_groove"),
                    "fillet each shoulder root to a ladder radius, or cut a relief undercut",
                ),
                shoulders=m.get("shoulders"),
                raw=m.get("raw"),
            )
        )
    elif m and m["status"] == ABSENT:
        out.append(
            _finding(
                "no_fastener_pattern",
                "pattern_discipline",
                "high",
                f"{m['message']} - place them with a rectangular pattern on a constant pitch at a "
                f"constant edge inset, symmetric about the part centrelines",
                builder=_builder(
                    ("bolt_pattern", "counterbore_at"),
                    "lib.common.bolt_pattern_rect() on a flat land",
                ),
            )
        )
    elif m and m["status"] == SCORED and (m["score"] or 0) < 90:
        for g in sorted(m.get("groups", []), key=lambda g: g["score"])[:2]:
            bits = []
            if g["pitch_cv"] is not None and g["pitch_cv"] > 0.15:
                bits.append(f"nearest-neighbour pitch CV {g['pitch_cv']:.2f} (target <= 0.15)")
            if g["symmetric_fraction"] < 0.99:
                bits.append(
                    f"only {g['symmetric_fraction'] * 100:.0f}% of holes have a "
                    f"centreline mirror partner"
                )
            if g["inset_cv"] is not None and g["inset_cv"] > 0.20:
                bits.append(
                    f"edge inset CV {g['inset_cv']:.2f} (mean inset {g['mean_inset_mm']} mm)"
                )
            if m.get("loose"):
                bits.append(f"{m['loose']} hole(s) belong to no family at all")
            if not bits:
                continue
            out.append(
                _finding(
                    # NOT "fastener_rhythm": that is a RETIRED METRIC id, and a
                    # live finding wearing a retired metric's name is how a
                    # reader concludes the retired metric is still being scored.
                    # Findings are named for the defect, metrics for the measure.
                    "irregular_fastener_pattern",
                    "pattern_discipline",
                    _severity(g["score"]),
                    f"{g['count']}x D{g['diameter']} holes on {g['axis']}: "
                    + "; ".join(bits)
                    + " - place them on a constant pitch at a constant 8-12 mm inset, symmetric "
                    "about the part centrelines",
                    builder=_builder(
                        ("bolt_pattern", "counterbore_at"),
                        "lib.common.bolt_pattern_rect() on a flat land",
                    ),
                )
            )

    m = metrics.get("symmetry")
    if m and m["status"] == SCORED and (m["score"] or 0) < 90:
        out.append(
            _finding(
                "asymmetric",
                "symmetry",
                _severity(m["score"]),
                f"best mirror plane (normal-{m['best_axis']}) still leaves {m['value'] * 100:.1f}% "
                f"of the volume asymmetric, with SLENDER difference spread over "
                f"{m['extent'] * 100:.0f}% of the bbox diagonal (per axis {m['per_axis']}) - "
                f"reference parts are near symmetric about at least one plane. A connector bay, "
                f"a mounting pad or any other compact interface is already excused here, so what "
                f"is left is a break, groove, rib or fin that exists on one side and not its "
                f"mirror; mirror it, or waive this metric in spec.json with a written reason",
            )
        )

    m = metrics.get("proportion")
    if m and m["status"] == SCORED and (m["score"] or 0) < 70:
        out.append(
            _finding(
                "extreme_proportion",
                "proportion",
                _severity(m["score"]),
                f"bbox aspect {m['value']:.1f}:1 ({m['sorted_dims']}) reads as "
                f"{'stick-like' if m['stick'] else 'slab-like'} - taper the section or "
                f"break the mass "
                f"with a step so it does not read as cut stock",
            )
        )

    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    out.sort(key=lambda f: order.get(f["severity"], 9))
    return out


# ---------------------------------------------------------------------------
# The configuration surface
# ---------------------------------------------------------------------------
# Keys that were removed rather than validated, and the sentence that says why.
# A removed key is an ERROR, never a silent ignore: an agent that writes it and
# sees no complaint will believe it worked.
#
# Keys are dotted PATHS, so a knob nested inside `style` retires by exactly the
# same route and produces exactly the same error as a top-level one.
RETIRED_CONFIG_KEYS = {
    "weights": (
        "design.weights has been removed. The relative weight of the metrics IS "
        "the standard, so a part that sets its own weights is not being held to "
        "one. Measured on a crude knife-edged box: 27.7/F honestly, 100.0/A with "
        "six weights zeroed, 425.5/A with two of them negative. Pick a role for a "
        "different rubric, waive a metric with a written reason to excuse it, or "
        "use metrics.<id>.min_score / max_value to make the bar HIGHER"
    ),
    "style.radius_ladder": (
        "design.style.radius_ladder has been removed, for the same reason "
        "design.weights was. The ladder IS the design language, so a part that "
        "declares its own is not being held to one - it is publishing one, and "
        "nothing in the report said the geometry had not changed. Validating the "
        "shape of the ladder (5 rungs, 4:1 span, a written reason) never checked "
        "the only thing that mattered, which is whether the rungs were anything "
        "but a transcription of the part's own measured radii. Measured on an "
        "unchanged STEP - a flat slab whose one plan radius was off-ladder - "
        "declaring a plausible-looking 5-rung ladder took radius_vocabulary from "
        "0.0 to 100.0 and the part from 57.3/C to 69.3/C, +12.0 points of pure "
        "configuration. A design family that genuinely uses different radii "
        "changes lib.features.Style, which is one reviewed edit that moves every "
        "part in the repo together, rather than one part's private standard"
    ),
}


@dataclass(frozen=True)
class ConfigError:
    """One rejected configuration key, with the sentence that rejects it."""

    key: str
    message: str


def _strip_retired(raw: dict) -> tuple[dict, list[ConfigError]]:
    """
    A deep copy of `raw` with every retired path removed, and one error each.

    Paths are dotted so a nested knob retires exactly like a top-level one. A
    retired key is never a silent ignore: an agent that writes one and sees no
    complaint will believe it worked, and the whole point of retiring a knob is
    that the belief is wrong.
    """
    errors: list[ConfigError] = []
    clean = copy.deepcopy(raw)
    for path, why in RETIRED_CONFIG_KEYS.items():
        parts = path.split(".")
        node = clean
        for step in parts[:-1]:
            node = node.get(step) if isinstance(node, dict) else None
            if not isinstance(node, dict):
                node = None
                break
        if isinstance(node, dict) and parts[-1] in node:
            del node[parts[-1]]
            errors.append(ConfigError(path, why))
    return clean, errors


def _normalise_config(config: dict | None) -> tuple[dict, list[ConfigError]]:
    """
    Validate the spec.json "design" block into the form review_shape() uses.

    ONE front door for both entry points - the spec.json block through
    lib/evaluate.py and `--config` through the CLI - because the audit found
    the two disagreeing about what was allowed, and the looser one is the one
    that decides. Returns (clean config, errors). Never raises: a malformed
    block produces errors and the DEFAULTS, so a typo cannot buy a lighter
    review, only a louder report.

    Every excusal it accepts - a waiver, or `metrics.<id>.enabled: false`, which
    is a waiver by another name - must carry a written reason, and lands in one
    `waivers` dict so there is a single place that knows what was excused.

    A metric carrying a RUBRIC_FLOORS floor cannot be excused at all, and a
    per-metric `min_score` below its floor is rejected rather than silently
    ignored: a floor a part could waive, disable or talk down is not a floor.
    """
    errors: list[ConfigError] = []
    raw = config or {}
    if not isinstance(raw, dict):
        return {}, [ConfigError("design", "the design config block must be an object")]

    clean, errors = _strip_retired(raw)

    # -- waivers, and the metric switches that are waivers in disguise --------
    waivers: dict[str, str] = {}
    raw_waivers = raw.get("waivers") or {}
    if not isinstance(raw_waivers, dict):
        errors.append(ConfigError("waivers", 'design "waivers" must be an object {metric: reason}'))
        raw_waivers = {}
    for mid, reason in raw_waivers.items():
        if mid not in METRIC_IDS:
            errors.append(
                ConfigError(
                    f"waivers.{mid}",
                    f"waives unknown metric {mid!r} (known: {', '.join(METRIC_IDS)})",
                )
            )
        elif mid in RUBRIC_FLOORS:
            errors.append(ConfigError(f"waivers.{mid}", _floor_not_waivable(mid)))
        elif not isinstance(reason, str) or not reason.strip():
            errors.append(
                ConfigError(
                    f"waivers.{mid}",
                    f"waiver for {mid!r} has no written reason - a metric that drops out "
                    f"of the score with nobody's name on it is how a standard rots",
                )
            )
        else:
            waivers[mid] = reason.strip()

    metrics = raw.get("metrics") or {}
    if not isinstance(metrics, dict):
        errors.append(ConfigError("metrics", 'design "metrics" must be an object'))
        metrics = {}
    clean_metrics: dict[str, dict] = {}
    for mid, cfg in metrics.items():
        if not isinstance(cfg, dict):
            errors.append(ConfigError(f"metrics.{mid}", "must be an object"))
            continue
        if mid not in METRIC_IDS:
            errors.append(
                ConfigError(
                    f"metrics.{mid}",
                    f"unknown metric {mid!r} (known: {', '.join(METRIC_IDS)})",
                )
            )
            continue
        cfg = dict(cfg)
        if cfg.get("enabled") is False:
            # Identical in effect to a waiver, so it is held to a waiver's
            # standard. It used to reach NOT_REQUIRED with no reason at all.
            if mid in RUBRIC_FLOORS:
                errors.append(ConfigError(f"metrics.{mid}.enabled", _floor_not_waivable(mid)))
            else:
                reason = cfg.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    errors.append(
                        ConfigError(
                            f"metrics.{mid}.enabled",
                            f"disabling {mid!r} is a waiver by another name and needs a written "
                            f'"reason" alongside it, exactly like design.waivers',
                        )
                    )
                elif mid not in waivers:
                    waivers[mid] = reason.strip()
        cfg.pop("enabled", None)
        # A part may RAISE a floor and never lower it, and "never lower it" has
        # to be unrepresentable rather than merely ineffective. A min_score
        # under the floor used to be accepted and quietly outranked, which reads
        # from the spec.json exactly like a floor the author chose.
        floor = RUBRIC_FLOORS.get(mid)
        if floor is not None and isinstance(cfg.get("min_score"), (int, float)):
            if float(cfg["min_score"]) < floor.score:
                errors.append(
                    ConfigError(
                        f"metrics.{mid}.min_score",
                        f"{float(cfg['min_score']):g} is below the rubric floor of "
                        f"{floor.score:g} for {mid!r}. A per-metric min_score may only ever "
                        f"make the bar HIGHER; the floor is part of the rubric, not of this "
                        f"part, and it is hard whatever this block says. Floor: {floor.why}",
                    )
                )
                cfg.pop("min_score", None)
        clean_metrics[mid] = cfg
    clean["metrics"] = clean_metrics
    clean["waivers"] = waivers

    # -- symmetry_max_faces: a cost guard, range-checked for typos -----------
    smf = raw.get("symmetry_max_faces", SYMMETRY_MAX_FACES_DEFAULT)
    if not isinstance(smf, int) or isinstance(smf, bool) or smf < SYMMETRY_MAX_FACES_MIN:
        errors.append(
            ConfigError(
                "symmetry_max_faces",
                f"must be an integer of at least {SYMMETRY_MAX_FACES_MIN} - it is a cost "
                f"guard, and tripping it is a METRIC_ERROR that costs the full weight, "
                f"not an exemption",
            )
        )
        smf = SYMMETRY_MAX_FACES_DEFAULT
    clean["symmetry_max_faces"] = smf

    # -- style: nothing left in it but the reason a retired ladder carried ----
    style = clean.get("style", {})
    if not isinstance(style, dict):
        errors.append(ConfigError("style", 'design "style" must be an object'))
        style = {}
    clean["style"] = dict(style)
    return clean, errors


def _floor_not_waivable(mid: str) -> str:
    """The sentence that refuses to let a floored metric be excused."""
    floor = RUBRIC_FLOORS[mid]
    return (
        f"{mid!r} carries a rubric floor of {floor.score:g} and cannot be waived or "
        f"disabled. A waiver renormalises a metric OUT of the weighted mean, so waiving "
        f"the metric a part fails is worth the most points exactly when it is least "
        f"deserved - measured at +15.1 on a slab with no broken edge anywhere. The floor "
        f"exists because no average may launder this metric, and an excusal is an average "
        f"by another route. Floor: {floor.why}"
    )


def config_errors(config: dict | None) -> list[str]:
    """
    Every reason this design config is not acceptable, as ready-made sentences.

    The public face of _normalise_config(), for lib/evaluate.py: a malformed
    spec must be a HARD spec error there, not merely an ERROR check at whatever
    severity the part happened to choose, or a part with no `min_score` could
    write a retired key and be told about it in a soft voice.
    """
    return [f"design.{e.key}: {e.message}" for e in _normalise_config(config)[1]]


# ---------------------------------------------------------------------------
# Scoring passes
# ---------------------------------------------------------------------------
def _rubric_block(rubric: Rubric) -> dict:
    """The rubric, as it appears in the report."""
    return {
        "weights": dict(rubric.weights),
        "void_knots": list(rubric.void_knots),
        "proportion_knots": list(rubric.proportion_knots),
        "exclude_blank_perimeter": rubric.exclude_blank_perimeter,
        "note": rubric.note,
        "claim": rubric.claim,
    }


def _run_metrics(
    topo: Topology,
    shape: cq.Shape,
    rubric: Rubric,
    *,
    features: list[dict],
    features_error: str | None,
    waivers: dict[str, str],
    sym_max: int,
    ladder: tuple[float, ...],
    reuse: dict[str, dict] | None = None,
) -> dict[str, dict]:
    """
    Every metric, measured under one rubric with one set of waivers.

    Factored out of review_shape() so the SAME topology can be scored twice -
    once as configured and once under the default rubric with nothing excused -
    which is what makes _config_delta() one extra scoring pass rather than a
    second geometric analysis. `reuse` carries results that do not depend on the
    rubric at all (symmetry is a pair of mirror booleans on the raw shape, and
    it is the expensive one), so the second pass never repeats them.
    """
    metrics: dict[str, dict] = {}

    # Edge classification is a SHARED INPUT of two metrics, so it is computed
    # once, here, before either of them runs. It used to be a side effect of the
    # edge_break_coverage metric, and run() short-circuits on a waiver BEFORE
    # calling the metric, so waiving or disabling edge_break_coverage left
    # sharp_edge_length reading an empty dict and reporting a KERNEL ERROR
    # ("edge classification did not run") on a part where nothing was wrong. At
    # the documented metric_severity=hard that failed the build.
    breaks: dict | None = None
    breaks_error: str | None = None
    try:
        breaks = _classify_breaks(topo, rubric)
    except Exception as exc:
        breaks_error = f"edge classification failed: {type(exc).__name__}: {exc}"

    def run(mid: str, fn, *, needs_features: bool = False, needs_breaks: bool = False):
        if not rubric.applies(mid):
            metrics[mid] = _metric(
                mid,
                NOT_REQUIRED,
                None,
                f"not required for role {rubric.role}: {rubric.note}",
            )
            return
        if mid in waivers:
            metrics[mid] = _metric(mid, NOT_REQUIRED, None, f"waived: {waivers[mid]}", waived=True)
            return
        if reuse and mid in reuse:
            metrics[mid] = copy.deepcopy(reuse[mid])
            return
        if needs_features and features_error is not None:
            metrics[mid] = _metric(
                mid,
                METRIC_ERROR,
                None,
                f"cylindrical feature extraction failed: {features_error}",
            )
            return
        if needs_breaks and breaks is None:
            metrics[mid] = _metric(mid, METRIC_ERROR, None, breaks_error or "no breaks")
            return
        try:
            metrics[mid] = fn()
        except Exception as exc:
            metrics[mid] = _metric(mid, METRIC_ERROR, None, f"{type(exc).__name__}: {exc}")

    run("edge_break_coverage", lambda: _metric_edge_break(topo, breaks), needs_breaks=True)
    run("sharp_edge_length", lambda: _metric_sharp_length(topo, breaks), needs_breaks=True)
    run("face_composition", lambda: _metric_face_composition(topo, rubric))
    run(
        "feature_composition",
        lambda: _metric_feature_composition(topo, features),
        needs_features=True,
    )
    run(
        "pattern_discipline",
        lambda: _metric_pattern_discipline(topo, rubric, features),
        needs_features=True,
    )
    run(
        "radius_vocabulary",
        lambda: _metric_radius_vocabulary(topo, rubric, ladder, breaks),
        needs_breaks=True,
    )
    run("symmetry", lambda: _metric_symmetry(shape, topo.frame, sym_max))
    run("proportion", lambda: _metric_proportion(topo, rubric))

    # A score that is not a finite number can never enter the mean.
    for m in metrics.values():
        if m["status"] in (SCORED, ABSENT):
            s = m["score"]
            if not isinstance(s, (int, float)) or not math.isfinite(s):
                m["status"] = METRIC_ERROR
                m["score"] = None
                m["message"] = f"non-finite score: {s!r}"
    return metrics


def _weighted(metrics: dict[str, dict], weights: dict[str, float]) -> dict:
    """
    The weighted mean and its accounting, for one set of metrics and weights.

    THE ERROR INVARIANT lives here, in one line: errored weight sits in the
    DENOMINATOR contributing zero, so breaking a metric can never be worth more
    than scoring it. Only NOT_REQUIRED renormalises out. `score` is None when
    nothing at all could be measured, which is not a verdict and must never be
    rendered as one.
    """
    # absent_defect is MEASURED weight: it was measured, and the answer was zero.
    counted = {
        mid: m
        for mid, m in metrics.items()
        if m["status"] in (SCORED, ABSENT) and m["score"] is not None
    }
    total_w = sum(weights.values())
    used_w = sum(weights.get(mid, 0.0) for mid in counted)
    errored_w = sum(
        weights.get(mid, 0.0) for mid, m in metrics.items() if m["status"] == METRIC_ERROR
    )
    numerator = sum(m["score"] * weights.get(mid, 0.0) for mid, m in counted.items())
    return {
        "score": (numerator / (used_w + errored_w)) if used_w > 0 else None,
        "numerator": numerator,
        "total_weight": total_w,
        "used_weight": used_w,
        "errored_weight": errored_w,
        "coverage": round(used_w / total_w, 3) if total_w > 0 else 0.0,
        "errored": sorted(mid for mid, m in metrics.items() if m["status"] == METRIC_ERROR),
        "absent": sorted(mid for mid, m in metrics.items() if m["status"] == ABSENT),
    }


def _check_floors(metrics: dict[str, dict], rubric: Rubric) -> list[dict]:
    """
    Every rubric floor that applies to this part, and whether it is met.

    A floor applies whenever the ROLE's rubric uses the metric. A role exclusion
    is the one thing that legitimately removes a floor, because a role's weights
    already sum to 1.00 and a metric the role does not use buys the part nothing
    - `sheet` excludes sharp_edge_length because a formed blank's perimeter is
    not a design edge, and that exclusion is guarded against the geometry before
    it is honoured.

    Everything else that removes a metric FAILS the floor:
      * ABSENT - the geometry says the metric should apply and it does not,
        which is the defect the floor is named after, not an escape from it.
      * ERROR - under the error invariant an unmeasured metric is already worth
        zero at full weight, so a floor it could not clear is not a floor it
        cleared. Breaking the measurement must never be cheaper than passing it.
      * NOT_REQUIRED by waiver - unreachable, because _normalise_config()
        refuses to accept a waiver on a floored metric at all. Checked anyway:
        an invariant that is only enforced in one place is enforced nowhere.
    """
    out: list[dict] = []
    for mid in METRIC_IDS:
        floor = RUBRIC_FLOORS.get(mid)
        if floor is None or not rubric.applies(mid):
            continue
        m = metrics.get(mid)
        status = m["status"] if m else METRIC_ERROR
        score = m.get(floor.key) if m else None
        if status == SCORED and isinstance(score, (int, float)):
            met = score >= floor.score
            detail = f"{floor.label} {score:.1f} against a floor of {floor.score:g}"
        elif status == SCORED:
            # the floored quantity is not in the report at all: a measurement
            # that did not happen, held to the same rule as any other
            met = False
            detail = (
                f"the metric scored, but its {floor.label} was not reported, so the "
                f"floor could not be cleared"
            )
        elif status == ABSENT:
            met = False
            detail = (
                f"absent where the geometry requires it, which is the defect this floor "
                f"names: {m['message'] if m else ''}"
            )
        elif status == NOT_REQUIRED:
            met = False
            detail = "excused, and a floored metric cannot be excused"
        else:
            met = False
            detail = (
                f"could not be measured, so the floor was not cleared: {m['message'] if m else ''}"
            )
        out.append(
            {
                "metric": mid,
                "floor": floor.score,
                "score": score if isinstance(score, (int, float)) else None,
                "status": status,
                "met": met,
                "detail": detail,
                "why": floor.why,
            }
        )
    return out


def _config_delta(
    configured: float | None,
    default: float | None,
    knobs: list[str],
    role: str = DEFAULT_ROLE,
    role_only: float | None = None,
) -> dict:
    """
    How far the CONFIGURATION moved the score, on unchanged geometry, SPLIT into
    the two different claims it is made of.

    Every knob was already accounted for on its own - a role error names a
    contradicted claim, `score_unexcused` prices the waivers - and nothing added
    them up. The measured attack stacked a role, a ladder override and one
    waiver to move an unchanged STEP by +43.8 points, and no line of the report
    said the geometry had not changed. This is that line.

    `default` is the SAME measurements scored under the default rubric with
    nothing excused; `role_only` is the same measurements under the part's own
    rubric, still with nothing excused. So:

        role_delta   = role_only - default     what the ROLE is worth
        waiver_delta = configured - role_only  what the WAIVERS are worth

    THE TWO ARE CAPPED SEPARATELY BECAUSE THEY ARE NOT THE SAME KIND OF CLAIM. A
    role is a proposition about the geometry and ROLE_GUARDS checks it against
    the B-rep before the rubric is honoured, so it is bounded by what the role's
    own weights can produce (ROLE_DELTA_ALLOWANCE). A waiver is an assertion
    nothing checks, so it keeps the tight arithmetic bound (MAX_CONFIG_DELTA).
    Capping the SUM against the waiver bound is what made an honest sheet-metal
    bracket a configuration error.

    `delta`, `cap` and `within_cap` are kept and still mean the whole of the
    configuration against the whole of its budget, so a reader who only looks at
    those is not misled - they are simply no longer the only numbers.
    """
    role_cap, waiver_cap = config_delta_caps(role)
    if configured is None or default is None:
        return {
            "default_score": None if default is None else round(default, 1),
            "configured_score": None if configured is None else round(configured, 1),
            "role_only_score": None if role_only is None else round(role_only, 1),
            "delta": None,
            "role_delta": None,
            "waiver_delta": None,
            "cap": round(role_cap + waiver_cap, 1),
            "role_cap": role_cap,
            "waiver_cap": waiver_cap,
            "within_cap": True,
            "knobs": knobs,
            "message": "the default-rubric comparison could not be scored",
        }
    if role_only is None:
        # One of the two terms is zero by construction, so the third scoring pass
        # was skipped and the number is already in hand: with no role there is no
        # role delta, and with no waiver the configured score IS the role-only
        # score. The caller passes `role_only` whenever both knobs are present.
        role_only = default if role == DEFAULT_ROLE else configured
    delta = configured - default
    role_delta = role_only - default
    waiver_delta = configured - role_only
    over = []
    if role_delta > role_cap + 1e-9:
        over.append(
            f"the role is worth {role_delta:+.1f}, past the {role_cap:g} its own weights can "
            f"produce"
        )
    if waiver_delta > waiver_cap + 1e-9:
        over.append(
            f"the waivers are worth {waiver_delta:+.1f}, past the {waiver_cap:g} that "
            f"{MAX_EXCUSED_WEIGHT:.0%} of excused weight can arithmetically buy"
        )
    return {
        "default_score": round(default, 1),
        "role_only_score": round(role_only, 1),
        "configured_score": round(configured, 1),
        "delta": round(delta, 1),
        "role_delta": round(role_delta, 1),
        "waiver_delta": round(waiver_delta, 1),
        "cap": round(role_cap + waiver_cap, 1),
        "role_cap": role_cap,
        "waiver_cap": waiver_cap,
        "within_cap": not over,
        "over": over,
        "knobs": knobs,
        "message": (
            f"configuration ({', '.join(knobs) if knobs else 'none'}) is worth {delta:+.1f} "
            f"points against the default rubric on the same geometry "
            f"({round(default, 1)} -> {round(configured, 1)}): role {role_delta:+.1f} "
            f"of {role_cap:g}, waivers {waiver_delta:+.1f} of {waiver_cap:g}"
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def review_shape(shape, source: str | None = None, config: dict | None = None) -> dict:
    """
    Score the refinement of a shape (Workplane or Shape). Returns a
    "design-review/2" dict. Never raises for geometry reasons: individual
    metrics report status "error" and are excluded from the score.

    `config` is the per-part block described in design_review_checks(). It goes
    through _normalise_config() first, so every entry point gets the same
    validation and a rejected key is a `config_error` in the report rather than
    a silent effect. Its "role" key selects the rubric; an absent role means
    `enclosure`, which is the strictest, so claiming a lighter rubric is always
    deliberate - and the claim is checked against the geometry before it is
    honoured.
    """
    started = time.time()
    config, config_faults = _normalise_config(config)
    # Canonicalise the partition BEFORE anything measures. The feature census in
    # lib/analyze_step.py reads the shape directly rather than through Topology,
    # so a solid whose barrel arrived as two half-cylinders would be counted
    # twice here and once there. See _canonical_partition: how a B-rep is cut
    # into faces is a property of the file, not of the part.
    shape = _canonical_partition(_shape(shape))
    # ONE ladder, from lib/features.py, for every part in the repo. The per-part
    # override is retired - see RETIRED_CONFIG_KEYS["style.radius_ladder"].
    ladder, ladder_src = _load_ladder()

    declared_role = config.get("role")
    rubric, role_error = resolve_rubric(declared_role)

    report: dict = {
        "schema": SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "role": rubric.role,
        "role_declared": declared_role,
        "rubric": _rubric_block(rubric),
        "style": {"radius_ladder": list(ladder), "ladder_source": ladder_src},
        "config_errors": [{"key": e.key, "message": e.message} for e in config_faults],
        "metrics": {},
        "findings": [],
    }
    if role_error:
        report["role_error"] = role_error

    if not shape.Solids():
        report["status"] = "error"
        report["score"] = None
        report["band"] = None
        report["message"] = "no solids in the shape - nothing to review"
        return report

    try:
        topo = Topology(shape)
    except Exception as exc:
        report["status"] = "error"
        report["score"] = None
        report["band"] = None
        report["message"] = f"topology traversal failed: {type(exc).__name__}: {exc}"
        return report

    # THE ROLE CLAIM IS CHECKED BEFORE IT IS HONOURED.
    # Refusing one exclusion and honouring every other relaxation was not
    # enough: `sheet` still lost sharp_edge_length and proportion from its
    # rubric and kept its relaxed emptiness knots on a part the guard had just
    # said was not sheet metal, and the other four roles had no guard at all.
    # A contradicted claim now falls back to the whole enclosure rubric, which
    # is the only rubric that asserts nothing about the geometry and so is the
    # only one that cannot be wrong.
    claim_error = check_role_claim(rubric.role, topo)
    if claim_error is not None:
        report["role_error"] = (
            f"role {rubric.role!r} claims to be {rubric.claim}, but {claim_error} - "
            f"reviewed as {DEFAULT_ROLE}"
        )
        rubric = ROLE_RUBRICS[DEFAULT_ROLE]
        report["role"] = rubric.role
        report["rubric"] = _rubric_block(rubric)

    features: list[dict] = []
    features_error: str | None = None
    try:
        features = _cylinder_features(shape)
    except Exception as exc:
        # An empty feature list must never be indistinguishable from a failed
        # extraction: two metrics would then report a shape of the FAILURE
        # rather than a shape of the part.
        features_error = f"{type(exc).__name__}: {exc}"

    bb = topo.bbox_size()
    report["shape"] = {
        "solids": len(shape.Solids()),
        "faces": len(topo.faces),
        "edges": len(topo.edges),
        "bbox_size": [round(v, 3) for v in bb],
        "bbox_surface_mm2": round(topo.bbox_surface(), 1),
        "volume_mm3": round(abs(shape.Volume()), 1),
        "features_error": features_error,
        # The reference frame every dimension above was measured in. A published
        # score has to be able to name its own ruler, the same way it names the
        # rubric that weighted it.
        "frame": frame_record(topo.frame),
    }

    waivers = config.get("waivers") or {}
    sym_max = int(config.get("symmetry_max_faces", SYMMETRY_MAX_FACES_DEFAULT))

    metrics = _run_metrics(
        topo,
        shape,
        rubric,
        features=features,
        features_error=features_error,
        waivers=waivers,
        sym_max=sym_max,
        ladder=ladder,
    )
    report["metrics"] = metrics

    # The rubric's weights, and only the rubric's weights. There is no override
    # any more - see RETIRED_CONFIG_KEYS.
    weights = dict(rubric.weights)
    report["weights"] = weights
    report["probe_failures"] = topo.probe_failures

    agg = _weighted(metrics, weights)
    report["coverage"] = agg["coverage"]
    report["errored"] = agg["errored"]
    report["absent"] = agg["absent"]

    # THE FLOORS. Computed from the metrics and the rubric alone, never from the
    # part's own config, and reported whether they are met or not: a bar nobody
    # can see is a bar nobody is held to.
    floors = _check_floors(metrics, rubric)
    report["floors"] = floors
    unmet = [f for f in floors if not f["met"]]
    report["floor_failures"] = [f["metric"] for f in unmet]

    # Excusal accounting: which metrics left the rubric on somebody's SAY-SO
    # rather than on a measurement, and how much of the bar that was. Role
    # exclusions are not in here - a role's own weights already sum to 1.00, so
    # a metric the role does not use costs the part nothing and buys it nothing.
    excused = {
        mid: metrics[mid]["message"]
        for mid in sorted(waivers)
        if metrics.get(mid, {}).get("status") == NOT_REQUIRED
    }
    total_w = agg["total_weight"]
    excused_w = sum(weights.get(mid, 0.0) for mid in excused)
    report["excused"] = excused
    report["excused_weight"] = round(excused_w / total_w, 3) if total_w > 0 else 0.0

    # AGGREGATE CONFIGURATION ACCOUNTING. One extra scoring pass over the same
    # Topology, the same extracted features and the same symmetry booleans -
    # only the rubric and the waivers differ - so it is a re-scoring, not a
    # second geometric analysis, and it is skipped entirely when there is no
    # configuration to account for.
    #
    # Measured 2026-07-25 against the corpus, second pass as a fraction of the
    # whole one-pass review: exemplar 0.23 s of 18.6 s (+1.2%), sealed cover
    # 0.11 s of 5.7 s (+1.9%), structural arm 0.04 s of 2.1 s (+1.9%), interface
    # plate 0.08 s of 2.1 s (+4.0%), sheet bracket 0.03 s of 0.9 s (+3.0%).
    default_rubric = ROLE_RUBRICS[DEFAULT_ROLE]
    knobs: list[str] = []
    if rubric.role != DEFAULT_ROLE:
        knobs.append(f"role={rubric.role}")
    knobs += [f"waiver:{mid}" for mid in sorted(excused)]
    if not knobs:
        report["config_delta"] = _config_delta(agg["score"], agg["score"], [], rubric.role)
    else:
        reuse = (
            {"symmetry": metrics["symmetry"]}
            if metrics.get("symmetry", {}).get("status") != NOT_REQUIRED
            else None
        )
        default_metrics = _run_metrics(
            topo,
            shape,
            default_rubric,
            features=features,
            features_error=features_error,
            waivers={},
            sym_max=sym_max,
            ladder=ladder,
            reuse=reuse,
        )
        # A THIRD PASS ONLY WHEN BOTH KNOBS ARE TURNED. With a role and no
        # waiver the configured score already IS the role-only score, and with
        # waivers and no role the default score already is; the split then costs
        # nothing. It is only when the two are stacked - which is the case the
        # cap exists for - that the middle number has to be measured.
        role_only = None
        if rubric.role != DEFAULT_ROLE and excused:
            role_metrics = _run_metrics(
                topo,
                shape,
                rubric,
                features=features,
                features_error=features_error,
                waivers={},
                sym_max=sym_max,
                ladder=ladder,
                reuse=reuse,
            )
            role_only = _weighted(role_metrics, weights)["score"]
        report["config_delta"] = _config_delta(
            agg["score"],
            _weighted(default_metrics, dict(default_rubric.weights))["score"],
            knobs,
            rubric.role,
            role_only,
        )
    if not report["config_delta"]["within_cap"]:
        # An ERROR, on the same surface every other rejected configuration lands
        # on, so it reaches design_review_checks() and the console with no new
        # plumbing and at the same severity as a retired key.
        report["config_errors"].append(
            {
                "key": "config_delta",
                "message": (
                    f"{report['config_delta']['message']} - "
                    f"{'; '.join(report['config_delta'].get('over') or [])}. Past this the "
                    f"verdict is a statement about the spec.json, not about the part"
                ),
            }
        )

    if agg["used_weight"] <= 0:
        report["status"] = "insufficient"
        report["score"] = None
        report["band"] = None
        report["message"] = "no metric could be measured - the review is not a verdict"
    else:
        score = agg["score"]
        report["score"] = round(score, 1)
        # WHAT THE WAIVERS BOUGHT, in points. A waiver is renormalised out, so
        # waiving a metric the part FAILS always raises the score, and the only
        # bound on that is MAX_EXCUSED_WEIGHT. Publishing the score the part
        # would have had if every excused metric had measured zero does not
        # change the verdict, but it makes the price of an assertion visible to
        # whoever reads the report instead of leaving it to be reconstructed.
        report["score_unexcused"] = (
            round(agg["numerator"] / total_w, 1)
            if excused_w > 0 and total_w > 0
            else report["score"]
        )
        band, label = next((b, lbl) for cut, b, lbl in BANDS if score >= cut)
        report["band_uncapped"] = band
        if unmet:
            # THE CAP. The score is left exactly as measured - hiding the mean
            # would be its own dishonesty - but the BAND is the one-word verdict
            # a reader acts on, and a part with an unmet floor is a draft
            # whatever its mean says. max() takes the WORSE of the two, so a
            # cap can only ever lower a band.
            if _BAND_RANK[FLOOR_BAND_CAP] > _BAND_RANK[band]:
                band, label = FLOOR_BAND_CAP, _BAND_LABEL[FLOOR_BAND_CAP]
        report["band"] = band
        report["band_label"] = label
        article = _article(rubric.role)
        if report["excused_weight"] > MAX_EXCUSED_WEIGHT + 1e-9:
            report["status"] = "insufficient"
            report["message"] = (
                f"{report['excused_weight'] * 100:.0f}% of the rubric was excused by "
                f"assertion ({', '.join(sorted(excused))}), over the "
                f"{MAX_EXCUSED_WEIGHT * 100:.0f}% cap - a written reason makes an excusal "
                f"deliberate, it does not make it measured"
            )
        elif report["coverage"] < MIN_COVERAGE:
            report["status"] = "insufficient"
            report["message"] = (
                f"only {report['coverage'] * 100:.0f}% of the metric weight could be measured "
                f"(min {MIN_COVERAGE * 100:.0f}%) - treat the score as indicative, not a verdict"
            )
        elif unmet:
            report["status"] = "ok"
            report["message"] = f"score {report['score']} but band {band} - {label}: " + "; ".join(
                f"{f['metric']} {f['detail']}" for f in unmet
            )
        else:
            report["status"] = "ok"
            report["message"] = (
                f"score {report['score']} ({band} - {label}) as {article} {rubric.role}"
            )
        if report["status"] == "insufficient":
            # THE BAND IS THE VERDICT, and an insufficient review is not one.
            # This module's own rule - "if the report says insufficient, the
            # score is not a verdict" - was contradicted three lines up: the
            # band was computed and left populated, and `band` is the single
            # most likely field for a consumer to read. The score stays, because
            # the number is still the arithmetic of what WAS measured and
            # deleting it would hide the evidence; the one-word grade goes.
            report["band"] = None
            report["band_label"] = None

    try:
        report["findings"] = _build_findings(topo, report["metrics"], ladder, floors)
    except Exception as exc:
        report["findings"] = []
        report["findings_error"] = f"{type(exc).__name__}: {exc}"

    report["elapsed_s"] = round(time.time() - started, 2)
    return report


def config_from_spec(spec: dict | None) -> dict | None:
    """
    The "design_review" block of a loaded spec.json, or None when the part opts
    out (block absent, or "enabled": false). None means "do not review" - it is
    not the same as {} , which means "review with all the defaults".
    """
    if not isinstance(spec, dict):
        return None
    block = spec.get("design_review")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ValueError('spec.json "design_review" must be an object')
    if block.get("enabled") is False:
        return None
    return block


def review_step(path: str | Path, config: dict | None = None) -> dict:
    """Review an exported STEP file - the artifact, not the in-memory model."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"STEP file not found: {path}")
    shape = cq.importers.importStep(str(path)).val()
    return review_shape(shape, source=str(path), config=config)


# ---------------------------------------------------------------------------
# evaluate.py bridge
# ---------------------------------------------------------------------------
def design_review_checks(report: dict, config: dict | None = None) -> list[dict]:
    """
    Convert a review report into lib/evaluate.py-shaped check dicts:
    {id, status, severity, message, measured}.

    `config` is the spec.json "design" block ("design_review" is an accepted
    alias). Shape (every key optional):

        "design": {
          "enabled":        true,          # false skips the whole review
          "role":           "enclosure",   # enclosure|cover|plate|bracket|sheet|structural
          "min_score":      70,            # overall gate, 0-100
          "severity":       "soft",        # "hard" makes a low score fail the build
          "metric_severity":"soft",        # default severity for per-metric gates
          "symmetry_max_faces": 6000,      # cost guard; tripping it is an ERROR
          "waivers":  {"symmetry": "handed part - mirrored variant by design"},
          "metrics":  {                    # per-metric gates and switches
              "edge_break_coverage": {"min_score": 80, "severity": "hard"},
              "face_composition":    {"max_value": 0.35},
              "sharp_edge_length":   {"max_value": 120},
              "pattern_discipline":  {"enabled": false,
                                      "reason": "welded assembly, not bolted"}
          }
        }

    There is NO "weights" key and NO "style.radius_ladder" key: see
    RETIRED_CONFIG_KEYS. Writing either is an ERROR check, not a silent no-op.

    RUBRIC FLOORS override everything in this block. A floored metric cannot be
    waived or disabled, and a per-metric `min_score` below its floor is a config
    ERROR rather than a quietly-outranked number: the spec may raise a floor and
    cannot express lowering one. An unmet floor emits
    `design_review.floor.<id>` as a FAIL at the OVERALL severity - so whenever
    the design gate is hard the floor is hard - and `metric_severity` never
    reaches it. It also fails `design_review.score` and caps the reported band
    at FLOOR_BAND_CAP at EVERY severity, so an unmet floor can never read as a
    passing band even on an advisory review.

    Semantics: `min_score` gates the weighted overall score. Per-metric
    `min_score` gates that metric's 0-100 sub-score; `max_value` / `min_value`
    gate its RAW measurement (the "value" field, whose units differ per metric -
    a ratio for edge_break_coverage / face_composition / symmetry, mm for
    sharp_edge_length, an aspect for proportion). Per-metric gates can only ever
    make the bar HIGHER, which is why they need no reason.

    A `not_required` metric emits no check (the role excused it, or it was
    waived with a written reason). An `absent_defect` metric ALWAYS emits a FAIL
    naming the evidence - the geometry says the metric should apply and it does
    not, which is a defect, not an exemption. A metric that ERRORED always emits
    an ERROR check - a kernel failure never reads as a pass, and under the error
    invariant it also costs its full weight at zero.

    The same config dict goes to review_shape()/review_step(), which normalises
    it through _normalise_config(), so a caller passes one block to both and
    both reject exactly the same things.
    """
    config = config or {}
    if config.get("enabled") is False:
        return []
    checks: list[dict] = []
    metric_cfg = config.get("metrics") or {}
    default_sev = config.get("metric_severity", "soft")
    overall_sev = config.get("severity", "soft")

    if report.get("schema") != SCHEMA:
        return [
            {
                "id": "design_review",
                "status": ERROR,
                "severity": overall_sev,
                "message": f"unexpected report schema {report.get('schema')!r}",
                "measured": None,
            }
        ]

    if report.get("status") == "error":
        return [
            {
                "id": "design_review",
                "status": ERROR,
                "severity": overall_sev,
                "message": report.get("message", "review failed"),
                "measured": None,
            }
        ]

    # A rejected configuration key is a spec defect, and it is reported at the
    # OVERALL severity: a part that opted in to a hard gate and then wrote a key
    # that no longer exists has not opted in to anything.
    for i, err in enumerate(report.get("config_errors") or []):
        checks.append(
            {
                "id": f"design_review.config[{i}]",
                "status": ERROR,
                "severity": overall_sev,
                "message": f"design.{err['key']}: {err['message']}",
                "measured": None,
            }
        )

    if report.get("role_error"):
        checks.append(
            {
                "id": "design_review.role",
                "status": ERROR,
                "severity": overall_sev,
                "message": report["role_error"],
                "measured": None,
            }
        )

    # THE FLOORS.
    #
    # A floor is emitted at the OVERALL severity, never at `metric_severity`,
    # and the distinction is the whole point. `metric_severity` is the author
    # saying which METRICS matter to them, and "this metric does not matter to
    # me" is precisely the claim a floor exists to refuse - so it does not reach
    # one. `severity` is the author saying whether this build is gated on design
    # AT ALL, which is a different question and not the floor's to answer: the
    # repo's policy is that a part predating the gate reports its number and
    # warns rather than failing, and a floor must not retroactively break every
    # such part's build as a side effect.
    #
    # What this guarantees is the thing that was actually broken: WHENEVER THE
    # DESIGN GATE IS HARD, THE FLOOR IS HARD. The audit's part was clearing a
    # hard 70 gate, and it cannot any more. An advisory review still cannot
    # report a passing band either, because the band cap and the failing
    # `design_review.score` check below apply at every severity.
    unmet = [f for f in (report.get("floors") or []) if not f.get("met")]
    for f in unmet:
        checks.append(
            {
                "id": f"design_review.floor.{f['metric']}",
                "status": FAIL,
                "severity": overall_sev,
                "message": (
                    f"rubric floor unmet: {f['metric']} {f['detail']} - a minimum on a single "
                    f"metric that belongs to the rubric, not to this spec.json: it cannot be "
                    f"waived, disabled, lowered, renormalised out or averaged away. {f['why']}"
                ),
                "measured": f.get("score"),
            }
        )

    min_score = float(config.get("min_score", 0.0))
    score = report.get("score")
    if score is None or report.get("status") == "insufficient":
        checks.append(
            {
                "id": "design_review.score",
                "status": ERROR,
                "severity": overall_sev,
                "message": report.get("message", "score could not be established"),
                "measured": score,
            }
        )
    else:
        # An unmet floor fails the score check too. The floor check above
        # already fails the build, but a reader scanning the check list must
        # never see "refinement score 85.6 ... PASS" on a part with no broken
        # edge anywhere: the number is real and it is not the verdict.
        ok = score >= min_score and not unmet
        floor_note = (
            ""
            if not unmet
            else f" -- rubric floor unmet ({', '.join(f['metric'] for f in unmet)}), "
            f"band capped at {report.get('band')}"
        )
        checks.append(
            {
                "id": "design_review.score",
                "status": PASS if ok else FAIL,
                "severity": overall_sev,
                "message": (
                    f"refinement score {score} ({report.get('band')} - "
                    f"{report.get('band_label')}) as {_article(report.get('role'))} "
                    f"{report.get('role')}, threshold {min_score:g}{floor_note}"
                ),
                "measured": score,
            }
        )

    for mid, metric in sorted(report.get("metrics", {}).items()):
        cfg = metric_cfg.get(mid, {})
        sev = cfg.get("severity", default_sev)
        if metric["status"] == METRIC_ERROR:
            checks.append(
                {
                    "id": f"design_review.{mid}",
                    "status": ERROR,
                    "severity": sev,
                    "message": f"could not measure: {metric['message']}",
                    "measured": None,
                }
            )
            continue
        if metric["status"] == NOT_REQUIRED:
            continue
        if metric["status"] == ABSENT:
            checks.append(
                {
                    "id": f"design_review.{mid}",
                    "status": FAIL,
                    "severity": sev,
                    "message": f"absent where the geometry requires it: {metric['message']}",
                    "measured": metric.get("value"),
                }
            )
            continue
        failures = []
        if "min_score" in cfg and metric["score"] is not None:
            if metric["score"] < float(cfg["min_score"]):
                failures.append(f"sub-score {metric['score']:.0f} < {float(cfg['min_score']):g}")
        raw = metric.get("value")
        if raw is not None and isinstance(raw, (int, float)):
            if "max_value" in cfg and raw > float(cfg["max_value"]):
                failures.append(f"{raw} > max_value {float(cfg['max_value']):g}")
            if "min_value" in cfg and raw < float(cfg["min_value"]):
                failures.append(f"{raw} < min_value {float(cfg['min_value']):g}")
        if not failures and not cfg:
            continue  # no gate configured: informational only, keep the report lean
        checks.append(
            {
                "id": f"design_review.{mid}",
                "status": FAIL if failures else PASS,
                "severity": sev,
                "message": (
                    f"{metric['message']}" + (f" -- {'; '.join(failures)}" if failures else "")
                ),
                "measured": raw,
            }
        )

    return checks


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------
_STATUS_TEXT = {
    NOT_REQUIRED: "   n/r",
    ABSENT: "ABSENT",
    METRIC_ERROR: " ERROR",
}


def format_report(report: dict, top_findings: int = 8) -> str:
    lines: list[str] = []
    src = report.get("source") or "<in-memory shape>"
    lines.append(f"Design review  {src}   role: {report.get('role')}")
    for err in report.get("config_errors") or []:
        lines.append(f"  CONFIG ERROR: design.{err['key']}: {err['message']}")
    if report.get("role_error"):
        lines.append(f"  ROLE ERROR: {report['role_error']}")
    if report.get("status") == "error":
        lines.append(f"  ERROR: {report.get('message')}")
        return "\n".join(lines)

    s = report.get("shape", {})
    lines.append(
        f"  {s.get('solids')} solid(s), {s.get('faces')} faces, {s.get('edges')} edges, "
        f"bbox {s.get('bbox_size')} mm, {s.get('volume_mm3')} mm3"
    )
    if s.get("features_error"):
        lines.append(f"  WARNING: cylindrical feature extraction failed: {s['features_error']}")
    lines.append("")
    lines.append(f"  {'metric':<22}{'score':>7}  {'weight':>6}  detail")
    lines.append(f"  {'-' * 22}{'-' * 7}  {'-' * 6}  {'-' * 44}")
    weights = report.get("weights", {})
    for mid in METRIC_IDS:
        m = report["metrics"].get(mid)
        if m is None:
            continue
        if m["status"] == SCORED:
            score_txt = f"{m['score']:6.1f}"
        else:
            score_txt = _STATUS_TEXT.get(m["status"], "     ?")
        lines.append(f"  {mid:<22}{score_txt} {weights.get(mid, 0):>7.2f}  {m['message']}")

    lines.append("")
    if report.get("score") is None:
        lines.append(f"  OVERALL: unscored - {report.get('message')}")
    else:
        lines.append(
            f"  OVERALL {report['score']:.1f}/100  band {report['band']} "
            f"({report.get('band_label')})   measured weight {report['coverage'] * 100:.0f}%"
        )
        if report.get("status") == "insufficient":
            lines.append(f"  WARNING: {report['message']}")
    # Floors print whether or not they bite: a bar only visible when you fail it
    # is a bar nobody designs towards.
    floors = report.get("floors") or []
    if floors:
        met = [f for f in floors if f["met"]]
        unmet = [f for f in floors if not f["met"]]
        if met:
            lines.append(
                "  rubric floors met: " + ", ".join(f"{f['metric']} {f['detail']}" for f in met)
            )
        for f in unmet:
            lines.append(f"  RUBRIC FLOOR UNMET: {f['metric']} {f['detail']}")
        if unmet:
            lines.append(
                f"    band capped at {FLOOR_BAND_CAP} "
                f"(measured band {report.get('band_uncapped')}) - a floor is a hard minimum "
                f"on one metric and cannot be waived, disabled or averaged away"
            )
    cd = report.get("config_delta") or {}
    if cd.get("knobs"):
        lines.append(f"  configuration: {cd.get('message')}")
        if not cd.get("within_cap", True):
            lines.append(
                f"    CONFIG ERROR: {'; '.join(cd.get('over') or [])} - the verdict is a "
                f"statement about the spec.json, not about the part"
            )
    if report.get("absent"):
        lines.append(f"  absent where required: {', '.join(report['absent'])}")
    if report.get("errored"):
        lines.append(
            f"  unmeasured metrics (scored zero at full weight): {', '.join(report['errored'])}"
        )
    if report.get("excused"):
        lines.append(
            f"  excused by assertion ({report['excused_weight'] * 100:.0f}% of the rubric): "
            f"{', '.join(sorted(report['excused']))}"
        )
        if report.get("score_unexcused") is not None and report.get("score") is not None:
            lines.append(
                f"    the waivers are worth "
                f"{report['score'] - report['score_unexcused']:+.1f} points "
                f"(unexcused: {report['score_unexcused']:.1f})"
            )

    findings = report.get("findings") or []
    if findings:
        lines.append("")
        lines.append(f"  Findings ({len(findings)}):")
        for f in findings[:top_findings]:
            lines.append(f"   [{f['severity']:<6}] {f['message']}")
            if f.get("builder"):
                lines.append(f"            -> {f['builder']}")
        if len(findings) > top_findings:
            lines.append(f"   ... {len(findings) - top_findings} more (see --json)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m lib.design_review",
        description="Measure and score mechanical/visual refinement of a STEP artifact.",
    )
    ap.add_argument("step", help="STEP file to review")
    ap.add_argument("--json", dest="json_out", help="write the full report to this path")
    ap.add_argument(
        "--min-score", type=float, default=None, help="fail (exit 1) below this overall score"
    )
    ap.add_argument("--role", choices=ROLES, default=None, help="rubric to judge under")
    ap.add_argument("--config", help="JSON file holding the design_review config block")
    ap.add_argument("--top", type=int, default=8, help="findings to print (default 8)")
    ap.add_argument("--quiet", action="store_true", help="suppress the console report")
    args = ap.parse_args(argv)

    config: dict = {}
    if args.config:
        try:
            config = json.loads(Path(args.config).read_text())
        except Exception as exc:
            print(f"ERROR: could not read config {args.config}: {exc}", file=sys.stderr)
            return 2
        config = config.get("design", config.get("design_review", config))
    if args.min_score is not None:
        config["min_score"] = args.min_score
    if args.role is not None:
        config["role"] = args.role

    try:
        report = review_step(args.step, config=config)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(format_report(report, top_findings=args.top))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, default=str))
        if not args.quiet:
            print(f"\n  report -> {args.json_out}")

    if report.get("status") == "error" or report.get("score") is None:
        return 2
    threshold = config.get("min_score")
    if threshold is not None and report["score"] < float(threshold):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
