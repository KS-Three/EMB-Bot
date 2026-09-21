// The original-bytes store (lib/sourceStore.js): what a digitize SENDS since
// 2026-09-20. jsdom has no IndexedDB, so every test hands in this fake, which
// implements exactly the surface the module uses — open with an upgrade,
// one object store, get/put/delete requests that settle on a microtask.
import { test, expect } from "vitest";
import { webcrypto } from "node:crypto";
import { deleteSource, getSource, putSource, sourceKeyFor, sourceStoreAvailable } from "./sourceStore.js";

function fakeIndexedDB() {
  const dbs = new Map();
  const request = (run) => {
    const r = { result: undefined, error: null, onsuccess: null, onerror: null };
    queueMicrotask(() => {
      try { r.result = run(); if (r.onsuccess) r.onsuccess({ target: r }); }
      catch (e) { r.error = e; if (r.onerror) r.onerror({ target: r }); }
    });
    return r;
  };
  return {
    opens: 0,
    closes: 0,
    open(name) {
      this.opens++;
      const idb = this;
      const r = { result: null, error: null, onsuccess: null, onerror: null, onupgradeneeded: null };
      queueMicrotask(() => {
        const fresh = !dbs.has(name);
        if (fresh) dbs.set(name, new Map());
        const stores = dbs.get(name);
        const db = {
          objectStoreNames: { contains: (s) => stores.has(s) },
          createObjectStore(s) { stores.set(s, new Map()); },
          transaction(s) {
            const m = stores.get(s);
            return { objectStore: () => ({
              get: (k) => request(() => m.get(k)),
              put: (v, k) => request(() => { m.set(k, v); return k; }),
              delete: (k) => request(() => { m.delete(k); }),
            }) };
          },
          close() { idb.closes++; },
        };
        r.result = db;
        if (fresh && r.onupgradeneeded) r.onupgradeneeded({ target: r });
        if (r.onsuccess) r.onsuccess({ target: r });
      });
      return r;
    },
  };
}

test("availability is a real check, not an assumption", () => {
  expect(sourceStoreAvailable(undefined)).toBe(false);
  expect(sourceStoreAvailable({})).toBe(false);
  expect(sourceStoreAvailable(fakeIndexedDB())).toBe(true);
});

test("the key is the content: SHA-256 hex, so one file uploaded twice is one record", async () => {
  const abc = new TextEncoder().encode("abc");
  expect(await sourceKeyFor(abc, webcrypto.subtle)).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  expect(await sourceKeyFor(abc, webcrypto.subtle)).toBe(await sourceKeyFor(new Uint8Array([97, 98, 99]), webcrypto.subtle));
  // No subtle crypto (an insecure context): the store still works, it just
  // stops de-duplicating — a random key, marked as such.
  const rnd = await sourceKeyFor(abc, null);
  expect(rnd).toMatch(/^r[0-9a-f]{32}$/);
  expect(await sourceKeyFor(abc, null)).not.toBe(rnd);
});

test("put then get round-trips the bytes, the type and the name; a missing key is null", async () => {
  const idb = fakeIndexedDB();
  const bytes = new Uint8Array([137, 80, 78, 71, 1, 2, 3]);
  await putSource("k1", { bytes, type: "image/png", name: "logo.png" }, idb);
  const rec = await getSource("k1", idb);
  expect(rec).toEqual({ bytes, type: "image/png", name: "logo.png" });
  expect(rec.bytes).toBeInstanceOf(Uint8Array);
  expect(await getSource("nope", idb)).toBeNull();
  // Every call opens and closes its own connection — nothing is left holding
  // the database open across the panel's lifetime.
  expect(idb.closes).toBe(idb.opens);
});

test("delete removes the record, and a store that is not there reads as absent rather than throwing", async () => {
  const idb = fakeIndexedDB();
  await putSource("k2", { bytes: new Uint8Array([1]), type: "image/webp", name: "a.webp" }, idb);
  await deleteSource("k2", idb);
  expect(await getSource("k2", idb)).toBeNull();
  expect(await getSource("k2", undefined)).toBeNull();
  await expect(deleteSource("k2", undefined)).resolves.toBeUndefined();
  expect(await getSource("", idb)).toBeNull();
});
