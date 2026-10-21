---
name: card-v4-sewout-letter-size-2026-10-20
description: Card v4 sew-out beside the pro's Fremont patch — the pro RAISES all small lettering to ~4 mm (EST/1895 2.1x the art, tagline 1.55x) and satins it; we trace the art's size as a hairline; plus 81 vs 92.5 mm. Box-clipped measures misled twice
metadata:
  type: project
---

2026-10-20/21: Kent sewed card v4 (`docs/sewout/card-v4-2026-10-20/`, PR #1024) on
black twill beside the pro's Fremont patch, paused mid-way. Kent: "your lettering
is much smaller than the pro's", then "it could be a scaling issue".

**Measured 2026-10-21** (pro DST from `Embroidery Files.zip` Hotel Patch, letters
by colour block, 1-99% stitch extent; art by connected components; both at
92.5 mm; `tools/pro_pair.py` sheets show it at a glance):

| text | art height | pro height | pro/art |
|---|---|---|---|
| EST | 1.9 mm | 3.9 | 2.1x |
| 1895 | 1.9 | 4.0 | 2.1x |
| EAT STAY PLAY | 2.5 | 3.9 | 1.55x |
| THE | 3.1 | ~3.3-3.9 | ~1.1-1.25x |
| HOTEL FREMONT | 6.8 | ~same | 1x |

The pro's rule, read off his file: big text as drawn; small text raised to a
~4 mm floor, re-set as bold satin block letters, and moved (EST 1895 down ~2 mm)
into free space. Ours traces the art's size as a 3-pass hairline. Three causes,
largest first: (1) the pro's 4 mm floor, (2) satin vs hairline, (3) Kent's hat
job at 81 mm vs the pro's 92.5 mm files.

The engine already has (1): `small_text_cap_mm` (OFF; config candidate 3.7) grows
a line to a cap height. Kent ruled earlier "you can't change the font size for
the final product". **REVERSED by Kent 2026-10-21** on this evidence: "Yes, match
the pro" -- grow small text like the pro (fix THE, let the tagline grow, satin
the grown letters), built OFF, then a 92.5 mm card beside his patch.
At cap 4.0 on today's engine (probe, 2026-10-21): EST/1895 grow 1.575x (room-
limited), THE 1.3x but its T is swallowed into the black band beside it,
the tagline is skipped `no_room` (boxed in by rope and border).
(2) is `bean_letter_satin_mm` (OFF, added in PR #1024).

**Measuring trap, hit TWICE this session:** a word's height read inside a FIXED
box around the art's word (`fremont_triage.ROIS` mapped onto the pro's extent)
is capped by the box — it first said the pro was 30% taller (box caught
neighbours), then "the pro is the art's size" (box clipped his bigger letters).
Read the pro's letters by colour block / connected pieces, and render the whole
design (`tools/pro_pair.py`) before any size claim.

The pro's patch also differs in design, not just digitizing: a fully filled dark
field, the rope replaced by stacked satin border bands, a satin edge; ours sews
the art literally (white fill, rope chevrons). 18,611 st / 55 trims vs his
15,458 / 21.

Also in the v4 photos: thread loops at the start of B's arm 2 and the end of arm 3
(tagline); the first arm sewn red/green (operator thread; the DST has one colour).
Related: [[pro-files-refute-scale-limit-2026-09-03]], [[lettering-thickness-fremont-2026-10-06]].
