// Pipe-tests for .claude/hooks/block-worktree-mutation.js — the PreToolUse
// guard that keeps a Bash/PowerShell call from deleting or moving a lane under
// .claude/worktrees/ (CLAUDE.md footgun 2).
//
// Every case here runs the hook exactly the way Claude Code does: a JSON
// payload on stdin (tool_name, tool_input.command, cwd), a JSON deny decision
// on stdout or nothing at all, exit 0 either way. Nothing here executes the
// commands under test; the hook only stats paths.
//
// The first guard denied on command TEXT (names `.claude/worktrees/` AND
// contains rm/rmdir/rd/del/mv as a word anywhere). Replayed over real session
// transcripts on 2026-10-03 that caught 1.6% of a wrong-root session's shell
// calls and 0.5% of a repo-rooted one's, and every sampled catch was a false
// positive — the four `fp` cases below are those, verbatim in shape. The `tp`
// cases are what the guard exists to stop. tools/replay-worktree-guard.mjs
// re-measures both over real transcripts.
const assert = require("node:assert");
const { test, before, after } = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const HOOK = path.join(__dirname, "..", ".claude", "hooks", "block-worktree-mutation.js");

// Kent's box, the two spellings a session actually uses for the same checkout.
const WIN = "C:\\Users\\EE-LT-11030\\Claude Personal\\EMB-Bot";
const GB = "/c/Users/EE-LT-11030/Claude Personal/EMB-Bot";
const HOME = "C:\\Users\\EE-LT-11030";
const WRONG_ROOT = "C:\\Users\\EE-LT-11030\\.claude-work"; // a Desktop session rooted outside the repo
const LANE = GB + "/.claude/worktrees/manual-holes";

function run(payload, policy) {
  const r = spawnSync(process.execPath, [HOOK], {
    input: typeof payload === "string" ? payload : JSON.stringify(payload),
    encoding: "utf8",
    env: { ...process.env, HOME, USERPROFILE: HOME, EMB_WORKTREE_GUARD_OWN_LANE: policy || "" },
  });
  assert.strictEqual(r.status, 0, "the hook must always exit 0; stderr: " + r.stderr);
  const out = r.stdout.trim();
  if (!out) return { deny: false, reason: "" };
  const json = JSON.parse(out);
  const h = json.hookSpecificOutput;
  assert.strictEqual(h.hookEventName, "PreToolUse");
  assert.strictEqual(h.permissionDecision, "deny");
  assert.ok(typeof h.permissionDecisionReason === "string" && h.permissionDecisionReason.length > 0);
  return { deny: true, reason: h.permissionDecisionReason };
}

const payload = (tool, cwd, command) => ({ tool_name: tool, cwd, tool_input: { command } });

