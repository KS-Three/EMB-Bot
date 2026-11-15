---
name: speck-prune-2026-11-14
description: Missing/invented pin families traced (19 + 41 pins); kanji in-fill (29) already cured on main; low_poly's 7 black dots = stage 3 keep_thin_strokes keeping hairline crossings as run loops; `speck_prune` built OFF cures all 7
metadata:
  type: project
---

**What:** Kent's two pin families from the 11-10..11-12 sittings, census
classes 6 (missing, 19 pins / 9 designs) and 7 (invented, 41 pins / 6),
re-run on main `66b11432` and traced
(`docs/missing-invented-traced-2026-11-14.md`). By pins:
- 29 white in-fill on transparent areas (kanji 28, neon 1): CURED on main by
  `enclosed_white_skip_transparent` ON 11-11 (the kit rendered before it);
- 7 low_poly "Random Black Spot": fixed here;
- 5 To a T speed lines: `fine_bar_survive` (#1513, OFF);
- 3 QR finder squares: `proofread_guard_clipped` (#1487, OFF);
- the rest 1-3 pins each (k_line box = satin band + inner fill, crest eye and
  crown keylines, arabic stems, Drone tonal, isometric shading band).

**The cause fixed:** low_poly's polygon edges are 1 px black lines at the work
grid (x1.01). Stage 2 labels only their crossings black; stage 3's
`keep_thin_strokes` contrast rescue keeps each crossing (0.13-0.30 mm2,
0.06-0.21 mm wide) and stage 4 sews it as a run loop, a black dot.

**`cfg.speck_prune` (built OFF):** `sliver_prune.prune_specks`, after
`sliver_prune`, flat/gradient only. A sub-floor mask that clears the run
floors, mean width < 2 source px, inscribed width < the thread
(`thread_profile().width_mm`), wedged in the figure, >= 10 dE00 off its host:
its pixels go to the host. ON low_poly: 7/7 dots gone, 10,539 -> 10,325
stitches, 97 -> 76 trims. The run-floor restriction matters: without it 3,400
tiny masks moved facet outlines for nothing. The inscribed test matters: 2 x
area / rim reads a short 0.6 mm stroke on a coarse source as under a thread.

**How to apply:** `sliver_prune`'s x1.25 enlargement gate does NOT apply to
specks (low_poly is native). Sheets:
`digitizer/eye_pairs_out/missing-1114/sheets/`. Flip is Kent's. Related:
[[sliver-prune-2026-11-10]], [[transparent-white-infill-2026-11-11]],
[[fine-bar-survive-2026-11-14]], [[proofread-2026-11-13]].

**Kent 2026-11-15:** `speck_prune` ticked ON (with `stroke_bridge_keep` and `lone_glyph_keep`). Ruled ON 11-15, flip pending.
