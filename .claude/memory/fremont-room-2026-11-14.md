---
name: fremont-room-2026-11-14
description: "Fremont's EST 1895 was no_room because the white field it sits IN covered 0.48 (<0.5) of 1895's hull; small_text_reset_ground_ring fixes the room test, and small_text_reset_bean_follows makes the dark-ink bean spines (read at drawn size) follow the grown letter; both cfg.extra, built OFF"
metadata:
  type: project
---

**What (Director's order 2026-11-14):** Kent pinned Fremont's small lettering;
the re-set's report (#1510) said both halves of "EST 1895" were `no_room`, one
blocked by a thread-2 shape spanning the design.

**Why no room:** that shape is the white FIELD the date sits in (ground, not
a neighbour). The re-set exempts the ground only when it covers half the
line's convex hull; for "1895" it covers 0.48 (the digits' ink and their own
traced counters take the rest), so it became an obstacle at distance 0 and
the line (both halves) failed. `cfg.extra["small_text_reset_ground_ring"]`:
a region covering half of a 0.3 mm ring round the hull and a quarter of the
hull is ground (a thin frame hugging text covers no hull, stays an obstacle).

**Second blocker found by eye:** with room, the regions grew 2x but the date
still SEWED at the drawn size: the letters are dark-ink beans
(`thin_ink.bean_dark_ink`, stage 4, before the re-set) and stage 7 sews
their spines, read at the drawn size. Dropping the spines sewed the grown
letters as columns with counters filled ("1895" read "1896", gross fault);
`cfg.extra["small_text_reset_bean_follows"]` moves the spines with the letter
(same scale about its centre, same shift). ON: EST 1895 reads clean at 2x.

**The pro (hat DST):** EST 1895 4.5 mm cap (art 1.9, 2.4x), span 30.8 mm
(art 20.9), grown DOWN to 0.4 mm above THE; EAT|STAY|PLAY 4.6 mm (art 2.4,
1.9x; ours 1.575x on main). His letters are bold satin; ours stay bean lines.
Respine stays rejected (EAT read "BAJ", #1510). Sheets:
`eye_pairs_out/fremont-room-1114/sheets/`. The flip is Kent's.
