---
name: fine-bar-survive-2026-11-14
description: "cfg.fine_bar_survive (built OFF): To a T's speed lines were split by stages 2-4, kinked by an anti-aliased sliver, or lost at stage 5 under the white field's under-fill; a broken straight ink bar is redrawn from the art, every straight ink bar keeps its art at stage 5; all 5 of Kent's pins fixed by eye"
metadata:
  type: project
---

**What (Director's order 2026-11-14, ADAPTATIONS item 2):** Kent's 5 To a T
pins on the speed lines (hat "Missing top bar", "Gap/Jump in the line", a
missing bar; beanie "Gap in the line" twice). Eye first, art | OFF | pro, then a
line-by-line trace (`eye_pairs_out/thin-bars-1114/`, primary checkout).

**The mechanisms (not width: ours already sews these 0.8-1.1 mm like the pro):**
- split in stages 2-4: collinear pieces with gaps (hat 2 x 6 mm 0.37 mm apart;
  beanie 20 + 8 mm with a 4 mm hole);
- kinked: a 27 mm white sliver (the bar's anti-aliased edge traced as its own
  shape) ate a 42 mm bar's width, and the satin jogged where it ended. The
  bar's own polygon wanders no more than a healthy bar's, so no geometry test
  on the piece finds it; the sliver beside it does;
- lost at stage 5: by then the white field is an under-fill
  (`silhouette_underfill`, `keyline_folded`) whose polygon covers the bar's
  hole, and the bar is clipped to nothing (`SHAPE_NOT_STITCHED`). Found by a
  `sys.settrace` on `resolve_overlaps` for one shape id (the stage-4
  regions say the field covers 0% of the bar; at stage 5 it covers 100%).

**Built (`digitizer_core/fine_bar.py`, OFF):** a straight thin ink bar is
read off the art's ink (nearer the bar's thread than its host, in a band
along it) and fitted as one straight tapering bar. It is REDRAWN only when
the trace broke it (a same-thread piece inside, ink 1 mm past the piece, or
3 mm of other-colour sliver along it); every such bar keeps its art at
stage 5 when the clip would leave under half. First cut redrew every bar and
widened Fremont's "|" divider (anti-aliased ink): a whole bar keeps its
outline. On: 8 of 11 other pro jobs byte-identical (see the PR for the list).

The flip is Kent's. Next lever if wanted: the lost beanie bar keeps its
narrow trace and sews a thin tail at one end.
