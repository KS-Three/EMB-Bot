# Font library expansion + shape elements (Slice 9) — design

Date: 2026-07-27
Status: approved in brainstorming, pending plan

## 1. Goal

Grow the pre-digitized satin font library from 21 to roughly 140–160 fonts, add
pictogram/shape packs as a first-class element type, and replace the font
dropdown with a browser that stays usable at that scale.

Kent's request was "more fonts, and simple shapes like a star, sun or flower."
Both are satisfiable from the same upstream source the current 21 came from,
using the existing `tools/build-font.mjs` pipeline. No new stitch-generation
math is required — this is a data, delivery, QC, and UI slice.

## 2. Source and eligible set

Upstream is `github.com/inkstitch/embroidery-fonts` (`src/` holds **186** font
directories). 21 are already imported, leaving **165**.

The split below is **estimated from directory names only** and has not been
verified against font contents. Names are suggestive but not authoritative — a
directory called `colorful` may or may not be multi-color, and `_small` in a
name does not prove small-size authoring. The exact split is produced by the
manifest build (§4.1) as its first output, and the plan must treat these numbers
as provisional until then.

| Category | Estimated count | In this round |
|---|---|---|
| Plain Latin text | ~105 | Yes |
| `_small` / `_tiny` size variants | ~20 | Yes |
| Pictogram / shape packs | ~14 | Yes |
| Monogram sets | ~4 | No |
| Non-Latin (Hebrew, Cyrillic, Greek, Braille) | ~8 | No |
| Multi-color / applique / tartan / tricolore | ~10 | No |
| Texture / fill-effect variants | ~4 | No |

Target: **~140 new, ~160 total** — with the caveat that QC rejections (§5) will
reduce this. At the 12.5% historical rejection rate, expect roughly **~122 to
survive**, for ~143 total. Any figure in this spec above 140 is optimistic.

The excluded categories need engine features that do not exist: applique
tackdown/cutline sequencing, per-glyph multi-color, RTL layout, and fill-effect
variants. Each is a candidate for a later slice, not a silent drop.

### Why the `_small` variants matter more than their count suggests

EMB Bot currently documents a hard limitation: text below ~4 mm cap height
"drops below what thread can hold — physics, not a bug. Size up or drop small
lines." Upstream ships ~20 fonts hand-authored specifically for that regime
(heavier rails, simplified counters). Importing them converts a limitation we
tell users to work around into a supported case.

## 3. Decisions taken (do not relitigate)

1. **Distribution: commercial product / paid tier.** Sets the licensing bar.
2. **License policy: OFL + CC-BY + CC-BY-SA.** Requires a credits screen and a
   public link to the derived font JSONs under their original license. A
   restricted "local-only" font tier was considered and **skipped** — its only
   plausible content was free-for-personal-use *outline* fonts, which can only
   be auto-traced, and auto-tracing was rejected on quality on 2026-07-24.
3. **`EMB-Bot-standalone.html` is retired.** 175 fonts inlined would be ~63 MB
   in a single local file, where gzip does not apply. Studio is the product.
   `tools/bundle.mjs` and the standing "rebuild the standalone after any `src/`
   change" rule retire with it.
4. **Slice order: this slice, then SVG import.** The pictogram packs already
   satisfy the star/sun/flower request, so SVG vector import (designed
   separately, same date) moves to the following slice.
5. **QC is automated**, with human review only of what the harness flags.
6. **Font browser + separate shape grid**, not a longer dropdown.

`EMB-Bot.html` (the non-inlined original tool) is **not** retired here. It may
still expose controls the Studio lacks — per-swatch stitch-angle override, the
explicit fabric dropdown. Audit before retiring it; that is separate work.

## 3a. Recommended split into two slices

This spec is larger than any slice this project has shipped. Slices 1–8 ran 4–6
tasks each and all merged clean; the work here is closer to 10 and spans three
distinct risk areas (bulk data import, a delivery-architecture change, and new
UI plus a model migration). The project's own convention — narrow slices ship
clean — argues against doing it in one pass.

