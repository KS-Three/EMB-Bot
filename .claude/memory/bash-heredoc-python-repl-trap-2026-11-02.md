---
name: bash-heredoc-python-repl-trap-2026-11-02
description: On Kent's Windows box a Bash-tool `python - <<'E'` heredoc can leave stdin unattached, so Python 3.14 opens its _pyrepl REPL, loops on a read traceback at one full core and writes gigabytes of prompts to the task output until killed; a `||` fallback interpreter respawns it the second the first dies. Write a script file instead.
metadata:
  type: project
---

**Found 2026-11-02, cost 26 hours of one core.** A Bash tool call from Kent's
Opus session ("Digitizing quality improvements"), issued 2026-11-01 17:23 with
cwd `.claude/worktrees/cap-flip`, read

```
python - <<'E' 2>/dev/null || ".../digitizer/.venv/Scripts/python" - <<'E2'
E
E2
sed -n 628,638p digitizer/tests/conftest.py; grep -n "color_cap_sewn" MASTER_SCOPE.md; ...
```

Both heredoc bodies were empty. The call never returned. `C:\Python314\python.exe -`
(PID 14848) sat at about one core for 23 hours, 22.5 CPU-h, until Kent said
"Kill it" at 16:44 on 11-02. Killing it made `python -` exit non-zero, so the
`||` branch started the venv interpreter on `-` **in the same second** (PID 12656),
which spun another 2.2 CPU-h until it was found and killed at 19:20. The task
output file (`%TEMP%\claude\<project>\<session>\tasks\<id>.output`) had grown
to **3.68 GB**: the Python 3.14.6 banner, then
`Traceback (most recent call last): File "C:\Python314\Lib\_pyrepl\rea...`
repeated for a day, closed by the sed/grep lines failing in the wrong cwd and
`[exited with code 0]`. Binned 19:29 (Kent "Bin it").

**What the output shows.** `python -` printed the interactive banner, so it saw
a terminal-like stdin, not the heredoc: the body never reached it. In
interactive mode CPython 3.14's `_pyrepl` read raised, Python printed the
traceback and read again, a tight loop. Why the redirect was lost inside the
Bash tool's `bash -c -l "... eval '<command>'"` wrapper was not traced; the
symptom is enough to act on. The worktree-isolation hook in a lane session
refuses heredocs outright, which is why a session rooted in a lane never hits
this; a session in the primary checkout, or any shell without that hook, can.

**Why:** one stray at one core for a day inflates every timing taken on this
box (see [[digitize-speed-2026-10-26]] and [[stage7-scene-speed-2026-10-29]]:
a loaded laptop stretches `process_time` 2.6x and concurrent jobs 4x each).
Everything measured on Kent's laptop between 2026-11-01 17:23 and 2026-11-02
19:20 ran one core short, including the sew-out card v8 render, the yardstick
run and the start of the pro-sized sitting render. And a "killed it, core
freed" report was wrong for two and a half hours because the fallback was not
looked for.

**How to apply:**
- In the Bash tool on Windows, never feed Python through stdin (`python -`
  with a heredoc or a pipe). Write the script to the scratchpad with the
  Write tool and run `python <path>\script.py`, or use the PowerShell tool
  with the same file. The same goes for any `interpreter -` form.
- A hung call of this shape looks like: a `python.exe` whose command line ends
  in ` -`, hours of CPU, and a `tasks\*.output` growing by megabytes a minute.
  `Get-CimInstance Win32_Process` with a `-match 'python\.exe" -$'` filter
  finds it; read the parent `bash.exe`'s `CommandLine` before killing, so a
  `||` or `;` continuation is known in advance.
- After a kill, list python processes again within a minute. A fallback
  interpreter starts the moment the first exits; the parent chain
  (`bash -c -l` wrappers) exits on its own once the last command list ends.
- Bin the output file afterwards (Recycle Bin, Kent's rule), after checking
  nothing holds it open: it sits in the owning session's `tasks` folder, not
  in the repo.
