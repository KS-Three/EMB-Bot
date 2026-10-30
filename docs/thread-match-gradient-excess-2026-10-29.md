# THREAD_MATCH_POOR on the gradient lane: re-measured, rescored, priced

MASTER_SCOPE defect 28, 2026-10-29. Kent asked for it to be fixed. Its
numbers were from 2026-09-06/07, so this re-measures them on `origin/main`
44ecf1cb first. Then it builds part 1, the excess yardstick for the gradient
lane, **OFF**, diagnoses gaulke, and prices the clamp floor for Kent without
building it.

**The ruling this runs into:** Kent ruled 2026-09-10 that the gradient lane
stays on raw distance (yardstick-disagreements row 4). His reason was that a
logo's palette can be changed and a photograph's cannot. So the flag ships
OFF, and flipping it means re-making that ruling.

Instrument: the scorecard matrix (`tools/corpus_scorecard.FIXTURES` × `MATRIX`,
26 fixtures × {left_chest, hat_front} at 80 mm = 52 entries), `digitize` then
`run_preflight`, each arm digitized separately. Windows, `-n` none. Read the
grades as advisory (DOCTRINE 2026-09-15). The deltas between arms are exact,
because both arms ran on the same box and the same plan.

## 1. Re-measured: the wall has moved

| | 2026-09-06 | 2026-10-29, raw (shipped) |
|---|---|---|
| fixtures at F 0 | 7 (14 entries) | **5 (10 entries)** |
| F entries carrying a `THREAD_MATCH_POOR` block | 14 | **14** (7 fixtures) |
| `THREAD_MATCH_POOR` blocks, whole matrix | — (40 before the 09-10 patch floor) | **38**, 36 of them gradient |

The seven F fixtures are not the same seven. **Out:** `logo_gaulke_roofing`
is B 76 with no thread finding at all (§3). `region_blobs` routes
`photo_scene` now and is D 46 on `GROUND_SEWN` with no thread finding.
**In:** `gradient_ramp_radial` is F 34 (one block, three warns) and
`logo_hotel_fremont` is F 16 / F 28 (two blocks). Every one is still on the
`gradient` lane.

## 2. Part 1, built OFF: `cfg.thread_match_excess_gradient`

One reader, in `preflight._thread_match_findings`. Set, a design whose traced
class is `gradient` is judged on excess over the best loaded spool, exactly
as the photo route is: the same `len(loaded) > 1` guard, the same offender
pick on `_score`, and `yardstick: "excess"` in the payload. Warns move too,
because the photo route's rescoring moves warns as well. Flat never moves.

**No stitch moves:** all 52 entries are plan-md5 identical OFF and ON, each
arm digitized on its own config. The ON report over the OFF plan is also
identical to the ON report over the ON plan. `tests/test_thread_match_excess_gradient.py`
pins the unit cases, the one-reader rule, and one real fixture.

**Headline, OFF → ON:** F entries carrying a thread block **14 → 4**. Entries
at score 0 **10 → 2**. Thread blocks **38 → 8** (the photo stub's 2 included,
which this flag cannot touch). Grades A/B/C/D/F **6/20/4/8/14 → 10/20/6/12/4**.

**What survives excess, and why it should:**

- `logo_hotel_fremont`, both garments: `0020 Black` at dE **100.0** on
  `S9bac9a3c` (7.34 mm² patch), and `0862 Wild Rice` at 26.7 on `S1b0527a5`.
  Excess equals raw on both. A loaded `0015 White` is that much closer, so
  black thread is sewing art the grader reads as white. That is a real
  reassignment and the finding names it. *(Cause: §2a.)*
- `summit_badge`, both garments: `0111 Whale` shade band at 21.5 raw, excess
  16.9, with `0134` loaded. This is the 10-08 "survives excess" case,
  unchanged. Summit stays F 0 on its other block (`GROUND_SEWN`): raw −146
  → −20.
- `photo_subject_stub`: photo route, `0722 Khaki` 33.7/33.9, with no closer
  loaded spool. This flag does not apply to it.

**The offender set moves with the yardstick.** On every fixture that moves,
all of its thread findings go (blocks and warns), apart from the
survivors above. No fixture gains a block it did not have.

Every entry, 80 mm, both yardsticks (`TMP` = `THREAD_MATCH_POOR` blocks/warns):

