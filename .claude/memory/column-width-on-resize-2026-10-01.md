---
name: column-width-on-resize-2026-10-01
description: "How a hand-drawn satin column's width behaves on resize (Kent's ruling 12) and where the manual-columns lane landed"
metadata:
  node_type: memory
  type: project
---

**Ruling 12 (Kent, 2026-10-01, on measured evidence):** a column's DRAWN width
scales with the design; the fabric's pull compensation stays a fixed amount on
top. So a column stores `widthPx` (authored canvas px, like its points), never
mm; mm is a view through the element's fit, and sewn = drawn + `pullCompMm`.

**The evidence** (`docs/satin-column-width-on-resize-2026-10-01.md`, one pro
digitizer's own files): a 1.25x design carries 1.195x columns, 1.33x -> 1.265x,
1.97x -> 1.78x, an effective k ~ 0.80-0.85 in width ~ size^k. The better reading
is NOT a power law: the outline scales 1:1 and a fixed ~0.3-0.55 mm (what a mm
pull-comp setting does) rides on top. "Width never changes" fits ~3x worse.
**No clamp anywhere between 0.67 and 11.8 mm** in eleven pairs; vendors answer
a too-wide column with auto-split, which is a physical constant nobody has sewn
here (gate 1) — so the Studio warns past 6.5 mm sewn (ruling 5) and clamps nothing.
One digitizer, documentation not cloth: it clears no gate.

**Where the lane landed (2026-10-11):** plan
`docs/superpowers/plans/2026-10-01-manual-columns.md`, all tasks done on
`claude/manual-columns`. Engine: a region's `sewAs: { kind: "column", railA,
railB }` sews `satinFromRails` with every interior rail pair as a rung (two
thinning rules were measured and lost). Studio: `shapeRing(shape)` is THE ring
any shape presents (engine, bbox, hit-test, placement guard); Column mode on the
side canvas; the popover and the assign box share `columnWidthNote`. The e2e
`app/e2e/manual-column.spec.js` (c) re-proves ruling 12 in the real app.

**Trap met merging main:** three byte-identity pins (two engine, one Studio)
were taken at the branch base; main's engine moved under them. Re-pin from
origin/main's OWN src (git archive, or `git checkout origin/main -- src/<file>`
and back), never from the code under test.
