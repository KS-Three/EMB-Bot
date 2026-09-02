// End-to-end test for text-cluster detection + convert-to-text (Step 7 of
// docs/superpowers/plans/2026-08-05-text-cluster-detection.md): drives the
// REAL digitizer service through the real DigitizePanel:
//
//   upload art (the "ENTERPRISES INC." subline benchmark fixture) -> set
//   target width to 90mm (the documented benchmark size at which the
//   Python-side pipeline tags a >=10-member cluster,
//   digitizer/tests/test_pipeline.py::test_full_pipeline_tags_a_text_cluster_on_the_benchmark_subline)
//   -> Digitize -> "looks like text" badge appears -> Convert to text ->
//   the source shapes stop stitching and a real text element is created and
//   selected -> type real text, pick a font -> navigate back to the
//   digitized element -> Undo -> the original shapes resume stitching and
//   the text element is gone.
//
// Fixture-path decision (flagged unresolved by the plan, resolved here):
// enthusiast_logo.png is copied into app/e2e/fixtures/ (alongside the
// existing two-squares.png) rather than referenced via a relative path into
// digitizer/testdata/photo/. Reasons: (1) app/e2e/fixtures/ already commits
// image fixtures directly (two-squares.png), so this follows existing
// convention rather than introducing a new one; (2) the file is small
// (~18KB) with no size/licensing concern -- it's already a committed repo
// fixture used by the Python test suite, so duplicating it is
// uncontroversial per the plan's own framing; (3) a relative reach into
// digitizer/testdata/ from an app/e2e spec would couple this spec's fixture
// resolution to the digitizer package's directory layout for no benefit,
// and would break if this spec is ever run from a checkout that only has
// app/ (e.g. a partial worktree).
//
// Same service-bootstrap and fixture-discovery boilerplate as
// digitize-boundary-edit.spec.js (copied verbatim per that file's own header
// convention: "each e2e spec here is self-contained, matching that file's
// own convention").
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { existsSync, readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// The per-shape rows sit behind a closed-by-default "Edit shapes" disclosure
// (2026-09-02: a two-colour logo otherwise opened 329 controls). Anything that
// drives a row has to open it first. Idempotent, so it is safe to call after
// every re-digitize -- the panel remounts per element and closes again.
async function openShapeRows(page) {
  const btn = page.getByRole("button", { name: /^Edit shapes/ });
  await expect(btn).toBeVisible({ timeout: 120_000 });
  if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
}


const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "enthusiast_logo.png");

// Screenshot output: this suite has no prior screenshot convention anywhere
// in app/e2e/ (checked -- no page.screenshot()/toHaveScreenshot() calls
// exist elsewhere), so this uses plain page.screenshot({ path }) calls into
// app/test-results/, which app/.gitignore already ignores wholesale
// (`/test-results/`) -- no new ignore pattern needed, and these screenshots
// are verification artifacts, not golden/committed images.
const SHOT_DIR = path.join(__dirname, "..", "test-results", "text-cluster-convert");
mkdirSync(SHOT_DIR, { recursive: true });

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