| fixture | garment | lane | raw yardstick (OFF) | TMP blk/warn | excess (ON) | TMP blk/warn | raw score OFF -> ON |
|---|---|---|---|---:|---|---:|---:|
| `becker_marine_logo.png` | hat_front | flat | A 100 | 0/0 | A 100 | 0/0 | 100 -> 100 |
| `becker_marine_logo.png` | left_chest | flat | A 100 | 0/0 | A 100 | 0/0 | 100 -> 100 |
| `bg_uncertain.png` | hat_front | flat | B 88 | 0/1 | B 88 | 0/1 | 88 -> 88 |
| `bg_uncertain.png` | left_chest | flat | B 88 | 0/1 | B 88 | 0/1 | 88 -> 88 |
| `logo_alpha.png` | hat_front | flat | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `logo_alpha.png` | left_chest | flat | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `logo_script_tires.png` | hat_front | gradient | A 100 | 0/0 | A 100 | 0/0 | 100 -> 100 |
| `logo_script_tires.png` | left_chest | gradient | A 100 | 0/0 | A 100 | 0/0 | 100 -> 100 |
| `logo_whitebg.png` | hat_front | flat | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `logo_whitebg.png` | left_chest | flat | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `drone_render.png` | hat_front | gradient | F 0 | 3/6 | D 52 **moves** | 0/0 | -110 -> 52 |
| `drone_render.png` | left_chest | gradient | F 0 | 3/6 | D 40 **moves** | 0/0 | -122 -> 40 |
| `enthusiast_logo.png` | hat_front | flat | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `enthusiast_logo.png` | left_chest | flat | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `fur_ramp.png` | hat_front | photo_scene | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `fur_ramp.png` | left_chest | photo_scene | B 88 | 0/0 | B 88 | 0/0 | 88 -> 88 |
| `gradient_ramp_linear.png` | hat_front | gradient | D 46 | 1/2 | A 100 **moves** | 0/0 | 46 -> 100 |
| `gradient_ramp_linear.png` | left_chest | gradient | D 46 | 1/2 | A 100 **moves** | 0/0 | 46 -> 100 |
| `gradient_ramp_radial.png` | hat_front | gradient | F 34 | 1/3 | B 88 **moves** | 0/1 | 34 -> 88 |
| `gradient_ramp_radial.png` | left_chest | gradient | F 34 | 1/3 | B 88 **moves** | 0/1 | 34 -> 88 |
| `logo_bridge_bar.jpg` | hat_front | gradient | F 0 | 6/2 | D 52 **moves** | 0/0 | -152 -> 52 |
| `logo_bridge_bar.jpg` | left_chest | gradient | F 0 | 6/2 | D 52 **moves** | 0/0 | -152 -> 52 |
| `logo_gaulke_roofing.png` | hat_front | gradient | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `logo_gaulke_roofing.png` | left_chest | gradient | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `logo_golden_tee.jpg` | hat_front | gradient | F 0 | 1/6 | C 64 **moves** | 0/0 | -38 -> 64 |
| `logo_golden_tee.jpg` | left_chest | gradient | F 0 | 1/6 | C 64 **moves** | 0/0 | -38 -> 64 |
| `logo_hotel_fremont.webp` | hat_front | gradient | F 28 | 2/0 | F 28 | 2/0 | 28 -> 28 |
| `logo_hotel_fremont.webp` | left_chest | gradient | F 16 | 2/0 | F 16 | 2/0 | 16 -> 16 |
| `photo_chrome_specular.png` | hat_front | photo_scene | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `photo_chrome_specular.png` | left_chest | photo_scene | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `photo_dof_meadow.png` | hat_front | photo_scene | C 64 | 0/0 | C 64 | 0/0 | 64 -> 64 |
| `photo_dof_meadow.png` | left_chest | photo_scene | C 64 | 0/0 | C 64 | 0/0 | 64 -> 64 |
| `photo_grass_macro.png` | hat_front | photo_subject | D 58 | 0/0 | D 58 | 0/0 | 58 -> 58 |
| `photo_grass_macro.png` | left_chest | photo_subject | D 46 | 0/0 | D 46 | 0/0 | 46 -> 46 |
| `photo_owl_pale.png` | hat_front | photo_scene | D 58 | 0/0 | D 58 | 0/0 | 58 -> 58 |
| `photo_owl_pale.png` | left_chest | photo_scene | D 58 | 0/0 | D 58 | 0/0 | 58 -> 58 |
| `photo_scene_stub.png` | hat_front | photo_scene | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `photo_scene_stub.png` | left_chest | photo_scene | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `photo_subject_stub.png` | hat_front | photo_subject | C 70 | 1/0 | C 70 | 1/0 | 70 -> 70 |
| `photo_subject_stub.png` | left_chest | photo_subject | C 70 | 1/0 | C 70 | 1/0 | 70 -> 70 |
| `photo_sunset_backlit.png` | hat_front | photo_scene | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `photo_sunset_backlit.png` | left_chest | photo_scene | B 76 | 0/0 | B 76 | 0/0 | 76 -> 76 |
| `region_blobs.png` | hat_front | photo_scene | D 46 | 0/0 | D 46 | 0/0 | 46 -> 46 |
| `region_blobs.png` | left_chest | photo_scene | D 46 | 0/0 | D 46 | 0/0 | 46 -> 46 |
| `repro_gradient_white_icon.png` | hat_front | gradient | B 76 | 0/2 | A 100 **moves** | 0/0 | 76 -> 100 |
| `repro_gradient_white_icon.png` | left_chest | gradient | B 76 | 0/2 | A 100 **moves** | 0/0 | 76 -> 100 |
| `screenshot_phone_ui_golke.jpg` | hat_front | gradient | F 0 | 2/0 | D 52 **moves** | 0/0 | -8 -> 52 |
| `screenshot_phone_ui_golke.jpg` | left_chest | gradient | F 0 | 2/0 | D 52 **moves** | 0/0 | -8 -> 52 |
| `summit_badge.png` | hat_front | gradient | F 0 | 2/8 | F 0 | 1/0 | -146 -> -20 |
| `summit_badge.png` | left_chest | gradient | F 0 | 2/8 | F 0 | 1/0 | -146 -> -20 |
| `ribbon_curve.png` | hat_front | flat | A 100 | 0/0 | A 100 | 0/0 | 100 -> 100 |
| `ribbon_curve.png` | left_chest | flat | A 100 | 0/0 | A 100 | 0/0 | 100 -> 100 |


