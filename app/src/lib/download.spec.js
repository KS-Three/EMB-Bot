// @vitest-environment jsdom
import { test, expect, vi, beforeEach, afterEach } from "vitest";
import { triggerDownload } from "./download.js";

let blobs, anchors;

beforeEach(() => {
  vi.useFakeTimers();
  blobs = [];
  anchors = [];
  URL.createObjectURL = vi.fn((b) => { blobs.push(b); return `blob:fake/${blobs.length}`; });
  URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () { anchors.push(this); });
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

const FORMATS = [
  ["dst", "application/octet-stream"],
  ["pes", "application/octet-stream"],
  ["exp", "application/octet-stream"],
  ["svg", "image/svg+xml"],
  ["png", "image/png"],
  ["json", "application/json"],
];

test.each(FORMATS)("%s: Uint8Array gets a blob of the given mime, bytes intact, and the given filename", async (ext, mime) => {
  triggerDownload({ bytes: new Uint8Array([1, 2, 3]), mime, filename: `design.${ext}` });
  expect(blobs).toHaveLength(1);
  expect(blobs[0].type).toBe(mime);
  expect(blobs[0].size).toBe(3);
  expect(anchors).toHaveLength(1);
  expect(anchors[0].download).toBe(`design.${ext}`);
  expect(anchors[0].href).toBe("blob:fake/1");
});

test("string bytes become a blob of the given type", async () => {
  triggerDownload({ bytes: "<svg/>", mime: "image/svg+xml", filename: "a.svg" });
  expect(blobs[0].type).toBe("image/svg+xml");
  expect(await blobs[0].text()).toBe("<svg/>");
});

test("an existing Blob is passed through untouched (its own type wins over out.mime)", () => {
  const blob = new Blob(["x"], { type: "image/png" });
  triggerDownload({ bytes: blob, mime: "application/octet-stream", filename: "a.png" });
  expect(blobs[0]).toBe(blob);
  expect(blobs[0].type).toBe("image/png");
});

test("the object URL is revoked after 1s, not before", () => {
  triggerDownload({ bytes: new Uint8Array([1]), mime: "application/octet-stream", filename: "a.dst" });
  expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  vi.advanceTimersByTime(999);
  expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  vi.advanceTimersByTime(1);
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:fake/1");
});
