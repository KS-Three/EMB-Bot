// @vitest-environment jsdom
//
// A garment switch AUTO-FITS a stitch file (hat: monarch 91 -> 60 mm) without
// touching element.sizeMm, which stays null. The panel read sizeMm alone, so
// it said "sews exactly as digitized" over a design scaled to 66%, and the
// file's size line kept the native 91x86 while the canvas drew 60x57
// (2026-11-14). The drawn width now comes from the field's `designDims` while
// sizeMm is null, so the same note shows at the same thresholds as a typed size.
import { beforeAll, expect, test } from "vitest";
import { render } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

let DesignPanel;

// 91 x 86 mm native, in decodeDST's space (0.1 mm ints).
function monarch() {
  const stitches = [
    { x: -455, y: -430, type: "stitch" },
    { x: 455, y: 430, type: "stitch" },
  ];
  return { stitches, widthMM: 91, heightMM: 86, stitchCount: 2, colorCount: 1, trimCount: 0, blocks: [{ count: 2 }] };
}

beforeAll(async () => {
  globalThis.window = globalThis;
  globalThis.EMB = {
    buildLetteringDesign() {},
    IMPORT_BLOCK_COLORS: [[0, 0, 0], [255, 0, 0]],
    decodeDSTStandard: () => monarch(),
    decodeDST: () => monarch(),
  };
  DesignPanel = (await import("./DesignPanel.svelte")).default;
});

const el = (o) => ({ id: "e1", type: "design", name: "monarch.dst", dstBase64: "AAAA", sizeMm: null, rotationDeg: 0, ...o });
const dims = (w, h) => ({ widthMM: w, heightMM: h });

test("auto-fit at native size (sizeMm null): no warning, 'sews exactly as digitized'", () => {
  const { container } = render(DesignPanel, { props: { element: el(), designDims: dims(91, 86) } });
  expect(container.textContent).not.toMatch(/Resized to/);
  expect(container.textContent).toMatch(/sews exactly as digitized/);
  expect(container.textContent).toMatch(/91×86 mm/);
});

test("auto-fit inside the band (80%): the resize note, not the hard warning", () => {
  const { container } = render(DesignPanel, { props: { element: el(), designDims: dims(72.8, 68.8) } });
  expect(container.textContent).toMatch(/Resized to 80%/);
  expect(container.textContent).not.toMatch(/well outside/);
  expect(container.textContent).not.toMatch(/sews exactly as digitized/);
});

test("auto-fit past 2% (90 -> 86 style, 95%): the resize note shows", () => {
  const { container } = render(DesignPanel, { props: { element: el(), designDims: dims(86.45, 81.7) } });
  expect(container.textContent).toMatch(/Resized to 95%/);
});

test("auto-fit outside the band (hat, 66%): the existing hard warning, and the size line matches the canvas", () => {
  const { container } = render(DesignPanel, { props: { element: el(), designDims: dims(60, 57) } });
  expect(container.textContent).toMatch(/Resized to 66%/);
  expect(container.textContent).toMatch(/well outside the safe 75–150% range/);
  expect(container.textContent).not.toMatch(/sews exactly as digitized/);
  expect(container.textContent).toMatch(/60×57 mm \(file: 91×86\)/);
});

test("a typed size still wins over designDims", () => {
  const { container } = render(DesignPanel, { props: { element: el({ sizeMm: 38.22 }), designDims: dims(38, 36) } });
  expect(container.textContent).toMatch(/Resized to 42%/);
});

// Kent 2026-11-14, "Stop at 75%, say so": auto-fit stops at the range edge, so
// the monarch on Hat is 68x65 and the note says the file does not fit.
test("auto-fit stopped at the 75% limit: one short line says the file does not fit the placement", () => {
  const { container } = render(DesignPanel, { props: { element: el(), designDims: dims(68.2, 64.5) } });
  expect(container.textContent).toMatch(/Resized to 75%/);
  expect(container.textContent).toMatch(/Auto-fit stopped\s+at the 75% limit/);
  expect(container.textContent).toMatch(/does\s+not fit the placement/);
  expect(container.textContent).not.toMatch(/well outside/);
  expect(container.textContent).toMatch(/68×65 mm \(file: 91×86\)/);
});

test("a TYPED 75% is just a resize: no 'auto-fit stopped' line", () => {
  const { container } = render(DesignPanel, { props: { element: el({ sizeMm: 68.25 }), designDims: dims(68.2, 64.5) } });
  expect(container.textContent).toMatch(/Resized to 75%/);
  expect(container.textContent).not.toMatch(/Auto-fit stopped/);
});
