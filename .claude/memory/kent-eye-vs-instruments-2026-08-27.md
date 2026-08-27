# Kent's eye vs the instruments — 2026-08-27

Full record with his fourteen notes verbatim: `docs/kent-review-2026-08-27.md`.
This entry is the decisions and the traps.

## The calibration datum

Kent put the stitch-outs at **60% of the way to Ember parity**. On the same
designs `artfidelity_self` averaged **83.7** and `preflight` **80.0**, and those
two correlate with each other at only **rho = 0.405**.

**ARTFID is a fidelity score and must never be quoted as a quality
percentage.** It measures whether thread is where the ink is, in the right
colour, in the right shape. It is structurally blind to craft — satin angle,
underlay, pull compensation, fragmentation, trims. The gap between 83.7 and 60
is not optimism, it is a different question.

This repo already learned the same thing on lettering
(`letterform-fidelity-2026-08-26.md`): *"a wrong-angle letter scores a perfect
IoU"*, and bare-fabric coverage graded a visibly deformed H at "1.9% bare,
fine". Kent independently arrived at the same split in his own words:
**"Shapes are accurate but smoothness is not."**

**Consequence for ROADMAP phase 1.** Its exit condition is "the metric's
ranking agrees with Kent's visual ranking". If his ranking is partly driven by
craft and the metric cannot see craft, no reweighting of
coverage/colour/structure reaches agreement in general — it would only agree
where fidelity and craft happen to move together. Worth knowing before more
effort goes into tuning weights.

## What he named, and what could see it

Two themes, and **both matter to him about equally** (his ruling, asked
directly):

1. **Smoothness — 8 of 14 designs.** Itself TWO complaints: edge noise
   ("sawtoothed and jaged") and curve fidelity ("lines/circles are not smooth
   like the photo" — a curve sewn as a polygon).
2. **Whole elements missing — 7 of 14.** Both designs he marked "out of place"
   are the two that lost an element.

`preflight.ARTWORK_UNCOVERED` fired on **one** of those seven and reported
`0.0 mm2` on the rest, with `uncovered_checked: True` — it ran and saw nothing.
Its own message says why: the area it measures is *"claimed by a shape the
design sews"*, so an element dropped before stage 3 ever made a region has no
shape to be uncovered. It correctly caught becker_marine's C infill (18.8 mm2),
which IS inside an existing shape.

## Two instruments built

**`tools/dropped_elements.py` — works.** `gaulke_roofing` reads 99.1% lost
against Kent's independent "the logo is 5% completed at most"; `enthusiast`
reads 24.6% against a limb he can see is gone. 13 tests.

Three definitions of "element" failed first, and the pattern is the
transferable part — **each looked correct until it was run against a design
Kent had already said was broken**:
  1. connected ink components — merges a red arm into the shield it touches;
     on alpha-keyed art the whole badge is one blob. Reported ZERO lost.
  2. ink plus enclosed ground — that shield's hexagon has BREAKS, so its
     interior white reaches the frame edge and no flood test calls it enclosed.
  3. whole-frame colour components — the background becomes ONE component and
     a median over it hides a small filled-in patch entirely.
What works: **segment the disagreement, not the artwork.** Per-pixel first,
components second — the same ordering lesson as `artfidelity_self`'s colour
component, where taking medians before the subtraction produced a metric that
could not fire at all.

**`tools/edge_smoothness.py` — half works.** `ragged_mm` (standard deviation of
boundary distance) measures edge noise. Its narrow 0.131-0.217 spread looked
like failure until Kent confirmed **`logo_alpha`, the only control, is "a bit
rough too"** — so the spread is probably right and what is missing is a BAR,
not a different metric.

Curve fidelity was built and **rejected, with a measurement**: turning
concentration cannot work on a raster. A rasterised 20 mm circle reads MORE
angular than a 40-gon at every resample step tested (0.5/1.0/2.0/3.0 mm), and
non-monotonically, because a raster boundary is itself a staircase — the raster
IS a polygon. The table is in that file's docstring; the code was deleted
rather than shipped.

## The trap that cost the most time

**Measuring pictures of stitches instead of the stitches.** Curve fidelity has
to read `plan.iter_runs()` — the vertices the machine actually sews, where a
20-gon has 20 of them — not a render. The same suspicion applies to
`ragged_mm`'s floor: `stitchviz` draws individual filaments, so every
stitch-out is furry at 0.1 mm/px and that texture may be the floor the real
signal sits on. **That is the next instrument, and it is a different INPUT, not
a different threshold.**

## Instruments contaminate each other — clip deliberately

`dropped_elements` opens away a 0.5 mm boundary band so a halo around every
shape cannot swamp lost elements. `edge_smoothness` clips to a 1.0 mm band so a
lost element cannot masquerade as a rough edge — measured: becker_marine's lost
C infill sits 3.32 mm out (Hausdorff, vs 0.7-1.0 mm for every other flat
design) and alone drove that design to the TOP of the raggedness ranking while
its perimeter ratio was the LOWEST of five. Two instruments on one boundary
need explicit scope or they measure each other.

## Two engine defects, neither fixed

1. **`summit_badge`'s background is half removed** — stage 1 strips the
   vignette's corners and sews the rest as a grey blob. Kent's "it's half
   missing" is right. **PR #276's body claims "the engine is correct at the
   shipped 6.0" — that sentence is wrong**; the instrument fix in that PR
   stands regardless.
2. **`stage1_prep.py:254-266`** computes `agreement` from `close`, which comes
   from `bg_tolerance_lab` — so the `BACKGROUND_ABSENT` gate (0.75) trips more
   easily the stricter the tolerance. Crossed between 4.5 (0.7454, nothing
   floods) and 4.8 (0.7687, floods 24%). Not what the comment there claims.

## Settled

* **`bg_tolerance_lab`: nothing to apply.** No stable optimum over 3.0-8.0;
  deltas `+4.83, +2.43, +4.51, +0.06, 0, +1.22, +1.30`, non-monotonic, with
  99.5%+ of every delta from two fixtures. The lost session's "6.0 -> 4.5 =
  +4.28" was the metric being wrong, not the engine improving.
* **`region_blobs` stays in the ranked set** (Kent): "hard cases matter" —
  dropping what we do worst on is how a fixture set becomes flattering.

## Still open

* Where `becker_marine` and `enthusiast_logo` should actually rank. He marked
  both out of place, not where they belong.
* The composite weights (0.40/0.25/0.35) stay provisional — they reproduce the
  table they were solved from and nothing else.

## The validation artifact self-republishes

`claude.ai/code/artifact/b313a4a6-5089-45ad-a2b2-815c142b1c85` saves Kent's
notes by publishing a new version of itself. **Never republish it from a script
or a scheduled check-in — that overwrites whatever he has written.** Read it
(`action: "read"`, the notes are in the page's `DATA` constant), do not write
it unless he asked for a rebuild.
