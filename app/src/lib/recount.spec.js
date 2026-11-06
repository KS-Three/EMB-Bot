// The recount's debounce / cancel / stale rules (lib/recount.js), without a DOM.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { createRecounter, recountText, RECOUNT_DEBOUNCE_MS } from "./recount.js";

const ANSWER = (shape_count, color_count) => ({ shape_count, color_count, size_mm: [30, 20] });

function setup() {
  const got = [];
  const recounter = createRecounter({ onResult: (key, counts) => got.push([key, counts]), cache: new Map() });
  // A run() whose promise the test settles by hand, remembering its signal.
  const asks = [];
  const run = () => (signal) => new Promise((resolve, reject) => {
    asks.push({ signal, resolve, reject });
  });
  return { recounter, got, asks, run };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("recountText -- counts and the size, nothing else", () => {
  test("plural, singular, and the size", () => {
    expect(recountText({ shapes: 22, colors: 2 }, 36.7)).toBe("22 shapes, 2 colors at 36.7 mm");
    expect(recountText({ shapes: 1, colors: 1 }, 113.5)).toBe("1 shape, 1 color at 113.5 mm");
    expect(recountText({ shapes: 93, colors: 2 }, 100)).toBe("93 shapes, 2 colors at 100 mm");
  });
  test("no counts, no text; no usable width, no 'at'", () => {
    expect(recountText(null, 80)).toBe("");
    expect(recountText({ shapes: 3, colors: 2 }, undefined)).toBe("3 shapes, 2 colors");
  });
});

describe("createRecounter", () => {
  test("waits out the debounce, then asks once and delivers the counts", async () => {
    const { recounter, got, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS - 1);
    expect(asks).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(1);
    expect(asks).toHaveLength(1);
    asks[0].resolve(ANSWER(22, 2));
    await vi.advanceTimersByTimeAsync(0);
    expect(got).toEqual([["a", { shapes: 22, colors: 2, sizeMm: [30, 20] }]]);
  });

  test("a burst of sizes asks once, for the last one", async () => {
    const { recounter, asks, run } = setup();
    for (const key of ["w=30", "w=31", "w=313", "w=31.3"]) {
      recounter.ask(key, run());
      await vi.advanceTimersByTimeAsync(100);
    }
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    expect(asks).toHaveLength(1);
  });

  test("the same key arriving again leaves the scheduled ask alone", async () => {
    const { recounter, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(300);
    recounter.ask("a", run());
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS - 300);
    expect(asks).toHaveLength(1);
  });

  test("a newer size aborts the in-flight request and drops its late answer", async () => {
    const { recounter, got, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    expect(asks[0].signal.aborted).toBe(false);
    recounter.ask("b", run());
    expect(asks[0].signal.aborted).toBe(true);
    // The stale answer arrives anyway: it must not be delivered.
    asks[0].resolve(ANSWER(5, 1));
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[1].resolve(ANSWER(9, 2));
    await vi.advanceTimersByTimeAsync(0);
    expect(got.map(([k, c]) => [k, c.shapes])).toEqual([["b", 9]]);
  });

  test("an empty key (idle gone, no service) cancels everything and asks nothing", async () => {
    const { recounter, got, asks, run } = setup();
    recounter.ask("a", run());
    recounter.ask("", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS * 2);
    expect(asks).toHaveLength(0);
    expect(got).toEqual([]);
  });

  test("a size answered before comes from the cache, with no new request", async () => {
    const { recounter, got, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[0].resolve(ANSWER(22, 2));
    await vi.advanceTimersByTimeAsync(0);
    recounter.ask("b", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[1].resolve(ANSWER(93, 2));
    await vi.advanceTimersByTimeAsync(0);
    recounter.ask("a", run()); // back to 'a': delivered at once from memory
    expect(got.map(([k]) => k)).toEqual(["a", "b", "a"]);
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS * 2);
    expect(asks).toHaveLength(2);
  });

  test("returning to the answered size mid-detour cancels the detour", async () => {
    const { recounter, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[0].resolve(ANSWER(22, 2));
    await vi.advanceTimersByTimeAsync(0);
    recounter.ask("b", run());      // scheduled, not yet sent
    recounter.ask("a", run());      // back to what is already answered
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS * 2);
    expect(asks).toHaveLength(1);
  });

  test("a 404 (null) means no route: delivers nothing and never asks again", async () => {
    const { recounter, got, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[0].resolve(null);
    await vi.advanceTimersByTimeAsync(0);
    recounter.ask("b", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS * 2);
    expect(asks).toHaveLength(1);
    expect(got).toEqual([]);
  });

  test("a failed ask is silent, and the next size still asks", async () => {
    const { recounter, got, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[0].reject(new Error("boom"));
    await vi.advanceTimersByTimeAsync(0);
    expect(got).toEqual([]);
    recounter.ask("b", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[1].resolve(ANSWER(3, 1));
    await vi.advanceTimersByTimeAsync(0);
    expect(got.map(([k]) => k)).toEqual(["b"]);
  });

  test("a malformed answer delivers nothing", async () => {
    const { recounter, got, asks, run } = setup();
    recounter.ask("a", run());
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS);
    asks[0].resolve({ shape_count: "many" });
    await vi.advanceTimersByTimeAsync(0);
    expect(got).toEqual([]);
  });

  test("stop() cancels a scheduled ask", async () => {
    const { recounter, asks, run } = setup();
    recounter.ask("a", run());
    recounter.stop();
    await vi.advanceTimersByTimeAsync(RECOUNT_DEBOUNCE_MS * 2);
    expect(asks).toHaveLength(0);
  });
});
