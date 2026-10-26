// tools/service-check.mjs: the launcher's decision about a digitizer already
// on 8721 (W3-14). The rules under test, in the order a customer meets them:
// keep a fresh service; keep a stale one that is working; report a stale idle
// one; replace it by default (Kent 2026-10-25), unless -KeepStale; never touch
// anything that is not a digitizer.
import { test } from "node:test";
import assert from "node:assert";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync, execFile } from "node:child_process";

const T = await import("../tools/service-check.mjs");

const REPO = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const HEAD = "7995d51512e47a39761956d56bf9faae963ac4ef";
const OLD = "0123456789abcdef0123456789abcdef01234567";
const IDLE = { jobs: 3, states: { done: 3 }, inflight: 0 };

function health({ commit = HEAD, dirty = false, jobs = IDLE, engine = true } = {}) {
  const h = { status: "ok", service: "digitizer", version: "0.6.0", jobs };
  if (engine) h.engine = { commit, dirty, started_at: "2026-10-25T12:00:00+00:00", defaults_sha: "0".repeat(64) };
  return h;
}
const verdict = (over) => T.decide({ status: "answered", head: HEAD, replace: true, health: health(), ...over });

// ---- keep (fresh) ----------------------------------------------------------

test("keep (fresh): the service's commit is HEAD and its tree was clean", () => {
  const v = verdict({});
  assert.strictEqual(v.action, "keep");
  assert.match(v.reason, /current \(commit 7995d51/);
  // Replacing by default changes nothing about a service that is not stale.
  assert.strictEqual(verdict({ replace: false }).action, "keep");
});

// ---- keep (busy) -----------------------------------------------------------

test("keep (busy): a stale service with a job running is never stopped, flag or not", () => {
  for (const jobs of [
    { jobs: 1, states: { running: 1 }, inflight: 1 },
    { jobs: 2, states: { queued: 1, done: 1 }, inflight: 1 },
    { jobs: 1, states: { done: 1 }, inflight: 1 },
  ]) {
    for (const replace of [false, true]) {
      const v = verdict({ health: health({ commit: OLD, jobs }), replace });
      assert.strictEqual(v.action, "busy", JSON.stringify(jobs));
      assert.match(v.reason, /STALE/);
      assert.match(v.reason, /keeping it/);
    }
  }
});

test("an unreadable jobs block counts as busy: an unknown is never idle", () => {
  for (const jobs of [undefined, null, "x", {}, { jobs: 0 }]) {
    const h = health({ commit: OLD });
    h.jobs = jobs;
    const v = verdict({ health: h, replace: true });
    assert.strictEqual(v.action, "busy", JSON.stringify(jobs));
  }
});

// ---- report (stale, idle, -KeepStale) --------------------------------------

test("report (stale and idle, -KeepStale): prints both commits and leaves it running", () => {
  const v = verdict({ health: health({ commit: OLD }), replace: false });
  assert.strictEqual(v.action, "report");
  assert.match(v.reason, /0123456/);
  assert.match(v.reason, /7995d51/);
  assert.match(v.reason, /-KeepStale/);
});

test("a service on HEAD that started with tracked edits is stale too", () => {
  assert.strictEqual(verdict({ health: health({ dirty: true }) }).action, "replace");
  const v = verdict({ health: health({ dirty: true }), replace: false });
  assert.strictEqual(v.action, "report");
  assert.match(v.reason, /dirty/);
});

test("a digitizer with no engine stamp predates this checkout: stale", () => {
  assert.strictEqual(verdict({ health: health({ engine: false }) }).action, "replace");
  const v = verdict({ health: health({ engine: false }), replace: false });
  assert.strictEqual(v.action, "report");
  assert.match(v.reason, /no engine stamp/);
  assert.strictEqual(verdict({ health: health({ engine: false, jobs: { states: { running: 1 } } }) }).action, "busy");
});

// ---- replace (stale, idle: the default) ------------------------------------

test("replace (stale, idle, the default): the only path that stops a service", () => {
  const v = verdict({ health: health({ commit: OLD }) });
  assert.strictEqual(v.action, "replace");
  assert.strictEqual(v.serviceCommit, OLD);
  assert.strictEqual(v.headCommit, HEAD);
  assert.match(v.reason, /0123456/);
  assert.match(v.reason, /7995d51/);
  const actions = new Set();
  for (const h of [health(), health({ commit: OLD }), health({ commit: OLD, jobs: { inflight: 1 } }), health({ dirty: true })]) {
    actions.add(verdict({ health: h }).action);
  }
  assert.deepStrictEqual([...actions].sort(), ["busy", "keep", "replace"]);
  // -KeepStale turns the same inputs into a report, never a stop.
  const kept = new Set();
  for (const h of [health(), health({ commit: OLD }), health({ commit: OLD, jobs: { inflight: 1 } }), health({ dirty: true })]) {
    kept.add(verdict({ health: h, replace: false }).action);
  }
  assert.deepStrictEqual([...kept].sort(), ["busy", "keep", "report"]);
});

test("cannot tell is keep, never replace: no commit on either side", () => {
  assert.strictEqual(verdict({ health: health({ commit: null }), replace: true }).action, "keep");
  assert.strictEqual(verdict({ head: null, replace: true, health: health({ commit: OLD }) }).action, "keep");
});

// ---- never touching anything that is not a digitizer -----------------------

test("a non-digitizer service on the port is foreign: not stopped, not started over", () => {
  for (const health_ of [{ service: "vite" }, { status: "ok" }, [], "ok", null]) {
    for (const replace of [false, true]) {
      const v = T.decide({ status: "answered", health: health_, head: HEAD, replace });
      assert.strictEqual(v.action, "foreign", JSON.stringify(health_));
      assert.match(v.reason, /leaving it alone/);
    }
  }
  // Held but not answering: also left alone.
  assert.strictEqual(T.decide({ status: "unknown", health: null, head: HEAD, replace: true }).action, "foreign");
});

test("only a free port starts a digitizer", () => {
  assert.strictEqual(T.decide({ status: "down", health: null, head: HEAD }).action, "start");
});

// ---- probe -----------------------------------------------------------------

test("probe tells a free port from a held one", async () => {
  const refused = () => Promise.reject(Object.assign(new TypeError("fetch failed"), { cause: { code: "ECONNREFUSED" } }));
  const timed = () => Promise.reject(Object.assign(new Error("t"), { name: "TimeoutError" }));
  const reset = () => Promise.reject(Object.assign(new TypeError("fetch failed"), { cause: { code: "ECONNRESET" } }));
  assert.strictEqual((await T.probe(undefined, { fetchImpl: refused })).status, "down");
  assert.strictEqual((await T.probe(undefined, { fetchImpl: timed })).status, "unknown");
  assert.strictEqual((await T.probe(undefined, { fetchImpl: reset })).status, "unknown");
  assert.strictEqual((await T.probe(undefined, { fetchImpl: async () => ({ ok: false }) })).status, "unknown");
  assert.strictEqual((await T.probe(undefined, { fetchImpl: async () => ({ ok: true, json: async () => { throw new Error("x"); } }) })).status, "unknown");
  const got = await T.probe(undefined, { fetchImpl: async () => ({ ok: true, json: async () => health() }) });
  assert.strictEqual(got.status, "answered");
  assert.strictEqual(got.health.service, "digitizer");
});

test("waitHealthy waits for a digitizer, not for any listener", async () => {
  let t = 0;
  const clock = { now: () => t, sleep: async (ms) => { t += ms; } };
  let calls = 0;
  const flaky = async () => {
    calls += 1;
    if (calls < 3) throw Object.assign(new TypeError("x"), { cause: { code: "ECONNREFUSED" } });
    return { ok: true, json: async () => (calls === 3 ? { service: "vite" } : health()) };
  };
  const r = await T.waitHealthy(undefined, { fetchImpl: flaky, timeoutMs: 30000, intervalMs: 1000, ...clock });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(calls, 4, "refused, refused, a non-digitizer, then the digitizer");
  const never = await T.waitHealthy(undefined, {
    fetchImpl: async () => { throw Object.assign(new TypeError("x"), { cause: { code: "ECONNREFUSED" } }); },
    timeoutMs: 5000, intervalMs: 1000, ...clock,
  });
  assert.strictEqual(never.ok, false);
});

test("jobsBusy reads JobRegistry.stats()", () => {
  assert.strictEqual(T.jobsBusy({ jobs: 0, states: {}, inflight: 0 }).busy, false);
  assert.strictEqual(T.jobsBusy({ jobs: 5, states: { done: 4, error: 1 }, inflight: 0 }).busy, false);
  assert.match(T.jobsBusy({ states: { running: 1, queued: 2 }, inflight: 3 }).why, /1 running, 2 queued/);
});

// ---- the CLI the launcher calls, against real sockets ----------------------
// Node starts in ~3 s on the laptop, so the calls run side by side.

function serve(handler) {
  return new Promise((resolve) => {
    const s = http.createServer(handler);
    s.listen(0, "127.0.0.1", () => resolve({ s, url: `http://127.0.0.1:${s.address().port}` }));
  });
}
function cli(args) {
  return new Promise((resolve, reject) => {
    execFile(process.execPath, [path.join(REPO, "tools", "service-check.mjs"), ...args],
      { cwd: REPO, encoding: "utf8", timeout: 60000 },
      (err, stdout, stderr) => (err && typeof err.code !== "number" ? reject(err) : resolve({ code: err ? err.code : 0, stdout, stderr })));
  });
}
const json = (res, body, code = 200) => { res.writeHead(code, { "Content-Type": "application/json" }); res.end(JSON.stringify(body)); };

test("CLI: one JSON verdict per service, HEAD read from the repo, /health only ever read", async () => {
  const head = execFileSync("git", ["rev-parse", "HEAD"], { cwd: REPO, encoding: "utf8" }).trim();
  const hits = [];
  const mk = (body, type = "json") => serve((req, res) => {
    hits.push(req.method + " " + req.url);
    if (type === "json") json(res, body);
    else { res.writeHead(200, { "Content-Type": "text/html" }); res.end(body); }
  });
  const busy = { jobs: 1, states: { running: 1 }, inflight: 1 };
  const fresh = await mk(health({ commit: head }));
  const stale = await mk(health({ commit: OLD }));
  const working = await mk(health({ commit: OLD, jobs: busy }));
  const vite = await mk({ service: "not-the-digitizer" });
  const page = await mk("<html>hi</html>", "html");
  // Bind then close: the OS now refuses connections on that port.
  const gone = await mk({});
  await new Promise((r) => gone.s.close(r));
  const servers = [fresh, stale, working, vite, page];
  try {
    const run = (u, ...extra) => cli(["--url", u, "--json", ...extra]).then((r) => JSON.parse(r.stdout));
    const got = await Promise.all([
      run(fresh.url), run(stale.url, "--keep-stale"), run(stale.url),
      run(working.url), run(vite.url), run(page.url), run(gone.url),
    ]);
    assert.deepStrictEqual(got.map((v) => v.action),
      ["keep", "report", "replace", "busy", "foreign", "foreign", "start"], got.map((v) => v.reason).join("; "));
    assert.ok(hits.length > 0 && hits.every((h) => h === "GET /health"), hits.join(", "));
  } finally {
    for (const { s } of servers) s.close();
  }
});

test("CLI --wait: exits 0 once a digitizer answers, 1 when only something else does", async () => {
  const up = await serve((req, res) => json(res, health()));
  const other = await serve((req, res) => json(res, { service: "vite" }));
  try {
    const [a, b] = await Promise.all([cli(["--url", up.url, "--wait", "5"]), cli(["--url", other.url, "--wait", "2"])]);
    assert.strictEqual(a.code, 0, a.stdout + a.stderr);
    assert.strictEqual(b.code, 1, b.stdout + b.stderr);
  } finally {
    up.s.close();
    other.s.close();
  }
});
