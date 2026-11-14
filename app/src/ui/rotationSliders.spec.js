// The three Rotation sliders end at 359 (review follow-up, 2026-11-13). A
// turn is stored in [0, 360) (hoop.js rotationPatch), so a slider whose
// right end was 360 saved 0 there and its thumb jumped back to the left.
// Read from the source: DigitizePanel has no light mount.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

test.each(["TextStep.svelte", "DesignPanel.svelte", "DigitizePanel.svelte"])("%s: the Rotation slider's range is 0..359", (file) => {
  const src = readFileSync(join(HERE, file), "utf8");
  const m = src.match(/<span>Rotation[\s\S]*?<input([\s\S]*?)\/>/);
  expect(m, "a Rotation slider").not.toBeNull();
  expect(m[1]).toMatch(/type="range"/);
  expect(m[1]).toMatch(/min="0"/);
  expect(m[1]).toMatch(/max="359"/);
});
