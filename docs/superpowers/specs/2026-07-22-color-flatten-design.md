# Color Flatten Workflow — Design Spec

**Date:** 2026-07-22 · **Owner:** Kent · **Scope:** Option A (approved in chat)

## Purpose
Make the color-merge step visible and controllable — the judgment call a human
digitizer performs before stitching. Image mode gains a "Flattened art" preview
whose result feeds stitch generation exactly.

## Feature
1. **Flatten preview:** after upload (and on Colors-slider change), show the
   image quantized to N colors at working resolution with cleanup applied:
   - `modeFilter` (3×3 majority) smooths ragged quantization edges;
   - `absorbSmallRegions` reassigns any connected color patch smaller than a
     threshold to its majority neighboring color (keeps coverage solid — no
     dropped specks/holes).
   Transparent pixels (alpha<128) stay transparent (checkerboard in preview).
2. **Palette bar:** one swatch per palette color with % of opaque pixels.
   Click to multi-select; **Merge Selected** collapses them into one color
   (population-weighted average) and remaps; **Reset** returns to auto result.
   Colors slider re-runs auto-flatten (clears manual merges).
3. **Download flat PNG:** exports the flattened art at ORIGINAL resolution
   (nearest-palette mapping + one modeFilter pass at full res), transparent
   background preserved.
4. **Generate** consumes the current flattened indices (per-color masks →
   `traceRegions` → `buildQualityDesign`) so stitches match the preview.

## Module: `src/flatten.js` (dual-mode, TDD)
- `modeFilter(indices, w, h, {iterations=1})` → `Uint8Array` — 3×3 mode of
  non-transparent neighbors; 255 (transparent) never changes or wins.
- `absorbSmallRegions(indices, w, h, minPx)` → `Uint8Array` — 4-connected
  components with `size < minPx` take the majority neighbor index; terminates;
  never invents new indices; transparent untouched.
- `mergeColors(palette, indices, idxList)` → `{palette, indices}` — merges the
  listed palette entries into one population-weighted color, remaps indices.
- `indicesToRGBA(indices, palette, w, h)` → `Uint8ClampedArray` for canvas.
- `paletteShares(indices, paletteLen)` → `number[]` fraction per entry.

## App wiring (`src/app.js`, `EMB-Bot.html`)
Image-mode panel gains the preview canvas, swatch bar, Merge/Reset buttons and
Download-flat-PNG button. State: `{palette, indices, w, h}` kept module-level;
Generate uses it instead of re-quantizing.

## Out of scope
Per-pixel painting/eyedropper; assigning real thread brand codes; SVG import.
