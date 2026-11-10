---
name: thread-match-leftovers-2026-11-10
description: "2026-11-10 — defect 28's last THREAD_MATCH_POOR blocks (bridge_bar 3, screenshot 1, photo stub 0722 1, per garment) are all CHART LIMITS: best whole-chart thread still 10.6-29.4 dE00 per pixel; no flag built"
metadata:
  type: project
---

# Defect 28 leftovers: chart limits (2026-11-10)

Kent picked these after [[blend-shade-median-2026-11-09]]. Measured on main 333147fd
with the grader's own estimator, the median of per-pixel CIEDE2000, against the
whole 398-spool Isacord chart (`tools/thread_chart_floor.py`):

- bridge_bar 0020: 19.3, best 1375 at 11.4. The black ring takes JPEG chroma
  bleed from the yellow disc.
- bridge_bar 3830: 11.6, best 4410 at 11.1. bridge_bar 4442: 10.6, already the
  best. Thin anti-aliased cyan letters and teal waves on yellow.
- screenshot 0111: 19.8, best 1776 at 12.2. Pen hatching runs L* 2-77; the
  median colour is 4174 at 1.0 but that spool is not loaded.
- photo_subject_stub 0722: 33.7, best 0111 at 29.4. The stub is uniform noise
  and sews one spool, so it is scored raw.

No thread clears 10 on any row, so **nothing was built**. A re-snap flag clears
0 blocks. Scoring excess over the best CHART thread would clear all six flat
blocks (to 2 warns), but that re-makes Kent's "flat stays raw" ruling
([[thread-match-excess-gradient-2026-10-29]]). It is priced, not proposed.
Doc: `docs/thread-match-leftovers-2026-11-10.md`.
