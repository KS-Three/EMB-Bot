// Client-side project registry (localStorage-backed).
//
// Storage shape:
//   embstudio:index      JSON array of {id, name, updatedAt} — one entry per
//                        saved project, newest-first once sorted by
//                        listProjects().
//   embstudio:p:<id>     one JSON project record per id (same shape as the
//                        legacy `embstudio:last` blob). Written via save.js's
//                        serialize(); read via loadProject()'s own
//                        JSON.parse + migrateProject — NOT save.js's
//                        deserialize(), which swallows a corrupt record into
//                        a fresh defaultProject() instead of surfacing null
//                        (see loadProject's own comment for why that
//                        distinction matters here).
//   embstudio:current    the id of the currently-open project (plain
//                        string, not JSON), or absent if none.
//
// Every exported function is try/catch-safe: if localStorage throws (quota
// exceeded, privacy mode, disabled storage, etc.) the app keeps working in
// memory, it just loses persistence — nothing here should ever throw out to
// a caller.
//
// Two invariants worth calling out explicitly, both from adversarial review
// of an earlier draft of this slice's plan:
//
//   1. saveProject/renameProject/deleteProject treat an id that is NOT in
//      the index as a no-op. This means an auto-save that fires after a
//      project has been deleted can never resurrect it (see A2/A10 in the
//      plan's amendments).
//   2. migrateLegacy writes in a specific order — project record, then a
//      read-back verification, then index + current pointer, and ONLY THEN
//      does it remove the legacy key. Any failure along the way aborts
//      before the legacy key is touched, so the user's original data is
//      never lost even if storage fails mid-migration (see A1).

import { defaultProject, migrateProject } from "./project.js";
import { serialize } from "./save.js";

const INDEX_KEY = "embstudio:index";
const CURRENT_KEY = "embstudio:current";
const LEGACY_KEY = "embstudio:last";

function projectKey(id) {
  return "embstudio:p:" + id;
}

function genId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "p" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
}

