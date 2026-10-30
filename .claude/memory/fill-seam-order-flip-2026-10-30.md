---
name: fill-seam-order-flip-2026-10-30
description: fill_seam_order + fill_bridge_cut_exposed flipped ON together (Kent 10-30) after a 17-logo + 16-pair check; the rim lead-in leak it found; trims are the cost
metadata:
  type: project
---

Kent flipped `fill_seam_order` (#1189) and `fill_bridge_cut_exposed` (#1187) ON together on 2026-10-30 ("Flip both (Recommended)"), off the OFF|ON sheet of the 17 corpus logos whose stitches changed at 80 mm left chest. Both are now pinned False in `PRE_FLIP`.

- **What ON buys:** section ridges are gone on all 17 logos, and shade flips on all but 3 (Instagram's remaining 5 are white under-fill). Exposed travel (`tools/travel_legs.py` exact) falls or stays flat on every logo: Instagram 53 → 3 mm, emoji 34 → 0, silhouette 60 → 5.
- **The cost is trims, almost all from `fill_bridge_cut_exposed`.** The crest goes 130 → 168, isometric 21 → 33 and Drone 83 → 93. Stitches rise 0–6%.
- **Pro pairs:** 6 of 16 are byte-identical; on the rest, stitches rise 0–2% and trims change by −3 to +10.
- **`fill_seam_order` alone RAISES exposure on some art** (crest 114 → 170). It moves where a fill ends, and the next bridge then crosses finished rows. Never flip it without `fill_bridge_cut_exposed`.
- **The leak the corpus found** (fixed in #1196): a satin rim's lead-in in `stage6_border.border_runs` went straight across the shape's finished fill. With seam order the fill ends mid-shape, so the emoji's horn got a 7 mm line.
  - **Under the cut flag** the lead-in rides only the band the ring's REMAINING arcs will sew: 0.8 × width, flat ends, never round a seam `omit` dropped. Otherwise it lifts.
  - **Gaps under `trim_at_mm` sew as before.** A band route there doubled back on kanji_brush.

**Why:** Kent circled buried lines and shade bands on the Instagram render (10-29). Layout is judged in the preview ([[layout-judged-in-preview-2026-10-22]]).

**How to apply:** when a fill-order change looks good on its own, run `travel_legs` on the WHOLE plan, rims included, before trusting the number. Read the zoomed renders as well, because `travel_legs` under-reads lines that run parallel to the rows. Related: [[exposed-travel-is-the-fill-tier-2026-09-19]], [[border-by-size-colour-seams-2026-10-28]].
