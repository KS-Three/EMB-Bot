// The starter pack as the Studio uses it (lib/starterPack.js), run against the
// REAL pack files in public/starter/ and the real engine -- no stub decoder,
// because the claims here are about what a customer gets: the manifest's
// stitch count on the canvas, inside the placement, in one undo step, and
// still there after a save and a load.
//
// What the pack IS (licences, file hashes, counts) is test/starter-pack.test.js's
// job, not this file's.
import { beforeAll, beforeEach, describe, expect, test } from "vitest";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const PACK = join(HERE, "..", "..", "public", "starter");
const manifest = JSON.parse(readFileSync(join(PACK, "manifest.json"), "utf8"));
const fileBytes = (name) => new Uint8Array(readFileSync(join(PACK, name)));

// A fetch that serves the pack from disk, by the document-relative URLs the
// module builds. Anything else is a 404, as the dev server would answer.
function packFetch(log = []) {
  return async (url) => {
    log.push(url);
    const m = /^starter\/([\w.-]+)$/.exec(url);
    let bytes = null;
    try {
      if (m) bytes = fileBytes(m[1]);
    } catch {
      bytes = null;
    }
    if (!bytes) return { ok: false, status: 404 };
    return {
      ok: true,
      status: 200,
      json: async () => JSON.parse(Buffer.from(bytes).toString("utf8")),
      arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    };
  };
}

function memoryStorage() {
  const store = new Map();
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => void store.set(k, String(v)),
    removeItem: (k) => void store.delete(k),
    clear: () => store.clear(),
  };
}

let pack, EMB, project, generate, designImport, STARTER_THREADS;
let designs;

beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  // The engine, loaded the way emb.spec.js loads it (order matters).
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
  ({ EMB } = await import("./emb.js"));
  pack = await import("./starterPack.js");
  project = await import("./project.js");
  generate = await import("./generate.js");
  designImport = await import("./designImport.js");
  ({ STARTER_THREADS } = await import("./starterThreads.js"));
  designs = pack.starterDesigns(manifest);
});

beforeEach(() => {
  globalThis.localStorage = memoryStorage();
});

const bytesOf = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

