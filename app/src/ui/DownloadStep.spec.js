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
import { beforeAll, beforeEach, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor, within } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

// DownloadStep pulls in the engine (emb.js throws unless the engine global
// exists) plus generate/threads/fontLoader/hoop. Only the download path is
// under test, so the heavy collaborators are mocked at module scope and the
// component is imported dynamically afterwards — the same "stub before
// importing" ordering GarmentStep.spec.js documents.
const exportCalls = [];
let nextVia = "browser";

// Mutable for the same reason `fitNote` below is: the JEF hoop-header note is
// derived from the combined design's SIZE, so a fixed 50x50 mock would leave
// every assertion about it passing against a band it never enters.
let designSize = { widthMM: 50, heightMM: 50 };
vi.mock("../lib/generate.js", () => ({
  generateAll: () => ({
    combined: { ...designSize, colors: [], blocks: [] },
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
  // Kept faithful to the real module rather than stubbed to a constant: the
  // JEF button's disabled state is derived from this, so a mock that always
  // said false would test a gate that never closes.
  isServiceOnlyFormat: (fmt) => fmt === "jef",
}));
vi.mock("../lib/download.js", () => ({ triggerDownload: () => {} }));
vi.mock("../lib/fontLoader.js", () => ({ ensureFonts: async () => {} }));
vi.mock("../lib/emb.js", () => ({ EMB: { getGarment: () => ({ label: "", widthIn: 4, heightIn: 4 }) } }));
// Mutable so the hoop-exceeds gate can be exercised: `hoopFitNote` returning a
// string is the ONLY thing that opens the confirm. It must be listed here even
// for the tests that never use it — the component calls it inside a try/catch
// that returns "" on throw, so a mock missing the export would leave every gate
// test passing against a gate that never ran.
let fitNote = "";
vi.mock("../lib/hoop.js", () => ({
  effectiveHoop: () => ({ hoop: { label: "4×4 in", widthMm: 100, heightMm: 100 } }),
  hoopFitNote: () => fitNote,
}));
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

beforeEach(() => { fitNote = ""; designSize = { widthMM: 50, heightMM: 50 }; });

function project(elements) {
  return { version: 2, name: "EMBBOT", garmentId: "left_chest", elements };
}

const LETTERING = [{ id: "e1", type: "text", text: "Hi" }];
// `result` present, because a digitized element that has never RUN has no
// stitches for the service to re-encode -- `isPurelyDigitized` counts only
// elements that actually sew. Without it these fixtures described a project
// no customer can produce, and the gate they exercise would read false for a
// reason unrelated to the one under test.
const DIGITIZED = [{ id: "e1", type: "digitized", result: { design: {} } }];
const MIXED = [{ id: "e1", type: "digitized", result: { design: {} } },
               { id: "e2", type: "text", text: "Hi" }];
// The shape of EVERY real logo-only project: defaultProject seeds an empty
// text element and a customer who uploads a logo never removes it. See the
// test at the end of this file for what that placeholder used to cost.
const DIGITIZED_PLUS_PLACEHOLDER = [
  { id: "e1", type: "text", text: "" },
  { id: "e2", type: "digitized", result: { design: {} } },
];

test("a lettering project is warned that its DST comes from the browser encoder", () => {
  const { getByTestId } = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {} },
  });
  const note = getByTestId("dst-browser-encoder-note");
  expect(note).toBeInTheDocument();
  // The consequence that actually bites a user opening the file elsewhere:
  // the orientation.
  //
  // "MIRROR" is load-bearing and this assertion used to read
  // /rotated a quarter turn/. Rendered 2026-09-07: a standard reader sees a
  // browser-encoded DST a quarter turn round AND mirror-imaged — letters
  // backwards. A customer told only "rotated" tries to rotate it back in
  // their own software and cannot, because rotation preserves orientation and
  // this does not. Naming the mirror is the difference between a warning they
  // can act on and one that sends them somewhere that will not work.
  expect(note.textContent).toMatch(/quarter turn/i);
  expect(note.textContent).toMatch(/flipped/i);
  expect(note.textContent).toMatch(/backwards/i);
  expect(note.textContent).toMatch(/will\s+not fix/i); // the note wraps mid-phrase
  // And NOT the colour stops, which used to be the note's second consequence.
  // The browser encoder wrote the colour change as 0x43 instead of 0xC3, so a
  // standard reader saw a sequin toggle and no stop at all; fixed 2026-09-08
  // (src/dst.js, pinned by test/crossval-stitch-formats.test.js against
  // pystitch). Asserted as an ABSENCE so the stale clause cannot come back:
  // telling a customer to distrust something that now works costs them the
  // format they most likely need.
  expect(note.textContent).not.toMatch(/color stops/i);
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

// The warning was doing its job while the layout undid it: DST was the
// filled `primary` button, first in the grid, sitting directly above the
// paragraph explaining that this exact file reads a quarter-turn rotated
// everywhere else. The most prominent choice was the broken one, and a user
// who trusts the emphasis rather than reading the note gets a ruined
// sew-out. Emphasis now follows the encoder.
test("when the browser encoder writes the DST, PES leads and DST carries the caveat", () => {
  const view = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {} },
  });
  const { container } = view;
  const formats = [...container.querySelectorAll(".formats button")];
  const primary = formats.filter((b) => b.classList.contains("primary"));

  expect(primary).toHaveLength(1);
  expect(primary[0].textContent.trim()).toBe("PES");
  // First in the grid as well as filled — reading order is emphasis too.
  expect(formats[0].textContent.trim()).toBe("PES");

  const dst = formats.find((b) => b.textContent.trim().startsWith("DST"));
  expect(dst.classList.contains("primary")).toBe(false);
  expect(dst.classList.contains("caveat")).toBe(true);
  // The button is still NAMED "DST" — the caveat is a description, not part
  // of the name — so it stays addressable by voice and by every existing
  // query. The asterisk is aria-hidden because "star" announces nothing.
  expect(dst).toHaveAccessibleName("DST");
  expect(dst.getAttribute("aria-describedby")).toBe("dst-encoder-note");
  expect(container.querySelector("#dst-encoder-note")).toBe(
    view.getByTestId("dst-browser-encoder-note"),
  );
});

