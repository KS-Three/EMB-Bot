# Connector edge-walk: the walk that buries its hops (2026-11-14)

Kent's ruling on #1490 (2026-11-14), looking at the Becker pin #14
OFF | ON sheet: "Build edge-walk, notice how the pro makes a nice corner
with the thread andc continues the stitch to the right".
`lettering_columns_connectors_buried` stays OFF until this lands and he
sees it.

## What the pro does at a join (read first, by eye)

The pro's Becker hat large DST was read stitch by stitch on MARINE's E, N
and A: eight joins in all. The sew order was drawn phase by phase, and
running stitch was told from satin by the stitch-list rule of
`docs/connectors-on-top-2026-11-14.md`.

**The E**, in this order:
1. **Middle arm.**
   - Its underlay is a zigzag plus edge runs, laid from the stem out to the
     arm's tip.
   - The satin is then sewn back from the tip to the stem. It ends on the
     stem's edge.
2. **Into the stem.** One travel runs from there into the stem. The stem is
   not sewn yet, so its satin later covers that travel.
3. **Stem and bottom arm, as one column.**
   - Underlay runs down the stem and along the bottom arm.
   - The satin then starts at the bottom arm's right end and runs left.
   - At the bottom-left corner the crosses fan about the inside corner. The
     column turns the corner and carries on up the stem.

   There is no join here and no travel. This is Kent's "nice corner with the
   thread": read the other way round, the stem's thread turns the corner and
   "continues the stitch to the right".
4. **Top arm.** Its underlay starts where the stem's satin ended (the top
   of the stem). Its satin then runs from that corner to the right, over
   the stem's top end.

**The N:**
1. The left stem is sewn bottom to top.
2. The diagonal's underlay starts at the stem's top and walks down the
   diagonal, along its edges.
3. The diagonal's satin is sewn from the top-left corner, which it covers,
   down to the right stem's foot.
4. The right stem's satin starts at its own bottom, covering the foot join,
   and is sewn to the top.

**The A:**
1. The crossbar is sewn first.
2. The right leg is sewn up to the apex.
3. The apex is sewn.
4. The left leg is sewn down from the apex.

Each leg's satin covers an end of the crossbar.

**The rule, on all eight joins:**
- The stroke sewn first ENDS at the join.
- The next stroke's satin STARTS there and covers it.
- The needle gets from one to the other inside the next stroke, as that
  stroke's underlay (a zigzag and runs along its edges), before its satin.
- A stroke with a free tip (the E's middle arm, the A's crossbar) is run
  out to the tip under itself and sewn back to its join.
- Where two strokes turn a corner, one column turns it.
- No travel crosses a finished stroke, and no join is cut.

## Why ours crossed finished satin

The Column lane walks a letter's span graph with a Chinese-postman Euler
trail (`columns._euler_trail`).
- **What the trail cares about.** It visits every span and puts the trail's
  ends near the needle's way in and out.
- **What it does not.** It never asks which END of a stroke the next stroke
  starts at, so a stroke often ended at its far tip while the next one
  started back at the join. The hop then ran back across the stroke just
  sewn: Kent's pins #14/#15.
- **What `connectors_buried` (#1490) could do.**
  - Rail choice: pick the rail a leg ends on.
  - Otherwise cut the hop: that is the +50 trims.
- **Why its re-route never fired.** On these letters no path existed under
  later satin, because the order made the next stroke start on the wrong
  side.

## The build: `cfg.lettering_columns_connectors_edge_walk` (built OFF)

It implies `connectors_buried`.

**Which letters it touches.** The letter is first sewn as
`connectors_buried` sews it. When that leaves a trim inside the letter, or a
hop more than 1.0 mm on finished satin, the walk order is searched
(`columns._edge_walk_trails`). A letter that sews clean keeps its walk byte
for byte.

**The search, per component of the letter's span graph:**
- **Candidates:** every Euler trail of the spans the postman gave it, from
  any start the parity allows, then the same with any one more span doubled.
  A doubled span is "run out under a stroke, sew it back".
- **The price** reads stations. A hop from a satin leg's last cross (the
  better rail) to the next leg's first centre point costs a trim when it
  would be cut (more than 1.0 mm on finished satin and not under satin to
  come) or jumped past the trim distance. A hop into or out of the letter
  past the trim distance costs one too.
- **Real check:** the 8 best-priced walks are sewn and measured on their
  stitches (`columns._walk_cost`). The station price is only a ranking,
  because tucks, rails and underlay move the real hops.
- **Who wins:** a walk replaces the postman's only when it is strictly
  better on (trims, mm of over-limit hops on finished satin). Among those,
  the least on top wins, then the least travel, then the shortest hops in
  and out.

Then `connectors_buried`'s rail choice and its cut run on the walk chosen.
The cut stays as the fallback where no order buries a hop.

