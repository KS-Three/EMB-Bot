# Artwork fidelity — a metric that needs no professional reference (2026-08-26)

**What landed:** `digitizer/tools/artfidelity_self.py`, `artfidelity_tune.py`,
and a fifth CI job. **What is NOT settled:** the composite's weights, which are
provisional until a human ranking has been checked against them.

---

## 0. Why

Two instruments existed, and neither asks the customer's question.

| instrument | asks |
|---|---|
| `digitizer_core/preflight.py` | does the plan obey machine rules — density, trims, stitch length |
| `tools/pro_parity/scorecard.py` | do our stitches match **this one professional's** stitches |

Nothing compared thread to the picture the customer handed us. A grep of
`digitizer_core/`, `tools/`, `app/src/` and `src/` for any render-vs-source
comparison returned nothing. `tools/pro_parity/artfidelity.py` computes
`art_iou`, but only for the **pro's** files, as a ceiling instrument.

That matters because `pro-parity-real-art-2026-08-15.md` §5 already measured the
similarity-to-a-pro instrument as **anti-correlated with visual quality** on its
own corpus: `gaulke_roofing_lc` scores 79.8 for an illegible smear and 52.9 for
a clean readable wordmark. And ROADMAP phase 1's exit condition is *"the
metric's ranking agrees with Kent's visual ranking"* — a condition no existing
instrument was built to meet.

An artwork-fidelity metric also has a property the pro-parity harness cannot
have: **it needs no reference**, so the corpus problem disappears. The
pro corpus is 23 designs on Kent's machine behind a Drive copy that corrupts
binaries in transit; the tonal corpus is gitignored and machine-bound. Any
artwork is a test case for this one, and CI can run it.

## 1. The instrument

Three scored components plus one diagnostic. Every constant is either imported
from an existing measured one or is a raster resolution shared with the sibling
probe — **no new physical constant is introduced**, so ROADMAP gate 1 is not
touched.

- **coverage** — binary ink IoU after ±4 mm shift registration. Uses
  `artfidelity.art_mask` and `artfidelity.best_iou` by **import**, so this
  number is directly comparable to the pro-side `art_iou` figures already
  published.
- **colour** — median CIEDE2000 **excess over the best spool in the chart**,
  across the eroded overlap. Raw distance was tried first and is wrong: the
  chart is 398 discrete cones, so a flawless engine reads 0.56 on
  `logo_whitebg` purely for the chart being finite. This repo already made and
  fixed that exact mistake once — MASTER_SCOPE live defect 12, 2026-08-24, a
  capped cone list that "guarantees per-thread distance, so `THREAD_MATCH_POOR`
  fired on every job". Zero point is `preflight.DELTA_E_CLEARLY_DIFFERENT`
  (10.0).
- **structure** — multi-scale SSIM on luminance. The term that sees *mush*.
- **legibility** — tesseract on render vs artwork. **Deliberately outside the
  composite**: the binary is absent on Kent's Windows box and present on CI, so
  a composite that included it would move depending on whether tesseract was
  installed, making a CI baseline meaningless.

Two guards decide whether a row means anything, and a flagged row is **printed,
never averaged**.

## 2. Measured — 14 tracked fixtures, Windows, `PipelineConfig()` defaults

Deterministic: two independent runs produced byte-identical JSON.

