// Undo/redo EDGE CASES in the Studio (foreman's ask, 2026-10-08). The happy
// path (colour change, Undo, Redo) lives in core-flows.spec.js; this file
// pins the awkward ones: undo after digitize / delete / colour / resize, a
// new action killing the redo branch, and the 100-step history limit
// (lib/history.js). Everything but the digitize test runs on the browser
// lettering lane off the "Left-chest name" template.
//
// A test marked `test.fail()` pins a bug on main TODAY: it passes while the
// bug stands, turns red when someone fixes it, and that PR deletes the line.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate, pickGarment, uploadArtwork, runDigitize, openAdvanced } from "./helpers.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
const SERVICE_URL = "http://127.0.0.1:8721";

const undo = (page) => page.getByRole("button", { name: "Undo" });
const redo = (page) => page.getByRole("button", { name: "Redo" });
const swatch = (page) => page.getByRole("button", { name: /^Thread color — / }).first();
const rows = (page) => page.locator(".elrow");

async function lettering(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
  const hint = page.getByRole("button", { name: "Dismiss hint" }).first();
  if (await hint.isVisible().catch(() => false)) await hint.click();
  await expect(page.locator(".hoop canvas")).toBeVisible();
  // NOT asserted: Undo disabled. Loading the template is itself a recorded
  // step, so history already holds one entry. Tests below are relative.
}

// Pick a colour by its swatch-cell name; returns the new aria-label.
async function pickColour(page, nth = 0, notName = null) {
  const sw = swatch(page);
  const cur = (await sw.getAttribute("aria-label")).replace(/^Thread color — /, "");
  await sw.click();
  const cell = page.locator(`button.tp-cell:not([aria-label="${notName ?? cur}"])`).nth(nth);
  await expect(cell).toBeVisible();
  const name = await cell.getAttribute("aria-label");
  await cell.click();
  await page.keyboard.press("Escape");
  await expect(sw).toHaveAttribute("aria-label", `Thread color — ${name}`);
  return name;
}

const widthInput = (page) => page.getByLabel("Width", { exact: true }).first();

// The mm box shows the width the design SEWS, to a tenth (2026-11-14; it was
// whole millimetres, which hid a 60.2 behind "60"). Lettering sews a little
// over what is typed (pull compensation), so "the box shows what I typed" is
// within half a millimetre, not string equality.
async function expectWidthNear(w, mm) {
  await expect.poll(async () => Math.abs(parseFloat(await w.inputValue()) - mm)).toBeLessThan(0.5);
}

async function setWidth(page, mm) {
  const unit = page.getByLabel("Size unit").first();
  if ((await unit.inputValue()) !== "mm") await unit.selectOption("mm");
  const w = widthInput(page);
  await w.fill(String(mm));
  await w.press("Tab");
  await expectWidthNear(w, mm);
}

test("undo after a colour change restores the colour; Redo re-applies it", async ({ page }) => {
  await lettering(page);
  const before = await swatch(page).getAttribute("aria-label");
  const picked = await pickColour(page);
  await expect(undo(page)).toBeEnabled();
  await undo(page).click();
  await expect(swatch(page)).toHaveAttribute("aria-label", before);
  await expect(redo(page)).toBeEnabled();
  await redo(page).click();
  await expect(swatch(page)).toHaveAttribute("aria-label", `Thread color — ${picked}`);
  await expect(redo(page)).toBeDisabled();
});

test("undo after a resize restores the previous width", async ({ page }) => {
  await lettering(page);
  const w = widthInput(page);
  await expect(w).toBeVisible();
  // Past history.js's 500 ms coalesce window: a width typed inside it REPLACES
  // the template load's step, so one Undo goes back to an empty project (no
  // design, an empty box). The old string checks passed on that empty box; the
  // numeric ones above do not (they read NaN), which is how this showed.
  await page.waitForTimeout(600);
  await setWidth(page, 60);
  await undo(page).click();
  await expect.poll(async () => Math.abs(parseFloat(await w.inputValue()) - 60)).toBeGreaterThanOrEqual(0.5);
  const original = await w.inputValue();
  await redo(page).click();
  await expectWidthNear(w, 60);
  await undo(page).click();
  await expect(w).toHaveValue(original);
});