test("text cluster: badge appears, convert to text, undo -- through the real service", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await page.goto("/");

  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What are you making?" })).toBeVisible();
  await page.getByRole("button", { name: "Artwork" }).click();

  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);

  // ---- set the documented 90mm benchmark width before digitizing ----------
  // Scoped via the label's own wrapping .dgp-param (not getByLabel -- the
  // label wraps BOTH the input and a trailing "mm" unit span, so its
  // computed accessible name is ambiguous/concatenated; this is the
  // unambiguous real selector).
  const widthInput = page
    .locator(".dgp-param")
    .filter({ hasText: "Stitch width" })
    .locator("input[type=number]");
  await widthInput.fill("90");
  await widthInput.blur();
  await expect(widthInput).toHaveValue("90");

  // No Digitize click: choosing the file already started a run at the DEFAULT
  // width, and the 90 above re-runs it (the params watcher counts an in-flight
  // first run, so the change is not dropped into the pre-result window). Both
  // runs write .dgp-stats, so waiting for mere visibility could read the 80mm
  // one -- wait for the benchmark width itself.
  await expect(page.locator(".dgp-stats")).toContainText(/\b90×/, { timeout: 120_000 });
  await openShapeRows(page);

  // ---- "looks like text" badge appears on at least one row ----------------
  const textBadges = page.locator(".dgp-lbadge", { hasText: "looks like text" });
  await expect(textBadges.first()).toBeVisible({ timeout: 120_000 });
  const badgeCountBefore = await textBadges.count();
  // Documented acceptance bar (test_pipeline.py): the benchmark subline
  // tags most of a >=10-member cluster. Assert real evidence, not just "a
  // badge exists somewhere".
  expect(badgeCountBefore).toBeGreaterThanOrEqual(10);

  const unstitchedBefore = await page.locator(".dgp-layer.unstitched").count();
  const elrowCountBefore = await page.locator(".ellist .elrow").count();

  await page.screenshot({ path: path.join(SHOT_DIR, "1-badge-appears.png"), fullPage: true });

  // ---- "Convert to text" action bar appears --------------------------------
  const clusterBar = page.locator(".dgp-mergebar").filter({ hasText: "looks like text" }).first();
  await expect(clusterBar).toBeVisible();
  await expect(clusterBar).toContainText("Convert to text");

  // ---- click Convert to text -- synchronous, client-side only -------------
  // Confirmed by reading App.svelte's onConvertClusterToText: it calls
  // addSeededTextElement + patches shapeOverrides in one synchronous
  // function body, no fetch/await/server round-trip. No network wait is
  // needed here.
  //
  // Real-run discovery: addSeededTextElement ALSO moves `selectedId` to the
  // brand-new text element in that same synchronous step, and
  // ContentStep.svelte's element panel is keyed on the selected element --
  // so DigitizePanel (and with it .dgp-mergebar/.dgp-lbadge/.dgp-layer)
  // unmounts the instant this click handler returns. There is no moment at
  // which "the action bar now shows Undo" is observable directly after this
  // click; that only becomes visible again once the user navigates back to
  // the digitized element (below), which is exactly why the plan's own
  // Step 8 has an explicit "navigate back" beat before checking Undo.
  await clusterBar.getByRole("button", { name: "Convert to text" }).click();

  // A new text element exists and is selected: ContentStep swaps to
  // TextStep automatically (addSeededTextElement moves selectedId to the
  // new element) -- its empty textarea is the visible signal.
  const textarea = page.locator("textarea.textin");
  await expect(textarea).toBeVisible();
  await expect(textarea).toHaveValue("");
  await expect(page.locator(".ellist .elrow")).toHaveCount(elrowCountBefore + 1);
  await expect(page.locator(".ellist .elrow.sel")).toContainText("Text");

  // Type real text, pick a font (the user fills in what detection can't).
  await textarea.fill("ENTERPRISES INC");
  await expect(textarea).toHaveValue("ENTERPRISES INC");

  await page.locator(".fs-trigger").click();
  const fontDialog = page.getByRole("dialog", { name: "Choose a font" });
  await expect(fontDialog).toBeVisible();
  await fontDialog.locator(".fb-tile").first().click();
  await expect(fontDialog).toBeHidden();
  // The trigger no longer shows the "choose a font" placeholder -- a real
  // font is now selected.
  await expect(page.locator(".fs-trigger .fs-name")).not.toHaveText("Choose a font");

  await expect(page.locator(".ellist .elrow.sel")).toContainText('"ENTERPRISES INC"');

  await page.screenshot({ path: path.join(SHOT_DIR, "2-converted-to-text.png"), fullPage: true });

  // ---- navigate back to the digitized element's panel ----------------------
  await page.locator(".ellist .elrow").filter({ hasText: "Digitized" }).click();
  await expect(page.locator(".dgp-stats")).toBeVisible();
  await openShapeRows(page);
  const clusterBarAgain = page.locator(".dgp-mergebar").filter({ hasText: "looks like text" }).first();

  // The action bar now shows Undo instead of Convert -- this is the first
  // point since the click where DigitizePanel is mounted again to check it.
  await expect(clusterBarAgain.getByRole("button", { name: "Undo — remove text element" })).toBeVisible();
  await expect(clusterBarAgain.getByRole("button", { name: "Convert to text" })).toHaveCount(0);

  // The converted cluster's member rows no longer show the badge (they've
  // moved to DigitizePanel's "unstitched" row branch, which renders no
  // per-row badges at all) and the unstitched-row count grew by exactly the
  // number of members that were converted.
  await expect(page.locator(".dgp-lbadge", { hasText: "looks like text" })).toHaveCount(0);
  await expect(page.locator(".dgp-layer.unstitched")).toHaveCount(unstitchedBefore + badgeCountBefore);

  // ---- a converted cluster member must never look restorable ---------------
  // Regression coverage for the interaction between this feature and the
  // BACKGROUND_ENCLOSED bulk-restore banner: a converted member's
  // stitched:false is a permanent hide belonging to THIS feature, not the
  // digitizer's own enclosed-background default, so it must never render a
  // "Sew it" button (which would silently un-hide it underneath the new
  // text element) and must never be counted by the banner's bulk action.
  // Only the pre-conversion baseline (genuine enclosed-background rows, if
  // any -- `unstitchedBefore`) is allowed to still offer "Sew it".
  await expect(
    page.locator(".dgp-layer.unstitched").getByRole("button", { name: "Sew it" })
  ).toHaveCount(unstitchedBefore);
  await expect(
    page.locator(".dgp-layer.unstitched").getByText("hidden — converted to text")
  ).toHaveCount(badgeCountBefore);
  if (unstitchedBefore > 0) {
    await expect(page.locator(".dgp-enclosed-banner")).toContainText(`Sew all ${unstitchedBefore}`);
  } else {
    await expect(page.locator(".dgp-enclosed-banner")).toBeHidden();
  }

  // ---- Undo -----------------------------------------------------------------
  await clusterBarAgain.getByRole("button", { name: "Undo — remove text element" }).click();

  // Action bar reverts to "Convert to text".
  await expect(clusterBarAgain.getByRole("button", { name: "Convert to text" })).toBeVisible();
  await expect(clusterBarAgain.getByRole("button", { name: "Undo — remove text element" })).toHaveCount(0);

  // The originally-unstitched member rows return to normal (badge count and
  // unstitched-row count both revert exactly).
  await expect(page.locator(".dgp-lbadge", { hasText: "looks like text" })).toHaveCount(badgeCountBefore);
  await expect(page.locator(".dgp-layer.unstitched")).toHaveCount(unstitchedBefore);

  // The text element created by the conversion is gone from the element
  // list.
  await expect(page.locator(".ellist .elrow")).toHaveCount(elrowCountBefore);
  await expect(page.locator(".ellist .elrow").filter({ hasText: "ENTERPRISES INC" })).toHaveCount(0);

  await page.screenshot({ path: path.join(SHOT_DIR, "3-after-undo.png"), fullPage: true });
});
