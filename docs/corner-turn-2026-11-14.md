# Corner turn: one column round a letter's corner (2026-11-14)

Kent on #1490's Becker pin #14 sheet (2026-11-14): "notice how the pro makes
a nice corner with the thread andc continues the stitch to the right".
`lettering_columns_connectors_edge_walk` (#1512) took the stray thread off
that corner but left the corner itself as a butt joint. This page is the
corner.

## What the pro does at a corner (read first, by eye)

I read the needle paths of the pro's DSTs phase by phase, satin told from
running stitch by the stitch-list rule
(`docs/connectors-on-top-2026-11-14.md`). There are nine corners on Becker
hat large's MARINE and MFab hat's WELDING.

| corner | the pro's construction | short stitches |
|---|---|---|
| Becker E, bottom-left (stem into bottom arm; Kent's pin #14) | **fan**: one column, the bottom arm sewn right to left, its crosses pivoting about the inside corner, then on up the stem | inner ends converge on the inside corner; outer ends walk round the apex |
| Becker E, top-left (stem into top arm) | **cap**: the stem's satin stops at the arm's lower edge; the top arm, sewn last, starts at the letter's left edge and covers the corner square | none: the arm's first crosses are full length |
| MFab E, top-left | **fan**: the top arm sewn right to left turns down into the stem | inside, as above |
| MFab E, bottom-left | **fan**: the stem turns into the bottom arm, sewn left to right; top arm, stem and bottom arm are ONE column | inside |
| Becker R, top-left (stem into the bar) | **cap**: the bar, sewn first, runs to the left edge; the stem's satin stops under it | none |
| Becker R, bar into bowl | one column turning through the curve (a bend, not a corner) | inside of the curve |
| Becker N, top-left (acute) | **cap**: the diagonal starts at the top-left corner, over the stem's top | none |
| Becker N, bottom-right (acute) | **cap**: the right stem starts at its own foot, over the diagonal's end | none |
| Becker A, apex (acute) | **cap**: a short column across the apex between the two legs | none |

T junctions are butted, never turned. The E's middle arm is sewn before the
stem and the stem's satin covers its root (both E's), and the A's crossbar is
sewn before the legs.

**Read:**
- **Right-angle L corners:** the pro fans three of the four read. Every fan
  pivots on the inside corner, so the short stitches are on the inside.
- **Acute corners and T junctions:** he caps or butts. Our lane already
  does too: the fold takes 35-110 deg turns only, and never a T's "through"
  pair.

## Why ours did not turn Becker's E

`lettering_columns_corner_fold` (ON by default, 2026-10-23) is this
construction. At a lone concave corner it joins the two columns there into
one "folded" column whose crosses fan about the inside corner (`_fold_pair`).
On Becker's E it is refused.

**What goes wrong:**
- Becker's art is 1.42 px/mm, so the E's two slots, traced, narrow to a
  point.
- Each inside corner is then a slot's TIP, and three column pieces touch it:
  the stem, the arm the fold would turn into, and the arm across the slot.
- The fold takes a corner only where two columns meet (a third piece over
  a tenth of the second refuses it). The arm across the slot had 0.40-0.44
  mm2 within 0.3 stroke widths against the arm's own 0.38-0.48.

`outline_cut._fold_corners` traced on the 80 mm lane fixture.

At Becker hat large's real size (101.9 mm, the size of Kent's pin) it is
worse.
- The slot tips turn 120-121 deg, past the fold's 110 limit.
- Each L corner is split across two concave vertices: the tip, plus the
  arm's root at 55-57 deg.
- The tip's bisector points straight into the stem, between the two arms.
  So the nearest apex it finds belongs to the arm across the slot, and
  `_fold_pair`'s arc test rightly refuses that pairing ('long_way').

## The build: `cfg.lettering_columns_corner_fold_apex_side` (built OFF)

The flag acts under `corner_fold`, in `outline_cut._fold_corners`, and
changes three things:
1. **A corner counts only the pieces on its APEX side:** the half-plane
   through the inside corner, square to the line to the apex the fold
   sweeps. The arm across a pointed slot lies on the far side, where no fold
   cross goes.
2. **A slot's tip is a corner up to 130 deg.** This applies only to a tip on
   the letter's OUTER outline. A counter's corner keeps the 110 limit: the
   first version took ProSeal hat's A counter top (125 deg) and fanned the
   A's apex, which the pro caps, and read worse by eye.
3. **Each apex is tried in turn**, every convex corner within 0.6-2.6 W on
   the corner's side (cosine to the bisector over 0.15), nearest first,
   until a pair folds. `_fold_pair`'s own tests (the arc, the width ratio,
   the cover) pick out the L.

