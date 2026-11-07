#!/usr/bin/env node
// Proves the `studio-e2e shard k/n` jobs together ran the whole Playwright
// suite, each test exactly once. Run by the `studio-e2e` aggregator job (the
// required check) over the shards' downloaded artifacts:
//
//   node tools/ci-e2e-shard-check.mjs <dir>
//
// <dir> holds one folder per shard (studio-e2e-shard-1, ...), each with:
//   shard.json            {"shard": k, "of": n}
//   list.json             `playwright test --list --reporter=json` with NO
//                         E2E_SHARD: the whole collected suite, as that shard
//                         saw it
//   results-parallel.json, results.json
//                         the JSON reports of the shard's two test steps
//
// Fails (exit 1) unless: exactly one shard each for 1..n; every shard
// collected the identical list (a non-empty one); every collected test passed
// (expected or flaky) exactly once across ALL shards and steps; and no report
// holds a test the collected list lacks. The digitizer's counterpart is
// digitizer/tools/ci_shard_check.py. Node stdlib only, no install.
import { readFileSync, readdirSync, appendFileSync } from "node:fs";
import { join } from "node:path";

const RESULT_FILES = ["results-parallel.json", "results.json"];
const PASSED = new Set(["expected", "flaky"]);

// One entry per (spec, project): a stable, readable key and the test's status.
export function testsOf(report) {
  const out = [];
  const walk = (suite, titles) => {
    for (const spec of suite.specs ?? []) {
      for (const t of spec.tests) {
        const path = [...titles, spec.title].join(" › ");
        out.push({ key: `${spec.file}:${spec.line}:${spec.column} › ${path} [${t.projectName}]`, status: t.status });
      }
    }
    for (const child of suite.suites ?? []) walk(child, [...titles, child.title]);
  };
  // The top level of a Playwright JSON report is one suite per file, titled
  // with the file name; the key already carries the file, so start below it.
  for (const fileSuite of report.suites ?? []) walk(fileSuite, []);
  return out;
}

export function check(dir) {
  const errors = [];
  const shards = readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => {
      const p = join(dir, d.name);
      const read = (f) => JSON.parse(readFileSync(join(p, f), "utf8"));
      return { name: d.name, meta: read("shard.json"), list: read("list.json"), reports: RESULT_FILES.map((f) => [f, read(f)]) };
    })
    .sort((a, b) => a.meta.shard - b.meta.shard);

  const n = shards[0]?.meta.of;
  const ids = shards.map((s) => s.meta.shard).join(",");
  const want = Array.from({ length: n ?? 0 }, (_, i) => i + 1).join(",");
  if (!n || ids !== want || shards.some((s) => s.meta.of !== n)) {
    errors.push(`expected one shard each for 1..${n}, got [${ids}] (of=${shards.map((s) => s.meta.of)})`);
  }

  const collected = testsOf(shards[0]?.list ?? {}).map((t) => t.key);
  const collectedSet = new Set(collected);
  if (collected.length === 0) errors.push("the collected list is empty");
  if (collectedSet.size !== collected.length) errors.push("the collected list repeats a test key");
  for (const s of shards.slice(1)) {
    const other = testsOf(s.list).map((t) => t.key);
    if (other.length !== collected.length || other.some((k, i) => k !== collected[i])) {
      errors.push(`${s.name} collected a different list (${other.length} vs ${collected.length} tests)`);
    }
  }

  const ran = new Map(); // key -> [where...]
  const perShard = [];
  for (const s of shards) {
    let count = 0;
    for (const [file, report] of s.reports) {
      for (const t of testsOf(report)) {
        if (!collectedSet.has(t.key)) errors.push(`${s.name}/${file} has a test the collected list lacks: ${t.key}`);
        if (t.status === "skipped") continue;
        if (!PASSED.has(t.status)) errors.push(`${s.name}/${file}: ${t.status}: ${t.key}`);
        ran.set(t.key, [...(ran.get(t.key) ?? []), `${s.name}/${file}`]);
        count++;
      }
    }
    perShard.push(`${s.name}: ${count} tests`);
  }
  for (const k of collected) {
    const where = ran.get(k) ?? [];
    if (where.length === 0) errors.push(`never ran: ${k}`);
    else if (where.length > 1) errors.push(`ran ${where.length} times (${where.join(", ")}): ${k}`);
  }
  return { errors, collected: collected.length, ran: ran.size, perShard };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const dir = process.argv[2];
  if (!dir) {
    console.error("usage: node tools/ci-e2e-shard-check.mjs <artifacts dir>");
    process.exit(2);
  }
  const { errors, collected, ran, perShard } = check(dir);
  const lines = [`collected ${collected} tests; ${ran} distinct tests ran`, ...perShard];
  if (errors.length) lines.push(`FAIL (${errors.length}):`, ...errors.slice(0, 50).map((e) => `  ${e}`));
  else lines.push(`OK: all ${collected} collected tests ran exactly once across the shards`);
  console.log(lines.join("\n"));
  if (process.env.GITHUB_STEP_SUMMARY) {
    appendFileSync(process.env.GITHUB_STEP_SUMMARY, ["## studio-e2e shard coverage", "", "```", ...lines, "```", ""].join("\n"));
  }
  process.exit(errors.length ? 1 : 0);
}
