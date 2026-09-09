# Automated design-review audit

Audit applies to the first exported snap v1 files reviewed on 2026-09-08. Re-run reports after any later geometry change. No scoring library, weights, roles (except the physically appropriate cover role for cover-only inspection), or geometry were modified by this audit.

| Export | Automatic score | Report |
| --- | ---: | --- |
| Original Opus5 TX v2 assembly | 44.0 | baseline_review.json |
| Snap v1 assembly | 47.2 | design_review.json |
| Snap v1 base alone | 43.5 | base_review.json |
| Snap v1 cover alone, cover role | 39.3 | cover_review.json |

These are heuristic geometry scores, not mechanical validation. Original feature composition was unmeasured (32% of feature population unclassified), contributing zero; therefore the overall score difference is not an unqualified measurement of improvement.

## Confirmed limitations

1. **Frame estimate contaminates symmetry.** The assembly estimated axes tilt about 0.084 degrees from its known modelling axes; the base tilt is about 0.167 degrees. Reusing the same exported solids and the same symmetry function with a diagnostic frame on the exact installed axes changes assembly symmetry from 0.0 to 84.0, with 2.76% asymmetric volume and 17.6% slender extent on its best plane. Base symmetry changes from 21.76 to 85.95. Cover symmetry stays 76.69 because its estimated axes are already exact. This demonstrates substantial sensitivity to the chosen frame and subsequent near-coincident Boolean cuts. It does not justify changing the geometry or silently substituting an overall score. See symmetry_audit.json.
2. **Best plane wording when all scores are zero.** The automatic assembly report names Y as best with 80.7% asymmetric volume, even though Z has 23.0%. All three planes saturate at a zero score, and first-entry tie order selects Y. The report is selecting best score, not smallest difference volume.
3. **Snap cover fastening is outside the hole-pattern rubric.** Cover pattern discipline returns zero and says there is no way to fasten the cover because there are no holes. The modeled cover is retained by two fixed hooks and two flexible hooks. Adding screw holes for this score would contradict the design intent.
4. **Feature families include non-fastener geometry.** Cover relief/text/curved boundaries contribute apparent feature centers (including D90.1), which are not a meaningful fastener pattern. Module pilots, mounting holes, front connector holes, tie anchors and drains are independent functional families; they should not be equalized to improve a score.
5. **Open-part/assembly visibility differs.** Base-only inspection exposes rim and partition crests; cover-only face composition penalizes the broad flat underside. The latter does not justify adding material that can collide with modules or fibers.

## Useful low-risk geometry findings

- Review small edge breaks (0.4-0.6 mm where stock permits) on exposed inner tray rim/partition crests and mounting-ear outside edges. They are touched during installation or cable routing. Preserve flat module support pads, mounting bores, and snap retention surfaces. Automatic 1 mm blanket suggestions are too broad for thin functional details.
- The base has significant measured unbroken convex edge length (1173 mm); it should not be dismissed entirely as a scorer problem. Inspect the cited edges in context and treat sharp edges near fiber routing as higher priority than hidden edge decoration.
- Retain the framed lid, controlled edge vocabulary and aligned visible interfaces. The new assembly radius vocabulary score is 96.75 versus original 47.87, although a print and visual inspection remain the practical confirmation.
- Maintain intentional latch/release asymmetry; do not mirror functional snap beams merely to increase symmetry.

No new holes, ribs, or reliefs should be added purely to satisfy the heuristic. Fit, snap travel, clearances, thermal provisions, connector qualification, and prototype cycle tests remain independent release criteria.
