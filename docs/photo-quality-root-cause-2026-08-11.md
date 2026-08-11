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
