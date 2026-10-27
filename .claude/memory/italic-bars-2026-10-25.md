---
name: italic-bars-2026-10-25
description: On italic block words the pro crosses BARS along the slant (parallel to the stems, an upright digitizing sheared); ours crossed them square, often leaning the wrong way. `lettering_columns_italic_lean` OFF moves straight bars only (E arms, A bar, L foot), not bowls. Read per cross with `tools/italic_cross.py` -- L6's piece-axis leaning share cannot see it
metadata:
  type: project
---

2026-10-25, task 6 of the director's wave, lane `claude/italic-cross-angle`.
Brief: #1061 found `lettering_columns_text_lean` (ON) moves italic PROSEAL's
leaning share away from the pro (0.27 -> 0.21 with fold, his 0.31).

**The instrument was the first problem.** The pro sews most PROSEAL letters as
ONE piece of 170-200 crosses (drift > 110 deg), so `letter_pieces`' piece axis
is no stroke's direction and L6's 12-65 deg "leaning" bin counts a whole P by
it. `tools/italic_cross.py` reads each cross against the LOCAL stroke axis
(midpoints within 0.9 mm, straight windows only) and classes it stem / bar /
diagonal; means are axial (a zigzag alternates +-atan(pitch/2w) about its
cross -- a signed median picks one side).

**His italic rule, measured** (PROSEAL hat 85.9 / beanie 75.0, slant 10.7 /
10.3; Golden Tee GOLF, slant 17.7): **bars cross along the slant** -- 52-54% of
bar crosses within 8 deg of it, mean 1.8-2.0 deg off (GOLF 48%, 0.1 deg). Stems
cross BETWEEN the line and square-to-slant (+6.1 / +6.0 / +6.2 deg); the A's
legs near the line (hat diag +3.9). Ours, text lean ON: house 10.8 (square to
the stems) -> stems +9.3, diagonals +9.0 / +23.7, bars square either side
(P, E, A bars leaned the WRONG way).

**Built OFF** (`column_lean.italic_bar`, ContextVar set by ONE wrapper hunk in
`pipeline.plan_stitches`, per-word slant = median `letter_lean_deg`, italic at
5-30 deg): bars along slant hat 0.31 -> 0.46 (pro 0.54), beanie 0.29 -> 0.36
(0.52); E arms 0.20 -> 0.70, A bar 0.00 -> 0.52. **Not reached:** P/R/O/S bars
-- they are bowl / ring columns, not straight. L6's leaning share does not move
(0.189 -> 0.189): bars are outside its bin. Byte-identical ON on Becker hat
small and Fremont 92.6 (full digitize md5), and on four lane fixtures.

**Why:** Kent's fine-lettering priority; layout flag, judged in renders.
**How to apply:** read italic work per cross, by stroke class, never by piece
axis. Open: stems (ours +9, his +6) and the A's legs (house 10.8 vs his ~0)
both follow the house square to the slant -- a shear-model house would fix the
legs and overshoot the stems; bowls need a ring rule.
**ON since 2026-10-27, Kent's flip** from the wave-5 sheet ("Flip ON
(Recommended)"; [[flip-sheet-wave5-2026-10-27]]).
Related: [[big-letter-construction-2026-10-24]], [[lettering-10mm-up-band-2026-10-23]].