// [name, tool, cwd, command, expectDeny, reasonMustInclude?]
const CASES = [
  // ---- the measured false positives (2026-10-03), all must now pass -------
  ["fp: rm of a scratchpad dir in a command that also names a lane",
    "Bash", WRONG_ROOT, `WT="${LANE}"; cd "$SCR" && rm -rf redcheck && mkdir -p redcheck/src && cp "$WT/src/fill.js" redcheck/src/`, false],
  ["fp: inline node code with a JS variable called mv",
    "Bash", GB, `cd "${LANE}" && node -e "const Q=require('./src/x.js'); for (const mv of Q.movesRecord(d)) { console.log(mv) }"`, false],
  ["fp: a temp file inside the session's own lane, reached by cd",
    "Bash", WRONG_ROOT, `cd "${LANE}" && rm vt.log`, false],
  ["fp: prose in a heredoc containing 'claude rm'",
    "Bash", GB, `cat >> notes.md <<'EOF'\nSee ${LANE} — NEVER run \`claude rm e2bbd7c9\` here.\nEOF`, false],
  ["fp: rm in the primary while merely listing the lanes",
    "Bash", GB, `rm -rf scratch_tmp && ls .claude/worktrees/`, false],
  ["fp: rm with redirects, lane named in a later echo",
    "Bash", GB, `rm -f build.log 2>/dev/null > /dev/null; echo "${LANE}"`, false],
  ["fp: own-lane delete with 2>&1 after the cd",
    "Bash", LANE, `cd "${LANE}" && rm -f build.log 2>&1`, false],
  ["fp: sudo rm of /tmp while echoing the worktrees path",
    "Bash", GB, `sudo rm -rf /tmp/foo && echo .claude/worktrees/`, false],

  // ---- true positives: the lane itself -----------------------------------
  ["tp: rm -rf of a lane by absolute Git Bash path", "Bash", GB, `rm -rf "${LANE}"`, true, "manual-holes"],
  ["tp: rm -rf of a lane by relative path from the primary", "Bash", WIN, `rm -rf .claude/worktrees/manual-holes`, true, "lane root"],
  ["tp: trailing slash does not hide a lane root", "Bash", WIN, `rm -rf .claude/worktrees/manual-holes/`, true],
  ["tp: mv of a lane", "Bash", GB, `mv .claude/worktrees/manual-holes /tmp/old`, true, "lane root"],
  ["tp: mv onto a lane root", "Bash", GB, `mv /tmp/x .claude/worktrees/manual-holes`, true],
  ["tp: Remove-Item on a Windows lane path", "PowerShell", WIN, `Remove-Item -Recurse -Force "${WIN}\\.claude\\worktrees\\manual-holes"`, true, "manual-holes"],
  ["tp: Remove-Item through a PowerShell variable set in the same command",
    "PowerShell", WIN, `$lane = "${WIN}\\.claude\\worktrees\\manual-holes"; Remove-Item -Recurse -Force $lane`, true, "manual-holes"],
  ["tp: rm through a bash variable set on an earlier line", "Bash", GB, `LANE="${LANE}"\nrm -rf "$LANE"`, true, "manual-holes"],
  ["tp: rm of the worktrees directory itself", "Bash", GB, `rm -rf .claude/worktrees`, true, "directory itself"],
  ["tp: a glob over every lane", "Bash", GB, `rm -rf .claude/worktrees/*`, true],
  ["tp: rm -rf . from inside a lane root", "Bash", LANE, `rm -rf .`, true, "lane root"],
  ["tp: rm -rf * from inside a lane root", "Bash", LANE, `rm -rf *`, true, "whole contents"],
  ["tp: the 8.3 short-name spelling of a lane", "Bash", WIN, `rm -rf /c/Users/EE-LT-11030/CLAUDE~4/EMB-Bot/.claude/worktrees/manual-holes`, true],
  ["tp: a lane reached through ~", "Bash", WIN, `rm -rf ~/Claude\\ Personal/EMB-Bot/.claude/worktrees/manual-holes`, true],
  ["tp: cd into the worktrees dir in a subshell, then rm a lane", "Bash", GB, `(cd .claude/worktrees && rm -rf manual-holes)`, true],
  ["tp: a heredoc with an apostrophe does not hide the rm after it",
    "Bash", GB, `cat <<'EOF' > notes.md\ndon't do this\nEOF\nrm -rf .claude/worktrees/manual-holes`, true],
  ["tp: bash -c wrapping the deletion", "Bash", GB, `bash -c 'rm -rf .claude/worktrees/manual-holes'`, true],
  ["tp: cmd /c rd /s /q on a lane", "PowerShell", WIN, `cmd /c rd /s /q "${WIN}\\.claude\\worktrees\\manual-holes"`, true],
  ["tp: a for loop over the lanes", "Bash", GB, `for d in .claude/worktrees/*; do rm -rf "$d"; done`, true],
  ["tp: find -delete rooted at a lane", "Bash", GB, `find .claude/worktrees/manual-holes -name '*.pyc' -delete`, true],
  ["tp: xargs rm fed from a lane", "Bash", GB, `find .claude/worktrees/manual-holes -name '*.pyc' | xargs rm`, true, "stdin"],
  ["tp: no cwd in the payload, relative lane path", "Bash", undefined, `rm -rf .claude/worktrees/manual-holes`, true],

  // ---- true positives: inside a lane the command is NOT running in --------
  ["tp: from one lane into a sibling lane", "Bash", LANE, `rm -rf ../fill-columns-zero-moves/digitizer`, true, "fill-columns-zero-moves"],
  ["tp: inside a lane by absolute path from the primary", "Bash", WIN, `rm -rf "${WIN}\\.claude\\worktrees\\manual-holes\\out"`, true, "cd into it first"],
  ["tp: inside a lane by absolute path from a wrong-root session", "Bash", WRONG_ROOT, `rm -rf "${LANE}/out"`, true],
  ["tp: Remove-Item inside a lane from the primary", "PowerShell", WIN, `Remove-Item "${WIN}\\.claude\\worktrees\\manual-holes\\out\\x.log"`, true],

  // ---- own lane (policy default: allow) ----------------------------------
  ["own: relative file and dir deletes inside the session's lane", "Bash", LANE, `rm -rf redcheck && rm *.log`, false],
  ["own: absolute path inside the session's lane", "Bash", LANE, `rm -rf "${LANE}/redcheck"`, false],
  ["own: $PWD inside the session's lane", "Bash", LANE, `rm -rf "$PWD/out"`, false],
  ["own: Windows cwd, PowerShell relative delete", "PowerShell", WIN + "\\.claude\\worktrees\\manual-holes", `Remove-Item .\\out -Recurse -Force`, false],
  ["own: del with a cmd-style flag", "PowerShell", WIN + "\\.claude\\worktrees\\manual-holes", `del /q out\\*.tmp`, false],
  ["own: Remove-Item -Filter under the lane root is not the lane root", "PowerShell", WIN + "\\.claude\\worktrees\\manual-holes", `Remove-Item -Path . -Filter *.log -Recurse`, false],
  ["own: find -delete with a name filter from the lane root", "Bash", LANE, `find . -name '*.pyc' -delete`, false],
  ["own: git clean inside the session's lane", "Bash", LANE, `git clean -fdx`, false],
  ["own: mv into the session's lane", "Bash", LANE, `mv /tmp/x.png "${LANE}/docs/x.png"`, false],

  // ---- unresolvable targets: fail closed only when the text names a lane --
  ["closed: unknown variable, command names a lane", "Bash", GB, `cd "${LANE}" && rm -rf "$OUT"`, true, "cannot resolve"],
  ["open: unknown variable, command never names a lane", "Bash", GB, `rm -rf "$OUT"`, false],
  ["open: PowerShell subexpression on a variable from an earlier call, no lane named", "PowerShell", WIN, `Remove-Item (Join-Path $lane 'out') -Recurse`, false],
  ["closed: the same subexpression when the command names a lane", "PowerShell", WIN, `$x = "${WIN}\\.claude\\worktrees"; Remove-Item (Join-Path $lane 'out') -Recurse`, true],

  // ---- git plumbing ------------------------------------------------------
  ["tp: git worktree remove of a lane", "Bash", GB, `git worktree remove --force .claude/worktrees/manual-holes`, true, "git worktree remove"],
  ["tp: git -C <repo> worktree remove of a lane from /tmp", "Bash", "/tmp", `git -C "${GB}" worktree remove .claude/worktrees/manual-holes`, true],
  ["ok: git worktree remove of a temp worktree outside the lanes", "Bash", GB, `git worktree remove /tmp/ref-main`, false],
  ["tp: git worktree add with an unset path variable from inside a lane (2026-08-31)",
    "Bash", GB + "/.claude/worktrees/wonderful-shaw", `git worktree add "$TMP_MAIN" origin/main --detach`, true, "worktree-add-empty-var-wipes-cwd"],
  ["ok: git worktree add of a new lane from the primary", "Bash", GB, `git worktree add .claude/worktrees/new-lane -b claude/new-lane origin/main`, false],
  ["ok: git worktree add with a literal temp path from inside a lane", "Bash", LANE, `git worktree add /tmp/ref-main origin/main --detach`, false],
];