### 2a. Fremont's surviving block

Both regions are small and both are judged against art the grader reads as
pure `255,255,255`: `S9bac9a3c` (7.71 mm², sewn `0020 Black`) and
`S1b0527a5` (6.06 mm², sewn `0862 Wild Rice`). They are not the dark-ink
flags. On left_chest, with `dark_ink_bean` OFF, and with that plus
`keep_dark_thin_strokes` OFF, the same two blocks appear at the same dE,
while the grade moves F 16 → F 4 on other findings. **Cause not
established.** It is a separate question from the yardstick: excess gets this
one right whichever way the flag is set. Listed as a follow-up.

### 2b. Cross-check: `tools/spool_remedy.py --yardstick`

This ran first, on its 09-06 list (left_chest). Six of seven clear every block
under excess and `summit_badge` holds one (`0111`). The other five agree with
the matrix block for block: drone 3, screenshot 2, golden_tee 1, bridge 6,
summit 2 → 1. **The run also found a bug in the tool.** It reported gaulke
`0015 White` at **33.9 BLOCK** and region_blobs `3770 Oyster` 10.6 BLOCK, and
the scorecard carries neither. The tool graded a plain `prep(art, cfg)`, while
`run_preflight` grades through `_two_tone_view` on the traced class's grid. So
it was re-judging gaulke's anti-alias grey, the very thing §3 describes.
Region_blobs is a photo-route design the tool scores without knowing its
route. Fixed with this change (`spool_remedy.graded_view`, pinned in the test
file). `F_WALL` is now today's seven.

__SPOOL2__

## 3. Gaulke: it no longer fails, and the "unexplained seventh" was explained

On main today `logo_gaulke_roofing` is **B 76 on both garments**. It has no
`THREAD_MATCH_POOR` finding under either yardstick. It loads exactly the two
inks the art has (`0015 White`, `0020 Black`) and carries only
`LETTERING_TOO_SMALL` and `STITCHES_TOO_SHORT` warns. Its 2026-09-07 entry,
"unexplained, worst dE 63.6", never caught up with two diagnoses made after it:

