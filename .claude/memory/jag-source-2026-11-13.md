---
name: jag-source-2026-11-13
description: Kent's 49 smooth/straight pins traced stage by stage — (b) stage-4 chord facets 18, (a) source pixels 10, (d) stitch construction 21 over 3 mechanisms; `outline_redraw_k` built OFF for (a)+(b), 0.75 since 11-14 (Kent "Set 0.75"); satin ends forming flat edges (14 pins) is the next lever
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

**Built:** `outline_redraw_k` (default None; **0.75 since Kent 2026-11-14**, "Set 0.75",
accepting Becker's +0.07-0.35 mm2 bare fabric; PRE_FLIP pins None). It reuses letterform priors'
line/arc geometry on every shape, capped at max(0.75 source px, 1 grid px),
on UPSCALED sources only. A clean upload is byte-identical (md5 on k_line,
n_sync, ahora, and_pizza). `outline_redraw_native` (OFF, not recommended)
adds arcs-only on clean uploads (the (b) cure).

**Readings (n=1 per design, instrument only).**
- Upscaled: roughness Becker 8.30 -> 5.25, Bridge 6.78 -> 6.11, MFab
  7.11 -> 6.81. Becker's staircase border sews as one even band.
- 2026-11-14 (`docs/satin-flat-ends-2026-11-14.md`), all 12 upscaled pro
  jobs: roughness falls on every one (Becker 2.8-3.1 deg at every size),
  exposed travel 0 in both arms. Becker's bare fabric in the art rises
  0.07-0.35 mm2 at 4 of its 5 sizes.
- 2026-11-14, flip PR: on a 50 mm upscaled disc with `subpixel_edges` (shipped)
  the redraw is rounder (rms 0.018 -> 0.004 mm) but sits the edge 0.065-0.088 mm
  INSIDE the true circle (subpixel alone +0.016/-0.003), vertices 33 -> 628:
  the bare-fabric rise's mechanism. CI tripwire, redraw alone: trims Becker hat
  large 11 -> 16, MFab hat 16 -> 23, needle-up +160 / +179 mm.
- The "+24 mm bare travel" in #1479 was a bad metric (it counted travel the
  border covers). The line seen beside Becker's border is a STAGE-7 fault,
  in both arms: single needle-down stitches of 14-92 mm joining a shape's
  own fill runs, with no jump or trim (Becker, MFab).
- Native opt-in: the polygons' facets are gone, but the stitches are mixed.
  The and_pizza "p" sewed a straight cut across a perfect arc and opened a
  seam, and n_sync's roughness rose 6.77 -> 7.92. On clean art the Column
  lane's satin, not the polygon, sets the edge.

**How to apply:** the polygon is not the light switch for most pins.
The 14 satin-end pins, traced 2026-11-14:
- No majority: 6 ends fan or turn onto a flat face, 5 are acute
  joints, 2 caps stop short, 1 matches the pro.
- The EXISTING OFF flag `lettering_columns_apex_cut` cures all 4 Z-joint
  pins with no regression seen. It is unflipped since 10-25 (Kent's call).
- Becker's flat tops are an ANGLE choice: the pro sews MARINE with
  near-vertical crosses.
- Snapping end points onto the edge line was measured useless (the ends
  were already collinear).
- Rail wobble on rings is still open. `coverage_edges` (the
10-10 iso-contour) WAS built (#818) and Kent ruled it no on 10-12. Related:
[[edge-fault-reader-2026-11-10]], [[defect-marks-sitting-2026-11-10]],
[[eye-first-diagnosis-2026-11-13]].
