// End-to-end test for MASTER_SCOPE area 5's self-flagged gap: the
// stale/unmatched-edit recovery flow, "never driven in a live browser" until
// this spec. It drives the REAL digitizer service (127.0.0.1:8721) through
// the real DigitizePanel:
//
//   upload art -> digitize -> per-shape edit (the new Border override
//   control) -> apply -> change stitch width (shape ids are content-derived
//   from mm centroids, so a new width regenerates them) -> the service
//   answers SHAPE_EDIT_UNKNOWN_ID and the panel shows the unmatched-edits
//   notice -> "Clear them" -> "Apply layer changes" -> clean result, no
//   warning, no unmatched edits.
//
// Service bootstrap: Playwright's webServer config only starts the Vite dev
// server, so this spec starts the Python digitizer service itself (and stops
// it if it was the one to start it). When no service is reachable AND no
// venv python can be found to start one, the test SKIPS with a clear message
// rather than failing -- the wizard smoke test stays green on a machine with
// no digitizer venv.
//
// Same runner split as wizard-smoke.spec.js: this is a @playwright/test spec
// (`npm run test:e2e`), not a vitest one -- vite.config.js excludes e2e/**.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Two black/red squares side by side on white, 200x100 px (generated with
// OpenCV, checked in as a fixture -- an earlier embedded-base64 version of
// this spec got one character mangled in copying and cv2 happily decoded
// the corrupt zlib stream into garbage regions, so: a real file, no prose
// copy of binary). Both squares sit OFF the design center on the x axis --
// that matters: shape ids hash the bucketed mm centroid
// (digitizer_core/regions.py::assign_shape_ids), so off-center shapes are
// guaranteed new ids when the target width changes, which is the natural
// way a user's applied edit goes stale.
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

let serviceProc = null; // the child THIS spec spawned (null = reused or none)
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
  // Run THIS checkout's service code (cwd puts it on sys.path for -m), with
  // whichever checkout's venv exists.
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

test("stale layer edits: service flags them, the panel surfaces them, Clear + Apply recovers", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  // Four real digitize runs ride through this test (initial, apply-edit,
  // width-change re-run, recovery apply); each is seconds on this artwork,
  // but budget generously.
  test.setTimeout(300_000);

  await page.goto("/");

  // ---- reach the digitize panel (same route as the wizard smoke test) ----
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();

  // The tile is health-gated (App probes /health on reaching this step); it
  // appearing IS the live assertion that the app sees the real service.
  await page.getByRole("button", { name: "+ Auto-digitize" }).click();

  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await page.getByRole("button", { name: "Digitize", exact: true }).click();

  // Three shapes, each an editable layer row: black square, red square, AND
  // the white ground -- the panel's canvas re-encode writes an OPAQUE-ALPHA
  // PNG, and the pipeline reads a fully opaque alpha channel as "no
  // background here", so white becomes a real region (verified against the
  // live service with an RGBA copy of the fixture: 2 shapes as RGB, 3 as
  // RGBA).
  const rows = page.locator(".dgp-layer");
  await expect(rows).toHaveCount(3, { timeout: 120_000 });
  await expect(page.locator(".dgp-stats")).toBeVisible();

  // ---- make a real per-shape edit and apply it ---------------------------
  // The edit vehicle is the Border override select (area 5's other flagged
  // gap -- this doubles as its live-wire verification): bean border on the
  // BLACK SQUARE's shape, an override the service accepts and sews. The
  // black square, not the first row: the first row is the white ground,
  // whose centroid sits at the design center -- bucket (0,0) at ANY width,
  // so an edit on IT would never go stale. The off-center square is the one
  // whose id regenerates.
  const blackRow = rows.filter({ hasText: "#0020" });
  const statsBefore = await page.locator(".dgp-stats").innerText();
  await blackRow.getByLabel("Border").selectOption("bean");

  // Located by class, not accessible name: the button reads "Apply layer
  // changes" when idle but "Digitizing…" mid-flight, and it disappearing
  // entirely (hasPendingEdits false) is the "edit landed" signal.
  const apply = page.locator(".dgp-apply");
  await expect(apply).toHaveText("Apply layer changes");
  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });
  // The service actually sewed the border: the stitch count moved.
  await expect(page.locator(".dgp-stats")).not.toHaveText(statsBefore);
  await expect(blackRow.getByLabel("Border")).toHaveValue("bean");
  // A valid, applied edit is NOT unmatched.
  await expect(page.locator(".dgp-unmatched")).toBeHidden();

  // ---- go stale: re-digitize at a new width ------------------------------
  // Shape ids hash the bucketed mm centroid, so halving the width gives both
  // shapes new ids; the applied border override now names a shape that no
  // longer exists. The width change re-digitizes automatically (the panel's
  // params watcher), carrying the now-stale override to the service.
  const width = page.getByLabel("Stitch width");
  await width.fill("40");
  await width.blur();

  // The service answered SHAPE_EDIT_UNKNOWN_ID (translated for the user)...
  await expect(
    page.getByText("One layer edit no longer matches any shape in the art, so it wasn't applied.")
  ).toBeVisible({ timeout: 120_000 });
  // ...and the panel counts the same stale edit against the fresh review.
  const unmatched = page.locator(".dgp-unmatched");
  await expect(unmatched).toBeVisible();
  await expect(unmatched).toContainText("1 layer edit");
  // Nothing is "pending": the stale edit WAS sent with this result. The
  // panel never silently drops a user's edit -- recovery is explicit.
  await expect(apply).toBeHidden();

  // ---- recover: Clear them, then Apply -----------------------------------
  await page.getByRole("button", { name: "Clear them" }).click();
  await expect(unmatched).toBeHidden();
  // Dropping the stale override makes the element's edits differ from the
  // ones this result was digitized with -> Apply reappears.
  await expect(apply).toHaveText("Apply layer changes");
  await apply.click();
  await expect(apply).toBeHidden({ timeout: 120_000 });

  // Clean state: no stale-edit warning, no unmatched notice, both shapes
  // still listed, and the cleared border select is back on the design-wide
  // setting.
  await expect(
    page.getByText("One layer edit no longer matches any shape in the art, so it wasn't applied.")
  ).toBeHidden();
  await expect(unmatched).toBeHidden();
  await expect(rows).toHaveCount(3);
  await expect(blackRow.getByLabel("Border")).toHaveValue("default");
});
