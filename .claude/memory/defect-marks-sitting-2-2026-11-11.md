---
name: defect-marks-sitting-2-2026-11-11
description: Second defect-marks sitting, Kent 11-11: 21 Commons logos, 115 pins, built as a hold-out for the letter-fault reader; frozen rule picked 30 pins on ONE logo (26 hit vs 0.13 chance) = no verdict; his words changed (extra in-fill, inconsistency, missing, flow)
metadata:
  type: project
---

**Why it was sat.** [[letter-fault-reader-2026-11-11]] cleared chance on 14
pins from 6 logos, and the same pins had chosen its rule. Kent, 2026-11-11,
asked whether to pin fresh designs for it: "Yes, build kit".

**The kit.** `eye_pairs_out/defect-marks-1111` (gitignored): the 21 Commons
logo rows of the photo corpus from the finished capture
`corpus_runs/main-950855b`, photos left out on purpose. Built by pointing
`defect_marks kit --corpus` at a folder holding only the logo rows' job files.
Served by launch.json `defect-marks-1111`, port 8737. Record:
`docs/defect-marks-2026-11-11/` (`SITTING.md`, `marks.json`, `kit.json`,
hold-out pins and score, the driver; no pictures).

**The sitting (Kent, 2026-11-11).** All 21 graded: Great 2, Good 4, Okay 1,
Bad 5, Terrible 9. 115 pins on 15 items, 61 with no kind (56 are his "same
issue" shorthand on the silhouette logo and the kanji seal).
- Against preflight: same grade 6, yardstick kinder 10, harsher 5; Spearman
  +0.18 (n 21). Distressed grunge Terrible vs A 100 again.
- Against his own 10-28 grades of the same artworks: Spearman +0.77, same 9,
  worse now 11, better 1. Not a test-retest (tree, render and page all
  changed).
- The session's reading of his notes (not his words): extra stitches in
  lettering 30 pins (silhouette); the same feature treated differently in
  different places 28 + 3 pins (kanji seal, devanagari) plus single notes on
  three more; random black spots 7 (low poly); pieces missing; "no flow".
  Closure words ("spacing", "merge") barely appear.

**The hold-out (instrument reading, one item).** Reader and rule as merged in
`79fa7646`, nothing changed, run after his marks were final. The rule selects
30 pins, all on `C_silhouette_logo` (one "hard to read" note and the 29 bare
pins it covers). Reader: stitches matched, 65 flags; 26 of 30 pins hit at 3 mm
vs 0.13 chance on stitched area. **No verdict:** one item collapses the
item-clustered interval to a point, 30 pins are one judgement, and 64 of 65
flags sit in the same lettering band as the pins, so it shows "found the bad
lettering", not "found the wrong letter". The harness's edge-band null read
0.00 again (as on Bridge): suspect, unused.

**How to apply:** a fresh sitting does not guarantee pins for a reader; the
pin rule is written in the first sitting's vocabulary and his words move with
the artwork. To replicate a reader, choose artwork that carries its fault, or
score flags against region-level judgements. The next themes with pins behind
them are inconsistency of like features and extra in-fill. The reader's `run`
takes pro jobs only; `docs/defect-marks-2026-11-11/run_reader_corpus.py` runs
it on corpus rows (set `PYTHONPATH` to the lane's `digitizer/`, pass `--tree`
equivalent = the primary). One note of his is a request: investigate border
stitches that carry a colour change (low poly, pin 2). Related:
[[defect-marks-sitting-2026-11-10]], [[edge-fault-reader-2026-11-10]].
