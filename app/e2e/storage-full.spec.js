// What the app says when localStorage is full — which, before 2026-09-07, was
// nothing.
//
// Everything EMB-Bot holds lives in localStorage. `saveProject` has always
// returned false when the write fails and `App.persist()` ignored it, so a
// failed save was silent: the work stays on screen, looks saved, and is gone
// on the next load.
//
// Measured in the shipped app with the store filled to the byte (its real
// quota here reads 5,241,856 characters): upload a logo, watch it digitize —
// panel "2,253 stitches · 81×16 mm · 2 colors", caption 3,818 stitches — and
// the stored record is 842 characters with the element saved WITHOUT its baked
// result. Reload: back on the quick-start screen, caption 1,565 stitches. The
// logo is gone, and nothing was said at any point. One digitized project runs
// ~186,600 characters, so the store holds about 28 of them.
//
// This spec uses the .dst import rather than the digitize lane to reach the
// same failure: it needs no service, it runs in a second, and a 34 KB file
// base64s to ~46 KB, which is far past the zero headroom left below.
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BIG_DST = path.resolve(
  __dirname,
  "../../digitizer/testdata/reference/becker_hat_polo_large_beckers_logolc.dst",
);

// Fill the origin's store and leave nothing. Junk keys the app never reads, so
// nothing here depends on EMB-Bot's own storage layout.
async function fillStorage(page) {
  return page.evaluate(() => {
    let big = 0;
    try { for (; big < 2000; big++) localStorage.setItem("junk:" + big, "x".repeat(64 * 1024)); } catch (e) {}
    let small = 0;
    try { for (; small < 100000; small++) localStorage.setItem("junkk:" + small, "y".repeat(1024)); } catch (e) {}
    let headroom = "some";
    try { localStorage.setItem("junkprobe", "z".repeat(1024)); localStorage.removeItem("junkprobe"); }
    catch (e) { headroom = "none"; }
    return { big, small, headroom };
  });
}

test("a save that cannot happen is said out loud", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByPlaceholder("Type a name or word").fill("A");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();

  // Nothing to say yet — the banner must not be a permanent fixture.
  await expect(page.getByTestId("save-failed-banner")).toHaveCount(0);

  const filled = await fillStorage(page);
  expect(filled.headroom).toBe("none");

  await page.getByRole("button", { name: "Design file" }).click();
  await page.locator(".dp-upload input[type=file]").setInputFiles(BIG_DST);
  await expect(page.locator(".dp-stats")).toBeVisible({ timeout: 60_000 });

  const banner = page.getByTestId("save-failed-banner");
  await expect(banner).toBeVisible();
  // The two controls that actually exist on this screen, not "try again".
  await expect(banner).toContainText("My designs");
  await expect(banner).toContainText(/download/i);
  await expect(banner).toContainText(/delete/i);

  // And it is telling the truth: the file did not reach the store.
  const stored = await page.evaluate(() => {
    const id = localStorage.getItem("embstudio:current");
    return (localStorage.getItem("embstudio:p:" + id) || "").length;
  });
  expect(stored).toBeLessThan(20_000); // the 46 KB of base64 is not in there

  // Freeing space and touching the design again clears it — the banner
  // reports the LAST save, not a mood the app gets into.
  await page.evaluate(() => {
    for (let i = 0; i < 2000; i++) localStorage.removeItem("junk:" + i);
    for (let i = 0; i < 100000; i++) localStorage.removeItem("junkk:" + i);
  });
  await page.getByRole("button", { name: "Text", exact: true }).click();
  await page.waitForTimeout(600);
  await expect(page.getByTestId("save-failed-banner")).toHaveCount(0);
});

test("a project deleted out from under an edit is not a storage problem", async ({ page }) => {
  // `saveProject` returns false for BOTH a failed write and an id that is no
  // longer in the registry (projects.js's A2/A10 no-op contract). Only the
  // first is data loss the customer can act on; raising the storage banner on
  // the second would tell them to delete designs to fix something that is not
  // about space at all.
  //
  // The state is not reachable by clicking — deleting the current project in
  // the drawer moves you to another one — so the registry is emptied directly.
  // That is the same shape the contract describes.
  test.setTimeout(120_000);
  await page.goto("/");
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByPlaceholder("Type a name or word").fill("A");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();

  await page.evaluate(() => localStorage.setItem("embstudio:index", "[]"));
  await page.getByPlaceholder("Type a name or word").fill("AB");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await page.waitForTimeout(800);

  await expect(page.getByTestId("save-failed-banner")).toHaveCount(0);
});
