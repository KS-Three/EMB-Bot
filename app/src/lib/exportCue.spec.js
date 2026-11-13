// The "Saved ..." line's verification tail (lib/exportCue.js): what it may say
// from a read-back result, and what it must NOT say.
import { expect, test, vi } from "vitest";
import { singleCue, zipCue } from "./exportCue.js";
vi.mock("./preview.js", () => ({ renderRealistic: () => {} }));
vi.mock("./digitizer.js", () => ({ exportViaService: async () => ({}) }));
vi.mock("./emb.js", () => ({ EMB: {} }));
import { ZIP_STITCH_FORMATS } from "./exportZip.js";

const ok = (extra = {}) => ({ verified: true, stitches: 2459, trims: 3, colors: 2, ...extra });
const all = (over = {}) => ZIP_STITCH_FORMATS.map((format) => ({ format, readback: format in over ? over[format] : ok() }));

test("a verified file says so with its real stitch and colour counts", () => {
  expect(singleCue(ok())).toBe(" - re-read and verified: 2,459 stitches, 2 colour changes");
  expect(singleCue(ok({ stitches: 1, colors: 1 }))).toBe(" - re-read and verified: 1 stitch, 1 colour change");
});

test("a verified file with no counts (service headers carried none) still says verified, no invented numbers", () => {
  expect(singleCue({ verified: true })).toBe(" - re-read and verified");
});

test("a read that skipped checks says how many, never a bare 'verified'", () => {
  expect(singleCue(ok({ skipped: ["trim_order", "color_order", "bounding_box", "stitch_positions"] }))).toBe(
    " - re-read and verified: 2,459 stitches, 2 colour changes (4 checks this format cannot give back skipped)",
  );
  expect(singleCue(ok({ skipped: ["longest_stitch"] }))).toMatch(/\(1 check this format cannot give back skipped\)/);
});

test("no read-back, or one that says unverified, is 'not re-read' and never 'verified'", () => {
  for (const rb of [undefined, null, {}, { verified: false }, { verified: "true" }]) {
    expect(singleCue(rb)).toBe(" - not re-read");
  }
  expect(singleCue({ verified: false, reason: "SVG is a picture of the design, not a stitch file" })).toBe(
    " - not re-read (SVG is a picture of the design, not a stitch file)",
  );
});

test("a zip whose every stitch file was fully re-read says so with the real count", () => {
  expect(zipCue(all({ svg: ok() }))).toBe(" - 7 stitch files re-read and verified");
});

test("SVG (never re-read) is named, and the count excludes it", () => {
  expect(zipCue(all({ svg: { verified: false, reason: "not a stitch file" } }))).toBe(
    " - 6 of 7 stitch files re-read and verified (SVG not re-read)",
  );
});

test("a format with skipped checks counts as read but is named; one with no result is not counted", () => {
  const items = all({
    svg: { verified: false },
    xxx: ok({ skipped: ["trim_order"] }),
    vp3: ok({ skipped: ["longest_stitch"] }),
    jef: undefined,
  });
  expect(zipCue(items)).toBe(" - 5 of 7 stitch files re-read and verified (JEF, SVG not re-read; XXX, VP3 with some checks skipped)");
});

test("nothing to say when the archive held no stitch files", () => {
  expect(zipCue([])).toBe("");
  expect(zipCue(undefined)).toBe("");
});
