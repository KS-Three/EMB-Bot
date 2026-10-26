// Is the digitizer service on this port the engine this checkout would run?
// (W3-14, 2026-10-25.) The decision half of tools/start-emb-bot.ps1; the
// launcher only does what this says.
//
// Why. On 2026-10-15 four of Kent's five red circles were a stale service on
// port 8721 holding old code; nothing told him. /health now names the engine
// that answered (`engine.commit`, `engine.dirty`; digitizer_service/app.py),
// and this compares it with HEAD.
//
// STALE means exactly this: /health says service=digitizer AND its engine
// commit differs from HEAD, or its tracked tree was dirty when it started. A
// digitizer that answers with no `engine` block predates the stamp, so its
// code is older than this checkout's: stale. One that has an `engine` block
// with no commit (git was missing when it started) cannot be judged, and is
// kept.
//
// The rules the launcher lives by:
//   * Other sessions run services from their own lanes on 8721 for e2e. A
//     service whose /health `jobs` shows work in flight (or that does not say)
//     is NEVER stopped: the verdict is "keep", with the reason printed.
//   * Anything on the port that is not a digitizer, or does not answer, is
//     never touched and never started over.
//   * A stale, idle service is REPLACED, with both commits printed (Kent's
//     ruling 2026-10-25: "Replace automatically"). `--keep-stale` (the
//     launcher's -KeepStale) is the opt-out: it is then only reported.
//
// Verdict `action`: start | keep | busy | report | replace | foreign.
//
// Usage:
//   node tools/service-check.mjs                    # human lines, exit 0
//   node tools/service-check.mjs --json [--keep-stale] # one JSON object, for the launcher
//   node tools/service-check.mjs --wait 90          # exit 0 once /health says digitizer, 1 after 90 s
//   options: --url http://127.0.0.1:8721  --repo <checkout whose HEAD is the reference>
import "./_help.mjs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const DEFAULT_URL = "http://127.0.0.1:8721";
const HERE = path.dirname(fileURLToPath(import.meta.url));

const short = (c) => (typeof c === "string" && c ? c.slice(0, 7) : "unknown");
const port = (url) => { try { return new URL(url).port || "80"; } catch { return "?"; } };

// Is the service working? `jobs` is JobRegistry.stats(): {jobs, states:
// {queued, running, done...}, inflight}. If it is missing or unreadable we
// cannot say it is idle, and an unknown is treated as busy.
export function jobsBusy(jobs) {
  if (!jobs || typeof jobs !== "object") return { busy: true, why: "its /health does not say whether a job is running" };
  const states = jobs.states && typeof jobs.states === "object" ? jobs.states : {};
  const running = Number(states.running) || 0;
  const queued = Number(states.queued) || 0;
  const inflight = Number(jobs.inflight) || 0;
  if (running + queued + inflight > 0) {
    const parts = [];
    if (running) parts.push(`${running} running`);
    if (queued) parts.push(`${queued} queued`);
    if (!running && !queued && inflight) parts.push(`${inflight} in flight`);
    return { busy: true, why: `a job is ${parts.join(", ")}` };
  }
  if (!("states" in jobs) && !("inflight" in jobs)) return { busy: true, why: "its /health does not say whether a job is running" };
  return { busy: false, why: "" };
}

// probe -> { status: "down" | "unknown" | "answered", health }
//   down      nothing is listening (connection refused): the port is free.
//   unknown   something is there and did not answer in time or sensibly.
//   answered  an HTTP 200 whose body parsed as JSON (`health`).
export async function probe(url = DEFAULT_URL, { fetchImpl = fetch, timeoutMs = 3000 } = {}) {
  let res;
  try {
    res = await fetchImpl(url.replace(/\/+$/, "") + "/health", { signal: AbortSignal.timeout(timeoutMs) });
  } catch (err) {
    const code = err && err.cause && err.cause.code;
    return { status: ["ECONNREFUSED", "ENOTFOUND", "EADDRNOTAVAIL"].includes(code) ? "down" : "unknown", health: null };
  }
  if (!res || !res.ok) return { status: "unknown", health: null };
  try {
    return { status: "answered", health: await res.json() };
  } catch {
    return { status: "unknown", health: null };
  }
}

export function isDigitizer(health) {
  return !!health && typeof health === "object" && health.service === "digitizer";
}

