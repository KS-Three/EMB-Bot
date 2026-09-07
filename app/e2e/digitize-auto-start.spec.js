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
// A vector logo with a `viewBox` and NO width/height — the shape SVGO and most
// hand-written exports produce, and the one Chrome hands back at its 300 px
// default size. Three inks on white: one blue circle, one red bar, one blue
// bar, so the ONLY honest answer is two thread colours.
const ART_SVG = path.join(__dirname, "fixtures", "vector_logo.svg");

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
  // The correction reached the engine: since 2026-09-02 it sends
  // `is_photographic` (photographic CONTENT -> depth sequencing + palette
  // bind) rather than forcing the fill tier, so the class may still read
  // flat while the SEW ORDER changes. What is asserted is what the user can
  // actually check: the run is not the one it replaced.
  await expect(page.locator(".dgp-stats")).not.toHaveText(statsBefore, { timeout: 120_000 });

  // ---- and back, in one click, with no override left behind --------------
  await read.getByRole("button", { name: "Use automatic detection" }).click();
  await expect(read).toContainText("Read as flat art", { timeout: 120_000 });
});

test("JEF downloads a real file through the service — the format with no browser encoder", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  // PRODUCT.md's launch checklist counted JEF as shipped from 2026-08-11
  // because `digitizer_service/formats.py` can write it. There was no button,
  // so a Janome owner could not export anything. That gap is invisible to a
  // unit test of the writer AND to a component test with a mocked exporter —
  // it lives exactly in the space this spec covers, so the guard lives here
  // rather than beside the other download tests in wizard-smoke.spec.js,
  // which deliberately has no service bootstrap.
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  await page.getByRole("button", { name: "4 Download", exact: true }).click();
  const jef = page.getByTestId("jef-button");
  // Enabled, because the service this spec bootstrapped is answering. The
  // disabled case is a component test (DownloadStep.spec.js) — reaching it
  // here would mean killing the service mid-spec.
  await expect(jef).toBeEnabled();

  const downloadPromise = page.waitForEvent("download");
  await jef.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("design.jef");
  const jefPath = await download.path();
  const jefBytes = readFileSync(jefPath);
  expect(jefBytes.length).toBeGreaterThan(512);

  // The panel names the encoder, and for JEF there is only one it can be —
  // this is the assertion that a browser-encoded file was not quietly
  // substituted, which is what the removed fallback would have done.
  await expect(page.getByText("Downloaded JEF (digitizer service encoder)")).toBeVisible();

  // And it is genuinely a different file from the DST of the same design, not
  // the same bytes under another name. (What the bytes MEAN is decoded with
  // pystitch in digitizer/tests/test_service.py, which owns that claim.)
  const dstPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const dst = await dstPromise;
  expect(dst.suggestedFilename()).toBe("design.dst");
  expect(readFileSync(await dst.path()).equals(jefBytes)).toBe(false);
});

test("a vector logo is rendered at the work size, not at the browser's default", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  // Measured in the shipped app on 2026-09-07, this exact file, before the
  // fix: 3,445 stitches in **4 colors**, with
  //
  //   "The image gives 3.1 pixels per millimetre at this size and needs 4.
  //    Enlarging it can't add detail that isn't in the file — about 1.3x
  //    wider, or a smaller design, will sew sharper."
  //
  // Every clause of which is false for a vector: the detail IS in the file,
  // and the app threw it away by keeping Chrome's 300 px default size. The two
  // extra "colors" were anti-alias fringe from that raster — two spools a
  // customer would have had to buy and two extra machine stops.
  //
  // Asserted on the COLOUR COUNT rather than on the absence of the warning: an
  // absence can pass for any reason, and the colour count is the thing the
  // customer pays for. Two is what the artwork has.
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_SVG);

  const stats = page.locator(".dgp-stats");
  await expect(stats).toBeVisible({ timeout: 120_000 });
  await expect(stats).toContainText("2 colors");

  // …and with the resolution genuinely there, the low-resolution finding has
  // nothing to report. This one IS an absence, and it is only meaningful
  // beside the assertion above.
  await expect(page.getByText(/pixels per millimetre/)).toHaveCount(0);
});

// ---- The hoop code JEF writes into its own header --------------------------
//
// `pystitch.JefWriter.get_jef_hoop_size` derives the code from the design's
// bbox correctly and then falls off the end of its ladder: anything at or over
// 200 mm in either axis is written as HOOP_110X110 — the second smallest of
// the five it knows. A Janome reads that before it reads a stitch.
//
// digitizer/tests/test_jef_hoop_code.py pins the BYTE and DownloadStep.spec.js
// pins the SENTENCE. Neither can prove the two agree, and that is the whole
// claim the customer is being asked to trust — so it is asserted here, on one
// real download, in both directions.
//
// Lettering rather than artwork on purpose: it is fast, it needs no upload,
// and JEF has no browser encoder, so a text design goes through the service
// exactly as a digitized one does.
const JEF_HOOP_CODE_OFFSET = 32;   // after the 4+4 header, the date and the counts

async function jefHoopCode(page) {
  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("jef-button").click();
  // Only opens for a design bigger than every hoop; harmless when it does not.
  const anyway = page.getByRole("button", { name: "Download JEF anyway", exact: true });
  if (await anyway.isVisible().catch(() => false)) await anyway.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("design.jef");
  return readFileSync(await download.path()).readInt32LE(JEF_HOOP_CODE_OFFSET);
}

async function reachDownloadWithText(page, garmentLabel, text) {
  await page.goto("/");
  await page.getByRole("button", { name: garmentLabel, exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByPlaceholder("Type a name or word").fill(text);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await page.getByRole("button", { name: "4 Download", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();
}

test("the JEF caveat appears exactly when the file's hoop code is the bad one", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  // ---- over the band: Full Back's placement box is 304.8 mm ---------------
  await reachDownloadWithText(page, "Full Back", "FRITSCHS");
  const note = page.getByTestId("jef-hoop-header-note");
  await expect(note).toBeVisible();
  await expect(note).toContainText("110 × 110 mm");
  // The button says so too, without the asterisk becoming part of its name.
  const jef = page.getByTestId("jef-button");
  await expect(jef).toHaveAttribute("aria-describedby", "jef-hoop-note");
  await expect(jef).toHaveAccessibleName("JEF");
  expect(await jefHoopCode(page)).toBe(0);   // HOOP_110X110

  // ---- under it: Left Chest is 101.6 mm -----------------------------------
  // The negative matters as much as the positive. A note that fired on every
  // design would pass the assertion above and be worthless, and a note wired
  // to the wrong threshold would leave real files unflagged.
  await reachDownloadWithText(page, "Left Chest", "FRITSCHS");
  await expect(page.getByTestId("jef-hoop-header-note")).toHaveCount(0);
  await expect(page.getByTestId("jef-button")).not.toHaveAttribute("aria-describedby", /./);
  expect(await jefHoopCode(page)).not.toBe(0);
});
