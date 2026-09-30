// Save exported files straight into a folder the user picks, instead of the
// browser's Downloads folder.
//
// Why this exists: the machine-transfer utilities people use (RnEmbNet and the
// like) send designs FROM a folder on disk. If every EMB-Bot download lands in
// Downloads, the operator hunts for the file each time before they can send it.
// Point EMB-Bot at that utility's send-folder once and the file is already
// where the utility looks.
//
// Mechanism: the File System Access API (`showDirectoryPicker`). The user
// grants access to ONE folder; we keep the returned handle in IndexedDB (a
// directory handle is a live object, not a string, so it cannot live in
// localStorage next to the other prefs) and write into it on each export. This
// stays entirely in the browser — no server, no path typed by hand, consistent
// with the project staying local (PRODUCT.md, "projects staying local").
//
// Support is Chromium-only (Chrome/Edge/Brave, desktop). Safari and Firefox do
// not implement it; `folderSaveSupported()` is false there and callers fall
// back to a normal download. Every function is defensive: a browser without
// the API, a cleared IndexedDB, or a permission the user later revokes must
// degrade to "just download it", never throw into the UI unhandled.

const DB_NAME = "embbot";
const STORE = "handles";
const KEY = "downloadDir";

// True only where the picker exists AND IndexedDB is available to remember the
// choice. Without persistence the feature would forget the folder on every
// reload, which is worse than not offering it — so both are required.
export function folderSaveSupported() {
  return (
    typeof window !== "undefined" &&
    typeof window.showDirectoryPicker === "function" &&
    typeof window.indexedDB !== "undefined"
  );
}

function openDb() {
  return new Promise((resolve, reject) => {
    let req;
    try {
      req = window.indexedDB.open(DB_NAME, 1);
    } catch (e) {
      reject(e);
      return;
    }
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error("IndexedDB open failed"));
  });
}

function idbDo(mode, fn) {
  return openDb().then(
    (db) =>
      new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const store = tx.objectStore(STORE);
        let result;
        const r = fn(store);
        // getters expose the value through the request; setters/deleters just
        // need the transaction to complete.
        if (r) r.onsuccess = () => { result = r.result; };
        tx.oncomplete = () => { db.close(); resolve(result); };
        tx.onerror = () => { db.close(); reject(tx.error); };
        tx.onabort = () => { db.close(); reject(tx.error); };
      })
  );
}

function idbGet(key) { return idbDo("readonly", (s) => s.get(key)); }
function idbSet(key, val) { return idbDo("readwrite", (s) => s.put(val, key)); }
function idbDel(key) { return idbDo("readwrite", (s) => s.delete(key)); }

// Ask the user to choose a folder. Must be called from a user gesture (a click)
// — the picker and the permission grant both require one. Returns the folder's
// display name on success. A user who cancels the picker triggers an
// AbortError; callers treat that as "no change", not an error to surface.
export async function pickFolder() {
  const handle = await window.showDirectoryPicker({ id: "embbot-out", mode: "readwrite" });
  await idbSet(KEY, handle);
  return handle.name;
}

// The remembered folder's display name, or null if none is set / not readable.
// Name only: enough to show "Saving to: <name>" without touching permissions.
export async function savedFolderName() {
  if (!folderSaveSupported()) return null;
  try {
    const handle = await idbGet(KEY);
    return handle ? handle.name : null;
  } catch (e) {
    return null;
  }
}

export async function forgetFolder() {
  try { await idbDel(KEY); } catch (e) { /* nothing to forget */ }
}

// Grant state for the saved folder WITHOUT prompting: "granted", "prompt"
// (needs a click to re-grant, e.g. after a reload), or "none" (no folder set).
export async function folderPermissionState() {
  try {
    const handle = await idbGet(KEY);
    if (!handle) return "none";
    const p = await handle.queryPermission({ mode: "readwrite" });
    return p === "granted" ? "granted" : "prompt";
  } catch (e) {
    return "none";
  }
}

// Re-grant access to the saved folder. Must run inside a user gesture, since
// `requestPermission` needs one. Returns true if access is now granted.
export async function reconnectFolder() {
  try {
    const handle = await idbGet(KEY);
    if (!handle) return false;
    if ((await handle.queryPermission({ mode: "readwrite" })) === "granted") return true;
    return (await handle.requestPermission({ mode: "readwrite" })) === "granted";
  } catch (e) {
    return false;
  }
}

// Write bytes into the chosen folder. Throws a tagged Error the caller can map
// to a friendly message:
//   "no-folder"          — nothing chosen (caller should fall back to download)
//   "folder-permission"  — access not granted / was revoked (needs reconnect)
// Any other failure (disk full, name clash the OS rejects) propagates as-is.
//
// Note on user activation: this does NOT call requestPermission. After a slow
// export the click's activation is spent, and requestPermission would throw for
// lack of a gesture. We only queryPermission; if it is not already "granted"
// we raise "folder-permission" so the UI can ask for a fresh click, rather than
// failing obscurely.
export async function saveToFolder(filename, bytes, mime) {
  const handle = await idbGet(KEY);
  if (!handle) { const e = new Error("no-folder"); e.code = "no-folder"; throw e; }
  if ((await handle.queryPermission({ mode: "readwrite" })) !== "granted") {
    const e = new Error("folder-permission"); e.code = "folder-permission"; throw e;
  }
  const fileHandle = await handle.getFileHandle(filename, { create: true });
  const writable = await fileHandle.createWritable();
  const blob = bytes instanceof Blob ? bytes : new Blob([bytes], { type: mime || "application/octet-stream" });
  await writable.write(blob);
  await writable.close();
  return handle.name;
}
