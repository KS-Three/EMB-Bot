// Every failure a customer can hit, forced in a real browser, and the words
// they are shown.
//
// The Studio used to render `err.message` as it came: "Failed to fetch" when
// the service was not running, "The operation was aborted due to timeout", a
// service traceback, "[object Object]" for a validation error. This spec drives
// each failure through the real UI and pins two things per case: the sentence
// says what happened and what to do, and the raw text is gone.
//
// The digitizer service is MOCKED here (page.route on 127.0.0.1:8721) rather
// than started, on purpose: a real service cannot be told to fail on cue, and
// this spec must run on a machine with no digitizer venv. The service's own
// success path is covered by digitize-auto-start.spec.js.
import { test, expect } from "@playwright/test";
import { startStudio, typeText, pickGarment, openDownload, uploadArtwork, runDigitize } from "./helpers.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "two-squares.png");
const SERVICE = "http://127.0.0.1:8721";
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "*",
  "access-control-allow-methods": "GET,POST,OPTIONS",
};
const json = (status, body) => ({ status, headers: { ...CORS, "content-type": "application/json" }, body: JSON.stringify(body) });

// `behave` maps "METHOD /path" -> route => fulfill/abort. /health is always up
// unless the case says otherwise: the Studio gates the whole feature on it, so
// "service down at click time" means health ok, then the call failing.
async function mockService(page, behave = {}) {
  await page.route(SERVICE + "/**", async (route) => {
    const req = route.request();
    if (req.method() === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });
    const key = req.method() + " " + new URL(req.url()).pathname;
    if (behave[key]) return behave[key](route);
    if (key === "GET /health") return route.fulfill(json(200, { status: "ok" }));
    return route.fulfill(json(404, { detail: "unmocked " + key }));
  });
}

