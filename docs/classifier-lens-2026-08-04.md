# Classifier lens — measuring stage 0's routing surface (2026-08-04)

Status: **measured, instrument-only, zero engine change.** M0-style pass on
`digitizer_core/stage0_classify.py` in the mold of
`docs/superpowers/plans/2026-08-04-m0-shape-lens-measurement.md`: build the
instrument, run it over everything committed, adjudicate ground truth,
report where the decision surface is thin — and create the evidence a
threshold change would need, without making one. The stakes grew with the
photo lanes: the SLIC/RAG region-former and the tonal tiers hang off this
router, so stage 0 now decides which *entire pipeline* a customer's art gets.

## The instrument

`digitizer/tools/classify_lens.py` (+ its own tests,
`digitizer/tests/test_classify_lens.py`, 12 passing — they pin the lens,
not the engine). For every image in `testdata/` and `testdata/photo/` it
prints one row: the three raw signals, every threshold the classifier
consults, the resulting class + confidence, and the nearest value of each
signal at which the FINAL verdict would change (distance-to-flip, demotion
band included). `--sweep` varies each of the 7 documented constants ±50%
and reports which fixtures flip class where. `--dir` points it at any local
art folder — that's the corpus leg (below).

Measurement-independence stance, adapted from `shape_lens.py`'s house rule:
the **signals are computed by the engine itself** (`classify()` is called
and its `signals` dict read back) — deliberate, because the subject here is
the *decision surface*, i.e. where the engine's own signals sit against its
own thresholds; second-implementation signals would measure a different
instrument. What IS re-derived independently is the **decision**: the lens
rebuilds the threshold tree from the module's documented constants,
parameterized for sweeping, and hard-errors unless it reproduces the
engine's class and confidence exactly on every fixture at nominal (the
self-check passed on all 12).

One non-obvious thing the flip analysis models that a naive
`|signal − threshold|` misses: `CONFIDENCE_FLOOR` (0.55) creates a
**demotion band** around every threshold — |value − t| < 0.1·margin puts the
weakest gate's confidence under the floor and collapses any would-be
non-flat class to `flat` + `CLASSIFICATION_UNCERTAIN`. So e.g. the ucm axis
has a `flat` buffer strip (0.272, 0.288) *between* gradient territory and
photo territory: a drifting signal degrades to the safe default before it
ever misroutes to a photo lane. That is a good property, and it is measured
below, not assumed.

## The signal table (measured, this container, seed 0)

```
fixture                                   ucm   grad_var  alpha  class           conf flr  ucm flips to                   grad_var flips to                  warnings
---------------------------------------------------------------------------------------------------------------------------------------------------------------------
bg_uncertain.png                       0.0030     0.0011  0.000  flat            0.77   .  photo_scene@0.288 (d=+0.285)   gradient@0.00158 (d=+0.000507)     -
logo_alpha.png                         0.0088     0.0001  0.006  flat            1.00   .  photo_scene@0.288 (d=+0.279)   gradient@0.00158 (d=+0.00152)      -
logo_whitebg.png                       0.0049     0.0006  0.000  flat            1.00   .  photo_scene@0.288 (d=+0.283)   gradient@0.00158 (d=+0.00102)      -
ribbon_curve.png                       0.0041     0.0000  0.000  flat            1.00   .  photo_scene@0.288 (d=+0.284)   gradient@0.00158 (d=+0.00155)      -
photo/drone_render.png                 0.1592     4.4635  0.008  gradient        1.00   .  flat@0.272 (d=+0.113)          flat@0.00158 (d=-4.46)             CLASSIFIED_GRADIENT
photo/enthusiast_logo.png              0.0000     0.0000  0.019  flat            1.00   .  photo_scene@0.288 (d=+0.288)   gradient@0.00158 (d=+0.00158)      -
photo/gradient_ramp_linear.png         0.0000     0.0387  0.000  gradient        1.00   .  flat@0.272 (d=+0.272)          flat@0.00158 (d=-0.0371)           CLASSIFIED_GRADIENT
photo/gradient_ramp_radial.png         0.0024     0.0050  0.000  gradient        1.00   .  flat@0.272 (d=+0.27)           flat@0.00158 (d=-0.00347)          CLASSIFIED_GRADIENT
photo/photo_scene_stub.png             0.4256     0.6613  0.000  photo_scene     1.00   .  flat@0.288 (d=-0.138)          flat@7.7 (d=+7.04)                 CLASSIFIED_PHOTO_SCENE
photo/photo_subject_stub.png           0.7547   184.2003  0.000  photo_subject   1.00   .  flat@0.288 (d=-0.467)          flat@8.3 (d=-176)                  CLASSIFIED_PHOTO_SUBJECT
photo/region_blobs.png                 0.0342     0.1867  0.000  gradient        1.00   .  flat@0.272 (d=+0.238)          flat@0.00158 (d=-0.185)            CLASSIFIED_GRADIENT
photo/repro_gradient_white_icon.png    0.0002     0.0118  0.000  gradient        1.00   .  flat@0.272 (d=+0.272)          flat@0.00158 (d=-0.0102)           CLASSIFIED_GRADIENT
```

