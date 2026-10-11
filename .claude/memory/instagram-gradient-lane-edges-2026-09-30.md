---
name: instagram-gradient-lane-edges-2026-09-30
description: Kent's REAL Instagram file classifies gradient correctly; the gradient lane (SLIC) wrecks the white shapes' edges, forced flat keeps them clean. Classifier is not the defect here
metadata:
  type: project
---

2026-09-30: Kent said "quality went down, auto-detect must not work" after digitizing the
Instagram logo. Measured: stage 0 said `CLASSIFIED_GRADIENT` — CORRECT for this art. The
defect is the gradient lane: SLIC superpixel borders make the white rounded square, ring
and dot jagged/stair-stepped with stray diagonal lines; `forced_class="flat"` keeps them
smooth but posterizes the sweep into hard bands (and at 188 mm drew the ring grey —
unexplained, unchased). Not a regression: the synthetic repro scored the same D/58 in August.

- Kent's real file now lives at `digitizer/testdata/photo/acceptance/instagram_original.png`
  (gitignored — trademarked, never commit). It is the first real tonal positive since
  `drone_render` toward gate 2's 3-5 (see `docs/stage0-signal-decision-2026-09-11.md`).
- Preflight grade is useless here: every arm on the real file reads F/0-F/16 (saturation,
  [[instruments-that-underreport-2026-09-06]]). Judge by render (`stitchviz.render_design`
  on the job's `design`).
- Studio sends `max_colors: 6`; a bare service call without it gives 12-17 colours — match it.

**Outcome the same night:** `snap_region_edges` built (lane `claude/snap-region-edges`,
unmerged): edges go clean, thread lifts 44 → 28, but the sweep still bands. Kent, on the
live Studio: "Still bad, bring the switch back" → PR KS-Three/EMB-Bot#587 restores ONE
button, "Sew as flat art" (`forced_class=flat`), reversing half of that morning's removal.
#587 MERGED 2026-10-01. Kent then asked why I recommended the snap OFF when ON looked better -- my reasons were my own re-pin work and a misread of 'still bad' (that was the banding, not the edges). Snap shipped ON as PR KS-Three/EMB-Bot#589. Flip moved 26 tests in 13 files: 21 ride `conftest.PRE_FLIP`, 3 held pre-snap by name, 1 re-pinned as a gain (THREAD_MATCH_POOR blocks drone 5->3, golden_tee 2->1).
Wider sheet AFTER the flip (should have been before): trims UP on 4 of 6 gradient logos (drone 121->138, golden_tee 40->44, gaulke 29->33, bridge 100->102); gaulke loses its grey roof chevron. Golden Tee's wrong red/teal goes. Do not recommend against a visibly better result to save test work.
Driver trap: `upload <sel> <path>` splits on the FIRST space — the selector cannot contain one.

**Why:** a "classifier is broken" report can be a lane defect on a correct classification.
**How to apply:** before touching stage 0 on a gradient complaint, A/B auto vs forced flat
and RENDER both.
