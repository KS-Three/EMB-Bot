// projectSources.js — the customer's original artwork between the .embproj
// file and this browser's source store (lib/sourceStore.js).
//
// The file carries originals (projectFile.js `sources`) because the store
// does not travel: IndexedDB is this browser's, and a design opened on
// another machine, or after cleared site data, has the 1,200-px preview and
// nothing else — which digitizes differently (DOCTRINE 2026-09-19/20), and
// the panel says so. Export gathers what the store still holds for the
// project's elements; import puts the file's originals back BEFORE the
// project is registered, so every element points at a record that exists.
//
// Both take the store's functions as a parameter so the unit tests can hand
// in a map; the defaults are the real store. Neither throws: an original we
// cannot read is one we do not embed, one we cannot keep is counted and the
// element digitizes from its preview here, as it did before 2026-09-20.

import { sourceKeysOf } from "./projectFile.js";
import { getSource, putSource, sourceKeyFor, sourceStoreAvailable } from "./sourceStore.js";

const REAL_STORE = { getSource, putSource, sourceKeyFor, available: sourceStoreAvailable };

// -> { key: { bytes, type, name } } for every original the store still holds
// among the project's elements. A missing record is simply absent: the file
// then says nothing about that element, and wherever it is opened that
// element digitizes from its preview with the panel's note.
export async function collectSources(project, store = REAL_STORE) {
  const out = {};
  if (!store.available()) return out;
  for (const key of sourceKeysOf(project)) {
    try {
      const rec = await store.getSource(key);
      if (rec && rec.bytes instanceof Uint8Array && rec.bytes.length) {
        out[key] = { bytes: rec.bytes, type: rec.type || "", name: rec.name || "" };
      }
    } catch (e) {
      // unreadable record: not embedded
    }
  }
  return out;
}

// Puts the file's originals into the store and returns the project to
// register: { project, restored, missing, failed }.
//
// Each original is stored under the key ITS BYTES hash to here (the store is
// content-addressed), not under the key the file carried — the two differ
// when the file was saved without `crypto.subtle` (a random key) or was
// edited — and every element that used the file's key is repointed. So a
// record is never filed under a name that is not its content, and one
// original uploaded here and imported from a file is one record.
//
// `missing`: elements whose original the file did not carry (saved before
// 2026-09-20, or the record was already gone when it was saved). `failed`:
// originals the file carried that this browser could not keep (no
// IndexedDB, quota) — those elements keep their key and digitize from the
// preview here, with the note.
export async function restoreSources(project, sources, store = REAL_STORE) {
  const result = { project, restored: 0, missing: 0, failed: 0 };
  const keys = sourceKeysOf(project);
  if (!keys.length) return result;
  const available = store.available();
  const repoint = {};
  for (const key of keys) {
    const rec = sources && typeof sources === "object" ? sources[key] : null;
    if (!rec || !(rec.bytes instanceof Uint8Array) || !rec.bytes.length) {
      result.missing++;
      continue;
    }
    if (!available) {
      result.failed++;
      continue;
    }
    try {
      const stored = await store.sourceKeyFor(rec.bytes);
      await store.putSource(stored, { bytes: rec.bytes, type: rec.type || "", name: rec.name || "" });
      if (stored !== key) repoint[key] = stored;
      result.restored++;
    } catch (e) {
      result.failed++;
    }
  }
  if (Object.keys(repoint).length) {
    result.project = {
      ...project,
      elements: project.elements.map((el) => {
        const key = el && el.sourceFile && el.sourceFile.key;
        return key && repoint[key] ? { ...el, sourceFile: { ...el.sourceFile, key: repoint[key] } } : el;
      }),
    };
  }
  return result;
}
