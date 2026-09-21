// projectFile.js — the .embproj on-disk design file (2026-07-29 market-parity
// launch scope): a JSON envelope around the exact serialized project shape
// the localStorage registry stores, so a design can be backed up, moved to
// another machine, or sent to someone without any backend. localStorage is
// ephemeral (a browser cache clear wipes every saved design); this file is
// the durable escape hatch.
//
// Pure string-in/string-out on purpose: the file-picker/download plumbing
// lives in App.svelte + download.js, so everything here is unit-testable.
//
// Since 2026-09-20 the envelope also carries the customer's ORIGINAL artwork
// bytes — `sources`, keyed by the SHA-256 the source store uses
// (lib/sourceStore.js) — BESIDE the project, never inside it. A digitize
// sends the file, not the panel's 1,200-px preview (DOCTRINE 2026-09-19/20:
// the preview cost the nine corpus logos 503 -> 609 trims), and the file
// lives in IndexedDB, which does not travel: a design opened on another
// machine, or after cleared site data, re-digitized from the preview with a
// note. So the export writes every stored original its elements point at,
// base64 in the envelope, and the import puts them back in the store
// (lib/projectSources.js) before the project is registered. `project` here
// is the very object the registry stores, so the localStorage record stays
// byte-free by construction — the bytes have no path into it.

import { migrateProject, looksLikeProject } from "./project.js";

export const PROJECT_FILE_FORMAT = "embproj";
// 2 (2026-09-20): the envelope may carry `sources`. Parsing never keys on
// this number — a version-1 file parses identically, with no sources — so
// the bump is a stamp for a human reading the file, not a gate.
export const PROJECT_FILE_VERSION = 2;

// One original may be up to the service's 12 MB upload limit. A `sources`
// entry past this was not written by this app for this service and is
// dropped on import rather than decoded into memory; the check runs on the
// base64 length BEFORE decoding, so the refusal costs nothing.
export const SOURCE_MAX_BYTES = 64 * 1024 * 1024;

// The originals a project points at: every digitized element's
// `sourceFile.key`, once each (two elements made from one upload share one
// record — the store is content-addressed).
export function sourceKeysOf(project) {
  const keys = [];
  const elements = project && Array.isArray(project.elements) ? project.elements : [];
  for (const el of elements) {
    const key =
      el && el.type === "digitized" && el.sourceFile && typeof el.sourceFile.key === "string"
        ? el.sourceFile.key
        : "";
    if (key && !keys.includes(key)) keys.push(key);
  }
  return keys;
}

