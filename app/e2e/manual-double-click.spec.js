// End-to-end for the gesture half of MASTER_SCOPE defect 55: a hand-drawn
// shape finished with a double-click whose second click SLIPS.
//
// A double-click is two clicks and then a `dblclick`, and the pointer moves
// between them. The side canvas used to take the second click as an anchor
// unless it landed within half a canvas pixel of the first, so a slip of one
// screen pixel left an anchor a pixel from the last one: a short edge that
// doubles back, which the fill's pull compensation then put a spike on.
//
// Only a real browser makes the events in question (the click count on the
// second click, then `dblclick`), so this is driven with the mouse itself:
// down and up once on the corner, then down and up with a click count of two
// a pixel away. ManualPanel.spec.js holds the same rule at component level.
//
// What is read is the shape as the app SAVED it, where a slipped anchor would
// stay for good. No digitizer service is involved.
import { test, expect } from "@playwright/test";
import { pickGarment } from "./helpers.js";

async function openDrawing(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await pickGarment(page, "Tote");
  await page.locator(".hoop canvas").click({ button: "right" });
  await page.locator(".fieldmenu button").filter({ hasText: "Draw shapes" }).click();
  await expect(page.locator(".mp-canvas")).toBeVisible();
}

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

// Three corners clicked, the fourth double-clicked with the second click
// `slip` screen px off the first.
async function drawBoxFinishedByDoubleClick(page, slip) {
  const box = await page.locator(".mp-canvas").boundingBox();
  const at = (fx, fy) => [box.x + box.width * fx, box.y + box.height * fy];
  for (const [fx, fy] of [[0.3, 0.3], [0.7, 0.3], [0.7, 0.7]]) await page.mouse.click(...at(fx, fy));
  const [x, y] = at(0.3, 0.7);
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.up();
  await page.mouse.move(x + slip[0], y + slip[1]);
  await page.mouse.down({ clickCount: 2 });
  await page.mouse.up({ clickCount: 2 });
}

for (const slip of [[0, 0], [-1, 1], [1, 2], [-2, -1]]) {
  test(`a box finished with a double-click that slips ${slip.join(", ")} px is the four corners clicked`, async ({ page }) => {
    await openDrawing(page);
    await drawBoxFinishedByDoubleClick(page, slip);
    await expect.poll(async () => (await savedShapes(page)).length, { timeout: 15_000 }).toBe(1);
    const [shape] = await savedShapes(page);
    expect(shape.points).toHaveLength(4);
    // and nothing was started by the second click
    await expect(page.getByRole("button", { name: "Undo point" })).toBeDisabled();
  });
}
