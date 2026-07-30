"""
The adversarial corpus, as a test.

tests/design_corpus.py builds a labelled set of solids whose RELATIVE quality
is known by construction and states the ordering contract any honest
refinement scorer must satisfy. This file is the pytest face of it: one
module-scoped run of the whole corpus, then one test per contract item, so a
failure names the specific relation that broke instead of one opaque assert.

The contract, not the numbers, is the invariant. Absolute scores will move
every time lib/design_review.py is reworked; if a test here starts failing,
the question is always "is the ordering still right", never "did the number
change".

Cost: the corpus caches each case as a STEP under tmp/design_corpus/ and each
review as JSON keyed by the hash of that STEP AND the hash of
lib/design_review.py. A run after an unrelated edit reuses everything; a run
after a scorer edit re-scores everything, which is the point.

Set DESIGN_CORPUS=fast to skip the cases marked slow (the two blobs and the
real artifacts). The real-part ordering then reports as unevaluated rather
than as a pass - a contract that could not be judged never counts as held.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.design_corpus import (  # noqa: E402
    CASES,
    CLASSES,
    GATE,
    MARGIN,
    ROLES,
    check_contract,
    format_contract,
    format_table,
    run_corpus,
    select,
)

FAST = os.environ.get("DESIGN_CORPUS", "").lower() == "fast"


@pytest.fixture(scope="module")
def corpus():
    """Build, export, re-import, review and judge every selected case once."""
    result = run_corpus(select(fast=FAST))
    print("\n" + format_table(result) + "\n\n" + format_contract(result))
    return result


def _item(result, cid):
    return next(c for c in result.contract if c.id == cid)


def _assert(result, cid):
    c = _item(result, cid)
    if c.ok is None:
        pytest.skip(f"{cid} could not be evaluated: {c.detail}")
    assert c.ok, f"{c.title}\n  {c.detail}"


# ---------------------------------------------------------------------------
# the corpus itself
# ---------------------------------------------------------------------------
def test_every_case_is_well_formed():
    """Ids unique, classes and roles known, and every class populated."""
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids)), "duplicate case id"
    assert {c.klass for c in CASES} == set(CLASSES)
    assert {c.role for c in CASES} <= set(ROLES)
    for c in CASES:
        assert c.why.strip(), f"{c.id} has no note saying why it is {c.klass}"


def test_every_role_has_a_good_reference():
    """
    Each role's rubric needs a part that defines what 'good' means for it.

    Without one, a role could be added to lib/design_review.py and tuned until
    it passes something - which is the failure this whole file exists to stop.
    """
    covered = {c.role for c in CASES if c.klass == "good"}
    assert covered == set(ROLES), f"roles with no good reference: {set(ROLES) - covered}"


def test_the_ladder_is_a_complete_chain():
    rungs = sorted(c.rung for c in CASES if c.rung)
    assert rungs == list(range(1, len(rungs) + 1))


def test_every_gamed_case_names_the_metric_it_attacks():
    for c in CASES:
        if c.klass == "gamed":
            assert c.attacks, f"{c.id} does not say which metric it games"


# ---------------------------------------------------------------------------
# the ordering contract
# ---------------------------------------------------------------------------
def test_every_case_produces_a_score(corpus):
    """A case that errors means the review broke, not that the part is bad."""
    _assert(corpus, "all_cases_scored")


def test_the_refinement_ladder_is_monotonic(corpus):
    """Each rung adds one move and removes nothing, so each must score higher."""
    _assert(corpus, "ladder_monotonic")


def test_the_plain_sharp_box_is_the_floor(corpus):
    _assert(corpus, "base_is_floor")


def test_no_gamed_case_reaches_the_advisory_gate(corpus):
    """The audit's headline failure: a blob cleared 70.0 and shipped as an A."""
    _assert(corpus, "gamed_below_gate")


