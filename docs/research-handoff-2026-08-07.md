# EMB-Bot research handoff — 2026-08-07

Two deep-research waves (134 agents, ~6.8M tokens) against vendor documentation,
source code, patents, peer-reviewed work and thread/stabilizer manufacturer
technical sheets. Every finding below carries a source URL and a tier. Findings
are mapped onto the engine as it stands on `main` @ `5c2332f`.

**Source tiers used, best first:** `vendor-doc` · `source-code` · `patent` ·
`peer-reviewed` · `thread-or-stabilizer-manufacturer` · `practitioner-blog` ·
`forum` · `seo-content-farm`.

**Verification status.** Four lanes got a full adversarial verify pass
(density-convention, melco-crossover, thread-break-physics, quality-scoring) —
that pass caught four fabricated numbers, listed in §10. Eight lanes
(wilcom-hatch-defaults, fabric-stabilizer, push-pull, small-lettering,
fill-techniques, image-prep, streamlines, opportunity-scout) died to a session
cap before their verifier ran; their findings are marked **[UNVERIFIED]** and
must be re-checked against the cited URL before anything is wired from them.
Two lanes never ran at all (ML 2024-2026, commercial auto-digitize knobs) — §11.

---

## 1. The headline: Law 19 is settled, and we are on the wrong side of it

**Professional fill density is quoted between rows sewn in the SAME direction.
Ours is quoted between physically adjacent rows. The two differ by exactly 2×,
and our tatami sews at half professional coverage.**

The chain, four independent lineages agreeing:

