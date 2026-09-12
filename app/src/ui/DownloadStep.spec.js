// @vitest-environment jsdom
//
// Component-level coverage for DownloadStep.svelte: which formats it offers,
// what it says about them, and the gates in front of a download.
//
// This file was written for a DST encoder-provenance NOTICE. A browser-encoded
// DST was the one file confirmed transposed against the Tajima standard, and
// `exportDesignPreferService` tagged every result `via: "service"` or
// `via: "browser"` while the panel surfaced only the service case — so the
// broken encoder was the silent default, on exactly the projects (lettering,
// hand-drawn) that can never take the service path.
//
// **That codec was fixed on 2026-09-08** — both record weight tables swapped,
// byte-identical to `pystitch.DstWriter.encode_record`, crossval reading
// `identity`, a rendered "FRITSCH" coming back upright — and the notice came
// out with it. What is left here of that work is a set of ABSENCE assertions:
// no caveat, no asterisk, no demotion, on any project type. They are the
// tripwire against re-adding a warning for a defect that no longer exists.
//
// Deliberately NOT covered here: the actual encoders' bytes (test/dst.test.js
// and the crossval harness own that), and the service round trip
// (exporters.spec.js owns the `via` tagging itself).
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
  // service-only buttons' disabled state is derived from this, so a mock that
  // always said false would test a gate that never closes. Three formats
  // since Kent's 2026-09-12 scope call, not one.
  isServiceOnlyFormat: (fmt) => ["jef", "xxx", "vp3"].includes(fmt),
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

// ---- the DST caveats are GONE, and stay gone -------------------------------
//
// From 2026-08 to 2026-09-08 a browser-encoded DST carried two warning
// paragraphs, an asterisk, and a demotion behind PES, because the browser's
// own codec wrote a private dialect: a standard reader saw the design a
// quarter turn round AND mirrored, letters backwards. Every word of that was
// true and every word of it is now false — the codec was put right (both
// record weight tables swapped, byte-identical to pystitch, crossval
// `identity`, a rendered "FRITSCH" upright at the design's own size), and the
// colour-change byte went `0x43` -> `0xC3` the day before.
//
// Asserted as ABSENCES rather than deleted, because a warning left standing
// after its defect is fixed is not the safe side of the trade: it steers
// people off the format most of their machines want, and it teaches them to
// distrust the ones we keep. If a real difference reappears, MEASURE it and
// write a note about THAT — do not restore these.

test("no DST caveat renders, on any project type", () => {
  for (const [name, els] of [["lettering", LETTERING], ["mixed", MIXED], ["digitized", DIGITIZED]]) {
    const view = render(DownloadStep, { props: { project: project(els), runtime: {} } });
    expect(
      ui(view).queryByTestId("dst-browser-encoder-note"),
      `${name} project must render no DST caveat`,
    ).not.toBeInTheDocument();
    // The words themselves, not just the testid — a note that came back under
    // a different id would still be the same false claim on the page.
    expect(view.container.textContent).not.toMatch(/quarter turn/i);
    expect(view.container.textContent).not.toMatch(/backwards/i);
    view.unmount();
  }
});

test("DST leads and is primary on every project type, with no asterisk", () => {
  // DST was demoted behind PES, and given a `caveat` class and an asterisk,
  // whenever the browser encoder would write it — because then the most
  // prominent choice was the one we knew read wrong elsewhere. With the codec
  // correct that reasoning is gone, and leaving the demotion would push people
  // off the industry default for no reason.
  //
  // The JEF button keeps its own asterisk when the hoop-header note applies;
  // that is a different caveat about a real, still-live pystitch behaviour, so
  // this looks only at the DST/PES/EXP group.
  for (const [name, els] of [["lettering", LETTERING], ["mixed", MIXED], ["digitized", DIGITIZED]]) {
    const view = render(DownloadStep, { props: { project: project(els), runtime: {} } });
    const formats = [...view.container.querySelectorAll(".formats button")];
    expect(formats[0].textContent.trim(), `${name}: DST leads`).toBe("DST");
    expect(formats[0].classList.contains("primary"), `${name}: DST is filled`).toBe(true);
    const dst = formats.find((b) => b.textContent.trim().startsWith("DST"));
    expect(dst.classList.contains("caveat"), `${name}: no caveat class`).toBe(false);
    expect(dst).toHaveAccessibleName("DST");
    expect(dst.getAttribute("aria-describedby"), `${name}: nothing to describe`).toBeNull();
    view.unmount();
  }
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
    for (const want of ["DST", "PES", "EXP", "JEF", "XXX", "VP3", "SVG", "PNG", "PDF worksheet"]) {
      expect(labels).toContain(want);
    }
    unmount();
  }
});

