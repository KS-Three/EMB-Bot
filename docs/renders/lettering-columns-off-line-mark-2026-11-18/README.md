# lettering_columns_off_line_mark: 2026-11-18 (built OFF)

Fault: `mfab_hat`, the small pointed black mark at the foot of the big M's inner V
(design x 14-19, y 21-27.5 mm). Sewn as a ragged black blob over the white legs,
running down beside the N of AND.

**Cause (stage 4 text tagging, then the Column lane).** The mark's polygon is fine
(an 11-vertex wedge, 12.4 mm^2). The text-cluster tagger put it in the "AND" cluster
(`TC5404afcc`; letters y 24.8-33.3, the mark's centre y 23.8). The Column lane then
sewed it as two satin pieces at different angles that cross mid-shape and overshoot
the polygon onto the white. Handed back to the ordinary ladder it is still satin
(`classify_ribbon`: ribbon_w 1.22 mm, aspect 7.3, as its medial axis is a long bent
line), three pieces, so the fix also sews it as fill.

**Flag.** `lettering_columns_off_line_mark` (default OFF, byte-identical OFF): a
text-cluster member that shares a line with none of its mates (under 50% vertical
overlap with every one), is glyph-sized (at least half the mates' median height) and
is stacked over a mate (at least half its width over that mate's x range) is not a
letter: the lane refuses it and it takes the fill tier.

**Result: 2 of 35 runs move** (9 pro jobs at their own size + 26 `corpus_scorecard`
fixtures at the Studio 80 mm `left_chest` request; compared by md5 of
`design["stitches"]`). 33 are byte-identical. Pictured: 2 of 2.

| run | what changed (read from the plan) | by eye |
|---|---|---|
| `mfab_hat` | the mark (`Sb189ad6d`): 2 satin pieces + 2 underlay -> 1 underlay + 3 fill pieces (89.6 + 4.6 + 9.5 mm of fill). It is now sewn before the AND letter `Scb0093ea` instead of after it, so the neighbours in that block re-order and a few travel lengths change. Stitches 20488 -> 20564, trims 25 -> 25, jumps 9 -> 8. | **Better.** One solid blade, crescent top, pointed tail, between the legs. Still a little wide on the left edge. |
| `toat_machine_hat` | the tagged leaf mark (`Sae425293`, 9.7 mm^2): underlay + 1 satin (75.9 mm) -> short underlay + 1 fill (68.4 mm). It moves to the head of its block and the block's run order shuffles around it. Stitches 17207 -> 17223, trims 22 -> 20, jumps 10 -> 12. | **Mixed, named first.** Fewer trims, but the leaf in the art is a slanted rhombus with a lower point; the fill is a rounder upright oval and loses that point. The old satin was ragged but kept the lean. |

Pictures: `*_overview.png` and `*_closeup.png` (ORIGINAL | BEFORE | AFTER; closeups at 30 px/mm).

**MFab, no cutout.** This container has no `rembg_isolated`, so MFab renders without the
background cutout Kent's machine uses. The tagging is in stage 4 on the decoded art, so I
expect the fault not to depend on it, but I did not run it with the cutout.

Sweep: `python -m tools.off_line_mark_sweep`. An earlier draft (centre outside the median
band of all mates) moved 8 of 35 and tagged 20 shapes on Gaulke's hat and 31 on the
phone screenshot (multi-line clusters); the per-mate line test replaced it.
