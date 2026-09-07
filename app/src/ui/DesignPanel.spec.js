// @vitest-environment jsdom
//
// Component-level coverage for DesignPanel.svelte's imported-.dst notices.
//
// This file used to assert the OPPOSITE of what it asserts now, and the
// correction is the point of it.
//
// EMB-Bot's DST codec disagrees with the Tajima standard, and until
// 2026-09-07 the import lane read third-party files with the EMB-Bot-
// convention reader. That was measured — 5 of 5 committed pro reference DSTs
// came in with width and height swapped — and then described as "a quarter
// turn", with the panel telling customers to "use Rotate to stand it up".
//
// A bbox swap is equally consistent with a rotation and with a mirror, and
// nobody had looked at the canvas. It was a MIRROR: an imported logo arrived
// with its letters backwards, and no rotation repairs that — the app has no
// mirror control at all. The import now goes through EMB.decodeDSTStandard,
// so a file from anywhere else lands correct and reports its real size.
//
// What is left is the same defect pointing the other way, and much smaller:
// EMB-Bot's own .dst read back in is now the one that comes in mirrored,
// because the WRITER still speaks EMB-Bot's convention (fixing that
// re-orients every DST this app has written and is Kent's call). The panel
// names that case and the lever for it.
//
// Deliberately NOT covered here: the codec itself — test/dstimport.test.js
// owns the bytes, including the signed-area test that separates a mirror from
// a turn against a pystitch-written fixture.
import { beforeAll, expect, test } from "vitest";
import { render } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

let DesignPanel;

// emb.js throws at import time unless the engine global is already present, so
// the stub is installed before the component is imported dynamically — the
// same ordering DownloadStep.spec.js and GarmentStep.spec.js document.
beforeAll(async () => {
  globalThis.window = globalThis;
  globalThis.EMB = {
    buildLetteringDesign() {},
    IMPORT_BLOCK_COLORS: [[0, 0, 0], [255, 0, 0]],
    // The LANDSCAPE truth for beckers_logo_hat: 101.9 x 62.1 mm, which is what
    // pystitch reads and therefore what the corrected reader returns. The old
    // stub returned 62.1 x 101.9 here, standing in for the swapped read; a
    // stub that still did would let this file pass against the defect.
    decodeDSTStandard: () => ({
      widthMM: 101.9,
      heightMM: 62.1,
      stitchCount: 8694,
      colorCount: 1,
      trimCount: 14,
      blocks: [{ count: 8694 }],
    }),
    // Present but NOT what the panel should call. If a future edit points the
    // panel back at it, the size assertion below fails with the swapped
    // numbers rather than passing quietly.
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

test("an imported file reports the size its own writer meant", () => {
  // 102x62, not 62x102. The swapped number was printed as fact, and it is not
  // cosmetic: the engine's fit clamp measures the wrong side, so on a hat or
  // beanie — a short placement box — a landscape logo was silently shrunk to
  // fit the height it never had.
  const { getByText } = render(DesignPanel, { props: { element: withFile } });

  expect(getByText(/102×62 mm/)).toBeInTheDocument();
});

test("the panel no longer tells anyone to rotate an import straight", () => {
  // The specific regression pin. Rotation cannot undo a mirror, so this
  // advice sent a customer away believing a backwards design was fixed —
  // worse than saying nothing. The old note's test id is checked by name so
  // reinstating it fails here rather than shipping.
  const { queryByTestId, container } = render(DesignPanel, { props: { element: withFile } });

  expect(queryByTestId("dst-import-orientation-note")).not.toBeInTheDocument();
  expect(container.textContent).not.toMatch(/stand it up/i);
});

test("the case that IS still wrong is named, with the lever that exists", () => {
  // EMB-Bot's own .dst read back in. "My designs" is the way to reopen your
  // own work and it is a real control on this screen's chrome — a warning
  // without it would be the same dead end the old note was.
  const { getByTestId } = render(DesignPanel, { props: { element: withFile } });

  const note = getByTestId("dst-own-file-note");
  expect(note).toBeInTheDocument();
  expect(note.textContent).toMatch(/mirrored/i);
  expect(note.textContent).toMatch(/My designs/);
});

test("nothing is claimed before a file is chosen", () => {
  const { queryByTestId } = render(DesignPanel, { props: { element: empty } });

  expect(queryByTestId("dst-own-file-note")).not.toBeInTheDocument();
});

test("the empty state says where your own work should be reopened from", () => {
  // Prevention, not just recognition: this is the copy someone reads while
  // deciding what file to pick.
  const { container } = render(DesignPanel, { props: { element: empty } });

  expect(container.textContent).toMatch(/My designs/);
  expect(container.textContent).toMatch(/mirrored/i);
});