**Slice 9a — library and delivery (no visible UI change)**
Manifest build, lazy font loading, removal of `satin-fonts.js`, the QC harness,
bulk import, licensing metadata. Ends with ~140 fonts present and loadable, the
existing dropdown still in place and still working. Verifiable on its own: font
output for the existing 21 must be byte-identical, and the app must behave
exactly as it does today.

**Slice 9b — browser and shapes (visible)**
Font browser, shape grid, `+ Shape` element, project model v3, credits screen.
Builds on a library that is already proven loadable.

The split is recommended, not mandatory. Its main benefit is that 9a's riskiest
change — removing the eager registry every existing call site depends on — gets
verified against unchanged UI, so any regression is unambiguously the delivery
change rather than the new picker.

## 4. Architecture

### 4.1 Font delivery

Today all fonts are inlined into a single `src/fonts/satin-fonts.js` (~7.7 MB
for 21) and loaded eagerly. That does not scale to ~150.

New model:

- Each font remains its own `src/fonts/<key>.json`.
- A small **manifest** (`src/fonts/manifest.json`) holds per-font metadata only
  — key, display name, category, license id, attribution, glyph coverage,
  `sizeMm`, recommended size band, preview image path. Kilobytes, loaded eagerly.
- Font JSON is fetched **on demand** when a font is first selected or previewed,
  then cached in memory. ~85 KB gzipped per font over HTTP.
- `satin-fonts.js` (the eager combined registry) is removed. `EMB.SATIN_FONTS`
  becomes a lazy accessor so existing engine call sites keep working.

### 4.2 Preview images

Generating real stitches for ~150 thumbnails on demand will not perform. Previews
are **pre-rendered at import time** into small PNGs (one per font, a fixed
sample string) and referenced from the manifest.

The browser's "preview my actual text" feature renders live, but only for fonts
currently visible in the viewport, debounced, and capped in flight. Static PNGs
carry the grid; live rendering is an enhancement layered on top.

### 4.3 Shape elements

The project model (v2) knows `text` and `image` elements. A shape is neither: it
is a glyph from a pictogram pack, chosen visually.

Add a third element type:

```js
{ type: "shape", pack: "mai_en_fleur", glyph: "k", sizeMm, offsetXMm, offsetYMm,
  colorRgb, underlay }
```

Bumps the model to **v3** with a `migrateProject` step, following the existing
v1→v2 precedent. Generation reuses `buildLetteringDesign` with a single-glyph
string — pictogram packs are structurally ordinary satin fonts, so no new
engine path is needed.

Shape packs are excluded from the font browser's list (they are not usable as
text fonts) and appear only in the shape grid.

## 5. QC harness

New `tools/qc-font.mjs`. Every check below encodes a failure this project has
already hit:

| Check | Origin |
|---|---|
| satin-column count > 0 | Some upstream fonts are single-stroke running only |
| Advance metrics present and non-degenerate | `medium_font` null advances collapsed glyphs |
| Rail/rung classification by intersection count | Aventurina "n" sprayed when a rung was taken as a rail |
| Glyph coverage A–Z / a–z / 0–9 (reported, not required) | Some fonts are caps-only |
| Per-glyph bbox finite, no NaN, no wild outliers | Broken metrics from dropped fonts |
| Stitch count per glyph within a plausible band | Catches degenerate or exploded geometry |
| License id present and in the allowed set | Required for the credits screen and policy compliance |

Output: pass / flag / reject per font, plus a montage PNG for anything flagged.
Prior manual QC rejected 3 of 24 (12.5%); at 154 fonts expect roughly 19 to need
eyes. Aesthetic rejections (Chopin was dropped for being too ornate) remain a
human call — the harness does not attempt taste.

## 6. Font browser UI

Replaces `FontSelect`'s dropdown.

