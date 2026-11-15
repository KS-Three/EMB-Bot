# Bukit's dots and the neon sign's (R): what closes them, and why nothing is built (2026-11-14)

Two faults from the night's eye sweep (`eye_pairs_out/eye-sweep-1114/REPORT.md`,
rows 10 and 13), first traced by the small-shapes worker
(`eye_pairs_out/small-shapes-1114/REPORT.md`). This page re-checks that trace
on main `5a647125`, measures what the pro sews at this scale, and says why no
flag is built. Evidence (gitignored, primary checkout):
`digitizer/eye_pairs_out/counters-1114/` (`runs/`, `strips/`, `sheets/`).

## Bukit Asam's red mark: two causes

**(a) The outer arc merges into the C: the satin rail push.** The art keeps
0.3-0.4 mm between them. #1529's `satin_push_keeps_gaps` stands the arc apart
at 80.4 mm (the small-shapes worker's sheet) and at the sweep's 113.5 mm on a
hat (`sheets/bukit_hat113.5_mark__art_off_on05growth_ontrue.png`). Pixels
moved: `0.5` + `growth_keeps_gaps` 8.95%, `true` 2.06%. Nothing new is needed
beyond #1529.

**(b) The three dots: stage 3 drops them.** Each is about 0.5 mm across
(0.2 mm2) and sits 0.3-0.4 mm from the ring. By the debug stages
(`strips/bukit_debug_off.png`) they are whole through stage 2. At stage 3 they
are left unoutlined under `cfg.min_detail_mm` (1.5), so they never become
regions. #1543's `tiny_detail_keep` does not keep them: it holds pieces ringed
by one host, and these sit on the page (`strips/bukit_tiny.png`, no dot in
either arm).

**What the pro sews at this scale.** Every isolated stitch block under 2.6 mm
in 11 pro jobs (`scripts/pro_small_marks.py`, blocks split at jumps, trims and
colour changes):
- the smallest are 1.0-1.3 mm on their short side:
  - TOAT beanie: 1.6 x 0.9 mm, 20 stitches;
  - TOAT machine hat: 1.8 x 1.0 mm, 19 stitches;
  - Drone: 1.3 x 1.9 mm, 15 stitches;
- ProSeal's six dots are 1.9-2.6 mm, 17-23 stitches each;
- Becker, Gaulke, Fremont and Golden Tee have none under 2.6 mm.

Each is a satin dot of 15-23 stitches. **None is under 0.9 mm on its short
side.** No pro file says how a 0.5 mm dot is sewn, or whether it can be. That
is the smallest-sewable-dot question, a physical constant: ROADMAP gate 1
(sew-out first). Raised to the pro's 1.0 mm instead, each dot would sit about
0.05 mm from the ring and close the gap that (a) just opened.

*(measured 2026-11-14 — `runs/bukit_lc_{sg_off,sg_tiny}/`,
`runs/bukit_hat_{b_off,b_on05g,b_on}/` on `493d5068`, the #1529 branch)*

## The neon sign's (R): stage 1 closes it

The source (R) is about 12 px across at 5.23 px/mm (2.3 mm). It is drawn in
alpha with 1 px transparent gaps between the ring and the R, 0.19 mm each:
half a 40 wt thread. Stage 1 closes them, through the alpha threshold, the
nearest-neighbour upscale and the enclosed-background fill. Stage 4 has one
3.7 mm2 region with no holes, and it sews as a solid satin dot ("neon.").
`tiny_detail_keep` does not change it (md5 identical,
`runs/neon_hat_{sg_off,sg_tiny}/`).

No geometry sews 0.19 mm gaps: they are under a thread's width. The ways
round it are Kent's:
- Leave the dot.
- Drop marks under some size.
- Sew the mark's strokes as running stitch (a ring and an R).

The last is untested. No pro file here has a sewn (R) or TM to measure, and
a raster skeleton of a 12 px R would be the "playhouse out of logs" Kent ruled
out for bean keylines on 2026-11-13 (memory
`hairline-keyline-bean-2026-11-13`).

## Kent's calls

1. Bukit's dots: leave them dropped (recommended), or raise them to the pro's
   smallest dot. Raising them touches the ring and brings the merge back.
2. The (R): leave the dot (recommended for now), drop marks under about
   3 mm, or have a running-stitch mark built behind a flag for a sheet.
