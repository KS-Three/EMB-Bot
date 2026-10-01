# Studio Configurator — PR 1: Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four-step wizard (`StepNav`, `STEPS`, `stepHistory`, the "create" review screen) with one right-hand scrolling panel, a sticky summary bar, and a Download sheet — and migrate every e2e spec off the Next/Next/Next walk.

**Architecture:** `App.svelte` stops keying the panel off `step`. It renders `Configurator.svelte` (a layout shell with a header, a start control and two named slots — `design`, `garment`) whose foot is `SummaryBar.svelte`; the bar's Download button opens `DownloadSheet.svelte`, which wraps the old review recap, `QualityReport` and the unchanged `DownloadStep`. Templates move into `ProjectsDrawer`. The panel moves to the right of the field. Garment content in this PR is the EXISTING `GarmentStep` tiles inside the new section (ugly, correct — the pill row is PR 2).

**Tech Stack:** Svelte 5, Vitest + `@testing-library/svelte` (jsdom) for units, `@playwright/test` for e2e. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-30-studio-configurator-design.md` — §2 (structure), §7 (tests), §8 (phasing). Read §2.1–2.5 before starting.

## Global Constraints

- `app/` only. `src/*.js` (the engine) is never touched.
- Every `data-testid`, button name and class inside `DownloadStep.svelte`, `ContentStep.svelte`'s element rows and `EmbroideryField.svelte` stays as-is — e2e locators depend on them.
- `isSewable` in `lib/flow.js` stays exported with its current body.
- `<h2>Download</h2>` in `DownloadStep.svelte` is the sheet's heading; e2e asserts `getByRole("heading", { name: "Download", exact: true })`.
- The summary bar's button is the ONLY control whose accessible name is exactly `Download`.
- Browser Back with the sheet open closes the sheet; with it closed, Back leaves the Studio (no step entries remain).
- Contrast: no new colour tokens in this PR; the theme pass is PR 4.
- Run Studio units from `app/`: `npx vitest run <file>`; e2e: `npx playwright test <file>` (needs the digitizer venv for the service-driven specs; the ones this plan touches that need it are marked).
- Commit after every task. Branch: `claude/configurator-structure`, cut from `main` in a worktree (`superpowers:using-git-worktrees`).
- PR opened ready-for-review with auto-merge armed while `mergeable_state` is `blocked` (CLAUDE.md). Budget 70 min for the `digitizer` job.

---

## File map

| File | Change | Responsibility |
|------|--------|----------------|
| `app/src/lib/flow.js` | modify | keep `isSewable` only |
| `app/src/lib/flow.spec.js` | modify | tests become `isSewable` tests |
| `app/src/lib/stepHistory.js`, `.spec.js` | delete | no steps, no step history |
| `app/src/App.stepHistory.spec.js` | delete | guarded a removed mechanism |
| `app/src/ui/StepNav.svelte`, `.spec.js`, `.testHarness.svelte` | delete | the stepper |
| `app/src/ui/SummaryBar.svelte` (+ `.spec.js`, `.testHarness.svelte`) | create | figures + Download button |
| `app/src/ui/DownloadSheet.svelte` (+ `.spec.js`, `.testHarness.svelte`) | create | dialog: recap, QualityReport, DownloadStep |
| `app/src/ui/Configurator.svelte` (+ `.spec.js`) | create | panel shell: header, start control, slots, bar |
| `app/src/ui/GarmentStep.svelte` | modify | drop TemplateRow/Hint/h2; add `<h3>Garment</h3>` |
| `app/src/ui/GarmentStep.spec.js` | modify | drop the template hint stub lines |
| `app/src/ui/ContentStep.svelte` | modify | drop `<h2>What are you making?</h2>` |
| `app/src/ui/ProjectsDrawer.svelte` | modify | host `TemplateRow` |
| `app/src/App.svelte` | modify | remove step machinery; render Configurator + sheet |
| `app/src/ui/theme.css` | modify | panel right; `.summarybar`, `.sheet`; drop `.stepnav*`, `.topbar-download`, `.createstep` |
| `app/e2e/helpers.js` | create | `startStudio`, `typeText`, `pickGarment`, `pickTemplate`, `openDownload` |
| `app/e2e/*.spec.js` (24 files) | modify | walk via helpers |
| `app/e2e/wizard-smoke.spec.js` → `configurator-smoke.spec.js` | rename+modify | |
| `MASTER_SCOPE.md`, `docs/scope/3-studio-app-wizard.md` | modify | area 3 status |

---

### Task 1: `flow.js` keeps only `isSewable`

**Files:**
- Modify: `app/src/lib/flow.js`
- Modify: `app/src/lib/flow.spec.js`

**Interfaces:**
- Produces: `isSewable(el) → boolean` (unchanged body). `STEPS`, `canAdvance`, `nextStep`, `prevStep` no longer exist — later tasks must not import them.

- [ ] **Step 1: Rewrite the spec to name `isSewable` directly**

Replace the whole of `app/src/lib/flow.spec.js` with:

```js
import { expect, test } from "vitest";
import { isSewable } from "./flow.js";

test("a text element is sewable once it has non-blank text", () => {
  expect(isSewable({ type: "text", text: "" })).toBe(false);
  expect(isSewable({ type: "text", text: "   " })).toBe(false);
  expect(isSewable({ type: "text", text: "EMB" })).toBe(true);
});

test("an image element is sewable only via its runtime _hasImage flag", () => {
  expect(isSewable({ type: "image" })).toBe(false);
  expect(isSewable({ type: "image", _hasImage: true })).toBe(true);
});

test("design and digitized elements gate on their baked content, not _hasImage", () => {
  expect(isSewable({ type: "design", _hasImage: true })).toBe(false);
  expect(isSewable({ type: "design", dstBase64: "AAAA" })).toBe(true);
  expect(isSewable({ type: "digitized", _hasImage: true })).toBe(false);
  expect(isSewable({ type: "digitized", result: { ok: true } })).toBe(true);
});

test("a manual element needs at least one valid completed shape", () => {
  expect(isSewable({ type: "manual", shapes: [] })).toBe(false);
  expect(isSewable({ type: "manual", shapes: [{ points: [{ x: 0, y: 0 }, { x: 10, y: 0 }] }] })).toBe(false);
  expect(isSewable({ type: "manual", shapes: [{ points: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }] }] })).toBe(true);
});

test("a preset shape element is sewable from birth", () => {
  expect(isSewable({ type: "shape", kind: "circle", params: {} })).toBe(true);
});

test("null is not sewable", () => {
  expect(isSewable(null)).toBe(false);
});
```

(The manual rule is `isValidShape` from `manualShapes.js`: at least 3 points and no self-intersection, so the two-point case fails and the triangle passes.)

- [ ] **Step 2: Run it — expect the old exports to still pass, then the new file to pass**

Run: `cd app && npx vitest run src/lib/flow.spec.js`
Expected: PASS (nothing removed yet).

- [ ] **Step 3: Remove the step exports from `flow.js`**

Delete `STEPS`, `canAdvance`, `nextStep`, `prevStep` and the header comment about "guided steps". Keep the `isValidShape` import and `isSewable` with its comment. File ends after `isSewable`.

- [ ] **Step 4: Run the spec again**

Run: `cd app && npx vitest run src/lib/flow.spec.js`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/flow.js app/src/lib/flow.spec.js
git commit -m "studio: flow.js keeps only isSewable — the step machinery goes"
```

(`App.svelte` is now broken at import time; Task 6 repairs it. Do not run the full suite until then.)

---

### Task 2: `SummaryBar.svelte`

**Files:**
- Create: `app/src/ui/SummaryBar.svelte`
- Create: `app/src/ui/SummaryBar.testHarness.svelte`
- Create: `app/src/ui/SummaryBar.spec.js`

**Interfaces:**
- Props: `sewFacts: Array<{label, value}>` (the rows `lib/estimate.js sewSummary` returns — labels `Size`, `Stitches`, `Run time`, `Thread changes`, `Trims`, `Thread`), `colorCount: number`, `canDownload: boolean`.
- Three figures, not the spec's four: `Run time`'s value is `~6 min at 650 spm`, too long for a 320 px bar; it stays in the sheet's recap. Decision recorded here so PR 4 does not re-open it.
- Dispatches: `download` (no detail) when the button is clicked.
- Markup contract: `<div class="summarybar">` containing `.summarybar-figures` with one `.summarybar-figure` per figure (`<b>` value, `<span>` label), and `<button class="primary summarybar-download">Download</button>`.

- [ ] **Step 1: Write the harness**

`app/src/ui/SummaryBar.testHarness.svelte`:

```svelte
<script>
  import SummaryBar from "./SummaryBar.svelte";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  export let onDownload = () => {};
</script>

<SummaryBar {sewFacts} {colorCount} {canDownload} on:download={onDownload} />
```

- [ ] **Step 2: Write the failing spec**

`app/src/ui/SummaryBar.spec.js`:

```js
// @vitest-environment jsdom
import { expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./SummaryBar.testHarness.svelte";

const FACTS = [
  { label: "Size", value: "76 × 18 mm" },
  { label: "Stitches", value: "3,412" },
  { label: "Run time", value: "~6 min at 650 spm" },
  { label: "Trims", value: "2" },
];

test("shows size, stitches and colours from the rows it is given", () => {
  render(Harness, { sewFacts: FACTS, colorCount: 1, canDownload: true });
  expect(screen.getByText("76 × 18 mm")).toBeInTheDocument();
  expect(screen.getByText("3,412")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
  expect(screen.getByText(/colou?r$/)).toBeInTheDocument();
});

test("pluralises colours", () => {
  render(Harness, { sewFacts: FACTS, colorCount: 3, canDownload: true });
  expect(screen.getByText("colors")).toBeInTheDocument();
});

test("prints a dash for every figure when nothing sews", () => {
  render(Harness, { sewFacts: [], colorCount: 0, canDownload: false });
  const dashes = screen.getAllByText("—");
  expect(dashes.length).toBe(3);
});

test("the Download button is disabled with a reason until the design can sew", () => {
  render(Harness, { sewFacts: [], colorCount: 0, canDownload: false });
  const btn = screen.getByRole("button", { name: "Download" });
  expect(btn).toBeDisabled();
  expect(btn).toHaveAttribute("title", "Add text or a logo first");
});

test("clicking Download dispatches download", async () => {
  const onDownload = vi.fn();
  render(Harness, { sewFacts: FACTS, colorCount: 1, canDownload: true, onDownload });
  await fireEvent.click(screen.getByRole("button", { name: "Download" }));
  expect(onDownload).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 3: Run it to see it fail**

Run: `cd app && npx vitest run src/ui/SummaryBar.spec.js`
Expected: FAIL — cannot resolve `./SummaryBar.svelte`.

- [ ] **Step 4: Write the component**

`app/src/ui/SummaryBar.svelte`:

```svelte
<script>
  // The panel's sticky foot (spec §2.3): three figures the customer keeps
  // glancing at while editing, and the one Download. Figures come from the
  // same rows the review recap used (lib/estimate.js sewSummary), so the
  // bar and the sheet can never disagree.
  import { createEventDispatcher } from "svelte";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  const d = createEventDispatcher();

  const DASH = "—";
  function row(label) {
    const r = (sewFacts || []).find((x) => x.label === label);
    return r ? r.value : DASH;
  }
  $: size = row("Size");
  $: stitches = row("Stitches");
  $: colors = colorCount > 0 ? String(colorCount) : DASH;
  $: colorLabel = colorCount === 1 ? "color" : "colors";
</script>

<div class="summarybar">
  <div class="summarybar-figures">
    <div class="summarybar-figure"><b>{size}</b><span>size</span></div>
    <div class="summarybar-figure"><b>{stitches}</b><span>stitches</span></div>
    <div class="summarybar-figure"><b>{colors}</b><span>{colorLabel}</span></div>
  </div>
  <button
    type="button"
    class="primary summarybar-download"
    disabled={!canDownload}
    title={canDownload ? "" : "Add text or a logo first"}
    on:click={() => d("download")}
  >Download</button>
</div>
```

- [ ] **Step 5: Run the spec**

Run: `cd app && npx vitest run src/ui/SummaryBar.spec.js`
Expected: PASS, 5 tests.

- [ ] **Step 6: Commit**

```bash
git add app/src/ui/SummaryBar.svelte app/src/ui/SummaryBar.testHarness.svelte app/src/ui/SummaryBar.spec.js
git commit -m "studio: SummaryBar — size, stitches, colours and the one Download"
```

---

### Task 3: `DownloadSheet.svelte`

**Files:**
- Create: `app/src/ui/DownloadSheet.svelte`
- Create: `app/src/ui/DownloadSheet.testHarness.svelte`
- Create: `app/src/ui/DownloadSheet.spec.js`

**Interfaces:**
- Props: `project`, `runtime`, `digitizerHealth`, `sewnColors`, `summaryRows: Array<{label, value}>` (the recap rows — garment, hoop, `designSummary` rows and, when `!qualityIsTheWholeDesign`, `sewFacts`; App assembles them), `qualityEntries`, `qualityPartial: boolean`, `ready: boolean`.
- Dispatches: `close`, `credits` (forwarded from `DownloadStep`, detail = the anchor element).
- Markup contract: `<div class="sheet" role="dialog" aria-label="Download">`; heading `Ready to stitch` / `Nothing to stitch yet`; `<dl class="summary">` (e2e reads it); `QualityReport`; `DownloadStep`; a close button named `Close`. Escape dispatches `close`.

- [ ] **Step 1: Write the harness**

`app/src/ui/DownloadSheet.testHarness.svelte`:

```svelte
<script>
  import DownloadSheet from "./DownloadSheet.svelte";
  export let project;
  export let runtime = { flats: {}, workImages: {} };
  export let summaryRows = [];
  export let qualityEntries = [];
  export let qualityPartial = false;
  export let ready = true;
  export let onClose = () => {};
</script>

<DownloadSheet
  {project}
  {runtime}
  digitizerHealth={null}
  sewnColors={null}
  {summaryRows}
  {qualityEntries}
  {qualityPartial}
  {ready}
  on:close={onClose}
/>
```

- [ ] **Step 2: Write the failing spec**

`app/src/ui/DownloadSheet.spec.js`. `DownloadStep` loads the engine global at module time exactly the way `GarmentStep.spec.js` documents, so the same `beforeAll` ordering applies — and it calls `generateAll` and the exporters on mount, which `DownloadStep.spec.js` mocks; the same two mocks go here so the sheet spec tests the sheet, not the engine:

```js
// @vitest-environment jsdom
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";
import { defaultProject } from "../lib/project.js";

vi.mock("../lib/generate.js", () => ({
  generateAll: () => ({ combined: { widthMM: 50, heightMM: 50, colors: [], blocks: [] } }),
}));
vi.mock("../lib/exporters.js", () => ({
  exportDesignPreferService: async (design, format) => ({
    bytes: new Uint8Array([1, 2, 3]), filename: `design.${format}`, mime: "application/octet-stream", via: "browser",
  }),
  exportWorksheetPDF: async () => {},
  exportPNG: async () => ({ blob: new Blob(), filename: "design.png", mime: "image/png" }),
  isServiceOnlyFormat: (fmt) => ["jef", "xxx", "vp3"].includes(fmt),
}));

let Harness;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  require("../../../src/fabrics.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./DownloadSheet.testHarness.svelte"));
});

const ROWS = [
  { label: "Garment", value: "Left Chest" },
  { label: "Hoop", value: "4×4 in (suggested)" },
  { label: "Content", value: 'Text — "EMB"' },
];

test("is a dialog named Download with the Download heading inside", () => {
  render(Harness, { project: defaultProject(), summaryRows: ROWS });
  expect(screen.getByRole("dialog", { name: "Download" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Download", exact: true })).toBeInTheDocument();
});

test("recaps the rows it is given and says Ready to stitch", () => {
  render(Harness, { project: defaultProject(), summaryRows: ROWS, ready: true });
  expect(screen.getByRole("heading", { name: "Ready to stitch" })).toBeInTheDocument();
  expect(screen.getByText("Left Chest")).toBeInTheDocument();
  expect(screen.getByText('Text — "EMB"')).toBeInTheDocument();
});

test("says Nothing to stitch yet when the design cannot sew", () => {
  render(Harness, { project: defaultProject(), summaryRows: ROWS, ready: false });
  expect(screen.getByRole("heading", { name: "Nothing to stitch yet" })).toBeInTheDocument();
});

test("Escape and the close button both dispatch close", async () => {
  const onClose = vi.fn();
  render(Harness, { project: defaultProject(), summaryRows: ROWS, onClose });
  await fireEvent.click(screen.getByRole("button", { name: "Close" }));
  expect(onClose).toHaveBeenCalledTimes(1);
  await fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
  expect(onClose).toHaveBeenCalledTimes(2);
});
```

- [ ] **Step 3: Run it to see it fail**

Run: `cd app && npx vitest run src/ui/DownloadSheet.spec.js`
Expected: FAIL — cannot resolve `./DownloadSheet.svelte`.

- [ ] **Step 4: Write the component**

`app/src/ui/DownloadSheet.svelte`:

```svelte
<script>
  // The Download sheet (spec §2.4): what used to be the "create" review step
  // and the "download" step, one above the other, in a dialog the summary
  // bar opens. DownloadStep is rendered here UNCHANGED — its buttons,
  // test ids and the "Download" h2 are what every export e2e reads.
  import { createEventDispatcher, onMount } from "svelte";
  import QualityReport from "./QualityReport.svelte";
  import DownloadStep from "./DownloadStep.svelte";
  import Icon from "./Icon.svelte";
  export let project;
  export let runtime;
  export let digitizerHealth = null;
  export let sewnColors = null;
  export let summaryRows = [];
  export let qualityEntries = [];
  export let qualityPartial = false;
  export let ready = false;
  const d = createEventDispatcher();

  let el = null;
  onMount(() => { if (el) el.focus(); });

  function onKey(e) {
    if (e.key === "Escape") { e.stopPropagation(); d("close"); }
  }
</script>

<div class="sheet" role="dialog" aria-label="Download" tabindex="-1" bind:this={el} on:keydown={onKey}>
  <div class="sheet-head">
    {#if ready}
      <h2>Ready to stitch</h2>
    {:else}
      <h2>Nothing to stitch yet</h2>
    {/if}
    <button type="button" class="sheet-close" aria-label="Close" on:click={() => d("close")}><Icon name="close" size={16} /></button>
  </div>
  {#if !ready}
    <p>
      This design has no content the machine can sew. Close this and type some
      lettering, upload artwork, or draw a shape — the field updates live as you do.
    </p>
  {/if}
  <dl class="summary">
    {#each summaryRows as row}
      <div><dt>{row.label}</dt><dd>{row.value}</dd></div>
    {/each}
  </dl>
  <QualityReport entries={qualityEntries} partial={qualityPartial} />
  <DownloadStep {project} {runtime} {digitizerHealth} on:credits={(e) => d("credits", e.detail)} />
</div>
```

- [ ] **Step 5: Run the spec**

Run: `cd app && npx vitest run src/ui/DownloadSheet.spec.js`
Expected: PASS, 4 tests. If `DownloadStep` throws at mount for a reason the `GarmentStep.spec.js` preamble does not cover, copy the additional stub from `DownloadStep.spec.js`'s own `beforeAll` — do not weaken the assertions.

- [ ] **Step 6: Commit**

```bash
git add app/src/ui/DownloadSheet.svelte app/src/ui/DownloadSheet.testHarness.svelte app/src/ui/DownloadSheet.spec.js
git commit -m "studio: DownloadSheet — the review recap and DownloadStep as one dialog"
```

---

### Task 4: `Configurator.svelte` — the panel shell

**Files:**
- Create: `app/src/ui/Configurator.svelte`
- Create: `app/src/ui/Configurator.testHarness.svelte`
- Create: `app/src/ui/Configurator.spec.js`

**Interfaces:**
- Props: `title = "Your design"`, `subtitle` (string, e.g. `Left Chest · 4×4 in`), plus the three `SummaryBar` props (`sewFacts`, `colorCount`, `canDownload`).
- Slots: `design`, `garment`.
- Dispatches: `addelement` with detail `"text"` | `"artwork"` (the start control), `download` (forwarded from the bar).
- Markup: `<div class="cfg-body">` (the scroll area; App binds it for scroll-to-top) with `<h2>{title}</h2>`, `<p class="cfg-sub">`, `<div class="startseg" role="group" aria-label="Start with">` holding two buttons `Add text` / `Upload logo`, `<section class="cfg-section" data-section="design">`, `<section class="cfg-section" data-section="garment">`; then `<SummaryBar>`.

- [ ] **Step 1: Write the harness**

`app/src/ui/Configurator.testHarness.svelte`:

```svelte
<script>
  import Configurator from "./Configurator.svelte";
  export let subtitle = "Left Chest · 4×4 in";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  export let onAdd = () => {};
  export let onDownload = () => {};
</script>

<Configurator {subtitle} {sewFacts} {colorCount} {canDownload} on:addelement={onAdd} on:download={onDownload}>
  <p slot="design" data-testid="design-slot">design goes here</p>
  <p slot="garment" data-testid="garment-slot">garment goes here</p>
</Configurator>
```

- [ ] **Step 2: Write the failing spec**

`app/src/ui/Configurator.spec.js`:

```js
// @vitest-environment jsdom
import { expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./Configurator.testHarness.svelte";

test("renders the title, subtitle and both slots in order", () => {
  render(Harness, { subtitle: "Tote · 8×8 in" });
  expect(screen.getByRole("heading", { name: "Your design" })).toBeInTheDocument();
  expect(screen.getByText("Tote · 8×8 in")).toBeInTheDocument();
  const design = screen.getByTestId("design-slot");
  const garment = screen.getByTestId("garment-slot");
  expect(design.compareDocumentPosition(garment) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

test("the start control dispatches addelement with text or artwork", async () => {
  const onAdd = vi.fn();
  render(Harness, { onAdd });
  await fireEvent.click(screen.getByRole("button", { name: "Add text" }));
  await fireEvent.click(screen.getByRole("button", { name: "Upload logo" }));
  expect(onAdd.mock.calls.map((c) => c[0].detail)).toEqual(["text", "artwork"]);
});

test("forwards the bar's download event", async () => {
  const onDownload = vi.fn();
  render(Harness, { canDownload: true, onDownload });
  await fireEvent.click(screen.getByRole("button", { name: "Download" }));
  expect(onDownload).toHaveBeenCalledTimes(1);
});

test("never renders a step number or a Next button", () => {
  render(Harness);
  expect(screen.queryByRole("button", { name: /^Next$/ })).toBeNull();
  expect(screen.queryByText(/^\d Garment|^\d Content|^\d Review|^\d Download/)).toBeNull();
});
```

- [ ] **Step 3: Run it to see it fail**

Run: `cd app && npx vitest run src/ui/Configurator.spec.js`
Expected: FAIL — cannot resolve `./Configurator.svelte`.

- [ ] **Step 4: Write the component**

`app/src/ui/Configurator.svelte`:

```svelte
<script>
  // The panel (spec §2.2): one scroll, sections in a fixed order, no step
  // numbers, and the summary bar pinned to the foot. This is a LAYOUT
  // shell — the sections' contents arrive through slots so App.svelte's
  // wiring of ContentStep and GarmentStep is unchanged.
  import { createEventDispatcher } from "svelte";
  import SummaryBar from "./SummaryBar.svelte";
  export let title = "Your design";
  export let subtitle = "";
  export let sewFacts = [];
  export let colorCount = 0;
  export let canDownload = false;
  // Bound by App so a project switch can scroll the panel back to the top.
  export let body = null;
  const d = createEventDispatcher();
</script>

<div class="cfg-body" bind:this={body}>
  <h2 class="cfg-title">{title}</h2>
  <p class="cfg-sub">{subtitle}</p>
  <div class="startseg" role="group" aria-label="Start with">
    <button type="button" class="startseg-btn" on:click={() => d("addelement", "text")}>Add text</button>
    <button type="button" class="startseg-btn" on:click={() => d("addelement", "artwork")}>Upload logo</button>
  </div>
  <section class="cfg-section" data-section="design"><slot name="design" /></section>
  <section class="cfg-section" data-section="garment"><slot name="garment" /></section>
</div>
<SummaryBar {sewFacts} {colorCount} {canDownload} on:download={() => d("download")} />
```

- [ ] **Step 5: Run the spec**

Run: `cd app && npx vitest run src/ui/Configurator.spec.js`
Expected: PASS, 4 tests.

- [ ] **Step 6: Commit**

```bash
git add app/src/ui/Configurator.svelte app/src/ui/Configurator.testHarness.svelte app/src/ui/Configurator.spec.js
git commit -m "studio: Configurator — the panel shell with slots and the summary bar"
```

---

### Task 5: Garment and Content sections, templates into the drawer

**Files:**
- Modify: `app/src/ui/GarmentStep.svelte:1-25, 100-108`
- Modify: `app/src/ui/GarmentStep.spec.js:24-40`
- Modify: `app/src/ui/ContentStep.svelte:165`
- Modify: `app/src/ui/ProjectsDrawer.svelte:186-190`

**Interfaces:**
- `GarmentStep` loses props `showTemplatesHint` and events `template`, `dismisshint`. Still dispatches `update`.
- `ProjectsDrawer` gains event `template` (detail = the template object `TemplateRow` picks).

- [ ] **Step 1: Trim `GarmentStep.svelte`**

Remove the imports of `TemplateRow` and `Hint`, the `showTemplatesHint` prop and its comment. Replace

```svelte
{#if showTemplatesHint}
  <Hint on:dismiss={() => d("dismisshint")}>One click starts a ready-made design.</Hint>
{/if}
<TemplateRow on:pick={(e) => d("template", e.detail)} />

<h2>What are you putting this on?</h2>
```

with

```svelte
<h3>Garment</h3>
```

- [ ] **Step 2: Trim `GarmentStep.spec.js`'s preamble**

Delete the two lines that exist only for `TemplateRow` (the `buildLetteringDesign` stub and the `fetch` rejection) and their comments. Run:

`cd app && npx vitest run src/ui/GarmentStep.spec.js`
Expected: PASS. If a test asserted the "What are you putting this on?" heading, change it to `Garment`.

- [ ] **Step 3: Drop the Content heading**

In `app/src/ui/ContentStep.svelte` delete the line `<h2>What are you making?</h2>`. Run:

`cd app && npx vitest run src/ui/ContentStep.reactivity.spec.js`
Expected: PASS.

- [ ] **Step 4: Host `TemplateRow` in the drawer**

In `app/src/ui/ProjectsDrawer.svelte` add `import TemplateRow from "./TemplateRow.svelte";` and, directly under the `+ New design` button:

```svelte
    <h3 class="drawer-templates-head">Start from a template</h3>
    <TemplateRow on:pick={(e) => d("template", e.detail)} />
```

- [ ] **Step 5: Commit**

```bash
git add app/src/ui/GarmentStep.svelte app/src/ui/GarmentStep.spec.js app/src/ui/ContentStep.svelte app/src/ui/ProjectsDrawer.svelte
git commit -m "studio: garment and content become sections; templates move to My designs"
```

---

### Task 6: `App.svelte` — remove the step machinery, render the configurator

**Files:**
- Modify: `app/src/App.svelte` (imports 5–6, 35, 38; lines 93–104, 130–131, 359, 400, 425–450, 583–590, 662–682, 795–801, 818–829 and its five callers 858/866/1018/1059/1062, 1068, 1085–1091, 1132–1234)
- Delete: `app/src/lib/stepHistory.js`, `app/src/lib/stepHistory.spec.js`, `app/src/App.stepHistory.spec.js`, `app/src/ui/StepNav.svelte`, `app/src/ui/StepNav.spec.js`, `app/src/ui/StepNav.testHarness.svelte`

**Interfaces:**
- Consumes: `Configurator` (Task 4), `DownloadSheet` (Task 3), `isSewable` (Task 1), `ProjectsDrawer`'s `template` event (Task 5).
- Produces: `sheetOpen` state; `openSheet()` / `closeSheet()`; `summaryRows` reactive array.

- [ ] **Step 1: Delete the files**

```bash
git rm app/src/lib/stepHistory.js app/src/lib/stepHistory.spec.js app/src/App.stepHistory.spec.js app/src/ui/StepNav.svelte app/src/ui/StepNav.spec.js app/src/ui/StepNav.testHarness.svelte
```

- [ ] **Step 2: Imports**

Replace lines 5–6 with `import { isSewable } from "./lib/flow.js";`. Replace the `StepNav` import with `import Configurator from "./ui/Configurator.svelte";` and add `import DownloadSheet from "./ui/DownloadSheet.svelte";`.

- [ ] **Step 3: Replace the step state with the sheet state**

Delete lines 93–104 (`let step`, the `stepHistory` block and `stepHistory.start(step)`). In their place:

```js
  // The Download sheet (spec §2.4). The only browser-history entry the
  // Studio pushes: opening pushes one, so the phone's Back gesture closes
  // the sheet instead of leaving the app; closing pops it. No URL changes.
  let sheetOpen = false;
  const SHEET_STATE = { embSheet: "download" };
  function openSheet() {
    if (sheetOpen) return;
    sheetOpen = true;
    history.pushState(SHEET_STATE, "");
    checkDigitizer();
  }
  function closeSheet() {
    if (!sheetOpen) return;
    if (history.state && history.state.embSheet === "download") history.back();
    else sheetOpen = false;
  }
  function onPopState() {
    sheetOpen = !!(history.state && history.state.embSheet === "download");
  }
```

Note `history` here is `window.history`; the project's undo history is the `const history = createHistory(project)` declared at line ~210 — that shadows it. **Rename the sheet helpers to use `window.history` explicitly** (`window.history.pushState`, `window.history.state`, `window.history.back()`) so the shadowing is harmless.

- [ ] **Step 4: Fix the reactive lines that read `step`**

- Line 130–131: `$: if (panelBody) { currentId; panelBody.scrollTop = 0; }` (drop `step`).
- Line 359: replace with `onMount(checkDigitizer);` (import `onMount` from `svelte` if not already imported) — the sheet re-checks on open (Step 3).
- Line 400: `$: readyToStitch = project.elements.some(isSewable);`
- Lines 425–450: delete `templatesShown` and its `dismissHint` branch; `eligibleHints` becomes

```js
  $: eligibleHints = [
    dragFieldShown && hasStitches ? "drag-field" : null,
    addElementsShown && project.elements.length < 2 ? "add-elements" : null,
  ].filter(Boolean);
```

  and delete `$: showTemplatesHint = …`.

- [ ] **Step 5: Remove the step moves**

- Line 589: delete `if (step !== "content" && canAdvance("garment", project)) stepHistory.go("content");` — the panel always shows the Design section now, so the orphan problem that line fixed cannot recur.
- Lines 681 (`stepHistory.go("content")` in `pickTemplate`): delete. Add `drawerOpen = false;` there instead.
- Lines 795–801 (`function go(dir)`): delete.
- `enterProject(id, proj, name, targetStep)`: drop the fourth parameter and the `stepHistory.replace(targetStep)` line with its comment; update the five callers to three arguments.
- Line 1068: `<svelte:window on:keydown={onGlobalKey} on:popstate={onPopState} />`.
- Lines 1085–1091: delete the `topbar-download` button.
- `ProjectsDrawer`: add `on:template={(e) => pickTemplate(e.detail)}`.

- [ ] **Step 6: Assemble the recap rows**

Beside `sewFacts` add:

```js
  // The rows the Download sheet recaps — one list, built here, so the
  // sheet is a renderer and never re-derives what the app already knows.
  $: summaryRows = [
    { label: "Garment", value: readable(project.garmentId) },
    { label: "Hoop", value: hoopInEffect.hoop.label + (hoopInEffect.suggested ? " (suggested)" : "") },
    ...designSummary(project, sewnColors),
    ...(qualityIsTheWholeDesign ? [] : sewFacts),
  ];
  $: subtitle = `${readable(project.garmentId)} · ${hoopInEffect.hoop.label}`;
```

- [ ] **Step 7: Replace the panel template (lines 1132–1234)**

```svelte
<div class="studio">
  <section class="field">
    <EmbroideryField … (unchanged block from the current file) … />
  </section>

  <aside class="panel">
    <Configurator
      {subtitle}
      {sewFacts}
      colorCount={sewnColors ? sewnColors.length : 0}
      canDownload={readyToStitch}
      bind:body={panelBody}
      on:addelement={(e) => onAddElement(e.detail)}
      on:download={openSheet}
    >
      <svelte:fragment slot="design">
        <ContentStep … (the exact prop/event block currently at lines 1145–1169) … />
      </svelte:fragment>
      <svelte:fragment slot="garment">
        <GarmentStep {project} {digitizerHealth} on:update={(e) => apply(e.detail)} />
      </svelte:fragment>
    </Configurator>
    {#if sheetOpen}
      <DownloadSheet
        {project}
        {runtime}
        {digitizerHealth}
        {sewnColors}
        {summaryRows}
        {qualityEntries}
        qualityPartial={!qualityIsTheWholeDesign}
        ready={readyToStitch}
        on:close={closeSheet}
        on:credits={(e) => openCredits(e.detail)}
      />
    {/if}
  </aside>
</div>
```

The `<section class="field">` now comes FIRST in the DOM (panel on the right). `SizePanel` was rendered on the review step; `ContentStep` already renders one for the selected element (line 335), so nothing is lost. Remove the now-unused `SizePanel` and `QualityReport` imports from `App.svelte` if nothing else references them.

- [ ] **Step 8: Build and run the unit suite**

Run: `cd app && npx vite build 2>&1 | tail -5` — Expected: build succeeds, no "unused export" warnings about `step`.
Run: `cd app && npm test 2>&1 | tail -15` — Expected: all green. Any spec that imported `STEPS`/`canAdvance` or rendered `StepNav` is one this plan already deleted or rewrote; a failure elsewhere is a real regression — fix, do not skip.

- [ ] **Step 9: Commit**

```bash
git add -A app/src
git commit -m "studio: the configurator replaces the four-step wizard"
```

---

### Task 7: `theme.css` — panel right, bar and sheet styles, dead rules out

**Files:**
- Modify: `app/src/ui/theme.css:284-297, 520-535, 1074-1125, 1919-1929, 2379-2513`

- [ ] **Step 1: Delete dead rules**

Remove `.topbar-download` + its hover (284–297), the `.createstep .summary*` block (1919–1929) and every `.stepnav*` rule (2379–2513, up to but not including the `/* ---- Motion` block). Keep `.stepnav-controls button`'s comment lesson by moving its "scope the neutral paint away from `.primary`" sentence to a comment above the new `.summarybar-download` rule.

- [ ] **Step 2: Panel on the right**

```css
.studio {
  display: grid;
  grid-template-columns: 1fr minmax(320px, 400px);
  height: calc(100vh - var(--topbar-h));
}

.panel {
  position: relative;          /* the sheet is absolutely positioned inside it */
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--surface);
  border-left: 1px solid var(--border);
}
```

Rename `.panel-body` to `.cfg-body` everywhere in the file (three rules: the scroll box, `h2`, `h3`). At 1400px: `.studio { grid-template-columns: 1fr minmax(400px, 460px); }`. In the 820px block, `.panel { border-left: none; border-top: 1px solid var(--border); … }`; `.field { order: -1 }` stays (harmless, field is already first).

- [ ] **Step 3: Configurator, bar and sheet**

Append before the Motion block:

```css
/* ---- Configurator (spec §2.2) ------------------------------------------ */
.cfg-title { text-align: center; margin-bottom: var(--space-1); }
.cfg-sub { text-align: center; color: var(--muted); font-size: var(--fs-sm); margin: 0 0 var(--space-5); }
.startseg {
  display: flex;
  padding: 3px;
  margin-bottom: var(--space-5);
  background: var(--bg);
  border-radius: var(--radius-s);
}
.startseg-btn {
  flex: 1;
  min-height: 36px;
  border: 0;
  border-radius: var(--radius-s);
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  cursor: pointer;
}
.startseg-btn:hover { color: var(--ink); }
.cfg-section + .cfg-section { margin-top: var(--space-6); padding-top: var(--space-5); border-top: 1px solid var(--border); }

