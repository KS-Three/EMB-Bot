---
name: yardstick-pro-pair-2026-11-01
description: Pro-pair figures (cuts, hops, needle-up mm, stitch-type kappa, word cc, columns) against Kent's 100 labelled pairs that have a pro file, every design re-drawn at the pro's size; what cleared chance and why the Phase 1 exit still fails
metadata:
  type: project
---

**Measured 2026-11-01** (`docs/yardstick-pro-pair-vs-kents-eye-2026-11-01.md`;
tool `digitizer/tools/eye_pairs/pro_pooled.py` over
`docs/eye-pairs-2026-11-01/pro-pair-inputs.json`, built by `pro_pooled_build.py`
`render` / `measure` / `build`). All 100 labelled pairs on a design with a pro
file (41 decided: 29 after, 12 before; 39 same, 20 both_bad) had BOTH arms
re-digitized on their sitting's tree, detached outside the repo, at the pro's
width and garment - no labelled render directory survived anywhere on the
laptop - and read beside the pro's DST with one reader (143 designs, about
three hours under the `%TEMP%\embwt\cpu.lock` slot, 5-26 s each to measure).

- **Ties-in kappa vs Kent's pick, clear on both intervals:** hops +0.24
  [+0.10, +0.39], cuts +0.23 [+0.08, +0.38], needle-up mm +0.17 [+0.03,
  +0.31] (its fixtures interval clears by 0.01). **Sides only:** hops alone,
  +0.33 [+0.02, +0.64] on 32 pairs, and it crosses zero again without the
  three tires pairs.
- **No evidence either way:** stitch-type kappa +0.02, word cc +0.15 (n 49),
  columns +0.09 (n 64) - the fidelity-shaped readers, and the only two whose
  reading actually uses the pro's own figure.
- **The exit's "never scores his pick worse" fails on all six:** hops 10 of
  32 decided pairs, cuts 11 of 32, mm 13 of 36, stitch-type 21 of 36. Four
  pairs he chose fail five instruments at once. The legible case is
  `ref_0827`: he picked the 09-18 engine over the 08-27 one on four logos
  where the old engine lay 12-71 hops nearer the pro - he trades trims for
  construction, and the trim family sees only trims.
- **The pro reference added no signal.** Ours has more cuts than the pro on
  187 of 200 designs, more hops on 188, more needle-up mm on 198, so "closer
  to the pro" is "fewer" on 97+ of 100 pairs: this is the 10-11 trims result
  (+0.28) reproduced on re-drawn designs. Only `columns` changes its pick
  with the pro in the reading (28 pairs), and it clears nothing.

**Why:** ROADMAP Phase 1 exits on "the metric's ranking agrees with Kent's
visual ranking, and nothing he judges better ever scores worse". The 10-11
doc showed no fidelity instrument clears chance and only trims do; the
pro-pair figures are what actually decides flips (pro_baseline,
lettering_board, word_legibility) and had never been tested against him.

**How to apply:** Quote hops or cuts as a distance to the pro only with the
caveat that they read trims and nothing else; do not present the pro
reference as a new yardstick on this corpus. The exit's second clause can be
met by no instrument here - Kent either sets a tolerance (the doc's §6
proposes one) or declares it unmet; phase marker untouched, his call. The
next sitting should use the doc's §4 tally (pairs where trims and his eye
disagree), at the pro's size, on the nine new logos. Method traps paid for:
`scorecard.chance_correct` clamps at 0, so compute the unclamped kappa when
ranking arms; `lettering_board.read_pair` appends the slug to its cache path
itself; a lane's rembg link must point at the PRIMARY checkout's venv, not
the lane's. Related: [[flip-eight-2026-10-23]], [[lettering-board-2026-10-25]],
[[word-legibility-instrument-2026-10-24]], [[trim-defects-4-6-2026-10-29]].
