---
name: reset-tight-word-space-2026-11-16
description: USAID tagline sewed "THEAMERICAN" (gap 0.484 of cap under the 0.5 floor); `small_text_reset_tight_word_space` reads the floor at 0.35; census 19 lines/114 gaps: only that gap moves, 7 of 8 reaching jobs byte-identical; built OFF, flip is Kent's
metadata:
  type: project
---

Fault: the small-text re-set (`small_text._words`) calls a gap a word space at
`>= max(2.0 x median gap, 0.5 x cap)`. USAID's "FROM THE AMERICAN PEOPLE"
(cap 3.23 mm, median 0.417 mm, 100 mm) has THE | AMERICAN at 1.562 mm = 0.484
of cap = 3.75x the median, 0.053 mm under the floor, so the re-set closed it
and sewed "THEAMERICAN".

Rule: `PipelineConfig.small_text_reset_tight_word_space` (default False) reads
the floor as `WORD_SPACE_CAP_TIGHT = 0.35` (a quarter em over a 0.7 em cap);
the 2x-median term is unchanged, so tracked text (gaps 0.4-0.8 cap at ~1x
median) and kerned lines (median ~0) stay as they were.

Measured (lane on main 362faeab, 62 jobs: 22 pro_baseline, logo batches 1-3,
Commons): 8 jobs reach `_words`, 19 lines, 114 gaps. OFF vs ON vs a 0.40
floor: the SAME single gap moves in both arms (USAID line 0 gap 6, 0.484 cap,
3.75x median). USAID stitches 12175 -> 12136, trims 47 -> 47, jumps 82 -> 83.
The other 7 jobs (Fremont hat and patch, Drone, ProSeal beanie and hat,
Bukit, Jakarta) are md5-identical OFF vs ON. Pictures stay local (public repo).

Built OFF, flip is Kent's. Tests: `tests/test_small_text_tight_word_space.py`.
