// End-to-end test for "trace an uploaded image into starting manual-
// digitizing shapes" (PR 3 of 3): the one thing PR 2's own component specs
// (TraceImportPanel.spec.js / ManualPanel.spec.js) deliberately did NOT
// cover -- a REAL file upload through a REAL createImageBitmap/canvas-decode
// path (jsdom has neither; see those files' own banners). This drives the
// whole stack for real:
//
//   Draw-shapes mode -> "Trace image..." -> upload a real PNG -> the real
//   trace pipeline (app/src/lib/manualTrace.js, PR 1) runs against the
//   decoded pixels -> preview shows the right shape/color counts and the
//   hole-dropped warning -> "Add N shapes" -> the traced shapes land on
//   ManualPanel's own main canvas -> the first traced shape is selected on
//   the DESIGN canvas (the hoop) and one of its anchors is dragged there, and
//   the stitch count changes.
//
// Unlike digitize-boundary-edit.spec.js / digitize-shape-identity.spec.js
// (DigitizePanel, the real Python digitizer service), manualTrace.js is
// pure client-side JS -- no service to boot, no skip-if-offline dance here.
//
// The first traced shape is the green ring-square (colorRgb [10,150,10] in
// the fixture PNG), so the spec finds it on the hoop by thread colour rather
// than by guessed coordinates: the bounding box of the green pixels IS the
// shape's box, and its top-left corner is where the anchor sits.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_PNG = path.join(__dirname, "fixtures", "trace-holes-and-colors.png");

test("upload -> trace preview (colors + hole warning) -> add shapes -> drag an anchor on the design canvas", async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  // Drawing tools left the tile row on 2026-08-13 (Kent's call) and live on
  // the canvas itself now: right-click the design field, pick the tool. Same
  // element type and panel on the other side of it — only the way in moved.
  await page.locator("canvas").first().click({ button: "right" });
  await expect(page.locator(".fieldmenu")).toBeVisible();
  await page.getByRole("menuitem", { name: "Draw shapes" }).click();
  await expect(page.locator(".fieldmenu")).toBeHidden();

  // ---- open the trace panel, upload the real fixture ---------------------
  await page.getByRole("button", { name: "Trace image…" }).click();
  await expect(page.locator(".tip-upload")).toBeVisible();
  await page.locator(".tip-upload input[type=file]").setInputFiles(FIXTURE_PNG);

  // Real decode takes a moment -- wait for the real preview/legend/Add-count
  // to settle rather than sleeping. The fixture (see its own generation
  // notes / app/src/lib/manualTrace.spec.js's proven annulus + touching-
  // block fixtures) traces to exactly 3 shapes: the two touching red/blue
  // blocks (never merged, different colors) plus the ring, whose interior
  // hole gets dropped with exactly one warning.
  const addBtn = page.getByRole("button", { name: /^Add \d+ shapes?$/ });
  await expect(addBtn).toHaveText("Add 3 shapes", { timeout: 15_000 });
  await expect(page.locator(".tip-preview")).toBeVisible();
  await expect(page.locator(".tip-swatch")).toHaveCount(3);

  const warnings = page.locator(".tip-warnings li");
  await expect(warnings).toHaveCount(1);
  await expect(warnings.first()).toContainText("interior hole");

  // ---- add the traced batch onto the real manual-digitizing canvas -------
  await addBtn.click();
  await expect(page.locator(".tip-upload")).toHaveCount(0); // panel closes itself on a successful add
  const rows = page.locator(".mp-shaperow");
  await expect(rows).toHaveCount(3);

  // ---- edit the first traced shape ON THE DESIGN CANVAS ------------------
  // The side canvas only draws now; a finished shape's points are edited on
  // the hoop (EmbroideryField + fieldNodeEdit.js). The first traced shape is
  // the green ring-square (colorRgb [10,150,10] in the fixture PNG), so find its
  // thread on the hoop canvas by colour, click inside it to select it (this
  // opens its popover), Escape the popover, then drag the anchor at its
  // top-left corner by (+40, -40) CSS px.
  const stats = page.locator("span.stats");
  await expect(stats).toContainText(/\d[\d,]* stitches/, { timeout: 20_000 });
  const hoop = page.locator(".hoop canvas");
  const greenBox = () => page.evaluate(() => {
    const c = document.querySelector(".hoop canvas");
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let x0 = c.width, y0 = c.height, x1 = -1, y1 = -1;
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) {
      const i = (y * c.width + x) * 4;
      if (d[i] < 50 && d[i + 2] < 50 && d[i + 1] > 110) {
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
    }
    return x1 < 0 ? null : { x0, y0, x1, y1, cw: c.width };
  });
  // Settle: three consecutive reads (300 ms apart) agree on the thread's box.
  // Read it AGAIN after the popover closes -- selecting a shape re-fits the
  // hoop's view (measured 2026-09-29: the box shrank ~18% and shifted), so a
  // box read before the click is stale by the time the drag starts.
  const settledBox = async () => {
    let box = null;
    await expect.poll(async () => {
      const reads = [];
      for (let i = 0; i < 3; i++) { reads.push(JSON.stringify(await greenBox())); await page.waitForTimeout(300); }
      box = JSON.parse(reads[0]);
      return box !== null && reads.every((r) => r === reads[0]);
    }, { timeout: 20_000 }).toBe(true);
    return box;
  };
  const centre = async (box) => {
    const hb = await hoop.boundingBox();
    const k = hb.width / box.cw; // canvas px -> CSS px
    return { hb, k, cx: hb.x + ((box.x0 + box.x1) / 2) * k, cy: hb.y + ((box.y0 + box.y1) / 2) * k };
  };
  const first = await centre(await settledBox());
  await page.mouse.click(first.cx, first.cy);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  const gb = await settledBox();
  const { hb, k } = await centre(gb);
  const cornerX = hb.x + gb.x0 * k, cornerY = hb.y + gb.y0 * k;
  const before = await stats.innerText();
  await page.mouse.move(cornerX, cornerY);
  await page.mouse.down();
  await page.mouse.move(cornerX + 40, cornerY - 40, { steps: 8 });
  await page.mouse.up();

  // The anchor drag reshapes the shape: the caption's stitch count moves,
  // and the shape survives under the same row/id.
  await expect.poll(() => stats.innerText(), { timeout: 20_000 }).not.toBe(before);
  await expect(rows).toHaveCount(3);
});
