// The Review step and the printed worksheet on a DIGITIZED design.
//
// `worksheet-numbers.spec.js` already pins this agreement — but only on the
// LETTERING lane, where the numbers come from `estimate.js` walking the
// stitches in the browser. A digitized design gets them from somewhere else
// entirely: the service's `stats` block, rendered by `QualityReport.svelte`.
// Two renderings, two sources, and nothing was comparing them.
//
// That matters because the digitized lane is the one with a per-cone
// breakdown, and a shopping list is exactly the thing an operator carries to
// the machine and adds up.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import zlib from "node:zlib";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "enthusiast_logo.png");

// Same extractor the other worksheet specs use.
function pdfText(bytes) {
  const out = [];
  const raw = bytes.toString("latin1");
  const streams = [raw];
  for (const m of raw.matchAll(/stream\r?\n([\s\S]*?)endstream/g)) {
    try {
      streams.push(zlib.inflateSync(Buffer.from(m[1], "latin1")).toString("latin1"));
    } catch {
      /* not deflated */
    }
  }
  for (const s of streams) {
    for (const m of s.matchAll(/\(((?:\\.|[^\\()])*)\)\s*Tj/g)) {
      out.push(m[1].replace(/\\([()\\])/g, "$1"));
    }
  }
  return out;
}

// Same bootstrap as `digitize-auto-start.spec.js`, deliberately duplicated
// rather than merely probing /health: CI builds `digitizer/.venv` for this
// job precisely so these specs RUN, and a spec that only probes would skip
// whenever it happened to be scheduled before whichever spec starts the
// service -- a silent skip, which is the dark-suite failure the workflow
// comment warns about. Reuse a developer's own instance, never kill it.
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

test("a digitized design's review and worksheet agree, and the cone rows add up", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");
  // Patch (3.5 in) SPECIFICALLY, not Left Chest. The garment sets the fit width,
  // which sets the thread metres, which decides whether the independent
  // rounding of the total and the rows lands on a disagreement. Left Chest
  // happens to round consistently, so this spec passed against the very bug
  // it exists to catch until the garment was pinned. A fixture that does not
  // straddle the boundary is not coverage.
  await page.getByRole("button", { name: "Patch", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 240000 });

  // ---- what the review says ----------------------------------------------
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".qr-bill")).toBeVisible({ timeout: 60000 });

  const bill = (await page.locator(".qr-bill").first().innerText()).replace(/\s+/g, " ");
  const rows = await page.locator(".qr-spool-m").allInnerTexts();
  const metres = rows.map((t) => Number(t.replace(/[^\d.]/g, ""))).filter((n) => !Number.isNaN(n));

  const total = bill.match(/([\d.]+) m of thread/);
  expect(total, "review states a thread total").not.toBeNull();

  // THE POINT: a customer can add the rows up. Independently rounded, they
  // stopped agreeing -- 4.03 total with [2.85, 1.19] per cone rendered as
  // "4.0 m of thread" over 2.9 and 1.2, a list adding to 4.1.
  if (metres.length) {
    const summed = metres.reduce((a, b) => a + b, 0);
    expect(Number(total[1]), `rows ${metres.join(" + ")} must sum to the stated total`)
      .toBeCloseTo(summed, 5);
  }

  const stitches = bill.match(/([\d,]+) stitches/);
  const trims = bill.match(/(\d[\d,]*) trims?/);
  expect(stitches, "review states a stitch count").not.toBeNull();

  // ---- what the sheet says ------------------------------------------------
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const dl = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /PDF worksheet/i }).click(),
  ]).then(([d]) => d);
  const texts = pdfText(readFileSync(await dl.path()));
  const sheet = texts.join(" ");

  expect(sheet).toContain(`Stitch count: ${stitches[1]}`);
  if (trims) expect(sheet).toContain(`Trims: ${trims[1]}`);
});
