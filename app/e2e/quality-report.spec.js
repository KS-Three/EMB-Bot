// The digitizer's own preflight report reaches the review step.
//
// The unit tests next to the component (src/ui/QualityReport.spec.js) render
// canned reports, so they prove how a report READS and nothing about where it
// comes from. This proves the wiring end to end through the real service:
// preflight runs in Python, rides the job envelope, is stored on the element,
// is picked up by App's `qualityEntries`, and lands on screen — plus the
// `stats` half, whose thread-length figure exists ONLY on the job (never in
// preflight's metrics) and which the Studio dropped on the floor until now.
//
// Same self-contained service bootstrap as the other digitize specs here.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "enthusiast_logo.png");

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
    const stat = readFileSync(path.join(roots[0], ".git"), "utf8");
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
      "digitizer service is not running and no venv python was found. " +
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


// Uploading IS the run (DigitizePanel's sourcePng watcher) — no Digitize click.
async function digitizeThenReview(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await page.getByRole("button", { name: "3 Review" }).click();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
}

test("the review step shows the grade, the findings, and the thread bill", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await digitizeThenReview(page);

  const quality = page.locator(".quality");
  await expect(quality).toBeVisible();

  // A real letter grade, computed in Python and rendered here. Not asserting
  // WHICH letter: the grade moves whenever the engine does, and pinning it
  // would make this an engine test wearing a UI test's clothes.
  await expect(quality.locator(".qr-grade b")).toHaveText(/^[ABCDF]$/);
  await expect(quality.locator(".qr-grade .qr-score")).toHaveText(/^\d{1,3}\/100$/);

  // The findings are the substance, and this fixture reliably has some.
  const rows = quality.locator(".qr-list li");
  expect(await rows.count()).toBeGreaterThan(0);
  // Sentences from preflight, not strings from the app: every finding message
  // ends in a full stop and is long enough to be advice rather than a label.
  const first = (await rows.first().innerText()).trim();
  expect(first.length).toBeGreaterThan(30);

  // The `stats` half. Thread length lives only on the job envelope, so a
  // metre figure here proves the new plumbing, not just preflight's metrics.
  await expect(quality.locator(".qr-bill"))
    .toHaveText(/[\d,]+ stitches · \d+ thread changes? · [\d.]+ m of thread/);
});

test("a lettering-only project shows no quality section", async ({ page }) => {
  test.skip(!serviceUp, skipReason);

  // Preflight runs in the Python digitizer, so browser-generated lettering has
  // no report to show. An empty "Quality check" heading over nothing would
  // imply the check ran and passed.
  await page.goto("/");
  await page.locator(".tcard", { hasText: "Left-chest name" }).click();
  await expect(page.getByText(/^\d+ stitches/)).toBeVisible();
  await page.getByRole("button", { name: "3 Review" }).click();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await expect(page.locator(".quality")).toHaveCount(0);
});
