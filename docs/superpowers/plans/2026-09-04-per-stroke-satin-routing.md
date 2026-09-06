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

---

## PR 2 — built and measured (2026-09-05)

`stage6_satin._stroke_dt_stats` / `classify_strokes` / `_partition_area_mm2`,
`tests/test_stroke_classify.py` (10), `tools/stroke_verdicts.py`. Nothing in
the pipeline calls any of it, and a test pins that.

**The headline reproduces exactly.** An independent implementation of §2's
recipe reads `becker_marine_logo.png` @ 100 mm as satin **274.0 → 1,708.3 mm²,
7.6% → 47.6%, five regions flipping 1,434.3 mm²** at the ≥ 0.75 area rule —
the plan's numbers to the decimal. §2's two claims hold: per-stroke cv runs
0.03–0.52 where the region pools to 0.50–0.69, and the p90 cap stays real
(Becker's big strokes measure 5.2–6.7 mm p90 against the 5.0 cap and are
correctly refused per stroke, so `S334e3a12` reaches only frac 0.23).

Four things the measurement changed.

### 1. The gain is a 100 mm number, and the corpus runs at 80

At 80 mm / `left_chest` the same 17 regions are **already 88.2% satin**
(1,982.3 of 2,248.2 mm²) and the rung adds **5.7 mm²**. At 100 mm they are
7.6% satin. Same artwork, same design class, same region count.

The cause is not a scale cliff in the classifier — that was checked and is
false. Scaling a fixed Becker polygon by 1.25 moves its cv by under 0.02
(0.694→0.701, 0.472→0.476, 0.368→0.355); the only verdict it changes is
`dt_p90_cap`, which is correct, because p90 is a length. What differs between
the two widths is **segmentation**: the region sets share no shape ids at all,
and their cv distributions sit at 0.37–0.51 (80 mm) against 0.43–0.55
(100 mm).

### 2. Becker's whole region set sits ON the gate

`2σ ≥ μ` is `cv ≥ 0.50`, and Becker's regions cluster there: **11 of 17 within
±0.10 of the gate at 80 mm, 16 of 17 at 100 mm**, with 2 and 9 respectively
over it. So `dt_irregular` on this design is not a property of the artwork —
it is which side of a knife-edge that run's segmentation happened to land on.
This is MASTER_SCOPE defect 26 (5 of 219 verdicts flip on boundary detail
alone) showing up at whole-design scale.

That is the strongest argument for the rung so far, and a better one than the
mm²: **a per-stroke reading is measurably more decisive.** Over 149 regions
and 740 strokes across five fixtures, median |cv − 0.50| is **0.154 per region
against 0.221 per stroke**, and the share sitting within ±0.10 of the gate
falls from **40.9% to 24.7%**. Better — not fixed. A quarter of strokes still
sit on the line, and the ≥ 0.75 area rule adds a second new threshold on top,
which is exactly what §7 said to score on `ribbon_stability.py` first.

### 3. The starburst needs no extra guard, by 9%

§4 expected `_PROMOTE_ELONGATION_MIN` to have to be carried onto the
per-stroke path to keep refusing `Sff37b029`. It does not: the star's two arms
are **themselves** irregular (cv 0.546 and 0.522, both past 0.50), so the area
fraction is 0.00 with no extra guard. The margin is 9% and 4% past the gate —
thin enough that it is pinned as a test, not noted as a remark.

### 4. The rung must be PROMOTION-ONLY — it demotes 15 regions otherwise

§4 asked for the reverse case to be measured. As described it does not exist:
`logo_alpha.png`'s `Sf5200f3f` reads `dt_irregular` at region level on this
tree, so it is not satin today and cannot be demoted.

Swept across 14 fixtures at 80 mm, though, **15 regions that sew satin today
do not reach frac 0.75**, and most are `promoted_ribbon` — shapes the shipped
`explained` path deliberately rescued. The largest are Becker's `Sead76620`
(**638.8 mm²**, frac 0.71) and `S579cb1c2` (226.4 mm², frac 0.19), and four
bridge-bar regions come back at frac **0.00**.

