// Outline fonts (lib/outlineFonts.js): the key convention, the service rows,
// the request a text element sends and the staleness it implies.
import { beforeAll, describe, expect, test, vi } from "vitest";
import { createRequire } from "node:module";

vi.mock("./threads.js", () => ({ loadPreferredPaletteId: () => "studio" }));

let of;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/sewtime.js");
  require("../../../src/garments.js");
  require("../../../src/fabrics.js");
  globalThis.EMB.buildLetteringDesign = globalThis.EMB.buildLetteringDesign || (() => { throw new Error("unused"); });
  of = await import("./outlineFonts.js");
});

const ROW = {
  key: "montserrat-bold", name: "Montserrat Bold", family: "Montserrat", group: "Sans",
  style: "Bold", weight: 700, variable: true, licenseId: "OFL-1.1", kind: "outline",
  source: "https://github.com/google/fonts/tree/abc/ofl/montserrat",
  coverage: [[65, 90], 97],
  file: "/fonts/outline/montserrat-bold/file", license: "/fonts/outline/montserrat-bold/license",
};

describe("keys", () => {
  test("outline keys carry the prefix and round-trip to the service key", () => {
    expect(of.isOutlineKey("outline:lobster")).toBe(true);
    expect(of.isOutlineKey("medium_font")).toBe(false);
    expect(of.isOutlineKey(null)).toBe(false);
    expect(of.serviceKeyOf("outline:lobster")).toBe("lobster");
    expect(of.serviceKeyOf("medium_font")).toBe("medium_font");
    expect(of.outlineKeyOf("lobster")).toBe("outline:lobster");
    expect(of.previewFamily("outline:eb-garamond")).toBe("embot-outline-eb-garamond");
  });
});

describe("rows", () => {
  test("a service row becomes a manifest-shaped verified row in the Outline group", () => {
    const row = of.outlineFontRow(ROW, "http://127.0.0.1:8721/");
    expect(row.key).toBe("outline:montserrat-bold");
    expect(row.tier).toBe("verified");
    expect(row.group).toBe(of.OUTLINE_GROUP);
    expect(row.kind).toBe("outline");
    expect(row.licenseId).toBe("OFL-1.1");
    expect(row.fileUrl).toBe("http://127.0.0.1:8721/fonts/outline/montserrat-bold/file");
    expect(row.licenseUrl).toBe("http://127.0.0.1:8721/fonts/outline/montserrat-bold/license");
    expect(row.attribution).toMatch(/SIL Open Font License/);
    expect(row.attribution).toMatch(/unmodified/i);
    expect(row.sizeMm).toBeNull();
  });

  test("fetchOutlineFonts maps rows and keys coverage by the outline key", async () => {
    const fetchFn = vi.fn(async (url) => {
      expect(url).toBe("http://svc/fonts/outline");
      return { ok: true, json: async () => ({ version: 1, fonts: [ROW, { key: "lobster", name: "Lobster" }] }) };
    });
    const o = await of.fetchOutlineFonts(fetchFn, "http://svc");
    expect(o.rows.map((r) => r.key)).toEqual(["outline:montserrat-bold", "outline:lobster"]);
    expect(o.coverage).toEqual({ "outline:montserrat-bold": [[65, 90], 97] });
  });

  test("a failed listing throws so the loader can decide", async () => {
    await expect(of.fetchOutlineFonts(async () => ({ ok: false, status: 404 }), "http://svc"))
      .rejects.toThrow(/404/);
  });
});

