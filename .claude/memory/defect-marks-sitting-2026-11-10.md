---
name: defect-marks-sitting-2026-11-10
description: Kent 11-10 asked why his eye and the yardstick differ; `tools/defect_marks.py` asks him where and what instead of left or right; he sat it 11-10 (15 items, 95 pins): smooth edges and closed/merged letters lead, all 4 photos Terrible
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

**The sitting (Kent, 2026-11-10; record `docs/defect-marks-2026-11-10/`,
with `marks.json` and `kit.json` committed, no pictures).** 15 items: 11 pro
logos and only 4 photos (the kit was built before the 39-row capture finished).
- Grades: Good 4, Okay 3, Terrible 5, none 3; no Great. All 4 photos Terrible,
  "can't tell what it is" + "not for thread", 2 pins between them.
- Against preflight on 12 graded items: same grade 3, yardstick kinder 6,
  harsher 3. Becker hat Okay vs A 100; Bridge hat Okay vs F 0; landscape photo
  Terrible vs B 76. Spearman +0.41 (n 12), +0.32 logos only (n 8): instrument
  readings, n too small to lean on.
- 95 pins: letter_shape 14, missing 10, mushed 7, other 7, jagged 5, wavy 5,
  stray 4, gap 4; 25 with no kind (22 are his "same as pin 1" shorthand on
  Golden Tee and Tires).
- The session's reading of his notes (keyword counts, not his words): edges
  that should be smooth = 17 pins on 7 items spread over 7 kinds; letters that
  close up or merge = 15 pins on 6 items.
- The page server stopped mid-sitting (the app stopped the session's preview);
  marks survived, see the record's "Gaps".

**How to apply:** the next yardstick is a set of fault readers, one per kind
Kent pins, each checked against his pin positions (mm, design frame), not a
new whole-design score. Check a reader against his NOTE, with the kind as a
hint: he files one fault under several kinds. Start with smooth edges and
closed/merged letters. The photo half needs a different question: pins have
nothing to point at on a render he cannot recognise. Run from a lane with `EMB_SCRATCH_KENT` and
`EMB_BRIDGE_PRO` set and `--tree` on the primary checkout (a lane has no rembg
venv and no pro files). Related: [[yardstick-pro-pair-2026-11-01]],
[[yardstick-dreamsim-2026-11-08]], [[photo-corpus-sxs-2026-10-27]].
