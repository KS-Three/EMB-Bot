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

**Result: 1 of 35 runs moves** (9 pro jobs at their own size + 26 `corpus_scorecard`
fixtures at the Studio 80 mm `left_chest` request; compared by md5 of
`design["stitches"]`). 34 are byte-identical, **`toat_machine_hat` and `toat_beanie`
included**. Pictured: 1 of 1 (`mfab_hat_overview.png`, `mfab_hat_closeup.png`,
ORIGINAL | BEFORE | AFTER, close-up at 30 px/mm).

| run | what changed (read from the plan) | by eye |
|---|---|---|
| `mfab_hat` | the mark (`Sb189ad6d`): 2 satin pieces + 2 underlay -> 1 underlay + 3 fill pieces (89.6 + 4.6 + 9.5 mm of fill). It is now sewn before the AND letter `Scb0093ea` instead of after it, so the neighbours in that block re-order and a few travel lengths change. No other shape retagged, merged or dropped. Stitches 20488 -> 20564, trims 25 -> 25, jumps 9 -> 8. | **Better.** One solid blade, crescent top, pointed tail, between the legs. Still a little wide on the left edge. |

**Why the first version was withdrawn.** It also moved `toat_machine_hat`: the mark
there is the DOT OF THE i in "Machine" (a slanted rhombus), and the fill made it an
upright oval. What separates the two, measured: MFab's mark sits 0.99 mm from the N it
is stacked over (0.12 of its mates' height); Toat's tittle sits 13.6 mm from the nearest
member of its cluster (the stem is not one), 2.0 of their height. The rule now needs the
stacked mate within 0.25 of the mates' median height, and also exempts a classic dot
(0.6-1.5 of the stem's width, centred within 0.15 of it; no real instance of that yet,
unit-tested only).

**MFab, no cutout.** This container has no `rembg_isolated`, so MFab renders without the
background cutout Kent's machine uses. The tagging is in stage 4 on the decoded art, so I
expect the fault not to depend on it, but I did not run it with the cutout.

Sweep: `python -m tools.off_line_mark_sweep`. An earlier draft (centre outside the median
band of all mates) moved 8 of 35 and tagged 20 shapes on Gaulke's hat and 31 on the
phone screenshot (multi-line clusters); the per-mate line test replaced it.
