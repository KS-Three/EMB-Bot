#!/usr/bin/env node
// Per-spec-file seconds for the `SPEC_SECONDS` table in app/playwright.config.js,
// measured from the Playwright JSON reports that `studio-e2e shard k/2` uploads
// (artifact studio-e2e-shard-k: results-parallel.json + results.json).
//
//   node tools/e2e-spec-times.mjs <run-id|dir> [<run-id|dir> ...] [--e2e-dir app/e2e] [--default 30]
//
// A numeric argument is a GitHub Actions run id: its shard artifacts are
// fetched with `gh run download` into a temp dir. Any other argument is a
// directory already holding the reports (searched recursively, one dir = one
// run). Prints the median over the runs, one `"file": seconds,` line each, in
// the table's own shape and sorted like it, ready to paste in.
//
// What a number means, per file:
//   serial step (results.json, the digitizer-service specs, --workers=1):
//     WALL seconds, first test start to last test end, so hook and fixture
//     time outside the per-test figure counts (the list reporter's per-test
//     figures under-counted field-reshape-mode against wall time, PR #1303).
//   parallel step (results-parallel.json, 4 shared workers): the SUM of the
//     file's test durations, because the file's wall span is mostly other
//     files' tests; the config charges these a quarter of this number.
//
// Files in the e2e dir that no run covered are flagged `DEFAULT` (they take
// NEW_SPEC_SECONDS in the config) and get a trailing comment, not a number.
// Exit 1 if any file fell back to the default. Node stdlib + `gh` only.
import "./_help.mjs";
import { readFileSync, readdirSync, mkdtempSync, existsSync, statSync } from "node:fs";
import { join, basename } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";

// Seconds per spec file in ONE report. `serial` picks wall span vs summed time.
export function fileSeconds(report, serial) {
  const acc = new Map();
  const walk = (suite) => {
    for (const spec of suite.specs ?? []) {
      const a = acc.get(spec.file) ?? { sum: 0, lo: Infinity, hi: -Infinity };
      for (const t of spec.tests) {
        for (const r of t.results ?? []) {
          const start = Date.parse(r.startTime);
          a.sum += r.duration;
          if (Number.isFinite(start)) {
            a.lo = Math.min(a.lo, start);
            a.hi = Math.max(a.hi, start + r.duration);
          }
        }
      }
      acc.set(spec.file, a);
    }
    for (const child of suite.suites ?? []) walk(child);
  };
  for (const s of report.suites ?? []) walk(s);
  const out = new Map();
  for (const [file, a] of acc) {
    const ms = serial && a.hi > a.lo ? a.hi - a.lo : a.sum;
    out.set(basename(file), ms / 1000);
  }
  return out;
}

export function median(xs) {
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// runs: array of runs, each an array of { serial, report }. -> Map file -> median seconds.
export function medianSeconds(runs) {
  const perFile = new Map();
  for (const run of runs) {
    const thisRun = new Map();
    for (const { serial, report } of run) {
      for (const [file, secs] of fileSeconds(report, serial)) thisRun.set(file, (thisRun.get(file) ?? 0) + secs);
    }
    for (const [file, secs] of thisRun) {
      if (!perFile.has(file)) perFile.set(file, []);
      perFile.get(file).push(secs);
    }
  }
  return new Map([...perFile].map(([f, xs]) => [f, median(xs)]));
}

// The table text; files in specFiles with no measurement are flagged, not numbered.
export function renderTable(times, specFiles, defaultSecs = 30) {
  const names = [...new Set([...specFiles, ...times.keys()])].sort();
  const lines = [];
  const defaults = [];
  for (const f of names) {
    if (times.has(f)) lines.push(`  ${JSON.stringify(f)}: ${Math.round(times.get(f))},`);
    else {
      defaults.push(f);
      lines.push(`  // ${JSON.stringify(f)}: DEFAULT (${defaultSecs} s) -- no run measured it`);
    }
  }
  const covered = names.length - defaults.length;
  return { text: `const SPEC_SECONDS = {\n${lines.join("\n")}\n};`, defaults, covered, total: names.length };
}

function findReports(dir) {
  const found = [];
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name === "results.json") found.push({ serial: true, report: JSON.parse(readFileSync(p, "utf8")) });
      else if (e.name === "results-parallel.json") found.push({ serial: false, report: JSON.parse(readFileSync(p, "utf8")) });
    }
  };
  walk(dir);
  return found;
}

function loadRun(arg) {
  let dir = arg;
  if (/^\d+$/.test(arg)) {
    dir = mkdtempSync(join(tmpdir(), `e2e-times-${arg}-`));
    const r = spawnSync("gh", ["run", "download", arg, "--repo", "KS-Three/EMB-Bot", "--pattern", "studio-e2e-shard-*", "--dir", dir], { encoding: "utf8" });
    if (r.status !== 0) throw new Error(`gh run download ${arg} failed: ${r.stderr}`);
  }
  if (!existsSync(dir) || !statSync(dir).isDirectory()) throw new Error(`not a directory: ${dir}`);
  const reports = findReports(dir);
  if (!reports.length) throw new Error(`no results*.json under ${dir}`);
  return reports;
}

function main(argv) {
  const args = [];
  let e2eDir = "app/e2e";
  let def = 30;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--e2e-dir") e2eDir = argv[++i];
    else if (argv[i] === "--default") def = Number(argv[++i]);
    else args.push(argv[i]);
  }
  if (!args.length) {
    console.error("usage: node tools/e2e-spec-times.mjs <run-id|dir> [...] [--e2e-dir app/e2e] [--default 30]");
    process.exit(2);
  }
  const times = medianSeconds(args.map(loadRun));
  const specFiles = existsSync(e2eDir) ? readdirSync(e2eDir).filter((f) => f.endsWith(".spec.js")) : [];
  const t = renderTable(times, specFiles, def);
  console.log(t.text);
  console.error(`median over ${args.length} run(s); ${t.covered}/${t.total} spec files covered, ${t.defaults.length} on the default`);
  if (t.defaults.length) {
    console.error(`DEFAULT: ${t.defaults.join(", ")}`);
    process.exit(1);
  }
}

if (process.argv[1] && import.meta.url.endsWith(basename(process.argv[1]))) main(process.argv.slice(2));