**The fold-cut judge** (`fold_cuts`) still reads each candidate cut on
`connectors_buried`'s walk. Edge-walk changes the order, not the cut, and
each cut is sewn once.

This is not a walk along a finished stroke's edge. The pro never does that
at these joins. He changes the order so the travel lies inside the stroke
sewn next. "Edge-walk" here is the needle reaching the next stroke inside
it, under its satin to come.

## Becker MARINE's six letters, lane only (fixture)

`testdata/becker80_lane_letters.json` holds the six letters stage 7 hands
the lane at 80 mm. They were sewn with the lane flags stage 7 passes by
default (fold cuts, square ends, rail axis, corner fold, inside stagger,
inside connectors). Trims count a hop into or out of the letter past the
trim distance.

| arm | trims | letters' travel on finished satin |
|---|---|---|
| OFF | 12 | 18.1 mm |
| connectors_buried | 15 | 0.4 mm |
| edge-walk | 12 | 0.4 mm |

Per letter:
- **The A:** 3 trims under connectors_buried, 1 under edge-walk. Its
  crossbar is now sewn first and its legs over its ends, as the pro does.
- **The E:** 4 trims, then 3.
- **The N:** keeps one cut. The cut the fold judge picks for it puts the
  left stem in a component of its own, and no order inside the other
  component buries the hop.

