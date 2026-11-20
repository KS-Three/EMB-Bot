// SessionStart hook: injects ROADMAP.md's current phase and hard gates so a
// session knows the ordering before it proposes work.
//
// It EXTRACTS those sections from ROADMAP.md rather than carrying its own copy —
// two copies of a rule drift, and the copy nobody reads is the one that goes
// stale. If the file moves or the headings are renamed, this goes quiet rather
// than asserting something out of date.
const fs = require('fs');
const path = require('path');

// Headings lifted verbatim (prefix match). A rename in ROADMAP.md fails SILENT
// here, so digitizer/tests/test_roadmap_budget.py reads this list and fails CI
// when any entry has no heading. ("## Standing item" sat here as a no-op after
// ROADMAP dropped that section; removed 2026-11-19.)
const WANTED = ['## Where we are', '## Hard gates'];

let data;
try {
  data = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}

const root = (data && data.cwd) || process.env.CLAUDE_PROJECT_DIR || process.cwd();

try {
  const text = fs.readFileSync(path.join(root, 'ROADMAP.md'), 'utf8');

  // Split on top-level headings, keeping each heading with its body.
  const blocks = text.split(/\n(?=## )/).map((b) => b.trim()).filter(Boolean);
  const picked = WANTED
    .map((h) => blocks.find((b) => b.startsWith(h)))
    .filter(Boolean);

  if (!picked.length) process.exit(0);

  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext:
        'EMB-Bot roadmap gates, from ROADMAP.md (read the file for the full ' +
        'phase list; only Kent may advance a phase, and a gate below is a ' +
        'refusal, not a preference):\n\n' + picked.join('\n\n')
    }
  }));
} catch {
  // A missing or unreadable ROADMAP.md must never break a session start.
}
process.exit(0);
