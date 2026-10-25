---
name: reset-bay-mouth-2026-10-25
description: Re-set small text shuts bays (Fremont E->B, S->8, 5->3); the pro's letters are NOT wider -- he keeps a MOUTH (median 0.51 mm, n 18); `small_text_bay_mouth` (cfg.extra, OFF) cuts back the terminal that shuts it
metadata:
  type: project
---

2026-10-25, W3-02, follow-on to [[small-text-reset-2026-10-21]] and
[[small-bold-columns-2026-10-21]]. The brief said "widen the bay glyphs ~15%
like the pro". **Measured false first** (both DSTs, each in its own frame,
`small_text_columns.pieces`): our re-set S/5/8 on the Fremont hat are WIDER
than his (w/h ours/pro 1.06/1.07/1.11), ProSeal's S too (1.09, 1.13); only
the patch is narrower (the re-set picked width 1.4x there, 1.85x on the hat).
Widening in place to 1.5x, room ignored, never opened the 5's bowl: every
shut mouth is a VERTICAL gap (5 tail up to its stem, S terminals back to the
spine, E arm serifs to the middle arm). Within the line's room it made the
hat WORSE (no spare room: every letter shrank).

**What he does:** ends the terminal short. `tools/bay_census.py --census`
(his E/S/5, Fremont hat + patch, ProSeal hat + beanie, out of the committed
zip): every mouth open, n 18, 0.27-1.20, median 0.51 = `BAY_MOUTH_MM`
(a test recomputes it from the zip). A mouth = 2 x the bottleneck clearance
from a pocket (ground inside the letter's 0.8 mm closing, >= 0.15 mm from
thread) to the outside; 0 = enclosed, so an 8's counters read 0 by design.

**Built (OFF, `cfg.extra["small_text_bay_mouth"]`, wired in pipeline.py's
`enlarge_small_text` call -- absent key, the call is today's word for word --
re-set only, `small_text._open_mouths`):** a pocket of the sewn extent (polygon +
`SEWN_EDGE_MM`) that is constricted and under 0.51 and is a BAY of the
letter (not a counter) -> the mouth's place is the bay's narrowest point in
the letter AS DRAWN (`_pinch`; on the sewn extent the wall is as thick
through an E's serif as across its mouth) -> cut the free end of the medial
axis pointing most squarely at it (`_facing`, <= 75 deg) by geodesic length
inside the ink (passes an S's serif beak), shortest cut that opens it.

**Measured on the DSTs** (`docs/renders/bay-mouth-2026-10-25/`): Fremont
hat E 0/0 -> 0.56/0.58, S -> 0.70/0.72, 5's bowl -> 0.65; patch E -> 0.62/0.70,
S (filled) -> 0.66/0.70, 5 -> 0.42; at viewing size "BST 1093" -> "EST 1895".
THE's E opens too. ProSeal hat and Drone byte-identical; the beanie S and one G
change. No height moves; three letters lose 0.10-0.14 mm width. ONE MISS: the
hat 5's slot under its bar stays a hole -- a uniform slot, filled by the
stroke; only the stroke (gate 1) opens it. Single-letter OCR is noisy (the
pro's own 5 reads 3): read mouths first.

**Traps, each hit:** (1) least-ink choice cut the E's MIDDLE ARM off whole
(one cut opened both mouths) -> pick by facing. (2) a mouth read from its OLD
deepest point says "open" at 0.35 while the census, reading the merged
pocket's new deepest point, says 0.94 -> stop on the census's own reading.
(3) a skeleton-branch cut stops at a junction: an S terminal's serif beak is
a 0.7 mm branch -> geodesic cut. (4) a scratch reader capped mouths at 0.80
and gave n 17 / 0.50; the committed reader is exact.

**Why:** a gate-1 stroke and a re-set layout can both be right and still
close a letter; what reads is the mouth. **How to apply:** before widening
or thinning anything to open a letter, read its mouths (`bay_mouths`) on
both machine files; a constricted bay opens at its terminal, not its width.
