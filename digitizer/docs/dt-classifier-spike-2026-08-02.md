# The DT classifier, measured

*A spike against `docs/dt-first-architecture-2026-08-01.md` §3: build Goldman's
distance-transform classifier, run it beside ours on every shape we have, and
find out whether DT-first would change a decision this engine currently makes
badly.*

Instrument: `digitizer/tools/shape_lens.py`. Nothing is wired into the
pipeline. `188 passed` before and after — the diff is tool + doc only.

---

## 0. The verdict, up front

**Yes, it changes a decision we make badly, and the decision is on the
benchmark logo.** But almost none of the benefit comes from where the note
says it does, and the note's own spec, transcribed faithfully, is worse than
what we ship.

Three results, in descending order of how much they should change what we do:

1. **We sew a 10.6 × 9.4 mm block as satin, and whether we do depends on the
   file format.** `logo_alpha.png` and `logo_whitebg.png` are the same logo.
   Its orange and purple blocks vectorize to `2*area/perimeter` = **4.9972 mm**
   on one and **5.0327 mm** on the other, against a 5.0 mm cap. The alpha
   version therefore sews them as **three satin columns, 361 stitch points**;
   the white-background version sews **one tatami fill, 190 points**. The
   satin render is a diagonal starburst overshooting the outline on all four
   sides. A DT term kills it on both: `dt_max` = **9.50 mm**, `dt_p90` =
   **9.10 mm**, `sigma/mu` = **0.568** — wide by any DT statistic, and
   irregular by Goldman's.

2. **`max(DT)` is not a width on a letterform, and the note's rule is built on
   `max(DT)`.** At the crossbar of a serif `t` the inscribed circle is
   `sqrt(2)` times the stroke, so `dt_max` reads **5.67 mm** on a glyph whose
   strokes are **3.64 mm**. The note's R2 (`2*max <= cap`) rejects **four of
   the eight** serif glyphs in `serif_text` and sends them to fill — which is
   the expensive error direction, a lumpy scribble in lettering. The 90th
   percentile strips the junction spike exactly (`dt_p90` **4.75 mm** on the
   same `t`) and keeps every glyph.

3. **Goldman's variance test is not a taper detector, which is the one job the
   note credits it with.** For a linear taper `a -> b` the DT at skeletal
   pixels is uniform on `[a/2, b/2]`, so `2*sigma < mu` reduces to
   `b < (2+sqrt(3))^2 * a` — **regular up to a 13.9:1 taper**. Measured on
   rasters it gives up at about **9.4:1**. A ribbon that fattens from 1 mm to
   8 mm over 30 mm passes Goldman's regularity test cleanly.

The smallest change that captures the benefit is **two extra AND terms on the
rule we already ship** — not a restructure, and not a new width statistic.

---

## 1. What was built

`tools/shape_lens.py`, an instrument, with its own rasteriser and its own
statistics. The independence is deliberate: `stage6_satin._rasterize` chooses
its resolution from `ribbon_width_mm(poly)`, and measuring the DT on a grid
whose resolution is a function of the statistic under test would be circular.
`mask_of` uses a fixed 20 px/mm with a 1400 px cap and knows nothing about
width.

```
dt_stats(mask, scale) -> max, mu, sigma, median, p10, p90 of the exact EDT
                         sampled at medial-axis pixels (rng=0), radii in px
```

Ten rule arms, all scored on identical inputs:

