// What a customer on bad wifi is told.
//
// `fetch` rejects with a bare TypeError and EmbroideryField rendered its
// `.message` verbatim, so the whole of what the app said was **"Failed to
// fetch"** — no cause, no action, and no retry control anywhere on the page.
// Measured 2026-09-07 by aborting `**/fonts/bin/**` in a real browser.
//
// Driven end to end rather than unit-tested because the failing call only
// exists in a browser: `fontLoader.readBytes` reads from disk under Node, so
// a stubbed `globalThis.fetch` in vitest is never reached. A first draft did
// exactly that and its three assertions passed against the real 85-font
// manifest loaded off the filesystem.
import { test, expect } from "@playwright/test";

test("a dead connection is explained, and names something that works", async ({ page }) => {
  await page.route("**/fonts/bin/**", (r) => r.abort());
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("FRITSCH");

  const err = page.locator("span.err");
  await expect(err).toBeVisible({ timeout: 20000 });
  // The thing that was wrong: fetch's own words, straight through.
  await expect(err).not.toContainText(/failed to fetch/i);
  // What it says instead — a cause, a lever, and a reassurance, all three
  // measured before being written down.
  await expect(err).toContainText(/connection/i);
  await expect(err).toContainText(/try again/i);
  await expect(err).toContainText(/saved/i);
});

test("and the app really does recover, with no reload", async ({ page }) => {
  // This is what makes "edit anything to try again" honest. `fontLoader`
  // clears its cached promise on failure on purpose, so the next attempt
  // re-fetches.
  let offline = true;
  await page.route("**/fonts/bin/**", (r) => (offline ? r.abort() : r.continue()));
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("FRITSCH");
  await expect(page.locator("span.err")).toBeVisible({ timeout: 20000 });

  offline = false;                       // the wifi comes back
  await page.locator("textarea").first().fill("FRITSCH ");   // one more character
  await expect(page.locator("span.stats")).toContainText(/\d[\d,]* stitches/, { timeout: 20000 });
  await expect(page.locator("span.err")).toHaveCount(0);
});

test("an HTTP status keeps its own message — not 'check your connection'", async ({ page }) => {
  // A 404 is a bad deploy or a missing file. Telling that customer to check
  // their connection sends them chasing the wrong thing, so the offline
  // wording is scoped to transport failures only.
  await page.route("**/fonts/bin/**", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("textarea").first().fill("FRITSCH");
  const err = page.locator("span.err");
  await expect(err).toBeVisible({ timeout: 20000 });
  await expect(err).toContainText(/404/);
  await expect(err).not.toContainText(/check your connection/i);
});