Nothing else in the fold changes:
- the cross construction;
- the width ratio;
- the arc limit;
- the T-junction refusal.

No apex-cut code is touched.

**Becker's E at both sizes:**
- It becomes ONE column, top arm -> stem -> bottom arm, fanned round both
  corners, and the middle arm is sewn on its own.
- The whole E is the form of the pro's MFab E.
- At its bottom-left it is the pro's Becker corner, the one Kent pointed
  at.
- At its top-left the pro's Becker file caps instead, so we differ from him
  there.
- The fans are larger than his: Becker's arms are as wide as its stem, and
  its corner squares are a third of the letter.

## The 28 lettering designs (OFF | ON, full digitize, one at a time)

#1490's corpus: the same 28 designs, digitized OFF and ON on this branch's
tree, rows only. OFF is byte-identical to the edge-walk corpus's OFF on all
28 (md5), so the flag off changes nothing.

ON moves the five Becker jobs and nothing else: their E is one column round
both corners. The other 23 designs are byte-identical, including:
- MFab;
- ProSeal;
- every lettering logo;
- the Gaulke, Bridge and Fremont jobs.

| design | letters' travel on finished thread, mm | trims | stitches |
|---|---|---|---|
| becker_hat_large | 15.8 -> 4.1 | 12 -> 11 | 16289 -> 16464 |
| becker_lc_large | 26.0 -> 15.0 | 13 -> 12 | 14951 -> 15106 |
| becker_hat_small | 21.4 -> 12.6 | 12 -> 11 | 10576 -> 10699 |
| becker_chest_small | 21.3 -> 12.6 | 12 -> 11 | 10339 -> 10483 |
| becker_beanie | 24.5 -> 15.8 | 16 -> 15 | 13902 -> 14034 |
| **total (28)** | **268.1 -> 219.2** | **589 -> 584** | 268308 -> 269037 |

**What the numbers mean:**
- The travel drops because the E needs no hop: one column runs through
  both corners.
- The E's own trim goes.
- The fans add about 130-175 stitches an E.
- Exposed travel is unchanged at 0.

## Sheets (OFF | ON | pro)

Gitignored, in the primary checkout:
`digitizer/eye_pairs_out/jag-source-1113/corner-turn/sheets/`.

There are the six Becker joins of the edge-walk sheets, the whole E, and
Kent's 14 end/corner pins from #1481. The pro is aligned by phase
correlation; the lettering logos have no pro file.

By eye:
- **#14 (Kent's corner):** the stem's thread turns the corner and carries
  on into the bottom arm, the crosses fanning about the inside corner. The
  pro's panel shows the same fan. OFF's diagonal is gone too.
- **#15:** the diagonal is gone. The top-left now fans into the stem, where
  the pro's Becker file caps; his MFab E fans there.
- **The whole E:** a C-shaped column with the middle arm butted. It reads as
  one stroke round the corners. The fans are large because Becker's arms
  are as wide as its stem.
- **The other joins:** the N's top and foot, the A's crossbar and pins #10,
  #11 are unchanged.
- **The 12 other end/corner pins:** k_line, and_pizza, Jakarta, ProSeal,
  Gaulke and Fremont are unchanged. Their designs do not move; those pins
  are end faces and acute joints, not L corners.

## With edge-walk and apex cut

Kent ruled `lettering_columns_connectors_edge_walk` and
`lettering_columns_apex_cut` (with its guard) ON on 2026-11-14. Their flip PR
belongs to another worker.

With this flag OFF, neither one's output changes anywhere: the cut and the
walk are byte for byte.

With this flag ON, read on the lane inputs of Becker 80 mm, Becker hat large
and ProSeal hat:
- **Only Becker's E changes.** It changes under each of edge-walk, apex
  cut, and both.
- **ProSeal's 28 letters are byte-identical** under every combination.
- **The E with the corner turn** sews no trim and nothing on finished
  satin, whatever else is on. Edge-walk then has nothing left to reorder.

So the flip PR's Becker E sheets (#14, #15, the E's middle-arm join) would
read differently if this flag is also ON. Its N, A and ProSeal sheets would
not.

## Not done

- **The top-left of Becker's E.** Kent's pin is the bottom corner, but the
  turn takes both. The pro caps Becker's top-left and fans MFab's, and no
  rule here tells the two apart.
- **Acute corners** (N, A, M) keep their caps. That is the pro's way.
- **Script words** (`script_strokes`) do not use the fold.
