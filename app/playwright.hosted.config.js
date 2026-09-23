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