```
fixture                        class          pf |  cover colour struct |  ARTFID
logo_whitebg.png               flat         A100 |  0.927  1.000  0.887 |    93.1
logo_alpha.png                 flat         A100 |  0.927  1.000  0.892 |    93.3
becker_marine_logo.png         flat         B 76 |  0.805  1.000  0.763 |    83.9
logo_script_tires.png          photo_scene  B 88 |  0.824  1.000  0.805 |    86.1
ribbon_curve.png               flat         A100 |  0.805  1.000  0.932 |    89.8
bg_uncertain.png               flat         B 88 |  0.979  1.000  0.941 |    97.1
enthusiast_logo.png            flat         B 88 |  0.662  1.000  0.774 |    78.6
drone_render.png               gradient     F  0 |  0.895  0.415  0.631 |    68.2  INK_AMBIGUOUS
logo_bridge_bar.jpg            gradient     F  0 |  0.963  0.802  0.830 |    87.6  INK_AMBIGUOUS
logo_gaulke_roofing.png        gradient     F  0 |  0.055  0.000  0.195 |     9.0  SUBJECT_MISMATCH(5.1x)
logo_golden_tee.jpg            gradient     F  0 |  0.723  0.397  0.825 |    67.8  INK_AMBIGUOUS
logo_hotel_fremont.webp        gradient     C 64 |  0.984  1.000  0.840 |    93.8  INK_AMBIGUOUS
summit_badge.png               gradient     F  0 |  0.748  0.786  0.559 |    69.1
region_blobs.png               gradient     F  0 |  0.443  0.625  0.492 |    50.6

mean ARTFID 82.4  over 9 TRUSTWORTHY of 14
```

### 2a. Preflight's grade carries little information about how a design looks

The five fixtures preflight grades **F/0** span **9.0 to 87.6** on artwork
fidelity. `logo_hotel_fremont` is graded **C/64** and is the second-best-looking
output in the set (0.984 coverage). `enthusiast_logo` is graded **B/88** and has
the worst coverage of any trustworthy row (0.662) — its wordmark is visibly
mush.

That is not a preflight defect. Preflight checks machine rules and never
receives the artwork except for the thread-match check; it was never built to
answer this. But it is the number the *product* shows a user, so the two should
not be read as the same kind of claim.

### 2b. `colour` is solved on flat art and is not solved on tonal art

1.000 on every flat fixture — consistent with the standing finding that
stage-4's re-snap sits "within ~1 dE00 of best-possible on nearly every shape".
It separates hard on the gradient lane (0.415 / 0.397 / 0.625 / 0.786), which is
where its weight is earned.

## 3. Two findings that are about the FIXTURES, not the engine

**`photo/logo_drone_thermal_badge.png` is byte-identical to
`photo/drone_render.png`** (md5 `adb0a79f25ff43a54c77957cc03e1bef`, both files).
Two fixture names, one image. Any measurement quoted over "both" is one
measurement, and any mean including both double-weights that design. Dropped
from `FIXTURES` with the md5 recorded inline.

**`photo/logo_gaulke_roofing.png` breaks `art_mask`, and the 9.0 above is an
INSTRUMENT artifact, not an engine result.** The file is a screenshot: a white
logo band inside a large black letterbox. `art_mask`'s opaque-art branch calls
every dark pixel ink, so it takes the whole black frame as the artwork (2.16:1
tall) while stage 1 correctly finds the white band (0.43:1 wide). Coverage
between those two rasters reads 0.055 for an engine that did the right thing.

`ink_is_ambiguous` does not catch this and structurally cannot: it inspects only
pixels the mask already calls ink, and the letterbox is uniformly dark, so no
light population is present inside it and the test comes back clean. It catches
the mirror case (dark panel, light knockout) — which is exactly the four
`INK_AMBIGUOUS` rows above.

So `_subject_mismatch` was added: compare `art_mask`'s aspect against the
**engine's own** `design_size_mm` aspect. When the two sizing rules disagree,
the mask and the engine are not looking at the same picture and no component on
that row means anything. Unflagged fixtures all sit under 1.05; gaulke reads
5.08; the tolerance is 1.15.

**This is worth flagging beyond this tool.** `pro-parity-real-art-2026-08-15.md`
§3 records `gaulke_roofing_*` as the worst `art_iou` in the corpus (0.34/0.36)
and attributes it to the pro re-composing the layout. That attribution may be
partly right, but the committed fixture is a letterboxed screenshot, and the
same mask feeds `artfidelity.py`. **Whether the published 0.34 is measuring the
pro's re-composition or the letterbox has not been separated.** It should be,
before that number is quoted again.

## 4. What is NOT established

- **The composite weights (0.40 / 0.25 / 0.35) are judgement, not
  measurement.** The instrument is only as good as its agreement with Kent's
  eye, and that ranking pass has not been done. Until it has, read the three
  components, not `ARTFID`. This repo has already paid for an unvalidated
  weight: `scorecard.py` spends 20 points on `direction`, whose pro-vs-pro
  ceiling is 0.11 on one pair.
