---
name: card-v4-sewout-letter-size-2026-10-20
description: Card v4 sew-out beside the pro's Fremont patch — "our letters are much smaller" is stroke WIDTH, not letter size: ours is a centreline hairline in the art's footprint, the pro covers the stroke with 0.8-0.9 mm satin; plus 81 vs 92.5 mm
metadata:
  type: project
---

2026-10-20: Kent sewed card v4 (`docs/sewout/card-v4-2026-10-20/`, PR #1024) on black
twill beside the pro's Fremont patch; paused mid-way (block B and the start of H
sewn). His verdict: "your lettering is much smaller than the pro's".

**What it is (rendered, `pro_vs_ours_92mm.png` in that folder: pro stitches and
ours over the art at 92.5 mm):** our EST / 1895 / THE sit in the SAME footprint as
the art's letters — same height, same width — but as a single thin bean line down
each stroke's centre. The pro covers the whole stroke with satin (0.8-0.9 mm
columns), reaching the art's outline. A hairline reads as a smaller word on cloth.
Second, smaller cause: the card was cut at Kent's 81 mm hat width; the pro patch
is 92.5 mm (x1.14).

**Retracted the same evening:** a first pass said the pro sews small words TALLER
than the art (THE 3.9 vs 3.0 mm). That was a bounding box over the pro's whole
black block in the word's box — satin overshoot, serif bars and neighbouring
stitches — not letter height. Rendered, the pro's letters match the art's size.
So this is NOT `small_text_cap_mm` (enlarging, Kent: "you can't change the font
size for the final product"); it is width: satin to the art's outline instead of
a centreline bean. The config comment at `SMALL_TEXT_TRUE_SIZE` records Kent
choosing centreline over bold for THE (0.5 mm bean threshold); this cloth is the
first evidence against that choice, and re-opening it is Kent's call.

Also in the photos: thread loops at the start of B's arm 2 and the end of arm 3
(tagline), and the first arm sewn red/green (operator thread; the DST has one
colour).

**Why:** a bounding box is not a letter: render before claiming a size. **How to
apply:** before reading any small-lettering arm against the pro, compare at the
same width (92.5 mm) and RENDER it; the lever is stroke coverage (bean vs satin to
the outline), not letter scale.
Related: [[pro-files-refute-scale-limit-2026-09-03]], [[lettering-thickness-fremont-2026-10-06]].
