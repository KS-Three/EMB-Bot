# Studio Configurator — PR 2: Garment Row + Original View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ten garment tiles with a compact pill row (`Polo · Hat · Tee · More ›`), and let the customer flip the field between the stitched design and the artwork they uploaded.

**Architecture:** A pure `lib/garmentPills.js` decides which pills show; `ui/GarmentPicker.svelte` renders them and a `role="menu"` popover listing all ten garments with the existing `garmentArt` icons; `GarmentStep.svelte` swaps its tile grid for the picker. "Original" is a fourth segment in `EmbroideryField`'s existing **View** group (Stitches · Realistic · Simulate · Original): when lit, the canvas renders fabric and hoop with no strands and draws each element's `sourcePng` into the rect its stitches occupy. `lib/originalImage.js` holds the pure fit maths and the decode cache.

**Tech Stack:** Svelte 5 (legacy `export let` / `on:` syntax), Vitest + `@testing-library/svelte`, `@playwright/test`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-30-studio-configurator-design.md` §3 (garment row), §4 (Original). Two deliberate departures from the spec's wording, both forced by rules the spec itself cites — Kent approves them by approving this plan:

1. **§4 says a 64×64 chip "top-left of the field surround".** The canvas fills the pane, so any top-left chip sits ON the canvas; DOCTRINE forbids chrome over sewable field and `e2e/field-chrome.spec.js` pins `.hoop > *` at exactly one child. "Original" therefore lives in the bar under the canvas, as a fourth View segment — text only, like the other three; no thumbnail.
2. **§4 says the source is drawn "fitted to the hoop's placement box".** It is drawn into the rect the element's own stitches occupy instead, so flipping Original ↔ Stitches compares like with like at the same place and size.

## Global Constraints

- `app/` only. `src/*.js` (the engine) is never touched.
- `project.garmentId / fabricRgb / hoopId` writes are unchanged — the picker dispatches the same `update` event with `{ garmentId }` the tiles did.
- Pill short names are exactly `Polo` (`left_chest`), `Hat` (`hat_front`), `Tee` (`full_back`); the popover lists all ten garments by the ENGINE's labels (`EMB.GARMENTS[].label`).
- The popover is `role="menu"` (never `role="dialog"` — a second dialog breaks every bare `getByRole("dialog")` in the e2e suite), its items `role="menuitemradio"` with `aria-checked`.
- No chrome over the canvas: `.hoop` keeps exactly one child (the canvas). Original is painted ON the canvas as a view mode and is view-only state — never saved, never in undo history, reset by any regeneration.
- Every existing `aria-label`/`aria-pressed` on the View segments stays (`Stitches view`, `Realistic view`, `Stitch simulator`); the new one is `Original view`.
- No new colour tokens (theme pass is PR 4).
- Unit: `cd app && npx vitest run <file>`; on this machine use `--hookTimeout=90000 --testTimeout=60000` for full-suite runs (pre-existing 10 s `beforeAll` hooks time out under load). e2e: `npx playwright test <file> --workers=1 --reporter=list > ../log 2>&1; echo "EXIT=$?" >> ../log` and read the EXIT line.
- Branch `claude/configurator-garment-row`, stacked on PR #585; merge `origin/main` in once #585 lands. Commit after every task: subject, blank line, `Co-Authored-By:` trailer.
- PR opened ready-for-review with auto-merge armed while `mergeable_state` is `blocked`.

---

## File map

| File | Change | Responsibility |
|------|--------|----------------|
| `app/src/lib/garmentPills.js` (+ `.spec.js`) | create | which pills to show for a garment id |
| `app/src/ui/GarmentPicker.svelte` (+ `.spec.js`, `.testHarness.svelte`) | create | pill row + More popover |
| `app/src/ui/GarmentStep.svelte` | modify | tiles out, picker in |
| `app/src/ui/theme.css` | modify | `.gpill*`, `.gmenu*`; delete `.tiles`, `.tile*` |
| `app/e2e/helpers.js` | modify | `pickGarment` goes through the More menu |
| `app/e2e/*.spec.js` (10 files, 12 sites) | modify | bare tile clicks → `pickGarment` |
| `app/src/lib/originalImage.js` (+ `.spec.js`) | create | data URL, aspect-fit rect, decode cache |
| `app/src/lib/settingHelp.js` | modify | tip text for the Original segment |
| `app/src/ui/EmbroideryField.svelte` | modify | fourth View segment; paint the original |
| `app/e2e/configurator-smoke.spec.js` | modify | Original view test |
| `MASTER_SCOPE.md`, `docs/scope/3-studio-app-wizard.md` | modify | area 3 status |

---

### Task 1: `lib/garmentPills.js`

**Files:**
- Create: `app/src/lib/garmentPills.js`
- Test: `app/src/lib/garmentPills.spec.js`

**Interfaces:**
- Produces: `PRIMARY_PILLS: Array<{ id: string, short: string }>` and `pillsFor(garmentId: string, garments: Array<{ id, label }>) → Array<{ id, text, title, selected }>`.

- [ ] **Step 1: Write the failing test**

```js
import { expect, test } from "vitest";
import { PRIMARY_PILLS, pillsFor } from "./garmentPills.js";

const GARMENTS = [
  { id: "hat_front", label: "Hat Front" },
  { id: "left_chest", label: "Left Chest" },
  { id: "full_back", label: "Full Back" },
  { id: "tote", label: "Tote" },
];

test("the three primary pills are Polo, Hat, Tee in that order", () => {
  expect(PRIMARY_PILLS.map((p) => p.short)).toEqual(["Polo", "Hat", "Tee"]);
  expect(PRIMARY_PILLS.map((p) => p.id)).toEqual(["left_chest", "hat_front", "full_back"]);
});

test("a primary garment shows three pills with that one selected", () => {
  const pills = pillsFor("hat_front", GARMENTS);
  expect(pills.map((p) => p.text)).toEqual(["Polo", "Hat", "Tee"]);
  expect(pills.map((p) => p.selected)).toEqual([false, true, false]);
});

test("each primary pill's title is the engine's full label", () => {
  expect(pillsFor("left_chest", GARMENTS).map((p) => p.title)).toEqual(["Left Chest", "Hat Front", "Full Back"]);
});

test("a garment outside the three adds a fourth, selected pill with its engine label", () => {
  const pills = pillsFor("tote", GARMENTS);
  expect(pills.map((p) => p.text)).toEqual(["Polo", "Hat", "Tee", "Tote"]);
  expect(pills.map((p) => p.selected)).toEqual([false, false, false, true]);
  expect(pills[3].id).toBe("tote");
});

test("an unknown garment id selects nothing and adds nothing", () => {
  const pills = pillsFor("nope", GARMENTS);
  expect(pills.length).toBe(3);
  expect(pills.some((p) => p.selected)).toBe(false);
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd app && npx vitest run src/lib/garmentPills.spec.js`
Expected: FAIL — cannot resolve `./garmentPills.js`.

- [ ] **Step 3: Write the module**

```js
// Which pills the garment row shows (spec §3). The three commonest
// placements are always there under a short name; any other garment in
// force rides along as a fourth pill, so the row always shows what is
// selected without listing all ten.
export const PRIMARY_PILLS = [
  { id: "left_chest", short: "Polo" },
  { id: "hat_front", short: "Hat" },
  { id: "full_back", short: "Tee" },
];

export function pillsFor(garmentId, garments) {
  const labelOf = (id) => {
    const g = (garments || []).find((x) => x.id === id);
    return g ? g.label : id;
  };
  const pills = PRIMARY_PILLS.map((p) => ({
    id: p.id,
    text: p.short,
    title: labelOf(p.id),
    selected: p.id === garmentId,
  }));
  const isPrimary = PRIMARY_PILLS.some((p) => p.id === garmentId);
  const known = (garments || []).some((g) => g.id === garmentId);
  if (!isPrimary && known) {
    pills.push({ id: garmentId, text: labelOf(garmentId), title: labelOf(garmentId), selected: true });
  }
  return pills;
}
```

- [ ] **Step 4: Run the spec**

Run: `cd app && npx vitest run src/lib/garmentPills.spec.js`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/garmentPills.js app/src/lib/garmentPills.spec.js
git commit -m "studio: garmentPills — which pills the garment row shows"
```

---

### Task 2: `GarmentPicker.svelte`

**Files:**
- Create: `app/src/ui/GarmentPicker.svelte`
- Create: `app/src/ui/GarmentPicker.testHarness.svelte`
- Test: `app/src/ui/GarmentPicker.spec.js`

**Interfaces:**
- Consumes: `pillsFor` (Task 1); `garmentArt(id)` from `ui/garmentArt.js`; `EMB.GARMENTS` via `lib/emb.js`.
- Props: `garmentId: string`.
- Dispatches: `update` with detail `{ garmentId }`.
- Markup contract (e2e and CSS depend on it): `<div class="gpicker">` → `<div class="gpills" role="group" aria-label="Garment">` holding one `<button class="gpill" class:sel aria-pressed title>` per pill and `<button class="gpill gpill-more" aria-haspopup="menu" aria-expanded aria-label="More garments">More ›</button>`; when open, `<div class="gmenu" role="menu" aria-label="All garments">` with one `<button class="gmenu-item" role="menuitemradio" aria-checked>` per garment (icon `span.gart` + label).

- [ ] **Step 1: Write the harness**

```svelte
<script>
  import GarmentPicker from "./GarmentPicker.svelte";
  export let garmentId = "left_chest";
  export let onUpdate = () => {};
</script>

<GarmentPicker {garmentId} on:update={onUpdate} />
```

- [ ] **Step 2: Write the failing spec**

`GarmentPicker` imports `lib/emb.js`, which throws unless the engine global exists — same preamble as `GarmentStep.spec.js`.

```js
// @vitest-environment jsdom
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent, screen, within } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

let Harness;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  ({ default: Harness } = await import("./GarmentPicker.testHarness.svelte"));
});

test("shows Polo, Hat, Tee and More, with the garment in force pressed", () => {
  render(Harness, { garmentId: "hat_front" });
  const group = screen.getByRole("group", { name: "Garment" });
  expect(within(group).getByRole("button", { name: "Polo" })).toHaveAttribute("aria-pressed", "false");
  expect(within(group).getByRole("button", { name: "Hat" })).toHaveAttribute("aria-pressed", "true");
  expect(within(group).getByRole("button", { name: "Tee" })).toBeInTheDocument();
  expect(within(group).getByRole("button", { name: "More garments" })).toBeInTheDocument();
});

test("clicking a pill dispatches update with its garment id", async () => {
  const onUpdate = vi.fn();
  render(Harness, { garmentId: "left_chest", onUpdate });
  await fireEvent.click(screen.getByRole("button", { name: "Tee" }));
  expect(onUpdate.mock.calls[0][0].detail).toEqual({ garmentId: "full_back" });
});

test("a garment outside the three appears as a fourth pressed pill", () => {
  render(Harness, { garmentId: "tote" });
  expect(screen.getByRole("button", { name: "Tote" })).toHaveAttribute("aria-pressed", "true");
});

test("More opens a menu of all ten garments, the current one checked", async () => {
  render(Harness, { garmentId: "tote" });
  expect(screen.queryByRole("menu")).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "More garments" }));
  const menu = screen.getByRole("menu", { name: "All garments" });
  expect(within(menu).getAllByRole("menuitemradio").length).toBe(10);
  expect(within(menu).getByRole("menuitemradio", { name: "Tote" })).toHaveAttribute("aria-checked", "true");
  expect(within(menu).getByRole("menuitemradio", { name: "Left Chest" })).toHaveAttribute("aria-checked", "false");
});

test("picking from the menu dispatches update and closes it", async () => {
  const onUpdate = vi.fn();
  render(Harness, { garmentId: "left_chest", onUpdate });
  await fireEvent.click(screen.getByRole("button", { name: "More garments" }));
  await fireEvent.click(screen.getByRole("menuitemradio", { name: "Beanie" }));
  expect(onUpdate.mock.calls[0][0].detail).toEqual({ garmentId: "beanie" });
  expect(screen.queryByRole("menu")).toBeNull();
});

test("Escape closes the menu and returns focus to More", async () => {
  render(Harness, { garmentId: "left_chest" });
  const more = screen.getByRole("button", { name: "More garments" });
  await fireEvent.click(more);
  await fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
  expect(screen.queryByRole("menu")).toBeNull();
  expect(document.activeElement).toBe(more);
});
```

- [ ] **Step 3: Run it to see it fail**

Run: `cd app && npx vitest run src/ui/GarmentPicker.spec.js`
Expected: FAIL — cannot resolve `./GarmentPicker.svelte`.

- [ ] **Step 4: Write the component**

```svelte
<script>
  // The garment row (spec §3): three pills for the commonest placements,
  // a fourth for anything else in force, and More › for the full list.
  // A menu, not a dialog — the Studio's e2e suite addresses its dialogs by
  // bare role, and this is a pick-one list, which is what a menu is.
  import { createEventDispatcher, tick } from "svelte";
  import { EMB } from "../lib/emb.js";
  import { garmentArt } from "./garmentArt.js";
  import { pillsFor } from "../lib/garmentPills.js";
  export let garmentId;
  const d = createEventDispatcher();

  const garments = (EMB.GARMENTS || []).map((g) => ({ id: g.id, label: g.label || g.id }));
  $: pills = pillsFor(garmentId, garments);

  let open = false;
  let moreBtn = null;
  let menuEl = null;

  function pick(id) {
    open = false;
    d("update", { garmentId: id });
  }
  async function toggle() {
    open = !open;
    if (open) {
      await tick();
      const cur = menuEl && menuEl.querySelector('[aria-checked="true"]');
      (cur || (menuEl && menuEl.querySelector("button")))?.focus();
    }
  }
  function onMenuKey(e) {
    if (e.key === "Escape") {
      e.stopPropagation();
      open = false;
      moreBtn && moreBtn.focus();
    }
  }
  // A press anywhere outside the picker closes the menu.
  function onWindowDown(e) {
    if (open && menuEl && !menuEl.contains(e.target) && e.target !== moreBtn) open = false;
  }
</script>

<svelte:window on:pointerdown={onWindowDown} />

<div class="gpicker">
  <div class="gpills" role="group" aria-label="Garment">
    {#each pills as p (p.id)}
      <button
        type="button"
        class="gpill"
        class:sel={p.selected}
        aria-pressed={p.selected}
        title={p.title}
        on:click={() => pick(p.id)}
      >{p.text}</button>
    {/each}
    <button
      type="button"
      class="gpill gpill-more"
      aria-haspopup="menu"
      aria-expanded={open}
      aria-label="More garments"
      bind:this={moreBtn}
      on:click={toggle}
    >More ›</button>
  </div>
  {#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="gmenu" role="menu" aria-label="All garments" tabindex="-1" bind:this={menuEl} on:keydown={onMenuKey}>
      {#each garments as g (g.id)}
        <button
          type="button"
          class="gmenu-item"
          role="menuitemradio"
          aria-checked={g.id === garmentId}
          on:click={() => pick(g.id)}
        >
          <span class="gart" aria-hidden="true">{@html garmentArt(g.id)}</span>
          <span>{g.label}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>
```

If Svelte reports a different a11y warning code for the menu's keydown handler, use the code it prints — the test output must be pristine.

- [ ] **Step 5: Run the spec**

Run: `cd app && npx vitest run src/ui/GarmentPicker.spec.js`
Expected: PASS, 6 tests, no warnings.

- [ ] **Step 6: Commit**

```bash
git add app/src/ui/GarmentPicker.svelte app/src/ui/GarmentPicker.testHarness.svelte app/src/ui/GarmentPicker.spec.js
git commit -m "studio: GarmentPicker — Polo, Hat, Tee and a More menu"
```

---

### Task 3: The picker replaces the tiles

**Files:**
- Modify: `app/src/ui/GarmentStep.svelte` (the `tiles` const and the `<div class="tiles">` block; imports)
- Modify: `app/src/ui/theme.css` (`.tiles`, `.tile*` at ~1124–1172; append `.gpill*`, `.gmenu*`)

**Interfaces:**
- Consumes: `GarmentPicker` (Task 2).
- `GarmentStep` still dispatches `update`; no prop changes.

- [ ] **Step 1: Swap the markup**

In `GarmentStep.svelte`: add `import GarmentPicker from "./GarmentPicker.svelte";`, remove the `garmentArt` import, the `readable` function and the `tiles` const if nothing else in the file uses them (`readable` — grep the file first). Replace

```svelte
<div class="tiles">
  {#each tiles as t}
    <button class="tile" class:sel={project.garmentId === t.id} on:click={() => d("update", { garmentId: t.id })}>
      <span class="gart" aria-hidden="true">{@html garmentArt(t.id)}</span>
      <span class="tile-label">{t.label}</span>
    </button>
  {/each}
</div>
```

with

```svelte
<GarmentPicker garmentId={project.garmentId} on:update={(e) => d("update", e.detail)} />
```

- [ ] **Step 2: CSS**

Delete `.tiles`, `.tile`, `.tile:hover`, `.tile.sel`, `.tile.sel .tile-label`, `.tile.sel .gart, .tile:hover .gart`, `.tile-label` and their comment block. KEEP `.gart`, `.gart svg`, `.gart .acc` (the menu uses them). Run `grep -rn 'class="tile\|tile-label\|"tiles"' src/` first — expected: no consumer left. Append before the Motion block:

```css
/* ---- Garment row (spec §3) --------------------------------------------- */
.gpicker { position: relative; }
.gpills { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.gpill {
  min-height: 32px;
  padding: 0 var(--space-3);
  border: 1px solid transparent;
  border-radius: var(--radius-full);
  background: var(--bg);
  color: var(--ink);
  font: inherit;
  font-size: var(--fs-sm);
  cursor: pointer;
}
.gpill:hover { border-color: var(--ink); }
.gpill.sel { background: var(--ink); color: var(--surface); }
.gpill-more { color: var(--muted); }

.gmenu {
  position: absolute;
  z-index: 6;
  top: calc(100% + var(--space-2));
  left: 0;
  right: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-1);
  padding: var(--space-2);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-m);
  box-shadow: var(--shadow-2);
  outline: none;
}
.gmenu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: var(--space-1) var(--space-2);
  border: 0;
  border-radius: var(--radius-s);
  background: transparent;
  color: var(--ink);
  font: inherit;
  font-size: var(--fs-sm);
  text-align: left;
  cursor: pointer;
}
.gmenu-item:hover, .gmenu-item:focus-visible { background: var(--bg); }
.gmenu-item[aria-checked="true"] { background: var(--tint); color: var(--accent); font-weight: var(--fw-semibold); }
.gmenu-item .gart svg { width: 24px; height: 24px; }
```

Confirm `--radius-full` and `--radius-m` exist (`grep -n "^\s*--radius-" src/ui/theme.css`); if `--radius-m` is named differently, use the token the file defines for 6 px.

- [ ] **Step 3: Run the specs**

Run: `cd app && npx vitest run src/ui/GarmentStep.spec.js src/ui/GarmentPicker.spec.js && npx vite build 2>&1 | tail -2`
Expected: all pass; build succeeds.

- [ ] **Step 4: Commit**

```bash
git add app/src/ui/GarmentStep.svelte app/src/ui/theme.css
git commit -m "studio: the garment tiles become a pill row"
```

---

### Task 4: e2e — `pickGarment` goes through the menu

**Files:**
- Modify: `app/e2e/helpers.js` (`pickGarment`)
- Modify: the 10 spec files that click a garment tile directly (12 sites)

- [ ] **Step 1: Rewrite the helper**

```js
// Every garment is reachable through More ›, by the engine's own label —
// so one path serves all ten, whether or not the garment has a pill.
export async function pickGarment(page, label) {
  await page.getByRole("button", { name: "More garments" }).click();
  await page.getByRole("menu", { name: "All garments" }).getByRole("menuitemradio", { name: label, exact: true }).click();
  await expect(page.getByRole("menu", { name: "All garments" })).toHaveCount(0);
  await expect(page.locator(".cfg-sub")).toContainText(label);
}
```

(`.cfg-sub` is the panel subtitle `"{Garment} · {hoop}"`, built from the same label.)

- [ ] **Step 2: Migrate the bare tile clicks**

Find them: `grep -rn 'getByRole("button", { name: "\(Tote\|Left Chest\|Patch\|Full Back\|Hat Front\|Beanie\|Sleeve\|Jacket Back\|Towel\|Blanket\)", exact: true })' e2e/*.spec.js`
Expected: 12 sites in 10 files (the `digitize-*`, `field-*`, `manual-trace-import`, `worksheet-*` specs kept a bare `Tote`/`Patch` click through PR 1). Replace each `await page.getByRole("button", { name: "X", exact: true }).click();` with `await pickGarment(page, "X");`, adding `pickGarment` to that file's `./helpers.js` import (add the import line if the file has none). Where a spec holds the tile in a variable and asserts `toHaveClass(/\bsel\b/)`, drop that assertion — `pickGarment` asserts the subtitle instead.

- [ ] **Step 3: Straggler grep**

Run: `grep -rn '"tile"\|\.tile\b\|tile-label\|/\\bsel\\b/' e2e/`
Expected: no garment-tile hit (a `.sel` assertion on a hoop tile or element row is unrelated — leave it).

- [ ] **Step 4: Run the no-service specs**

Run: `cd app && npx playwright test e2e/configurator-smoke.spec.js e2e/design-naming.spec.js e2e/download-machine.spec.js e2e/worksheet-numbers.spec.js --workers=1 --reporter=list > ../e2e-pr2-t4.log 2>&1; echo "EXIT=$?" >> ../e2e-pr2-t4.log`
Expected: `EXIT=0`. The smoke suite's Tote/Hat Front/Full Back tests exercise both a menu-only garment and two pill garments through the menu.

- [ ] **Step 5: Commit**

```bash
git add app/e2e
git commit -m "e2e: garments are picked through the More menu"
```

---

### Task 5: `lib/originalImage.js`

**Files:**
- Create: `app/src/lib/originalImage.js`
- Test: `app/src/lib/originalImage.spec.js`

**Interfaces:**
- Produces:
  - `originalDataUrl(sourcePng: string|null) → string|null` — `sourcePng` is BARE base64 (see `DigitizePanel.svelte:1880`, `App.svelte:780`).
  - `fitRect(imgW, imgH, rect: {x,y,w,h}) → {x,y,w,h}` — aspect-preserving, centred, inside `rect`.
  - `loadOriginal(sourcePng) → Promise<HTMLImageElement>` — cached by the base64 string.
  - `hasOriginal(el) → boolean`.

- [ ] **Step 1: Write the failing test**

```js
import { expect, test } from "vitest";
import { originalDataUrl, fitRect, hasOriginal } from "./originalImage.js";

test("builds a PNG data URL from bare base64, and nothing from nothing", () => {
  expect(originalDataUrl("AAAA")).toBe("data:image/png;base64,AAAA");
  expect(originalDataUrl(null)).toBeNull();
  expect(originalDataUrl("")).toBeNull();
});

test("a wide image in a square rect is letterboxed and centred", () => {
  expect(fitRect(200, 100, { x: 10, y: 20, w: 100, h: 100 })).toEqual({ x: 10, y: 45, w: 100, h: 50 });
});

test("a tall image in a wide rect is pillarboxed and centred", () => {
  expect(fitRect(100, 200, { x: 0, y: 0, w: 300, h: 100 })).toEqual({ x: 125, y: 0, w: 50, h: 100 });
});

test("a degenerate image or rect yields null", () => {
  expect(fitRect(0, 100, { x: 0, y: 0, w: 10, h: 10 })).toBeNull();
  expect(fitRect(10, 10, { x: 0, y: 0, w: 0, h: 10 })).toBeNull();
  expect(fitRect(10, 10, null)).toBeNull();
});

test("only image and digitized elements with a sourcePng have an original", () => {
  expect(hasOriginal({ type: "image", sourcePng: "AAAA" })).toBe(true);
  expect(hasOriginal({ type: "digitized", sourcePng: "AAAA" })).toBe(true);
  expect(hasOriginal({ type: "digitized", sourcePng: null })).toBe(false);
  expect(hasOriginal({ type: "text", text: "A" })).toBe(false);
  expect(hasOriginal(null)).toBe(false);
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd app && npx vitest run src/lib/originalImage.spec.js`
Expected: FAIL — cannot resolve `./originalImage.js`.

- [ ] **Step 3: Write the module**

```js
// The artwork a customer uploaded, for the field's Original view (spec §4).
// `element.sourcePng` is bare base64 — the 1,200-px preview both the image
// and the digitized lanes keep on the element (lib/project.js).
export function originalDataUrl(sourcePng) {
  return typeof sourcePng === "string" && sourcePng.length > 0 ? "data:image/png;base64," + sourcePng : null;
}

export function hasOriginal(el) {
  return !!el && (el.type === "image" || el.type === "digitized") && !!originalDataUrl(el.sourcePng);
}

// Aspect-preserving fit of an image inside `rect`, centred. The rect is the
// one the element's own stitches occupy, so flipping Original <-> Stitches
// compares like with like at the same place and size.
export function fitRect(imgW, imgH, rect) {
  if (!rect || !(imgW > 0) || !(imgH > 0) || !(rect.w > 0) || !(rect.h > 0)) return null;
  const s = Math.min(rect.w / imgW, rect.h / imgH);
  const w = imgW * s;
  const h = imgH * s;
  return { x: rect.x + (rect.w - w) / 2, y: rect.y + (rect.h - h) / 2, w, h };
}

const cache = new Map();
export function loadOriginal(sourcePng) {
  const url = originalDataUrl(sourcePng);
  if (!url) return Promise.reject(new Error("no original"));
  if (cache.has(sourcePng)) return cache.get(sourcePng);
  const p = new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => resolve(im);
    im.onerror = () => { cache.delete(sourcePng); reject(new Error("original failed to decode")); };
    im.src = url;
  });
  cache.set(sourcePng, p);
  return p;
}
```

- [ ] **Step 4: Run the spec**

Run: `cd app && npx vitest run src/lib/originalImage.spec.js`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/originalImage.js app/src/lib/originalImage.spec.js
git commit -m "studio: originalImage — the uploaded artwork, fitted to the design's rect"
```

---

### Task 6: The Original view on the field

**Files:**
- Modify: `app/src/lib/settingHelp.js` (after the `realistic` entry, ~line 150)
- Modify: `app/src/ui/EmbroideryField.svelte` (view state ~L169–180; `paint()` ~L1587; `repaintView()` ~L1743; the View segment markup ~L3086–3118)
- Modify: `app/e2e/configurator-smoke.spec.js` (one new test)

**Interfaces:**
- Consumes: `hasOriginal`, `loadOriginal`, `fitRect` (Task 5); the field's own `perElementRects` (`{ id, x, y, w, h }` in CSS px, rebuilt by every `paint()`/`repaintView()`), `renderRealistic(..., { limitStrands })`, `scheduleViewRepaint()`, `stopSim()`.

- [ ] **Step 1: The tip text**

In `settingHelp.js`, after the `realistic` entry:

```js
  originalView: {
    title: "Original view",
    what: "Shows the artwork you uploaded in place of the stitches, at the same spot and size.",
    changes: "The view only. Nothing about the design or the file changes.",
    when: "Flip between this and the stitches to check the digitizing against what you asked for.",
  },
```

- [ ] **Step 2: View state**

Beside `let realisticView = true;` add:

```js
  // Original view (spec §4): the uploaded artwork in place of the thread.
  // View-only, like zoom — never saved, and any regeneration drops it,
  // because a regenerated design is the thing the customer now wants to see.
  let originalView = false;
  $: anyOriginal = !!(project && project.elements && project.elements.some(hasOriginal));
  $: if (!anyOriginal && originalView) originalView = false;
  function showOriginal() {
    if (simActive) stopSim();
    originalView = true;
    scheduleViewRepaint();
  }
```

Import `hasOriginal, loadOriginal, fitRect` from `"../lib/originalImage.js"`. In `showFlat` and `showRealistic` add `if (originalView) { originalView = false; scheduleViewRepaint(); }` as their first line (they already stop the simulator). In `startSim` (find it — it sets `simActive = true`) add `originalView = false;`. At the top of `paint()` — right after `stopSim();` — add `originalView = false;`.

- [ ] **Step 3: Paint it**

In `repaintView()`, the `renderRealistic` call's options gain one line — `limitStrands` already exists for the simulator:

```js
        limitStrands: originalView ? 0 : simActive ? Math.floor(simIndex) : undefined,
```

and after the `perElementRects` loop in `repaintView()`, before `if (!simActive) drawOverlay();`, add:

```js
      if (originalView) { drawOriginals(); return; }
```

Then define, next to `drawOverlay`:

```js
  // Draws each element's uploaded artwork into the rect its stitches occupy.
  // Same CSS-px coordinate space drawOverlay uses — it sets the same dpr
  // transform for itself, for the same reason: it can run without a render
  // having just left one. A token guards the awaits: a view change or a
  // regeneration during a decode must not paint over the new frame.
  let originalToken = 0;
  async function drawOriginals() {
    const my = ++originalToken;
    const jobs = (project.elements || []).filter(hasOriginal).map(async (el) => {
      const rect = perElementRects.find((r) => r.id === el.id);
      if (!rect) return;
      let im;
      try { im = await loadOriginal(el.sourcePng); } catch (e) { return; }
      if (my !== originalToken || !originalView || !canvas) return;
      const box = fitRect(im.naturalWidth, im.naturalHeight, rect);
      if (!box) return;
      const ctx = canvas.getContext("2d");
      ctx.save();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.drawImage(im, box.x, box.y, box.w, box.h);
      ctx.restore();
    });
    await Promise.all(jobs);
  }
```

Read `drawOverlay`'s first ten lines before writing this: use EXACTLY the transform call it uses (if it is not `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)`, copy what is there). Bump `originalToken` (`originalToken++`) wherever `originalView` is set to `false`, so an in-flight decode cannot paint after the view left.

- [ ] **Step 4: The segment**

After the `Simulate` button inside `<span class="viewseg" role="group" aria-label="View">`:

```svelte
        <button
          type="button"
          class="zoombtn viewseg-btn viewseg-orig"
          class:viewseg-on={originalView}
          on:click={showOriginal}
          disabled={!hasDesign || !anyOriginal}
          aria-pressed={originalView}
          aria-label="Original view"
          use:tip={"originalView"}
        >Original</button>
```

and change the three existing `class:viewseg-on` / `aria-pressed` expressions so they are false while `originalView` is true: `!realisticView && !simActive && !originalView`, `realisticView && !simActive && !originalView`, `simActive` (unchanged — `showOriginal` stops the simulator).

No thumbnail in the segment: a fourth text segment matches the other three, and an image inside one of four equal segments would be the only picture in the bar. (Decision recorded so PR 4 does not re-open it.)

- [ ] **Step 5: The e2e**

Append to `configurator-smoke.spec.js`:

```js
test("Original view swaps the thread for the uploaded artwork, and any edit swaps it back", async ({ page }) => {
  await page.route("**/health", (r) => r.abort());   // browser lane: an `image` element, no service
  await startStudio(page);
  const orig = page.getByRole("button", { name: "Original view" });
  // A text-only design has no artwork to show.
  await typeText(page, "ABC");
  await expect(orig).toBeDisabled();

  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator("input[type=file]").first().setInputFiles(ART_PNG);
  await expect(page.locator("span.stats")).toBeVisible({ timeout: 60_000 });
  await expect(orig).toBeEnabled();

  const shot = () => page.evaluate(() => document.querySelector(".hoop canvas").toDataURL());
  const stitched = await shot();

  await orig.click();
  await expect(orig).toHaveAttribute("aria-pressed", "true");
  await expect.poll(shot).not.toBe(stitched);
  // No chrome was added over the canvas to do it.
  expect(await page.locator(".hoop > *").count()).toBe(1);

  await page.getByRole("button", { name: "Realistic view" }).click();
  await expect(orig).toHaveAttribute("aria-pressed", "false");
  await expect.poll(shot).toBe(stitched);
});
```

`ART_PNG` is already defined at the top of the file. If the final `toBe(stitched)` proves flaky because the realistic render is not byte-stable between two paints, replace it with `await expect.poll(shot).not.toBe(await originalShot)` where `originalShot` is captured while Original is lit — the assertion that matters is that the view left Original.

- [ ] **Step 6: Run**

Run: `cd app && npx vite build 2>&1 | tail -2; npx playwright test e2e/configurator-smoke.spec.js e2e/field-chrome.spec.js --workers=1 --reporter=list > ../e2e-pr2-t6.log 2>&1; echo "EXIT=$?" >> ../e2e-pr2-t6.log`
Expected: build succeeds; `EXIT=0`; `field-chrome`'s `.hoop > *` count of 1 still holds.

- [ ] **Step 7: Look at it**

From the worktree: `npm run dev -- --port 5190 --strictPort` in the background, `preview_start` with `http://localhost:5190`. Upload `e2e/fixtures/two-squares.png` as Artwork (or drive it by `form_input` on the file input), click Original, screenshot; click Realistic, screenshot. The artwork must sit where the stitches sat. Stop the server afterwards.