Thresholds consulted (read live from the module, never hardcoded in the
lens): `UCM_PHOTO_MIN 0.28` (margin 0.08), `GRAD_VAR_GRADIENT_MIN 0.0015`
(margin 0.0008), `GRAD_VAR_SUBJECT_MIN 8.0` (margin 3.0),
`CONFIDENCE_FLOOR 0.55`. `alpha_softness` is carried in `signals` but the
tree never consults it — measured ≤ 0.019 on all 12 fixtures, i.e.
currently a vestigial signal exactly as the module docstring says (both
real fixtures read hard-edged regardless of class).

## Ground truth, adjudicated per fixture

Class definitions are the plan doc's
(`docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md`): these
are **pipeline routings**, not art-historical labels — `gradient` means
"decompose ramps into 3–5 thread shades via the blend tier", `photo_*`
means "SLIC/RAG region-former + (future) subject/scene handling".
Adjudicating "what should this be" means "which pipeline serves this art",
not "what would a curator call it".

| fixture | adjudicated | reasoning |
|---|---|---|
| `logo_whitebg.png` | flat | Synthetic spot-color shapes (circles/rects), the flat-lane golden. Signals near zero. |
| `logo_alpha.png` | flat | Same design, alpha encoding. |
| `ribbon_curve.png` | flat | One solid red curved stroke. |
| `bg_uncertain.png` | flat | Solid navy rectangle with a slot — unambiguous spot color. Note below: it is the corpus's nearest-to-flip flat fixture. |
| `photo/enthusiast_logo.png` | flat | Kent's real two-color production logo; the flattest thing measured (0.0000 on both axes). |
| `photo/drone_render.png` | **gradient** | The hard case — reasoning below. |
| `photo/gradient_ramp_linear.png` | gradient | Synthetic linear ramp, generated by `make_gradient_fixture.py` for exactly this class. |
| `photo/gradient_ramp_radial.png` | gradient | Synthetic radial ramp, same provenance. |
| `photo/photo_scene_stub.png` | photo_scene | By construction (plan doc: "low-freq gradient + texture raster" scene stand-in). |
| `photo/photo_subject_stub.png` | photo_subject | By construction: per-pixel noise raster standing in for photographic subject texture. |
| `photo/region_blobs.png` | gradient | See note below — the interesting one nobody warned about. |
| `photo/repro_gradient_white_icon.png` | gradient | The Instagram-style gradient icon; committed as the gradient-tier's own repro fixture. |

**`drone_render.png` — engaging with the documented reasoning, not
assuming it's wrong.** Semantically this is a photographic render with a
subject; a naive read of the class names says `photo_subject`, and the
COOKBOOK flags the `gradient` verdict as a known quirk. Measured, the
routing holds up as *deliberate and correct under the routing definition*:

