# Studio Slice 4: Polish Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the guided studio's "first five minutes": printable PDF worksheet in the download step, letter-spacing control for text, ~10 more satin fonts, and one-click starter templates on the first screen.

**Architecture:** All engine capabilities already exist (`EMB.buildWorksheetPDF`, `letterSpacingMm` plumbed through `buildLetteringDesign`, the font builder toolchain). This slice is app wiring + one offline dependency (jspdf via npm, exposed as `window.jspdf` before the engine call) + an offline font-batch import using `tools/build-font.mjs`.

**Tech Stack:** unchanged. Branch `feat/studio-polish`.

## Global Constraints

- Do NOT modify `src/*.js` EXCEPT regenerating `src/fonts/satin-fonts.js` + adding `src/fonts/<key>.{json,LICENSE.txt}` via the existing toolchain (Task 3 — data, not code). Repo-root `node --test` (145) stays green.
- App tests `.spec.js`. Text path stays offline — jspdf ships IN the bundle (npm dep), not from a CDN.
- Fonts: only satin + permissive licenses (OFL/CC-BY-SA/public domain) from `github.com/inkstitch/embroidery-fonts`; keep each LICENSE; build with `FLATTEN=5`; skip any font whose built JSON > 1 MB.
- Templates are PRESETS, not saved projects: applying one just patches the project model.

---

### Task 1: Letter spacing (text mode)

**Files:**
- Modify: `app/src/lib/project.js` (+spec), `app/src/lib/generate.js` (+spec), `app/src/ui/TextStep.svelte`

**Interfaces:**
- `defaultProject()` gains `letterSpacingMm: 0`.
- `generateDesign` passes `letterSpacingMm: project.letterSpacingMm || 0` (engine already consumes it — `src/digitize.js:536`).
- TextStep gains a compact "Letter spacing" slider, range −1…6 mm step 0.5, default 0, label shows the value; dispatches `update({ letterSpacingMm })`.

- [ ] **Step 1: Failing tests** — project default includes `letterSpacingMm: 0`; generate: same text with `letterSpacingMm: 4` yields `design.widthMM` strictly greater than with 0 (use text "AB", `sizeMm: null`, and assert width increases by ≥ 3mm).
- [ ] **Step 2-4: Implement, verify (`npx vitest run` all green; build clean), commit** — `git commit -m "feat(app): letter spacing control (text mode)"`

---

### Task 2: PDF worksheet in the download step

**Files:**
- Modify: `app/package.json` (add `"jspdf": "^2.5.1"` dependency), `app/src/lib/exporters.js` (+spec), `app/src/ui/DownloadStep.svelte`

**Interfaces:**
- New in exporters.js: `exportWorksheetPDF(design, garment)` — dynamic-imports jspdf (`const mod = await import("jspdf")`), sets `window.jspdf = { jsPDF: mod.jsPDF }` if not already set, then calls `EMB.buildWorksheetPDF(design, { garmentLabel: garment.label, fileName: "embbot-worksheet.pdf", garmentBox: { widthMM: garment.widthIn*25.4, heightMM: garment.heightIn*25.4 } })`. NOTE: read `src/pdfsheet.js` first — `buildWorksheetPDF` SAVES the file itself via jsPDF's `doc.save`, so this helper triggers the download directly (async function, no `{bytes}` return).
- DownloadStep: add a "PDF worksheet" button (both modes) calling it with the current design + garment; disable + friendly error while/if jspdf fails to load.

- [ ] **Step 1: `cd app && npm install jspdf`** (writes package.json + lockfile).
- [ ] **Step 2: Failing spec** — in `exporters.spec.js` (node env): mock enough to assert wiring — `exportWorksheetPDF` sets `window.jspdf.jsPDF` and calls `EMB.buildWorksheetPDF` with a `garmentBox` of `{widthMM: 127, heightMM: 57.15}` for a 5×2.25in garment (stub `EMB.buildWorksheetPDF` via spy on the loaded engine global; restore after).
- [ ] **Step 3-4: Implement, verify (all specs green; `npm run build` clean — jspdf becomes a lazy chunk), commit** — `git commit -m "feat(app): PDF worksheet export (offline jspdf)"`

---

### Task 3: Font batch import (~10 more satin fonts) — CONTROLLER TASK (needs network + visual QC)

