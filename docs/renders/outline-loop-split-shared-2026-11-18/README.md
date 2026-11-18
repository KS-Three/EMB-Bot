# `outline_loop_split_shared` OFF vs ON — 2026-11-18

Prime-grader fault: `L_becker_hat_large`, the outline where it dips between the
B and the E (pin x 21.0, y 8.5 mm; the E/R join near x 78-81, y 4-5 mm is the
same mechanism). Kent pinned this border 11-10.

## Diagnosis (stage named, number confirmed)

- The black outline is ONE region (`S92f2350b`, 1201 mm2, 5 holes = the five
  BECKER faces) sewn by `border_from_outline` at stage 7: one satin loop round
  each face hole (`stage6_border.keyline_runs`), crosses cut at the loop's width
  (2.57 mm) and never into a hole.
- Where two faces stand under two widths apart (the stem between the B and the
  E: 2.7-3.0 mm wide at y 8.5-9.5, `slice` of the region polygon) BOTH loops
  cover the whole stem. Plotted by column (`cols`): the B's loop (red) and the
  E's loop (blue) run side by side down the stem from y 7 to y 20 and both mitre
  into the V at the top. That is the knot. The stem WIDTH is faithful to the art
  (the sewn band is the region polygon); the fault is two columns where the
  professional's file sews one (his stem is a column of horizontal stitches butted
  to a border that carries on over the top).
- Fix, behind `cfg.outline_loop_split_shared` (OFF): each loop's crosses stop at
  the line the two holes share (`SPLIT_LAP_MM` 0.2 past it), so the columns butt.
  A cut under the satin floor (0.5 mm) is not made.

## The numbers

Becker large at 102.1 mm: 8,484 crosses read, **1,874 shortened**, mean 0.75 mm.
MFab hat: 7,060 read, 1,324 shortened (0.61 mm). Becker marine at 80 mm: 7,102
read, 1,788 shortened (0.63 mm). Stitch counts are unchanged to within noise
(16,265 -> 16,264; 20,549 -> 20,546; 10,672 -> 10,644): the thread count does not
fall, the crosses stop OVERLAPPING.

## 35 runs, flag OFF vs ON, md5 of `design["stitches"]`

The 9 committed pro jobs (`tools.prime_grader.population()`, each at its own size,
`tools.pro_baseline.JOBS` width and garment) and the 26 `corpus_scorecard.FIXTURES`
(Studio request, `target_width_mm` 80, `left_chest`):

**3 of 35 moved, 32 byte-identical.** Movers: `becker_hat_large`, `mfab_hat`,
`fx_becker_marine_logo`. **3 pictured** (all of them).

| run | stitches OFF -> ON | what changed (read from the plan) | by eye |
|---|---|---|---|
| becker_hat_large | 16265 -> 16264 | outline `S92f2350b`: 5 loops, every cross standing nearer a neighbouring face than its own cut at the shared line (1,874 crosses, stems and the letter-to-letter joins); loops' start phase and the hop order shift, so ~1,600 points move; no shape retagged, merged or dropped (182 -> 184 runs: two underlay / travel splits) | **slightly better** at the B/E stem (`becker_dip_B_E_*`) and the E/R join (closeup spot 2): the stem is two butting columns, no piled overlap; the V at the top is still a fan, NOT the pro's continuous border. The R's right edge re-phases (closeups 3-5): same look |
| mfab_hat | 20549 -> 20546 | the WHITE keyline loops (`S1a1cc475`): 1,324 crosses cut where two letter holes are under two widths apart (AND WELDING LLC's letters, the F-hyphen join); phase shifts, run count unchanged (300) | **no visible change** at print size; in the close-ups the white F/hyphen join gets a short tuck where it had a few crossing stitches, one curl appears at the top of the "N" in WELDING (spot 2), too small to call worse |
| fx_becker_marine_logo (80 mm) | 10672 -> 10644 | same outline mechanism: 1,788 crosses cut (stems), 156 -> 155 runs; the diff of the two renders at 14 px/mm is 0 mm2 (black over black) | **no visible change** at print size; the cut is under black |

**Worse:** nothing worse by eye. **Not what the pro does:** the V at the top of the
dip, where the B's loop and the E's loop turn their convex corners into each other,
is still a pile; closing that needs ONE border loop round the whole word (the pro's)
and the stem as its own column, not a per-face loop.

Files: `<run>.png` = ORIGINAL | BEFORE | AFTER; `<run>_closeup.png` = BEFORE left,
AFTER right at 44 px/mm (Becker: the pin, the E/R join, then the three largest render
diffs); `becker_dip_B_E_before_60pxmm.png` / `_after_60pxmm.png` = the pin at 60
px/mm. Renders are ours; no render of a professional's file is committed.
