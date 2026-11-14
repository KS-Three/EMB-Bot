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

PENDING.

## Sheets (OFF | ON | pro)

PENDING.
