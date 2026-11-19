// PreToolUse hook: on `git commit`, nudges that COOKBOOK.md is due a refresh once
// enough source commits have landed since its last REFRESH. Never blocks —
// informational only.
//
// It counts from the end SHA of the header line COOKBOOK.md keeps for that,
//   **Last refreshed 2026-11-19** over `0eb5e02..df50b217` on `main`
// and NOT from the file's last commit: feature PRs append a section now and
// then, and counting from the last touch let every append reset the clock
// while the body aged a month (audit 2026-11-19: 837 commits past the
// refresh, nudge silent). If the header is missing or its SHA is unknown
// here, it falls back to the last commit that touched the file.
//
// The threshold is days of work, not one afternoon: main lands roughly 30
// source commits a day (2026-11), and a refresh is one named session's job,
// so a nudge on every commit only invites appends.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const STALE_THRESHOLD = Number(process.env.EMB_COOKBOOK_STALE_THRESHOLD) || 150;
const SOURCE_PATHS = ['src/', 'digitizer/', 'app/src'];
const HEADER = /\*\*Last refreshed (\d{4}-\d{2}-\d{2})\*\*\s+over\s+`[0-9a-f]{4,40}\.\.([0-9a-f]{4,40})`/;

let data;
try {
  data = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}

const cmd = (data.tool_input && data.tool_input.command) || '';
if (!/\bgit\s+commit\b/i.test(cmd)) process.exit(0);

const cwd = data.cwd || process.cwd();

// No shell: on Windows execSync goes through cmd.exe, which eats the `^` in
// `<sha>^{commit}` and silently sent every lookup to the fallback.
function run(...args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
}

function refreshBase() {
  try {
    const top = run('rev-parse', '--show-toplevel');
    const head = fs.readFileSync(path.join(top, 'COOKBOOK.md'), 'utf8').slice(0, 4000);
    const m = head.match(HEADER);
    if (m) {
      const sha = run('rev-parse', '--verify', '--quiet', `${m[2]}^{commit}`);
      if (sha) return { sha, date: m[1], how: 'last refresh' };
    }
  } catch {
    // fall through to the last touch
  }
  const sha = run('log', '-1', '--format=%H', '--', 'COOKBOOK.md');
  if (!sha) return null;
  return { sha, date: run('log', '-1', '--format=%cd', '--date=short', sha), how: 'last edit' };
}

try {
  const base = refreshBase();
  if (!base) process.exit(0);

  const count = parseInt(
    run('rev-list', '--count', `${base.sha}..HEAD`, '--', ...SOURCE_PATHS),
    10
  );

  if (count >= STALE_THRESHOLD) {
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        additionalContext:
          `Heads up: ${count} source commits have landed since COOKBOOK.md's ` +
          `${base.how} (${base.date}, ${base.sha.slice(0, 8)}). A refresh is one ` +
          `named session's job: don't append to COOKBOOK from a feature PR; ` +
          `mention it to Kent or the foreman instead.`
      }
    }));
  }
} catch {
  // never block a commit over a docs nudge failing to compute
}
process.exit(0);
