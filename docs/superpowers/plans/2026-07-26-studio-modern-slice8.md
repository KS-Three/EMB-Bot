# Studio Slice 8: "Modern Studio" — Visual Overhaul + Display Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elevate the studio from "functional" to "credible modern design tool": a cohesive design system (modern-studio direction), a richer embroidery field (fabric color, weave, zoom), visual pickers (garment illustrations, template previews, grouped fonts), and a named thread-color system.

**Architecture:** Pure app-layer work (`app/` only; engine untouched). A token-based design system in `theme.css` (CSS custom properties: palette, type scale, spacing, radii, elevation) with Inter via `@fontsource-variable/inter` (bundled, offline). Field upgrades ride through `renderRealistic` opts (fabric color/weave) + a view-transform (zoom) held by EmbroideryField. Thread system = a curated named palette in `lib/threads.js` + one `ThreadPicker.svelte` used everywhere colors are chosen.

**Tech Stack:** unchanged + `@fontsource-variable/inter` (npm, bundled). Branch `feat/studio-modern`.

## Global Constraints

- `app/` only; do NOT modify `src/*.js`. Engine 155 / app 149 suites stay green; new logic gets specs.
- Fully offline (fonts/textures bundled or procedural — no CDN).
- The "modern studio" look: light neutral ground with ONE confident accent (indigo family, keep `--accent` as the single accent), Inter type with a real scale, subtle elevation (2 shadow levels), consistent radii, visible keyboard focus everywhere, `prefers-reduced-motion` respected for every transition added.
- Backward compat: existing saved projects must load unchanged. New project field(s) (`fabricRgb`) get defaults via `migrateProject`-style merge (already spread-merges over defaults — verify).
- The 2.5D preview stays a still image (no animation); zoom must not distort stitch thickness logic (thread px scales with zoom).
- Thread palette: ~48-64 GENERIC named shades (no brand names), each `{ name, rgb }`; custom hex stays available ("Custom…").

---

### Task 1: Design system + chrome (theme, topbar, stepper)

**Files:**
- Modify: `app/src/ui/theme.css` (token system rewrite), `app/src/App.svelte` (topbar structure), `app/src/ui/StepNav.svelte` (labeled stepper)
- Add dep: `@fontsource-variable/inter` (import in `app/src/main.js`)

