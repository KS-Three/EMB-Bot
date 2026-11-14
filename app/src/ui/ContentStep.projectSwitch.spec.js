// @vitest-environment jsdom
//
// A run belongs to the DESIGN it was started in, not just to an element id.
// Element ids are per project -- every artwork-only design's logo is `e1` --
// and App.enterProject swaps `project` without remounting ContentStep. While
// the panel was keyed by `el.id` alone it survived the switch, and its
// landing patch ({ id: "e1" }) went through App.elUpdate into whichever
// design was open by then: Auto Digitize in design A, open design B from My
// designs before it ended, and A's stitches, review and appliedConfig were
// saved on B's `e1` (2026-11-13 review, reproduced). The sessionStorage
// resume mark had the same hole: `embot.digitizing.e1` left by design A
// auto-ran a digitize on design B's `e1` that nobody pressed.
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor, screen } from "@testing-library/svelte";
import Harness from "./ContentStep.testHarness.svelte";
import { defaultProject, defaultDigitizedElement, defaultTextElement, DEFAULT_DIGITIZE_PARAMS } from "../lib/project.js";

vi.mock("../lib/emb.js", async () => {
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign = globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used"); });
  return { EMB: globalThis.EMB };
});
// The pre-run reading and stitch recount would otherwise reach for a service.
vi.mock("../lib/digitizer.js", async (orig) => ({
  ...(await orig()),
  classifyArt: () => new Promise(() => {}),
  recountArt: () => new Promise(() => {}),
}));
vi.mock("../lib/outlineFonts.js", async (orig) => ({ ...(await orig()), digitizeLettering: vi.fn() }));

beforeEach(() => {
  sessionStorage.clear();
  // FontSelect (TextStep) fetches its manifest on mount; nothing here reads it.
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
});
afterEach(() => vi.restoreAllMocks());

const HEALTH = { ok: true, limits: { max_upload_bytes: 12e6, max_pixels: 4e7 } };
const DESIGN = (name) => ({
  name, stitchCount: 2, widthMM: 50, heightMM: 10, colorCount: 1, colors: [{ r: 1, g: 2, b: 3 }],
  stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 500, y: 100, type: "stitch" }, { x: 0, y: 0, type: "end" }],
});
const settle = () => new Promise((r) => setTimeout(r, 60));

function artProject(png, name, extra = []) {
  const el = { ...defaultDigitizedElement("e1"), name, sourcePng: png, params: { ...DEFAULT_DIGITIZE_PARAMS } };
  return { ...defaultProject(), elements: [el, ...extra], selectedId: "e1", selectedIds: ["e1"] };
}

async function spyDigitize() {
  const mod = await import("../lib/digitizer.js");
  const sent = [];
  const resolvers = [];
  vi.spyOn(mod, "digitize").mockImplementation((image) => {
    sent.push(image);
    return new Promise((r) => resolvers.push(r));
  });
  return { sent, resolvers };
}

test("a run started in design A never lands on design B's element with the same id", async () => {
  const { sent, resolvers } = await spyDigitize();
  const A = artProject("AAAA", "dog-photo.png");
  const B = artProject("BBBB", "church-logo.png");
  const updates = [];
  const onElUpdate = (d) => updates.push(d);
  const utils = render(Harness, { props: { project: A, projectId: "pA", digitizerHealth: HEALTH, onElUpdate } });
  await fireEvent.click(await screen.findByRole("button", { name: "Auto Digitize Image" }));
  await waitFor(() => expect(sent).toEqual(["AAAA"]));

  // My designs -> open design B: App.enterProject swaps project and currentId.
  await utils.rerender({ project: B, projectId: "pB", digitizerHealth: HEALTH, onElUpdate });
  await settle();
  resolvers[0]({ design: DESIGN("from-AAAA"), warnings: [], review: null, stats: null, preflight: null });
  await settle();

  expect(updates.filter((u) => u.patch && "result" in u.patch)).toEqual([]);
  // ...and B was not digitized behind the customer's back either.
  expect(sent).toEqual(["AAAA"]);
});

test("design A's resume mark does not auto-run a digitize on design B's e1, and still resumes on A", async () => {
  const { sent } = await spyDigitize();
  const e2 = { ...defaultDigitizedElement("e2"), name: "other.png" };
  const A = artProject("AAAA", "dog-photo.png", [e2]);
  const B = artProject("BBBB", "church-logo.png");
  const onElUpdate = () => {};
  const utils = render(Harness, { props: { project: A, projectId: "pA", digitizerHealth: HEALTH, onElUpdate } });
  await fireEvent.click(await screen.findByRole("button", { name: "Auto Digitize Image" }));
  await waitFor(() => expect(sent).toEqual(["AAAA"]));

  // Click A's other element: the panel is torn down mid-run and leaves the
  // mark for the next panel of A's e1 to join the job (lib/digitizeBusy.js).
  await utils.rerender({ project: { ...A, selectedId: "e2", selectedIds: ["e2"] }, projectId: "pA", digitizerHealth: HEALTH, onElUpdate });
  await settle();
  // Open design B, whose selected element is also `e1`.
  await utils.rerender({ project: B, projectId: "pB", digitizerHealth: HEALTH, onElUpdate });
  await settle();
  expect(sent).toEqual(["AAAA"]);

  // Back to design A: ITS mark is still there and the run is joined.
  await utils.rerender({ project: A, projectId: "pA", digitizerHealth: HEALTH, onElUpdate });
  await waitFor(() => expect(sent).toEqual(["AAAA", "AAAA"]));
});

test("an outline-font lettering run started in design A never lands on design B's text e1", async () => {
  const { digitizeLettering } = await import("../lib/outlineFonts.js");
  const reqs = [];
  let resolveJob;
  digitizeLettering.mockImplementation((req) => {
    reqs.push(req.text);
    return new Promise((r) => (resolveJob = r));
  });
  const textProject = (text) => {
    const el = { ...defaultTextElement("e1"), text, fontKey: "outline:test_font" };
    return { ...defaultProject(), elements: [el], selectedId: "e1", selectedIds: ["e1"] };
  };
  const updates = [];
  const onElUpdate = (d) => updates.push(d);
  const utils = render(Harness, { props: { project: textProject("ALPHA"), projectId: "pA", digitizerHealth: HEALTH, onElUpdate } });
  await fireEvent.click(await screen.findByRole("button", { name: "Digitize lettering" }));
  await waitFor(() => expect(reqs).toEqual(["ALPHA"]));

  await utils.rerender({ project: textProject("BRAVO"), projectId: "pB", digitizerHealth: HEALTH, onElUpdate });
  await screen.findByRole("button", { name: "Digitize lettering" });
  resolveJob({ design: DESIGN("ALPHA"), warnings: [], review: null, stats: null, preflight: null, lettering: null });
  await settle();

  expect(updates.filter((u) => u.patch && "result" in u.patch)).toEqual([]);
  expect(reqs).toEqual(["ALPHA"]);
});
