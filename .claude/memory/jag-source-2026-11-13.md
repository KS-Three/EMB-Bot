---
name: jag-source-2026-11-13
description: Kent's 49 smooth/straight pins traced stage by stage — (b) stage-4 chord facets 18, (a) source pixels 10, (d) stitch construction 21 over 3 mechanisms; `outline_redraw_k` built OFF for (a)+(b); satin ends forming flat edges (14 pins) is the next lever
metadata:
  type: project
---

Director's brief 2026-11-13 under Kent's "find that light switch tonight": find
where the jag ENTERS at each pin Kent placed for "should be smooth / straight
/ square / tips rounded", by eye, and fix the majority cause.

**Tool.** `digitizer/tools/jag_strips.py`: `capture` pickles every stage of
one digitize, `strips` cuts one strip per pin (source pixels at native
resolution | mask | stage 4 | stage 5 | our needles | pro). Pins come from the
defect-marks sittings (1110/1111/1112). Run it from a lane with
`EMB_EYE_PAIRS` pointing at the primary's `eye_pairs_out`. ONE digitize at a
time.

**Tally (49 pins, 12 designs; `docs/jag-source-2026-11-13.md`).** No
majority:
- (b) stage-4 chords on clean curves: 18. 14 of them are and_pizza's bowls.
  The cause is `_refine_curves`' one-raster-pixel floor, which leaves 12-20
  degree facets on a 4 mm bowl at 22 px/mm.
- (a) source pixels / mask: 10 (Becker 1.42 px/mm, MFab 3.85, ProSeal M,
  low_poly's stage-3 keyline junctions).
- (d) stitch construction: 21, in three mechanisms. 14 are satin ENDS making
  a flat edge or corner, 4 are rail wobble on rings, 3 are fans at cusps.
- (c) pull comp and (e) the renderer: 0 as primary.

**Built:** `outline_redraw_k` (default None). It reuses letterform priors'
line/arc geometry on every shape, capped at max(0.75 source px, 1 grid px),
on UPSCALED sources only. A clean upload is byte-identical (md5 on k_line,
n_sync, ahora, and_pizza). `outline_redraw_native` (OFF, not recommended)
adds arcs-only on clean uploads (the (b) cure).

**Readings (n=1 per design, instrument only).**
- Upscaled: roughness Becker 8.30 -> 5.25, Bridge 6.78 -> 6.11, MFab
  7.11 -> 6.81. Becker's staircase border sews as one even band. Cost: Becker
  +24 mm of travel on bare fabric (stage 7 re-sequenced).
- Native opt-in: the polygons' facets are gone, but the stitches are mixed.
  The and_pizza "p" sewed a straight cut across a perfect arc and opened a
  seam, and n_sync's roughness rose 6.77 -> 7.92. On clean art the Column
  lane's satin, not the polygon, sets the edge.

**How to apply:** the polygon is not the light switch for most pins. The
next lever is the satin emitter: square or parallel ends where a satin meets
a straight edge (14 pins), then rail wobble on rings. `coverage_edges` (the
10-10 iso-contour) WAS built (#818) and Kent ruled it no on 10-12. Related:
[[edge-fault-reader-2026-11-10]], [[defect-marks-sitting-2026-11-10]],
[[eye-first-diagnosis-2026-11-13]].