Candidates (satin + permissive, from the surveyed library — final picks by size/quality):
sans/display: `tt_directors`, `excalibur_KOR` (public domain), `milli_marif_bold`, `inkstitch_masego`, `roaring_twenties_KOR`; serif: `emilio_20_bold`, `roman_ags`; script: `monicha`, `auberge_marif`, `digory_doodles_bean`.

- [ ] Download each font dir (ltr.svg + font.json + LICENSE) into `scratch_ink/<key>_dir`; verify `satin_column` count > 0.
- [ ] `FLATTEN=5 node tools/build-font.mjs scratch_ink/<key>_dir src/fonts/<key>.json` for each; DROP any output > 1 MB.
- [ ] Montage-render "Sample" per font (`tools/word-satin.mjs` + the montage script pattern); view; drop any that render broken/illegible.
- [ ] Regenerate `src/fonts/satin-fonts.js` with ALL kept keys (existing 14 + new); copy LICENSEs to `src/fonts/<key>.LICENSE.txt`.
- [ ] Verify: `node --test` (145) green; app `npx vitest run` green (the ≥14 fonts assertion still passes); `node tools/bundle.mjs` rebuilds the old-tool standalone (also gains the fonts).
- [ ] Commit — `git commit -m "feat(fonts): +N satin fonts (…styles…), licenses kept"`

---

### Task 4: Starter templates on the first screen

**Files:**
- Create: `app/src/lib/templates.js` (+spec), `app/src/ui/TemplateRow.svelte`
- Modify: `app/src/ui/GarmentStep.svelte` (host the row), `app/src/App.svelte` (apply patch + jump), `app/src/ui/theme.css`

**Interfaces:**
- `templates.js` exports `TEMPLATES: [{ id, label, hint, patch }]` — each `patch` is a plain project patch. Ship exactly 4:
  1. `{ id:"hat-name", label:"Name on a hat", hint:"Bold block letters, hat front", patch:{ garmentId:"hat_front", mode:"text", fontKey:"manga_impact", text:"YOUR NAME", sizeMm:null, offsetXMm:0, offsetYMm:0 } }`
  2. `{ id:"chest-name", label:"Left-chest name", hint:"Clean sans, business look", patch:{ garmentId:"left_chest", mode:"text", fontKey:"geneva_simple", text:"Your Name", sizeMm:76.2 } }` (3in)
  3. `{ id:"script-name", label:"Script monogram", hint:"Flowing cursive", patch:{ garmentId:"left_chest", mode:"text", fontKey:"aventurina", text:"Yours", sizeMm:null } }`
  4. `{ id:"logo-patch", label:"Logo patch", hint:"Upload your logo next", patch:{ garmentId:"patch", mode:"image" } }`
  and `applyTemplate(project, template) → project` (merge patch, always resets offsets to 0 unless patch sets them).
- UI: a "Quick start" row of 4 template cards ABOVE the garment tiles on the first step. Clicking one applies the patch and jumps the flow to the "content" step (dispatch a `template` event; App applies + sets `step = "content"`).
- Spec: applyTemplate merges + resets offsets; every TEMPLATES entry's `fontKey` (when mode text) exists in `EMB.SATIN_FONTS` and `garmentId` resolves via `EMB.getGarment` (engine-loading test pattern).

- [ ] **Step 1-4: TDD templates.js, build UI, verify (suite green, build clean), commit** — `git commit -m "feat(app): quick-start templates on the first screen"`

---

### Task 5: Browser acceptance + docs (controller)

- [ ] Live: template card → lands on content step with prefilled text/font → spacing slider visibly widens text in the field → download PDF (file saves, non-trivial size) + DST → image template jumps to image mode. Text+image regression.
- [ ] New fonts appear in FontSelect with rendered thumbnails (spot-check 3).
- [ ] Update `app/README.md` (templates, spacing, PDF, font count). Ledger. Commit.

## Notes for the implementer
- jspdf import must be DYNAMIC so the initial bundle stays lean and the text path loads instantly.
- `buildWorksheetPDF` reads `window.jspdf.jsPDF` (src/pdfsheet.js:29) and saves the file itself.
- Template `fontKey`s reference fonts that exist in the CURRENT registry — if Task 3 changes availability, Task 4's spec catches it.
