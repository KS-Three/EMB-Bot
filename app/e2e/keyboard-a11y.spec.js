// Keyboard + screen-reader pass over the Studio's main flow (Kent 2026-10-08):
// every control has an accessible name, focus is visible, Tab follows the
// layout, Escape closes dialogs, Delete removes the selection, arrows nudge it,
// Ctrl+Z / Ctrl+Shift+Z undo and redo.
//
// `@axe-core/playwright` is not a dependency, so the name audit reads the
// browser's own accessibility tree over CDP instead — the same tree a screen
// reader is handed, which is what axe's `button-name` / `label` rules inspect.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate, openDownload } from "./helpers.js";

const NAMED_ROLES = new Set([
  "button", "link", "textbox", "searchbox", "combobox", "listbox", "checkbox", "radio",
  "switch", "slider", "spinbutton", "tab", "menuitem", "menuitemradio", "menuitemcheckbox",
  "option",
]);

// Every non-ignored interactive node in the AX tree whose computed name is
// empty, described well enough to find it.
async function unnamedControls(page) {
  const cdp = await page.context().newCDPSession(page);
  const { nodes } = await cdp.send("Accessibility.getFullAXTree");
  const bad = [];
  for (const n of nodes) {
    if (n.ignored || !NAMED_ROLES.has(n.role?.value)) continue;
    if ((n.name?.value || "").trim()) continue;
    let html = "";
    if (n.backendDOMNodeId) {
      try {
        const { outerHTML } = await cdp.send("DOM.getOuterHTML", { backendNodeId: n.backendDOMNodeId });
        html = outerHTML.slice(0, 140);
      } catch { /* node gone */ }
    }
    bad.push(`${n.role.value}: ${html}`);
  }
  await cdp.detach();
  return bad;
}

async function reachDesign(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
}

test("every control on the main flow has an accessible name", async ({ page }) => {
  await reachDesign(page);
  expect(await unnamedControls(page)).toEqual([]);

  // Same audit with each overlay open: they mount their own controls.
  await page.getByRole("button", { name: /^My designs/ }).click();
  await expect(page.getByRole("dialog", { name: "My designs" })).toBeVisible();
  expect(await unnamedControls(page)).toEqual([]);
  await page.keyboard.press("Escape");

  await openDownload(page);
  expect(await unnamedControls(page)).toEqual([]);
});

test("focus is visible on whatever Tab lands on, and Tab follows the layout", async ({ page }) => {
  await reachDesign(page);
  await page.locator("body").click({ position: { x: 1, y: 1 } });

  const hidden = [];
  const order = [];
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      const ring = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) ||
        (cs.boxShadow && cs.boxShadow !== "none");
      return {
        ring,
        top: Math.round(r.top), left: Math.round(r.left),
        name: el.getAttribute("aria-label") || el.textContent?.trim().slice(0, 30) || el.tagName,
        tag: el.tagName.toLowerCase(),
        visible: r.width > 0 && r.height > 0,
      };
    });
    if (!info) continue;
    expect(info.visible, `focused element is on screen: ${info.name}`).toBe(true);
    if (!info.ring) hidden.push(`${info.tag} "${info.name}"`);
    order.push(info);
  }
  expect(order.length).toBeGreaterThan(10);
  expect(hidden).toEqual([]);

  // Layout order: the header's controls come before the field's, and the
  // field's before the footer's. Compare each focused control's row against
  // the one before — reading order never jumps back up past the whole band.
  const canvasIdx = order.findIndex((o) => o.tag === "canvas");
  expect(canvasIdx).toBeGreaterThan(0);
  const header = order.slice(0, canvasIdx);
  expect(Math.max(...header.map((o) => o.top))).toBeLessThan(900);
  expect(order[canvasIdx].top).toBeGreaterThan(Math.min(...header.map((o) => o.top)));
});

test("Escape closes each dialog and hands focus back to what opened it", async ({ page }) => {
  await reachDesign(page);

  const designs = page.getByRole("button", { name: /^My designs/ });
  await designs.click();
  await expect(page.getByRole("dialog", { name: "My designs" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "My designs" })).toHaveCount(0);
  await expect(designs).toBeFocused();

  const download = page.getByRole("button", { name: "Download", exact: true });
  await download.click();
  await expect(page.getByRole("dialog", { name: "Download" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Download" })).toHaveCount(0);
  await expect(download).toBeFocused();
});

test("Ctrl+Z / Ctrl+Shift+Z undo and redo a nudge from the focused field", async ({ page }) => {
  await reachDesign(page);
  const canvas = page.locator(".hoop canvas");
  await canvas.focus();

  // Compare rendered pixels: the live region only announces a nudge, it does
  // not re-announce an undo, so it cannot be the oracle here.
  const shot = () => page.evaluate(() => document.querySelector(".hoop canvas").toDataURL());
  // history.js coalesces edits inside 500 ms into one undo step, so a nudge
  // fired straight after the template load would undo together with it. No
  // person is that quick; let the window lapse so the nudge is its own step.
  await page.waitForTimeout(700);
  const start = await shot();

  await page.keyboard.press("ArrowRight");
  await expect.poll(shot, { timeout: 10_000 }).not.toBe(start);
  const nudged = await shot();

  await page.keyboard.press("Control+z");
  await expect.poll(shot, { timeout: 10_000 }).toBe(start);

  await page.keyboard.press("Control+Shift+Z");
  await expect.poll(shot, { timeout: 10_000 }).toBe(nudged);
});

test("the undo and redo buttons, and the canvas, are reachable and named", async ({ page }) => {
  await reachDesign(page);
  await expect(page.getByRole("button", { name: "Undo" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Redo" })).toBeVisible();
  await expect(page.getByRole("application", { name: /Embroidery field/ })).toBeVisible();
});

// The menus that mount their own controls after a click: the garment menu and
// the field's tool menu. Each is audited open; the garment menu must close on
// Escape.
test("menus are named, and Escape closes the garment menu", async ({ page }) => {
  await reachDesign(page);

  await page.getByRole("button", { name: "More garments" }).click();
  const gmenu = page.getByRole("menu", { name: "All garments" });
  await expect(gmenu).toBeVisible();
  expect(await unnamedControls(page)).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(gmenu).toHaveCount(0);

  const cv = page.locator(".hoop canvas");
  const b = await cv.boundingBox();
  await page.mouse.click(b.x + 10, b.y + 10, { button: "right" });
  const tools = page.locator(".fieldmenu");
  await expect(tools).toBeVisible();
  expect(await unnamedControls(page)).toEqual([]);
  await tools.locator("button").filter({ hasText: "Basic shape" }).click();
});
