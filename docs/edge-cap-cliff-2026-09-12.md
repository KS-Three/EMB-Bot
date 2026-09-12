# The edge cap's bill oscillates with design size — measured 2026-09-12

**Status: open defect, found on a flag that is DEFAULT ON in front of customers.**
`cfg.edge_cap="bean"` was flipped ON 2026-09-11 on a measured bill of
*"+5.9–26.3%, median +13.4%"*. That band is a **one-width reading** —
`tools/pro_silhouette.py` defaults to `width = 80.0` and the flip's evidence doc
(`docs/superpowers/plans/2026-09-11-edge-cap-from-the-pro.md` §3) measures six
fixtures at 80 mm only.

On `becker_marine_logo` the bill reaches **+58.7% at 88 mm**, eight millimetres
above the only width anyone measured. That is worse than `drone_render`'s
+56.9%, the number DOCTRINE calls *"a whisker off the blanket-border negative."*

**Nothing was sewn. Every number here is geometry or bytes.**

## The headline

**A 0.3 mm larger design is 5,592 needle penetrations — 34% — cheaper.**

| becker @ | plan cap off | plan cap on | DST needle-downs off / on | cap delta | bytes |
|---|---|---|---|---|---|
| 95.7 mm | 10,558 | 16,537 | 10,687 / 16,666 | **5,979** | 32,570 → 50,744 |
| 96.0 mm | 8,644 | 10,945 | 8,773 / 11,074 | **2,301** | 26,840 → 34,001 |

Re-derived independently by summing `len(run.points)` over runs stamped
`shape_id == "__edge_cap__"`, then cross-checked against the exported `.dst`
with a separate Tajima reader — not read off `EDGE_CAP_APPLIED`. **The engine's
own bill is honest.** It correctly reports what the cap costs. The problem is
what that number does across size.

## It is not a cliff at 95.7 mm. It is an oscillating knife edge from 88 mm

| width | art st | cap st | cap % | `edges` | `cracks_filled` | omit cover |
|---|---|---|---|---|---|---|
| 80 | 5,592 | 1,011 | +18.1% | 18 | 1 | 1,355.6 mm² |
| **88** | 8,437 | **4,949** | **+58.7%** | 19 | 1 | 394.7 mm² |
| 90 | 6,795 | 1,756 | +25.8% | 25 | 1 | 1,445.4 mm² |
| **91** | 9,161 | **5,197** | **+56.7%** | 15 | 1 | 294.2 mm² |
| **95.7** | 10,559 | **5,979** | **+56.6%** | 16 | 0 | 85.7 mm² |
| 96 | 8,645 | 2,301 | +26.6% | 20 | 0 | 1,286.0 mm² |
| **100** | 11,374 | **6,324** | **+55.6%** | 17 | 0 | 87.4 mm² |
| **110** | 13,327 | **7,114** | **+53.4%** | 17 | 0 | **None** |

All five rows of the originally reported table reproduce to the digit.

## Cause: the `omit` gate loses its input — not the silhouette, not the cracks

`stage7_sequence.silhouette_cap` was instrumented at its call site to capture
the exact geometry and the exact `omit` it was handed, then re-run on that
captured geometry with the gate on and off:

| becker @ | cap st, gate ON | cap st, gate OFF | gate saves | omit cover |
|---|---|---|---|---|
| 90 mm | 1,564 | 5,632 | **72.2%** | 1,445 mm² |
| 95.7 mm | 5,851 | 6,026 | **2.9%** | **86 mm²** |

**The ungated cost is essentially flat with size** (5,632 → 6,026, +7%,
tracking ring length +7%). The entire 3.4× jump is the gate's saving going from
72% to 3%. At 110 mm `_sewn_linear_cover` returns `None` outright — the design
has zero linear runs — so the gate does not exist and the cap is back in the
pre-gate `+8.6–100.4%` regime the gate was built to kill.

### Why the input evaporates

One shape carries ~94% of this design's linear cover: the "BECKER" banner, a
~1.9 mm × 616 mm ribbon of 640–935 mm². A spy on `stage6_satin.classify_ribbon`
tracking that shape across the sweep:

| width | linear runs | omit cover | banner verdict | `explained` |
|---|---|---|---|---|
| 80 | 36 | 1,355.6 mm² | SATIN `promoted_ribbon` | 0.8140 |
| 86 | 34 | 1,491.9 mm² | SATIN | 0.8069 |
| **88** | **9** | **394.7 mm²** | **fill `dt_irregular`** | **0.7965** |
| 90 | 22 | 1,445.4 mm² | SATIN | 0.8055 |
| **91** | **8** | **294.2 mm²** | **fill** | **0.7832** |
| 92 | 27 | 1,410.8 mm² | SATIN | 0.8051 |
| **95** | **4** | **246.6 mm²** | **fill** | **0.7781** |
| 95.5 | 28 | 1,287.5 mm² | SATIN | 0.8076 |
| **95.7** | **1** | **85.7 mm²** | **fill** | **0.7868** |
| 96 | 19 | 1,286.0 mm² | SATIN | — |
| 110 | **0** | **None** | fill | — |

