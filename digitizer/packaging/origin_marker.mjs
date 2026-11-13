// The browser half of `one_origin_smoke.py`: a real browser, a profile kept
// on disk between runs, so localStorage survives the way a customer's does.
//
//   node origin_marker.mjs <write|read> <url> <profileDir> <token> <appDir>
//
// write: open <url>, wait for the Studio to save its first project
//        (`embstudio:index`, written by app/src/lib/projects.js), add
//        `embbot-smoke:marker` = <token> beside it, close the browser.
// read:  open <url> with the same profile and report what is stored there.
//        `studio` says whether the page was the Studio (it waits for the index
//        only then: another origin is a different, empty store).
//
// Prints ONE JSON line. Uses the @playwright/test the Studio already installs
// (app/node_modules) and the browser already on the machine (Edge, else
// Chrome), so nothing is downloaded.
import { createRequire } from "node:module";
import path from "node:path";

const [mode, url, profileDir, token, appDir] = process.argv.slice(2);
if (!["write", "read"].includes(mode) || !url || !profileDir || !appDir) {
  console.error("usage: node origin_marker.mjs <write|read> <url> <profileDir> <token> <appDir>");
  process.exit(2);
}
const require = createRequire(path.join(path.resolve(appDir), "package.json"));
const { chromium } = require("@playwright/test");

const INDEX = "embstudio:index";
const CURRENT = "embstudio:current";
const MARKER = "embbot-smoke:marker";

async function open() {
  let lastError;
  for (const channel of ["msedge", "chrome", undefined]) {
    try {
      const ctx = await chromium.launchPersistentContext(profileDir, { channel, headless: true });
      return { ctx, channel: channel || "bundled chromium" };
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError;
}

const { ctx, channel } = await open();
try {
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto(url, { waitUntil: "load", timeout: 60_000 });
  const studio = (await page.locator("#app").count()) > 0;
  if (studio) {
    await page.waitForFunction(
      (k) => { try { return JSON.parse(localStorage.getItem(k) || "[]").length > 0; } catch { return false; } },
      INDEX, { timeout: 60_000 });
  }
  if (mode === "write") {
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [MARKER, token]);
  }
  const stored = await page.evaluate(([i, c, m]) => {
    let ids = [];
    try { ids = JSON.parse(localStorage.getItem(i) || "[]").map((p) => p.id); } catch {}
    return { origin: location.origin, projectIds: ids, current: localStorage.getItem(c),
             marker: localStorage.getItem(m), keys: localStorage.length };
  }, [INDEX, CURRENT, MARKER]);
  console.log(JSON.stringify({ mode, url, channel, studio, ...stored }));
} finally {
  await ctx.close(); // flushes localStorage to the profile on disk
}
