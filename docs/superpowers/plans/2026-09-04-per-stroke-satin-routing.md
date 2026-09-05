# Per-stroke satin routing — the measured gap, and where the split belongs

**Date:** 2026-09-04
**Status:** decision document. Nothing built. Two of the seven questions below
already have measured answers, and one of them contradicts the framing this
plan was commissioned under.
**Instrument this plan proposes:** `digitizer/tools/satin_columns.py`

## The gap

An independent audit against the professional's own files for the same logos
measured the share of emitted stitches lying inside a sustained zigzag column:
Becker 1.8% against the pro's 42.8%, Gaulke 5.3% against 76.3%, Fremont 25.2%
against 51.1%. Our median column runs 0.80–0.84 mm against the pro's
1.40–2.52. Preflight agrees from the other side — Gaulke reports
`STITCHES_TOO_SHORT` at 74% of satin stitches under the 1 mm needle minimum
(`preflight.py`, "a healthy plan runs about 10%").

The Becker half was reproduced exactly. `becker_marine_logo.png` at 100 mm:
17 regions, 3,588 mm², 11,373 stitches; 3 regions earn satin over 274 mm²;
the 14 rejections are `dt_irregular` (9) and `dt_p90_cap` (5).

## 1. Where the split goes — inside the classifier, not above the ladder

`satin_shape` (`stage6_satin.py`) **already** decomposes and sews per stroke:
it calls `extract_strokes`, loops per stroke, gives each its own underlay and
column, and walks the unsewn skeleton web between them (`_build_travel_graph`).
Nothing needs building there.

What is whole-region is the *decision*. `classify_ribbon` pools the distance
transform over the entire region's skeleton (`_dt_stats`) and returns one
bool, which `stage7_sequence.stitch_one` consults once per region. A branchy
letterform — wide at junctions, thin along its arms — fails `2σ < μ` as a unit.

**Recommendation: put the rung inside `classify_ribbon`, behind a config flag,
and change no emitter.** Splitting regions into stroke sub-shapes above the
ladder would create N shape ids per letter, re-run stage 5 per piece, churn
`match_and_carry`, and cost a trim per piece — which DOCTRINE already rules
against ("joined inside one stroke, never a split into strokes").

```python
def _stroke_dt_stats(field: _WidthField, spine: list[tuple[float, float]],
                     area_mm2: float) -> _DtStats | None
def classify_strokes(poly: Polygon, max_width_mm: float, *,
                     design_class: str = "flat") -> list[RibbonVerdict]
```

plus one keyword `per_stroke: bool = False` on `classify_ribbon` /
`is_satin_candidate`, threaded from `cfg` at all **three** call sites —
`stage5_overlap._comp_axis`, `stage7_sequence._sews_satin` (borders-last) and
`stage7_sequence.stitch_one` — the way `design_class` was threaded, and for
the identical reason: compensation, layer ordering and routing must not
disagree.

## 2. What decides a stroke is a column

`_dt_stats`' arithmetic, per stroke, read off the **parent's** field rather
than a re-rasterized sub-polygon: radii from `field.half_at(p)` along the
stroke's own spine, `spine_len_mm` from the polyline, and an area from a
nearest-spine partition of the parent mask. Re-rasterizing each stroke gives
it a *different* skeleton and is both slower and less true.

Run on Becker's 14 rejections, the result is sharper than expected:

- **`dt_irregular` is almost entirely a pooling artifact.** Per stroke,
  `2σ < μ` holds for every stroke inspected but one. Region cv 0.50–0.69
  decomposes into per-stroke cv 0.03–0.52.
- **`dt_p90_cap` is not an artifact.** Becker's big letter strokes are
  genuinely 4.3–6.4 mm wide (p90 5.3–8.0) against
  `machine.SATIN_MAX_WIDTH_MM` = 5.0. The cap must stay per stroke, or
  `_rail_points`' own per-station guard sews 5 mm crosses in a 6.4 mm stroke
  and leaves bare cloth — DOCTRINE's measured negative.

At a rule of "flip the region when ≥ 0.75 of its stroke-partitioned area
passes both per-stroke gates", five regions flip (1,434 mm²), taking Becker's
satin from **274 → 1,708 mm², 7.6% → 47.6% of region area.** Unanimity
instead of area-majority flips only three tiny regions (65 mm²).

## 3. Joins

Covered twice, and neither needs work here. At a skeleton branch node
`_merge_through_junctions` sets `Stroke.tuck_under_*` and `satin_stroke`
clears the neighbour's corridor — a T's stem tucking under its bar. At a
≥ 45° corner *with* a reflex boundary corner, the 2026-09-03 Goldman join
(`_split_sharp_corners`, `_satin_joined`) keeps the members inside one stroke,
gives the longer one the corner, and butts the other in.

What is **not** covered is a satin stroke adjacent to a *filled* one inside
the same region. No seam machinery exists for that, which is why the first cut
must stay all-or-nothing per region; a mixed-tier shape is a later slice.

## 4. What must not regress, with its fixture

