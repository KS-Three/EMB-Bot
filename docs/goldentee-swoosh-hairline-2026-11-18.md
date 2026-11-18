# Golden Tee swoosh: the "hairline sewn as a heavy band" is the pro's treatment too

Prime-grader pin `L_goldentee_hat` (10.0, 8.0) mm, nitpick: *"The swoosh's outer
line is a hairline in the art but is sewn as a black band as heavy as the inner
one, with a jagged saw-toothed edge along the arc."* (`docs/prime-grader/scorecard-2026-11-17.md`)

**Verdict: reproduced on main, but it is not a fault against the professional's file. No code change.**
Nothing here is flipped or built; no flag is added.

## What we sew (current main, 2026-11-18)

Pictures: `docs/renders/goldentee-swoosh-2026-11-18/` (original beside ours; no pro render is committed).

- The art's outer line is about 0.17 mm. The black arc is ONE region (hairline + the
  0.8 mm inner band joined at the tips), sewn as satin; the white crescent between is a
  separate satin field. Region `Sd166de81`-class, thread black, `stitch_width_pull_mm` 0.4.
- Outer band sewn about 1.33 mm, inner band about 1.9 mm (crown of the arc, vertical cross-section, 12 px/mm overview).
- The "saw teeth" are the round-capped ends of satin crosses at about 0.45 mm pitch
  (close-up `closeup-pin-10-8-default-4x.png`): the render of any satin edge.

## What the professional sews (read by eye and by pixel from the overview, not committed)

- Outer line: a black satin band about **1.0 mm** (not a run, not a bean, not left out).
- Inner band: about **2.0 mm**.
- Edge: scalloped the same way. Pixel-to-pixel edge jitter at the crown: ours 0.49 px, the pro's 0.34 px at 12 px/mm,
  a difference of about 0.01 mm. Not visible as a different kind of edge.

So the pro also sews the hairline as a real black band. Ours is 0.3 mm wider on the outer line and equal on the inner.
The 0.3 mm is the satin cross floor plus pull on a 0.17 mm line: a physical constant
(ROADMAP gate 1, satin width floor / pull compensation). Not changed.

## Existing flags tried (both OFF), pictures in the folder

- `satin_hairline_tier`: **no change at all** on this design (byte-identical picture).
  The ring is not a stroke the tier reads (its median cross is over the gate).
- `hairline` (global tier): the swoosh becomes two thin runs and the saw teeth go, **but every black
  edge in the design thins to a run** (G, T, GOLF, tee). The pro keeps those at 1-2 mm. Wrong direction; not proposed.
- `border_from_outline_hairline_run` (ON) does not apply: the swoosh is a region, not an art outline.

## Not built, on purpose

A "hairline arm of a ring as a bean" cure would sew the outer line thinner than the pro's 1.0 mm band,
trading a 0.3 mm excess for a line the pro does not sew. The remaining 0.3 mm is a satin-floor question for a sew-out.
