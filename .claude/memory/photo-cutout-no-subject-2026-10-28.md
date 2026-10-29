---
name: photo-cutout-no-subject-2026-10-28
description: rembg keeps 0.01-5.4% of a SCENE as subject (real subjects 27-76%) and the lane sewed the empty rest; #1179's `photo_cutout_min_kept` (0.20, ON) refuses it; prep-skipped measured better than prep-kept; a full-frame scene then costs 373-2,100 s, stage 7's rank pass
metadata:
  type: project
---

**Finding (2026-10-28).** After #1178 sent every corpus photograph to the
photo lane, six scenes came back at 0-3,117 stitches: the rembg cut-out
(`stage1_photo_prep.remove_background_seam`, isnet-general-use) answers a
scene with low alpha everywhere. Alpha >= 128 as a share of the frame:
snow_highkey 0.0001, landscape_lake 0.0006, pencil_sketch 0.0011,
underwater_reef 0.003, night_neon 0.005, night_skyline 0.014, stained_glass
0.054 -- against 0.27-0.76 on every row with a real subject (fireworks 0.27,
bw_street 0.31, dark_dog 0.31, group_people 0.38, food_plate 0.57,
architecture 0.76). The seam thresholds at 128, `_clean_background_mask`
refills only SMALL background islands, and `pipeline.run_stages` accepted any
non-None mask, so the frame became background (census item 1 of 10-27).

**The guard:** #1179's `cfg.photo_cutout_min_kept` (0.20 of stage 1's
artwork, ON; 0.0 = the old engine) landed the same night this was measured --
a cut-out keeping less is refused: stage 1's border-flood `bg_mask` stays,
`subject_bg_mask` stays None, `PHOTO_CUTOUT_REFUSED` instead of
`PHOTO_BACKGROUND_REMOVED` (never UNAVAILABLE -- rembg ran), and the job takes
the classical route (prep skipped, arm B). This session's parallel flag on
the frame share (OFF, 0.12) was dropped on rebase; the six scenes read
0.000-0.042 under either denominator, all refused at 0.20; the floor sits
3.7x above the scenes and 1.35x below the smallest real subject (fireworks
0.27 of its frame; #1179's smallest kept, bw_street, 0.31 of its artwork).
Kent 10-28 "measure A vs B, ship better": B (prep skipped) beat A (prep kept)
on cc on 4 of 6 rows (night_neon +0.06, night_skyline +0.06, reef +0.02,
stained +0.01), lost on landscape_lake (-0.016), tied on snow; B's
neon/skyline renders read as scenes, A's as fragments -- so main's arm is the
measured one.

**Why:** Kent 10-27: the lane must improve ALL photos; it was tuned on
portraits and the owl, every one of which has a subject. Kent 10-28 (via the
director): "Measure A vs B, ship better" -- A = refused frame still gets
tone/texture/face prep, B = prep skipped too (the `cutout_failed` route).

**How to apply:**
- A refused scene is no longer an empty hoop; it is a 25,000-82,000-stitch
  posterised frame that takes **450-2,100 s** (stages 0-4 90-320 s, stage 7
  the rest; three arm-B rows timed out at 1,200 s inside
  `stage7_sequence.sequence`'s rank-only second pass, `column_lean.run` ->
  `stitch_one`). The Studio stops waiting at 600 s. Capture these rows with
  `--timeout 2400`; the stage-7 cost is the next thing to measure, not this
  flag's to fix.
- Read `cutout_refused_kept_frac` on the sxs page, not `cutout_removed_frac`
  (after-minus-before: pencil_sketch shows 0.842 removed while rembg kept 0.1%).
- `python -m tools.photo_corpus capture --set FIELD=JSON` captures the other
  arm of a flag without editing the tree; the override lands in run.json's
  config. `sxs --only SLUG` builds a page over a partial capture.
- A real subject under 20% of its artwork refuses with the scenes and sews
  with its background; no corpus row has one -- add the row before moving the
  floor.
- Alpha probe script and overlays: the session scratchpad only (not committed);
  readings in the spec.

Related: [[stage0-texture-gate-2026-10-28]], [[photo-lane-generalise-2026-10-27]],
[[photo-corpus-sxs-2026-10-27]], [[shape-memo-2026-10-28]] (the rank pass).
