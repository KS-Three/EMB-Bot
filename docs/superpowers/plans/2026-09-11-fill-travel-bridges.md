# Why the last third of fill travel is still exposed — and why the three proposed fixes do not reach it (2026-09-11)

**Status: INSTRUMENT SHIPPED, BOTH ENGINE ARMS MEASURED AND REVERTED.** Quality
review 2026-09-08 item 12. The review's own words were *"the cause is not
established"*; this establishes it, and the answer disqualifies all three
remedies the review listed plus a fourth I tried.

## 0. What already governs this — read before changing the plan

- **`fill_travel_under_cover` is ON by default** since Kent's flip 2026-09-03,
  with the 2:25 exposed-stitch-to-trim weight ratified the same day. It halved
  exposed travel; this item is about what it cannot reach.
- **`_score` is `cuts * 25 + travel_stitches + exposed_stitches * 2`**
  (`_TRIM_STITCH_EQUIVALENT`, `_EXPOSED_STITCH_WEIGHT`). Both are Kent's
  ratified judgements about how a design LOOKS and how long it takes, not
  fabric constants — ROADMAP gate 1 does not reach them, and neither does this
  plan without his say-so.
- **`_reorder_for_cover` already prefers a next column whose STRAIGHT bridge is
  clean**, scores both orders and keeps the cheaper, pinning the last path so
  the exit point never moves.
- **The review's stale figures.** It quotes Becker 55.8 mm of 148, Bridge Bar
  75.8 of 194, Fremont 59.6 of 185. Re-measured 2026-09-11 on today's engine:
  **Becker 29.6 of 76.7, Bridge Bar 114.2 of 275.4, Fremont 23.9 of 123.5.**
  Two of the three moved a long way — do not quote the review's numbers.

## 1. The instrument

`digitizer/tools/fill_bridges.py`, pinned by `tests/test_fill_bridges.py` (4).
For every fill-phase travel run that still lies over finished fill it re-asks
`travel_path` the same question under relaxed caps and records which relaxation
produces a clean route, plus the three facts that decide what to do when none
does: how much of the bridge a LATER colour buries (`covered_by`), what a jump
would cost (the straight gap against `trim_at`), and whether any unsewn ground
connects the two ends at all.

That last one is the question the review did not ask, and it is the one that
settles this.

## 2. The census — 9 fixtures, 92 bridges, 912.6 mm exposed

| cause | bridges | mm | share |
|---|---|---|---|
| **no corridor** — no unsewn ground touches both ends | **65** | **801.1** | **88%** |
| router — a corridor exists, `travel_path` cannot use it uncapped | 13 | 55.4 | 6% |
| budget — the detour cap refused a route | 8 | 35.8 | 4% |
| buried — a later colour covers it anyway | 6 | 20.3 | 2% |

Per fixture: becker 3/29.6 (100% no-corridor), fremont 3/23.9 (100%),
bridge_bar 13/114.2 (79%), drone 17/151.3 (89%), gaulke 1/3.1, enthusiast 0,
whitebg 1/9.2 (100%), meadow 23/255.8 (89%), sunset 31/325.5 (88%).

**On the two fixtures Kent actually pointed at — Becker and Hotel Fremont —
every single exposed millimetre is no-corridor.** The needle is standing inside
finished fill with the next column on the far side of more finished fill. No
rule about WHERE to route can help, because there is nowhere to route through.

## 3. The three proposed remedies, priced

- **"route under the covering colour"** reaches the 2%. `covered_by` — the
  artwork union of later layers — simply does not overlap these bridges.
- **"lift as a jump when shorter than `trim_at`"** reaches **8 bridges / 26 mm**
  corpus-wide at pique knit's `trim_at` of 3.0 mm, and **none at all** on
  Becker, Fremont, Bridge Bar or drone. It is not wrong, it is tiny.
- **"route along the shape's edge run"** is what the ring route already is.
  Built as `cfg.fill_travel_detour` (raise the detour cap when the alternative
  is exposed travel rather than a lift, since a cut can be undone with scissors
  and a sewn line cannot) and measured: **a perfect no-op on all nine
  fixtures**, every count identical.

**The `budget` bucket does not survive contact with the engine.** Its first
reading was 26 bridges / 110 mm and it was an artefact: `travel_path` returns
its route with the START EXCLUDED (`_densify` is a-exclusive), and that first
step is exactly the part lying inside the column just finished, so measuring
exposure without it made every short bridge read clean. The tell was a detour
ratio of **0.5x**, geometrically impossible between two fixed points. Corrected,
the bucket is 8 bridges / 36 mm whose "clean" route is 1.0–1.4x the straight
gap — inside the existing 4x cap, so the cap was never what stopped them.
`tests/test_fill_bridges.py` pins the start point so this cannot come back.

## 4. The fourth idea, and why it is worse

Not in the review: give `_reorder_for_cover`'s greedy a second tier — when no
candidate has a clean straight bridge, prefer one that at least still shares
unsewn ground with the needle, before settling for the nearest. Aimed straight
at the 88%.

**Measured WORSE on six of nine fixtures and better on none:**

| fixture | exposed off→on | trims | travel |
|---|---|---|---|
| gaulke | 3.1 → **84.0** | 23 → 17 | 75.8 → 343.3 |
| fremont | 23.9 → **99.9** | 46 → 43 | 123.5 → 429.2 |
| sunset | 325.5 → **552.1** | 48 → 55 | 881 → 1222 |
| meadow | 255.8 → **403.7** | 41 → 43 | 584 → 738 |
| drone | 151.3 → 171.3 | 87 → 92 | — |
| bridge_bar | 114.2 → 127.7 | 125 → 127 | — |

It works, and that is the problem: it finds orders with fewer CUTS, and `_score`
buys those — one trim is worth 25 stitches, an exposed stitch only 2, so six
cuts pay for eighty millimetres of visible thread and the scorer calls it a win.

**A per-shape ratchet did not stop it.** Adding "never keep an order that scores
more exposed than the one it replaces" changed only meadow (403.7 → 354.0) and
sunset (552.1 → 412.2) and left gaulke at 84.0 — which is its own finding:
`_order_cost` and `emit` can disagree about what a given order will sew, because
`emit` keeps a `route_cache` across a shape's bridges and the scorer builds a
fresh one, and `travel_path` tries cached rings first. Both arms were reverted.

## 5. What is actually left, and what is Kent's

The exposed remainder is **manufactured by the column order**, and the order is
already chosen by a scorer whose exchange rate makes exposure cheap. Three ways
forward, in increasing size:

1. **The exchange rate is Kent's** (ratified 2026-09-03, before this
   measurement existed). gaulke is the concrete case: today's rate buys 81 mm of
   visible thread for 6 trims. If that trade is wrong, `_EXPOSED_STITCH_WEIGHT`
   moves and several of these arms change sign — but the same rate governs every
   fill in the corpus, so it is a design-wide decision, not a knob for item 12.
2. **`_order_cost` and `emit` must agree**, cache included, before any ordering
   work can be trusted. Today a per-shape ratchet can be satisfied and the sewn
   result still get worse. This is a prerequisite, not a feature.
3. **The greedy itself.** Once an island is stranded every later haul crosses
   finished fill; a route over the columns' connectivity graph would not strand
   it. That is a real piece of work and it should be proposed with evidence, not
   started at the end of a session.

Nothing here is built. The instrument and this record are the deliverable.
