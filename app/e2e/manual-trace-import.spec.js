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
//   ManualPanel's own main canvas -> a vertex on one of them is dragged
//   through the SAME, unmodified vertex editor hand-drawn shapes already
//   use, and the outline genuinely moves.
//
// Unlike digitize-boundary-edit.spec.js / digitize-shape-identity.spec.js
// (DigitizePanel, the real Python digitizer service), manualTrace.js is
// pure client-side JS -- no service to boot, no skip-if-offline dance here.
//
// Targeting the vertex-drag precisely (rather than guessing screen
// coordinates) uses a trick worth calling out: the exact canvas-space
// points the browser's preview/main-canvas will draw are fully
// deterministic from the fixture PNG's pixels (traceShapesFromRGBA has no
// randomness), so this file recomputes them in Node -- via the SAME
// manualTrace.js/manualShapes.js modules the app itself imports, fed the
// SAME fixture file decoded with the project's own tools/png.mjs decoder --
// once in beforeAll, then converts that one canvas-space vertex to a live
// page coordinate via the rendered canvas's actual boundingBox() (which is
// exactly what ManualPanel's own canvasPointFromEvent does in reverse). No
// coordinate here is guessed.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const FIXTURE_PNG = path.join(__dirname, "fixtures", "trace-holes-and-colors.png");
const BG_RGBA = [244, 242, 236, 255]; // ManualPanel's canvas background, "#f4f2ec"

let CANVAS_W, CANVAS_H;
// The first traced shape's canvas-space points, in the exact order/values
// the browser's own trace will produce -- see this file's banner.
let firstShapePoints;

test.beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "exp", "fonts", "digitize"]) {
    require(path.join(REPO_ROOT, "src", f + ".js"));
  }
  const { decodePNG } = await import(path.join(REPO_ROOT, "tools", "png.mjs"));
  const { traceShapesFromRGBA, rescaleTracedShapes } = await import(
    path.join(REPO_ROOT, "app", "src", "lib", "manualTrace.js")
  );
  const { CANVAS_W: W, CANVAS_H: H } = await import(path.join(REPO_ROOT, "app", "src", "lib", "manualShapes.js"));
  CANVAS_W = W;
  CANVAS_H = H;

  // Same decode path TraceImportPanel's prepRGBA takes for a file this small
  // (well under WORK_MAX_PX=480, so no downscale) -- see manualTrace.js's
  // own file banner for why this is the identical pipeline the browser runs.
  const { width, height, rgba } = decodePNG(FIXTURE_PNG);
  const { shapes } = traceShapesFromRGBA(rgba, width, height, { nColors: 6, removeBg: true });
  const rescaled = rescaleTracedShapes(shapes, width, height, CANVAS_W, CANVAS_H);
  firstShapePoints = rescaled[0].points;
});

// Converts a canvas-space (0..CANVAS_W, 0..CANVAS_H) point into a live page
// coordinate, using the rendered <canvas>'s actual displayed size -- the
// exact inverse of ManualPanel's own canvasPointFromEvent.
async function toPagePoint(canvasLocator, cx, cy) {
  const box = await canvasLocator.boundingBox();
  return { x: box.x + (cx / CANVAS_W) * box.width, y: box.y + (cy / CANVAS_H) * box.height };
}

// NOTE: getImageData reads the canvas's own intrinsic pixel buffer
// (CANVAS_W x CANVAS_H), NOT page/CSS coordinates -- callers pass the same
// canvas-space (cx, cy) used everywhere else in this file, never the
// page-space point toPagePoint produces for mouse events.
async function readPixel(page, cx, cy) {
  return page.evaluate(
    ({ x, y }) => {
      const el = document.querySelector(".mp-canvas");
      const d = el.getContext("2d").getImageData(Math.round(x), Math.round(y), 1, 1).data;
      return [d[0], d[1], d[2], d[3]];
    },
    { x: cx, y: cy }
  );
}

test("upload -> trace preview (colors + hole warning) -> add shapes -> drag a vertex on the real canvas", async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
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

  // ---- select the first traced shape, enter edit mode --------------------
  // A trace-add SELECTS its first shape on landing (ManualPanel.onTraced's
  // "anchor the batch add" selection), and a click on the selected row
  // TOGGLES the selection off (selectShape). So do not click blindly: click
  // only if the panel is not already showing the selected-shape controls.
  // This spec used to click unconditionally and deselect the very shape it
  // meant to edit — it was written before the auto-select existed.
  const editBtn = page.getByRole("button", { name: "Edit points" });
  if (!(await editBtn.isVisible())) await rows.first().click();
  await expect(editBtn).toBeEnabled();
  await page.getByRole("button", { name: "Edit points" }).click();

  const canvas = page.locator(".mp-canvas");
  // Entering edit mode grows the page (the vertex-edit assignment panel),
  // which can scroll the canvas partway (or fully) out of the viewport --
  // boundingBox() still returns a (possibly off-screen, even negative-y)
  // rect either way, so ground it back into view first, or the mouse
  // coordinates computed from it would target real page pixels that aren't
  // actually over the canvas.
  await canvas.scrollIntoViewIfNeeded();
  // A plain, isolated corner vertex of the first traced shape (see
  // beforeAll) -- validated offline (manualShapes.js's own isValidShape) to
  // stay a simple, sewable polygon after this drag.
  const from = firstShapePoints[1];
  const to = { x: from.x + 40, y: from.y - 40 };
  const fromPage = await toPagePoint(canvas, from.x, from.y);
  const toPage = await toPagePoint(canvas, to.x, to.y);

  // The drag target is background before the drag -- the clean baseline the
  // post-drag pixel check below proves against.
  expect(await readPixel(page, to.x, to.y)).toEqual(BG_RGBA);

  await page.mouse.move(fromPage.x, fromPage.y);
  await page.mouse.down();
  await page.mouse.move(toPage.x, toPage.y, { steps: 8 });
  await page.mouse.up();

  // A valid drag (no self-intersection) -- no rejection message.
  await expect(page.locator(".mp-draftissue")).toHaveCount(0);

  // Direct pixel confirmation the outline actually moved: the drag target
  // was background before, and must now be covered by the (now-larger)
  // filled shape -- genuine geometric movement, not just a redraw.
  await expect.poll(() => readPixel(page, to.x, to.y)).not.toEqual(BG_RGBA);

  // Exiting edit mode confirms the shape survived the edit under the same
  // row/id, editable through the existing, unmodified UI end to end.
  await page.getByRole("button", { name: "Done editing" }).click();
  await expect(rows).toHaveCount(3);
});
