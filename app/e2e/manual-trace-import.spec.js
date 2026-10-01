// End-to-end test for "trace an uploaded image into starting manual-
// digitizing shapes" (PR 3 of 3): the one thing PR 2's own component specs
// (TraceImportPanel.spec.js / ManualPanel.spec.js) deliberately did NOT
// cover -- a REAL file upload through a REAL createImageBitmap/canvas-decode
// path (jsdom has neither; see those files' own banners). This drives the
// whole stack for real:
//
//   Draw-shapes mode -> "Trace image..." -> upload a real PNG -> the real
//   trace pipeline (app/src/lib/manualTrace.js, PR 1) runs against the
//   decoded pixels -> preview shows the right shape/color counts and no
//   hole warning -> "Add N shapes" -> the traced shapes (the ring's hole
//   among them, as a Cut out shape) land on
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
import { pickGarment } from "./helpers.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_PNG = path.join(__dirname, "fixtures", "trace-holes-and-colors.png");

test("upload -> trace preview (colors, hole kept as a cut-out) -> add shapes -> drag an anchor on the design canvas", async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto("/");
  await pickGarment(page, "Tote");
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
  // block fixtures) traces to the two touching red/blue blocks (never
  // merged, different colors) plus the ring. Until 2026-10-01 the ring's
  // interior hole was dropped with an "interior hole" warning; it now
  // arrives as a Cut out shape right after its parent, with no warning
  // (manual-holes plan Task 7). The fallback that still drops a hole says
  // "A traced hole could not be kept ..." -- so the absence of BOTH texts is
  // asserted, not just an empty list.
  const addBtn = page.getByRole("button", { name: /^Add \d+ shapes?$/ });
  await expect(addBtn).toHaveText("Add 4 shapes", { timeout: 15_000 });
  await expect(page.locator(".tip-preview")).toBeVisible();
  await expect(page.locator(".tip-swatch")).toHaveCount(3);

  await expect(page.locator(".tip-warnings li")).toHaveCount(0);
  await expect(page.getByText(/interior hole|traced hole could not be kept/)).toHaveCount(0);

  // ---- add the traced batch onto the real manual-digitizing canvas -------
  await addBtn.click();
  await expect(page.locator(".tip-upload")).toHaveCount(0); // panel closes itself on a successful add
  const rows = page.locator(".mp-shaperow");
  await expect(rows).toHaveCount(4);
  // The ring's hole is a cut-out row, and it cuts its ring: the row ENDS at
  // its name, with no "cuts nothing" reason line under it.
  const cutRows = rows.filter({ hasText: "· Cut out" });
  await expect(cutRows).toHaveCount(1);
  await expect(cutRows.first()).toHaveText(/^\s*Shape \d+ · Cut out\s*$/);

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
  // Since 2026-10-01 the ring's middle is its CUT-OUT (Shape 2), and a click
  // there selects that, whose anchors are not at the green box's corner. So
  // the click goes into the ring's band (15% in from its left edge, which the
  // fixture's hole -- its middle third -- never reaches), and the popover must
  // name the ring. The field's drag hint is closed by its own X first: the
  // first press on the field dismisses it and moves the canvas ~76 px, which
  // would land the release somewhere other than the press.
  const dismiss = page.getByRole("button", { name: "Dismiss hint" });
  if (await dismiss.count()) { await dismiss.first().click(); await expect(dismiss).toHaveCount(0); }
  const box0 = await settledBox();
  const first = await centre(box0);
  await page.mouse.click(first.hb.x + (box0.x0 + 0.15 * (box0.x1 - box0.x0)) * first.k, first.cy);
  await expect(page.getByRole("dialog")).toHaveAttribute("aria-label", "Shape 1 · Fill");
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
  await expect(rows).toHaveCount(4);
});
