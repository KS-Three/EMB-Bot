// PreToolUse guard: `git add -A`/`--all`/`.` stages everything without review —
// CLAUDE.md asks for a look at `git status` first. This warns, doesn't block.
const fs = require('fs');
const { execSync } = require('child_process');

let data;
try {
  data = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}

const cmd = (data.tool_input && data.tool_input.command) || '';
const addSegment = (cmd.match(/git\s+add\b[^&|;]*/i) || [])[0] || '';
const isAddAll = addSegment && (/(-A\b|--all\b)/i.test(addSegment) || /\.\s*$/.test(addSegment.trim()));

if (isAddAll) {
  let status;
  try {
    status = execSync('git status --short', { cwd: data.cwd || process.cwd(), encoding: 'utf8' }).trim();
  } catch (e) {
    status = '(could not run git status: ' + e.message + ')';
  }
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'allow',
      additionalContext:
        'Heads up: this stages everything. `git status --short` right now:\n' +
        (status || '(clean)') +
        '\nReview before committing — CLAUDE.md asks for a look before a blind `git add -A` from the repo root.'
    }
  }));
}
process.exit(0);
