// tools/ci-e2e-shard-check.mjs is what the required `studio-e2e` check runs
// over its two shards' reports. A checker that passes the wrong thing would
// let a missing shard, a skipped file or a double-run test go green, so every
// way it must FAIL is pinned here on small made-up reports in the shape
// Playwright's JSON reporter writes (top-level suites are files; describe
// blocks nest; each spec carries tests[] with projectName and status).
const assert = require("node:assert");
const { test, before } = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

let check;
before(async () => {
  ({ check } = await import("../tools/ci-e2e-shard-check.mjs"));
});

const spec = (file, line, title, status = "expected") => ({
  title, file, line, column: 1, tests: [{ projectName: "chromium", status }],
});
const report = (...specs) => {
  const byFile = new Map();
  for (const s of specs) byFile.set(s.file, [...(byFile.get(s.file) ?? []), s]);
  return { suites: [...byFile].map(([file, ss]) => ({ title: file, file, specs: ss, suites: [] })) };
};
// The whole suite, as --list reports it (status "skipped", nothing ran yet).
const LIST = report(spec("a.spec.js", 1, "a1", "skipped"), spec("a.spec.js", 9, "a2", "skipped"),
  spec("b.spec.js", 3, "b1", "skipped"), spec("c.spec.js", 5, "c1", "skipped"));

function layout(shards) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "e2e-shard-check-"));
  shards.forEach((s, i) => {
    const d = path.join(dir, `studio-e2e-shard-${i + 1}`);
    fs.mkdirSync(d);
    fs.writeFileSync(path.join(d, "shard.json"), JSON.stringify(s.meta ?? { shard: i + 1, of: shards.length }));
    fs.writeFileSync(path.join(d, "list.json"), JSON.stringify(s.list ?? LIST));
    fs.writeFileSync(path.join(d, "results-parallel.json"), JSON.stringify(s.parallel ?? report()));
    fs.writeFileSync(path.join(d, "results.json"), JSON.stringify(s.serial ?? report()));
  });
  return dir;
}

const GOOD = () => [
  { parallel: report(spec("a.spec.js", 1, "a1"), spec("a.spec.js", 9, "a2", "flaky")), serial: report(spec("c.spec.js", 5, "c1")) },
  { parallel: report(spec("b.spec.js", 3, "b1")) },
];

test("two shards that split the list between them pass", () => {
  const r = check(layout(GOOD()));
  assert.deepStrictEqual(r.errors, []);
  assert.strictEqual(r.collected, 4);
  assert.strictEqual(r.ran, 4);
});

test("a test no shard ran fails", () => {
  const s = GOOD();
  s[1].parallel = report();
  assert.match(check(layout(s)).errors.join("\n"), /never ran: b\.spec\.js:3:1 › b1/);
});

test("a test that only skipped counts as never run", () => {
  const s = GOOD();
  s[1].parallel = report(spec("b.spec.js", 3, "b1", "skipped"));
  assert.match(check(layout(s)).errors.join("\n"), /never ran: b\.spec\.js/);
});

test("a test run on both shards fails", () => {
  const s = GOOD();
  s[1].serial = report(spec("c.spec.js", 5, "c1"));
  assert.match(check(layout(s)).errors.join("\n"), /ran 2 times .* c\.spec\.js:5:1 › c1/);
});

test("a failed test fails", () => {
  const s = GOOD();
  s[0].serial = report(spec("c.spec.js", 5, "c1", "unexpected"));
  assert.match(check(layout(s)).errors.join("\n"), /unexpected: c\.spec\.js/);
});

test("a missing shard fails, even if the one present ran everything", () => {
  const all = { parallel: report(spec("a.spec.js", 1, "a1"), spec("a.spec.js", 9, "a2"), spec("b.spec.js", 3, "b1"), spec("c.spec.js", 5, "c1")), meta: { shard: 1, of: 2 } };
  assert.match(check(layout([all])).errors.join("\n"), /one shard each for 1\.\.2/);
});

test("shards that collected different lists fail", () => {
  const s = GOOD();
  s[1].list = report(spec("a.spec.js", 1, "a1", "skipped"), spec("b.spec.js", 3, "b1", "skipped"));
  assert.match(check(layout(s)).errors.join("\n"), /collected a different list/);
});

test("a report holding a test outside the collected list fails", () => {
  const s = GOOD();
  s[1].serial = report(spec("z.spec.js", 1, "zz"));
  assert.match(check(layout(s)).errors.join("\n"), /lacks: z\.spec\.js/);
});

test("an empty collected list fails rather than proving nothing", () => {
  assert.match(check(layout([{ list: report() }, { list: report() }])).errors.join("\n"), /collected list is empty/);
});

test("same title in two describe blocks are two tests", () => {
  const list = { suites: [{ title: "d.spec.js", file: "d.spec.js", specs: [], suites: [
    { title: "on", file: "d.spec.js", specs: [spec("d.spec.js", 4, "t", "skipped")], suites: [] },
    { title: "off", file: "d.spec.js", specs: [spec("d.spec.js", 4, "t", "skipped")], suites: [] },
  ] }] };
  const ran = JSON.parse(JSON.stringify(list).replaceAll('"skipped"', '"expected"'));
  assert.deepStrictEqual(check(layout([{ list, parallel: ran }, { list }])).errors, []);
});
