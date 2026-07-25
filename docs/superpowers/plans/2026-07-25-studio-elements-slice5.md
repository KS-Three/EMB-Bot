# Studio Slice 5: Multi-Element Designs + Thread Colors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A design can now hold MULTIPLE elements — text lines and images combined (logo + name, two fonts) — each independently selected, moved, sized, and colored on the field; image elements get per-swatch THREAD color pickers.

**Architecture:** Project model v2: `elements: [...]` (each element carries its own type/text/font/image-settings/size/offsets/colors) with automatic v1→v2 migration on load. Each element generates its own design via the EXISTING engine calls (offsets already bake hoop-space placement into the stitches), and a pure app-side `combineDesigns()` concatenates them with trim+color records — **no engine changes**. The field renders the combined design but keeps per-element bboxes for click-selection; handles/drag operate on the SELECTED element. ContentStep becomes an element manager (add/remove/select + per-element property panel). Image thread colors: per-palette-index RGB overrides applied when regions are built.

**Tech Stack:** unchanged. Branch `feat/studio-elements`.

## Global Constraints

- Do NOT modify `src/*.js`. Engine suite (145) stays green. App tests `.spec.js`.
- **v1 projects must keep working:** `deserialize`/`loadLocal` migrates `{mode,text,fontKey,...}` into `elements:[one element]` losslessly; a fresh `defaultProject()` is v2 with ONE text element.
- Element defaults: the FIRST element may use `sizeMm: null` (auto-fit); every ADDED element is seeded with an explicit `sizeMm` (40% of hoop width) and a small offset so it doesn't stack invisibly on the previous one.
- Combined designs: elements sew in array order; a trim + color-change separates consecutive elements' stitch runs. Per-element color blocks are preserved (image elements can be multi-color).
- Thread overrides: `element.threadRgb = { [paletteIndex]: [r,g,b] }` — affects generated stitches AND the field preview; the flatten PREVIEW (art) stays showing art colors, chips get a small thread-color input.
- The hoop-clamp, sub-5mm warning, and SizePanel semantics from Slice 3/4 now apply to the SELECTED element.

---

### Task 1: Project model v2 + migration + element ops

**Files:**
- Modify: `app/src/lib/project.js` (+spec), `app/src/lib/save.js` (+spec), `app/src/lib/templates.js` (+spec), `app/src/lib/flow.js` (+spec)

**Interfaces:**
- `defaultProject() → { version: 2, garmentId: "left_chest", selectedId: "e1", elements: [defaultTextElement("e1")] }`
- `defaultTextElement(id) → { id, type:"text", text:"", fontKey:"geneva_simple", colorRgb:[20,20,20], letterSpacingMm:0, underlay:true, sizeMm:null, offsetXMm:0, offsetYMm:0 }`
- `defaultImageElement(id) → { id, type:"image", nColors:4, removeBg:true, threadRgb:{}, underlay:true, sizeMm:null, offsetXMm:0, offsetYMm:0 }`
- `addElement(project, type) → project` (generates next id "eN"; non-first elements seeded `sizeMm: 0.4 * hoopWmm`-style — caller passes `hoopWmm`; offsets +0, −10*(n−1) so items stagger downward), `removeElement(project, id)`, `selectElement(project, id)`, `updateElement(project, id, patch) → project` (all immutable).
- `migrateProject(any) → v2 project` — v1 (`mode` at top level) becomes one element (text mode → text element carrying text/fontKey/colorRgb/letterSpacingMm/sizeMm/offsets; image mode → image element carrying nColors/removeBg/sizeMm/offsets). `deserialize` in save.js runs it; unknown input still falls back to `defaultProject()`.
- `flow.canAdvance("create", project)` → at least ONE element is "ready" (text element with text, or image element with `project._imagesReady?.[el.id]` — the UI supplies a runtime map; simplest: flow receives the project only and checks `el.type==="text" ? el.text.trim() : el._hasImage===true`, with `_hasImage` stamped on the ELEMENT by the UI).
- Templates: patches become v2 — each template's patch now sets `elements:[{...one seeded element...}]` + `selectedId` (keep the same 4 templates; logo-patch has an image element).

- [ ] TDD everything above (defaults shape, addElement id/seeding, remove/select/updateElement immutability, migrateProject from a real v1 fixture object, deserialize(v1 json) migrates, templates produce v2 patches whose fontKeys/garments validate against the engine).
- [ ] Full app suite green (EXPECT other specs to break — generate/flow specs reference v1 fields; UPDATE them minimally to v2 in this task so the suite is green at commit).
- [ ] Commit — `git commit -m "feat(app): project model v2 — multi-element with v1 migration"`

---

### Task 2: Per-element generation + combineDesigns

**Files:**
- Modify: `app/src/lib/generate.js` (+spec)
- Create: `app/src/lib/combine.js` (+spec)

**Interfaces:**
- `generate.js`: `generateElement(element, garment, runtime) → design|null` — text: existing buildLetteringDesign path using the ELEMENT's fields; image: needs `runtime.flats[element.id]` (a flatState) → existing flatToRegions/buildQualityDesign path, applying `element.threadRgb` overrides (see Task 3), and `targetWidthMm/offsets` from the element. Returns null if the element isn't ready (empty text / no flat).
  `generateAll(project, runtime) → { combined, perElement: [{id, design, bboxMm}] }` — generates every ready element in order, combines, and computes each element's bbox in mm (stitch coords /10).
