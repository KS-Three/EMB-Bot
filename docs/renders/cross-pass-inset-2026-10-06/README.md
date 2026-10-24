# `cross_tatami` at its own 0.4 mm inset — 2026-10-06

Underlay only, red; top stitching faint grey. Same three logos, 80 mm, as
[`../cross-tatami-underlay-2026-10-05/`](../cross-tatami-underlay-2026-10-05/README.md),
whose `*_cross.jpg` are the same pass at the edge run's 1.0 mm. Both with
`blend_fallback_underlay` ON.

| file | |
|---|---|
| `fremont_inset04.jpg` | Hotel Fremont patch |
| `bridge_inset04.jpg` | Bridge Bar |
| `drone_inset04.jpg` | drone thermal badge |

## The probe Kent picked from

A throwaway probe (monkeypatched, not in the repo) sewed the pass five ways
and read each DST back with `tools/pro_fill_underlay.py`. Underlay under
fills as a share of the fill's thread; the professional's median is 16.1%.

| variant | Fremont | Bridge Bar | drone | trims F / B / D |
|---|---|---|---|---|
| inset 1.0, largest piece (shipped 10-05) | 12.3% | 10.0% | 8.2% | 39 / 113 / 139 |
| inset 1.0, every piece | 12.3% | 10.1% | 9.6% | 39 / 113 / 145 |
| inset 0.6, every piece | 13.6% | 12.9% | 12.1% | 34 / 109 / 154 |
| inset 0.4, every piece | 14.3% | 14.4% | 13.9% | 34 / 113 / 151 |
| inset 0.2, every piece | 15.2% | 16.1% | 15.5% | 39 / 118 / 158 |

Fill area within one row pitch of the pass (his median 0.94), 1.0 → 0.4 →
0.2: Fremont 0.81 → 0.88 → 0.88, Bridge Bar 0.42 → 0.66 → 0.74, drone
0.66 → 0.78 → 0.75.

**Kent picked 0.4 mm.** Built as `machine.UNDERLAY_CROSS_INSET_MM`, this
style only; every other underlay style keeps `UNDERLAY_INSET_MM` 1.0.
"Every piece" was NOT built: it moved nothing on two logos and 1.4 points on
the third for six trims.

## Through the real code, 0.4 mm

| case | stitches | trims | share of fill thread | read back: pitch / median stitch / angle |
|---|---|---|---|---|
| fremont | 14,642 | 34 | 14.3% | 1.00 / 2.53 / 89.8° |
| bridge | 18,697 | 113 | 14.4% | 0.99 / 2.70 / 88.6° |
| drone | 20,704 | 151 | 13.5% | 1.00 / 2.50 / 89.9° |

Against the same logos on the fabric preset's `edge_run`: stitches 13,779 /
18,083 / 19,283, trims 43 / 98 / 131.

## A correction to the 10-05 README

It said the bare patch low in the middle of `fremont_cross.jpg` was the
largest-piece-only rule. **It was not.** The probe's "every piece" row leaves
Fremont unchanged, and at 0.4 mm the patch is sewn (`fremont_inset04.jpg`):
it was the 1.0 mm inset closing up around the tagline's small letters.

## Why the median stitch stays near 2.5 mm

Measured, fills only: the pass's rows are short. Median row 7.2 mm on
Fremont, 2.8 on Bridge Bar, 3.6 on drone; 54%, 82% and 80% of rows are under
8 mm, and a quarter or fewer of the stitches are a full 4.0. These grounds
are cut up by lettering. The professional's 3.99 mm is on larger, cleaner
fills; no inset closes that.

## Not known

- **Whether 0.4 mm shows past the fill's edge on cloth.** Not sewn. The
  pass is inside the sewn outline by 0.4 mm by construction; pull is what
  decides, and only fabric says.
- The professional's own inset. The classifier's fill edge is about 0.3 mm
  fuzzy, too coarse to choose between 0.2 and 0.6.
- The browser engine's pass is still not inset at all.
