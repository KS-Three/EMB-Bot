import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { configDefaults } from "vitest/config";

export default defineConfig({
  plugins: [svelte()],
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
