# Font library expansion (Slice 10) — design

Date: 2026-07-27 (revised same day after the roadmap reset — see §0)
Status: approved in brainstorming, pending plan
Sequencing: **now FIRST**, ahead of the parked SVG import slice (see §0)

## 0. Roadmap reset (2026-07-27, supersedes earlier sequencing)

Kent re-stated the product direction mid-day and several earlier decisions
changed. The tool is an **in-house embroidery interface** (Kent is the primary
user; Tajima/DST machine), with a possible market product later. Priorities:

1. **Fonts — as many as possible.** This slice. Now first in line.
2. **Pre-digitized designs found online** (DST import — decode logic already
   exists in `tools/render-dst.mjs`, needs porting into the engine).
3. **Auto-digitizing (photo → embroidery file): TABLED.** Not the product.
   The existing image path stays but gets no further investment for now.
4. Market: later; keeps constraints (licensing) but drives nothing today.

Consequences binding this spec:
- **SVG import (Slice 9) is PARKED** at Task 1 (committed clean on
  `feat/svg-import-shapes`, review approved). Its remaining justification is
  the 44 fill-artwork fonts (below), not customer logos.
- Font source is now **Kent's local clone** of inkstitch/embroidery-fonts at
  `scratch_ink/` (140 dirs, 302 MB, copied from Desktop) — not remote fetches.
  Remote probes earlier today produced a false finding (six packs "missing
  font.json" that actually have it); local files are ground truth.
- Font stitch-out validation is **Kent's own loop**: he stitches, he reports.
  The tool's QC duty is everything machine-checkable short of thread.

## 2. Source and eligible set — MEASURED, no longer estimates

All 140 dirs in `scratch_ink/` were classified on 2026-07-27
(`scratch_ink/_classify.mjs`, results in `scratch_ink/_tiers.json`). A trial
bulk import of every new satin-capable `ltr.svg` font succeeded **70/70 with
zero failures** (`scratch_ink/_out/*.json`, 62 MB raw JSON).

### The two tiers (Kent's decision, 2026-07-27)

**VERIFIED (71 = 21 shipped + 50 new): ships in the app.** Criteria, all
machine-checked per font: satin columns present; `ltr.svg` layout the importer
supports; `font.json` metrics present; LICENSE present; clean trial import;
full A–Z uppercase and 0–9 digits; every glyph advance > 0; Latin script; no
multi-color/applique variant markers.

**UNVERIFIED (69): does NOT ship.** Kent chose "don't ship them at all" over
badging or a toggle — users can never pick a font that might fail. Unverified
is an internal work queue, not a rejected pile. Reasons (fonts may have
several):

| Count | Reason | What would promote them |
|---|---|---|
| 44 | Fill artwork, zero satin columns | SVG import slice (parked Slice 9) |
| 10 | Multi-color/applique/tartan variants | per-glyph multi-color engine work |
| 9 | Non-Latin (Hebrew/Cyrillic/Greek/Braille) | RTL/layout proving |
| 6 | Missing digits | possibly nothing — some fonts are caps-only by design; needs per-font call |
| 6 | Missing uppercase | same |
| 6 | Glyphs with advance ≤ 0 | metrics repair in the importer |
| 5 | `ltr/` directory layout (incl. mai_en_fleur) | small importer extension — cheapest promotion available |
| 5 | No recognisable glyph source | investigate individually |

The manifest carries `tier: "verified" | "unverified"` per font, and the app
build includes only verified. Promotion = flipping the field after the gap is
closed and QC passes; the tiers are expected to shift over time.

### Historical estimate errors, for the record

Earlier versions of this spec estimated ~125 importable new fonts from
directory names. Measurement says **50 new verified** (plus a queue). The
directory-name heuristic overcounted by ~2.5x. Numbers in this spec are now
measurements; treat any surviving estimate with suspicion.

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
3. **`EMB-Bot-standalone.html` is retired.** ~145 fonts inlined would be tens of
   MB in a single local file, where gzip does not apply. Studio is the product.
   `tools/bundle.mjs` and the standing "rebuild the standalone after any `src/`
   change" rule retire with it.
4. **Slice order: this slice FIRST; SVG import parked.** (Third and final
   reorder — see §0. The middle state, "SVG import first," lasted a few hours
   until the roadmap reset removed its main justification.) Fonts and vector
   import remain independent — nothing here depends on that slice's code.
5. **QC is automated**, with human review only of what the harness flags.
   Stitch-out validation is Kent's loop, not the harness's (§0).
6. **Font browser**, not a longer dropdown. The shape grid moved to the SVG slice
   along with shapes themselves.
7. **Two tiers, verified-only ships** (§2). The manifest records both; the app
   build includes only `tier: "verified"`.
8. **Binary font format** (§4.1a) — measured 24.5x smaller than JSON, enabling
   "hundreds of fonts" per Kent's explicit request.

`EMB-Bot.html` (the non-inlined original tool) is **not** retired here. It may
still expose controls the Studio lacks — per-swatch stitch-angle override, the
explicit fabric dropdown. Audit before retiring it; that is separate work.

## 3a. Recommended split into two stages

Moving shapes and the model v3 migration into the SVG slice shrank this spec
meaningfully, but it still spans two distinct risk areas: a bulk data import
plus a delivery-architecture change, and new UI. Slices 1–8 ran 4–6 tasks each
and all merged clean; this is closer to 8.

**Stage A — library and delivery (no visible change)**
Binary format + manifest build, lazy font loading, removal of `satin-fonts.js`,
the QC/tier harness (already prototyped as `scratch_ink/_classify.mjs`), bulk
import of the 50 new verified fonts, licensing metadata. Ends with 71 verified
fonts present and loadable with the existing dropdown still in place and still
working. Verifiable on its own: output for the existing 21 fonts must match the
§4.1a guard and the app must behave exactly as it does today.

**Stage B — browser and credits (visible)**
Font browser with search, filters and live text previews; credits screen
generated from the manifest. Builds on a library already proven loadable.

The split is recommended, not mandatory. Its value is that Stage A's riskiest
change — removing the eager registry that every existing call site depends on —
gets verified against unchanged UI, so any regression is unambiguously the
delivery change rather than the new picker.

## 4. Architecture

### 4.1 Font delivery

Today all fonts are inlined into a single `src/fonts/satin-fonts.js` (~7.7 MB
for 21) and loaded eagerly. The 70-font trial import produced 62 MB of raw
JSON — the eager model is dead at this scale, and Kent wants headroom for
hundreds.

New model:

- A small **manifest** (`src/fonts/manifest.json`) holds per-font metadata only
  — key, display name, category, **tier**, license id, attribution, glyph
  coverage, `sizeMm`, recommended size band, preview image path. Kilobytes,
  loaded eagerly. Only verified-tier fonts are exposed to the app.
- Font data is fetched **on demand** when a font is first selected or
  previewed, then cached in memory.
- `satin-fonts.js` (the eager combined registry) is removed. `EMB.SATIN_FONTS`
  becomes a lazy accessor so existing engine call sites keep working.

### 4.1a Binary font format (measured 2026-07-27, `scratch_ink/_fmt.mjs`)

JSON stores coordinates as decimal text (`[77.5,113.4]` = 13 bytes for 4 bytes
of information). The replacement format: quantize coordinates to a fixed grid
(×4 per font unit), delta-encode consecutive points, pack as Int16, serve with
HTTP compression (brotli/gzip — native to every browser, zero dependencies).

Measured on real imported fonts (not estimated):

| Font | glyphs | JSON | binary+brotli |
|---|---|---|---|
| alchemy | 469 | 6.62 MB | 0.19 MB |
| montecarlo | 800 | 2.82 MB | 0.18 MB |
| cats | 115 | 0.50 MB | 0.03 MB |

**24.5x overall. Quantization error 0.02–0.03 mm** (machine placement is
~0.1 mm, so this is beyond stitch resolution). Zero Int16 overflow across
596k test points. Capacity math: 70 fonts ≈ 2.5 MB, 500 fonts ≈ 18 MB total
at rest; a user fetches ~35 KB per font actually used.

**Byte-identical guard:** decoded binary must produce byte-identical stitch
output vs. today's JSON for the existing 21 fonts, pinned by a snapshot test
BEFORE the JSON path is removed. Quantization changes coordinates by design,
so "byte-identical" is achieved by quantizing the reference JSON the same way
in the comparison — the test pins decoder correctness, and a separate
rendered-diff check pins that quantization is visually invisible.

### 4.2 Preview images

Generating real stitches for ~150 thumbnails on demand will not perform. Previews
are **pre-rendered at import time** into small PNGs (one per font, a fixed
sample string) and referenced from the manifest.

The browser's "preview my actual text" feature renders live, but only for fonts
currently visible in the viewport, debounced, and capped in flight. Static PNGs
carry the grid; live rendering is an enhancement layered on top.

### 4.3 No project model change

This slice adds no element types and no model migration. Fonts are selected by
key on existing text elements, exactly as today. The `shape` element type and
the v2→v3 migration live in the SVG import slice.

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

## 7. Licensing deliverables

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

## 8. Testing

- `tools/qc-font.mjs` gets unit tests per check, with fixtures built from the
  known-bad fonts already identified (`medium_font` metrics, a running-stitch-only
  font, a caps-only font).
- Manifest generation is tested: license extraction, category assignment,
  coverage computation.
- Lazy font loading is tested at the adapter level — cache hit/miss, concurrent
  requests for the same font, and failed fetch surfacing an error rather than a
  silent empty design.
- Existing engine suite must stay green; no stitch-math changes are in scope, so
  any diff in generated stitches for existing fonts is a regression.

## 9. Out of scope

- Monogram sets, non-Latin scripts, multi-color/applique/tartan/tricolore
  variants, texture variants (each needs engine work).
- Pictogram/shape packs, the `shape` element type, the shape grid, and the model
  v2→v3 migration — all moved to the SVG import slice, which precedes this one.
- SVG vector import itself (separate spec, same date, now PARKED — resumes when
  the 44 fill-artwork fonts or vector logo import justify it).
- The `ltr/` directory importer extension (5 fonts incl. mai_en_fleur). Small
  and high-value — first candidate AFTER this slice ships, but not in it.
- DST design import (roadmap item 2; decode exists in tools/render-dst.mjs).
- Retiring `EMB-Bot.html` (needs a feature audit first).
- Stroke→satin conversion.
- Outline-font (.otf/.ttf) import — auto-tracing was rejected on quality.

## 10. Risks

1. ~~Eligible font count unverified~~ **RESOLVED by measurement**: 50 new
   verified + 21 shipped = 71. The classify harness is the mitigation, now
   built and run.
2. **Preview performance.** Even with pre-rendered PNGs, a 71-tile grid with
   live text rendering layered on is the most likely part of this slice to need
   rework. Mitigation: static PNGs must stand alone as an acceptable experience.
3. **Binary decoder correctness.** A subtle decode bug corrupts every font at
   once. Mitigation: the §4.1a guard — snapshot tests pin decoder output for
   all 21 existing fonts before the JSON path is removed.
4. **Quantization taste risk.** 0.02mm is beyond machine resolution, but the
   proof is a rendered diff, not arithmetic. Mitigation: before/after renders
   of at least 3 fonts at hat scale in the plan's acceptance step.
5. **Removing `satin-fonts.js` touches every existing font call site.** The lazy
   accessor must preserve current behaviour exactly, pinned by the §4.1a guard.
6. **`_classify.mjs` criteria could mis-tier a font** (e.g. caps-only script
   fonts flagged for "missing uppercase" that are fine as monogram fonts).
   Mitigation: tiers live in the manifest as data, not code — a wrong call is
   a one-field fix, and Kent's stitch-out reports are the final arbiter.
