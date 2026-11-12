// @vitest-environment jsdom
//
// Cancel on a running digitize (2026-11-12). A job runs 60 to 600 s and the
// panel used to offer wait-or-reload. The control sits beside the status
// line while a run is in flight; pressing it tells the service to stop the
// job and puts the panel back to idle with the artwork, every setting and
// the previous result untouched. A cancel is not an error and shows none
// (no-warnings ruling 2026-10-02).
//
// The service here is a fetch stub; the real one is driven end to end by
// e2e/digitize-cancel.spec.js.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { render, fireEvent, screen, cleanup, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./DigitizePanel.testHarness.svelte";
import { DEFAULT_DIGITIZE_PARAMS } from "../lib/project.js";

vi.mock("../lib/emb.js", async () => {
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  return { EMB: globalThis.EMB };
});

const PRIOR = { stitchCount: 100, widthMM: 50, heightMM: 50, colorCount: 1, colors: [], stitches: [] };
const FRESH = {
  name: "Digitized design", stitchCount: 2, colorCount: 1, widthMM: 1, heightMM: 0.1,
  colors: [{ r: 0, g: 0, b: 0, name: "Black" }],
  stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 10, y: 0, type: "stitch" }, { x: 0, y: 0, type: "end" }],
};

function element(extra = {}) {
  return {
    id: "e1", type: "digitized", name: "logo.png", sourcePng: "AAAA",
    params: { ...DEFAULT_DIGITIZE_PARAMS }, result: PRIOR, warnings: [], blockColors: {},
    review: { brandId: "studio", shapes: [] }, shapeOverrides: {}, deletedShapeIds: [],
    appliedEdits: null, preflight: null, sizeMm: null, offsetXMm: 0, offsetYMm: 0, rotationDeg: 0, ...extra,
  };
}

