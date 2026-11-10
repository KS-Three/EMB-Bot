---
name: defect-marks-sitting-2026-11-10
description: Kent 11-10 asked why his eye and the yardstick differ; the answer so far is whole-design number vs local faults, and `tools/defect_marks.py` is the sitting that asks him where and what instead of left or right
metadata:
  type: project
---

**Kent, 2026-11-10:** "determine why my eye judges a digitized photo differently
than your yard stick. This is the tool that needs to get fixed so we can start
to automate the digitizing improvements on your end." Asked which artwork, he
chose "Both (Recommended)": his pro-file logos first, then the photo corpus.

**The reading that started it (instrument readings, n = 21, one tree).** On the
21 Commons logo rows Kent graded Great..Terrible on 10-28
(`docs/scoreboards/photo-corpus/grades-5ff48c5-2026-10-28.json`), the same
tree's preflight raw score (`baseline-5ff48c5.json`) has Spearman 0.00 against
his grade: `distressed_grunge` he called Terrible and preflight scored A 100,
`gradient_mascot` he called Great and it scored D 58. `fidelity_cc` runs the
wrong way (-0.32); trims +0.50. Preflight prices sewing hazards (thread match,
trims, density); it does not read whether the stitches look like the art.

**Why the ten pair sittings could not fix it.** Every instrument tested is ONE
number for the whole design, and a left/right pick carries no "where" or
"what". His 22 written reasons ([[kent-judging-rubric-2026-11-07]]) are all
local faults.

**What was built.** `digitizer/tools/defect_marks.py`: `capture-pro` (one job
per pro artwork, `PRO_SLUGS`, through `photo_corpus`'s worker so each carries
preflight), `kit` (pro logos, photos, Commons logos; render at 12 px/mm, the
pro's PES drawn beside it), `serve` (port 8736; launch.json `defect-marks`),
`report`. Per render Kent gives an absolute grade, pins each fault (15 kinds,
3 severities, note), ticks whole-design problems. The page never receives the
yardstick's reading; `kit.json` keeps it for `report`. Answers land in
`eye_pairs_out/defect-marks-1110/marks.json` (gitignored).

**How to apply:** the next yardstick is a set of fault readers, one per kind
Kent pins, each checked against his pin positions (mm, design frame), not a
new whole-design score. Run from a lane with `EMB_SCRATCH_KENT` and
`EMB_BRIDGE_PRO` set and `--tree` on the primary checkout (a lane has no rembg
venv and no pro files). Related: [[yardstick-pro-pair-2026-11-01]],
[[yardstick-dreamsim-2026-11-08]], [[photo-corpus-sxs-2026-10-27]].
