# SVG vector import + shape elements (Slice 9) — design

Date: 2026-07-27
Status: approved in brainstorming, pending plan

## 1. Goal

Add a vector path parser that turns SVG artwork into stitch regions, and use it
to ship two things at once:

1. **Customer vector logos** — exact edges, no rasterize-then-re-flatten round trip.
2. **Shape elements** — star, sun, flower and similar, chosen from a visual grid.

These were originally scoped as two separate slices in the opposite order. That
was wrong, and §2 explains why.

## 2. Why shapes depend on this slice

Kent asked for "simple shapes and figures like a star, sun or flower." The
upstream Ink/Stitch collection ships ~14 pictogram packs that look like the
obvious source. They were assumed to be satin fonts — structurally identical to
the 21 already imported — which would have made shapes a data-only job.

**Verified on 2026-07-27; that assumption was false.**

| Pack | `font.json` | `satin_column` count | Nature |
|---|---|---|---|
| animals, animaux, nautical | yes | **0** | fill artwork |
| flowery_crosses, magic_crosses | yes | **0** | cross-stitch fills |
| egyptian, decadent_flowers_monogram | no | **0** | fill artwork |
| cats, cogs_KOR, pisankris, dinomouse72, colorful | **no** | 241–889 | satin, no metrics |
| infinipicto | yes | 10 | mostly fill |
| mai_en_fleur | yes | not measured | `ltr/` directory, not `ltr.svg` |

Method sanity-checked against two known-good imports: `geneva_simple` reports
318 satin columns and `aventurina` 548, so a zero is a real zero.

The fill-based packs are `<path>` elements carrying `fill:` colours, grouped into
`GlyphLayer` groups, with `inkstitch:fill_method`, `cross_stitch_method`,
`fill_coverage` and `pattern_size_mm` attributes. Consuming them means parsing
SVG paths, grouping by fill colour, and producing regions for
`buildQualityDesign` — which *is* this slice's parser.

Decisively: the flowers Kent asked for live only in `flowery_crosses`,
`decadent_flowers_monogram` and `mai_en_fleur`, all fill-based. **There is no
satin route to them.** Shapes therefore cannot ship before this parser exists.

## 3. Architecture

### 3.1 The seam

`buildQualityDesign(colorRegions, opts)` consumes
`[{rgb, shapes:[{outer, holes}]}]` and does not care how the polygons were
produced. Raster tracing (`imageRegions.js` / `app.js`) is one producer; this
adds a second. **The stitch engine is not modified.**

New `src/svgimport.js` exports:

- `parseSVG(svgText, opts)` → `{regions, pxPerMm, warnings}` — same contract
  `flatToRegions` already returns, so downstream code is unchanged.
- `parseGlyphLayers(svgText, opts)` → `{glyphs: {label → regions}, ...}` — the
  pictogram-pack path, which is `parseSVG` restricted to one `GlyphLayer` group
  at a time.

### 3.2 Path parsing

Hand-written, pure JS, **no DOM**. The browser's `getPointAtLength()` would flatten
béziers and arcs correctly for free, but jsdom stubs it, which would put this
module outside the Node test suite. Given the engine currently has 169 passing
tests, testability wins over the shortcut.

Coverage: `M/L/H/V/C/S/Q/T/A/Z` plus relative forms; arc→bézier via the SVG
spec's endpoint parameterisation (F.6.5); primitives `rect` (incl. `rx`/`ry`),
`circle`, `ellipse`, `line`, `polyline`, `polygon`; nested `<g transform>` matrix
composition for `translate/scale/rotate/matrix/skewX/skewY`; `viewBox` scaling.

### 3.3 Flattening tolerance in final mm

Bézier flattening tolerance derives from the **target output size**, not source
coordinates. A tolerance pinned to source units silently coarsens as a design
scales up — the same class of bug as the 2026-07-27 density regression, where
fixed pixel floors overrode correctly-scaled values past ~4-10x. That fix's
lesson applies directly here.

### 3.4 Colour and region grouping

Resolve `fill` from presentation attribute, inline `style`, and inherited group
fill; support hex, `rgb()`, and named colours. Identical colours across separate
elements merge into one region, reducing thread changes. `fill="none"` is skipped.

**No flatten step.** An SVG states its colours exactly; running median-cut over
it would discard the precision that motivates this slice.

### 3.5 Holes