const FORBIDDEN = /failed to fetch|networkerror|\[object|traceback|aborted due to|answered \d{3}/i;

async function loadArtwork(page) {
  await startStudio(page);
  await uploadArtwork(page, ART_PNG, { run: false });
}

test.describe("digitize", () => {
  test("service unreachable: says it is not running and how to start it", async ({ page }) => {
    await mockService(page, { "POST /digitize": (r) => r.abort("connectionrefused") });
    await loadArtwork(page);
    await runDigitize(page);
    const err = page.locator(".dgp-error");
    await expect(err).toBeVisible({ timeout: 30_000 });
    await expect(err).toContainText("Couldn’t reach the digitizer service");
    await expect(err).toContainText("python -m digitizer_service");
    await expect(err).toContainText("Your artwork and settings are saved");
    await expect(err).not.toContainText(FORBIDDEN);
  });

  test("digitize fails inside the service: no traceback, a next step", async ({ page }) => {
    await mockService(page, {
      "POST /digitize": (r) => r.fulfill(json(202, { job_id: "j1", state: "queued", cached: false })),
      "GET /jobs/j1": (r) => r.fulfill(json(200, {
        state: "error",
        error: "Traceback (most recent call last):\n  File \"digitizer_core/pipeline.py\", line 88, in run\nValueError: bad shape",
      })),
    });
    await loadArtwork(page);
    await runDigitize(page);
    const err = page.locator(".dgp-error");
    await expect(err).toContainText("Digitizing didn’t work on this image", { timeout: 30_000 });
    await expect(err).toContainText("try again");
    await expect(err).not.toContainText(FORBIDDEN);
    await expect(err).not.toContainText(/pipeline\.py|ValueError/);
  });

  test("the service's own plain sentence is kept", async ({ page }) => {
    await mockService(page, {
      "POST /digitize": (r) => r.fulfill(json(400, { detail: "unknown thread brand 'nope'. See /health for the list." })),
    });
    await loadArtwork(page);
    await runDigitize(page);
    await expect(page.locator(".dgp-error")).toContainText("unknown thread brand 'nope'", { timeout: 30_000 });
  });

  test("image too large for the service", async ({ page }) => {
    await mockService(page, { "POST /digitize": (r) => r.fulfill({ status: 413, headers: CORS, body: "" }) });
    await loadArtwork(page);
    await runDigitize(page);
    const err = page.locator(".dgp-error");
    await expect(err).toContainText("too large for the digitizer", { timeout: 30_000 });
    await expect(err).toContainText("crop it tighter");
    await expect(err).not.toContainText(FORBIDDEN);
  });

  test("the service dies mid-run", async ({ page }) => {
    await mockService(page, {
      "POST /digitize": (r) => r.fulfill(json(202, { job_id: "j2", state: "queued", cached: false })),
      "GET /jobs/j2": (r) => r.abort("connectionreset"),
    });
    await loadArtwork(page);
    await runDigitize(page);
    const err = page.locator(".dgp-error");
    await expect(err).toContainText("Couldn’t reach the digitizer service", { timeout: 30_000 });
    await expect(err).not.toContainText(FORBIDDEN);
  });

  test("a job that never finishes times out with advice, not a spinner forever", async ({ page }) => {
    await page.clock.install();
    await mockService(page, {
      "POST /digitize": (r) => r.fulfill(json(202, { job_id: "j3", state: "queued", cached: false })),
      "GET /jobs/j3": (r) => r.fulfill(json(200, { state: "running" })),
    });
    await loadArtwork(page);
    await runDigitize(page);
    await expect(page.locator(".dgp-run")).toHaveText(/Digitizing/, { timeout: 30_000 });
    await page.clock.fastForward(6 * 60 * 1000);
    const err = page.locator(".dgp-error");
    await expect(err).toContainText("Digitizing took too long", { timeout: 30_000 });
    await expect(err).toContainText("simpler image");
    await expect(page.locator(".dgp-run")).toHaveText("Auto Digitize Image");
  });
});

test.describe("upload", () => {
  test("an unsupported file says what works instead", async ({ page }) => {
    await mockService(page);
    await startStudio(page);
    await page.getByTestId("art-file").setInputFiles({
      name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("this is not an image"),
    });
    const err = page.locator(".dgp-error");
    await expect(err).toBeVisible({ timeout: 30_000 });
    await expect(err).toContainText("PNG, JPEG, WebP, GIF, BMP and SVG");
    await expect(err).toContainText("PDF, AI or EPS");
    await expect(err).not.toContainText(FORBIDDEN);
  });

  test("a corrupt image is the same plain answer, not a decoder exception", async ({ page }) => {
    await mockService(page);
    await startStudio(page);
    await page.getByTestId("art-file").setInputFiles({
      name: "logo.png", mimeType: "image/png", buffer: Buffer.from("\x89PNG\r\n\x1a\nnot really"),
    });
    const err = page.locator(".dgp-error");
    await expect(err).toBeVisible({ timeout: 30_000 });
    await expect(err).toContainText(/PNG, JPEG/);
    await expect(err).not.toContainText(/decode|InvalidState|DOMException/i);
  });
});

test.describe("export", () => {
  async function reachJef(page) {
    await startStudio(page);
    await typeText(page, "FRITSCH");
    return openDownload(page);
  }

  test("JEF while the service is down names the file and the fix", async ({ page }) => {
    await mockService(page, { "POST /export": (r) => r.abort("connectionrefused") });
    await reachJef(page);
    const jef = page.getByTestId("jef-button");
    await expect(jef).toBeEnabled();
    await jef.click();
    const note = page.getByText(/Couldn’t make the JEF file/);
    await expect(note).toBeVisible();
    await expect(note).toContainText("isn’t answering");
    await expect(note).toContainText("python -m digitizer_service");
    await expect(note).not.toContainText(FORBIDDEN);
  });

  test("JEF that the service rejects keeps its reason in words", async ({ page }) => {
    await mockService(page, {
      "POST /export": (r) => r.fulfill(json(400, { detail: "That design has no stitches to write." })),
    });
    await reachJef(page);
    await page.getByTestId("jef-button").click();
    await expect(page.getByText("That design has no stitches to write.")).toBeVisible();
  });

  test("JEF that the service answers with a 500 and no detail is not shown as a status code", async ({ page }) => {
    await mockService(page, { "POST /export": (r) => r.fulfill({ status: 500, headers: CORS, body: "boom" }) });
    await reachJef(page);
    await page.getByTestId("jef-button").click();
    const note = page.getByText(/Couldn’t make the JEF file/);
    await expect(note).toBeVisible();
    await expect(note).toContainText("Try again");
    await expect(note).not.toContainText(FORBIDDEN);
  });

  test("a design bigger than the hoop says so, why it matters, and what to change", async ({ page }) => {
    await mockService(page);
    await startStudio(page);
    await pickGarment(page, "Tote");
    await typeText(page, "FRITSCH");
    await openDownload(page);
    await page.getByRole("button", { name: "DST", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: /This design is bigger than/ });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("Exceeds your 8×8 in hoop");
    await expect(dialog).toContainText("Make the design smaller, or choose a larger hoop");
    await expect(dialog).toContainText("hit the frame");
  });
});
