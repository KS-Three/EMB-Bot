# The photo edit tail: a refuted fast path, one flag, and an exact memo

**2026-09-17/18.** Started from "make adding/removing satin borders easier to
preview" and ended somewhere else. Read this before proposing ANY digitizer
performance work — two of the three findings are things not to do.

## 1. A stale number scoped a whole task. Measure first.

`DigitizePanel.svelte` carried *"0.65s on simple line art but ~10-14s on a real
photograph, with no useful cache"*, dated **2026-08-13** — nine days before the
stage 0-4 generation cache landed. A border edit HITS that cache
(`generation_key` strips `shape_overrides`), so only the tail re-runs.

Measured at customer defaults: the border-edit tail is **0.95–3.61 s across five
logos**. On a logo there was never a 10-14 s to remove. A "border-only service
fast path" was scoped on that stale sentence, approved, and dropped before any
code was written.

**The number had also been copied forward into a PR body**, which is how it
survived. A figure in a code comment is a measurement with a date, not a fact.

## 2. One flag is ~58% of the photograph's edit tail

Bisected on `owl_kent.jpg`, customer defaults, baseline tail 72.42 s, noise
floor ±0.40 s:

| flag OFF | saved | share |
|---|---|---|
| **`fill_travel_under_cover`** | **41.67 s** | **57.7%** |
| `subpixel_edges` | 9.32 s | 12.9% |
| `borders_last` | 4.36 s | 6.0% |
| `curve_turn_deg` | 2.83 s | 3.9% |
| `edge_cap` | 0.95 s | 1.3% |
| `design_ramp`, `satin_house_fourfold`, `enclosed_by_garment` | ≤0.3 s | **INERT** — byte-identical output |

Holds on `drone_render`: 48.8%. `_reorder_for_cover` landed in **PR #454,
2026-09-11** — a month after the 6.63 s tail of 2026-08-13. That is the growth,
and it was deliberate, not a regression.

**Flipping it is not free and is Kent's call:** +2,500 stitches on owl_kent,
+1,364 on drone_render, and it re-exposes the travel it was built to hide
(286 → 90 mm on the Hotel Fremont field; 204 → 8 on gaulke).

**Denominator trap:** these are % of the EDIT TAIL. `flag-runtime-bills`' older
table is % of TOTAL digitize time. The same 41.67 s is 50.7% of total and 57.7%
of the tail. Do not compare the two tables' percentages.

## 3. The fix was a memo, and the obvious design was the wrong one

**Measured:** 80 of owl_kent's 82 shapes do byte-identical fill work across a
border toggle. Both fill reorders are pure functions of ONE shape's own inputs —
`_reorder_for_cover`'s `sewn` accumulator starts at None and unions only the
paths it was handed. So a content-keyed memo is EXACT: 79.34 → **44.61 s**,
verified against the same edit computed cold.

**The rejected design, which was approved first and would have shipped a bug:**
skip the cover reorder on interactive restitches, keep it for export. Two
independent reasons it fails, both worth remembering:

- **`/export` does not re-run the pipeline.** It encodes the design it is
  handed, and `DownloadStep` hands it `element.result`. Preview quality would
  have shipped verbatim.
- **The preview would have looked wrong** — 3-25x more exposed travel, i.e. the
  exact *"the in-fill stitching doesn't look clean"* complaint that created the
  flag on 2026-09-02.

**The memo's one failure mode:** it is safe only while both reorders stay pure.
A future dependency on sew order, another shape, or module state turns it from a
cache into silent corruption. `tests/test_fill_reorder_memo.py` leads with that
property for that reason.

## Still open

- A **cold** photo digitize is ~90 s and still pays the flag in full. The memo
  helps re-stitches only. MASTER_SCOPE queue item 18.
- `flag-runtime-bills`' 2026-09-13 boost-off caveat is **unresolvable from a
  cloud session** — it needs `flagcost.py` against the gitignored corpus.

Detail: `docs/flag-runtime-bills-2026-09-12.md`, `docs/scope/5-review-manual-editing.md`, PRs #504/#505/#508.
