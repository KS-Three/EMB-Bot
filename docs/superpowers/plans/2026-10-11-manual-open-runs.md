# Open runs in the manual lane, and run ↔ column — Implementation Plan (plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A hand-drawn open polyline that sews as a running stitch along its own path (a bean by default), drawn in a **Line** mode beside Shape | Hole | Column, and convertible to a satin column and back without touching its spine.

**Architecture:** A run is a shape record `{ id, kind: "run", points, curves, colorRgb, passes?, stitchLenMm? }` — the same OPEN spine a column has, with no width. `shapesToRegions` hands the engine a hairline-stroked ring as `outer` (for hit-testing, the bbox and the sew order — nothing may sew it) and `sewAs: { kind: "run", path, passes, stitchLenMm }`. The engine branches on that `sewAs` with three gates (no underlay, `runAlongPath` as the top stitch, no finishing outline). Conversion swaps the fields a shape carries — the points and curves are copied, never recomputed.

**Tech Stack:** `src/fill.js` + `src/digitize.js` (browser-global engine, `node --test`), Svelte 5 in legacy syntax, vitest, Playwright, pystitch (read-back only, from the main checkout's `digitizer/.venv`).

**Spec:** `docs/superpowers/specs/2026-09-30-manual-digitizing-gaps-design.md` — §2 (a run's `outer` is a PROXY: ruling 1's three gates), §4 (the model; ruling 8, run ↔ column), **§7 (the whole of plan 3)**, §10 rulings 1, 4, 6, 7, 8. Plans 1–2: `2026-10-01-manual-holes.md`, `2026-10-01-manual-columns.md` (PR #831 — Column mode, `shapeRing`, `predictedFit`, `newColumnWidthPx`).

## Global Constraints

- **Byte-identical for every design with no run.** A region with no `sewAs`, or with a `sewAs` that is not `{ kind: "run", path: [≥2 points] }`, sews exactly as today (the existing test that a `sewAs: { kind: "run", railA, railB }` with no `path` is ignored must stay green). `shapesToRegions` on shapes with no `kind: "run"` emits exactly what it emits today. Engine `node --test` stays green with no stored hash or golden changed; one new sha256 pin is taken on origin/main's own code before any engine edit.
- **No new numbers** (ruling 6). Passes 3 and stitch 0.73 mm are `BEAN_PASSES` / `BEAN_STITCH_MM`, read from `EMB.LETTERING_GUARDS` (`src/satinfont.js:1301`) — never re-declared. The 2.2 mm floor is ONE new JS declaration, `RUN_MIN_LOOP_MM = 2.2` in `src/fill.js`, mirroring `digitizer_core/machine.py:724`. The hairline that strokes a run's proxy ring (`RUN_HAIRLINE_PX = 1`, authored px) is a hit-test aid, not a sewing number. Column width on conversion is `COLUMN_DEFAULT_MM` (ruling 9).
- **No ties** (ruling 7): `buildQualityDesign` has none; a single-pass run sews unlocked. Not papered over.
- **Do not bump `PROJECT_FILE_VERSION`.** `kind` absent means a closed shape.
- **UI word is "Line"** (ruling 4: `Shape | Hole | Column | Line`; ruling 8: *Make it a column* / *Make it a line*). The record kind is `"run"`; the span kind is `"run"`.
- **Exact user-facing strings:**
  - name: `Shape N · Line`
  - `A line needs at least 2 points.`
  - `This line is too short to sew.` (flattened length ≤ `MIN_COLUMN_LEN_PX`, the mis-click floor plan 2 set)
  - mode hint: `Click along the line, then double-click to finish.`
  - popover/assign rows: `Passes` (choices `Single run` = 1, `Bean (3 passes)` = 3), `Stitch length` (mm, step 0.1, min 0.5)
  - actions: `Make it a column`, `Make it a line`
  - short-run note (fit known, sewn length < 2.2 mm): `Shorter than 2.2 mm — it will not sew.`
- Self-crossing is ALLOWED for a run (a signature crosses itself). A run is never a cut-out and never a cut-out's parent.
- Closed ↔ open conversion is NOT offered (ruling 8).
- Engine edits in `src/` only; `node app/scripts/copy-engine.mjs` before any Studio/e2e run after one.
- Svelte: legacy syntax only. `EmbroideryField.svelte` has no mount test: `cd app && npx vite build` is its compile gate.
- Edit tool for source edits (PowerShell regex round-trips corrupt UTF-8). Never pipe a test run to `tail`; log to a file, append the exit code, read the log.
- One heavy job at a time. Studio suite `npx vitest run --maxWorkers=2`. Never the full Python suite. Playwright: only the spec files a task names.
- Don't edit `MASTER_SCOPE.md`, `docs/scope-history.md`, `DOCTRINE.md`, `CLAUDE.md`, `COOKBOOK.md` (foreman's rule for this run). The area doc `docs/scope/5-review-manual-editing.md` carries the record.
- Public repo: no client artwork or names in fixtures.

## Review Focus

1. **A run doubling straight back on itself** (a hairpin: A→B→A). The proxy ring folds; the run must still sew along its path and stay selectable. → Task 1 test (engine sews a hairpin path), Task 2 test (`runIssues` is empty for a hairpin and a figure-8).
2. **A curved run.** Curves must be flattened before the walk, or the stitches cut the chord. → Task 2 test (`shapesToRegions` hands a flattened `path` whose length is the curve's), Task 6 DST read-back on a bent line.
3. **Conversion at a different fit.** A run converted on the hoop must come out 4.0 mm drawn at the fit it is in and move nothing else. → Task 3 test through the real engine (rectangle does not move; width reads 4.0).
4. **A run below 2.2 mm sewn.** Must sew nothing and say why, not leave a stray stitch or an orphan outline. → Task 1 test (no stitches, outline dropped), Task 4 test (the note).
5. **`passes` / `stitchLenMm` absent on an old or fresh record.** Defaults must come from the engine, and a garbage value must fall back, not throw. → Task 1 test (`passes: 2`, `stitchLenMm: -1` fall back to the defaults).

---

### Task 1: Engine — `runAlongPath`, and a region that sews along its path

**Files:** Modify `src/fill.js`, `src/digitize.js`; Test `test/manualrun.test.js` (new).

**Interfaces — produces:**
- `fill.runAlongPath(path, { stitchLenPx, passes }) → [{x,y}...]` — walks the OPEN polyline at `stitchLenPx` (same carry walk as `runningOutline`, no closing segment), lands a station on the final vertex exactly (a remainder under half a step moves the last station onto it instead of adding a stub). `passes` 1 → the stations; 3 → stations forward, backward, forward over the SAME stations (`2n − 2` + `n − 1` more points; every pass ends on an end vertex). Any other `passes` value is treated as 1 if `< 2`, else 3. `[]` for a path with under two distinct points.
- `fill.RUN_MIN_LOOP_MM = 2.2` (exported on `EMB`).
- `digitize.js`: a region shape with `sewAs: { kind: "run", path: [≥2 {x,y}], passes, stitchLenMm }` sews ONLY `runAlongPath(path, { stitchLenPx: stitchLenMm × pxPerFinalMm, passes })` as one run of span kind `"run"`. No underlay (with or without fabric), no finishing outline, no fill plan, no pull comp. `passes` not 1 or 3 → `BEAN_PASSES`; `stitchLenMm` not a finite number > 0 → `BEAN_STITCH_MM` (both from `satinfontmod.LETTERING_GUARDS`). A path shorter than `RUN_MIN_LOOP_MM` in final mm sews nothing and its outline is dropped.

- [x] **Step 1: pin today.** Before touching `src/`, write the no-run sha256 pin test (a design with a fill rectangle and a satin column built from `shapesToRegions`, `underlay: true`, fabric `jersey`; hash of `JSON.stringify(d.stitches)`), run it, record the hash it prints from this tree (= origin/main), and paste it into the assertion.
- [x] **Step 2: failing tests** in `test/manualrun.test.js`:
  1. `runAlongPath([(0,0),(100,0)], {stitchLenPx: 10, passes: 1})` → 11 stations, x = 0,10,…,100; last is exactly (100,0).
  2. Remainder: path length 104, step 10 → last station exactly the end vertex, no stitch shorter than 5 px.
  3. `passes: 3` → `3n − 2` points; forward stations equal pass 1; the middle pass is pass 1 reversed; ends on the last vertex.
  4. An L-shaped path: every station lies on the path (distance < 1e-9).
  5. Engine: a straight run region (`path` 300 px, `outer` = hairline ring, `tierOverride: "fill"`) with `underlay: true`, a fabric and `outline: true` → `d.runs.map(r => r.kind)` is exactly `["run"]`; stitch count ≈ `3 × (L_mm / 0.73)` ±3; `nFill`, `nSatin` both 0.
  6. Defaults: `passes: 2, stitchLenMm: -1` sews the same stitches as `passes: null, stitchLenMm: null`, which equal `passes: 3, stitchLenMm: 0.73`.
  7. A path whose final length is under 2.2 mm → no stitches for that shape and its `shapeOutlines` entry is `dropped: true`.
  8. A hairpin path (0,0)→(200,0)→(0,0) sews (count > 0), all stations on y = path y.
  9. `sewAs: { kind: "run" }` with no `path` sews as the plain fill it always did (deep-equal to no `sewAs`).
- [x] **Step 3: run** `node --test test/manualrun.test.js` → the engine tests fail (no `runAlongPath`).
- [x] **Step 4: implement.** `runAlongPath` + `RUN_MIN_LOOP_MM` in `fill.js` beside `runningOutline`, both in the API object. In `digitize.js`, at the top of the per-shape body (after `rings`/`angle` are known): `const runSew = (shape.sewAs && shape.sewAs.kind === "run" && Array.isArray(shape.sewAs.path) && shape.sewAs.path.length >= 2) ? shape.sewAs : null;` then: `if (runSew) thin = false;` gate `fillColumns && !thin && !runSew`, `if (useUnderlay && !runSew)`, the top-stitch `try` takes `runSew` first, `if (o.outline && !runSew)`. Comment each gate with spec §2 / ruling 1.
- [x] **Step 5: run** the new file and the whole engine suite to a log → zero failures, the pin unchanged. `node app/scripts/copy-engine.mjs`.
- [x] **Step 6: commit** — `Engine: a region with an authored path sews a run along it (runAlongPath), and nothing else of it`.

---

### Task 2: The run record, its ring, its validity, and the conversion

**Files:** Modify `app/src/lib/manualShapes.js`; Test `app/src/lib/manualShapes.spec.js`, `app/src/lib/flow.spec.js`, `app/src/lib/projectFile.spec.js`.

**Interfaces — produces (manualShapes.js):**
- `isRun(shape)`; `isOpenShape(shape)` = column or run.
- `RUN_HAIRLINE_PX = 1`.
- `runIssues(shape) → string[]`: `A line needs at least 2 points.`; too-many-points (existing string); `This line is too short to sew.` (flattened length ≤ `MIN_COLUMN_LEN_PX`). No self-crossing check.
- `runPath(shape) → [{x,y}]` = `flattenShape(points, curves, false)`.
- `shapeRing(run)` = `railsFromSpine(runPath, RUN_HAIRLINE_PX).ring` or `[]`.
- `shapeProblems` / `isSewableShape` handle a run (a stray `cutOut` on a run is ignored).
- `resolveCutOuts`, `withCutOut`: a run takes no part, like a column.
- `manualShapeName` → `Shape N · Line`.
- `shapesToRegions`: a valid run emits `{ id, outer: hairline ring, holes: [], tierOverride: "fill", angleOverride: null, sewAs: { kind: "run", path, passes: shape.passes ?? null, stitchLenMm: shape.stitchLenMm ?? null } }`.
- `runToColumn(shape, widthPx) → column` = `{ id, kind: "column", points, curves, colorRgb, widthPx }` (no passes/stitchLenMm); returns `shape` unchanged when not a run or `widthPx` not > 0. `columnToRun(shape) → run` = `{ id, kind: "run", points, curves, colorRgb }` (no widthPx/taperMm); unchanged when not a column. `points`/`curves` are copied (new arrays/objects, same values).

- [x] **Step 1: failing tests:** `isRun`/`isOpenShape`; `runIssues` for each message, and `[]` for a hairpin and for a figure-8 that crosses itself; `shapeRing(run)` is a closed ring whose area ≈ length × 1 px; `shapesToRegions` on [rectangle, run] — the rectangle's region deep-equal to `shapesToRegions([rectangle])`'s, the run's region as specified, with a curved run's `path` equal to `flattenShape(points, curves, false)`; `resolveCutOuts` never picks a run as a parent; `manualShapeName`; `isSewableShape` (2-point run true; 1-point false); `runToColumn` → `columnToRun` round-trip deep-equals the original spine (points and curves) and does not share array identity; `flow.isSewable` on an element holding only a run; projectFile round-trips a run with `kind`, `passes`, `stitchLenMm`.
- [x] **Step 2: run** → fail. **Step 3: implement.** **Step 4:** suite to a log, zero failures.
- [x] **Step 5: commit** — `manualShapes: a run is an open path with a hairline proxy ring; run <-> column swaps fields, never the spine`.

---

### Task 3: Node editing an open run, and conversion through the re-fit rule

**Files:** Modify `app/src/lib/fieldNodeEdit.js`; Test `app/src/lib/fieldNodeEdit.spec.js`.

**Interfaces — produces:**
- `authoredInFieldMm`, `removeAnchor`, `flatBBox`: open-ness from `isOpenShape` (a run has n − 1 segments and a floor of 2); rails only for a column.
- `convertOpenShape(element, fit, shapeId, to, garment?) → patch | { error }`: `to === "column"` → `runToColumn(run, COLUMN_DEFAULT_MM / fit.mmPerPx)` (with no usable fit: `newColumnWidthPx` with `garment`, else nominal `COLUMN_DEFAULT_MM × PX_PER_MM`); `to === "run"` → `columnToRun`. Refuses a column that would fold (`shapeProblems`' first string). Commits through `refitShapesPatch` when the fit is usable, else `{ shapes }`.

- [x] **Step 1: failing tests**, through the REAL engine as the file's invariance tests do: (a) element [rectangle, run]; drag a run anchor via `editedElementPatch`; regenerate — the rectangle's outline moves ≤ the existing tolerance, `fit.mmPerPx` held to 1e-12; (b) `convertOpenShape(…, "column")` then regenerate — the rectangle has not moved, `columnWidthMm` reads 4.0 ± 0.01, the region now sews satin; (c) then `"run"` — the spine (points, curves) deep-equals the original run's and it sews a run again; unit: `removeAnchor` on a 2-point run → null; on a run's end anchor drops only that end's curve; `authoredInFieldMm(run)` has n − 1 handles and no `rails`.
- [x] **Step 2–4:** fail → implement → suite to a log, zero failures.
- [x] **Step 5: commit** — `fieldNodeEdit: a run edits open, and converts to a column and back through the re-fit rule`.

---

### Task 4: The popover for a run, and the conversion actions

**Files:** Modify `app/src/lib/shapePopover.js`, `app/src/ui/EmbroideryField.svelte`; Test `app/src/lib/shapePopover.spec.js`.

**Interfaces:**
- `runDefaults() → { passes, stitchLenMm }` from `globalThis.EMB.LETTERING_GUARDS` (`BEAN_PASSES`, `BEAN_STITCH_MM`); nulls when the engine is not loaded.
- `popoverModel` for a run: name `Shape N · Line`; rows `[ color, { key: "passes", kind: "choice", label: "Passes", value: String(passes), options: [{ "1", "Single run" }, { "3", "Bean (3 passes)" }] }, { key: "stitchLenMm", kind: "number", label: "Stitch length", value, hint: "mm", step: 0.1, min: 0.5, note? }, { key: "toColumn", kind: "action", label: "Make it a column" }, editPoints, delete ]`. The note is `Shorter than 2.2 mm — it will not sew.` with `warn: true` when the fit is known and the path's sewn length < `EMB.RUN_MIN_LOOP_MM`. A column gains `{ key: "toRun", kind: "action", label: "Make it a line" }` before Edit points.
- `popoverPatch`: `passes` → `{ passes: 1|3 }`; `stitchLenMm` → number ≥ 0.5 or null (blank = default); both null on a non-run; `toColumn`/`toRun` are actions, not patches (null).
- `ShapePopover.svelte`: `stitchLenMm` commits on `change` like `widthMm`.
- `EmbroideryField.svelte`: `onPopAction` handles `toColumn`/`toRun` through `convertOpenShape` (error → `shapeEditError`); `anchorFloor`/`anchorFloorMessage`, `drawAuthoredNodes`' `open`, and every `hitAuthored(..., closed)` use `isOpenShape`; the run message is `A line needs at least 2 points.`.

- [x] Steps: failing spec tests (run rows; defaults read off a stubbed `EMB`; patches; a column's `toRun` row; the short note) → implement → spec + suite to a log → `npx vite build` EXIT 0 → commit `Popover: a line shows its passes and stitch length, and a line and a column convert into each other`.

---

### Task 5: Line mode on the side canvas

**Files:** Modify `app/src/ui/ManualPanel.svelte`; Test `app/src/ui/ManualPanel.spec.js`.

Behaviour:
1. Mode strip `Shape | Hole | Column | Line`. Line mode: the hint string; a click always places a point (never selects); a click near the start does not finish; double-click / Enter / Finish finishes with ≥ 2 points; draft issues via `runIssues`.
2. `finishShape` in Line mode creates `{ id, kind: "run", points, curves, colorRgb }` (no passes/stitchLenMm: the engine's defaults stand).
3. Render: a run draws as its flattened path stroked in its colour (2.5 px, Dim applies), label `LINE` at the path's middle point when not dimmed. Hit-test: a run is hit within `CLOSE_RADIUS_PX` of its path (`nearestSegmentIndex(..., false)`), since its ring is a hairline.
4. List row `Shape N · Line`. Assign box for a run: Dim, Color, Passes (two buttons), Stitch length (number, mm), `Make it a column` button. A column's assign box gains `Make it a line`. Conversion goes through `convertOpenShape` with the panel's `fit` and `garment`.

- [x] Steps: failing spec tests (four mode buttons; 2 clicks + double-click in Line mode → one `kind: "run"` shape, no `stitchType`/`widthPx`; near-start click adds a point; list row; assign rows; `Make it a column` → the shape becomes a column with the same points; existing Shape/Hole/Column tests unmodified) → implement → suite + `vite build` → commit `ManualPanel: Line mode — draw an open path, sew a run; convert to a column and back`.

---

### Task 6: Read it back from the DST

**Files:** Create `test/manualrun-dst.test.js`.

- [x] A bent 3-point line (60 × 30 mm design) through the Studio's own `shapesToRegions` (dynamic import of `app/src/lib/manualShapes.js`) → `buildQualityDesign` → `encodeDST` → written to a temp file → `tools/crossval_decode.py` via `tools/crossval-stitch-formats.mjs`'s `resolvePython`/`pyDecode` (skip locally without pystitch, FAIL on CI as that file does). Assert in mm: every decoded STITCH lies within 0.15 mm of the path (path mapped through `d.fit`); the first and last stitches are within 0.15 mm of the path's ends; the summed stitch length is 3 × path length ± 2 %; the median stitch is 0.73 ± 0.1 mm; zero TRIMs between the run's stitches.
- [x] Run → green against the venv (`EXIT=0`, test not skipped); commit `test: a drawn line read back from its DST by pystitch, in mm`.

---

### Task 7: End to end, screenshot, docs

**Files:** Create `app/e2e/manual-run.spec.js`, `docs/screens/manual-run-2026-10-11.png`; Modify `docs/scope/5-review-manual-editing.md`, this plan (status block).

e2e (helpers copied from `manual-column.spec.js`):
- (a) Line mode: draw a 3-point line, double-click → row `Shape 1 · Line`; the caption shows stitches; a pixel on the path inside the fabric is thread; the stitched box is far wider than it is tall.
- (b) Click it on the hoop → popover `Shape 1 · Line` with a Passes select reading `3`; set `Single run` → the stitch count drops to about a third (0.25–0.45 ×).
- (c) `Make it a column` → the side panel row reads `Shape 1 · Column`, its Width reads 4.0; `Make it a line` → `Shape 1 · Line`, and the stitch count equals (a)'s bean count exactly: conversion drops `passes` (back to the default) and leaves the spine as drawn.
- Prove (a) red by making `shapesToRegions` skip runs, then restore.
- Screenshot: a curved line on the hoop at 1440×900 → `docs/screens/manual-run-2026-10-11.png`; open it and say what it shows.
- Run only: `npx playwright test e2e/manual-run.spec.js e2e/manual-column.spec.js`.

Docs: a dated section in `docs/scope/5-review-manual-editing.md` (what shipped; rulings 1, 4, 6, 7, 8 as built; the one new constant; what is not built — ties, taper, closed ↔ open). Plan: tick every box, add a "Status" block listing departures.

- [x] Commit — `e2e + docs: a drawn line proven end to end, and run <-> column on the record`.

---

## Done means

- Engine and Studio suites green; `manual-run.spec.js` green; DST read-back green against pystitch; screenshot in `docs/screens/`.
- PR ready for review against `main`, auto-merge armed while `BLOCKED`.

## Not in this plan

Lock stitches (ruling 7 — its own PR with the bill measured); taper; closed ↔ open conversion; drawing on the field; trace import emitting runs.

## Status 2026-10-11 — every task done

Built in one session on `claude/manual-open-runs` (PR #840). Where the build departed from the text above, and why:

- **Two pre-existing assertions changed on purpose.** `shapePopover.spec.js`'s column row list gained `toRun` ("Make it a line", ruling 8). `ManualPanel.spec.js`'s mode strip now has a fourth button, `Line` (ruling 4). Both are the spec's own additions; no other existing test was touched.
- **Task 6's DST numbers** (bent line, one curved segment): 316 stitches, 76.53 mm path, worst 0.058 mm off it, 229.90 mm laid, median 0.721 mm, no trims.
- **Task 7 screenshot** was taken once, by hand, and is not a test. A skip-gated screenshot test (`EMB_SHOTS=1`) turned CI's `studio-e2e` red: that job fails on ANY skipped spec, reading a skip as a failed service bootstrap. It was removed.
- **Merging main brought configurator PR 3 (#845):** the drawing tools now sit behind "Advanced ›", so the spec calls `openAdvanced(page)` as `manual-column.spec.js` does.
- **Task 7 (a) was proven red**: with `shapesToRegions` skipping runs it fails (no `Shape 1 · Line` row with stitches). It was green again once restored.
- **Docs**: the area doc `docs/scope/5-review-manual-editing.md` carries the dated section. `MASTER_SCOPE.md` / `COOKBOOK.md` are left for an `update-master-scope` pass (the foreman's rule for this run).
