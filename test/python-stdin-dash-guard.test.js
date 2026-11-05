// Pipe-tests for .claude/hooks/block-python-stdin-dash.js: denies a Python
// interpreter given `-` as its script (reads stdin; with no stdin it falls into
// the 3.14 REPL and spins a core — memory bash-heredoc-python-repl-trap-2026-11-02).
// `node -` is NOT guarded: node with no piped stdin just reads EOF and exits,
// it has no REPL fallback (a REPL starts only with no script AND a TTY).
const assert = require("node:assert");
const { test, describe } = require("node:test");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const HOOK = path.join(__dirname, "..", ".claude", "hooks", "block-python-stdin-dash.js");

function verdict(command) {
  const r = spawnSync(process.execPath, [HOOK], {
    input: JSON.stringify({ tool_name: "Bash", tool_input: { command } }),
    encoding: "utf8",
  });
  assert.strictEqual(r.status, 0, r.stderr);
  const out = r.stdout.trim();
  return out ? JSON.parse(out).hookSpecificOutput.permissionDecision : "allow";
}

const MEASURED_1102 = `python - <<'EOF'\nprint(1)\nEOF`;
const MEASURED_1103 =
  `cd "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer"; python - 2>/dev/null; ` +
  `sed -i 's/a/b/' tools/dark_ink_flip_sheet.py; sed -n 66,73p tools/dark_ink_flip_sheet.py; ` +
  `(.venv/Scripts/python -m tools.dark_ink_flip_sheet run --x 1 > log 2>&1; echo "EXIT=$?" >> log) &`;

describe("denies python -", () => {
  const deny = {
    "2026-11-02 heredoc": MEASURED_1102,
    "2026-11-03 compound": MEASURED_1103,
    python: "python -",
    python3: "python3 -",
    "python3.12": "python3.12 -",
    py: "py -",
    "python.exe": "python.exe -",
    "venv Scripts": ".venv/Scripts/python -",
    "venv bin": ".venv/bin/python -",
    "windows path": String.raw`C:\Python314\python.exe -`,
    "quoted path": String.raw`"C:\Python314\python.exe" -`,
    "after &&": "cd x && python -",
    "after ||": "false || python - <<'E'\nx\nE",
    "after pipe": "cat f | python -",
    "subshell bg": "(python - ) &",
    "flag before dash": "python -I -",
    "env prefix": "PYTHONUTF8=1 python -",
    "command subst": "x=$(python -)",
  };
  for (const [name, c] of Object.entries(deny)) test(name, () => assert.strictEqual(verdict(c), "deny"));
  test("reason names the trap and the fix", () => {
    const r = spawnSync(process.execPath, [HOOK], {
      input: JSON.stringify({ tool_input: { command: "python -" } }), encoding: "utf8" });
    assert.match(r.stdout, /scratchpad/);
    assert.match(r.stdout, /REPL/);
  });
});

describe("allows everything else", () => {
  const allow = {
    "-m pytest": "python -m pytest -q",
    "-c code": 'python -c "print(1)"',
    "script then dash arg": ".venv/Scripts/python tools/x.py --flag -",
    "echo": "echo python -",
    "git log": "git log -- python -",
    "-I script": "python -I script.py",
    "-V": "python -V",
    "-m with dash arg": "python -m foo -",
    node: "node - <<'E'\nconsole.log(1)\nE",
    "heredoc body mentions it": "cat <<'E'\npython -\nE",
    "quoted mention": 'grep "python -" notes.md',
    "other word": "mypython -",
    empty: "",
  };
  for (const [name, c] of Object.entries(allow)) test(name, () => assert.strictEqual(verdict(c), "allow"));
  test("garbage stdin passes", () => {
    const r = spawnSync(process.execPath, [HOOK], { input: "not json", encoding: "utf8" });
    assert.strictEqual(r.status, 0);
    assert.strictEqual(r.stdout.trim(), "");
  });
});
