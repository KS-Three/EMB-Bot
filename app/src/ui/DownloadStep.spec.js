// @vitest-environment jsdom
//
// Component-level coverage for DownloadStep.svelte's DST encoder-provenance
// notice.
//
// The gap this closes is a product-correctness one, not a styling one:
// `exportDesignPreferService` has always tagged its result `via: "service"`
// or `via: "browser"`, but the panel only ever surfaced the service case, so
// a browser-encoded DST — the one encoder confirmed transposed against the
// Tajima standard (MASTER_SCOPE.md, "DST codec axis bug") — was the silent
// default. A lettering or hand-drawn project can never take the service
// path, so it is exactly the case that most needed telling and got told
// least.
//
// Deliberately NOT covered here: the actual encoders' bytes (test/dst.test.js
// and the crossval harness own that), and the service round trip
// (exporters.spec.js owns the `via` tagging itself). This file only asserts
// what the panel SAYS about which encoder ran.
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor, within } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

// DownloadStep pulls in the engine (emb.js throws unless the engine global
// exists) plus generate/threads/fontLoader/hoop. Only the download path is
// under test, so the heavy collaborators are mocked at module scope and the
// component is imported dynamically afterwards — the same "stub before
// importing" ordering GarmentStep.spec.js documents.
const exportCalls = [];
let nextVia = "browser";

vi.mock("../lib/generate.js", () => ({
  generateAll: () => ({
    combined: { widthMM: 50, heightMM: 50, colors: [], blocks: [] },
  }),
}));
vi.mock("../lib/exporters.js", () => ({
  exportDesignPreferService: async (design, format, opts) => {
    exportCalls.push({ format, preferService: opts.preferService });
    return {
      bytes: new Uint8Array([1, 2, 3]),
      filename: `design.${format}`,
      mime: "application/octet-stream",
      via: nextVia,
    };
  },
  exportWorksheetPDF: async () => {},
  exportPNG: async () => ({ blob: new Blob(), filename: "design.png", mime: "image/png" }),
}));
vi.mock("../lib/download.js", () => ({ triggerDownload: () => {} }));
vi.mock("../lib/fontLoader.js", () => ({ ensureFonts: async () => {} }));
vi.mock("../lib/emb.js", () => ({ EMB: { getGarment: () => ({ label: "", widthIn: 4, heightIn: 4 }) } }));
vi.mock("../lib/hoop.js", () => ({ effectiveHoop: () => ({ hoop: null }) }));
vi.mock("../lib/threads.js", () => ({
  PALETTE_INDEX: [{ id: "studio", label: "Studio" }],
  STUDIO_PALETTE: { threads: [] },
  getCachedPalette: () => ({ threads: [] }),
  loadPalette: async () => ({ threads: [] }),
  nearestInList: () => ({ rgb: [0, 0, 0], name: "Black" }),
  loadPreferredPaletteId: () => "studio",
  savePreferredPaletteId: () => {},
}));

let DownloadStep;
beforeAll(async () => {
  ({ default: DownloadStep } = await import("./DownloadStep.svelte"));
});

function project(elements) {
  return { version: 2, name: "EMBBOT", garmentId: "left_chest", elements };
}

const LETTERING = [{ id: "e1", type: "text", text: "Hi" }];
const DIGITIZED = [{ id: "e1", type: "digitized" }];
const MIXED = [{ id: "e1", type: "digitized" }, { id: "e2", type: "text", text: "Hi" }];

test("a lettering project is warned that its DST comes from the browser encoder", () => {
  const { getByTestId } = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {} },
  });
  const note = getByTestId("dst-browser-encoder-note");
  expect(note).toBeInTheDocument();
  // The two consequences that actually bite a user opening the file
  // elsewhere, per the audit: a quarter-turn rotation and unseen color stops.
  expect(note.textContent).toMatch(/rotated a quarter turn/i);
  expect(note.textContent).toMatch(/color stops/i);
});

test("a purely-digitized project gets no browser-DST warning", () => {
  const { queryByTestId } = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  expect(queryByTestId("dst-browser-encoder-note")).not.toBeInTheDocument();
});

