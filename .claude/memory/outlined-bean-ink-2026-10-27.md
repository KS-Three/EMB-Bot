---
name: outlined-bean-ink-2026-10-27
description: W5-05. MFab LC's AND (black letters, black body, white keyline) had its WHITE keyline read as the bean ink (0.4-1.7% of the spine inside the letter) and sewed as white letters. `bean_ink_outlined_letters` (built OFF) drops a read under half inside; the A sews black satin (crosses 44 -> 116, pro 114). Hat, WELDING, LLC unmoved
metadata:
  type: project
---

W5-05, for the foreman's wave 5: `text_cluster_part_touching` could not flip
while it turned the LC's AND N bean as well. Full record:
`docs/outlined-bean-ink-2026-10-27.md`.

**Mechanism.** `ink_path.read_cluster_ink` takes its ground from pixels
0.8 mm or more from the members and its ink from the colour nearest them that
differs most. On MFab the ground is the black body, the letters' own colour,
so the "ink" is the white keyline: a line round each letter, a median
0.14-0.15 mm OUTSIDE it. The reads are 0.42-0.44 mm, pass
`INK_SHAPE_MAX_RATIO` (2.54-2.94 < 3.0), and go bean.

**What it sewed.** Main's defaults: the A as a white letter with a thin black
line round it. With part_touching: the N too. The thin line IS the bean
letter: its runs follow the read, on the keyline, and the letter's area
shows the riders' white panel. The pro sews both black satin on a white
keyline.

**Board (LC 6-10 mm line, ours/pro):** columns 25 -> 31 (pro 30), trims
inside letters 5 -> 4 (pro 0), cc unmoved (-0.07; pro +0.20).

**The rule.** A real read lies inside its letter:

- bridge's eight bean letters: 98.4-100% inside;
- the same MFab words on the hat (read, but failing the ratio gate):
  67.7-100% inside;
- AND's outline reads: 0.4-1.7% inside.

`INK_INSIDE_MIN_SHARE = 0.5` is geometry, not cloth (no gate 1).

**Not this mechanism.** On today's main WELDING and LLC read 0.083 mm or
nothing, fail the ratio gate and never reach the decision. They are
byte-identical OFF and ON. So is the hat (its reads are 0.167 mm).

**Instrument traps.**

- A Generation pickled on an older main replays validly only with the cfg
  REBUILT from the Studio request on today's engine. One fresh digitize with
  the flag ON matched the replay byte for byte.
- A plan run with `jump=True` still sews: the flag is the lift INTO it. The
  premise capture tallied only non-jump runs and reported the A's bean runs
  (19 + 191 points) as vanished. Count every run's points.

Flip is Kent's (layout: judged in the preview). See also
[[text-cluster-part-touching-2026-10-25]], [[mfab-underfill-panels-2026-10-25]].
