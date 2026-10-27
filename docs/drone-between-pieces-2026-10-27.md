# Drone: the between-piece trim gap, ours vs the pro (satin-split worker, 2026-10-27)

Precision Drone hat at 62.6 mm (`tools.pro_pair` width).

- **Engine:** main 1d83bc4c.
- **OFF arm:** the census's plan. Its md5 a2318ddc equals main's.
- **Recipe arm:** all nine `white_keyline_art.RECIPE` switches set True, plus
  `cfg.extra["absorb_fragments"]`. That is what #1143 makes the default; it
  was still open when this was measured.
- **Route:** the Drone needs no rembg (no `PHOTO_BACKGROUND_REMOVED` on any
  arm).
- **Readers:** `tools.between_walks` (pieces, steps, cover), `tools.trim_classes`
  and `between_walks.diagnose_plan`. Each reads both files the same way.
- **Lettering vs badge:** a step is lettering when its entry point lies inside
  our text regions grown 1 mm. The pro's entry points are mapped into our frame
  by `small_text_floor_census.register` (IoU 0.89).

## Totals

| | ours OFF | ours recipe | pro |
|---|---|---|---|
| DST trims | 104 | 94 | 59 |
| stitches | 14,599 | 14,360 | 14,552 |
| colour blocks / colours / revisits | 12 / 7 / 5 | 11 / 7 / 4 | 23 / 8 / 15 |
| between-piece steps: cut / flown / walked | 71 / 15 / 11 | 70 / 15 / 11 | 37 / 0 / 70 |
| walked mm (buried / on work / bare) | 48 (19 / 25 / 4.1) | 48 (19 / 29 / 0) | 1,022 (541 / 480 / 0.7) |
| lettering: cut / flown / walked | 21 / 9 / 0 | 21 / 9 / 0 | 19 / 0 / 2 |
| badge: cut / flown / walked | 50 / 6 / 11 | 49 / 6 / 11 | 18 / 0 / 68 |
| in-piece cuts (`inpiece_cuts`) | 20 | — | 20 |
| exposed travel (`travel_cover`) | 44.3 mm | 41.5 mm | — |

- **His 59 trims** are exactly 37 between-piece cuts plus 22 colour changes.
- **Our 104** are 71 between-piece cuts, 20 in-piece cuts and 11 colour changes
  (with a couple of edge cases).
- **The gap is the badge's between-piece cuts:** 50 against 18. The lettering
  is at parity: 21 against 19 cuts. The 9 flown are uncut short jumps; he walks
  2.
- **The recipe arm moves one between-piece cut** (71 → 70). Its 10 fewer trims
  are elsewhere: one block fewer and in-piece cuts.

**Our cuts inside a colour block** (`diagnose_plan`, no length budget):

| | cuts | no route under later thread | buried route over budget |
|---|---|---|---|
| OFF | 92 | 91 | 1 |
| recipe | 83 | 81 | 2 (one budget, one gap cap) |

Where the cheapest route's uncovered part lies, in mm:

| | on the ground under it | on a sibling colour sewn earlier | bare | own colour |
|---|---|---|---|---|
| OFF | 248 | 248 | 185 | 97 |
| recipe | 345 | 98 | 173 | 93 |

## Per colour block

Between-piece steps; walked mm is split into buried under a LATER colour and
on work.

| | blk | colour | cut | flown | walk | walked mm | later | on work |
|---|---|---|---|---|---|---|---|---|
| ours OFF | 2 | grey #8c8984 | 11 | 3 | 0 | | | |
| | 3 | orange | 4 | | | | | |
| | 4 | dark #3e3f41 (the ground) | 7 | 1 | 6 | 10.1 | 0.1 | 0.5 |
| | 5 | #5a5e61 | 2 | | | 14.2 | 0 | 9.6 |
| | 6 | light #cccccc | 14 | 7 | 4 | 13.9 | 0 | 9.1 |
| | 7 | grey | 4 | | | | | |
| | 8 | #5a5e61 | 19 | 2 | 1 | 9.9 | 0 | 5.5 |
| | 9 | orange | 10 | 2 | | | | |
| pro | 1-3 | dark / orange / grey | 11 / 8 / 8 | | 0 | | | |
| | 4 | dark #293133 (the ground) | **0** | | **20** | **315.8** | **269.1** | 0 |
| | 5-14 | ten detail passes, revisits | **0** | | 11 | 78 | 69 | 1 |
| | 15 / 16 / 21 | dark / grey / grey | 1 / 3 / 1 | | 0 / 2 / 0 | | | |
| | 17 | black (run outline) | 0 | | 21 | 465.8 | 19.1 | **354.4** |
| | 22 | black (run outline) | 5 | | 16 | 159.4 | 0 | **124.8** |

## His rule on the badge

1. **The ground is one early pass, and it walks under what comes after.** His
   dark ground (block 4) is sewn as one ground under the detail colours: 20
   walks and no cut, 85% of the walked thread buried by later colours. Ours is
   knock-out: the details cut holes in the ground. So our ground's pieces are
   separate, it cuts 7 times, and nothing later covers its gaps (0.1 mm).
2. **The details come in small revisit passes.** He sews the details in many
   passes of a colour (15 revisits). Each pass is one or two pieces with no cut
   inside it: blocks 5-14 have 0 cuts. A revisit costs a colour change (his
   22), and it saves the within-colour hops. Ours sews each detail colour in one
   or two long passes that hop across the badge: 14, 19 and 10 cuts.
3. **The black outline walks on top of finished work by design.** Blocks 17 and
   22 hold 480 mm of walk on work. That is the drone's run-stitch outline, not
   travel; it is what `between_walks`' "lone run line" note warns about.

## Rows that contradict it

- **Black (block 22) cuts 5 times among 16 walks; grey (16) 3 times; 15 and 21
  once each.** That is 10 badge cuts he takes even with his layering.
- **The lettering (blocks 1-3) cuts 27 times and walks almost never**, the same
  as ours. Nothing is sewn later over the letters' gaps.
- **None of his 37 cut hops would have been fully buried** (`cut_hop_fully_buried`
  0). He cuts where no later thread covers, as stage 7's bury rule already
  does.

## What is NOT the lever

**Routing.** 91 of 92 of our in-block cuts have no route under later thread at
any length. A walk or bury rule cannot move them. Gate 3 (chaining) is not
needed and not touched.

**The levers are upstream construction:**

- (a) the badge's dark ground sewn whole under the details (no knock-out);
- (b) detail colours split into local passes and interleaved (revisits) where a
  colour's pieces sit far apart with nothing to walk under.

`silhouette_underfill` (in the recipe) does not reach the Drone. That is
measured: in the recipe arm the ground still cuts 7, and the off-route mm move
from sibling to ground (248 → 345) with no cut gone. Why is inferred, not
re-checked on the Drone: the `silhouette-underfill` and `buried-walk` memory
notes say it hosts ring outlines, and the Drone's ground is not one.

**Both are layout.** Judged from renders, so they are Kent's call (ruling
2026-10-22).
