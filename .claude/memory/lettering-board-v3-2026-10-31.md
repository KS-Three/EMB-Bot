---
name: lettering-board-v3-2026-10-31
description: lettering board re-baselined on engine a8758e96 -- <4 mm cc +0.66 -> +0.92 (pro +1.00), but Fremont's gain is bean construction, not the pro's satin; Becker trims inside letters 62 -> 21; Drone's gap reads as thread contrast
metadata:
  type: project
---

Baseline: `docs/scoreboards/lettering-board-2026-10-31.{md,json}`, engine `a8758e96`, tree 38094e04,
tesseract v5.4.0.20240606, 42 lines, no job rerouted. Compare a lettering PR against this one.

**Headline (ours / pro, cc):** <4 +0.92 / +1.00, 4-6 +0.90 / +0.98, 6-10 +0.84 / +0.92, 10+ +0.97 / +0.68.
Reach <4 3.58 / 3.81. Trims inside letters 10+ 21 / 14 (was 62).

**Fremont's jump is a stitch-type change.** Hat <4 cc: main +1.00; `dark_ink_bean` OFF +0.33;
`keep_dark_thin_strokes` OFF +0.38; `bean_only_lines` OFF +1.00. The tan small letters are dark reads on their
ground, so they bean along the skeleton at about drawn size; columns 43 -> 16 is that, not a reader fault. The pro
re-sets them much larger in satin. The bean reads better on the render; nothing is sewn. Quote it with that.

**Drone's gap is mostly contrast, read by hand (not by the board).** PRECISION is one thread, 204 grey (median
rendered 180; pro 134). Crops forced dark: ours PRECISAIN, pro PRECISION, psm 8; raw ours "PRE Tig IN". AND DRONE:
ours 140-137-132 with A's pieces in 90-94-97, median 141 against the pro's 55. The pro darkens lettering the art
draws pale on a dark panel. Which garment he assumed is not established.
Related: [[lettering-board-v2-2026-10-27]], [[dark-ink-bean-2026-10-28]], [[dark-thin-strokes-flip-2026-10-28]].
