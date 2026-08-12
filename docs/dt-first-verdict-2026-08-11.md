# DT-first classifier: the verdict

*2026-08-11, `probe/dt-first-classifier` lane. Closes the masters teardown's
one open structural item: does making the satin/fill call FROM the distance
transform (Goldman/SoftSight step 408, rule of record `2σ < μ < max/2` at
skeletal pixels) beat the classifier we ship?*

**Verdict up front: MIXED — negative on the classifier swap, positive on one
narrow floor.** The DT-first satin/fill call is never right where it
disagrees with the shipped classifier on this corpus — every satin-vs-fill
disagreement adjudicates in the shipped rule's favour, and the rule as
printed in the patent is unshippable outright. But the probe surfaced one
real, previously uncounted defect class the DT sees and the shipped ladder
cannot: **19 of 162 corpus regions (11.7%) sew today as sub-millimetre
satin** — Law 31 violations ("under 1 mm: convert to multi-ply run") — and a
run-tier floor read off numbers the shipped classifier ALREADY computes
catches all 19 at zero marginal cost. That floor, not an architecture
rewrite, is the shippable remainder of the DT-first thesis.

Instrument: `digitizer/tools/dt_first_probe.py` (standalone; imports
`shape_lens`'s rasteriser/statistics; nothing imported by the pipeline).
Population: every stitched region the current pipeline produces on the 14
committed `testdata/` fixtures — the same corpus `tools/corpus_scorecard.py`
scores, benchmark `photo/enthusiast_logo.png` and the fixture logo included —
at 80 mm, cap `SATIN_MAX_WIDTH_MM = 5.0`. 162 regions. Gallery renders (DT
heat + skeleton | shipped choice sewn | DT choice sewn, one PNG per
disagreement): `debug_out/dt_first_probe/` (131 files, regenerable with
`--render`); machine-readable dump `debug_out/dt_first_probe/probe.json`.

---

## 1. What was compared

**Shipped** (three-way, stage 7's auto ladder, predicates verbatim, on the
ARTWORK polygon): run if `area < min_detail_mm²`; else satin if
`is_satin_candidate` — which since `satin-classifier-organic-shapes` landed
is `2A/P ≤ cap` AND aspect ≥ 3:1 AND the internal DT tightening
(`_dt_regular_and_within_cap`: `2σ < μ` AND `2·p90 ≤ cap` — the spike's VP90
arm); else fill.

**Three DT-first arms**, all three-way, DT statistics at medial-axis pixels
on a fixed 20 px/mm grid (trim 0 — the spike's measured correction), run
tier = `2·max ≤ 1.0 mm` (Law 31's floor as a DT read):

| arm | satin iff | provenance |
|---|---|---|
| `goldman_printed` | `2σ<μ` AND `μ<max/2` AND `2·max≤cap` | the rule of record, as printed |
| `goldman_bench` | `2σ<μ` AND `μ>max/2` AND `2·max≤cap` | the architecture note's corrected spec (spike R2) |
| `dt_var_p90` | `2σ<μ` AND `2·p90≤cap` | the closeout's "only terms worth shipping", standing alone — no ribbon width, no aspect gate |

## 2. Confusion matrices — shipped (rows) vs arm (columns), 162 regions

Shipped tier mix: 83 satin / 51 fill / 28 run.

```
goldman_printed  (agree  79/162)      goldman_bench  (agree 137/162)      dt_var_p90  (agree 139/162)
         run  satin  fill                      run  satin  fill                    run  satin  fill
run       26      0     2             run       26      0     2           run      26      0     2
satin     19      2    62             satin     19     60     4           satin    19     62     2
fill       0      0    51             fill       0      0    51           fill      0      0    51
```

Two structural facts before any adjudication:

- **`fill→satin` is zero in every arm.** The DT-first arms never promote a
  shipped-fill region to satin on this corpus — the shipped classifier's
  satin set is already DT-tightened (VP90 landed inside
  `is_satin_candidate`), so pure DT-first has no tightening left to
  contribute; what remains unique to it is only the *loosening* (no ribbon
  width, no aspect gate), and no fixture region happened to probe it. The
  spike's `DOT r1.5` result stands as the standing counterexample: pure DT
  regularity cannot tell a disc from a ribbon, and only the aspect gate
  catches it. This population never adversarially tested that gate; the
  synthetic one did, and DT-first lost there.
- **The rule as printed is unshippable.** `goldman_printed` keeps 2 of the 83
  shipped satins and sends 62 clean ribbons to fill — all-FN, the expensive
  direction. A uniform ribbon has μ ≈ max, so `μ < max/2` fails on exactly
  the shapes satin exists for. This reconfirms, on real artwork, the
  transcription defect §1.7 of the architecture note flagged; the printed
  middle term is inverted and the teardown's "rule of record" cannot be
  implemented as written. Clean negative; the item is closed.

## 3. Adjudication — every disagreement judged by the physics laws

Judge rules, in severity order (mechanical; `judge()` in the probe): satin
dies on p90 width > 8 mm (snag ceiling) or > 5 mm (cap), on rendered crosses
escaping the outline, or on a compact blob (skeleton < 2× mean width); fill
dies where `poly.buffer(-0.6)` is empty (no room for one row,
`MIN_FILL_WIDTH_MM`); satin-vs-run is decided NON-CIRCULARLY on the median
of the crosses the satin choice actually emits (Law 31's 1.0 mm floor) —
the engine's own geometry, not the lens statistic that produced the verdict.

| arm | DT right | shipped right | tossup |
|---|---|---|---|
| `goldman_printed` | 19 | **64** | 0 |
| `goldman_bench` | 19 | **6** | 0 |
| `dt_var_p90` | 19 | **4** | 0 |

### 3.1 The satin/fill call: shipped wins every disagreement

Every `satin→fill` and `run→fill` disagreement adjudicated shipped-right:

- `goldman_bench`'s four `satin→fill` are the spike's serif-crossbar failure
  reproduced on the corpus: `max`-based terms reject real thin-stroke shapes
  at junctions. The clearest render is `summit_badge/S25e8f264` (an ice-axe
  glyph: 50.5 mm of 1.2 mm-wide stroke) — max radius spikes to 1.63 mm where
  the head crosses the shaft, `μ > max/2` fails, and the arm sends a
  perfect satin ribbon to single-row tatami. Gallery:
  `debug_out/dt_first_probe/goldman_bench__summit_badge_S25e8f264.png`.
- `dt_var_p90`'s two `satin→fill` (`repro_gradient_white_icon/S73134226`,
  `drone_render/S473606e7`) are knife-edge variance reads: σ/μ = 0.5025 and
  0.5089 at the lens's 20 px/mm against the 0.5 threshold, where the shipped
  classifier's own internal DT check (6+ px/mm adaptive raster) reads the
  same shapes as regular. The variance term is resolution-sensitive within
  ~1% of its threshold; that is a reason to keep it as a tiebreaker inside a
  wider rule (as shipped) rather than as the rule.
- Both `run→fill` (`Sdf9f8b3c` on both logo fixtures, 0.98–1.02 mm²) are
  below the detail floor and cannot hold a single fill row; the shipped run
  rescue is right.

**On the satin-vs-fill question, DT-first contributes nothing here that the
already-landed VP90 tightening did not: zero corrected errors, six
introduced ones (four of them the FN direction the closeout named as the
expensive one).** This is the same shape of result as the 2026-08-02
closeout (VP90 NOT_SOUND at cap 3.0; "if a term ships, it is the variance
term") — the variance term did ship, inside `is_satin_candidate`, and the
rest of the DT-first rule remains a net negative.

### 3.2 The one thing DT-first found: there is no width floor under satin

All 19 `satin→run` disagreements — shared by all three arms, since the run
floor is Law 31 applied to the DT, not part of Goldman's rule — adjudicated
DT-right. 15 in `photo/drone_render.png`, 4 in `photo/summit_badge.png`; all
photo-class, none in the flat fixtures.

The shipped ladder has exactly one route to the run tier: `area <
min_detail_mm² = 2.25 mm²`. A LONG sub-millimetre sliver (artwork p90 widths
here: 0.50–0.94 mm; areas 2.3–10.5 mm²) sails over the area floor, passes
`is_satin_candidate` (it is, after all, a perfectly regular ribbon), and
sews as satin with sub-millimetre crosses. Measured off the REAL end-to-end
plans (the machine sews the stage-5 pull-compensated polygon, so the probe's
artwork-geometry renders were re-verified against realized output — see the
probe docstring's scope caveat):

- 12 of 19 sew with median realized crosses **0.50–0.97 mm** — under Law
  31's floor even after pull compensation fattens them (e.g.
  `drone_render/Se861074f` median 0.56 mm, `S60de6f78` median 0.50 mm —
  thread-width zigzag, snag/perforation territory).
- The remaining 7 clear 1.0 mm only BECAUSE compensation more than doubles
  thread-width artwork (`summit_badge/S0a881283`: 0.64 mm artwork sewn as
  1.89 mm crosses — comp added 1.2 mm to a stroke narrower than the
  addition). That is itself the defect stage 7's own run-tier comment names:
  "a run does not pull fabric and compensation would fatten a thread-width
  stroke past its own letterform".

Either way the pro answer for all 19 is the run tier (multi-ply/bean run on
the artwork outline), which is precisely what the DT run floor voted.

## 4. The narrowest shippable integration

**Not M2/M3. Not a classifier swap. One floor, using numbers the shipped
classifier already computes.** `_dt_regular_and_within_cap` already builds
the `ShapeField` (M1 infrastructure) and already holds `r` and `p90` for
every shape that reaches it. The proposal:

> In stage 7's ladder, when a shape passes `is_satin_candidate` but its DT
> width floor fails — `2·p90/scale < ~1.0 mm` — route it to the run tier
> (`run_outline` on the artwork polygon, exactly the existing rescue path)
> instead of satin.

- **Measured expected impact:** flips 19/162 corpus regions (11.7%) from
  sub-millimetre satin to outline run; 15 on `drone_render`, 4 on
  `summit_badge`. Zero flips on the five flat-lane fixtures at 80 mm —
  measured, not guaranteed by construction, so the flat byte-identical
  suites still gate the landing.
- **Marginal cost ≈ 0:** the field and the percentile are already computed
  in that code path for every satin candidate; the floor is one comparison.
- **Error direction is safe-by-physics, not safe-by-subset:** it converts
  thread-width satin (snag/break/perforation risk, Law 31) into the same
  bean-run treatment the area rescue already gives shapes of this scale. It
  cannot touch any shape wider than ~1 mm at p90.
- **The floor constant should be settled with the cap's own method:** 1.0 mm
  is Law 31's number; `SATIN_MIN_CROSS_MM = 0.5` is the emitter's clamp;
  the honest landing sweeps 0.8/1.0/1.2 against the corpus scorecard and —
  per this repo's standing rule for classifier-visible changes — a sew-out
  of a handful of the 19 before the default flips. (2026-08-02's closeout
  is the cautionary precedent for skipping that step.)

## 5. What this closes and what stays open

- **Closed, negative:** the Goldman DT-statistics classifier — printed OR
  corrected — as a replacement for the shipped satin/fill call. The printed
  rule inverts on uniform ribbons (79/162 agreement, 62 all-FN); the
  corrected arms lose every satin/fill disagreement they create (junction
  spikes for `max`-terms, threshold-edge instability for the bare variance
  pair). The teardown's "ordering, not algorithms" thesis survives only as
  M1 (the field hoist, already merged) and the VP90 terms (already inside
  `is_satin_candidate`); the *decision* itself stays where it is.
- **Closed, positive:** the DT found the missing width floor under the satin
  tier (§3.2), and the fix needs no new architecture.
- **Still open, unchanged:** the 37-file `scratch_corpus/` referee run
  (gitignored, never locally available) that M2/M3 was formally gated on —
  moot for the swap now (the swap is dead on fixture evidence alone), still
  the right gate if anyone reopens it; and the sew-out for the run-floor
  landing.

Repro: `PYTHONPATH=. .venv/Scripts/python tools/dt_first_probe.py --render
--json ../debug_out/dt_first_probe/probe.json` from `digitizer/`
(deterministic; `medial_axis(rng=0)` throughout; full run ≈ 3 min including
renders).
