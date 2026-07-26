# Font editing abilities (Round 1) — design spec

**Date:** 2026-07-27
**Status:** approved, ready for implementation plan
**Author:** Kent + Claude

## 1. Background

Kent asked for "more font editing abilities" for text elements in EMB Bot
Studio, with rotating text upside-down as the headline ask. Brainstormed via
one-question-at-a-time dialogue (see conversation) into four abilities safe
enough to build now, plus two riskier abilities explicitly deferred to a
prototype-first Round 2.

The text-element pipeline (`src/satinfont.js` `layoutText` → `src/digitize.js`
`buildLetteringDesign` → `app/src/ui/TextStep.svelte`) uses **hand-authored
pre-digitized satin fonts** (parsed Ink/Stitch rails+rungs), not auto-traced
lettering — that's the whole reason this font system exists (auto-tracing
fragmented curves/junctions and looked worse than commercial tools; see the
2026-07-24 "pre-digitized satin FONTS" work). Any new ability that reshapes
column geometry (not just repositions the finished stitches) carries real
risk of degrading that quality, so each ability below is explicitly rated for
that risk and engineered accordingly.

## 2. Scope: four abilities, this round

### 2.1 Rotation (incl. one-click upside-down)
**Risk: none.** Pure post-transform on already-generated stitches; never
touches column geometry.

- New text-element field `rotationDeg` (0–360, default 0).
- UI: a slider next to the existing Curve control in `TextStep.svelte`, plus a
  "Flip upside-down" button that toggles between 0 and 180.
- Engine: in `buildLetteringDesign`, after the existing center + `offsetXMm`/
  `offsetYMm` transform, apply a rigid rotation of the finished DST-space
  stitch coordinates about the element's own bbox center (the same point the
  center-transform already uses). Composes for free with `arcDeg` and resize,
  since it's the last step applied to already-correct stitches.
- Scope: text elements only (not image/logo elements) per Kent's call.

### 2.2 Per-letter color (range groups)
**Risk: low** (workflow cost — more color changes/trims — not a quality risk).

- New text-element field `colorRanges`: array of `{ startIdx, endIdx, colorRgb }`
  over the string's character indices, `startIdx` inclusive / `endIdx`
  exclusive (standard slice convention — matches `str.slice(startIdx, endIdx)`).
  Characters not covered by any range use the element's existing `colorRgb`
  (so old single-color projects need no migration — an empty/absent
  `colorRanges` is fully backward compatible).
- Engine: `buildLetteringDesign` inserts a color-change + trim at each range
  boundary, reusing the same trim/color-block approach `combine.js`'s
  `combineDesigns` already applies between separate elements — just applied
  *within* one element's glyph run sequence instead of across elements.
- UI: in `TextStep.svelte`, select a character range in the text preview
  (click-drag or shift-click) and assign it a color via the existing
  `ThreadPicker`. Show a small non-blocking note if the number of ranges gets
  high (more thread changes = longer sew time) — informational, not a hard cap.

### 2.3 Bold (Thin / Normal / Bold presets)
**Risk: moderate.** Reshapes column width — needs real tuning + collision
guards, not just a plugged-in offset.

- New text-element field `weightPreset`: `"thin" | "normal" | "bold"`,
  default `"normal"`.
- Engine: each non-default preset maps to a tuned rail-offset amount, pushing
  `railA`/`railB` apart (thin: together) before routing — same offset math
  shape as the existing `pullCompMm` handling already in the pipeline.
- Guard: after offsetting, verify the offset hasn't collapsed a counter
  (interior hole, e.g. the bowl of "e"/"a"/"g") or caused adjacent strokes in
  a narrow letter to merge. Tune the two preset values against the full font
  library's tightest letterforms, not just the roomiest ones, before shipping.
- Deliberately NOT a continuous slider — presets keep users inside a range
  that's been verified to actually stitch cleanly.

### 2.4 Slant / italic (bounded slider)
**Risk: moderate.** Shear transform per glyph — gentler on column geometry
than bold, but still touches per-glyph geometry, so it's bounded.

- New text-element field `slantDeg` (-20 to +20, default 0).
- UI: a slider in `TextStep.svelte`, same visual pattern as Curve/letter-spacing.
- Engine: this mechanism already exists for the OLDER auto-satin image path
  (`satin.js`'s `slantDeg` support). This round extends it to the
  pre-digitized-font text path (`satinfont.js`/`satinplay.js`), where it
  doesn't currently reach — apply the shear to each glyph's rails+rungs before
  `routeGlyph`, bounded to ±20° so rungs stay meeting their rails cleanly at
  junctions instead of fanning out at extreme angles.

## 3. Explicitly out of scope this round

**Condensed/expanded width** (non-uniform horizontal squeeze/stretch) and
**mixed per-letter size** (e.g. a bigger monogram initial) are deferred to a
separate Round 2. Both risk distorting a satin column's effective width
unevenly along a curve, and could interact badly with the density-correction
math fixed in the 2026-07-27 resize-density bug fix. Round 2 will prototype
against the real font library and produce actual stitch-out renders for
review before any commitment to ship.

## 4. Testing plan

- Engine-level tests per ability in `test/` (Node test runner):
  - Rotation: pure geometry check (rotated stitch set is the exact rigid
    rotation of the unrotated set), similar in spirit to the existing arc
    rotation tests in `test/satinfont.test.js`.
  - Per-letter color: color/trim records land exactly at range boundaries;
    an empty `colorRanges` is byte-identical to today's single-color output
    (back-compat snapshot).
  - Bold/slant: rendered-and-measured checks against the actual generated
    stitch geometry (not just "a parameter changed") — same rigor as the
    resize-density fix's before/after stitch-count and matched-scale render
    verification, applied to the tightest letterforms in the library.
- Full suite (`node --test` + `cd app && npx vitest run`) green before calling
  any ability done.
- Live browser verification of each new control in the Studio UI (drag the
  rotation slider, click upside-down, pick a per-range color, switch bold
  presets, drag slant) before reporting complete.

## 5. Files touched (expected)

- `src/satinfont.js` — slant shear plumbing, per-glyph geometry hooks.
- `src/digitize.js` — `buildLetteringDesign`: rotation post-transform,
  color-range trim insertion, bold rail-offset + guard, slant wiring.
- `src/satinplay.js` / `src/satin.js` — shared rail-offset helper reused for
  bold (already has similar logic for pull comp).
- `app/src/ui/TextStep.svelte` — rotation slider + upside-down button,
  slant slider, weight preset buttons, per-letter-range color UI.
- `app/src/lib/generate.js` — thread the four new element fields through to
  `buildLetteringDesign`'s opts.
- `test/satinfont.test.js`, `test/digitize.test.js`, and new/updated
  `app/src/**/*.spec.js` files as needed.
