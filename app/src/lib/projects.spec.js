import { test, expect, beforeEach, vi } from "vitest";
import {
  listProjects,
  createProject,
  loadProject,
  saveProject,
  renameProject,
  deleteProject,
  duplicateProject,
  importProject,
  currentProjectId,
  setCurrentProject,
  migrateLegacy,
} from "./projects.js";
import { defaultProject, updateElement } from "./project.js";

// --- in-memory localStorage stubs -------------------------------------
//
// vitest here runs in a node environment (no browser globals), so every
// spec needs its own fake `localStorage` on `globalThis`. `makeMemoryStorage`
// is a normal Map-backed stand-in; `makeThrowingStorage` behaves the same
// for reads but makes every `setItem` throw (simulating a full/denied
// storage), which is what the A1 write-ordering spec needs.

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
    clear: () => store.clear(),
    _store: store,
  };
}

function makeThrowingStorage(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: () => {
      throw new Error("storage full");
    },
    removeItem: (k) => {
      store.delete(k);
    },
    _store: store,
  };
}

// Simulates a PARTIAL storage failure: only the keys named in `throwingKeys`
// throw on setItem (everything else behaves like normal memory storage).
// Used to reproduce "the project record write succeeds but the index write
// doesn't" -- the exact partial-failure shape createProject/duplicateProject
// must roll back cleanly instead of leaving an orphaned, unindexed record
// behind.
function makePartialThrowingStorage(throwingKeys, initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => {
      if (throwingKeys.includes(k)) throw new Error("storage full (partial)");
      store.set(k, String(v));
    },
    removeItem: (k) => {
      store.delete(k);
    },
    _store: store,
  };
}

beforeEach(() => {
  globalThis.localStorage = makeMemoryStorage();
});

// --- createProject / listProjects --------------------------------------

test("createProject registers a fresh project, sets it current, and returns it", () => {
  const { id, project } = createProject("Hat design");
  expect(typeof id).toBe("string");
  expect(id.length).toBeGreaterThan(0);
  expect(project).toEqual(defaultProject());
  expect(currentProjectId()).toBe(id);
  expect(listProjects()).toEqual([{ id, name: "Hat design", updatedAt: expect.any(Number) }]);
});

test("createProject defaults the name when omitted", () => {
  const { id } = createProject();
  expect(listProjects().find((p) => p.id === id).name).toBe("Untitled design");
});

test("createProject/duplicateProject mint distinct ids on consecutive calls", () => {
  const a = createProject("A");
  const b = createProject("B");
  expect(a.id).not.toBe(b.id);
  const c = duplicateProject(a.id);
  expect(c.id).not.toBe(a.id);
  expect(c.id).not.toBe(b.id);
});

// --- createProject/duplicateProject: partial storage failure --------------
// (record write succeeds, index write fails -- the exact "orphan record"
// hazard that used to poison auto-save for the rest of every future
// session, since saveProject/renameProject/deleteProject all treat an
// unindexed id as a no-op.)

test("createProject rolls back the record and does not set CURRENT_KEY when only the index write fails", () => {
  globalThis.localStorage = makePartialThrowingStorage(["embstudio:index"]);

  const { id, project } = createProject("Hat");

  // still returns a working in-memory project (degraded-but-consistent)
  expect(project).toEqual(defaultProject());
  // the record write that happened before the failed index write must be
  // undone -- no orphan record left behind
  expect(localStorage.getItem("embstudio:p:" + id)).toBeNull();
  // and CURRENT_KEY must NOT point at an id the index doesn't know about
  expect(currentProjectId()).toBeNull();
  expect(listProjects()).toEqual([]);
});

