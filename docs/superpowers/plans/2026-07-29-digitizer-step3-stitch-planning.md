# Digitizer Step 3 — Stitch Planning (regions → sewable stitches)

Blueprint: Kent's Auto-Digitizing Engine Blueprint v2.1 + the v2.2 amendments
(2026-07-29). Builds directly on step 1 (`5fcf41b`, stages 1–4).

**Sequencing note.** The blueprint orders SAM 2 as step 2 and stitch planning
as step 3. Kent chose to take step 3 first (2026-07-29): the `Segmenter` ABC
built in step 1 means a `SamSegmenter` drops in later without touching any
stitch code, so nothing is wasted — and step 3 is what first produces output
that can be sewn and judged, which is the milestone-3 sew-out gate.

## Scope

Regions (mm polygons, y-down) → a `StitchPlan` that can be written to DST and
sewn. **Fill path only.** Satin is the blueprint's biggest single work item and
is step 4; step 3 must therefore *detect* shapes too thin to fill well and warn
rather than sew them badly in silence.

In scope:

1. Machine-physics constraint table + fabric presets (ported from the JS engine).
2. Sew order across threads, and overlap resolution consistent with it.
3. Pull compensation.
4. Tatami fill: angle, density, staggered penetrations, stitch-length control.
5. Underlay per shape, in the styles the fabric preset names.
6. Travel routing inside a shape; jump/trim when travel is not possible.
7. Tie-in / tie-off lock stitches; short-stitch filtering.
8. `StitchPlan` → DST via pyembroidery, cross-checked against the JS decoder.
9. Debug renders of the stitch path.

Explicitly NOT in scope (resist creep): satin columns (step 4), the stitch
processor / re-density of imported designs (later), preflight scoring (step 9),
FastAPI (step 8), EMB-Bot UI (step 10), directional (per-axis) pull comp.

## Sew order comes first, and overlap follows it

These two decisions are coupled, and getting them out of order produces a
visible defect on fabric: if region A is grown so it tucks under region B, A
**must** sew before B, or the grown edge sits on top and the seam shows.

So the order is decided once, up front:

1. Threads sew in descending total area (stage 2 already orders layers by pixel
   weight — largest first). Background and large areas go down first, small
   detail last, which is also what keeps details crisp.
2. Ties are broken by thread number, so the order is deterministic.
3. Overlap resolution then grows each region by `overlap_mm` **only where it
   touches a region that sews later**, never where it touches an earlier one.

`overlap_mm` default 0.25 mm — enough to survive fabric pull, small enough that
it never reads as a color error.

## Machine constraints (`machine.py`)

One module, every number named and justified, nothing magic anywhere else.

| Constant | Value | Why |
|---|---|---|
| `MAX_STITCH_MM` | 12.1 | DST records encode ±121 units of 0.1 mm — a hard format ceiling, not a preference |
| `FILL_STITCH_MM` | 4.0 | Standard tatami run length |
| `MIN_STITCH_MM` | 1.0 | Below this the needle re-enters the same hole: thread breaks, needle wear |
| `TINY_STITCH_MM` | 0.5 | Filter floor — anything shorter is dropped outright |
| `FILL_ROW_MM` | 0.40 | Standard fill density (2.5 rows/mm) |
| `FILL_STAGGERS` | 4 | Penetrations realign every 4th row; without this, needle holes line up into visible channels through the fill |
| `TRAVEL_STITCH_MM` | 2.5 | Travel runs shorter than fill so they hide under later coverage |
| `TRAVEL_INSET_MM` | 0.6 | Travel keeps this far inside the edge so it never shows past the outline |
| `UNDERLAY_INSET_MM` | 1.0 | Edge-walk underlay sits inside the finished edge |
| `UNDERLAY_STITCH_MM` | 2.5 | Underlay is structural, not decorative |
| `UNDERLAY_ZIGZAG_MM` / `_LATTICE_MM` | 2.0 / 2.5 | Row spacing for the two sparse underlay fills |
| `MIN_FILL_WIDTH_MM` | 1.2 | Narrower than this cannot hold a fill — satin's job (step 4), warned here |
| `TIE_STITCH_MM` | 0.8 | Lock-stitch leg length |
| `TIE_STITCHES` | 3 | Three legs, the standard lock |
| `TRIM_AT_MM` | 3.0 | Longer needle-up moves get cut instead of left as a float |

