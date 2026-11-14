---
name: reset-one-baseline-2026-11-13
description: "2026-11-13 — Kent's 'letters jumped out of line' (+Jakarta, Bukit Asam, graded Bad) = the small-text re-set grew a LOWERCASE line's two height classes as two lines; `small_text_reset_one_baseline` + `text_cluster_solid_guard` built OFF; ring/satin faults named, not fixed"
metadata:
  type: project
---

# Re-set on one baseline, and a row of squares is no word — 2026-11-13

**What Kent pinned (sitting 11-12, `eye_pairs_out/defect-marks-1112/`).**
lt_jakarta: tagline letters "jumped in elevation, not inline"; lt_bukit_asam
(ruins): "e, o, n jumped higher". Both Bad. Traced by eye with `debug_dir`
at kit size (80 mm left_chest, the Studio request); stage 4 is intact in both,
the fault enters in the small-text re-set (`enlarge_small_text`, between
stage 4 and 5). Sheets: `digitizer/eye_pairs_out/reset-scatter-1113/`.

**Cause 1 (row split).** The tagger keeps one line at one size
(`LETTER_HEIGHT_RATIO` 0.8), so a lowercase line is TWO clusters: x-height
letters (Jakarta 2.54 mm) and ascender/descender letters (3.33). The re-set
grouped lines on the same 0.8 and grew each class as its own line, the other
its obstacle. Jakarta: x-height baseline 15.96 -> 17.06 (+1.10, held its top
against its own i-dots, 0.375 mm "near"), ascenders 15.9 -> 12.3 (-3.6, slid
the full MAX_SHIFT_CAPS), the grown r moved 5.43 mm aside as a "bar", the o
counters carried off as the other line's inner pieces. Bukit: b-y-d tall
enough (3.68 >= 3.6), skipped; e-o-n re-set alone, slid UP 2.53 mm.
**Fix** `cfg.extra["small_text_reset_one_baseline"]`: classes sharing a band
(`_one_line`) merge into one cluster (`_merge_baseline_classes`, cap = taller
class), core-dropped members come back, word spaces read on the x-height, a
thin letter is no bar (`BASELINE_BAR_CAPS` 1.1), inner pieces read on the
line's box (i-dots), a class beside a tall-enough line is left as drawn.
ON Jakarta: every foot 15.79-15.89 (art spread x1.2), descender = depth x1.2,
20 letters in art order. Bukit: e-o-n stay as drawn.

**Cause 2 (merged squares).** Not stage 2-4 and not pull: the tagger made a
"word" of the mark (5 squares + corner triangle), the re-set grew 3 squares
x1.52 + 0.52 mm a side and closed their 2.71 mm gaps to 0.59; satin needle
paths touched (0.000 mm). **Fix** `cfg.extra["text_cluster_solid_guard"]`:
a cluster 3/4 of whose members are solid (stroke >= 0.45 of the longer side)
is not tagged. Per-member was wrong: a small o with a dropped counter reads
0.65; all-members was wrong: the triangle reads 0.33. ON: fill, gaps 2.2/2.1.

**No regression:** Fremont hat/patch, ProSeal hat/beanie, MFab hat/lc
replayed both ways from one stages-0-4 pass: 0 shapes differ (all-caps
lines are one height class; the re-set acted on Fremont and ProSeal).

**Named, not fixed (other lanes):** Bukit ring gap 0.417 mm art, unchanged
at stage 5, needle paths 0.000 = stage 6 satin rails; its dots lost at stage
4. Jakarta's dotted edges/rounded stem tops = satin rail penetrations/ends.

Traps: `inspect.getsource` tests fail when the file is edited mid-run; the
Bash `python - <<EOF` hook blocks even an empty heredoc. Related:
[[reset-grow-away-2026-10-26]], [[small-text-reset-2026-10-21]],
[[eye-first-diagnosis-2026-11-13]], [[defect-marks-sitting-2-2026-11-11]].
