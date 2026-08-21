// @vitest-environment jsdom
//
// Component-level coverage for DesignPanel.svelte's DST import-orientation
// notice — the import-side twin of DownloadStep.spec.js's export-side one.
//
// The gap this closes: EMB-Bot's DST codec is transposed against the Tajima
// standard (MASTER_SCOPE.md, "DST codec axis bug"), and that is symmetric —
// it applies to files EMB-Bot READS just as much as to files it writes. Until
// 2026-08-21 only the export direction said so. Measured on all five pro
// reference DSTs committed under digitizer/testdata/reference/: 5 of 5 come in
// as an exact axis swap, so a 101.9x62.1 mm hat logo reports 62x102 mm and the
// panel printed that as fact. Worse on a hat or beanie, whose placement box is
// short: the engine's fit clamp then measures the wrong side and shrinks the
// design to ~37-46% of intended width, silently.
//
// Deliberately NOT covered here: the codec itself (test/dstimport.test.js owns
// the bytes), and whether the numbers are right — they are not, and fixing
// that is gated on a sew-out because re-orienting the table changes every DST
// EMB-Bot has ever written. This file only asserts the panel SAYS so.
import { beforeAll, expect, test } from "vitest";
import { render } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

// emb.js throws at import time unless the engine global is already present, so
// the stub is installed before the component is imported dynamically — the
// same ordering DownloadStep.spec.js and GarmentStep.spec.js document.
let DesignPanel;

beforeAll(async () => {
  globalThis.window = globalThis;
  globalThis.EMB = {
    buildLetteringDesign() {},
    IMPORT_BLOCK_COLORS: [[0, 0, 0], [255, 0, 0]],
    // Stands in for the transposed decode: a landscape 101.9x62.1 mm file
    // reported portrait, which is exactly what the real decoder does here.
    decodeDST: () => ({
      widthMM: 62.1,
      heightMM: 101.9,
      stitchCount: 8694,
      colorCount: 1,
      trimCount: 14,
      blocks: [{ count: 8694 }],
    }),
  };
  DesignPanel = (await import("./DesignPanel.svelte")).default;
});

const withFile = { id: "e1", type: "design", name: "beckers_logo_hat.dst", dstBase64: "AAAA" };
const empty = { id: "e1", type: "design", name: "", dstBase64: "" };

test("an imported DST warns that it may have come in a quarter turn round", () => {
  const { getByTestId } = render(DesignPanel, { props: { element: withFile } });

  const note = getByTestId("dst-import-orientation-note");
  expect(note).toBeInTheDocument();
  // The user's way out has to be named, or the warning is just bad news.
  expect(note.textContent).toMatch(/rotate/i);
});

test("the notice repeats the reported size, so the number and the caveat travel together", () => {
  // The stats line prints 62x102; a caveat elsewhere on the page that doesn't
  // name the number is easy to read as being about some other design.
  const { getByTestId } = render(DesignPanel, { props: { element: withFile } });

  expect(getByTestId("dst-import-orientation-note").textContent).toContain("62×102 mm");
});

test("the notice names the size consequence, not just the rotation", () => {
  // Rotation alone reads cosmetic. The clamp shrinking a hat design to ~37% of
  // its intended width is the part that ruins a garment, and it only bites
  // because the transposed height is what gets measured against a short box.
  const { getByTestId } = render(DesignPanel, { props: { element: withFile } });

  expect(getByTestId("dst-import-orientation-note").textContent).toMatch(/hat|beanie/i);
});

test("no orientation notice before a file is chosen", () => {
  // Nothing has been read yet, so there is nothing to be wrong about.
  const { queryByTestId } = render(DesignPanel, { props: { element: empty } });

  expect(queryByTestId("dst-import-orientation-note")).not.toBeInTheDocument();
});
