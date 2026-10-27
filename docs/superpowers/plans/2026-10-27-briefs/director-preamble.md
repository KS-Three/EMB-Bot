STANDING RULES (director's lanes, 2026-10-26)

PROJECT
- EMB-Bot is Kent's embroidery auto-digitizer. The repo is KS-Three/EMB-Bot and it is PUBLIC.
- The goal is a plug-and-play digitizer whose DST matches the professional digitizer's ("the pro") file for the same job.
- Read first: CLAUDE.md, digitizer/CLAUDE.md, the ROADMAP gates, and the memory notes your task names.

LANE
- Work in your own worktree, cut from origin/main. Run `git fetch --all` first.
- Never edit, stash or check out anything in the main checkout `C:/Users/EE-LT-11030/Claude Personal/EMB-Bot`.
- Never touch another lane under `.claude/worktrees/`.
- Interpreter: `"C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe" -m ...`, with cwd set to YOUR lane's `digitizer/`. Never run a bare `python`.

ROUTE TRAP (#1152, 10-27)
- A digitize launched from a lane has no rembg_isolated venv. MFab hat and Tires (photo_scene) silently take the classical route, with no error.
- Grep each result for PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE and check the route.
- Point stage 1 at the primary checkout's rembg_isolated venv (read-only), as #1152's board does, or mark the row classical-route.

CPU (Kent: CPU is the limiting factor on this laptop: 8 cores, shared with another foreman's lanes)
- Before every heavy run, read `C:/Users/EE-LT-11030/AppData/Local/Temp/embwt/cpu_status.txt`.
  - A heavy run is a digitize, a census over several jobs, a flip-sheet batch, or a pytest run over 5 minutes.
- A heavy run needs a FREE slot:
  - take one with `mkdir C:/Users/EE-LT-11030/AppData/Local/Temp/embwt/cpu.lock` (or `cpu.lock2`);
  - write `holder.txt` inside it: session, lane, command, start time, ETA;
  - `rm -r` it the moment the run ends, failure included.
- Take whichever slot is free. If `cpu.lock2/holder.txt` says WATCHDOG, slot 2 is closed because the CPU is high.
- One heavy run at a time per lane. Never two MFab jobs at once. pytest `-n 2` at most.
- STATE=HOT in the status file means start nothing heavy.
- Fair turns: poll for a slot no more often than every 30 s. After you RELEASE a slot, wait 90 s before trying again, so waiting lanes get in.
- Waiting for a slot:
  - use at most ONE waiter loop, sleeping 60 s or more between checks (every process spawn costs kernel CPU here);
  - kill it, and any Monitor/tail you started, before your turn ends.
- TRAP (bridge-census 10-27): TaskStop on a background waiter does NOT kill its child bash/python. A stopped waiter's job can still start later, holding no slot. After any TaskStop, find the children by command line and kill them by PID. cpu_status.txt tags each python job "lock-aware" or "NO LOCK SEEN".
- Search with `git grep` inside your own lane. Never run a recursive grep/find on `../..` or the repo root: that walks every lane, venv and node_modules (one ran a full core for minutes on 10-27).
- Batch your arms into one slot hold where you can, and cache outputs so nothing is digitized twice.

QUESTIONS
Kent 2026-10-27: "qestions from your workers should roll up to you for me to answer."
- Never use AskUserQuestion, and never ask Kent directly.
- SendMessage the director (`local_5b2045fa-a0d8-4424-b855-853dfd5ac53f`) with:
  - the question;
  - 2-4 options, each with what it delivers, its cost and its catch;
  - your pick.
- Then carry on with whatever doesn't depend on the answer.

EXPOSURE (the repo is public)
- Never commit pro files: .DST/.PES/.EMB/.BMP/.pdf from `Claude Personal/Embroidery`, `scratch_kent/` or `Embroidery Files.zip`.
- Never commit renders or crops of them, new client names, or credentials.
- Images go to your session scratchpad; commit numbers only.
- Kent 2026-10-27 on pro renders: "Stop new ones, keep old (Recommended)". `tools/flip_sheet_renders report` writes `__pro.jpg` tiles under docs/ BY DEFAULT, so always pass a scratch `--renders` path. Commit only ours-side images (OFF / ON); the pro's panel goes in local sheets only.

GATES
- Gate 1: a physical constant (stitch length, density, pull, width floor) needs a sew-out. Don't tune one.
- Gate 3: chaining and contour stay as they are.
- Gate 4: quote chance-corrected agreement only, with raw in brackets at most.
- New behaviour ships default OFF, md5-pinned byte-identical OFF.
- Proof is OFF | ON | pro, each design in its own frame, every arm read with one reader.

MD5 PINS (W5-06b flip-proof pins)
- Spread the frozen engine dict in any md5 pin: `tests.conftest.frozen_cfg(...)`, built on `tests/engine_2026_10_27.json`.
- When an md5 goes red, run `tools.ci_repin RUN_ID` before hand-editing it.
- A new PipelineConfig field, or a flip that makes one default-on, must also go into `tests/engine_*.json` in the same PR, with its PRE-flip value. `tests/test_pins_are_frozen.py` fails until it does.
- A new 32-hex pin that spreads no frozen dict fails that same test. If the pin is deliberately about the current default (a golden the flip is meant to move), add `# pin-rides-defaults: <why>` to the test file.

TESTS AND PR
- Run only the tests you touch, plus test_scope_budget.py and test_memory_budget.py.
- Use `> log 2>&1; echo EXIT=$? >> log`. Never pipe to tail. Never run the full suite locally: CI's sharded run is the full check.
- Before every push, run `git fetch origin main && git merge origin/main`. Never rebase.
- Open a ready-for-review PR, not a draft.
- Arm auto-merge while mergeStateStatus is BLOCKED: `gh pr merge N --auto --squash`. Never merge by hand.
- Fix your own red CI. Never skip or xfail a test.
- Add a memory note in `.claude/memory/`, and insert its MEMORY.md line alphabetically by filename (under 260 chars).
- Add one MASTER_SCOPE line only if test_scope_budget passes.
- Done: SendMessage the director with the PR URL, the headline numbers, and any sheet or crop paths. Otherwise stay quiet.
- Never flip a default yourself. Flips are Kent's, from your proof.