describe("the manifest as the picker sees it", () => {
  test("twelve designs, each with the manifest's title and a provenance line", () => {
    expect(designs).toHaveLength(12);
    for (const [i, d] of designs.entries()) {
      const m = manifest.designs[i];
      expect(d.title).toBe(m.title);
      expect(d.credit).toBe(`Art by ${m.author} · ${m.license}`);
      expect(d.sourceUrl).toBe(m.source_page_url);
      expect(d.sourceUrl).toMatch(/^https:\/\//);
    }
    expect(pack.creditLine({ author: "Jon Phillips", license: "CC0" })).toBe("Art by Jon Phillips · CC0");
  });

  test("file URLs are document-relative (the bundle is built with base './')", () => {
    for (const d of designs) {
      expect(d.artUrl).toMatch(/^starter\/[\w-]+\.svg$/);
      expect(d.dstUrl).toMatch(/^starter\/[\w-]+\.dst$/);
    }
  });

  test("no preflight grade, score or finding reaches the Studio", () => {
    // Kent's ruling: nothing about the pack is shown as a warning. The grades
    // stay in the manifest as a record; the Studio's view of a design does
    // not carry them, so no later template can print one by accident.
    expect(manifest.designs.some((d) => "preflight_grade" in d)).toBe(true);
    for (const d of designs) expect(JSON.stringify(d)).not.toMatch(/preflight|grade|score/i);
    const src = readFileSync(join(HERE, "..", "ui", "StarterPicker.svelte"), "utf8");
    expect(src.replace(/<script>[\s\S]*?<\/script>/, "").replace(/<!--[\s\S]*?-->/g, "")).not.toMatch(/preflight|grade|score|warn/i);
  });

  test("an unreadable manifest throws instead of listing nothing", () => {
    expect(() => pack.starterDesigns({})).toThrow(/unreadable/);
    expect(() => pack.starterDesigns(null)).toThrow(/unreadable/);
  });

  test("loadStarterPack fetches once, and a failure is not cached", async () => {
    const down = async () => ({ ok: false, status: 503 });
    await expect(pack.loadStarterPack(down)).rejects.toThrow(/503/);
    const log = [];
    const a = await pack.loadStarterPack(packFetch(log));
    const b = await pack.loadStarterPack(packFetch(log));
    expect(a).toBe(b);
    expect(a.map((d) => d.id)).toEqual(manifest.designs.map((d) => d.id));
    expect(log).toEqual(["starter/manifest.json"]);
  });
});

describe("thread colours", () => {
  test("every design has one colour per block of its DST, and nothing else is listed", () => {
    expect(Object.keys(STARTER_THREADS).sort()).toEqual(manifest.designs.map((d) => d.id).sort());
    for (const d of manifest.designs) {
      const threads = STARTER_THREADS[d.id];
      expect(threads, d.id).toHaveLength(d.colors);
      for (const rgb of threads) {
        expect(rgb).toHaveLength(3);
        for (const v of rgb) expect(Number.isInteger(v) && v >= 0 && v <= 255, `${d.id}: ${rgb}`).toBe(true);
      }
    }
  });

  test("starterBlockColors is the blockColors shape, and a copy", () => {
    const colors = pack.starterBlockColors("heart");
    expect(colors).toEqual({ 0: STARTER_THREADS.heart[0], 1: STARTER_THREADS.heart[1], 2: STARTER_THREADS.heart[2] });
    colors[0][0] = 1;
    expect(STARTER_THREADS.heart[0][0]).not.toBe(1);
    expect(pack.starterBlockColors("no-such-design")).toEqual({});
  });
});

describe("loading one design", () => {
  test("the patch is the ordinary file import of that .dst, plus its thread colours", async () => {
    const heart = designs.find((d) => d.id === "heart");
    const log = [];
    const patch = await pack.loadStarterPatch(heart, packFetch(log));
    expect(log).toEqual(["starter/heart.dst"]);
    // Same function DesignPanel's file picker calls, same bytes in: the only
    // difference a starter makes is the colours.
    expect(patch).toEqual({
      ...designImport.designFilePatch(fileBytes("heart.dst"), "Heart"),
      blockColors: pack.starterBlockColors("heart"),
    });
    expect(patch.name).toBe("Heart");
    expect(patch.sizeMm).toBeNull();
    expect(Array.from(bytesOf(patch.dstBase64))).toEqual(Array.from(fileBytes("heart.dst")));
  });

  test("a missing file or a response that is not a DST is refused", async () => {
    const heart = designs.find((d) => d.id === "heart");
    await expect(pack.loadStarterPatch(heart, async () => ({ ok: false, status: 404 }))).rejects.toThrow(/404/);
    // What a misconfigured static host does: answers 200 with its index page.
    const html = new TextEncoder().encode("<!doctype html><html><body>" + "x".repeat(2000) + "</body></html>");
    const page = async () => ({ ok: true, status: 200, arrayBuffer: async () => html.buffer });
    await expect(pack.loadStarterPatch(heart, page)).rejects.toThrow();
  });
});

describe("adding a design to the project", () => {
  const patchFor = (id) => pack.loadStarterPatch(designs.find((d) => d.id === id), packFetch());

  test("on a fresh project it replaces the untouched blank text box", async () => {
    const fresh = project.defaultProject();
    const frozen = JSON.stringify(fresh);
    const next = pack.addStarterDesign(fresh, await patchFor("owl"), 101.6);
    expect(next.elements).toHaveLength(1);
    const el = next.elements[0];
    expect(el.type).toBe("design");
    expect(el.name).toBe("Owl");
    expect(next.selectedId).toBe(el.id);
    expect(next.selectedIds).toEqual([el.id]);
    expect(project.deriveProjectName(next)).toBe("Owl");
    expect(JSON.stringify(fresh)).toBe(frozen); // pure: the input is untouched
  });

  test("on a project with content it is added beside it, selected, at the file's own size", async () => {
    const fresh = project.defaultProject();
    const typed = project.updateElement(fresh, fresh.elements[0].id, { text: "TEAM" });
    const next = pack.addStarterDesign(typed, await patchFor("baseball"), 101.6);
    expect(next.elements.map((e) => e.type)).toEqual(["text", "design"]);
    expect(next.elements[0]).toBe(typed.elements[0]); // existing work is not touched
    const el = next.elements[1];
    expect(next.selectedId).toBe(el.id);
    expect(el.sizeMm).toBeNull(); // native size; never a seeded resize of pre-digitized stitches
    expect(el.offsetYMm).toBe(-10); // addElement's usual stagger for a second element
  });

  test("it is one undo step, and never merges into the edit before it", async () => {
    const { createHistory } = await import("./history.js");
    const fresh = project.defaultProject();
    const typed = project.updateElement(fresh, fresh.elements[0].id, { text: "TEAM" });
    const history = createHistory(fresh);
    history.record(typed, 1000);
    // 100 ms later, well inside the 500 ms window that merges a drag's
    // patches: App records the insert as discrete, so it stands alone.
    const withStarter = pack.addStarterDesign(typed, await patchFor("turtle"), 101.6);
    history.record(withStarter, 1100, true);
    expect(history.undo()).toBe(typed);
    expect(history.undo()).toBe(fresh);
    expect(history.redo()).toBe(typed);
    expect(history.redo()).toBe(withStarter);
    expect(history.canRedo()).toBe(false);
  });

  test("it survives the .embproj file and the saved-designs registry unchanged", async () => {
    const { buildProjectFile, parseProjectFile } = await import("./projectFile.js");
    const { createProject, saveProject, loadProject } = await import("./projects.js");
    const p = pack.addStarterDesign(project.defaultProject(), await patchFor("christmas-tree"), 101.6);

    const file = parseProjectFile(buildProjectFile(p, "Christmas tree"));
    expect(file.project.elements).toEqual(p.elements);

    const { id } = createProject("Christmas tree");
    expect(saveProject(id, p)).toBe(true);
    expect(loadProject(id).elements).toEqual(p.elements);

    // And what comes back still sews: same stitches, same threads.
    const garment = EMB.getGarment(p.garmentId);
    const before = generate.generateElement(p.elements[0], garment, {});
    const after = generate.generateElement(file.project.elements[0], garment, {});
    expect(after.stitchCount).toBe(before.stitchCount);
    expect(after.colors).toEqual(before.colors);
    expect(after.stitches).toEqual(before.stitches);
  });
});

describe("what lands on the canvas", () => {
  test("every design sews the manifest's stitch count in the pack's thread colours", async () => {
    const garment = EMB.getGarment("left_chest");
    for (const d of designs) {
      const m = manifest.designs.find((x) => x.id === d.id);
      const p = pack.addStarterDesign(project.defaultProject(), await pack.loadStarterPatch(d, packFetch()), 101.6);
      const built = generate.generateElement(p.elements[0], garment, {});
      expect(built.stitchCount, d.id).toBe(m.stitches);
      expect(built.colorCount, d.id).toBe(m.colors);
      expect(built.colors, d.id).toEqual(STARTER_THREADS[d.id].map(([r, g, b]) => ({ r, g, b })));
      // On the default placement (a 4 in box) the file is not resized at all.
      expect(built._debug.scale, d.id).toBe(1);
      expect(built.widthMM, d.id).toBeCloseTo(m.width_mm, 0);
      expect(built.heightMM, d.id).toBeCloseTo(m.height_mm, 0);
    }
  });

  // Kent 2026-11-14, "Stop at 75%, say so": auto-fit of a stitch file no longer
  // shrinks it to the placement at any cost. It fits, or it sits exactly at the
  // 75% edge of the safe range and overflows the box (DesignPanel then says so:
  // StarterOverflow.spec.js). Before, every starter fitted every garment; the
  // table of what overflows now is in PR 1495.
  test("on every garment and placement a design either fits it or sits exactly at the 75% limit", async () => {
    const MM_PER_INCH = 25.4;
    const patches = await Promise.all(designs.map((d) => pack.loadStarterPatch(d, packFetch())));
    let shrunk = 0, atLimit = 0;
    for (const base of EMB.GARMENTS) {
      for (const pid of EMB.GARMENT_PLACEMENTS[base.id] || [base.id]) {
        const garment = EMB.resolvePlacement(base.id, pid === base.id ? null : pid); // as placed, like the Studio
        const boxW = garment.widthIn * MM_PER_INCH, boxH = garment.heightIn * MM_PER_INCH;
        for (const patch of patches) {
          const where = `${patch.name} on ${pid}`;
          const el = { ...project.defaultDesignElement("e1"), ...patch };
          const built = generate.generateElement(el, garment, {});
          const sc = built._debug.scale;
          expect(sc, where).toBeGreaterThanOrEqual(0.75 - 1e-9);
          expect(sc, where).toBeLessThanOrEqual(1.5 + 1e-9);
          if (sc < 1) shrunk++;
          const fits = built.widthMM <= boxW + 0.05 && built.heightMM <= boxH + 0.05;
          if (!fits) {
            atLimit++;
            expect(sc, `${where} overflows, so it must sit exactly at the limit`).toBeCloseTo(0.75, 9);
          }
        }
      }
    }
    // Not vacuous: some placements are smaller than some designs, and the
    // limit is reached (Shamrock on the hat front: 58.95 mm tall in a 57.2 box).
    expect(shrunk).toBeGreaterThan(0);
    expect(atLimit).toBeGreaterThan(0);
  });

  test("a design that fits a placement is inserted as it always was (no limit, no shrink)", async () => {
    const patches = await Promise.all(designs.map((d) => pack.loadStarterPatch(d, packFetch())));
    const garment = EMB.getGarment("full_back"); // 12 in: everything fits
    for (const patch of patches) {
      const built = generate.generateElement({ ...project.defaultDesignElement("e1"), ...patch }, garment, {});
      expect(built._debug.scale, patch.name).toBe(1);
    }
  });
});
