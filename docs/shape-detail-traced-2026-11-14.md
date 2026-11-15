# Shape detail lost: Kent's pins traced to a stage (2026-11-14)

Kent's pin family "shape detail lost" (census class 3 in
`agent-eye-1113/census_table.md`: 16 groups, 18 pins, on 10 of his sat
designs): the element is there but its shape is wrong. A blob where the art
has a figure, points rounded off, an inner shape simplified away. Each pin
was looked at by eye (art | ours | pro), then traced on main `f49d5b1a`
(Kent's 11-14 flips in) with the corpus request (`tools.pro_pair.digitize`,
80 mm on `left_chest` for the Commons designs, the pro job's own garment and
width otherwise). The trace printed the traced polygon (stage 4's output) over
our needles at 40 px/mm, so a pin is either lost BEFORE stage 4 (the polygon
lacks it) or AFTER (the polygon has it and the thread does not).

Counts are counts, n = 1 design each; no agreement figure is claimed (ROADMAP
gate 4). Pictures, gitignored, in the primary checkout:
`digitizer/eye_pairs_out/detail-1114/` (`pins/` art | ours | pro at every pin,
`trace/` the polygon overlays, `sheets/` the OFF | ON sheets).

## Tally

| pin | design | what the shape lost (eye) | stage | evidence | the pro |
|---|---|---|---|---|---|
| #2 | and_pizza | the I's foot is not a crisp rectangle | 6, satin end at a flat edge | traced in `docs/satin-flat-ends-2026-11-14.md` (the cap's last cross stops short) | no file |
| #3, #4 | and_pizza | the Z's foot is not straight | 6, two Column pieces butt at the acute joint | same doc: `lettering_columns_apex_cut` cures it | no file |
| #5 | and_pizza | the &'s pointed terminal ends blunt | 6, the terminal's crosses fan | same doc (V terminal) | no file |
| #20, #21 | and_pizza | the Z's top is not flat | 6, the joint again | same doc: apex_cut cures it | no file |
| #5 | k_line | the I's top is not flat | 6, the cap stops short | same doc (0.4 mm before the end) | no file |
| #6 | k_line | corners not square | 6, satin end at a corner | by eye, same family; not traced on its own | no file |
| #2 | dot_music | not a clean corner | 6, satin junction at a concave corner of a text-tagged `m` | by eye | no file |
| **#1** | **dot_music** | **the notch cut into the disc is gone** | **5, a fill's pull growth** | the polygon keeps the slot (inscribed 0.64 mm); the pull grows 0.3 mm in from both walls and the band round the disc welds its mouth | no file |
| **#1** | **Ahora** | **a gear sewn as a circle** | **6, satin rails** | the polygon keeps all 16 teeth (244 vertices; 18 tooth gaps 0.48-0.74 mm across); the rails are a smoothed offset of the spine (median over 5 stations, 4 averaging passes), so the crosses run over every gap | no file |
| #1 | low_poly | the triangles' tips rounded off | 6, tier: narrow facets sew as satin | the white triangle is traced exactly (4 vertices) and filled; its neighbours, 0.45-0.73 mm wide, sew as short satin columns whose round ends lie over its tips | no file |
| #3 | low_poly | all detail in the fine shapes lost | 2-3, colour cap + sub-thread lines | facets sewn as 1.75 mm² rescued satins; the art's facet lines are 1 px (0.13 mm at 7.9 px/mm) and the greys share 6 threads | no file |
| #6 | Becker | the A's counter is not a triangle | 0-1, source resolution | the art is 1.42 px/mm: the counter is about 4 x 2 source pixels. `outline_redraw_k` (0.75 since today) is the lever we have | redraws a crisp triangle and a crossbar |
| #7 | Bridge | the handle lacks its little jut-outs | none of ours: the art has none | the art's handle is a plain spindle (4.4 px/mm) | adds a collar nub (director-night: his change is the handle's SHAPE) |
| #3 | Fremont | the rope's end does not finish cleanly | 3-6, the art's twists sewn one by one | each drawn twist is its own piece | one satin rope |
| #2 | Drone | "I cannot tell this is a drone" | 0, photoreal art (gate 2) | whole element, not one shape | redraws it flat |
| #1 | comic_halftone | "the N isn't an N" | 6, a letter's stroke junction steps | by eye | no file |

One neighbour from census class 15 ("blob") belongs here and is counted
below: **crest #3, "Can't tell what this is"**, the eagle's open beak. Its
polygon (93 vertices) keeps the open mouth; one satin column covers it, so
the beak sews as a red blob. Stage 6, satin rails, the same mechanism as
Ahora's gear.

Left out, with their owner: merged letters and closed counters (k_line #1,
hed_p_e #2 and #3: `counters-1114`); the isometric icon's blobs (shaded
pile-ups on tonal art: Phase 4, gate 2); Becker #5 (a stroke junction);
Bridge #3, "thicker than the image" (pull and thread width: gate 1).

## By cause (18 class-3 pins, plus crest #3)

| cause | pins | stage | whose |
|---|---:|---|---|
| satin end, corner or tip at a flat edge (lettering construction) | 9 | 6 | `apex_cut` and its guard (apex-like-pro); flat satin ends (`docs/satin-flat-ends-2026-11-14.md`, the next wave) |
| **an inlet in the outline, kept by stage 4, sewn over** | **2 + crest = 3** | **5 (fill growth), 6 (satin rails)** | **this PR** |
| the pro redraws what the art draws | 3 | 0-1 / none | not geometry: redraw (Becker's partly `outline_redraw_k`) |
| narrow facets as satin, the colour cap | 2 | 2-6 | low_poly only |
| a letter's stroke junction | 1 | 6 | lettering lane |
| photoreal art | 1 | 0 | gate 2 |

The largest cause, satin ends at flat edges, is already traced and owned
(apex-like-pro is building the `apex_cut` guard; the flat-end construction is
in the next wave). Neither pull compensation's magnitude nor the satin width
floor (gate 1) is the largest cause. The next largest that geometry can
settle is the outline's own INLET: a gap the art keeps inside a shape's outer
outline but open to the outside (a gear's tooth gaps, an open beak, a notch).
The polygon keeps it and the thread sews over it, two ways.

## The fix: `cfg.extra["outline_inlets_kept"]`, built OFF

`digitizer_core/outline_inlets.py`. An inlet is what closing the outer
outline with a 1.0 mm disc adds (`GAP_PROTECT_MM / 2`: an inlet under 2 mm
across), in pieces at least 0.5 mm across (`GAP_SEWABLE_MM`) and 0.1 mm² in
area (a 90-degree corner's fillet is 0.34 mm across, so corners are not
inlets). Holes are counters and stay `growth_keeps_gaps`'s.

1. **Stage 5, a fill:** its growth stays out of its own inlets that no other
   artwork fills, and out of the pull band at their mouths (without that, the
   first build opened the slot and welded its mouth). An inlet another colour
   fills is a seam and is left alone. Free fill angles are pinned to the OFF
   pass, as the fat-ink flags do, so a kept notch cannot tip a near-tie row
   angle.
2. **After stage 7, a satin:** a shape whose satin thread (needle path plus
   0.2 mm) covers half or more of one of its own inlets, and inlet area of at
   least 3% of the shape in all, cannot draw that shape; it is planned again
   as a fill, on a copy of the regions, through the `tier = "fill"` field
   every stage-5/7 reader honours.

Neither part touches a letter (text-tagged: its openings are the lettering
lane's) or a shape whose tier was set by hand.

**The 3% gate is measured, not guessed.** The first build re-planned
Becker's black border as a fill: its outer edge dips between the letters,
and its satin sews over the dips. The pro sews that border as a satin band
too, so moving it was a step away from his file. Inlet area as a share of
the shape: Ahora's gear 0.104, Becker's border 0.002.

Only where thread goes changes. Whether a kept inlet stays open on the cloth
is the sew-out's to settle.

## What it does (sheets in `eye_pairs_out/detail-1114/sheets/`)

- **dot_music #1:** the notch is cut into the disc and open at its mouth, as
  the art draws it.
- **Ahora #1:** the gear sews as a fill and its teeth show. The catch: a
  1.1 mm ring sewn as short fill rows reads rougher than OFF's smooth satin
  ring. The shape is right; the texture is the price.
- **crest #3:** see the PR body (run still out when this was written).
- **Must not move:** k_line, byte-identical ON (design md5 `213ff7a7...`
  both ways); Becker and and_pizza in the PR body.

## Not built

- Satin rails that follow a toothed edge. The rail smoother and the envelope
  exist to stop exactly that ("on the cloth a tooth", `_drop_short_reaches`),
  so a satin that keeps teeth is a construction question with sew-out
  history, not this PR.
- low_poly's facets: a tier and colour-cap question on one shaded design.