| arm | rule |
|---|---|
| `ribbon` | **what we ship.** `2*area/P <= cap` AND `perimeter/2 - w >= 3w` |
| `R1` | `2*sigma < mu` AND `2*mu <= cap` (sibling patent US6397120B1, no max term) |
| `R2` | `2*sigma < mu` AND `mu > max/2` AND `2*max <= cap` (the note's spec) |
| `R2n` | R2 with `mu > max/2` ablated — the note's stated open question |
| `R3` | `med > 2*(p90-p10)` AND `2*max <= cap` (order-statistic variant) |
| `MIN` | `ribbon` AND `2*max <= cap` |
| `MIN2` | `MIN` AND `2*sigma < mu` |
| `VAR` | `ribbon` AND `2*sigma < mu` |
| `P90` | `ribbon` AND `2*p90 <= cap` |
| **`VP90`** | **`ribbon` AND `2*sigma < mu` AND `2*p90 <= cap`** |

The last four are **pure tightenings**: they only ever turn a satin call into
a fill call. That matters more than the accuracy number, because it means no
shape that sews correctly today can start sewing worse.

Populations: 21 synthetic fixtures with a stated truth (the five `test_satin.py`
archetypes plus the shapes this spike exists for), and 28 real regions from
seven artworks through the engine's own stages 1-4.

---

## 2. Three corrections to the note, each measured

### 2.1 The endpoint trim is wrong, and it costs 4.65x

The note specifies `trim_endpoints(skel, k=int(round(dist[skel].max())))`.
Measured across all 21 fixtures at `k` = 0, 3, 8 and max-radius, **every arm
gets monotonically worse as the trim grows**:

| trim | `R2` wrong | `R1` wrong | what flipped |
|---|---|---|---|
| **0** | **1/21** | **3/21** | — |
| 3 | 2/21 | 4/21 | `SQUARE 4x4` irregular -> regular |
| 8 | 2/21 | 5/21 | `SQUARE 8x8` too |
| max-radius | 2/21 | 3/21 | see below |

The mechanism is structural, not a tuning miss: the peel removes **low-DT**
skeletal pixels, and low DT *is* the evidence that a shape is not of uniform
thickness. On an 18 mm blob with a 2 mm tail, the max-radius trim (179 px)
deletes the blob's entire skeleton and leaves the tail — `sigma` collapses
**45.6 -> 0.0 px** and the verdict flips fill -> satin. The trim converts the
one shape class it most needs to catch into a clean false positive.

It is also the single most expensive line in the pass: 6 regions at 20 px/mm,
**921.8 ms at trim 0 against 4285.6 ms at max-radius**, because it is an
iterative peel with `k` full-array passes.

`dt_stats` therefore defaults to `trim=0`, and `trim_endpoints` is kept only
for the ablation.

### 2.2 `mu > max/2` never changes a verdict

The note names this as the open question between the two patent readings.
Across all 49 shapes, **`R2` and `R2n` return identical verdicts on every
one**. Whenever `2*sigma < mu` holds, `mu > max/2` holds too. The term is
redundant given the variance test, and the ablation is settled: drop it.

### 2.3 The variance test does not reject tapers

`shape_lens.py taper` sweeps a 30 mm wedge from 1:1 to 50:1:

| b/a | wide end | `sigma/mu` | `2s<m` | `ribbon` | `VAR` | `P90` |
|---|---|---|---|---|---|---|
| 4 | 4.0 mm | 0.386 | regular | satin | satin | satin |
| 6 | 6.0 mm | 0.450 | regular | satin | satin | **fill** |
| 8 | 8.0 mm | 0.485 | **regular** | satin | **satin** | fill |
| 10 | 10.0 mm | 0.507 | irregular | satin | fill | fill |
| 12 | 12.0 mm | 0.523 | irregular | **fill** | fill | fill |

The note's §3.3 claims `area/perimeter` "wrongly accepts tapering blobs" that
the DT variance "would fail instantly". The opposite is true: `2*sigma < mu`
calls an **8:1 taper** predominantly regular, and rejects tapers only from
about 9.4:1 — barely ahead of the shipped rule's 12:1. What actually catches
a taper is a **width percentile**, which rejects from 6:1.

---

## 3. The confusion matrix

21 fixtures with a stated truth, satin = positive. FN — fill where satin was
right — is the expensive direction.

| arm | TP | FP | TN | FN | wrong | misses |
|---|---|---|---|---|---|---|
| `ribbon` (shipped) | 9 | 6 | 6 | 0 | **6/21** | WEDGE 1→9, SERRATED ×2, BAR 5.2, SQUARE ×2 |
| `R1` | 9 | 3 | 9 | 0 | 3/21 | WEDGE 1→9, BAR 5.2, DOT |
| `R2` | 9 | 1 | 11 | 0 | 1/21 | DOT r1.5 |
| `R2n` | 9 | 1 | 11 | 0 | 1/21 | DOT r1.5 |
| `R3` | 5 | 1 | 11 | **4** | 5/21 | T_SHAPE, WEDGE ×2, BAR 4.8, DOT |
| `MIN` | 9 | 1 | 11 | 0 | 1/21 | SQUARE 4x4 |
| `MIN2` | 9 | 0 | 12 | 0 | **0/21** | (none) |
| `VAR` | 9 | 2 | 10 | 0 | 2/21 | WEDGE 1→9, BAR 5.2 |
| `P90` | 9 | 1 | 11 | 0 | 1/21 | SQUARE 4x4 |
| **`VP90`** | **9** | **0** | **12** | **0** | **0/21** | **(none)** |

**And this table on its own picks the wrong arm.** `MIN2` scores 0/21 here and
is disqualified by the artwork, because it inherits `MIN`'s `2*max <= cap` and
that term rejects serifs. A confusion matrix with no adjudication is worth
nothing; §4 is the part that decides.

Two structural notes the matrix makes visible:

- **Every DT arm satins `DOT r1.5`** — a 3 mm round dot. A disc's medial axis
  collapses to a 2-pixel centre, so `sigma` is exactly 0 and Goldman's rule
  calls it perfectly regular. **DT regularity cannot tell a disc from a
  ribbon**; both are of uniform thickness. What separates them is length, and
  that is our aspect gate, which no DT arm has. Any arm that keeps the aspect
  gate gets this free.
- `SERRATED disc r10 t1.2` reads `2*area/P` = **1.07 mm** against a true 18 mm
  width. Boundary noise doubles the perimeter and collapses the estimate; the
  DT is unmoved at `dt_max` 17.92. The note is right about this one, and it is
  the strongest argument for the DT existing at all.

---

## 4. Adjudication — where they disagree, and who is right

Renders in `debug_out/shape_lens/` (`ribbon_vs_<arm>__<shape>.png`, DT as a
heat ramp, skeleton overlaid). On real artwork, agreement is:

| arm | agrees with `ribbon` on 28 real regions |
|---|---|
| `R1` | 25/28 |
| `R2`, `R2n` | 21/28 |
| `R3` | 20/28 |
| `MIN`, `MIN2` | 22/28 |
| **`VAR`, `P90`, `VP90`** | **26/28** |

### 4.1 The two disagreements that matter — `ribbon` is wrong

`logo_alpha/Sb253ebba` and `/Sf5200f3f`. Measured directly:

```
bbox 10.63 x 9.43 mm   area 100.24   perim 40.12
2A/P = 4.9972 mm  <= cap 5.0     -> is_satin_candidate = True
aspect: length_est 15.06 >= 3w 14.99   -> True (by 0.07 mm)
DT: max 9.50 mm   p90 9.10 mm   sigma/mu 0.568   -> irregular, wide
```

The same two shapes on `logo_whitebg` read `2A/P` = 5.0327 and go to fill. End
to end, `digitize()` confirms the split: **`Sb253ebba` sews `{'underlay': 6,
'satin': 3}` on alpha and `{'underlay': 2, 'travel': 2, 'fill': 1}` on
whitebg.**

Two things are wrong at once and both are the statistic's fault:

- For a rectangle `w x h`, `2A/P = wh/(w+h)`, which for a near-square is close
  to **half** the true width. It reports 5.03 mm for a shape 9.43 mm wide.
- For a rectangle, `length_est` is **exactly `3w`**. Every square sits on the
  aspect gate's knife edge, so the gate provides no margin at all where it is
  needed most.

The render is not ambiguous: the satin version is a starburst of three columns
crossing a solid block, crosses escaping the outline on all four sides, 361
points against fill's 190.

**Verdict: `ribbon` is wrong, every DT arm is right, and the defect is on the
benchmark.**

### 4.2 The four disagreements where `ribbon` is right — serifs

`serif_text` renders "Fritsch" in a triple-stroke serif face at 80 mm. `MIN`,
`MIN2`, `R2`, `R2n` and `R3` send four of the eight glyphs to fill:

| glyph | `2A/P` | `dt_max` | `dt_p90` | `dt_mu` | `sigma/mu` |
|---|---|---|---|---|---|
| `h` | 3.78 | **5.38** | 4.82 | 3.89 | 0.304 |
| `t` | 3.48 | **5.67** | 4.75 | 3.64 | 0.311 |
| `S59cf8e1f` | 3.76 | **5.50** | 4.84 | 3.88 | 0.273 |
| `S844d92fa` | 3.40 | **5.33** | 4.86 | 3.64 | 0.343 |

The heat maps say exactly where the max comes from: on the `t` it is the
**crossbar junction**, where the inscribed circle is `sqrt(2)` times either
stroke; on the `h` it is the **serif feet**. Neither is a stroke that has to
be crossed by a satin stitch. Filling a serif glyph because one serif foot is
0.38 mm over the cap is the error the note itself names as the more expensive
one.

Our own `T_SHAPE` fixture carries the same signature and nobody had noticed:
3 mm walls, `dt_max` **3.86 mm**, `dt_p90` **3.10 mm**. The junction inflates
`max` by 29 % and `p90` by 3 %.

**Verdict: `ribbon` is right, `max`-based arms are wrong, `p90` is the fix.**

### 4.3 The one where both are arguably wrong

`serif_text/Sb8eac675` — a ~2 x 3 mm fragment, a serif crossbar broken off by
quantization. `ribbon` says fill (aspect gate), `R1`/`R2` say satin. It is
below the sewable-detail floor and belongs in the run tier, which is where
stage 7 already sends shapes under `min_detail_mm^2`. Not a classifier
question.

---

## 5. Cost

`logo_whitebg.png` at 80 mm, 6 regions, best of 5, this machine:

| pass | time | vs stages 1-4 |
|---|---|---|
| stages 1-4 | **1313.1 ms** | — |
| current classify, all 6 regions | **0.473 ms** | 0.036 % |
| DT, ALL regions @ 6 px/mm | 500.7 ms | 38.1 % |
| DT, ALL regions @ 20 px/mm | 914.4 ms | 69.6 % |
| **DT, only regions `ribbon` already accepts @ 6 px/mm** | **78.3 ms** | **6.0 %** |
| DT, only regions `ribbon` already accepts @ 20 px/mm | 86.9 ms | 6.6 % |

The two figures are answers to different questions and the difference is the
whole architectural argument:

- A **real DT-first restructure** computes the field before deciding, so it
  pays on all 6 regions: **38-70 % on top of stages 1-4**. Of those 6, only 1
  currently gets a medial axis in stage 6, so 5 are new work.
- The **add-a-term arms** run only on shapes the current rule already accepted
  — which is exactly the set stage 6 already builds a medial axis for. That
  work is not new, it is work moved earlier, and the **true marginal cost of
  `VP90` is approximately zero**, with `M1`'s hoisted `ShapeField` making it
  exactly zero.

**Resolution sensitivity.** `dt_p90` across 6, 10, 20 and 30 px/mm on all six
benchmark regions: max spread **0.233 mm** (`Sf5200f3f`, 9.33 → 9.10). The
statistic is portable across grids and no verdict in the population is within
0.233 mm of the cap. A cap-threshold rule on `p90` does not need the lens's
20 px/mm; stage 6's own 6 px/mm raster is sufficient.

**Determinism.** Two consecutive full runs of `shape_lens.py dt --ablate` are
byte-identical, 98 lines. `medial_axis(rng=0)` throughout.

---

## 6. What this spike could NOT establish

**The professional corpus is not a usable referee for a per-shape rule, and
`shape_lens.py corpus` prints a banner saying so.** The attempt is documented
because the failure is itself the finding, and because the numbers looked
plausible at two of the three stages.

Three successive defects, each of which produced a confident and wrong
confusion matrix:

1. **Reconstructing the sewn region from stitch centrelines injects the
   serrated-disc failure mode.** Tracing needle-down segments as 1 px lines
   and closing the gaps gives a band serrated at the stitch pitch, whose
   medial axis is a starburst of spurs. `sigma/mu` came back 0.6-1.0 on
   obviously-satin 2 mm leaves and **every variance arm scored 100 % false
   negatives**. Rendering four masks caught it; the matrix alone read like a
   real result. Fixed by stroking each segment at the thread's own width
   (0.4 mm) and simplifying the contour at stage 4's own 0.2 mm.
2. **One needle-down run is not one shape.** Professionals satin a whole word
   without lifting, so `pro=satin` rows came back with `dt_max` of 14, 17 and
   21 mm — the height of the lettering. Partly fixed by dropping segments over
   4 mm as travels and taking every connected component.
3. **In a script face the letters touch.** Rendering three `pro=satin` shapes
   from `bridesman.dst` returns the word "Bridesm" at 38x40, 42x44 and
   55x38 mm as single connected regions. This one cannot be fixed from stitch
   data. Every arm — ours included — is being asked for one verdict on a whole
   word, which is not the operation the digitizer performed.

The population moved 128 → 216 → 301 shapes across those three fixes and the
matrix reordered the arms each time. Numbers that unstable under instrument
changes are not evidence and none are quoted here.

There is a real finding underneath: **for connected script lettering the
per-shape satin/fill question is the wrong question.** Both classifiers are
per-shape. That is gap G2 / step M6 — per-branch classification — and this
population is the argument for it.

Also unproven:

- **No sew-out.** Every judgement here is geometry and rendering. The claim
  that the 9.4 mm block sews better as fill than as three satin columns is
  strongly implied by 361 points against 190 and by crosses escaping the
  outline, but it has not been stitched.
- **The 21 fixture truths are my adjudication**, not a corpus vote. `SQUARE
  4x4 = fill` and `BAR 40x5.2 = fill` are the two most arguable.
- **`p90` is not tuned.** 90 was chosen to sit above the junction spike and
  below a genuinely wide region, and it works on this population unmodified.
  70 (Melco's percentile, US9702070) was not tested. That sweep is cheap and
  should happen before any flip.
- **`SATIN_MAX_WIDTH_MM` is 5.0 here, and `main` was 3.0 when this was written.**
  Every number in this document is at 5.0. **No longer a discrepancy: `main` is
  also 5.0, so these numbers compare directly.** *(confirmed 2026-08-17 —
  `digitizer_core/machine.py:336`)*

---

## 7. Recommendation

**Not a restructure. Two AND terms on `is_satin_candidate`.**

```python
# stage6_satin.py — under cfg.extra["satin_classifier"] = "dt", default off
def is_satin_candidate_dt(poly, max_width_mm, field):
    if not is_satin_candidate(poly, max_width_mm):
        return False                       # unchanged: width, aspect, artwork
    r = field.dist[field.skel]             # exact EDT at medial-axis pixels
    if 2.0 * r.std() >= r.mean():
        return False                       # not of uniform thickness
    return 2.0 * np.percentile(r, 90) / field.scale <= max_width_mm
```

Why this shape and not the note's:

- **Pure tightening.** It cannot produce a fill-where-satin-was-right, so the
  expensive error direction is closed by construction rather than by a score.
- **`p90`, not `max`.** `max` is a junction artefact on every letterform with
  a crossing and on every serif. Measured: it costs four of eight glyphs.
- **The aspect gate stays.** It is the only thing in either rule that
  distinguishes a disc from a ribbon, and every pure-DT arm fails `DOT r1.5`
  without it.
- **`2*area/perimeter` stays too.** What it gets wrong is not the width of a
  ribbon but the recognition that a shape is not a ribbon — and that is
  precisely what `2*sigma < mu` reports.
- **No new pass.** It reads the field stage 6 already builds. Marginal cost
  measured at ~6 % of stages 1-4 as a standalone pass, and ~0 once `M1` hoists
  `ShapeField`.

Scored: **0/21 fixture misses, 26/28 agreement on real artwork, and both
disagreements are shapes we currently sew wrong.**

**Before flipping the default:** sweep `p90` against `p70`/`p80`/`p95`, settle
the 3.0-vs-5.0 cap, and sew out the disagreement set. Corpus agreement cannot
gate this one, for the reasons in §6.

**Do not adopt** from the note as written: the max-radius endpoint trim (§2.1),
the `mu > max/2` term (§2.2), or `2*max <= cap` as the thinness test (§4.2).
The variance term is worth having; the framing around it is not.
