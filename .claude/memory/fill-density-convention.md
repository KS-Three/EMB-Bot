---
name: fill-density-convention
description: "Law 19 SETTLED — pro fill density is quoted between SAME-DIRECTION rows, so EMB-Bot's tatami sews at half professional coverage; satin is unaffected"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6af48c79-e021-4bd9-8487-47656de0c74e
  modified: 2026-08-08T19:34:59.854Z
---

Resolved 2026-08-07 by a two-wave research pass (handoff at
`EMB-Bot/docs/research-handoff-2026-08-07.md`). **Professional fill "spacing"/
"density" is measured between rows sewn in the SAME direction. EMB-Bot's
`FILL_ROW_MM` is measured between physically adjacent generated rows
(`stage6_fill._row_spans`: `y = miny + row_mm*(i+0.5)`). The two differ by
exactly 2×, so our tatami at 0.40 sews HALF professional coverage.**

Four independent lineages agree: Hatch "The spacing setting is the distance
between two **forward** rows"; Wilcom blog "the first is a stitch line and the
next row is a back stitch so the measurement is taken on each second row";
Melco "the distance between stitch lines going the **same direction**" (standard
fill 3.8 pt = 0.38 nominal = 0.19 physical); Wilcom tatami default 0.38.
That is exactly what our 39-file DST corpus measured (0.19-0.20 adjacent) — the
corpus number was never anomalous.

Two checks that do NOT use the convention argument: (1) Coats publishes fill at
~1,250 stitches/in²; our `1/(0.40 × 3.0)` = **538 st/in²**, and the constant only
reconciles near a 0.20 mm row pitch. (2) Ink/Stitch's `row_spacing_mm` default is
**0.25 mm** and its source proves it is adjacent-row (`current_row_y +=
row_spacing`, alternating rows merely direction-swapped) — same convention as
ours, 1.6× denser.

**SATIN IS UNAFFECTED AND CORRECT.** Hatch defines stitch spacing as the distance
between penetrations **on the same side** of a shape; our emitter advances one
spacing per cross with constant A,B,A,B rail order (`stage6_satin.py:1104-1107`),
so `SATIN_SPACING_MM = 0.4` IS the same-rail pitch. Confirmed by Melco (4 pt
default), Embrilliance (4-5 pt, range 0.3-2.0), Madeira (40wt = 0.40), and
Ink/Stitch's own `mm/cycle` unit string: "This is double the mm/stitch
measurement used by most mechanical machines."

**Why:** the engine is right on satin and 2× light on fill — that asymmetry
explains thin-looking fills without implicating the satin work.

**How to apply:** do NOT change `FILL_ROW_MM` on analysis. Block 2 of the
existing sew-out card (`docs/sewout-card-2026-07-31.md`) tests 0.40 vs 0.20 vs
interleaved two-pass and predates the law — it is now the decisive experiment.
Halving the pitch and interleaving two passes at 0.40 give the same coverage but
different fabric behaviour. Either doubles stitch count, thread, and run time;
preflight coverage goes 1.0 → 2.0 units, still under `COVERAGE_WARN_UNITS = 2.5`,
so the grader was already calibrated for pro density. Note `_underlay_paths`
derives lattice spacing from `row_mm`, so underlay moves with it unless pinned.
See [[emb-bot-digitizer]].