// (Removed 2026-09-08: "the warning names PES and EXP as the unaffected
// formats". It pinned the DST-only scope of a warning that no longer exists —
// PR #58 had fixed both browser encoders' byte framing, and the DST codec
// caught up. There is no format here to warn about, so there is no scope to
// pin; the absence test above covers what is left to say.)

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

test("no post-download DST note appears, whichever encoder actually ran", async () => {
  // Three tests lived here: one proving a browser-encoded DST got flagged
  // even on a digitized project (the service can fall back silently), one
  // proving that note stood alone rather than pointing at absent text, and
  // one proving it did not blame the service on a lettering project. All
  // three guarded the WORDING of a warning that no longer has anything to
  // warn about.
  //
  // What replaces them is the property that matters now: whichever encoder
  // ran, the customer is told which one and nothing more. The `via` label is
  // neutral provenance; it is not a caveat, and it must not grow back into
  // one.
  for (const [via, els] of [["browser", DIGITIZED], ["browser", LETTERING], ["service", DIGITIZED]]) {
    nextVia = via;
    const view = render(DownloadStep, { props: { project: project(els), runtime: {} } });
    await fireEvent.click(fmtButton(view, "DST"));
    await ui(view).findByText(/encoder/i);
    expect(ui(view).queryByTestId("dst-browser-encoder-downloaded")).not.toBeInTheDocument();
    expect(view.container.textContent).not.toMatch(/quarter turn|backwards/i);
    view.unmount();
  }
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

// (Removed 2026-09-08: "the post-download note clears when a non-stitch format
// is downloaded next". It guarded a note that no longer renders at all.)

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
  // logo keeps the whole thing on the browser path.
  //
  // This used to assert the caveat as well. The ROUTING is the part worth
  // pinning and it is unaffected by the caveat going away — which encoder
  // runs still matters to the code even though it no longer matters to the
  // customer.
  exportCalls.length = 0;
  nextVia = "browser";
  const view = render(DownloadStep, {
    props: { project: project(MIXED), runtime: {} },
  });
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

// (Removed 2026-09-08, hours after being added: two tests pinned that the DST
// caveat NAMED JEF as an alternative when the service was up, and did not when
// it was down. Both were right about the caveat that existed that morning. The
// codec fix removed the caveat, so there is nothing left to name JEF in --
// which is the better outcome for the Janome owner those tests were written
// for: the format they need no longer needs recommending, because the one they
// were being steered away from now works too.)

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

// ---- XXX (Singer) and VP3 (Husqvarna Viking / Pfaff) ----------------------
//
// Kent's scope call 2026-09-12, closing MASTER_SCOPE open item 14 for these
// two: both round-trip `identity` through pystitch
// (`digitizer/tools/format_roundtrip.py`) and both return the design's own
// thread RGB, which PES, PEC and JEF do not. PEC and U01 were left exactly
// where they were.
//
// They inherit JEF's contract, so they inherit its tests: service-only, hence
// disabled with a reason when the service is down, and gated by the
// hoop-exceeds confirm like every other machine format.

test("XXX and VP3 are offered, and are disabled with a reason naming their brands", () => {
  const down = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {}, digitizerHealth: null },
  });
  for (const [id, brand] of [["xxx-button", /Singer/], ["vp3-button", /Husqvarna Viking \/ Pfaff/]]) {
    const btn = ui(down).getByTestId(id);
    expect(btn).toBeDisabled();
    // The reason names the fix, and the title names the machines — "XXX" on
    // the face of the button is not something a Singer owner recognises.
    expect(btn.getAttribute("title")).toMatch(/digitizer service running/i);
    expect(btn.getAttribute("title")).toMatch(brand);
  }
  down.unmount();

  const up = render(DownloadStep, {
    props: { project: project(LETTERING), runtime: {}, digitizerHealth: { status: "ok" } },
  });
  for (const [id, brand] of [["xxx-button", /Singer/], ["vp3-button", /Husqvarna Viking \/ Pfaff/]]) {
    const btn = ui(up).getByTestId(id);
    expect(btn).toBeEnabled();
    expect(btn.getAttribute("title")).toMatch(brand);
  }
});

