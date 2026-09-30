import { test, expect } from "vitest";
import {
  CARD_FORMATS, downloadCalibrationCard, readCalibrationPhoto, fetchCalibrationInfo,
  readingRows, fmtMm, fmtPct,
} from "./calibration.js";

function res(body, { ok = true, status = 200, headers = {} } = {}) {
  const h = new Map(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v]));
  return {
    ok, status,
    headers: { get: (k) => h.get(k.toLowerCase()) || null },
    json: async () => body,
    blob: async () => new Blob([body instanceof Uint8Array ? body : new Uint8Array([1])]),
  };
}

test("the card is offered in the Download step's six machine formats, all from the service", () => {
  expect(CARD_FORMATS).toEqual(["dst", "pes", "exp", "jef", "vp3", "xxx"]);
});

test("downloadCalibrationCard asks for the format and returns a triggerDownload-shaped file with its size", async () => {
  const calls = [];
  const fetchFn = async (url, opts) => {
    calls.push({ url, opts });
    return res(new Uint8Array([1, 2, 3]), {
      headers: {
        "Content-Disposition": 'attachment; filename="EMBBOT_CALIBRATION_CARD_V2.pes"',
        "Content-Type": "application/octet-stream",
        "X-Design-Width-Mm": "82.00", "X-Design-Height-Mm": "103.00",
      },
    });
  };
  const out = await downloadCalibrationCard("pes", fetchFn);
  expect(calls[0].url).toMatch(/\/calibration\/card\?format=pes$/);
  expect(out.filename).toBe("EMBBOT_CALIBRATION_CARD_V2.pes");
  expect(out.widthMm).toBe(82);
  expect(out.heightMm).toBe(103);
  expect(out.bytes).toBeInstanceOf(Blob);
  await expect(downloadCalibrationCard("bmp", fetchFn)).rejects.toThrow(/Unknown card format/);
});

test("a service error surfaces its own detail sentence", async () => {
  const fetchFn = async () => res({ detail: "Could not find the card in the photo." }, { ok: false, status: 422 });
  await expect(readCalibrationPhoto(new Blob([1]), "left_chest", fetchFn)).rejects.toThrow(/Could not find the card/);
  const fetch500 = async () => ({ ok: false, status: 500, json: async () => { throw new Error("x"); } });
  await expect(fetchCalibrationInfo(fetch500)).rejects.toThrow(/answered 500/);
});

test("readCalibrationPhoto posts the photo and the garment as multipart and returns the reading", async () => {
  let got;
  const fetchFn = async (url, opts) => {
    got = { url, opts };
    return res({ profile: { pull_comp_delta_mm: -0.05 }, notes: [] });
  };
  const photo = new Blob([1, 2], { type: "image/jpeg" });
  const reading = await readCalibrationPhoto(photo, "left_chest", fetchFn);
  expect(got.url).toMatch(/\/calibration\/read$/);
  expect(got.opts.method).toBe("POST");
  expect(got.opts.body).toBeInstanceOf(FormData);
  expect(got.opts.body.get("garment_id")).toBe("left_chest");
  expect(got.opts.body.get("photo")).toBeTruthy();
  expect(reading.profile.pull_comp_delta_mm).toBe(-0.05);
});

test("readingRows keeps the satin bars, fill squares and seams and drops the lock bars and words", () => {
  const rows = readingRows({
    features: [
      { name: "lock-A", role: "bar", d_height_mm: 0.01, d_width_mm: 0 },
      { name: "satin-4mm", role: "bar", d_height_mm: -0.31, d_width_mm: 0.4 },
      { name: "fill-D-0.15", role: "square", d_coverage: -0.12, d_width_mm: -0.2 },
      { name: "word-0", role: "word", d_coverage: 0 },
      { name: "seam-A-0", role: "seam", d_coverage: 0 },
    ],
    seam_gap_delta_mm: { "0": 0.45, "0.25": 0 },
  });
  expect(rows.map((r) => r.kind)).toEqual(["satin", "fill", "seam", "seam"]);
  expect(rows[0]).toMatchObject({ name: "4mm column", pullIn: 0.31, push: 0.4 });
  expect(rows[1]).toMatchObject({ name: "D-0.15 fill", showThrough: 0.12, pullIn: 0.2 });
  expect(rows[2]).toMatchObject({ name: "0 mm underlap seam", gap: 0.45 });
  expect(readingRows(null)).toEqual([]);
});

test("formatting: signed millimetres, whole percents, a dash for nothing", () => {
  expect(fmtMm(0.31)).toBe("+0.31 mm");
  expect(fmtMm(-0.05)).toBe("-0.05 mm");
  expect(fmtMm(null)).toBe("—");
  expect(fmtPct(0.124)).toBe("12%");
  expect(fmtPct(undefined)).toBe("—");
});
