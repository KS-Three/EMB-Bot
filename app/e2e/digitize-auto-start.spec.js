// End-to-end proof that uploading artwork is the WHOLE interaction: the run
// starts on its own, and the panel then says in plain words what it made of
// the art.
//
// Kent, 2026-08-30: "the photo upload is very confusing -- choose flat work,
// real photo etc. IDK what ANY of that even means, can't we just upload a
// photo/image and the tool AUTOMATICALLY recognizes what needs to be done?"
// It always classified the art itself (stage 0); Studio just asked anyway,
// with a "This is a photo" checkbox sitting in the params list and a Digitize
// button the user had to find. This spec pins the two halves of that fix:
//
//   * upload -> stitches, with NO Digitize click anywhere in the test, and
//   * a reading row that names what stage 0 decided, with the correction for
//     that reading (and only that one) beside it.
//
// Deliberately NOT a component test: DigitizePanel.spec.js covers the row's
// states off canned warnings, but it renders with `health: null` and never
// runs a job, so it cannot see a real classification arrive or prove that
// nothing had to be clicked to get one. That is exactly what regressed here.
//
// Same service bootstrap and skip posture as digitize-stale-edits.spec.js:
// reuse a running service, start one from a venv if there isn't one, and SKIP
// (never fail) on a machine with no digitizer venv.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// The same flat two-squares fixture the stale-edits spec uses: black and red
// on white, which stage 0 reads as flat art -- so this spec's expected reading
// is the flat one, and the correction offered beside it is "It's a photo".
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
    const stat = readFileSync(path.join(roots[0], ".git"), "utf8"); // throws when .git is a directory
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
    serviceUp = true; // a developer's own instance -- reuse, never kill
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
  skipReason = "digitizer service failed to answer /health within 30s of being started.";
});

test.afterAll(() => {
  if (serviceProc) serviceProc.kill("SIGTERM");
});

test("uploading artwork digitizes it on its own, and the panel says what it read", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");

  // ---- reach the digitize panel (same route as the wizard smoke test) ----
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  // Health-gated tile: it appearing IS the live assertion that the app sees
  // the real service, which is also what arms the upload watcher below.
  await page.getByRole("button", { name: "Artwork" }).click();

  // Nothing has been uploaded, so nothing is claimed about the art yet -- and
  // the empty state must not be asking the user to classify it either.
  await expect(page.locator(".dgp-read")).toHaveCount(0);
  await expect(page.getByText(/Drop in any image/)).toBeVisible();

  // ---- the whole interaction: choose a file ------------------------------
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);

  // No Digitize click. Stitches arrive anyway.
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  // ---- and the panel states what stage 0 made of it ----------------------
  const read = page.locator(".dgp-read");
  await expect(read).toHaveCount(1);
  await expect(read).toContainText("Read as flat art");
  // The correction for THIS reading, and not the other one.
  await expect(read.getByRole("button", { name: "It's a photo" })).toBeVisible();
  await expect(read.getByRole("button", { name: "It's flat art" })).toHaveCount(0);

  // ---- correcting it is one click, and it re-runs by itself --------------
  const statsBefore = await page.locator(".dgp-stats").innerText();
  await read.getByRole("button", { name: "It's a photo" }).click();
  await expect(read).toContainText("You set this to a photo.", { timeout: 120_000 });
  // The correction reached the engine: a photo_subject run is not the flat
  // one it replaced.
  await expect(page.locator(".dgp-stats")).not.toHaveText(statsBefore, { timeout: 120_000 });

  // ---- and back, in one click, with no override left behind --------------
  await read.getByRole("button", { name: "Use automatic detection" }).click();
  await expect(read).toContainText("Read as flat art", { timeout: 120_000 });
});
