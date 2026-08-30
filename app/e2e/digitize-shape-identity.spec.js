// End-to-end test for shape identity edits (contract v1.5, `merge_shape_ids`/
// `split_shapes`) -- the other half of the shape-recognition gap
// `digitize-boundary-edit.spec.js` didn't touch: that spec reshapes ONE
// shape's outline; this one changes the SET of shapes. Drives the REAL
// digitizer service through the real DigitizePanel:
//
//   SPLIT: upload art -> digitize -> "Split shape" on one shape -> Save cut
//   (the default cut line, a horizontal line through the shape's own
//   centroid, is already valid for a plain rectangle -- no drag required to
//   reach a savable state) -> Apply layer changes -> the ONE original shape
//   is replaced by TWO new rows sharing its thread, the design's stitch
//   count moved, and each row carries a "split shape" badge -> Undo split
//   restores the original single shape.
//
//   MERGE (selection mechanics only -- see the note below for why): select
//   two DIFFERENT-colored rows for merge -> the merge bar shows the
//   same-color validation issue and disables the Merge button -> clearing
//   the selection hides the bar.
//
// Why merge's live proof stops at selection mechanics, not a full apply
// round trip: `regions.apply_shape_merges` requires the source shapes to
// already touch or overlap (Region.polygon is one Polygon throughout the
// whole pipeline, so a merge that doesn't reduce to one polygon has no
// legal result -- see that function's own module comment in regions.py).
// Stage 3's connected-component labeling (connectivity=8) means two
// genuinely touching same-color regions are already fused into ONE shape_id
// before the review screen ever sees them, so no simple committed fixture
// image reliably produces two REAL touching same-thread rows to merge live.
// The successful-union path IS proven -- just not through this browser
// harness -- at the core level (synthetic adjacent Regions,
// tests/test_shape_identity.py) and the service level (a real HTTP
// round trip is service-level only where a genuinely non-adjacent pair
// -- the fixture's own two same-thread "1305" regions -- proves the
// config reaches the real pipeline and is cleanly rejected,
// digitizer/tests/test_service.py).
//
// Same service-bootstrap and fixture as digitize-boundary-edit.spec.js (this
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

test("split editor: cut one shape into two through the real service, then undo", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");

  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();

  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  // No Digitize click: choosing the file starts the run (DigitizePanel's
  // sourcePng watcher). The button reads "Digitize again" by the time a
  // result exists, so clicking an exact "Digitize" here would hang.
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  const statsBefore = await page.locator(".dgp-stats").innerText();
  const blackRow = page.locator(".dgp-layer").filter({ hasText: "#0020" });
  await expect(blackRow).toHaveCount(1);

  // ---- open the split editor, save the default cut straight away ---------
  await blackRow.getByLabel("Split shape").click();
  await expect(page.getByText(/^Splitting shape/)).toBeVisible();

  const saveBtn = page.getByRole("button", { name: "Save cut" });
  await expect(saveBtn).toBeEnabled(); // the default line already crosses cleanly
  await expect(page.locator(".dgp-editor-issues")).toBeHidden();
  await saveBtn.click();

  // ---- back in the Layers list: a pending edit, Apply ---------------------
  await expect(page.getByText(/^Splitting shape/)).toBeHidden();
  const apply = page.locator(".dgp-apply");
  await expect(apply).toHaveText("Apply layer changes");
  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });

  // ---- the real service actually cut the shape into two -------------------
  await expect(page.locator(".dgp-stats")).not.toHaveText(statsBefore);
  const splitRows = page.locator(".dgp-layer").filter({ hasText: "#0020" });
  await expect(splitRows).toHaveCount(2); // both pieces keep the source thread
  await expect(splitRows.first().getByText("split shape")).toBeVisible();
  await expect(splitRows.last().getByText("split shape")).toBeVisible();

  // ---- Undo split restores the single original shape -----------------------
  await splitRows.first().getByLabel("Undo split").click();
  await expect(apply).toHaveText("Apply layer changes");
  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });
  await expect(page.locator(".dgp-layer").filter({ hasText: "#0020" })).toHaveCount(1);
});

test("merge selection: picking shapes of two different colors shows the same-color validation and disables Merge", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");

  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();

  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  // No Digitize click: choosing the file starts the run (DigitizePanel's
  // sourcePng watcher). The button reads "Digitize again" by the time a
  // result exists, so clicking an exact "Digitize" here would hang.
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  const rows = page.locator(".dgp-layer");
  await expect(rows).toHaveCount(2); // two-squares.png: one black shape, one red shape

  await rows.nth(0).locator('input[type="checkbox"]').check();
  await expect(page.locator(".dgp-mergebar")).toContainText("1 selected for merge");

  await rows.nth(1).locator('input[type="checkbox"]').check();
  await expect(page.locator(".dgp-mergebar")).toContainText("2 selected for merge");
  await expect(page.locator(".dgp-mergeissue")).toContainText("one color");
  await expect(page.getByRole("button", { name: /^Merge \d+ shapes$/ })).toBeDisabled();

  await page.getByRole("button", { name: "Clear" }).click();
  await expect(page.locator(".dgp-mergebar")).toBeHidden();
});