/* The sticky foot: the figures a customer glances at while editing, and
   the one Download. `.primary`'s paint is left alone on purpose — the
   stepper's neutral `background: var(--surface)` once out-cascaded it and
   painted the app's only CTA white-on-white (2026-08-25); the bar sets no
   background on its button at all. */
.summarybar {
  padding: var(--space-3) var(--space-5) var(--space-4);
  background: var(--surface);
  border-top: 1px solid var(--border);
}
.summarybar-figures { display: flex; justify-content: space-between; margin-bottom: var(--space-3); }
.summarybar-figure { display: flex; flex-direction: column; font-size: var(--fs-2xs); color: var(--muted); }
.summarybar-figure b { font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--ink); }
.summarybar-download { width: 100%; min-height: 44px; font-size: var(--fs-md); }

/* The Download sheet: a dialog over the panel, panel-wide, full height. */
.sheet {
  position: absolute;
  inset: 0;
  z-index: 5;
  overflow-y: auto;
  padding: var(--space-5);
  background: var(--surface);
  box-shadow: var(--shadow-2);
  outline: none;
}
.sheet-head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }
.sheet-head h2 { margin: 0; }
.sheet-close { border: 0; background: transparent; color: var(--muted); cursor: pointer; padding: var(--space-1); }
.sheet-close:hover { color: var(--ink); }
.sheet .summary { margin: var(--space-5) 0; }
.sheet .summary > div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border);
}
.sheet .summary dt { color: var(--muted); margin: 0; }
.sheet .summary dd { margin: 0; font-weight: var(--fw-semibold); text-align: right; }
.drawer-templates-head { margin-top: var(--space-4); }
```

Inside the Motion block add `.sheet { transition: transform 150ms ease; }` only if a slide-in is wired; otherwise add nothing (no dead transitions).

- [ ] **Step 4: Look at it**

Start the dev server with `preview_start` (`run-emb-bot` skill) at 1440×900. Confirm: field left, panel right, "Your design" heading, Add text | Upload logo, Design then Garment sections, bar pinned at the foot with `—` figures, Download disabled. Type `FRITSCH`: figures fill, Download enables, click → sheet with "Ready to stitch", recap, "Download" heading, DST button. Press Escape → closes. Resize to 375 wide: field on top, panel below, bar still visible. Screenshot both for the PR body.

- [ ] **Step 5: Commit**

```bash
git add app/src/ui/theme.css
git commit -m "studio: panel on the right; summary bar and sheet styles; stepper rules out"
```

---

### Task 8: e2e helpers

**Files:**
- Create: `app/e2e/helpers.js`

**Interfaces (Produces):**
```js
startStudio(page)                 // goto("/"), wait for the "Your design" heading
typeText(page, text)              // fill the text input, wait for a stitch count
pickGarment(page, label)          // click the garment tile by exact label (tiles still exist in PR 1)
pickTemplate(page, name)          // open My designs, click the .tcard containing name, wait for stitches
openDownload(page)                // click the summary bar's Download, wait for the dialog + "Download" heading
closeDownload(page)               // Escape, wait for the dialog to go
```

- [ ] **Step 1: Write the helpers**

```js
// Shared drives for the configurator (spec §7). Every spec used to walk
// Next → Next → Next; the walk is gone, so the way to each place is stated
// once here. Assertions about WHAT is reached stay in each spec.
import { expect } from "@playwright/test";

