---
name: satin-small-shapes-2026-10-20
description: Defect 57's remainder (star centre, round-end cap, squares and dots) built OFF as `satinSmallShapes` in the browser satin, PR #994 merged 2026-10-20; no new mm constant; OFF byte-identical on six md5 pins; the flip and the sharp-tip question are Kent's
metadata:
  type: project
---

# Browser satin small shapes (2026-10-20)

Lane `claude/elegant-bohr-mhznfy`, [KS-Three/EMB-Bot#994](https://github.com/KS-Three/EMB-Bot/pull/994),
merged by auto-merge nine minutes after it opened. Sheet, SVGs, numbers and
the per-shape account: `docs/renders/browser-satin-small-shapes/README.md`.
Tool: `node tools/satin-small-shapes.mjs` (`--sheet`, `--svg`, `--json`,
`--pins`). Test: `test/satin-small-shapes.test.js`.

- **What main did (measured, not read).** The branch guard passes a 10 mm
  five-point star as satin (equal halves, every rung midpoint inside), so the
  defect text's "even-pointed stars only" is too narrow. Each arm's stations
  run in to the centre and cast crosses arm to arm: longest 8.0 mm, centre
  sewn five times. A round end's last cross carries the width of the station
  before it: 0.27 mm outside the curve. A square thins to TWO pixels whose
  direction is thinning's accident (1.5 mm level and fine; 6 mm diagonal, a
  7.8 mm stitch). A dot over 1.5 mm has no skeleton and takes the
  outline-split column, 12% in from each end (6 mm dot sewn 5.0 tall).
- **The cure, one option, OFF:** `buildQualityDesign({ satinSmallShapes })`
  → `medialSatin(opts.smallShapes)` → `smallShapesSatin` in `src/satin.js`.
  The cap: a cross end outside the drawn shape is pulled onto the outline
  (`capToContours`). The smallest column: a shape with no stroke to
  `ringToSpines`' own floor sews as a 2-point spine along the ring's
  principal axis (`ringAxis`, polygon second moments; equal moments → level).
  The zone: non-free ends within a half-width are a junction; 3+ arms are
  cut at the disc reaching the nearest wall (`cutSpineAtDisc`; on a regular
  star exactly the pentagon's inradius) and the centre sews once, last, as
  the smallest column over the arms' base crosses; arms alternate direction,
  order chosen for least needle-up. Lettering never reaches `medialSatin`.
- **Price ON (left chest):** star longest 8.02 → 4.60 mm, 131 → 104 st,
  cover 99.7 → 96.9%, plan extent 10.0 → 9.6 (tips capped); round end
  outside 0.35 → 0.20 (0.15 is pull comp), sewn 10.0 → 9.4, cover up; 1 mm
  dot cover 67.5 → 100%; 6 mm square 7.78 → 6.40 longest; 6 mm dot 5.0 →
  6.2 tall; T set to satin 10.40 → 2.53. ON reaches EVERY junction of every
  satin letter in the image lane (not drawn).
- **Pins:** OFF md5s of four shapes + two words, taken on main before the
  option and equal on main after #990. PR #1000 then flipped `ties`,
  `fillStagger`, `dedupeHoles` ON, so the test now builds with those OFF
  (`TRIO_OFF`); the pins still hold. Rebuild them with `--pins` only after
  a deliberate stream change, never to make a red test green.
- **Kent's, not decided:** flip whole; flip with a sharp-tip exemption (an
  angle or a tier, gate 1, not built); or leave OFF. The star's tier (ask
  whether the whole rung stays inside) is still a separate open item.
- **Trap:** `startNear` (underlayDirection) may reverse the whole stroke
  list, turning base-to-base jumps into tip-to-base; measure needle-up at
  the design level, not from `medialSatin`'s output.