test("duplicateProject rolls back the new record and returns null when only the index write fails", () => {
  const { id } = createProject("Original"); // succeeds on normal memory storage
  const seed = Object.fromEntries(globalThis.localStorage._store);
  globalThis.localStorage = makePartialThrowingStorage(["embstudio:index"], seed);

  const before = listProjects();
  const dup = duplicateProject(id);

  expect(dup).toBeNull();
  expect(listProjects()).toEqual(before);
  // no unindexed duplicate record left behind under a new id
  const recordKeys = Array.from(globalThis.localStorage._store.keys()).filter((k) =>
    k.startsWith("embstudio:p:")
  );
  expect(recordKeys).toEqual(["embstudio:p:" + id]);
  // and the original is untouched
  expect(loadProject(id)).not.toBeNull();
});

test("listProjects is empty when nothing has been created", () => {
  expect(listProjects()).toEqual([]);
});

test("listProjects sorts by updatedAt descending, and saveProject re-bumps order", () => {
  vi.useFakeTimers();
  try {
    vi.setSystemTime(1000);
    const a = createProject("A");
    vi.setSystemTime(2000);
    const b = createProject("B");
    vi.setSystemTime(3000);
    const c = createProject("C");

    expect(listProjects().map((p) => p.id)).toEqual([c.id, b.id, a.id]);

    vi.setSystemTime(4000);
    saveProject(a.id, defaultProject());
    expect(listProjects().map((p) => p.id)).toEqual([a.id, c.id, b.id]);
  } finally {
    vi.useRealTimers();
  }
});

// --- loadProject / saveProject ------------------------------------------

test("loadProject returns null for an id that was never created", () => {
  expect(loadProject("nope")).toBeNull();
});

test("loadProject returns null for a corrupt record and leaves the raw record untouched", () => {
  const { id } = createProject("Hat");
  const key = "embstudio:p:" + id;
  localStorage.setItem(key, "{not valid json");

  expect(loadProject(id)).toBeNull();
  // the corrupt-but-maybe-recoverable raw string must survive the failed
  // load untouched -- NOT get silently replaced by a fresh defaultProject()
  // the way save.js's deserialize() would (see loadProject's own comment).
  expect(localStorage.getItem(key)).toBe("{not valid json");
  // and the record staying corrupt-on-disk must not have de-registered it
  expect(listProjects().find((p) => p.id === id)).not.toBeUndefined();
});

test("saveProject round-trips edits through loadProject", () => {
  const { id, project } = createProject("Hat");
  const edited = updateElement(project, "e1", { text: "Team" });
  saveProject(id, edited);
  expect(loadProject(id).elements[0].text).toBe("Team");
});

test("saveProject is a no-op for an id not in the index (never resurrects a deleted project)", () => {
  const before = listProjects();
  saveProject("ghost-id", defaultProject());
  expect(listProjects()).toEqual(before);
  expect(loadProject("ghost-id")).toBeNull();
});

// --- renameProject --------------------------------------------------------

test("renameProject updates the index entry's name", () => {
  const { id } = createProject("Old name");
  renameProject(id, "New name");
  expect(listProjects().find((p) => p.id === id).name).toBe("New name");
});

test("renameProject is a no-op for an unknown id", () => {
  const before = listProjects();
  renameProject("ghost-id", "New name");
  expect(listProjects()).toEqual(before);
});

// --- deleteProject ----------------------------------------------------------

test("deleteProject removes the entry and its record", () => {
  const { id } = createProject("Hat");
  deleteProject(id);
  expect(listProjects()).toEqual([]);
  expect(loadProject(id)).toBeNull();
});

test("deleteProject clears the current pointer only when deleting the current project", () => {
  const a = createProject("A");
  const b = createProject("B"); // current is now b
  deleteProject(a.id); // not current -> pointer untouched
  expect(currentProjectId()).toBe(b.id);

  deleteProject(b.id); // is current -> pointer cleared
  expect(currentProjectId()).toBeNull();
});

test("deleteProject is a no-op for an unknown id", () => {
  const { id } = createProject("A");
  const before = listProjects();
  deleteProject("ghost-id");
  expect(listProjects()).toEqual(before);
  expect(currentProjectId()).toBe(id);
});