def test_every_good_case_clears_the_gate_under_its_own_role(corpus):
    """A cover, a plate and a sheet bracket are not failed enclosures."""
    _assert(corpus, "good_clears_gate")


def test_gamed_cases_score_below_good_cases(corpus):
    _assert(corpus, "gamed_below_good")


def test_crude_cases_score_below_good_cases(corpus):
    _assert(corpus, "crude_below_good")


def test_no_gamed_case_outranks_the_exemplar(corpus):
    _assert(corpus, "gamed_below_exemplar")


def test_the_real_part_ordering_holds(corpus):
    """
    The exemplar leads every other real part, and none of the others passes.

    Re-baselined 2026-07-25: this used to assert a total order over three real
    parts, two of which are draft-grade. See the comment at contract item 8 in
    tests/design_corpus.py for what was asserted, why it was not an invariant,
    and what replaced it.
    """
    _assert(corpus, "real_ordering")


# ---------------------------------------------------------------------------
# the contract machinery itself - it must be able to fail
# ---------------------------------------------------------------------------
def test_the_contract_detects_an_inverted_ordering(corpus):
    """
    A fixture that cannot fail proves nothing, so invert one score and check
    that the contract notices.
    """
    import copy

    rows = copy.deepcopy(corpus.rows)
    gamed = [r for r in rows if r.case.klass == "gamed" and r.ok]
    if not gamed:
        pytest.skip("no gamed case scored")
    gamed[0].score = 99.0
    results = {c.id: c for c in check_contract(rows, margin=MARGIN, gate=GATE)}
    assert results["gamed_below_gate"].ok is False
    assert results["gamed_below_good"].ok is False


def test_a_case_that_cannot_be_built_is_reported_not_skipped(corpus):
    """`missing` is a distinct status, and it never counts as a pass."""
    missing = [r for r in corpus.rows if r.status == "missing"]
    for r in missing:
        assert r.score is None
        assert r.message, f"{r.id} is missing with no explanation"