for (const [name, tool, cwd, command, expectDeny, includes] of CASES) {
  test(name, () => {
    const r = run(payload(tool, cwd, command));
    assert.strictEqual(r.deny, expectDeny, (expectDeny ? "expected a deny" : "expected no output") + " for:\n" + command + "\nreason: " + r.reason);
    if (includes) assert.ok(r.reason.includes(includes), `reason should mention "${includes}":\n${r.reason}`);
  });
}

test("the deny decision is the documented shape and names the target and the rule", () => {
  const r = run(payload("Bash", GB, `rm -rf "${LANE}"`));
  assert.ok(r.deny);
  assert.ok(r.reason.includes("Blocked"));
  assert.ok(r.reason.includes("manual-holes"), r.reason);
  assert.ok(r.reason.includes("git worktree list"), r.reason);
  assert.ok(r.reason.includes("block-worktree-mutation.js"), r.reason);
});

test("malformed or empty stdin: silent, exit 0", () => {
  assert.strictEqual(run("not json").deny, false);
  assert.strictEqual(run("").deny, false);
  assert.strictEqual(run({}).deny, false);
  assert.strictEqual(run({ tool_name: "Bash", tool_input: {} }).deny, false);
  assert.strictEqual(run({ tool_name: "Read", tool_input: { file_path: ".claude/worktrees/x" } }).deny, false);
});

