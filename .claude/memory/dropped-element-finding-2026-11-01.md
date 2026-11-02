---
name: dropped-element-finding-2026-11-01
description: ARTWORK_ELEMENT_DROPPED (preflight) reads the pipeline's own SHAPE_NOT_STITCHED / SHAPES_LEFT_UNSEWN / colour-cap / stage-4 drops by area; floor 5 mm2, block at 10% of artwork; Kent graded two rows it fires on Good/Great
metadata:
  type: project
---

**What:** `preflight._element_drop_findings` (PR, 2026-11-01) turns the losses
the pipeline already reports into one customer-facing finding,
`ARTWORK_ELEMENT_DROPPED`, judged by AREA. Four causes, each a pipeline seam:
`clipped` (stage 5 `SHAPE_NOT_STITCHED` ids), `unsewn_enclosed`
(`SHAPES_LEFT_UNSEWN` on an enclosed-background region whose artwork is
>= `DELTA_E_CLEARLY_DIFFERENT` from `cfg.garment_rgb`; a review override is
the customer's call and never counts), `folded` (a region with
`meta["color_cap_merged_from"]` touching a shape of its new thread within
0.3 mm and >= 10 dE00 from that thread on the thread grader's own rows), and
`unsewable` (stage 4 `DROPPED_SMALL_SHAPES` with `all_small` False, count and
largest only). Piece floor `_THREAD_MATCH_MIN_PATCH_MM2` (5 mm2); severity
`block` once the lost area is 10% of the regions' area
(`1 - _ARTWORK_REACHED_FLOOR`), `warn` under it. Metrics
`element_drop_checked`, `element_drop_colour_checked`, `element_dropped_count /
_mm2 / _frac`. `run_preflight` now grades the regions ONCE
(`_region_color_errors`) and hands the rows to both the thread check and this
one (`_thread_match_findings(rows=)`).

**Why it existed as a hole:** grep 2026-11-01, zero consumers of
`SHAPE_NOT_STITCHED`, `DROPPED_SMALL_SHAPES`, `THREAD_RESNAPPED_AFTER_DRIFT` in
`preflight.py`; the 2026-10-27 logo census (items 3-4) sent `qr_code` (864 mm2
clipped) out at D 46 with no drop finding, `duotone_poster`'s disc folded into
its tan ground, `gradient_mascot`'s pupils unsewn as enclosed background (the
black ground was read as BACKGROUND_UNCERTAIN, so `enclosed_by_garment` could
not speak). `ARTWORK_NOT_SEWN` (#1179) cannot see any of these: all within
1 mm of thread.

**Not reached, by design:** ink stage 1 removed WITH the ground
(`distressed_grunge`'s ring and monogram) never becomes a region; that is a
stage-1 refusal with its own plan doc. Stage 3's count-only
`DROPPED_SMALL_SHAPES` and `CLIP_DROPPED_SLIVER` (floor 0.56 mm2) are details.

**Kent's grades vs the finding:** he graded `gradient_mascot` GREAT and
`duotone_poster` GOOD on 10-28 with the pupils and the disc already gone
(`docs/scoreboards/photo-corpus/grades-5ff48c5-2026-10-28.json`), so this
finding fires on two of his Good/Great rows for losses the census itself named.
Read that as "he graded the render, not the report", not as a false positive;
whether it should BLOCK there is his severity call (a block is a Download
confirm, never a refusal, `DownloadStep.svelte` 2026-09-14).

**Census (tools/element_drop_census.py, 80 mm left_chest, this worktree):**
PENDING — filled in when the run under the CPU slot finishes.

**How to apply:** when a pipeline stage drops or re-threads a whole shape,
give it ids and mm2 in its warning (stage 7's count-only `SHAPE_NOT_STITCHED`
is the one this check cannot read) and this finding picks it up; do not add a
second drop finding. Related: [[photo-corpus-sxs-2026-10-27]],
[[colour-cap-sewn-2026-10-29]], [[no-warnings-reaches-readouts]].
