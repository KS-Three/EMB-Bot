# The wide-column policy — satin between 5.0 and 6.5 mm (quality review item 4)

**Status: BUILT and MEASURED 2026-09-09, Kent's pick after #433.
`cfg.wide_columns`, DEFAULT OFF, byte-identical off; the measurement (§4,
scope-history's wide-column entry) says the band's blocker is the
decomposition, not the width, so the flip waits on item 5's next PR. Flipping it is Kent's: the ceiling is a
physical constant read from five files sewn on garments (gate 1's own
evidence class), and the look is his.**

## 0. What already governs this — read before changing the plan

- **Raising `SATIN_MAX_WIDTH_MM` 5.0 → 7.0: both coherent routes break
  something measured** (DOCTRINE 2026-09-02). Coupled, the per-station
  overlap guard moves with it and crosses physically overlap again (18
  failures); split, the classifier admits bands the emitter refuses to
  cover and artwork sews bare (13). "Any route past 5.0 needs the overlap
  guard rebuilt on real local geometry — better discrimination, not a
  bigger number." This plan builds that guard first and moves the number
  second, and keeps the classifier and the emitter on ONE number by
  threading it, never by a second constant.
- **`machine.SATIN_MAX_WIDTH_MM` is load-bearing in FOUR places**: the
  classifier (stages 5 and 7 via `cfg.satin_max_width_mm or ...`),
  `_rail_points`' per-station cap, `_stroke_underlay`'s oversize trigger
  and its leg clamp. All four follow the flag together.
- **The cap is not what separates us from the pro in satin SHARE** — the
  pro's own p90 column is 5.00 mm and the gap is segmentation (DOCTRINE
  2026-09-06). That ruling stands and this plan does not claim it: the band
  above the cap is worth MARINE's letters at hat and chest sizes (review
  §2b, §2c), not the corpus's satin share.
- **`SPLIT_SATIN_ABOVE_MM` = 5.0 (corpus law) carries crosses over 5.0 mm**
  as split penetrations at fill pitch. The policy relies on it and does not
  move it.
- **Gate 1.** The ceiling's number comes from five commissioned Becker
  files sewn on garments — the evidence class that settled `FILL_ROW_MM` —
  and the DST lesson's test applies to how the gate is read: no machine
  owner answers "what width does a pro sew whole" faster than the sewn
  files do. The flag still ships OFF: reading a number off sewn files
  settles the number, and whether to ship it is Kent's.
- **Goldens re-capture on ubuntu-latest with the pre-change proof** if any
  flat-lane key moves. Off is byte-identical, so none moves in this PR.

## 1. The gap

