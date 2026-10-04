# Attributing the corpus scorecard baseline — 2026-10-04

**Verdict: recaptured at `6e0cb943` on cloud Linux. Forty-eight of 52 rows
moved against the 2026-09-16 ruler; five fell a letter band and five rose;
every mover is attributed to a named first-parent commit by bisection over
the 51 trees between the two rulers — 387 change points, 23 commits moved a
row, 27 moved none (section "Every mover attributed").**
The five band falls are regressions for Kent to weigh, not noise — the
recapture does not make them go away, it makes them the ruler.

Why now: PR #619 added 17 metric keys to `run_preflight` that judge nothing
(`edge_wobble_{satin,border,fill,line}_{p95,std,max}_mm`,
`curve_roughness_deg`, `curve_turn_gini`, `curve_vertices`,
`curve_corner_vertices`, `curve_traces`). `corpus_scorecard.diff` compares
only keys both sides hold, so until the baseline carried them no tool read
them. Recapture is the only way those numbers become visible, and COOKBOOK's
rule is diff-then-capture with every mover attributed — this file is that
attribution.

## The state of the ruler

| | |
|---|---|
| Old ruler | `2c60cd87`, 2026-09-16 (PR #502) |
| New ruler | `6e0cb943`, 2026-10-04 (the merge of PR #619) |
| First-parent commits touching `digitizer_core/` in between | **50** (124 counting every commit) |
| Rows | 52 (26 fixtures × 2 garments), 0 errors in either ruler |
| Rows moved by the tool's own rule (score, grade, findings, or a metric past 5 % noise) | **48** |
| Rows the tool calls unmoved | 4 — and all four moved under the noise floor (below) |
| Leaves that changed on pre-existing keys | **721** |
| Metric keys per row | 40 → **66** |

## Environment, and the controls that make the numbers trustworthy

Captured on **Linux only**, per DOCTRINE "The scorecard baseline is
platform-bound": an Ubuntu cloud container, `python3.12` 3.12.3, the pinned
`requirements.txt`, `tesseract-ocr` 5.3.4 from apt, no `rembg_isolated/venv`.
That is the CI `digitizer` job's environment. Not the WSL box on Kent's
laptop, which COOKBOOK says never captures (its `photo_grass_macro` rows are
the machine's).

1. **Platform control, run before anything else, as DOCTRINE asks.** All 52
   rows re-scored at the old ruler's own `captured_at_commit` (`2c60cd87`)
   on this box, in a 3-worker pool: **identical to the stored baseline on
   every leaf** — score, grade, findings and all 40 metrics, 52 of 52. The
   old ruler was the engine's, not the machine's, and the pooled scorer adds
   no drift of its own.
2. **The tool's own serial `diff`, twice.** Once at `aa7f934` (main before
   #619 merged) and once at `6e0cb943` (the capture commit): the two
   outputs are **identical line for line, 576 lines, exit 1 both**. So the
   17 keys #619 added changed no score, grade, finding or metric on any row
   — Kent's "metrics only" ruling holds corpus-wide, measured.
3. **Pooled and serial agree.** The 3-worker pool's rows at `de1d2c0a` (the
   last pipeline commit before the merge) replayed through `diff()` print
   the same 576 lines; and the serial `capture` at `6e0cb943` matches those
   pooled rows on every common leaf, 52 of 52.
4. **The new ruler is self-consistent.** HEAD's rows replayed through
   `diff()` against the new file: `no drift against the baseline.`, exit 0.

Serial `diff` took 38.7 and 39.6 minutes; serial `capture` 40.2; the
bisection ran beside them in a spawn-per-evaluation pool against
`git archive` trees of each commit's `digitizer/`.

## The five rows that fell a band

| row | grade | score | what appeared |
|---|---|---|---|
| `logo_script_tires.png @ 80mm/hat_front` | A → **B** | 100 → 88 | `SATIN_GAPS_TIGHT:warn` |
| `photo/photo_chrome_specular.png @ 80mm/hat_front` | B → **C** | 88 → 64 | `ARTWORK_UNCOVERED:warn`, `LETTERING_TOO_SMALL:warn` |
| `photo/photo_chrome_specular.png @ 80mm/left_chest` | C → **D** | 64 → 52 | `ARTWORK_UNCOVERED:warn` |
| `photo/photo_scene_stub.png @ 80mm/hat_front` | B → **D** | 76 → 52 | `ARTWORK_UNCOVERED:warn`, `SATIN_GAPS_TIGHT:warn` |
| `photo/photo_scene_stub.png @ 80mm/left_chest` | C → **D** | 64 → 52 | `SATIN_GAPS_TIGHT:warn` |

Five rose: `photo/logo_hotel_fremont.webp` both garments C → B
(`STITCHES_TOO_SHORT:warn` resolved; on the cap `LETTERING_ILLEGIBLE:warn`
too), `photo/photo_subject_stub.png` both D → C (`ARTWORK_UNCOVERED:warn`
resolved, `uncovered_total_mm2` 956 → 0), `photo/photo_grass_macro.png @
hat_front` F → D (`LETTERING_TOO_SMALL` and `STITCHES_TOO_SHORT` resolved).

## Grade distribution over the 52 rows

| grade | old | new |
|---|---|---|
| A | 7 | 6 |
| B | 13 | 14 |
| C | 10 | 11 |
| D | 6 | 8 |
| F | 16 | 13 |

## Corpus-wide finding deltas

`SATIN_GAPS_TIGHT:warn` 0 → 10 (a check that did not exist in the old
ruler — #573), `ARTWORK_UNCOVERED:warn` 6 → 14, `STITCHES_TOO_SHORT:warn`
18 → 5, `THREAD_MATCH_POOR:block` 34 → 26, `THREAD_MATCH_POOR:warn` 68 → 72,
`LETTERING_TOO_SMALL:warn` 23 → 20, `LETTERING_ILLEGIBLE:warn` 10 → 7,
`STABILIZER_CUTAWAY:info` 6 → 8, `DENSITY_EXTREME:warn` 2 → 0,
`TRIM_HEAVY:warn` 18 → 17.

## The 26 metric keys the new ruler carries that the old one did not

None of these is a mover — `diff` could not see them until now. Each is in
the new file on all 52 rows (a `None` where the design has no such tier).

| keys | from | rows with a value |
|---|---|---|
| `edge_wobble_satin_{p95,std,max}_mm` | #619 | 38 |
| `edge_wobble_border_{p95,std,max}_mm` | #619 | 16 |
| `edge_wobble_fill_{p95,std,max}_mm` | #619 | 40 |
| `edge_wobble_line_{p95,std,max}_mm` | #619 | 30 |
| `curve_roughness_deg`, `curve_turn_gini`, `curve_vertices`, `curve_corner_vertices`, `curve_traces` | #619 | 52 |
| `uncovered_hole_mm2`, `uncovered_holes`, `uncovered_patches`, `uncovered_top_mm2` | #572 (`41de6430`) | 52 |
| `satin_gaps_judged`, `satin_gaps_tight_shapes`, `satin_gaps_tight_worst_frac` | #573 (`493ac45b`) | 52 |
| `tiny_steps`, `tiny_step_fraction` | #597 (`944d664e`) | 52 |

## The four rows the tool calls unmoved moved too — under its noise floor

`uncovered_wanted_mm2` rose on **all 52 rows**, these four included
(`bg_uncertain` 3287.5 → 3447.9 and 3334.5 → 3435.2; `gradient_ramp_linear`
3736.5 → 3800.0 on both garments). `bg_uncertain` also lost 35–47 stitches
and a few hundredths of `coverage_max`. All of it sits under the 5 % noise
fraction, which is why `diff` printed nothing for them. It is in the complete
leaf list below and in the new file.

## Every mover attributed

Method: every one of the 48 moved rows was bisected over the 51 first-parent
trees between the rulers (`git archive` of each commit's `digitizer/`, scored by
that tree's own `_score_one` in a fresh interpreter per evaluation). A change
point is a commit whose row differs from the one before it by the tool's own
rule. **387 change points, 50 commits, 1,176 evaluations;
23 of the 50 commits moved at least one row, 27 moved none.** Every mover below
is pinned to a named commit; the one interval the bisection could not split
(both halves read unmoved while the whole moved) is listed as gradual drift.

### What each commit did to the corpus

"kind" is measured, not inferred: *instrument only* means `stitch_count` is
byte-identical on every row the commit moved and no geometry metric passed the
noise fraction — the grader read the same stitches differently.

| commit | PR | rows moved | score moved | grade moved | `stitch_count` changed | kind | what moved most |
|---|---|---|---|---|---|---|---|
| `da6606e4` | #515 | 4 | 1 | 0 | 4 | geometry | `satin_short_fraction`, `satin_shapes`, `satin_steps`; findings `ARTWORK_UNCOVERED:warn +1`×1, `STITCHES_TOO_SHORT:warn +1`×1 |
| `396a7458` | #516 | 32 | 3 | 2 | 32 | geometry | `trims_per_1000`, `satin_short_fraction`, `same_hole_fraction`; findings `STITCHES_TOO_SHORT:warn −1`×2, `TRIM_HEAVY:warn −1`×1, `LETTERING_ILLEGIBLE:warn −1`×1 |
| `bff6b37a` | #521 | 19 | 0 | 0 | 19 | geometry | `trims_per_1000`, `coverage_max`, `same_hole_fraction` |
| `5d2db084` | #520 | 30 | 6 | 3 | 30 | geometry | `satin_short_fraction`, `trims_per_1000`, `coverage_max`; findings `ARTWORK_UNCOVERED:warn −1`×3, `LETTERING_ILLEGIBLE:warn +1`×2, `STITCHES_TOO_SHORT:warn −1`×2 |
| `24fce102` | #523 | 14 | 0 | 0 | 14 | geometry | `trims_per_1000`, `link_thread_mm`, `link_segments` |
| `48b03066` | #528 | 2 | 0 | 0 | 2 | geometry | `uncovered_worst_mm2`, `color_changes`, `satin_short_fraction` |
| `00cdf44c` | #537 | 22 | 2 | 0 | 22 | geometry | `satin_steps`, `satin_short_fraction`, `legibility`; findings `DENSITY_EXTREME:warn −1`×2 |
| `8a48c3b4` | #554 | 38 | 10 | 4 | 38 | geometry | `satin_short_fraction`, `coverage_max`, `satin_steps`; findings `STITCHES_TOO_SHORT:warn −1`×6, `STITCHES_TOO_SHORT:warn +1`×4, `LETTERING_TOO_SMALL:warn −1`×4 |
| `254eb3a4` | #557 | 12 | 0 | 0 | 12 | geometry | `trims_per_1000`, `satin_short_fraction`, `same_hole_fraction`; findings `TRIM_HEAVY:warn −1`×1 |
| `89161704` | #558 | 21 | 0 | 0 | 21 | geometry | `uncovered_worst_mm2`, `satin_short_fraction`, `satin_steps`; findings `TRIM_HEAVY:warn +1`×1, `DENSITY_STACKED:warn +1`×1 |
| `08c46a54` | #561 | 25 | 5 | 4 | 25 | geometry | `coverage_max`, `satin_short_fraction`, `satin_steps`; findings `STITCHES_TOO_SHORT:warn −1`×5, `DENSITY_STACKED:warn −1`×2, `LETTERING_TOO_SMALL:warn +1`×1 |
| `7cc7df4d` | #559 | 33 | 3 | 2 | 33 | geometry | `satin_steps`, `satin_short_fraction`, `uncovered_worst_mm2`; findings `STITCHES_TOO_SHORT:warn −1`×3, `STABILIZER_CUTAWAY:info +1`×1, `STITCHES_TOO_SHORT:warn +1`×1 |
| `ce8bdb89` | #565 | 13 | 0 | 0 | 12 | geometry | `satin_short_fraction`, `legibility`, `trims_per_1000`; findings `STITCHES_TOO_SHORT:warn −1`×1 |
| `722f5a9b` | #567 | 8 | 0 | 0 | 8 | geometry | `satin_short_fraction`, `coverage_max`, `uncovered_worst_mm2` |
| `d59ff556` | #573 | 12 | 8 | 6 | 0 | **instrument only** | `raw_score`; findings `SATIN_GAPS_TIGHT:warn +1`×12 |
| `6706a71e` | #577 | 7 | 0 | 0 | 7 | geometry | `coverage_max`, `uncovered_worst_mm2`, `satin_short_fraction` |
| `1c3d067a` | #578 | 12 | 1 | 1 | 12 | geometry | `satin_short_fraction`, `satin_steps`, `stitch_count`; findings `STITCHES_TOO_SHORT:warn −1`×1 |
| `e2c9f77e` | #579 | 1 | 0 | 0 | 1 | geometry | `link_segments`, `link_thread_mm` |
| `41de6430` | #572 | 46 | 14 | 9 | 0 | **instrument only** | `uncovered_wanted_mm2`, `uncovered_worst_mm2`, `uncovered_total_mm2`; findings `ARTWORK_UNCOVERED:warn +1`×13, `ARTWORK_UNCOVERED:warn −1`×2 |
| `e851e5aa` | #589 | 18 | 5 | 0 | 18 | geometry | `trims_per_1000`, `raw_score`, `coverage_max`; findings `THREAD_MATCH_POOR:warn +1`×4, `THREAD_MATCH_POOR:block −1`×4, `THREAD_MATCH_POOR:block −2`×2 |
| `0c3b7725` | #599 | 8 | 0 | 0 | 8 | geometry | `trims_per_1000`, `coverage_max`, `color_changes`; findings `LETTERING_ILLEGIBLE:warn −1`×2, `THREAD_MATCH_POOR:block −2`×2, `THREAD_MATCH_POOR:warn +3`×2 |
| `5337e2f6` | #608 | 7 | 1 | 0 | 7 | geometry | `uncovered_patches`, `satin_short_fraction`, `uncovered_hole_mm2`; findings `ARTWORK_UNCOVERED:warn −1`×2 |
| `de1d2c0a` | #614 | 3 | 0 | 0 | 2 | geometry | `legibility`, `uncovered_patches`, `legibility_worst` |

### The band moves, step by step

| row | old → new | the path, by PR |
|---|---|---|
| `logo_script_tires.png @ 80mm/hat_front` | A 100 → **B 88** | #573 A 100 → B 88 (+`SATIN_GAPS_TIGHT:warn`) |
| `photo/photo_chrome_specular.png @ 80mm/hat_front` | B 88 → **C 64** | #554 B 88 → B 76 (+`STITCHES_TOO_SHORT:warn`); #561 B 76 → C 64 (+`LETTERING_TOO_SMALL:warn`); #578 C 64 → B 76 (−`STITCHES_TOO_SHORT:warn`); #572 B 76 → C 64 (+`ARTWORK_UNCOVERED:warn`) |
| `photo/photo_chrome_specular.png @ 80mm/left_chest` | C 64 → **D 52** | #572 C 64 → D 52 (+`ARTWORK_UNCOVERED:warn`) |
| `photo/photo_scene_stub.png @ 80mm/hat_front` | B 76 → **D 52** | #573 B 76 → C 64 (+`SATIN_GAPS_TIGHT:warn`); #572 C 64 → D 52 (+`ARTWORK_UNCOVERED:warn`) |
| `photo/photo_scene_stub.png @ 80mm/left_chest` | C 64 → **D 52** | #520 C 64 → B 76 (−`ARTWORK_UNCOVERED:warn`); #573 B 76 → C 64 (+`SATIN_GAPS_TIGHT:warn`); #572 C 64 → D 52 (+`ARTWORK_UNCOVERED:warn`) |
| `photo/logo_hotel_fremont.webp @ 80mm/hat_front` | C 64 → **B 88** | #554 C 64 → B 76 (−`STITCHES_TOO_SHORT:warn`); #589 B 76 → B 88 (−`LETTERING_ILLEGIBLE:warn`) |
| `photo/logo_hotel_fremont.webp @ 80mm/left_chest` | C 64 → **B 76** | #554 C 64 → B 76 (−`STITCHES_TOO_SHORT:warn`) |
| `photo/photo_grass_macro.png @ 80mm/hat_front` | F 22 → **D 46** | #516 F 22 → F 10 (+`TRIM_HEAVY:warn`); #520 F 10 → F 22 (−`TRIM_HEAVY:warn`); #554 F 22 → D 46 (−`LETTERING_TOO_SMALL:warn`, −`STITCHES_TOO_SHORT:warn`) |
| `photo/photo_subject_stub.png @ 80mm/hat_front` | D 58 → **C 70** | #572 D 58 → C 70 (−`ARTWORK_UNCOVERED:warn`) |
| `photo/photo_subject_stub.png @ 80mm/left_chest` | D 58 → **C 70** | #572 D 58 → C 70 (−`ARTWORK_UNCOVERED:warn`) |

**The step that crosses the band line is an instrument on all five falls,
not the engine.** `#572` taught the uncovered-area check to see holes
(`uncovered_worst_mm2` 0 → tens of mm² on 41 rows, `ARTWORK_UNCOVERED:warn`
+1 on 13) and `#573` added `SATIN_GAPS_TIGHT:warn` (12 rows). Neither moved a
single stitch on any row — `stitch_count` is byte-identical either side of
both on every row they touched. The same `#572` is why `photo_subject_stub`
ROSE two bands: the 956 mm² it was docked for sat inside a hole. One fall
carries geometry too: `photo_chrome_specular` hat_front lost 88 → 64 inside
and below the B band through `#554` (rail comp ON, `STITCHES_TOO_SHORT`
appeared) and `#561` (seam reading, `LETTERING_TOO_SMALL` appeared), came back
to 76 at `#578`, and `#572` took it to 64 for good; the `LETTERING_TOO_SMALL`
from `#561` is still on the row. The geometry flips otherwise net their band
moves upward (`#554` lifts `hotel_fremont` C → B on both garments and
`grass_macro` F → D). Whether a check that fires on 10 rows should cost a
band is Kent's to weigh, not this file's.

### Every moved row, by the commits that moved it

Format: `PR(what)` — a grade or score step, a finding that appeared (+) or
resolved (−), or `Nm` for N metric lines past the noise fraction and nothing
else.

- `becker_marine_logo.png @ 80mm/hat_front`: #515(88→76, +ARTWORK_UNCOVERED), #516(4m), #520(76→88, -ARTWORK_UNCOVERED), #523(2m), #528(2m), #537(3m), #554(6m), #557(2m), #558(1m), #559(5m), #567(5m), #577(3m), #578(4m), #572(88→76, +ARTWORK_UNCOVERED), #599(14m), #608(8m)
- `becker_marine_logo.png @ 80mm/left_chest`: #515(8m), #516(4m), #520(76→88, -ARTWORK_UNCOVERED), #528(4m), #537(5m), #554(5m), #557(2m), #558(1m), #559(5m), #567(4m), #577(1m), #578(5m), #572(88→76, +ARTWORK_UNCOVERED), #599(12m), #608(8m)
- `logo_alpha.png @ 80mm/hat_front`: #521(1m), #572(2m)
- `logo_alpha.png @ 80mm/left_chest`: #554(1m), #572(2m)
- `logo_script_tires.png @ 80mm/hat_front`: #516(4m), #520(4m), #537(7m), #554(4m), #557(3m), #559(6m), #573(A→B, +SATIN_GAPS_TIGHT), #578(5m), #572(2m)
- `logo_script_tires.png @ 80mm/left_chest`: #516(B→A, -TRIM_HEAVY), #520(5m), #523(3m), #537(6m), #554(5m), #557(3m), #559(6m), #573(A→B, +SATIN_GAPS_TIGHT), #578(3m), #572(2m), #614(1m)
- `logo_whitebg.png @ 80mm/hat_front`: #521(1m), #572(2m)
- `logo_whitebg.png @ 80mm/left_chest`: #554(1m), #572(2m)
- `photo/drone_render.png @ 80mm/hat_front`: #516(4m), #520(+LETTERING_ILLEGIBLE), #523(4m), #537(4m), #554(8m), #558(1m), #561(4m), #559(2m), #572(+ARTWORK_UNCOVERED), #589(-THREAD_MATCH_POOR, +THREAD_MATCH_POOR), #608(-ARTWORK_UNCOVERED)
- `photo/drone_render.png @ 80mm/left_chest`: #516(-LETTERING_ILLEGIBLE), #520(+LETTERING_ILLEGIBLE), #523(1m), #537(2m), #554(7m), #558(1m), #561(2m), #559(5m), #572(2m), #589(-THREAD_MATCH_POOR, +THREAD_MATCH_POOR)
- `photo/enthusiast_logo.png @ 80mm/hat_front`: #516(9m), #520(4m), #523(2m), #537(1m), #554(76→88, -LETTERING_ILLEGIBLE), #557(2m), #559(2m), #572(88→76, +ARTWORK_UNCOVERED), #608(76→88, -ARTWORK_UNCOVERED)
- `photo/enthusiast_logo.png @ 80mm/left_chest`: #516(8m), #520(3m), #523(2m), #537(3m), #554(4m), #557(2m), #559(3m), #572(88→76, +ARTWORK_UNCOVERED), #608(6m)
- `photo/fur_ramp.png @ 80mm/hat_front`: #572(1m)
- `photo/fur_ramp.png @ 80mm/left_chest`: #572(1m)
- `photo/gradient_ramp_radial.png @ 80mm/hat_front`: #521(1m), #599(3m)
- `photo/gradient_ramp_radial.png @ 80mm/left_chest`: #521(2m), #599(3m)
- `photo/logo_bridge_bar.jpg @ 80mm/hat_front`: #515(+STITCHES_TOO_SHORT), #516(4m), #520(3m), #523(2m), #537(3m), #554(-STITCHES_TOO_SHORT), #557(1m), #558(4m), #561(7m), #559(7m), #567(1m), #573(+SATIN_GAPS_TIGHT), #577(1m), #578(2m), #572(2m), #589(+THREAD_MATCH_POOR, +THREAD_MATCH_POOR), #599(-LETTERING_ILLEGIBLE, -THREAD_MATCH_POOR, +THREAD_MATCH_POOR)
- `photo/logo_bridge_bar.jpg @ 80mm/left_chest`: #515(9m), #516(6m), #520(4m), #537(3m), #554(-STITCHES_TOO_SHORT), #558(3m), #561(5m), #559(7m), #565(2m), #567(2m), #573(+SATIN_GAPS_TIGHT), #577(2m), #572(2m), #589(+ARTWORK_UNCOVERED, +THREAD_MATCH_POOR, +THREAD_MATCH_POOR), #599(-ARTWORK_UNCOVERED, -LETTERING_ILLEGIBLE, +STITCHES_TOO_SHORT, -THREAD_MATCH_POOR, +THREAD_MATCH_POOR)
- `photo/logo_gaulke_roofing.png @ 80mm/hat_front`: #516(11m), #520(C→B, -STITCHES_TOO_SHORT), #523(3m), #537(6m), #554(7m), #561(1m), #559(2m), #565(2m), #573(B→C, +SATIN_GAPS_TIGHT), #572(2m), #589(5m)
- `photo/logo_gaulke_roofing.png @ 80mm/left_chest`: #516(4m), #520(C→B, -STITCHES_TOO_SHORT), #523(4m), #537(7m), #554(8m), #561(1m), #559(1m), #565(1m), #573(B→C, +SATIN_GAPS_TIGHT), #572(2m), #589(7m)
- `photo/logo_golden_tee.jpg @ 80mm/hat_front`: #516(-STITCHES_TOO_SHORT), #520(6m), #554(+DENSITY_STACKED, +STITCHES_TOO_SHORT), #557(-TRIM_HEAVY), #558(+TRIM_HEAVY), #561(-DENSITY_STACKED, -STITCHES_TOO_SHORT), #559(4m), #565(4m), #573(+SATIN_GAPS_TIGHT), #572(2m), #589(+ARTWORK_UNCOVERED, -THREAD_MATCH_POOR, +THREAD_MATCH_POOR)
- `photo/logo_golden_tee.jpg @ 80mm/left_chest`: #516(7m), #520(8m), #554(11m), #557(1m), #558(+DENSITY_STACKED), #561(-DENSITY_STACKED), #559(6m), #565(-STITCHES_TOO_SHORT), #573(+SATIN_GAPS_TIGHT), #572(2m), #589(-THREAD_MATCH_POOR, +THREAD_MATCH_POOR), #608(1m)
- `photo/logo_hotel_fremont.webp @ 80mm/hat_front`: #516(1m), #554(C→B, -STITCHES_TOO_SHORT), #561(2m), #572(2m), #589(76→88, -LETTERING_ILLEGIBLE) gradual(#517..#528]
- `photo/logo_hotel_fremont.webp @ 80mm/left_chest`: #516(3m), #523(4m), #554(C→B, -STITCHES_TOO_SHORT), #561(2m), #559(2m), #572(2m), #589(2m)
- `photo/photo_chrome_specular.png @ 80mm/hat_front`: #516(2m), #521(3m), #520(2m), #554(88→76, +STITCHES_TOO_SHORT), #558(1m), #561(B→C, +LETTERING_TOO_SMALL), #559(3m), #565(1m), #578(C→B, -STITCHES_TOO_SHORT), #572(B→C, +ARTWORK_UNCOVERED)
- `photo/photo_chrome_specular.png @ 80mm/left_chest`: #516(1m), #521(3m), #520(2m), #554(5m), #561(4m), #559(3m), #565(1m), #578(2m), #572(C→D, +ARTWORK_UNCOVERED)
- `photo/photo_dof_meadow.png @ 80mm/hat_front`: #516(C→B, -STITCHES_TOO_SHORT), #521(2m), #520(1m), #537(3m), #554(B→C, +STITCHES_TOO_SHORT), #558(1m), #561(C→B, -STITCHES_TOO_SHORT), #559(2m), #565(2m), #578(2m), #572(B→C, +ARTWORK_UNCOVERED)
- `photo/photo_dof_meadow.png @ 80mm/left_chest`: #516(2m), #521(1m), #520(2m), #554(3m), #558(1m), #561(C→B, -STITCHES_TOO_SHORT), #559(2m), #565(1m), #567(2m), #572(B→C, +ARTWORK_UNCOVERED)
- `photo/photo_grass_macro.png @ 80mm/hat_front`: #516(22→10, +TRIM_HEAVY), #520(10→22, -TRIM_HEAVY), #554(F→D, -LETTERING_TOO_SMALL, -STITCHES_TOO_SHORT), #558(3m), #561(1m), #559(2m), #572(3m)
- `photo/photo_grass_macro.png @ 80mm/left_chest`: #520(2m), #554(10→22, -LETTERING_TOO_SMALL), #558(2m), #561(3m), #559(22→34, -STITCHES_TOO_SHORT), #572(3m)
- `photo/photo_owl_pale.png @ 80mm/hat_front`: #516(-STABILIZER_CUTAWAY), #537(46→58, -DENSITY_EXTREME), #554(+STABILIZER_CUTAWAY), #557(1m), #558(1m), #561(-STABILIZER_CUTAWAY), #559(+STABILIZER_CUTAWAY), #565(2m), #572(2m)
- `photo/photo_owl_pale.png @ 80mm/left_chest`: #537(46→58, -DENSITY_EXTREME), #554(58→46, +STITCHES_TOO_SHORT), #558(3m), #561(46→58, -STITCHES_TOO_SHORT), #559(2m), #572(1m)
- `photo/photo_scene_stub.png @ 80mm/hat_front`: #516(2m), #521(1m), #520(6m), #537(2m), #554(8m), #557(1m), #558(2m), #561(8m), #559(6m), #565(3m), #567(3m), #573(B→C, +SATIN_GAPS_TIGHT), #577(2m), #578(4m), #579(2m), #572(C→D, +ARTWORK_UNCOVERED), #608(2m)
- `photo/photo_scene_stub.png @ 80mm/left_chest`: #516(3m), #521(1m), #520(C→B, -ARTWORK_UNCOVERED), #523(2m), #537(1m), #554(9m), #557(1m), #558(3m), #561(5m), #559(3m), #565(2m), #567(2m), #573(B→C, +SATIN_GAPS_TIGHT), #577(1m), #578(2m), #572(C→D, +ARTWORK_UNCOVERED)
- `photo/photo_subject_stub.png @ 80mm/hat_front`: #572(D→C, -ARTWORK_UNCOVERED)
- `photo/photo_subject_stub.png @ 80mm/left_chest`: #572(D→C, -ARTWORK_UNCOVERED)
- `photo/photo_sunset_backlit.png @ 80mm/hat_front`: #516(2m), #521(1m), #520(2m), #554(76→88, -LETTERING_TOO_SMALL), #558(2m), #561(B→A, -STITCHES_TOO_SHORT), #559(A→B, +STITCHES_TOO_SHORT), #572(88→76, +ARTWORK_UNCOVERED)
- `photo/photo_sunset_backlit.png @ 80mm/left_chest`: #516(3m), #521(2m), #520(3m), #554(76→88, -LETTERING_TOO_SMALL), #559(B→A, -STITCHES_TOO_SHORT), #572(A→B, +ARTWORK_UNCOVERED)
- `photo/region_blobs.png @ 80mm/hat_front`: #521(1m), #572(1m), #589(+THREAD_MATCH_POOR), #599(-THREAD_MATCH_POOR, -THREAD_MATCH_POOR)
- `photo/region_blobs.png @ 80mm/left_chest`: #521(1m), #572(1m), #589(+THREAD_MATCH_POOR), #599(-THREAD_MATCH_POOR, -THREAD_MATCH_POOR)
- `photo/repro_gradient_white_icon.png @ 80mm/hat_front`: #516(1m), #521(1m), #520(3m), #537(1m), #554(6m), #558(1m), #561(2m), #559(1m), #567(1m), #573(58→46, +SATIN_GAPS_TIGHT), #577(1m), #578(2m), #572(2m), #589(46→58, -SATIN_GAPS_TIGHT)
- `photo/repro_gradient_white_icon.png @ 80mm/left_chest`: #516(1m), #521(1m), #520(3m), #554(5m), #561(2m), #559(2m), #573(58→46, +SATIN_GAPS_TIGHT), #578(2m), #572(2m), #589(46→58, -SATIN_GAPS_TIGHT)
- `photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front`: #516(4m), #521(1m), #520(5m), #523(2m), #537(3m), #554(-STITCHES_TOO_SHORT), #558(1m), #559(7m), #572(2m), #589(0→22, -THREAD_MATCH_POOR, -THREAD_MATCH_POOR)
- `photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest`: #516(1m), #520(1m), #523(2m), #537(3m), #554(5m), #559(3m), #572(2m), #589(0→10, -THREAD_MATCH_POOR, -THREAD_MATCH_POOR)
- `photo/summit_badge.png @ 80mm/hat_front`: #516(4m), #521(1m), #520(4m), #523(2m), #537(4m), #554(8m), #561(1m), #559(-STITCHES_TOO_SHORT), #565(1m), #572(2m), #589(+STABILIZER_CUTAWAY, +THREAD_MATCH_POOR, -THREAD_MATCH_POOR), #614(1m)
- `photo/summit_badge.png @ 80mm/left_chest`: #516(5m), #521(3m), #520(3m), #537(4m), #554(1m), #558(1m), #561(1m), #559(3m), #572(2m), #589(+STABILIZER_CUTAWAY, +THREAD_MATCH_POOR, -THREAD_MATCH_POOR), #614(2m)
- `ribbon_curve.png @ 80mm/hat_front`: #554(1m), #572(1m)
- `ribbon_curve.png @ 80mm/left_chest`: #554(1m), #572(2m)

### Appendix C — every change point with its leaves

```
becker_marine_logo.png @ 80mm/hat_front
  @ da6606e4 #515: score 88 -> 76; ARTWORK_UNCOVERED:warn x0 -> x1; coverage_max: 4.8 -> 4.4; raw_score: 88 -> 76; satin_shapes: 8 -> 6; satin_short_fraction: 0.072 -> 0.054; satin_steps: 3215 -> 2869; trims_per_1000: 8.6 -> 6.8; uncovered_total_mm2: 0.0 -> 6.5; uncovered_worst_mm2: 4.8 -> 6.5
  @ 396a7458 #516: coverage_max: 4.4 -> 4.69; same_hole_fraction: 0.071 -> 0.062; satin_short_fraction: 0.054 -> 0.046; trims_per_1000: 6.8 -> 4.8
  @ 5d2db084 #520: score 76 -> 88; ARTWORK_UNCOVERED:warn x1 -> x0; coverage_max: 4.69 -> 5.93; coverage_p95: 3.52 -> 3.33; raw_score: 76 -> 88; same_hole_fraction: 0.062 -> 0.051; satin_shapes: 6 -> 8; satin_short_fraction: 0.046 -> 0.063; satin_steps: 2830 -> 4035; stitch_count: 7459 -> 6474; trims_per_1000: 4.8 -> 7.7; uncovered_total_mm2: 6.5 -> 0.0; uncovered_worst_mm2: 6.5 -> 2.8
  @ 24fce102 #523: satin_short_fraction: 0.063 -> 0.059; trims_per_1000: 7.7 -> 7.3
  @ 48b03066 #528: color_changes: 2 -> 1; uncovered_worst_mm2: 2.8 -> 2.2
  @ 00cdf44c #537: coverage_p95: 3.46 -> 3.23; satin_steps: 4017 -> 3716; stitch_count: 6377 -> 5980
  @ 8a48c3b4 #554: coverage_max: 5.94 -> 5.46; coverage_p50: 1.38 -> 1.45; satin_short_fraction: 0.062 -> 0.054; satin_steps: 3716 -> 3381; trims_per_1000: 7.4 -> 6.8; uncovered_worst_mm2: 2.2 -> 4.8
  @ 254eb3a4 #557: satin_short_fraction: 0.054 -> 0.051; trims_per_1000: 6.8 -> 6.3
  @ 89161704 #558: uncovered_worst_mm2: 4.8 -> 3.8
  @ 7cc7df4d #559: coverage_max: 5.46 -> 6.23; coverage_p95: 3.24 -> 3.52; satin_steps: 3393 -> 3828; stitch_count: 5902 -> 6328; uncovered_worst_mm2: 3.8 -> 3.5
  @ 722f5a9b #567: coverage_max: 6.23 -> 8.56; same_hole_fraction: 0.049 -> 0.046; satin_short_fraction: 0.051 -> 0.047; satin_steps: 3828 -> 4097; uncovered_worst_mm2: 3.5 -> 3.8
  @ 6706a71e #577: coverage_max: 8.56 -> 6.23; satin_short_fraction: 0.047 -> 0.05; satin_steps: 4097 -> 3890
  @ 1c3d067a #578: satin_short_fraction: 0.05 -> 0.044; satin_steps: 3890 -> 4388; stitch_count: 6315 -> 6813; trims_per_1000: 6.3 -> 5.9
  @ 41de6430 #572: score 88 -> 76; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 88 -> 76; uncovered_total_mm2: 0.0 -> 27.5; uncovered_wanted_mm2: 710.2 -> 1347.9; uncovered_worst_mm2: 3.8 -> 4.9
  @ 0c3b7725 #599: coverage_max: 6.23 -> 9.49; coverage_p95: 3.52 -> 3.86; same_hole_fraction: 0.045 -> 0.041; satin_gaps_judged: 1 -> 2; satin_shapes: 8 -> 9; satin_short_fraction: 0.045 -> 0.029; satin_steps: 4335 -> 4638; trims_per_1000: 6.0 -> 4.6; uncovered_hole_mm2: 4.9 -> 4.6; uncovered_holes: 10 -> 7; uncovered_patches: 65 -> 45; uncovered_total_mm2: 27.5 -> 15.9; uncovered_wanted_mm2: 1347.9 -> 1419.4; uncovered_worst_mm2: 4.9 -> 4.6
  @ 5337e2f6 #608: same_hole_fraction: 0.041 -> 0.044; satin_short_fraction: 0.029 -> 0.043; trims_per_1000: 4.6 -> 5.2; uncovered_hole_mm2: 4.6 -> 1.7; uncovered_holes: 7 -> 4; uncovered_patches: 45 -> 52; uncovered_total_mm2: 15.9 -> 5.9; uncovered_worst_mm2: 4.6 -> 1.7

becker_marine_logo.png @ 80mm/left_chest
  @ da6606e4 #515: coverage_area_mm2: 1956.0 -> 2069.0; coverage_max: 4.57 -> 4.11; same_hole_fraction: 0.067 -> 0.076; satin_shapes: 8 -> 6; satin_short_fraction: 0.082 -> 0.074; satin_steps: 3173 -> 2828; uncovered_total_mm2: 6.5 -> 18.5; uncovered_worst_mm2: 6.5 -> 18.5
  @ 396a7458 #516: coverage_max: 4.11 -> 4.56; same_hole_fraction: 0.076 -> 0.07; satin_short_fraction: 0.074 -> 0.058; trims_per_1000: 7.6 -> 5.4
  @ 5d2db084 #520: score 76 -> 88; ARTWORK_UNCOVERED:warn x1 -> x0; coverage_max: 4.56 -> 5.16; raw_score: 76 -> 88; same_hole_fraction: 0.07 -> 0.052; satin_shapes: 6 -> 8; satin_steps: 2786 -> 3644; stitch_count: 6436 -> 6057; trims_per_1000: 5.6 -> 6.9; uncovered_total_mm2: 18.5 -> 0.0; uncovered_worst_mm2: 18.5 -> 1.2
  @ 48b03066 #528: color_changes: 2 -> 1; satin_short_fraction: 0.059 -> 0.065; trims_per_1000: 6.9 -> 7.4; uncovered_worst_mm2: 1.2 -> 3.8
  @ 00cdf44c #537: coverage_max: 4.92 -> 4.35; same_hole_fraction: 0.051 -> 0.054; satin_short_fraction: 0.065 -> 0.07; satin_steps: 3715 -> 3461; trims_per_1000: 7.4 -> 8.0
  @ 8a48c3b4 #554: coverage_p50: 1.35 -> 1.46; same_hole_fraction: 0.054 -> 0.051; satin_short_fraction: 0.07 -> 0.06; satin_steps: 3461 -> 3227; trims_per_1000: 8.0 -> 7.2
  @ 254eb3a4 #557: satin_short_fraction: 0.06 -> 0.056; trims_per_1000: 7.2 -> 6.7
  @ 89161704 #558: uncovered_worst_mm2: 3.8 -> 3.2
  @ 7cc7df4d #559: coverage_max: 4.27 -> 6.14; coverage_p95: 3.15 -> 3.46; satin_short_fraction: 0.057 -> 0.054; satin_steps: 3230 -> 3648; stitch_count: 5691 -> 6101
  @ 722f5a9b #567: coverage_max: 6.14 -> 8.28; satin_short_fraction: 0.054 -> 0.049; satin_steps: 3648 -> 3843; uncovered_worst_mm2: 3.2 -> 3.8
  @ 6706a71e #577: coverage_max: 8.28 -> 6.14
  @ 1c3d067a #578: same_hole_fraction: 0.048 -> 0.045; satin_short_fraction: 0.051 -> 0.046; satin_steps: 3699 -> 4133; stitch_count: 6093 -> 6527; trims_per_1000: 6.4 -> 6.0
  @ 41de6430 #572: score 88 -> 76; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 88 -> 76; uncovered_total_mm2: 0.0 -> 29.3; uncovered_wanted_mm2: 730.2 -> 1347.9; uncovered_worst_mm2: 3.8 -> 5.1
  @ 0c3b7725 #599: coverage_max: 6.14 -> 9.24; coverage_p95: 3.41 -> 3.68; same_hole_fraction: 0.046 -> 0.041; satin_gaps_judged: 1 -> 2; satin_shapes: 8 -> 9; satin_steps: 4080 -> 4375; tiny_step_fraction: 0.08 -> 0.074; tiny_steps: 476 -> 441; trims_per_1000: 6.2 -> 4.7; uncovered_holes: 12 -> 11; uncovered_patches: 77 -> 60; uncovered_wanted_mm2: 1347.9 -> 1415.4
  @ 5337e2f6 #608: same_hole_fraction: 0.041 -> 0.045; satin_short_fraction: 0.044 -> 0.068; trims_per_1000: 4.7 -> 5.8; uncovered_hole_mm2: 4.9 -> 3.4; uncovered_holes: 11 -> 6; uncovered_patches: 60 -> 70; uncovered_total_mm2: 29.3 -> 13.4; uncovered_worst_mm2: 4.9 -> 3.4

logo_alpha.png @ 80mm/hat_front
  @ bff6b37a #521: trims_per_1000: 1.6 -> 1.8
  @ 41de6430 #572: uncovered_wanted_mm2: 1157.2 -> 1292.2; uncovered_worst_mm2: 0.0 -> 0.1

logo_alpha.png @ 80mm/left_chest
  @ 8a48c3b4 #554: satin_short_fraction: 0.05 -> 0.034
  @ 41de6430 #572: uncovered_wanted_mm2: 1141.8 -> 1280.2; uncovered_worst_mm2: 0.0 -> 0.1

logo_script_tires.png @ 80mm/hat_front
  @ 396a7458 #516: color_changes: 1 -> 0; coverage_p95: 2.99 -> 2.81; same_hole_fraction: 0.025 -> 0.027; satin_short_fraction: 0.037 -> 0.039
  @ 5d2db084 #520: coverage_p50: 1.34 -> 1.42; same_hole_fraction: 0.027 -> 0.025; satin_short_fraction: 0.039 -> 0.036; trims_per_1000: 3.8 -> 2.5
  @ 00cdf44c #537: coverage_p50: 1.45 -> 1.33; coverage_p95: 2.88 -> 2.55; same_hole_fraction: 0.025 -> 0.027; satin_short_fraction: 0.036 -> 0.039; satin_steps: 1580 -> 1428; stitch_count: 2434 -> 2232; trims_per_1000: 2.5 -> 2.7
  @ 8a48c3b4 #554: coverage_max: 5.09 -> 5.35; same_hole_fraction: 0.027 -> 0.024; satin_short_fraction: 0.039 -> 0.019; satin_steps: 1428 -> 1310
  @ 254eb3a4 #557: same_hole_fraction: 0.024 -> 0.021; satin_short_fraction: 0.019 -> 0.013; trims_per_1000: 2.8 -> 1.9
  @ 7cc7df4d #559: coverage_p95: 2.5 -> 2.76; same_hole_fraction: 0.021 -> 0.023; satin_short_fraction: 0.013 -> 0.02; satin_steps: 1298 -> 1425; stitch_count: 2119 -> 2230; trims_per_1000: 1.9 -> 3.1
  @ d59ff556 #573: score 100 -> 88; grade A -> B; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 100 -> 88
  @ 1c3d067a #578: same_hole_fraction: 0.023 -> 0.021; satin_short_fraction: 0.02 -> 0.018; satin_steps: 1425 -> 1639; stitch_count: 2230 -> 2444; trims_per_1000: 3.1 -> 2.9
  @ 41de6430 #572: uncovered_wanted_mm2: 507.0 -> 737.7; uncovered_worst_mm2: 0.0 -> 0.1

logo_script_tires.png @ 80mm/left_chest
  @ 396a7458 #516: score 88 -> 100; grade B -> A; TRIM_HEAVY:warn x1 -> x0; coverage_p50: 1.27 -> 1.36; raw_score: 88 -> 100; same_hole_fraction: 0.028 -> 0.026; trims_per_1000: 4.7 -> 3.8
  @ 5d2db084 #520: coverage_p50: 1.36 -> 1.47; same_hole_fraction: 0.026 -> 0.032; satin_short_fraction: 0.033 -> 0.041; stitch_count: 2352 -> 2487; trims_per_1000: 3.8 -> 3.6
  @ 24fce102 #523: same_hole_fraction: 0.032 -> 0.024; satin_short_fraction: 0.041 -> 0.03; trims_per_1000: 3.6 -> 2.0
  @ 00cdf44c #537: coverage_p95: 3.27 -> 2.88; same_hole_fraction: 0.024 -> 0.026; satin_short_fraction: 0.03 -> 0.033; satin_steps: 1447 -> 1341; stitch_count: 2475 -> 2295; trims_per_1000: 2.0 -> 2.2
  @ 8a48c3b4 #554: color_changes: 1 -> 0; coverage_p50: 1.42 -> 1.55; same_hole_fraction: 0.026 -> 0.021; satin_short_fraction: 0.033 -> 0.023; trims_per_1000: 2.2 -> 2.9
  @ 254eb3a4 #557: same_hole_fraction: 0.021 -> 0.017; satin_short_fraction: 0.023 -> 0.014; trims_per_1000: 2.9 -> 1.7
  @ 7cc7df4d #559: coverage_p95: 2.89 -> 3.13; same_hole_fraction: 0.017 -> 0.02; satin_short_fraction: 0.014 -> 0.018; satin_steps: 1290 -> 1416; stitch_count: 2380 -> 2500; trims_per_1000: 1.7 -> 2.4
  @ d59ff556 #573: score 100 -> 88; grade A -> B; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 100 -> 88
  @ 1c3d067a #578: satin_short_fraction: 0.018 -> 0.017; satin_steps: 1416 -> 1568; stitch_count: 2500 -> 2652
  @ 41de6430 #572: uncovered_wanted_mm2: 503.8 -> 736.5; uncovered_worst_mm2: 0.0 -> 0.1
  @ de1d2c0a #614: uncovered_patches: 9 -> 7

logo_whitebg.png @ 80mm/hat_front
  @ bff6b37a #521: trims_per_1000: 1.6 -> 1.8
  @ 41de6430 #572: uncovered_wanted_mm2: 1151.8 -> 1280.3; uncovered_worst_mm2: 0.0 -> 0.2

logo_whitebg.png @ 80mm/left_chest
  @ 8a48c3b4 #554: satin_short_fraction: 0.05 -> 0.034
  @ 41de6430 #572: uncovered_wanted_mm2: 1139.8 -> 1277.0; uncovered_worst_mm2: 0.0 -> 0.1

photo/drone_render.png @ 80mm/hat_front
  @ 396a7458 #516: legibility: 0.545 -> 0.5; legibility_worst: 0.545 -> 0.5; trims_per_1000: 8.1 -> 7.6; uncovered_worst_mm2: 2.8 -> 2.2
  @ 5d2db084 #520: LETTERING_ILLEGIBLE:warn x0 -> x1; legibility: 0.5 -> 0.222; legibility_worst: 0.5 -> 0.222; raw_score: -110 -> -122; uncovered_worst_mm2: 2.2 -> 1.5
  @ 24fce102 #523: legibility: 0.222 -> 0.462; legibility_worst: 0.222 -> 0.462; link_segments: 1 -> 2; link_thread_mm: 0.2 -> 0.6
  @ 00cdf44c #537: legibility: 0.462 -> 0.429; legibility_worst: 0.462 -> 0.429; link_segments: 2 -> 6; link_thread_mm: 0.6 -> 3.9
  @ 8a48c3b4 #554: color_changes: 14 -> 15; coverage_max: 7.27 -> 12.49; legibility: 0.429 -> 0.167; legibility_worst: 0.429 -> 0.167; link_segments: 6 -> 1; link_thread_mm: 3.9 -> 0.2; satin_short_fraction: 0.217 -> 0.139; uncovered_worst_mm2: 1.5 -> 0.2
  @ 89161704 #558: coverage_max: 12.49 -> 11.71
  @ 08c46a54 #561: coverage_max: 11.71 -> 7.51; satin_steps: 3965 -> 3696; trims_per_1000: 7.2 -> 7.6; uncovered_worst_mm2: 0.2 -> 0.8
  @ 7cc7df4d #559: link_segments: 1 -> 2; link_thread_mm: 0.2 -> 0.3
  @ 41de6430 #572: ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: -122 -> -134; uncovered_total_mm2: 0.0 -> 2.1; uncovered_wanted_mm2: 1968.5 -> 3063.9; uncovered_worst_mm2: 0.8 -> 2.1
  @ e851e5aa #589: THREAD_MATCH_POOR:block x5 -> x3; THREAD_MATCH_POOR:warn x2 -> x6; color_changes: 15 -> 16; coverage_max: 7.85 -> 9.52; ground_span_frac: 0.478 -> 0.571; link_segments: 2 -> 1; link_thread_mm: 0.3 -> 0.2; raw_score: -134 -> -122; same_hole_fraction: 0.061 -> 0.071; satin_gaps_judged: 9 -> 10; satin_shapes: 58 -> 61; satin_steps: 3888 -> 4432; thread_worst_delta_e: 18.1 -> 19.8; trims_per_1000: 7.5 -> 7.9; uncovered_hole_mm2: 2.1 -> 1.8; uncovered_patches: 37 -> 35; uncovered_total_mm2: 2.1 -> 1.8; uncovered_worst_mm2: 2.1 -> 1.8
  @ 5337e2f6 #608: ARTWORK_UNCOVERED:warn x1 -> x0; raw_score: -122 -> -110; uncovered_hole_mm2: 1.8 -> 0.0; uncovered_holes: 1 -> 0; uncovered_patches: 35 -> 37; uncovered_total_mm2: 1.8 -> 0.0; uncovered_worst_mm2: 1.8 -> 0.4

photo/drone_render.png @ 80mm/left_chest
  @ 396a7458 #516: LETTERING_ILLEGIBLE:warn x1 -> x0; coverage_max: 10.7 -> 6.63; legibility: 0.333 -> 0.545; legibility_worst: 0.333 -> 0.545; link_segments: 2 -> 1; link_thread_mm: 0.4 -> 0.2; raw_score: -122 -> -110; same_hole_fraction: 0.068 -> 0.063; satin_steps: 4229 -> 3839; trims_per_1000: 7.4 -> 6.7
  @ 5d2db084 #520: LETTERING_ILLEGIBLE:warn x0 -> x1; legibility: 0.545 -> 0.364; legibility_worst: 0.545 -> 0.364; raw_score: -110 -> -122
  @ 24fce102 #523: link_segments: 1 -> 2
  @ 00cdf44c #537: satin_short_fraction: 0.233 -> 0.219; satin_steps: 3892 -> 3692
  @ 8a48c3b4 #554: color_changes: 14 -> 15; coverage_max: 6.48 -> 9.92; legibility: 0.364 -> 0.2; legibility_worst: 0.364 -> 0.2; link_segments: 2 -> 1; satin_short_fraction: 0.219 -> 0.202; satin_steps: 3692 -> 3955
  @ 89161704 #558: coverage_max: 9.92 -> 10.57
  @ 08c46a54 #561: coverage_max: 10.57 -> 12.7; satin_short_fraction: 0.202 -> 0.215
  @ 7cc7df4d #559: legibility: 0.2 -> 0.182; legibility_worst: 0.2 -> 0.182; link_segments: 1 -> 2; link_thread_mm: 0.2 -> 0.4; satin_steps: 4063 -> 4325
  @ 41de6430 #572: uncovered_wanted_mm2: 1944.0 -> 3058.9; uncovered_worst_mm2: 0.2 -> 0.4
  @ e851e5aa #589: THREAD_MATCH_POOR:block x5 -> x3; THREAD_MATCH_POOR:warn x2 -> x6; color_changes: 15 -> 16; coverage_max: 12.66 -> 8.31; ground_span_frac: 0.478 -> 0.571; legibility: 0.182 -> 0.2; legibility_worst: 0.182 -> 0.2; link_segments: 2 -> 1; link_thread_mm: 0.4 -> 0.2; raw_score: -122 -> -110; same_hole_fraction: 0.065 -> 0.069; satin_gaps_judged: 9 -> 10; satin_shapes: 58 -> 61; thread_worst_delta_e: 18.1 -> 19.8; trims_per_1000: 6.5 -> 7.6; uncovered_patches: 51 -> 48; uncovered_worst_mm2: 0.4 -> 0.5

photo/enthusiast_logo.png @ 80mm/hat_front
  @ 396a7458 #516: coverage_max: 6.37 -> 6.0; coverage_p50: 1.48 -> 1.59; legibility: 0.542 -> 0.686; legibility_worst: 0.286 -> 0.462; link_segments: 1 -> 0; link_thread_mm: 0.4 -> 0.0; satin_short_fraction: 0.107 -> 0.092; trims_per_1000: 9.2 -> 7.2; uncovered_worst_mm2: 0.5 -> 0.0
  @ 5d2db084 #520: coverage_max: 6.0 -> 6.43; same_hole_fraction: 0.128 -> 0.12; satin_short_fraction: 0.092 -> 0.073; trims_per_1000: 7.2 -> 4.9
  @ 24fce102 #523: satin_short_fraction: 0.073 -> 0.089; trims_per_1000: 4.9 -> 6.1
  @ 00cdf44c #537: satin_steps: 1374 -> 1288
  @ 8a48c3b4 #554: score 76 -> 88; LETTERING_ILLEGIBLE:warn x1 -> x0; coverage_max: 6.41 -> 4.05; coverage_p50: 1.57 -> 1.37; coverage_p95: 3.54 -> 3.29; legibility: 0.686 -> 1.0; legibility_worst: 0.462 -> 1.0; raw_score: 76 -> 88; same_hole_fraction: 0.129 -> 0.107; satin_short_fraction: 0.093 -> 0.051; satin_steps: 1288 -> 1037; stitch_count: 3125 -> 2530
  @ 254eb3a4 #557: satin_short_fraction: 0.051 -> 0.04; trims_per_1000: 6.3 -> 5.1
  @ 7cc7df4d #559: satin_short_fraction: 0.04 -> 0.037; satin_steps: 1025 -> 1095
  @ 41de6430 #572: score 88 -> 76; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 88 -> 76; uncovered_total_mm2: 0.0 -> 1.2; uncovered_wanted_mm2: 161.5 -> 377.6; uncovered_worst_mm2: 0.0 -> 1.2
  @ 5337e2f6 #608: score 76 -> 88; ARTWORK_UNCOVERED:warn x1 -> x0; raw_score: 76 -> 88; satin_short_fraction: 0.037 -> 0.05; trims_per_1000: 5.0 -> 5.3; uncovered_hole_mm2: 1.2 -> 0.0; uncovered_holes: 1 -> 0; uncovered_patches: 13 -> 14; uncovered_total_mm2: 1.2 -> 0.0; uncovered_worst_mm2: 1.2 -> 0.5

photo/enthusiast_logo.png @ 80mm/left_chest
  @ 396a7458 #516: legibility_worst: 0.929 -> 1.0; link_segments: 1 -> 0; link_thread_mm: 0.4 -> 0.0; same_hole_fraction: 0.122 -> 0.113; satin_short_fraction: 0.115 -> 0.088; satin_steps: 1262 -> 1165; trims_per_1000: 9.6 -> 6.6; uncovered_worst_mm2: 1.5 -> 0.0
  @ 5d2db084 #520: satin_short_fraction: 0.088 -> 0.095; satin_steps: 1165 -> 1269; trims_per_1000: 6.6 -> 7.1
  @ 24fce102 #523: satin_short_fraction: 0.095 -> 0.08; trims_per_1000: 7.1 -> 4.4
  @ 00cdf44c #537: legibility_worst: 1.0 -> 0.929; satin_short_fraction: 0.08 -> 0.074; satin_steps: 1249 -> 1169
  @ 8a48c3b4 #554: coverage_max: 4.19 -> 4.41; satin_short_fraction: 0.074 -> 0.053; satin_steps: 1169 -> 1036; trims_per_1000: 4.6 -> 6.3
  @ 254eb3a4 #557: satin_short_fraction: 0.053 -> 0.046; trims_per_1000: 6.3 -> 5.9
  @ 7cc7df4d #559: coverage_max: 4.41 -> 4.84; satin_short_fraction: 0.046 -> 0.043; satin_steps: 1030 -> 1114
  @ 41de6430 #572: score 88 -> 76; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 88 -> 76; uncovered_total_mm2: 0.0 -> 2.6; uncovered_wanted_mm2: 160.0 -> 381.9; uncovered_worst_mm2: 0.0 -> 1.6
  @ 5337e2f6 #608: satin_short_fraction: 0.043 -> 0.052; uncovered_hole_mm2: 1.6 -> 1.0; uncovered_holes: 2 -> 1; uncovered_patches: 27 -> 29; uncovered_total_mm2: 2.6 -> 1.0; uncovered_worst_mm2: 1.6 -> 1.0

photo/fur_ramp.png @ 80mm/hat_front
  @ 41de6430 #572: uncovered_wanted_mm2: 1097.5 -> 1284.9

photo/fur_ramp.png @ 80mm/left_chest
  @ 41de6430 #572: uncovered_wanted_mm2: 1094.8 -> 1285.6

photo/gradient_ramp_radial.png @ 80mm/hat_front
  @ bff6b37a #521: trims_per_1000: 0.3 -> 0.4
  @ 0c3b7725 #599: color_changes: 5 -> 6; coverage_max: 4.04 -> 4.62; trims_per_1000: 0.4 -> 0.7

photo/gradient_ramp_radial.png @ 80mm/left_chest
  @ bff6b37a #521: coverage_max: 4.41 -> 4.06; trims_per_1000: 0.3 -> 0.4
  @ 0c3b7725 #599: color_changes: 5 -> 6; coverage_max: 4.06 -> 4.47; trims_per_1000: 0.4 -> 0.6

photo/logo_bridge_bar.jpg @ 80mm/hat_front
  @ da6606e4 #515: STITCHES_TOO_SHORT:warn x0 -> x1; color_changes: 15 -> 16; coverage_p95: 4.12 -> 4.42; legibility: 0.133 -> 0.0; legibility_worst: 0.133 -> 0.0; link_segments: 0 -> 1; link_thread_mm: 0.0 -> 0.3; raw_score: -38 -> -50; satin_shapes: 28 -> 26; satin_short_fraction: 0.218 -> 0.301; satin_steps: 4701 -> 4154; trims_per_1000: 8.2 -> 7.6; uncovered_wanted_mm2: 1374.0 -> 1736.0
  @ 396a7458 #516: legibility: 0.0 -> 0.133; legibility_worst: 0.0 -> 0.133; trims_per_1000: 7.6 -> 6.4; uncovered_worst_mm2: 0.2 -> 0.0
  @ 5d2db084 #520: coverage_max: 6.67 -> 8.94; coverage_p95: 4.36 -> 4.58; satin_steps: 4096 -> 4401
  @ 24fce102 #523: legibility: 0.133 -> 0.0; legibility_worst: 0.133 -> 0.0
  @ 00cdf44c #537: coverage_max: 8.94 -> 8.25; legibility: 0.0 -> 0.25; legibility_worst: 0.0 -> 0.25
  @ 8a48c3b4 #554: STITCHES_TOO_SHORT:warn x1 -> x0; color_changes: 16 -> 15; coverage_max: 8.25 -> 14.66; coverage_p95: 4.57 -> 5.04; legibility: 0.25 -> 0.225; legibility_worst: 0.25 -> 0.225; raw_score: -50 -> -38; same_hole_fraction: 0.063 -> 0.072; satin_short_fraction: 0.272 -> 0.152; satin_steps: 4209 -> 5451; stitch_count: 14401 -> 15768; trims_per_1000: 6.2 -> 6.7; uncovered_worst_mm2: 0.0 -> 0.2
  @ 254eb3a4 #557: trims_per_1000: 6.7 -> 6.3
  @ 89161704 #558: link_segments: 1 -> 2; link_thread_mm: 0.3 -> 0.7; satin_short_fraction: 0.149 -> 0.14; uncovered_worst_mm2: 0.2 -> 1.0
  @ 08c46a54 #561: coverage_max: 15.13 -> 13.67; legibility: 0.231 -> 0.095; legibility_worst: 0.231 -> 0.095; link_segments: 2 -> 3; link_thread_mm: 0.7 -> 1.0; satin_steps: 5640 -> 5063; uncovered_worst_mm2: 1.0 -> 1.2
  @ 7cc7df4d #559: coverage_max: 13.67 -> 14.97; coverage_p95: 5.09 -> 5.55; legibility: 0.095 -> 0.1; legibility_worst: 0.095 -> 0.1; satin_steps: 5063 -> 5917; stitch_count: 15268 -> 16093; uncovered_worst_mm2: 1.2 -> 0.2
  @ 722f5a9b #567: coverage_max: 14.52 -> 15.55
  @ d59ff556 #573: SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: -38 -> -50
  @ 6706a71e #577: coverage_max: 15.55 -> 14.52
  @ 1c3d067a #578: legibility: 0.1 -> 0.111; legibility_worst: 0.1 -> 0.111
  @ 41de6430 #572: uncovered_wanted_mm2: 1740.8 -> 2440.1; uncovered_worst_mm2: 0.2 -> 0.6
  @ e851e5aa #589: THREAD_MATCH_POOR:block x3 -> x5; THREAD_MATCH_POOR:warn x0 -> x1; color_changes: 15 -> 13; coverage_max: 14.52 -> 8.85; ground_area_frac: 0.454 -> 0.401; legibility: 0.111 -> 0.0; legibility_clusters: 0 -> 1; legibility_worst: 0.111 -> 0.0; link_segments: 3 -> 0; link_thread_mm: 1.0 -> 0.0; raw_score: -50 -> -122; same_hole_fraction: 0.068 -> 0.079; satin_gaps_judged: 11 -> 6; satin_gaps_tight_shapes: 3 -> 2; satin_gaps_tight_worst_frac: 0.616 -> 0.426; satin_shapes: 27 -> 25; satin_short_fraction: 0.124 -> 0.105; satin_steps: 6271 -> 5547; thread_worst_delta_e: 12.4 -> 14.5; trims_per_1000: 6.2 -> 7.0; uncovered_patches: 23 -> 42; uncovered_worst_mm2: 0.6 -> 0.3
  @ 0c3b7725 #599: LETTERING_ILLEGIBLE:warn x1 -> x0; THREAD_MATCH_POOR:block x5 -> x3; THREAD_MATCH_POOR:warn x1 -> x4; color_changes: 13 -> 12; coverage_max: 8.85 -> 8.16; ground_area_frac: 0.401 -> 0.355; legibility_readable: 1 -> 0; link_segments: 0 -> 4; link_thread_mm: 0.0 -> 4.7; raw_score: -122 -> -86; same_hole_fraction: 0.079 -> 0.063; satin_gaps_judged: 6 -> 10; satin_gaps_tight_shapes: 2 -> 3; satin_gaps_tight_worst_frac: 0.426 -> 0.383; satin_shapes: 25 -> 31; satin_short_fraction: 0.105 -> 0.154; satin_steps: 5547 -> 6399; thread_worst_delta_e: 14.5 -> 26.3; trims_per_1000: 7.0 -> 5.2; uncovered_patches: 42 -> 9; uncovered_worst_mm2: 0.3 -> 0.4

photo/logo_bridge_bar.jpg @ 80mm/left_chest
  @ da6606e4 #515: color_changes: 14 -> 15; coverage_p95: 3.99 -> 4.23; legibility: 0.125 -> 0.133; legibility_worst: 0.125 -> 0.133; satin_shapes: 28 -> 26; satin_short_fraction: 0.278 -> 0.302; satin_steps: 5075 -> 4262; uncovered_wanted_mm2: 1376.5 -> 1740.8; uncovered_worst_mm2: 0.0 -> 0.2
  @ 396a7458 #516: coverage_max: 6.91 -> 7.4; legibility: 0.133 -> 0.125; legibility_worst: 0.133 -> 0.125; same_hole_fraction: 0.072 -> 0.068; satin_short_fraction: 0.302 -> 0.279; trims_per_1000: 8.0 -> 6.3
  @ 5d2db084 #520: legibility: 0.125 -> 0.167; legibility_worst: 0.125 -> 0.167; satin_steps: 4086 -> 4418; uncovered_worst_mm2: 0.2 -> 0.5
  @ 00cdf44c #537: legibility: 0.171 -> 0.19; legibility_worst: 0.171 -> 0.19; satin_steps: 4406 -> 4182
  @ 8a48c3b4 #554: STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 7.52 -> 10.14; coverage_p95: 4.32 -> 4.6; legibility: 0.19 -> 0.208; legibility_worst: 0.19 -> 0.208; link_segments: 0 -> 1; link_thread_mm: 0.0 -> 0.4; raw_score: -50 -> -38; satin_short_fraction: 0.269 -> 0.245; satin_steps: 4182 -> 5427; stitch_count: 14677 -> 15811; trims_per_1000: 6.6 -> 7.0; uncovered_worst_mm2: 0.5 -> 1.5
  @ 89161704 #558: legibility: 0.208 -> 0.165; legibility_worst: 0.208 -> 0.165; uncovered_worst_mm2: 1.5 -> 1.0
  @ 08c46a54 #561: coverage_max: 10.27 -> 13.03; link_segments: 1 -> 2; link_thread_mm: 0.4 -> 0.8; satin_steps: 5569 -> 5036; uncovered_worst_mm2: 1.0 -> 1.2
  @ 7cc7df4d #559: coverage_max: 13.03 -> 14.24; coverage_p95: 4.6 -> 5.04; legibility: 0.165 -> 0.176; legibility_worst: 0.165 -> 0.176; satin_short_fraction: 0.228 -> 0.212; satin_steps: 5036 -> 5794; uncovered_worst_mm2: 1.2 -> 0.2
  @ ce8bdb89 #565: legibility: 0.176 -> 0.202; legibility_worst: 0.176 -> 0.202
  @ 722f5a9b #567: legibility: 0.202 -> 0.146; legibility_worst: 0.202 -> 0.146
  @ d59ff556 #573: SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: -38 -> -50
  @ 6706a71e #577: legibility: 0.146 -> 0.202; legibility_worst: 0.146 -> 0.202
  @ 41de6430 #572: uncovered_wanted_mm2: 1730.2 -> 2440.1; uncovered_worst_mm2: 0.2 -> 0.6
  @ e851e5aa #589: ARTWORK_UNCOVERED:warn x0 -> x1; THREAD_MATCH_POOR:block x3 -> x5; THREAD_MATCH_POOR:warn x0 -> x1; color_changes: 15 -> 13; coverage_max: 14.62 -> 9.6; ground_area_frac: 0.454 -> 0.401; legibility: 0.202 -> 0.0; legibility_clusters: 0 -> 1; legibility_worst: 0.202 -> 0.0; link_segments: 2 -> 0; link_thread_mm: 0.8 -> 0.0; raw_score: -50 -> -134; same_hole_fraction: 0.07 -> 0.083; satin_gaps_judged: 11 -> 6; satin_gaps_tight_shapes: 3 -> 2; satin_gaps_tight_worst_frac: 0.563 -> 0.309; satin_shapes: 27 -> 25; satin_short_fraction: 0.208 -> 0.176; satin_steps: 5831 -> 5380; thread_worst_delta_e: 12.4 -> 14.5; trims_per_1000: 5.8 -> 6.9; uncovered_hole_mm2: 0.0 -> 2.2; uncovered_holes: 0 -> 1; uncovered_patches: 67 -> 20; uncovered_total_mm2: 0.0 -> 2.2; uncovered_worst_mm2: 0.6 -> 2.2
  @ 0c3b7725 #599: ARTWORK_UNCOVERED:warn x1 -> x0; LETTERING_ILLEGIBLE:warn x1 -> x0; STITCHES_TOO_SHORT:warn x0 -> x1; THREAD_MATCH_POOR:block x5 -> x3; THREAD_MATCH_POOR:warn x1 -> x4; color_changes: 13 -> 12; coverage_max: 9.6 -> 8.33; ground_area_frac: 0.401 -> 0.355; legibility_readable: 1 -> 0; link_segments: 0 -> 5; link_thread_mm: 0.0 -> 5.0; raw_score: -134 -> -98; same_hole_fraction: 0.083 -> 0.069; satin_gaps_judged: 6 -> 10; satin_gaps_tight_shapes: 2 -> 3; satin_shapes: 25 -> 31; satin_short_fraction: 0.176 -> 0.286; satin_steps: 5380 -> 6455; thread_worst_delta_e: 14.5 -> 26.3; tiny_step_fraction: 0.14 -> 0.133; tiny_steps: 2119 -> 1989; trims_per_1000: 6.9 -> 5.5; uncovered_hole_mm2: 2.2 -> 0.0; uncovered_holes: 1 -> 0; uncovered_patches: 20 -> 13; uncovered_total_mm2: 2.2 -> 0.0; uncovered_worst_mm2: 2.2 -> 0.5

photo/logo_gaulke_roofing.png @ 80mm/hat_front
  @ 396a7458 #516: coverage_max: 5.14 -> 5.42; coverage_p95: 2.72 -> 2.9; legibility: 0.806 -> 0.758; legibility_worst: 0.806 -> 0.758; link_segments: 2 -> 1; link_thread_mm: 0.4 -> 0.1; same_hole_fraction: 0.082 -> 0.066; satin_short_fraction: 0.266 -> 0.252; satin_steps: 2894 -> 2705; stitch_count: 4539 -> 4310; trims_per_1000: 12.1 -> 8.8
  @ 5d2db084 #520: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 5.42 -> 4.76; legibility: 0.758 -> 0.824; legibility_worst: 0.758 -> 0.824; raw_score: 64 -> 76; satin_short_fraction: 0.252 -> 0.23; trims_per_1000: 8.8 -> 7.9
  @ 24fce102 #523: legibility: 0.824 -> 0.866; legibility_worst: 0.824 -> 0.866; trims_per_1000: 7.9 -> 7.0
  @ 00cdf44c #537: legibility: 0.866 -> 0.806; legibility_worst: 0.866 -> 0.806; same_hole_fraction: 0.06 -> 0.063; satin_steps: 2756 -> 2530; stitch_count: 4263 -> 4021; trims_per_1000: 7.0 -> 7.5
  @ 8a48c3b4 #554: coverage_max: 4.74 -> 6.74; legibility: 0.806 -> 0.692; legibility_worst: 0.806 -> 0.692; link_segments: 1 -> 2; link_thread_mm: 0.1 -> 0.4; satin_short_fraction: 0.215 -> 0.117; trims_per_1000: 7.5 -> 8.1
  @ 08c46a54 #561: coverage_max: 6.72 -> 6.01
  @ 7cc7df4d #559: coverage_p95: 2.83 -> 3.0; satin_steps: 2527 -> 2721
  @ ce8bdb89 #565: legibility: 0.692 -> 0.925; legibility_worst: 0.692 -> 0.925
  @ d59ff556 #573: score 76 -> 64; grade B -> C; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 76 -> 64
  @ 41de6430 #572: uncovered_wanted_mm2: 209.0 -> 669.8; uncovered_worst_mm2: 0.0 -> 0.6
  @ e851e5aa #589: coverage_max: 6.09 -> 4.8; same_hole_fraction: 0.063 -> 0.056; thread_worst_delta_e: 18.5 -> 13.4; trims_per_1000: 7.9 -> 7.4; uncovered_worst_mm2: 0.6 -> 0.4

photo/logo_gaulke_roofing.png @ 80mm/left_chest
  @ 396a7458 #516: link_segments: 1 -> 12; link_thread_mm: 0.2 -> 21.4; satin_short_fraction: 0.268 -> 0.254; uncovered_worst_mm2: 0.0 -> 0.2
  @ 5d2db084 #520: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 5.59 -> 8.15; raw_score: 64 -> 76; same_hole_fraction: 0.067 -> 0.062; satin_short_fraction: 0.254 -> 0.226; trims_per_1000: 8.5 -> 6.6
  @ 24fce102 #523: coverage_max: 8.15 -> 7.52; link_segments: 12 -> 1; link_thread_mm: 21.4 -> 0.2; trims_per_1000: 6.6 -> 7.5
  @ 00cdf44c #537: coverage_p50: 1.07 -> 1.0; legibility: 0.853 -> 0.746; legibility_worst: 0.853 -> 0.746; satin_short_fraction: 0.235 -> 0.216; satin_steps: 2895 -> 2661; stitch_count: 4406 -> 4168; trims_per_1000: 7.5 -> 7.9
  @ 8a48c3b4 #554: coverage_max: 7.2 -> 6.82; legibility: 0.746 -> 1.0; legibility_worst: 0.746 -> 1.0; link_segments: 1 -> 2; link_thread_mm: 0.2 -> 0.5; same_hole_fraction: 0.067 -> 0.071; satin_short_fraction: 0.216 -> 0.164; uncovered_worst_mm2: 0.2 -> 0.0
  @ 08c46a54 #561: coverage_max: 6.96 -> 6.1
  @ 7cc7df4d #559: satin_steps: 2543 -> 2683
  @ ce8bdb89 #565: trims_per_1000: 7.4 -> 6.7
  @ d59ff556 #573: score 76 -> 64; grade B -> C; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 76 -> 64
  @ 41de6430 #572: uncovered_wanted_mm2: 215.8 -> 680.7; uncovered_worst_mm2: 0.0 -> 0.3
  @ e851e5aa #589: coverage_max: 6.12 -> 5.39; link_segments: 2 -> 1; link_thread_mm: 0.5 -> 0.2; satin_short_fraction: 0.152 -> 0.164; thread_worst_delta_e: 18.5 -> 13.4; trims_per_1000: 6.7 -> 7.8; uncovered_patches: 48 -> 53

photo/logo_golden_tee.jpg @ 80mm/hat_front
  @ 396a7458 #516: STITCHES_TOO_SHORT:warn x1 -> x0; coverage_p50: 1.47 -> 1.66; coverage_p95: 3.63 -> 3.96; link_segments: 3 -> 10; link_thread_mm: 1.0 -> 17.3; raw_score: -80 -> -68; same_hole_fraction: 0.066 -> 0.059; satin_short_fraction: 0.262 -> 0.247; trims_per_1000: 10.0 -> 6.8; uncovered_worst_mm2: 0.2 -> 0.0
  @ 5d2db084 #520: color_changes: 12 -> 13; coverage_max: 6.7 -> 8.2; link_segments: 10 -> 3; link_thread_mm: 17.3 -> 1.1; trims_per_1000: 6.8 -> 5.7; uncovered_worst_mm2: 0.0 -> 0.2
  @ 8a48c3b4 #554: DENSITY_STACKED:warn x0 -> x1; STITCHES_TOO_SHORT:warn x0 -> x1; coverage_max: 8.2 -> 17.73; coverage_over_warn_mm2: 0.0 -> 36.0; coverage_p50: 1.6 -> 1.97; coverage_p95: 3.9 -> 7.59; link_segments: 3 -> 4; link_thread_mm: 1.1 -> 3.2; raw_score: -68 -> -92; same_hole_fraction: 0.059 -> 0.089; satin_shapes: 29 -> 31; satin_short_fraction: 0.244 -> 0.266; satin_steps: 5304 -> 8826; stitch_count: 7047 -> 11621; trims_per_1000: 5.8 -> 4.5
  @ 254eb3a4 #557: TRIM_HEAVY:warn x1 -> x0; raw_score: -92 -> -80; trims_per_1000: 4.5 -> 4.0
  @ 89161704 #558: TRIM_HEAVY:warn x0 -> x1; coverage_max: 17.34 -> 15.14; coverage_over_warn_mm2: 36.0 -> 28.0; raw_score: -80 -> -92; trims_per_1000: 4.0 -> 4.3; uncovered_worst_mm2: 0.2 -> 0.0
  @ 08c46a54 #561: DENSITY_STACKED:warn x1 -> x0; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 15.14 -> 10.6; coverage_over_warn_mm2: 28.0 -> 0.0; coverage_p50: 1.99 -> 1.78; coverage_p95: 7.64 -> 4.4; link_segments: 4 -> 0; link_thread_mm: 3.2 -> 0.0; raw_score: -92 -> -68; same_hole_fraction: 0.088 -> 0.054; satin_short_fraction: 0.261 -> 0.214; satin_steps: 9182 -> 5643; stitch_count: 11969 -> 7590; trims_per_1000: 4.3 -> 5.4
  @ 7cc7df4d #559: coverage_p95: 4.4 -> 4.74; same_hole_fraction: 0.054 -> 0.059; satin_steps: 5643 -> 6092; stitch_count: 7590 -> 8055
  @ ce8bdb89 #565: coverage_max: 10.76 -> 13.8; coverage_p95: 4.74 -> 5.57; satin_short_fraction: 0.206 -> 0.135; trims_per_1000: 5.5 -> 5.2
  @ d59ff556 #573: SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: -68 -> -80
  @ 41de6430 #572: uncovered_wanted_mm2: 377.0 -> 879.8; uncovered_worst_mm2: 0.0 -> 0.6
  @ e851e5aa #589: ARTWORK_UNCOVERED:warn x0 -> x1; THREAD_MATCH_POOR:block x2 -> x1; THREAD_MATCH_POOR:warn x6 -> x7; coverage_max: 13.8 -> 12.39; coverage_p50: 1.91 -> 2.03; coverage_p95: 5.57 -> 6.23; legibility_clusters: 1 -> 2; raw_score: -80 -> -74; satin_gaps_judged: 16 -> 17; satin_gaps_tight_shapes: 3 -> 2; satin_gaps_tight_worst_frac: 0.649 -> 0.522; satin_shapes: 31 -> 37; satin_short_fraction: 0.133 -> 0.118; stitch_count: 8119 -> 8562; thread_worst_delta_e: 14.9 -> 13.0; trims_per_1000: 5.2 -> 5.7; uncovered_hole_mm2: 0.0 -> 1.2; uncovered_holes: 0 -> 1; uncovered_patches: 19 -> 15; uncovered_total_mm2: 0.0 -> 1.2; uncovered_worst_mm2: 0.6 -> 1.2

photo/logo_golden_tee.jpg @ 80mm/left_chest
  @ 396a7458 #516: coverage_max: 8.11 -> 8.77; coverage_p50: 1.48 -> 1.59; coverage_p95: 3.88 -> 4.24; link_segments: 3 -> 12; link_thread_mm: 1.1 -> 20.6; same_hole_fraction: 0.06 -> 0.054; trims_per_1000: 8.6 -> 5.7
  @ 5d2db084 #520: color_changes: 12 -> 13; coverage_max: 8.77 -> 6.59; coverage_p50: 1.59 -> 1.67; coverage_p95: 4.24 -> 3.67; link_segments: 12 -> 3; link_thread_mm: 20.6 -> 1.6; trims_per_1000: 5.7 -> 5.3; uncovered_worst_mm2: 0.0 -> 0.8
  @ 8a48c3b4 #554: coverage_max: 6.45 -> 12.84; coverage_p50: 1.63 -> 1.86; coverage_p95: 3.43 -> 6.02; link_segments: 3 -> 0; link_thread_mm: 1.6 -> 0.0; same_hole_fraction: 0.055 -> 0.085; satin_shapes: 29 -> 31; satin_short_fraction: 0.307 -> 0.387; satin_steps: 5130 -> 8067; stitch_count: 6770 -> 10525; uncovered_worst_mm2: 0.8 -> 0.2
  @ 254eb3a4 #557: trims_per_1000: 5.6 -> 5.2
  @ 89161704 #558: DENSITY_STACKED:warn x0 -> x1; coverage_over_warn_mm2: 0.0 -> 27.0; raw_score: -80 -> -92; uncovered_worst_mm2: 0.2 -> 0.0
  @ 08c46a54 #561: DENSITY_STACKED:warn x1 -> x0; coverage_max: 12.22 -> 7.99; coverage_over_warn_mm2: 27.0 -> 0.0; coverage_p95: 6.25 -> 4.32; raw_score: -92 -> -80; same_hole_fraction: 0.085 -> 0.06; satin_short_fraction: 0.382 -> 0.347; satin_steps: 8255 -> 5806; stitch_count: 10762 -> 7952; uncovered_worst_mm2: 0.0 -> 0.5
  @ 7cc7df4d #559: coverage_max: 7.99 -> 9.24; coverage_p95: 4.32 -> 4.65; satin_steps: 5806 -> 6327; stitch_count: 7952 -> 8496; trims_per_1000: 5.3 -> 4.9; uncovered_worst_mm2: 0.5 -> 0.2
  @ ce8bdb89 #565: STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 9.24 -> 10.34; coverage_p95: 4.65 -> 5.15; raw_score: -80 -> -68; same_hole_fraction: 0.062 -> 0.066; satin_short_fraction: 0.336 -> 0.238
  @ d59ff556 #573: SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: -68 -> -80
  @ 41de6430 #572: uncovered_wanted_mm2: 382.0 -> 875.9; uncovered_worst_mm2: 0.2 -> 0.7
  @ e851e5aa #589: THREAD_MATCH_POOR:block x2 -> x1; THREAD_MATCH_POOR:warn x6 -> x7; coverage_p50: 1.9 -> 2.0; coverage_p95: 5.15 -> 5.53; legibility_clusters: 1 -> 2; link_segments: 0 -> 1; link_thread_mm: 0.0 -> 0.4; raw_score: -80 -> -62; satin_gaps_judged: 16 -> 17; satin_gaps_tight_shapes: 3 -> 2; satin_gaps_tight_worst_frac: 0.572 -> 0.475; satin_shapes: 31 -> 37; thread_worst_delta_e: 14.9 -> 13.0; trims_per_1000: 4.9 -> 5.7; uncovered_patches: 17 -> 11; uncovered_worst_mm2: 0.7 -> 2.3
  @ 5337e2f6 #608: uncovered_patches: 11 -> 10

photo/logo_hotel_fremont.webp @ 80mm/hat_front
  @ 396a7458 #516: trims_per_1000: 4.1 -> 2.8
  @ 8a48c3b4 #554: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 6.9 -> 8.04; coverage_p50: 2.71 -> 2.92; legibility: 0.587 -> 0.501; legibility_worst: 0.296 -> 0.148; link_segments: 4 -> 5; link_thread_mm: 1.6 -> 1.9; raw_score: 64 -> 76; same_hole_fraction: 0.12 -> 0.105; satin_shapes: 18 -> 19; satin_short_fraction: 0.991 -> 0.071; satin_steps: 2289 -> 2473; trims_per_1000: 2.6 -> 3.0
  @ 08c46a54 #561: link_segments: 5 -> 4; link_thread_mm: 1.9 -> 1.5
  @ 41de6430 #572: uncovered_wanted_mm2: 1492.8 -> 2146.1; uncovered_worst_mm2: 0.0 -> 0.2
  @ e851e5aa #589: score 76 -> 88; LETTERING_ILLEGIBLE:warn x1 -> x0; legibility: 0.501 -> 0.726; legibility_worst: 0.148 -> 0.533; raw_score: 76 -> 88; satin_short_fraction: 0.067 -> 0.061; uncovered_patches: 5 -> 2
  gradual drift across (c5a99a2a, 48b03066]

photo/logo_hotel_fremont.webp @ 80mm/left_chest
  @ 396a7458 #516: link_segments: 6 -> 5; link_thread_mm: 2.3 -> 2.0; trims_per_1000: 4.1 -> 2.8
  @ 24fce102 #523: link_segments: 5 -> 9; link_thread_mm: 2.0 -> 8.1; link_uncovered_max_mm: 0.0 -> 0.1; link_uncovered_mm: 0.0 -> 0.1
  @ 8a48c3b4 #554: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_p50: 2.79 -> 2.99; link_segments: 9 -> 5; link_thread_mm: 8.1 -> 1.9; link_uncovered_max_mm: 0.1 -> 0.0; link_uncovered_mm: 0.1 -> 0.0; raw_score: 64 -> 76; same_hole_fraction: 0.112 -> 0.106; satin_shapes: 18 -> 19; satin_short_fraction: 0.992 -> 0.098; satin_steps: 2293 -> 2457; trims_per_1000: 2.7 -> 2.9
  @ 08c46a54 #561: link_segments: 5 -> 4; link_thread_mm: 1.9 -> 1.5
  @ 7cc7df4d #559: coverage_max: 6.65 -> 7.05; satin_short_fraction: 0.094 -> 0.103
  @ 41de6430 #572: uncovered_wanted_mm2: 1473.5 -> 2138.6; uncovered_worst_mm2: 0.0 -> 0.1
  @ e851e5aa #589: trims_per_1000: 3.0 -> 2.5; uncovered_patches: 1 -> 3

photo/photo_chrome_specular.png @ 80mm/hat_front
  @ 396a7458 #516: satin_short_fraction: 0.236 -> 0.197; satin_steps: 199 -> 178
  @ bff6b37a #521: coverage_max: 9.26 -> 7.41; same_hole_fraction: 0.049 -> 0.044; trims_per_1000: 2.0 -> 2.6
  @ 5d2db084 #520: satin_short_fraction: 0.197 -> 0.23; satin_steps: 178 -> 191
  @ 8a48c3b4 #554: score 88 -> 76; STITCHES_TOO_SHORT:warn x0 -> x1; coverage_max: 7.35 -> 8.03; raw_score: 88 -> 76; satin_advance_mm: 0.414 -> 0.44; satin_short_fraction: 0.23 -> 0.336; satin_steps: 191 -> 307; uncovered_worst_mm2: 0.0 -> 0.2
  @ 89161704 #558: satin_steps: 303 -> 327
  @ 08c46a54 #561: score 76 -> 64; grade B -> C; LETTERING_TOO_SMALL:warn x0 -> x1; coverage_max: 7.94 -> 7.35; raw_score: 76 -> 64; satin_short_fraction: 0.312 -> 0.369; satin_steps: 327 -> 263; uncovered_worst_mm2: 0.2 -> 0.8
  @ 7cc7df4d #559: satin_short_fraction: 0.369 -> 0.316; satin_steps: 263 -> 304; uncovered_worst_mm2: 0.8 -> 0.2
  @ ce8bdb89 #565: satin_short_fraction: 0.316 -> 0.268
  @ 1c3d067a #578: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; raw_score: 64 -> 76; satin_short_fraction: 0.268 -> 0.232; satin_steps: 306 -> 354
  @ 41de6430 #572: score 76 -> 64; grade B -> C; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 76 -> 64; uncovered_total_mm2: 0.0 -> 2.1; uncovered_wanted_mm2: 6529.5 -> 7874.0; uncovered_worst_mm2: 0.2 -> 89.9

photo/photo_chrome_specular.png @ 80mm/left_chest
  @ 396a7458 #516: satin_short_fraction: 0.371 -> 0.39
  @ bff6b37a #521: coverage_max: 7.1 -> 6.6; same_hole_fraction: 0.046 -> 0.043; trims_per_1000: 2.5 -> 2.8
  @ 5d2db084 #520: satin_short_fraction: 0.39 -> 0.333; satin_steps: 205 -> 189
  @ 8a48c3b4 #554: coverage_max: 6.6 -> 7.22; satin_advance_mm: 0.421 -> 0.445; satin_short_fraction: 0.337 -> 0.487; satin_steps: 187 -> 298; uncovered_worst_mm2: 0.0 -> 1.2
  @ 08c46a54 #561: coverage_max: 7.36 -> 6.6; satin_short_fraction: 0.5 -> 0.466; satin_steps: 312 -> 296; uncovered_worst_mm2: 1.2 -> 0.0
  @ 7cc7df4d #559: coverage_max: 6.6 -> 7.07; satin_short_fraction: 0.466 -> 0.517; satin_steps: 296 -> 346
  @ ce8bdb89 #565: satin_short_fraction: 0.517 -> 0.477
  @ 1c3d067a #578: satin_short_fraction: 0.473 -> 0.409; satin_steps: 351 -> 406
  @ 41de6430 #572: score 64 -> 52; grade C -> D; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 64 -> 52; uncovered_total_mm2: 0.0 -> 2.3; uncovered_wanted_mm2: 6567.0 -> 7824.2; uncovered_worst_mm2: 0.0 -> 65.8

photo/photo_dof_meadow.png @ 80mm/hat_front
  @ 396a7458 #516: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; raw_score: 64 -> 76; satin_short_fraction: 0.256 -> 0.237
  @ bff6b37a #521: coverage_max: 10.2 -> 9.5; trims_per_1000: 3.1 -> 3.6
  @ 5d2db084 #520: satin_short_fraction: 0.237 -> 0.144
  @ 00cdf44c #537: satin_advance_mm: 0.478 -> 0.454; satin_short_fraction: 0.144 -> 0.156; satin_steps: 132 -> 122
  @ 8a48c3b4 #554: score 76 -> 64; grade B -> C; STITCHES_TOO_SHORT:warn x0 -> x1; coverage_max: 9.5 -> 13.72; raw_score: 76 -> 64; satin_short_fraction: 0.156 -> 0.255; satin_steps: 122 -> 353; trims_per_1000: 3.6 -> 3.8
  @ 89161704 #558: satin_steps: 353 -> 383
  @ 08c46a54 #561: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 13.67 -> 9.5; raw_score: 64 -> 76; satin_short_fraction: 0.258 -> 0.216; satin_steps: 383 -> 153
  @ 7cc7df4d #559: satin_short_fraction: 0.216 -> 0.177; satin_steps: 153 -> 192
  @ ce8bdb89 #565: satin_short_fraction: 0.177 -> 0.199; satin_steps: 192 -> 206
  @ 1c3d067a #578: satin_short_fraction: 0.199 -> 0.155; satin_steps: 206 -> 264
  @ 41de6430 #572: score 76 -> 64; grade B -> C; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 76 -> 64; uncovered_total_mm2: 0.0 -> 9.4; uncovered_wanted_mm2: 3796.8 -> 4473.7; uncovered_worst_mm2: 0.2 -> 43.6

photo/photo_dof_meadow.png @ 80mm/left_chest
  @ 396a7458 #516: satin_short_fraction: 0.405 -> 0.372; satin_steps: 121 -> 113
  @ bff6b37a #521: trims_per_1000: 2.8 -> 3.2
  @ 5d2db084 #520: satin_short_fraction: 0.372 -> 0.299; satin_steps: 113 -> 134
  @ 8a48c3b4 #554: coverage_max: 7.68 -> 10.55; satin_short_fraction: 0.299 -> 0.349; satin_steps: 134 -> 307
  @ 89161704 #558: satin_short_fraction: 0.349 -> 0.319
  @ 08c46a54 #561: score 64 -> 76; grade C -> B; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 10.28 -> 7.68; raw_score: 64 -> 76; satin_short_fraction: 0.319 -> 0.167; satin_steps: 317 -> 168
  @ 7cc7df4d #559: satin_short_fraction: 0.167 -> 0.2; satin_steps: 168 -> 190
  @ ce8bdb89 #565: satin_short_fraction: 0.2 -> 0.176
  @ 722f5a9b #567: satin_short_fraction: 0.176 -> 0.167; satin_steps: 193 -> 203
  @ 41de6430 #572: score 76 -> 64; grade B -> C; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 76 -> 64; uncovered_total_mm2: 0.0 -> 18.4; uncovered_wanted_mm2: 3790.5 -> 4452.2; uncovered_worst_mm2: 0.0 -> 44.9

photo/photo_grass_macro.png @ 80mm/hat_front
  @ 396a7458 #516: score 22 -> 10; TRIM_HEAVY:warn x0 -> x1; raw_score: 22 -> 10; same_hole_fraction: 0.02 -> 0.021
  @ 5d2db084 #520: score 10 -> 22; TRIM_HEAVY:warn x1 -> x0; coverage_max: 3.61 -> 4.23; raw_score: 10 -> 22; satin_short_fraction: 0.692 -> 0.561; satin_steps: 107 -> 98; trims_per_1000: 4.3 -> 3.8
  @ 8a48c3b4 #554: score 22 -> 46; grade F -> D; LETTERING_TOO_SMALL:warn x1 -> x0; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 4.23 -> 3.73; raw_score: 22 -> 46; same_hole_fraction: 0.02 -> 0.021; satin_short_fraction: 0.552 -> 0.137; satin_steps: 96 -> 102
  @ 89161704 #558: satin_advance_mm: 0.45 -> 0.473; satin_short_fraction: 0.137 -> 0.118; satin_steps: 102 -> 110
  @ 08c46a54 #561: satin_short_fraction: 0.118 -> 0.165
  @ 7cc7df4d #559: satin_short_fraction: 0.165 -> 0.124; satin_steps: 115 -> 137
  @ 41de6430 #572: uncovered_total_mm2: 460.2 -> 920.1; uncovered_wanted_mm2: 4633.2 -> 4965.4; uncovered_worst_mm2: 26.5 -> 135.3

photo/photo_grass_macro.png @ 80mm/left_chest
  @ 5d2db084 #520: satin_short_fraction: 0.681 -> 0.612; trims_per_1000: 4.8 -> 4.5
  @ 8a48c3b4 #554: score 10 -> 22; LETTERING_TOO_SMALL:warn x1 -> x0; raw_score: 10 -> 22; satin_advance_mm: 0.43 -> 0.455; satin_short_fraction: 0.604 -> 0.308; satin_steps: 96 -> 104
  @ 89161704 #558: satin_short_fraction: 0.308 -> 0.273; satin_steps: 104 -> 110
  @ 08c46a54 #561: satin_advance_mm: 0.467 -> 0.431; satin_short_fraction: 0.273 -> 0.31; satin_steps: 110 -> 116
  @ 7cc7df4d #559: score 22 -> 34; STITCHES_TOO_SHORT:warn x1 -> x0; raw_score: 22 -> 34; satin_short_fraction: 0.31 -> 0.217; satin_steps: 116 -> 138
  @ 41de6430 #572: uncovered_total_mm2: 407.8 -> 967.0; uncovered_wanted_mm2: 4592.2 -> 4945.2; uncovered_worst_mm2: 28.8 -> 111.4

photo/photo_owl_pale.png @ 80mm/hat_front
  @ 396a7458 #516: STABILIZER_CUTAWAY:info x1 -> x0; satin_short_fraction: 0.019 -> 0.022
  @ 00cdf44c #537: score 46 -> 58; DENSITY_EXTREME:warn x1 -> x0; raw_score: 46 -> 58; same_hole_fraction: 0.026 -> 0.024; satin_advance_mm: 0.625 -> 0.583; satin_short_fraction: 0.022 -> 0.041; satin_steps: 408 -> 222
  @ 8a48c3b4 #554: STABILIZER_CUTAWAY:info x0 -> x1; coverage_max: 6.34 -> 11.27; same_hole_fraction: 0.024 -> 0.029; satin_advance_mm: 0.583 -> 0.479; satin_short_fraction: 0.041 -> 0.223; satin_steps: 222 -> 883; trims_per_1000: 0.4 -> 0.6
  @ 254eb3a4 #557: trims_per_1000: 0.6 -> 0.5
  @ 89161704 #558: satin_steps: 875 -> 963
  @ 08c46a54 #561: STABILIZER_CUTAWAY:info x1 -> x0; coverage_max: 11.58 -> 7.29; same_hole_fraction: 0.029 -> 0.026; satin_advance_mm: 0.486 -> 0.439; satin_short_fraction: 0.212 -> 0.124; satin_steps: 963 -> 380; trims_per_1000: 0.5 -> 0.6; uncovered_worst_mm2: 0.0 -> 0.2
  @ 7cc7df4d #559: STABILIZER_CUTAWAY:info x0 -> x1; satin_short_fraction: 0.124 -> 0.102; satin_steps: 380 -> 492; trims_per_1000: 0.6 -> 0.5
  @ ce8bdb89 #565: trims_per_1000: 0.5 -> 0.6; uncovered_worst_mm2: 0.2 -> 0.0
  @ 41de6430 #572: uncovered_wanted_mm2: 8088.2 -> 8519.9; uncovered_worst_mm2: 0.0 -> 139.2

photo/photo_owl_pale.png @ 80mm/left_chest
  @ 00cdf44c #537: score 46 -> 58; DENSITY_EXTREME:warn x1 -> x0; raw_score: 46 -> 58; satin_advance_mm: 0.627 -> 0.579; satin_short_fraction: 0.023 -> 0.041; satin_steps: 398 -> 218
  @ 8a48c3b4 #554: score 58 -> 46; STITCHES_TOO_SHORT:warn x0 -> x1; coverage_max: 6.33 -> 8.09; raw_score: 58 -> 46; same_hole_fraction: 0.024 -> 0.026; satin_advance_mm: 0.579 -> 0.458; satin_short_fraction: 0.041 -> 0.296; satin_steps: 218 -> 801; trims_per_1000: 0.5 -> 0.6
  @ 89161704 #558: coverage_max: 8.09 -> 8.8; satin_steps: 801 -> 877; trims_per_1000: 0.6 -> 0.7
  @ 08c46a54 #561: score 46 -> 58; STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 8.8 -> 6.63; raw_score: 46 -> 58; same_hole_fraction: 0.027 -> 0.025; satin_advance_mm: 0.465 -> 0.438; satin_short_fraction: 0.298 -> 0.133; satin_steps: 877 -> 376; trims_per_1000: 0.7 -> 0.5
  @ 7cc7df4d #559: satin_short_fraction: 0.133 -> 0.152; satin_steps: 376 -> 488
  @ 41de6430 #572: uncovered_worst_mm2: 0.0 -> 112.4

photo/photo_scene_stub.png @ 80mm/hat_front
  @ 396a7458 #516: satin_short_fraction: 0.127 -> 0.103; trims_per_1000: 5.6 -> 4.8
  @ bff6b37a #521: same_hole_fraction: 0.056 -> 0.052
  @ 5d2db084 #520: coverage_max: 7.63 -> 9.65; same_hole_fraction: 0.052 -> 0.055; satin_short_fraction: 0.103 -> 0.121; satin_steps: 3696 -> 4231; trims_per_1000: 4.7 -> 5.0; uncovered_worst_mm2: 4.5 -> 1.0
  @ 00cdf44c #537: coverage_max: 9.65 -> 8.25; satin_steps: 4251 -> 3854
  @ 8a48c3b4 #554: coverage_max: 8.25 -> 18.86; coverage_p95: 4.98 -> 5.34; same_hole_fraction: 0.055 -> 0.067; satin_short_fraction: 0.129 -> 0.193; satin_steps: 3854 -> 5444; stitch_count: 22208 -> 24603; trims_per_1000: 5.1 -> 5.6; uncovered_worst_mm2: 1.0 -> 3.2
  @ 254eb3a4 #557: trims_per_1000: 5.6 -> 5.0
  @ 89161704 #558: satin_short_fraction: 0.185 -> 0.174; uncovered_worst_mm2: 3.2 -> 2.5
  @ 08c46a54 #561: coverage_max: 19.56 -> 8.74; coverage_p95: 5.41 -> 5.04; same_hole_fraction: 0.066 -> 0.058; satin_short_fraction: 0.174 -> 0.092; satin_steps: 5604 -> 3886; stitch_count: 24770 -> 22669; trims_per_1000: 5.0 -> 4.5; uncovered_worst_mm2: 2.5 -> 1.0
  @ 7cc7df4d #559: coverage_max: 8.74 -> 10.36; link_segments: 0 -> 7; link_thread_mm: 0.0 -> 11.6; satin_short_fraction: 0.092 -> 0.08; satin_steps: 3886 -> 4796; uncovered_worst_mm2: 1.0 -> 3.5
  @ ce8bdb89 #565: link_segments: 7 -> 0; link_thread_mm: 11.6 -> 0.0; satin_short_fraction: 0.08 -> 0.073
  @ 722f5a9b #567: coverage_max: 10.31 -> 11.0; satin_short_fraction: 0.073 -> 0.065; uncovered_worst_mm2: 3.5 -> 2.8
  @ d59ff556 #573: score 76 -> 64; grade B -> C; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 76 -> 64
  @ 6706a71e #577: coverage_max: 11.0 -> 10.31; uncovered_worst_mm2: 2.8 -> 3.5
  @ 1c3d067a #578: link_segments: 0 -> 7; link_thread_mm: 0.0 -> 11.6; satin_short_fraction: 0.065 -> 0.056; satin_steps: 4841 -> 5398
  @ e2c9f77e #579: link_segments: 7 -> 0; link_thread_mm: 11.6 -> 0.0
  @ 41de6430 #572: score 64 -> 52; grade C -> D; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 64 -> 52; uncovered_total_mm2: 0.0 -> 18.3; uncovered_wanted_mm2: 3524.5 -> 4388.8; uncovered_worst_mm2: 3.5 -> 99.7
  @ 5337e2f6 #608: satin_short_fraction: 0.058 -> 0.068; uncovered_patches: 19 -> 21

photo/photo_scene_stub.png @ 80mm/left_chest
  @ 396a7458 #516: coverage_max: 8.36 -> 9.09; satin_short_fraction: 0.118 -> 0.106; trims_per_1000: 5.0 -> 4.4
  @ bff6b37a #521: trims_per_1000: 4.4 -> 4.8
  @ 5d2db084 #520: score 64 -> 76; grade C -> B; ARTWORK_UNCOVERED:warn x1 -> x0; coverage_max: 9.09 -> 8.15; raw_score: 64 -> 76; same_hole_fraction: 0.052 -> 0.055; satin_short_fraction: 0.106 -> 0.13; satin_steps: 3805 -> 4160; trims_per_1000: 4.8 -> 5.3; uncovered_total_mm2: 6.0 -> 0.0; uncovered_worst_mm2: 6.0 -> 1.2
  @ 24fce102 #523: link_segments: 1 -> 6; link_thread_mm: 0.2 -> 6.3
  @ 00cdf44c #537: satin_steps: 4148 -> 3728
  @ 8a48c3b4 #554: coverage_max: 7.95 -> 15.61; coverage_p95: 4.66 -> 4.96; link_segments: 6 -> 1; link_thread_mm: 6.3 -> 0.2; same_hole_fraction: 0.055 -> 0.065; satin_short_fraction: 0.133 -> 0.216; satin_steps: 3728 -> 5214; stitch_count: 21700 -> 23893; trims_per_1000: 5.3 -> 5.0
  @ 254eb3a4 #557: trims_per_1000: 5.0 -> 4.6
  @ 89161704 #558: coverage_max: 15.76 -> 17.4; satin_short_fraction: 0.21 -> 0.197; uncovered_worst_mm2: 1.2 -> 1.0
  @ 08c46a54 #561: coverage_max: 17.4 -> 13.24; same_hole_fraction: 0.063 -> 0.059; satin_short_fraction: 0.197 -> 0.139; satin_steps: 5298 -> 4253; stitch_count: 24012 -> 22607
  @ 7cc7df4d #559: satin_short_fraction: 0.139 -> 0.146; satin_steps: 4253 -> 5216; trims_per_1000: 4.5 -> 4.8
  @ ce8bdb89 #565: coverage_max: 13.33 -> 14.24; satin_short_fraction: 0.146 -> 0.132
  @ 722f5a9b #567: satin_short_fraction: 0.132 -> 0.122; uncovered_worst_mm2: 1.0 -> 0.5
  @ d59ff556 #573: score 76 -> 64; grade B -> C; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 76 -> 64
  @ 6706a71e #577: uncovered_worst_mm2: 0.5 -> 1.0
  @ 1c3d067a #578: satin_short_fraction: 0.124 -> 0.116; satin_steps: 5237 -> 5631
  @ 41de6430 #572: score 64 -> 52; grade C -> D; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 64 -> 52; uncovered_total_mm2: 0.0 -> 20.1; uncovered_wanted_mm2: 3517.8 -> 4354.6; uncovered_worst_mm2: 1.0 -> 94.6

photo/photo_subject_stub.png @ 80mm/hat_front
  @ 41de6430 #572: score 58 -> 70; grade D -> C; ARTWORK_UNCOVERED:warn x1 -> x0; raw_score: 58 -> 70; uncovered_total_mm2: 956.2 -> 0.0; uncovered_wanted_mm2: 4094.2 -> 4428.0; uncovered_worst_mm2: 38.2 -> 142.1

photo/photo_subject_stub.png @ 80mm/left_chest
  @ 41de6430 #572: score 58 -> 70; grade D -> C; ARTWORK_UNCOVERED:warn x1 -> x0; raw_score: 58 -> 70; uncovered_total_mm2: 956.0 -> 0.0; uncovered_wanted_mm2: 4094.2 -> 4394.1; uncovered_worst_mm2: 38.2 -> 138.1

photo/photo_sunset_backlit.png @ 80mm/hat_front
  @ 396a7458 #516: satin_short_fraction: 0.571 -> 0.653; satin_steps: 42 -> 49
  @ bff6b37a #521: trims_per_1000: 3.2 -> 3.5
  @ 5d2db084 #520: satin_advance_mm: 0.389 -> 0.344; satin_short_fraction: 0.653 -> 0.771
  @ 8a48c3b4 #554: score 76 -> 88; LETTERING_TOO_SMALL:warn x1 -> x0; raw_score: 76 -> 88; satin_advance_mm: 0.344 -> 0.481; satin_short_fraction: 0.771 -> 0.316; satin_steps: 48 -> 38
  @ 89161704 #558: satin_short_fraction: 0.316 -> 0.3; satin_steps: 38 -> 40
  @ 08c46a54 #561: score 88 -> 100; grade B -> A; STITCHES_TOO_SHORT:warn x1 -> x0; raw_score: 88 -> 100; satin_short_fraction: 0.3 -> 0.345; satin_steps: 40 -> 29
  @ 7cc7df4d #559: score 100 -> 88; grade A -> B; STITCHES_TOO_SHORT:warn x0 -> x1; raw_score: 100 -> 88; satin_short_fraction: 0.345 -> 0.256; satin_steps: 29 -> 39
  @ 41de6430 #572: score 88 -> 76; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 88 -> 76; uncovered_total_mm2: 0.0 -> 24.6; uncovered_wanted_mm2: 4326.8 -> 5024.2; uncovered_worst_mm2: 0.2 -> 23.5

photo/photo_sunset_backlit.png @ 80mm/left_chest
  @ 396a7458 #516: satin_advance_mm: 0.371 -> 0.338; satin_short_fraction: 0.582 -> 0.673; satin_steps: 55 -> 52
  @ bff6b37a #521: coverage_max: 8.34 -> 7.87; trims_per_1000: 2.6 -> 2.9
  @ 5d2db084 #520: satin_advance_mm: 0.338 -> 0.421; satin_short_fraction: 0.673 -> 0.739; satin_steps: 52 -> 46
  @ 8a48c3b4 #554: score 76 -> 88; LETTERING_TOO_SMALL:warn x1 -> x0; raw_score: 76 -> 88; satin_short_fraction: 0.727 -> 0.326
  @ 7cc7df4d #559: score 88 -> 100; grade B -> A; STITCHES_TOO_SHORT:warn x1 -> x0; raw_score: 88 -> 100; satin_short_fraction: 0.311 -> 0.236; satin_steps: 45 -> 55
  @ 41de6430 #572: score 100 -> 88; grade A -> B; ARTWORK_UNCOVERED:warn x0 -> x1; raw_score: 100 -> 88; uncovered_total_mm2: 0.0 -> 25.0; uncovered_wanted_mm2: 4314.2 -> 5009.7; uncovered_worst_mm2: 0.2 -> 43.2

photo/region_blobs.png @ 80mm/hat_front
  @ bff6b37a #521: trims_per_1000: 1.2 -> 1.4
  @ 41de6430 #572: uncovered_wanted_mm2: 3186.0 -> 3612.4
  @ e851e5aa #589: THREAD_MATCH_POOR:warn x7 -> x9; color_changes: 16 -> 15; coverage_max: 6.77 -> 6.42; raw_score: -86 -> -110; trims_per_1000: 1.4 -> 1.7
  @ 0c3b7725 #599: THREAD_MATCH_POOR:block x2 -> x1; THREAD_MATCH_POOR:warn x9 -> x3; color_changes: 15 -> 11; coverage_p95: 4.48 -> 4.03; ground_area_frac: 0.506 -> 0.639; raw_score: -110 -> -8; same_hole_fraction: 0.035 -> 0.033; stitch_count: 18909 -> 16193; thread_worst_delta_e: 11.5 -> 12.2; tiny_step_fraction: 0.227 -> 0.185; tiny_steps: 4156 -> 2926; trims_per_1000: 1.7 -> 1.2

photo/region_blobs.png @ 80mm/left_chest
  @ bff6b37a #521: trims_per_1000: 1.3 -> 1.6
  @ 41de6430 #572: uncovered_wanted_mm2: 3186.5 -> 3614.1
  @ e851e5aa #589: THREAD_MATCH_POOR:warn x7 -> x9; color_changes: 16 -> 15; coverage_max: 6.61 -> 6.22; raw_score: -86 -> -110; trims_per_1000: 1.6 -> 1.7
  @ 0c3b7725 #599: THREAD_MATCH_POOR:block x2 -> x1; THREAD_MATCH_POOR:warn x9 -> x3; color_changes: 15 -> 11; coverage_p95: 4.25 -> 3.92; ground_area_frac: 0.506 -> 0.639; raw_score: -110 -> -8; stitch_count: 18895 -> 16058; thread_worst_delta_e: 11.5 -> 12.2; tiny_step_fraction: 0.227 -> 0.188; tiny_steps: 4153 -> 2941; trims_per_1000: 1.7 -> 1.3

photo/repro_gradient_white_icon.png @ 80mm/hat_front
  @ 396a7458 #516: uncovered_worst_mm2: 0.5 -> 0.2
  @ bff6b37a #521: trims_per_1000: 0.8 -> 0.9
  @ 5d2db084 #520: coverage_max: 5.43 -> 5.73; satin_short_fraction: 0.006 -> 0.008; uncovered_worst_mm2: 0.2 -> 0.0
  @ 00cdf44c #537: satin_short_fraction: 0.008 -> 0.01
  @ 8a48c3b4 #554: coverage_max: 5.73 -> 6.53; coverage_p95: 3.74 -> 3.54; same_hole_fraction: 0.025 -> 0.038; satin_short_fraction: 0.01 -> 0.008; trims_per_1000: 0.9 -> 1.3; uncovered_worst_mm2: 0.0 -> 0.8
  @ 89161704 #558: satin_short_fraction: 0.008 -> 0.009
  @ 08c46a54 #561: coverage_max: 6.82 -> 8.51; satin_short_fraction: 0.009 -> 0.008
  @ 7cc7df4d #559: uncovered_worst_mm2: 0.8 -> 0.0
  @ 722f5a9b #567: coverage_max: 8.51 -> 9.09
  @ d59ff556 #573: score 58 -> 46; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 58 -> 46
  @ 6706a71e #577: coverage_max: 9.09 -> 8.51
  @ 1c3d067a #578: satin_short_fraction: 0.008 -> 0.006; satin_steps: 2030 -> 2470
  @ 41de6430 #572: uncovered_wanted_mm2: 6012.5 -> 6539.0; uncovered_worst_mm2: 0.0 -> 80.9
  @ e851e5aa #589: score 46 -> 58; SATIN_GAPS_TIGHT:warn x1 -> x0; coverage_max: 8.51 -> 4.9; raw_score: 46 -> 58; same_hole_fraction: 0.038 -> 0.028; satin_gaps_tight_shapes: 1 -> 0; satin_short_fraction: 0.006 -> 0.004; satin_steps: 2470 -> 1888; stitch_count: 22744 -> 21407; trims_per_1000: 1.3 -> 1.0; uncovered_patches: 2 -> 6

photo/repro_gradient_white_icon.png @ 80mm/left_chest
  @ 396a7458 #516: uncovered_worst_mm2: 0.8 -> 0.2
  @ bff6b37a #521: trims_per_1000: 0.8 -> 0.9
  @ 5d2db084 #520: coverage_max: 4.83 -> 5.71; satin_short_fraction: 0.006 -> 0.011; uncovered_worst_mm2: 0.2 -> 0.0
  @ 8a48c3b4 #554: coverage_max: 5.7 -> 6.48; same_hole_fraction: 0.026 -> 0.037; satin_short_fraction: 0.011 -> 0.007; trims_per_1000: 0.9 -> 1.3; uncovered_worst_mm2: 0.0 -> 0.8
  @ 08c46a54 #561: coverage_max: 6.78 -> 7.6; satin_short_fraction: 0.007 -> 0.013
  @ 7cc7df4d #559: satin_short_fraction: 0.013 -> 0.012; uncovered_worst_mm2: 0.8 -> 0.0
  @ d59ff556 #573: score 58 -> 46; SATIN_GAPS_TIGHT:warn x0 -> x1; raw_score: 58 -> 46
  @ 1c3d067a #578: satin_short_fraction: 0.012 -> 0.011; satin_steps: 2091 -> 2326
  @ 41de6430 #572: uncovered_wanted_mm2: 6012.5 -> 6539.0; uncovered_worst_mm2: 0.0 -> 80.9
  @ e851e5aa #589: score 46 -> 58; SATIN_GAPS_TIGHT:warn x1 -> x0; coverage_max: 7.62 -> 6.94; coverage_p95: 3.56 -> 4.12; raw_score: 46 -> 58; same_hole_fraction: 0.037 -> 0.026; satin_gaps_tight_shapes: 1 -> 0; satin_short_fraction: 0.011 -> 0.004; satin_steps: 2326 -> 1888; trims_per_1000: 1.3 -> 1.0

photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front
  @ 396a7458 #516: legibility: 0.562 -> 0.113; link_segments: 1 -> 9; link_thread_mm: 0.5 -> 11.8; trims_per_1000: 9.3 -> 9.9
  @ bff6b37a #521: trims_per_1000: 9.9 -> 10.4
  @ 5d2db084 #520: legibility: 0.113 -> 0.492; link_segments: 9 -> 1; link_thread_mm: 11.8 -> 0.4; satin_short_fraction: 0.335 -> 0.317; trims_per_1000: 10.4 -> 9.5
  @ 24fce102 #523: legibility: 0.492 -> 0.139; link_thread_mm: 0.4 -> 0.2
  @ 00cdf44c #537: legibility: 0.139 -> 0.297; satin_short_fraction: 0.318 -> 0.292; satin_steps: 2601 -> 2386
  @ 8a48c3b4 #554: STITCHES_TOO_SHORT:warn x1 -> x0; coverage_max: 7.15 -> 5.77; coverage_p50: 1.95 -> 1.78; legibility: 0.297 -> 0.383; link_segments: 1 -> 4; link_thread_mm: 0.2 -> 1.5; raw_score: -44 -> -32; satin_short_fraction: 0.292 -> 0.238; satin_steps: 2386 -> 2257; stitch_count: 8528 -> 7877; trims_per_1000: 10.0 -> 9.4; uncovered_worst_mm2: 0.2 -> 0.5
  @ 89161704 #558: link_thread_mm: 1.5 -> 1.4
  @ 7cc7df4d #559: coverage_p50: 1.79 -> 1.88; link_segments: 4 -> 2; link_thread_mm: 1.4 -> 0.9; satin_short_fraction: 0.235 -> 0.223; satin_steps: 2272 -> 2437; trims_per_1000: 9.4 -> 8.8; uncovered_worst_mm2: 0.5 -> 0.2
  @ 41de6430 #572: uncovered_wanted_mm2: 389.8 -> 954.8; uncovered_worst_mm2: 0.2 -> 0.8
  @ e851e5aa #589: score 0 -> 22; THREAD_MATCH_POOR:block x2 -> x1; THREAD_MATCH_POOR:warn x2 -> x0; color_changes: 12 -> 11; coverage_max: 5.77 -> 6.58; coverage_p95: 3.63 -> 3.27; ground_area_frac: 0.46 -> 0.484; legibility: 0.397 -> 0.469; legibility_readable: 4 -> 3; link_segments: 2 -> 4; link_thread_mm: 0.9 -> 1.6; raw_score: -32 -> 22; thread_worst_delta_e: 44.4 -> 16.9; uncovered_patches: 39 -> 52; uncovered_worst_mm2: 0.8 -> 0.9

photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest
  @ 396a7458 #516: legibility: 0.5 -> 0.457
  @ 5d2db084 #520: legibility: 0.457 -> 0.5
  @ 24fce102 #523: link_segments: 1 -> 0; link_thread_mm: 0.3 -> 0.0
  @ 00cdf44c #537: legibility: 0.5 -> 0.373; satin_short_fraction: 0.395 -> 0.334; satin_steps: 2640 -> 2291
  @ 8a48c3b4 #554: coverage_max: 6.32 -> 5.5; legibility: 0.373 -> 0.287; link_segments: 0 -> 2; link_thread_mm: 0.0 -> 0.8; uncovered_worst_mm2: 0.5 -> 0.2
  @ 7cc7df4d #559: legibility: 0.287 -> 0.635; satin_steps: 2301 -> 2494; uncovered_worst_mm2: 0.2 -> 0.0
  @ 41de6430 #572: uncovered_wanted_mm2: 388.0 -> 951.3; uncovered_worst_mm2: 0.0 -> 0.7
  @ e851e5aa #589: score 0 -> 10; THREAD_MATCH_POOR:block x2 -> x1; THREAD_MATCH_POOR:warn x2 -> x0; color_changes: 12 -> 11; coverage_max: 5.5 -> 7.19; coverage_p95: 3.61 -> 3.39; ground_area_frac: 0.46 -> 0.484; legibility: 0.635 -> 0.55; legibility_readable: 4 -> 3; link_segments: 2 -> 3; link_thread_mm: 0.8 -> 1.1; raw_score: -44 -> 10; satin_short_fraction: 0.338 -> 0.357; thread_worst_delta_e: 44.4 -> 16.9; trims_per_1000: 8.8 -> 7.8; uncovered_worst_mm2: 0.7 -> 0.9

photo/summit_badge.png @ 80mm/hat_front
  @ 396a7458 #516: legibility: 0.33 -> 0.264; legibility_worst: 0.154 -> 0.0; link_thread_mm: 0.4 -> 0.5; trims_per_1000: 1.7 -> 1.6
  @ bff6b37a #521: trims_per_1000: 1.6 -> 2.0
  @ 5d2db084 #520: legibility: 0.264 -> 0.25; satin_steps: 680 -> 639; trims_per_1000: 2.0 -> 1.9; uncovered_worst_mm2: 0.0 -> 0.2
  @ 24fce102 #523: legibility: 0.25 -> 0.392; legibility_worst: 0.0 -> 0.222
  @ 00cdf44c #537: legibility: 0.392 -> 0.349; legibility_worst: 0.222 -> 0.133; satin_short_fraction: 0.374 -> 0.338; satin_steps: 639 -> 577
  @ 8a48c3b4 #554: legibility: 0.349 -> 0.111; legibility_worst: 0.133 -> 0.0; link_thread_mm: 0.5 -> 0.3; satin_advance_mm: 0.427 -> 0.462; satin_short_fraction: 0.338 -> 0.253; satin_steps: 577 -> 643; trims_per_1000: 1.9 -> 2.0; uncovered_worst_mm2: 0.2 -> 0.0
  @ 08c46a54 #561: legibility: 0.111 -> 0.239
  @ 7cc7df4d #559: STITCHES_TOO_SHORT:warn x1 -> x0; legibility: 0.239 -> 0.197; raw_score: -116 -> -104; satin_steps: 647 -> 695
  @ ce8bdb89 #565: legibility: 0.197 -> 0.147
  @ 41de6430 #572: uncovered_wanted_mm2: 4262.0 -> 4649.7; uncovered_worst_mm2: 0.0 -> 0.4
  @ e851e5aa #589: STABILIZER_CUTAWAY:info x0 -> x1; THREAD_MATCH_POOR:block x1 -> x2; THREAD_MATCH_POOR:warn x9 -> x8; color_changes: 11 -> 13; coverage_max: 6.43 -> 6.81; legibility: 0.147 -> 0.074; link_segments: 1 -> 0; link_thread_mm: 0.3 -> 0.0; raw_score: -104 -> -122; same_hole_fraction: 0.042 -> 0.039; stitch_count: 23175 -> 25611; thread_worst_delta_e: 12.5 -> 21.5; trims_per_1000: 2.0 -> 2.1; uncovered_patches: 18 -> 15
  @ de1d2c0a #614: legibility: 0.074 -> 0.037

photo/summit_badge.png @ 80mm/left_chest
  @ 396a7458 #516: legibility: 0.325 -> 0.382; legibility_worst: 0.143 -> 0.167; link_segments: 2 -> 1; link_thread_mm: 0.9 -> 0.3; trims_per_1000: 1.6 -> 1.7
  @ bff6b37a #521: coverage_max: 7.25 -> 6.58; legibility: 0.382 -> 0.358; trims_per_1000: 1.7 -> 2.1
  @ 5d2db084 #520: legibility: 0.358 -> 0.42; legibility_worst: 0.167 -> 0.267; satin_short_fraction: 0.403 -> 0.38
  @ 00cdf44c #537: legibility: 0.42 -> 0.31; legibility_worst: 0.267 -> 0.0; satin_short_fraction: 0.387 -> 0.353; satin_steps: 714 -> 660
  @ 8a48c3b4 #554: satin_short_fraction: 0.353 -> 0.304
  @ 89161704 #558: legibility: 0.317 -> 0.27
  @ 08c46a54 #561: legibility: 0.27 -> 0.327
  @ 7cc7df4d #559: legibility: 0.327 -> 0.344; legibility_worst: 0.0 -> 0.167; satin_steps: 638 -> 688
  @ 41de6430 #572: uncovered_wanted_mm2: 4252.0 -> 4639.5; uncovered_worst_mm2: 0.0 -> 0.4
  @ e851e5aa #589: STABILIZER_CUTAWAY:info x0 -> x1; THREAD_MATCH_POOR:block x1 -> x2; THREAD_MATCH_POOR:warn x9 -> x8; color_changes: 11 -> 13; legibility: 0.344 -> 0.205; legibility_worst: 0.167 -> 0.091; link_thread_mm: 0.3 -> 0.4; raw_score: -116 -> -134; same_hole_fraction: 0.042 -> 0.038; stitch_count: 23362 -> 25496; thread_worst_delta_e: 12.5 -> 21.5; trims_per_1000: 2.0 -> 1.9; uncovered_patches: 13 -> 11
  @ de1d2c0a #614: legibility: 0.205 -> 0.188; legibility_worst: 0.091 -> 0.0

ribbon_curve.png @ 80mm/hat_front
  @ 8a48c3b4 #554: satin_short_fraction: 0.011 -> 0.009
  @ 41de6430 #572: uncovered_wanted_mm2: 121.8 -> 236.1

ribbon_curve.png @ 80mm/left_chest
  @ 8a48c3b4 #554: satin_short_fraction: 0.017 -> 0.009
  @ 41de6430 #572: uncovered_wanted_mm2: 124.0 -> 235.5; uncovered_worst_mm2: 0.0 -> 0.1
```

## Per-row summary

| row | grade | score | findings appeared | findings resolved |
|---|---|---|---|---|
| `becker_marine_logo.png @ 80mm/hat_front` | B | 88 → 76 | `ARTWORK_UNCOVERED:warn` | — |
| `becker_marine_logo.png @ 80mm/left_chest` | B | 76 | — | — |
| `bg_uncertain.png @ 80mm/hat_front` | B | 88 | — | — |
| `bg_uncertain.png @ 80mm/left_chest` | B | 88 | — | — |
| `logo_alpha.png @ 80mm/hat_front` | A | 100 | — | — |
| `logo_alpha.png @ 80mm/left_chest` | A | 100 | — | — |
| `logo_script_tires.png @ 80mm/hat_front` | A → **B** | 100 → 88 | `SATIN_GAPS_TIGHT:warn` | — |
| `logo_script_tires.png @ 80mm/left_chest` | B | 88 | `SATIN_GAPS_TIGHT:warn` | `TRIM_HEAVY:warn` |
| `logo_whitebg.png @ 80mm/hat_front` | A | 100 | — | — |
| `logo_whitebg.png @ 80mm/left_chest` | A | 100 | — | — |
| `photo/drone_render.png @ 80mm/hat_front` | F | 0 | `LETTERING_ILLEGIBLE:warn`, `THREAD_MATCH_POOR:warn x4` | `THREAD_MATCH_POOR:block x2` |
| `photo/drone_render.png @ 80mm/left_chest` | F | 0 | `THREAD_MATCH_POOR:warn x4` | `THREAD_MATCH_POOR:block x2` |
| `photo/enthusiast_logo.png @ 80mm/hat_front` | B | 76 → 88 | — | `LETTERING_ILLEGIBLE:warn` |
| `photo/enthusiast_logo.png @ 80mm/left_chest` | B | 88 → 76 | `ARTWORK_UNCOVERED:warn` | — |
| `photo/fur_ramp.png @ 80mm/hat_front` | B | 88 | — | — |
| `photo/fur_ramp.png @ 80mm/left_chest` | B | 88 | — | — |
| `photo/gradient_ramp_linear.png @ 80mm/hat_front` | C | 64 | — | — |
| `photo/gradient_ramp_linear.png @ 80mm/left_chest` | C | 64 | — | — |
| `photo/gradient_ramp_radial.png @ 80mm/hat_front` | C | 64 | — | — |
| `photo/gradient_ramp_radial.png @ 80mm/left_chest` | C | 64 | — | — |
| `photo/logo_bridge_bar.jpg @ 80mm/hat_front` | F | 0 | `SATIN_GAPS_TIGHT:warn`, `THREAD_MATCH_POOR:warn x4` | `LETTERING_ILLEGIBLE:warn` |
| `photo/logo_bridge_bar.jpg @ 80mm/left_chest` | F | 0 | `SATIN_GAPS_TIGHT:warn`, `THREAD_MATCH_POOR:warn x4` | `LETTERING_ILLEGIBLE:warn` |
| `photo/logo_gaulke_roofing.png @ 80mm/hat_front` | F → **C** | 34 → 64 | `SATIN_GAPS_TIGHT:warn` | `GROUND_SEWN:block`, `STITCHES_TOO_SHORT:warn` |
| `photo/logo_gaulke_roofing.png @ 80mm/left_chest` | F → **C** | 34 → 64 | `SATIN_GAPS_TIGHT:warn` | `GROUND_SEWN:block`, `STITCHES_TOO_SHORT:warn` |
| `photo/logo_golden_tee.jpg @ 80mm/hat_front` | F | 0 | `ARTWORK_UNCOVERED:warn`, `SATIN_GAPS_TIGHT:warn`, `THREAD_MATCH_POOR:warn` | `STITCHES_TOO_SHORT:warn`, `THREAD_MATCH_POOR:block` |
| `photo/logo_golden_tee.jpg @ 80mm/left_chest` | F | 0 | `SATIN_GAPS_TIGHT:warn`, `THREAD_MATCH_POOR:warn` | `STITCHES_TOO_SHORT:warn`, `THREAD_MATCH_POOR:block` |
| `photo/logo_hotel_fremont.webp @ 80mm/hat_front` | C → **B** | 64 → 88 | — | `LETTERING_ILLEGIBLE:warn`, `STITCHES_TOO_SHORT:warn` |
| `photo/logo_hotel_fremont.webp @ 80mm/left_chest` | C → **B** | 64 → 76 | — | `STITCHES_TOO_SHORT:warn` |
| `photo/photo_chrome_specular.png @ 80mm/hat_front` | B → **C** | 88 → 64 | `ARTWORK_UNCOVERED:warn`, `LETTERING_TOO_SMALL:warn` | — |
| `photo/photo_chrome_specular.png @ 80mm/left_chest` | C → **D** | 64 → 52 | `ARTWORK_UNCOVERED:warn` | — |
| `photo/photo_dof_meadow.png @ 80mm/hat_front` | C | 64 | `ARTWORK_UNCOVERED:warn` | `STITCHES_TOO_SHORT:warn` |
| `photo/photo_dof_meadow.png @ 80mm/left_chest` | C | 64 | `ARTWORK_UNCOVERED:warn` | `STITCHES_TOO_SHORT:warn` |
| `photo/photo_grass_macro.png @ 80mm/hat_front` | F → **D** | 22 → 46 | — | `LETTERING_TOO_SMALL:warn`, `STITCHES_TOO_SHORT:warn` |
| `photo/photo_grass_macro.png @ 80mm/left_chest` | F | 10 → 34 | — | `LETTERING_TOO_SMALL:warn`, `STITCHES_TOO_SHORT:warn` |
| `photo/photo_owl_pale.png @ 80mm/hat_front` | D | 46 → 58 | — | `DENSITY_EXTREME:warn` |
| `photo/photo_owl_pale.png @ 80mm/left_chest` | D | 46 → 58 | — | `DENSITY_EXTREME:warn` |
| `photo/photo_scene_stub.png @ 80mm/hat_front` | B → **D** | 76 → 52 | `ARTWORK_UNCOVERED:warn`, `SATIN_GAPS_TIGHT:warn` | — |
| `photo/photo_scene_stub.png @ 80mm/left_chest` | C → **D** | 64 → 52 | `SATIN_GAPS_TIGHT:warn` | — |
| `photo/photo_subject_stub.png @ 80mm/hat_front` | D → **C** | 58 → 70 | — | `ARTWORK_UNCOVERED:warn` |
| `photo/photo_subject_stub.png @ 80mm/left_chest` | D → **C** | 58 → 70 | — | `ARTWORK_UNCOVERED:warn` |
| `photo/photo_sunset_backlit.png @ 80mm/hat_front` | B | 76 | `ARTWORK_UNCOVERED:warn` | `LETTERING_TOO_SMALL:warn` |
| `photo/photo_sunset_backlit.png @ 80mm/left_chest` | B | 76 → 88 | `ARTWORK_UNCOVERED:warn` | `LETTERING_TOO_SMALL:warn`, `STITCHES_TOO_SHORT:warn` |
| `photo/region_blobs.png @ 80mm/hat_front` | F | 0 | — | `THREAD_MATCH_POOR:block`, `THREAD_MATCH_POOR:warn x4` |
| `photo/region_blobs.png @ 80mm/left_chest` | F | 0 | — | `THREAD_MATCH_POOR:block`, `THREAD_MATCH_POOR:warn x4` |
| `photo/repro_gradient_white_icon.png @ 80mm/hat_front` | D | 58 | — | — |
| `photo/repro_gradient_white_icon.png @ 80mm/left_chest` | D | 58 | — | — |
| `photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front` | F | 0 → 22 | — | `STITCHES_TOO_SHORT:warn`, `THREAD_MATCH_POOR:block`, `THREAD_MATCH_POOR:warn x2` |
| `photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest` | F | 0 → 10 | — | `THREAD_MATCH_POOR:block`, `THREAD_MATCH_POOR:warn x2` |
| `photo/summit_badge.png @ 80mm/hat_front` | F | 0 | `STABILIZER_CUTAWAY:info`, `THREAD_MATCH_POOR:block` | `STITCHES_TOO_SHORT:warn`, `THREAD_MATCH_POOR:warn` |
| `photo/summit_badge.png @ 80mm/left_chest` | F | 0 | `STABILIZER_CUTAWAY:info`, `THREAD_MATCH_POOR:block` | `THREAD_MATCH_POOR:warn` |
| `ribbon_curve.png @ 80mm/hat_front` | A | 100 | — | — |
| `ribbon_curve.png @ 80mm/left_chest` | A | 100 | — | — |

## Appendix A — the tool's own `diff` output at `6e0cb943` (identical at `aa7f934`)

```
logo_alpha.png @ 80mm/left_chest:
    satin_short_fraction: 0.05 -> 0.034
    uncovered_wanted_mm2: 1141.8 -> 1280.2
    uncovered_worst_mm2: 0.0 -> 0.1
logo_alpha.png @ 80mm/hat_front:
    trims_per_1000: 1.6 -> 1.8
    uncovered_wanted_mm2: 1147.5 -> 1292.2
    uncovered_worst_mm2: 0.0 -> 0.1
logo_whitebg.png @ 80mm/left_chest:
    satin_short_fraction: 0.05 -> 0.034
    uncovered_wanted_mm2: 1139.0 -> 1277.0
    uncovered_worst_mm2: 0.0 -> 0.1
logo_whitebg.png @ 80mm/hat_front:
    trims_per_1000: 1.6 -> 1.8
    uncovered_wanted_mm2: 1140.8 -> 1280.3
    uncovered_worst_mm2: 0.0 -> 0.2
ribbon_curve.png @ 80mm/left_chest:
    satin_short_fraction: 0.017 -> 0.009
    uncovered_wanted_mm2: 124.5 -> 235.5
    uncovered_worst_mm2: 0.0 -> 0.1
ribbon_curve.png @ 80mm/hat_front:
    satin_short_fraction: 0.011 -> 0.009
    uncovered_wanted_mm2: 123.5 -> 236.1
photo/drone_render.png @ 80mm/left_chest:
  score: 0 unchanged, raw -122 -> -110 (better)
  finding count changed: THREAD_MATCH_POOR:block: x5 -> x3
  finding count changed: THREAD_MATCH_POOR:warn: x2 -> x6
    color_changes: 14 -> 16
    coverage_max: 10.7 -> 8.31
    ground_span_frac: 0.478 -> 0.571
    legibility: 0.333 -> 0.2
    legibility_worst: 0.333 -> 0.2
    link_segments: 2 -> 1
    link_thread_mm: 0.4 -> 0.2
    raw_score: -122 -> -110
    satin_shapes: 58 -> 61
    satin_short_fraction: 0.246 -> 0.221
    satin_steps: 4229 -> 4505
    thread_worst_delta_e: 18.1 -> 19.8
    uncovered_wanted_mm2: 1946.2 -> 3050.6
    uncovered_worst_mm2: 0.2 -> 0.5
photo/drone_render.png @ 80mm/hat_front:
  findings APPEARED: ['LETTERING_ILLEGIBLE:warn']
  finding count changed: THREAD_MATCH_POOR:block: x5 -> x3
  finding count changed: THREAD_MATCH_POOR:warn: x2 -> x6
    color_changes: 14 -> 16
    coverage_max: 7.27 -> 9.52
    ground_span_frac: 0.478 -> 0.571
    legibility: 0.545 -> 0.167
    legibility_worst: 0.545 -> 0.167
    same_hole_fraction: 0.066 -> 0.071
    satin_shapes: 58 -> 61
    satin_short_fraction: 0.234 -> 0.138
    satin_steps: 3898 -> 4451
    thread_worst_delta_e: 18.1 -> 19.8
    uncovered_wanted_mm2: 1979.5 -> 3029.9
    uncovered_worst_mm2: 2.8 -> 0.4
photo/enthusiast_logo.png @ 80mm/left_chest:
  score: 88 -> 76 (worse; raw 88 -> 76)
  findings APPEARED: ['ARTWORK_UNCOVERED:warn']
    coverage_max: 4.01 -> 4.84
    coverage_p50: 1.17 -> 1.26
    coverage_p95: 3.07 -> 3.33
    link_segments: 1 -> 0
    link_thread_mm: 0.4 -> 0.0
    raw_score: 88 -> 76
    same_hole_fraction: 0.122 -> 0.106
    satin_short_fraction: 0.115 -> 0.051
    satin_steps: 1262 -> 1123
    trims_per_1000: 9.6 -> 5.6
    uncovered_total_mm2: 0.0 -> 1.0
    uncovered_wanted_mm2: 158.5 -> 381.9
    uncovered_worst_mm2: 1.5 -> 1.0
photo/enthusiast_logo.png @ 80mm/hat_front:
  score: 76 -> 88 (better; raw 76 -> 88)
  findings resolved: ['LETTERING_ILLEGIBLE:warn']
    coverage_max: 6.37 -> 4.42
    coverage_p95: 3.53 -> 3.35
    legibility: 0.542 -> 1.0
    legibility_worst: 0.286 -> 1.0
    link_segments: 1 -> 0
    link_thread_mm: 0.4 -> 0.0
    raw_score: 76 -> 88
    same_hole_fraction: 0.134 -> 0.106
    satin_short_fraction: 0.107 -> 0.049
    satin_steps: 1341 -> 1108
    stitch_count: 3267 -> 2629
    trims_per_1000: 9.2 -> 5.3
    uncovered_wanted_mm2: 156.2 -> 377.6
photo/fur_ramp.png @ 80mm/left_chest:
    uncovered_wanted_mm2: 1094.8 -> 1285.6
photo/fur_ramp.png @ 80mm/hat_front:
    uncovered_wanted_mm2: 1097.5 -> 1284.9
photo/gradient_ramp_radial.png @ 80mm/left_chest:
    color_changes: 5 -> 6
    trims_per_1000: 0.3 -> 0.6
photo/gradient_ramp_radial.png @ 80mm/hat_front:
    color_changes: 5 -> 6
    coverage_max: 4.17 -> 4.62
    trims_per_1000: 0.3 -> 0.7
photo/photo_chrome_specular.png @ 80mm/left_chest:
  score: 64 -> 52 (worse; raw 64 -> 52)
  grade: C -> D (FELL A BAND)
  findings APPEARED: ['ARTWORK_UNCOVERED:warn']
    raw_score: 64 -> 52
    same_hole_fraction: 0.046 -> 0.043
    satin_advance_mm: 0.402 -> 0.445
    satin_short_fraction: 0.371 -> 0.413
    satin_steps: 202 -> 402
    trims_per_1000: 2.5 -> 2.8
    uncovered_total_mm2: 0.0 -> 2.3
    uncovered_wanted_mm2: 6567.0 -> 7824.2
    uncovered_worst_mm2: 0.0 -> 65.8
photo/photo_chrome_specular.png @ 80mm/hat_front:
  score: 88 -> 64 (worse; raw 88 -> 64)
  grade: B -> C (FELL A BAND)
  findings APPEARED: ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn']
    coverage_max: 9.26 -> 7.42
    raw_score: 88 -> 64
    same_hole_fraction: 0.049 -> 0.044
    satin_advance_mm: 0.409 -> 0.451
    satin_steps: 199 -> 354
    trims_per_1000: 2.0 -> 2.6
    uncovered_total_mm2: 0.0 -> 2.1
    uncovered_wanted_mm2: 6529.5 -> 7874.0
    uncovered_worst_mm2: 0.0 -> 89.9
photo/photo_dof_meadow.png @ 80mm/left_chest:
  findings APPEARED: ['ARTWORK_UNCOVERED:warn']
  findings resolved: ['STITCHES_TOO_SHORT:warn']
    satin_advance_mm: 0.412 -> 0.446
    satin_short_fraction: 0.405 -> 0.162
    satin_steps: 121 -> 210
    trims_per_1000: 2.8 -> 3.3
    uncovered_total_mm2: 0.0 -> 18.4
    uncovered_wanted_mm2: 3790.5 -> 4452.2
    uncovered_worst_mm2: 0.0 -> 44.9
photo/photo_dof_meadow.png @ 80mm/hat_front:
  findings APPEARED: ['ARTWORK_UNCOVERED:warn']
  findings resolved: ['STITCHES_TOO_SHORT:warn']
    coverage_max: 10.2 -> 9.5
    satin_short_fraction: 0.256 -> 0.153
    satin_steps: 129 -> 262
    trims_per_1000: 3.1 -> 3.9
    uncovered_total_mm2: 0.0 -> 9.4
    uncovered_wanted_mm2: 3796.8 -> 4473.7
    uncovered_worst_mm2: 0.2 -> 43.6
photo/photo_grass_macro.png @ 80mm/left_chest:
  score: 10 -> 34 (better; raw 10 -> 34)
  findings resolved: ['LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn']
    raw_score: 10 -> 34
    satin_short_fraction: 0.688 -> 0.214
    satin_steps: 96 -> 140
    trims_per_1000: 4.8 -> 4.5
    uncovered_total_mm2: 407.8 -> 967.0
    uncovered_wanted_mm2: 4592.2 -> 4945.2
    uncovered_worst_mm2: 28.8 -> 111.4
photo/photo_grass_macro.png @ 80mm/hat_front:
  score: 22 -> 46 (better; raw 22 -> 46)
  grade: F -> D
  findings resolved: ['LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn']
    raw_score: 22 -> 46
    satin_short_fraction: 0.67 -> 0.124
    satin_steps: 103 -> 137
    trims_per_1000: 4.1 -> 3.8
    uncovered_total_mm2: 460.2 -> 920.1
    uncovered_wanted_mm2: 4633.2 -> 4965.4
    uncovered_worst_mm2: 26.5 -> 135.3
photo/photo_owl_pale.png @ 80mm/left_chest:
  score: 46 -> 58 (better; raw 46 -> 58)
  findings resolved: ['DENSITY_EXTREME:warn']
    coverage_max: 6.33 -> 6.88
    raw_score: 46 -> 58
    satin_advance_mm: 0.627 -> 0.458
    satin_short_fraction: 0.022 -> 0.146
    satin_steps: 412 -> 472
    uncovered_worst_mm2: 0.0 -> 112.4
photo/photo_owl_pale.png @ 80mm/hat_front:
  score: 46 -> 58 (better; raw 46 -> 58)
  findings resolved: ['DENSITY_EXTREME:warn']
    coverage_max: 6.43 -> 7.75
    raw_score: 46 -> 58
    satin_advance_mm: 0.628 -> 0.443
    satin_short_fraction: 0.019 -> 0.104
    satin_steps: 424 -> 510
    trims_per_1000: 0.4 -> 0.6
    uncovered_wanted_mm2: 8088.2 -> 8519.9
    uncovered_worst_mm2: 0.0 -> 139.2
photo/photo_scene_stub.png @ 80mm/left_chest:
  score: 64 -> 52 (worse; raw 64 -> 52)
  grade: C -> D (FELL A BAND)
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn']
    coverage_max: 8.36 -> 14.27
    coverage_p95: 4.72 -> 5.02
    raw_score: 64 -> 52
    same_hole_fraction: 0.054 -> 0.059
    satin_steps: 3833 -> 5651
    stitch_count: 21675 -> 23946
    uncovered_total_mm2: 6.0 -> 20.1
    uncovered_wanted_mm2: 3517.8 -> 4354.6
    uncovered_worst_mm2: 6.0 -> 94.6
photo/photo_scene_stub.png @ 80mm/hat_front:
  score: 76 -> 52 (worse; raw 76 -> 52)
  grade: B -> D (FELL A BAND)
  findings APPEARED: ['ARTWORK_UNCOVERED:warn', 'SATIN_GAPS_TIGHT:warn']
    coverage_max: 7.71 -> 10.3
    coverage_p95: 5.03 -> 5.3
    raw_score: 76 -> 52
    satin_short_fraction: 0.127 -> 0.068
    satin_steps: 3805 -> 5477
    stitch_count: 22467 -> 24115
    trims_per_1000: 5.6 -> 4.5
    uncovered_total_mm2: 0.0 -> 18.3
    uncovered_wanted_mm2: 3524.5 -> 4388.8
    uncovered_worst_mm2: 4.5 -> 97.7
photo/photo_subject_stub.png @ 80mm/left_chest:
  score: 58 -> 70 (better; raw 58 -> 70)
  grade: D -> C
  findings resolved: ['ARTWORK_UNCOVERED:warn']
    raw_score: 58 -> 70
    uncovered_total_mm2: 956.0 -> 0.0
    uncovered_wanted_mm2: 4094.2 -> 4394.1
    uncovered_worst_mm2: 38.2 -> 138.1
photo/photo_subject_stub.png @ 80mm/hat_front:
  score: 58 -> 70 (better; raw 58 -> 70)
  grade: D -> C
  findings resolved: ['ARTWORK_UNCOVERED:warn']
    raw_score: 58 -> 70
    uncovered_total_mm2: 956.2 -> 0.0
    uncovered_wanted_mm2: 4094.2 -> 4428.0
    uncovered_worst_mm2: 38.2 -> 142.1
photo/photo_sunset_backlit.png @ 80mm/left_chest:
  score: 76 -> 88 (better; raw 76 -> 88)
  findings APPEARED: ['ARTWORK_UNCOVERED:warn']
  findings resolved: ['LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn']
    coverage_max: 8.34 -> 7.87
    raw_score: 76 -> 88
    satin_advance_mm: 0.371 -> 0.445
    satin_short_fraction: 0.582 -> 0.236
    trims_per_1000: 2.6 -> 2.8
    uncovered_total_mm2: 0.0 -> 25.0
    uncovered_wanted_mm2: 4314.2 -> 5009.7
    uncovered_worst_mm2: 0.2 -> 43.2
photo/photo_sunset_backlit.png @ 80mm/hat_front:
  findings APPEARED: ['ARTWORK_UNCOVERED:warn']
  findings resolved: ['LETTERING_TOO_SMALL:warn']
    satin_advance_mm: 0.401 -> 0.447
    satin_short_fraction: 0.571 -> 0.256
    satin_steps: 42 -> 39
    trims_per_1000: 3.1 -> 3.5
    uncovered_total_mm2: 0.0 -> 24.6
    uncovered_wanted_mm2: 4326.8 -> 5024.2
    uncovered_worst_mm2: 0.2 -> 23.5
photo/region_blobs.png @ 80mm/left_chest:
  score: 0 unchanged, raw -86 -> -8 (better)
  finding count changed: THREAD_MATCH_POOR:block: x2 -> x1
  finding count changed: THREAD_MATCH_POOR:warn: x7 -> x3
    color_changes: 16 -> 11
    coverage_max: 6.62 -> 6.02
    coverage_p95: 4.43 -> 3.92
    ground_area_frac: 0.502 -> 0.639
    raw_score: -86 -> -8
    stitch_count: 18884 -> 16058
    thread_worst_delta_e: 11.5 -> 12.2
    uncovered_wanted_mm2: 3187.2 -> 3619.9
photo/region_blobs.png @ 80mm/hat_front:
  score: 0 unchanged, raw -86 -> -8 (better)
  finding count changed: THREAD_MATCH_POOR:block: x2 -> x1
  finding count changed: THREAD_MATCH_POOR:warn: x7 -> x3
    color_changes: 16 -> 11
    coverage_p95: 4.61 -> 4.03
    ground_area_frac: 0.502 -> 0.639
    raw_score: -86 -> -8
    stitch_count: 18845 -> 16193
    thread_worst_delta_e: 11.5 -> 12.2
    uncovered_wanted_mm2: 3186.0 -> 3620.6
photo/repro_gradient_white_icon.png @ 80mm/left_chest:
    coverage_max: 4.92 -> 6.94
    coverage_p95: 3.62 -> 4.12
    satin_short_fraction: 0.006 -> 0.004
    trims_per_1000: 0.8 -> 1.0
    uncovered_wanted_mm2: 6095.5 -> 6561.0
    uncovered_worst_mm2: 0.8 -> 81.0
photo/repro_gradient_white_icon.png @ 80mm/hat_front:
    coverage_max: 5.43 -> 4.9
    coverage_p95: 3.8 -> 3.59
    same_hole_fraction: 0.026 -> 0.028
    satin_short_fraction: 0.006 -> 0.004
    stitch_count: 23663 -> 21407
    trims_per_1000: 0.8 -> 1.0
    uncovered_wanted_mm2: 6098.2 -> 6561.0
    uncovered_worst_mm2: 0.5 -> 81.0
photo/summit_badge.png @ 80mm/left_chest:
  score: 0 unchanged, raw -116 -> -134 (worse)
  findings APPEARED: ['STABILIZER_CUTAWAY:info']
  finding count changed: THREAD_MATCH_POOR:block: x1 -> x2
  finding count changed: THREAD_MATCH_POOR:warn: x9 -> x8
    color_changes: 11 -> 13
    coverage_max: 7.25 -> 6.29
    legibility: 0.325 -> 0.188
    legibility_worst: 0.143 -> 0.0
    link_segments: 2 -> 1
    link_thread_mm: 0.9 -> 0.4
    raw_score: -116 -> -134
    same_hole_fraction: 0.044 -> 0.038
    satin_advance_mm: 0.417 -> 0.45
    satin_short_fraction: 0.42 -> 0.293
    stitch_count: 23831 -> 25496
    thread_worst_delta_e: 12.5 -> 21.5
    trims_per_1000: 1.6 -> 1.9
    uncovered_wanted_mm2: 4252.0 -> 4638.1
    uncovered_worst_mm2: 0.0 -> 0.4
photo/summit_badge.png @ 80mm/hat_front:
  score: 0 unchanged, raw -116 -> -122 (worse)
  findings APPEARED: ['STABILIZER_CUTAWAY:info']
  findings resolved: ['STITCHES_TOO_SHORT:warn']
  finding count changed: THREAD_MATCH_POOR:block: x1 -> x2
  finding count changed: THREAD_MATCH_POOR:warn: x9 -> x8
    color_changes: 11 -> 13
    legibility: 0.33 -> 0.037
    legibility_worst: 0.154 -> 0.0
    link_segments: 1 -> 0
    link_thread_mm: 0.4 -> 0.0
    raw_score: -116 -> -122
    same_hole_fraction: 0.044 -> 0.039
    satin_advance_mm: 0.416 -> 0.446
    satin_short_fraction: 0.384 -> 0.243
    stitch_count: 23495 -> 25602
    thread_worst_delta_e: 12.5 -> 21.5
    trims_per_1000: 1.7 -> 2.2
    uncovered_wanted_mm2: 4262.0 -> 4650.8
    uncovered_worst_mm2: 0.0 -> 0.4
becker_marine_logo.png @ 80mm/left_chest:
    color_changes: 2 -> 1
    coverage_max: 4.57 -> 9.24
    coverage_p50: 1.43 -> 1.54
    coverage_p95: 3.28 -> 3.68
    fill_axis_concentration: 1.0 -> 0.946
    same_hole_fraction: 0.067 -> 0.044
    satin_shapes: 8 -> 9
    satin_short_fraction: 0.082 -> 0.065
    satin_steps: 3173 -> 4520
    trims_per_1000: 7.5 -> 5.6
    uncovered_total_mm2: 6.5 -> 13.4
    uncovered_wanted_mm2: 738.2 -> 1415.4
    uncovered_worst_mm2: 6.5 -> 3.4
becker_marine_logo.png @ 80mm/hat_front:
  score: 88 -> 76 (worse; raw 88 -> 76)
  findings APPEARED: ['ARTWORK_UNCOVERED:warn']
    color_changes: 2 -> 1
    coverage_max: 4.8 -> 9.49
    coverage_p50: 1.33 -> 1.59
    coverage_p95: 3.45 -> 3.87
    raw_score: 88 -> 76
    same_hole_fraction: 0.072 -> 0.043
    satin_shapes: 8 -> 9
    satin_short_fraction: 0.072 -> 0.041
    satin_steps: 3215 -> 4722
    trims_per_1000: 8.6 -> 5.1
    uncovered_total_mm2: 0.0 -> 5.9
    uncovered_wanted_mm2: 715.8 -> 1419.4
    uncovered_worst_mm2: 4.8 -> 1.7
logo_script_tires.png @ 80mm/left_chest:
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn']
  findings resolved: ['TRIM_HEAVY:warn']
    color_changes: 1 -> 0
    coverage_p50: 1.27 -> 1.67
    coverage_p95: 2.91 -> 3.13
    same_hole_fraction: 0.028 -> 0.02
    satin_short_fraction: 0.034 -> 0.017
    satin_steps: 1492 -> 1570
    stitch_count: 2345 -> 2654
    trims_per_1000: 4.7 -> 2.3
    uncovered_wanted_mm2: 508.2 -> 736.6
    uncovered_worst_mm2: 0.0 -> 0.1
logo_script_tires.png @ 80mm/hat_front:
  score: 100 -> 88 (worse; raw 100 -> 88)
  grade: A -> B (FELL A BAND)
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn']
    color_changes: 1 -> 0
    coverage_p95: 2.99 -> 2.75
    raw_score: 100 -> 88
    same_hole_fraction: 0.025 -> 0.021
    satin_short_fraction: 0.037 -> 0.018
    trims_per_1000: 3.7 -> 2.9
    uncovered_wanted_mm2: 503.0 -> 737.6
    uncovered_worst_mm2: 0.0 -> 0.1
photo/logo_bridge_bar.jpg @ 80mm/left_chest:
  score: 0 unchanged, raw -50 -> -98 (worse)
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn', 'THREAD_MATCH_POOR:warn']
  findings resolved: ['LETTERING_ILLEGIBLE:warn']
    color_changes: 14 -> 12
    coverage_max: 6.94 -> 8.33
    coverage_p95: 3.99 -> 4.95
    ground_area_frac: 0.459 -> 0.355
    legibility_clusters: 0 -> 1
    legibility_readable: 1 -> 0
    link_segments: 0 -> 5
    link_thread_mm: 0.0 -> 5.0
    raw_score: -50 -> -98
    satin_shapes: 28 -> 31
    satin_steps: 5075 -> 6465
    stitch_count: 14695 -> 16364
    thread_worst_delta_e: 12.2 -> 26.3
    trims_per_1000: 8.1 -> 5.6
    uncovered_wanted_mm2: 1376.5 -> 2441.2
    uncovered_worst_mm2: 0.0 -> 0.5
photo/logo_bridge_bar.jpg @ 80mm/hat_front:
  score: 0 unchanged, raw -38 -> -86 (worse)
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn', 'THREAD_MATCH_POOR:warn']
  findings resolved: ['LETTERING_ILLEGIBLE:warn']
    color_changes: 15 -> 12
    coverage_max: 7.01 -> 8.16
    coverage_p50: 2.68 -> 2.83
    coverage_p95: 4.12 -> 5.24
    ground_area_frac: 0.459 -> 0.355
    legibility_clusters: 0 -> 1
    legibility_readable: 1 -> 0
    link_segments: 0 -> 4
    link_thread_mm: 0.0 -> 4.7
    raw_score: -38 -> -86
    same_hole_fraction: 0.071 -> 0.063
    satin_shapes: 28 -> 31
    satin_short_fraction: 0.218 -> 0.157
    satin_steps: 4701 -> 6428
    stitch_count: 14268 -> 16321
    thread_worst_delta_e: 12.2 -> 26.3
    trims_per_1000: 8.2 -> 5.3
    uncovered_wanted_mm2: 1374.0 -> 2441.2
    uncovered_worst_mm2: 0.2 -> 0.4
photo/logo_gaulke_roofing.png @ 80mm/left_chest:
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn']
  findings resolved: ['STITCHES_TOO_SHORT:warn']
    coverage_p50: 1.08 -> 1.02
    legibility: 0.882 -> 1.0
    legibility_worst: 0.882 -> 1.0
    satin_short_fraction: 0.268 -> 0.164
    satin_steps: 2983 -> 2688
    stitch_count: 4531 -> 4205
    thread_worst_delta_e: 18.5 -> 13.4
    trims_per_1000: 8.8 -> 7.8
    uncovered_wanted_mm2: 209.2 -> 681.5
    uncovered_worst_mm2: 0.0 -> 0.3
photo/logo_gaulke_roofing.png @ 80mm/hat_front:
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn']
  findings resolved: ['STITCHES_TOO_SHORT:warn']
    coverage_max: 5.14 -> 4.8
    coverage_p95: 2.72 -> 3.01
    legibility: 0.806 -> 0.941
    legibility_worst: 0.806 -> 0.941
    same_hole_fraction: 0.082 -> 0.055
    satin_short_fraction: 0.266 -> 0.111
    satin_steps: 2894 -> 2726
    thread_worst_delta_e: 18.5 -> 13.4
    trims_per_1000: 12.1 -> 7.4
    uncovered_wanted_mm2: 204.8 -> 670.9
    uncovered_worst_mm2: 0.0 -> 0.4
photo/logo_golden_tee.jpg @ 80mm/left_chest:
  score: 0 unchanged, raw -80 -> -62 (better)
  findings APPEARED: ['SATIN_GAPS_TIGHT:warn']
  findings resolved: ['STITCHES_TOO_SHORT:warn']
  finding count changed: THREAD_MATCH_POOR:block: x2 -> x1
  finding count changed: THREAD_MATCH_POOR:warn: x6 -> x7
    color_changes: 12 -> 13
    coverage_max: 8.11 -> 9.94
    coverage_p50: 1.48 -> 2.0
    coverage_p95: 3.88 -> 5.5
    legibility_clusters: 1 -> 2
    link_segments: 3 -> 1
    link_thread_mm: 1.1 -> 0.4
    raw_score: -80 -> -62
    same_hole_fraction: 0.06 -> 0.065
    satin_shapes: 29 -> 37
    satin_short_fraction: 0.319 -> 0.228
    satin_steps: 5407 -> 6467
    stitch_count: 7094 -> 8595
    thread_worst_delta_e: 14.9 -> 13.0
    trims_per_1000: 8.6 -> 5.7
    uncovered_wanted_mm2: 383.0 -> 874.6
    uncovered_worst_mm2: 0.0 -> 2.3
photo/logo_golden_tee.jpg @ 80mm/hat_front:
  score: 0 unchanged, raw -80 -> -74 (better)
  findings APPEARED: ['ARTWORK_UNCOVERED:warn', 'SATIN_GAPS_TIGHT:warn']
  findings resolved: ['STITCHES_TOO_SHORT:warn']
  finding count changed: THREAD_MATCH_POOR:block: x2 -> x1
  finding count changed: THREAD_MATCH_POOR:warn: x6 -> x7
    color_changes: 12 -> 13
    coverage_max: 6.49 -> 12.39
    coverage_p50: 1.47 -> 2.03
    coverage_p95: 3.63 -> 6.23
    legibility_clusters: 1 -> 2
    link_segments: 3 -> 0
    link_thread_mm: 1.0 -> 0.0
    raw_score: -80 -> -74
    same_hole_fraction: 0.066 -> 0.059
    satin_shapes: 29 -> 37
    satin_short_fraction: 0.262 -> 0.118
    satin_steps: 5416 -> 6419
    stitch_count: 7125 -> 8560
    thread_worst_delta_e: 14.9 -> 13.0
    trims_per_1000: 10.0 -> 5.7
    uncovered_total_mm2: 0.0 -> 1.2
    uncovered_wanted_mm2: 380.8 -> 882.3
    uncovered_worst_mm2: 0.2 -> 1.2
photo/logo_hotel_fremont.webp @ 80mm/left_chest:
  score: 64 -> 76 (better; raw 64 -> 76)
  grade: C -> B
  findings resolved: ['STITCHES_TOO_SHORT:warn']
    coverage_max: 6.65 -> 7.17
    coverage_p50: 2.81 -> 2.98
    link_segments: 6 -> 4
    link_thread_mm: 2.3 -> 1.5
    raw_score: 64 -> 76
    same_hole_fraction: 0.115 -> 0.104
    satin_shapes: 18 -> 19
    satin_short_fraction: 0.996 -> 0.104
    satin_steps: 2423 -> 2582
    trims_per_1000: 4.1 -> 2.5
    uncovered_wanted_mm2: 1473.5 -> 2141.2
    uncovered_worst_mm2: 0.0 -> 0.1
photo/logo_hotel_fremont.webp @ 80mm/hat_front:
  score: 64 -> 88 (better; raw 64 -> 88)
  grade: C -> B
  findings resolved: ['LETTERING_ILLEGIBLE:warn', 'STITCHES_TOO_SHORT:warn']
    coverage_max: 6.9 -> 7.77
    coverage_p50: 2.7 -> 2.94
    legibility: 0.587 -> 0.726
    legibility_worst: 0.296 -> 0.533
    link_thread_mm: 1.6 -> 1.5
    raw_score: 64 -> 88
    same_hole_fraction: 0.122 -> 0.105
    satin_shapes: 18 -> 19
    satin_short_fraction: 0.997 -> 0.061
    satin_steps: 2412 -> 2577
    trims_per_1000: 4.1 -> 3.0
    uncovered_wanted_mm2: 1492.8 -> 2146.3
    uncovered_worst_mm2: 0.0 -> 0.2
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest:
  score: 0 -> 10 (better; raw -44 -> 10)
  findings resolved: ['THREAD_MATCH_POOR:warn']
  finding count changed: THREAD_MATCH_POOR:block: x2 -> x1
    color_changes: 12 -> 11
    coverage_max: 6.32 -> 7.19
    coverage_p95: 3.71 -> 3.39
    ground_area_frac: 0.46 -> 0.484
    legibility: 0.5 -> 0.55
    legibility_readable: 4 -> 3
    link_segments: 1 -> 3
    link_thread_mm: 0.3 -> 1.1
    raw_score: -44 -> 10
    satin_advance_mm: 0.416 -> 0.44
    satin_short_fraction: 0.412 -> 0.357
    stitch_count: 8356 -> 7934
    thread_worst_delta_e: 44.4 -> 16.9
    trims_per_1000: 8.4 -> 7.8
    uncovered_wanted_mm2: 388.0 -> 942.9
    uncovered_worst_mm2: 0.5 -> 0.9
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front:
  score: 0 -> 22 (better; raw -44 -> 22)
  findings resolved: ['STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:warn']
  finding count changed: THREAD_MATCH_POOR:block: x2 -> x1
    color_changes: 12 -> 11
    coverage_max: 7.17 -> 6.58
    coverage_p95: 3.66 -> 3.27
    ground_area_frac: 0.46 -> 0.484
    legibility: 0.562 -> 0.469
    legibility_readable: 4 -> 3
    link_segments: 1 -> 4
    link_thread_mm: 0.5 -> 1.6
    raw_score: -44 -> 22
    satin_short_fraction: 0.342 -> 0.229
    satin_steps: 2761 -> 2496
    stitch_count: 8961 -> 7897
    thread_worst_delta_e: 44.4 -> 16.9
    trims_per_1000: 9.3 -> 8.5
    uncovered_wanted_mm2: 390.0 -> 945.9
    uncovered_worst_mm2: 0.2 -> 0.9
EXIT=1
```

## Appendix B — every leaf that changed on a pre-existing key, old → new

721 leaves. Metric keys the old ruler did not carry are not listed
(they are new, not changed). Values are the stored ones, so this is the
complete answer to "which existing numbers moved, and by how much".

```
becker_marine_logo.png @ 80mm/hat_front :: score: 88 -> 76
becker_marine_logo.png @ 80mm/hat_front :: findings: ['TRIM_HEAVY:warn'] -> ['ARTWORK_UNCOVERED:warn', 'TRIM_HEAVY:warn']
becker_marine_logo.png @ 80mm/hat_front :: metrics.color_changes: 2 -> 1
becker_marine_logo.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 2104.0 -> 2091.0
becker_marine_logo.png @ 80mm/hat_front :: metrics.coverage_max: 4.8 -> 9.49
becker_marine_logo.png @ 80mm/hat_front :: metrics.coverage_p50: 1.33 -> 1.59
becker_marine_logo.png @ 80mm/hat_front :: metrics.coverage_p95: 3.45 -> 3.87
becker_marine_logo.png @ 80mm/hat_front :: metrics.fill_axis_concentration: 0.983 -> 1.0
becker_marine_logo.png @ 80mm/hat_front :: metrics.ground_area_frac: 0.284 -> 0.297
becker_marine_logo.png @ 80mm/hat_front :: metrics.ground_span_frac: 0.665 -> 0.672
becker_marine_logo.png @ 80mm/hat_front :: metrics.raw_score: 88 -> 76
becker_marine_logo.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.072 -> 0.043
becker_marine_logo.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.419 -> 0.416
becker_marine_logo.png @ 80mm/hat_front :: metrics.satin_shapes: 8 -> 9
becker_marine_logo.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.072 -> 0.041
becker_marine_logo.png @ 80mm/hat_front :: metrics.satin_steps: 3215 -> 4722
becker_marine_logo.png @ 80mm/hat_front :: metrics.stitch_count: 6894 -> 7060
becker_marine_logo.png @ 80mm/hat_front :: metrics.trims_per_1000: 8.6 -> 5.1
becker_marine_logo.png @ 80mm/hat_front :: metrics.uncovered_total_mm2: 0.0 -> 5.9
becker_marine_logo.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 715.8 -> 1419.4
becker_marine_logo.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 4.8 -> 1.7
becker_marine_logo.png @ 80mm/left_chest :: metrics.color_changes: 2 -> 1
becker_marine_logo.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 1956.0 -> 1957.0
becker_marine_logo.png @ 80mm/left_chest :: metrics.coverage_max: 4.57 -> 9.24
becker_marine_logo.png @ 80mm/left_chest :: metrics.coverage_p50: 1.43 -> 1.54
becker_marine_logo.png @ 80mm/left_chest :: metrics.coverage_p95: 3.28 -> 3.68
becker_marine_logo.png @ 80mm/left_chest :: metrics.fill_advance_mm: 0.15 -> None
becker_marine_logo.png @ 80mm/left_chest :: metrics.fill_axis_concentration: 1.0 -> 0.946
becker_marine_logo.png @ 80mm/left_chest :: metrics.ground_area_frac: 0.284 -> 0.297
becker_marine_logo.png @ 80mm/left_chest :: metrics.ground_span_frac: 0.665 -> 0.672
becker_marine_logo.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.067 -> 0.044
becker_marine_logo.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.421 -> 0.418
becker_marine_logo.png @ 80mm/left_chest :: metrics.satin_shapes: 8 -> 9
becker_marine_logo.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.082 -> 0.065
becker_marine_logo.png @ 80mm/left_chest :: metrics.satin_steps: 3173 -> 4520
becker_marine_logo.png @ 80mm/left_chest :: metrics.stitch_count: 6829 -> 6558
becker_marine_logo.png @ 80mm/left_chest :: metrics.trims_per_1000: 7.5 -> 5.6
becker_marine_logo.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 6.5 -> 13.4
becker_marine_logo.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 738.2 -> 1415.4
becker_marine_logo.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 6.5 -> 3.4
bg_uncertain.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 3766.0 -> 3765.0
bg_uncertain.png @ 80mm/hat_front :: metrics.coverage_max: 4.23 -> 4.11
bg_uncertain.png @ 80mm/hat_front :: metrics.coverage_p95: 3.4 -> 3.42
bg_uncertain.png @ 80mm/hat_front :: metrics.ground_span_frac: 0.997 -> 0.992
bg_uncertain.png @ 80mm/hat_front :: metrics.stitch_count: 11282 -> 11235
bg_uncertain.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 3287.5 -> 3447.9
bg_uncertain.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 3764.0 -> 3720.0
bg_uncertain.png @ 80mm/left_chest :: metrics.coverage_max: 3.77 -> 3.68
bg_uncertain.png @ 80mm/left_chest :: metrics.coverage_p95: 3.1 -> 3.11
bg_uncertain.png @ 80mm/left_chest :: metrics.ground_span_frac: 0.997 -> 0.992
bg_uncertain.png @ 80mm/left_chest :: metrics.stitch_count: 10384 -> 10349
bg_uncertain.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 3334.5 -> 3435.2
logo_alpha.png @ 80mm/hat_front :: metrics.coverage_max: 4.88 -> 5.0
logo_alpha.png @ 80mm/hat_front :: metrics.coverage_p50: 2.99 -> 3.01
logo_alpha.png @ 80mm/hat_front :: metrics.coverage_p95: 3.55 -> 3.51
logo_alpha.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.405 -> 0.399
logo_alpha.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.033 -> 0.034
logo_alpha.png @ 80mm/hat_front :: metrics.satin_steps: 121 -> 119
logo_alpha.png @ 80mm/hat_front :: metrics.stitch_count: 6211 -> 6208
logo_alpha.png @ 80mm/hat_front :: metrics.trims_per_1000: 1.6 -> 1.8
logo_alpha.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 1147.5 -> 1292.2
logo_alpha.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 0.1
logo_alpha.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 1599.0 -> 1600.0
logo_alpha.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.403 -> 0.399
logo_alpha.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.05 -> 0.034
logo_alpha.png @ 80mm/left_chest :: metrics.satin_steps: 121 -> 119
logo_alpha.png @ 80mm/left_chest :: metrics.stitch_count: 5784 -> 5792
logo_alpha.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 1141.8 -> 1280.2
logo_alpha.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.1
logo_script_tires.png @ 80mm/hat_front :: score: 100 -> 88
logo_script_tires.png @ 80mm/hat_front :: grade: A -> B
logo_script_tires.png @ 80mm/hat_front :: findings: [] -> ['SATIN_GAPS_TIGHT:warn']
logo_script_tires.png @ 80mm/hat_front :: metrics.color_changes: 1 -> 0
logo_script_tires.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 1037.0 -> 1020.0
logo_script_tires.png @ 80mm/hat_front :: metrics.coverage_max: 5.16 -> 5.34
logo_script_tires.png @ 80mm/hat_front :: metrics.coverage_p50: 1.32 -> 1.36
logo_script_tires.png @ 80mm/hat_front :: metrics.coverage_p95: 2.99 -> 2.75
logo_script_tires.png @ 80mm/hat_front :: metrics.raw_score: 100 -> 88
logo_script_tires.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.025 -> 0.021
logo_script_tires.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.433 -> 0.415
logo_script_tires.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.037 -> 0.018
logo_script_tires.png @ 80mm/hat_front :: metrics.satin_steps: 1606 -> 1641
logo_script_tires.png @ 80mm/hat_front :: metrics.stitch_count: 2415 -> 2446
logo_script_tires.png @ 80mm/hat_front :: metrics.trims_per_1000: 3.7 -> 2.9
logo_script_tires.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 503.0 -> 737.6
logo_script_tires.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 0.1
logo_script_tires.png @ 80mm/left_chest :: findings: ['TRIM_HEAVY:warn'] -> ['SATIN_GAPS_TIGHT:warn']
logo_script_tires.png @ 80mm/left_chest :: metrics.color_changes: 1 -> 0
logo_script_tires.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 983.0 -> 976.0
logo_script_tires.png @ 80mm/left_chest :: metrics.coverage_max: 5.49 -> 5.53
logo_script_tires.png @ 80mm/left_chest :: metrics.coverage_p50: 1.27 -> 1.67
logo_script_tires.png @ 80mm/left_chest :: metrics.coverage_p95: 2.91 -> 3.13
logo_script_tires.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.028 -> 0.02
logo_script_tires.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.423 -> 0.413
logo_script_tires.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.034 -> 0.017
logo_script_tires.png @ 80mm/left_chest :: metrics.satin_steps: 1492 -> 1570
logo_script_tires.png @ 80mm/left_chest :: metrics.stitch_count: 2345 -> 2654
logo_script_tires.png @ 80mm/left_chest :: metrics.trims_per_1000: 4.7 -> 2.3
logo_script_tires.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 508.2 -> 736.6
logo_script_tires.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.1
logo_whitebg.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 1622.0 -> 1625.0
logo_whitebg.png @ 80mm/hat_front :: metrics.coverage_max: 4.97 -> 4.98
logo_whitebg.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.405 -> 0.406
logo_whitebg.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.033 -> 0.034
logo_whitebg.png @ 80mm/hat_front :: metrics.satin_steps: 121 -> 117
logo_whitebg.png @ 80mm/hat_front :: metrics.stitch_count: 6175 -> 6180
logo_whitebg.png @ 80mm/hat_front :: metrics.trims_per_1000: 1.6 -> 1.8
logo_whitebg.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 1140.8 -> 1280.3
logo_whitebg.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 0.2
logo_whitebg.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 1595.0 -> 1596.0
logo_whitebg.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.074 -> 0.073
logo_whitebg.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.403 -> 0.406
logo_whitebg.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.05 -> 0.034
logo_whitebg.png @ 80mm/left_chest :: metrics.satin_steps: 121 -> 117
logo_whitebg.png @ 80mm/left_chest :: metrics.stitch_count: 5752 -> 5758
logo_whitebg.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 1139.0 -> 1277.0
logo_whitebg.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.1
photo/drone_render.png @ 80mm/hat_front :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_TOO_SMALL:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn']
photo/drone_render.png @ 80mm/hat_front :: metrics.color_changes: 14 -> 16
photo/drone_render.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 3842.0 -> 3813.0
photo/drone_render.png @ 80mm/hat_front :: metrics.coverage_max: 7.27 -> 9.52
photo/drone_render.png @ 80mm/hat_front :: metrics.coverage_p50: 2.67 -> 2.68
photo/drone_render.png @ 80mm/hat_front :: metrics.coverage_p95: 4.81 -> 4.85
photo/drone_render.png @ 80mm/hat_front :: metrics.ground_area_frac: 0.474 -> 0.485
photo/drone_render.png @ 80mm/hat_front :: metrics.ground_span_frac: 0.478 -> 0.571
photo/drone_render.png @ 80mm/hat_front :: metrics.legibility: 0.545 -> 0.167
photo/drone_render.png @ 80mm/hat_front :: metrics.legibility_worst: 0.545 -> 0.167
photo/drone_render.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.066 -> 0.071
photo/drone_render.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.418 -> 0.413
photo/drone_render.png @ 80mm/hat_front :: metrics.satin_shapes: 58 -> 61
photo/drone_render.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.234 -> 0.138
photo/drone_render.png @ 80mm/hat_front :: metrics.satin_steps: 3898 -> 4451
photo/drone_render.png @ 80mm/hat_front :: metrics.stitch_count: 18435 -> 18531
photo/drone_render.png @ 80mm/hat_front :: metrics.thread_worst_delta_e: 18.1 -> 19.8
photo/drone_render.png @ 80mm/hat_front :: metrics.trims_per_1000: 8.1 -> 7.9
photo/drone_render.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 1979.5 -> 3029.9
photo/drone_render.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 2.8 -> 0.4
photo/drone_render.png @ 80mm/left_chest :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn']
photo/drone_render.png @ 80mm/left_chest :: metrics.color_changes: 14 -> 16
photo/drone_render.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 3747.0 -> 3732.0
photo/drone_render.png @ 80mm/left_chest :: metrics.coverage_max: 10.7 -> 8.31
photo/drone_render.png @ 80mm/left_chest :: metrics.coverage_p50: 2.67 -> 2.69
photo/drone_render.png @ 80mm/left_chest :: metrics.coverage_p95: 4.71 -> 4.67
photo/drone_render.png @ 80mm/left_chest :: metrics.ground_area_frac: 0.474 -> 0.485
photo/drone_render.png @ 80mm/left_chest :: metrics.ground_span_frac: 0.478 -> 0.571
photo/drone_render.png @ 80mm/left_chest :: metrics.legibility: 0.333 -> 0.2
photo/drone_render.png @ 80mm/left_chest :: metrics.legibility_worst: 0.333 -> 0.2
photo/drone_render.png @ 80mm/left_chest :: metrics.link_segments: 2 -> 1
photo/drone_render.png @ 80mm/left_chest :: metrics.link_thread_mm: 0.4 -> 0.2
photo/drone_render.png @ 80mm/left_chest :: metrics.raw_score: -122 -> -110
photo/drone_render.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.068 -> 0.069
photo/drone_render.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.416 -> 0.412
photo/drone_render.png @ 80mm/left_chest :: metrics.satin_shapes: 58 -> 61
photo/drone_render.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.246 -> 0.221
photo/drone_render.png @ 80mm/left_chest :: metrics.satin_steps: 4229 -> 4505
photo/drone_render.png @ 80mm/left_chest :: metrics.stitch_count: 18168 -> 18658
photo/drone_render.png @ 80mm/left_chest :: metrics.thread_worst_delta_e: 18.1 -> 19.8
photo/drone_render.png @ 80mm/left_chest :: metrics.trims_per_1000: 7.4 -> 7.6
photo/drone_render.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 1946.2 -> 3050.6
photo/drone_render.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.2 -> 0.5
photo/enthusiast_logo.png @ 80mm/hat_front :: score: 76 -> 88
photo/enthusiast_logo.png @ 80mm/hat_front :: findings: ['LETTERING_ILLEGIBLE:warn', 'TRIM_HEAVY:warn'] -> ['TRIM_HEAVY:warn']
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 720.0 -> 715.0
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.coverage_max: 6.37 -> 4.42
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.coverage_p50: 1.48 -> 1.42
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.coverage_p95: 3.53 -> 3.35
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.fill_axis_concentration: 0.929 -> 0.945
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.legibility: 0.542 -> 1.0
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.legibility_worst: 0.286 -> 1.0
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.link_segments: 1 -> 0
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.link_thread_mm: 0.4 -> 0.0
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.raw_score: 76 -> 88
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.134 -> 0.106
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.43 -> 0.418
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.107 -> 0.049
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.satin_steps: 1341 -> 1108
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.stitch_count: 3267 -> 2629
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.trims_per_1000: 9.2 -> 5.3
photo/enthusiast_logo.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 156.2 -> 377.6
photo/enthusiast_logo.png @ 80mm/left_chest :: score: 88 -> 76
photo/enthusiast_logo.png @ 80mm/left_chest :: findings: ['TRIM_HEAVY:warn'] -> ['ARTWORK_UNCOVERED:warn', 'TRIM_HEAVY:warn']
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 663.0 -> 674.0
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.coverage_max: 4.01 -> 4.84
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.coverage_p50: 1.17 -> 1.26
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.coverage_p95: 3.07 -> 3.33
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.fill_axis_concentration: 0.92 -> 0.942
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.link_segments: 1 -> 0
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.link_thread_mm: 0.4 -> 0.0
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.raw_score: 88 -> 76
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.122 -> 0.106
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.425 -> 0.419
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.115 -> 0.051
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.satin_steps: 1262 -> 1123
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.stitch_count: 2492 -> 2484
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.trims_per_1000: 9.6 -> 5.6
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 0.0 -> 1.0
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 158.5 -> 381.9
photo/enthusiast_logo.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 1.5 -> 1.0
photo/fur_ramp.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 1097.5 -> 1284.9
photo/fur_ramp.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 1094.8 -> 1285.6
photo/gradient_ramp_linear.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 3736.5 -> 3800.0
photo/gradient_ramp_linear.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 3736.5 -> 3800.0
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.color_changes: 5 -> 6
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 5245.0 -> 5243.0
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.coverage_max: 4.17 -> 4.62
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.coverage_p50: 2.67 -> 2.68
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.coverage_p95: 3.67 -> 3.64
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.ground_span_frac: 0.991 -> 0.99
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.021 -> 0.022
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.stitch_count: 18101 -> 18128
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.subject_bg_delta_l: 72.99 -> 72.98
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.thread_worst_delta_e: 6.4 -> 6.3
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.trims_per_1000: 0.3 -> 0.7
photo/gradient_ramp_radial.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 4869.8 -> 5002.8
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.color_changes: 5 -> 6
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.coverage_max: 4.41 -> 4.47
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.coverage_p50: 2.67 -> 2.68
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.coverage_p95: 3.66 -> 3.67
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.ground_span_frac: 0.991 -> 0.99
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.021 -> 0.022
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.stitch_count: 18091 -> 18092
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.subject_bg_delta_l: 72.99 -> 72.98
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.thread_worst_delta_e: 6.4 -> 6.3
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.trims_per_1000: 0.3 -> 0.6
photo/gradient_ramp_radial.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 4867.8 -> 5002.8
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'TRIM_HEAVY:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn']
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.color_changes: 15 -> 12
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.coverage_area_mm2: 2703.0 -> 2725.0
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.coverage_max: 7.01 -> 8.16
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.coverage_p50: 2.68 -> 2.83
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.coverage_p95: 4.12 -> 5.24
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.ground_area_frac: 0.459 -> 0.355
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.ground_span_frac: 0.329 -> 0.327
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.legibility: 0.133 -> None
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.legibility_clusters: 0 -> 1
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.legibility_readable: 1 -> 0
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.legibility_worst: 0.133 -> None
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.link_segments: 0 -> 4
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.link_thread_mm: 0.0 -> 4.7
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.raw_score: -38 -> -86
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.same_hole_fraction: 0.071 -> 0.063
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.satin_advance_mm: 0.415 -> 0.417
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.satin_shapes: 28 -> 31
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.satin_short_fraction: 0.218 -> 0.157
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.satin_steps: 4701 -> 6428
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.stitch_count: 14268 -> 16321
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.thread_worst_delta_e: 12.2 -> 26.3
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.trims_per_1000: 8.2 -> 5.3
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 1374.0 -> 2441.2
photo/logo_bridge_bar.jpg @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.2 -> 0.4
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'TRIM_HEAVY:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn']
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.color_changes: 14 -> 12
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.coverage_area_mm2: 2680.0 -> 2709.0
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.coverage_max: 6.94 -> 8.33
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.coverage_p50: 2.68 -> 2.78
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.coverage_p95: 3.99 -> 4.95
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.ground_area_frac: 0.459 -> 0.355
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.ground_span_frac: 0.329 -> 0.327
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.legibility: 0.125 -> None
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.legibility_clusters: 0 -> 1
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.legibility_readable: 1 -> 0
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.legibility_worst: 0.125 -> None
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.link_segments: 0 -> 5
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.link_thread_mm: 0.0 -> 5.0
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.raw_score: -50 -> -98
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.same_hole_fraction: 0.07 -> 0.069
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.satin_advance_mm: 0.414 -> 0.417
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.satin_shapes: 28 -> 31
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.satin_short_fraction: 0.278 -> 0.287
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.satin_steps: 5075 -> 6465
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.stitch_count: 14695 -> 16364
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.thread_worst_delta_e: 12.2 -> 26.3
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.trims_per_1000: 8.1 -> 5.6
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 1376.5 -> 2441.2
photo/logo_bridge_bar.jpg @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.5
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: findings: ['LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'TRIM_HEAVY:warn'] -> ['LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'TRIM_HEAVY:warn']
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 1191.0 -> 1152.0
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.coverage_max: 5.14 -> 4.8
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.coverage_p50: 1.08 -> 1.03
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.coverage_p95: 2.72 -> 3.01
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.fill_axis_concentration: 0.967 -> 0.968
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.ground_area_frac: 0.225 -> 0.223
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.legibility: 0.806 -> 0.941
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.legibility_worst: 0.806 -> 0.941
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.082 -> 0.055
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.418 -> 0.427
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.266 -> 0.111
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.satin_steps: 2894 -> 2726
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.stitch_count: 4539 -> 4318
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.thread_worst_delta_e: 18.5 -> 13.4
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.trims_per_1000: 12.1 -> 7.4
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 204.8 -> 670.9
photo/logo_gaulke_roofing.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 0.4
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: findings: ['LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'TRIM_HEAVY:warn'] -> ['LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'TRIM_HEAVY:warn']
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 1129.0 -> 1083.0
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.coverage_max: 5.57 -> 5.39
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.coverage_p50: 1.08 -> 1.02
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.coverage_p95: 2.9 -> 2.93
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.ground_area_frac: 0.225 -> 0.223
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.legibility: 0.882 -> 1.0
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.legibility_worst: 0.882 -> 1.0
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.069 -> 0.066
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.415 -> 0.427
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.268 -> 0.164
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.satin_steps: 2983 -> 2688
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.stitch_count: 4531 -> 4205
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.thread_worst_delta_e: 18.5 -> 13.4
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.trims_per_1000: 8.8 -> 7.8
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 209.2 -> 681.5
photo/logo_gaulke_roofing.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.3
photo/logo_golden_tee.jpg @ 80mm/hat_front :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn'] -> ['ARTWORK_UNCOVERED:warn', 'COLOR_STOPS_HEAVY:warn', 'LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn']
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.color_changes: 12 -> 13
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.coverage_area_mm2: 1415.0 -> 1400.0
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.coverage_max: 6.49 -> 12.39
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.coverage_p50: 1.47 -> 2.03
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.coverage_p95: 3.63 -> 6.23
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.legibility_clusters: 1 -> 2
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.link_segments: 3 -> 0
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.link_thread_mm: 1.0 -> 0.0
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.raw_score: -80 -> -74
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.same_hole_fraction: 0.066 -> 0.059
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.satin_advance_mm: 0.424 -> 0.423
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.satin_shapes: 29 -> 37
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.satin_short_fraction: 0.262 -> 0.118
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.satin_steps: 5416 -> 6419
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.stitch_count: 7125 -> 8560
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.thread_worst_delta_e: 14.9 -> 13.0
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.trims_per_1000: 10.0 -> 5.7
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.uncovered_total_mm2: 0.0 -> 1.2
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 380.8 -> 882.3
photo/logo_golden_tee.jpg @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.2 -> 1.2
photo/logo_golden_tee.jpg @ 80mm/left_chest :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn']
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.color_changes: 12 -> 13
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.coverage_area_mm2: 1339.0 -> 1326.0
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.coverage_max: 8.11 -> 9.94
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.coverage_p50: 1.48 -> 2.0
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.coverage_p95: 3.88 -> 5.5
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.legibility_clusters: 1 -> 2
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.link_segments: 3 -> 1
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.link_thread_mm: 1.1 -> 0.4
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.raw_score: -80 -> -62
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.same_hole_fraction: 0.06 -> 0.065
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.satin_shapes: 29 -> 37
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.satin_short_fraction: 0.319 -> 0.228
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.satin_steps: 5407 -> 6467
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.stitch_count: 7094 -> 8595
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.thread_worst_delta_e: 14.9 -> 13.0
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.trims_per_1000: 8.6 -> 5.7
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 383.0 -> 874.6
photo/logo_golden_tee.jpg @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 2.3
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: score: 64 -> 88
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: grade: C -> B
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: findings: ['LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn'] -> ['LETTERING_TOO_SMALL:warn']
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.coverage_max: 6.9 -> 7.77
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.coverage_p50: 2.7 -> 2.94
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.coverage_p95: 5.58 -> 5.76
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.ground_area_frac: 0.743 -> 0.742
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.legibility: 0.587 -> 0.726
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.legibility_worst: 0.296 -> 0.533
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.link_thread_mm: 1.6 -> 1.5
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.raw_score: 64 -> 88
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.same_hole_fraction: 0.122 -> 0.105
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.satin_advance_mm: 0.402 -> 0.404
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.satin_shapes: 18 -> 19
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.satin_short_fraction: 0.997 -> 0.061
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.satin_steps: 2412 -> 2577
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.stitch_count: 13716 -> 13836
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.trims_per_1000: 4.1 -> 3.0
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 1492.8 -> 2146.3
photo/logo_hotel_fremont.webp @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 0.2
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: score: 64 -> 76
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: grade: C -> B
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: findings: ['LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn'] -> ['LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn']
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.coverage_area_mm2: 2349.0 -> 2347.0
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.coverage_max: 6.65 -> 7.17
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.coverage_p50: 2.81 -> 2.98
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.coverage_p95: 5.51 -> 5.62
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.ground_area_frac: 0.743 -> 0.742
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.link_segments: 6 -> 4
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.link_thread_mm: 2.3 -> 1.5
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.raw_score: 64 -> 76
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.same_hole_fraction: 0.115 -> 0.104
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.satin_advance_mm: 0.402 -> 0.404
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.satin_shapes: 18 -> 19
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.satin_short_fraction: 0.996 -> 0.104
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.satin_steps: 2423 -> 2582
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.stitch_count: 13436 -> 13609
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.trims_per_1000: 4.1 -> 2.5
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 1473.5 -> 2141.2
photo/logo_hotel_fremont.webp @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.1
photo/photo_chrome_specular.png @ 80mm/hat_front :: score: 88 -> 64
photo/photo_chrome_specular.png @ 80mm/hat_front :: grade: B -> C
photo/photo_chrome_specular.png @ 80mm/hat_front :: findings: ['PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info'] -> ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info']
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.coverage_max: 9.26 -> 7.42
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.coverage_p95: 5.39 -> 5.26
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.raw_score: 88 -> 64
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.049 -> 0.044
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.409 -> 0.451
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.236 -> 0.232
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.satin_steps: 199 -> 354
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.stitch_count: 37227 -> 36555
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.trims_per_1000: 2.0 -> 2.6
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.uncovered_total_mm2: 0.0 -> 2.1
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 6529.5 -> 7874.0
photo/photo_chrome_specular.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 89.9
photo/photo_chrome_specular.png @ 80mm/left_chest :: score: 64 -> 52
photo/photo_chrome_specular.png @ 80mm/left_chest :: grade: C -> D
photo/photo_chrome_specular.png @ 80mm/left_chest :: findings: ['LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info', 'STITCHES_TOO_SHORT:warn'] -> ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info', 'STITCHES_TOO_SHORT:warn']
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.coverage_max: 7.1 -> 7.07
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.coverage_p95: 5.02 -> 4.9
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.raw_score: 64 -> 52
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.046 -> 0.043
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.402 -> 0.445
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.371 -> 0.413
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.satin_steps: 202 -> 402
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.stitch_count: 36175 -> 35819
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.trims_per_1000: 2.5 -> 2.8
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 0.0 -> 2.3
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 6567.0 -> 7824.2
photo/photo_chrome_specular.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 65.8
photo/photo_dof_meadow.png @ 80mm/hat_front :: findings: ['LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn', 'STITCHES_TOO_SHORT:warn'] -> ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn']
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.coverage_max: 10.2 -> 9.5
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.coverage_p50: 3.01 -> 2.97
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.coverage_p95: 5.23 -> 5.15
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.067 -> 0.065
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.463 -> 0.459
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.256 -> 0.153
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.satin_steps: 129 -> 262
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.stitch_count: 22089 -> 21993
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.trims_per_1000: 3.1 -> 3.9
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.uncovered_total_mm2: 0.0 -> 9.4
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 3796.8 -> 4473.7
photo/photo_dof_meadow.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.2 -> 43.6
photo/photo_dof_meadow.png @ 80mm/left_chest :: findings: ['LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn', 'STITCHES_TOO_SHORT:warn'] -> ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn']
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.coverage_max: 7.97 -> 7.68
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.coverage_p95: 5.16 -> 5.06
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.07 -> 0.067
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.412 -> 0.446
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.405 -> 0.162
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.satin_steps: 121 -> 210
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.stitch_count: 21154 -> 20868
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.trims_per_1000: 2.8 -> 3.3
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 0.0 -> 18.4
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 3790.5 -> 4452.2
photo/photo_dof_meadow.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 44.9
photo/photo_grass_macro.png @ 80mm/hat_front :: score: 22 -> 46
photo/photo_grass_macro.png @ 80mm/hat_front :: grade: F -> D
photo/photo_grass_macro.png @ 80mm/hat_front :: findings: ['ARTWORK_UNCOVERED:warn', 'GROUND_SEWN:block', 'LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn', 'STITCHES_TOO_SHORT:warn'] -> ['ARTWORK_UNCOVERED:warn', 'GROUND_SEWN:block', 'PHOTO_RESOLUTION_LOW:warn']
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.coverage_max: 3.61 -> 3.72
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.coverage_p95: 1.34 -> 1.35
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.raw_score: 22 -> 46
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.428 -> 0.444
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.67 -> 0.124
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.satin_steps: 103 -> 137
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.stitch_count: 3945 -> 3979
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.trims_per_1000: 4.1 -> 3.8
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.uncovered_total_mm2: 460.2 -> 920.1
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 4633.2 -> 4965.4
photo/photo_grass_macro.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 26.5 -> 135.3
photo/photo_grass_macro.png @ 80mm/left_chest :: score: 10 -> 34
photo/photo_grass_macro.png @ 80mm/left_chest :: findings: ['ARTWORK_UNCOVERED:warn', 'GROUND_SEWN:block', 'LETTERING_TOO_SMALL:warn', 'PHOTO_RESOLUTION_LOW:warn', 'STITCHES_TOO_SHORT:warn', 'TRIM_HEAVY:warn'] -> ['ARTWORK_UNCOVERED:warn', 'GROUND_SEWN:block', 'PHOTO_RESOLUTION_LOW:warn', 'TRIM_HEAVY:warn']
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.coverage_max: 3.84 -> 3.8
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.coverage_p95: 1.32 -> 1.33
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.raw_score: 10 -> 34
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.024 -> 0.025
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.424 -> 0.442
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.688 -> 0.214
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.satin_steps: 96 -> 140
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.stitch_count: 3980 -> 4032
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.trims_per_1000: 4.8 -> 4.5
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 407.8 -> 967.0
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 4592.2 -> 4945.2
photo/photo_grass_macro.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 28.8 -> 111.4
photo/photo_owl_pale.png @ 80mm/hat_front :: score: 46 -> 58
photo/photo_owl_pale.png @ 80mm/hat_front :: findings: ['DENSITY_EXTREME:warn', 'GROUND_SEWN:block', 'PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info'] -> ['GROUND_SEWN:block', 'PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info']
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.coverage_max: 6.43 -> 7.75
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.raw_score: 46 -> 58
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.628 -> 0.443
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.019 -> 0.104
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.satin_steps: 424 -> 510
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.stitch_count: 25009 -> 25004
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.trims_per_1000: 0.4 -> 0.6
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 8088.2 -> 8519.9
photo/photo_owl_pale.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 139.2
photo/photo_owl_pale.png @ 80mm/left_chest :: score: 46 -> 58
photo/photo_owl_pale.png @ 80mm/left_chest :: findings: ['DENSITY_EXTREME:warn', 'GROUND_SEWN:block', 'PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info'] -> ['GROUND_SEWN:block', 'PHOTO_RESOLUTION_LOW:warn', 'STABILIZER_CUTAWAY:info']
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.coverage_max: 6.33 -> 6.88
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.coverage_p95: 4.08 -> 4.07
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.raw_score: 46 -> 58
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.024 -> 0.025
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.627 -> 0.458
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.022 -> 0.146
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.satin_steps: 412 -> 472
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.stitch_count: 25342 -> 25316
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 8087.5 -> 8474.2
photo/photo_owl_pale.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 112.4
photo/photo_scene_stub.png @ 80mm/hat_front :: score: 76 -> 52
photo/photo_scene_stub.png @ 80mm/hat_front :: grade: B -> D
photo/photo_scene_stub.png @ 80mm/hat_front :: findings: ['LETTERING_TOO_SMALL:warn', 'TRIM_HEAVY:warn'] -> ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'TRIM_HEAVY:warn']
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 4375.0 -> 4377.0
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.coverage_max: 7.71 -> 10.3
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.coverage_p50: 2.94 -> 3.05
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.coverage_p95: 5.03 -> 5.3
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.raw_score: 76 -> 52
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.45 -> 0.442
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.127 -> 0.068
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.satin_steps: 3805 -> 5477
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.stitch_count: 22467 -> 24115
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.trims_per_1000: 5.6 -> 4.5
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.uncovered_total_mm2: 0.0 -> 18.3
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 3524.5 -> 4388.8
photo/photo_scene_stub.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 4.5 -> 97.7
photo/photo_scene_stub.png @ 80mm/left_chest :: score: 64 -> 52
photo/photo_scene_stub.png @ 80mm/left_chest :: grade: C -> D
photo/photo_scene_stub.png @ 80mm/left_chest :: findings: ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn', 'TRIM_HEAVY:warn'] -> ['ARTWORK_UNCOVERED:warn', 'LETTERING_TOO_SMALL:warn', 'SATIN_GAPS_TIGHT:warn', 'TRIM_HEAVY:warn']
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 4360.0 -> 4364.0
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.coverage_max: 8.36 -> 14.27
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.coverage_p50: 2.86 -> 2.99
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.coverage_p95: 4.72 -> 5.02
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.raw_score: 64 -> 52
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.054 -> 0.059
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.451 -> 0.439
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.118 -> 0.119
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.satin_steps: 3833 -> 5651
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.stitch_count: 21675 -> 23946
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.trims_per_1000: 5.0 -> 4.8
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 6.0 -> 20.1
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 3517.8 -> 4354.6
photo/photo_scene_stub.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 6.0 -> 94.6
photo/photo_subject_stub.png @ 80mm/hat_front :: score: 58 -> 70
photo/photo_subject_stub.png @ 80mm/hat_front :: grade: D -> C
photo/photo_subject_stub.png @ 80mm/hat_front :: findings: ['ARTWORK_UNCOVERED:warn', 'THREAD_MATCH_POOR:block'] -> ['THREAD_MATCH_POOR:block']
photo/photo_subject_stub.png @ 80mm/hat_front :: metrics.raw_score: 58 -> 70
photo/photo_subject_stub.png @ 80mm/hat_front :: metrics.uncovered_total_mm2: 956.2 -> 0.0
photo/photo_subject_stub.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 4094.2 -> 4428.0
photo/photo_subject_stub.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 38.2 -> 142.1
photo/photo_subject_stub.png @ 80mm/left_chest :: score: 58 -> 70
photo/photo_subject_stub.png @ 80mm/left_chest :: grade: D -> C
photo/photo_subject_stub.png @ 80mm/left_chest :: findings: ['ARTWORK_UNCOVERED:warn', 'THREAD_MATCH_POOR:block'] -> ['THREAD_MATCH_POOR:block']
photo/photo_subject_stub.png @ 80mm/left_chest :: metrics.raw_score: 58 -> 70
photo/photo_subject_stub.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 956.0 -> 0.0
photo/photo_subject_stub.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 4094.2 -> 4394.1
photo/photo_subject_stub.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 38.2 -> 138.1
photo/photo_sunset_backlit.png @ 80mm/hat_front :: findings: ['LETTERING_TOO_SMALL:warn', 'STABILIZER_CUTAWAY:info', 'STITCHES_TOO_SHORT:warn'] -> ['ARTWORK_UNCOVERED:warn', 'STABILIZER_CUTAWAY:info', 'STITCHES_TOO_SHORT:warn']
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.coverage_max: 7.63 -> 7.35
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.coverage_p95: 5.16 -> 5.05
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.057 -> 0.055
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.401 -> 0.447
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.571 -> 0.256
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.satin_steps: 42 -> 39
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.stitch_count: 25870 -> 25649
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.trims_per_1000: 3.1 -> 3.5
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.uncovered_total_mm2: 0.0 -> 24.6
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 4326.8 -> 5024.2
photo/photo_sunset_backlit.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.2 -> 23.5
photo/photo_sunset_backlit.png @ 80mm/left_chest :: score: 76 -> 88
photo/photo_sunset_backlit.png @ 80mm/left_chest :: findings: ['LETTERING_TOO_SMALL:warn', 'STABILIZER_CUTAWAY:info', 'STITCHES_TOO_SHORT:warn'] -> ['ARTWORK_UNCOVERED:warn', 'STABILIZER_CUTAWAY:info']
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.coverage_max: 8.34 -> 7.87
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.coverage_p95: 5.08 -> 4.94
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.raw_score: 76 -> 88
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.059 -> 0.057
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.371 -> 0.445
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.582 -> 0.236
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.stitch_count: 26103 -> 25813
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.trims_per_1000: 2.6 -> 2.8
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.uncovered_total_mm2: 0.0 -> 25.0
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 4314.2 -> 5009.7
photo/photo_sunset_backlit.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.2 -> 43.2
photo/region_blobs.png @ 80mm/hat_front :: findings: ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn']
photo/region_blobs.png @ 80mm/hat_front :: metrics.color_changes: 16 -> 11
photo/region_blobs.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 3915.0 -> 3911.0
photo/region_blobs.png @ 80mm/hat_front :: metrics.coverage_max: 6.77 -> 6.5
photo/region_blobs.png @ 80mm/hat_front :: metrics.coverage_p50: 2.71 -> 2.7
photo/region_blobs.png @ 80mm/hat_front :: metrics.coverage_p95: 4.61 -> 4.03
photo/region_blobs.png @ 80mm/hat_front :: metrics.ground_area_frac: 0.502 -> 0.639
photo/region_blobs.png @ 80mm/hat_front :: metrics.ground_span_frac: 0.992 -> 0.99
photo/region_blobs.png @ 80mm/hat_front :: metrics.raw_score: -86 -> -8
photo/region_blobs.png @ 80mm/hat_front :: metrics.stitch_count: 18845 -> 16193
photo/region_blobs.png @ 80mm/hat_front :: metrics.thread_worst_delta_e: 11.5 -> 12.2
photo/region_blobs.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 3186.0 -> 3620.6
photo/region_blobs.png @ 80mm/left_chest :: findings: ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn']
photo/region_blobs.png @ 80mm/left_chest :: metrics.color_changes: 16 -> 11
photo/region_blobs.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 3882.0 -> 3886.0
photo/region_blobs.png @ 80mm/left_chest :: metrics.coverage_max: 6.62 -> 6.02
photo/region_blobs.png @ 80mm/left_chest :: metrics.coverage_p50: 2.71 -> 2.7
photo/region_blobs.png @ 80mm/left_chest :: metrics.coverage_p95: 4.43 -> 3.92
photo/region_blobs.png @ 80mm/left_chest :: metrics.ground_area_frac: 0.502 -> 0.639
photo/region_blobs.png @ 80mm/left_chest :: metrics.ground_span_frac: 0.992 -> 0.99
photo/region_blobs.png @ 80mm/left_chest :: metrics.raw_score: -86 -> -8
photo/region_blobs.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.035 -> 0.036
photo/region_blobs.png @ 80mm/left_chest :: metrics.stitch_count: 18884 -> 16058
photo/region_blobs.png @ 80mm/left_chest :: metrics.thread_worst_delta_e: 11.5 -> 12.2
photo/region_blobs.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 3187.2 -> 3619.9
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 6723.0 -> 6561.0
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.coverage_max: 5.43 -> 4.9
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.coverage_p50: 2.68 -> 2.67
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.coverage_p95: 3.8 -> 3.59
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.ground_area_frac: 0.516 -> 0.515
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.ground_span_frac: 0.683 -> 0.674
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.026 -> 0.028
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.402 -> 0.4
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.006 -> 0.004
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.satin_steps: 1923 -> 1888
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.stitch_count: 23663 -> 21407
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.trims_per_1000: 0.8 -> 1.0
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 6098.2 -> 6561.0
photo/repro_gradient_white_icon.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.5 -> 81.0
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 6720.0 -> 6561.0
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.coverage_max: 4.92 -> 6.94
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.coverage_p95: 3.62 -> 4.12
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.ground_area_frac: 0.516 -> 0.515
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.ground_span_frac: 0.683 -> 0.674
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.401 -> 0.4
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.006 -> 0.004
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.satin_steps: 1923 -> 1888
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.stitch_count: 23407 -> 22741
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.thread_worst_delta_e: 13.0 -> 12.8
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.trims_per_1000: 0.8 -> 1.0
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 6095.5 -> 6561.0
photo/repro_gradient_white_icon.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.8 -> 81.0
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: score: 0 -> 22
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'THREAD_MATCH_POOR:block', 'TRIM_HEAVY:warn']
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.color_changes: 12 -> 11
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.coverage_area_mm2: 1697.0 -> 1653.0
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.coverage_max: 7.17 -> 6.58
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.coverage_p50: 1.94 -> 1.85
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.coverage_p95: 3.66 -> 3.27
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.ground_area_frac: 0.46 -> 0.484
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.legibility: 0.562 -> 0.469
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.legibility_readable: 4 -> 3
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.link_segments: 1 -> 4
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.link_thread_mm: 0.5 -> 1.6
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.raw_score: -44 -> 22
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.same_hole_fraction: 0.109 -> 0.107
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.satin_advance_mm: 0.431 -> 0.442
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.satin_short_fraction: 0.342 -> 0.229
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.satin_steps: 2761 -> 2496
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.stitch_count: 8961 -> 7897
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.thread_worst_delta_e: 44.4 -> 16.9
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.trims_per_1000: 9.3 -> 8.5
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 390.0 -> 945.9
photo/screenshot_phone_ui_golke.jpg @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.2 -> 0.9
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: score: 0 -> 10
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: findings: ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'TRIM_HEAVY:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'TRIM_HEAVY:warn']
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.color_changes: 12 -> 11
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.coverage_area_mm2: 1612.0 -> 1604.0
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.coverage_max: 6.32 -> 7.19
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.coverage_p50: 1.82 -> 1.83
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.coverage_p95: 3.71 -> 3.39
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.ground_area_frac: 0.46 -> 0.484
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.legibility: 0.5 -> 0.55
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.legibility_readable: 4 -> 3
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.link_segments: 1 -> 3
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.link_thread_mm: 0.3 -> 1.1
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.raw_score: -44 -> 10
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.same_hole_fraction: 0.104 -> 0.105
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.satin_advance_mm: 0.416 -> 0.44
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.satin_short_fraction: 0.412 -> 0.357
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.satin_steps: 2636 -> 2509
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.stitch_count: 8356 -> 7934
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.thread_worst_delta_e: 44.4 -> 16.9
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.trims_per_1000: 8.4 -> 7.8
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 388.0 -> 942.9
photo/screenshot_phone_ui_golke.jpg @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.5 -> 0.9
photo/summit_badge.png @ 80mm/hat_front :: findings: ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STABILIZER_CUTAWAY:info', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn']
photo/summit_badge.png @ 80mm/hat_front :: metrics.color_changes: 11 -> 13
photo/summit_badge.png @ 80mm/hat_front :: metrics.coverage_area_mm2: 5002.0 -> 4989.0
photo/summit_badge.png @ 80mm/hat_front :: metrics.coverage_max: 6.68 -> 6.81
photo/summit_badge.png @ 80mm/hat_front :: metrics.coverage_p50: 2.69 -> 2.7
photo/summit_badge.png @ 80mm/hat_front :: metrics.coverage_p95: 4.81 -> 4.82
photo/summit_badge.png @ 80mm/hat_front :: metrics.ground_span_frac: 0.968 -> 0.969
photo/summit_badge.png @ 80mm/hat_front :: metrics.legibility: 0.33 -> 0.037
photo/summit_badge.png @ 80mm/hat_front :: metrics.legibility_worst: 0.154 -> 0.0
photo/summit_badge.png @ 80mm/hat_front :: metrics.link_segments: 1 -> 0
photo/summit_badge.png @ 80mm/hat_front :: metrics.link_thread_mm: 0.4 -> 0.0
photo/summit_badge.png @ 80mm/hat_front :: metrics.raw_score: -116 -> -122
photo/summit_badge.png @ 80mm/hat_front :: metrics.same_hole_fraction: 0.044 -> 0.039
photo/summit_badge.png @ 80mm/hat_front :: metrics.satin_advance_mm: 0.416 -> 0.446
photo/summit_badge.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.384 -> 0.243
photo/summit_badge.png @ 80mm/hat_front :: metrics.satin_steps: 713 -> 687
photo/summit_badge.png @ 80mm/hat_front :: metrics.stitch_count: 23495 -> 25602
photo/summit_badge.png @ 80mm/hat_front :: metrics.thread_worst_delta_e: 12.5 -> 21.5
photo/summit_badge.png @ 80mm/hat_front :: metrics.trims_per_1000: 1.7 -> 2.2
photo/summit_badge.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 4262.0 -> 4650.8
photo/summit_badge.png @ 80mm/hat_front :: metrics.uncovered_worst_mm2: 0.0 -> 0.4
photo/summit_badge.png @ 80mm/left_chest :: findings: ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn'] -> ['COLOR_STOPS_HEAVY:warn', 'GROUND_SEWN:block', 'LETTERING_ILLEGIBLE:warn', 'LETTERING_TOO_SMALL:warn', 'STABILIZER_CUTAWAY:info', 'STITCHES_TOO_SHORT:warn', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:block', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn', 'THREAD_MATCH_POOR:warn']
photo/summit_badge.png @ 80mm/left_chest :: metrics.color_changes: 11 -> 13
photo/summit_badge.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 4974.0 -> 4967.0
photo/summit_badge.png @ 80mm/left_chest :: metrics.coverage_max: 7.25 -> 6.29
photo/summit_badge.png @ 80mm/left_chest :: metrics.coverage_p50: 2.69 -> 2.7
photo/summit_badge.png @ 80mm/left_chest :: metrics.coverage_p95: 4.62 -> 4.55
photo/summit_badge.png @ 80mm/left_chest :: metrics.ground_span_frac: 0.968 -> 0.969
photo/summit_badge.png @ 80mm/left_chest :: metrics.legibility: 0.325 -> 0.188
photo/summit_badge.png @ 80mm/left_chest :: metrics.legibility_worst: 0.143 -> 0.0
photo/summit_badge.png @ 80mm/left_chest :: metrics.link_segments: 2 -> 1
photo/summit_badge.png @ 80mm/left_chest :: metrics.link_thread_mm: 0.9 -> 0.4
photo/summit_badge.png @ 80mm/left_chest :: metrics.raw_score: -116 -> -134
photo/summit_badge.png @ 80mm/left_chest :: metrics.same_hole_fraction: 0.044 -> 0.038
photo/summit_badge.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.417 -> 0.45
photo/summit_badge.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.42 -> 0.293
photo/summit_badge.png @ 80mm/left_chest :: metrics.satin_steps: 722 -> 690
photo/summit_badge.png @ 80mm/left_chest :: metrics.stitch_count: 23831 -> 25496
photo/summit_badge.png @ 80mm/left_chest :: metrics.thread_worst_delta_e: 12.5 -> 21.5
photo/summit_badge.png @ 80mm/left_chest :: metrics.trims_per_1000: 1.6 -> 1.9
photo/summit_badge.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 4252.0 -> 4638.1
photo/summit_badge.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.4
ribbon_curve.png @ 80mm/hat_front :: metrics.coverage_max: 2.58 -> 2.59
ribbon_curve.png @ 80mm/hat_front :: metrics.coverage_p95: 2.54 -> 2.53
ribbon_curve.png @ 80mm/hat_front :: metrics.satin_short_fraction: 0.011 -> 0.009
ribbon_curve.png @ 80mm/hat_front :: metrics.satin_steps: 473 -> 469
ribbon_curve.png @ 80mm/hat_front :: metrics.stitch_count: 995 -> 991
ribbon_curve.png @ 80mm/hat_front :: metrics.uncovered_wanted_mm2: 123.5 -> 236.1
ribbon_curve.png @ 80mm/left_chest :: metrics.coverage_area_mm2: 342.0 -> 343.0
ribbon_curve.png @ 80mm/left_chest :: metrics.coverage_max: 2.59 -> 2.58
ribbon_curve.png @ 80mm/left_chest :: metrics.coverage_p50: 2.03 -> 2.05
ribbon_curve.png @ 80mm/left_chest :: metrics.coverage_p95: 2.55 -> 2.53
ribbon_curve.png @ 80mm/left_chest :: metrics.satin_advance_mm: 0.4 -> 0.401
ribbon_curve.png @ 80mm/left_chest :: metrics.satin_short_fraction: 0.017 -> 0.009
ribbon_curve.png @ 80mm/left_chest :: metrics.satin_steps: 475 -> 469
ribbon_curve.png @ 80mm/left_chest :: metrics.uncovered_wanted_mm2: 124.5 -> 235.5
ribbon_curve.png @ 80mm/left_chest :: metrics.uncovered_worst_mm2: 0.0 -> 0.1
```
