// "Jumps per trim": encodeDST(design, { jumpsPerTrim: N }) writes N consecutive
// jump records for a trim, N an integer 1..10, default 3. Default (and any
// invalid value) must leave every existing file byte-identical.
//
// The pystitch half reads each file back with `trim_at: N` — the reader's own
// name for "N consecutive jumps are a trim" — and needs a Python with pystitch
// (same resolver as the crossval harness); it skips on a box without one,
// except under CI, where it must run.
const assert = require("node:assert");
const { test } = require("node:test");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const dst = require("../src/dst.js");
const { decodeDST } = require("../src/dstimport.js");

const HEADER = 512;
const S = (x, y, type = "stitch") => ({ x, y, type });
const design = (stitches) => ({ stitches, colors: [{ r: 0, g: 0, b: 0, name: "c" }] });
const body = (out) => {
  const recs = [];
  for (let i = HEADER; i + 5 < out.length; i += 3) recs.push([out[i], out[i + 1], out[i + 2]]);
  return recs;
};
const jumps = (out) => body(out).filter((r) => (r[2] & 0xc0) === 0x80).length;

// Zero-travel trim (the shape the service adapter and the shape builder emit)
// and a trim with real travel.
const ZERO = design([S(0, 0), S(10, 0), S(10, 0, "trim"), S(40, 0), S(50, 0)]);
const MOVED = design([S(0, 0), S(10, 0), S(30, 20, "trim"), S(40, 0)]);

const SIZES = [1, 2, 3, 5, 10];

test("jumpsPerTrim N writes exactly N jump records for a trim", () => {
  for (const n of SIZES) {
    assert.strictEqual(jumps(dst.encodeDST(ZERO, { jumpsPerTrim: n })), n, `zero-travel trim, N=${n}`);
    assert.strictEqual(jumps(dst.encodeDST(MOVED, { jumpsPerTrim: n })), n, `trim with travel, N=${n}`);
  }
});

test("trim travel still lands where the design says, for every N", () => {
  for (const n of SIZES) {
    const recs = body(dst.encodeDST(MOVED, { jumpsPerTrim: n }));
    // Sum the jump deltas through the importer's own decoder: it sees the
    // same final position whatever N is.
    const back = decodeDST(dst.encodeDST(MOVED, { jumpsPerTrim: n }));
    const last = back.stitches[back.stitches.length - 1];
    const ref = decodeDST(dst.encodeDST(MOVED));
    const refLast = ref.stitches[ref.stitches.length - 1];
    assert.deepStrictEqual([last.x, last.y], [refLast.x, refLast.y], `N=${n}`);
    assert.ok(recs.length > 0);
  }
});

test("default is 3 and byte-identical to the writer with no option", () => {
  for (const d of [ZERO, MOVED]) {
    const plain = Buffer.from(dst.encodeDST(d));
    assert.ok(plain.equals(Buffer.from(dst.encodeDST(d, {}))));
    assert.ok(plain.equals(Buffer.from(dst.encodeDST(d, { jumpsPerTrim: 3 }))));
    assert.ok(plain.equals(Buffer.from(dst.encodeDST(d, { jumpsPerTrim: undefined }))));
  }
});

test("an unusable jumpsPerTrim falls back to 3 rather than changing the bytes", () => {
  const plain = Buffer.from(dst.encodeDST(ZERO));
  for (const bad of [0, 11, -1, 2.5, NaN, "x", null, true]) {
    assert.ok(plain.equals(Buffer.from(dst.encodeDST(ZERO, { jumpsPerTrim: bad }))), String(bad));
  }
});

test("a design with no trims is unchanged by the option", () => {
  const d = design([S(0, 0), S(10, 0), S(60, 0, "jump"), S(70, 0)]);
  const plain = Buffer.from(dst.encodeDST(d));
  for (const n of SIZES) assert.ok(plain.equals(Buffer.from(dst.encodeDST(d, { jumpsPerTrim: n }))), `N=${n}`);
});

test("pystitch reads the file back with a TRIM where the setting says", async (t) => {
  const harness = await import("../tools/crossval-stitch-formats.mjs");
  const python = harness.resolvePython();
  if (!python) {
    if (process.env.CI) throw new Error("no python with pystitch available, and CI is set");
    t.skip("no python with pystitch available");
    return;
  }
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jpt-"));
  try {
    const script = [
      "import sys, pystitch",
      "p, n = sys.argv[1], int(sys.argv[2])",
      "pat = pystitch.read(p, {'trim_at': n})",
      "print(sum(1 for s in pat.stitches if (s[2] & pystitch.COMMAND_MASK) == pystitch.TRIM))",
    ].join("\n");
    for (const n of SIZES) {
      const file = path.join(dir, `n${n}.dst`);
      fs.writeFileSync(file, Buffer.from(dst.encodeDST(ZERO, { jumpsPerTrim: n })));
      const r = spawnSync(python, ["-c", script, file, String(n)], { encoding: "utf8" });
      assert.strictEqual(r.status, 0, r.stderr);
      assert.strictEqual(Number(r.stdout.trim()), 1, `N=${n}: pystitch should see one TRIM`);
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
