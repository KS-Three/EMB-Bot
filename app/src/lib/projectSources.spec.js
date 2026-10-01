import { test, expect, describe } from "vitest";
import { collectSources, restoreSources } from "./projectSources.js";
import { defaultProject, defaultDigitizedElement } from "./project.js";

// The bridge between the .embproj file and the browser's source store, run
// against an in-memory stand-in for the store (jsdom has no IndexedDB).

function bytesOf(n, seed = 1) {
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i++) out[i] = (i * 13 + seed) & 0xff;
  return out;
}

function project(keys) {
  const elements = keys.map((key, i) => ({
    ...defaultDigitizedElement("d" + (i + 1)),
    sourceFile: key ? { key, type: "image/png", size: 3, width: 10, height: 10 } : null,
  }));
  return { ...defaultProject(), elements, selectedId: "d1" };
}

function fakeStore(map, { available = true, keyFor = async (b) => "h" + b.length, failPut = false, failGet = false } = {}) {
  return {
    available: () => available,
    getSource: async (key) => {
      if (failGet) throw new Error("boom");
      return map.get(key) || null;
    },
    putSource: async (key, rec) => {
      if (failPut) throw new Error("quota");
      map.set(key, rec);
    },
    sourceKeyFor: keyFor,
  };
}

describe("collectSources", () => {
  test("gathers what the store holds for the project's elements, once per key, and skips what is gone", async () => {
    const map = new Map([["k1", { bytes: bytesOf(5), type: "image/png", name: "a.png" }]]);
    const out = await collectSources(project(["k1", "k1", "k2", null]), fakeStore(map));
    expect(Object.keys(out)).toEqual(["k1"]);
    expect(out.k1).toEqual({ bytes: bytesOf(5), type: "image/png", name: "a.png" });
  });

  test("an unavailable store, an unreadable record, or a project without uploads gives nothing — and never throws", async () => {
    const map = new Map([["k1", { bytes: bytesOf(5), type: "", name: "" }]]);
    expect(await collectSources(project(["k1"]), fakeStore(map, { available: false }))).toEqual({});
    expect(await collectSources(project(["k1"]), fakeStore(map, { failGet: true }))).toEqual({});
    expect(await collectSources(defaultProject(), fakeStore(map))).toEqual({});
    // A record with no bytes is not an original.
    expect(await collectSources(project(["k1"]), fakeStore(new Map([["k1", { bytes: new Uint8Array(0) }]])))).toEqual({});
  });
});

describe("restoreSources", () => {
  test("puts each original in the store under the key its bytes hash to and repoints every element that used the file's key", async () => {
    const map = new Map();
    const input = project(["file-key", "file-key", "absent"]);
    const sources = { "file-key": { bytes: bytesOf(5), type: "image/png", name: "a.png" } };
    const r = await restoreSources(input, sources, fakeStore(map));

    expect(r.restored).toBe(1);
    expect(r.missing).toBe(1);          // "absent" was not in the file
    expect(r.failed).toBe(0);
    expect(map.get("h5")).toEqual({ bytes: bytesOf(5), type: "image/png", name: "a.png" });
    expect(map.has("file-key")).toBe(false);
    expect(r.project.elements.map((e) => e.sourceFile.key)).toEqual(["h5", "h5", "absent"]);
    // The caller's object is untouched; the repointed project is a new one.
    expect(input.elements.map((e) => e.sourceFile.key)).toEqual(["file-key", "file-key", "absent"]);
    expect(r.project).not.toBe(input);
    expect(r.project.elements[2]).toBe(input.elements[2]);
  });

  test("when the file's key already is the content key nothing is rewritten and the same project comes back", async () => {
    const map = new Map();
    const input = project(["h5"]);
    const r = await restoreSources(input, { h5: { bytes: bytesOf(5), type: "", name: "" } }, fakeStore(map));
    expect(r).toEqual({ project: input, restored: 1, missing: 0, failed: 0 });
    expect(r.project).toBe(input);
    expect(map.get("h5").bytes).toEqual(bytesOf(5));
  });

  test("a browser that cannot keep originals registers the design unchanged and counts them as failed", async () => {
    const input = project(["k1", "k2"]);
    const sources = { k1: { bytes: bytesOf(5) } };
    const off = await restoreSources(input, sources, fakeStore(new Map(), { available: false }));
    expect(off).toEqual({ project: input, restored: 0, missing: 1, failed: 1 });

    const quota = await restoreSources(input, sources, fakeStore(new Map(), { failPut: true }));
    expect(quota).toEqual({ project: input, restored: 0, missing: 1, failed: 1 });
    expect(quota.project.elements[0].sourceFile.key).toBe("k1");
  });

  test("a file without originals, or a project without uploads, is a no-op", async () => {
    const input = project(["k1"]);
    expect(await restoreSources(input, {}, fakeStore(new Map()))).toEqual({ project: input, restored: 0, missing: 1, failed: 0 });
    expect(await restoreSources(input, null, fakeStore(new Map()))).toEqual({ project: input, restored: 0, missing: 1, failed: 0 });
    const text = defaultProject();
    expect(await restoreSources(text, { k1: { bytes: bytesOf(5) } }, fakeStore(new Map()))).toEqual({ project: text, restored: 0, missing: 0, failed: 0 });
  });
});