export async function startStudio(page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your design" })).toBeVisible();
}

export async function typeText(page, text) {
  const input = page.getByPlaceholder("Type a name or word");
  await input.fill(text);
  await expect(input).toHaveValue(text);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
}

export async function pickGarment(page, label) {
  const tile = page.getByRole("button", { name: label, exact: true });
  await tile.click();
  await expect(tile).toHaveClass(/\bsel\b/);
}

export async function pickTemplate(page, name) {
  await page.getByRole("button", { name: /^My designs/ }).click();
  await page.locator(".tcard", { hasText: name }).click();
  await expect(page.getByRole("dialog", { name: "My designs" })).toHaveCount(0);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
}

export async function openDownload(page) {
  await page.getByRole("button", { name: "Download", exact: true }).click();
  const sheet = page.getByRole("dialog", { name: "Download" });
  await expect(sheet).toBeVisible();
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();
  return sheet;
}

export async function closeDownload(page) {
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Download" })).toHaveCount(0);
}
```

If `ProjectsDrawer`'s dialog is not named "My designs", read its `aria-label` (line ~175 of the component) and use that.

- [ ] **Step 2: Commit**

```bash
git add app/e2e/helpers.js
git commit -m "e2e: helpers for the configurator — start, type, template, openDownload"
```

---

### Task 9: `configurator-smoke.spec.js` (was `wizard-smoke`)

**Files:**
- Rename: `app/e2e/wizard-smoke.spec.js` → `app/e2e/configurator-smoke.spec.js`
- Modify: every test in it

Mapping, applied test by test (line numbers are the CURRENT file):

| Test | Change |
|------|--------|
| `reachReviewWithText` helper (66–85) | becomes `reachDownloadWithText(page, garmentLabel, text)`: `startStudio`, `pickGarment`, `typeText`, `openDownload`. Delete the `.topbar-download` assertion. |
| 87 "garment → content → review → download" | rename "configurator: text → download sheet → DST". Same body through the helpers; the `dl.summary` assertions run INSIDE the sheet (`page.locator(".sheet dl.summary")`); the `.threadlist` and DST download assertions unchanged. |
| 152 loop over Hat Front / Full Back | `reachDownloadWithText`, then the two `dl.summary` assertions and the `.threadrow` one. |
| 183 image path | replace the tile/Next/heading lines with `startStudio` + `pickGarment(page, "Tote")`; everything after "Artwork" unchanged; the review part = `openDownload` + `dl.summary` assertions. |
| 298 PES/EXP/PDF | `reachDownloadWithText` then the format buttons unchanged. |
| 353 "panel is scrolled to the top after every step change" | DELETE — there are no step changes. Replace with "the panel scrolls to the top when a different design is opened": `pickTemplate(page, "Left-chest name")`, scroll `.cfg-body` to bottom, open My designs, click `+ New design`, `expect.poll(scrollTop).toBe(0)`. |
| 396 "does not claim readiness for a design with nothing in it" | `startStudio`; Download button `toBeDisabled()` with `title` "Add text or a logo first"; then `typeText("HELLO")`, `openDownload`, expect "Ready to stitch" and `'Text — "HELLO"'`. The "Nothing to stitch yet" branch is unit-tested (Task 3) — it is unreachable from the bar, so drop that half here. |
| 440 artwork survives refresh | replace the leading walk; after `page.reload()` expect the "Your design" heading (not "What are you putting this on?"); the review = `openDownload` + `dl.summary` contains "Logo / image". |
| 497 recap names every element | walk via helpers; `openDownload`; same summary assertions on `.sheet dl.summary`. |
| 519 size field and caption agree | leading walk via `pickGarment`/`typeText`; rest unchanged. |
| 556 font that can't set the text | leading walk via helpers; rest unchanged. |
| 593 every control has an accessible name | replace the four step clicks: check after `startStudio` ("configurator"), after "Artwork" click, after `openDownload` ("download sheet"). |
| 617 no console errors | expect "Your design" heading. |
| 633 empty canvas hint | `startStudio` + `pickGarment("Left Chest")` then unchanged. |
| 662 simulator unit | leading walk via helpers. |
| 691 review names the cost | `openDownload` then the `.sheet dl.summary` assertions. |

- [ ] **Step 1: `git mv` and rewrite per the table**

Replace the file header comment's first paragraph with: "End-to-end smoke test for the Studio configurator: one panel, the summary bar, the Download sheet — walked as a customer would, asserting real state, not just 'the page didn't crash'."

- [ ] **Step 2: Run it**

Run: `cd app && npx playwright test e2e/configurator-smoke.spec.js --reporter=list 2>&1 | tail -40`
Expected: all tests in the file pass. Read the tail for the pass count, not the exit code.

- [ ] **Step 3: Commit**

```bash
git add -A app/e2e
git commit -m "e2e: wizard-smoke becomes configurator-smoke"
```

---

### Task 10: Migrate the remaining 23 e2e specs

**Files:** every file below. Each edit is mechanical; the table says what replaces the walk. `H` = `import { startStudio, typeText, pickGarment, pickTemplate, openDownload } from "./helpers.js";` added at the top.

| File | Old walk (lines) | New |
|------|------------------|-----|
| `design-import.spec.js` 29–31, 124–129, 136–138 | goto, Left Chest, Next; later `4 Download` button | `startStudio` (Left Chest is the default — drop the click); `typeText`; `openDownload` in place of `4 Download` |
| `design-naming.spec.js` 32–35 | Left Chest, Next, fill | `typeText(page, text)` (default garment) |
| `design-originals.spec.js` 138–140 | goto, Tote, Next | `startStudio`, `pickGarment("Tote")` |
| `digitize-auto-start.spec.js` 115–120, 187–189, 243–245, 287–293 | goto, tile, Next, heading; `4 Download` | `startStudio`, `pickGarment(label)`; `openDownload` |
| `digitize-background-enclosed.spec.js` 159–160, 229–230 | Next + heading | delete both lines (already on the panel) |
| `digitize-boundary-edit.spec.js` 113–114 | Next + heading | delete |
| `digitize-shape-identity.spec.js` 139–140, 192–193 | Next + heading | delete |
| `digitize-stale-edits.spec.js` 143–144 | Next + heading | delete |
| `download-machine.spec.js` 9–16, 49–50 | template `.tcard` on "/", Next, Next; `.topbar-download` | `startStudio`, `pickTemplate("Left-chest name")`, `openDownload`; line 49 → `openDownload` |
| `field-border-menu.spec.js` 98–99 | Next + heading | delete |
| `field-node-edit.spec.js` 49–50 | Next + heading | delete |
| `field-outlines.spec.js` 117–118 | Next + heading | delete |
| `field-panel-sync.spec.js` 114–115 | Next + heading | delete |
| `field-shape-popover.spec.js` 51–52 | Next + heading | delete |
| `font-load-failure.spec.js` 18, 39, 55 | Next | delete |
| `manual-trace-import.spec.js` 36–37 | Next + heading | delete |
| `quality-report.spec.js` 91–99, 178–182, 246–250, 292–296, 313–317 | Tote, Next, heading …, `3 Review`, "Ready to stitch" | `startStudio`, `pickGarment("Tote")` …; `openDownload` in place of `3 Review` + the "Ready to stitch" expect (the sheet's h2 IS "Ready to stitch", so keep that expect after `openDownload`) |
| `storage-full.spec.js` 48–51, 100–103 | Left Chest, Next, fill | `typeText(page, "A")` |
| `text-cluster-convert.spec.js` 140–142 | Tote, Next, heading | `pickGarment("Tote")` |
| `touch-drawing-tools.spec.js` 34, 56, 69 | Next click / tap | delete (the field hint is visible from the start) |
| `typographic-punctuation.spec.js` 25, 39, 53, 62 | Next | delete |
| `worksheet-digitized-lane.spec.js` 127, 133, 157 | Patch tile, Next; Next (review, `.qr-bill`); Next (download, PDF button) | `pickGarment("Patch")`; delete 127; replace 133 with `openDownload` (the `.qr-bill` expect stays — QualityReport is in the sheet); delete 157 |
| `worksheet-numbers.spec.js` 45, 50, 63, 84, 88–89, 129, 133–134 | Next; Next (review, reads `body` innerText for `Trims N`); Next; Next; Next×2; Full Back + Next; Next×2 | delete 45; 50 → `openDownload` (the innerText read stays — the recap is in the sheet); delete 63; delete 84; 88–89 → `openDownload`; 129 → `pickGarment("Full Back")`; 133–134 → `openDownload` |

Where a `Tote`/`Left Chest` click preceded `Next`, keep the click through `pickGarment` ONLY when the test's assertions depend on that garment (Tote's oversize confirm, the hoop label). `Left Chest` is the default and its click can go.

- [ ] **Step 1: Apply the table**

- [ ] **Step 2: Grep for stragglers**

Run: `cd app && grep -rn 'name: "Next"\|3 Review\|4 Download\|2 Content\|topbar-download\|What are you making\|What are you putting\|name: "Back"' e2e/`
Expected: no output.

- [ ] **Step 3: Run the no-service specs locally**

Run: `cd app && npx playwright test e2e/design-naming.spec.js e2e/download-machine.spec.js e2e/font-load-failure.spec.js e2e/storage-full.spec.js e2e/typographic-punctuation.spec.js e2e/touch-drawing-tools.spec.js e2e/design-import.spec.js --reporter=list 2>&1 | tail -30`
Expected: all pass.

- [ ] **Step 4: Run the service-backed specs**

Start the digitizer service (`run-emb-bot` skill) then:
Run: `cd app && npx playwright test --workers=1 --reporter=list > ../e2e.log 2>&1; echo "EXIT=$?" >> ../e2e.log; tail -30 ../e2e.log`
Expected: `EXIT=0`. Read the recorded code, not the harness's.

- [ ] **Step 5: Commit**

```bash
git add -A app/e2e
git commit -m "e2e: every spec walks the configurator through helpers.js"
```

---

### Task 11: Docs — MASTER_SCOPE area 3, the area doc, COOKBOOK pointer

**Files:**
- Modify: `MASTER_SCOPE.md:291, 358, 634-640`
- Modify: `docs/scope/3-studio-app-wizard.md` (top of file; append a dated entry)
- Modify: `COOKBOOK.md` (the Studio architecture paragraph that names StepNav/steps — grep `StepNav`)

- [ ] **Step 1: MASTER_SCOPE**

- Line 291 row title: `3. Studio app / configurator`. Append to its status cell: `**The wizard is gone (2026-09-30, PR N)** — one panel, a summary bar, a Download sheet; spec \`docs/superpowers/specs/2026-09-30-studio-configurator-design.md\`, PRs 2–4 pending.`
- Line 358 (resolved item 15 about step history): append `**Superseded 2026-09-30:** there are no step entries; the Download sheet is the one history entry, and Back closes it.`
- Line 634 heading: `### 3. Studio app / configurator — [detail](docs/scope/3-studio-app-wizard.md)`; line 637: "The Svelte configurator (one panel: design → colours → garment, summary bar, Download sheet)…".

