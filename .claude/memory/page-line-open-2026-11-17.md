---
name: page-line-open-2026-11-17
description: "Kent 2026-11-17: page_line_open ON (Flip ON, Recommended): the art's thin white line (two_tone.keep_lines) stays bare fabric as in the pro's one-thread Gaulke DST; page_line_front stays OFF; only Gaulke moves; our hairline is thinner than the pro's (pull comp, needs a sew-out)"
metadata:
  type: project
---

**Fault (prime grader scorecard 2026-11-17, `gaulke_roofing_hat`):** the hairline white gap under the inner roof
sewed as a wide white satin bar over the thin black line beneath it (ragged fringe).

**Cause, traced stage by stage:** stage 1 marks the gap background, but stage 1.3 `two_tone.keep_lines`
(2026-10-08, written so golke's roof lines do not close to one black mass) hands a thin white channel back as
light ink and widens it to the satin floor into the ink either side. That white is a region of its own
(thread White, layer 1) and sews AFTER the black, so its satin covers the black line's edge.

**What the pro does** (`c golke logo hat.DST`, read at 30 px/mm): 0 colour-change commands, one black thread.
The light line is bare fabric 0.73-0.83 mm wide between the roof mass and a 1.17 mm black line, the art's own gap.

**Two flags:** `page_line_front` (sew the line first so the ink lays over it; OFF) and `page_line_open`
(leave the channel unsewn; **ON, Kent "Flip ON (Recommended)"**). No new width or tolerance number; a review
`stitched` still wins. PRE_FLIP arm `PAGE_LINE_OPEN_2026_11_17_OFF`; `tests/engine_2026_10_27.json` keeps false.

**Reach:** 9 pro jobs and 26 fixtures at 80 mm, 1 each moves (Gaulke), the rest byte-identical.
Pictures and the by-eye calls: `docs/renders/page-line-front-2026-11-17/`.

**Still wrong (a sew-out, gate 1):** our fabric hairline is thinner than the pro's and broken in places, because
the black fills' pull compensation closes into the channel. Widening it means touching pull comp.

**Trap:** `pro_pair.digitize(..., None)` is the shipped default, so an OFF arm must pass
`{"page_line_open": False}` now.
