# Attributing the corpus scorecard baseline — 2026-11-12

**Verdict: recaptured at `ffefc3b1` on cloud Linux (GitHub Actions
`ubuntu-latest`, `Corpus scorecard` workflow, capture run 43253187536, stamped
2026-11-12). 28 of 52 rows moved against the 2026-11-05 ruler (`292418a8`): 5
rose a letter band, 14 fell, 9 moved inside a band (score or findings only);
A/B/C/D/F 10/20/8/10/4 → 8/20/6/10/8, mean score 71.9 → 68.7. The mean fell.
every mover is attributed to a named flip by flag-off CI arms, not by guess,
except one step: `logo_golden_tee` hat_front's B 76 → C 64 (of its B 76 → D 40)
is unattributed.** No flag is changed by this recapture.

Read the grade as what it is: preflight-finding conformance (ROADMAP gate 4;
phase 1 is open). The fall is not a worse sew-out and was not measured as one.
It is `THREAD_MATCH_POOR` blocks appearing on five designs that stage 0 now
routes to the flat lane (#1301, Kent 2026-11-06), plus a photo-lane under-fill
gate (#1263) that traded `DENSITY_STACKED` for `STITCHES_TOO_SHORT` on two rows.
The one big rise (Fremont, F → B on both garments) is #1329.

## Kent's ruling (2026-11-12)

The mean fell and F rows went 4 → 8, so the director showed Kent the mover table
before this baseline landed. Kent, relayed verbatim by the director session:
**"Land as is (Recommended)."** The baseline is committed as captured; the
`logo_golden_tee` hat_front B 76 → C 64 step stays named as unattributed
(candidate #1277, not tested; no bisect arm was run). Landing records the new
floor as a conformance reading, not a quality claim (gate 4).

## The state of the ruler

| | |
|---|---|
| Old ruler | `292418a8`, 2026-11-05 (`docs/scorecard-baseline-attribution-2026-11-05.md`) |
| New ruler | `ffefc3b1`, 2026-11-12 — `origin/main` after #1406 |
| Capture | run 43253187536, `ubuntu-latest`, 15:56 UTC, Tesseract in-process, Python 3.12 |
| Cross-check | `diff` run 43253195083 on the same SHA scored the same rows: the diff log's per-row grade changes (bg_uncertain, bridge, chrome, dof_meadow, scene_stub, sunset, region_blobs, white_icon, summit) match the capture's |
| Rows | 52 (26 fixtures × 2 garments), 0 errors |
| Unchanged in grade, score and findings | 24 |
| Up / down / inside a band | 5 / 14 / 9 |
| Grades, old → new (A/B/C/D/F) | 10/20/8/10/4 → 8/20/6/10/8 |
| Mean score | 71.9 → 68.7 |

(The `diff` run's step shows red in the Actions UI. That is the tool's own
`EXIT=1` on fallen bands, not a failure of the run; the workflow's step lets
the exit code through. Its log is the report this file answers.)

## Method: flag-off arms on the same ruler

87 pipeline commits (`digitizer/digitizer_core`, `digitizer_service`) landed between the rulers, so a bisection was not the
plan. Every default that flipped ON since 2026-11-05 is a `PipelineConfig` field,
so six throwaway branches off `ffefc3b1` set a group of them back and were
captured by the same workflow on the same runner class (branches
`claude/scorecard-arm-*`, config edit only, never merged, deleted after):

| arm | run | flags set back |
|---|---|---|
| `all` | 43257834939 | everything in the next four rows at once |
| `s0` | 43257813107 | #1301: `stage0_scale_relative_grad`, `flat_page_fringe_soft_ramp`, `flat_ramp_blend_dissolve` OFF |
| `photo` | 43257820455 | #1263: `silhouette_underfill_photo` True (the pre-gate photo under-fill) |
| `rest` | 43257828074 | #1329 `thread_match_grade_traced_letter`, `flat_light_text_runs`; #1365 `dropped_element_v2`; #1366 `text_cluster_nest_door_aspect`; #1378 `blend_shade_median`; #1396 `enclosed_white_skip_transparent` OFF |
| `r1` | 43262340859 | #1329 pair only OFF |
| `r2` | 43262348489 | #1378 only OFF |

**The `all` arm reproduces the 11-05 baseline on 51 of 52 rows** (grade, score
and findings), and its mean reads 71.7 against 71.9. So everything that moved
is one of those flips, except the single row named below. The `s0` arm turns the
three #1301 flags off together; it does not split stage 0 from the fringe cure
(`docs/flip-1301-attribution-2026-11-07.md` found the cure moves only
`toat_beanie`, a tripwire job outside this corpus).

Arm summaries (A/B/C/D/F, mean): `s0` 10/22/8/10/2, 75.5; `photo` 8/19/7/10/8,
67.5; `rest` 8/18/6/11/9, 66.7; `r1` 8/18/6/11/9, 67.1; `r2` 8/20/6/10/8, 68.3;
`all` 10/19/9/10/4, 71.7.

## Every mover attributed

Grade and score per row, `old → new`. "Restored by" lists the arms whose row
equals the old baseline exactly.

### Moved with the flat-lane route: #1301 (12 rows, all fell)

| row | old → new | what appeared / went | restored by | cause |
|---|---|---|---|---|
| `bg_uncertain` hat_front | B 88 → D 58 | `THREAD_MATCH_POOR:block` | `s0`, `all` | **#1301** |
| `bg_uncertain` left_chest | B 88 → F 34 | `THREAD_MATCH_POOR:block`, `LETTERING_TOO_SMALL:warn`, `STITCHES_TOO_SHORT:warn` | `s0`, `all` | **#1301** |
| `logo_bridge_bar` hat_front | C 64 → F 0 | `THREAD_MATCH_POOR:block` ×3, `STABILIZER_CUTAWAY:info` appear; `COLOR_STOPS_HEAVY:warn` goes | `s0`, `all` | **#1301** |
| `logo_bridge_bar` left_chest | C 64 → F 0 | same, plus `STITCHES_TOO_SHORT:warn`, `TRIM_HEAVY:warn` | `s0`, `all` | **#1301** |
| `logo_gaulke_roofing` hat_front, left_chest | B 76 → C 64 | `TRIM_HEAVY:warn` | `s0`, `all` | **#1301** (the 11-07 doc already has gaulke's trims +2 under stage 0) |
| `logo_golden_tee` left_chest | C 64 → F 28 | `THREAD_MATCH_POOR:warn`, `TRIM_HEAVY:warn` appear; `SATIN_GAPS_TIGHT:info` goes | `s0`, `all` | **#1301** (the 11-07 doc: Golden Tee goes flat, trims 25 → 39) |
| `logo_golden_tee` hat_front | B 76 → D 40 | same two warns appear; `SATIN_GAPS_TIGHT:info` goes | none | **#1301 for C 64 → D 40; B 76 → C 64 is unattributed**, below |
| `photo/screenshot_phone_ui_golke` hat_front, left_chest | D 52 → F 34 | `THREAD_MATCH_POOR:block` appears; `ARTWORK_UNCOVERED:info`, `LETTERING_ILLEGIBLE:warn`, `SATIN_GAPS_TIGHT:info` go | `s0`, `all` | **#1301** |
| `repro_gradient_white_icon` hat_front, left_chest | A 100 → B 88 | `THREAD_MATCH_POOR:warn` (left_chest also `STABILIZER_CUTAWAY:info`) | `s0`, `all` | **#1301** |

These are rows MASTER_SCOPE says now trace `flat` (tires, bridge_bar, gaulke,
golden_tee, fremont, screenshot, white_icon). The `THREAD_MATCH_POOR` check
reads them differently on the flat lane; none of it was rendered or sewn.

### Moved with the photo lane: #1263 (12 rows, 6 designs)

`silhouette_underfill` is gated off for photo classes since #1263 (Kent
2026-11-05); the `photo` arm restores all of these.

| row | old → new | what appeared / went | cause |
|---|---|---|---|
| `photo_chrome_specular` hat_front | C 64 → B 76 | `DENSITY_STACKED:warn` goes | **#1263** |
| `photo_chrome_specular` left_chest | B 76 → C 64 | `STITCHES_TOO_SHORT:warn` appears | **#1263** (a fall) |
| `photo_dof_meadow` hat_front, left_chest | C 64 → B 76 | `DENSITY_STACKED:warn` goes | **#1263** |
| `photo_scene_stub` hat_front, left_chest | B 76 → B 88 | `DENSITY_STACKED:warn`, `STABILIZER_CUTAWAY:info` go | **#1263** |
| `photo_sunset_backlit` left_chest | B 76 → C 64 | `STITCHES_TOO_SHORT:warn`, `TRIM_HEAVY:warn` appear; `DENSITY_STACKED:warn` goes | **#1263** (a fall) |
| `photo_sunset_backlit` hat_front | B 76 → B 76 | `STITCHES_TOO_SHORT:warn` replaces `DENSITY_STACKED:warn`, score unchanged | **#1263** |
| `region_blobs` hat_front | D 46 → D 58 | `DENSITY_STACKED:warn` goes; `ARTWORK_UNCOVERED:info` appears | **#1263** |
| `region_blobs` left_chest | D 46 → D 58 | `DENSITY_STACKED:warn` goes | **#1263** |
| `photo_owl_pale` hat_front, left_chest | D 58 → D 58 | `STABILIZER_CUTAWAY:info` goes | **#1263** |

This closes the question 11-05 left open ("`DENSITY_STACKED` now fires on five
photo-lane rows ... kept-frame guard #1179 suspected"): the quieter state
returns when the under-fill is gated off. It also names what replaced it on two
rows, `STITCHES_TOO_SHORT:warn`.

### Rose: #1329 (Fremont) and #1378 (summit) (4 rows)

| row | old → new | what went | restored by | cause |
|---|---|---|---|---|
| `logo_hotel_fremont` hat_front | F 28 → B 88 | `THREAD_MATCH_POOR:block` ×2 | `all` only | **#1329** (`thread_match_grade_traced_letter`, with `flat_light_text_runs`), with #1301's help |
| `logo_hotel_fremont` left_chest | F 16 → B 76 | `THREAD_MATCH_POOR:block` ×2 | `all` only | same |
| `summit_badge` hat_front, left_chest | F 0 → F 10 | `THREAD_MATCH_POOR:block` (the `0111` block) | `rest`, `r2`, `all` | **#1378** (`blend_shade_median`): the 11-09 note named summit's `0111` speckled end bucket as the cause; `r2` confirms it |

Fremont is two-factor, and the arms say how: with #1329 off and #1301 on
(`rest`, `r1`) hat reads D 46 and left_chest F 34; with #1329 on and #1301 off
(`s0`) both read B; both on is also B 88 / B 76; both off (`all`) is the old F
28 / F 16. So #1329 clears the dE-100 blocks (the traced-letter grader reads the
ground an enlarged letter grew over), and #1301 alone moves the rows a partial
step up. Summit stays F on `GROUND_SEWN`.

### Unattributed: one row part

`logo_golden_tee` hat_front, **B 76 → C 64**. It is present in the `s0` and the
`all` arms alike: with every flag above set back, the row still reads C 64
because `LETTERING_ILLEGIBLE:warn` appears (stitch count 11,844 → 11,847). No
flag tested owns it. It is an OCR verdict on a flipped read, the kind
DOCTRINE's 2026-09-15 platform entry warns about, and the candidates that
landed after the 11-05 capture are the in-process OCR reader (#1277,
tesserocr 5.5.3 against the runner's 5.3.x) and some unflagged commit among the
87. Not bisected; not guessed.

### Rows that moved in metrics, not in grade

`logo_alpha` both: stitches 6,796 → 6,260 (hat), `satin_steps` 572 → 137,
`artwork_reached_frac` 1.0 → 0.931; grade B 88 and findings unchanged. The `rest`
arm restores the old figures exactly, so it is **#1396**
(`enclosed_white_skip_transparent`, Kent 2026-11-11), the flip the scorecard was
expected to show. `drone_render` both: stitches 19,259 → 19,170 and 19,758 →
19,670, grade and findings unchanged, restored by `rest`: **#1396**.
`logo_whitebg` moved only by three new metric keys (#1365 / #1329 counters).
**#1396 moved no grade.**

### Unchanged (24 rows)

`becker_marine_logo`, `logo_alpha`, `logo_whitebg`, `logo_script_tires`,
`ribbon_curve`, `drone_render`, `enthusiast_logo`, `fur_ramp`,
`gradient_ramp_linear`, `gradient_ramp_radial`, `photo_grass_macro`,
`photo_subject_stub` — both garments each.

## What the tool's own `diff` says

Run 43253195083, `diff` mode against the 11-05 file: exit 1, on the fallen
bands above and the `THREAD_MATCH_POOR` that appeared on five designs.
It reports Fremont's blocks resolved. That is the report this file answers; it
is not a CI gate (workflow comment, tool docstring).

## What stays open

- **Five designs carry a new `THREAD_MATCH_POOR` read on the flat lane**
  (bg_uncertain, bridge_bar, golden_tee, screenshot, white_icon; gaulke falls
  on `TRIM_HEAVY`): the price of #1301 on this scorecard. Not rendered here.
  Kent flipped it knowing the tripwire rows; the scorecard now carries it too.
- **`logo_golden_tee` hat_front's `LETTERING_ILLEGIBLE:warn`** is the one
  unattributed row part.
- **#1263's `STITCHES_TOO_SHORT:warn`** on chrome left_chest and sunset: two
  falls the gate bought for six `DENSITY_STACKED` clears.
- Fremont is no longer the scorecard's remaining F: B 88 / B 76 (the open
  `LETTERING_TOO_SMALL:warn` on both stays).

## Platform notes

- Capture and `diff` ran on the same `ffefc3b1` tree and agree row for row, the
  same check the 11-05 file made across two machines.
- Every arm ran on the same GitHub runner class, so arm-to-arm differences are
  the flag, not the machine. Arms differ from the capture only by config.
- Nothing from Kent's Windows box or the WSL box is in this baseline.
