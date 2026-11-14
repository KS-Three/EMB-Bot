// @vitest-environment jsdom
//
// The "Resized to N%" note on a TURNED stitch file (review follow-up,
// 2026-11-13). The panel measured the turned design with a turned-rectangle
// rule of its own, so a round design turned 45 degrees at its own size read
// "Resized to 71%" while the engine sewed it at 100%. It now uses
// staleness.js rotatedWidth, the engine's measure of the turned stitches.
import { beforeAll, expect, test } from "vitest";
import { render } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

let DesignPanel;

// A round design, 100 x 100 mm, in decodeDST's space (0.1 mm ints).
function ring() {
  const stitches = [];
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * Math.PI * 2;
    stitches.push({ x: Math.round(500 * Math.cos(a)), y: Math.round(500 * Math.sin(a)), type: "stitch" });
  }
  return { stitches, widthMM: 100, heightMM: 100, stitchCount: stitches.length, colorCount: 1, trimCount: 0, blocks: [{ count: stitches.length }] };
}

beforeAll(async () => {
  globalThis.window = globalThis;
  globalThis.EMB = {
    buildLetteringDesign() {},
    IMPORT_BLOCK_COLORS: [[0, 0, 0], [255, 0, 0]],
    decodeDSTStandard: () => ring(),
    decodeDST: () => ring(),
  };
  DesignPanel = (await import("./DesignPanel.svelte")).default;
});

const el = (o) => ({ id: "e1", type: "design", name: "round.dst", dstBase64: "AAAA", sizeMm: 100, rotationDeg: 45, ...o });

test("a round design turned 45 degrees at its own size is not 'resized'", () => {
  const { container } = render(DesignPanel, { props: { element: el() } });
  expect(container.textContent).not.toMatch(/Resized to/);
});

test("the same design at 70 mm, turned, says 70% and the 75-150% warning", () => {
  const { container } = render(DesignPanel, { props: { element: el({ sizeMm: 70 }) } });
  expect(container.textContent).toMatch(/Resized to 70%/);
  expect(container.textContent).toMatch(/well outside the safe 75–150% range/);
});

test("at 80 mm it is resized but inside the band", () => {
  const { container } = render(DesignPanel, { props: { element: el({ sizeMm: 80 }) } });
  expect(container.textContent).toMatch(/Resized to 80%/);
  expect(container.textContent).not.toMatch(/well outside/);
});
