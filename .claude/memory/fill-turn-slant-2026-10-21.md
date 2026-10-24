---
name: fill-turn-slant-2026-10-21
description: fill_turn_slant built OFF (PR #1036); Kent 2026-10-22 holds it OFF until the next sew-out card carries an OFF/ON swatch
metadata:
  type: project
---

`cfg.fill_turn_slant` (PR #1036, built OFF): fill rows turn 0.7 mm along the row
(`machine.FILL_TURN_ALONG_MM`, `stage6_fill._slant_turns`) like the pro's
0.71-0.83 mm turns, instead of one 0.15 mm pitch straight across. Fremont
sub-0.5 mm stitches 3,084 -> 847, Drone 2,013 -> 1,098; OFF byte-identical.

**Kent 2026-10-22: hold OFF; the OFF/ON fill swatch goes on the NEXT sew-out
card.** The one open question is cloth: whether the corner the slanted thread
lies over stays covered at real thread width (renders hide it at 0.4 mm, show
it at 0.2 mm).

**Why:** a render cannot settle thread width; Kent cannot sew right now.
**How to apply:** don't flip it from renders or numbers; when building the next
sew-out card, add a fill swatch pair OFF/ON. The rule to keep: pull the INNER
point of each turn — pulling every entry drew a staircase on widening edges.
Edge "penetrations per mm" vs region polygons is meaningless here: fills sew on
a grown polygon. `src/fill.js` port started from the parent session 10-22.
Detail: `docs/fill-turn-slant-2026-10-21.md`.
