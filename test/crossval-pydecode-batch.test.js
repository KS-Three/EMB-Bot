// pyDecode must not hand every path to ONE python spawn.
//
// Windows CreateProcess caps a command line at 32,767 characters. PR #1306's
// codec fuzz test passed all 900 corpus paths (~64 chars each, ~58,500 in
// all) to one `pyDecode` call, so on any Windows box with the digitizer venv
// spawnSync failed with ENAMETOOLONG and `node --test` went red on a correct
// tree. CI is Linux (no such cap), so it stayed green there.
//
// Two checks: the pure batching helper (runs everywhere, so Linux CI guards
// the budget too), and a real decode of 900 long-named files (needs a python
// with pystitch; skips without one, except on CI).

const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

test("pyDecodeBatches: every batch's command line stays under the budget, order kept", async () => {
  const { pyDecodeBatches, PY_ARGV_BUDGET } = await import("../tools/crossval-stitch-formats.mjs");
  assert.ok(PY_ARGV_BUDGET < 32767, "budget must sit under the Windows CreateProcess cap");
  const files = [];
  for (let i = 0; i < 900; i++) {
    files.push(`C:\\Users\\EE-LT-~1\\AppData\\Local\\Temp\\emb-codec-fuzz-abcdef\\fuzz_${i}.dst`);
  }
  const batches = pyDecodeBatches(files);
  assert.ok(batches.length > 1, "900 long paths must not fit one spawn");
  for (const b of batches) {
    assert.ok(b.length >= 1);
    const chars = b.reduce((n, f) => n + f.length + 3, 0); // quotes + space per arg
    assert.ok(chars <= PY_ARGV_BUDGET, `batch of ${b.length} paths is ${chars} chars`);
  }
  assert.deepStrictEqual(batches.flat(), files);
  assert.deepStrictEqual(pyDecodeBatches([]), []);
  assert.deepStrictEqual(pyDecodeBatches(["a.dst"]), [["a.dst"]]);
});

test("pyDecode: 900 long-named files decode in one call (no ENAMETOOLONG)", async (t) => {
  const harness = await import("../tools/crossval-stitch-formats.mjs");
  const python = harness.resolvePython();
  if (!python) {
    if (process.env.CI) throw new Error("no python with pystitch, and CI is set: this check must run on CI.");
    t.skip("no python with pystitch available");
    return;
  }
  const { encodeDST } = require("../src/dst.js");
  const bytes = Buffer.from(encodeDST(harness.buildFixture({ withTrim: false })));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "emb-pydecode-batch-"));
  try {
    const files = [];
    for (let i = 0; i < 900; i++) {
      const f = path.join(dir, `fuzz_long_name_padding_${String(i).padStart(4, "0")}.dst`);
      fs.writeFileSync(f, bytes);
      files.push(f);
    }
    const decoded = harness.pyDecode(python, files);
    assert.strictEqual(Object.keys(decoded).length, 900);
    for (const f of files) {
      const d = decoded[path.basename(f)];
      assert.ok(d && d.stitches && d.stitches.length > 0, path.basename(f) + " not decoded");
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
