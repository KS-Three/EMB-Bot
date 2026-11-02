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

**Census (`tools/element_drop_census.py`, 80 mm left_chest, this tree, 2026-11-01):**
fires on 4 of 19 Commons logo rows and 4 of 22 committed fixtures, every one
WARN (0.5–9.8 % of the artwork, none reaches the 10 % block): qr_code 10
clipped modules 864 mm2 (9.8 %, D 46 → F 34); gradient_mascot 2 unsewn pupils
85 mm2 (1.9 %, C 70 → D 58, Kent GREAT); pixel_art_sprite 4 unsewn black
pixels 44 mm2 (1.9 %, A → B, Kent GOOD); isometric_icon 1 folded face 9 mm2
(0.5 %, Kent OKAY); becker 2 unsewn Blackberry holes 12.6 mm2 (0.5 %, A → B);
drone_render 1 folded Fox Fire 25 mm2 + 4 unsewn Titanium 51 mm2 (1.7 %);
bridge_bar 4 folded 30 mm2 (1.3 %); golden_tee 2 folded 17 mm2 (1.1 %).
**Every `unsewn_enclosed` piece carried `enclosed_colour_unknown`** — the
garment rule could not speak there, which is why they were left unsewn.
`duotone_poster` routes photo_scene on this tree (texture gate), no cap
fires, no finding: the fold case it was named for no longer occurs here and
rests on the synthetic test. `heraldic_crest`'s 18 cap merges do not reach
the fold's touch-and-10-dE test (conservative). 15 of 19 and 18 of 22 rows
unchanged; grunge A 100 unchanged (stage-1 half, out of reach).

**How to apply:** when a pipeline stage drops or re-threads a whole shape,
give it ids and mm2 in its warning (stage 7's count-only `SHAPE_NOT_STITCHED`
is the one this check cannot read) and this finding picks it up; do not add a
second drop finding. Related: [[photo-corpus-sxs-2026-10-27]],
[[colour-cap-sewn-2026-10-29]], [[no-warnings-reaches-readouts]].