| invariant | pinned by |
|---|---|
| starburst refusal (`Sff37b029`, `Scd89ad66`) | `tests/test_satin.py` — the star reads `explained` 0.974 at elongation 8.3; keep `_PROMOTE_ELONGATION_MIN` on the per-stroke path too |
| trim ceiling 4.1/1k | `tests/test_chaining.py` |
| verdict stability, 5-of-219 | `tools/ribbon_stability.py`, MASTER_SCOPE defect 26 — a per-stroke rung adds a NEW threshold, so re-run it and report flips *and* shipped verdicts changed |
| byte identity | `test_flat_lane_byte_identical.py`, `test_photo_lane_byte_identical.py` — the flag defaults OFF, and OFF must be md5-identical with no exception taken |
| the reverse case | `logo_alpha.png`'s `Sf5200f3f`: satin-classified today with one stroke running 0.33–10.33 mm locally. Per-stroke routing may *demote* it. Arguably correct, definitely a golden move — measure before deciding |

## 5. How it is measured — on the stitches

DOCTRINE's rule, learned when `tools/seam_underlap.py` read stage 5's **plan**
and hid a month-long defect: prove it on the stitches
(`tools/sewn_compensation.py` is the precedent).

**`digitizer/tools/satin_columns.py`**, with `tests/test_satin_columns.py`
pinning it on synthetic zigzags. It reads needle-down runs from either a
`StitchPlan` or a decoded machine file (`pystitch`, as
`tools/row_pitch_union.py` already does), marks a stitch as in-column when
consecutive segment lengths sit in a band and the turn between them exceeds a
reversal threshold for a sustained run, and reports **satin-cross share** plus
the **column-width distribution** (median, p10/p90, and the sub-0.7 / sub-1.0
mm fractions the audit used).

**Built and calibrated the same day** (`tools/satin_columns.py`,
`tests/test_satin_columns.py`, 9 tests). It detects a cross by SIGN
ALTERNATION about the chord rather than by a turn-angle threshold, which the
first cut used and which is not scale-free: at the 0.4 mm satin pitch a
2.5 mm column turns 162 deg but a 0.5 mm one only 103, so a 120 deg gate is
blind to columns under ~0.69 mm — exactly the hairline satin the instrument
exists to find. Measured:

| file | crossing share | median column | under 0.7 mm |
|---|---:|---:|---:|
| pro, Becker large (committed) | **44.3%** of 11,274 | 2.52 mm | 5% |
| pro, Becker chest small (committed) | 48.6% of 8,694 | 2.09 mm | 7% |
| **ours, becker_marine_logo @ 100 mm** | **2.2%** of 11,374 | **0.29 mm** | **84%** |
| ours, `logo_gaulke_roofing` @ 80 mm | 2.9% of 10,233 | 0.91 mm | 8% (83% under 1.0) |
| ours, `logo_script_tires` @ 80 mm | 64.6% of 2,340 | 3.42 mm | 12% |

The independent audit read the same pro file at 42.8% / 2.52 — the median to
the digit, the share 1.5 points under, entirely explained by its angle gate.
`logo_script_tires` is the control that says the instrument is not simply
reporting low numbers: a logo we DO sew as satin reads 64.6%.

**It can run in CI.** `digitizer/testdata/reference/becker_hat_polo_large_beckers_logolc.dst`
is committed and decodes to 11,274 stitches — the audit's pro Becker exactly.
The Gaulke and Fremont pro files are not committed, so those arms stay local.

## 6. Size and staging

**PR 1 — the instrument alone** (~250 lines tool + ~120 test). Zero engine
change. Becker CI arm against the committed pro file; local arms for the
others. This is the PR that makes the gap a number.

**PR 2 — `_stroke_dt_stats` + `classify_strokes`, no wiring** (~150 lines +
tests). Pure additions; nothing in the pipeline calls them. Report the
per-stroke verdict table for the four letterform archetypes plus the serrated
disc.

**PR 3 — the flag** (~60 lines across `config.py`, `stage5_overlap.py`,
`stage7_sequence.py` ×2), default OFF, plus a per-shape tier diff. OFF is
md5-identical. The ON arm's numbers then go to Kent for the flip, followed by
the scorecard recapture.

## 7. Risks, and the cheapest experiment — which already ran

**The largest risk is that this does not fix the headline.** Gaulke at 80 mm:
**43 of its 56 regions already earn satin**, one more is `promoted_ribbon`,
and only 7 are `dt_irregular` (440 mm² rescuable against 1,918 still refused).
Gaulke's 5.3% is not a routing failure — it is that segmentation shatters the
logo into 56 regions whose satin-earning area is 316 mm², sewn as 0.84 mm
hairlines, while the pro re-sets the same logo at 95 × 42 mm and sews 5,151
stitches. **Per-stroke routing will not move Gaulke.** That belongs to defect
5's segmentation remainder and defect 24's hairline tier.

Second: a new area-fraction threshold on a classifier DOCTRINE has already
measured as threshold-fragile. Score it on `ribbon_stability.py` before
adopting a number, not after.

Third: Becker's ceiling is bounded by the 5.0 mm cap, which DOCTRINE closed in
both directions. Per-stroke buys the `dt_irregular` nine; the `dt_p90_cap`
five stay refused, and correctly.

**The cheapest experiment already ran, at two fixture runs.** The honest
current answer: the per-stroke rung is worth roughly +1,434 mm² of satin on
Becker, nothing on Gaulke, and Fremont is unmeasured. The decision for Kent is
whether that is the biggest gap, or whether the instrument should land first
and re-rank it.