test("undo after deleting an element brings it back; redo deletes it again", async ({ page }) => {
  await lettering(page);
  await expect(rows(page)).toHaveCount(1);
  await openAdvanced(page);
  await page.locator(".eladd", { hasText: "Text" }).click();
  await expect(rows(page)).toHaveCount(2);
  await page.waitForTimeout(600);        // past history.js's 500 ms coalesce window
  await page.getByRole("button", { name: "Remove element" }).last().click();
  await expect(rows(page)).toHaveCount(1);
  await undo(page).click();
  await expect(rows(page)).toHaveCount(2);
  await redo(page).click();
  await expect(rows(page)).toHaveCount(1);
  // Two more undos walk back through the add (and past it) -- never to zero rows.
  await undo(page).click();
  await undo(page).click();
  await expect(rows(page)).toHaveCount(1);
});

test("deleting an element right after adding it can still be undone", async ({ page }) => {
  // Was a pinned bug until 2026-11-12: history.record() coalesced ANY two
  // records inside 500 ms, so an add and a delete in quick succession merged
  // into one step -- Undo then skipped straight back past the add and the
  // deleted element was not restored. Adding and removing an element are now
  // discrete records (App.svelte persistStructural), each its own undo step;
  // the drag-storm coalescing stays for continuous gestures.
  await lettering(page);
  await openAdvanced(page);
  await page.locator(".eladd", { hasText: "Text" }).click();
  await expect(rows(page)).toHaveCount(2);
  await page.getByRole("button", { name: "Remove element" }).last().click();
  await expect(rows(page)).toHaveCount(1);
  await undo(page).click();
  await expect(rows(page)).toHaveCount(2);
  // The add is its own step too: a second Undo takes it back, Redo re-adds it.
  await undo(page).click();
  await expect(rows(page)).toHaveCount(1);
  await redo(page).click();
  await expect(rows(page)).toHaveCount(2);
});

// The first element's vertical offset, from the project the app keeps in localStorage.
function savedOffsetY(page) {
  return page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const project = id && JSON.parse(localStorage.getItem("embstudio:p:" + id) || "null");
    const el = project && (project.elements || [])[0];
    return el ? el.offsetYMm || 0 : null;
  });
}

test("one drag is one undo step, even when the pointer rests mid-drag, and the next drag is its own", async ({ page }) => {
  // Until 2026-11-13 history.js split field drags on its 500 ms clock: a
  // drag held still for 0.7 s undid in two steps, and two drags under
  // 500 ms apart in one. Each drag's flushes now carry its press's token.
  await lettering(page);
  const canvas = page.locator(".hoop canvas");
  const box = await canvas.boundingBox();
  const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
  const start = await savedOffsetY(page);

  await page.mouse.move(cx, cy);
  await page.mouse.down();
  await page.mouse.move(cx, cy + 15, { steps: 6 });
  await expect.poll(() => savedOffsetY(page)).not.toBe(start);
  await page.waitForTimeout(700); // rest, button still down
  await page.mouse.move(cx, cy + 30, { steps: 6 });
  await page.mouse.up();
  await expect.poll(() => savedOffsetY(page)).toBeLessThan(start - 2);
  const afterFirst = await savedOffsetY(page);

  // a second drag straight away, well inside 500 ms of the first
  await page.mouse.move(cx, cy + 30);
  await page.mouse.down();
  await page.mouse.move(cx, cy + 45, { steps: 4 });
  await page.mouse.up();
  await expect.poll(() => savedOffsetY(page)).toBeLessThan(afterFirst - 1);

  await undo(page).click();
  await expect.poll(() => savedOffsetY(page)).toBeCloseTo(afterFirst, 6);
  await undo(page).click();
  await expect.poll(() => savedOffsetY(page)).toBeCloseTo(start, 6);
});

// The hand-drawn element's shapes, from the project the app keeps in
// localStorage ([] until there is one).
function savedShapes(page) {
  return page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const project = id && JSON.parse(localStorage.getItem("embstudio:p:" + id) || "null");
    const manual = project && (project.elements || []).find((e) => e.type === "manual");
    return manual ? manual.shapes || [] : [];
  });
}

