// @vitest-environment jsdom
//
// Drawer thumbnails: lazy (only rows in view draw) and cached (a second open
// of the drawer makes no render calls). renderRealistic is mocked and
// counted; IntersectionObserver is a hand-driven stub, since jsdom has none.
import { beforeAll, beforeEach, expect, test, vi } from "vitest";
// projectThumb.js (imported below) builds through generate.js, which reads the
// engine globals at import time (lib/emb.js throws otherwise): load them
// hoisted, before any import, as projectThumb.spec.js does.
vi.hoisted(async () => {
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
});
import { render, cleanup } from "@testing-library/svelte";
import { tick } from "svelte";
import { createRequire } from "node:module";

vi.mock("../lib/preview.js", () => ({ renderRealistic: vi.fn() }));
import { renderRealistic } from "../lib/preview.js";
import { clearThumbCache } from "../lib/projectThumb.js";

let ProjectsDrawer;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  ({ default: ProjectsDrawer } = await import("./ProjectsDrawer.svelte"));
});

let observers;
class FakeIO {
  constructor(cb) { this.cb = cb; this.nodes = new Set(); observers.push(this); }
  observe(n) { this.nodes.add(n); }
  unobserve(n) { this.nodes.delete(n); }
  disconnect() { this.nodes.clear(); }
}
// Report the first `k` observed nodes as in view.
async function scrollTo(k) {
  const io = observers[observers.length - 1];
  const hits = [...io.nodes].slice(0, k).map((target) => ({ target, isIntersecting: true }));
  io.cb(hits);
  await tick();
}

const stitchy = { elements: [{ id: "e", type: "digitized", result: { stitches: [
  { x: 0, y: 0, type: "stitch" }, { x: 50, y: 20, type: "stitch" }, { x: 90, y: 0, type: "stitch" },
], colors: [{ rgb: [1, 2, 3] }] } }] };

function seed(n, withStitches = n) {
  const index = [];
  for (let i = 0; i < n; i++) {
    const id = "p" + i;
    index.push({ id, name: "Design " + i, updatedAt: 1000 + i });
    localStorage.setItem("embstudio:p:" + id, JSON.stringify(i < withStitches ? stitchy : { elements: [] }));
  }
  localStorage.setItem("embstudio:index", JSON.stringify(index));
  return index.slice().sort((a, b) => b.updatedAt - a.updatedAt);
}

beforeEach(() => {
  cleanup();
  localStorage.clear();
  clearThumbCache();
  renderRealistic.mockClear();
  observers = [];
  vi.stubGlobal("IntersectionObserver", FakeIO);
  HTMLCanvasElement.prototype.getContext = () => ({});
  HTMLCanvasElement.prototype.toDataURL = () => "data:image/png;base64,AAAA";
});

test("opening the drawer a second time makes 0 render calls", async () => {
  const projects = seed(4);
  const first = render(ProjectsDrawer, { projects, currentId: null });
  await scrollTo(10);
  expect(renderRealistic).toHaveBeenCalledTimes(4);
  expect(first.container.querySelectorAll(".drawer-thumb img").length).toBe(4);
  first.unmount();

  renderRealistic.mockClear();
  const second = render(ProjectsDrawer, { projects, currentId: null });
  await scrollTo(10);
  expect(renderRealistic).toHaveBeenCalledTimes(0);
  expect(second.container.querySelectorAll(".drawer-thumb img").length).toBe(4);
});

test("a 30-project list draws only the rows that scroll into view", async () => {
  const projects = seed(30);
  const { container } = render(ProjectsDrawer, { projects, currentId: null });
  expect(container.querySelectorAll(".drawer-thumb").length).toBe(30);
  expect(renderRealistic).toHaveBeenCalledTimes(0); // nothing intersects yet
  await scrollTo(5);
  expect(renderRealistic).toHaveBeenCalledTimes(5);
  expect(container.querySelectorAll(".drawer-thumb img").length).toBe(5);
});

test("a project with no stitches keeps the placeholder and draws nothing", async () => {
  const projects = seed(3, 1); // only p0 has stitches
  const { container } = render(ProjectsDrawer, { projects, currentId: null });
  await scrollTo(10);
  expect(renderRealistic).toHaveBeenCalledTimes(1);
  expect(container.querySelectorAll(".drawer-thumb img").length).toBe(1);
  expect(container.querySelectorAll(".drawer-thumb-empty").length).toBe(2);
});