- `combine.js`: `combineDesigns(designs) → design` — pure: `stitches` = d0.stitches (minus trailing "end") ++ for each next d: `{type:"trim"}` at last pos, `{type:"color"}`, then d.stitches (minus trailing end) ... final "end" if the inputs had one (inspect real designs: buildLetteringDesign emits no explicit "end"; buildQualityDesign returns stitches possibly with "end" — READ both return paths and normalize: strip any `type:"end"` records and do NOT append one; the exporters already handle designs without it — VERIFY by reading `src/dst.js` encodeDST's handling first; if encodeDST requires an end record, append exactly one at the very end).
  `colors` = concat of each design's colors; `stitchCount` = sum; `widthMM/heightMM` = combined bbox from stitches (mm); `colorCount` = colors.length; `_debug` merged loosely.
- Spec: combining two known text designs → stitchCount = sum; exactly one trim+color pair inserted between; colors.length = 2; decoding survives `EMB.encodeDST(combined)` (bytes > both inputs).

- [ ] TDD; full suite green; commit — `git commit -m "feat(app): per-element generation + stitch-level combineDesigns"`

---

### Task 3: Thread color overrides (image) 

**Files:**
- Modify: `app/src/lib/imageRegions.js` (+spec)

**Interfaces:**
- `flatToRegions(flat, opts)` gains `opts.threadRgb` (`{ [paletteIdx]: [r,g,b] }`): each region's `rgb` becomes the override when present, else the palette color. (Region order = palette index order — the existing code already iterates palette indices; keep the mapping stable and skip-safe.)
- Spec: a two-color flat with `threadRgb: {0: [255,0,0]}` → region[for palette 0].rgb === [255,0,0], other region keeps its palette color.

- [ ] TDD; suite green; commit — `git commit -m "feat(app): per-swatch thread color overrides in image regions"`

---

### Task 4: Field — multi-element render, selection, per-element handles

**Files:**
- Modify: `app/src/ui/EmbroideryField.svelte`, `app/src/lib/interact.js` (+spec if new math), `app/src/App.svelte`

**Behavior:**
- App owns `runtime = { flats: {}, workImages: {} }` keyed by element id (replaces the single workImage/flat — migrate the existing wiring; ImagePanel events now carry the element id).
- Field calls `generateAll(project, runtime)`; renders the COMBINED design (hooped, as today); keeps `perElement` bboxes.
- Click selects the element whose bbox contains the point (topmost = LAST in array order wins); selection drawn only around the SELECTED element's bbox with its handles; empty-space click keeps current selection.
- Drag/resize applies to the selected element via `updateElement` patches (`dispatch("update", { elementId, patch })` — App routes to updateElement). Seeding sizeMm-from-current-width now reads the SELECTED element's bbox width.
- Stats line: combined stitchCount + combined size; the sub-5mm warning fires per selected element (check its bbox).
- Post-generation offset re-clamp (Slice 3 fix) now clamps EACH element's offsets against the hoop.

- [ ] Implement; any new pure math (bbox contains-point, topmost pick) goes in interact.js with specs; suite green; build clean; commit — `git commit -m "feat(app): multi-element field — per-element selection, handles, combined render"`

---

### Task 5: UI — element manager + per-element panels + thread pickers

**Files:**
- Modify: `app/src/ui/ContentStep.svelte`, `app/src/ui/TextStep.svelte` (→ per-element text panel), `app/src/ui/ImagePanel.svelte` (element-scoped + thread pickers), `app/src/ui/SizePanel.svelte` (selected element), `app/src/App.svelte`, `app/src/ui/theme.css`

**Behavior:**
- ContentStep header: element LIST — one row per element (icon + summary: `Text — "YOUR NAME"` / `Image — 3 colors`), click selects (syncs `selectedId`, same selection the field uses), ✕ removes (min 1 element enforced), plus "+ Text" and "+ Image" buttons (call addElement with hoopWmm from the garment).
- Below the list: the SELECTED element's panel (TextStep fields bound to that element via `updateElement`, or ImagePanel scoped to that element's runtime flat/workImage + settings).
- ImagePanel swatches: each chip gains a small `<input type="color">` (thread override for that palette index → `updateElement(id, { threadRgb: {...} })`); a tiny "reset" affordance clears the override. Chips still merge-select as before (two interactions: click = select-for-merge, the color input is its own control).
- SizePanel binds to the SELECTED element (sizeMm/offsets/dims of that element; dims event from the field now reports the selected element's bbox).
- Mode tiles ("Text"/"Logo or image") are REPLACED by the element list + add buttons (the old mode concept dissolves; `project.mode` is gone in v2 — flow/templates already updated in Task 1).

- [ ] Implement; suite green; `npm run build` clean; commit — `git commit -m "feat(app): element manager UI + per-element panels + thread color pickers"`

---

### Task 6: Browser acceptance + docs (controller)

- [ ] Live: template → add a second text element (different font/color) → both render, click-select each, move/resize independently → add image element, upload, override a swatch's thread color (field re-renders in the new thread color) → DST downloads with MULTIPLE color blocks (decode: colorChanges ≥ 1) → PDF worksheet still works → v1 localStorage project migrates on reload. Regression: single-element text flow feels unchanged.
- [ ] README update; ledger; commit.

## Notes for the implementer
- READ `src/dst.js` encodeDST color/end-record handling BEFORE writing combineDesigns.
- Stitch coords are hoop-absolute (offsets baked in) — combining is pure concatenation; do NOT re-center in combineDesigns.
- The old `project.mode`/top-level text fields die in v2 — grep the whole `app/src` for `project.mode|project.text|project.fontKey|project.sizeMm|project.offset` and migrate every reference to the element model.
