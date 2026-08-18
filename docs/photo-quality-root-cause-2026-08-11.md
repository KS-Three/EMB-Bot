# Photo/gradient quality — root cause, not segmentation

**Date:** 2026-08-11 · **Scope:** why `drone_render.png`, `summit_badge.png`, and
`repro_gradient_white_icon.png` score low on `digitizer/tools/corpus_scorecard.py`,
and what actually fixes each one.

**Context:** this investigation was launched to scope a "raise photo/gradient
quality to 50/100" effort. The working assumption going in was that a
segmentation upgrade (SAM2, see `docs/sam2-segmentation-live-acceptance-
2026-08-10.md`) would be the fix. It isn't — none of these fixtures even
route through SAM2's eligible pipeline lane, and a segmentation upgrade
already shipped for the lane they DO use (PR #45, SLIC+RAG replacing k-means
for the `gradient` class) without moving their grade. Read this doc before
spending more effort assuming segmentation is the bottleneck here.

## Correction to a stale MASTER_SCOPE.md claim

`MASTER_SCOPE.md` states "the F/0 scores on `drone_render.png`,
`repro_gradient_white_icon.png` and `summit_badge.png` are real." That's
wrong for `repro_gradient_white_icon.png`, which is **D/58** in both configs,
not F/0. Only `drone_render.png` is literally F/0 at both configs;
`summit_badge.png` is F-grade at both but only 0 at one config (10 at the
other). Worth fixing that claim separately — treat the numbers in the table
below as ground truth.

## Classification: all three are "gradient," none are photo_subject/photo_scene

`stage0_classify.classify()` confidence 1.00 on all three:
- `drone_render.png` → `gradient`
- `summit_badge.png` → `gradient`
- `repro_gradient_white_icon.png` → `gradient`

`pipeline.py`'s stage-2 dispatch sends `photo_subject`/`photo_scene`/`gradient`
all through `stage2_photo_segment` (SLIC+RAG) — but SAM2 (per its own locked
scoping) only ever engages for `photo_subject`/`photo_scene`. **None of these
three fixtures would ever reach SAM2, regardless of how good SAM2 is.**

## Per-fixture findings

