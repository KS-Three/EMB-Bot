---
name: tm-mark-golden-tee-2026-10-26
description: Golden Tee's 0.94 mm TM -- the pro re-sets it as a 4.3 x 2.0 mm black double run; we drop it in stage 2 (thin_ink's 3 px floor refuses its 2 px strokes, SEEDS returns it as page); the only R/C/TM mark in 19 artworks / 27 pro files, so Kent ruled NO build -- a future R/TM job drops it silently
metadata:
  type: project
---

**KENT'S RULING, 2026-10-26 (relayed by the director), verbatim: "Name the cause, no build (Recommended)".**
`small_mark_run` is NOT built. Do not propose a mark rule again without a SECOND job that carries a TM, (R)
or (C). The director's 10-25 small-symbols census put this TM among ~12 one-off redraws on 5 artworks that
no mark property predicts (kappa 0.000 on keep / thicken / redraw / drop). This follows on from L8,
[[small-text-floor-2026-10-24]], which found it as the one row against the small-text floor.

**The mark.** Art `testdata/photo/logo_golden_tee.jpg` at the pro's 74.9 mm: 1.72 x 0.94 mm, two parts
0.09 mm apart, stroke 0.09-0.12 mm (2-2.8 px at the source's 23.3 px/mm), ink (49,49,49).

**The pro** (`scratch_kent/goldentee_hat.dst`, the same file as `GOLF HAT.DST`):
- Block 2, which is BLACK per the PES. A render that shows it red is the fallback palette, not his thread.
- Stitches 3697-3725: 29 needle-downs, a TRIM before and after.
- ONE skeleton double run: each stroke out and back, 1.0 mm stitches, 0.6 mm locks at the end. The M's left stem shares the T bar's right end.
- Needle box 4.3 x 2.0 mm (2.35 mm painted), about x2.1 tall and x2.5 wide.
- Anchored at the art's TOP-LEFT: (60.86, 39.43) -> (61.1, 39.1) in each file's own extents frame. It grows right and down.

**Where ours loses it: stage 2, the gradient lane.** Measured on main `0113e8cb` (2026-10-27), at the pro's
width and garment, through the Studio request, with read-only taps on prep / photo_segment / find_thin_ink /
resolve_small_regions / vectorize.
- Golden Tee classes `gradient`. The source is 23.3 px/mm, so there is no upscale, and stage 1 hands the TM on intact: 382 ink px (grey < 200, down to 1) in its 41 x 22 px box, every one of them inside the foreground the photo lane segments.
- The thin-ink population (`cfg.keep_thin_strokes`, ON) is the rescue built for exactly this: strokes that SEEDS would average into their ground. It quantises the TM correctly (249 px black spool 4, the anti-alias fringe in two other labels), then REFUSES both letters:
  - The T (72 px, skeleton length 33.8 px against the 25.6 px floor, ground 0.78) fails only `thin_ink.py:188`. Its median full width is 2.0 px against `THIN_INK_MIN_PX = 3.0`.
  - The M (178 px, length 74.6 px) fails the same floor, and ALSO the one-ground rule at line 194: 0.688 against `THIN_INK_GROUND_SHARE` 0.75, because its fringe labels split the ring around it.
- Refused, its pixels go into SEEDS with the ground and leave stage 2 as page: all 902 px of its box, the 382 ink px included, are -1. Stage 3 never gets a mask there, and no region or stitch of ours sews it. Whether the RAG merge or the halo dissolve set the -1 was not split.
- Today's totals: 11,629 st / 35 trims, against the pro's 5,973 / 10.

**Why that floor is not a free fix.** 3 px is the halo guard: a 2 px component is JPEG ringing at any
resolution (Fremont's 34.6 mm, 0.07 mm sliver). The TM's 0.09 mm stroke at 23.3 px/mm is exactly that
width, so lowering the floor reopens the halo, and option C's knot (below) is all it would buy.

**It is the only one.**
- Art side: free-standing ink clusters 0.35-2.4 mm, nothing else within 0.6 mm, over 19 art x width pairs. Besides the TM they are ProSeal's honeycomb hexagons and "+", Fremont's "EST" and Machine's 1.9 mm speed dash.
- Pro side: trim-bounded segments <= 5 mm in 27 registered pro DSTs. Every other small run glyph is line art (Gaulke Plowing's tractor windows, Gaulke JB's map lines). Every small satin glyph is a window, foliage, spoke, star, honeycomb cell or "+".
- Catch: Becker's committed art is 1.4-1.9 px/mm, too coarse to show such a mark; that is why the pro side was read too. Bridge's pro files were not on the machine.

**How to apply.** A TM / (R) / (C) on a customer's art is DROPPED today, silently: no warnings, Kent 10-02,
[[no-warnings-reaches-readouts]]. The per-job fix is a manual edit, like the Bridge anchor; copy the pro (a
black double run, its cap ~2 mm at the needle, anchored on the art's top-left).

If a second mark job arrives, the rule that was priced and refused here is `small_mark_run`:
- what it catches: a dropped dark multi-part cluster <= 2 mm with stroke <= 0.2 mm, free-standing beside lettering;
- how it sews it: a skeleton double run at x2.1;
- the catch: n=1 sets every constant, and it cannot tell a TM from dust without OCR.

Keeping the mark at drawn size is worse than dropping it: a 0.94 mm double run of 1 mm stitches is a knot.
