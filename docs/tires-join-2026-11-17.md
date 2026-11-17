# Tires: the r/e join lump and notch (2026-11-17): mostly a limit, not a defect we can cure

Prime grader scorecard pin (74.0, 31.5) mm, `tires_hat_3d`: "the sections overlap in a lump with a square
notch on its left edge, where the art crosses cleanly."

**What the pictures say** (`docs/renders/tires-join-2026-11-17/`).
- `polygon-on-ink.png`: the traced polygon (red) against the working raster's ink at the join, window
  design mm x 66-80, y 26-37. The polygon sits on the ink to within one pixel. The square notch is the
  ink's own: the e's left edge runs near-vertical (x about 71.7-72.4) from y 29 to 32.2 and meets the r's
  top edge in a corner of about 110 degrees. Nothing stage 4 or the emitter adds.
- `strokes-at-join.png`: the pen strokes the script lane builds there (orange: the r exit through the
  baseline, green: the e's left side). The green stroke's last crosses run horizontally at y 29.2-29.7 and
  its first two run diagonally; measured against the orange ribbon only 39-50 % of those two diagonals lie
  inside it and the end crosses 0 %, so the existing end cut-back (`script_columns`) has nothing to cut and
  `script_strokes_drawn_width` made it worse (crosses criss-cross at the join).
- The professional's file at the same window (rendered locally from the gitignored third-party PES, not
  committed) has the same vertical left edge and the same corner. Where ours differs is small: ragged
  rounded cross ends along that left edge at y 28-30.

**Verdict.** The notch is a limit of the art at this size, shared with the pro; the residual difference
(ragged cross ends, 2 mm long) is not worth a flag. The e's upper exit edge straight run at (80.5, 34.0)
is different: that one is the polygon (a near-straight edge ending in a corner at the counter tip) and
the pro's is a smooth curve; it is the unfinished half of (b), not of this note.

The e/s step at (93.5, 35.5) was not examined.
