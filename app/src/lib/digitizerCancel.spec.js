// The customer's Cancel on a running digitize (2026-11-12): lib/digitizer.js
// `cancelJob`, and the `stop` signal pollJob / digitize take.
//
// Two things here look alike and are not: `isCancelled` is a torn-down panel
// (leave the service's job running, the next panel joins it), `stop` is the
// customer saying no (tell the service, land nothing).
import { afterEach, describe, expect, test, vi } from "vitest";
import { cancelJob, digitize, pollJob } from "./digitizer.js";

const BASE = "http://127.0.0.1:8721";
const ok = (body) => ({ ok: true, status: 200, json: async () => body });

// A fake service: records every request, answers polls from `poll()`.
function service({ poll = () => ({ state: "running", job_id: "j1" }), cancel } = {}) {
  const calls = [];
  const fetchFn = async (url, init = {}) => {
    const path = String(url).replace(BASE, "");
    const method = init.method || "GET";
    calls.push(method + " " + path);
    if (method === "POST" && path === "/digitize") return { ok: true, status: 202, json: async () => ({ job_id: "j1", state: "queued", cached: false }) };
    if (method === "POST" && path.endsWith("/cancel")) {
      return cancel ? cancel(init) : ok({ job_id: "j1", state: "cancelled" });
    }
    return ok(poll());
  };
  const count = (line) => calls.filter((c) => c === line).length;
  return { fetchFn, calls, count };
}

afterEach(() => vi.useRealTimers());

describe("cancelJob", () => {
  test("POSTs /jobs/{id}/cancel and resolves true when the service took it", async () => {
    const { fetchFn, calls } = service();
    expect(await cancelJob("j1", fetchFn)).toBe(true);
    expect(calls).toEqual(["POST /jobs/j1/cancel"]);
  });

  test("resolves false, and never throws, when the service is older than the route", async () => {
    const { fetchFn } = service({ cancel: () => ({ ok: false, status: 404, json: async () => ({ detail: "Not Found" }) }) });
    expect(await cancelJob("j1", fetchFn)).toBe(false);
  });

  test("resolves false, and never throws, when the service cannot be reached", async () => {
    const { fetchFn } = service({ cancel: () => { throw new TypeError("Failed to fetch"); } });
    expect(await cancelJob("j1", fetchFn)).toBe(false);
  });
});

describe("pollJob with a stop signal", () => {
  test("a stop between polls ends the wait at once, tells the service once, and resolves null", async () => {
    vi.useFakeTimers();
    const { fetchFn, count } = service();
    const stop = new AbortController();
    let out = "pending";
    const p = pollJob("j1", { fetchFn, intervalMs: 60000, stop: stop.signal }).then((j) => { out = j; });
    await vi.advanceTimersByTimeAsync(10);          // first poll read "running"; now waiting a minute
    expect(count("GET /jobs/j1")).toBe(1);
    stop.abort();
    await vi.advanceTimersByTimeAsync(0);            // no minute passes
    await p;
    expect(out).toBeNull();
    expect(count("POST /jobs/j1/cancel")).toBe(1);
    expect(count("GET /jobs/j1")).toBe(1);           // and it never polled again
    expect(vi.getTimerCount()).toBe(0);              // nothing left ticking
  });

  test("resolves only after the service has been told, so a re-run cannot overtake the cancel", async () => {
    let answerCancel;
    const { fetchFn } = service({ cancel: () => new Promise((res) => { answerCancel = () => res(ok({ state: "cancelled" })); }) });
    const stop = new AbortController();
    stop.abort();
    let settled = false;
    const p = pollJob("j1", { fetchFn, intervalMs: 0, stop: stop.signal }).then((j) => { settled = true; return j; });
    await new Promise((r) => setTimeout(r, 5));
    expect(settled).toBe(false);
    answerCancel();
    expect(await p).toBeNull();
  });

  test("a stop that lands while a poll is in flight wins over the 'done' that poll reads", async () => {
    const stop = new AbortController();
    const { fetchFn, count } = service({
      poll: () => {
        stop.abort();                                // pressed while this poll was out
        return { state: "done", job_id: "j1", design: { stitches: [] } };
      },
    });
    expect(await pollJob("j1", { fetchFn, intervalMs: 0, stop: stop.signal })).toBeNull();
    expect(count("POST /jobs/j1/cancel")).toBe(1);
  });

  test("still resolves null when the service could not be told", async () => {
    const { fetchFn } = service({ cancel: () => { throw new TypeError("Failed to fetch"); } });
    const stop = new AbortController();
    stop.abort();
    expect(await pollJob("j1", { fetchFn, intervalMs: 0, stop: stop.signal })).toBeNull();
  });

  test("a job the service reports cancelled resolves null: not an error, and no second cancel", async () => {
    const { fetchFn, count } = service({ poll: () => ({ state: "cancelled", job_id: "j1" }) });
    const seen = [];
    expect(await pollJob("j1", { fetchFn, intervalMs: 0, onState: (s) => seen.push(s) })).toBeNull();
    expect(seen).toEqual([]);
    expect(count("POST /jobs/j1/cancel")).toBe(0);
  });

  test("a torn-down panel (isCancelled) does NOT cancel the service's job", async () => {
    const { fetchFn, calls } = service();
    expect(await pollJob("j1", { fetchFn, intervalMs: 0, isCancelled: () => true })).toBeNull();
    expect(calls).toEqual([]);                       // left running for the next panel to join
  });

  test("without a stop signal nothing changes: queued -> running -> done still lands", async () => {
    const states = [{ state: "queued" }, { state: "running" }, { state: "done", design: { stitches: [] } }];
    let i = 0;
    const { fetchFn, count } = service({ poll: () => states[Math.min(i++, states.length - 1)] });
    const stop = new AbortController();              // offered, never pressed
    const job = await pollJob("j1", { fetchFn, intervalMs: 0, stop: stop.signal });
    expect(job.state).toBe("done");
    expect(count("POST /jobs/j1/cancel")).toBe(0);
  });
});

describe("digitize with a stop signal", () => {
  test("a Cancel pressed during the upload lets the submit land, then cancels that job without polling it", async () => {
    const { fetchFn, calls } = service();
    const stop = new AbortController();
    stop.abort();                                    // pressed before the service answered the upload
    expect(await digitize("AAAA", {}, { fetchFn, intervalMs: 0, stop: stop.signal })).toBeNull();
    expect(calls).toEqual(["POST /digitize", "POST /jobs/j1/cancel"]);
  });

  test("cancel, then digitize again: the second run submits afresh and lands", async () => {
    let cancelled = false;
    const { fetchFn, calls } = service({
      poll: () => (cancelled ? { state: "done", job_id: "j1", design: { stitches: [] } } : { state: "running", job_id: "j1" }),
    });
    const stop = new AbortController();
    const first = digitize("AAAA", {}, { fetchFn, intervalMs: 1, stop: stop.signal });
    await new Promise((r) => setTimeout(r, 10));
    stop.abort();
    expect(await first).toBeNull();
    cancelled = true;

    const second = await digitize("AAAA", {}, { fetchFn, intervalMs: 1, stop: new AbortController().signal });
    expect(second.state).toBe("done");
    // The cancel reached the service before the second upload was sent.
    expect(calls.indexOf("POST /jobs/j1/cancel")).toBeLessThan(calls.lastIndexOf("POST /digitize"));
    expect(calls.filter((c) => c === "POST /digitize")).toHaveLength(2);
  });
});
