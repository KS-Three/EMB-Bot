---
name: cap-frame-height-2026-10-26
description: PHYSICAL FACT, Kent 2026-10-26 - his cap frames sew at least 64 mm (2.5 in) tall. Gate 1 for hat-front height is settled by his frames; the pro's hat box (113.5 x 64) is the auto-fit default (`garments.proSized`).
metadata:
  type: project
---

Kent, 2026-10-26, asked whether the pro's 64 mm hat height fits his cap
frames (ROADMAP gate 1: a physical constant, which geometry cannot settle).
His words: **"64 mm (2.5 in) or more"**. The option he picked read: "Then the
pro's boxes can go on: hat 113.5 x 64, left chest 96 x 64.5, beanie 94.5 x 56
mm. Auto-fit lands within about 1-3% of the pro's widths, against 11-15%
today."

**Why it matters:** the Hat Front box was 5.0 x 2.25 in (127 x 57.2 mm), and
nothing in the repo said whether the 2.25 in was a cap-frame limit. The pro
sews 6 of his 12 hats taller than 57.2 (to 63.8). Kent's frames take 64 mm or
more, so the 2.25 in was a round number, not a field.

**How to apply:** do not re-raise hat height up to 64 mm as a gate-1 question;
Kent's frames settle it. ABOVE 64 mm is unasked: a box taller than that is a
new gate-1 question for Kent. `src/garments.js` `PRO_PLACEMENT_MM` is the
default (`proSized`); `{ proSized: false }` is the round-inch box.
Related: [[garment-size-like-pro-2026-10-26]].
