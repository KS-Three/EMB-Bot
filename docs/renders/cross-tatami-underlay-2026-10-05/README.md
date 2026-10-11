# `cross_tatami`: the fabric preset's underlay beside the crossing pass — 2026-10-05

Underlay only. Red is every `UNDERLAY` run in the plan; grey is the top
stitching drawn faint. The Studio preview draws underlay beneath the top
thread and cannot show this.

| file | arm |
|---|---|
| `*_preset.jpg` | the garment's fabric preset (`edge_run` on all three) |
| `*_cross.jpg` | `underlay_style="cross_tatami"` design-wide |

Hotel Fremont patch (`patch`), Bridge Bar and the drone thermal badge
(`left_chest`), 80 mm, `max_colors=6`. All three class `gradient`, so **both
arms run `blend_fallback_underlay=True`**; without it neither arm puts any
underlay under these fills.

## Numbers

| case | stitches | trims | underlay under fills, % of the fill's thread |
|---|---|---|---|
| fremont | 13,779 → 14,388 | 43 → 39 | 4.0 → 12.3 |
| bridge | 18,083 → 18,507 | 98 → 113 | 6.5 → 10.0 |
| drone | 19,283 → 19,846 | 131 → 139 | 4.0 → 8.2 |
| becker (flat class) | 6,557 → 6,540 | 38 → 35 | 8.1 → 8.0 |

## Our own file, read back

Each `cross` plan was written to DST by the `/export` writer and read with the
audit's classifier — the instrument that read the professional's files
(`docs/underlay-audit-2026-10-05.md`).

| fill | verdict | row pitch mm | median stitch mm | angle to top ° | share of top thread % |
|---|---|---|---|---|---|
| fremont, 2,268 mm² | crossing pass | 1.00 | 2.4 | 90.0 | 9.2 |
| bridge, 1,514 mm² | crossing pass | 0.99 | 2.5 | 88.5 | 5.0 |
| drone, 2,063 mm² | crossing pass | 1.00 | 2.5 | 90.0 | 8.9 |
| drone, 215 mm² | crossing pass | 1.00 | 2.55 | 89.9 | 5.1 |
| the professional, 34 fills, p50 | crossing pass | 0.98 | 3.99 | 89 | 16.1 |

**Where ours falls short of his, plainly:**

- **Median stitch 2.4–2.5 mm against his 3.99.** The pass is laid at 4.0 mm
  and 4.0 is the commonest stitch on Fremont's ground (210 of 697), but these
  grounds are cut up by lettering and every row that meets a letter ends in a
  short stitch. The first run of this table read exactly 2.0: `stitch_shape`
  was re-splitting every underlay path at the lattice's 2.5 mm, halving each
  4 mm stitch. Found here, fixed, and pinned by
  `test_the_sewn_pass_keeps_its_four_millimetre_stitch`.
- **Thread share 5–12% against his 16%.** Ours stops 1.0 mm inside the edge
  (`UNDERLAY_INSET_MM`) and stays out of every hole; where that inset splits a
  shape only the largest piece gets a pass, which is the bare patch low in
  the middle of `fremont_cross.jpg`. Both are older rules this change does
  not touch (research option 3).
- **Becker shows nothing.** At 80 mm its one fill is too narrow for a row
  the classifier can see, and the plan barely moves.
- **Bridge Bar pays 15 trims** (98 → 113), drone 8; Fremont gets 4 back.

Not sewn. Nothing here says what the pass does on cloth.
