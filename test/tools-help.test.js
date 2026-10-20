// Every CLI under tools/*.mjs answers --help with its header comment and
// exits 0 without doing its work (several rewrite the font library or hit
// the network). Libraries that export helpers and have no CLI are listed.
import { test } from "node:test";
import assert from "node:assert";
import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";

const TOOLS = join(dirname(fileURLToPath(import.meta.url)), "..", "tools");
const LIBRARIES = new Set([
  "_help.mjs", "png.mjs", "font-license.mjs", "font-sample.mjs",
  "file-cut-import-set.mjs", "file-cut-satin-set.mjs", "file-cut-sweep-set.mjs",
]);

for (const f of readdirSync(TOOLS).filter((n) => n.endsWith(".mjs") && !LIBRARIES.has(n)).sort()) {
  test(`tools/${f} --help exits 0 with usage text`, () => {
    const cwd = mkdtempSync(join(tmpdir(), "tools-help-"));
    const r = spawnSync(process.execPath, [join(TOOLS, f), "--help"], { cwd, encoding: "utf8", timeout: 30000 });
    assert.strictEqual(r.status, 0, r.stderr);
    assert.ok(r.stdout.trim().length > 0, "printed nothing");
    assert.deepStrictEqual(readdirSync(cwd), [], "--help wrote files");
  });
}
