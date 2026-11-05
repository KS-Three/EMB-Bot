---
name: preflight-score-2026-11-05
description: The 0-100 preflight score ALREADY EXISTS (and the Studio shows it); the 11-05 "add a metrics-only stitch-out score" task was scoped on a wrong premise, so only the mapping comment + pins + tool columns were added
metadata:
  type: project
---

Kent ruled 2026-11-05, after the free-digitizer survey (openstitch ships a
"stitch-out score /100"): build the score metrics-only, no Studio display, no
Show/Fix. The task was handed to a worker as "add a numeric score". **It was
already there.** Do not build a second one.

What exists (main 67319af2, before this note):
- `run_preflight` returns `score` = `max(0, 100 - sum(_DEDUCT[severity]))`,
  `_DEDUCT` = info 0 / warn 12 / block 30; `grade` is `_grade_for(score)`
  (A>=90, B>=75, C>=60, D>=40, F). Same arithmetic, so they cannot disagree.
- `metrics.raw_score` is the unclamped value (`tests/test_raw_score_metric.py`).
- The service returns the whole report as `preflight`; `score` is in it.
- **The Studio already prints it**: `app/src/ui/QualityReport.svelte:189`
  renders `{e.preflight.score}/100` beside the grade, and
  `DigitizePanel.svelte:447` reads it. That sat against the 11-05 "no Studio
  display" ruling, so the director asked Kent. **Kent: "Keep as is."** So the
  ruling reads: no NEW display; the existing `score/100` and grade stay.
  Nothing in `app/` changes and there is no removal PR.

What this change added (no behaviour change, `app/` untouched):
- a module comment in `digitizer_core/preflight.py` ("THE STITCH-OUT SCORE")
  with the mapping, the floor (0), the ceiling (100) and the block cap
  (k blocks score at most 100 - 30k: one block never above C, two D, three F);
  `_raw_score` / `_grade_for` helpers so the arithmetic lives once;
- `tests/test_preflight_score.py`: exhaustive warn x block monotonicity, band
  edges, the block cap, and the 52-row `corpus_scorecard_baseline.json`
  (every A above every B, ...); `test_service.py` pins the served pair;
- score beside the grade in `flip_sheet.py`, `photo_corpus.py` (raw) and
  `pro_pair.py`; `corpus_scorecard`, `preflight_report`, `thread_match_floor`,
  `floor_depth`, `element_drop_census` already printed it.
`bench_free_digitizers.py` prints no preflight grade, so nothing to add there.

Baseline table (52 rows, `corpus_scorecard_baseline.json`): A 9 (100), B 18
(76-88), C 7 (64-70), D 6 (46-58), F 12 (0-22). Bands do not overlap.

**Why:** a session scoped from a survey line, not from the code. **How to
apply:** before "adding" a metric to preflight, grep `run_preflight`'s return
and the Studio for it first. Related: [[no-warnings-reaches-readouts]].
