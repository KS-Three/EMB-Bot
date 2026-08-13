// End-to-end test for the BACKGROUND_ENCLOSED fix (MASTER_SCOPE.md area 1):
// landed via PR #9/#10 (pipeline + service contract + Studio UI) and PR #22
// (the opaque-alpha caveat -- Studio's real upload path re-encodes every
// image through a canvas, which manufactures an all-255 opaque alpha
// channel; stage1_prep used to treat that as "nothing here is background"
// and silently disabled enclosed-region detection for every real panel
// upload). Both fixes were previously confirmed only by POSTing directly to
// the digitizer service's HTTP API -- this spec is the first real-browser
// check, driving the REAL digitizer service through the real DigitizePanel:
//
//   upload art with enclosed white icon linework (a camera glyph on a
//   gradient badge -- ring, dot, and frame all read as background-colored
//   but are not reachable from the canvas border) -> digitize -> confirm the
//   Layers panel shows them as dimmed "not sewn -- enclosed area" rows
//   (not silently dropped, not wrongly filled solid) -> "Sew it" on one ->
//   "restored" badge + Apply layer changes -> Apply -> the real service
//   re-sews it (stitch count grows) and the row now carries a normal tier.
//
// Kent's own real-world repro of this exact fixture's problem class (the
// Instagram icon) reported "still white gaps" even after the restore
// mechanism above shipped -- the per-row "Sew it" control was too easy to
// miss buried in a dimmed list line. The fix adds a loud, actionable
// ".dgp-enclosed-banner" (replacing the old plain-text warning bullet) with
// a "Sew all N" bulk action; the second test below exercises that path.
//
// Same service-bootstrap and fixture-sourcing conventions as
// digitize-boundary-edit.spec.js / digitize-stale-edits.spec.js. The art
// fixtures are NOT copied into app/e2e/fixtures like two-squares.png --
// they're referenced straight from digitizer/testdata/, the same git-tracked
// files the Python suites point at, so the browser check and the
// Python-level checks exercise the identical bytes.
//
// FIXTURE CHANGE, 2026-08-13: these tests originally ran on
// `repro_gradient_white_icon.png` (Kent's Instagram-icon repro). The
// 2026-08-11 background-existence guards deliberately stopped treating that
// edge-to-edge artwork as having a background at all (BACKGROUND_ABSENT) --
// and with no background there is nothing to tag enclosed, so the banner
// this spec exists to test can never fire on it. The Python tests took a
// guards-off config the same day (see COOKBOOK's parallel-lanes lesson);
// this spec CANNOT -- it drives the real Studio, which sends only real
// Studio configs -- so it moves to fixtures whose white ground survives the
// guards. Verified live against the real service before the swap:
// logo_whitebg -> banner with exactly 1 enclosed area (the single-restore
// test), enthusiast_logo -> "Sew all 4" (the bulk test). The suite was dark
// from 2026-08-10 to -13 (tile-locator break), which is why the premise
// loss went unnoticed.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Single enclosed area: the O-type counter in the logo's lettering.
const ART_SINGLE_PNG = path.join(__dirname, "../../digitizer/testdata/logo_whitebg.png");
// Several enclosed areas (4) -- a real bulk-restore case.
const ART_BULK_PNG = path.join(
  __dirname,
  "../../digitizer/testdata/photo/enthusiast_logo.png"
);

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

