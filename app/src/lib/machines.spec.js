// @vitest-environment jsdom
import { test, expect, beforeEach } from "vitest";
import { MACHINES, MACHINE_KEY, machineById, loadMachineId, saveMachineId } from "./machines.js";

beforeEach(() => {
  localStorage.clear();
});

test("every machine maps to a format the Download step can write", () => {
  const known = new Set(["dst", "pes", "exp", "jef", "xxx", "vp3"]);
  expect(MACHINES.length).toBeGreaterThanOrEqual(6);
  const ids = new Set();
  for (const m of MACHINES) {
    expect(known.has(m.format), `${m.id} -> ${m.format}`).toBe(true);
    expect(m.label.length).toBeGreaterThan(0);
    expect(ids.has(m.id), `duplicate id ${m.id}`).toBe(false);
    ids.add(m.id);
  }
  // The four home brands a customer is most likely to own are all here.
  expect(machineById("brother").format).toBe("pes");
  expect(machineById("janome").format).toBe("jef");
  expect(machineById("husqvarna").format).toBe("vp3");
  expect(machineById("singer").format).toBe("xxx");
});

test("the choice round-trips through storage, and clearing it removes the key", () => {
  expect(loadMachineId()).toBeNull();
  saveMachineId("janome");
  expect(localStorage.getItem(MACHINE_KEY)).toBe("janome");
  expect(loadMachineId()).toBe("janome");
  saveMachineId(null);
  expect(localStorage.getItem(MACHINE_KEY)).toBeNull();
  expect(loadMachineId()).toBeNull();
});

test("a stored id this build does not list reads as no choice", () => {
  localStorage.setItem(MACHINE_KEY, "toyota");
  expect(loadMachineId()).toBeNull();
  expect(machineById("toyota")).toBeNull();
});

test("unreadable storage is no choice, not a throw", () => {
  const real = globalThis.localStorage;
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    get() { throw new Error("denied"); },
  });
  try {
    expect(loadMachineId()).toBeNull();
    expect(() => saveMachineId("brother")).not.toThrow();
  } finally {
    Object.defineProperty(globalThis, "localStorage", { configurable: true, value: real });
  }
});
