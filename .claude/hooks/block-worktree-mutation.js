// PreToolUse guard: deleting/moving anything under .claude/worktrees/ can
// destroy another lane's live, uncommitted work — see CLAUDE.md.
const fs = require('fs');

let data;
try {
  data = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}

const cmd = (data.tool_input && data.tool_input.command) || '';
const targetsWorktrees = /\.claude[\\/]+worktrees[\\/]?/i.test(cmd);
const isDestructive = /\b(rm|rmdir|rd|del|mv)\b/i.test(cmd) || /Remove-Item|Move-Item/i.test(cmd);

if (targetsWorktrees && isDestructive) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason:
        'Blocked: this deletes or moves something under .claude/worktrees/, which holds ' +
        'live uncommitted work from parallel feature lanes (see CLAUDE.md). Run ' +
        '`git worktree list` to check current lanes — if removal is really intended, ' +
        'ask Kent to do it directly.'
    }
  }));
}
process.exit(0);