test("a project that exports through the service keeps DST primary", () => {
  // The point is not that DST is bad — it is the industry default and the
  // service's DST is spec-correct. Demoting it unconditionally would push
  // users off the right format for their machine.
  const { container } = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  const formats = [...container.querySelectorAll(".formats button")];
  expect(formats[0].textContent.trim()).toBe("DST");
  expect(formats[0].classList.contains("primary")).toBe(true);
  expect(container.querySelector(".formats button.caveat")).toBeNull();
});

test("every format is still reachable in both encoder states", () => {
  // The conditional branch duplicates the DST/PES/EXP buttons, which is
  // exactly the shape of edit that drops one of them.
  for (const els of [LETTERING, DIGITIZED]) {
    const { container, unmount } = render(DownloadStep, {
      props: { project: project(els), runtime: {} },
    });
    const labels = [...container.querySelectorAll(".formats button")]
      .map((b) => b.textContent.trim().replace(/\*.*$/s, "").trim());
    for (const want of ["DST", "PES", "EXP", "JEF", "SVG", "PNG", "PDF worksheet"]) {
      expect(labels).toContain(want);
    }
    unmount();
  }
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

test("the post-download DST note stands alone — it never points at absent text", async () => {
  // The bug this replaces: the note said "see the note above", and the note
  // above (`dst-browser-encoder-note`) renders only when the browser encoder
  // was PREDICTED. On a purely-digitized project it is not, so in the one
  // case the post-download note exists for, it referred the customer to a
  // paragraph that is not on the page. The test directly above proves the
  // up-front note is absent here; this proves what the message then has to
  // carry on its own.
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  expect(ui(view).queryByTestId("dst-browser-encoder-note")).not.toBeInTheDocument();
  await fireEvent.click(fmtButton(view, "DST"));
  const note = await ui(view).findByTestId("dst-browser-encoder-downloaded");

  // No dangling cross-reference, whatever wording a future edit picks.
  expect(note.textContent).not.toMatch(/note above|above before|see above/i);
  // The consequence, in the customer's terms rather than the encoder's name.
  expect(note.textContent).toMatch(/quarter turn/i);
  // Not the colour stops — those survive as of 2026-09-08. See the absence
  // assertion in the up-front-note test above for why this is pinned.
  expect(note.textContent).not.toMatch(/color stops/i);
  // And the cause, which is the actionable half: the service was asked for
  // this file and could not answer.
  expect(note.textContent).toMatch(/digitizer service/i);
  expect(note.textContent).toMatch(/PES or EXP/i);
});

test("a lettering project's post-download note is self-contained too, and does not blame the service", async () => {
  // Here the up-front note IS rendered, so the two paragraphs sit together
  // and the second must not read as a fragment of the first — nor claim a
  // service failure, since a lettering project never asks the service at all
  // (preferService is false, so `via: "browser"` is the intended path).
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {} },
  });
  expect(ui(view).getByTestId("dst-browser-encoder-note")).toBeInTheDocument();
  await fireEvent.click(fmtButton(view, "DST"));
  const note = await ui(view).findByTestId("dst-browser-encoder-downloaded");
  expect(note.textContent).not.toMatch(/note above|above before|see above/i);
  expect(note.textContent).toMatch(/quarter turn/i);
  expect(note.textContent).not.toMatch(/digitizer service/i);
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

// --- the hoop-exceeds export gate ------------------------------------------
//
// A design bigger than the hoop used to be one clause of grey caption text
// while Download stayed enabled. These pin that it now costs a deliberate yes,
// and — the half that matters more — that it costs NOTHING when it fits.

const P = { props: { project: project(DIGITIZED), runtime: {} } };

test("a design that fits downloads in one click, with no dialog", async () => {
  const view = render(DownloadStep, P);
  await fireEvent.click(fmtButton(view, "DST"));
  expect(view.queryByRole("dialog")).toBeNull();
  expect(exportCalls.map((c) => c.format)).toContain("dst");
});

test("a design bigger than the hoop must be confirmed before it exports", async () => {
  fitNote = "Exceeds your 4×4 in hoop";
  const view = render(DownloadStep, P);
  const before = exportCalls.length;
  await fireEvent.click(fmtButton(view, "DST"));

  // Nothing has been written yet — that is the whole point.
  expect(exportCalls.length).toBe(before);
  const dialog = view.getByRole("dialog");
  // It repeats the measured reason rather than inventing its own wording.
  expect(dialog.textContent).toMatch(/Exceeds your 4×4 in hoop/);

  await fireEvent.click(view.getByText(/Download DST anyway/));
  expect(exportCalls.map((c) => c.format)).toContain("dst");
});

test("Go back cancels the export entirely", async () => {
  fitNote = "Exceeds your 4×4 in hoop";
  const view = render(DownloadStep, P);
  const before = exportCalls.length;
  await fireEvent.click(fmtButton(view, "DST"));
  await fireEvent.click(view.getByText("Go back"));
  expect(view.queryByRole("dialog")).toBeNull();
  expect(exportCalls.length).toBe(before);
});

test("the confirm names the format it holds, so one dialog serves them all", async () => {
  fitNote = "Exceeds your 4×4 in hoop";
  const view = render(DownloadStep, P);
  await fireEvent.click(fmtButton(view, "PES"));
  expect(view.getByRole("dialog").textContent).toMatch(/Download PES anyway/);
});

test("PNG is NOT gated — it is not a file a machine stitches", async () => {
  fitNote = "Exceeds your 4×4 in hoop";
  const view = render(DownloadStep, P);
  await fireEvent.click(fmtButton(view, "PNG"));
  expect(view.queryByRole("dialog")).toBeNull();
});

// --- the placeholder that made the service export path unreachable ---------
//
// Measured 2026-09-07 by downloading from the shipped UI and decoding with
// pystitch, the third-party reader CI cross-validates against. The app
// claimed 81x16 mm; the DST a customer actually gets read back as
//
//     16.3 x 80.5 mm, 0 threads
//
// — the quarter turn and the unrecognised colour-change record of CLAUDE.md
// footgun 1. PES from the same design read 80.5 x 16.3 with 2 threads, so
// the design was fine and the encoder was not.
//
// The app HAS a mitigation for exactly this: prefer the service's
// pyembroidery-convention encoder for a purely-digitized project. It never
// fired, because `defaultProject()` seeds an empty text element that a
// customer who uploads a logo never removes, and `every(el => el.type ===
// "digitized")` counted that placeholder as mixed content.
//
// Worse than silent: the caveat the customer DID see says "this project
// includes lettering or hand-drawn shapes", which was not true of a logo-only
// design — a false reason for steering them off a format that was available
// and correct.

test("a logo-only project exports through the service despite its empty text placeholder", async () => {
  exportCalls.length = 0;
  nextVia = "service";
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED_PLUS_PLACEHOLDER), runtime: {} },
  });
  // No caveat, and DST leads again — it is the industry default and, on this
  // path, spec-correct.
  expect(ui(view).queryByTestId("dst-browser-encoder-note")).not.toBeInTheDocument();
  await fireEvent.click(fmtButton(view, "DST"));
  expect(exportCalls).toEqual([{ format: "dst", preferService: true }]);
  await ui(view).findByText(/digitizer service encoder/i);
});

