---
name: stitch-angle-convention-2026-09-03
description: the trade's stitch-angle rule, measured — stems perpendicular (pro 4.7°, 86 fonts 1.8°), bars perpendicular in fonts / wide columns in the pro file, diagonals leaned 15–30° toward the house and rarely past 45°; the 45° bisector is what nobody does; Goldman's expired rule for ≥45° corners (through-member + butt-join) and Pulse's density-under-lean (spacing/cos θ) explain the ENTHUSIAST pile
metadata:
  type: reference
---

Full record with sources and tables: `docs/stitch-angle-convention-2026-09-03.md`.
Kent asked for *"a logical way to determine this for every logo and photo"*
instead of choosing 45 vs 135. The answer is that no convention constant is
needed: the angle comes from the art.

## What was measured (do not re-measure)

- **Pro file** (five `becker_*.dst`, satin zigzags only): cross deviation from
  the column-advance perpendicular — axial columns 4.7–7.9° median, diagonal
  columns **15.9°** (p75 26°, p90 43°). Limit: "column advance" is not the
  letter stroke; the render is what shows the E's arms sewn as wide columns.
- **86 shipped fonts** (their own rungs, `scratchpad/fontangles.py`): stems
  **1.8°**, bars **3.0°** off perpendicular — font authors never sew a bar as
  a wide column; diagonals **18°** (N A V K M W X Y Z: 29.5°), **58% leaning
  toward the stems' cross**. One angle for a whole glyph is a minority style:
  5 of 64 fonts.
- **Published trade**: perpendicular to the column; mitre corners with the two
  angle lines parallel at ~45°; fill defaults to 45° and should vary; nobody
  publishes a diagonal rule.
- **Expired patents** (masters teardown): **Goldman** — at ≥ 45° corners break
  the column, *one member runs through and is extended, the others butt into
  it and are shortened* (the diagonal runs through on an N). **Pulse** — hold
  the PERPENDICULAR interstitch distance constant under lean; at 45° the
  along-column inset is 58.6%.

## The two mechanisms behind the 09-02 findings

- **The bisector was a workaround**, not a convention: house = 0 scrambled
  horizontals only because `_clamp_to_span` picks the ±45 SIDE by tangent
  noise. Perpendicular has no side — the font convention — and removes the
  flip without inventing an angle.
- **The N piled because spine spacing is not perpendicular spacing.** Stations
  0.4 mm along the spine with crosses leaned θ land 0.4·cos θ apart across the
  thread: at 45°, 0.28 mm, **1.41× density** on every leaned stroke — the whole
  45° Hotel Fremont render included. Spacing/cos θ keeps the constant's meaning
  without touching it (gate 1 clean).

## The rule proposed to Kent

House = perpendicular to the dominant stem family (longer family in the
two-family case; never the bisector) → a stroke that cannot span it takes its
own perpendicular → diagonals lean toward the house, capped (30° inside both
bands; 45° is the pro's p90) → spacing/cos(lean) → ≥45° corners get the Goldman
through-member + butt-join, which is NOT the withdrawn `_SPLIT_TURN_DEG` 90→70
(that splits into two capped columns). Fill: lettering inherits; other shapes
→ fragment-count minimisation (G3), not 45° and not PCA. Photos: direction
field, already.

Decisions left to Kent: adopt; lean cap 30 vs 45; build order (density comp
first — small and fixes the pile alone; Goldman join is the corner work the
letterform memory has circled since 08-26).

See also [[hotel-fremont-fine-details-2026-09-02]], [[letterform-fidelity-2026-08-26]],
[[thresholds-on-the-wrong-population-2026-08-28]].