`explained` oscillates in a ±0.03 band straddling
**`_PROMOTE_EXPLAINED_MIN = 0.80`** (`stage6_satin.py:513`), read by the
`promoted_ribbon` rescue at `stage6_satin.py:414-417`. Above 0.80 the banner is
satin and lays ~1,400 mm² of linear cover; below it the banner is tatami and
lays none. **That single shape is the gate**, and its verdict is not monotone
in design size.

## The render settles it

`docs/renders/edge-cap-cliff-2026-09-12/` — red = the cap's emitted thread,
green = the `omit` cover the gate was handed, blue = artwork linear runs, black
hairline = silhouette rings.

Compare `becker_95.7mm_bean.png` against `becker_96mm_bean.png`, 0.3 mm apart
and with an identical silhouette:

- **95.7 mm** — one tiny green patch, on the "I" of MARINE. Red traces *every*
  ring end to end, including all six letter counters of BECKER.
- **96.0 mm** — the BECKER banner is one large green satin field; red survives
  only as short arcs where the satin genuinely stops.

`becker_88mm_bean.png` and `becker_91mm_bean.png` show the same collapsed
picture *below* the originally reported cliff. `becker_110mm_bean.png` has no
green at all. Nothing in any of these is a more fragmented silhouette, and
nothing is a hairline crack network.

## Both first-guess explanations, measured and refuted

**(a) A genuinely more fragmented silhouette — refuted.** `sil_parts = 10` and
`interiors_pre = 7` at *every* width from 80 to 110. Ring length scales
smoothly 1,200.8 → 1,696.6 mm (+41% over a +37.5% size change). Defect 19's
fragmentation story is real for `drone_render`; it is not this.

**(b) Tracing the crack network — refuted as the cause, but a real 0.8% effect
and a genuine bug.** Re-running `silhouette_cap` on the captured 95.7 mm
silhouette with the crack ruler widened from `BORDER_WIDTH_MM` (1.70) to 2.00,
filling the one surviving 1.705 mm interior: **5,851 → 5,802 cap stitches — 49
stitches, 0.8% of the bill.** And `cracks_filled` decorrelates completely: 1 at
80 (cheap), 1 at 88 (expensive), 1 at 90 (cheap), 1 at 91 (expensive), 0 at
95.7 (expensive), 0 at 96 (cheap).

The guessed mechanism — *"a scale-dependent **perimeter** floor in
`_fill_cracks`"* — is not what that function does. `stage6_border.py:865-866`
judges a ring by its own **width**:

```python
keep = [ring for ring in part.interiors
        if not Polygon(ring).buffer(-width / 2.0).is_empty]
```

There *is* a scale dependence there and it is worth naming: the ruler is
absolute (`BORDER_WIDTH_MM / 2 = 0.85 mm`) while the feature scales with
`target_width_mm`. One becker interior measures 1.604 mm at 90 mm (filled) and
1.705 mm at 95.7 mm (survives) — the same hole, opposite sides of a fixed
ruler. Worth 49 stitches. (The genuine perimeter floor is elsewhere —
`RUN_MIN_LOOP_MM = 2.2` at `stage6_border.py:1015` — and nothing in this sweep
comes near it; smallest ring is 9.6 mm.)

## Is becker special?

**The fixture is; the mechanism is not.** Four other fixtures across the same
sweep are all flat or declining:

| fixture | 80 | 90 | 95.7 | 100 | 110 | largest shape |
|---|---|---|---|---|---|---|
| `enthusiast_logo` | +5.9% | +6.9% | +4.7% | +4.4% | +4.4% | 48–76 mm², satin throughout, `explained` 0.96–1.01 |
| `logo_whitebg` | +26.3% | +24.3% | +23.2% | +22.4% | +21.2% | `width_cap` fill throughout — never a ribbon candidate |
| `logo_hotel_fremont` | +8.6% | +7.9% | +7.1% | +7.1% | +5.5% | 1 silhouette part throughout |

What makes becker vulnerable: **one shape carries ~94% of the design's linear
cover, and that shape sits on the `explained = 0.80` boundary.** Any design
with that profile has the same cliff. `logo_gaulke_roofing` is the warning from
the other direction — 6 linear runs and 59–72 mm² of cover at both 80 and
90 mm, i.e. *permanently* collapsed, which is why its 80 mm bill was already
the second-worst on the flip sheet (+22.6%).

## Two corroborating defects found on the way

**Preflight is blind exactly where it matters, and the mechanism is
self-masking.**

