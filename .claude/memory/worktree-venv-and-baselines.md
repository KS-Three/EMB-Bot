---
name: worktree-venv-and-baselines
description: "EMB-Bot worktrees have no .venv — use the main checkout's interpreter with cwd shadowing; never use the main checkout as a measurement baseline (it sits on feature branches)"
metadata: 
  node_type: memory
  type: project
  originSessionId: b64ff04e-0620-41a0-be70-534221642741
  modified: 2026-09-01T04:48:36.966Z
---

Two facts for any session rooted in an EMB-Bot worktree (`.claude/worktrees/<name>/`), both hit 2026-08-31:

1. **No `.venv` in the worktree.** The venv lives in the MAIN checkout (`C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer\.venv`, editable-installed). Run `"<main>\digitizer\.venv\Scripts\python.exe" -m pytest` with **cwd in the worktree's `digitizer/`** — `python -m` puts cwd first on `sys.path`, so the worktree's `digitizer_core` shadows the editable install (verified via `digitizer_core.__file__`). Same for `python tools/<script>.py` (tools insert their own ROOT).

2. **The main checkout is NOT a baseline.** It routinely sits on a feature branch (2026-08-31: `claude/artwork-fidelity` at 312d390, pre-#291/#293 — owl measured 17 blocks there vs 13 on the real base). For before/after measurements, `git worktree add <scratchpad>/base <merge-base-sha>` from your own worktree, measure there, `git worktree remove` after. Find the base with `git merge-base HEAD origin/main`.

Related: [[digitizer-local-env]], [[windows-goldens-fail-locally]].