// --- duplicateProject -------------------------------------------------------

test("duplicateProject copies the project content under a new id/name", () => {
  const { id, project } = createProject("Original");
  const edited = updateElement(project, "e1", { text: "Copy me" });
  saveProject(id, edited);

  const dup = duplicateProject(id);
  expect(dup).not.toBeNull();
  expect(dup.id).not.toBe(id);
  expect(dup.project.elements[0].text).toBe("Copy me");
  expect(listProjects().find((p) => p.id === dup.id).name).toBe("Original copy");
  // source untouched
  expect(loadProject(id).elements[0].text).toBe("Copy me");
});

test("duplicateProject accepts an explicit name", () => {
  const { id } = createProject("Original");
  const dup = duplicateProject(id, "My Copy");
  expect(listProjects().find((p) => p.id === dup.id).name).toBe("My Copy");
});

test("duplicateProject returns null for an unknown id and creates nothing", () => {
  const before = listProjects();
  expect(duplicateProject("ghost-id")).toBeNull();
  expect(listProjects()).toEqual(before);
});

// --- currentProjectId / setCurrentProject ---------------------------------

test("currentProjectId is null until something sets it", () => {
  expect(currentProjectId()).toBeNull();
});

test("setCurrentProject/currentProjectId round-trip", () => {
  const { id } = createProject("A");
  const other = createProject("B");
  setCurrentProject(id);
  expect(currentProjectId()).toBe(id);
  expect(currentProjectId()).not.toBe(other.id);
});

// --- migrateLegacy: v1 blob -------------------------------------------------

test("migrateLegacy converts a v1 legacy blob into a registry project named 'My first design'", () => {
  const v1 = {
    garmentId: "hat_front",
    text: "Crew",
    fontKey: "medium_font",
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
    colorRgb: [20, 20, 20],
    underlay: true,
    mode: "text",
    nColors: 4,
    removeBg: true,
    letterSpacingMm: 0,
  };
  localStorage.setItem("embstudio:last", JSON.stringify(v1));

  migrateLegacy();

  expect(localStorage.getItem("embstudio:last")).toBeNull();
  const id = currentProjectId();
  expect(id).toEqual(expect.any(String));
  expect(listProjects()).toEqual([{ id, name: "My first design", updatedAt: expect.any(Number) }]);
  const migrated = loadProject(id);
  expect(migrated.version).toBe(2);
  expect(migrated.garmentId).toBe("hat_front");
  expect(migrated.elements[0].text).toBe("Crew");
});

// --- migrateLegacy: v2 blob -------------------------------------------------

test("migrateLegacy converts a v2 legacy blob into a registry project", () => {
  const v2 = updateElement(defaultProject(), "e1", { text: "Already v2" });
  localStorage.setItem("embstudio:last", JSON.stringify(v2));

  migrateLegacy();

  expect(localStorage.getItem("embstudio:last")).toBeNull();
  const id = currentProjectId();
  const migrated = loadProject(id);
  expect(migrated.version).toBe(2);
  expect(migrated.elements[0].text).toBe("Already v2");
  expect(listProjects()).toHaveLength(1);
});

// --- migrateLegacy: corrupt blob --------------------------------------------

test("migrateLegacy leaves a corrupt/unparseable legacy blob untouched and creates nothing", () => {
  localStorage.setItem("embstudio:last", "{not valid json");

  migrateLegacy();

  expect(localStorage.getItem("embstudio:last")).toBe("{not valid json");
  expect(localStorage.getItem("embstudio:index")).toBeNull();
  expect(listProjects()).toEqual([]);
  expect(currentProjectId()).toBeNull();
});

// --- migrateLegacy: no-ops ---------------------------------------------------

