# The satin/fill classifier under boundary detail — eight cures measured, none adopted (2026-09-03)

Kent picked "classifier robust to boundary detail" after #330, on the
evidence from the curve flip: two borderline ribbons changed tier when only
their polygon's detail changed (a 12 × 3 mm drone ribbon satin → fill, a
meadow blob fill → satin), and the diagnosis at the time was skeleton spurs
off the refined boundary inflating the spine length. This is the record of
what a census of the real fixtures did to that diagnosis and to every cure
tried against it. **No engine change ships from this item**; the instrument
does (`tools/ribbon_stability.py`), and the result goes into DOCTRINE.

## 1. The instrument and the baseline

`tools/ribbon_stability.py` digitizes every fixture twice — the shipped
polygons, and the same art with the curve refinement ungated (the strongest
boundary-detail change the engine can make without touching the artwork) —
pairs shapes by id then centroid, and over the population the DT gates
actually judge (past the width cap and the aspect gate: 219 shapes across
the ten fixtures) reports the verdicts that differ. Today's classifier:

| fixture | DT population | flips shipped → refined | the shapes |
|---|---|---|---|
| drone (19 px/mm, gradient) | 70 | **2** | the 12 × 3 mm ribbon: `promoted_ribbon` → `dt_irregular` (`explained` 0.83 → 0.70); a 0.85 mm shape: `satin` → `aspect` |
| gaulke (16, gradient) | 51 | **2** | 0.92 mm: `satin` → `dt_irregular`; 0.85 mm: `dt_irregular` → `satin` (cv across 0.5) |
| meadow (10, photo) | 17 | **1** | the 2.4 mm blob: `dt_irregular` → `satin` (cv 0.53 → 0.48) |
| Fremont, ENTHUSIAST, Becker, sunset, whitebg, alpha, ribbon | 81 | 0 | |

Five flips in 219. Four of them are shapes sitting on a threshold — the
regularity edge (cv 0.5), the aspect gate (3 widths), the promotion floor
(`explained` 0.80) — where any perturbation flips a coin; one (the drone
ribbon) is the spur-inflation mechanism the item was priced on.

## 2. Eight cures in five families, measured the same way

Every variant is scored on two numbers: the flips it leaves, and the
shipped verdicts it changes on the polygons as they are today (the cost of
adopting it). The four letterform archetypes and the serrated disc from
`tests/test_satin` are checked alongside.

| variant | flips (today 5) | shipped verdicts changed | archetypes / serrated disc |
|---|---|---|---|
| prune spurs shorter than 1× the junction radius, measure the rest | 8 | 2 | hold |
| … 1.5× | 4 | 12 | hold |
| … 2× | 3 | 16 | hold |
| the sewing spur rule (`_prune_spurs`, 1.6 half-widths, iterated) | 6 | 4 | hold |
| hybrid: regularity and p90 on the full skeleton, spine length on the sewing-pruned one | 6 | 2 | hold |
| smooth the classifier's raster (open + close) by 1 px, then thin | 7 | 18 | hold |
| … 2 px | 12 | 48 | **BAR and T fall to fill** |
| a margin band on the regularity edge (cv 0.45–0.55) where the promotion rule decides both ways | 6 | 15 (every one a small satin shape with elongation under 10, demoted) | hold |

Why pruning fails: on a compact or irregular shape the "spurs" ARE the
medial axis. Pruning collapses the spine, `explained` explodes (0.9 → 2–19)
and the radius spread of what is left reads *regular* — so the shape walks
into satin through the ordinary path, which has no elongation guard
(`Se744e0bc` on drone: 0.70 mm wide, `explained` 19.6, elongation 0.1,
verdict `satin`). The blob detector depends on the whole skeleton. And even
the hybrid, which keeps the blob detector intact, leaves the drone ribbon
flipping: its extra 17% of spine under the refined boundary is not short
spurs — the sewing rule prunes nothing that matters there.

Why the band fails: it moves the knife edge to the band's two edges and
demotes every small satin shape whose elongation is under the promotion
floor — fifteen shipped verdicts on six fixtures — for one more flip, not
one fewer. A margin needs a memory to be a margin.

Why smoothing fails: the classifier's raster is adaptive, about eight pixels
across the wall (`_rasterize`), so a one- or two-pixel morphological radius
is 12–25% of the wall. It moves every shape's radii, not just the noisy
ones. A smoothing radius would also be exactly the new constant DOCTRINE's
standing ruling on smoothing warns against.

## 3. What this leaves

The classifier's sensitivity to boundary detail is intrinsic to hard
thresholds on 1-px-skeleton statistics: cv, `explained` and aspect each
move by ~0.05–0.1 when the boundary gains detail, and a shape within that
of a threshold flips. Every cure that changed the statistics changed
shipped verdicts on 2–48 shapes for a flip count of 3–12 against 5. The one
mitigation that works is the one already shipped: not feeding the
classifier boundary detail (`_CURVE_MIN_PX_PER_MM`, #330).

What would work is a different construction, not a tuning: a verdict with a
margin (e.g. a shape within ±0.05 of the regularity edge takes the tier of
the shape it was in the last run — impossible for a single digitize) or a
classifier that does not rasterize (a polygon-native width profile). Both
are Kent's call and neither is a session.

## 4. Provenance

The promotion thresholds (0.80 / 1.25 / 10) were tuned on Kent's 15-design
customer corpus (`scratch_kent`, gitignored), which this checkout does not
have — so no variant here re-tuned them, and none could have been adopted
without that sweep. The ten fixtures are the population this record is
measured on; the corpus would widen it, not change the mechanism.
