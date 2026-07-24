# EMB Bot Studio — design spec

**Date:** 2026-07-24
**Status:** approved direction; Slice 1 detailed for build
**Author:** Kent + Claude

## 1. Vision

A browser-based, beginner-first embroidery design tool — in the spirit of Ember
Design (emberdesign.net), but better on the three things that matter most to a
newcomer's trust and results:

1. **Photo/art digitizing quality** (clean art & logos first, honest about photos).
2. **Font library + quality** — pre-digitized satin fonts with real underpathing.
3. **A realistic preview** — 2.5D shaded-thread rendering so people believe the output.

The product is validated in slices. This spec covers **Slice 1**, the first thing
we put in front of real testers, and records the roadmap for growing it into a
larger product if it validates.

### Positioning
MVP to **validate first**. Not a launched SaaS yet: no accounts, no billing, no
backend. Prove the concept and the quality with a handful of real users, then
decide whether to grow it into a hosted product.

### Success criteria (what "validated" means)
- **Beginners succeed fast:** a newcomer reaches a good, downloadable stitch file
  in minutes, without help or confusion.
- **Usable real files:** testers actually run the file on their machine and are
  happy with the result on fabric (same byte-verified DST engine we already have).
- **Would-pay signal:** testers say they'd use it regularly / pay for it.

## 2. Shape of the product (settled)

- **Client-side static web app.** Runs entirely in the browser; deploys as static
  files (GitHub Pages / Netlify) for free; no server, no accounts. Projects save
  locally (browser storage + downloadable project file).
- **Guided generator, not a full canvas editor.** A short, hand-holding flow:
  choose what you're making → add content → auto-generate → preview → download.
  (A full drag/layer/node editor is explicitly out of scope for the MVP.)
- **Reuses the existing engine.** The stitch logic (digitize, satin fonts,
  underpathing, exporters) is proven and stays the source of truth; the new work
  is the UI, the guided flow, and the realistic preview.

## 3. Slice 1 — "Guided Text Studio"

The first testable release: a complete, polished beginner journey for **text /
lettering**, our strongest quality card, plus the realistic preview. It showcases
two of the three differentiators (fonts + preview). Photo/logo digitizing is the
very next slice.

### The guided flow (5 steps)
1. **What are you making?** Garment tiles (hat front, left chest, shirt front,
   tote, …). Selecting one sets hoop size, placement, and smart stitch defaults
   (density, pull comp, underlay) via the existing garment/fabric presets.
2. **Add your text.** Type the text; pick a font from the satin-font gallery
   (live thumbnails); choose size and thread color. Smart defaults so a beginner
   can skip straight to preview.
3. **Generate.** The engine runs (satin font layout + underpathing) behind a
   friendly progress state.
4. **Realistic preview.** 2.5D shaded-thread render on a fabric swatch. Change
   thread colors live; a plain "does this look right?" gut-check.
5. **Download.** DST by default, plus PES/EXP and the printable worksheet/PDF.

### Beginner-first principles
- Smart defaults everywhere; advanced controls tucked behind an optional panel.
- Plain language ("hat front", not "hoop 5×2.25in"), one decision per step.
- The preview is the confidence-builder — it must look convincingly like thread.

## 4. Architecture

Static Svelte + Vite app. Clear module boundaries so each unit is understandable
and testable on its own:

- **`engine/`** — the existing dual-mode JS modules (`digitize`, `satinfont`,
  `satinplay`, `satin`, `fill`, `fonts`, `dst`/`exp`/`pes`/`svgexport`,
  `garments`, `fabrics`, `units`) imported unchanged. Keeps stitch generation
  isolated; the existing `node --test` suite (139 tests) keeps guarding it.