**Details:**
- Tokens at `:root`: `--ink/--muted/--bg/--surface/--border/--accent/--accent-ink/--radius-s/-m/-l/--shadow-1/-2/--space-1..6`, type scale (`--fs-xs..xl`, Inter). Rework EVERY existing component style to consume tokens (grep the whole theme; keep class names stable so components don't change).
- Topbar: compact logo mark ("EMB" tile + "Bot Studio"), centered editable project name (subtle until hover/focus), right side: My designs button (badge) + a small "Download" shortcut jumping to the download step when a design exists.
- StepNav: labeled steps (Garment · Content · Review · Download) — clickable for steps already reachable (`canAdvance` chain respected: clicking a future step allowed only if all gates up to it pass; past steps always clickable); current step accented; keep Back/Next buttons.
- Transitions: 120-160ms ease on hover/panel swaps via CSS only, all inside `@media (prefers-reduced-motion: no-preference)`.
- Verify: build clean; suite green; visual pass is controller's.

### Task 2: Field upgrades — fabric color, weave, zoom

**Files:**
- Modify: `app/src/lib/project.js` (+spec: `fabricRgb: [235,232,223]` default at PROJECT level), `app/src/lib/preview.js` (+spec where pure), `app/src/ui/EmbroideryField.svelte`, `app/src/ui/GarmentStep.svelte` (fabric color control), `app/src/lib/generate.js` only if needed (it isn't — fabric is render-only).

**Details:**
- `renderRealistic` opts gain `fabricRgb` ([r,g,b] → bg fill + hoop ring contrast) and `weave: true` — a cheap procedural weave: after bg fill, draw a subtle crosshatch (1px lines every ~3px at 8% alpha of a darkened fabric tone, both directions) BEFORE strands; skip when zoomed-out scale makes it noise (< 1.5 px/mm). Pure helper `weavePattern(ctx, w, h, rgb, scale)` testable by spy.
- Zoom: EmbroideryField keeps `let zoom = 1` (1-4x), wheel on canvas zooms around the cursor (translate the hoop transform), a small zoom control (− / % / + / fit) overlaid on the field corner; pan by dragging EMPTY field space when zoom > 1 (design drag still wins when hitting the design). Implementation: extend the hoopTransform usage — `renderRealistic` opts gain `view: { zoom, panX, panY }` applied to the transform (pure math in `hoopTransform` or a wrapper — spec the math: zoom 2 doubles scale and keeps the anchor point fixed).
- Fabric color UI: on the Garment step under the tiles: "Fabric color" — a row of ~8 garment-common swatches (white, natural, sand, red, royal, navy, forest, black) + Custom; sets `project.fabricRgb`, field re-renders (render-only, not in stitches). Thread contrast: hoop outline + hint colors must stay legible on dark fabrics (compute luminance → switch outline/hint to a light variant when fabric is dark; pure helper + spec).
- Sub-5mm warning etc. unchanged.

### Task 3: Visual pickers — garment art, template previews, grouped fonts

**Files:**
- Modify: `app/src/ui/GarmentStep.svelte`, `app/src/ui/TemplateRow.svelte`, `app/src/ui/FontSelect.svelte`, `app/src/ui/theme.css`
- Create: `app/src/ui/garmentArt.js` (inline SVG strings per garment id)

**Details:**
- Garment tiles: small inline SVG line-illustrations (hat front, left chest polo, full back tee, beanie, sleeve, tote, jacket back, patch, towel, blanket) — simple 2-tone strokes using `currentColor` + accent; hand-write compact paths (~10-20 commands each; keep each under ~600 bytes). Tile layout: icon over label, selected state = accent ring + tint.
- Template cards: each card renders a real mini stitch preview on mount — generate via the same engine path (`buildLetteringDesign` for text templates at low density e.g. spacingMm 1.2 for speed; the logo-patch template shows an upload glyph instead) onto a small canvas via `renderRealistic` design-fit; cache per template id (module-level). Card = preview + label + hint.
- FontSelect: group options under headers (Sans / Serif / Script / Display) via a hardcoded style map in `FontSelect.svelte` (keys → group; unknown keys land in "More"); bigger thumbnails (280×44 wide "Sample" renders); sticky group headers in the list; keep lazy thumbnail generation + cache.

### Task 4: Thread color system

**Files:**
- Create: `app/src/lib/threads.js` (+spec), `app/src/ui/ThreadPicker.svelte`
- Modify: `app/src/ui/TextStep.svelte`, `app/src/ui/ImagePanel.svelte`, `app/src/ui/DownloadStep.svelte`, `app/src/ui/theme.css`

**Details:**
- `threads.js`: `THREADS: [{ name, rgb }]` — 56 generic shades covering a real embroidery wheel (whites/creams, yellows, oranges, reds, pinks, purples, blues, teals, greens, browns, greys, black, plus metallic-ish gold/silver tones named "Old Gold"/"Silver Grey" etc. — NAMES generic, no brands); `nearestThread(rgb) → {name, rgb, index}` (Euclidean RGB); spec: exact match returns itself; a near-miss maps to the nearest; list has no duplicate names.
- `ThreadPicker.svelte`: props `rgb`; renders the current swatch + name (via nearestThread when not exact) as a button; opens a compact popover grid of all shades (title tooltips), plus "Custom…" exposing the raw color input; dispatches `pick` with `[r,g,b]`. Keyboard: grid focusable, Esc closes. ONE component reused everywhere.
- Replace raw `<input type="color">` in TextStep (element color) and ImagePanel (per-swatch thread overrides) with ThreadPicker (ImagePanel keeps the per-swatch reset affordance).
- DownloadStep: a "Threads" summary — the combined design's colors mapped through `nearestThread` (name + swatch + count of blocks), so a user can shop shades.
- Fabric swatch row (Task 2) may reuse the popover pattern but stays its own simple control.

### Task 5: Browser acceptance + visual report + final review (controller)

- [ ] Full-flow acceptance across BOTH modes at desktop width; verify: tokensized chrome, labeled stepper gating, fabric color changes field + legibility on navy/black, zoom/pan (wheel + buttons; drag-design still wins), garment art renders, template previews generate, grouped font list, ThreadPicker everywhere + download thread summary; reduced-motion query present; suites green; build clean.
- [ ] Produce a visual report for Kent: capture field canvas states (dataURL) + describe chrome; publish updated artifact page with before/after screenshots where capturable.
- [ ] FINAL REVIEW via 3-lens workflow (correctness/regressions · visual-consistency/a11y · perf) + adversarial verification; fix loop; merge to main + push; memory.

## Notes for the implementer
- Class names in theme.css are consumed across many Svelte files — keep selectors stable; you are re-skinning, not renaming.
- `renderRealistic` return contract (toCanvas/scale/designBBoxMm) is consumed by EmbroideryField interaction code — extending the transform with zoom/pan MUST keep that contract correct (interaction math depends on it; update the px→mm conversions for zoom).
- FontSelect thumbnails use the design-fit path — don't regress it.
- Template preview generation must not block first paint (generate lazily/idle; cache).