| fixture | hat_front | left_chest | dominant cost |
|---|---|---|---|
| `drone_render.png` | F, 0 | F, 0 | `max_colors=12` cap forces bad merges (chart has good matches, ceiling doesn't let it use them) |
| `summit_badge.png` | F, 10 | F, 0 | segmentation-merge chaining upstream of palette selection — NOT a palette bug |
| `repro_gradient_white_icon.png` | D, 58 | D, 58 | thread-chart matching (worst ΔE in corpus) + a genuinely new bug: thin-sliver color/geometry desync |

### `drone_render.png` — config/algorithm fix, cheap

`select_palette` (chart-restricted weighted k-medoids, `digitizer_core/palette.py`)
hits `colors == 12 == cfg.max_colors` — the cap binds before its own excess-ΔE
target (4.5) is satisfied (`max_excess_de00=7.599`). Traced the two
worst-offending regions: both have excellent chart spools available
(`floor=1.98`/`1.51` ΔE00 — e.g. Isacord "Silver" 204,204,204) but the
area-weighted objective doesn't spend one of only 12 medoid slots on them, so
they force-merge onto "Armour" (105,104,91) at ΔE 9.10-9.18 — matches
preflight's reported worst 9.2 exactly.

**Fix:** raise `max_colors` past 12 (chart is Isacord, 398 threads, ample
headroom) or make the BUILD stop rule floor-aware — never let the cap discard
a candidate whose own `floor` is very low (e.g. &lt;3 ΔE00) in favor of a
large-area region that's already well served.

### `summit_badge.png` — segmentation fix, NOT palette.py

This one is NOT a palette bug. Traced the actual worst-match region (17.3mm²,
biggest region carrying thread `0108 Cobblestone`): internal Lab spread is
`b` ranging -14 to +15 across the region — a smooth, continuous ~29-unit
swing, a genuine blue-to-warm metallic sheen sitting inside ONE stage-2
region. This is a hierarchical-RAG-merge chaining artifact: adjacent SLIC
superpixels along a real gradient merged repeatedly (`MERGE_DELTAE00_THRESH`-
gated, in `stage2_photo_segment.py`, BEFORE `select_palette` ever runs) because
each pairwise step looked locally similar enough. The region's *mean* Lab
(≈64.1, 5.5, 0.4) looks near-neutral because the gradient's two ends roughly
cancel — `select_palette` then correctly matches that mean (ΔE 7.00,
reasonable given the input), but the input itself was too coarse.

Preflight's reported worst value (14.8, thread "Cobblestone" vs.
`artwork_rgb=[183,157,178]`) is worse still: that `artwork_rgb` is a
per-channel INDEPENDENT median over the pooled pixel population of all 8
regions sharing the thread (`preflight.py`'s `_artwork_colors_by_thread`) — a
synthetic color no actual pixel carries, since medians taken independently
per channel across two visually distinct color families don't correspond to
any real sample.

**Fix:** `MERGE_DELTAE00_THRESH` or the RAG hierarchical-merge stopping rule
needs to detect within-region gradient chaining — e.g. cap merge on
region-internal Lab spread, not just pairwise adjacent-superpixel distance —
so the metallic sheen splits into 2-3 sub-regions before `select_palette`
ever runs.

### `repro_gradient_white_icon.png` — a genuinely new bug class

Only ONE final region carries the worst-match thread (`2560 Azalea Pink` vs.
`artwork_rgb=[255,255,255]`, ΔE 23.9 — worst in the whole 14-fixture corpus):
a thin sliver, ~1.95mm × 11.7mm (2·area/perimeter ≈ 1.27mm wide). At
segmentation time this sliver's mean Lab was genuinely `(80.2, 25.1, 4.1)` — a
real pinkish-white anti-alias blend between the white icon and an adjacent
fuchsia gradient band. `select_palette` matched it well (near-zero excess —
Azalea Pink IS an excellent match for that Lab value). **The bug is
downstream**: by the time this sliver became a final vectorized/simplified
stitch-plan polygon (`simplify_tol_mm=0.2mm` + small-shape handling), its
outline drifted enough — a fraction of a millimetre, large relative to a
~1.3-2mm-wide ring — that it now sits mostly over the solid white icon
interior rather than the pink AA-halo band it was measured from. Re-sampling
its final 1990 pixels gives median (255,255,255) — pure white. Nothing
downstream re-validates that a shape's assigned thread still matches the
pixels its FINAL polygon actually covers.

**Fix:** a post-vectorization sanity check — re-verify a shape's assigned
thread still matches (within some ΔE00 budget) the pixels its final polygon
covers, especially for thin/hairline shapes, and re-snap or flag when it
doesn't. This is a new mechanism, not a tuning knob — needs its own design
pass before a plan can be written for it. Orthogonal to both `max_colors` and
chart coverage.

**Not the enclosed-background bug.** This fixture also has a real, separate,
ALREADY-FIXED issue (commit `c1b9e35`, "enclosed background pixels become
real, restorable regions") — its white icon linework sews unstitched by
DEFAULT (not a bug, a feature: restorable via the "Sew this enclosed area"
control in Studio's Layers panel). Don't reopen that; it's done. This doc's
finding is a completely different, still-open issue about color/geometry
desync on the shapes that DO sew.

## Verdict / priority

Ranked by leverage: **(1) drone_render's max_colors fix** is the cheapest,
most contained, most certain win — a config/algorithm tweak with a clear
mechanism. **(2) summit_badge's merge-threshold fix** is a real but
moderate-complexity change to `stage2_photo_segment.py`'s merge logic — the
SAME file the SAM2 branch also touched (Task 1's `kept_masks_to_quant`
extraction), so check for rebase conflicts before starting. **(3) the
post-vectorization color-check for repro_gradient_white_icon** is a new
mechanism nobody has designed yet — needs its own investigation-to-plan cycle,
not a quick fix.

None of these three fixes require SAM2 or any segmentation-quality
improvement. Segmentation was already tried here (PR #45) and didn't move the
grade — the real cost is thread-chart color matching (2 of 3 fixtures) and a
geometry-registration bug nobody had found before (1 of 3).

---

# Follow-up, 2026-08-11 (later) — #6.2 refuted on measurement, #6.3 fixed

Both remaining fixes from this doc were taken to measurement. One of the two
recommendations above did not survive it. Everything below is measured on this
repo's own fixtures, at the configs named. The probes that produced them were
throwaway and are not committed; every number they produced is reproduced
inline below, and the two findings worth re-running live on as tests
(`digitizer/tests/test_thread_revalidate.py`).

## #6.2 (`summit_badge.png`) — REFUTED as specified. Do not build it.

The recommendation was: cap the RAG hierarchical merge on region-internal Lab
spread so a chained gradient splits before `select_palette` runs. It was built
(per-node foreground Lab moments — count/sum/sum-of-squares, exact and O(1)
under merge — plus a refusal on the predicted merged spread) and swept. Three
findings, in the order they killed it:

**1. A tightening factor cannot enforce a bound.** Built first in the shape of
the three merge protections already in `stage2_photo_segment.py`
(`_area_ratio_factor`, `_boundary_contrast_factor`, `_face_local_threshold`),
which divide an edge weight by a factor. That only DEFERS a merge in
`merge_hierarchical`'s global heap, so a different merge fires in its place —
and the substitutes were worse than what was prevented. `drone_render.png`
worst region-internal RMS went **35.88 (rule off) → 62.97 at a cap of 16.0**,
and region count moved non-monotonically with the cap (`summit_badge` 13 → 15 →
13 across caps 12/10/8). Refusal (infinite edge weight) is the only mechanism
that bounds anything here.

**2. The ceiling is SEEDS granularity, not the merge.** A merge rule can never
make a region tighter than the coarsest superpixel already inside it, and on
the fixture with the worst score that is the entire story:

| fixture | worst RAW SEEDS superpixel | worst final region |
|---|---|---|
| `drone_render.png` | 70.00 RMS (240 px) | 70.00 at **every** cap |
| `summit_badge.png` | 39.58 RMS (188 px) | 39.58 at cap 10 |
| `repro_gradient_white_icon.png` | 43.60 RMS (259 px) | 43.60 rule off |

The rule fires 8,359 times on `drone_render.png` and cannot touch its worst
region. Tripling SEEDS density does not rescue it either — `SEEDS_TARGET_FG_
SUPERPIXELS` 1200 → 3600 moves worst final spread **35.88 → 35.61** on
`drone_render` and **16.10 → 16.10** on `summit_badge`, because the merge
threshold simply re-merges the finer pieces. The controlling knob is
`MERGE_DELTAE00_THRESH` (26.0), which is pinned to the 20-80 region-count
accept band; within-region spread and that band are in direct tension.

**3. The usable window is empty.** Below cap ~14 the rule blows the accept
band (`drone_render` 21 → **170** regions at 90mm, straight through the ceiling
`test_busy_gradient_fixtures_land_inside_the_accept_band` pins — undoing PR #45
wholesale). Adding a chaining discriminator (refuse only when BOTH sides are
themselves under the cap, which is what "chained along a gradient" actually
means) recovers a lot — 170 → 84 — but still misses. At caps ≥18 the rule does
nothing measurable. The one surviving candidate, cap 16.0, buys
`summit_badge` worst RMS 16.10 → 14.60 and mean 9.30 → 9.06 — and then:

| fixture / config | grade, score (cap off) | grade, score (cap 16.0) |
|---|---|---|
| `summit_badge` left_chest | F, 0 | F, 0 |
| `summit_badge` hat_front | F, 10 | F, 10 |
| `drone_render` both | F, 0 | F, 0 |
| `repro_gradient_white_icon` both | D, **58** | D, **46** |

It buys nothing on either fixture it targets and costs a third fixture 12
points. **Reverted; nothing of it is on the branch.**

**What #6.2 actually needs.** Not a merge rule. Either split regions by colour
AFTER merging (a different mechanism, downstream of the accept band), or accept
that a wide-spread region is legitimate and let a tonal tier sew it — which is
already what `source_pixels` and the blend/streamline tiers exist for. Note
also that this doc's own caveat about `preflight._artwork_colors_by_thread`
(pooled per-thread medians) applies with full force: **the current scorecard
cannot see a segmentation fix at all**, so making that metric per-region is a
prerequisite for #6.2 being measurable, not a side quest.

**Update 2026-08-17: that prerequisite landed, same day.** `619e9ad`
(2026-08-11) made `THREAD_MATCH_POOR` per-region, same as the #6.3 fix below
records. Whether #6.2 (still reverted, not rebuilt) is now measurable under
the new instrument was not re-checked here.

## #6.3 (`repro_gradient_white_icon.png`) — FIXED, and the estimator was the fix

`stage4_vectorize.revalidate_threads`, called from `pipeline.run_stages` right
after `tag_enclosed_background`. It re-scores every shape against the pixels
its FINAL polygon covers and re-snaps the ones that drifted, emitting
`THREAD_RESNAPPED_AFTER_DRIFT`. It changes threads only, never geometry — the
simplified outline is the one that sews well, so the honest correction is to
give it the thread it now needs.

**The estimator is the whole fix, and the first build got it wrong.** Scoring
the region by MEAN Lab reported the traced sliver at dE00 **5.54** — i.e.
reported the defect as absent. The sliver is bimodal, and every statistic that
collapses it to one colour first will hide that:

```
shape S648e28fc  thread 2560 Azalea Pink rgb(255,185,204)  2333 px
  mean   RGB (247.1, 182.6, 192.8)  -> dE00  5.54   <- almost no pixel is this
  median RGB (255, 255, 255)        -> dE00 23.87
  per-pixel dE00:  p10 23.9   p50 23.9   p90 25.2
  near-white pixels (all channels >= 235): 1389 / 2333 = 59.5%
```

This is the SAME trap this doc already documents for `preflight._artwork_
colors_by_thread`, walked into from the other direction. Scoring the MEDIAN OF
THE PER-PIXEL dE00 keeps the answer on real pixels: the traced shape scores
**23.87**, matching this doc's original measurement to two decimals, and
re-snaps to **0.00**.

Measured effect on the honest per-region metric (each shape's own final-polygon
pixels vs its own thread, 80mm/left_chest):

| fixture | worst per-region dE00 before | after | shapes re-snapped |
|---|---|---|---|
| `repro_gradient_white_icon.png` | 23.87 | 0.00 | 1 |
| `drone_render.png` | 20.99 | 10.64 | 2 |
| `summit_badge.png` | 9.47 | 9.47 | 2 (mean 3.76 → 3.52) |

**Caveat as first written, now SUPERSEDED — kept because the sequence is the
lesson.** This section originally read: "this does NOT move the corpus
scorecard grade... on `drone_render` the pooled `thread_worst_delta_e` reads
9.2 before and 33.6 after, while the per-region worst genuinely halves. Do not
read that as a regression, and do not tune against it — it is the measurement
instrument disagreeing with itself, and it is the strongest argument yet for
making `_artwork_colors_by_thread` per-region."

That argument was accepted and acted on the same day: `619e9ad` made
`THREAD_MATCH_POOR` score per region instead of per pooled thread median.
Re-measured against the new instrument, the caveat is simply false — #6.3
moves the grade, decisively:

| fixture | #6.3 off | #6.3 on |
|---|---|---|
| `repro_gradient_white_icon` (both configs) | **F, 0** — worst dE 28.3 | **B, 76** — worst dE 6.8 |
| `drone_render` (both configs) | F, 0 — worst dE 36.0 | F, 0 — worst dE **14.1** |
| `summit_badge` (both configs) | F, 0 — worst dE 10.3 | F, 0 — worst dE 10.2 |

The OFF baseline moved too (`repro` was D/58 under the pooled instrument, F/0
under the per-region one): the new instrument sees the 23.9 dE drift the pooled
median had been averaging away, grades it as the failure it is, and then agrees
that #6.3 fixes it. **The lesson worth keeping: for one day this repo held a
real fix and a broken instrument, and the instrument's verdict was the one
written down. When a fix and a metric disagree, establish which one is wrong
before recording either.**

Tests: `digitizer/tests/test_thread_revalidate.py` (7), including one that
pins the mean-vs-per-pixel gap so a future refactor cannot quietly reintroduce
the estimator that hid the bug.