test("deleting a hand-drawn shape right after drawing it can still be undone", async ({ page }) => {
  // The element-level bug above, one level down: a shape drawn and deleted
  // inside history.js's 500 ms window coalesced into one step, so Undo went
  // back past the draw and the shape never returned. ManualPanel now sends a
  // shape added or removed as a discrete elupdate. No waits anywhere here on
  // purpose -- the draw and the delete must land inside the window.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await page.locator(".hoop canvas").click({ button: "right" });
  await page.locator(".fieldmenu button").filter({ hasText: "Draw shapes" }).click();
  await openAdvanced(page);
  const canvas = page.locator(".mp-canvas");
  await expect(canvas).toBeVisible();
  const box = await canvas.boundingBox();
  for (const [fx, fy] of [[0.3, 0.3], [0.7, 0.3], [0.5, 0.7]]) {
    await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
  }
  // "Undo" alone also matches the drawing panel's "Undo point" button.
  const undoBtn = page.getByRole("button", { name: "Undo", exact: true });
  const redoBtn = page.getByRole("button", { name: "Redo", exact: true });
  await canvas.focus();
  await page.keyboard.press("Enter");     // finishes the triangle and selects it
  await page.keyboard.press("Delete");    // ...and it is gone again, milliseconds later
  expect(await savedShapes(page)).toHaveLength(0);
  await undoBtn.click();                  // the delete alone
  await expect.poll(() => savedShapes(page).then((s) => s.length)).toBe(1);
  await undoBtn.click();                  // then the draw
  await expect.poll(() => savedShapes(page).then((s) => s.length)).toBe(0);
  await redoBtn.click();
  await expect.poll(() => savedShapes(page).then((s) => s.length)).toBe(1);
  await redoBtn.click();
  await expect.poll(() => savedShapes(page).then((s) => s.length)).toBe(0);
});

test("a new action after an undo clears the redo branch", async ({ page }) => {
  await lettering(page);
  const first = await pickColour(page, 0);
  await page.waitForTimeout(600);        // past history.js's 500 ms coalesce window
  await pickColour(page, 1, first);
  await undo(page).click();
  await expect(redo(page)).toBeEnabled();
  await page.waitForTimeout(600);
  // A different edit, made while a redo is pending, buries the redo.
  await setWidth(page, 70);
  await expect(redo(page)).toBeDisabled();
  await page.locator("body").click({ position: { x: 5, y: 5 } });
  await page.keyboard.press("Control+y");
  await expectWidthNear(widthInput(page), 70);
});

test("history keeps 100 snapshots: undoing past that stops after 99 steps", async ({ page }) => {
  test.setTimeout(240_000);
  // Each edit must land >500 ms after the last or it coalesces into it
  // (history.js). Waiting out 100 real half-seconds would be a minute of
  // dead air, so skew the page's clock instead.
  await page.addInitScript(() => {
    window.__skew = 0;
    const real = Date.now.bind(Date);
    Date.now = () => real() + window.__skew;
  });
  await lettering(page);
  const sw = swatch(page);
  const start = await sw.getAttribute("aria-label");
  const labels = [start];
  // 104 edits that each change the project: alternate two colours.
  const a = await (async () => { await sw.click(); const c = page.locator("button.tp-cell").nth(0); const n = await c.getAttribute("aria-label"); await page.keyboard.press("Escape"); return n; })();
  const b = await (async () => { await sw.click(); const c = page.locator("button.tp-cell").nth(1); const n = await c.getAttribute("aria-label"); await page.keyboard.press("Escape"); return n; })();
  expect(a).not.toBe(b);
  const EDITS = 104;
  for (let i = 0; i < EDITS; i++) {
    await page.evaluate(() => { window.__skew += 1000; });
    const have = (await sw.getAttribute("aria-label")).replace(/^Thread color — /, "");
    await sw.click();
    // Always pick a cell that differs from the current colour.
    const cell = page.locator(`button.tp-cell[aria-label="${have === a ? b : a}"]`).first();
    await cell.click();
    await page.keyboard.press("Escape");
    labels.push(`Thread color — ${have === a ? b : a}`);
  }
  await expect(undo(page)).toBeEnabled();
  let steps = 0;
  while (await undo(page).isEnabled()) {
    await undo(page).click();
    steps++;
    if (steps > 130) break;
  }
  // The stack holds 100 SNAPSHOTS (lib/history.js limit), i.e. 99 undo steps.
  expect(steps).toBe(99);
  // The oldest edits fell off: the earliest reachable state is the one after
  // edit 5, not the original colour.
  await expect(sw).toHaveAttribute("aria-label", labels[EDITS - 99]);
  await expect(redo(page)).toBeEnabled();
});

