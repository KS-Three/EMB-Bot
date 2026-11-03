// End-to-end test for editing a digitized shape's boundary (shape-layers
// contract v1.4): the self-flagged gap MASTER_SCOPE.md area 5 used to list as
// fully open -- "no manual point editing." Drives the REAL digitizer service.
//
// The editor moved. The Layers row's pencil and its small SVG editor were
// retired 2026-11-03 (node-reshape spec, ruling 7): the hoop canvas is the one
// boundary editor, entered from the shape popover's "Edit points". The claim
// is the same:
//
//   upload art -> digitize -> click the black square -> Edit points -> drag a
//   vertex on the hoop canvas -> the restitch lands -> the SAME shape id
//   survives, its outline visibly changed (different area), the design's
//   stitch count moved, and the row carries an "edited outline" badge.
//
// Same service-bootstrap and fixture as digitize-stale-edits.spec.js (this
// file intentionally duplicates that boilerplate rather than importing it --
// each e2e spec here is self-contained, matching that file's own convention).
import { test, expect } from "@playwright/test";
import { pickGarment, uploadArtwork, openAdvanced, runDigitize, pinDigitizeConfig } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// The per-shape rows sit behind a closed-by-default "Edit shapes" disclosure
// (2026-09-02: a two-colour logo otherwise opened 329 controls). Anything that
// drives a row has to open it first. Idempotent, so it is safe to call after
// every re-digitize -- the panel remounts per element and closes again.
async function openShapeRows(page) {
  // The list lives on the Shapes tab since 2026-09-30; the tab appears with
  // the result, so the click waits for it.
  await openAdvanced(page);
  await page.getByRole("tab", { name: "Shapes" }).click({ timeout: 120_000 });
  const btn = page.getByRole("button", { name: /^Edit shapes/ });
  await expect(btn).toBeVisible({ timeout: 120_000 });
  if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
}


const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");

async function healthy() {
  try {
    const r = await fetch(SERVICE_URL + "/health");
    if (!r.ok) return false;
    const h = await r.json();
    return !!h && h.status === "ok";
  } catch (e) {
    return false;
  }
}

function venvPythonCandidates() {
  const roots = [path.resolve(__dirname, "../..")];
  try {
    const gitPath = path.join(roots[0], ".git");
    const stat = readFileSync(gitPath, "utf8");
    const m = stat.match(/^gitdir:\s*(.+)$/m);
    if (m) {
      const mainRoot = path.resolve(m[1].trim(), "../../..");
      if (mainRoot !== roots[0]) roots.push(mainRoot);
    }
  } catch (e) {
    // .git is a directory: a normal checkout, nothing to add
  }
  const out = [];
  for (const root of roots) {
    out.push(path.join(root, "digitizer", ".venv", "bin", "python"));
    out.push(path.join(root, "digitizer", ".venv", "Scripts", "python.exe"));
  }
  return out.filter(existsSync);
}

let serviceProc = null;
let serviceUp = false;
let skipReason = "";

