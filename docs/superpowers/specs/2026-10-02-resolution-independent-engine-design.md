# Resolution-independent engine, v1 — design

**Date:** 2026-10-02 · **Status:** design approved in chat by Kent 2026-10-02;
this file awaits his review. No engine code and no plan until he approves it.

## Kent's ruling this rests on (2026-10-02)

> "We shouldn't have to warn the user of anything. the tool needs the ability
> to identify the image it's being given and follow a path to produce the best
> output possible."

This **withdraws** his 2026-10-01 approval of "warn sooner on small files"
(never started). Three calls followed, in order:

1. When an upload lacks detail for the sew size: **rebuild, and show what
   changed** — a quiet note of what the engine did, not a warning and not a
   task for the customer.
2. v1 scope: **shapes only.** Not font re-set, not stroke rebuild, not an AI
   upscaler.
3. Approach: **denominate the pipeline in millimetres**, so it behaves the
   same at any source resolution.

## Problem

The engine's output depends on how many pixels the customer's file happens to
have, at a fixed design size. Measured 2026-09-30 (`tools/lowres_detail.py`,
DOCTRINE "work grid"): downsampled to 5 px/mm, four real logos lose fine ink
their own full-resolution digitization keeps. Kent's ranking on the pairs page
was full-size file, then the 8 px/mm work grid, then the old grid, on every
logo.

The mechanism is not the edge. A 0.7–1.4 mm stroke is 3–5 px; every
superpixel on it holds ink and ground both; the RAG merge compares means and
dissolves the letter. The rules that decide this are counted in PIXELS and
were tuned at 8.4 px/mm and up. A customer's website logo is 4–6.

Inventory on `origin/main` (0c3b7725): about 25 pixel-denominated constants
that affect output. `stage0_classify.py` never reads `px_per_mm` at all.

## Goal and exit

The same artwork at the same design size digitizes the same from a 5 px/mm
file as from a 20 px/mm file, within what the pixels carry. This is ROADMAP
phase 2's exit, for every lane EXCEPT stage 0's routing (see "Out").

**Not claimed:** that a small file equals its full-size self. Enlargement
cannot add information. The claim is that the engine stops losing detail the
file DOES carry.

## Part 1 — the yardstick, before anything else

Promote `tools/lowres_detail.py` to a pinned test. Each high-resolution real
logo is downsampled to 4, 5, 6.5 and 8 px/mm and scored against its own
full-resolution digitization on `agree`, `fine`, stitches and trims.

- **A noise floor is part of the instrument.** On 09-30 half a pixel of
  foreground shift moved ENTHUSIAST's `fine` 0.90 → 0.70. Each cell is read
  over sub-pixel offsets of the downsample; a gain inside that spread is not
  a gain.
- Nothing in part 2 starts until this reads today's loss and its spread.
- Gate 4 applies: no quality claim on a raw agreement number.

## Part 2 — millimetres, one lane at a time

Each constant becomes a millimetre (or mm²) quantity resolved to pixels from
the working `px_per_mm` at run time, **set so it equals today's pixel value at
the resolution it was tuned at**. So each conversion is an identity there and a
change only below it. Order, by measured loss:

| # | Rule | Today | Where |
|---|---|---|---|
| a | RAG merge size gates | `AREA_RATIO_MIN_SMALL_PX` 1000, `BOUNDARY_CONTRAST_MIN_SMALL_PX` 1000 | `stage2_photo_segment.py` |
| b | Thin-ink floor and ring | `THIN_INK_MIN_PX` 3, `_RING_PX` 2, `_MIN_SKELETON_PX` 3 | `thin_ink.py` |
| c | Curve re-fit gate | `_CURVE_MIN_PX_PER_MM` 20 — only Fremont clears it | `stage4_vectorize.py` |
| d | Thread revalidation | `THREAD_REVALIDATE_MIN_PX` 200 / 50 | `stage4_vectorize.py` |
| e | Trace and junction floors | `_MIN_TRACE_PX` 3, `_JUNCTION_CLUSTER_MIN_PX` 3, `_WALK_BACKTRACK_PX` 3 | `stage6_detail.py`, `stage6_satin.py` |

Each row is its own PR behind its own config flag, **built OFF**, flipped by
Kent on renders plus the part-1 table — the way `work_px_per_mm` went.

**A recorded negative governs row (a).** The comment above
`AREA_RATIO_MIN_SMALL_PX` records that lowering it alone, down to 200, left
recovery flat (the ratio condition never fires early in the merge chain), and
that the settings which did recover pushed `drone_render` from 74 to 122
regions. So a unit conversion of the two gates may measure as nothing. If it
does, row (a) is reported as a measured negative and the question returns to
Kent with the number — it is NOT widened into a merge-threshold retune inside
this spec.

## Part 3 — the quiet note

The engine reports what it did as data (`enlarged 1.6x`, `fine strokes kept`),
and the Studio shows one muted line on review. `INPUT_LOW_RESOLUTION` leaves
`ATTENTION_WARNINGS`; the sentence stops asking the customer for a bigger file.
Wording is Kent's; it lands last, after at least one part-2 flip is ON, so the
note describes something the engine really does.

## Out of v1

- **Stage 0's thresholds.** Making routing scale-aware is a recalibration, and
  ROADMAP gate 2 refuses that without real tonal artwork. Blocker named; its
  own spec.
- Lettering re-set from fonts, stroke rebuild, AI super-resolution (Kent's
  scope call above).
- The photo lane's SEEDS constants — a different lane and a different loss.
- Render, OCR and preflight rasters (`stitchviz`, `legibility`, `textcluster`
  OCR, `shapefield`): they do not decide stitches.

## Testing

- Part 1's test, per resolution, with its spread.
- Per conversion: an identity test at the tuning resolution (byte-identical
  plan with the flag ON), then the low-resolution table and renders.
- Goldens re-pin on Linux only, per flip.

## Risks

- **Real:** every flip re-pins goldens, and `digitizer` CI is ~35 minutes a
  round.
- **Real:** superpixel placement noise can exceed the gain (see part 1).
- **Real:** row (a) may be a negative (see above).
- Minor: 6.5 px/mm sources gained nothing from the work grid and may gain
  nothing here.