- **`preview/`** — new Canvas-2D **2.5D renderer** (distinct from the existing
  flat 2D `render.js`; new name e.g. `renderRealistic`). Pure function
  `renderRealistic(stitchList, opts) → canvas image`: each satin/running stitch
  drawn as a lit thread strand (directional highlight + soft drop shadow) over a
  fabric texture; thread color per block. No 3D library. Independently testable
  by rendering to an offscreen canvas and asserting on pixels/among snapshots.
- **`flow/`** — the guided-step state machine + the **project model** (garment,
  text runs, font, colors, settings). One place that knows "what the user built."
- **`save/`** — project ↔ localStorage; export/import a `.embproj` JSON file.
  No backend.
- **`ui/`** — Svelte components per step; the gallery, controls, and download bar.

### Data flow
`flow` (project model) → `engine.buildLetteringDesign(...)` → stitch list →
`preview.renderRealistic(...)` for the on-screen 2.5D image **and** →
`engine` exporters for the downloadable files. Preview and export consume the
*same* stitch list, so what you see is what you sew.

### Choice of stack
Svelte + Vite: smallest/fastest static output, minimal boilerplate, reactivity
that fits a stepwise UI + live canvas. Alternatives considered: React+Vite
(heavier than needed), vanilla+Vite (too much hand-written state for a polished
flow).

## 5. The 2.5D preview (new, the differentiator)

Goal: a beginner looks at it and trusts it's what they'll get. Approach:
- Draw on a fabric-texture background (subtle weave, tinted to garment color).
- For each stitch segment, draw a **thread strand**: a rounded capsule with a
  light-direction highlight along its length and a soft offset shadow, colored by
  the thread block. Satin columns read as dense parallel sheen; running/underpath
  stays hidden beneath (drawn first, covered).
- Order matters: underlay/underpath drawn before top stitches (mirrors sew order).
- Performance: batch by color; cap redraw cost; it's a still image, not animated.

Full rotatable 3D + fabric drape is a **later** slice, not the MVP.

## 6. Engine work that rides along

Quality fixes already validated against Ink/Stitch's own font previews land in
the shared engine and benefit the app directly:
- Rail/rung classification by intersection count; Chinese-Postman underpath
  routing; bbox-derived advances for metric-less fonts.
- **Known open item:** lowercase-"e"/tight-curl satin fan — the fix is
  density-adaptive correspondence resolution (resample rung-sections by length,
  not a fixed count). Tracked and fixed in `satinplay`.

## 7. Testing

- Engine: existing `node --test` suite stays green (139+).
- Preview: offscreen-canvas render tests (non-empty, correct bounds, color blocks).
- Flow/model: unit tests on the project model and step transitions.
- Manual: the beginner journey on a few real garments/fonts, ending in a DST that
  decodes cleanly (existing `render-dst` check).

## 8. Roadmap (slices)

- **Slice 1 (this spec):** shell + guided text flow + 2.5D preview + export + local save.
- **Slice 2:** photo/logo digitizing — flatten workflow + auto-digitize + quality
  polish, added as a parallel input path in the same guided flow.
- **Slice 3:** grow the font library (toward/beyond Ember's 25), more garments.
- **Slice 4:** onboarding polish, templates, saved-project management.
- **Beyond MVP (if validated):** accounts + cloud projects, sharing/community,
  paid tier, full 3D preview, batch/roster names. These require a backend and are
  deliberately deferred until validation.

## 9. Non-goals for the MVP
Full canvas/node editor; accounts/billing/backend; cloud sync; marketplace;
custom user font upload; complex-photo/portrait digitizing promises.

## 10. Risks / open questions
- **Preview realism vs effort:** 2.5D must look good enough to build trust without
  ballooning into a 3D engine. Mitigation: iterate on the strand shader with real
  stitch outputs; keep it a still image.
- **Repo layout:** app lives in the same repo to reuse `engine/` — confirm folder
  structure (`app/` for the Svelte project, engine imported from existing `src/`).
- **Font count for launch:** 14 today; is that enough to validate, or grow first?
- **Naming/branding:** working name "EMB Bot Studio"; revisit before any public test.
