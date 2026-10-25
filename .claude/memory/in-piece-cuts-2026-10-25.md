---
name: in-piece-cuts-2026-10-25
description: W4-01 — cuts inside one piece by cause (ours 109 vs pro 25): fill sections 35 (pro 0), satin split 40; `fill_section_travel` built OFF routes underlay ring hops inside the field (Fremont 51 -> 41 DST trims, exposure unchanged); fill ORDER gains all refused by the gate
metadata:
  type: project
---

W4-01 classified every cut INSIDE one sewn piece (`tools/sequence_pro.py`'s
piece rule) on the five #1072 hats with a new reader, `tools/inpiece_cuts.py`
(ours: each DST command attributed to its plan run; pro: stitch character
either side). Main c531c7b8, `off` arm: ours 109, pro 25. Ours by cause:
fill sections 35 (Fremont's field 23 = 13 fill + 10 underlay, Drone 12),
satin split 40 (+2 satin/fill), shape-to-shape 20, edge cap 11. The pro has
ZERO between sections of one fill; all 25 of his have satin on a side.
Doc: `docs/in-piece-cuts-2026-10-25.md`.

- **The pro's Fremont field is one section**: no knock-out under HOTEL
  FREMONT, rows near-vertical, letters sewn on top — that is
  `silhouette_underfill`'s construction, not routing.
- **Ours: underlay hops are routable, fill hops are walled in.** Underlay
  `edge_lattice` rings: 22/22 lifted hops have an in-shape geodesic. Fill:
  4/54 (Fremont) have one over unsewn ground — the ORDER (bands above and
  below the letters sewn first) leaves every letter gap an island.
- Built `cfg.extra["fill_section_travel"]` OFF (`digitizer_core/
  fill_section_travel.py`; read in `plan_stitches` via a context var, so no
  `config.py` / `stage7_sequence.py` edit while #1057 owned them): hidden
  geodesic bridges (fill under rows still to sew, touching finished fill only
  inside the column it leaves; underlay inside the shape) + a raster section
  planner priced by `_score`, kept only if no more cuts AND no more exposure.
- **Measured ON (DST):** Fremont 51 -> 41 trims (the underlay), travel_cover
  exposure and bare thread equal OFF on all five; chaining benchmark identical
  on main (3.93) and #1057's head (5.17).
- **What the gate refused:** a looser first build (bridges allowed travel_path's 2.5 mm on finished fill, plans kept on `_score` alone) took Drone 106 -> 99 DST
  trims but +7.8 mm exposed (bare unchanged) and Fremont's fill 12 -> 9 at 86
  travel stitches per cut (rate 25). With the strict rule none survives.

**Why:** "route the travel under the next section's rows" reads as a router
job; the measurement says the router only helps the underlay, and the fill
cuts are the knock-out construction plus order.
**How to apply:** for Fremont-like fields, measure `silhouette_underfill` ON
before more routing work; the next in-piece class is satin splits (40 vs
<= 25), then the edge cap. Read any planner gain with `tools/travel_cover`,
not trims alone. Related: [[sequence-like-pro-2026-10-25]],
[[silhouette-underfill-2026-10-24]], [[exposed-travel-is-the-fill-tier-2026-09-19]],
[[cut-after-bury-2026-10-23]].