// The verdict. `head` is the reference checkout's HEAD (a sha, or null when it
// cannot be read); `replace` is on by default, `false` is the -KeepStale opt-out.
export function decide({ url = DEFAULT_URL, status, health, head, replace = true }) {
  const p = port(url);
  const out = (action, reason, extra = {}) => ({ action, reason, lines: [reason], ...extra });

  if (status === "down") return out("start", `nothing is listening on :${p}; starting the digitizer.`);
  if (status !== "answered" || !isDigitizer(health)) {
    const what = status === "answered" ? `answers on :${p} but is not the digitizer` : `holds :${p} and did not answer /health`;
    return out("foreign", `something ${what}; leaving it alone, not starting a digitizer over it.`);
  }

  const eng = health.engine && typeof health.engine === "object" ? health.engine : null;
  const svc = eng ? eng.commit : null;
  const started = eng && eng.started_at ? `, started ${eng.started_at}` : "";
  const info = { serviceCommit: svc || null, headCommit: head || null, serviceDirty: eng ? eng.dirty === true : null };

  let stale = null; // null: cannot tell
  let why = "";
  if (!eng) {
    stale = true;
    why = `its /health has no engine stamp, so it predates this checkout (HEAD ${short(head)})`;
  } else if (!svc) {
    stale = null;
  } else if (!head) {
    stale = null;
  } else if (svc !== head) {
    stale = true;
    why = `service commit ${short(svc)}${eng.dirty ? " (dirty)" : ""} is not HEAD ${short(head)}`;
  } else if (eng.dirty === true) {
    stale = true;
    why = `service commit ${short(svc)} matches HEAD but its tree was dirty when it started`;
  } else {
    stale = false;
  }

  if (stale === null) {
    const r = !svc ? "its /health records no commit (git was unavailable when it started)" : "HEAD cannot be read here";
    return out("keep", `digitizer on :${p} is running; cannot tell if it is stale (${r}). Keeping it.`, info);
  }
  if (!stale) return out("keep", `digitizer on :${p} is current (commit ${short(svc)}${started}). Keeping it.`, info);

  const { busy, why: busyWhy } = jobsBusy(health.jobs);
  if (busy) {
    return out("busy", `digitizer on :${p} is STALE (${why}) but ${busyWhy}; keeping it. Stop it yourself when the job is done.`, info);
  }
  if (replace) return out("replace", `digitizer on :${p} is STALE (${why}) and idle; replacing it.`, info);
  return out("report", `digitizer on :${p} is STALE (${why}) and idle; left running (-KeepStale).`, info);
}

export function headCommit(repo = path.resolve(HERE, "..")) {
  try {
    return execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo, encoding: "utf8", timeout: 10000, stdio: ["ignore", "pipe", "ignore"] }).trim() || null;
  } catch {
    return null;
  }
}

// Poll /health until a digitizer answers. `now`/`sleep` are injectable so the
// timing is testable without waiting.
export async function waitHealthy(url = DEFAULT_URL, {
  fetchImpl = fetch, timeoutMs = 90000, intervalMs = 1000,
  now = () => Date.now(), sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
} = {}) {
  const deadline = now() + timeoutMs;
  for (;;) {
    const r = await probe(url, { fetchImpl, timeoutMs: 2000 });
    if (r.status === "answered" && isDigitizer(r.health)) return { ok: true, health: r.health };
    if (now() >= deadline) return { ok: false, health: null };
    await sleep(intervalMs);
  }
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const argv = process.argv.slice(2);
  const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 ? argv[i + 1] : d; };
  const url = flag("url", DEFAULT_URL);
  if (argv.includes("--wait")) {
    const secs = Number(flag("wait", "90")) || 90;
    const r = await waitHealthy(url, { timeoutMs: secs * 1000 });
    console.log(r.ok ? `digitizer answers on :${port(url)}` : `no digitizer answered on :${port(url)} in ${secs} s`);
    // exitCode, not process.exit(): exiting with a fetch socket still closing
    // aborts node on Windows (0xC0000409) instead of returning the code.
    process.exitCode = r.ok ? 0 : 1;
  } else {
    const r = await probe(url);
    const verdict = decide({ url, ...r, head: headCommit(flag("repo", path.resolve(HERE, ".."))), replace: !argv.includes("--keep-stale") });
    if (argv.includes("--json")) console.log(JSON.stringify(verdict));
    else console.log(verdict.lines.join("\n"));
  }
}