1. **The 63.6 itself** was `3971 Silver` on `Se6eddd27`, a 0.58 mm² shard.
   DOCTRINE named the cause the same day: stage 4's re-snap took the median
   of a bimodal pixel pool (103 near-black + 65 near-white) and the grader
   took the eroded core. Two masks gave 52.2 dE00 apart on one polygon.
   `resnap_mask_matches_grader` fixed it, and the 5.0 mm² patch floor means
   a 0.58 mm² shard can no longer judge anyway. Both have been ON since
   2026-09-10.
2. **The block after that** was `0015 White` at **33.9** on `Saba1ec0a`. It is
   the same failure in the grader. `two_tone.keep_lines` widens the thin roof
   lines to the satin floor, and the grader judged them against the
   anti-alias grey under them (median 126). The pixels are bimodal again:
   34% have L* < 30 and 32% have L* > 80. Fixed 2026-10-08 (c2161d9c): the
   grader reads the two-tone raster the pipeline sewed. **Reproduced
   today:** scoring today's plan against the plain re-read instead of
   `_two_tone_view` brings back exactly `0015 White` 33.9 on `Saba1ec0a`
   (14.94 mm² footprint), and `3971 Silver` would be the chart-wide best at
   9.3.

Ablation, left_chest, both yardsticks: today's engine B 76; `two_tone_snap`
OFF, B 76; that plus `resnap_mask_matches_grader` and
`revalidate_small_shapes` OFF, B 76. None of these arms has a thread finding.
**Read the cone list, not the grade** (DOCTRINE): with `two_tone_snap` OFF
gaulke loads only `0020 Black`. Its White finding is gone because the cone
is gone, not because anything was cured.

**So both of gaulke's thread blocks were the same instrument failure: a median
over a bimodal pixel pool.** It hit stage 4 first and the grader second. Neither
was a thread problem in the design. Gaulke leaves defect 28.

## 4. The clamp floor, priced — Kent's call, NOT built

`score = max(0, 100 − 30·blocks − 12·warns)`, bands A ≥ 90, B ≥ 75, C ≥ 60,
D ≥ 40, else F. `metrics.raw_score` has carried the unclamped value since
2026-09-06.

Floored today (raw arm): **10 of 52 entries**, unclamped −152 to −8.

| fixture | raw score | points to D | ≈ blocks to clear |
|---|---:|---:|---:|
| `logo_bridge_bar` ×2 | −152 | 192 | 7 |
| `summit_badge` ×2 | −146 | 186 | 7 |
| `drone_render` left / hat | −122 / −110 | 162 / 150 | 6 / 5 |
| `logo_golden_tee` ×2 | −38 | 78 | 3 |
| `screenshot_phone_ui_golke` ×2 | −8 | 48 | 2 |

With `thread_match_excess_gradient` ON the floor holds **2** entries
(`summit_badge`, raw −20). On this corpus most of the floor is the raw
yardstick.

| option | letters that move (of 52) | what changes | catch |
|---|---:|---|---|
| **A. Keep the clamp** (today) | 0 | nothing; `raw_score` already rides in `metrics` | `corpus_scorecard.diff` reads it only after the next baseline recapture (`_metric_deltas` intersects keys) |
| B. Print the raw score | 0 | the 10 floored entries show −152…−8 | an operator sees negative scores; every stored baseline re-bases |
| C. Saturating curve `100·e^(−D/65.5)` (F/D edge kept at two blocks) | **12** | the floored 10 spread to 2–19 inside F | **every** design with findings re-bases: two warns B 76 → C 69 (gaulke, chrome, scene, sunset, repro), dof_meadow C 64 → D 58 |

**Pick: A.** B moves no letter and only puts the number the scorecard
already records in front of the operator. C costs 12 letter moves on designs
nobody is asking about, to rank designs that all mean "do not sew". If the
excess flag flips, the floor shrinks to 2 entries and the question mostly
goes away.

## Reproduce

Scratch scripts, not committed. The matrix is `tools/corpus_scorecard`'s
FIXTURES × MATRIX through `digitize` and `run_preflight`, per arm. The F-wall
cross-check is `python -m tools.spool_remedy --yardstick`. The gaulke rows
are `_region_color_errors` over plain `prep()` against `_two_tone_view`.

