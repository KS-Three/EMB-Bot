// Launches the Playwright MCP server (@playwright/mcp), pointing it at a
// pre-installed browser when one is present instead of letting it try to
// download its own. Some sandboxed Claude Code environments pre-cache a
// Chromium build at /opt/pw-browsers/chromium but block outbound access to
// the Playwright browser CDN, so an unpinned @playwright/mcp release whose
// bundled playwright-core expects a newer browser revision than what's
// cached fails outright instead of falling back — confirmed 2026-08-03,
// see COOKBOOK.md. On a normal machine (no pre-installed path) this just
// runs `npx @playwright/mcp@latest` as usual and lets it download normally.
//
// Usage (from .mcp.json): node tools/mcp-playwright.mjs
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";

const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium";

const args = ["-y", "@playwright/mcp@latest", "--isolated", "--headless"];
if (existsSync(SANDBOX_CHROMIUM)) {
  args.push("--executable-path", SANDBOX_CHROMIUM);
}

const child = spawn("npx", args, {
  stdio: "inherit",
  shell: process.platform === "win32",
});
child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exit(code ?? 0);
});
child.on("error", (err) => {
  console.error("Failed to launch Playwright MCP server:", err.message);
  process.exit(1);
});