- `unique_color_mass` 0.159 means a 16-color quantize holds together on
  ~84% of its pixel neighborhoods — the art is smooth bands, metallic
  ramps, and glow halos, not per-pixel photographic texture. That is
  precisely the blend tier's operating assumption (few shades + ramps),
  and this file is the founding-complaint art that tier was built for.
  Routing it to `photo_subject` today would hand it to a lane whose own
  warning says "handling isn't built yet, results will be low quality."
- The COOKBOOK's warning is confirmed to the digit: `gradient_smoothness`
  reads 4.46 — *seven times rougher* than the synthetic photo_scene stub
  (0.66). Any re-tune that promoted `gradient_smoothness` to the
  photo/non-photo gate would misroute this fixture; `unique_color_mass`
  is the only measured signal that separates it from photo territory,
  exactly as the module docstring argues.
- Robustness: ucm sits 0.113 below the demotion band (43% of threshold) —
  and en route to photo territory it would pass through the `flat` +
  `CLASSIFICATION_UNCERTAIN` buffer first, not silently flip lanes.

Honest caveat: this adjudication is conditional on today's pipeline. If the
photo lanes mature to where they'd genuinely out-sew the blend tier on this
art, the right answer could change — that re-litigation needs sew-out
evidence, and this lens will show exactly what any re-tune breaks.

**`region_blobs.png` — a corpus gap the lens surfaced.** The fixture built
*for* the SLIC/RAG photo segmenter routes to `gradient` (ucm 0.034 — a
16-color quantize holds almost everywhere on smooth Gaussian blobs). This
is not a live misroute: `test_stage2_photo_segment.py` drives the segmenter
directly, bypassing stage 0, and as pure synthetic blend art `gradient` is
the right routing for what it *is*. But it means **no committed fixture
reaches the photo lanes through stage 0 except the two synthetic stubs** —
the lanes with the most new code hanging off this router have the least
realistic routing evidence. Fixing that wants real portrait/pet/scene
fixtures (the plan doc already schedules them for step 3+), not a
threshold move.

## Confusion table — current classifier vs. adjudicated truth

12/12 agree. **Zero misroutes on the committed corpus.**

| | adj. flat | adj. gradient | adj. photo_subject | adj. photo_scene |
|---|---|---|---|---|
| **classified flat** | 5 | 0 | 0 | 0 |
| **classified gradient** | 0 | 5 | 0 | 0 |
| **classified photo_subject** | 0 | 0 | 1 | 0 |
| **classified photo_scene** | 0 | 0 | 0 | 1 |

## Sensitivity — the ±50% sweep (measured)

```
ucm_photo_min (nominal 0.28):
  photo/drone_render.png     gradient -> photo_scene  at x0.50 (0.14)
  photo/drone_render.png     gradient -> flat         at x0.55 (0.154)
  photo/photo_scene_stub.png photo_scene -> flat      at x1.50 (0.42)
ucm_margin (0.08):            no flips anywhere in the range
grad_gradient_min (0.0015):
  bg_uncertain.png           flat -> gradient         for x0.50..x0.65 (0.00075..0.000975)
grad_gradient_margin (0.0008): no flips
grad_subject_min (8.0):        no flips
grad_subject_margin (3.0):     no flips
confidence_floor (0.55):       no flips
```

Combined with the exact per-fixture flip points, the safe windows are:

- **`UCM_PHOTO_MIN` — safe in ≈ (0.167, 0.418)**, bounded below by
  drone_render (0.1592 + demotion band 0.008) and above by
  photo_scene_stub (0.4256 − 0.008). Nominal 0.28 sits near the center of
  its window — the max-headroom placement. Every move inside ±40% flips
  nothing; the first casualties in each direction are exactly the two
  fixtures the module docstring says the gate was tuned on.