// The digitizer venv is gitignored and lives with a real checkout, not
// necessarily this one: a git worktree (this repo's parallel-lane setup)
// shares no untracked files with the main checkout. So candidate roots are
// this checkout AND -- when this checkout is a linked worktree (.git is a
// file pointing at <main>/.git/worktrees/<name>) -- the main checkout.
function venvPythonCandidates() {
  const roots = [path.resolve(__dirname, "../..")];
  try {
    const gitPath = path.join(roots[0], ".git");
    const stat = readFileSync(gitPath, "utf8"); // throws when .git is a directory
    const m = stat.match(/^gitdir:\s*(.+)$/m);
    if (m) {
      // <main>/.git/worktrees/<name> -> <main>
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
    serviceUp = true; // a developer's own service instance -- reuse, never kill
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

test("BACKGROUND_ENCLOSED: enclosed icon linework is held out by default and restorable through the real service", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");

  // ---- reach the digitize panel (same route as the other digitize specs) --
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();

  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_SINGLE_PNG);
  await page.getByRole("button", { name: "Digitize", exact: true }).click();
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  // ---- the pipeline actually classified this art as carrying enclosed
  // background-colored regions, surfaced as the loud, actionable banner ----
  const banner = page.locator(".dgp-enclosed-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("enclosed area");

  // ---- the Layers panel reflects it: dimmed rows, "not sewn -- enclosed
  // area", each with its own "Sew it" restore control -- not silently
  // dropped (no row at all) and not wrongly filled solid (a normal row) --
  const unstitchedRows = page.locator(".dgp-layer.unstitched");
  const countBefore = await unstitchedRows.count();
  expect(countBefore).toBeGreaterThan(0);
  await expect(unstitchedRows.first().getByText("not sewn — enclosed area")).toBeVisible();
  const restoreBtn = unstitchedRows.first().getByRole("button", { name: "Sew it" });
  await expect(restoreBtn).toBeVisible();

  // Banner's own count tracks the live unstitched rows, not a stale
  // server-reported number.
  await expect(banner.getByRole("button")).toHaveText(`Sew all ${countBefore}`);

  const statsBefore = await page.locator(".dgp-stats").innerText();

  // ---- restore one enclosed region: local toggle first (nothing sent yet) -
  await restoreBtn.click();
  await expect(unstitchedRows).toHaveCount(countBefore - 1);
  const restoredRow = page.locator(".dgp-layer").filter({ has: page.locator(".dgp-lbadge", { hasText: "restored" }) });
  await expect(restoredRow).toBeVisible();
  await expect(restoredRow.getByRole("button", { name: "Mark as not sewn again" })).toBeVisible();
  // The banner exists only while unstitched rows remain ({#if
  // unstitchedRows.length}) — restoring the LAST one removes it outright
  // rather than showing "Sew all 0". On the old multi-enclosed fixture this
  // branch never ran; logo_whitebg has exactly one enclosed area, so it
  // always does.
  if (countBefore - 1 === 0) {
    await expect(banner).toBeHidden();
  } else {
    await expect(banner.getByRole("button")).toHaveText(`Sew all ${countBefore - 1}`);
  }

  const apply = page.locator(".dgp-apply");
  await expect(apply).toHaveText("Apply layer changes");
  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });

  // ---- the real service actually re-sewed the restored region -----------
  await expect(page.locator(".dgp-stats")).not.toHaveText(statsBefore);
  // The service now echoes stitched:true for this shape (contract v1.x --
  // see test_stitched_default_and_override_round_trip_over_http), so the
  // row reports a normal stitch tier and drops out of the unstitched count.
  await expect(page.locator(".dgp-layer.unstitched")).toHaveCount(countBefore - 1);
});

test("BACKGROUND_ENCLOSED: the banner's 'Sew all' bulk-restores every enclosed region in one click", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");

  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();

  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_BULK_PNG);
  await page.getByRole("button", { name: "Digitize", exact: true }).click();
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  const banner = page.locator(".dgp-enclosed-banner");
  await expect(banner).toBeVisible();
  const unstitchedRows = page.locator(".dgp-layer.unstitched");
  const countBefore = await unstitchedRows.count();
  expect(countBefore).toBeGreaterThan(1); // this fixture carries several -- a real bulk case

  const statsBefore = await page.locator(".dgp-stats").innerText();

  // ---- one click restores every enclosed region, not just one -----------
  await banner.getByRole("button", { name: `Sew all ${countBefore}` }).click();
  await expect(unstitchedRows).toHaveCount(0);
  await expect(banner).toBeHidden();
  await expect(page.locator(".dgp-lbadge", { hasText: "restored" })).toHaveCount(countBefore);

  const apply = page.locator(".dgp-apply");
  await expect(apply).toHaveText("Apply layer changes");
  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });

  // ---- the real service actually re-sewed every one of them --------------
  await expect(page.locator(".dgp-stats")).not.toHaveText(statsBefore);
  await expect(page.locator(".dgp-layer.unstitched")).toHaveCount(0);
});