- **Every number here is from a Windows box.** No baseline is committed, and one
  must not be captured here — goldens are re-captured on Linux, never Windows.
  The CI job is report-only until a Linux run supplies the reference.
- **`--max-drop 2.0` is uncalibrated.** Chosen to be obviously larger than
  platform numerics and obviously smaller than a regression, with no
  cross-platform measurement behind it.
- **The legibility column has never run on this machine** — no tesseract. CI is
  the only place it is exercised.
- **Nothing has been sewn.** Unchanged, and unchanged by this work.

## 4b. What a sweep actually costs, and the OpenCV threading trap

Measured on Kent's box (8 cores), one fixture at a time, `cv2.setNumThreads(1)`:

```
logo_whitebg.png             7.3s      photo/enthusiast_logo.png    12.2s
logo_alpha.png               5.5s      photo/region_blobs.png       19.6s
becker_marine_logo.png       5.4s      photo/summit_badge.png       57.8s
ribbon_curve.png             4.6s      logo_script_tires.png        77.8s
bg_uncertain.png             6.3s
```

**Two fixtures are 69% of the cost of the whole trustworthy set** — 136 s of
197 s. `logo_script_tires.png` is the expensive one *because* stage 0 misroutes
it to `photo_scene`: a flat 80 mm logo paying 77.8 s of single-thread pipeline
for a lane it should never enter. The misroute is already a known defect; that
it also costs 14× a correctly-routed logo of the same size was not recorded.

**The threading trap, hit and fixed.** The first parallel sweep ran 6 worker
processes without pinning OpenCV, so each spawned threads across all 8 cores:
48 threads on 8 cores, ~840 s of CPU burned on work that takes 292 s serially,
and the baseline never finished. `_eval_one` now calls `cv2.setNumThreads(1)`
before importing the pipeline. **The CI workflow already records this exact
mechanism from the other side** — "GitHub's standard runners are 2-core, so
`-n auto` gets two workers and OpenCV's threading competes with them" — so this
was a documented trap walked into anyway, which is worth noting for the next
person: the note lives in a CI comment, not anywhere a tools author reads.

Consequence for method: the search runs over the **fast seven** and any winner
is then re-scored on the full trustworthy nine. Tuning on the full set is an
overnight job on this hardware, not a within-session one. The subset is
flat-lane-weighted, and flat-lane `colour` is already saturated at 1.000, so a
subset-tuned result is biased toward coverage and structure — state that
whenever one is quoted.

## 5. The tuner

`tools/artfidelity_tune.py` — coordinate descent over `PipelineConfig`, scored
by mean ARTFID across trustworthy fixtures. **It never writes `config.py`**; it
prints proposals.

The gates are enforced in code, not in a comment. The search space is an
allowlist (13 parameters, each carrying a written reason it is not a physical
constant); `DENIED` records 10 more with the ruling that excludes each
(`min_detail_mm` and `overlap_mm` as gate-1 territory, `simplify_tol_mm` as a
closed investigation, the SAM2 pair as a standing ruling, and so on); and
`chain_links` / `split_tonal_regions` / `contour_fill` are refused outright
under gate 3. Passing anything off-list is an error, not a widened search.

Purpose is not the optimum. It is that a metric computed from the artwork alone
turns tuning from one-threshold-per-session into a search — and that whatever it
proposes arrives as a hypothesis with a measurement attached, for a human to
argue with.

## 6. First search result — ONE parameter, and it is `bg_tolerance_lab`

46 evaluations over the fast seven, 736 s. Proposal: `merge_delta_e` 6.0→3.0,
`aa_iterations` 2→0, `bg_tolerance_lab` 6.0→4.5, `min_px_per_mm` 4.0→3.0.

**Re-scored on the full trustworthy nine**, including the two the search never
saw:

