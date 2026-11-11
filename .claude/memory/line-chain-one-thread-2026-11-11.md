---
name: line-chain-one-thread-2026-11-11
description: Fix B for low_poly pin 2: line_chain_one_thread, RULED OFF by Kent 2026-11-11 ("very little improvements, if any"); gives a connected drawn line one thread when its core colours agree; 4 of 21 rows move, blocks never change, isometric slab untouched
metadata:
  type: project
---

2026-11-11, Kent after the eye-check of `resnap_hairline_never_lightens`
(that flag's inner lines went blue-grey, isometric's slab went dark gold to
bright yellow): "Keep OFF, build fix B". Doc: `docs/line-chain-one-thread-2026-11-11.md`;
code `digitizer_core/line_chain.py`, called from `pipeline.py` after the re-snap and
rehome, before the colour cap.

- **Rule:** lines no wider than `bean_rule.LINE_MAX_MM` with ink contrast (core
  colour 25+ dE00 from the ground) that touch within 0.3 mm form a chain; if the
  pieces within 12 dE00 of the median core hold 90% of the area, the chain takes the
  nearest LOADED spool (most-used within 15 dE00), cone set never grows. A line that
  really changes colour is refused.
- **Result (21 Commons rows, OFF byte-identical to the stored capture):** 4 move:
  low_poly -22 st / trims 91 to 84 / blocks 6 to 6 (fin outline one black ribbon,
  inner lines black), silhouette +92, vintage -8, chalkboard -70; 17 identical.
  Isometric: 0 of 7 candidates pass the ink test, identical to OFF, slab unmoved.
- **Why it works where flag A did not:** the swing came from the colour cap
  re-choosing a cone; this never adds a cone and moves pieces to the existing cone's
  layer (no layer sandwich, no extra block).
- **Catch:** thresholds are set on these 21 rows; no corpus row has a real
  coloured-outline drawing to prove the uniformity test on. Not flipped on.

**Why:** the colour of a hairline piece read from its own halo is wrong; the line's
colour is one thing, read from its core, shared along its length.
**Ruling 2026-11-11 (Kent, after the eye-check of 5 rows): "Keep off, very little
improvements were made, if any."** Stays default OFF: no flip PR, no pro-pair run,
no more build on this line, no retuning thresholds for a bigger effect. Do not
propose the flip from the dE00 numbers.
**How to apply:** do not flip it; `meta["line_chain_thread"]` on a region shows what it moved.
Related: [[border-colour-change-2026-11-11]], [[bean-census-2026-10-27]],
[[border-by-size-colour-seams-2026-10-28]].