- [ ] **Step 8: Commit**

```bash
git add app/src/lib/settingHelp.js app/src/ui/EmbroideryField.svelte app/e2e/configurator-smoke.spec.js
git commit -m "studio: Original view — the uploaded artwork where the stitches sit"
```

---

### Task 7: Docs, verify, PR

**Files:**
- Modify: `MASTER_SCOPE.md` (area 3 row and body), `docs/scope/3-studio-app-wizard.md` (dated paragraph at the top)

- [ ] **Step 1: Docs**

Area doc: a dated paragraph — the tile grid is gone; `GarmentPicker` (three pills, a fourth for anything else, More › menu of ten); Original is a fourth View segment painted on the canvas into each element's own rect, view-only; the two departures from spec §4 and why (DOCTRINE no-chrome rule; like-for-like compare). MASTER_SCOPE row 3: append one sentence with a `(verb date — source)` pointer naming `GarmentPicker.spec.js` and the smoke test. No net line growth in MASTER_SCOPE.

- [ ] **Step 2: Full unit suite**

Run: `cd app && npx vitest run --hookTimeout=90000 --testTimeout=60000 > ../unit-pr2.log 2>&1; echo "EXIT=$?" >> ../unit-pr2.log; tail -6 ../unit-pr2.log`
Expected: `EXIT=0`, zero failures.

- [ ] **Step 3: e2e, no-service group**

Run: `cd app && npx playwright test e2e/configurator-smoke.spec.js e2e/design-naming.spec.js e2e/design-import.spec.js e2e/download-machine.spec.js e2e/font-load-failure.spec.js e2e/storage-full.spec.js e2e/typographic-punctuation.spec.js e2e/touch-drawing-tools.spec.js e2e/field-chrome.spec.js e2e/worksheet-numbers.spec.js --workers=1 --reporter=list > ../e2e-pr2.log 2>&1; echo "EXIT=$?" >> ../e2e-pr2.log; tail -15 ../e2e-pr2.log`
Expected: `EXIT=0`. Service-backed specs: CI's `studio-e2e`.

- [ ] **Step 4: Merge `origin/main`** (PR #585 must have landed; if it has not, the PR targets `claude/configurator-structure` instead and says so).

- [ ] **Step 5: Dispatch `emb-bot-reviewer`** on the branch; fix what is real.

- [ ] **Step 6: Open the PR ready-for-review**, body: spec link, the two §4 departures stated up front, screenshots from Task 6 Step 7, unit and e2e counts with recorded exit codes. Arm auto-merge while `mergeable_state` is `blocked`.
