---
name: flag-stripe-underfill-2026-11-12
description: Kent's flag idea built OFF: `stripe_underfill` sews the lighter thread as one fill under a stripe field, darker bands satin on top held at art; `satin_free_end_chord_aim` squares ends a raster hook slanted
metadata:
  type: project
---

2026-11-12, branch `claude/flag-stripe-underfill`, from Kent's Flag.webp at 96 mm Hat Front.
Kent: "why not fill in the entire bottom of the flag white (to provide structure), and then
do the red stripes in satin?", then "Build it, OFF" and "THEN fix the ends".

**Side by side (today):** every stripe sewed ~4.65 mm from 3.96 mm art; white sews last and
lay over red: white 4.67, inner red visible 3.14. The 10-30 flags (see
[[flag-stripes-seam-cap-2026-10-30]]) still OFF; ON they even it, 3.92 / 3.90.

**`stripe_underfill`:** `silhouette_underfill.plan_stripes` reads a chain of >= 4 bands (rect
fill 0.9, aspect 4, within 5 deg), two threads alternating, union solid. Lighter thread (L*)
= host, fills the union via `apply(rings=...)`; red bands tagged `STRIPE_ON_KEY` hold rails
on the fill outline (stage 7 `stripe_ground`); host tagged `STRIPE_HOST_KEY`: stage 5 keeps
it to the outline (its pull ran 0.4 mm past the red ends) and no under-fill rim (1,615
stitches under the red). `_carriers_first`: the canton carries the stars, so it stays ahead
of the white (a carried shape sits in a HOLE: test the carrier's exterior). Flag: inner red
3.86, white gap 3.96, outer red 4.23 (outer edge keeps its pull). 15,930 -> 21,107 stitches
(+32%). Not on photo classes.

**`satin_free_end_chord_aim`:** the left ends' spine ended in a 0.17 mm hook at 16.5 deg,
tip mid-stroke (half 1.04), so `_cut_cap_fork` rightly refused (no turn >= 20, no pinch)
and `_extend_to_cap` aimed 1.9 mm along the hook. ON: stray > 8 deg off the one-stroke chord
-> chord aim; plus the corner path's 0.03 mm cap inset on every free end (a dead-square cap
kept 2.6 of a 3.9 mm final cross). With `satin_cap_skew_inset` too, every end reads square.

**Open:** pull on a satin sewn over a fill is a sew-out question (gate 1). Corpus effect of
each flag measured in the PR body.
