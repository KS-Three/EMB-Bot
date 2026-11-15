---
name: subject-loss-2026-11-14
description: Walkthrough item 2 — toadstool photo graded B 76 with "lettering" advice; A fixed (wording keyed on text tags), B measured — edge recall separates Kent's detail-lost rows but not beyond photo-vs-flat, metric only
metadata:
  type: project
---

**A (fixed).** `LETTERING_TOO_SMALL` judges every satin shape and always said
"lettering"; the toadstool (0 text tags) was told to simplify its lettering.
Now `_job_has_lettering` (any region with `text_candidate` / `text_cluster_id`
/ `word_id` / truthy `lettering_group`) picks the wording: "details" / "these
shapes" when none; `extra.lettering` True/False/None. Code, severity, grade
unchanged on every job.

**B (measured, `docs/subject-loss-2026-11-14.md`).** Off-line on the saved
`main-950855b` corpus capture against Kent's defect-marks grades of the same
renders (13 LOST = detail_lost/unrecognizable ticks, 5-6 GOOD): `edge_recall`
Somers' D +0.88 [+0.63, +1.00]; source-only control +0.28 (crosses 0); blob
readings and `element_dropped_frac` do not separate. **But** every GOOD row is
flat art and "class is not flat" alone reads +0.77 [+0.54, +1.00], and the
toadstool reads 0.940, only 0.009 under the lowest GOOD row. Shipped as metric
`subject_edge_recall` only (~0.2 s/job).

**Why:** walkthrough 2026-11-13 item 2; Kent 2026-10-02 no-warnings ruling.
**How to apply:** no threshold/finding/grade from this data. To settle it,
Kent must grade PHOTOS Good as well as bad (none is today), with the cut-off
pre-registered. `ARTWORK_ELEMENT_DROPPED` cannot see a recoloured subject.
Related: [[dropped-element-finding-2026-11-01]], [[preflight-score-2026-11-05]],
[[no-warnings-reaches-readouts]], [[photo-corpus-sxs-2026-10-27]],
[[defect-marks-sitting-2026-11-10]].