- [ ] **Step 2: Area doc**

At the top of `docs/scope/3-studio-app-wizard.md` add a dated paragraph: what changed, what stayed (`EmbroideryField`, `DownloadStep`, every export lane), what the e2e migration cost (files touched, helpers), and that PRs 2–4 follow. Pointer style `(verb date — source)`.

- [ ] **Step 3: COOKBOOK**

`COOKBOOK.md:12` describes `app/` as "a Svelte 5 + Vite guided wizard (garment → …)". Rewrite that bullet: "a Svelte 5 + Vite configurator — one panel (`ui/Configurator.svelte`: design, colours, garment), a sticky `SummaryBar`, and a `DownloadSheet` that wraps `DownloadStep`; e2e specs reach the sheet through `e2e/helpers.js` `openDownload`."

- [ ] **Step 4: Commit**

```bash
git add MASTER_SCOPE.md docs/scope/3-studio-app-wizard.md COOKBOOK.md
git commit -m "docs: area 3 is a configurator now; the wizard and its step history are gone"
```

---

### Task 12: Verify, review, open the PR

- [ ] **Step 1: Full Studio unit suite**

Run: `cd app && npm test > ../unit.log 2>&1; echo "EXIT=$?" >> ../unit.log; tail -12 ../unit.log`
Expected: `EXIT=0`. Record the pass count for the PR body.

- [ ] **Step 2: Engine suite (nothing should have moved, prove it)**

Run: `node --test 2>&1 | tail -6`
Expected: same pass count as `main`.

- [ ] **Step 3: Adversarial read of the diff**

Run: `git diff main...HEAD --stat` and read `App.svelte`'s diff in full. Check specifically: no remaining reference to `step`, `stepHistory`, `canAdvance`, `showTemplatesHint`; `window.history` used in the sheet helpers (not the shadowed `history`); `enterProject` has three parameters at every call.

- [ ] **Step 4: Dispatch `emb-bot-reviewer`** on the branch; fix what it finds that is real.

- [ ] **Step 5: Open the PR ready-for-review**

Body: the spec link, the two screenshots from Task 7 Step 4 (1440 and 375), unit and e2e counts with the recorded exit codes, and the trade-off flagged in the spec: the "Nothing to stitch yet" screen is now unreachable from the UI (Download is disabled instead) and is covered by a unit test only. Arm auto-merge while `mergeable_state` is `blocked`. Budget 70 minutes for `digitizer`.
