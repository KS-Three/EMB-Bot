---
name: point-touch-split-2026-11-14
description: NSYNC at 70.9 mm: the star touches the N at one point, so one region and a fan of satin spikes; `point_touch_split` cuts a body that pinches under 0.15 mm into body-sized pieces before the text tagger (#1544); ticked ON 11-15, flip pending
metadata:
  type: project
---

Point-touch split, 2026-11-14 (#1544; eye sweep fault 11). NSYNC at 70.9 mm
on a beanie: the italic N's top-left sews as a fan of loose satin spikes.
Traced to stage 4, not stage 6. The star's arm tip touches the N at a single
point (a 1-2 source px neck, about 0.05 mm), both one navy, so they trace as
ONE region (144.5 mm2). The text tagger's neck split never sees it (same-ink
line only) and its 15% piece floor refuses the star (13%).

`cfg.extra["point_touch_split"]` (`point_touch.py`, built OFF) cuts a body
that pinches under `textcluster.TOUCH_MAX_MM` (0.15 mm) into pieces that tile
it, before the text tagger. Each piece must itself be a body (mean width over
0.8 mm, at least 2 mm2). Lettering, rescued details, counters and enclosed
background are left alone. ON, the N sews as one clean italic N and the star
stands apart; controls md5-identical.

**Kent 2026-11-15:** ticked ON. Ruled ON 11-15, flip pending.
