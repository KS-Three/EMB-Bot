// @vitest-environment jsdom
// fontLoader's BROWSER path (fetch, not fs) and loadCoverage — the half the
// Node-side fontLoader.spec.js cannot reach, because IS_NODE is fixed at import.
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

function okJson(obj) {
  const bytes = new TextEncoder().encode(JSON.stringify(obj));
  return { ok: true, status: 200, arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) };
}

// fontLoader imports the engine at load; none of these tests decode a font.
vi.mock("./emb.js", () => ({ EMB: {} }));

beforeEach(() => { vi.resetModules(); });
afterEach(() => { vi.unstubAllGlobals(); });

describe("fontLoader in the browser", () => {
  it("fetches document-relative, never from the domain root", async () => {
    const fetchMock = vi.fn(async () => okJson({ fonts: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const { loadManifest } = await import("./fontLoader.js");
    await loadManifest();
    expect(fetchMock).toHaveBeenCalledWith("fonts/manifest.json");
  });

  it("the manifest keeps only verified fonts", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => okJson({ fonts: [
      { key: "a", tier: "verified" }, { key: "b", tier: "candidate" }, { key: "c" },
    ] })));
    const { loadManifest } = await import("./fontLoader.js");
    expect((await loadManifest()).fonts.map((f) => f.key)).toEqual(["a"]);
  });

  it("a dead connection is flagged offline and names the file", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    const { loadManifest } = await import("./fontLoader.js");
    const err = await loadManifest().catch((e) => e);
    expect(err.offline).toBe(true);
    expect(err.message).toMatch(/manifest\.json/);
    expect(err.message).toMatch(/Failed to fetch/);
  });

  it("an HTTP error is NOT offline and keeps its status", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 404 })));
    const { loadManifest } = await import("./fontLoader.js");
    const err = await loadManifest().catch((e) => e);
    expect(err.offline).toBeUndefined();
    expect(err.message).toMatch(/404/);
  });

  it("a failed manifest load is retried, not cached as a rejection", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("down"))
      .mockResolvedValue(okJson({ fonts: [{ key: "a", tier: "verified" }] }));
    vi.stubGlobal("fetch", fetchMock);
    const { loadManifest } = await import("./fontLoader.js");
    await expect(loadManifest()).rejects.toThrow();
    expect((await loadManifest()).fonts).toHaveLength(1);
  });

  it("loadCoverage returns the parsed file and caches it", async () => {
    const fetchMock = vi.fn(async () => okJson({ fonts: { a: "abc" } }));
    vi.stubGlobal("fetch", fetchMock);
    const { loadCoverage } = await import("./fontLoader.js");
    const c = await loadCoverage();
    expect(c.fonts.a).toBe("abc");
    expect(await loadCoverage()).toBe(c);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("loadCoverage degrades to null on a fetch failure or a file with no fonts, and retries", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("down"))
      .mockResolvedValueOnce(okJson({ nothing: 1 }))
      .mockResolvedValue(okJson({ fonts: {} }));
    vi.stubGlobal("fetch", fetchMock);
    const { loadCoverage } = await import("./fontLoader.js");
    expect(await loadCoverage()).toBeNull();
    // a parsed-but-wrong file resolves null and is cached (not a failure)
    expect(await loadCoverage()).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
