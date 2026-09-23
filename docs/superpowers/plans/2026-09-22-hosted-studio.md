# Hosted Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the EMB-Bot Studio as a free, self-contained static web app on GitHub Pages, with the localhost-digitizer assumptions honestly handled instead of silently broken.

**Architecture:** One build-time flag, `VITE_HOSTED`, set only by the Pages deploy job. It gates three things: the doomed `127.0.0.1:8721` health probe, the ContentStep note that currently claims art is not digitized when it is, and the unavailable-reason copy on the three service-only export formats. No runtime behaviour, no availability logic, and no engine code changes — `digitizerHealth` already goes `null` and every lane already falls back correctly.

**Tech Stack:** Svelte 5 + Vite 8 (`app/`), vitest for units and component specs, Playwright for browser proof, GitHub Actions for deploy.

**Spec:** `docs/superpowers/specs/2026-09-22-hosted-studio-design.md`

## Global Constraints

- **Branch:** `claude/hosted-studio`, already cut from `origin/main`; spec committed at `a66e4025`.
- **`VITE_HOSTED` is read as the exact string `"1"`.** Any other value, including `"true"`, is not hosted.
- **The flag is set by the deploy job and the hosted Playwright config ONLY.** A local `npm run dev` / `npm run build` must stay unhosted so Kent's machine keeps probing the service.
- **Do not touch `*Available` logic** in `DownloadStep.svelte`. It is already correct under hosting — it goes false, which is the truth. Only the `*Title` reason strings change.
- **Do not touch** `digitizer/`, `src/`, or any stitch engine. This plan changes `app/`, `.github/workflows/`, `README.md` and `PRODUCT.md` only.
- **Never `git add -A`.** The working tree carries untracked files from other lanes (`digitizer/renders/`, `digitizer/sam2_isolated/venv.husk-2026-09-22/`, `docs/becker-axis-review-2026-09-17.md`, `docs/loose-work-2026-09-18.md`, `docs/renders/becker-axis-2026-09-17/`). Stage by name, every time.
- **Edits to source use the Edit tool, never a PowerShell regex round-trip** — it silently corrupts UTF-8 in this repo (CLAUDE.md footgun #3). The copy strings in this plan contain em-dashes.
- **Run the studio suite from `app/`:** `cd app && npx vitest run`.

---

### Task 1: The hosted flag, and a probe that does not fire

**Files:**
- Create: `app/src/lib/hosted.js`
- Create: `app/src/lib/hosted.spec.js`
- Modify: `app/src/lib/digitizer.js:38-87` (add import; change `fetchHealth`)
- Test: `app/src/lib/digitizer.spec.js` (append two tests)

**Interfaces:**
- Produces: `isHosted(): boolean` from `app/src/lib/hosted.js`. Consumed by Tasks 3 and 4.
- Produces: `fetchHealth(fetchFn?, { hosted? }?): Promise<object|null>` — second parameter is new and optional. `App.svelte:352` calls `fetchHealth()` with no arguments and must keep working unchanged.

- [ ] **Step 1: Write the failing test for `isHosted`**

Create `app/src/lib/hosted.spec.js`:

```js
import { test, expect, vi, afterEach } from "vitest";
import { isHosted } from "./hosted.js";

afterEach(() => {
  vi.unstubAllEnvs();
});

test("unset VITE_HOSTED is not hosted", () => {
  expect(isHosted()).toBe(false);
});

test("the exact string \"1\" is hosted", () => {
  vi.stubEnv("VITE_HOSTED", "1");
  expect(isHosted()).toBe(true);
});

// Deliberate: a truthy-looking value must NOT flip the posture. The flag is
// set in exactly two places (the Pages job, the hosted Playwright config) and
// a typo there should fail closed to the desktop behaviour, not silently
// publish a build that stops probing on Kent's own machine.
test("any other value is not hosted", () => {
  vi.stubEnv("VITE_HOSTED", "true");
  expect(isHosted()).toBe(false);
  vi.stubEnv("VITE_HOSTED", "");
  expect(isHosted()).toBe(false);
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd app && npx vitest run src/lib/hosted.spec.js`
Expected: FAIL — `Failed to resolve import "./hosted.js"`.

- [ ] **Step 3: Create `app/src/lib/hosted.js`**

```js
// Build-time posture flag, set ONLY by the GitHub Pages deploy job and the
// hosted Playwright config (VITE_HOSTED=1). A local `npm run dev` or
// `npm run build` leaves it unset, so Kent's own machine keeps probing the
// localhost digitizer service and nothing about the desktop workflow changes.
//
// Read through a function rather than a module-level const so vitest's
// vi.stubEnv can drive both postures inside a single run. The try/catch
// mirrors the house pattern digitizer.js already uses for localStorage: an
// environment that does not define import.meta.env is "not hosted", never a
// throw.
export function isHosted() {
  try {
    return import.meta.env.VITE_HOSTED === "1";
  } catch (e) {
    return false;
  }
}
```

- [ ] **Step 4: Run it and watch it pass**

Run: `cd app && npx vitest run src/lib/hosted.spec.js`
Expected: PASS, 3 tests.

- [ ] **Step 5: Write the failing tests for the probe**

Append to `app/src/lib/digitizer.spec.js`. First confirm `fetchHealth` is in that file's import list from `./digitizer.js` and add it if it is not:

```js
// A hosted build has no localhost service and never will. The probe is not
// merely doomed there — from an HTTPS page it is blocked as mixed content and
// logged as an error on EVERY page load, on the product's public face. This
// asserts the request is not made at all, not merely that the result is null.
test("hosted: fetchHealth returns null without calling fetch", async () => {
  const fetchFn = vi.fn(() => {
    throw new Error("fetch must not be called on a hosted build");
  });
  const h = await fetchHealth(fetchFn, { hosted: true });
  expect(h).toBe(null);
  expect(fetchFn).not.toHaveBeenCalled();
});

// The desktop path is the one Kent uses; the flag must not disturb it.
test("unhosted: fetchHealth still probes and returns the payload", async () => {
  const fetchFn = vi.fn(async () => ({ ok: true, json: async () => ({ status: "ok" }) }));
  const h = await fetchHealth(fetchFn, { hosted: false });
  expect(h).toEqual({ status: "ok" });
  expect(fetchFn).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 6: Run them and watch the first fail**

Run: `cd app && npx vitest run src/lib/digitizer.spec.js -t "fetchHealth"`
Expected: the hosted test FAILS with `fetch must not be called on a hosted build`; the unhosted test PASSES (that behaviour already exists).

- [ ] **Step 7: Change `fetchHealth`**

In `app/src/lib/digitizer.js`, add to the import block near the top (beside `import { loadPreferredPaletteId } from "./threads.js";`):

```js
import { isHosted } from "./hosted.js";
```

Then replace the `fetchHealth` declaration line and add the guard as the first statement in the body. Current:

```js
export async function fetchHealth(fetchFn = globalThis.fetch) {
  try {
```

Becomes:

```js
export async function fetchHealth(fetchFn = globalThis.fetch, { hosted = isHosted() } = {}) {
  // A hosted build has no localhost service and never will, so this request
  // cannot succeed — and from an HTTPS page it is blocked as mixed content
  // and logged as an error on every page load. Return the same null the
  // catch below would produce, without spending the request.
  if (hosted) return null;
  try {
```

Leave the rest of the function untouched.

- [ ] **Step 8: Run the full studio suite**

Run: `cd app && npx vitest run`
Expected: PASS, no regressions. `App.svelte:352` calls `fetchHealth()` with no arguments — the new parameter is optional and defaults through `isHosted()`, which is false in the test environment.

- [ ] **Step 9: Commit**

```bash
git add app/src/lib/hosted.js app/src/lib/hosted.spec.js app/src/lib/digitizer.js app/src/lib/digitizer.spec.js
git commit -m "The hosted flag, and a health probe that does not fire under it"
```

---

### Task 2: A Playwright rig that drives a real hosted build

**Files:**
- Create: `app/playwright.hosted.config.js`
- Create: `app/e2e/hosted/smoke.spec.js`
- Modify: `app/playwright.config.js` (add `testIgnore`)
- Modify: `app/package.json` (add `test:e2e:hosted` script)

**Interfaces:**
- Consumes: `isHosted()` and the Task 1 probe change, exercised end-to-end rather than mocked.
- Produces: `npm run test:e2e:hosted` — the gate Tasks 3 and 4 add their assertions to.

Why this comes before the copy changes: it is the only thing that proves the built bundle behaves, and ContentStep/DownloadStep are expensive to render in isolation (both pull the engine plus many children). Building the rig first means Tasks 3 and 4 each land with real browser evidence instead of a mocked render.

- [ ] **Step 1: Stop the main config sweeping the hosted specs**

`app/playwright.config.js` has `testDir: "./e2e"`, which would collect `e2e/hosted/` too — and those specs need a hosted build, not the dev server. Add one line immediately after it:

```js
  testDir: "./e2e",
  // e2e/hosted/* need a HOSTED production build served by `vite preview`,
  // not this config's dev server — they run from playwright.hosted.config.js.
  testIgnore: "hosted/**",
```

- [ ] **Step 2: Create the hosted config**

Create `app/playwright.hosted.config.js`:

```js
// Playwright config for the HOSTED posture: a real `vite build` with
// VITE_HOSTED=1, served by `vite preview`, with NO digitizer service running.
// That is exactly what GitHub Pages serves, so this is the only test in the
// repo that exercises what a customer actually gets.
//
// Browser executable path: same sandbox pin as playwright.config.js — see the
// comment there and CLAUDE.md footgun #6.
import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";

const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium";
const launchOptions = existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {};

// 5184, one past playwright.config.js's 5183, so both suites can run at once.
const PORT = 5184;
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e/hosted",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], launchOptions } }],
  webServer: {
    // `env` below rather than a `VITE_HOSTED=1 ...` prefix: that prefix is
    // POSIX-only and Kent runs Windows, where it is a syntax error.
    command: "npm run build && npx vite preview --port 5184 --strictPort",
    env: { VITE_HOSTED: "1" },
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    // A cold build plus preview startup; the build itself measured 2.26s.
    timeout: 120_000,
  },
});
```

- [ ] **Step 3: Add the npm script**

In `app/package.json`, add one line to `"scripts"` after `"test:e2e"`:

```json
    "test:e2e:hosted": "playwright test -c playwright.hosted.config.js",
```

- [ ] **Step 4: Write the failing smoke test**

Create `app/e2e/hosted/smoke.spec.js`:

```js
// The hosted build, in a real browser, with no digitizer service running.
import { test, expect } from "@playwright/test";

// Nothing may reach for the localhost service from a hosted build. This is the
// assertion Task 1's unit test makes, re-made against the shipped bundle —
// where an accidental static import or a second call site would still fire it.
test("no request is made to the digitizer service", async ({ page }) => {
  const attempts = [];
  page.on("request", (r) => {
    if (r.url().includes("8721")) attempts.push(r.url());
  });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  expect(attempts).toEqual([]);
});

// The app has to actually boot from a relative-base build served at root.
test("the Studio loads and reaches the content step", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Text", exact: true })).toBeVisible({ timeout: 15_000 });
  expect(errors).toEqual([]);
});
```

- [ ] **Step 5: Run it**

Run: `cd app && npm run test:e2e:hosted`
Expected: PASS, 2 tests. If the "Text" button is not reachable from the first screen, read `app/e2e/wizard-smoke.spec.js` for how that suite navigates from the garment step and mirror it — do not weaken the assertion to make it pass.

- [ ] **Step 6: Prove one full lane reaches a file**

Spec §8.4 asks that every lane reach a downloadable file on the hosted build.

**Deliberate narrowing, flag it in the PR body.** This step proves ONE lane —
text → DST — end to end on the hosted bundle. The other four (shapes, manual
draw, DST import, image upload) are already covered lane-by-lane by the
existing dev-server e2e suite, and nothing in this change touches lane logic:
the flag gates a probe and two strings. Re-proving all five against a second
posture buys a rebuild of existing coverage, not new signal. If Kent wants the
full five, it is four more tests in this same file.

Append to `app/e2e/hosted/smoke.spec.js`. Read `app/e2e/wizard-smoke.spec.js`
first and mirror its navigation and download interception verbatim — it
already walks garment → content → download and captures a file:

```js
// The whole point: a hosted build, with no service anywhere, still hands a
// customer a real stitch file. Navigation and download capture are lifted
// from e2e/wizard-smoke.spec.js — if that spec changes, change this with it.
test("text lane reaches a downloadable DST", async ({ page }) => {
  await page.goto("/");
  // <- mirror wizard-smoke.spec.js's steps to the download step here
  const download = await page.waitForEvent("download");
  expect(download.suggestedFilename()).toMatch(/\.dst$/i);
});
```

Run: `cd app && npm run test:e2e:hosted`
Expected: PASS, 3 tests. If the download never fires, the lane is genuinely
broken on a hosted build and that is a finding — report it, do not delete the
test.

- [ ] **Step 7: Commit**

```bash
git add app/playwright.hosted.config.js app/e2e/hosted/smoke.spec.js app/playwright.config.js app/package.json
git commit -m "A Playwright rig that drives a real hosted build with no service"
```

---

### Task 3: ContentStep stops claiming art is not digitized

**Files:**
- Modify: `app/src/ui/ContentStep.svelte` (script: add import; template around `:237-245`)
- Test: `app/e2e/hosted/smoke.spec.js` (append one test)

**Interfaces:**
- Consumes: `isHosted()` from `app/src/lib/hosted.js` (Task 1).

The note at `ContentStep.svelte:241` currently reads *"Artwork will be placed but not auto-digitized — that needs the local digitizer service. Start it, then [check again]."* Its own code comment three lines above says the opposite is true: *"it just falls back to the browser engine's own flatten-and-sew lane."* Confirmed at `project.js:412` — with health null, artwork routes to `"image"`, which is a real digitize.

**Scope note, deliberate:** the UNHOSTED string is left exactly as it is. It is misleading in the same way, but locally there is an actionable fix behind it (start the service), so it has a job to do. Rewording the desktop case is a separate call for Kent and is out of this spec.

- [ ] **Step 1: Write the failing test**

Append to `app/e2e/hosted/smoke.spec.js`:

```js
// On a hosted build the service can never appear, so "start it" is advice
// nobody can follow and the recheck button is a dead affordance. The note has
// to describe what the web app actually does.
test("the digitize note describes the browser lane, not a missing service", async ({ page }) => {
  await page.goto("/");
  const note = page.locator(".digitize-offline");
  await expect(note).toBeVisible({ timeout: 15_000 });
  await expect(note).toContainText("in your browser");
  await expect(note).not.toContainText("Start it");
  await expect(page.locator(".digitize-recheck")).toHaveCount(0);
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd app && npm run test:e2e:hosted -- -g "digitize note"`
Expected: FAIL — the note contains "Start it" and `.digitize-recheck` exists.

- [ ] **Step 3: Import the flag in ContentStep**

In `app/src/ui/ContentStep.svelte`, add to the script's import block:

```js
  import { isHosted } from "../lib/hosted.js";
```

and immediately after the `export let sewnColors = null;` line, add:

```js
  // Build-time posture, not reactive state: a hosted bundle can never reach a
  // localhost service, so the "start it and check again" affordance below is
  // dead there and the note has to say what actually happens instead.
  const hosted = isHosted();
```

- [ ] **Step 4: Branch the note**

Replace the whole `{#if !digitizerHealth}` block (the `<p class="digitize-offline">` and its comment) with:

```svelte
{#if !digitizerHealth}
  <!-- The tile no longer disappears when the service is down — Artwork still
       works, it just falls back to the browser engine's own flatten-and-sew
       lane (App.onAddElement). So this says what CHANGES rather than what is
       missing: art still goes in, it is not auto-digitized. -->
  {#if hosted}
    <!-- Hosted: there is nothing to start, so "not auto-digitized" would be
         both wrong and unactionable. project.js:412 routes artwork to the
         browser lane when health is null, and that IS a digitize. -->
    <p class="digitize-offline">
      Artwork is digitized right here in your browser. The desktop version
      adds a finer satin pass on small detail.
    </p>
  {:else}
    <p class="digitize-offline">
      Artwork will be placed but not auto-digitized — that needs the local
      digitizer service. Start it, then
      <button type="button" class="digitize-recheck" on:click={() => d("checkservice")}>check again</button>.
    </p>
  {/if}
{/if}
```

- [ ] **Step 5: Run the hosted e2e and the studio suite**

Run: `cd app && npm run test:e2e:hosted`
Expected: PASS, 4 tests.

Run: `cd app && npx vitest run`
Expected: PASS. `ContentStep.reactivity.spec.js` compiles the component source and asserts on legacy-effect dependency lists — `hosted` is a plain `const`, not a `$:` statement, so it adds no reactive dependency. If that spec fails, the branch was written as `$:` by mistake.

- [ ] **Step 6: Commit**

```bash
git add app/src/ui/ContentStep.svelte app/e2e/hosted/smoke.spec.js
git commit -m "ContentStep: on a hosted build, say that art digitizes in the browser"
```

---

### Task 4: The three service-only formats get a reason a hosted user can act on

**Files:**
- Modify: `app/src/ui/DownloadStep.svelte:133-162` (script: add import; three `*Title` strings)
- Test: `app/e2e/hosted/smoke.spec.js` (append one test)

**Interfaces:**
- Consumes: `isHosted()` from `app/src/lib/hosted.js` (Task 1).

JEF (Janome), XXX (Singer) and VP3 (Husqvarna Viking / Pfaff) have no browser encoder — `exporters.js:97` holds them in `SERVICE_ONLY_FORMATS`, and `src/` has `dst.js`, `exp.js`, `pes.js`, `svgexport.js` and nothing else. On a hosted build they are permanently unavailable, and their current reason tells the user to start a service that does not exist.

**Kent's ruling 2026-09-22:** the buttons stay visible and disabled, with honest copy. Not hidden.

- [ ] **Step 1: Write the failing test**

Append to `app/e2e/hosted/smoke.spec.js`:

```js
// JEF/XXX/VP3 are service-only (exporters.js:97) and no browser encoder
// exists, so a hosted build can never write them. Kent's ruling: keep the
// buttons visible and disabled, but stop telling people to start something
// they cannot start.
test("service-only formats are disabled with a reason a hosted user can act on", async ({ page }) => {
  await page.goto("/");
  // Walk to the download step the same way wizard-smoke.spec.js does; if that
  // navigation differs, copy it from there rather than weakening this test.
  for (const label of ["JEF", "XXX", "VP3"]) {
    const btn = page.getByRole("button", { name: new RegExp(label) });
    await expect(btn).toBeVisible();
    await expect(btn).toBeDisabled();
    const title = await btn.getAttribute("title");
    expect(title).toContain("desktop version");
    expect(title).not.toContain("digitizer service running");
  }
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd app && npm run test:e2e:hosted -- -g "service-only formats"`
Expected: FAIL — the title reads "needs the digitizer service running".

If the test cannot reach the download step, read `app/e2e/wizard-smoke.spec.js` and mirror its navigation into this spec before changing any assertion.

- [ ] **Step 3: Import the flag in DownloadStep**

In `app/src/ui/DownloadStep.svelte`, add to the script's import block:

```js
  import { isHosted } from "../lib/hosted.js";
```

and near the other top-of-script declarations:

```js
  // Build-time posture. On a hosted bundle the three service-only formats can
  // never become available, so their unavailable reason must name the desktop
  // version rather than a service the user has no way to start.
  const hosted = isHosted();
```

- [ ] **Step 4: Change the three reason strings**

Leave every `*Available` line exactly as it is — they are already correct under hosting. Change only the falsy branch of each `*Title`:

```js
  $: jefTitle = jefAvailable
    ? "Janome JEF, written by the digitizer service"
    : hosted
      ? "Janome JEF needs the desktop version — it has no in-browser encoder"
      : "Janome JEF needs the digitizer service running — it has no in-browser encoder";
```

```js
  $: xxxTitle = xxxAvailable
    ? "Singer XXX, written by the digitizer service"
    : hosted
      ? "Singer XXX needs the desktop version — it has no in-browser encoder"
      : "Singer XXX needs the digitizer service running — it has no in-browser encoder";
  $: vp3Available = !isServiceOnlyFormat("vp3") || !!digitizerHealth;
  $: vp3Title = vp3Available
    ? "Husqvarna Viking / Pfaff VP3, written by the digitizer service"
    : hosted
      ? "Husqvarna Viking / Pfaff VP3 needs the desktop version — it has no in-browser encoder"
      : "Husqvarna Viking / Pfaff VP3 needs the digitizer service running — it has no in-browser encoder";
```

- [ ] **Step 5: Run both suites**

Run: `cd app && npm run test:e2e:hosted`
Expected: PASS, 5 tests.

Run: `cd app && npx vitest run`
Expected: PASS. `DownloadStep.spec.js` asserts on format offerings and absence of the old DST caveat; it runs unhosted, so all three unhosted strings must be byte-identical to what shipped.

- [ ] **Step 6: Commit**

```bash
git add app/src/ui/DownloadStep.svelte app/e2e/hosted/smoke.spec.js
git commit -m "JEF/XXX/VP3: name the desktop version, not a service nobody can start"
```

---

### Task 5: The Pages deploy job

**Files:**
- Modify: `.github/workflows/python-package-conda.yml` (add `permissions`, `concurrency`, and a `pages` job)

**Interfaces:**
- Consumes: `VITE_HOSTED=1` at build time (Task 1).

**Prerequisite Kent must do by hand, once:** GitHub → repo Settings → Pages → **Source: GitHub Actions**. The workflow cannot enable this, and `deploy-pages` fails with *"Get Pages site failed"* until it is set. Do not start this task without confirming it.

**Deliberate deviation from the spec, flag it in the PR body.** The spec says "after the existing required checks", which is all four. This job needs `engine`, `studio` and `studio-e2e` only — the three that cover the shipped bundle. `digitizer` runs 33–55 minutes (CLAUDE.md footgun #7) and tests Python that is not in `dist/` at all; gating a static JS deploy on it would add ~50 minutes to every publish for no signal about the thing being published. If Kent wants it faithful to the letter, add `digitizer` to `needs`.

- [ ] **Step 1: Add the top-level permissions and concurrency blocks**

`deploy-pages` needs an OIDC token. Immediately after the `on:` block in `.github/workflows/python-package-conda.yml`, add:

```yaml
permissions:
  contents: read
  pages: write
  id-token: write

# One in-flight Pages deploy at a time; never cancel one mid-publish.
concurrency:
  group: pages
  cancel-in-progress: false
```

- [ ] **Step 2: Add the deploy job**

Append to the end of the `jobs:` mapping, at the same indentation as `engine:` and `studio:`:

```yaml
  pages:
    # Publishes app/dist to GitHub Pages. Push to main only — a PR must never
    # replace the live site.
    #
    # needs is engine/studio/studio-e2e, NOT digitizer: those three cover what
    # is actually in the bundle, while digitizer runs 33-55 min against Python
    # that ships nowhere near dist/. Gating the deploy on it would add ~50 min
    # to every publish for no signal about the thing being published.
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [engine, studio, studio-e2e]
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
          cache-dependency-path: app/package-lock.json
      - name: Install
        working-directory: app
        run: npm ci
      - name: Build (hosted)
        working-directory: app
        env:
          # The ONLY place besides playwright.hosted.config.js that sets this.
          VITE_HOSTED: '1'
        run: npm run build
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: app/dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Structural check before pushing**

No YAML parser is reachable here — this machine's `python` has no PyYAML and
the app's dependency tree ships no `yaml` package (controller checked both,
ledger F2). GitHub's own parse is the real gate; this catches the realistic
local failure, which is indentation.

Run:

```bash
grep -nE "^  [a-z0-9-]+:$" .github/workflows/python-package-conda.yml && grep -nE "^(permissions|concurrency):$" .github/workflows/python-package-conda.yml
```

Expected: the first command lists `pages:` alongside `engine:`, `studio:`,
`digitizer:`, `studio-e2e:` and `art-fidelity-baseline:` — all at exactly two
spaces, `pages` among them. The second prints `permissions:` and
`concurrency:` at column 0. If `pages:` appears at any other indentation it is
nested inside the previous job and the workflow is wrong.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/python-package-conda.yml
git commit -m "Publish app/dist to GitHub Pages on push to main"
```

---

### Task 6: The docs stop being wrong

**Files:**
- Modify: `README.md:17`, `README.md:61`
- Modify: `PRODUCT.md:48`

No test. These are prose corrections; the guard is reading them.

- [ ] **Step 1: Fix the font count**

`README.md` says `55-font` in two places. It is **85** — `src/fonts/bin/` holds 85 `.embf`, the built `dist/fonts/bin` holds 85, and `PRODUCT.md` row 7 states 85 with its own evidence trail.

Line 17: `and a **55-font pre-digitized satin library** loaded on demand.` → `85-font`.
Line 61: `pick a font from the 55-font pre-digitized` → `85-font`.

- [ ] **Step 2: Add the hosted URL to the README quick start**

Immediately above the `## Quick start` fenced block, add:

```markdown
**Try it without installing anything:** <https://ks-three.github.io/EMB-Bot/>
— the full Studio, running entirely in your browser. Designs stay on your
machine; there is no account and nothing is uploaded. The hosted build writes
DST, PES and EXP; JEF, XXX and VP3 need the local digitizer service, which is
a desktop-only component.
```

- [ ] **Step 3: Amend the desktop-only line**

`PRODUCT.md:48` currently reads `- Desktop-only, stated on the site.` Replace with:

```markdown
- **Hosted web app, free, no account** (Kent's call 2026-09-22 —
  `docs/superpowers/specs/2026-09-22-hosted-studio-design.md`). This replaces
  "Desktop-only, stated on the site." Hosting breaks the letter of that line
  and keeps every promise underneath it: projects live in the browser's own
  storage, nothing is uploaded, there is no account and no subscription. The
  line existed to differentiate against a subscription SaaS competitor and had
  become a distribution cost instead. The Python digitizer stays desktop-only,
  which is what makes JEF/XXX/VP3 unavailable on the web — see the spec's §5.3.
```

- [ ] **Step 4: Re-read both files around the edits**

Run: `cd "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot" && grep -n "55-font\|85-font\|github.io" README.md && sed -n '44,58p' PRODUCT.md`
Expected: no `55-font` remains; two `85-font`; the URL present; the PRODUCT.md replacement reads cleanly in context.

- [ ] **Step 5: Commit**

```bash
git add README.md PRODUCT.md
git commit -m "The font count is 85, and the product is hosted"
```

---

## Closing out

- [ ] **Full verification, recorded not assumed**

```bash
cd "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot" && node --test 2>&1 | tail -5
```

```bash
cd "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/app" && npx vitest run 2>&1 | tail -5
```

```bash
cd "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/app" && npm run test:e2e:hosted 2>&1 | tail -10
```

Paste the real output. Per CLAUDE.md: never pipe a test run to `tail` in a way that makes the harness report `tail`'s exit code — these are foreground reads where the printed summary is the evidence, so read the summary line, not the exit status.

- [ ] **Adversarial diff re-read** — `git diff origin/main...HEAD`, checking specifically that no `*Available` logic moved, no unhosted string changed, and nothing under `digitizer/` or `src/` is in the diff.

- [ ] **Open the PR ready-for-review, arm auto-merge** (CLAUDE.md: ready-for-review by default, arm while `mergeable_state` is `blocked`). PR body must state the Task 5 `needs` deviation and that hosted v1 serves no Janome, Singer, Husqvarna or Pfaff owner.

- [ ] **After merge, verify the live site** — open `https://ks-three.github.io/EMB-Bot/`, confirm it loads, confirm no request to `8721` in the network panel, and screenshot it. The deploy is not done until the URL has been driven.

- [ ] **Update `MASTER_SCOPE.md`** via the `update-master-scope` skill — this changes a capability area's status (the product now has a distribution path) and `PRODUCT.md`'s launch posture.