describe("request", () => {
  const project = { garmentId: "left_chest", fabricRgb: [10, 20, 30] };
  const el = {
    id: "e1", type: "text", fontKey: "outline:lobster", text: "Fremont  \n", colorRgb: [200, 0, 0],
    sizeMm: 76.25, letterSpacingMm: 0, align: "center",
  };

  test("carries exactly what the service reads, canonically", () => {
    const req = of.outlineRequest(el, project);
    expect(req).toEqual({
      font: "lobster", text: "Fremont", width_mm: 76.3, thread_rgb: [200, 0, 0],
      config: { garment_id: "left_chest", garment_rgb: [10, 20, 30] },
    });
  });

  test("letter spacing and a non-centre justification ride only when set", () => {
    const req = of.outlineRequest({ ...el, letterSpacingMm: 1.5, align: "left" }, project);
    expect(req.letter_spacing_mm).toBe(1.5);
    expect(req.align).toBe("left");
  });

  test("no typed width falls back to the placement box, clamped to the field's range", () => {
    const req = of.outlineRequest({ ...el, sizeMm: null }, project);
    expect(req.width_mm).toBeGreaterThanOrEqual(10);
    expect(req.width_mm).toBeLessThanOrEqual(400);
    const tiny = of.outlineRequest({ ...el, sizeMm: 2 }, project);
    expect(tiny.width_mm).toBe(10);
  });

  test("the key moves with text, font, width, colour, garment — and not with a no-op edit", () => {
    const k = (e, p = project) => of.outlineRequestKey(of.outlineRequest(e, p));
    const base = k(el);
    expect(k({ ...el, text: "Fremont" })).toBe(base);            // trailing whitespace trimmed
    expect(k({ ...el, letterSpacingMm: 0 })).toBe(base);
    expect(k({ ...el, text: "Fremonts" })).not.toBe(base);
    expect(k({ ...el, fontKey: "outline:anton" })).not.toBe(base);
    expect(k({ ...el, sizeMm: 60 })).not.toBe(base);
    expect(k({ ...el, colorRgb: [0, 0, 0] })).not.toBe(base);
    expect(k(el, { ...project, garmentId: "hat_front" })).not.toBe(base);
  });

  test("outlineStale: typed-but-never-digitized is behind; a result is behind when its key moved", () => {
    // text with no result sews nothing and would be left out of the file silently
    expect(of.outlineStale({ ...el, result: null }, project)).toBe(true);
    // empty text: nothing to sew, nothing to press — never locks Download
    expect(of.outlineStale({ ...el, text: "  ", result: null }, project)).toBe(false);
    const applied = of.outlineRequestKey(of.outlineRequest(el, project));
    const digitized = { ...el, result: { stitches: [] }, appliedConfig: applied };
    expect(of.outlineStale(digitized, project)).toBe(false);
    expect(of.outlineStale({ ...digitized, text: "Other" }, project)).toBe(true);
    expect(of.outlineStale({ ...digitized, text: "" }, project)).toBe(false);
    expect(of.outlineStale({ ...digitized, fontKey: "medium_font" }, project)).toBe(false);
    // a legacy result with no stamp reads as current unless a baseline is given
    expect(of.outlineStale({ ...digitized, appliedConfig: null }, project)).toBe(false);
    expect(of.outlineStale({ ...digitized, appliedConfig: null, text: "Other" }, project, { baselineKey: applied })).toBe(true);
  });

  test("outlineTargetWidthMm: the element's width at 0/180°, the design's own size when rotated", () => {
    expect(of.outlineTargetWidthMm({ sizeMm: 76, rotationDeg: 0 })).toBe(76);
    expect(of.outlineTargetWidthMm({ sizeMm: 76, rotationDeg: 180 })).toBe(76);
    expect(of.outlineTargetWidthMm({ sizeMm: 76, rotationDeg: -180 })).toBe(76);
    expect(of.outlineTargetWidthMm({ sizeMm: 76, rotationDeg: 90 })).toBeUndefined();
    expect(of.outlineTargetWidthMm({ sizeMm: 76, rotationDeg: 37 })).toBeUndefined();
    expect(of.outlineTargetWidthMm({ sizeMm: null, rotationDeg: 0 })).toBeUndefined();
  });
});

describe("run", () => {
  test("startLettering posts JSON to /lettering and surfaces the service's detail on error", async () => {
    const calls = [];
    const ok = vi.fn(async (url, opts) => {
      calls.push([url, opts]);
      return { ok: true, json: async () => ({ job_id: "j1", state: "queued", cached: false }) };
    });
    const sub = await of.startLettering({ font: "lobster", text: "Hi", width_mm: 40, config: {} }, ok);
    expect(sub.job_id).toBe("j1");
    expect(calls[0][0]).toMatch(/\/lettering$/);
    expect(calls[0][1].method).toBe("POST");
    expect(JSON.parse(calls[0][1].body).font).toBe("lobster");
    const bad = async () => ({ ok: false, status: 400, json: async () => ({ detail: "unknown outline font 'x'" }) });
    await expect(of.startLettering({ font: "x" }, bad)).rejects.toThrow(/unknown outline font/);
  });

  test("digitizeLettering submits then polls the job to done", async () => {
    let polls = 0;
    const fetchFn = vi.fn(async (url) => {
      if (/\/lettering$/.test(url)) return { ok: true, json: async () => ({ job_id: "j2", state: "queued" }) };
      polls += 1;
      return { ok: true, json: async () => (polls < 2
        ? { job_id: "j2", state: "running" }
        : { job_id: "j2", state: "done", design: { stitches: [{ x: 0, y: 0, type: "stitch" }] }, lettering: { letters: 2 } }) };
    });
    const job = await of.digitizeLettering({ font: "lobster", text: "Hi", width_mm: 40, config: {} }, { fetchFn, intervalMs: 0 });
    expect(job.state).toBe("done");
    expect(job.lettering.letters).toBe(2);
  });
});