test("migrateLegacy is a no-op when there is no legacy blob", () => {
  migrateLegacy();
  expect(listProjects()).toEqual([]);
  expect(currentProjectId()).toBeNull();
  expect(localStorage.getItem("embstudio:index")).toBeNull();
});

test("migrateLegacy is idempotent: a second call after a successful migration changes nothing", () => {
  localStorage.setItem("embstudio:last", JSON.stringify(defaultProject()));
  migrateLegacy();
  const firstIndex = listProjects();
  const firstCurrent = currentProjectId();

  migrateLegacy();

  expect(listProjects()).toEqual(firstIndex);
  expect(currentProjectId()).toBe(firstCurrent);
});

test("migrateLegacy does not run if an index already exists, even if a legacy blob is present", () => {
  createProject("Existing"); // creates the index
  localStorage.setItem("embstudio:last", JSON.stringify(defaultProject()));

  migrateLegacy();

  expect(listProjects()).toHaveLength(1);
  expect(listProjects()[0].name).toBe("Existing");
  // the (stray/unexpected) legacy blob is left alone since migration didn't run
  expect(localStorage.getItem("embstudio:last")).not.toBeNull();
});

// --- migrateLegacy: A1 write-ordering / no data loss on storage failure ----

test("A1: if setItem throws partway through migration, the legacy key survives and no partial index is created", () => {
  const v1 = { garmentId: "hat_front", text: "Crew", mode: "text" };
  globalThis.localStorage = makeThrowingStorage({ "embstudio:last": JSON.stringify(v1) });

  expect(() => migrateLegacy()).not.toThrow();

  expect(localStorage.getItem("embstudio:last")).toBe(JSON.stringify(v1));
  expect(localStorage.getItem("embstudio:index")).toBeNull();
  expect(localStorage.getItem("embstudio:current")).toBeNull();
});

test("A1: other localStorage ops also swallow a throwing setItem without crashing", () => {
  globalThis.localStorage = makeThrowingStorage();
  expect(() => createProject("A")).not.toThrow();
  expect(() => saveProject("x", defaultProject())).not.toThrow();
  expect(() => setCurrentProject("x")).not.toThrow();
});

// --- importProject (.embproj import, 2026-07-29 market-parity scope) -------

test("importProject registers a new entry under the given name WITHOUT touching the current pointer", () => {
  const { id: existingId } = createProject("Already open");
  const incoming = defaultProject();
  const result = importProject(incoming, "From a file");

  expect(result).not.toBeNull();
  expect(result.id).not.toBe(existingId);
  // like duplicateProject: the caller decides whether to open the import
  expect(currentProjectId()).toBe(existingId);
  const row = listProjects().find((p) => p.id === result.id);
  expect(row.name).toBe("From a file");
  // the stored record loads back as the same (migrated) project
  expect(loadProject(result.id)).toEqual(incoming);
});

test("importProject never overwrites: importing twice mints two independent entries", () => {
  const a = importProject(defaultProject(), "Same design");
  const b = importProject(defaultProject(), "Same design");
  expect(a.id).not.toBe(b.id);
  expect(listProjects()).toHaveLength(2);
});

test("importProject defaults the name when omitted", () => {
  const { id } = importProject(defaultProject());
  expect(listProjects().find((p) => p.id === id).name).toBe("Imported design");
});

test("importProject rolls back the record and returns null when only the index write fails", () => {
  globalThis.localStorage = makePartialThrowingStorage(["embstudio:index"]);
  const result = importProject(defaultProject(), "Doomed");
  expect(result).toBeNull();
  expect(listProjects()).toEqual([]);
  // no orphaned embstudio:p:<id> record left behind
  const keys = Array.from(globalThis.localStorage._store.keys());
  expect(keys.filter((k) => k.startsWith("embstudio:p:"))).toEqual([]);
});

test("importProject returns null (and does not throw) on total storage failure", () => {
  globalThis.localStorage = makeThrowingStorage();
  expect(importProject(defaultProject(), "X")).toBeNull();
});
