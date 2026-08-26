// Guard: every tracked .ps1 must be ASCII-only.
//
// Windows PowerShell 5.1 decodes a BOM-less file as cp1252, not UTF-8. An em
// dash U+2014 is the bytes E2 80 94, and 0x94 lands on a double-quote-class
// character in cp1252 — which terminates the enclosing string literal and
// makes the rest of the file unparseable. On 2026-08-25 both
// tools/start-emb-bot.ps1 and digitizer/tools/pro_parity/ladder.ps1 failed to
// parse at all under 5.1 (measured with Parser::ParseFile on 5.1.26100.7462),
// while parsing fine under pwsh 7, which reads UTF-8 by default. The launcher
// was simply dead on the host most likely to run it.
//
// No other suite executes a .ps1, so nothing else can catch a regression here.
// Scope is `git ls-files` rather than a filesystem walk on purpose: the
// .claude/worktrees/ lanes hold their own older checkouts of these same
// scripts, and a walk would fail on those instead of on this tree's code.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const REPO = path.join(__dirname, "..");

function trackedPowerShellFiles() {
  const out = execFileSync("git", ["ls-files", "*.ps1"], {
    cwd: REPO,
    encoding: "utf8",
  });
  return out.split("\n").map((s) => s.trim()).filter(Boolean);
}

const files = trackedPowerShellFiles();

// A guard that silently matches nothing is worse than no guard: it reads green
// forever. Pin the floor so a bad glob or a move can't hollow this out.
test("the guard actually sees the repo's PowerShell scripts", () => {
  assert.ok(
    files.length >= 2,
    "expected at least 2 tracked .ps1 files, found " + files.length,
  );
});

for (const rel of files) {
  test("ASCII-only (Windows PowerShell 5.1 parses it): " + rel, () => {
    const text = fs.readFileSync(path.join(REPO, rel), "latin1");
    const offenders = [];
    text.split(/\r?\n/).forEach((line, i) => {
      // eslint-disable-next-line no-control-regex
      if (/[^\x00-\x7F]/.test(line)) offenders.push(rel + ":" + (i + 1) + ": " + line.trim());
    });
    assert.deepStrictEqual(
      offenders,
      [],
      "non-ASCII bytes in a PowerShell script — Windows PowerShell 5.1 will " +
        "misdecode these as cp1252 and can fail to parse the whole file:\n" +
        offenders.join("\n"),
    );
  });
}
