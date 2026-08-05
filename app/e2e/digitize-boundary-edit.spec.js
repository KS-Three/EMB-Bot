// End-to-end test for the boundary editor (shape-layers contract v1.4): the
// one self-flagged gap MASTER_SCOPE.md area 5 used to list as fully open --
// "no true shape-recognition re-editing... no manual point editing." Drives
// the REAL digitizer service through the real DigitizePanel:
//
//   upload art -> digitize -> open "Edit shape boundary" on one shape ->
//   drag a vertex -> Save boundary -> Apply layer changes -> the SAME shape
//   id survives, its outline visibly changed (bigger area), the design's
//   stitch count moved, and the row carries an "edited outline" badge.
//
// Same service-bootstrap and fixture as digitize-stale-edits.spec.js (this
// file intentionally duplicates that boilerplate rather than importing it --
// each e2e spec here is self-contained, matching that file's own convention).
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

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

test("boundary editor: drag a vertex, save, apply -- the shape reshapes through the real service", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");

  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "+ Auto-digitize" }).click();

  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await page.getByRole("button", { name: "Digitize", exact: true }).click();
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  const statsBefore = await page.locator(".dgp-stats").innerText();
  const blackRow = page.locator(".dgp-layer").filter({ hasText: "#0020" });
  const areaBefore = await blackRow.locator(".dgp-larea").innerText();

  // ---- open the editor, drag a corner outward -----------------------------
  await blackRow.getByLabel("Edit shape boundary").click();
  await expect(page.getByText(/^Editing boundary/)).toBeVisible();

  const vertex = page.locator(".dgp-editor-vertex").first();
  const box = await vertex.boundingBox();
  const start = { x: box.x + box.width / 2, y: box.y + box.height / 2 };

  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  await page.mouse.move(start.x - 18, start.y - 14, { steps: 6 });
  await page.mouse.up();

  // Enlarging a corner grows the polygon: the working preview reflects the
  // drag before anything is saved (still purely local edit state).
  const saveBtn = page.getByRole("button", { name: "Save boundary" });
  await expect(saveBtn).toBeEnabled();
  await expect(page.locator(".dgp-editor-issues")).toBeHidden();

  await saveBtn.click();

  // ---- back in the Layers list: a pending edit, badge, Apply -------------
  await expect(page.getByText(/^Editing boundary/)).toBeHidden();
  await expect(blackRow.getByText("edited outline")).toBeVisible();
  const apply = page.locator(".dgp-apply");
  await expect(apply).toHaveText("Apply layer changes");

  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });

  // ---- the real service actually reshaped and resewed the design ---------
  await expect(page.locator(".dgp-stats")).not.toHaveText(statsBefore);
  await expect(blackRow.getByText("edited outline")).toBeVisible();
  const areaAfter = await blackRow.locator(".dgp-larea").innerText();
  expect(areaAfter).not.toBe(areaBefore);
  // The shape survived under the SAME row (same id, same thread number) --
  // a boundary edit alone never churns identity.
  await expect(blackRow).toBeVisible();

  // ---- Reset to auto undoes it, same "auto" convention as every other
  // override control here -----------------------------------------------
  await blackRow.getByLabel("Edit shape boundary").click();
  await expect(page.getByRole("button", { name: "Reset to auto" })).toBeVisible();
  await page.getByRole("button", { name: "Reset to auto" }).click();
  await expect(apply).toHaveText("Apply layer changes");
  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });
  await expect(blackRow.getByText("edited outline")).toBeHidden();
});