test.beforeAll(async () => {
  if (await healthy()) {
    serviceUp = true;
    return;
  }
  const [python] = venvPythonCandidates();
  if (!python) {
    skipReason =
      "digitizer service is not running and no venv python was found " +
      "(looked for digitizer/.venv in this checkout and the main checkout). " +
      "Start it manually: `python -m digitizer_service` in digitizer/.";
    return;
  }
  serviceProc = spawn(python, ["-m", "digitizer_service"], {
    cwd: path.resolve(__dirname, "../../digitizer"),
    stdio: "ignore",
  });
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (await healthy()) {
      serviceUp = true;
      return;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  skipReason = "digitizer service failed to answer /health within 30s of being started (" + python + ").";
});

test.afterAll(() => {
  if (serviceProc) serviceProc.kill("SIGTERM");
});

test("boundary editor: drag a vertex on the hoop canvas -- the shape reshapes through the real service", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await pickGarment(page, "Tote");
  // No border ring around the square: with `border_by_size` on, the sewn ring
  // widens the black bounding box past the outline, and this spec aims at the
  // outline's corner. (The flag's own behaviour is pinned in the digitizer's tests.)
  await pinDigitizeConfig(page, { border_by_size: false });

  await uploadArtwork(page, ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await openShapeRows(page);

  const statsBefore = await page.locator(".dgp-stats").innerText();
  const blackRow = page.locator(".dgp-layer").filter({ hasText: "#0020" });
  const areaBefore = await blackRow.locator(".dgp-larea").innerText();

  // ---- find the black square on the canvas (its fill is the only near-black
  // thing there, so its bounding box is its four vertices) ---------------------
  const canvas = page.locator(".hoop canvas");
  const corners = async () => {
    const f = await page.evaluate(() => {
      const c = document.querySelector(".hoop canvas");
      const w = c.width, h = c.height;
      const d = c.getContext("2d").getImageData(0, 0, w, h).data;
      let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const i = (y * w + x) * 4;
        if (d[i + 3] > 200 && d[i] < 14 && d[i + 1] < 14 && d[i + 2] < 14) {
          if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
        }
      }
      return { x0, y0, x1, y1, cw: w };
    });
    expect(f.x1, "a black square is on the canvas").toBeGreaterThan(0);
    const hb = await canvas.boundingBox();
    const k = hb.width / f.cw;
    return { tr: { x: hb.x + f.x1 * k, y: hb.y + f.y0 * k }, centre: { x: hb.x + ((f.x0 + f.x1) / 2) * k, y: hb.y + ((f.y0 + f.y1) / 2) * k } };
  };

  // ---- open the editor: click inside the square, Edit points ---------------
  const { centre } = await corners();
  await page.mouse.click(centre.x, centre.y);
  const dlg = page.getByRole("dialog", { name: /^Thread #/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByTestId("shapepop-points")).toHaveText(/^Points: \d+$/);
  await dlg.getByRole("button", { name: "Edit points" }).click();
  await expect(canvas).toHaveAttribute("data-reshape", "on");
  // Selecting re-fits the view a little: aim at where the corner is NOW.
  await page.waitForTimeout(600);
  const { tr } = await corners();

  // ---- drag its top-right vertex outward ------------------------------------
  // Raw mouse events, in stages (the drag has a dead zone). The corner is on
  // the page, in view: the canvas never scrolls.
  await page.mouse.move(tr.x, tr.y);
  await page.mouse.down();
  await page.mouse.move(tr.x + 26, tr.y - 20, { steps: 8 });
  await page.mouse.up();
  // Fail HERE if the drag did not take, not at the stats assertion later: a
  // no-op drag restitches nothing and the rest of the spec would test nothing.
  await expect.poll(async () => page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    const parsed = JSON.parse(localStorage.getItem("embstudio:p:" + id));
    const proj = parsed.project || parsed;
    const el = (proj.elements || []).find((e) => e.type === "digitized");
    return Object.values(el.shapeOverrides || {}).filter((v) => v.boundary_override).length;
  })).toBe(1);

  // ---- the restitch: a pending edit, then the real service re-sews ----------
  await expect(blackRow.getByText("edited outline")).toBeVisible();
  const moved = () => page.locator(".dgp-stats").innerText().then((t) => t !== statsBefore);
  const landed = await expect.poll(moved, { timeout: 8_000 }).toBe(true).then(() => true, () => false);
  if (!landed) {
    await runDigitize(page);
    await expect.poll(moved, { timeout: 120_000 }).toBe(true);
  }

  // ---- the real service actually reshaped and resewed the design ---------
  await expect(blackRow.getByText("edited outline")).toBeVisible();
  const areaAfter = await blackRow.locator(".dgp-larea").innerText();
  expect(areaAfter).not.toBe(areaBefore);
  // The shape survived under the SAME row (same id, same thread number) --
  // a boundary edit alone never churns identity.
  await expect(blackRow).toBeVisible();
});