- Full-panel browser with a search field (name and category), category filters
  (Sans / Serif / Script / Display / Small), and a results grid.
- Each tile shows the font rendered with **the user's current text**, falling
  back to the pre-rendered PNG until the live render resolves.
- Size guidance is surfaced inline. Each font's **recommended size band** is
  derived from the `sizeMm` its upstream `font.json` declares — the size the
  author digitised it for — as `[sizeMm × 0.75, sizeMm × 2.0]`. Below the band a
  font's counters and rail widths start closing up; above it, density thins.
  These multipliers are a starting point, not measured values, and should be
  validated against real stitch-outs before being treated as authoritative.
  Picking a font far outside its band shows a non-blocking note. This closes the
  trap where a small-optimised font is scaled to 100 mm, or a display font is
  shrunk below what thread holds.
- Current selection is always visible and restorable.

## 7. Shape grid UI

- New `+ Shape` action in ContentStep alongside `+ Text` and `+ Image`.
- Opens a grid of pre-rendered shape thumbnails, grouped by pack, searchable by
  pack name and shape label where upstream provides one.
- Clicking inserts a shape element; it then behaves like any other element —
  drag, resize, thread colour, hoop clamp.
- Shape labels come from the manifest, authored during import. Glyph letters are
  never surfaced to the user.

## 8. Licensing deliverables

These are scope in this slice, not follow-up paperwork:

- Per-font `license` and `attribution` fields in the manifest, populated by the
  importer from the upstream `LICENSE` file — never hand-maintained.
- A credits screen in the Studio, generated from the manifest.
- A published route serving the derived font JSONs under their original license,
  satisfying CC-BY-SA ShareAlike on the transformed data.
- QC rejects any font whose license id is outside the allowed set.

**Not legal advice.** The ShareAlike containment position — font data carries
its own license, application code does not inherit it — is standard practice but
should be confirmed by a lawyer before a paid launch.

## 9. Testing

- `tools/qc-font.mjs` gets unit tests per check, with fixtures built from the
  known-bad fonts already identified (`medium_font` metrics, a running-stitch-only
  font, a caps-only font).
- Manifest generation is tested: license extraction, category assignment,
  coverage computation.
- Lazy font loading is tested at the adapter level — cache hit/miss, concurrent
  requests for the same font, and failed fetch surfacing an error rather than a
  silent empty design.
- Project model v2→v3 migration gets the same treatment v1→v2 received.
- Shape element generation is tested through `buildLetteringDesign` to confirm
  single-glyph output matches a text element with the same glyph.
- Existing engine suite must stay green; no stitch-math changes are in scope, so
  any diff in generated stitches for existing fonts is a regression.

## 10. Out of scope

- Monogram sets, non-Latin scripts, multi-color/applique/tartan/tricolore
  variants, texture variants (each needs engine work).
- SVG vector import (next slice, separate spec, same date).
- Retiring `EMB-Bot.html` (needs a feature audit first).
- Stroke→satin conversion.
- Outline-font (.otf/.ttf) import — auto-tracing was rejected on quality.

## 11. Risks

1. **Pictogram packs may not all be satin columns.** Some could be fills or
   multi-color, which would move them into the excluded set. The QC harness
   catches this at import, but ~14 could shrink. Mitigation: verify the packs
   first, before building the shape grid around them.
2. **Preview performance.** Even with pre-rendered PNGs, a 175-tile grid with
   live text rendering layered on is the most likely part of this slice to need
   rework. Mitigation: static PNGs must stand alone as an acceptable experience.
3. **Import volume.** ~140 fonts is far more than any prior font batch (max 7).
   Mitigation: the harness runs unattended; only flagged fonts consume attention.
4. **Repo size.** ~140 JSON files plus preview PNGs is a large committed
   addition. Worth confirming the delivery story before committing them all.
5. **Removing `satin-fonts.js` touches every existing font call site.** The lazy
   accessor must preserve current behaviour exactly; existing font output should
   be byte-identical.