test("a project that genuinely mixes SEWABLE content still stays on the browser encoder", async () => {
  // The scoping ruling is unchanged: there is no way to export part of a
  // combined design through two encoders, so a real text element beside the
  // logo keeps the whole thing on the browser path — and the caveat, whose
  // stated reason ("includes lettering") is then true.
  exportCalls.length = 0;
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project(MIXED), runtime: {} },
  });
  expect(ui(view).getByTestId("dst-browser-encoder-note")).toBeInTheDocument();
  await fireEvent.click(fmtButton(view, "DST"));
  expect(exportCalls).toEqual([{ format: "dst", preferService: false }]);
});

test("a digitized element that has never run is not exportable through the service", async () => {
  // There are no stitches to re-encode, so the browser path is correct here
  // and the gate must not be fooled by the element's TYPE alone.
  exportCalls.length = 0;
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project([{ id: "e1", type: "digitized", result: null }]), runtime: {} },
  });
  await fireEvent.click(fmtButton(view, "DST"));
  expect(exportCalls).toEqual([{ format: "dst", preferService: false }]);
});

// ---- JEF (Janome) ---------------------------------------------------------
//
// The only format here the browser cannot write, so it is the only button
// whose availability depends on something outside the app. PRODUCT.md's launch
// checklist has counted JEF as shipped since 2026-08-11 on the evidence that
// `digitizer_service/formats.py` can write it — which was true, and which no
// customer could reach, because nothing rendered a button.