- **`GRAD_VAR_GRADIENT_MIN` — safe in ≈ (0.00115, 0.00494)**, bounded
  below by `bg_uncertain.png` (grad_var 0.00107 — lowering the threshold
  ≤35% misroutes a solid navy rectangle to the gradient lane) and above by
  `gradient_ramp_radial.png` (0.0050). Nominal 0.0015 sits in the lower
  third of the window. **This is the thinnest live margin in the whole
  map: bg_uncertain sits only 0.0005 (32% headroom) below the effective
  flip point.** Why a solid rectangle reads nonzero at all is worth one
  sentence: its antialiased edge ramp spans a few pixels, and windows
  adjacent to the Canny-dilated exclusion zone retain partial gradient
  magnitude (hypothesis from the mechanism, not separately measured).
  Also note the demoted-confidence tell: bg_uncertain is the only fixture
  not at conf 1.00 (0.77).
- **`GRAD_VAR_SUBJECT_MIN` — essentially unconstrained** by this corpus:
  the only two photo-territory fixtures sit at 0.66 and 184.2, a 280×
  spread, and 8.0 could move an order of magnitude either way without a
  flip. This gate has never met a hard case. Treat its placement as
  provisional until real portrait/scene art exists.
- **Margins and `CONFIDENCE_FLOOR`**: no flips at ±50% — no fixture's
  confidence sits near the floor except bg_uncertain (0.77, still 0.22
  clear). The floor's demotion bands are narrow (±0.008 ucm, ±0.00008
  grad_var at nominal margins) but real, and the flip columns show them
  functioning as a safe-default buffer on the ucm axis.

## Does a safe single-threshold fix exist? — the finding

**No fix is needed, and none is motivated: the classifier is 12/12 against
adjudicated truth on everything committed.** The sweep shows every
single-threshold move within ±50% either changes nothing or *creates* a
misroute (drone_render off its deliberate lane, scene_stub demoted to
flat, bg_uncertain into the gradient lane). The COOKBOOK's known quirk —
drone_render as `gradient` — adjudicates as correct routing under the
plan's own class definitions, not as a defect this pass should have found a
threshold for. The deliverable is therefore the map itself: the safe
windows above are what any future re-tune (e.g. when real photo art
arrives in step 3+) must be measured against, and the two named boundary
fixtures on each constrained axis are the regression canaries.

## Honest limits

- **A dozen fixtures is not a corpus.** Two are real production art (both
  Kent's, both non-photo); photo territory is populated by exactly two
  synthetic stubs engineered to be easy. The subject/scene gate in
  particular is unconstrained evidence-free space (280× spread between its
  only two data points).
- **The local-only leg.** `scratch_corpus/` is professional *stitch files*
  (DST), not source art, so it cannot feed this instrument — the real-art
  leg here is Kent's local folders (`scratch_kent/`, the Reference Art
  directory, real customer uploads). The tool grew a `--dir` flag for
  exactly this: `PYTHONPATH=. .venv/Scripts/python tools/classify_lens.py
  --sweep --dir <path-to-real-art>` run locally and handed back would turn
  the safe windows above from 12-fixture claims into corpus claims — the
  same shape as M0's still-blocked corpus leg.
- **Environment sensitivity.** Signals were measured in this container;
  the suite's 3 known golden failures (COOKBOOK "Running things") already
  demonstrate small numeric drift between environments in this stack.
  Every routing verdict here has ≥30% signal headroom, so drift at the
  third decimal cannot flip any committed fixture — but quote the signal
  values as this-container measurements, not universal constants.
- **Nothing here is sew-out evidence.** This measures routing only; whether
  the blend tier actually out-sews the photo lanes on drone-class art is a
  sew-out question, explicitly out of scope per the M0 discipline.

## Verification

- Baseline (this container, before any change): 458 passed, 3 failed —
  the exact 3 pre-existing golden failures COOKBOOK documents
  (`test_flat_lane_byte_identical` logo_alpha, `test_pushcomp`
  logo_whitebg-towel, `test_stage2_photo_segment` logo_alpha).
- After (instrument + tests + this doc only): 470 passed, same 3 failed —
  zero new failures, +12 from the lens's own tests. No engine file
  touched; `git diff --stat` shows only `tools/classify_lens.py`,
  `tests/test_classify_lens.py`, and this document.
