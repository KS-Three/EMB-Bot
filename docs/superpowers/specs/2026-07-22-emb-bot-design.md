# EMB Bot — Design Spec

**Date:** 2026-07-22
**Owner:** Kent (kent@sdwheel.com)
**Deliverable:** `<user-home>\EMB-Bot\EMB-Bot.html` — a single self-contained HTML tool.

## 1. Purpose

A browser-based auto-digitizing + lettering tool that converts an uploaded
logo/photo **or** typed text into real machine embroidery files, sized to a
chosen garment placement, with a PDF stitch-out worksheet.

**Delivery:** Single self-contained `.html` file opened locally (no server, no
CSP sandbox). Requires an internet connection on first use to load the vector
library and fonts from CDN; degrades gracefully with a clear message if offline.

## 2. Honest scope and known limits

These are design constraints, not TODOs:

- **Lettering → embroidery:** high quality achievable. Priority-secondary per
  user, but built on the same robust engine.
- **Logo → embroidery (PRIORITY):** "decent auto-digitized" quality — color
  reduction + region fills + optional outlines. Good for flat, limited-color
  logos. Not professional-software grade.
- **Photo → embroidery:** accepted but fundamentally limited; treated as an
  image (quantized). UI shows a non-blocking "logos work best" note.
- **PES export:** best-effort (PEC block is complex). UI labels it "verify on
  your machine." DST and EXP are the reliable formats.

## 3. Architecture

Single HTML file, three logical layers:

1. **Input layer (UI):** mode toggle (Image / Text), file upload or text+font,
   garment dropdown, output-format dropdown, sliders (colors, density, outline).
2. **Stitch engine (shared core):** converts a set of colored regions or glyph
   outlines into an ordered stitch list, scaled to garment size.
3. **Export layer:** encoders (DST, EXP, PES), image exporters (PNG, SVG), and a
   PDF worksheet generator.

### 3.1 Stitch model

Internal representation is the single source of truth for all exporters:

```
Stitch = { x, y, type }        // x,y in 0.1 mm units (DST native)
type ∈ { "stitch", "jump", "color", "trim", "end" }
Design = {
  stitches: Stitch[],
  colors:   ThreadColor[],     // one per color block, RGB + name
  widthMM, heightMM,           // final physical size
  stitchCount, colorCount
}
```

Coordinate convention: origin at design center; +X right, +Y up (exporters flip
Y as each format requires). 1 DST unit = 0.1 mm.

### 3.2 Fill generator (shared by image + text)

- **Tatami/scan-line fill:** for a given polygon region and fill angle, generate
  parallel stitch rows spaced by `rowSpacingMM` (from density slider), scanning
  boundary intersections per row, alternating row direction (boustrophedon).
- **Stitch splitting:** long runs split to `maxStitchLenMM` (default 4.0 mm).
- **Outline (toggle):** region boundary → running stitch following the simplified
  contour, `stitchLenMM` ≈ 1.8 mm.
- **Despeckle:** regions below `minAreaMM2` are dropped.

### 3.3 Region extraction (image mode)

1. Draw upload to canvas at working resolution.
2. Optional background knockout: near-white OR sampled top-left corner color →
   transparent (tolerance controlled internally).
3. **Median-cut quantization** to N colors (N = colors slider, 2–12).
4. Per color: build binary mask → **marching squares** → contour polygons →
   polygon simplification (Douglas–Peucker) → despeckle.
5. Fill each color's polygons; order colors to minimize thread changes.
6. Insert color-change + trim between color blocks; compute jumps between
   disjoint regions.

### 3.4 Glyph extraction (text mode)

1. Load selected font TTF via **opentype.js**; get per-glyph path.
2. Lay out the typed string on a baseline (kerning via font metrics).
3. Convert each glyph contour to polygons → same fill + outline engine.
4. **Lettering approach: fill + outline** (robust at all sizes). No satin in v1.

### 3.5 Scaling to garment

Design bounding box is uniformly scaled (aspect preserved) to **fit inside** the
selected garment box, then centered. Physical size recorded in `widthMM/heightMM`.

Garment table (width × height, inches):

| Garment            | W    | H    |
|--------------------|------|------|
| Hat / cap front    | 5.0  | 2.25 |
| Left chest         | 4.0  | 4.0  |
| Full back          | 12.0 | 12.0 |
| Beanie             | 4.5  | 2.5  |
| Sleeve             | 3.0  | 3.0  |
| Tote / bag         | 8.0  | 8.0  |
| Jacket back        | 12.0 | 10.0 |
| Patch / emblem     | 3.5  | 3.5  |
| Towel              | 6.0  | 6.0  |
| Blanket            | 10.0 | 8.0  |

If the fitted design exceeds a typical hoop envelope, show a non-blocking warning.

## 4. Exporters

- **DST (Tajima):** 512-byte ASCII header (LA, ST, CO, +X/-X/+Y/-Y, AX, AY, MX,
  MY, PD) + 3-byte stitch records using the DST bit encoding; jump/color/stop
  flag bytes; end record `0x00 0x00 0xF3`. Primary, most reliable.
- **EXP (Melco):** 2-byte signed dx/dy per stitch; `0x80 0x01` color change,
  jump/trim control codes. Simple and reliable.
- **PES (Brother):** PES v1 wrapper + PEC block incl. required thumbnail bitmap.
  **Best-effort**; UI flags verification.
- **PNG:** canvas render of the stitch simulation → `toBlob`.
- **SVG:** stitch polylines as `<path>` elements, colored per thread.

Format dropdown **defaults to `.DST`**. Multiple formats can be downloaded.

## 5. PDF stitch-out worksheet

Generated with **jsPDF**. Contents:

- Rendered stitch **simulation image** (each stitch drawn as a shaded thin line).
- Design metadata: final dimensions (in + mm), total stitch count, color count.
- **Thread color list** (swatch + RGB per color block, in sew order).
- Selected garment + placement box size.

## 6. Live preview

Center canvas renders the actual generated stitches (thin shaded lines) so the
preview reflects real output, updating on Generate.

## 7. UI layout

- **Left panel:** mode toggle; (image) upload + bg-knockout checkbox / (text)
  text field + font picker; garment dropdown; format dropdown; sliders — colors,
  density, outline on/off.
- **Center:** live stitch preview canvas with the garment placement box drawn.
- **Bottom bar:** stats (stitch count, dimensions, colors) + buttons: **Generate**,
  **Download file(s)**, **Export PDF**.

## 8. Fonts

~100 curated Google Fonts loaded as real TTF outlines via **jsDelivr mirror of
the `google/fonts` repo** (CORS-friendly), parsed by opentype.js. A small subset
is bundled base64 for offline fallback. Font list is a JSON map of
family → CDN TTF URL, verified during implementation.

## 9. Libraries (CDN, loaded at runtime)

- **opentype.js** — font outline parsing.
- **jsPDF** — PDF worksheet.
- Everything else hand-written: median-cut quantizer, marching squares, polygon
  simplify, tatami fill, DST/EXP/PES encoders, PNG/SVG export.

Load failures show a clear "check your internet connection" message.

## 10. Defaults

| Setting          | Default        |
|------------------|----------------|
| Colors           | 4              |
| Density (row sp.)| 0.4 mm         |
| Max stitch length| 4.0 mm         |
| Outline stitch   | 1.8 mm         |
| Outline toggle   | on             |
| Output format    | .DST           |
| Garment          | Left chest     |

## 11. Out of scope (v1)

- Manual stitch editing / node editing.
- True satin-column auto-generation for lettering.
- Applique, sequins, specialty stitches.
- Cloud hosting / sharing (local file only).