# ---------------------------------------------------------------------------
# scorer robustness - a degeneracy must never be answered with a score
# ---------------------------------------------------------------------------
def test_a_perfectly_symmetric_solid_is_not_scored_asymmetric(tmp_path):
    """
    Regression guard, found while building this corpus.

    probe_exactly_symmetric_solid() is symmetric about y = 0 to the last bit -
    mirroring it about y = 0 leaves 0.000000 mm3 - but after the STEP round
    trip that every review does, OCC puts its centroid at y = +4.0e-07.
    lib/design_review._metric_symmetry mirrors about a plane through that
    centroid, and differencing a solid against its own 0.4 micron mirror is a
    degenerate boolean: it hands back most or all of the volume.

    Measured 2026-07-25 on this exact solid: in memory (centroid y = -2.6e-08)
    the metric scores 100.0; re-imported from its own STEP (centroid y =
    +4.0e-07) it scores 0.0, and the reported per-axis figure was not even
    stable between runs (1.0, then 0.5). Same part, opposite verdicts, and the
    re-imported one is the artifact that ships.

    Whatever the scorer does about this, the worst possible score is not it: a
    degeneracy is an ERROR, per the module's own stated safety property.

    THIS ASSERTION USED TO BE VACUOUS, which is worse than not having it. It
    read `metric["status"] != "ok" or metric["score"] > 50.0`, and "ok" is the
    REPORT-level status - a METRIC status is only "scored", "not_required" or
    "error", so the left operand was True for every possible input and the test
    passed unconditionally, including against the exact defect it names. The
    second half of the test below re-runs the OLD centroid-mirroring behaviour
    and asserts that the fixed assertion CATCHES it, so a guard that cannot fail
    can never sit here again.
    """
    import math

    import cadquery as cq

    import lib.design_review as dr
    from tests.design_corpus import probe_exactly_symmetric_solid

    shape = probe_exactly_symmetric_solid().val()
    mirrored = shape.mirror("XZ", (0.0, 0.0, 0.0))
    asymmetric = sum(abs(s.Volume()) for s in mirrored.cut(shape).Solids())
    assert asymmetric < 1e-6, "the probe is supposed to be exactly symmetric"

    # reviews read the exported artifact, never the in-memory object, and the
    # round trip is what moves the centroid - so the guard must round-trip too
    path = tmp_path / "symmetric_probe.step"
    cq.exporters.export(shape, str(path))
    reimported = cq.importers.importStep(str(path)).val()

    def verdict(metric: dict) -> bool:
        """The guard itself, so both halves of the test apply the same rule."""
        return metric["status"] != dr.SCORED or metric["score"] > 50.0

    metric = dr._metric_symmetry(reimported)
    assert metric["status"] in (dr.SCORED, dr.METRIC_ERROR), metric["status"]
    assert verdict(metric), (
        f"a perfectly symmetric solid scored symmetry {metric['score']} "
        f"({metric['message']}) - a degenerate mirror boolean is being reported "
        f"as a measurement"
    )

    # -- and now prove the guard can fail ----------------------------------
    # The old code mirrored about the CENTROID. Reproduce exactly that on the
    # same round-tripped solid and check the assertion above would have caught
    # it. If this ever stops failing, the assertion has gone vacuous again.
    centre = reimported.Center()
    assert abs(centre.y) > 1e-9, "the round trip is supposed to move the centroid off y = 0"
    old_scores = []
    for plane, axis in (("YZ", 0), ("XZ", 1), ("XY", 2)):
        try:
            vol, extent, _raw = dr._mirror_difference(
                reimported, reimported.mirror(plane, centre.toTuple())
            )
        except Exception:
            continue
        diag = math.sqrt(sum(d * d for d in dr.Topology(reimported).bbox_size()))
        old_scores.append(
            min(
                dr._lerp_score(vol / (2.0 * abs(reimported.Volume())), best=0.01, worst=0.12),
                dr._lerp_score(extent / diag if diag > 1e-9 else 0.0, best=0.15, worst=0.75),
            )
        )
    assert old_scores, "the centroid-mirroring reproduction did not run at all"
    old_metric = {"status": dr.SCORED, "score": max(old_scores)}
    assert not verdict(old_metric), (
        f"the centroid-mirroring behaviour this test guards against now scores "
        f"{max(old_scores):.1f} - either OCC changed or the guard is vacuous again"
    )


# ---------------------------------------------------------------------------
# the class the corpus did not cover, and the defect that shipped because of it
# ---------------------------------------------------------------------------
def test_the_turned_class_is_adversarially_covered():
    """
    A part class with no ADVERSARY in the corpus is a class nothing is testing.

    Every gamed case here used to be a prism, so nothing ever asked what a body
    of revolution could get for free - and the answer was face_composition, at
    its full 0.19 weight, for a metric that read planar faces only and could
    not see a barrel at all. This asserts the gap is closed as a matter of
    corpus SHAPE, not just as a score: the turned class now has a reference at
    the top, a crude case at the bottom and an adversary aimed at the metric
    that missed it.
    """
    turned = {c.id: c for c in CASES if "turned" in c.id}
    by_class: dict[str, set[str]] = {}
    for c in turned.values():
        by_class.setdefault(c.klass, set()).add(c.id)
    assert by_class.get("good"), "the turned class has no reference"
    assert by_class.get("crude"), "the turned class has no floor"
    assert by_class.get("gamed"), "the turned class has no adversary"
    attacked = {m for c in turned.values() if c.klass == "gamed" for m in c.attacks}
    assert "face_composition" in attacked, (
        "the turned adversary must aim at the metric a curved surface used to hide from"
    )