| Source | Statement | Tier |
|---|---|---|
| Hatch (Wilcom engine) | "The spacing setting is the distance between two forward rows." [`Adjust_tatami_fill_density.htm`](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Adjust_tatami_fill_density.htm) | vendor-doc |
| Wilcom blog | "the first is a stitch line and the next row is a back stitch so the measurement is taken on each second row" [`stitch-spacing-or-density`](https://wilcom.com/resources/blog/stitch-spacing-or-density) | vendor-doc |
| Melco | "The density setting in DesignShop represents the distance between stitch lines going the same direction." [`Density_is_Too_Tight.htm`](https://www.melco-service.com/source1/Density_is_Too_Tight.htm) | vendor-doc |
| Melco | standard fill density **3.8 points = 0.38 mm nominal → 0.19 mm physical** | vendor-doc |
| Wilcom | tatami defaults **Spacing 0.38 mm, Length 4 mm, Offset fraction 0.25** | vendor-doc |
| Madeira | 40wt → **0.40 mm**, 51 satin stitches/cm; Polyneon 75 → 0.20 mm, 94/cm ([`Density.pdf`](https://www.madeirausa.com/_resources/common/userfiles/file/Resources/TH.Reads/Density.pdf)) | thread mfr |
| Our own 39-file / 410k-stitch DST corpus | 0.19–0.20 mm between adjacent physical rows | measured |

The corpus number was never anomalous. It is exactly what a design digitized at
a nominal 0.38–0.40 mm looks like when you measure adjacent lines.

**Independent arithmetic check that does not use the convention argument at
all.** Coats publishes solid fill at **≈1,250 stitches/in²**
([`discovering-your-embroidery-solution`](https://www.coats.com/en-us/info-hub/discovering-your-embroidery-solution/), thread mfr).
Our generator produces `1/(FILL_ROW_MM × FILL_STITCH_MM)` = `1/(0.40 × 3.0)`
= 0.833 st/mm² = **538 st/in²** — 43% of the published figure. At a 0.20 mm row
pitch with our 3.0 mm stitch we land at 1,075 st/in²; at the corpus-median
2.6 mm stitch, 1,240 st/in². The published constant only reconciles at ~0.20 mm.

**Second independent check that also avoids the convention argument.**
Ink/Stitch's `row_spacing_mm` default is **0.25 mm** and its source proves the
value is between adjacent generated rows — `current_row_y += row_spacing` per
row with alternating rows merely direction-swapped, no extra return row
([`lib/stitches/fill.py`](https://raw.githubusercontent.com/inkstitch/inkstitch/main/lib/stitches/fill.py),
[`tatami_fill.py`](https://raw.githubusercontent.com/inkstitch/inkstitch/main/lib/stitches/tatami_fill.py)).
Same convention as ours, 1.6× denser than ours. Even discarding every vendor
claim above, the one tool that measures the way we measure runs denser.

### What this does NOT touch: satin

`SATIN_SPACING_MM = 0.4` is **correct and needs no change.** Hatch defines stitch
spacing generally as "the distance in millimeters between two needle
penetrations on the same side of a shape"
([`Stitch_spacing.htm`](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Stitch_spacing.htm)) —
that is the same-rail pitch. Our emitter advances one spacing per cross with
constant A,B,A,B rail order (`stage6_satin.py:1104-1107`), so our same-rail pitch
*is* 0.4 mm, measured at 0.41 mm on the benchmark. Corroborated three more ways:
Melco DesignShop default column density 4 points = 0.40 mm; Embrilliance normal
satin 4–5 points with a 0.3–2.0 mm legal range; Madeira 40wt = 0.40 mm.
Ink/Stitch's `zigzag_spacing_mm` default is also 0.4 with the unit string
`mm/cycle` and the comment *"This is double the mm/stitch measurement used by
most mechanical machines"* — the same convention, stated outright.

**So the engine is right on satin and 2× light on fill.** That asymmetry is the
single most consequential thing in this document.

### What to do about it

Do **not** change `FILL_ROW_MM` on analysis. Block 2 of the existing sew-out card
(`docs/sewout-card-2026-07-31.md`) was built to test exactly 0.40 vs 0.20 vs
interleaved two-pass and is now the decisive experiment — it predates the law and
happens to be aimed at it. Sew it.

Two candidate implementations, and they are not equivalent:

1. **Halve the row pitch** — `FILL_ROW_MM 0.40 → 0.20`. One pass, doubled row
   count. Simplest, matches the corpus geometry literally.
2. **Interleaved two-pass at 0.40** — sew all odd rows, then all even rows offset
   by 0.20. Same final coverage, but the fabric is stabilized by the first pass
   before the second lands, and travel/routing is halved per pass.

Both double stitch count on every filled design. Consequences to pre-compute
before the sew-out: preflight coverage goes from 1.0 to 2.0 units (still under
`COVERAGE_WARN_UNITS = 2.5`, so the grader is already calibrated for professional
density — it is the generator that is off); run time doubles on fills; thread
consumption doubles; and `_underlay_paths` derives lattice spacing from
`row_mm`, so underlay density moves with it unless pinned.

---

## 2. Confirmed — do not touch these

| Constant | Value | Corroboration |
|---|---|---|
| `SATIN_SPACING_MM` | 0.4 | Melco 4 pt, Embrilliance 4–5 pt (range 0.3–2.0), Madeira 40wt 0.40, Ink/Stitch 0.4 mm/cycle |
| `FILL_STAGGERS` | 4 | Ink/Stitch `staggers=4`; Wilcom "Offset fraction 0.25" is the same 4-cycle. Named artifact suppressed: a needle-hole valley/ridge perpendicular to the rows |
| `MAX_STITCH_MM` | 12.1 | Wilcom: ternary coding (Tajima) 12.1 mm, binary (Barudan) 12.7 mm. pyembroidery `MAX_STITCH_DISTANCE = 121` at 10 units/mm. Correct for DST; PES/JEF on binary-coded machines could go to 12.7 |
| `MIN_STITCH_MM` | 1.0 | Melco's satin floor is exactly 10 pt = 1.0 mm. **But see §4 — it should not be one global number** |
| `overlap_mm` (underlap) | 0.25 | Embrilliance registration allowance is 3–4 stitch points (0.3–0.4 mm), "about half a needle width". Practitioner consensus is 1–2 mm, higher — worth a look |
| CIEDE2000 spool snapping | — | **Ahead of documented vendor practice.** No primary source recommends CIELAB for embroidery colour reduction; Brother's own patent (US6407745B1) uses plain RGB Euclidean to 7 colours, Wilcom uses unspecified clustering plus a 5%-area gate |
| Trims/1k target band | 0.1–4.1 | unchanged |

---

## 3. Contradicted — where the engine disagrees with the sources

### 3.1 Satin is capped 1–2× too narrow

`SATIN_MAX_WIDTH_MM = 5.0`. Melco's published satin→fill switch is **60 points =
6.0 mm** ([`Determining Stitch Type`](https://melco.zendesk.com/hc/en-us/articles/4402567000589-Determining-Stitch-Type-Satin-Stitch-or-Fill-Stitch), vendor-doc), and its
machine manual brackets maximum satin stitch length at 6–7 mm. Wilcom goes
further: it keeps satin usable to ~10 mm by **splitting stitches at 7.00 mm**
rather than dropping to tatami ([`Split_satin_stitches.htm`](https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Split_satin_stitches.htm), vendor-doc, verified).

We already have a split-satin tier at `SPLIT_SATIN_ABOVE_MM = 5.0`. The
market-parity configuration is **satin ceiling ~10 mm with auto-split at 7.0 mm**,
not a hard fall to tatami at 5.0.

One correction worth recording: the "corpus median 5.0 mm split threshold" framing
conflated two different things. Wilcom's 7.00 mm gates on **per-stitch length**,
so a turning column splits only in its wide sections. Ink/Stitch ships **no**
default satin split at all. Our 5.0 is a satin-vs-fill cutoff; theirs is a
split trigger. Different quantities.

### 3.2 Satin spacing should vary with column width — ours is flat

Both major vendors compute satin spacing as a function of column width; we use a
constant.

- **Melco Auto-Density ramp** (vendor-doc, `32774a.pdf`): 1.0 mm column →
  **0.60 mm** spacing; 2.0 mm column → **0.50 mm**; linear between. We sew 0.40 at
  every width, i.e. **33–50% over-dense on narrow satins** — a direct thread-break
  and bulletproofing cause.
- **Wilcom Auto Spacing** (vendor-doc): derives spacing from width, then applies a
  global percentage where *lower means denser*. Documented values: 110–115% to
  open, 90–85% to tighten, **75% generally produces high quality**. Worked example
  from the Wilcom blog: a 4 mm column at 0.4 mm × 90% → 0.36 mm.
- **Thread-weight offsets** (vendor-doc, `Satin_auto-spacing.htm`): Type A ~40
  denier **+0.01 mm**, B ~30 den **+0.03**, C ~80 den **−0.03**, D ~100 den **−0.06**.

Direction of the ramp is the opposite of intuition and matters: *narrow columns
get looser, not tighter.* Melco says the same thing again for small lettering —
"Density should be set to Auto Density or increased so you have less stitches",
with **4.2–4.8 pt (0.42–0.48 mm)** for small text versus 4.0 normal.

### 3.3 Fabric pull compensation runs high on the pile fabrics

Wilcom publishes a fabric-indexed table in absolute mm
([`Apply_automatic_pull_compensation`](https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/underlays/Apply_automatic_pull_compensation.htm), vendor-doc):

| Wilcom | mm | our preset | ours | verdict |
|---|---|---|---|---|
| Drills / cotton | 0.20 | canvas_tote, woven_dress | 0.20 | exact match |
| T-shirt | 0.35 | jersey_tee | 0.35 | exact match |
| Fleece / jumper | 0.40 | fleece_sweatshirt | **0.50** | 25% high |
| Lettering | 0.2–0.3 | — | — | we have no element-size term |
| — | — | terry_towel | **0.60** | above anything any source publishes |
| — | — | pique_knit | **0.30** | Hatch Auto Fabric reportedly ships Pique at 0.17–0.20 **[UNVERIFIED, seo tier]** |
| — | — | structured_cap | 0.40 | inside the reported 0.35–0.45 cap band |

Trade press puts sweatshirt fleece at **0.22–0.26 mm** (practitioner-blog,
Impressions) — lower still. Terry at 0.60 has exactly one supporting source
(theembroiderycoach, practitioner-blog) which prescribes it **together with a
contour underlay at 0.40 mm inset and 4 lines of perpendicular underlay** — the
other half of a prescription we only implemented half of.

The one **peer-reviewed measurement** found: a 6 mm closed contour on stabilized
poly/cotton woven came out **1.7–3.3% narrower** than digitized, i.e. a total
width deficit of **0.10–0.20 mm** ([KTU Materials Science](https://matsc.ktu.lt/index.php/MatSc/article/view/16095/8786)).
That is ~0.05–0.10 mm per side on stable woven — *less* than our 0.20 if our
value is per-side.

**Unit ambiguity we must resolve before porting any of these numbers.** Melco and
Ink/Stitch both state compensation **per side**, so the entered value doubles the
finished width (Melco: a 5-pt satin with pull offset 3 finishes at 11 pt).
Ink/Stitch's unit string is literally `mm (each side)`. If our 0.2–0.6 is a total
width gain we are at half of vendor-equivalent; if per-side we match. Pin this
down in `stage5_overlap.py` before adopting anything from the table.

### 3.4 Compensation shape: constant-mm is the worst of both worlds

Every vendor examined offers **absolute + proportional, summed**, not either/or:

- Ink/Stitch kernel: `offset_a = offset_px[0] + (distance * offset_proportional[0])`,
  per side, with an anti-collapse clamp ([`lib/utils/geometry.py`](https://raw.githubusercontent.com/inkstitch/inkstitch/main/lib/utils/geometry.py)).
  Final width = `W*(1+p_a+p_b) + mm_a + mm_b`. Ours is that formula with the
  proportional term pinned to zero.
- Melco AMAYA exposes percentage **and** points, separately on X and Y — a shipping
  machine OS doing anisotropic comp, defaulting to zero.
- Embrilliance uses clamped-proportional: `clamp(min_mm, pct·W, max_mm)`, suggesting
  2–3% per side, minimum 0–0.3 mm.
- Practitioner curve (theembroiderycoach): 2 mm column → +0.15 mm (7.5% of width);
  5–6 mm column → +0.25–0.30 mm (~5%). **Sub-proportional** — comp per mm of width
  falls as columns widen.

Embrilliance names the selection rule outright: use the percentage form when a
single object's width varies along its length. **Our medial-axis satins vary in
width by construction**, which is precisely the case that vendor says requires the
proportional term.

### 3.5 Push cutback should track the fabric, not be a constant

`PUSH_CUTBACK_MM = 0.4` fixed, and `end_cutback = pull_comp + 0.4` only when
`directional_comp` is on (it is off, so push comp is entirely inert today).
Published rule of thumb is symmetric: **cut the open ends back by the same
magnitude added to the width** — so the cutback should equal the fabric's pull
comp, not add a constant to it. The peer-reviewed measurement also says push is
**localised at corners and direction changes** (+0.10 to +0.20 mm on a 6 mm
element, concentrated where stitch rows converge), not uniform along a column.

---

## 4. `MIN_STITCH_MM` should be three numbers, not one

Melco publishes per-stitch-type minimums ([`Stitches_Too_Small.htm`](https://www.melco-service.com/source1/Stitches_Too_Small.htm), vendor-doc, verified):

| stitch type | Melco floor | ours |
|---|---|---|
| satin | 10 pt = **1.0 mm** | 1.0 ✓ |
| walk / travel | 15 pt = **1.5 mm** | 1.0 ✗ |
| fill | 20 pt = **2.0 mm** | 1.0 ✗ |

Our Dijkstra travel runs and tatami rows are permitted to emit stitches Melco
classifies as break-prone. Note the verifier's correction: DesignShop filters
"every **other** stitch that falls below five points" — a decimation, not a hard
floor. Different algorithm from ours; do not copy it as a filter.

**Physics behind the floors.** Schmetz: needle size *is* blade diameter — 65/9 =
0.65 mm, 70/10 = 0.70, 75/11 = 0.75, 80/12 = 0.80, 90/14 = 0.90. A&E adds that a
ball-eye needle's eye runs 0.003–0.004 in (0.076–0.102 mm) larger than the blade,
so the **effective hole is blade + ~0.08–0.10 mm** — a 75/11 makes a ~0.83 mm hole.
A 1.0 mm stitch therefore clears the previous hole edge by ~0.17 mm. The floor is
marginal, not comfortable.

**This directly implicates `TIE_STITCH_MM = 0.8 × 3.`** 0.8 mm is *below* the
effective hole diameter of every needle from 70/10 up. Three ties at 0.8 mm
spacing are effectively one hole struck three times — which is what A&E's
embroidery bulletin warns against, and what Melco avoids by using a **0.6 mm tie
width with an adaptive stitch count that scales with element size** rather than a
fixed repeat. Our fixed 0.8 × 3 is both wider than Melco's and non-adaptive.

*(Countervailing evidence already in the corpus: our own law-17 investigation
found pros stack lock penetrations too — 9.455% of 732,246 corpus penetrations
land on points struck 2+ times, in all 36 files. So stacked ties are not
disqualifying. What is new here is the 0.6 mm width and the adaptive count.)*

**Thread strength budget, for grader calibration.** Madeira Polyneon 40 (poly):
1200 cN breaking force, dtex 135×2, needle 60/8–75/11. Madeira Classic 40 (rayon):
identical count, **580 cN** — less than half. A design safe on poly has 2.07× the
margin of the same design on rayon. And the cold figure is optimistic:
peer-reviewed measurement recorded 187 °C at the needle at 4000 rpm with
**exactly 50% strength loss at ≥3000 rpm**, recommending ≤2000 rpm without
cooling ([Mazari, *Polymers* 2021;13(24):4405](https://pmc.ncbi.nlm.nih.gov/articles/PMC8706176/)).
Coats caps rayon at ~600 SPM versus 800+ for trilobal polyester.

We have no thread-type axis at all. That is the missing dimension behind both
density and stitch-length limits.

---

## 5. Missing subsystems, with the exact numbers to build them

### 5.1 Satin contour / edge-run underlay — the biggest structural hole

We have center-run and zigzag only; any fabric preset naming `edge_run`,
`edge_lattice`, `center_run` or `double_lattice` for satin silently degrades to a
bare center run (`stage6_satin.py:1207-1238`). Exact published defaults:

| source | inset | stitch length | notes | tier |
|---|---|---|---|---|
| Melco Edge Walk | rails at **70% of column width** (15%/side) | **3.0 mm** | vendor default | vendor-doc |
| Ink/Stitch contour | **0.4 mm absolute each side** | **3.0 mm**, tolerance 0.2 mm | ON by default | source-code |
| Wilcom (practitioner report) | **0.35 mm** baseline, 0.6–0.7 on tight curves | ~2.2 mm | engages at ≥4 mm width | **[UNVERIFIED, seo]** |
| Embrilliance | — | underlay density 0.8–1.2 mm | — | vendor-doc |

Note the two conventions disagree: Melco is **proportional** (15%/side),
Ink/Stitch is **absolute** (0.4 mm/side). On a 1.2 mm column those give 0.18 vs
0.4 mm; on a 5 mm column, 0.75 vs 0.4. Our current zigzag inset is 30%/side —
underlay spanning only 40% of the width, against Melco's 70%. **We are both
too-narrow-spanning and too-long-stitched** (2.0 mm vs Melco's 1.5 mm zigzag).

**Free implementation path:** Ink/Stitch applies pull compensation and *every*
underlay inset through the same rail-offset primitive, differing only in sign —
underlay inset is negative pull compensation
([`satin_column.py`](https://raw.githubusercontent.com/inkstitch/inkstitch/main/lib/elements/satin_column.py)).
We already have the rail-offset code in `stage5_overlap`. No new geometry needed.

**Ordering constraint, and it is load-bearing:** inset must be measured from the
**compensated** rail, i.e. from the final needle penetration point — compute pull
comp first, then inset the underlay from the compensated rail. (Ink/Stitch appears
to inset from the raw rail, so its underlay-to-topstitch margin shrinks as comp
grows.)

### 5.2 Underlay selection by width — the band we skip entirely

Two independent Wilcom-family products publish the same ladder, and Ink/Stitch's
tutorial publishes a compatible one:

| column width | Wilcom / Hatch | Ink/Stitch tutorial | ours |
|---|---|---|---|
| 1–2 mm | center run ("narrow columns e.g. 2–3 mm") | centerline | center run ✓ |
| 2–3.5 mm | center run | **contour** | center run |
| 3.5–4 mm | **edge run** (~4 mm per practitioner report) | contour | zigzag (from 2.5) |
| >4 mm | zigzag / double zigzag | zigzag **+ contour** | zigzag |

**Our `SATIN_ZIGZAG_ABOVE_MM = 2.5` jumps straight from center-run to zigzag and
skips the contour/edge-run band that both vendors put in between.** Wilcom's own
words: single zigzag "runs in a similar direction to satin cover stitching causing
it to *sink*", while double zigzag cross-hatches, gives more support, and can
produce a raised puff-like effect.

### 5.3 Lettering underlay by letter height — we have no height axis at all

Wilcom ES and Hatch publish identical thresholds (two vendor-docs, independent
pages):

- **under 5 mm → no underlay at all**
- **6–10 mm → center run**
- **over 10 mm → edge run** (this is also the shipped default lettering underlay)

We apply center-run to every satin unconditionally. Melco goes further for small
text: automatic underlay **off**, replaced by **two manual center runs per whole
letter at 1.5–1.8 mm** stitch length — where ours is a single pass at 2.5 mm.

### 5.4 Minimum satin width — we have a ceiling and no floor

| context | floor | source |
|---|---|---|
| general satin | **1.0 mm** (Melco `Min. Col. Width` field, recommended entry 10) | vendor-doc |
| lettering | **1.2 mm** (12 pt) | vendor-doc |
| caps | **1.2 mm** absolute, **1.7 mm** before it is "difficult" | vendor-doc |
| hard reject | **0.3 mm** — Ink/Stitch will not treat an element as satin below this | source-code |
| practical | 1.5 mm "to avoid thread nesting" | **[UNVERIFIED, seo]** |

`is_satin_candidate` gates on `ribbon_width ≤ max` and aspect ≥ 3:1 with no lower
bound, so degenerate sub-millimetre columns can be emitted. Add a floor that
demotes to the bean/run tier, and a hard reject below ~0.3 mm.

### 5.5 Corner handling — absent, and the thresholds are published

Wilcom's Smart Corners ([`Adjust_smart_corner_settings.htm`](https://docs.wilcom.com/embroiderystudio/e4/en/MainHelp/Quality/quality/Adjust_smart_corner_settings.htm), vendor-doc):

- **Cap** below **20°**
- **Mitre** below **45°**
- **Lap** below **110°** (mutually exclusive with mitre/cap)

Wilcom separately confirms the failure mode: "Sharp corners may cause stitch
bunching which can create hard spots in the embroidery and damage fabric or
needle."

### 5.6 Short-stitch / inner-rail crowding — absent

On the inside of a curve the rail is shorter than the spine, so penetrations
crowd below the nominal spacing and the needle re-enters its own hole. Published
mechanisms:

- **Ink/Stitch:** trigger at **0.25 mm**, inset **15%** — and three rules we would
  otherwise miss: the inset is a percentage of the *current stitch's* rail-to-rail
  length, hard-capped at **50%**, and further capped at `max_stitch_length/3` when
  splitting is active. Multiple space-separated values level consecutive short
  stitches.
- **Wilcom:** triggers on a **spacing percentage** rather than an absolute distance
  (scale-invariant — better for us, since we resize art before stitching), allows
  at most **5 consecutive** shortened stitches, and expresses each level as a
  percentage *of* original length (80% = shortened to 80%).
- **Wilcom Fractional Spacing** — a second, independent cure: measure density at a
  fraction across the column rather than at the outer edge. **0.33** reduces
  bunching with fewer stitches; **0.66** eliminates it but may under-cover. Our
  medial-axis satin effectively measures at 0.5.
- **Melco:** auto-disables short-stitch below **2.0 mm** column width — below that,
  do not shorten at all.

Our `SATIN_SHORT_STITCH_AT_MM = 0.3` sits inside the 0.83 mm effective needle hole,
which is the law-17 concern already on record. Ink/Stitch's 0.25 mm is lower still,
so the discrepancy is not ours alone — but the **inset mechanism**, not the
trigger, is what we are missing.

### 5.7 Border tier has no underlay — and the vendor default disagrees on width too

Melco's Auto-Borders ships border satin at **1.0 mm width, 0.40 mm density**, and
critically **inherits the parent element's underlay** rather than running bare.
Ours is 1.40 mm wide with no underlay at all.

### 5.8 Gradient blend fills sew with no underlay — the recipe is derivable

`stage6_blend.py:370,409` hard-codes `underlay_style="none"`. Ink/Stitch's fill
underlay is ON by default and fully derived from constants we already have:

```
underlay_angle       = fill_angle + 90°
underlay_row_spacing = 3 × fill_row_spacing      # 1.20 mm at our current 0.40
underlay_inset       = 0 mm
underlay_max_stitch  = fill max stitch length
```

Wilcom independently states the same orientation rule as a hard constraint:
"Underlay stitch angle should run counter to cover stitching."

### 5.9 Travel routing — three published rules we do not implement

1. **Collapse length.** Ink/Stitch converts any inter-object jump shorter than
   **3.0 mm** into an ordinary stitch — no trim, no tie
   ([`stitch_plan.py`](https://raw.githubusercontent.com/inkstitch/inkstitch/main/lib/stitch_plan/stitch_plan.py)).
   This is the single biggest lever on trims/1k that does not touch routing.
2. **Split the one threshold into three.** Wilcom uses separate run-or-jump,
   tie-off and trim gates with the constraint `tie_off_distance ≤ trim_distance` —
   letting a design tie without trimming in the 2–3 mm band.
3. **Travel grating geometry.** Ink/Stitch routes underpath on a three-way grid
   deliberately skewed off the fill angle: gratings at `fill_angle ±45°` spaced
   **2.0 mm** plus `fill_angle −90°` spaced **1.414 mm**; grid density doubled when
   the shape is under ~700 mm²; **boundary edges weighted 3×** their length to push
   travel inward; interior edges given a bonus inversely proportional to distance
   from the outline. Never parallel to the rows, never on the boundary.

Also: Hatch auto-enables **Travel on Edge** above 0.9 mm nominal spacing
(= 0.45 mm physical) — above that row pitch, interior travel becomes visible.

### 5.10 Cap-specific rules — a whole preset dimension missing

`structured_cap` currently differs from other presets only by `pull_comp_mm`.
Melco publishes (vendor-doc, via the Zendesk JSON API):

- **Sew order is center-out**, alternating across the centre seam: for five
  elements, order **3-4-2-5-1**. This *conflicts with our global largest-first
  ordering* and should override it when the fabric preset is `structured_cap`.
  Implementable as: sort by `|centroid.x − design.center.x|`, alternate sign.
- Satin floor **1.2 mm**, "difficult" below **1.7 mm**.
- Needles under 0.75 mm deflect on caps — use **85/13**.
- Tie style 5, tie-in width 7 (0.7 mm).
- **Cap frame sewing field = 70 mm × 152 mm.** Our preflight has no hoop-bounds
  check at all; this is a cheap hard block on unsewable files.
- Sew speed **900 spm** on caps, **600** for thick columns on caps.

### 5.11 Sew-time and thread-consumption estimation — computable today

Melco's per-application speed table (vendor-doc): **1100 spm** flats, **900** caps,
**850** heavy garments, **700** 3D foam, **600** thick columns on caps.
`sew_time = stitches / spm(fabric_preset, has_puff, max_column_width)` is
computable at export from data we already hold.

Thread: Coats gives **6.0 m needle thread + 2.3 m bobbin per 1,000 stitches**;
Madeira gives ~5 m and ~3 m. Coats also publishes per-stitch-class ratios —
zigzag lockstitch (ISO 304, i.e. satin) consumes **7.0 cm of thread per cm of
seam** versus **2.5** for straight lockstitch (ISO 301), 50/50 needle/bobbin, plus
10–15% wastage. Our stitch plan already holds per-tier path lengths, so a per-colour
yardage figure is a summation away.

---

## 6. Preflight / grader upgrades

### 6.1 A density-map grader, with two independently-derived implementations

Both converge on **6** as the failure threshold:

- **Embrilliance Density Map:** bright red = **six or more layers of thread**,
  "which undoubtedly will produce poor embroidery results" (vendor-doc). Only that
  one band is published anywhere — a full band table does not exist in public
  Embrilliance documentation.
- **US6633794B2** (patent, expired 2021, inventor Brian D. Bailie — *not* assigned
  to BriTon Leap, see §10): rasterize every stitch segment into a grid whose cell
  edge equals the thread width, **0.25 mm for 40wt**, and hold a positive-integer
  accumulator per cell. 40wt = 4 threads per mm; 30wt = 3 per mm.
- **Ink/Stitch density map** (source-code, `templates/density_map.xml`): **red at 6
  stitches within a 0.5 mm radius, yellow at 3**. Converted: red = 7.6
  penetrations/mm², yellow = 3.8/mm². It uses an R-tree `dwithin` neighbour count
  over penetration points — O(n log n), no rasterization, and it measures **needle
  crowding** (the thread-break driver) rather than thread coverage.

Our `coverage_units` metric is neither of these. Adding the penetration-crowding
count is cheap and gives an industry-legible number.

### 6.2 Split the short-stitch check into two bands

EmbroidAI's DST analyzer (vendor-doc, closest direct competitor to our grader)
uses a subtractive 10-point score with: **micro < 0.5 mm**, **short < 1 mm**,
**overlong > ~7 mm**, plus jumps/trims, per-grid-cell local density, and excessive
colour changes. It publishes no deduction weights. Two things to take: the
**micro/short two-tier split** below our single 1.0 mm line, and the
**"long jumps that should really be trims"** defect class — we optimise trims/1k
downward but never check that no long uncut jump survives.

### 6.3 Checks we have no equivalent for

| check | threshold | source |
|---|---|---|
| hoop / sewing-field bounds | 70×152 mm cap frame; 100×100, 130×180, 200×300 mm common | vendor-doc |
| letter height floor | 5.08 mm flat / 6.35 mm cap (Melco); <5 mm no-underlay band (Wilcom) | vendor-doc |
| counter (letter hole) closure | ≥1 mm void diameter; warn below 0.80 mm after comp | practitioner |
| input resolution | 300 DPI required (Hatch, rejects 96); 150–300 DPI (Melco) = 5.9–11.8 px/mm at final size | vendor-doc |
| minimum artwork detail | **2 mm** — two vendors agree | vendor-doc |
| shape thickness window | 1.3 mm – 12.5 mm (Melco) | vendor-doc |
| colour count | ≤6 recommended, ≤16 max (Melco); intermediate palette ≤128 (Wilcom) | vendor-doc |
| total stitch count | 15,000 (Melco); 12,000 standard / 18,000 large (Inkthreadable) | vendor-doc |
| resize band | ±10% before re-digitizing | vendor-doc |
| stitch-count sanity | fill ≈1,250 st/in²; satin 200 st/linear in; run 50 st/linear in | thread mfr |
| corner angle | flag satin corners below 20° | vendor-doc |

Note our `min_detail_mm = 1.5` sits below the vendor-consensus **2 mm** floor, and
potrace's default `turdsize = 2 px` (0.17 mm at 300 DPI) is ~12× finer than the
embroidery floor — the vectoriser keeps specks that can never sew.

---

## 7. Photo / gradient tier — a complete, implementable algorithm

*[UNVERIFIED lane, but the primary sources are a peer-reviewed paper and its own
public source code, which is the highest-trust combination available.]*

**Automatic Digitizing of Embroidery Patterns Using Streamlines**, Computer
Graphics Forum 42(2), Eurographics 2023, DOI 10.1111/cgf.14770, CC BY-NC-ND,
code at [`desmondlzy/embroidery-streamlines`](https://github.com/desmondlzy/embroidery-streamlines).

The mechanism, in order:

1. **Density field as a conservation law.** With `Z(p) = α(p)·v(p)` (density ×
   unit direction), `∫div(Z) = #sources − #sinks` over any subregion, and
   neighbouring streamlines end up `1/α` apart. This is a *provably* correct
   variable-density fill with no spacing heuristic.
2. **Seeding.** Sources only where `div Z > 0`, sinks only where `< 0`, as two
   independent point sets — mixing them spawns streamlines where density is
   falling and produces junk segments. Placement via a k-d tree that bisects until
   the divergence integrates to exactly 1.0 per leaf, one source at each leaf's
   centre of mass.
3. **Tracing.** 2nd-order Runge-Kutta at fixed arc-length step; boundary-seeded
   sources nudged inward by 0.002 normalized (0.198 mm at the 99 mm example size)
   to stop immediate truncation.
4. **Termination.** Sink assignment is a **global minimum-weight bipartite full
   matching** (`networkx`), not nearest-first — greedy is provably wrong here and
   produces ragged fragments.
5. **Spacing.** One sparse linear solve of a quadratic spring energy over a
   constrained Delaunay triangulation. Target gap per edge is literally
   `line_width / α`, so at 0.4 mm thread and α ∈ [0.1, 1.0] the row gap sweeps
   **0.4 mm to 4.0 mm — a 10× density range inside one fill.**
6. **Shading.** Two-thread halftone with a closed-form law: background thread
   fills solid, foreground spaced at `1/α` on top, perceived blend `t = b·α`, so
   `α = t/b`. **At most 2 thread layers stack anywhere** — which is why fabric
   distortion stays negligible. The background layer is the same direction field
   **rotated exactly 90° at uniform α = 1.0**, so the two cross-hatch. *That
   background layer doubles as the missing underlay on gradient fills.*
7. **Routing.** Streamlines joined into **one continuous path** via a minimum
   spanning tree over Delaunay edges with cost `‖p_j − p_i‖ / α(midpoint)`, walked
   depth-first (doubled tree ⇒ Eulerian circuit). **Zero trims per colour.**
8. **Colour.** Thread pairs chosen *jointly*: `E(t1,t2) = ΔE2000(s1,t1) +
   ΔE2000(s2,t2) + 10·max{C(s1,s2) − C(t1,t2), 0}` where C is W3C relative
   contrast. Per-colour nearest-match collapses a gradient's tonal separation;
   the contrast-deficit term with weight 10 is a one-line fix to our existing
   CIEDE2000 snapping.
9. **Cost.** 1.58 s for a 1,164-vertex region in pure Python (0.79 s tracing,
   0.66 s matrix assembly); 20 s at 22,630 vertices. Regions are independent.
10. **Stitch pitch.** The shipped example resamples to 4× line width then
    subsamples to a **1.3 mm** hard maximum — a photo tier needs a much shorter
    pitch than our `FILL_STITCH_MM = 3.0` to hold a curved direction field.

**Missing input, and it has a known answer.** The method needs a per-pixel
direction field, which the paper obtains by hand annotation. **Coherent Line
Drawing / Edge Tangent Flow** supplies one automatically from a photograph
([Kang et al., NPAR 2007](https://cg.postech.ac.kr/papers/kang_npar07_hi.pdf)):
ETF kernel radius 5, `wm = ½(1+tanh[η(ĝ(y)−ĝ(x))])` with η = 1, `wd = |t(x)·t(y)|`.

**Cheaper alternatives on the same axis:**
- **Ink/Stitch `linear_gradient_fill`** — blends two colours by interleaving whole
  stitch *rows* on the existing tatami grid: `sections = floor(sqrt(total_lines))`,
  first half mirrored onto the second. **No variable row spacing needed at all.**
- **Ink/Stitch meander fill** — tiles the shape into a graph, finds a
  shortest path, then substitutes longer simple paths until exhausted. Inherently
  single-path (zero trims), no row direction. A texture tier we do not have.
- **Embird Sfumato** (vendor-doc, longest-shipping commercial photo-stitch):
  density 3.5–4.5 tenths mm (**0.35–0.45 mm** — brackets our 0.40 exactly),
  **1–5 shades per object** classically, 2–6 typical in Studio NEXT. Photo
  embroidery is done with *few* threads plus spacing modulation, not many threads.
- **Wilcom Color PhotoStitch** (vendor-doc) publishes the shade schedule:
  **5–6 grayscale, 7–10 simple colour, 14–16 complex, hard cap 20.** Also: any
  colour covering **>5% of image area is auto-included** in the reduced palette —
  an area-weighted gate on top of clustering that we should add so a 6%
  brand-critical accent is never merged away.
- **Hertzmann layered painterly rendering** (SIGGRAPH 98) for a coarse-to-fine
  shade schedule: radius-halving layers, place a stroke only where mean cell error
  exceeds threshold T, seed at the max-error pixel. Impressionist preset T = 100,
  R = (8, 4, 2), minLength 4, maxLength 16.

---

## 8. Fabric, stabilizer and topping — the matrix exists, published by manufacturers

*[UNVERIFIED lane.]* **OESD's Stabilizer Quick Reference** is a published
**22 fabric × 16 stabilizer** table where each cell is marked light / medium /
heavy / all design density
([`OESD_stabilizers.pdf`](https://oesd.com/content/img/pages/stabilizer/OESD_stabilizers.pdf)) —
this is the decision matrix, already machine-readable, from a manufacturer.

Floriani publishes per-stabilizer stitch budgets with an additive rule: No Show
Nylon Mesh 1.5 oz = **6,000–8,000 stitches on a 4″×4″ design**; Medium Cutaway
2.0 oz = **14,000**; float one extra layer of 1.5 oz tearaway per additional 8,000
stitches. Derived, 1.5 oz mesh gives **375–500 st/in²** — well under Coats' 1,250
fill constant, i.e. *stabilizer, not fabric, is the binding constraint on a dense
fill.*

**Documented absence worth recording:** no vendor publishes a stitches-per-in² cap
keyed to a fabric × stabilizer *pair*. That was the headline ask and it does not
exist in manufacturer literature. Nobody crosses the two axes.

Two things that invert naive assumptions:

- **Heavier garments need *less* backing, not more** — AllStitch splits fleecewear
  into 7 oz (2.5–3.3 oz cutaway) / 12 oz (drops to 2.0–2.5 oz). The real axis is
  garment weight *within* a fabric class, which our single-valued presets cannot
  express.
- **Lighter designs are not always safer.** Embroidery Library's per-fabric
  complexity caps require **medium-to-high** design complexity on waffle weave,
  velour, terry and sweater knit — light running-stitch designs get *lost* in the
  pile. Our bean/run tier for small shapes produces exactly the output vendors say
  fails on those fabrics.

**Unresolved contradiction on napped goods.** Impressions trade press says
sweatshirt fleece needs density **increased 10–15%** and underlay nearly doubled.
Our presets *decrease* fleece density (`row × 0.90`) and terry (`× 0.85`), which
agrees instead with an SEO-tier per-fabric table. Both directions have advocates;
neither is vendor-doc. **This belongs on a sew-out card, not in a commit.**

**Architecture finding that outranks any single number:** Wilcom's Auto Fabric does
not store one parameter set per fabric. It stores **a separate settings block per
stitch-object class within each fabric** — fabric × {Tatami, Wide Satin, Narrow
Satin, Lettering}. Our presets are one `pull_comp_mm` scalar plus a row multiplier.
That shape difference is the real gap; the individual numbers are secondary.

---

## 9. Opportunities outside the brief

*[UNVERIFIED lane, but the puff and cap numbers are Melco/Wilcom vendor-doc.]*

**3D puff** is a coherent, well-documented mode we do not have:
satin spacing **0.15–0.17 mm** (Melco) or 0.2–0.4 mm (Wilcom) — 2.5× denser than
our 0.4; column width **3.0–11.0 mm**, so our 5 mm satin ceiling would wrongly
route wide puff shapes to tatami; pull comp 0.3–0.5 mm scaled to foam thickness;
**every column overlap ≥3 stitches** or foam pushes through; foam anchored by
zigzag underlay at 1.5–2.0 mm plus 1.7 mm tack runs; 5 tie stitches; 700 spm;
needle 90; foam ≤5 mm. Wilcom and Hatch **contradict each other on whether puff
takes underlay at all** — expose it as a switch rather than hard-coding.

**Metallic thread:** 900 spm, needle 90/14, density reduced, tie stitches
lengthened. We have no thread-type axis.

**Placement boxes** (practitioner tier): left chest 50.8–88.9 mm; sleeve
76.2–95.3 mm; cap front 44.5 mm tall × 101.6–127 mm wide, sitting inside the
70×152 mm cap field with ~25 mm margin. A placement enum pairs naturally with the
fabric preset we already ask for.

**A vein worth mining.** `melco.zendesk.com` returns HTTP 403 to normal fetches,
but the **Zendesk REST API works**:
`https://melco.zendesk.com/api/v2/help_center/en-us/articles/{id}.json` and
`/articles/search.json?query=`. That was the single most productive vendor-doc
source found and is far from exhausted.

---

## 10. Claims the verifiers killed — do not propagate these

| claim as first reported | correction |
|---|---|
| Melco DesignShop "filters stitches below 5 points" | Filters **every other** stitch below 5 points — a decimation, not a floor. Materially different algorithm |
| Peer-reviewed stiffness regression: R = 0.96, R² = 0.92, adj 0.91 | **Fabricated.** Actual: Multiple R = 0.84, R² = 0.70, adj 0.66, SE 25.84. The equation and all seven coefficients *are* correct, and density *is* the top-ranked term (Dutta & Chatterjee, *Fashion and Textiles* 2020;7:36) |
| Madeira "satin count = 2 × (10 mm / spacing)" | **Fabricated formula.** Table values are correct and empirical; the formula misses 51→50, 41→40, 94→100. Do not interpolate spacings not in the table |
| Needle temperature 150–320 °C, 35–45% strength loss "measured" | Those are the paper's *citations to prior work*. Its own measurement is 187 °C at 4000 rpm, with exactly **50%** loss at ≥3000 rpm (not >50%) |
| Wilcom docs define 1.0 mm as the short-stitch cutoff | It is an "e.g." inside a user-configurable filter. 1.0 mm remains reasonable, but this page does not standardize it |
| Wilcom satin practical max 10–12 mm, cited to `Split_satin_stitches.htm` | Not on that page. The 7.00 mm Auto Split figure **is** verbatim there; the width figure comes from the Wilcom blog instead |
| Melco "Variable Pull Comp", Custom1 = flat hoop / Custom2 = cap hoop, 25%/20 pt limit | Feature is called **Auto Compensation**; Custom1/Custom2 exist but Melco does not state their semantics; the 25%/20 pt limit and "2004 Cap Driver" preset are unsupported. **Keep:** width-binned with first two bins at 9 pt / 15 pt, values per side so the increase doubles |
| US6633794B2 assigned to BriTon Leap / is the Embrilliance engine | Assignee is an individual (Brian D. Bailie). Expired 2021-07-20. The Embrilliance link is inference, not fact. The 0.25 mm grid number is correct |
| Ink/Stitch "0.4 = 5 lines/mm" is a project statement | Written by the issue *reporter*, marked "IMHO". Numbers are self-consistent; tier is forum, not vendor |
| SPI = 25.4 / spacing_mm; 0.4 mm → 63.5 SPI | The cited source's own worked example says 0.4 mm ↔ **5.1 stitches/mm** (~129.5 SPI) — exactly 2× the naive reciprocal, because it counts forward *and* return penetrations. **This independently reproduces the factor of 2 in §1.** The "55 SPI = 0.462 mm" figure does not appear in the source |
| Ink/Stitch min satin stroke width = 1.5 mm | Refuted in wave 1. The shipped default is **1.0 mm** (`lib/utils/settings.py`); 1.5 mm is a one-off tutorial aside about drawn contour width |

Also flagged: SEO content farms publish fill densities labelled "SPI" that are
actually Melco points (e.g. "cotton 3.8 SPI"). A true 3.8 SPI is 6.7 mm spacing —
physically impossible for a fill. **Never ingest scraped density tables.**

---

## 11. What is still missing

Not answered by this corpus:

1. **Two lanes never ran** — modern ML (SAM-based segmentation, post-MSEmbGAN
   neural photo-to-embroidery, 2024-2026 papers, what "AI digitizing" products
   actually ship) and the commercial auto-digitize parameter surface (what Wilcom
   Smart Design / Hatch / Pulse / Ember expose, categorical vs continuous). Both
   died to network errors, not to a dead end. Re-runnable.
2. **Eight lanes are unverified.** Everything marked [UNVERIFIED] needs its cited
   URL re-fetched before use — the four lanes that *were* verified produced four
   fabricated numbers, so the base rate is not low.
3. **No published measurement of fabric displacement per stitch or per unit
   density exists.** Nothing anywhere states "X mm of pull per N stitches/mm²".
   The KTU paper measures net element width deviation but never normalizes by
   stitch count. This is a genuine hole in the literature.
4. **Appliqué numerics: zero primary sources found.** Our appliqué constants
   remain unsourced.
5. **Wilcom does not publish underlay defaults.** Every underlay page across three
   doc versions was fetched in full; all are prose. The numeric underlay defaults
   in §5.1 come from Melco (vendor-doc) and Ink/Stitch (source-code), with the
   Wilcom figures only from practitioner screenshots.
6. **`LINK_COVER_TOL_MM` is still a thread spec, not a measurement.** Nothing found
   addresses at what clearance a needle-down float becomes visible on fleece. Still
   the highest-value unknown, still one hooping.

---

## 12. Priority order

Ranked by (evidence strength × customer-visible impact), with the condition under
which each would be wrong.

**1. Sew out the fill-density block.** Four vendor lineages plus an independent
stitches-per-in² calculation plus our own corpus all say our tatami is 2× light.
*Wrong if:* Wilcom's "back stitch" row is the same line retraced rather than a
second offset line — but Hatch's "distance between two **forward** rows" makes
that reading hard to sustain, and Ink/Stitch's 0.25 mm at our own convention
corroborates independently.

**2. Add the satin contour/edge-run underlay tier and the width→underlay ladder.**
Two vendors publish the same 5 / 6–10 / >10 mm lettering bands and the same
center→contour→zigzag width ladder; we skip the whole middle band, and our zigzag
rails span 40% of the column against Melco's 70%. Implementation is a sign flip on
existing rail-offset code. *Wrong if:* our medial-axis rails are too noisy to inset
reliably on narrow columns — testable before committing.

**3. Make satin spacing and pull compensation functions of column width.** Melco
ships an explicit width→density ramp (looser on narrow), Wilcom ships width-derived
Auto Spacing at 75–90%, Melco bins pull comp by width at 9 pt / 15 pt, and every
vendor's comp model is absolute **+** proportional. Our flat 0.4 mm at every width
is 33–50% over-dense on narrow satins. *Wrong if:* our medial-axis widths are
unstable enough that a width-keyed ramp introduces more variance than it removes.

**4. Split `MIN_STITCH_MM` by stitch type (satin 1.0 / walk 1.5 / fill 2.0) and
revisit the tie.** Vendor-doc, and the needle physics behind it is solid: effective
hole = blade + 0.08–0.10 mm, so `TIE_STITCH_MM = 0.8` is below the hole diameter of
every needle from 70/10 up. *Wrong if:* raising the travel floor to 1.5 mm forces
travel paths outside shapes that 1.0 mm currently keeps inside — check against the
travel router before changing.

**5. Add the missing preflight gates** — hoop bounds, letter height, input
resolution, 2 mm minimum detail, penetration-crowding density map. All vendor-doc
thresholds, all cheap, none touch the generator. *Wrong if:* they fire on
already-good designs; every threshold here needs a pass over the existing fixture
set before it is allowed to block rather than warn.

**Explicitly not recommended:** raising `SATIN_MAX_WIDTH_MM` to 10 mm. Wilcom
supports it, but only in combination with a working auto-split at 7 mm per-stitch
length, and our split tier gates on column width instead. Sequence it after item 3.

---

*Raw research: 134 agents across `wf_70a4dba9-669` (wave 1, 74/107 completed) and
`wf_5a458cc6-d7c` (wave 2, 16/27 completed). Both journals hold every completed
agent's full return including the runs whose synthesis step was capped.*
