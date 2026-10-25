---
name: letter-separation-2026-10-25
description: W3-07 — where our 5-10 mm letters touch and the pro's do not, on 8 paired jobs (`tools/letter_gap_census.py`). Premise TRUE (the traced polygons stand 0.60-0.87 mm apart), but every touching pair is PULL COMP, not construction: both rails sit 0.17-0.29 mm outside the outline, so a traced gap under 0.4 + 2 x comp touches. The pro keeps >= 0.10 mm at 5-8 mm caps, tip touches only.
metadata:
  type: project
---

2026-10-25, W3-07, branch `claude/letter-separation-w3-a0c436`. Doc
`docs/letter-separation-2026-10-25.md`, crops
`docs/renders/letter-separation-2026-10-25/`.

**The instrument.** `tools/small_text_columns.py` gained `text_lines` and
`word_letters` (`pieces` untouched, W3-02 imports it): a joined piece is
shared out between the known word's letters (DP on width shares) and
parted at a 1.0 mm opening when they part there (a TIP touch, contact =
shared boundary) or cut at the narrowest column (FUSED). The census
(`tools/letter_gap_census.py --digitize/--read`) gives per word min gap,
touching and fused pairs, ours vs pro, each file in its own frame, plus
`d4` (our stage-4 polygons' gap = the art's spacing) for every pair.

**Result, 8 jobs: 95 within-word pairs read on ours, 103 on the pro's.** Ours touch 6:
Fremont hat O-T (fused 1.65 mm) and N-T (tip), Drone O-N (fused 4.2 — its O
is also sewn shut, the split alpha counter), Gaulke hat K-E and O-O, Gaulke
LC O-O (tips). The pro touches 2 of 82 at 5-8 mm caps, tips only (Fremont
O-T 0.20 mm, MFab I-N 0.45), never fused. All 6 of ours: `d4` 0.60-0.87,
each letter's facing needles within 0.03 of its own rail offset (Gaulke's
K arm end +0.09): **pull comp** (hat 0.4 - 0.11 inset = 0.29/side, LC 0.17).
No fan past the outline, no absorbed serif at this size.

**The pro's rule:** at 5-8 mm caps >= 0.10 mm visible (p10 0.15-0.22,
median 0.36-0.49), and at 6.5-8 mm his gap ignores the art's spacing (r
-0.06; ours +0.76); at 9-13 mm the art's gap (>= 0.75). His sewn letter
WIDTHS equal ours (Drone per letter within 0.05-0.5 mm).

**Prototype (harness only, gate-1 candidate, I5):** holding the facing
needles apart to 0.25 visible (`small_text_cap_letter_gap_mm`) opens all 6
to 0.25-0.35, moving 2-22 needles by <= 0.29 mm. A build would clamp the
pull push of a rail facing another letter of the word: `columns.py`
`sewn_rails` (in #1057, not edited here).

**The wave's 4 mm number was the OCR.** Fremont's FREMONT 0.00 (job
+0.42 vs pro +1.00) is unchanged with O-T and N-T held apart, and our 4 mm
crop reads FREMONT plainly to the eye; tesseract says "CSA". Look at the
`--dump` crop before planning on a `word_legibility` zero.

**Traps:** a backdrop fill under the letters is another colour block —
match letter to plan shape in the letter's OWN block (plan block = DST
block, 1:1) or every letter maps to the backdrop. MFab's AND WELDING is
white knocked out of a black keyline (`sew_enclosed_white` OFF): no letter
thread in ours, row named, never 0. Overrun needles fall in the
NEIGHBOUR's mask; judge a letter by its shapes' points, not by its mask.

Related: [[lettering-5-10mm-band-2026-10-23]], [[pull-comp-by-stroke-2026-10-22]],
[[small-text-reset-2026-10-21]], [[word-legibility-instrument-2026-10-24]],
[[layout-judged-in-preview-2026-10-22]], [[lettering-board-2026-10-25]].
