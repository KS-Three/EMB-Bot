# Column-lane cover hand-back, narrowed: description and confirmation (2026-11-13)

Kent's ruling on the first census ([`column-cover-handback-census-2026-11-13.md`](column-cover-handback-census-2026-11-13.md)),
2026-11-13: **"Narrow it, re-census"**. The flag `lettering_columns_cover_handback` stays **OFF**, and flipping it is
Kent's call.

The rule below is a **foreman's decision, not a Kent ruling**. Among three candidates (STRICT, NET, a 10 mm² floor),
the foreman picked NET.

## The rule (`columns.handback_wins`, `HANDBACK_RULE = "net"`)

1. The Column lane sews a text-tagged shape and covers under 0.90 of it (`satin_cover`).
2. The ordinary ladder is then sewn ONCE as a trial, as the shape would sew untagged.
3. The ladder's runs replace the lane's only when the ladder puts **at least as much new thread inside the shape as it
   adds outside it**:
   - cover gain ≥ spill gain, measured as satin and fill thread widened 0.2 mm a side;
   - and its cover is higher than the lane's.
4. Otherwise the lane's runs stand, and the trial leaves nothing behind.

There is no fitted constant.

## Pass line, committed BEFORE the confirmation run

For every shape the narrowed rule hands back on fresh material:

> **per shape cover gain ≥ spill gain; no board figure worse; OFF byte-identical**

**The per-shape half is true by construction.** It is the rule itself, so it cannot fail. The confirmation therefore
also reports a check that **no rule reads**: thread laid over the shape's own holes, which means a counter sewn shut.
Every fresh hand-back is also rendered for the eye.

**Fresh material** means shapes the rule was not chosen on:
- every starter design across its ±2% width sweep (9 widths each, its pack config);
- the 9 commons lettering logos at 65 and 100 mm;
- the Becker, Fremont, Drone and MFab art at 70 and 110 mm;
- typed lettering (4 outline fonts × 3 texts) at 50 and 120 mm.

None of these widths was used in the first census. If the fresh hand-backs are too few to say anything, the count is
reported and the confirmation stops there.

## Part 1: the 13 candidates (a DESCRIPTION, not a test)

The rule was chosen after looking at these same 13 shapes, so how it scores on them describes the choice. It does not
test it.

RESULTS_13

## Part 2: fresh confirmation

RESULTS_FRESH

## Runtime cost of the trial

RESULTS_COST

## Open item (not a task)

**The owl's −4.5% black** at targets 79.2 / 79.6 / 80.8 / 81.6 mm is still untraced. Three black shapes are tagged as
lettering at those widths, but the lane already covers them at 0.90 or more. So neither version of the hand-back
touches them, and the loss has another cause ([`monarch-size-cliff-2026-11-13.md`](monarch-size-cliff-2026-11-13.md)).
