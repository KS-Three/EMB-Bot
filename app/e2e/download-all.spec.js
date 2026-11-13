// "Download all" on the Download step: one zip with every stitch format the step
// offers, the PDF worksheet, a preview picture and the thread list (Kent,
// 2026-11-05). Driven end to end on the lettering lane, against the REAL
// digitizer service: JEF, XXX and VP3 have no browser encoder, so the button is
// disabled without it (like theirs), and the zip's three files are the
// service's.
//
// What this proves that the unit specs cannot: the files in the zip are the
// files the single buttons hand out (the lettering lane's DST is the browser
// encoder's, so the zip's DST must equal the DST button's, byte for byte), the
// service-only formats arrive non-empty, and the worksheet and picture are a
// real PDF and a real PNG.
//
// Same service bootstrap and skip posture as download-stale-artwork.spec.js:
// reuse a running service, start one from a venv if there is none, SKIP (never
// fail) with no digitizer venv. @playwright/test, not vitest.
import { test, expect } from "@playwright/test";
import { startStudio, pickTemplate, openDownload } from "./helpers.js";
import { unzipSync } from "fflate";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));

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
  const [python] = venvPythonCandidates();
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

async function savedBytes(download) {
  return new Uint8Array(readFileSync(await download.path()));
}

test("Download all saves one zip whose files are the ones the single buttons hand out", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);
  await pickTemplate(page, "Left-chest name");
  await openDownload(page);

  // The single DST button, for the byte comparison below.
  const dstPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "DST", exact: true }).click();
  const singleDst = await savedBytes(await dstPromise);
  // The line says the file was re-read, with the counts it read back.
  await expect(page.getByText(/^Saved DST \(browser encoder\) - re-read and verified: [\d,]+ stitches, \d+ colour changes?$/)).toBeVisible();

  const all = page.getByRole("button", { name: "Download all" });
  await expect(all).toBeEnabled();
  const zipPromise = page.waitForEvent("download");
  await all.click();
  const download = await zipPromise;
  expect(download.suggestedFilename()).toBe("your-name.zip");
  // Real service headers (exposed to this origin by the CORS expose list): SVG is
  // never re-read; XXX and VP3 are re-read with checks pystitch cannot give back.
  await expect(page.getByText("Saved ZIP - 6 of 7 stitch files re-read and verified (SVG not re-read; XXX, VP3 with some checks skipped)")).toBeVisible();

  const files = unzipSync(await savedBytes(download));
  expect(Object.keys(files).sort()).toEqual(
    [
      "your-name.dst", "your-name.pes", "your-name.exp", "your-name.jef", "your-name.xxx", "your-name.vp3", "your-name.svg",
      "your-name-worksheet.pdf", "your-name-preview.png", "your-name-threads.txt",
    ].sort(),
  );
  for (const [name, bytes] of Object.entries(files)) expect(bytes.length, name).toBeGreaterThan(name.endsWith("-threads.txt") ? 10 : 100);

  // The lettering lane writes DST in the browser: the zip's is the button's.
  expect(Array.from(files["your-name.dst"])).toEqual(Array.from(singleDst));
  // Real PDF and PNG.
  expect(new TextDecoder().decode(files["your-name-worksheet.pdf"].slice(0, 5))).toBe("%PDF-");
  expect(Array.from(files["your-name-preview.png"].slice(0, 4))).toEqual([0x89, 0x50, 0x4e, 0x47]);
  // The thread list names a chart and numbers the blocks in sewn order.
  const threads = new TextDecoder().decode(files["your-name-threads.txt"]);
  expect(threads).toMatch(/^Thread chart: .+\r\n1\. .+ \(#[0-9A-F]{6}\)/);
});
