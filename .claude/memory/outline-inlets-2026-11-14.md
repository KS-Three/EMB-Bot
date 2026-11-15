---
name: outline-inlets-2026-11-14
description: "2026-11-14 — Kent's 'shape detail lost' pins (class 3, 18 pins) traced: 9 = satin ends at flat edges (apex/flat-ends lanes), 3 = an outline INLET the polygon keeps but thread sews over; `outline_inlets_kept` built OFF"
metadata:
  type: project
---

Census class 3 ("shape detail lost": blob, rounded points, simplified inner
shape), 16 groups / 18 pins on 10 designs, traced on main `f49d5b1a`
(`docs/shape-detail-traced-2026-11-14.md`; pictures gitignored in the
primary's `digitizer/eye_pairs_out/detail-1114/`).

- **9 pins: satin end, corner or tip at a flat edge** (and_pizza, k_line,
  dot_music #2). Already traced in `docs/satin-flat-ends-2026-11-14.md`;
  `lettering_columns_apex_cut` + its guard and the flat-end construction own them.
- **3 pins: an INLET of the outline** (gear tooth gaps on Ahora, the open
  beak on crest #3, the notch on dot_music #1). Stage 4's polygon KEEPS it;
  stage 6 satin rails (a smoothed spine offset: median 5, 4 passes) run over
  it, and stage 5 fill growth (0.3 mm from both walls + the band at the
  mouth) closes it.
- 3 pins the pro redraws (Becker A counter at 1.42 px/mm, Bridge's collar
  nub the art lacks, Fremont's rope as one satin); 2 low_poly (narrow facets
  as satin + colour cap); 1 letter junction; 1 photoreal (Drone).

Built OFF: `cfg.extra["outline_inlets_kept"]` (`digitizer_core/outline_inlets.py`):
inlet = closing the outer ring with a 1.0 mm disc, pieces >= 0.5 mm across
and >= 0.1 mm2. Fill growth stays out of them and their mouths; a satin whose
thread covers >= half of one AND inlet area >= 3% of the shape is re-planned
as fill (copy, `tier="fill"`); letters and hand-set tiers never move. The 3%
gate exists because the first build turned Becker's black border (share
0.002, a satin band in the pro's file) into a fill; the gear is 0.104.

**Why:** Kent 11-14 "exactly like the pros"; these are geometry, not gate 1.
**How to apply:** sheets show the shape right but Ahora's 1.1 mm ring as
short fill rows reads rougher than the OFF satin: a flip is Kent's, from the
`art | OFF | ON` sheets. Satin rails that follow teeth were NOT built: the
envelope drops short reaches on purpose (`_drop_short_reaches`). Related:
[[fat-ink-ledger-2026-11-14]], [[jag-source-2026-11-13]].
