---
name: fine-detail-work-grid-2026-09-30
description: Bridge's missing "RESTAURANT" was the tracer's 4 px/mm grid, not the 400 px file — the RAG merge averages a 3-5 px stroke into its ground; `cfg.work_px_per_mm` traces low-res line art at 8, and three other logos got lettering back
metadata:
  type: project
---

Kent, 2026-09-30: *"the 'restaurant' is completely missing … figure out why,
what prevents it from doing fine detail, and make a fix."* Full record:
`docs/fine-detail-work-grid-2026-09-30.md`, renders beside it.

**The diagnosis already on file was half right and stopped one step short.**
That morning's entry said the teal words were a segmentation loss at
3.5 px/mm, "a resolution fact no stitch rule moves" — while recording, in the
same paragraph, that the SAME 400 px file brings the words back at 140 mm. A
bigger design adds no information to a JPEG; it only spreads a letter over
more of the engine's grid (stage 1 enlarges a sub-floor source to
`min_px_per_mm` = 4 at any size). **When "make it bigger" recovers detail from
the same file, the loss is the engine's grid, not the artwork.**

**Where it dies:** the gradient lane's RAG merge, not SEEDS and not a floor.
At 4 px/mm a 0.7-1.4 mm stroke is 3-5 px; teal-majority superpixels still
hold 67 of 81 mm² of teal, then `merge_hierarchical` compares MEAN colours at
26 dE00 and the diluted letters read 19-23 from a diluted ground — 39 mm²
left. Both merge protections are size-gated (1,000 px; 9% of the design) and
never see a letter. Traced at 5-10 px/mm the same merge keeps 64-67.

**The fix, BUILT OFF (flip is Kent's):** `cfg.work_px_per_mm` (None; measured at 8.0) — the grid a low-res source is TRACED
on, separate from `min_px_per_mm` (4), which still owns `INPUT_LOW_RESOLUTION`.
Photo classes keep the source line; a 2,800 px side budget bounds it; the
alpha-extension gate and preflight's "lost in tracing" note follow the grid.

**It was never one logo, and the corpus could not say so** — bridge is the
only gradient logo under 5 px/mm. `tools/lowres_detail.py` downsamples the
high-res logos and scores each against its OWN full-res digitization (`fine` =
ink under 1.5 mm sewn in its colour). At a 5 px/mm source, traced at 4 → 8:
ENTHUSIAST 0.25 → 0.90 (tagline back), screenshot 0.66 → 0.83, golden_tee
0.66 → 0.78, Fremont 0.86 → 0.90 ("THE" back), drone 0.78 → 0.78; mean
0.64 → 0.84 (6: 0.72, 7: 0.74). From 6.5 px/mm the gain is inside the noise
(0.77 → 0.80, two of five down). Price: trims rise toward the full-res
file's own; `logo_whitebg` at 5 px/mm is the one loser (12 → 21 trims).

**Measured and rejected:** 4x superpixels (works, moves every design);
`thin_ink`'s 3 px floor counted in source px (worse); cubic/linear for
Lanczos (no arm wins twice); forcing flat (olive halo round every letter).

**Why OFF:** not robust — enlarging the bg mask smoothly instead of NEAREST
(half a pixel of foreground) sent bridge's words to a grey-green cone and
ENTHUSIAST 0.90 → 0.70; and ON it moves ~45 tests, some real regressions on
6-7 px/mm synthetics (radial ramp 2 regions for 1). A reboot killed the
measurement run mid-way; drone/screenshot/whitebg smooth arms never ran.

**What it does not fix:** the letters are 3.25-4.5 mm with 0.7 mm strokes and
each sews as ONE satin bar — present, not legible letter by letter. That is
`LETTERING_TOO_SMALL`'s question (size), now about thread instead of tracing.

**How to apply:** before writing "the source cannot carry it", re-trace the
same file on a finer grid at the same design size. And when a corpus has one
fixture in a regime, build the regime from the others before generalising.

Session traps: a second Claude lane was running a full suite on this
8-core laptop the whole time — check `Get-CimInstance Win32_Process` for
another `pytest -n auto` before launching heavy parallel work, or both crawl
(their run took 3 h 14 m). A scratch file written under `.claude/worktrees/`
cannot be removed by a session (the guard hook blocks `rm` there): keep
scratch in the scratchpad.

Related: [[bridge-border-and-script-2026-09-30]],
[[thresholds-on-the-wrong-population-2026-08-28]],
[[native-ramp-edge-read-2026-09-18]], [[worktree-venv-and-baselines]].
