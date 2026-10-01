// sourceStore.js — the customer's ORIGINAL artwork bytes, kept in IndexedDB so
// a digitize (and every re-digitize after a reload) sends the FILE to the
// service, not the panel's preview of it.
//
// Until 2026-09-20 DigitizePanel re-encoded every upload through a 1,200-px
// canvas and sent THAT PNG to /digitize — a raster the customer never made:
// resampled at Chrome's default "low" smoothing, its RGB under transparency
// rewritten by the canvas's premultiplied alpha. Measured on the nine corpus
// logos it cost 503 -> 609 trims (Becker alone 59 -> 175 on an image the
// canvas never even resized; tires 6 -> 14 with no alpha at all) — DOCTRINE
// 2026-09-19/20, scope-history 2026-09-20 §E. The service's own decoder caps
// at 2,800 px with INTER_AREA, so the panel's resample bought the engine
// nothing; it existed because the base64 preview lives in localStorage with
// the project, where a 5 MB JPEG has no place.
//
// So the file's bytes live HERE, keyed by their SHA-256, and the element
// carries only the key (`element.sourceFile`, see project.js). localStorage
// keeps the 1,200-px preview it always kept; IndexedDB has room for the
// original. Content-addressed on purpose: two elements made from one file
// share one record, and re-uploading a file the store already holds is a
// no-op. Nothing here prunes — a record is a few MB and the cost of pruning
// wrong is a re-digitize that silently falls back to the preview (the panel
// says so when that happens, but it is still the worse result).
//
// Every function takes the IndexedDB factory as its last argument so the
// unit tests can hand in a fake; jsdom has none.

const DB_NAME = "embstudio-sources";
const STORE = "sources";
const VERSION = 1;

function req(r) {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error || new Error("IndexedDB request failed"));
  });
}

function openDb(idb) {
  const r = idb.open(DB_NAME, VERSION);
  r.onupgradeneeded = () => {
    const db = r.result;
    if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
  };
  return req(r);
}

// True when this browser can keep originals at all (a private window with
// storage blocked, or an old WebView, may not). The caller falls back to the
// preview path — the pre-2026-09-20 behaviour — rather than failing the upload.
export function sourceStoreAvailable(idb = globalThis.indexedDB) {
  return Boolean(idb && typeof idb.open === "function");
}

// SHA-256 of the bytes as hex — the record key. `crypto.subtle` is absent
// outside secure contexts; there a random key still makes the store work, it
// just stops de-duplicating.
export async function sourceKeyFor(bytes, subtle = globalThis.crypto && globalThis.crypto.subtle) {
  if (subtle && typeof subtle.digest === "function") {
    const digest = new Uint8Array(await subtle.digest("SHA-256", bytes));
    return Array.from(digest, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  const rnd = new Uint8Array(16);
  if (globalThis.crypto && typeof globalThis.crypto.getRandomValues === "function") {
    globalThis.crypto.getRandomValues(rnd);
  } else {
    for (let i = 0; i < rnd.length; i++) rnd[i] = Math.floor(Math.random() * 256);
  }
  return "r" + Array.from(rnd, (b) => b.toString(16).padStart(2, "0")).join("");
}

// Store {bytes, type, name} under key. Overwrites — the key IS the content.
export async function putSource(key, record, idb = globalThis.indexedDB) {
  const db = await openDb(idb);
  try {
    const tx = db.transaction(STORE, "readwrite");
    await req(tx.objectStore(STORE).put({ bytes: record.bytes, type: record.type || "", name: record.name || "" }, key));
  } finally {
    db.close();
  }
}

// -> { bytes: Uint8Array, type, name } or null when the record is gone
// (cleared site data, another browser, another machine).
export async function getSource(key, idb = globalThis.indexedDB) {
  if (!key || !sourceStoreAvailable(idb)) return null;
  const db = await openDb(idb);
  try {
    const rec = await req(db.transaction(STORE, "readonly").objectStore(STORE).get(key));
    if (!rec || !rec.bytes) return null;
    return { bytes: rec.bytes instanceof Uint8Array ? rec.bytes : new Uint8Array(rec.bytes), type: rec.type || "", name: rec.name || "" };
  } finally {
    db.close();
  }
}

export async function deleteSource(key, idb = globalThis.indexedDB) {
  if (!key || !sourceStoreAvailable(idb)) return;
  const db = await openDb(idb);
  try {
    await req(db.transaction(STORE, "readwrite").objectStore(STORE).delete(key));
  } finally {
    db.close();
  }
}
