// Playwright Test config for the Studio's guided-wizard E2E smoke test.
//
// Browser executable path: this sandbox class pre-caches a Chromium build at
// /opt/pw-browsers/chromium but blocks outbound access to Playwright's
// browser-download CDN, so an unpinned config that lets Playwright manage
// (and try to download) its own browser fails outright with no fallback --
// confirmed 2026-08-03, see CLAUDE.md footgun #6 and tools/mcp-playwright.mjs,
// which pins the same executable for the Playwright MCP server. Passing
// executablePath only when that path exists keeps this config portable to a
// normal machine (e.g. Kent's local setup), which still gets Playwright's
// regular auto-download/managed-browser behavior.
import { defineConfig, devices } from "@playwright/test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium";
const launchOptions = existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {};

const PORT = 5183;
const BASE_URL = `http://localhost:${PORT}`;
const E2E_DIR = join(dirname(fileURLToPath(import.meta.url)), "e2e");

// ---------------------------------------------------------------------------
// CI SHARDING (E2E_SHARD="k/n"). Unset -- every local run -- means no
// sharding: this block changes nothing.
//
// CI splits the suite across `studio-e2e shard k/2` jobs, and the job named
// `studio-e2e` (the required check) fails unless their reports show every
// collected test ran exactly once across them (tools/ci-e2e-shard-check.mjs).
// The split is by spec FILE, not Playwright's own --shard, for two reasons:
// --shard cuts by test count in file order, and one file here
// (field-reshape-mode, 614 s) WAS ~45% of the serial step's time, until it was
// split into three files on 2026-11-07; and the
// digitizer-service specs must keep one file's tests on one machine, since
// each file's afterAll kills the service it started.
//
// SPEC_SECONDS: seconds per spec file, the median over four green `main` runs
// that include the reshape split (#1318) -- runs 42406340687, 42407202584,
// 42407932826 and 42408103660, 2026-11-07 -- read by tools/e2e-spec-times.mjs
// from the shards' results*.json (serial files: wall span; parallel files: sum
// of test durations, charged a quarter). Only the PROPORTIONS matter for
// balance; a slow runner slows both shards alike. Re-measure when a shard
// runs >3 minutes longer than its sibling on a few runs in a row.
//
// Cost model, matching the two CI steps: a digitizer-service file (any file
// naming SERVICE_URL) runs serially, so it costs its full time; every other
// file shares four workers, so it costs a quarter. Files are dealt
// heaviest-first to the lightest shard (ties to the lower shard, then by
// name), so the partition is a pure function of the e2e/ directory listing
// and every shard computes the same one. A file missing from the table (a
// new spec) is charged NEW_SPEC_SECONDS -- it still runs, on exactly one
// shard; the table only steers balance, never coverage.
const SPEC_SECONDS = {
  "art-first-size.spec.js": 14,
  "configurator-smoke.spec.js": 114,
  "core-flows.spec.js": 23,
  "crop-upload.spec.js": 6,
  "design-block-thumbs.spec.js": 40,
  "design-import.spec.js": 29,
  "design-naming.spec.js": 19,
  "design-originals.spec.js": 62,
  "dialog-focus.spec.js": 31,
  "digitize-auto-start.spec.js": 30,
  "digitize-background-enclosed.spec.js": 84,
  "digitize-boundary-edit.spec.js": 29,
  "digitize-reload-mid-run.spec.js": 10,
  "digitize-restitch-trigger.spec.js": 48,
  "digitize-shape-identity.spec.js": 21,
  "digitize-stale-edits.spec.js": 15,
  "download-all.spec.js": 2,
  "download-machine.spec.js": 11,
  "download-stale-artwork.spec.js": 88,
  "dst-extents.spec.js": 6,
  "export-filename.spec.js": 8,
  "fabric-contrast.spec.js": 3,
  "field-bar-fit.spec.js": 30,
  "field-bar-narrow.spec.js": 8,
  "field-border-menu.spec.js": 19,
  "field-chrome.spec.js": 26,
  // new 2026-11-07; local sum of test durations (3 tests), not a CI median yet.
  "field-compare.spec.js": 26,
  "field-node-edit.spec.js": 64,
  "field-outlines.spec.js": 17,
  "field-panel-sync.spec.js": 18,
  // the reshape spec was split in three 2026-11-07 (#1318); weights measured.
  "field-reshape-mode.spec.js": 201,
  "field-reshape-move.spec.js": 218,
  "field-reshape-nodes.spec.js": 204,
  "field-sewn-width.spec.js": 16,
  "field-shape-popover.spec.js": 21,
  "font-browser-script-fit.spec.js": 8,
  "font-load-failure.spec.js": 8,
  "friendly-errors.spec.js": 44,
  "keyboard-a11y.spec.js": 29,
  "large-upload.spec.js": 9,
  "manual-column.spec.js": 26,
  "manual-cutout.spec.js": 63,
  "manual-double-click.spec.js": 12,
  "manual-run.spec.js": 11,
  "manual-trace-backdrop.spec.js": 3,
  "manual-trace-import.spec.js": 8,
  "oversize-fix.spec.js": 9,
  "projects-drawer.spec.js": 11,
  "quality-report.spec.js": 92,
  "reduced-motion.spec.js": 7,
  "save-load-roundtrip.spec.js": 8,
  "shortcuts-help.spec.js": 9,
  "size-cap-note.spec.js": 3,
  "storage-full.spec.js": 9,
  "text-cluster-convert.spec.js": 16,
  "text-color-ranges-edit.spec.js": 7,
  "text-two-lines.spec.js": 6,
  "theme-contrast.spec.js": 10,
  "thread-picker.spec.js": 6,
  "touch-drawing-tools.spec.js": 8,
  "typographic-punctuation.spec.js": 13,
  "undo-redo.spec.js": 38,
  "upload-full-res.spec.js": 7,
  "worksheet-digitized-lane.spec.js": 17,
  "worksheet-numbers.spec.js": 13,
  "worksheet-quote.spec.js": 4,
};
const NEW_SPEC_SECONDS = 30;
const PARALLEL_WORKERS = 4;