| width | cap | grade | stitches | trims | findings |
|---|---|---|---|---|---|
| 90 | none | 88 / B | 6,794 | 26 | `ARTWORK_UNCOVERED` |
| 90 | bean | **76 / B** | 8,550 | 50 | + `TRIM_HEAVY` |
| 95.7 | none | 88 / B | 10,558 | 27 | `DENSITY_EXTREME` |
| 95.7 | bean | **88 / B** | 16,537 | 43 | `DENSITY_EXTREME` |
| 100 | none | 88 / B | 11,373 | 23 | `DENSITY_EXTREME` |
| 100 | bean | **88 / B** | 17,697 | 40 | `DENSITY_EXTREME` |

Preflight catches the *cheap* case (90 mm, 88 → 76) and misses both expensive
ones. `TRIM_HEAVY` is a **rate** — trims per 1,000 stitches. At 90 mm the cap
takes 26 → 50 trims on 8,550 stitches = 5.85/1k and fires. At 100 mm it takes
23 → 40 on 17,697 = 2.26/1k and does not. **The cap's own stitch cost inflates
the denominator that would have flagged its trim cost.**

**`EDGE_CAP_APPLIED`'s `edges` field points the wrong way.**
`stage7_sequence.py:2448` sets `edges = loops + bean_loops`, and `run_outline`
increments `loops` once per emitted *run* — one per **arc** when the gate
splits a ring, one per **whole ring** when it does not. So the field an
operator reads as "how fragmented is this" goes 18 → 25 → 16 as the bill goes
+18% → +26% → +57%. It falls precisely because the cap got more expensive.

## Why nothing caught it

`digitizer/tests/test_edge_cap.py` (22 passed, 33.9 s on this tree) builds its
geometry from synthetic `bar(15, 30)` polygons fed straight into
`resolve_overlaps`/`sequence`. It **never calls `digitize`, never touches real
artwork, and never sweeps size**, so it cannot see a bill whose value depends
on the artwork's tiering. `test_a_crack_is_judged_by_width_not_perimeter` is a
correct test of `_fill_cracks` in isolation and is not what is under stress.

This is the pattern DOCTRINE keeps paying for: a green suite, an honest bill,
and a flag whose real cost nobody swept.

## Fix directions — none implemented, this was a verification pass

1. **The real defect is upstream, in `classify_ribbon`.** `stage6_satin.py:414-417`
   gates a 935 mm² shape on a single scalar within 0.013 of a hard threshold,
   and the scalar is not monotone in design size. `_PROMOTE_EXPLAINED_MIN`'s own
   comment says 0.80 was *"measured best of a 0.5–0.85 sweep … on a plateau
   rather than a knife edge"* — that plateau claim is about **corpus cell
   counts**, not about stability **per shape across size**, and becker refutes
   the latter. Candidates: hysteresis or a band rather than a step;
   area-weighting so a shape carrying most of a design's linear cover cannot
   flip on 0.013; or sweeping `explained` against size for every corpus fixture
   and treating non-monotonicity as the acceptance criterion.
   **This changes the artwork, so it is a bigger decision than the cap.**
2. **Make the cap's bill defend itself.** `stage7_sequence.py:1240-1241`
   returns `None` when a design has no linear runs and the cap silently reverts
   to the full pre-gate cost — the exact regime the gate exists to prevent.
   Either warn loudly when `_sewn_linear_cover` returns `None` or near-empty
   while `edge_cap` is on, or put a cost ceiling on the cap (it already knows
   `_art_st` when it computes `percent`).
3. **Fix the bill's own fields.** Split `edges` into `whole_loops` and `arcs`
   at `stage7_sequence.py:2448` — `c_report` already carries `arcs` and
   `yielded` and stage 7 throws them away. Add the gate's effectiveness
   (`1 - gated/ungated`); it is the one number that would have made this
   visible at a glance.
4. **Give `_fill_cracks` a scale-aware ruler** (`stage6_border.py:866`). Worth
   49 stitches, so low priority — but a fixed absolute ruler against a feature
   that scales with `target_width_mm` will keep producing "the same hole,
   different verdict."
5. **Sweep size before quoting a bill.** `tools/pro_silhouette.py` already
   takes `--width`; the evidence for a flip needs to be a curve, not a point.

## Caveats

- Read-only pass. Nothing under `digitizer_core/`, `app/`, `src/`, `test/` or
  `tools/` was edited; the only additions are this doc and the render set.
- The `hotel_fremont` bill above uses `fill_exposure.SHORT`'s kwargs
  (`max_colors=3, forced_class="flat", border="off"`) and matches the plan
  doc's 80 mm value exactly. An earlier informal reading of "+6.6% → +6.2%"
  must come from different settings; the direction agrees either way.
- `tests/test_edge_cap.py` was run, not the full suite — no code changed, so a
  full run would not have been evidence about this claim.
- **The flip was not touched.** Kent flipped `edge_cap` deliberately; this
  establishes whether it bills correctly, not whether it should be on.