// Reads the index array, tolerating missing/corrupt storage by returning [].
function readIndex() {
  try {
    const raw = localStorage.getItem(INDEX_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch (e) {
    return [];
  }
}

// Writes the whole index array in one shot (localStorage.setItem is
// effectively atomic per key, so this never leaves a "partially written"
// index — it either lands whole or throws and leaves the old value alone).
function writeIndex(list) {
  try {
    localStorage.setItem(INDEX_KEY, JSON.stringify(list));
    return true;
  } catch (e) {
    return false;
  }
}

export function listProjects() {
  return readIndex()
    .slice()
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}

export function currentProjectId() {
  try {
    return localStorage.getItem(CURRENT_KEY) || null;
  } catch (e) {
    return null;
  }
}

export function setCurrentProject(id) {
  try {
    localStorage.setItem(CURRENT_KEY, id);
  } catch (e) {}
}

export function createProject(name) {
  const id = genId();
  const project = defaultProject();
  const finalName = name || "Untitled design";
  try {
    localStorage.setItem(projectKey(id), serialize(project));
    const idx = readIndex();
    idx.push({ id, name: finalName, updatedAt: Date.now() });
    if (writeIndex(idx)) {
      localStorage.setItem(CURRENT_KEY, id);
    } else {
      // Partial failure: the record write above succeeded but the index
      // write didn't, so this id would otherwise be an orphan -- a project
      // record with no index entry and no current pointer. Every other
      // registry function (saveProject/renameProject/deleteProject) treats
      // an unindexed id as a no-op, so if we left the record AND pointed
      // CURRENT_KEY at it, auto-save would be permanently dead for the rest
      // of this session and every session after. Undo the record write and
      // leave CURRENT_KEY alone so the caller falls back to the same
      // degraded-but-consistent in-memory-only state as a total storage
      // failure (below): a working project the app just can't persist.
      try {
        localStorage.removeItem(projectKey(id));
      } catch (e2) {}
    }
  } catch (e) {
    // Storage failed entirely — the app still gets a working in-memory
    // project, it just won't persist (matches the try/catch-safe contract).
  }
  return { id, project };
}

// Returns null for a missing OR corrupt record. Unlike save.js's
// deserialize() (which swallows a JSON.parse failure into a fresh
// defaultProject() — the right call for the legacy single-blob path, where
// there's nowhere else to route a "load"), a corrupt registry record must
// NOT be silently replaced: the caller (App's boot / openProject) treats
// null as "nothing to open" and falls back to a brand-new project, and the
// very next auto-save would then overwrite this id's corrupt-but-maybe-
// recoverable raw string with that fresh blank one. So the parse happens
// here, directly, and a parse failure returns null WITHOUT touching
// storage — the raw record is left in place for a human to recover later.
export function loadProject(id) {
  try {
    const raw = localStorage.getItem(projectKey(id));
    if (!raw) return null;
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (e) {
      return null; // corrupt: leave the raw record untouched
    }
    return migrateProject(parsed);
  } catch (e) {
    return null;
  }
}

// Update-only: an id that isn't registered in the index is a no-op so an
// auto-save can never resurrect a deleted project (A2/A10).
export function saveProject(id, project) {
  try {
    const idx = readIndex();
    const i = idx.findIndex((e) => e.id === id);
    if (i === -1) return false;
    localStorage.setItem(projectKey(id), serialize(project));
    idx[i] = { ...idx[i], updatedAt: Date.now() };
    writeIndex(idx);
    return true;
  } catch (e) {
    return false;
  }
}

// No-op for an unknown id (A10).
export function renameProject(id, name) {
  try {
    const idx = readIndex();
    const i = idx.findIndex((e) => e.id === id);
    if (i === -1) return false;
    idx[i] = { ...idx[i], name };
    writeIndex(idx);
    return true;
  } catch (e) {
    return false;
  }
}

// No-op for an unknown id (A10). Clears the current pointer if (and only
// if) the deleted project was the current one.
export function deleteProject(id) {
  try {
    const idx = readIndex();
    const i = idx.findIndex((e) => e.id === id);
    if (i === -1) return false;
    idx.splice(i, 1);
    writeIndex(idx);
    try {
      localStorage.removeItem(projectKey(id));
    } catch (e) {}
    if (currentProjectId() === id) {
      try {
        localStorage.removeItem(CURRENT_KEY);
      } catch (e) {}
    }
    return true;
  } catch (e) {
    return false;
  }
}

// Returns null (and creates nothing) if `id` isn't a registered project.
// Does NOT change the current pointer — duplicating a design doesn't switch
// you away from what you're currently editing.
export function duplicateProject(id, name) {
  try {
    const idx = readIndex();
    const srcEntry = idx.find((e) => e.id === id);
    const project = loadProject(id);
    if (!srcEntry || project === null) return null;
    const newId = genId();
    const newName = name || srcEntry.name + " copy";
    localStorage.setItem(projectKey(newId), serialize(project));
    idx.push({ id: newId, name: newName, updatedAt: Date.now() });
    if (!writeIndex(idx)) {
      // Same orphan hazard as createProject: the record write above
      // succeeded but the index write didn't, so undo it rather than leave
      // an unindexed record behind, and report failure so the caller never
      // believes a duplicate exists that the registry doesn't know about.
      try {
        localStorage.removeItem(projectKey(newId));
      } catch (e2) {}
      return null;
    }
    return { id: newId, project };
  } catch (e) {
    return null;
  }
}

// One-time migration of the old single-project `embstudio:last` blob into
// the registry, run once at app boot before anything else reads storage.
//
// Guarded so it only ever does something when there's a legacy blob AND no
// index yet — once an index exists (whether from a completed migration or
// from the user simply creating projects), this is a permanent no-op even
// if a legacy blob is somehow still present.
//
// Write ordering (A1, non-negotiable): the project record is written and
// then read back and verified BEFORE the index/current pointer are written,
// and the legacy key is only removed as the very last step. If anything
// throws (or the read-back doesn't check out) at any point before that
// final removeItem, the whole thing aborts with `embstudio:last` completely
// untouched — migration simply retries on the next boot.
//
// A corrupt/unparseable legacy blob (JSON.parse throws) is treated as
// unrecoverable: the key is left in place, nothing is created, and boot
// proceeds (the caller falls back to createProject()). We don't attempt to
// salvage it into a defaultProject() — a human might still want to inspect
// the raw string, and silently replacing it with a blank design would be
// its own small data-loss.
export function migrateLegacy() {
  try {
    const indexExists = localStorage.getItem(INDEX_KEY) != null;
    const legacyRaw = localStorage.getItem(LEGACY_KEY);
    if (indexExists || legacyRaw == null) return;

    let parsed;
    try {
      parsed = JSON.parse(legacyRaw);
    } catch (e) {
      return; // corrupt/unparseable: leave the key, create nothing
    }

    const project = migrateProject(parsed);
    const id = genId();
    const recordKey = projectKey(id);

    // (1) write the project record
    localStorage.setItem(recordKey, serialize(project));

    // (2) read it back and verify it parses before touching anything else
    const readBack = localStorage.getItem(recordKey);
    if (readBack == null) throw new Error("migrateLegacy: read-back missing");
    JSON.parse(readBack); // throws -> caught below, legacy key stays put

    // (3) only now write index + current pointer
    localStorage.setItem(
      INDEX_KEY,
      JSON.stringify([{ id, name: "My first design", updatedAt: Date.now() }])
    );
    localStorage.setItem(CURRENT_KEY, id);

    // (4) only after index + current are safely written, remove the legacy key
    localStorage.removeItem(LEGACY_KEY);
  } catch (e) {
    // Swallow every failure here. Because removeItem(LEGACY_KEY) is the very
    // last statement in the try block, any throw above it leaves
    // embstudio:last completely untouched.
  }
}
