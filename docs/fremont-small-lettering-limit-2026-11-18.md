# Hotel Fremont hat: EST 1895 / EAT STAY PLAY at 93 mm, thread limit and one sew-out-only choice (2026-11-18)

**Prime-grader pins:** "lumpy tube-like strokes, wrong letter forms" on the small tan lettering.
**Verdict:** mostly a thread-width limit plus a construction choice that is ROADMAP gate 1
(satin counters/floor need a sew-out). One real, narrow defect is named (the A) but no flag was
built: the fix is a re-spine and "Respine stays rejected (EAT read BAJ, #1510)". Nothing in the
engine changed. Pictures (ours only, no professional's file): `docs/renders/fremont-small-lettering-2026-11-18/`.

## Measured in the artwork at 93.3 mm (testdata/photo/logo_hotel_fremont.webp, tan ink)

| row | letters | cap height | hair stroke | thick stroke |
|---|---|---|---|---|
| EST 1895 | E S T 1 8 9 5 | 1.90-1.98 mm | 0.27-0.30 mm | about 0.45-0.7 mm |
| EAT STAY PLAY | 11 letters | 2.54 mm (T/Y 2.65) | 0.30 mm (serifs, crossbar) | 0.45-0.75 mm |

Every one of the 18 letters/digits is below the limits: stroke 0.27-0.30 mm is under a thread's
width (a bean line is about 0.4-0.5 mm; `bean_letter_max_stroke_mm` 0.5) and cap 1.9/2.5 mm is under
Kent's small-text floor of about 3.2 mm (`small-text-floor-2026-10-24`). As drawn they cannot be sewn.
That part is a limit.

## What is sewn (plan read, `tools.fremont_triage.run_arm`, main, 93.3 mm)

- The reset (ON) regrows them: EST 1895 x2.0 and tagline x1.62, caps **4.2-4.8 mm** (pro 4.5 / 4.6), polygon
  strokes measured 0.87-1.22 mm, gaps between neighbouring letters **0.59 mm** everywhere (word gaps
  0.9-3.6). Neighbouring strokes do not merge.
- All 21 letter shapes are tagged (`text_candidate`, `lettering_group`, `small_text_reset`), sewn by the
  bean-letter lane (`bean_letter_spines`, run kind, never the Column lane: stage7_sequence `tier == auto`
  and a bean letter returns runs, not columns). Ink stroke 0.425 mm <= 0.5 puts them there by rule.
- Stations: 881 stitches in 61 runs, length mean 0.49 mm (p10 0.30, p90 0.63). The spine is read from
  pixels, so it wobbles about 0.05-0.07 mm sideways (one art pixel), one eighth of the cord.
  Too small to be the lump; smoothing it would not be visible at print size.

## Why they still read as tubes

The polygon is a 0.9-1.2 mm stroke; the sewn thing is one 0.5 mm bean cord down its middle. The pro sews
0.86-1.26 mm bold satin. Switching these to satin columns means satin with 0.6 mm counters
(`small_text_min_counter_mm` 0.619) and a stroke at the 1.0 mm floor (`PHOTO_MIN_SATIN_WIDTH_MM`, never
tuned): cloth constants, ROADMAP gate 1, and already listed open in `fremont-room-2026-11-14`
("small satin counters ... needs a sew-out"). Existing OFF flags `small_print_floor` +
`lettering_columns_small_stem` were run at 93.3 mm: 15,459 -> 15,479 stitches, no visible change.

## The one real defect: A (EAT, STAY, PLAY)

The A's spine is apex -> one fused trunk -> fork to the feet: **no crossbar and no counter**, apex flag leans
left, so A reads as a lambda (`tag_spines.png`). The ink read at art resolution cannot separate the legs
above a 0.3 mm crossbar (counter about 0.7 mm in the art). The reset polygon does hold the counter. A fix
(re-spine from the grown polygon) is the rejected "respine" family and would need a sew-out to judge 0.6 mm
gaps in thread, so it is not built here. Serif feet also collapse to forks for the same reason.

## Not claimed

Whether satin would read better on a hat is unknown. The grader is unproven.