test("XXX and VP3 download through the service on a lettering project too", async () => {
  // Same point the JEF test above makes: `preferService` is false here, and
  // these formats have no second encoder to prefer, so the panel must still
  // ask for them rather than quietly skipping the button's format.
  for (const fmt of ["xxx", "vp3"]) {
    exportCalls.length = 0;
    nextVia = "service";
    const view = render(DownloadStep, {
      props: { project: project(LETTERING), runtime: {}, digitizerHealth: { status: "ok" } },
    });
    await fireEvent.click(ui(view).getByTestId(`${fmt}-button`));
    await waitFor(() =>
      expect(ui(view).getByText(new RegExp(`Downloaded ${fmt.toUpperCase()}`))).toBeInTheDocument());
    expect(exportCalls).toEqual([{ format: fmt, preferService: false }]);
    view.unmount();
  }
});

test("an oversize design still has to be confirmed before an XXX or a VP3 leaves", async () => {
  fitNote = "Exceeds your 4×4 in hoop";
  for (const fmt of ["xxx", "vp3"]) {
    exportCalls.length = 0;
    const view = render(DownloadStep, {
      props: { project: project(LETTERING), runtime: {}, digitizerHealth: { status: "ok" } },
    });
    await fireEvent.click(ui(view).getByTestId(`${fmt}-button`));
    expect(exportCalls).toEqual([]);
    const dialog = ui(view).getByRole("dialog");
    await fireEvent.click(
      within(dialog).getByRole("button", { name: `Download ${fmt.toUpperCase()} anyway` }));
    await waitFor(() => expect(exportCalls).toEqual([{ format: fmt, preferService: false }]));
    view.unmount();
  }
});

test("VP3's 0.1 mm is not put in front of the customer", () => {
  // The measured difference: from the THIRD colour block on, VP3 reads back 1
  // unit — 0.1 mm — narrower, pinned there and not accumulating. Kent's call
  // 2026-09-12 is that it belongs in the PR body and in exporters.js, not in
  // the UI. This is the tripwire against a future session helpfully adding an
  // asterisk to a tenth of a millimetre.
  //
  // Rendered at 240 mm on purpose: that is the size that DOES earn JEF its
  // asterisk, so a caveat appearing on VP3 here could not be waved off as the
  // note simply not being reachable.
  designSize = { widthMM: 240, heightMM: 60 };
  const view = render(DownloadStep, {
    props: { project: project(DIGITIZED), runtime: {}, digitizerHealth: { status: "ok" } },
  });
  for (const [id, name] of [["vp3-button", "VP3"], ["xxx-button", "XXX"]]) {
    const btn = ui(view).getByTestId(id);
    expect(btn).toHaveAccessibleName(name);
    expect(btn.classList.contains("caveat")).toBe(false);
    expect(btn.getAttribute("aria-describedby")).toBeNull();
  }
  // The words, not just the markers — a caveat under any other id would be
  // the same paragraph in front of the same customer.
  expect(view.container.textContent).not.toMatch(/0\.1\s?mm/i);
  expect(view.container.textContent).not.toMatch(/narrower/i);
  // Not vacuous: the JEF caveat IS on the page at this size.
  expect(ui(view).getByTestId("jef-hoop-header-note")).toBeInTheDocument();
});