test("JEF is offered, and is disabled with a reason when the service is not running", () => {
  const { getByTestId, unmount } = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {}, digitizerHealth: null },
  });
  const off = getByTestId("jef-button");
  expect(off).toBeDisabled();
  // The reason has to name the fix, not just the state.
  expect(off.getAttribute("title")).toMatch(/digitizer service running/i);
  unmount();

  const { getByTestId: get2 } = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {}, digitizerHealth: { status: "ok" } },
  });
  expect(get2("jef-button")).toBeEnabled();
});

test("JEF downloads through the service on a LETTERING project too — the preferService split does not apply to it", async () => {
  // `preferService` chooses between two encoders for dst/exp/pes and is false
  // here (lettering). JEF has no second encoder, so exporters.js routes it to
  // the service regardless; this asserts the panel actually asks for it rather
  // than quietly skipping the button's format.
  exportCalls.length = 0;
  nextVia = "service";
  const { getByTestId, getByText } = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {}, digitizerHealth: { status: "ok" } },
  });
  await fireEvent.click(getByTestId("jef-button"));
  await waitFor(() => expect(getByText(/Downloaded JEF/)).toBeInTheDocument());
  expect(exportCalls).toEqual([{ format: "jef", preferService: false }]);
});

test("an oversize design still has to be confirmed before a JEF leaves — the gate is per format, not per encoder", async () => {
  fitNote = "Exceeds your 4×4 in hoop";
  exportCalls.length = 0;
  const { getByTestId, getByRole } = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {}, digitizerHealth: { status: "ok" } },
  });
  await fireEvent.click(getByTestId("jef-button"));
  expect(exportCalls).toEqual([]);
  const dialog = getByRole("dialog");
  await fireEvent.click(within(dialog).getByRole("button", { name: "Download JEF anyway" }));
  await waitFor(() => expect(exportCalls).toEqual([{ format: "jef", preferService: false }]));
});

