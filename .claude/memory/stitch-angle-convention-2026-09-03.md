---
name: stitch-angle-convention-2026-09-03
description: the trade's stitch-angle rule, measured and ADOPTED by Kent (cap 30°), pass 1 BUILT same day — fading lean past the cap (no side flip), spacing/cos(lean) (thread pitch 0.152 → 0.20 on every leaned column), stems = the four-fold family square to the LINE OF TEXT ("longer family" was wrong on THERMAL and ENTHUSIAST); bisector deleted; four-fold flag FLIPPED ON by Kent on the numbers; rail-dent defect found in `place`; Goldman corner join is pass 2
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

## The rule, as adopted and built (pass 1, same day)

Kent adopted the rule and the 30° cap, chose pass 1 first. Built:

- **Fade, not snap.** Past the cap the lean fades linearly to zero at the
  house axis (`lean = cap·(90−|d|)/(90−cap)`), so a bar along the axis is
  perpendicular with no side and a 45° diagonal leans 22.5°. Items 2 and 3
  contradicted each other at the boundary; this is the reconciliation.
- **Density compensation** (`_cross_angles` + `_resample_by_pitch`): thread
  pitch on leaned columns **0.152 → 0.198–0.201 mm** (Fremont, ENTHUSIAST);
  Fremont crosses 885 → 812, ENTHUSIAST chaining benchmark with the flag on
  4.62 → **4.09/1k** (ceiling 4.1). Gate 1 untouched: no constant moved.
- **CORRECTION to item 1 — "the longer family" is wrong.** Trimmed-chain
  lengths: Fremont stems 84 : 72, but THERMAL 20 : 23 and ENTHUSIAST 61 : 71
  the other way. Stems are the family square to the **line of text**
  (`_line_of_text_deg`, principal axis of member centroids); right on all
  four groups, agrees with the doubled reading on Becker. Bisector deleted.
- **Flag ON (Kent, same session):** Fremont and THERMAL move, eleven other
  fixtures md5-identical, no golden moves, time unchanged.
- **Not this pass:** the Goldman join (corners still sweep 90° over the
  smoothing width — Becker 40% of crosses past 45° vs a 24% stock floor),
  wide-column bars, the four-fold flip (Kent's).
- **Tried and withdrawn: a lean floor for hairline columns.** THE (2.6 mm,
  0.40–0.52 mm columns) loses its bars under the rule — the shipped default
  already does; the bisector kept them by accident. A per-station floor from
  the boundary distance fans 45→2→45° over a 2.5 mm stem and still lands
  crosses at 0.44–0.49. Small lettering wants its own tier, not a lean hack.
- **Found, recorded, not fixed: rail dents.** `place` shrinks a rail 15%
  when the full-width point misses `covers` by float dust; a STOCK 3 mm bar
  rotated 25° has one whole rail at 1.22–1.27 vs 1.44–1.46 mm. Every satin
  golden carries it; a fix is its own PR.

Instrument: `digitizer/tools/satin_lean.py` (lean and cross-vs-house
histograms, thread pitch; `--stock` for the floor).

See also [[hotel-fremont-fine-details-2026-09-02]], [[letterform-fidelity-2026-08-26]],
[[thresholds-on-the-wrong-population-2026-08-28]].