// Bytes <-> base64, chunked so a 12 MB original never hits the argument
// limit of String.fromCharCode.apply. decodeBase64 returns null for anything
// that is not base64 rather than throwing: a malformed entry is dropped, the
// design still imports.
export function encodeBase64(bytes) {
  let bin = "";
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

export function decodeBase64(text) {
  if (typeof text !== "string" || text.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(text)) return null;
  let bin;
  try {
    bin = atob(text);
  } catch (e) {
    return null;
  }
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// The envelope carries its own format/version stamps (so parse can reject
// non-design JSON outright) plus the display name — the registry keeps
// names in its index, not in the project record, so without this the name
// would be lost in transit.
//
// `sources` is what the store handed back for this project's keys
// (projectSources.js `collectSources`): { key: { bytes, type, name } }. Only
// keys an element actually points at are written, so a stale map cannot
// smuggle a stranger's artwork into someone's design file, and a project
// with no stored originals writes the same envelope it always did — no
// `sources` member at all.
export function buildProjectFile(project, name, sources = null) {
  const envelope = {
    format: PROJECT_FILE_FORMAT,
    version: PROJECT_FILE_VERSION,
    name: name || "Untitled design",
    savedAt: new Date().toISOString(),
    project,
  };
  const embedded = {};
  if (sources && typeof sources === "object") {
    for (const key of sourceKeysOf(project)) {
      const rec = sources[key];
      if (!rec || !(rec.bytes instanceof Uint8Array) || rec.bytes.length === 0) continue;
      embedded[key] = {
        type: typeof rec.type === "string" ? rec.type : "",
        name: typeof rec.name === "string" ? rec.name : "",
        size: rec.bytes.length,
        data: encodeBase64(rec.bytes),
      };
    }
  }
  if (Object.keys(embedded).length) envelope.sources = embedded;
  return JSON.stringify(envelope, null, 1);
}

// "Fritsch's Stitches: Hat #2" -> "fritsch-s-stitches-hat-2.embproj"
export function projectFileName(name) {
  const base = (name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return (base || "design") + ".embproj";
}

// Returns { name, project, sources } (project already migrated to the
// current version; sources the originals the file carried for ITS elements,
// { key: { bytes, type, name } }, {} when it carried none) or null for
// anything that isn't a design file. The shape gate
// here is load-bearing: migrateProject() never throws — it normalizes ANY
// object into a valid project (unrecognizable input becomes a blank
// defaultProject()) — so without the gate, importing a random .json would
// "succeed" as an empty design instead of being rejected. Two accepted
// shapes:
//   1. the .embproj envelope written by buildProjectFile (any version —
//      the inner project's own migration handles forward compat), and
//   2. a bare project record (a raw embstudio:p:<id> value hand-rescued
//      from localStorage).
//
// BOTH shapes gate on the same `looksLikeProject` the migrator itself
// branches on, and that is the whole point (2026-09-14). Until then the two
// disagreed: the envelope branch waved through any inner payload on the
// strength of the "handles forward compat" promise in the line above, which
// migrateProject did not keep — it matched `version === 2` exactly and blanked
// the rest. So an envelope wrapping a v3 save, a `"2"` string stamp, or a
// record that lost its version key imported as an EMPTY design carrying the
// customer's own file name, reported as success. Sharing the recognizer is
// what stops the gate and the migrator drifting apart again; the migrator now
// also recovers those three instead of discarding them, so this rejection path
// is reached only by input with no design in it at all.
//
// `sources` is read the same defensively as the project: an entry that is not
// an object, whose data is not base64, that decodes to nothing or to more
// than `opts.maxSourceBytes` (SOURCE_MAX_BYTES), or that no element points
// at is dropped and the design imports without it — that element then
// digitizes from its preview, with the panel's note, exactly as it would
// have from a file saved before originals travelled.
export function parseProjectFile(text, opts = {}) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    return null;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;

  if (parsed.format === PROJECT_FILE_FORMAT) {
    if (!looksLikeProject(parsed.project)) return null;
    const name =
      typeof parsed.name === "string" && parsed.name.trim() ? parsed.name.trim() : "Imported design";
    const project = migrateProject(parsed.project);
    return { name, project, sources: parseSources(parsed.sources, project, opts.maxSourceBytes) };
  }

  if (looksLikeProject(parsed)) {
    return { name: "Imported design", project: migrateProject(parsed), sources: {} };
  }

  return null;
}

function parseSources(raw, project, maxBytes = SOURCE_MAX_BYTES) {
  const out = {};
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return out;
  const limit = Number.isFinite(maxBytes) && maxBytes > 0 ? maxBytes : SOURCE_MAX_BYTES;
  for (const key of sourceKeysOf(project)) {
    const entry = raw[key];
    if (!entry || typeof entry !== "object" || typeof entry.data !== "string") continue;
    // 4 base64 characters per 3 bytes: refuse an oversize entry unread.
    if (entry.data.length > Math.ceil(limit / 3) * 4) continue;
    const bytes = decodeBase64(entry.data);
    if (!bytes || bytes.length === 0 || bytes.length > limit) continue;
    out[key] = {
      bytes,
      type: typeof entry.type === "string" ? entry.type : "",
      name: typeof entry.name === "string" ? entry.name : "",
    };
  }
  return out;
}
