// PreToolUse guard: nudges to update COOKBOOK.md once 20+ source commits
// have piled up since it was last touched. Never blocks — informational only.
const fs = require('fs');
const { execSync } = require('child_process');

const STALE_THRESHOLD = 20;
const SOURCE_PATHS = ['src/', 'digitizer/', 'app/src'];

let data;
try {
  data = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}

const cmd = (data.tool_input && data.tool_input.command) || '';
if (!/\bgit\s+commit\b/i.test(cmd)) process.exit(0);

const cwd = data.cwd || process.cwd();

function run(gitCmd) {
  return execSync(gitCmd, { cwd, encoding: 'utf8' }).trim();
}

try {
  const lastCookbookCommit = run('git log -1 --format=%H -- COOKBOOK.md');
  if (!lastCookbookCommit) process.exit(0);

  const count = parseInt(
    run(`git rev-list --count ${lastCookbookCommit}..HEAD -- ${SOURCE_PATHS.join(' ')}`),
    10
  );

  if (count >= STALE_THRESHOLD) {
    const lastDate = run(`git log -1 --format=%cd --date=short ${lastCookbookCommit}`);
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'allow',
        additionalContext:
          `Heads up: COOKBOOK.md hasn't been touched in ${count} source commits ` +
          `(last updated ${lastDate}, commit ${lastCookbookCommit.slice(0, 7)}). ` +
          `Worth a pass if this is a natural stopping point.`
      }
    }));
  }
} catch {
  // never block a commit over a docs nudge failing to compute
}
process.exit(0);