```
                                   mean ARTFID   art_missed   ours_extra
shipped defaults                       82.40        0.119        0.102
bg_tolerance_lab 6.0->4.5 ONLY         86.68        0.046        0.101
all four proposed                      86.80        0.047        0.099
the other three, WITHOUT bg            82.52        0.120        0.100
```

**`bg_tolerance_lab` alone is +4.28 of the +4.40. The other three together are
+0.12 — noise.** Coordinate descent kept them because it keeps anything above
zero; the isolation arm is what separates a result from an artifact, and it
should be run on every proposal this tool ever makes.

**It is not the metric being gamed.** `art_missed` falls 0.119 → 0.046 while
`ours_extra` is flat (0.102 → 0.101): the engine covers artwork it was
previously leaving bare, without spilling more thread onto ground the artwork
does not ask for. A metric-gaming move would raise both.

Per-fixture, the gain is concentrated in the gradient lane, where the
background detector was eating artwork:

```
region_blobs.png     50.6 -> 69.2   coverage 0.443 -> 0.844
summit_badge.png     69.1 -> 89.9   coverage 0.748 -> 0.993   (HELD OUT)
```

The held-out pair moved **+10.25** mean against +4.40 overall, so this is not
overfit to the seven it was tuned on.

**`summit_badge` is worth its own line.** MASTER_SCOPE records it as F/0 at both
corpus-scorecard configs and **SATURATED**, with the standing instruction to
judge any fix on `thread_worst_delta_e` because the score cannot discriminate.
This instrument discriminates on it — 69.1 → 89.9 — which is the first
independent evidence that the reference-free metric sees things the existing
harness structurally cannot.

### What this proposal costs, and why it is NOT applied here

- **It changes flat-lane output**, so it breaks byte-identical goldens.
  `logo_whitebg` moves 93.1 → 92.8 (a small *loss*). Any application needs a
  golden re-capture, on Linux, under the same-failure-set discipline.
- **`colour` drops slightly** (0.935 → 0.905 overall; `region_blobs`
  0.625 → 0.331). Newly-sewn regions are matched worse than the ones already
  sewn. That is a real tradeoff, not a rounding artifact.
- **The metric's weights are still unvalidated.** A +4.28 on an instrument
  whose 0.40/0.25/0.35 nobody has checked against Kent's eye is a hypothesis.
  The ranking pass has to land first.
- **`aa_iterations` 2→0 deserves suspicion if it is ever revisited.** Turning
  off anti-alias correction makes our output resemble artwork that still
  carries the encoder's soft edges — a way this metric could reward the wrong
  thing. It measured +0.01 here, so nothing rests on it, but the mechanism is
  the kind that would not announce itself.

---

## Addendum, 2026-09-01 — what changed between writing this and landing it

This document and `tools/artfidelity_tune.py` were written on 2026-08-26 and
then stranded: the scorer half of that work reached `main`, the tuner and this
doc did not, and sat on an unmerged local branch until 2026-09-01. Everything
above is left as written. Three things drifted underneath it:

1. **The scorer's API was renamed on its way in.** `score_one` is now
   `score_image`, `_resolve` takes a LIST of names, and the per-row verdict is
   `refusal is None` rather than a `trustworthy` bool. The tuner is adapted at
   its two call sites; prose above that names `score_one` is describing the
   same function under its old name.

2. **`GATE3_FLAGS` named a field that has never existed.** It listed
   `contour_fill`; `PipelineConfig` carries no such attribute, so ROADMAP
   gate 3's refusal for the contour tier fenced nothing. Contour is a VALUE of
   `fill_technique` (default `"tatami"`), so the field itself is refused now.
   `tests/test_artfidelity_tune.py` pins every name in `TUNABLE`, `DENIED` and
   `GATE3_FLAGS` to a real dataclass field, and was watched go red against the
   old name before the fix landed.

3. **The `bg_tolerance_lab` proposal in §6 is still NOT applied, and is now
   older than the engine it was measured on.** #291, #293 and #301 have since
   changed sequencing and re-snap behaviour. Re-measure before quoting it; the
   caveats it shipped with (a fit to one metric whose weights are unvalidated
   against Kent's eye, on a flat-lane-weighted subset) are unchanged.
