---
name: mfab-recipe-trims-2026-10-26
description: MFab recipe trims (Kent's "Prepare the flip", 2026-10-26). The trims came from keyline slivers behind a dark hairline; keyline_fold_slivers folds them into the field (OFF). Hat 41 -> 27, LC 54 -> 29 with skip_covered_shapes + fill_section_travel; the hat's on-thread exposed travel rises 23 -> 43 mm
metadata:
  type: project
---

Kent chose "Prepare the flip" for the MFab recipe (d2 + panels + mitre) on
2026-10-26: cut its trims first, render it on the other jobs, then flip from
one sheet. This was the trims half. Full record:
`docs/mfab-recipe-trims-2026-10-26.md`.

**How the pro avoids each cut** (read with `tools/sequence_pro` /
`inpiece_cuts`, one reader on both DSTs):

- **Under-fill:** ONE stretch, 9,199 stitches, no lift. Ours makes 12 / 8
  cuts: underlay ring hops plus fill sections. That is #1091's class, cured by
  its `fill_section_travel`.
- **White:** 7 stretches, two of them long satin chains that open with a run
  walk he then covers.
- **Specks:** he has none. Every one of our 31 (hat) / 51 (LC) white sliver
  stitches lies within 0.3 mm of his white.

**The slivers are the keyline cut off by a dark hairline the art draws on its
inner edge.** In order the trace reads: letter, sliver, hairline, field. Our
loop rides the field's hole (the hairline's outer edge) and never reaches the
sliver; the pro's rail is on the letter.

`keyline_fold_slivers` (built OFF) folds a piece back into the field when it
is:

- in the field's thread, not routed, and not text;
- narrower than a thread, and within a thread of the field.

Slits a fold closes are filled, and a fold may shrink a hole but never split
one. It is the lever: −11 / −21 cuts.

`skip_covered_shapes` (built OFF) drops a shape whose whole thread lies on its
own colour block's other thread. It takes the LC −6 and the hat 0.

**What tripped this session:**

- **Kent had already ruled `trim_bury_under_later` ON** (#1057, unmerged). A
  same-colour bury variant was built and dropped as superseded. Measure on
  `BASE` (`tools/sewout_card_v7.py`), not on main's defaults.
- **The Column lane re-sequences itself with the lane OFF** to rank shapes. A
  pass that DROPS shapes must be off in that inner call, or it re-orders
  unrelated blocks (the riders did).
- **The first fold left 72 new pinhole holes in the field:** 61 became 133.
  Count holes after any polygon union.

**Why:** the trims looked like a cutting policy, but they were construction
(the trace). **How to apply:** before tuning cuts, ask whether the pro has the
piece at all. The hat's exposed travel rises 23 -> 43 mm, on thread and
same-colour, from the fill tier reacting to a 5 mm² change in the host's
shape; flag it with the renders, don't hide it. Related:
[[mfab-underfill-panels-2026-10-25]], [[sequence-like-pro-2026-10-25]],
[[trim-economy-2026-10-21]], [[cut-after-bury-2026-10-23]].
