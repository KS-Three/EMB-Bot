import { test, expect, beforeEach, vi } from "vitest";

// hints.js is loaded fresh (dynamic import after vi.resetModules()) in every
// test so each one starts with a clean module-level `sessionDismissed` Set
// (see hints.js's own comment on why that Set exists) — without this, a
// dismiss() in one test would leak into every later test in this file since
// ES module instances are otherwise cached/shared across the whole run.

function makeMemoryStorage(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => {
      store.set(k, String(v));
    },
    removeItem: (k) => {
      store.delete(k);
    },
    _store: store,
  };
}

// Every read AND write throws — simulates disabled/denied storage entirely.
function makeThrowingStorage() {
  return {
    getItem: () => {
      throw new Error("denied");
    },
    setItem: () => {
      throw new Error("denied");
    },
    removeItem: () => {},
  };
}

// Reads succeed normally (backed by a real Map), but every write throws —
// simulates a full/quota-exceeded storage.
function makeReadOnlyStorage(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: () => {
      throw new Error("quota");
    },
    removeItem: (k) => {
      store.delete(k);
    },
  };
}

let hints;

beforeEach(async () => {
  globalThis.localStorage = makeMemoryStorage();
  vi.resetModules();
  hints = await import("./hints.js");
});

// --- shouldShow / dismiss: basic contract -----------------------------------

test("shouldShow defaults to true for a key that's never been dismissed", () => {
  expect(hints.shouldShow("templates")).toBe(true);
  expect(hints.shouldShow("add-elements")).toBe(true);
  expect(hints.shouldShow("drag-field")).toBe(true);
});

test("dismiss flips shouldShow to false for that key only", () => {
  hints.dismiss("templates");
  expect(hints.shouldShow("templates")).toBe(false);
  expect(hints.shouldShow("add-elements")).toBe(true);
  expect(hints.shouldShow("drag-field")).toBe(true);
});

test("dismiss persists to storage: a fresh module instance still sees it dismissed", async () => {
  hints.dismiss("add-elements");

  // Simulate a page reload: a brand-new module instance (fresh
  // sessionDismissed Set) reading the SAME underlying localStorage.
  vi.resetModules();
  const reloaded = await import("./hints.js");

  expect(reloaded.shouldShow("add-elements")).toBe(false);
  // Untouched keys are unaffected by the reload either.
  expect(reloaded.shouldShow("templates")).toBe(true);
});

test("dismissing twice is harmless (idempotent)", () => {
  hints.dismiss("drag-field");
  hints.dismiss("drag-field");
  expect(hints.shouldShow("drag-field")).toBe(false);
});

// --- storage-throw paths -----------------------------------------------------

test("a storage READ failure is treated as nothing dismissed yet (default SHOW)", () => {
  globalThis.localStorage = makeThrowingStorage();
  expect(hints.shouldShow("templates")).toBe(true);
  expect(hints.shouldShow("add-elements")).toBe(true);
  expect(hints.shouldShow("drag-field")).toBe(true);
});

test("a corrupt/unparseable stored value is also treated as default SHOW", () => {
  globalThis.localStorage = makeMemoryStorage({ "embstudio:hints": "{not valid json" });
  expect(hints.shouldShow("templates")).toBe(true);
});

test("a storage WRITE failure makes dismiss a persistence no-op, but the session-level Set still hides it for the rest of THIS session", () => {
  globalThis.localStorage = makeReadOnlyStorage();

  expect(() => hints.dismiss("templates")).not.toThrow();
  // Same module instance (same page session) -> still hidden.
  expect(hints.shouldShow("templates")).toBe(false);
  // But nothing was actually persisted...
  expect(globalThis.localStorage.getItem("embstudio:hints")).toBeNull();
});

test("...and confirms it: a fresh module instance (next real reload) sees it as shown again, since the write never landed", async () => {
  const storage = makeReadOnlyStorage();
  globalThis.localStorage = storage;
  hints.dismiss("templates");
  expect(hints.shouldShow("templates")).toBe(false); // this session: still hidden

  vi.resetModules();
  const reloaded = await import("./hints.js");
  // Same (never-actually-written-to) storage handed to the fresh instance.
  globalThis.localStorage = storage;
  expect(reloaded.shouldShow("templates")).toBe(true);
});

// --- visibleHint: A7 priority rule (drag-field > add-elements > templates) --

test("visibleHint returns null when nothing is eligible", () => {
  expect(hints.visibleHint([])).toBeNull();
  expect(hints.visibleHint(undefined)).toBeNull();
});

test("visibleHint returns the only eligible key when just one is eligible (templates can show alone)", () => {
  expect(hints.visibleHint(["templates"])).toBe("templates");
  expect(hints.visibleHint(["add-elements"])).toBe("add-elements");
  expect(hints.visibleHint(["drag-field"])).toBe("drag-field");
});

test("drag-field outranks add-elements and templates whenever it's eligible", () => {
  expect(hints.visibleHint(["templates", "drag-field"])).toBe("drag-field");
  expect(hints.visibleHint(["add-elements", "drag-field"])).toBe("drag-field");
  expect(hints.visibleHint(["templates", "add-elements", "drag-field"])).toBe("drag-field");
  // Order of the input list must not matter.
  expect(hints.visibleHint(["drag-field", "templates", "add-elements"])).toBe("drag-field");
});

test("add-elements outranks templates when drag-field isn't eligible", () => {
  expect(hints.visibleHint(["templates", "add-elements"])).toBe("add-elements");
});

test("templates only wins when it's the only one eligible", () => {
  expect(hints.visibleHint(["templates"])).toBe("templates");
  // As soon as anything higher-priority joins the eligible set, templates loses.
  expect(hints.visibleHint(["templates", "add-elements"])).not.toBe("templates");
  expect(hints.visibleHint(["templates", "drag-field"])).not.toBe("templates");
});

test("visibleHint ignores unrecognized keys", () => {
  expect(hints.visibleHint(["mystery-hint"])).toBeNull();
});

// --- end-to-end-ish: eligible set naturally shrinks as hints get dismissed --

test("once the higher-priority eligible hint is dismissed, a lower one can win on the next check", () => {
  // App.svelte's real usage: it only ever feeds visibleHint keys that are
  // BOTH contextually eligible AND still shouldShow()-true (see hints.js's
  // module doc). This test exercises that whole loop directly.
  const contextuallyEligible = ["templates", "add-elements", "drag-field"];
  const stillEligible = () => contextuallyEligible.filter((k) => hints.shouldShow(k));

  expect(hints.visibleHint(stillEligible())).toBe("drag-field");

  hints.dismiss("drag-field");
  expect(hints.visibleHint(stillEligible())).toBe("add-elements");

  hints.dismiss("add-elements");
  expect(hints.visibleHint(stillEligible())).toBe("templates");

  hints.dismiss("templates");
  expect(hints.visibleHint(stillEligible())).toBeNull();
});
