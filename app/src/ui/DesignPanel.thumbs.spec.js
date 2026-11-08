// @vitest-environment jsdom
//
// The block rows with thumbnails. jsdom has no layout, so "the row is no taller"
// is asserted at its cause here -- each thumbnail sits in a FIXED-size box that
// exists before its canvas does, and the box is no taller than the compact
// thread picker that already sets the row's height -- and MEASURED for real in
// e2e/design-block-thumbs.spec.js (row heights with and without the thumbnail,
// equal on every row).
import { beforeAll, expect, test, vi } from "vitest";
import { render } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { readFileSync } from "node:fs";

let DesignPanel;

const S = (x, y) => ({ x, y, type: "stitch" });
const decoded = {
  widthMM: 10, heightMM: 5, stitchCount: 5, colorCount: 2, trimCount: 0,
  stitches: [S(0, 0), S(100, 0), S(100, 50), { x: 0, y: 0, type: "color" }, S(0, 0), S(50, 50)],
};

beforeAll(async () => {
  globalThis.window = globalThis;
  globalThis.EMB = {
    buildLetteringDesign() {},
    IMPORT_BLOCK_COLORS: [[0, 0, 0], [255, 0, 0]],
    decodeDSTStandard: () => decoded,
    decodeDST: () => decoded,
  };
  // jsdom has no 2d context; give canvases a no-op one so the thumbnails build.
  const noop = new Proxy({}, { get: () => () => {}, set: () => true });
  HTMLCanvasElement.prototype.getContext = () => noop;
  DesignPanel = (await import("./DesignPanel.svelte")).default;
});

const el = { id: "e1", type: "design", name: "x.dst", dstBase64: "AAAA" };

test("each block row shows its own stitch count, before any picture is drawn", () => {
  const { container } = render(DesignPanel, { props: { element: el } });
  const counts = [...container.querySelectorAll(".dp-block-st")].map((n) => n.textContent.trim());
  expect(counts).toEqual(["3 st", "2 st"]);
});

test("a canvas lands in every thumbnail box once the list is visible", async () => {
  const { container } = render(DesignPanel, { props: { element: el } });
  // Built one task after the rows paint (see DesignPanel's schedule()).
  await vi.waitFor(() => expect(container.querySelectorAll(".dp-thumb canvas")).toHaveLength(2));
  expect(container.querySelectorAll(".dp-thumb")).toHaveLength(2);
});

test("no picture is built while the block list is off screen", async () => {
  const seen = [];
  const Real = globalThis.IntersectionObserver;
  globalThis.IntersectionObserver = class { constructor(cb) { seen.push(cb); } observe() {} disconnect() {} };
  try {
    const { container } = render(DesignPanel, { props: { element: el } });
    await new Promise((r) => setTimeout(r, 30));
    expect(container.querySelectorAll(".dp-thumb canvas")).toHaveLength(0);
    // The box is there regardless: the row does not wait for the picture.
    expect(container.querySelectorAll(".dp-thumb")).toHaveLength(2);
    seen[0]([{ isIntersecting: true }]);
    await vi.waitFor(() => expect(container.querySelectorAll(".dp-thumb canvas")).toHaveLength(2));
  } finally {
    if (Real) globalThis.IntersectionObserver = Real; else delete globalThis.IntersectionObserver;
  }
});

test("the thumbnail box is a fixed size no taller than the compact picker", () => {
  const css = readFileSync("src/ui/theme.css", "utf8");
  const box = /\.dp-thumb\s*\{([^}]*)\}/.exec(css)[1];
  const h = parseInt(/height:\s*(\d+)px/.exec(box)[1], 10);
  const w = parseInt(/width:\s*(\d+)px/.exec(box)[1], 10);
  expect(w).toBeGreaterThan(0);
  // The compact trigger: a 22px swatch plus its padding/border -- the e2e
  // measures the real row (34 px); the box must stay inside it.
  expect(h).toBeLessThanOrEqual(28);
  expect(/flex:\s*none/.test(box)).toBe(true);
});
