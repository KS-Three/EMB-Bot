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

  // The recap ABOVE the grade, which nothing had ever looked at on this path.
  // Every assertion in this file was about `.quality`, and every recap
  // assertion lives in wizard-smoke.spec.js on the text and image paths —
  // both of which have their own branch. So an auto-digitized design, the
  // commonest thing this app does, recapped as `Content: Text — ""` with a
  // blank `Font` (measured in a browser 2026-09-07): App.svelte's summary
  // ended in a text-shaped `{:else}`, and `digitized` fell into it.
  const summary = page.locator("dl.summary");
  await expect(summary).toContainText("Auto-digitized artwork");
  await expect(summary).toContainText(path.basename(ART_PNG));
  await expect(summary).not.toContainText("Text —");
  // A blank <dd> is how the old Font row rendered — assert every row has one.
  const values = await summary.locator("dd").allInnerTexts();
  expect(values.length).toBeGreaterThanOrEqual(4);
  for (const v of values) expect(v.trim()).not.toBe("");

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

  // The `stats` half. Thread length AND the trim count live only on the job
  // envelope, never in preflight's metrics, so both figures here prove the
  // plumbing rather than re-reading something preflight already had. Trims
  // sit before metres on purpose: trims and thread changes are what the
  // operator has to DO, metres is what they have to buy.
  await expect(quality.locator(".qr-bill"))
    .toHaveText(/[\d,]+ stitches · \d+ thread changes? · \d+ trims? · [\d.]+ m of thread/);
});

test("a lettering-only project shows no quality section", async ({ page }) => {
  test.skip(!serviceUp, skipReason);

  // Preflight runs in the Python digitizer, so browser-generated lettering has
  // no report to show. An empty "Quality check" heading over nothing would
  // imply the check ran and passed.
  await page.goto("/");
  await page.locator(".tcard", { hasText: "Left-chest name" }).click();
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await page.getByRole("button", { name: "3 Review" }).click();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();
  await expect(page.locator(".quality")).toHaveCount(0);
});

// The thread picker offers replacements from a chart — and it defaulted to
// Studio's 56 generic shades on a design whose cones the engine chose out of
// a 398-colour catalog. Found 2026-09-07 with the picker open, showing
// "Studio basics" directly above a label reading `0134 Smoky`: a customer
// changing one thread was offered generic names to replace a real cone, and
// picking one threw the catalog number away.
//
// Same defect as the Download step's shopping list, on a screen the fix for
// that one did not touch — `loadPreferredPaletteId()` has two callers and
// only one was passed the design's brand. It is now a store both read
// (lib/designChart.js), because ThreadPicker is used in nine places.
test("the thread picker offers the chart the design's cones came from", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  await page.getByRole("button", { name: /^Thread color/ }).first().click();
  const brand = page.locator("select.tp-brand").first();
  await expect(brand).toBeVisible();
  await expect(brand).toHaveValue("isacord");
  // And the grid really is the brand chart: catalog numbers, not shade names.
  await expect(page.locator(".tp-cell").first()).toHaveAttribute("title", /^\d{4}\s/);
});

