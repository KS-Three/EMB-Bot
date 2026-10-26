---
name: buried-walk-2026-10-26
description: W4-03 premise FALSE, nothing built — the buried walk rule already exists (trim_bury_under_later ON, detour budget = the pro's p90 2.57x), and 0 of our 176 between-shape cuts on five hats have ANY route under later thread; the pro's metre on Drone comes from layering + colour revisits (23 blocks), not a walk rule
metadata:
  type: project
---

W4-03 asked for a walk-needle-down-under-later-thread flag for the third
#1072 trim item (Drone: pro walks ~1 m between pieces, we cut). Measured
first with a new reader, `digitizer/tools/between_walks.py` (both DSTs:
every piece-to-piece step cut / flown / walked, each walked mm buried /
on work / bare; our plan: `diagnose_plan`, stage 7's own cover with NO
length budget). Doc: `docs/buried-walk-2026-10-26.md`. Main 46949f78.

- **The rule is already there.** `trim_bury_under_later` (ON since
  2026-10-23) buries a cut under later thread within `_link_budget_mm`
  (max(14, 2.5x hop), cap 72). The pro's 331 clean buried walks over his 28
  DSTs: detour p90 2.57, longest hop 26.7 mm. 11 of 331 (3%) are past our
  budget (Fremont 2.6-2.9x, Drone's 97.9 mm walk for a 15.8 mm hop).
- **Ours have nothing to walk under.** Five hats, `off`: 0 of 176
  between-shape cuts have a route under later thread at ANY length (`cut`
  arm 0 of 212). The best route's uncovered part lies on another colour
  sewn earlier (Drone 407 mm, MFab 223, Fremont 128), bare fabric (Drone
  184, MFab 133, Becker 101, Gaulke 87) or our own colour (80-96 each).
- **Drone's gap is all in the badge**: lettering 28 cuts vs his 27 (both
  bare). Badge 45 vs his 10 cuts + 70 walks. His badge is back to front: the
  dark ground (block 4) walks 316 mm under 18 later blocks; 23 blocks of 8
  cones (dark grey x6, black x4). Ours: 11 blocks of 6 cones, knock-out.
  `silhouette_underfill` ON does not reach it (73 cuts, 0 routes).
- **Half his walking is not travel**: 480 of 1,022 mm on Drone lies on work,
  mostly the drone's run-stitch OUTLINE — the piece rule opens a lone run
  line away, so design run lines read as walks. Look at the sew path.

**Why:** "the pro walks, we cut" reads as a missing routing rule; the
cover-only diagnosis shows our layout offers no later thread over the gaps,
so no budget or length change can move a cut.
**How to apply:** before any routing/walk work on trims, run
`between_walks.diagnose_plan` on the plan — `takes_now`/`budget`/`gap_cap`
are routing, `no_route` is construction. The lever here is layering + colour
order/revisits, upstream of stage 5 (layout: Kent's call from renders).
Related: [[sequence-like-pro-2026-10-25]], [[in-piece-cuts-2026-10-25]],
[[trim-economy-2026-10-21]], [[cut-after-bury-2026-10-23]],
[[silhouette-underfill-2026-10-24]].
