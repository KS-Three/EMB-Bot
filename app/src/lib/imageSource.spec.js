import { test, expect } from "vitest";
import { pendingImageRehydrations, rehydrateImages } from "./imageSource.js";

// Measured 2026-09-07 in a browser, on the shipped build: upload artwork with
// the digitizer service down (which is the ONLY way to get an `image`
// element), press refresh, and the design is gone — 2739 stitches before,
// no stitch caption after, and not one word about it. The pixels lived only
// in App's `runtime`, which is not persisted, while `_hasImage: true` was.
//
// The decode itself needs a canvas and is covered by the e2e round trip in
// wizard-smoke.spec.js. What is unit-tested here is the part that actually
// goes wrong: WHICH elements get restored, in what order, and what happens
// when one of them fails or a project switch overtakes the run.

const img = (id, extra = {}) => ({ id, type: "image", sourcePng: "b64-" + id, nColors: 4, removeBg: true, ...extra });

function spy() {
  const calls = [];
  const fn = (...a) => { calls.push(a); return a; };
  fn.calls = calls;
  return fn;
}

function harness(over = {}) {
  const onImage = spy(), onFlat = spy(), onError = spy();
  return {
    onImage, onFlat, onError,
    decode: async (b64) => ({ rgba: new Uint8ClampedArray(4), w: 1, h: 1, from: b64 }),
    flatten: (workImage, nColors, removeBg) => ({ of: workImage.from, nColors, removeBg }),
    ...over,
  };
}

// --- which elements ---------------------------------------------------------

test("only image elements with saved artwork that runtime does not already hold", () => {
  const project = { elements: [
    img("a"),
    { id: "b", type: "image", sourcePng: null },      // never uploaded
    { id: "c", type: "text", sourcePng: "b64-c" },    // not an image element
    { id: "d", type: "digitized", sourcePng: "b64" }, // keeps its own result
    img("e"),
  ]};
  expect(pendingImageRehydrations(project, { workImages: { e: {} } }).map((el) => el.id)).toEqual(["a"]);
  expect(pendingImageRehydrations(project, {}).map((el) => el.id)).toEqual(["a", "e"]);
});

test("a missing or empty project is not an error", () => {
  for (const p of [null, undefined, {}, { elements: null }]) {
    expect(pendingImageRehydrations(p, {})).toEqual([]);
  }
  expect(pendingImageRehydrations({ elements: [img("a")] }, null).map((e) => e.id)).toEqual(["a"]);
});

// --- publishing -------------------------------------------------------------

test("each element is published as it lands, working image before flat", async () => {
  const h = harness();
  const order = [];
  const res = await rehydrateImages({ elements: [img("a"), img("b")] }, {}, {
    ...h,
    onImage: (id, w) => order.push(`image:${id}`),
    onFlat: (id, f) => order.push(`flat:${id}`),
  });
  // Interleaved per element, not both images then both flats: a two-element
  // project shows its first artwork without waiting for the second.
  expect(order).toEqual(["image:a", "flat:a", "image:b", "flat:b"]);
  expect(res).toEqual({ done: ["a", "b"], failed: [], abandoned: false });
});

test("the flatten runs at the element's OWN settings, not the factory defaults", async () => {
  const h = harness();
  await rehydrateImages({ elements: [img("a", { nColors: 7, removeBg: false })] }, {}, h);
  expect(h.onFlat.calls[0][1]).toEqual({ of: "b64-a", nColors: 7, removeBg: false });
});

// --- the two ways it can go wrong -------------------------------------------

test("one unreadable record does not stop the others coming back", async () => {
  const h = harness({
    decode: async (b64) => {
      if (b64 === "b64-b") throw new Error("truncated record");
      return { rgba: new Uint8ClampedArray(4), w: 1, h: 1, from: b64 };
    },
  });
  const res = await rehydrateImages({ elements: [img("a"), img("b"), img("c")] }, {}, h);
  expect(res.done).toEqual(["a", "c"]);
  expect(res.failed).toEqual(["b"]);
  expect(h.onError.calls.map((c) => c[0])).toEqual(["b"]);
  // And nothing was published for the one that failed.
  expect(h.onImage.calls.map((c) => c[0])).toEqual(["a", "c"]);
});

test("a project switch mid-run abandons it without writing into the new runtime", async () => {
  const h = harness();
  let live = true;
  const res = await rehydrateImages({ elements: [img("a"), img("b"), img("c")] }, {}, {
    ...h,
    onFlat: (id, f) => { h.onFlat(id, f); if (id === "a") live = false; },
    token: () => live,
  });
  expect(res.abandoned).toBe(true);
  expect(res.done).toEqual(["a"]);
  // b and c never reached runtime — that is the whole point of the token.
  expect(h.onImage.calls.map((c) => c[0])).toEqual(["a"]);
});

test("a switch that lands between the decode and the publish is still caught", async () => {
  // The narrow window: the token is checked again AFTER the await, so a
  // decode that was already in flight cannot write into the new project.
  const h = harness();
  let live = true;
  const res = await rehydrateImages({ elements: [img("a")] }, {}, {
    ...h,
    decode: async (b64) => { live = false; return { rgba: new Uint8ClampedArray(4), w: 1, h: 1, from: b64 }; },
    token: () => live,
  });
  expect(res).toEqual({ done: [], failed: [], abandoned: true });
  expect(h.onImage.calls).toEqual([]);
});

test("nothing to do is a clean no-op", async () => {
  const h = harness();
  expect(await rehydrateImages({ elements: [{ id: "a", type: "text" }] }, {}, h))
    .toEqual({ done: [], failed: [], abandoned: false });
  expect(h.onImage.calls).toEqual([]);
});
