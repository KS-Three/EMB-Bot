import { test, expect } from "vitest";

// TDD for the health-wait core of scripts/ensure-digitizer.mjs. The spawn
// side is OS glue verified live; this is the decision logic: probe until
// healthy or deadline, injected fetch + clock, no real network or timers.

test("waitHealthy resolves true as soon as a probe returns ok health", async () => {
  const { waitHealthy } = await import("../../scripts/ensure-digitizer.mjs");
  let calls = 0;
  const fetchFn = async () => {
    calls++;
    if (calls < 3) throw new Error("ECONNREFUSED");
    return { ok: true, json: async () => ({ status: "ok" }) };
  };
  const sleeps = [];
  const ok = await waitHealthy({ fetchFn, sleepFn: async (ms) => sleeps.push(ms), attempts: 10 });
  expect(ok).toBe(true);
  expect(calls).toBe(3);
  expect(sleeps.length).toBe(2); // slept only between failed probes
});

test("waitHealthy gives up false after the attempt budget, never throws", async () => {
  const { waitHealthy } = await import("../../scripts/ensure-digitizer.mjs");
  let calls = 0;
  const fetchFn = async () => { calls++; throw new Error("ECONNREFUSED"); };
  const ok = await waitHealthy({ fetchFn, sleepFn: async () => {}, attempts: 4 });
  expect(ok).toBe(false);
  expect(calls).toBe(4);
});

test("waitHealthy treats non-ok HTTP and bad JSON as not-yet-healthy", async () => {
  const { waitHealthy } = await import("../../scripts/ensure-digitizer.mjs");
  const responses = [
    { ok: false, json: async () => ({}) },
    { ok: true, json: async () => { throw new Error("bad json"); } },
    { ok: true, json: async () => ({ status: "ok" }) },
  ];
  let i = 0;
  const ok = await waitHealthy({ fetchFn: async () => responses[i++], sleepFn: async () => {}, attempts: 5 });
  expect(ok).toBe(true);
  expect(i).toBe(3);
});
