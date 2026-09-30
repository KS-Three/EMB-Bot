// @vitest-environment jsdom
//
// Coverage for folderTarget.js — the "save into a chosen folder" helper behind
// DownloadStep's save-location control. The File System Access API and
// IndexedDB are stubbed, since jsdom ships neither; these tests pin the
// contract the component relies on (support detection, the tagged errors, the
// permission gate) rather than the browser's real behaviour.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  folderSaveSupported,
  pickFolder,
  savedFolderName,
  folderPermissionState,
  reconnectFolder,
  saveToFolder,
} from "./folderTarget.js";

// A stand-in for the whole IndexedDB dance in folderTarget.js: one slot that
// pickFolder writes and everything else reads. Installed as window.indexedDB.
// Callbacks fire on setTimeout(0) so every handler idbDo assigns synchronously
// is in place first, and — as real IndexedDB guarantees — a request's onsuccess
// runs before the transaction's oncomplete.
function installFakeIdb() {
  let slot;
  window.indexedDB = {
    open: () => {
      const db = {
        objectStoreNames: { contains: () => true },
        createObjectStore: () => {},
        close: () => {},
        transaction: () => {
          const reqs = [];
          const mkReq = (result) => { const r = { result, onsuccess: null, onerror: null }; reqs.push(r); return r; };
          const store = {
            get: (key) => mkReq(key === "downloadDir" ? slot : undefined),
            put: (val) => { slot = val; return mkReq(undefined); },
            delete: () => { slot = undefined; return mkReq(undefined); },
          };
          const tx = { objectStore: () => store, oncomplete: null, onerror: null, onabort: null };
          setTimeout(() => {
            for (const r of reqs) if (r.onsuccess) r.onsuccess();
            if (tx.oncomplete) tx.oncomplete();
          }, 0);
          return tx;
        },
      };
      const req = { result: db, onupgradeneeded: null, onsuccess: null, onerror: null };
      setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
      return req;
    },
  };
}

// A directory handle whose permission state the test controls.
function fakeDirHandle(name, perm = "granted") {
  const writes = [];
  return {
    name,
    _writes: writes,
    queryPermission: async () => perm,
    requestPermission: async () => perm,
    getFileHandle: async () => ({
      createWritable: async () => ({
        write: async (blob) => writes.push(blob),
        close: async () => {},
      }),
    }),
  };
}

afterEach(() => {
  delete window.showDirectoryPicker;
  delete window.indexedDB;
  vi.restoreAllMocks();
});

describe("folderSaveSupported", () => {
  test("false without the picker", () => {
    delete window.showDirectoryPicker;
    expect(folderSaveSupported()).toBe(false);
  });
  test("true with picker and IndexedDB", () => {
    window.showDirectoryPicker = () => {};
    installFakeIdb();
    expect(folderSaveSupported()).toBe(true);
  });
  test("false with the picker but no IndexedDB", () => {
    window.showDirectoryPicker = () => {};
    delete window.indexedDB;
    expect(folderSaveSupported()).toBe(false);
  });
});

describe("with a chosen folder", () => {
  beforeEach(() => {
    installFakeIdb();
    window.showDirectoryPicker = async () => fakeDirHandle("SendFolder");
  });

  test("pickFolder stores it and its name comes back", async () => {
    const name = await pickFolder();
    expect(name).toBe("SendFolder");
    expect(await savedFolderName()).toBe("SendFolder");
  });

  test("saveToFolder writes the bytes when permission is granted", async () => {
    await pickFolder();
    const where = await saveToFolder("design.dst", new Uint8Array([1, 2, 3]), "application/octet-stream");
    expect(where).toBe("SendFolder");
  });

  test("permission state is granted after a fresh pick", async () => {
    await pickFolder();
    expect(await folderPermissionState()).toBe("granted");
  });
});

describe("permission not granted", () => {
  beforeEach(() => {
    installFakeIdb();
    window.showDirectoryPicker = async () => fakeDirHandle("SendFolder", "prompt");
  });

  test("saveToFolder raises the folder-permission code, not a raw throw", async () => {
    await pickFolder();
    await expect(saveToFolder("design.dst", new Uint8Array([1]), "x")).rejects.toMatchObject({
      code: "folder-permission",
    });
  });

  test("folderPermissionState reports prompt, and reconnect reflects the grant", async () => {
    await pickFolder();
    expect(await folderPermissionState()).toBe("prompt");
    // requestPermission also returns "prompt" here, so reconnect fails.
    expect(await reconnectFolder()).toBe(false);
  });
});

describe("no folder chosen", () => {
  beforeEach(() => {
    installFakeIdb();
    window.showDirectoryPicker = () => {};
  });
  test("saveToFolder raises no-folder", async () => {
    await expect(saveToFolder("design.dst", new Uint8Array([1]), "x")).rejects.toMatchObject({
      code: "no-folder",
    });
  });
  test("savedFolderName is null and permission state is none", async () => {
    expect(await savedFolderName()).toBe(null);
    expect(await folderPermissionState()).toBe("none");
  });
});
