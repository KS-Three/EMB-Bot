#!/usr/bin/env node
// Replay the worktree guard over real Claude Code transcripts, READ-ONLY.
//
// For every Bash/PowerShell tool_use in the given *.jsonl transcripts it feeds
// the command (and the record's `cwd`) to two judges — the text-only rule the
// guard shipped with until 2026-10-04 (its two regexes, copied verbatim
// below) and the current target-judging guard — and reports, per transcript
// directory: how many shell calls each caught, which commands the new guard
// STILL denies, which it NEWLY allows, and which it NEWLY denies. Nothing is
// ever executed; the hook itself only stats paths.
//
// Usage (Kent's machine, the two session groups measured on 2026-10-03):
//
//   node tools/replay-worktree-guard.mjs --since 2026-10-01 \
//     "C:\Users\EE-LT-11030\.claude\projects\C--Users-EE-LT-11030--claude-work" \
//     "C:\Users\EE-LT-11030\.claude\projects\C--Users-EE-LT-11030-Claude-Personal-EMB-Bot"
//
// Options:
//   --since YYYY-MM-DD   only tool calls at or after this date (default: all)
//   --home PATH          HOME/USERPROFILE for `~` and $HOME in the replayed
//                        commands (default: this process's)
//   --recursive          also read *.jsonl in subdirectories (subagent logs)
//   --full               print whole commands instead of the first 240 chars
//   --json FILE          also write every classified call as JSON
//   --hook FILE          judge with a different copy of the hook
//
// Cloud sessions cannot see Kent's transcripts; the counts in the PR that
// introduced this tool came from running it on his box.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));

// The pre-2026-10-04 guard, verbatim: deny when BOTH match anywhere in the text.
const OLD_NAMES_WORKTREES = /\.claude[\\/]+worktrees[\\/]?/i;
const OLD_DESTRUCTIVE_A = /\b(rm|rmdir|rd|del|mv)\b/i;
const OLD_DESTRUCTIVE_B = /Remove-Item|Move-Item/i;
const oldDenies = (cmd) => OLD_NAMES_WORKTREES.test(cmd) && (OLD_DESTRUCTIVE_A.test(cmd) || OLD_DESTRUCTIVE_B.test(cmd));

function parseArgs(argv) {
  const o = { inputs: [], since: null, home: null, recursive: false, full: false, json: null, hook: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--since') o.since = argv[++i];
    else if (a === '--home') o.home = argv[++i];
    else if (a === '--recursive') o.recursive = true;
    else if (a === '--full') o.full = true;
    else if (a === '--json') o.json = argv[++i];
    else if (a === '--hook') o.hook = argv[++i];
    else if (a === '--help' || a === '-h') { console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').filter((l) => l.startsWith('//')).map((l) => l.slice(3)).join('\n')); process.exit(0); }
    else o.inputs.push(a);
  }
  if (!o.inputs.length) { console.error('usage: replay-worktree-guard.mjs [--since DATE] [--home PATH] [--recursive] [--full] [--json FILE] <dir-or-jsonl>…'); process.exit(2); }
  return o;
}

function listJsonl(input, recursive) {
  const st = fs.statSync(input);
  if (st.isFile()) return [input];
  const out = [];
  const walk = (dir, depth) => {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, ent.name);
      if (ent.isFile() && ent.name.endsWith('.jsonl')) out.push(p);
      else if (ent.isDirectory() && recursive) walk(p, depth + 1);
    }
  };
  walk(input, 0);
  return out.sort();
}

function* shellCalls(file) {
  const text = fs.readFileSync(file, 'utf8');
  for (const line of text.split('\n')) {
    if (!line) continue;
    let rec;
    try { rec = JSON.parse(line); } catch { continue; }
    if (rec.type !== 'assistant' || !rec.message || !Array.isArray(rec.message.content)) continue;
    for (const block of rec.message.content) {
      if (!block || block.type !== 'tool_use') continue;
      if (block.name !== 'Bash' && block.name !== 'PowerShell') continue;
      const command = block.input && block.input.command;
      if (typeof command !== 'string') continue;
      yield { file, tool: block.name, command, cwd: rec.cwd || null, timestamp: rec.timestamp || null, sessionId: rec.sessionId || null };
    }
  }
}

