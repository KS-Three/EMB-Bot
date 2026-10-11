// Every failure a customer can hit, forced, with the sentence they would read.
//
// The assertions are on WORDS a person acts on ("running", "try again",
// "crop") and, as much, on the raw text that must NOT appear: "Failed to
// fetch", "[object Object]", a traceback, a bare status code. The component
// wiring is proved end to end in e2e/friendly-errors.spec.js; this file pins
// the mapping and the client's tagging that feeds it.
import { test, expect, describe, vi } from "vitest";
import { friendlyError, isPlainSentence, OFFLINE_DIGITIZE, TIMEOUT_DIGITIZE, FAILED_DIGITIZE, TOO_LARGE_DIGITIZE, BAD_UPLOAD } from "./friendlyError.js";

const RAW = /failed to fetch|networkerror|\[object|traceback|aborted due to|undefined|answered \d+/i;
const timeoutErr = () => Object.assign(new Error("The operation was aborted due to timeout"), { name: "TimeoutError" });

describe("digitize", () => {
  test("service not running", () => {
    for (const msg of ["Failed to fetch", "NetworkError when attempting to fetch resource.", "Load failed", "fetch failed"]) {
      const out = friendlyError(new TypeError(msg), "digitize");
      expect(out).toBe(OFFLINE_DIGITIZE);
      expect(out).toMatch(/running/i);
      expect(out).toMatch(/Auto Digitize Image again/);
      expect(out).not.toMatch(RAW);
    }
  });
  test("timed out, by our own poll limit or the browser's", () => {
    expect(friendlyError(Object.assign(new Error("Digitizing timed out."), { kind: "timeout" }), "digitize")).toBe(TIMEOUT_DIGITIZE);
    expect(friendlyError(timeoutErr(), "digitize")).toBe(TIMEOUT_DIGITIZE);
    expect(TIMEOUT_DIGITIZE).toMatch(/simpler|tighter/);
  });
  test("a job that errored with a traceback is replaced, one with a sentence is kept", () => {
    expect(friendlyError(new Error("Traceback (most recent call last):\n  File \"x.py\", line 3"), "digitize")).toBe(FAILED_DIGITIZE);
    expect(friendlyError(new Error("ValueError: bad shape"), "digitize")).toBe(FAILED_DIGITIZE);
    expect(friendlyError(new Error("unknown thread brand 'nope'. See /health for the list."), "digitize"))
      .toMatch(/unknown thread brand/);
    expect(FAILED_DIGITIZE).toMatch(/try again/i);
  });
  test("a bare HTTP status is not shown to the customer", () => {
    const e = Object.assign(new Error("The digitizer service answered 500."), { status: 500 });
    expect(friendlyError(e, "digitize")).toBe(FAILED_DIGITIZE);
    const big = Object.assign(new Error("The digitizer service answered 413."), { status: 413 });
    expect(friendlyError(big, "digitize")).toBe(TOO_LARGE_DIGITIZE);
  });
  test("non-Error throws do not render as [object Object]", () => {
    expect(friendlyError({ detail: [{ msg: "x" }] }, "digitize")).toBe(FAILED_DIGITIZE);
    expect(friendlyError(undefined, "digitize")).toBe(FAILED_DIGITIZE);
    expect(friendlyError("boom", "digitize")).toBe(FAILED_DIGITIZE);
  });
});

describe("upload", () => {
  test("keeps the format list when it is already a sentence, else supplies it", () => {
    expect(friendlyError(new Error(BAD_UPLOAD), "upload")).toBe(BAD_UPLOAD);
    expect(friendlyError(new DOMException("The source image could not be decoded.", "InvalidStateError"), "upload"))
      .toMatch(/could not be decoded|Couldn’t open/);
    expect(friendlyError(new TypeError("x is not a function"), "upload")).toBe(BAD_UPLOAD);
    expect(BAD_UPLOAD).toMatch(/PNG, JPEG/);
  });
});

describe("export", () => {
  test("service down names the file and the fix", () => {
    const out = friendlyError(new TypeError("Failed to fetch"), "export", "JEF file");
    expect(out).toMatch(/JEF file/);
    expect(out).toMatch(/isn’t answering/);
    expect(out).toMatch(/Start it/);
    expect(out).not.toMatch(RAW);
  });
  test("timeout and unknown failures say what to try", () => {
    expect(friendlyError(timeoutErr(), "export", "DST file")).toMatch(/too long.*Try again/);
    const out = friendlyError(new Error("canvas.toBlob returned null"), "export", "PNG picture");
    expect(out).toMatch(/Couldn’t make the PNG picture/);
    expect(out).toMatch(/Try again/);
  });
  test("a plain sentence from the engine passes through", () => {
    expect(friendlyError(new Error("Nothing to stitch yet — add some content first."), "export", "DST file"))
      .toBe("Nothing to stitch yet — add some content first.");
  });
});

test("isPlainSentence rejects technical text", () => {
  for (const bad of ["", "x", "{\"detail\":1}", "[object Object]", "TypeError: x is not a function", "at foo (bar.js:1:2)", "a\nb c d"]) {
    expect(isPlainSentence(bad), bad).toBe(false);
  }
  expect(isPlainSentence("That image is too heavy to save with the design.")).toBe(true);
});

describe("the client tags what the Studio needs", () => {
  const stub = () => { vi.stubGlobal("localStorage", { getItem: () => null, setItem() {} }); };
  test("startDigitize: connection refused reaches the panel as the service-offline sentence", async () => {
    stub();
    const { startDigitize } = await import("./digitizer.js");
    const err = await startDigitize("AAAA", {}, async () => { throw new TypeError("Failed to fetch"); }).catch((e) => e);
    expect(friendlyError(err, "digitize")).toBe(OFFLINE_DIGITIZE);
  });
  test("startDigitize: a FastAPI 422 (detail is a list) is not shown as [object Object]", async () => {
    stub();
    const { startDigitize } = await import("./digitizer.js");
    const fetchFn = async () => ({ ok: false, status: 422, json: async () => ({ detail: [{ loc: ["body"], msg: "field required" }] }) });
    const err = await startDigitize("AAAA", {}, fetchFn).catch((e) => e);
    expect(err.status).toBe(422);
    expect(friendlyError(err, "digitize")).toBe(FAILED_DIGITIZE);
  });
  test("startDigitize: 413 from the service", async () => {
    stub();
    const { startDigitize } = await import("./digitizer.js");
    const fetchFn = async () => ({ ok: false, status: 413, json: async () => { throw new Error("no body"); } });
    const err = await startDigitize("AAAA", {}, fetchFn).catch((e) => e);
    expect(friendlyError(err, "digitize")).toBe(TOO_LARGE_DIGITIZE);
  });
  test("pollJob: the service dying mid-run, a stuck job and a failed job", async () => {
    stub();
    const { pollJob } = await import("./digitizer.js");
    const dead = await pollJob("j", { fetchFn: async () => { throw new TypeError("Failed to fetch"); } }).catch((e) => e);
    expect(friendlyError(dead, "digitize")).toBe(OFFLINE_DIGITIZE);

    const running = async () => ({ ok: true, json: async () => ({ state: "running" }) });
    const stuck = await pollJob("j", { fetchFn: running, intervalMs: 1, timeoutMs: 5 }).catch((e) => e);
    expect(friendlyError(stuck, "digitize")).toBe(TIMEOUT_DIGITIZE);

    const failed = async () => ({ ok: true, json: async () => ({ state: "error", error: "Traceback (most recent call last): boom" }) });
    const bad = await pollJob("j", { fetchFn: failed }).catch((e) => e);
    expect(friendlyError(bad, "digitize")).toBe(FAILED_DIGITIZE);
  });
  test("exportViaService: a 10 s timeout reads as too long", async () => {
    stub();
    const { exportViaService } = await import("./digitizer.js");
    const err = await exportViaService({}, "jef", "x", async () => { throw timeoutErr(); }).catch((e) => e);
    expect(friendlyError(err, "export", "JEF file")).toMatch(/too long/);
  });
});
