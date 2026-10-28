---
name: dark-read-refusal-2026-10-28
description: "2026-10-28 — `dark_ink_refuse_strays` built OFF (Kent on #1172: \"Keep ON, queue refusal\"): a kept dark read within 4 px of the artwork's edge, or not under its ring as a whole, is refused; the 10 \"not ink\" rows of #1172's table were the 10 components at the frame, judged against an artwork window the sheet tool had clipped and stretched"
metadata:
  type: project
---

# Dark read refusal (`dark_ink_refuse_strays`) — 2026-10-28

Kent on #1172, verbatim: **"Keep ON, queue refusal (worker's pick)"**, then
"Start refusal lane". The flag (`config.py`, beside `keep_dark_thin_strokes`;
`thin_ink.stray_clause`, one gated line in `find_dark_thin_ink`) refuses a kept
dark component when (a) its bbox lies within `DARK_INK_EDGE_PX` = guard + ring
= 4 px of `p.art_bbox` ("edge": the one-ground test ran on part of a ring), or
(b) fewer than `DARK_INK_STRAY_SHARE` = 0.5 of its pixels sit `DARK_INK_DEPTH_L`
(8 L*) under the ring's median ("ground"). OFF is byte-identical.

**Kent's ruling on #1173, relayed by the foreman 2026-10-28, verbatim: "Hold
OFF, keep as instrument (worker's pick)."** Ships OFF as built; no flip queued;
#1172's "stray reads" paragraph is corrected by #1173's table.

**What the measurement found (the engine's own raster, Lab).** All 30 of
#1172's reads are 11-98 L* darker than their ring's median, with 0.75-1.0 of
their pixels 8 L* under it — clause (b) fires on none. The 10 rows judged "not
ink" are exactly the 10 components within 1 px of the frame (owl 8, patch 2);
the 16 ink reads sit 6-170 px in (the patch's keylines at 6, the nearest), so
any edge margin from 1 to 5 px gives the same split; 4 px is the module's own
ring reach. Two "mixed" owl reads at the frame (Skylight on the bottom edge,
the breast stripe's edge) go with the edge clause. **Why the table was wrong:**
`tools.dark_ink_flip_sheet._art_crop` clipped a window past the artwork's edge
and stretched the rest to the whole window, so every edge window's artwork sat
shifted inward against the renders beside it; the "plain ground" under the
owl's left-edge Blackberry columns is a dark feather streak once the window is
padded instead (fixed with this flag; the tool takes `--flag`).

**Pins.** `PRE_FLIP["dark_ink_refuse_strays"] = False` and the field in
`tests/engine_2026_10_27.json` (the roll-forward rule, [[flip-proof-pins-2026-10-27]]);
no md5 pin moved. `tests/test_dark_ink_refuse_strays.py`: the clauses, a drawn
ground with bars at the frame, the owl (16 -> 6 dark reads ON) and the patch
(14 -> 12; N, O, F and both keylines held). Sheet:
`docs/renders/dark-read-refusal-2026-10-28/`. Related: [[dark-thin-strokes-flip-2026-10-28]].