// ---- cases that need a real directory tree: ancestors, policies, symlinks --
let tmp;
let repo;
let laneA;
let laneB;
let link;
before(() => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), "emb-guard-"));
  repo = path.join(tmp, "EMB-Bot");
  laneA = path.join(repo, ".claude", "worktrees", "laneA");
  laneB = path.join(repo, ".claude", "worktrees", "laneB");
  fs.mkdirSync(path.join(laneA, "sub", "dir"), { recursive: true });
  fs.mkdirSync(laneB, { recursive: true });
  fs.mkdirSync(path.join(tmp, "elsewhere"), { recursive: true });
  fs.writeFileSync(path.join(laneA, "sub", "file.txt"), "x");
  link = path.join(tmp, "link-laneA");
  try { fs.symlinkSync(laneA, link, "dir"); } catch { link = null; }
});
after(() => {
  if (tmp) fs.rmSync(tmp, { recursive: true, force: true });
});

test("ancestor: rm -rf of the repo root that holds the lanes is denied", () => {
  const r = run(payload("Bash", tmp, `rm -rf "${repo}"`));
  assert.ok(r.deny, "expected deny");
  assert.ok(r.reason.includes("every lane"), r.reason);
});
test("ancestor: rm -rf .claude is denied, a sibling directory is not", () => {
  assert.ok(run(payload("Bash", repo, `rm -rf .claude`)).deny);
  assert.ok(run(payload("Bash", tmp, `mv EMB-Bot EMB-Bot.bak`)).deny);
  assert.strictEqual(run(payload("Bash", tmp, `rm -rf elsewhere`)).deny, false);
});
test("ancestor: git clean -ffdx at the repo root is denied, single -f is not", () => {
  assert.ok(run(payload("Bash", repo, `git clean -ffdx`)).deny);
  assert.ok(run(payload("Bash", repo, `git clean -f -f -d -x`)).deny);
  assert.ok(run(payload("Bash", repo, `git clean --force --force -dx`)).deny);
  assert.strictEqual(run(payload("Bash", repo, `git clean -fdx`)).deny, false);
  assert.strictEqual(run(payload("Bash", repo, `git clean --force -dx`)).deny, false);
  assert.strictEqual(run(payload("Bash", laneA, `git clean -ffdx`)).deny, false);
});
test("policy files-only: an existing file in the own lane passes, a directory or glob does not", () => {
  assert.strictEqual(run(payload("Bash", laneA, `rm sub/file.txt`), "files-only").deny, false);
  assert.ok(run(payload("Bash", laneA, `rm -rf sub/dir`), "files-only").deny);
  assert.ok(run(payload("Bash", laneA, `rm -rf sub/*`), "files-only").deny);
});
test("policy deny: nothing under .claude/worktrees/ is deletable, own lane included", () => {
  assert.ok(run(payload("Bash", laneA, `rm sub/file.txt`), "deny").deny);
  assert.ok(run(payload("Bash", laneA, `rm -rf sub/dir`), "deny").deny);
});
test("policy allow (default): the same deletes pass; the sibling lane still does not", () => {
  assert.strictEqual(run(payload("Bash", laneA, `rm sub/file.txt`)).deny, false);
  assert.strictEqual(run(payload("Bash", laneA, `rm -rf sub/dir`)).deny, false);
  assert.ok(run(payload("Bash", laneA, `rm -rf ../laneB`)).deny);
  assert.ok(run(payload("Bash", laneA, `rm -rf "${laneB}/x"`)).deny);
});
test("a cwd that reaches the lane through a symlink is still that lane", (t) => {
  if (!link) return t.skip("this filesystem refused the symlink");
  assert.strictEqual(run(payload("Bash", link, `rm -rf "${laneA}/sub/dir"`)).deny, false);
  assert.ok(run(payload("Bash", link, `rm -rf "${laneB}"`)).deny);
});