test("undo after Auto Digitize removes the digitized result and Redo restores it", async ({ page }) => {
  test.setTimeout(240_000);
  let up = false;
  for (let i = 0; i < 30 && !up; i++) {
    up = await fetch(SERVICE_URL + "/health").then((r) => r.ok).catch(() => false);
    if (!up) await new Promise((r) => setTimeout(r, 1000));
  }
  test.skip(!up, "digitizer service not reachable on 8721 (npm run dev starts it when digitizer/.venv exists)");
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await uploadArtwork(page, ART_PNG, { run: false });
  await runDigitize(page);
  const stats = page.locator("span.stats");
  await expect(stats).toHaveText(/[\d,]+ stitches/, { timeout: 120_000 });
  await expect(undo(page)).toBeEnabled();
  await undo(page).click();
  // Whatever the undo lands on, it must not leave the pre-digitize state
  // claiming the digitized stitch count, and Redo must bring the result back.
  await expect(redo(page)).toBeEnabled();
  await redo(page).click();
  await expect(stats).toHaveText(/[\d,]+ stitches/, { timeout: 30_000 });
});

test("hiding two digitized shapes back to back undoes one at a time", async ({ page }) => {
  // The same coalescing bug as the two "right after" tests above, on a
  // digitized element's Layers list: two shapes hidden inside history.js's
  // 500 ms window merged into one step, so one Undo brought BOTH back.
  // Hiding and restoring a shape are now discrete elupdates (DigitizePanel
  // patchShapeHidden; the field's Delete key sends the same). No waits
  // between the two clicks on purpose.
  test.setTimeout(240_000);
  let up = false;
  for (let i = 0; i < 30 && !up; i++) {
    up = await fetch(SERVICE_URL + "/health").then((r) => r.ok).catch(() => false);
    if (!up) await new Promise((r) => setTimeout(r, 1000));
  }
  test.skip(!up, "digitizer service not reachable on 8721 (npm run dev starts it when digitizer/.venv exists)");
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await uploadArtwork(page, ART_PNG, { run: false });
  await runDigitize(page);
  await expect(page.locator("span.stats")).toHaveText(/[\d,]+ stitches/, { timeout: 120_000 });
  await openAdvanced(page);
  await page.getByRole("tab", { name: "Shapes" }).click({ timeout: 120_000 });
  const rowsBtn = page.getByRole("button", { name: /^Edit shapes/ });
  await expect(rowsBtn).toBeVisible({ timeout: 120_000 });
  if ((await rowsBtn.getAttribute("aria-expanded")) !== "true") await rowsBtn.click();

  // The digitized element's hidden shape ids, as the app saved them.
  const hidden = () => page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const project = id && JSON.parse(localStorage.getItem("embstudio:p:" + id) || "null");
    const el = project && (project.elements || []).find((e) => e.type === "digitized");
    return el ? (el.deletedShapeIds || []).length : -1;
  });
  const hide = page.locator('button[aria-label^="Hide this shape — "]');
  expect(await hide.count()).toBeGreaterThanOrEqual(2);
  expect(await hidden()).toBe(0);
  // A hidden row swaps its Hide button for Restore, so first() is the next shape.
  await hide.first().click();
  await hide.first().click();
  expect(await hidden()).toBe(2);
  const undoBtn = page.getByRole("button", { name: "Undo", exact: true });
  const redoBtn = page.getByRole("button", { name: "Redo", exact: true });
  await undoBtn.click();                  // the second hide alone
  await expect.poll(hidden).toBe(1);
  await undoBtn.click();                  // then the first
  await expect.poll(hidden).toBe(0);
  await redoBtn.click();
  await expect.poll(hidden).toBe(1);
  await redoBtn.click();
  await expect.poll(hidden).toBe(2);
});
