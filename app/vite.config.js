import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { svelteTesting } from "@testing-library/svelte/vite";
import { configDefaults } from "vitest/config";

export default defineConfig({
  // svelteTesting() only does anything under `process.env.VITEST` (its own
  // internal guard) — `vite build`/`vite dev` are untouched. It does two
  // things component specs (ManualPanel.spec.js) need: resolves "svelte" to
  // its client build (mount() only exists there, not in the SSR build
  // Vite's default node condition would otherwise pick — "not available on
  // the server" without this), and registers an afterEach that unmounts +
  // clears the DOM between tests, without which multiple specs' rendered
  // output piles up in the same jsdom document.
  plugins: [svelte(), svelteTesting()],
  base: "./",
  test: {
    // e2e/ holds @playwright/test specs (run via `npx playwright test` /
    // `npm run test:e2e`, their own runner). Vitest's default include
    // pattern sweeps up any *.spec.js, and a Playwright spec imported by
    // vitest dies at collection ("Playwright Test did not expect test() to
    // be called here") — a permanently-red suite in every `npm test` run.
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
});