The pro sews MARINE at 95.7 mm as whole satin crosses (rendered:
`docs/renders/wide-columns-2026-09-09/pro_marine_M.png` — the M's stems are
rail-to-rail crosses, no mid-penetration). In the MARINE bands of
`becker_hat_polo_large_beckers_logolc.dst` the crosses read **p50 4.8–4.9,
p90 5.0–5.2, p99 6.2 mm, max 7.2–8.5; 11–18.5% over 5.0, 0.6–0.7% over
6.5** (`_crosses` on the file's turn triples, 2026-09-09). We refuse those
letters at 100 mm on `dt_p90_cap`:

`tools/wide_columns.py --widths 80 100` over the corpus at the default
config — every region the shipped classifier refuses on width, and what a
6.5 mm ceiling admits (region-level doubled p90 of the medial radius):

| fixture | mm | refused on width | admissible at 6.5 | the admissible shapes (area, p90, typical width) |
|---|---|---|---|---|
| becker | 80 | 2 | **2** (260 mm²) | `Sf795e8d1` 130.4 / 5.77 / 3.58; `Saee8fbe5` 129.7 / 5.31 / 3.38 |
| becker | 100 | 4 | **4** (738 mm²) | `Sf62099db` 211.4 / 6.48 / 4.04; `Sa587cbf9` 184.0 / 5.27 / 3.51; `Sd77c18ad` 178.7 / 5.52 / 3.59; `S35d83e6d` 164.2 / 5.82 / 3.81 |
| whitebg / alpha | 80 | 4 | 1 (378 mm²) | `S09c5bd0d` 377.8 / 6.12 / 6.01 — the goldens' fixtures, OFF byte-identical |
| whitebg / alpha | 100 | 4 | 0 | — |
| drone | 80 | 1 | 1 (153 mm²) | `S0bae4b0d` 152.6 / 6.19 / 3.82 |
| drone | 100 | 1 | 0 | `S80e95c28` 2594 mm² at p90 12.08 stays fill |
| fremont, enthusiast, gaulke (80) | — | 0 | 0 | — |
| gaulke 100, sunset, meadow | — | 1–4 each | 0 | photo-class blobs at p90 8.7–20 |

MARINE's fifth letter, `Sdd5f27fb` (210.9 mm²), is refused on
`dt_irregular`, not width — its per-stroke p90 reads 7.47–8.02 — and stays
tatami under this policy. So the band is narrow and exactly what §2b
named: the MARINE letters at hat and chest sizes, one 6 mm shape on the
golden fixtures, one drone ribbon.

The refusal statistic is the doubled p90 of the medial radius. On a letter
it is inflated by the junction blobs (the M's and N's diagonals meeting
their stems), which is why two MARINE letters read 6.75–8.02 while the pro
sews their stems at 5: a junction-aware width statistic is the follow-up
this plan names in §8, not something it does.

## 2. Why the current pipeline cannot do this itself

The classifier's ceiling and the emitter's per-station cap are one number
and must stay one number, and that number also stands in for a guard
against something else entirely: at an apex whose local corridor is 9 mm
the crosses fan and physically overlap (2,580 crossing pairs, a 9.57-layer
coverage spike, 2026-08-05), and the flat cap at 2.5 mm half-width happens
to keep that fan short. Raise the number and the fan comes back. The guard
has to be about the thing that overlaps — the column bending faster than
its width allows — not about the width.

## 3. The design

`cfg.wide_columns: bool = False`. ON:

1. **The fold guard** in `_rail_points`: at every station the half-width
   is also capped by `_FOLD_FRAC × R_i`, where `R_i = s_i / |Δθ_i|` is the
   local radius of the spine's curvature read from the smoothed cross
   angles `_cross_angles` already lays (`s_i` the station's spine step,
   `Δθ_i` the cross-angle change across it). A cross wider than the bend's
   radius puts its inner rail BEHIND the previous one — that is the fold,
   and every crossing pair the 2026-08-05 measurement counted is one. Below
   `R` the inner rail merely crowds, which `_short_stitch_guard` already
   handles. `_FOLD_FRAC` is read off the instrument (§5): the largest
   fraction at which no fixture's crossing pairs or `coverage_max` rise
   above the flat cap's.
2. **The ceiling** `SATIN_WIDE_COLUMN_MAX_MM = 6.5` replaces
   `SATIN_MAX_WIDTH_MM` in all four places when the flag is on — the
   classifier via `cfg.satin_max_width_mm`'s existing plumbing, the emitter
   and underlay via a `max_width_mm` argument threaded from `satin_shape`
   down, so the number the classifier admitted is the number the emitter
   sews at. 6.5 is the pro's p99 on MARINE rounded up to the band edge the
   review named; 0.6% of the pro's crosses sit past it.
3. Crosses over 5.0 mm split as they do today (`SPLIT_SATIN_ABOVE_MM`).

OFF, no line of this runs: byte-identical.

## 4. What it should move — predictions, and what happened

- MARINE at 100 mm: the three letters whose p90 sits in (5.0, 6.5] sew
  satin; the two at 6.75–8.02 do not. **Four do** (`Sf62099db`'s
  region-level p90 is 6.48; the 7.33 was per-stroke); `Sdd5f27fb` stays
  tatami on `dt_irregular`. At 80 mm both cap-hitters sew satin — held.
- Self-crossing pairs on `logo_alpha`'s `Sf5200f3f` stay at 0 under the
  guard — **held, and 0 without the guard too** at every ceiling to 8.0:
  the 2026-09-02 premise has moved. Where the guard is load-bearing is
  Becker's bends at 80 mm (coverage_max 7.07 → 5.08). Becker at 100 mm
  gains 251 crossing pairs ON — at the letters' feet and junctions, which
  no width guard is about.
- `ARTWORK_UNCOVERED` on Becker does not rise where a letter turns satin —
  held at 80 mm, missed by 1.0 mm² at 100 (0.5 → 1.5); drone's admitted
  wing 0.5 → 7.0, not predicted.
- Stitches fewer on the admitted letters — held (−5% at 80, −13% at 100).
  Trims were not predicted and are the largest cost: +17 and +18, 4–7 per
  letter against the pro's ~2.

## 5. Instrument first — `tools/wide_columns.py`

The band table above; with `--compare`, OFF against ON per fixture and
size: stitches, trims, sewn tier per shape, satin self-crossing pairs (a
windowed count of the 2026-08-05 measurement), preflight's `coverage_max`
and uncovered. `_FOLD_FRAC` is swept on it before it is fixed.

## 6. What must not regress, with its fixture

- `test_satin_crosses_do_not_self_overlap_across_a_wide_junction`,
  `test_a_wide_oversize_satin_stroke_does_not_block_on_underlay_glue`
  (`coverage_max` < 5.0 on alpha) — run both ways.
- `test_promotion_cannot_reopen_the_width_cap` and every direct
  `classify_ribbon(..., machine.SATIN_MAX_WIDTH_MM)` call — the constant
  does not move.
- The flat-lane goldens and pushcomp pins — off is byte-identical.

## 7. Size and staging

| PR | content | size | gate |
|---|---|---|---|
| 1 | this: the flag, the fold guard, the threaded ceiling, the instrument, the OFF/ON footprint, renders of MARINE | ~200 lines + tests | flipping is Kent's (gate 1, read from sewn files) |
| 2 | a junction-aware width statistic for the classifier (the two MARINE letters at 6.75–8.02) | medium | none |

## 8. Decisions for Kent

- The flag stays OFF on this measurement: MARINE at 100 mm is satin at
  −13% stitches and looks worse (the renders), because the letters
  decompose into fanning, crossing columns with 4–7 trims each. The band
  is worth flipping once item 5's next PR (serifs as their own columns, a
  junction cover on the clustered graph) sews a bold letter the way the
  pro's M is sewn. Flip now anyway, wait for that PR, or ask for the
  sew-out of a 6.5 mm column first — yours.
- PR 2 of this plan (a junction-aware width statistic) after item 5's PR.
