# House rules for every W6 worker (foreman local_c188b954-ebb7-4429-a085-9a2fcb4974d4)

- Public repo: no client artwork, customer names, third-party stitch files, credentials. Pro renders: Kent ruled "Stop new ones, keep old" — no NEW pro images committed; renders go to a gitignored scratch dir, commit ours-side images only.
- CPU is the laptop's limit. A heavy run (digitize, batch, census, pytest over 5 min) needs a CPU slot:
  - mkdir C:/Users/EE-LT-11030/AppData/Local/Temp/embwt/cpu.lock (else cpu.lock2), write holder.txt inside (session id, lane, job, start time, ETA), rm -r ONLY the slot you took the moment the job ends.
  - cpu.lock2 only when line 2 of embwt/cpu_status.txt starts STATE=OK. A cpu.lock2 holder.txt starting WATCHDOG means slot 2 is closed.
  - One job per take, about 20 min max. Poll for a slot no more often than every 30 s; after releasing, wait 90 s before trying again.
  - STATE=HOT: start nothing heavy. Never two MFab jobs at once. pytest -n 2 max. Never run the full digitizer suite — CI shards it.
- MFab/Tires/any rembg-route job: a worktree has NO rembg_isolated or sam2_isolated venv, so a digitize or service started from a lane silently takes the classical route (PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE). Start the service / point stage 1 at the PRIMARY checkout's venvs (C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer), and check each result's route.
- TaskStop on a background waiter does NOT kill its child bash/python: kill those by PID, and release your slot.
- New PipelineConfig fields go into digitizer/tests/engine_2026_10_27.json with their pre-flip (OFF) value (test_pins_are_frozen.py guards this). New md5 pins pin explicit values, never ride defaults. Re-pin after CI with `python -m tools.ci_repin <run id>` (dry run first, then --apply).
- git: fetch origin main && merge origin/main before every push. Never rebase, never force-push, never `git stash` bare.
- Before pushing: run digitizer tests/test_memory_budget.py and tests/test_tools_console.py. Add one memory note + one alphabetical MEMORY.md index line (under ~170 chars); if the budget test fails, move the OLDEST index lines whole to MEMORY-archive.md.
- Do not edit MASTER_SCOPE.md, DOCTRINE.md, CLAUDE.md, COOKBOOK.md, docs/scope-history.md. Status goes in the PR body.
- Never flip a default. Fix your own red CI; never skip/xfail to get green. `pytest > log 2>&1; echo "EXIT=$?" >> log` — never pipe pytest to tail.
- Questions roll up: never ask Kent directly (Kent 10-27: "qestions from your workers should roll up to you for me to answer"). Message the foreman with the decision, options, cost and catch; keep working on what doesn't depend on it.
- Finish: PR ready-for-review, auto-merge armed while mergeable_state is blocked, auto-fix on. Message the foreman with the PR number and the headline numbers (or the premise result if you stopped).
