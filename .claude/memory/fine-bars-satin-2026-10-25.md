---
name: fine-bars-satin-2026-10-25
description: fine_bars_satin (ON since Kent's flip 2026-10-26) — the pro satins every free-standing thin ink bar (5/5 artworks); ours rang them under the area floor. Aspect 2.5 was wrong (rope); STEM_MIN_ASPECT or under one cross. 37 of 38 targets cure; region kappa 0.905.
metadata:
  type: project
---

Small-symbols census follow-up, 2026-10-25 (Kent: "measure what the pro does
with small symbols and fine line art ... then propose a rule to build OFF").
Flag `cfg.fine_bars_satin`, predicate `columns.is_fine_bar`, tests
`tests/test_fine_bars_satin.py`, flip-sheet row in `tools/flip_sheet_renders.py`.

- **The rule:** non-lettering, one polygon, no hole, >= 2 x SATIN_MIN_CROSS_MM
  long, and a stem by STEM_MIN_ASPECT (6) OR under one cross across; its
  thread not within enclosed_by_garment_de00 of the garment nor an
  enclosed_background thread; not lighter (L*) than EVERY sewn region within
  0.25 mm. Touching nothing QUALIFIES (most targets lie on fabric). No new
  constant.
- **Why not aspect 2.5:** in ours' polygons it admitted 116 Fremont rope
  strands and Golden Tee's teal keyline fragment (region kappa 0.29). Rope
  reads aspect <= 3.8, short side >= 0.59; targets 0.38 or less.
- **Route:** `routes_to_run` skips the run rescue; `stitch_one` sends the bar
  down the ladder once (`fine_bar_trying`) and, if no satin comes out, sews
  today's ring with the run rung's exact call. Ahead of the hairline tier.
  Both flags ON: `small_solids_satin` tries first and keeps what it sews; a
  bar it reads but cannot sew (under a cross on the artwork) is still a fine
  bar — nearly every fine bar over a laid width IS an is_small_solid.
- **Measured (16 jobs, one digitize each on main 7995d515, replanned):** OFF
  reproduces main's md5 on all 16. Cures: To a T 6/6/8/10, Fremont
  separators 2+2 (sewn 1.08 mm on the hat: stage 5 does NOT clip them), drone
  S2c9243e0 + S86171fd3, MFab LC Sefb7e3ba. ONE fallback: mfab_hat Sb22b5123
  — that generation is photo-class and the classifier's photo_width_floor
  refuses under 1 mm. One unlisted cure: drone S4baeec3e (dark grey 4.71 x
  0.76, aspect 6.2). No construction change outside the cures; the 7
  controls byte-identical ON.
- **Gate 4:** region kappa 0.905 (n 584; 0.814 with the drone's uncertain
  blade pieces as positives). Pooled core 0.226 -> 0.357 (trivial "all ink
  satin" scores 0.38, so not evidence alone); dedup 0.233 -> 0.321; one file
  per artwork median 0.211 -> 0.294 (128 combos); without To a T 0.236 ->
  0.259.
- Widths 0.68-1.45 (pro 0.86-1.10); lengths shortened like the job's own long
  rules (satin end cutback), not by this flag.

**Why:** a parallel set of speed rules sewed half bold, half hollow ring.
**ON since 2026-10-26** (Kent, wave-3 flip sheet: "Fine bars as satin"; `PRE_FLIP`
names the OFF arm). Sheet: Machine hat 8,450 -> 8,378 st, rings 48 -> 42; Fremont
17,381 -> 17,359; drone 13,438/95 -> 13,372/94; MFab and Bridge unchanged.
**How to apply:** layout, judged in the preview; a 1 mm
satin bar holding on a cap is the sew-out question small_solids_satin
carries (gate 1). Related: [[small-text-floor-2026-10-24]].
