// Download never ships stitches that are behind their settings.
//
// Two ways a shop used to be handed a file it had not asked for, without a
// word (area-3 doc, 2026-10-08):
//
//   (1) corner-drag a digitized logo smaller: generate.js hands `sizeMm` to
//       buildImportedDesign, which SCALES the baked stitches, so all of them
//       stay on the smaller area -- 80 -> 62 mm was 1.66x the thread per mm2;
//   (2) switch the garment after digitizing: the file still carries the first
//       garment's request (`garment_id` in the POSTed config), so the first
//       fabric's pull compensation, underlay and density.
//
// Kent's call 2026-10-25, "block until re-digitized": Download stays disabled
// while the stitches are behind, the Auto Digitize button is lit, and nothing
// is said in words (no-warnings ruling 2026-10-02). Nothing re-runs by itself
// (2026-10-05): the run is the customer's click. ONE rule (lib/staleness.js)
// drives the panel's button, the field's hatch and the Download step, and
// this spec drives all three against the REAL digitizer service.
//
// Each case: the panel and the field's hatch mark the element behind, no
// request was made, Download is locked, the customer presses the lit button,
// Download opens, and the file is what the NEW settings produce -- read back
// with pystitch, the same third-party reader CI cross-validates against.
//
// Same service bootstrap and skip posture as digitize-restitch-trigger.spec.js:
// reuse a running service, start one from a venv if there is none, SKIP
// (never fail) with no digitizer venv. @playwright/test, not vitest.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, uploadArtwork, runDigitize, openDownload, closeDownload, openAdvanced } from "./helpers.js";
import { spawn, execFileSync } from "node:child_process";
import { existsSync, readFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Two squares side by side, centred: the fixture the restitch specs use.
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
// A synthetic red disc, for the corner drag. The field gives a shape's nodes
// (9 px) priority over the element's corner handles (8 px), and every corner
// of the two squares' box IS a shape node, so a drag there grabs the shape and
// never resizes. A disc's box corners sit ~0.4 radius off its outline.
const DISC_PNG = path.join(__dirname, "fixtures", "red-disc.png");

// An uncached digitize takes a second or two on a quiet machine. On one
// pinned at 100% CPU by other work it has taken minutes, so a slow box sets
// E2E_SLOW_FACTOR (the service caches by config, so a re-run is quick again).
const SLOW = Math.max(1, Number(process.env.E2E_SLOW_FACTOR) || 1);
const DIGITIZE_MS = 120_000 * SLOW;
const CASE_MS = 300_000 * SLOW;

const STATS = "span.stats";
const MACHINE_FILES = ["DST", "PES", "EXP", "SVG"];

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
let python = null;

test.beforeAll(async () => {
  [python] = venvPythonCandidates();
  if (await healthy()) {
    serviceUp = true; // a developer's own instance -- reuse, never kill
    return;
  }
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

// ---- reading what the machine would read -----------------------------------

// The saved file, decoded by pystitch in the digitizer's venv: stitch records
// (not jumps, trims or colour changes), and the extents in mm.
function readDst(file) {
  const code = [
    "import json, sys, pystitch",
    "p = pystitch.read(sys.argv[1])",
    "n = sum(1 for s in p.stitches if (s[2] & 0xFF) == pystitch.STITCH)",
    "x0, y0, x1, y1 = p.bounds()",
    "print(json.dumps({'stitches': n, 'w': (x1 - x0) / 10, 'h': (y1 - y0) / 10}))",
  ].join("\n");
  return JSON.parse(execFileSync(python, ["-I", "-c", code, file], { encoding: "utf8" }));
}

// "8,764 stitches · 80×16 mm ..." as the field's status line reads it.
async function caption(page) {
  const text = await page.locator(STATS).innerText();
  const m = text.match(/([\d,]+) stitches/);
  const dims = text.match(/([\d.]+)×([\d.]+) mm/);
  return { text, stitches: m ? Number(m[1].replace(/,/g, "")) : NaN, w: dims ? Number(dims[1]) : NaN, h: dims ? Number(dims[2]) : NaN };
}

// Every POST /digitize the page makes, config as sent. Playwright's
// `postDataBuffer()` is null for a multipart body carrying a Blob, so the
// config part is read off the FormData in the page, by wrapping fetch.
async function tapDigitizePosts(page) {
  await page.evaluate(() => {
    const real = window.fetch;
    window.__posts = [];
    window.fetch = async (url, init) => {
      if (String(url).endsWith("/digitize") && init && init.body instanceof FormData) {
        window.__posts.push(JSON.parse(init.body.get("config")));
      }
      return real(url, init);
    };
  });
  return () => page.evaluate(() => window.__posts);
}

// The ids the field is hatching, as it mirrors them on its canvas.
const staleIds = (page) => page.locator(".hoop canvas").first().getAttribute("data-stale-ids");

async function expectBehind(page, posts, postsBefore) {
  const run = page.locator(".dgp-run");
  // The panel: the button is out of date AND lit...
  await expect(run).toHaveClass(/dgp-run-stale/);
  await expect(run).toHaveClass(/dgp-run-lit/);
  await expect(run).toHaveAttribute("data-blocks-download", "true");
  // ...the field hatches the same element...
  await expect.poll(() => staleIds(page), { timeout: 15_000 }).not.toBe("");
  // ...and nothing ran on its own.
  await page.waitForTimeout(2500);
  expect((await posts()).length).toBe(postsBefore);
}

async function expectCurrent(page) {
  const run = page.locator(".dgp-run");
  // First the attribute that is true for the whole of a pending run: the
  // class goes off the moment the button is pressed (the button is disabled
  // and reads "Digitizing…"), which is not the same as the run having landed.
  await expect(run).toHaveAttribute("data-blocks-download", "false", { timeout: DIGITIZE_MS });
  await expect(run).toHaveText("Auto Digitize Image");
  await expect(run).not.toHaveClass(/dgp-run-stale/);
  await expect(run).not.toHaveClass(/dgp-run-lit/);
  await expect.poll(() => staleIds(page), { timeout: 15_000 }).toBe("");
}

async function expectLocked(page) {
  const sheet = await openDownload(page);
  for (const label of MACHINE_FILES) {
    await expect(sheet.getByRole("button", { name: label, exact: true }), label).toBeDisabled();
  }
  // Said in no words (Kent's no-warnings ruling, 2026-10-02).
  await expect(sheet).not.toContainText(/stale|out of date|re-?digitize|behind|changed since/i);
  await closeDownload(page);
}

async function digitizedOn(page, garment, art = ART_PNG) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickGarment(page, garment);
  const posts = await tapDigitizePosts(page);
  await uploadArtwork(page, art);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: DIGITIZE_MS });
  await expectCurrent(page);
  expect((await posts()).length).toBe(1);
  return posts;
}