So a per-stroke rung has to read `region.satin OR per-stroke flip`, never
replace the region call. Written as a replacement it would cost more area than
it wins: corpus-wide the flips are **+143.8 mm² (2%, 21 regions)** against
those 15 demotions.

**Net for the decision:** the rung is worth a lot on one fixture at one size,
little across the corpus at the size the corpus runs, and its real value is
decisiveness at a threshold this project has already measured as fragile.
PR 3's flag is unchanged in shape; what it must NOT be is a replacement.

---

## PR 3 — the flag, built and measured on the stitches (2026-09-06)

`cfg.satin_per_stroke`, **default OFF**. `classify_ribbon` and
`is_satin_candidate` take `per_stroke=`; the three call sites §1 identified
(`stage5_overlap._comp_axis`, `stage7_sequence._sews_satin`, and `stitch_one`'s
ladder) pass `cfg.satin_per_stroke`, so compensation and routing cannot
disagree about which shapes are satin. `tests/test_satin_per_stroke_flag.py`
(6).

The rung sits on the `dt_irregular` branch **alone**, which is what makes it
promotion-only: it can turn a refusal into a satin call and nothing else.
`dt_p90_cap` stays out of its reach (a stroke past the machine cap must still
be refused, or `_rail_points`' per-station guard leaves bare cloth), and
`_floor_or` still applies, so Law 31's width floor cannot be sidestepped by
splitting. No recursion: `classify_strokes` calls `classify_ribbon`, so the
rung consults a shared `_stroke_rows` helper instead of calling back.

**Measured on the emitted stitches** with `tools/satin_columns.py` — this
repo's rule, and the reason the instrument was built first:

| `becker_marine_logo.png` | crossing share | median column | under 0.7 mm | penetrations |
|---|---:|---:|---:|---:|
| @ 100 mm, flag OFF | 2.2% | 0.29 mm | 84% | 11,374 |
| **@ 100 mm, flag ON** | **35.0%** | **2.12 mm** | **11%** | 8,512 |
| *the professional's own file* | *44.3%* | *2.52 mm* | *5%* | *11,274* |
| @ 80 mm, OFF and ON | 54.5% | 1.82 mm | 13% | 5,531 |

So at 100 mm the flag closes most of the gap the audit opened this whole line
of work with — a 0.29 mm hairline median becomes a real 2.12 mm column — and
the design sheds a quarter of its stitches, because satin covers a ribbon far
more cheaply than fill rows do. At 80 mm it is **byte-identical**, and that is
not a null result: Becker at 80 mm already reads 54.5%, ABOVE the pro's 44.3%,
which is the same fact §PR 2 found from the classifier side (88.2% satin
there already).

Two honest qualifications.

- **The classifier's "+1,434 mm², five regions" overstates what sews.** Four
  shapes actually change tier (`S6d3d3130`, `S92a90056`, `Sc9b48e5a`,
  `Sf48a80bd`). The fifth, `S4d48640b` (333 mm²), is one of seven
  ENCLOSED-BACKGROUND regions this fixture leaves unsewn at either flag
  setting — `SHAPES_LEFT_UNSEWN` names all seven, 1,462 mm², with
  `enclosed_background: 7`, and `BACKGROUND_ENCLOSED` explains them as holes
  the user can toggle on in review. Its promotion is inert. (Checked before
  reporting: preflight's silence about that area is correct, not a hole —
  `_uncovered_findings` defers unsewn regions to `SHAPES_LEFT_UNSEWN` on
  purpose, and that warning does fire.)
- **One fixture, one size.** Everything above is Becker at 100 mm. §PR 2's
  corpus sweep is the breadth number and it is small: +143.8 mm² (2%) over 14
  fixtures at 80 mm.

**The flip to ON is Kent's**, and ROADMAP gate 3 wants the instrument rebuilt
first — it is (`tools/satin_columns.py`, #352). What is still missing is a
RENDER: every number here is geometric, and the question "does a 2.12 mm
column read better on this logo than the fill it replaces" is one for his eyes.
