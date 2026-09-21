# Area-weighting the satin/fill gates — what it fixes, and what it does not

Built as `cfg.classify_area_weighted` (DEFAULT OFF) on Kent's pick,
2026-09-16, after the decomposition census
(`docs/superpowers/plans/2026-09-15-decomposition-census.md`) pointed at the
satin/fill router rather than the skeleton as the Becker-parity lever.

**The headline is a refutation.** The 2026-09-12 gap audit (§4.2, inv. 3)
measured a size CLIFF — nine 1 mm steps swinging becker's sewn satin share by
≥ 17 points — reported that five reparameterisations were as unstable or
worse, and concluded *"only area-weighting survives"*. Area-weighting is now
built and measured, and **it does not touch that cliff**. What it does fix is
a different instability, and the cliff's real cause is now named.

## 1. What it is

The gates pool the distance transform over the shape's skeleton PIXELS, each
counted once: the regularity gate `2σ < μ`, and the `dt_p90_cap` width
ceiling. A pixel of spine at radius r stands for 2r of area, so a long thin
tail outvotes a wide body of few pixels. ON, the regularity gate weights each
pixel by r.

**The width cap is deliberately NOT weighted, and that is measured.** The
first cut weighted `p90` too, which asks the widest part of a shape about
itself twice. On becker it DEMOTED real satin — `S579cb1c2` satin →
`dt_p90_cap` (p90 4.96 → 5.01 mm against the 5.0 cap) and the rope border
`Sead76620` promoted_ribbon → dt_irregular — taking the design's sewn satin
share **0.468 → 0.193 at 80 mm**. The cap is a question about the MAXIMUM;
only the regularity gate is a question about a shape's typical width.
`explained` and `elongation` stay unweighted too: `explained` is area over
what the spine SWEEPS, and weighting the sweep's width by width compares a
shape against a stroke it never makes.

Scope: the pooled REGION gate only. The per-stroke rung has its own
statistic (`_stroke_dt_stats`) and is untouched.

## 2. What it fixes — stability under boundary detail

`tools/ribbon_stability.py --variant area` digitizes each fixture twice, once
with the curve refinement ungated (the strongest boundary-detail change the
engine can make without touching the artwork), and counts shapes whose
verdict differs:

| | flips, shipped → refined |
|---|---|
| shipped classifier | **3** (all on drone) |
| area-weighted | **0** |

**14 shipped verdicts change, and every one is `dt_irregular` → satin** —
enthusiast 1, Fremont 2, drone 11, becker 0. Typical row: drone `Sc8d707b2`,
cv **0.52 → 0.32** at an unchanged `explained` 0.89. Promotion-only is the
direction DOCTRINE requires of any classifier rung. The letterform
archetypes (bar, O-ring, C-stroke, T-shape) keep satin and the serrated
discs stay refused.

## 3. What it does NOT fix — the size cliff

`tools/classifier_cliff.py`, becker at every millimetre from 80 to 100 mm,
sewn satin share read off the emitted plan:

| | span | worst 1 mm step |
|---|---|---|
| shipped | 0.080–0.482 (0.402) | **0.288** at 87 → 88 mm |
| area-weighted | 0.097–0.482 (0.385) | **0.288** at 87 → 88 mm |

The cliff is identical. **It is not a weighting problem: it is two hard
thresholds with no margin, each crossed by under 1%** — measured by diffing
every region's verdict at 87 and 88 mm:

| shape | 87 mm | 88 mm | what crossed |
|---|---|---|---|
| rope border, 756.1 mm² | `promoted_ribbon` | `dt_irregular` | `explained` **0.806 → 0.794** against `_PROMOTE_EXPLAINED_MIN` 0.80 |
| 266.7 mm² | `satin` | `dt_p90_cap` | p90 **4.96 → 5.01 mm** against `SATIN_MAX_WIDTH_MM` 5.0 |
| 157.8 mm² | `dt_irregular` | `satin` | cv 0.523 → 0.488 against 0.5 |

Becker goes 12 satin shapes of 18 to 10, and 7,567 stitches to 13,402. Three
thresholds, three crossings, one millimetre. **A cure has to be a margin
rule** (hysteresis, or a decision that does not turn on the last 1% of a
measurement), not a better statistic — and it is Kent's, because the 5.0 mm
number itself is frozen (DOCTRINE) while a margin around it is a new rule.

## 4. Corpus A/B — 26 fixtures at 80 mm / left_chest

`tools/flip_sheet.py`, arm `area_weighted`: **9 move, 17 identical; net
−5,027 stitches, +41 trims; blocks, cones and colour stops unchanged.**

| fixture | stitches | trims | grade |
|---|---:|---:|---|
| `photo_chrome_specular` | −1,804 | +33 | C 64 → **B 76** |
| `screenshot_phone_ui_golke` | −1,401 | +9 | F 0 → F 0 |
| `photo_dof_meadow` | −849 | +1 | C 64 → **B 76** |
| `photo_scene_stub` | −394 | −4 | C 64 → C 64 |
| `drone_render` | −297 | +2 | F 0 → F 0 (raw −122 → −134) |
| `enthusiast_logo` | −165 | 0 | B 88 → B 88 |
| `logo_hotel_fremont` | −84 | −1 | C 64 → C 64 |
| `repro_gradient_white_icon` | −28 | +1 | D 58 → D 58 |
| `photo_sunset_backlit` | −5 | 0 | B 76 → B 76 |

**Every mover is a photo- or gradient-lane fixture; not one flat-lane logo
moves** (becker, tires, whitebg, alpha and the rest are byte-identical). That
is the shape of the change: it promotes branchy, varying-width regions that
the pooled gate reads as irregular, and those live on the lane real logo art
is currently misrouted to.

## 5. Limits

- Windows same-machine A/B (DOCTRINE 2026-09-15): compare arms, do not quote
  a grade as a baseline.
- The cliff sweep is ONE fixture over ONE 20 mm window. The audit's own range
  was 60–108 mm; nothing here says the cliff is only at 87 → 88.
- Stability was measured against boundary detail, which is the instrument
  `ribbon_stability` owns. Stability against SIZE is what §3 says is still
  open.
- No render was made of the 14 promoted shapes: they sew as satin where they
  sewed as fill, and whether each reads better on cloth is a look question
  this doc does not answer.
