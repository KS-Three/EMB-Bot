---
name: edge-cap-remeasure-2026-10-29
description: "2026-10-29 — MASTER_SCOPE defect 19 re-measured on main 44ecf1cb: our sewn silhouette is 0.0-4.0% bare with NO cap (was 5.9-100% on 09-11), closed by silhouette_underfill_rim + border_by_size; the cap's size swing is gone (worst bill +5.6%); the default bean cap sews nothing since bean_only_lines; no lever built"
metadata:
  type: project
---

# Defect 19 re-measured — the edge is closed upstream, the cap is inert (2026-10-29)

Asked to fix defect 19 (fill rows end in open air on the design's own edge)
and the cap's size swing. Measured first, on main 44ecf1cb, with
`tools/edge_cap_remeasure.py` (same rule as `pro_silhouette.py --ours`):

- **Cap off, 80 mm: 0.0-4.0% bare** on the six 09-11 fixtures (Fremont
  100 -> 0.0, whitebg 82.6 -> 1.8, gaulke 76.7 -> 0.3, enthusiast 5.9 -> 4.0,
  becker 2.9, drone 0.2). One flag OFF at a time: `silhouette_underfill_rim`
  holds Fremont's whole edge (and needs `silhouette_underfill`), whitebg 28
  pts, drone 6.8; `border_by_size` whitebg 49, gaulke 5.7. Fabric edges,
  `border_from_outline`, the mitre: under a point.
- **No swing:** becker satin cap +0.0% (60 mm) rising to +2.3% (120), the
  09-12 cliff widths +0.6-1.5% (were +53-59%). Worst anywhere 60-120 mm:
  +5.6%. So the brief's conditional lever (stable cap decision across size)
  was NOT built. `classify_ribbon` not re-probed — the cap stopped depending
  on it.
- **`edge_cap="bean"` (the default) sews NOTHING since 10-27:**
  `bean_only_lines` turns the bean style into "none" in stage 7. Satin is the
  only live style: byte-identical on 3 of 4 paired jobs at the pro's width,
  Becker 16 points + a colour change.
- **Studio lie found:** Design edge defaults to "Bean cap"; with no
  EDGE_CAP_* warning and no edge_cap runs, `borderMenu.edgeCapState` says
  "found nothing to sew … too small or too narrow" on every design.
  Fixed 10-30: a fresh design reads "Design edge off."; a saved "bean" reads
  "No design edge sewn." (no warning + no cap run = the cap never ran; a real
  empty cap always says EDGE_CAP_EMPTY). Its reason now names an edge already
  stitched: satin on Fremont sews 0 points because it is covered, not too small.

**Why:** a stale defect re-measured before building — 09-12's oscillation
needed a design whose art carried no linear cover at some sizes; today's art
covers its edge at every size.
**Kent's rulings, 2026-10-29:** "'none' default (Recommended)" -- `edge_cap`
defaults to "none" in the engine and the Studio, plans byte-identical (DST md5
on seven runs, #1192) -- and "Close it (Recommended)": defect 19 is Closed.
A site rebuilding the pre-10-27 engine with `bean_only_lines` OFF passes
`edge_cap="bean"` with it.
**How to apply:** don't build an edge-cap stability fix or re-open the cap's
budget without a new sweep showing bills over a few percent. The readout
and the default are Kent's calls (sent up). Evidence:
`docs/edge-cap-remeasure-2026-10-29.md`, `docs/renders/edge-cap-2026-10-29/`.
Related: [[border-by-size-colour-seams-2026-10-28]], [[underfill-outer-rim-2026-10-25]],
[[bean-census-2026-10-27]].