Without the default lane flags (the fixture's recorded call):
- the N's two cuts and the A's one go;
- the N sews the right stem, then the diagonal from its foot up, then the
  left stem.

Time: the lane takes about 1.5x as long on these letters (13 s against 9 s
for the six). Letters that sew clean cost one extra measure.

## The 28 lettering designs (full digitize, one at a time)

#1490's corpus: the same 28 designs, with OFF, `connectors_buried` and
edge-walk all digitized on this branch's tree. These are rows only: nothing
was kept but the numbers.
- **Letters' travel on finished thread:** the kind rule of
  `docs/connectors-on-top-2026-11-14.md`, travel no later thread covers, in
  lettering shapes, rastered at 20 px/mm with 0.4 mm thread.
- **Trims:** the design's own trim count.
- **Exposed:** travel with no stitching within 0.3 mm.

Each cell reads OFF / buried / edge-walk.

| design | letters' travel on finished thread, mm | trims | stitches | exposed travel, mm |
|---|---|---|---|---|
| becker_hat_large | 15.8 / 0.0 / 0.0 | 12 / 14 / 13 | 16289 / 16287 / 16291 | 0.0 / 0.0 / 0.0 |
| mfab_hat | 9.4 / 0.0 / 0.0 | 17 / 22 / 20 | 20849 / 20846 / 20863 | 0.0 / 0.0 / 0.0 |
| lt_and_pizza | 11.0 / 0.0 / 0.5 | 5 / 7 / 7 | 2454 / 2385 / 2407 | 0.0 / 0.0 / 0.0 |
| lt_bukit_asam | 6.6 / 2.4 / 2.4 | 10 / 11 / 10 | 2046 / 2065 / 2060 | 0.1 / 0.1 / 0.1 |
| lt_dot_music | 7.4 / 0.0 / 0.0 | 5 / 5 / 5 | 1529 / 1526 / 1526 | 0.4 / 0.0 / 0.0 |
| lt_jakarta | 15.6 / 4.2 / 3.0 | 22 / 27 / 23 | 2966 / 2990 / 2936 | 0.0 / 0.0 / 0.0 |
| lt_k_line | 9.7 / 0.0 / 0.0 | 10 / 14 / 12 | 3372 / 3382 / 3414 | 0.0 / 0.0 / 0.0 |
| lt_n_sync | 1.7 / 0.3 / 0.3 | 2 / 2 / 2 | 2479 / 2478 / 2478 | 0.0 / 0.0 / 0.0 |
| becker_lc_large | 26.0 / 2.9 / 0.2 | 13 / 16 / 12 | 14951 / 14957 / 14902 | 0.0 / 0.0 / 0.0 |
| becker_hat_small | 21.4 / 2.8 / 0.0 | 12 / 15 / 11 | 10576 / 10583 / 10566 | 0.0 / 0.0 / 0.0 |
| becker_chest_small | 21.3 / 2.8 / 0.0 | 12 / 15 / 11 | 10339 / 10346 / 10315 | 0.0 / 0.0 / 0.0 |
| becker_beanie | 24.5 / 3.1 / 0.0 | 16 / 19 / 15 | 13902 / 13908 / 13879 | 0.0 / 0.0 / 0.0 |
| mfab_lc | 5.9 / 1.4 / 0.9 | 20 / 24 / 21 | 17897 / 17915 / 17945 | 0.0 / 0.0 / 0.0 |
| bridge_hat | 2.2 / 1.7 / 1.7 | 12 / 13 / 12 | 8569 / 8574 / 8568 | 0.0 / 0.0 / 0.0 |
| bridge_lc | 8.2 / 1.2 / 1.2 | 13 / 16 / 14 | 10998 / 11010 / 11005 | 0.0 / 0.0 / 0.0 |
| gaulke_roofing_hat | 11.8 / 0.0 / 0.0 | 33 / 35 / 33 | 7494 / 7471 / 7467 | 0.0 / 0.0 / 0.0 |
| gaulke_roofing_lc | 11.8 / 1.5 / 2.0 | 24 / 29 / 26 | 5852 / 5870 / 5891 | 0.0 / 0.0 / 0.0 |
| gaulke_roofing_beanie | 8.2 / 1.7 / 1.7 | 26 / 27 / 26 | 7679 / 7655 / 7651 | 0.0 / 0.0 / 0.0 |
| hotel_fremont_hat | 14.0 / 0.9 / 0.9 | 28 / 28 / 28 | 16106 / 16107 / 16107 | 0.0 / 0.0 / 0.0 |
| hotel_fremont_patch | 10.2 / 7.0 / 7.0 | 23 / 23 / 23 | 15061 / 15060 / 15060 | 0.0 / 0.0 / 0.0 |
| precision_drone | 8.6 / 1.4 / 1.4 | 93 / 93 / 93 | 14984 / 14979 / 14979 | 0.0 / 0.0 / 0.0 |
| proseal_hat | 10.6 / 5.2 / 4.4 | 46 / 48 / 44 | 6434 / 6440 / 6419 | 0.0 / 0.1 / 0.1 |
| proseal_beanie | 4.6 / 2.9 / 3.6 | 39 / 40 / 39 | 7785 / 7790 / 7795 | 0.0 / 0.0 / 0.0 |
| goldentee_hat | 1.6 / 0.8 / 0.8 | 45 / 45 / 45 | 13636 / 13633 / 13633 | 0.0 / 0.0 / 0.0 |
| lt_ahora, lt_but_seriously, lt_hed_p_e, toat_machine_hat | unchanged in all three (md5 same) | | | |
| **total (28)** | **268.1 / 44.2 / 32.0** | **589 / 639 / 596** | 268308 / 268318 / 268218 | 0.5 / 0.2 / 0.2 |

**Totals:**
- Edge-walk keeps `connectors_buried`'s cleanup and more: letters' travel on
  finished thread is 268 mm OFF, 44 buried, 32 edge-walk.
- It gives back 43 of buried's 50 extra trims: +7 over OFF, not +50.
- **Better than OFF on trims:** five designs, every Becker job but the hat
  large, and ProSeal hat.
- **Worse than OFF on trims:** eight designs, MFab hat the most (+3).
- **Same walk as buried (md5) on ten designs.** Their hops were already
  clean or no order bettered them.
- Three designs read slightly more travel on finished thread than buried:
  and_pizza 0 -> 0.5, Gaulke LC 1.5 -> 2.0 and ProSeal beanie 2.9 -> 3.6 mm.
  Each hop there is under the 1.0 mm limit, and each design trades it for a
  trim or more back.
- **Time:** the whole digitize took the same under both, 1261 s against 1263
  s for buried over the 28. The lane's extra work is lost in the run.

## The pins (OFF | edge-walk | pro)

Sheets, gitignored, in the primary checkout:
`digitizer/eye_pairs_out/jag-source-1113/edge-walk/sheets/`.

There are six Becker hat large joins, OFF | edge-walk | pro thread:
- Kent's pins #14 and #15;
- the E's middle-arm join;
- the N's top and foot;
- the A's crossbar.

The pro is aligned by phase correlation of the two designs' coverage.

By eye:
- **#14:** the diagonal thread across the E's stem foot is gone. The corner
  is not what the pro sews (see "Not done").
- **#15:** the diagonal across the top arm is gone.
- **The other four joins:** they read as OFF did. Nothing new on top.

## Not done: the corner itself

Kent's words point at the corner as much as at the travel.
- **What the pro does there:** the E's bottom-left is ONE column turning the
  corner. Its crosses fan about the inside corner and carry on into the arm.
- **What this build does there:** it takes away the thread across the
  stroke, but our corner still butts two columns.

`lettering_columns_corner_fold` (ON by default) is the column that turns a
corner, and on Becker's E it is not taken. Traced on the 80 mm lane
fixture:
- Both of the E's inside corners pass its corner test: turns of 100 and 88
  deg, each with an apex across.
- Each then finds THREE column pieces within 0.3 stroke widths of the
  corner: the stem, the arm, and the middle arm.
- At 1.42 px/mm art the slots on either side of the middle arm are about
  1 mm wide, so the middle arm's piece is as large there as the arm's own
  (0.44 / 0.40 against 0.48 / 0.38 mm2).
- The rule refuses a third piece over a tenth of the second
  (`outline_cut._fold_corners`), so neither corner folds.

Letting the fold through on a narrow slot is the next build. It is separate
from this one.

Script words (`script_strokes`) call the walk without either flag.
