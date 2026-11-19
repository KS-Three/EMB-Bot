---
name: marine-match-2026-11-18
description: "Kent 11-18 'make MARINE match the pros': pro construction measured per letter (tools/marine_construct.py, docs/marine-pro-construction-2026-11-18.md); r_bowl, block_butt_small, a_bar, block_lean ON since Kent 11-19 'Flip all four ON (Recommended)'; only Becker moves; R counter held by a 0.5 mm inset read from his file (sew-out row 15)"
metadata:
  type: project
---

The pro sews MARINE as: level uncut stems, a sheared slab across each top, diagonals/V level, R = stem + ONE bowl column
normal to the wall + level leg, A bar = horizontal column of upright crosses butting two uncut legs, E = stem + butted arms.
Numbers for all five Becker placements in `docs/marine-pro-construction-2026-11-18.md` (read by `tools/marine_construct.py`;
NOTHING of his file is rendered, `tests/test_no_new_pro_renders`).

Four flags (built OFF as `cfg.extra` keys, #1686; typed `PipelineConfig` fields ON since Kent's 2026-11-19 "Flip all four ON (Recommended)", conftest `MARINE_MATCH_2026_11_19_OFF` in PRE_FLIP, engine json false), on top of block_butt: `r_bowl`, `block_butt_small` (gate 3.5 -> 3.0 mm:
Becker at 76.5-79.8 measures 3.46, so block_butt did nothing to its E/A/N there), `a_bar`, `block_lean` (lean cap 30 -> 50 deg where
the level house cross then passes). Each sweep: 44 runs, only the 6 Becker runs move; MFab hat 30 mm identical.
**Traps:** (1) normal crosses at a counter close it under the pull (3.2 vs block_butt's 4.59 mm2, his 9.85, art 6.63): his counter is LARGER
than the art's, that is gate 1 (row 15 of the sew-out list), not a bug. (2) `find_cuts` does not call the A's notch-left vertex reflex and
the `again` cut is added later by `_refine`, so `_a_bar_cuts` reads the `through` cut from the counter's bottom-left vertex. (3) The
lane's `letter_columns` is imported inside `columns.lettering_columns_shape`: spy on `outline_cut.letter_columns`, not `columns`.
(4) Pictures use `tools/marine_match_pics.py` (our renders only); numbers `tools/marine_match_figs.py`.
Related: [[block-butt-2026-11-18]], [[apex-family-revert-2026-11-17]].