// A fake service. `svc.poll` is what GET /jobs/{id} answers; `svc.submit`
// may hold the upload open. /classify and /recount answer "no such route".
let svc;
beforeEach(() => {
  sessionStorage.clear();
  svc = { calls: [], poll: () => ({ state: "running" }), submit: null, jobs: 0 };
  vi.stubGlobal("fetch", async (url, init = {}) => {
    const path = new URL(String(url)).pathname;
    const method = init.method || "GET";
    svc.calls.push(method + " " + path);
    const json = (status, body) => ({ ok: status < 400, status, json: async () => body });
    if (method === "POST" && path === "/digitize") {
      if (svc.submit) await svc.submit();
      return json(202, { job_id: "j" + ++svc.jobs, state: "queued", cached: false });
    }
    if (method === "POST" && /^\/jobs\/[^/]+\/cancel$/.test(path)) return json(200, { state: "cancelled" });
    if (method === "GET" && path.startsWith("/jobs/")) return json(200, svc.poll());
    return json(404, { detail: "Not Found" });
  });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const count = (line) => svc.calls.filter((c) => c === line).length;
const runButton = () => screen.getByRole("button", { name: /Auto Digitize Image|Digitizing…/ });
const cancelButton = () => screen.queryByRole("button", { name: "Cancel digitizing" });

function mount(extra) {
  const patches = [];
  render(Harness, { props: { element: element(extra), health: { status: "ok" }, onPatch: (d) => patches.push(d) } });
  return patches;
}

async function startRun() {
  await fireEvent.click(runButton());
  await waitFor(() => expect(screen.getByText("Digitizing your art…")).toBeInTheDocument(), { timeout: 3000 });
}

describe("Cancel on a running digitize", () => {
  test("is offered only while a run is in flight, as a labelled button beside the status line", async () => {
    mount();
    expect(cancelButton()).toBeNull();
    await startRun();
    const cancel = cancelButton();
    expect(cancel).toBeVisible();
    expect(cancel.tagName).toBe("BUTTON");          // keyboard reachable: a real button, in tab order
    expect(cancel).toHaveTextContent("Cancel");
    expect(cancel).not.toHaveAttribute("tabindex", "-1");
    expect(cancel.closest(".dgp-pending").querySelector("[role=status]")).toHaveTextContent("Digitizing your art…");
  });

  test("pressing it tells the service, returns the panel to idle, and lands nothing", async () => {
    const patches = mount();
    await startRun();
    await fireEvent.click(cancelButton());

    await waitFor(() => expect(runButton()).toBeEnabled());
    expect(runButton()).toHaveTextContent("Auto Digitize Image");
    expect(cancelButton()).toBeNull();
    expect(count("POST /jobs/j1/cancel")).toBe(1);
    // Nothing of the cancelled run reached the element...
    expect(patches).toEqual([]);
    // ...so the previous result is still what the panel reports,
    expect(screen.getByText(/100 stitches/)).toBeInTheDocument();
    // and a cancel is not an error: no alert, no message of any kind.
    expect(document.querySelector(".dgp-error")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(document.querySelector(".dgp-pending")).toBeNull();
    // A later reload must not resume the run the customer cancelled.
    expect(sessionStorage.getItem("embot.digitizing.e1")).toBeNull();
  });

  test("the artwork and every setting are kept, and digitizing again runs and lands", async () => {
    const patches = mount({ params: { ...DEFAULT_DIGITIZE_PARAMS, max_colors: 3 } });
    await startRun();
    await fireEvent.click(cancelButton());
    await waitFor(() => expect(runButton()).toBeEnabled());

    svc.poll = () => ({ state: "done", design: FRESH, warnings: [], stats: null, review: null, preflight: null });
    await fireEvent.click(runButton());
    await waitFor(() => expect(patches).toHaveLength(1), { timeout: 3000 });
    expect(patches[0].patch.result.stitchCount).toBe(2);
    expect(patches[0].patch.params).toBeUndefined();           // the run changed no setting
    expect(count("POST /digitize")).toBe(2);
    // The service heard the cancel before it was sent the second upload.
    expect(svc.calls.indexOf("POST /jobs/j1/cancel")).toBeLessThan(svc.calls.lastIndexOf("POST /digitize"));
    await waitFor(() => expect(runButton()).toBeEnabled());
    expect(document.querySelector(".dgp-error")).toBeNull();
  });

  test("pressed while the upload is still on its way: the submit lands, then that job is cancelled", async () => {
    let finishUpload;
    svc.submit = () => new Promise((res) => { finishUpload = res; });
    const patches = mount();
    await fireEvent.click(runButton());
    await waitFor(() => expect(screen.getByText("Sending your art…")).toBeInTheDocument());
    await fireEvent.click(cancelButton());
    expect(screen.getByText("Cancelling…")).toBeInTheDocument();
    expect(cancelButton()).toHaveAttribute("aria-disabled", "true");
    await fireEvent.click(cancelButton());                      // a second press does nothing more

    finishUpload();
    await waitFor(() => expect(runButton()).toBeEnabled());
    expect(count("POST /jobs/j1/cancel")).toBe(1);
    expect(svc.calls.some((c) => c.startsWith("GET /jobs/"))).toBe(false);
    expect(patches).toEqual([]);
    expect(document.querySelector(".dgp-error")).toBeNull();
  });

  test("a run that finishes in the moment Cancel is pressed is still not landed", async () => {
    const patches = mount();
    await startRun();
    svc.poll = () => ({ state: "done", design: FRESH, warnings: [] });
    await fireEvent.click(cancelButton());
    await waitFor(() => expect(runButton()).toBeEnabled());
    expect(patches).toEqual([]);
    expect(screen.getByText(/100 stitches/)).toBeInTheDocument();
  });

  test("a failure after the press is not shown: a cancel is not an error", async () => {
    let failUpload;
    svc.submit = () => new Promise((_, rej) => { failUpload = () => rej(new TypeError("Failed to fetch")); });
    mount();
    await fireEvent.click(runButton());
    await waitFor(() => expect(cancelButton()).not.toBeNull());
    await fireEvent.click(cancelButton());
    failUpload();
    await waitFor(() => expect(runButton()).toBeEnabled());
    expect(document.querySelector(".dgp-error")).toBeNull();
  });

  test("keyboard: focus on Cancel moves to the run button when the run is gone", async () => {
    mount();
    await startRun();
    cancelButton().focus();
    expect(document.activeElement).toBe(cancelButton());
    await fireEvent.click(cancelButton());                      // Enter/Space on a focused button is a click
    await waitFor(() => expect(runButton()).toBeEnabled());
    await waitFor(() => expect(document.activeElement).toBe(runButton()));
  });

  test("a job the service reports cancelled (another tab pressed it) goes idle the same quiet way", async () => {
    const patches = mount();
    await startRun();
    svc.poll = () => ({ state: "cancelled" });
    await waitFor(() => expect(runButton()).toBeEnabled(), { timeout: 3000 });
    expect(patches).toEqual([]);
    expect(document.querySelector(".dgp-error")).toBeNull();
    expect(count("POST /jobs/j1/cancel")).toBe(0);
  });
});