export function specCost(file, serial) {
  const secs = SPEC_SECONDS[file] ?? NEW_SPEC_SECONDS;
  return serial ? secs : secs / PARALLEL_WORKERS;
}

export function partitionSpecs(n, dir = E2E_DIR) {
  const files = readdirSync(dir).filter((f) => f.endsWith(".spec.js")).sort();
  const items = files.map((f) => {
    const serial = readFileSync(join(dir, f), "utf8").includes("SERVICE_URL");
    return { file: f, cost: specCost(f, serial) };
  });
  items.sort((a, b) => b.cost - a.cost || (a.file < b.file ? -1 : 1));
  const shards = Array.from({ length: n }, () => ({ files: [], cost: 0 }));
  for (const it of items) {
    let best = 0;
    for (let i = 1; i < n; i++) if (shards[i].cost < shards[best].cost) best = i;
    shards[best].files.push(it.file);
    shards[best].cost += it.cost;
  }
  for (const s of shards) s.files.sort();
  return shards;
}

function shardTestMatch(spec) {
  const m = /^(\d+)\/(\d+)$/.exec(spec);
  const k = m && Number(m[1]);
  const n = m && Number(m[2]);
  // Fail closed: a malformed value must not quietly run everything (or nothing).
  if (!m || n < 1 || k < 1 || k > n) throw new Error(`E2E_SHARD must be "k/n" with 1<=k<=n, got "${spec}"`);
  return partitionSpecs(n)[k - 1].files.map((f) => `**/e2e/${f}`);
}

const shardOptions = process.env.E2E_SHARD ? { testMatch: shardTestMatch(process.env.E2E_SHARD) } : {};

export default defineConfig({
  testDir: "./e2e",
  ...shardOptions,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], launchOptions },
    },
  ],
  // Playwright's own test runner starts/stops the dev server so this test
  // is self-contained and repeatable -- don't assume a server is already
  // running on the developer's normal port (5173), which may be busy with
  // an interactive session. reuseExistingServer mirrors Playwright's usual
  // convention: reuse a server a developer already has up locally, but
  // always start fresh in CI.
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