// A NAME BESIDE A LOGO — the commonest thing a customer combines, and the case
// where "one design, one number" stopped being true.
//
// App.svelte suppressed the whole-design totals whenever `qualityEntries` was
// non-empty, on the reasoning that an auto-digitized design already gets its
// numbers from the quality report. That holds when the digitized elements ARE
// the design. On a mixed one it left the artwork's figures standing alone, and
// QualityReport hides its per-entry label at exactly one entry, so nothing
// said the number was about a part. Measured in a browser 2026-09-08:
//
//   canvas caption ....... 3,219 stitches   (966 lettering + 2,253 artwork)
//   review summary ....... 2,253 stitches   the artwork alone
//
// A 30% understatement on the screen headed "Ready to stitch", whose entire
// job is to say what you are about to sew. Same defect shape as the thread
// total that did not add up (#412) and the two widths for one design (#403).
test("a name beside a logo is summarised as one design, not as the logo", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  // Start from a real starter so the lettering is whatever the app ships,
  // not a string invented here.
  await page.locator(".tcard", { hasText: "Left-chest name" }).click();
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();

  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await page.getByRole("button", { name: "3 Review" }).click();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();

  const num = (s) => Number(String(s).replace(/[^\d]/g, ""));

  // The canvas caption is the combined design — it always was, which is what
  // made the disagreement visible on one screen.
  const caption = await page.locator(".fieldmeta").innerText();
  const combined = num((caption.match(/([\d,]+) stitches/) || [])[1]);
  expect(combined).toBeGreaterThan(0);

  // The recap must quote that same design, not one element of it.
  const summary = page.locator("dl.summary");
  await expect(summary).toContainText("Stitches");
  const dts = await summary.locator("dt").allInnerTexts();
  const dds = await summary.locator("dd").allInnerTexts();
  const stitchRow = dds[dts.findIndex((t) => t.trim() === "Stitches")];
  expect(num(stitchRow), `recap says ${stitchRow}, the field says ${combined}`).toBe(combined);

  // And the quality entry, which really is about one element, says so — the
  // label is what stops its smaller figure reading as the design's.
  const quality = page.locator(".quality");
  await expect(quality).toBeVisible();
  await expect(quality.locator(".qr-name")).toHaveText(path.basename(ART_PNG));
  const bill = num((await quality.locator(".qr-bill").innerText()).match(/([\d,]+) stitches/)[1]);
  expect(bill).toBeLessThan(combined);
});

// TWO LOGOS — the residual left by the first version of the rule above.
//
// That version suppressed the recap's totals whenever every sewable element
// was digitized, which is true of two logos as much as of one. Measured
// 2026-09-08: each entry reported 2,187 stitches, the design was 4,374, and no
// number on the recap was the design's — the customer was left adding two
// panels together. Neither entry is WRONG there, which is what makes it easy
// to miss; neither is the answer either.
//
// The rule is now "a single entry IS the design", the only case where showing
// the totals as well would really be two answers to one question.
test("two logos in one design are summarised as one design, not as two panels", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  // `.eladd-row` is the add-element row. Once an element exists its own chip
  // also matches the name "Artwork", so the bare role query is ambiguous from
  // the second add onwards.
  const addArtwork = page.locator(".eladd-row button", { hasText: "Artwork" });
  await addArtwork.click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });

  const stitches = async () => {
    const m = (await page.locator(".fieldmeta").innerText()).match(/([\d,]+) stitches/);
    return m ? Number(m[1].replace(/[^\d]/g, "")) : 0;
  };
  const afterOne = await stitches();
  expect(afterOne).toBeGreaterThan(0);

  // A second one, so no single quality entry is the design any more.
  await addArtwork.click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  await expect.poll(stitches, { timeout: 120_000 }).toBeGreaterThan(afterOne);

  await page.getByRole("button", { name: "3 Review" }).click();
  await expect(page.getByRole("heading", { name: "Ready to stitch" })).toBeVisible();

  const num = (s) => Number(String(s).replace(/[^\d]/g, ""));
  const caption = await page.locator(".fieldmeta").innerText();
  const combined = num((caption.match(/([\d,]+) stitches/) || [])[1]);
  expect(combined).toBeGreaterThan(0);

  const summary = page.locator("dl.summary");
  const dts = await summary.locator("dt").allInnerTexts();
  const dds = await summary.locator("dd").allInnerTexts();
  const i = dts.findIndex((t) => t.trim() === "Stitches");
  expect(i, "the recap states a stitch count for a two-element design").toBeGreaterThanOrEqual(0);
  expect(num(dds[i]), `recap says ${dds[i]}, the field says ${combined}`).toBe(combined);

  // Two entries, and each says which element it is about.
  const names = page.locator(".quality .qr-name");
  expect(await names.count()).toBe(2);
});