// ---- The JEF header declares a hoop the design does not fit -------------
//
// pystitch's `get_jef_hoop_size` ladder falls through to HOOP_110X110 — the
// second smallest of its five codes — for any design at or over 200 mm in
// either axis, and a Janome reads that code before it reads a stitch.
// Measured through the real /export route on 2026-09-07 and pinned in
// digitizer/tests/test_jef_hoop_code.py; these tests own only what the panel
// SAYS about it, the same split the DST notice above uses.

test("a design over 200 mm carries the JEF hoop-header caveat", () => {
  designSize = { widthMM: 240.0, heightMM: 60.0 };
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  const note = view.getByTestId("jef-hoop-header-note");
  expect(note).toBeInTheDocument();
  // The three things a customer needs: what the file says, what it means, and
  // what they can do instead.
  expect(note.textContent).toMatch(/110 × 110 mm/);
  expect(note.textContent).toMatch(/240\.0 × 60\.0 mm/);
  expect(note.textContent).toMatch(/Under 200 mm the header is correct/);
});

test("the caveat rides the JEF button by description, not by name", () => {
  designSize = { widthMM: 240.0, heightMM: 60.0 };
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  const jef = view.getByTestId("jef-button");
  expect(jef).toHaveAccessibleName("JEF");
  expect(jef.classList.contains("caveat")).toBe(true);
  expect(jef.getAttribute("aria-describedby")).toBe("jef-hoop-note");
  expect(view.container.querySelector("#jef-hoop-note")).toBe(
    view.getByTestId("jef-hoop-header-note"),
  );
});

test("a design that fits every hoop is left alone", () => {
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  expect(view.queryByTestId("jef-hoop-header-note")).not.toBeInTheDocument();
  const jef = view.getByTestId("jef-button");
  expect(jef.classList.contains("caveat")).toBe(false);
  expect(jef.getAttribute("aria-describedby")).toBeNull();
});

test("the boundary is the writer's own, in the writer's own units", () => {
  // get_jef_hoop_size compares ROUNDED 0.1 mm units against 2000, so 199.9 mm
  // is the last size that declares a hoop it fits and 200.0 mm is the first
  // that does not. A threshold expressed in whole mm would put the note on
  // the wrong side of exactly this pair.
  designSize = { widthMM: 199.9, heightMM: 60 };
  const under = render(DownloadStep, { props: { project: project(DIGITIZED), runtime: {} } });
  expect(under.queryByTestId("jef-hoop-header-note")).not.toBeInTheDocument();
  under.unmount();

  designSize = { widthMM: 200.0, heightMM: 60 };
  const over = render(DownloadStep, { props: { project: project(DIGITIZED), runtime: {} } });
  expect(over.getByTestId("jef-hoop-header-note")).toBeInTheDocument();
});

test("height alone triggers it — the ladder tests both axes", () => {
  // 150 x 240 mm is not a hypothetical: it FITS the 6x10 hoop, so the
  // hoop-exceeds confirm never opens for it, and it is still stamped 110x110.
  designSize = { widthMM: 150, heightMM: 240 };
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  expect(view.getByTestId("jef-hoop-header-note")).toBeInTheDocument();
});

test("the note does not depend on the hoop-exceeds gate", () => {
  // The whole reason this is a persistent note and not a line in the confirm
  // dialog. `fitNote` stays "" here — the design fits the customer's hoop —
  // and the caveat must still appear, because the FILE is wrong either way.
  designSize = { widthMM: 200, heightMM: 150 };
  fitNote = "";
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  expect(view.getByTestId("jef-hoop-header-note")).toBeInTheDocument();
});

test("only the formats verified to carry no hoop header are named", () => {
  // Scope pin. Grepping pystitch's writers, exactly two mention a hoop:
  // JefWriter and PesWriter. So DST and EXP are safe to name and PES is not —
  // its hoop bytes are a constant that never described the design, and what a
  // Brother machine does with them is not measurable in this repo.
  designSize = { widthMM: 240, heightMM: 60 };
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {} },
  });
  const note = view.getByTestId("jef-hoop-header-note");
  expect(note.textContent).toMatch(/DST and\s+EXP carry no hoop header at all/);
  expect(note.textContent).not.toMatch(/PES/);
});