Per-path fill-rule (`nonzero` default, `evenodd`) plus containment and winding
tests assign subpaths as holes of their enclosing outer ring, producing the
`{outer, holes}` shape the existing hole-aware machinery expects.

### 3.6 Shape packs

A pack is an Ink/Stitch SVG with one `GlyphLayer` group per shape. Import is
offline (`tools/build-shapes.mjs`), producing per-pack JSON of pre-parsed regions
plus a manifest entry per shape: pack, label, preview PNG, natural size.

Two structural variations must be handled:

- **No `font.json`** (5 packs): derive size from the SVG `viewBox` and glyph
  bounding boxes. No kerning or advance is needed — shapes are placed
  individually, not laid out as text.
- **`ltr/` directory instead of `ltr.svg`** (`mai_en_fleur`): glyphs split across
  files. The importer must handle both layouts.

Shape **labels** are authored during import. Glyph letters are never surfaced —
a star must never be "press k".

### 3.7 Shape element type

The project model (v2) knows `text` and `image`. Add a third:

```js
{ type: "shape", pack, shapeId, sizeMm, offsetXMm, offsetYMm, colorRgb, underlay }
```

Bumps the model to **v3** with a `migrateProject` step, following the v1→v2
precedent. Generation calls `buildQualityDesign` with the pack's stored regions —
the same path image elements already use.

## 4. UI

- **Logo upload**: `ImagePanel` accepts `.svg`. On vector input the flatten
  controls (colour slider, merge, reset) hide entirely, since the file already
  states its palette. Parsed colours show as swatches with the existing
  `ThreadPicker`. A "Vector — exact edges" marker makes the active path obvious.
- **Shapes**: a `+ Shape` action in `ContentStep` beside `+ Text` and `+ Image`,
  opening a grid of pre-rendered thumbnails grouped by pack, searchable by label.
  Clicking inserts a shape element, which then drags, resizes, recolours and
  hoop-clamps like any other.

## 5. Known quality limits

- **Cross-stitch and pattern fills do not reproduce.** Packs using
  `cross_stitch_method` or `pattern_size_mm` (`flowery_crosses`, `magic_crosses`,
  and others) will stitch as ordinary tatami fill. This is a visible downgrade
  from the `preview.png` upstream ships. Either implement those fill types or
  exclude those packs — do not ship them silently looking different from their
  own preview image.
- **Stroke→satin is out of scope.** An SVG stroke is a centreline plus a width,
  which is exactly `satinFromRails` input, and converting it would be a genuine
  quality win. It needs prototype-first treatment with real stitch-out renders,
  as the deferred font abilities got.

## 6. Error handling

Every case below produces a clear message rather than a silent empty design:

- Unparseable SVG.
- Zero fillable paths (stroke-only art) — states that strokes are not yet handled.
- `<text>` elements present — "convert text to outlines first." Customers send
  this constantly and the text would otherwise vanish without explanation.
- Unsupported units or a missing `viewBox` — falls back to a stated assumption.

## 7. Testing

- Per-command path parser tests; arc conversion checked against known control
  points; transform composition; fill-rule and hole assignment; colour resolution
  across attribute, inline style, and inheritance.
- Golden-region snapshots from real SVGs, including at least one shape pack.
- Flattening tolerance verified to hold at multiple output scales — the
  regression the density fix taught us to test for explicitly.
- Model v2→v3 migration, matching the v1→v2 test treatment.
- Shape element generation produces the same design as feeding the same regions
  through the image path.
- Existing engine suite stays green; no stitch-math changes are in scope, so any
  diff in existing output is a regression.

## 8. Out of scope

- Stroke→satin conversion.
- Cross-stitch and pattern fill types.
- The ~140-font library expansion — separate spec, same date, now sequenced
  after this slice.
- Retiring `EMB-Bot.html` (needs a feature audit first).

## 9. Risks

1. **Pack quality is unverified beyond structure.** We know these packs are
   fill-based; we have not confirmed they *stitch well* through
   `buildQualityDesign`. Mitigation: parse and render two packs early, before
   building the grid around them.
2. **Arc parsing is the classic source of subtle vector bugs.** Mitigation: test
   against known control points rather than eyeballing renders.
3. **Shape count may shrink.** If cross-stitch packs are excluded (§5), the
   available shape set is materially smaller than 14 packs implies.
4. **Two pack layouts** (`ltr.svg` vs `ltr/`) suggest more upstream variation
   than sampled. Mitigation: the importer should fail loudly on an unrecognised
   layout, not skip silently.