// Press the lit button and wait for the run it started to LAND: the request
// went out, and the button is back to current.
async function runAndLand(page, posts, expectedPosts) {
  await runDigitize(page);
  await expect.poll(async () => (await posts()).length, { timeout: 30_000 }).toBe(expectedPosts);
  await expectCurrent(page);
}

async function saveDst(page) {
  const sheet = await openDownload(page);
  const dst = sheet.getByRole("button", { name: "DST", exact: true });
  await expect(dst).toBeEnabled();
  const saved = page.waitForEvent("download");
  await dst.click();
  // pystitch picks its reader by file extension, and Playwright's own copy has
  // none: save it under the name the customer's machine would see.
  const file = path.join(mkdtempSync(path.join(tmpdir(), "emb-stale-")), "download.dst");
  await (await saved).saveAs(file);
  await closeDownload(page);
  return readDst(file);
}

test.describe("download never ships stitches that are behind their settings", () => {
  test.describe.configure({ mode: "serial" });

  test("garment switched after the run: locked and lit until the customer runs it, then the file is the new garment's", async ({ page }) => {
    test.skip(!serviceUp, skipReason);
    test.setTimeout(CASE_MS);
    const posts = await digitizedOn(page, "Left Chest");
    expect((await posts())[0].garment_id).toBe("left_chest");

    // Current: Download is open.
    const sheet = await openDownload(page);
    for (const label of MACHINE_FILES) await expect(sheet.getByRole("button", { name: label, exact: true })).toBeEnabled();
    await closeDownload(page);

    // Left Chest -> Hat Front. The stitches on the canvas are still Left
    // Chest's request.
    const before = await caption(page);
    await pickGarment(page, "Hat Front");
    await expectBehind(page, posts, 1);
    await expectLocked(page);

    // The customer's click, on the lit button.
    await runAndLand(page, posts, 2);
    expect((await posts())[1].garment_id).toBe("hat_front");

    // Download opens, and the file is the hat's job: what the caption now says.
    const after = await caption(page);
    const file = await saveDst(page);
    expect(file.stitches, `DST stitches vs caption "${after.text}" (was "${before.text}")`).toBe(after.stitches);
    expect(Math.abs(file.w - after.w)).toBeLessThanOrEqual(0.5);
    expect(Math.abs(file.h - after.h)).toBeLessThanOrEqual(0.5);
  });

  test("resized by a corner drag: locked and lit until the customer runs it, then the stitches are a fresh job's", async ({ page, browser }) => {
    test.skip(!serviceUp, skipReason);
    test.setTimeout(CASE_MS * 2);
    const posts = await digitizedOn(page, "Tote", DISC_PNG);
    const digitized = await caption(page);

    // The design is already the selected element after its upload (clicking
    // it would select a SHAPE instead). Drag its bottom-right handle toward its
    // centre, once the layout has settled: the field moves a few seconds after
    // a digitize lands.
    await expect.poll(async () => {
      const a = JSON.stringify(await page.locator(".hoop canvas").first().boundingBox());
      await page.waitForTimeout(700);
      return a === JSON.stringify(await page.locator(".hoop canvas").first().boundingBox());
    }, { timeout: 30_000 }).toBe(true);
    // Auto-snap pulls a resize toward hoop and element guides; a plain drag
    // is what this is about.
    const snap = page.getByRole("button", { name: "Auto-snap" });
    if ((await snap.getAttribute("aria-pressed")) === "true") await snap.click();
    await expect(snap).toHaveAttribute("aria-pressed", "false");
    const handles = await page.evaluate(() => {
      const c = document.querySelector(".hoop canvas");
      const r = c.getBoundingClientRect();
      const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
      const k = c.width / r.width;
      // The selection box and its four 8 px handles are the theme's accent,
      // exactly; the extreme corner pixels of that colour are the TL and BR
      // handles' outer corners.
      const hex = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim().replace("#", "");
      const A = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
      let tl = null, br = null;
      for (let i = 0, px = 0; i < d.length; i += 4, px++) {
        if (d[i + 3] > 250 && Math.abs(d[i] - A[0]) < 4 && Math.abs(d[i + 1] - A[1]) < 4 && Math.abs(d[i + 2] - A[2]) < 4) {
          const x = px % c.width, y = Math.floor(px / c.width);
          if (!tl || x + y < tl.x + tl.y) tl = { x, y };
          if (!br || x + y > br.x + br.y) br = { x, y };
        }
      }
      return tl && br && {
        // a handle is 8 px square, centred on the box's corner
        br: { x: r.x + (br.x + 1) / k - 4, y: r.y + (br.y + 1) / k - 4 },
      };
    });
    expect(handles).not.toBeNull();
    await page.mouse.move(handles.br.x, handles.br.y);
    await page.mouse.down();
    // Diagonally, toward the centre: dragResize averages the horizontal and
    // vertical estimates, so a purely horizontal pull only moves half as far.
    // Stop once the caption reads about three quarters of the digitized width.
    for (let i = 1; i <= 60; i++) {
      await page.mouse.move(handles.br.x - 4 * i, handles.br.y - 4 * i);
      if (i % 3 === 0 && (await caption(page)).w <= digitized.w * 0.78) break;
    }
    await page.mouse.up();

    // The caption follows the drag; the STITCH COUNT does not -- the bug.
    await expect.poll(async () => (await caption(page)).w, { timeout: 15_000 }).toBeLessThan(digitized.w * 0.9);
    const dragged = await caption(page);
    expect(dragged.w / digitized.w).toBeGreaterThan(0.6);
    expect(dragged.stitches).toBe(digitized.stitches);
    test.info().annotations.push({
      type: "premise",
      description: `drag ${digitized.w} -> ${dragged.w} mm kept ${dragged.stitches} stitches (digitized: ${digitized.stitches})`,
    });

    await expectBehind(page, posts, 1);
    await expectLocked(page);

    // The customer's click: the run digitizes AT the dragged width.
    await runAndLand(page, posts, 2);
    const sent = (await posts())[1].target_width_mm;
    expect(Math.abs(sent - dragged.w)).toBeLessThan(dragged.w * 0.05);
    const landed = await caption(page);
    const file = await saveDst(page);
    expect(file.stitches, `DST stitches vs caption "${landed.text}"`).toBe(landed.stitches);
    expect(Math.abs(file.w - landed.w)).toBeLessThanOrEqual(0.5);

    // ...and those stitches are the ones a fresh job at that width makes, not
    // the old count squeezed onto the smaller area.
    const fresh = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    try {
      const other = await fresh.newPage();
      await startStudio(other);
      await pickGarment(other, "Tote");
      await uploadArtwork(other, DISC_PNG, { run: false });
      await openAdvanced(other);
      const width = other.getByLabel("Design width");
      await width.fill(String(sent));
      await width.blur();
      await runDigitize(other);
      await expect(other.locator(".dgp-stats")).toBeVisible({ timeout: DIGITIZE_MS });
      await expect(other.locator(".dgp-run")).not.toHaveClass(/dgp-run-stale/, { timeout: DIGITIZE_MS });
      expect((await caption(other)).stitches).toBe(landed.stitches);
    } finally {
      await fresh.close();
    }
  });
});
