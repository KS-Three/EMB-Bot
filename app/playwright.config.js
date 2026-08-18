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
import { existsSync } from "node:fs";

const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium";
const launchOptions = existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {};

const PORT = 5183;
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
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