test("a mixed project is warned — it cannot take the service path either", () => {
  // Guards the real reason `isPurelyDigitized` requires EVERY element to be
  // digitized: a combined design is encoded once, so one text element puts
  // the whole download on the browser encoder.
  const { getByTestId } = render(DownloadStep, {
    props: { project: project(MIXED), runtime: {} },
  });
  expect(getByTestId("dst-browser-encoder-note")).toBeInTheDocument();
});

test("the warning names PES and EXP as the unaffected formats", () => {
  // PR #58 fixed both browser encoders' byte framing (identity/rms 0 against
  // pyembroidery). Warning about them too would be telling the user
  // something untrue, so this pins the DST-only scope.
  const { getByTestId } = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {} },
  });
  expect(getByTestId("dst-browser-encoder-note").textContent)
    .toMatch(/PES and EXP are\s+unaffected/i);
});

// Two reasons every query below goes through this helper rather than the
// view's own bound queries. First, the warning copy itself contains "DST"
// and "PES and EXP", so a text query for a format name is ambiguous by
// construction — the button has to be found by role. Second,
// @testing-library/svelte binds its queries to document.body, not to the
// render's own container, so a test that renders twice (or renders in a
// loop) sees BOTH trees and every query goes ambiguous. Scoping to
// `view.container` keeps each render's assertions about that render.
const ui = (view) => within(view.container);
const fmtButton = (view, label) => ui(view).getByRole("button", { name: label });

test("the download message names the encoder in both directions", async () => {
  exportCalls.length = 0;
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {} },
  });
  await fireEvent.click(fmtButton(view, "DST"));
  expect(await ui(view).findByText(/browser encoder/i)).toBeInTheDocument();
  expect(exportCalls).toEqual([{ format: "dst", preferService: false }]);

  nextVia = "service";
  const digitized = render(DownloadStep, { props: { project: project(DIGITIZED), runtime: {} } });
  await fireEvent.click(fmtButton(digitized, "DST"));
  expect(await ui(digitized).findByText(/digitizer service encoder/i)).toBeInTheDocument();
});

test("a browser-encoded DST is flagged after the download, even for a digitized project", async () => {
  // The prediction and the observation can disagree: the service falling
  // over makes `exportDesignPreferService` fall back to the browser encoder
  // silently, so a purely-digitized project shows no up-front warning and
  // still gets a browser DST. The post-download note is what catches it.
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  expect(ui(view).queryByTestId("dst-browser-encoder-note")).not.toBeInTheDocument();
  await fireEvent.click(fmtButton(view, "DST"));
  expect(await ui(view).findByTestId("dst-browser-encoder-downloaded")).toBeInTheDocument();
});

test("a service-encoded DST is not flagged after the download", async () => {
  nextVia = "service";
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  await fireEvent.click(fmtButton(view, "DST"));
  await ui(view).findByText(/digitizer service encoder/i);
  expect(ui(view).queryByTestId("dst-browser-encoder-downloaded")).not.toBeInTheDocument();
});

test("PES and EXP downloads are never flagged, whichever encoder ran", async () => {
  nextVia = "browser";
  for (const fmt of ["PES", "EXP"]) {
    const view = render(DownloadStep, {
      props: { project: project(LETTERING), runtime: {} },
    });
    await fireEvent.click(fmtButton(view, fmt));
    await ui(view).findByText(/browser encoder/i);
    expect(ui(view).queryByTestId("dst-browser-encoder-downloaded")).not.toBeInTheDocument();
  }
});

test("the post-download note clears when a non-stitch format is downloaded next", async () => {
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {} },
  });
  await fireEvent.click(fmtButton(view, "DST"));
  await ui(view).findByTestId("dst-browser-encoder-downloaded");
  await fireEvent.click(fmtButton(view, "PNG"));
  await waitFor(() =>
    expect(ui(view).queryByTestId("dst-browser-encoder-downloaded")).not.toBeInTheDocument()
  );
});
