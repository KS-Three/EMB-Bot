---
name: proofread-2026-11-13
description: "cfg.proofread (built OFF, metrics only): the plan's top thread vs the traced art per colour class in mm (MISSING/EXTRA/MOVED/MERGED/CLOSED/SHAPE/WIDTH), each finding attributed to the shapes and region tags that made it; found kanji_seal's red bodies left unsewn as enclosed background"
metadata:
  type: project
---

**What (Director's order 2026-11-13, "find the light switch"):** nothing in the
engine compared what the plan SEWS with what the art SHOWS and named the rule
behind a difference. `digitizer_core/proofread.py` does, report-only behind
`cfg.proofread` (OFF writes no key; findings ride in preflight `metrics`,
never a customer finding, [[no-warnings-reaches-readouts]]). Step-0 inventory:
`legibility` (OCR), `glyph_read` (text words, metrics), `ARTWORK_UNCOVERED`
(inside sewn shapes), `ARTWORK_ELEMENT_DROPPED` (the pipeline's own warnings),
`tools/dropped_elements.py` (pixel dE regions, offline) and the five fault
readers (offline, one fault each) each read one thing; only the Column lane's
cover hand-back acts on a sewn-vs-drawn comparison.

**How it reads:** both pictures on one 10 px/mm grid in the plan frame; thread
= every run's segments at 0.4 mm in sew order as run index (top run exact;
jump-started runs drawn; recall 0.994 against `stage6_stitches.png` on
lt_jakarta). Art = the graded raster, nearest plan thread (Lab), garment-like,
other-ink, bg. `tol` = fabric pull + half a filament (0.5 pique, 0.6 cap).
Explanations come from region `meta` tags and run roles; `subpixel_accepted`
and `lettering_ink_stray` explain nothing (they move no outline). Three
departures leave NO tag (outline-loop border, Column lane, sliver prune), so
they always read as unexplained.

**What it found on main 7ad9c124 (80 mm left_chest):** bukit_asam's "e o n"
MOVED 3.1 mm up (`small_text_reset`); jakarta's tagline MOVED/MERGED and its
three squares joined into one bar; ahora's H-O and A-! joined across the pink
ground; TOAT's 0.7 mm keyline hexagon sewn as a 1 mm-wider satin (untagged
outline loop).

**RETRACTED 2026-11-14: "kanji_seal sews its solid red bodies hollow".** The
bodies are TRANSPARENT empty spaces in the source; the red was RGB flattened
under the alpha, which the first read took for ink because stage 1 keeps
enclosed holes out of `bg_mask` (`Prep.enclosed_mask`). The hollow render is
right. jakarta's boxed "a" counters were the same error. Since then
`proofread.page_mask` reads `bg_mask | enclosed_mask` as page, and on non-alpha
art a thread within 10 dE of `bg_edge_rgb` reads as page (a white field sewn
white). The lesson: look at the SOURCE composited over white, not the prepped
raster, before calling ink missing ([[eye-first-diagnosis-2026-11-13]]).

**Against Kent's pins (instrument reading, n small, 13 items' renders were on
older trees):** on the 7 items where a random pin hits under 0.6 of the time,
20/34 pins hit within 3 mm vs a pin-weighted chance of 0.38, about 18 of the 20
for the right fault. qr_code/low_poly (chance 0.87/0.98) say nothing. Misses:
stitch type/direction/angle (not geometry), ahora's ~0.8 mm gear teeth (under
the SHAPE floor, tol + a filament), the crest's ~1 mm eyes (under the art
floor). Pro logos Kent graded Good: unexplained Fremont 0, ProSeal 17, TOAT 5;
by eye ~20 of the 22 are real departures he graded through (honeycomb gaps
closed, gun highlights lost, keyline thickened), 2 sit at the floor; plus 2
Fremont misfires that are anti-alias grey read as the tan thread.

**Census 2026-11-14 (34 of 45 kit items; `tools/proofread.py census`, tables
in `eye_pairs_out/proofread-1113/census/`):** ranked by misfires, the steps not
being fixed elsewhere that night were stage 5's clip (`clipped_stage5`: 42 on 6
designs, 2,577 mm2), enclosed white 30, per-shape border 29, colour-cap fold
25, run-tier rescue 20. Untagged satin/fill departures (Column lane, outline
loops, plain shape error) are the bulk: 610 findings. Good/Great designs carry
3.2 unexplained findings each (6 of 13 none), the rest 29.4; by eye about a
quarter of those on Good/Great are false (AA fringe, a 1 mm eye).

**First guard: `cfg.proofread_guard_clipped` (built OFF).** A shape stage 5
dropped or cut whose own-colour ink the art shows is re-planned with its art
sewn over the earlier colour (`stage5_overlap.keep_art_scope`), kept only when
the read improves by 5 mm2. qr_code: finder squares and modules back. A first
guard on `left_unsewn` was built and dropped the same night: its evidence was
the alpha-hole error above. See the PR for the sheets and plan-time cost.

Pictures: primary checkout `digitizer/eye_pairs_out/proofread-1113/`. Next:
tag the untagged departures (outline loop, Column lane, sliver prune).