function excerpt(cmd, full) {
  const one = cmd.replace(/\r/g, '').replace(/\n/g, ' ⏎ ');
  return full ? one : one.length > 240 ? one.slice(0, 240) + ' …' : one;
}

function main() {
  const o = parseArgs(process.argv.slice(2));
  const hookPath = o.hook ? path.resolve(o.hook) : path.join(HERE, '..', '.claude', 'hooks', 'block-worktree-mutation.js');
  const { judge } = require(hookPath);
  const env = { ...process.env };
  if (o.home) { env.HOME = o.home; env.USERPROFILE = o.home; }
  const since = o.since ? new Date(o.since).getTime() : null;

  const groups = [];
  const all = [];
  for (const input of o.inputs) {
    const files = listJsonl(input, o.recursive);
    const g = { label: path.basename(input.replace(/[\\/]+$/, '')), files: files.length, calls: 0, old: 0, new: 0, both: 0, newlyAllowed: 0, newlyDenied: 0, rows: [] };
    for (const f of files) {
      for (const call of shellCalls(f)) {
        if (since && call.timestamp && new Date(call.timestamp).getTime() < since) continue;
        g.calls++;
        const oldDeny = oldDenies(call.command);
        const verdict = judge({ tool_name: call.tool, cwd: call.cwd, tool_input: { command: call.command } }, { env });
        const row = {
          group: g.label, file: path.basename(f), timestamp: call.timestamp, cwd: call.cwd, tool: call.tool,
          old: oldDeny, new: verdict.deny,
          rules: verdict.findings.filter((x) => x.deny).map((x) => x.rule),
          why: verdict.findings.filter((x) => x.deny).map((x) => x.why),
          findings: verdict.findings.map((x) => ({ verb: x.verb, raw: x.raw, resolved: x.resolved, status: x.status, rule: x.rule, deny: x.deny })),
          command: call.command,
        };
        if (oldDeny) g.old++;
        if (verdict.deny) g.new++;
        if (oldDeny && verdict.deny) g.both++;
        if (oldDeny && !verdict.deny) g.newlyAllowed++;
        if (!oldDeny && verdict.deny) g.newlyDenied++;
        if (oldDeny || verdict.deny) g.rows.push(row);
        all.push(row);
      }
    }
    groups.push(g);
  }

  const pct = (a, b) => (b ? ((100 * a) / b).toFixed(2) + '%' : '-');
  console.log('# Worktree guard replay' + (o.since ? ` (tool calls since ${o.since})` : ''));
  console.log('');
  console.log('| group | transcripts | shell calls | old guard caught | new guard denies | both | newly allowed | newly denied |');
  console.log('|---|---:|---:|---:|---:|---:|---:|---:|');
  for (const g of groups) {
    console.log(`| ${g.label} | ${g.files} | ${g.calls} | ${g.old} (${pct(g.old, g.calls)}) | ${g.new} (${pct(g.new, g.calls)}) | ${g.both} | ${g.newlyAllowed} | ${g.newlyDenied} |`);
  }
  const section = (title, pred) => {
    const rows = groups.flatMap((g) => g.rows.filter(pred));
    console.log('');
    console.log(`## ${title} (${rows.length})`);
    for (const r of rows) {
      console.log('');
      console.log(`- **${r.group}** / ${r.file} @ ${r.timestamp || '?'} — cwd \`${r.cwd || '?'}\`` + (r.rules.length ? ` — rules: ${[...new Set(r.rules)].join(', ')}` : ''));
      for (const w of r.why) console.log(`  - ${w}`);
      console.log('  ```');
      console.log('  ' + excerpt(r.command, o.full));
      console.log('  ```');
    }
  };
  section('Still denied (old AND new)', (r) => r.old && r.new);
  section('Newly allowed (old caught, new allows)', (r) => r.old && !r.new);
  section('Newly denied (old missed, new denies)', (r) => !r.old && r.new);

  if (o.json) fs.writeFileSync(o.json, JSON.stringify({ since: o.since, groups: groups.map(({ rows, ...g }) => g), rows: all }, null, 2));
}

main();