Fabric presets (`fabrics.py`) are a straight port of `src/fabrics.js` — the same
7 presets, same values, so the Python engine and the browser engine make the
same physical choices until sew-outs say otherwise. They drive pull comp,
underlay style, density adjustment, and trim distance.

## Stage contracts

**Stage 5** `resolve_overlaps(regions, cfg) -> (regions, warnings)` — sew order
assignment + underlap growth + pull compensation, all as shapely buffers.
Guard: pull comp on a shape with a thin waist can swallow its own hole, so a
hole that would shrink below `min_detail_mm²` is preserved at that floor and
counted.

**Stage 6** `fill_region(region, params) -> [StitchRun]` — the fill itself.

- Angle: per-region PCA major axis (carried over from the JS engine, where it
  measurably beat a fixed 45°), overridable per region.
- Rotate the polygon so rows are horizontal, scan at `row_spacing`, intersect
  each scanline with the polygon via shapely (not hand-rolled parity — the
  robustness matters more than the speed here), then rotate points back.
- Along a row, stitches land every `stitch_length`, offset by
  `(row_index % staggers) / staggers` of a stitch — the stagger that stops
  penetration channels.
- Row ends are exact: the last stitch of a row lands on the span end, and a
  stub shorter than `MIN_STITCH_MM` is merged backwards rather than emitted.
- Spans are grouped into connected sections (spans overlapping in x on adjacent
  rows); within a section, boustrophedon.

**Travel** between sections, in order of preference: a straight run if the
segment stays inside the shape; else a run following the shape's inset boundary
ring the short way round; else needle-up jump, trimmed past `TRIM_AT_MM`.

**Stage 7** `sequence(plan_items, cfg) -> StitchPlan` — nearest-neighbour shape
order within a thread (start point of the next shape nearest the end point of
the last), tie-in before the first stitch of a block and tie-off before every
trim and at the end of a color, then the short-stitch filter as the last pass
over the whole plan.

## Data model (`stitches.py`)

```
Stitch      = (x_mm, y_mm)                     floats, y-DOWN, origin art center
StitchRun   = points + kind: fill|underlay|travel|tie
StitchBlock = thread_index + runs + shape_id provenance
StitchPlan  = blocks + palette + stats + warnings
```

`StitchPlan.stats` carries stitch count, per-color thread length estimate,
color changes, trims, and bbox — the numbers a review screen shows and the
numbers a regression test can pin.

## Export

`export_dst(plan) -> bytes` via pyembroidery (MIT, pure Python — no new binary
weight). Verification is deliberately cross-implementation: write the DST,
decode it with pyembroidery, and *also* decode it with the JS engine's own
`decodeDST` through node, then compare stitch counts and bbox. A format bug that
fools one decoder does not usually fool the other.

## Acceptance

1. Fill a plain rectangle: row count matches `height / row_spacing` ±1, every
   stitch ≤ `MAX_STITCH_MM`, none below `TINY_STITCH_MM`.
2. Stagger is real: penetration x-positions on rows 0 and 1 differ by a quarter
   stitch; rows 0 and 4 agree.
3. Ring fixture: no stitch segment crosses the hole (the classic defect).
4. Touching two-color fixture: the earlier color's fill extends under the later
   one; the later one is not grown into the earlier.
5. Full fixture end-to-end → DST bytes that both decoders read with matching
   stitch count and bbox, and bbox width within 0.5 mm of `target_width_mm`.
6. Determinism: two runs byte-identical, same as the step-1 rule.
7. Thin-bar fixture (~2 mm) raises the too-thin-to-fill warning rather than
   silently sewing a one-row fill.

## Method

Step 1's lesson, repeated deliberately: **smoke-test and look at the debug
renders before writing tests.** That order found 5 real defects in step 1 that
tests written first would have simply frozen.
