// .claude/hooks/nudge-cookbook-stale.js counts source commits since COOKBOOK's
// last REFRESH (the end SHA in its "Last refreshed ... over `a..b`" header),
// not since the file's last edit. Before 2026-11-19 it counted from the last
// edit, so every appended section reset the clock while the body went a month
// stale with the nudge silent. These run the hook against a throwaway repo.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const HOOK = path.join(__dirname, '..', '.claude', 'hooks', 'nudge-cookbook-stale.js');

function git(cwd, ...args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' }).trim();
}

function repo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'nudge-'));
  git(dir, 'init', '-q');
  git(dir, 'config', 'user.email', 't@example.invalid');
  git(dir, 'config', 'user.name', 't');
  git(dir, 'config', 'commit.gpgsign', 'false');
  return dir;
}

function commit(dir, file, text) {
  fs.mkdirSync(path.dirname(path.join(dir, file)), { recursive: true });
  fs.writeFileSync(path.join(dir, file), text);
  git(dir, 'add', file);
  git(dir, 'commit', '-q', '-m', file);
  return git(dir, 'rev-parse', 'HEAD');
}

function sourceCommits(dir, n, tag) {
  for (let i = 0; i < n; i++) commit(dir, `src/${tag}${i}.js`, String(i));
}

function runHook(dir, command = 'git commit -m x') {
  const out = execFileSync(process.execPath, [HOOK], {
    input: JSON.stringify({ cwd: dir, tool_input: { command } }),
    encoding: 'utf8',
    env: { ...process.env, EMB_COOKBOOK_STALE_THRESHOLD: '3' },
  });
  return out.trim() ? JSON.parse(out).hookSpecificOutput.additionalContext : '';
}

test('an append to COOKBOOK does not reset the clock while the refresh header stands', () => {
  const dir = repo();
  const base = commit(dir, 'src/base.js', 'base');
  commit(dir, 'COOKBOOK.md', `# C\n\n**Last refreshed 2026-11-19** over \`0000000..${base.slice(0, 8)}\` on \`main\`\n`);
  sourceCommits(dir, 2, 'a');
  fs.appendFileSync(path.join(dir, 'COOKBOOK.md'), '\n## A new section\n');
  git(dir, 'commit', '-qam', 'append');
  sourceCommits(dir, 1, 'b');
  const msg = runHook(dir);
  assert.match(msg, /3 source commits/);
  assert.match(msg, /last refresh/);
});

test('below the threshold it stays quiet', () => {
  const dir = repo();
  const base = commit(dir, 'src/base.js', 'base');
  commit(dir, 'COOKBOOK.md', `**Last refreshed 2026-11-19** over \`0000000..${base.slice(0, 8)}\`\n`);
  sourceCommits(dir, 2, 'a');
  assert.strictEqual(runHook(dir), '');
});

test('no header falls back to the last edit of COOKBOOK', () => {
  const dir = repo();
  commit(dir, 'COOKBOOK.md', '# no header\n');
  sourceCommits(dir, 3, 'a');
  assert.match(runHook(dir), /last edit/);
});

test('a header SHA this clone does not have falls back instead of failing', () => {
  const dir = repo();
  commit(dir, 'COOKBOOK.md', '**Last refreshed 2026-11-19** over `0000000..deadbeef`\n');
  sourceCommits(dir, 3, 'a');
  assert.match(runHook(dir), /last edit/);
});

test('it only speaks on git commit', () => {
  const dir = repo();
  commit(dir, 'COOKBOOK.md', '# no header\n');
  sourceCommits(dir, 3, 'a');
  assert.strictEqual(runHook(dir, 'git status'), '');
});
