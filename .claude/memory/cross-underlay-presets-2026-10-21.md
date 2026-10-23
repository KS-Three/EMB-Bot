---
name: cross-underlay-presets-2026-10-21
description: fill_underlay_cross built OFF for hat/LC/beanie; the "bare" MFab/Becker fills were satin misread by pro_fill_underlay
metadata:
  type: project
---

`cfg.fill_underlay_cross` / browser `crossUnderlay` (built OFF 2026-10-21):
structured_cap, pique_knit, jersey_tee sew `cross_tatami` under fills instead
of `edge_zigzag` / `edge_run`. Photo class keeps its own `edge_lattice`;
explicit `underlay_style` and per-shape overrides still win. Gate 1: Kent's
flip after card `docs/sewout/card-cross-underlay-2026-10-21/`.

**The "defect" was the instrument.** PR #1032 reported MFab hat (2,521 mm²) and
Becker beanie fills sewing BARE. Neither job sews a single tatami fill: both
are split SATIN with per-column centre-run underlay (872 / 1,324 mm).
`tools/pro_fill_underlay.py` reads satin crosses as dense fill rows and counts
only running stitch before the region's first dense row. **Why:** a wrong
"bare" reading sends a session hunting an engine bug that does not exist.
**How to apply:** before calling one of OUR fills bare, list the plan's
`StitchRun.kind` per shape. The real gap on those jobs is TIER (pro fills
the silhouette, we satin it), not underlay.

Measured ON vs OFF (pro_pair, pro's width): Fremont hat 2.0→1.0 mm pass,
share 4.9-7.6→8.9-10.6% (pro 0.75 mm, 17.3%), −416 st, −15 trims; Machine hat
(with `sew_enclosed_white`) −253 st, −17 trims; To-a-T beanie (same) +710 st,
+14 trims. Our pass stitch reads 2.5-3.5 mm vs the pro's 3.5-4.0: even
division per row, the same gap as fill row 11. Badge-field fills on
Machine/To-a-T only exist with [[sew-enclosed-white]] ON.
