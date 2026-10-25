# Italic bars: `lettering_columns_italic_lean` OFF / ON / pro (2026-10-25)

ProSeal's italic PROSEAL at the pro's widths: `proseal_86_off_on_pro.png`
(hat, 85.9 mm) and `proseal_75_off_on_pro.png` (beanie, 75.0 mm). One row per
letter (P, R, S, A, E, L), each `OFF | ON | pro`, 40 px/mm, drawn with
`tools/pro_pair.py`'s renderer (`stitchviz.render_design` over
`pairframe.design_for`). Each file is in its own frame. The crop window is the
pro's letter box, laid on our file by the median offset of the two files'
letter centres, matched left to right. (Our beanie carries the knockdown and
border, so its stitch extents do not start where the pro's do.)

What to look at: the E's arms, the A's bar and the L's foot cross ALONG THE
SLANT under ON, as his do; OFF crosses them square, or leaning the other way.
The P's and R's bowls, the O and the S are bowl and ring columns. The flag
does not move them, and his bowl bars cross along the slant too. That is the
open half. Stems and the A's legs are the text lean's, unchanged.

Numbers: `tools/italic_cross.py` (bars along the slant within 8 deg: hat
0.31 -> 0.46, beanie 0.29 -> 0.36, pro 0.54 / 0.52), in the PR body.
