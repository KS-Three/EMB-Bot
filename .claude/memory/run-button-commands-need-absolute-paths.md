---
name: run-button-commands-need-absolute-paths
description: shell commands handed to Kent must use an absolute cd, because the desktop app's Run button reuses one PowerShell whose cwd persists — the second relative `cd digitizer` lands in digitizer/digitizer and fails
metadata:
  type: feedback
---

Every fenced shell block in a reply gets a **Run button** in the Claude Code
desktop app, and they all execute in **one persistent PowerShell session whose
cwd survives between them**. A command written `cd digitizer && ...` is
therefore correct exactly once.

**Hit 2026-09-15.** Two commands were handed over at the end of a session, both
opening `cd digitizer && ...`. The first ran, left the shell in `digitizer/`,
and the second produced:

    Set-Location: Cannot find path
    'C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer\digitizer'
    because it does not exist.

Kent reported it as *"It cannot complete"* — with no way to know the command
was fine in isolation and only wrong in sequence.

**Why:** my own Bash tool starts each call at the primary working directory, so
a relative `cd` always looks right while I am testing it. Kent's shell does
not reset. The two environments disagree precisely on the thing the command
depends on.

**How to apply:** give Kent an absolute `cd`, quoted for the space in
`Claude Personal`:

    cd "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer" && .venv\Scripts\python -m pytest -q

That is idempotent — correct from the repo root, from `digitizer/`, from a
worktree, and on the second press. Verify a handed-over command from a
DIFFERENT cwd than the one it was written in, or the defect is invisible.

Related: the same scrollback showed a Run button appending to text already
sitting at the prompt (`...-m digitizer_servicecd digitizer && ...`), which
concatenates two commands into one line. Not something a command's wording can
prevent — worth a word to Kent when it shows up.

See also [[memory-index-overflow-2026-09-15]] (the session this happened at the
end of).