def test_the_turned_adversary_is_held_by_the_gate_contract(corpus):
    """
    gamed_turned_blank_tube measured 77.3/B before face_composition could
    develop a curved face - OVER the 70.0 advisory gate, on a bored bar with
    one blanket .fillet(1.0) and nothing else. It is in the corpus so that can
    never be true again silently, and this pins it to the contract rather than
    to a number.
    """
    row = next((r for r in corpus.rows if r.id == "gamed_turned_blank_tube"), None)
    if row is None or not row.ok:
        pytest.skip("gamed_turned_blank_tube was not scored in this selection")
    assert row.score < GATE, f"the turned adversary clears the gate at {row.score}"
    goods = [r for r in corpus.rows if r.ok and r.case.klass == "good"]
    assert goods, "no good case scored"
    assert row.score + MARGIN <= min(r.score for r in goods), (
        f"the turned adversary at {row.score} is within {MARGIN} of a good part"
    )
    # and it fails on the metric it attacks, not on a technicality
    assert row.metrics.get("face_composition") is not None
    assert row.metrics["face_composition"] < 10.0, row.metrics


# ---------------------------------------------------------------------------
# richness must not be mistaken for incoherence
# ---------------------------------------------------------------------------
def test_the_corpus_holds_both_poles_of_the_plain_versus_rich_comparison():
    """
    A corpus of adversaries alone cannot catch a gate that rewards PLAINNESS.

    Every gamed case here is a part pretending to be better than it is. None of
    them asks the opposite question - whether an honest, plain, tidy part can
    outrank an honest, rich, mechanical one - and for a while the answer was
    yes. So both poles are corpus members and both are real artifacts, not
    fixtures: the scaffold `make new-part` hands out, and the exemplar the skill
    tells agents to copy.
    """
    ids = {c.id for c in CASES}
    assert {"good_scaffold_template", "real_reference_mast_node"} <= ids


def test_the_rich_exemplar_outranks_the_plain_scaffold(corpus):
    """
    The acceptance test for the 2026-07-26 rework of radius_vocabulary and
    symmetry, kept as a contract rather than as a paragraph in a report.

    Measured before: scaffold 85.9, exemplar 83.1, and the +2.80 decomposed
    almost entirely into the two metrics that were measuring the wrong
    construct - radius_vocabulary +4.75 to the scaffold (48.5 against 91.7, for
    holding 10 correct sizes against 5) and symmetry +1.72 (75.5 against 100,
    for having a connector bay). Both parts pass the gate and both deserve to,
    so what is asserted is the ORDER and not a margin: claiming five points
    between two good enclosures would be false precision, and the honest
    statement is that the part built from a fin bank, a gasket land, a
    connector bay and a stepped seal must not sit below a rounded case with
    decorative grooves.
    """
    rows = {r.id: r for r in corpus.rows}
    scaffold = rows.get("good_scaffold_template")
    exemplar = rows.get("real_reference_mast_node")
    if not scaffold or not exemplar or not (scaffold.ok and exemplar.ok):
        pytest.skip("one of the two real artifacts was not scored in this selection")
    assert scaffold.score >= GATE, f"the scaffold must still pass: {scaffold.score}"
    assert exemplar.score > scaffold.score, (
        f"the scaffold ({scaffold.score}) outranks the exemplar ({exemplar.score}) - the gate "
        f"is paying for plainness again. Per-metric: "
        f"{ {k: (scaffold.metrics.get(k), exemplar.metrics.get(k)) for k in scaffold.metrics} }"
    )
    # ... and for the right reason, on both of the metrics that were rebuilt
    for mid in ("radius_vocabulary", "symmetry"):
        assert exemplar.metrics.get(mid) is not None, mid
        assert exemplar.metrics[mid] >= 90.0, (
            f"the exemplar scores {exemplar.metrics[mid]} on {mid}; it draws 97% of its break "
            f"area from this repo's own ladder and is 0.9% asymmetric about its free plane, so "
            f"a low number here is the metric being wrong about the part again"
        )
