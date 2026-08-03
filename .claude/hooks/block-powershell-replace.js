// PreToolUse guard: PowerShell "-replace" piped into a write cmdlet corrupts
// UTF-8 in this repo (mojibake + BOM, no error thrown) — see CLAUDE.md.
const fs = require('fs');

let data;
try {
  data = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}

const cmd = (data.tool_input && data.tool_input.command) || '';
const hasReplace = /-replace\b/i.test(cmd);
const hasWrite = /\b(Set-Content|Out-File|Add-Content)\b/i.test(cmd);

if (hasReplace && hasWrite) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason:
        'Blocked: PowerShell "-replace" piped into Set-Content/Out-File/Add-Content ' +
        'silently corrupts UTF-8 in this repo (mojibake + BOM, no error thrown) — ' +
        'documented in CLAUDE.md. Use the Edit tool for source file changes instead.'
    }
  }));
}
process.exit(0);
