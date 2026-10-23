# ProSeal's bubble borders: why ours rings them and the pro's file does not (2026-10-22)

Kent's question: on the ProSeal logo our output puts a satin border on each
little blue bubble; the pro's file has none. Why?

Measured on Kent's own job files (`scratch_kent/Embroidery Files/Proseal/`,
gitignored): the art `PROSeal Logo.jpg`, the pro's `PROSEALHAT.DST`
(85.9 x 63.3 mm, 5,894 stitches, 54 trims, 4 colour changes) and
`PROSEALHAT BEANI.DST` (75.0 x 55.4 mm, 48 trims, 5 changes). Ours was
digitized the Studio's way through `tools.pro_pair` (hat preset, 85.9 mm,
the engine at `94eef9cb`). Renders: `docs/renders/proseal-bubble-borders-2026-10-22/`
(the spray crop, 28-52 mm x 12-36 mm of the design, art | ours | pro).

## The answer

**It is not the border tier.** `cfg.border` is `None`, which a logo reads
as "off", and `borders_last`, the seam-ownership rule and `bg_border_*`
(a background detector) never touch a bubble. Two things read as a border,
and which one depends on the bubble's size:

| bubbles | size (mm) | what ours sews (OFF) | what the pro sews |
|---|---|---|---|
| 16 spray + honeycomb hexagons at or over the detail floor (`min_detail_mm`² = 2.25 mm²) | 2.0-3.7 across, up to 4.6 in the honeycomb | **tatami fill** (45-82 points, 2-3 underlay points) **plus a bean edge-cap ring** round each one (53-60 points, `__edge_cap__`, role `edge_cap`) | **one satin blob**: 15-32 stitches at 1.1-2.8 mm, crosses the hex at ~0.37 mm pitch, nothing round it |
| 6 smallest spray hexagons, under the floor | 1.1-1.3 across | a **bean run on the outline** only, bare cloth inside (`SMALL_SHAPES_AS_RUN`, `rescued_small_shape`) | the same satin blob, 15 stitches at 1.6-1.7 mm (the pro sewed them a third bigger than the art) |
| 3-4 half-hexes at the spray's edge | 0.8-1.6 | not sewn (`stitched: false`) | satin, 1.3 x 2.9 mm, 23 stitches |

The ring Kent saw is the **edge cap**. The chain on a 2-4 mm hexagon:

1. `stage6_satin.classify_ribbon` refuses it for **aspect**: its width
   (2 x inradius) fits the 5.0 mm hat ceiling, but its length estimate
   (half the perimeter minus one width) is ~1.3 widths against the 3 a
   ribbon needs. A hexagon, a circle, a square: all "aspect".
2. So stage 7 sews it as tatami rows. Every row end on an isolated island
   stands in open air.
3. `cfg.edge_cap = "bean"` (ON since 2026-09-11) caps every stretch of the
   silhouette with no linear stitching on it: a three-pass bean run round
   each bubble, 53-60 points, in the bubble's own cone. That is the
   "border".

The six under-floor bubbles are the run tier's ring, a different
mechanism with the same look, and the sibling flag `small_solids_satin`
(built OFF 2026-10-20, PR #1023) already answers it.

**The pro's rule, one sentence:** a compact solid up to the satin ceiling
(1.6-4.8 mm across on the hat, up to 5.5 on the beanie) is one satin
column across its short side at the satin pitch, with no fill, no
underlay and no outline; a ring appears nowhere in the spray or the
honeycomb (block 4 of the hat DST: 30 pieces, 28 of them under 6 mm, all
satin by stitch length).

## The flag: `compact_solids_satin` (OFF)

`PipelineConfig.compact_solids_satin`, default `False`, read once in
`stage7_sequence.stitch_one` right after the satin tier declines a shape:

- the shape is "auto", `cfg.satin` is on, the classifier's verdict is not
  satin and its reason is exactly `"aspect"` (width already under the
  ceiling; a `width_cap` refusal stays a fill);
- not lettering (`columns.is_lettering`; note `lettering_columns_skip_blobs`
  already untags a solid blob), not riding a design ramp (the gradient
  ruling), no hole and a bare inside under a ring (`is_small_solid`, the
  sibling rule's own test, on the artwork polygon);
- then `stage6_satin.small_solid_satin` sews ONE column across the
  short side of the shape's minimum rectangle at the block's satin pitch
  and the design's ceiling, on **`p.polygon`** (the stage-5 polygon the
  fill would have sewn; the satin tier sews `p.polygon` too). On the
  artwork polygon the column stopped a pull width inside the silhouette
  and the cap ringed it anyway; measured on `S55719e33`, satin x 2.32-5.32
  against the cap's 1.91-5.72.
- Satin is linear cover (`_LINEAR_KINDS`), so the edge cap omits that
  edge by its own gate. No cap rule changes, no new constant: the ceiling
  is `machine.satin_ceiling_mm` (5.0 hat), the pitch the satin tier's own.

A column that comes out empty (fewer than two crosses, a chord over the
ceiling) falls through to the fill as before.

**The JS twin is not needed.** `src/digitize.js` has no aspect test:
`thin = widthMmFinal <= satinMaxWidthMm && holes.length === 0`, so the
browser engine already sews a compact blob under its ceiling as satin.

## Measured, ProSeal at 85.9 mm (hat)

| arm | stitches | trims | bubbles | md5 `ours.dst` |
|---|---|---|---|---|
| OFF (main `94eef9cb` and this branch) | 7,767 | 55 | fill + cap ring | `54e345c3dd7fdc4fab2381801c419380` |
| `compact_solids_satin` ON | 6,386 | 40 | satin blob, no ring (16 of 16) | `dbc4e4d7d53ccb9c95cc1c2f09f7c889` |
| + `small_solids_satin` ON | 6,320 | 41 | the six smallest also satin | `51cd6d551928aad0267c04a623bbbd11` |
| pro | 5,894 | 54 | satin blob | |

Per bubble, ON: `S3ce7f795` (2.1 x 2.4 mm) 45 fill + 3 underlay points
-> 16 satin points, no cap; `S55719e33` (3.0 x 3.3) 67 + 10 + 56 cap -> 22
satin; `S7bd13cbf` (3.1 x 3.3) 77 + 10 + 59 cap -> 26 satin. The pro's
same-size pieces are 21-29 stitches.

One difference left ON: the pro sews every hexagon at one angle; ours
takes each shape's own minimum-rectangle axis, and a regular hexagon's is
ambiguous, so neighbours in the honeycomb lean differently. The emitter has
no angle parameter today.

## What moves on the other paired jobs

Hotel Fremont (hat, 92.6 mm) and MFab (hat, 104.9 mm) OFF/ON runs were still
in flight when this PR opened; their numbers and renders land in a follow-up
commit on this branch.

## What is Kent's

- The flip. Gate 1: whether a 4.8 mm satin dot on a cap holds (the pro's
  do; ours has not sewn one).
- Whether `small_solids_satin` flips with it: the two together are the
  pro's spray.
