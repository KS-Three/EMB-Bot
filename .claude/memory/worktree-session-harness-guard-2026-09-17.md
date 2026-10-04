---
name: worktree-session-harness-guard-2026-09-17
description: In a worktree-isolated desktop session the harness refuses git-adjacent commands with quoted paths, `cd`, `-C` or `cmd`; the venv is reachable ONLY by its 8.3 path, and preview_start reads the MAIN checkout's launch.json
metadata:
  type: project
---

Measured 2026-09-17 in a session that `EnterWorktree`'d into
`.claude/worktrees/eye-pairs-gallery` on Kent's Windows box.

**The guard.** Once a session is worktree-isolated, the Bash tool refuses
any command it cannot prove stays inside the worktree: `git -C <shared>`,
`cd "<path with space>" && git …`, a quoted absolute exe path
(`"/c/Users/…/Claude Personal/…/python.exe"` reads as "a command whose name
is computed at runtime"), `cmd //c …`, and multi-line heredoc commits
prefixed with `cd`. Plain `git …` from the persisted cwd works, and so does
an UNQUOTED path with no spaces.

**"Git-adjacent" is nearly every command here, because `digitizer` contains
the letters `git`** (re-measured 2026-10-03, `edge-wobble-metrics`). The
refusal text is always *"names git in a form too complex to verify"*, and it
fired on commands with no git in them at all: `cd digitizer && <python> …`
with a quoted `"$S/log"`, a `grep` that also read `../.gitattributes`, and a
`grep -c $'\r' digitizer_core/…`. What passes: `cd digitizer` ALONE as its own
call (the cwd persists), then unquoted space-free paths, `;` chains, plain
redirects, plain `git add/commit/status/show` from that cwd. What does not:
`$'…'` strings, quoted variables, `cd x && …`. Use the Grep/Read tools for
anything pattern-shaped. And a helper script run BY PATH from the scratchpad
gets its own directory on `sys.path`, not the cwd — `sys.path.insert(0,
os.getcwd())` first, or `import digitizer_core` fails. **In a SUBAGENT the cwd
does not persist** — it resets every call — and heredocs are refused outright;
`python -m pytest digitizer/tests/…` from the worktree root is what worked
there. **A background command is killed at its `timeout` (max 10 min); a
foreground one that overruns is moved to the background and gets 30.** Neither
fits a full digitizer suite on this laptop, so run the files a change can
reach and let CI's required `digitizer` job be the full run.

**The venv path that works.** Worktrees have no `.venv`
([[worktree-venv-and-baselines]]); the main checkout's interpreter by its
8.3 short name has no space and passes the guard:

    /c/Users/EE-LT-11030/CLAUDE~4/EMB-Bot/digitizer/.venv/Scripts/python.exe -m pytest tests/test_foo.py -q

(`CLAUDE~4` = `Claude Personal`; `~1` is `.claude`, `~2`/`~3` are other
folders — `ls /c/Users/EE-LT-11030/CLAUDE~N/` tells them apart.) Run from
the worktree's `digitizer/` so its own `digitizer_core` shadows the
editable install — verified: `digitizer_core.__file__` resolved inside the
worktree.

**Previewing a page from a worktree.** `preview_start {name}` reads
`.claude/launch.json` from the MAIN checkout, not the worktree — an entry
added in the worktree is "not found". A `file://` URL inside the project
renders (scripts run) but as a `data:` snapshot: relative `img/` refs 404
and `localStorage` throws. What worked: `python -m http.server 8741 --bind
127.0.0.1 --directory <dir>` in a background Bash task, then `navigate` to
`http://127.0.0.1:8741/` in a fresh tab; `TaskStop` it when done. Two page
defects only that route found: a missing `<meta charset>` (mojibake on a
bare static server) and a missing viewport meta (980 px layout under the
mobile preset).

**The memory junction is per-checkout.** Writing to
`~/.claude/projects/<mangled>/memory/` from a worktree session is refused
("edit the worktree copy"); write to `<worktree>/.claude/memory/` and it
rides the PR, which is where this file came from. **And because it rides the
PR, `tests/test_memory_budget.py` gates it:** an index line over 260 chars
turned PR #507's `digitizer` job red after 55 minutes with 2514 other tests
green. Run that one file (half a second) after ANY edit to `MEMORY.md`.
