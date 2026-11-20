---
name: outline-frame-guard-2026-11-14
description: k_line's red box sewn as a satin loop round the K with fill outside = a field read as an art outline; `outline_frame_guard` keeps a holder whose area is 1.0x or more its looped holes' (#1538); ticked ON 11-15 with a combined-check STOP, flipped ON (#1576)
metadata:
  type: project
---

Outline frame guard, 2026-11-14 (#1538). Kent's k_line pins ("the red bean
stitch should not have infill outside of it", "the red box is missing").
Stage 5's geometry is right (a red box with a K-shaped hole). Stage 7 sews
the box through `border_from_outline`: it passes the band and body tests, so
it gets one satin loop round the K with fill under, and its corners are lost.

The rule: an outline is smaller than what it holds. Holder area over its
looped holes' area: To a T frame 0.05, MFab keyline 0.67, Becker keyline
0.72 (all outlines the pro borders); Ahora gear ring 1.37, **k_line box
1.90**, Ahora pink ground 2.10 (fields). `cfg.outline_frame_guard` (built
OFF): at 1.0 or more, `find_art_outlines` tags the holder `framed_field` and
leaves it a field.

**Kent 2026-11-15:** ticked ON with the "K-Line box + gear flags" group
(`outline_frame_guard`, `outline_inlets_kept`, `outline_inlets_teeth`). The
Director had advised holding it for a combined check and a quiet-machine
timing run; both are STOP conditions in the flip PR. Ruled ON 11-15;
flipped ON in code (#1576). Related: [[outline-inlets-2026-11-14]].
