# Sew-out card: bean passes (2026-10-14)

Kent asked what happens when thread is stitched on top of thread. A bean
letter already is: three passes of one run through the same holes. Our
renderer draws those three passes as ONE thread, so no picture can say how
wide they really sew. This card asks the cloth.

**What to sew:** `card_passes_40wt.dst`, one colour (dark), 40 wt, on a hat
front like the Fremont job.

**What is on it:** Fremont's own "THE" (row T) and "1895" (row N) at 81 mm,
cut from the logo's replay with `small_text_true_size` ON. The teeth above
each copy count its passes: 1 tooth = one pass, 2 = two, 3 = three (what the
switch sews today). Nothing else differs between the copies.

**What to look at, per copy:**

1. Line width: does each extra pass make the line visibly wider, or just
   higher / glossier?
2. The 5 in 1895: is the small opening at its top still open?
3. The 8's two holes and the 9's hole: open or filled?
4. The fabric: any shredded or enlarged holes, puckering, or thread breaks
   (three passes put three needle hits in holes 0.45 mm apart)?
5. Which one reads best from arm's length?

The pictures in `card_passes_40wt_blocks.png` are the renderer's view: all
three copies look nearly the same there. That is the point of sewing it.

## Pieces

| block | arm | passes | stitches | runs | size (mm) |
|---|---|---|---|---|---|
| T | p1 | 1 | 68 | 14 | 8.37 x 2.3 |
| T | p2 | 2 | 106 | 14 | 8.37 x 2.3 |
| T | p3 | 3 | 152 | 14 | 8.37 x 2.3 |
| N | p1 | 1 | 54 | 11 | 5.39 x 1.51 |
| N | p2 | 2 | 89 | 11 | 5.39 x 1.51 |
| N | p3 | 3 | 124 | 11 | 5.39 x 1.51 |

## The file checks (pystitch reading the DST back)

| | 40 wt |
|---|---|
| file | `card_passes_40wt.dst` (2,972 bytes) |
| blocks on the card | 2 |
| stitches in the file / in the plan | 718 / 718 |
| colour changes in the file / planned | 0 / 0 |
| colours (stops) | 1 |
| extent (mm), x by y | 35.2 x 26.8 |
| x range / y range (mm) | [-17.6, 17.6] / [-13.4, 13.4] |
| inside 100 x 100 mm | yes |
| longest needle stitch (mm) | 1.72 |
| longest record, per axis (mm; the format's limit is 12.1) | 11.2 |
| trims | 14 |
| 0.8 mm lock-leg stitches | 68 |

Stitches per piece:

| piece | stitches |
|---|---|
| N:p1 | 50 |
| N:p2 | 85 |
| N:p3 | 120 |
| N:strips | 73 |
| T:p1 | 72 |
| T:p2 | 106 |
| T:p3 | 156 |
| T:strips | 86 |

Stitches per colour stop:

| stop | thread | stitches (thread m) |
|---|---|---|
| 1 | dark | 748 (0.38) |

Where each piece sits (mm, x0 y0 x1 y1, centre of the card at 0, 0):

| piece | box |
|---|---|
| N:p1 | [-17.6, 11.9, -12.2, 13.4] |
| N:p2 | [-7.2, 11.9, -1.8, 13.4] |
| N:p3 | [3.2, 11.9, 8.6, 13.4] |
| T:p1 | [-17.6, -4.4, -9.2, -2.1] |
| T:p2 | [-4.2, -4.4, 4.2, -2.1] |
| T:p3 | [9.2, -4.4, 17.6, -2.1] |

