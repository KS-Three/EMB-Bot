// projectFile.js — the .embproj on-disk design file (2026-07-29 market-parity
// launch scope): a JSON envelope around the exact serialized project shape
// the localStorage registry stores, so a design can be backed up, moved to
// another machine, or sent to someone without any backend. localStorage is
// ephemeral (a browser cache clear wipes every saved design); this file is
// the durable escape hatch.
//
// Pure string-in/string-out on purpose: the file-picker/download plumbing
// lives in App.svelte + download.js, so everything here is unit-testable.

import { migrateProject, looksLikeProject } from "./project.js";

export const PROJECT_FILE_FORMAT = "embproj";
export const PROJECT_FILE_VERSION = 1;

// The envelope carries its own format/version stamps (so parse can reject
// non-design JSON outright) plus the display name — the registry keeps
// names in its index, not in the project record, so without this the name
// would be lost in transit.
export function buildProjectFile(project, name) {
  return JSON.stringify(
    {
      format: PROJECT_FILE_FORMAT,
      version: PROJECT_FILE_VERSION,
      name: name || "Untitled design",
      savedAt: new Date().toISOString(),
      project,
    },
    null,
    1
  );
}

// "Fritsch's Stitches: Hat #2" -> "fritsch-s-stitches-hat-2.embproj"
export function projectFileName(name) {
  const base = (name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return (base || "design") + ".embproj";
}

// Returns { name, project } (project already migrated to the current
// version) or null for anything that isn't a design file. The shape gate
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
export function parseProjectFile(text) {
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
    return { name, project: migrateProject(parsed.project) };
  }

  if (looksLikeProject(parsed)) {
    return { name: "Imported design", project: migrateProject(parsed) };
  }

  return null;
}
