# Attributing the corpus scorecard baseline — 2026-11-05

**Verdict: recaptured at `292418a8` on cloud Linux (GitHub Actions
`ubuntu-latest`, run 42148952004, 25 min wall, the new `Corpus scorecard`
workflow; stamped 2026-11-06 UTC, the evening of 2026-11-05 in Kent's time).
Thirty of 52 rows moved against the 2026-10-05 ruler (`d000e370`); 19 rose a
letter band and 10 fell; mean score 61.8 → 71.9. Every mover is attributed below to a
named flip, to a dated measurement that already recorded it, or explicitly as
undiagnosed drift — by evidence, not by bisection: 546 commits touched
`digitizer_core/` between the rulers, and the intermediate 2026-10-29
measurement splits the interval in two.**

Read the grade as what it is: preflight-finding conformance. ROADMAP phase 1
is open because no instrument, this one included, agrees with Kent's eye
(`docs/yardstick-pro-pair-vs-kents-eye-2026-11-01.md`); gate 4 forbids a
quality claim on it. The ten-point rise is almost entirely one check going
quiet on the gradient lane, which is real colour work (defect 28) and not
evidence that the sewn designs look better.

## The state of the ruler

| | |
|---|---|
| Old ruler | `d000e370`, 2026-10-05 (scope-history 10-05) |
| New ruler | `292418a8`, 2026-11-05 — `origin/main` after #1254 (`fb682ef9`) plus the workflow file; the pipeline tree is `fb682ef9`'s |
| Commits touching `digitizer_core/` in between | 546 (all), 24 first-parent after the 10-29 anchor |
| Rows | 52 (26 fixtures × 2 garments), 0 errors in either ruler |
| Rows unchanged in grade and score | 22 |
| Rows up a band / down a band / score only | 19 / 10 / 1 |
| Grades, old → new (A/B/C/D/F) | 9/18/7/6/12 → 10/20/8/10/4 |
| Mean score | 61.8 → 71.9 (the WSL pass read 71.7: one row, below) |

### Where the numbers come from, and why they agree

Three independent scorings of the same tree family bracket the result:

1. **WSL box, 2026-11-05, `origin/main` e9205673** — `/root/scorecard_pool.py`,
   6 workers, 18.9 min; no rembg venv, Tesseract 5.3.4, Python 3.12.3. This is
   the box COOKBOOK says a `diff` may run on and a capture may not
   (`photo_grass_macro`'s two rows are the machine's). Its 52 rows are the
   per-row evidence below.
2. **Cloud Linux capture, 2026-11-05, `292418a8`** — the committed file. Its
   rows against the WSL rows: **51 of 52 identical in grade, score and
   findings.** The one difference is `logo_hotel_fremont` hat_front, F 28 on
   Linux against F 16 on WSL — the WSL read added `LETTERING_ILLEGIBLE:warn`,
   an OCR verdict, and nothing else moved on the row; the Linux F 28 is the
   10-29 anchor's figure exactly. `stitch_count` differs on 4 rows by at most
   1.06 % (platform numerics, no finding moved).
3. **The 2026-10-29 anchor** — `docs/thread-match-gradient-excess-2026-10-29.md`
   scored all 52 rows on `44ecf1cb` twice, with `thread_match_excess_gradient`
   OFF (shipped then) and ON (shipped since #1200, 2026-10-30). Windows, so
   advisory, but its OFF→ON deltas are exact and its row table is what lets
   this attribution say which movers predate 10-29.

## Every mover attributed

Grade and score per row; `10-29 OFF` / `10-29 ON` are the anchor's two arms.
A cause in **bold** is a named commit; *drift* means the interval is known and
the commit is not.

### Rose a band (19 rows)

| row | 10-05 | 10-29 OFF | 10-29 ON | 11-05 | what resolved | cause |
|---|---|---|---|---|---|---|
| `becker_marine_logo` hat_front, left_chest | B 88 | A 100 | A 100 | A 100 | `TRIM_HEAVY:warn` (`SATIN_GAPS_TIGHT:info` appears, no points) | *drift 10-05 → 10-29*: the 10-20 Column-lane flips — **#999** `lettering_columns_fold_cuts` is the one area 1 already queued for this row's trims, alongside **#1001** (resolution floor) |
| `gradient_ramp_linear` both | C 64 | D 46 | A 100 | A 100 | 3 × `THREAD_MATCH_POOR:warn` | **#1200** `thread_match_excess_gradient` ON (defect 28); the C → D step before it is *drift 10-05 → 10-29* on the gradient lane |
| `gradient_ramp_radial` both | C 64 | F 34 | B 88 | B 88 | 2 × `THREAD_MATCH_POOR:warn` | **#1200**; the C → F step before it is *drift 10-05 → 10-29* |
| `repro_gradient_white_icon` both | D 58 | B 76 | A 100 | A 100 | `THREAD_MATCH_POOR:block` + warn | **#1200**; D → B before it is *drift 10-05 → 10-29* |
| `drone_render` hat_front | F 0 | F 0 | D 52 | D 52 | 3 blocks + 6 warns `THREAD_MATCH_POOR`, `LETTERING_ILLEGIBLE:warn` (`DENSITY_STACKED:warn` appears) | **#1200**; area 1 also queued **#856** (clip keeps ink) and **#1005** (`dissolve_phantom_blends`, `clip_keep_pieces`) for this row inside the OFF arm |
| `drone_render` left_chest | F 0 | F 0 | D 40 | D 40 | same, plus `STITCHES_TOO_SHORT:warn` appears | same |
| `logo_bridge_bar` both | F 0 | F 0 | D 52 | C 64 | 3 blocks + 4 warns `THREAD_MATCH_POOR`, then `TRIM_HEAVY:warn` after 10-29 (`DENSITY_STACKED:warn` appears) | **#1200** for F → D; D → C is *drift 10-29 → 11-05*, candidates **#1192** (`edge_cap` "none", the cap stretches were this row's repeated cones) and the seam-order flips **#1198 / #1205**; area 1 queued **#856, #1005, #1001** inside the OFF arm |
| `logo_golden_tee` hat_front | F 0 | F 0 | C 64 | B 76 | 1 block + 7 warns, then `TRIM_HEAVY:warn` after 10-29 | **#1200** for F → C; C → B is *drift 10-29 → 11-05*, same candidates as bridge (**#1192**, **#1198 / #1205**) |
| `logo_golden_tee` left_chest | F 0 | F 0 | C 64 | C 64 | 1 block + 7 warns, `TRIM_HEAVY:warn` (`STITCHES_TOO_SHORT:warn` appears) | **#1200**; area 1 queued **#1005** |
| `region_blobs` both | F 0 | D 46 | D 46 | D 46 | `COLOR_STOPS_HEAVY:warn`, 1 block + 3 warns `THREAD_MATCH_POOR` (`DENSITY_STACKED`, `PHOTO_RESOLUTION_LOW`, `SATIN_GAPS_TIGHT:info` appear) | the 10-29 anchor records it: the fixture **routes `photo_scene` now** and sits on `GROUND_SEWN` — **#1178** stage-0 texture gate (2026-10-28) |
| `screenshot_phone_ui_golke` hat_front, left_chest | F 22, F 10 | F 0 | D 52 | D 52 | `COLOR_STOPS_HEAVY:warn`, `THREAD_MATCH_POOR:block` (`ARTWORK_UNCOVERED:info`, `SATIN_GAPS_TIGHT:info`, hat `STITCHES_TOO_SHORT:warn` appear) | **#1200**; the F 22/10 → F 0 step is **#899** (icon guard ON, "Waiting on Kent" 37), which area 1 queued for exactly this row |
| `photo_chrome_specular` left_chest | C 64 | B 76 | B 76 | B 76 | `ARTWORK_UNCOVERED:info`, `STITCHES_TOO_SHORT:warn` | **#856** `clip_parent_keeps_ink` — defect 61's text names chrome's `ARTWORK_UNCOVERED:info` clearing |

### Fell a band (10 rows)

| row | 10-05 | 10-29 OFF | 10-29 ON | 11-05 | what appeared | cause |
|---|---|---|---|---|---|---|
| `logo_alpha` both, `logo_whitebg` both | A 100 | B 88 | B 88 | B 88 | `LETTERING_TOO_SMALL:warn` | *drift 10-05 → 10-29*: the Column lane now tags the synthetic logos' text as lettering and reads it under 4 mm at 80 mm — **#863** `lettering_columns` ON (2026-10-12) and **#955** `small_text_true_size` ON (2026-10-15) are the flips that make a traced word a lettering shape with a size; not bisected between them |
| `logo_hotel_fremont` hat_front | B 88 | F 28 | F 28 | F 28 | 2 × `THREAD_MATCH_POOR:block` (`0020 Black` at dE 100 on a 7.34 mm² patch; `0862 Wild Rice` 26.7) | the B → F fall is *drift 10-05 → 10-29* and was **already recorded on 2026-10-29** (`thread-match-gradient-excess-2026-10-29.md` §1 "In", cause in its §2a: black thread sewing art the grader reads as white — a real reassignment, which is why excess did not clear it); unchanged since. (The WSL pass read F 16 here with a `LETTERING_ILLEGIBLE:warn` the Linux capture does not carry — an OCR verdict on the box, not drift.) |
| `logo_hotel_fremont` left_chest | B 76 | F 16 | F 16 | F 16 | same two blocks | same fall, recorded 10-29; unchanged since |
| `photo_chrome_specular` hat_front | B 76 | B 76 | B 76 | C 64 | `DENSITY_STACKED:warn` (`ARTWORK_UNCOVERED:info` resolves) | *drift 10-29 → 11-05* on the photo lane; stitches 36,555 → 39,984; candidates **#1210** and **#1233** `dark_ink_floor_rescue` ON; `tonal_split_ceiling` (the one commit naming the check, 4a6de923) is built OFF and cannot be it |
| `photo_dof_meadow` both | B 76 | C 64 | C 64 | C 64 | `DENSITY_STACKED:warn` (`ARTWORK_UNCOVERED:info` resolves on hat) | *drift 10-05 → 10-29* on the photo lane; stitches 21,993 → 22,525; the kept-frame guard **#1179** `photo_cutout_min_kept` (2026-10-29, inside the anchor tree) is the named candidate, not confirmed |
| `photo_sunset_backlit` left_chest | A 100 | B 76 | B 76 | B 76 | `DENSITY_STACKED:warn`, `LETTERING_TOO_SMALL:warn` | *drift 10-05 → 10-29*; stitches 25,813 → 31,908; the same two candidate sets as dof_meadow (**#1179**) and the synthetic logos (**#863 / #955**) |

### Moved in score only (1 row)

| row | 10-05 | 11-05 | what moved | cause |
|---|---|---|---|---|
| `photo_sunset_backlit` hat_front | B 88 | B 76 | `DENSITY_STACKED:warn`, `LETTERING_TOO_SMALL:warn` appear; `STITCHES_TOO_SHORT:warn` resolves | as its left_chest row |

### Unchanged (22 rows)

`bg_uncertain` (B 88), `logo_script_tires` (A 100), `ribbon_curve` (A 100),
`enthusiast_logo` (B 88), `fur_ramp` (B 88), `logo_gaulke_roofing` (B 76),
`photo_grass_macro` (D 58 / D 46), `photo_owl_pale` (D 58), `photo_scene_stub`
(B 76), `photo_subject_stub` (C 70), `summit_badge` (F 0) — all both garments.
`summit_badge` keeps its F on `GROUND_SEWN` plus the `0111 Whale` block that
survives the excess yardstick (10-29 doc §2). Gaulke's B 76 on 10-05 was the
10-29 doc's "out" row; it has not moved since.

## What the tool's own `diff` says

Run on the WSL rows against the 10-05 file: exit **1**, on the ten band
falls above (`_grade_fell`) and the two `THREAD_MATCH_POOR:block` that
APPEARED on Fremont. No other block appeared anywhere. That exit is the
report this file answers; it is not a CI gate (the tool's docstring). The
self-consistency replay (`diff` of the new file against itself, "no drift
against the baseline") was not run this time: the capture and the WSL
scoring agree row for row, which is the same check across two machines.

## Platform notes

- `photo_grass_macro` did not move on the WSL box (D 58 / D 46 on both
  rulers), so the one row COOKBOOK says that box cannot be trusted on is
  not among the movers.
- The WSL box and the GitHub runner both lack a rembg venv and both read
  through Tesseract 5.3.x on Python 3.12, which is CI's pipeline; Kent's
  Windows box has rembg and would score the photo rows differently.
- The 10-29 anchor was scored on Windows; only its OFF→ON deltas and its
  per-row grades are used here, as the dated record that a row had already
  moved by then.
- The runner and the WSL box disagreed on exactly one OCR verdict
  (Fremont hat_front's `LETTERING_ILLEGIBLE`), which is the kind of row the
  2026-09-15 platform entry in DOCTRINE warns about. Grades on the gradient
  and photo lanes agreed on every row.

## What stays open

- **Fremont is F 28 / F 16 on both garments** on a real customer logo: black thread
  sewing art the grader reads as white (10-29 §2a). The 10-29 doc priced a
  clamp floor; Kent kept the clamp. This is defect 28's remaining live case.
- **`DENSITY_STACKED` now fires on five photo-lane rows** that were quiet on
  10-05, with 2–24% more stitches each. Nobody has rendered them. Defect 20's
  `tonal_split_ceiling` is built OFF; the kept-frame guard is the suspect.
- **The Column lane reads the synthetic flat logos as small lettering**
  (`logo_alpha`, `logo_whitebg`). Cosmetic on synthetics; worth one look at
  what it says on real art at 80 mm.
- Area 1's queue of movers to attribute at the next capture (#856, #899,
  #1005, #1001, #999, #1002) is discharged by this file; #1002's rows
  (Column-lane lowercase) are among the 22 unchanged, so it moved no grade.
