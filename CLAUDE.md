# EMB-Bot — read this first

**Personal project — kentschaefer3@gmail.com.** Launch via `claude-personal.cmd`, not the Desktop app icon — the Desktop app always authenticates as the default kent@sdwheel.com profile regardless of which folder you're in. (Both addresses already appear in `BACKUPS.md` and `COOKBOOK.md`, so this adds no exposure a public repo did not already have.)

## Read before you act

Each doc gates a different kind of decision. Read the one matching what you're about to do.

- **[`ROADMAP.md`](ROADMAP.md) — before proposing work.** Current build phase, the
  hard dependency gates, and the advisory ordering. A gate is a refusal with the
  blocker named, not a preference. Only Kent advances a phase; you may propose one
  with evidence. A SessionStart hook injects the gate list automatically, but it
  does NOT fire inside a nested worktree or when a session is rooted outside this
  repo — if you have not seen the gates, open the file.
- **`COOKBOOK.md` — before touching code.** The handoff doc: architecture, running
  things, working conventions.
- **`PRODUCT.md` — before making a scope call.** Launch-scope decisions and
  non-goals, previously only in Kent's memory.
- **`MASTER_SCOPE.md` — for current status.** What's implemented, what's not, and
  how much to trust each capability area. A live dashboard kept current after
  PR-sized work, not a one-time requirements doc. **Current state ONLY, under an
  800-line budget.** Every claim carries a `(verb date — source)` pointer; one
  without a pointer is unverified.
  - Dated snapshots: `docs/scope-history.md` — append-only. Never quote a number
    from it as live status.
  - Per-area detail: `docs/scope/`.
- **`.claude/memory/MEMORY.md` — for narrative history and decisions.** Indexes
  every entry (`emb-bot-digitizer`, `dst-codec-axis-discrepancy`, the Ember
  teardowns). Moved into the repo 2026-08-14 so a cloud session gets the same
  context as a local one; on Kent's machine
  `~/.claude/projects/<mangled-repo-path>/memory` is a junction
  pointing here, so automatic memory recall and these files are the same bytes.

## End a turn by PROMPTING Kent, not by describing options

When work finishes and the next step is Kent's decision, **put the choices in
front of him with `AskUserQuestion`** — do not narrate the options in prose and
wait. "Say the word and I'll do X" is not a prompt; it reads as finished work
and stalls until he re-opens the thread himself. He has asked for this
explicitly (2026-08-21), after a session that ended four separate turns with
dangling offers.

Each option needs enough to decide on without scrolling back: what it delivers,
what it costs, and the catch. Include the option you would not pick, if it is
genuinely live.

This is about *decisions that are his* — tiering a font, a physical constant
that needs a sew-out, scope, spending money. Routine judgement calls inside work
he already approved are still yours to make; asking about those is its own kind
of stall.

## This repo is PUBLIC

`gh repo view KS-Three/EMB-Bot` → `visibility: PUBLIC`, confirmed 2026-08-16;
public since creation on 2026-07-22. This file previously claimed it was private,
and a session that believed that could commit something it shouldn't. Keeping it
public is Kent's deliberate call — private repos would cost GitHub Actions credits.

**Treat everything here as world-readable. Assume anything you commit is published.**

- Already exposed and known to Kent: five competitor teardowns,
  `docs/lawyer-brief-cc-by-sa-2026-08-04.md`, the full defect list, a named
  client's artwork (`digitizer/testdata/reference/becker_*.jpg`,
  `Embroidery Files.zip`), and a third-party digitizer's commercial stitch files
  (`becker_*.pes` / `.dst`).
- **Do not add new client artwork, customer names, third-party stitch files,
  credentials, or legal correspondence without asking Kent first.**

## Commands

No root `package.json` — three independent suites, each run from its own directory.

```bash
node --test                                        # engine tests (repo root, no npm deps)
node --test test/geometry.test.js                  # single engine test file
cd app && npm install && npm run dev               # Studio dev server
cd app && npm test                                 # Studio tests (vitest)
cd app && npx vitest run test/foo.test.js          # single Studio test
node tools/build-embf.mjs                          # rebuild the binary font library
tools/start-emb-bot.ps1                            # Windows: both servers + opens browser

cd digitizer && .venv/Scripts/python -m pytest -q -n auto  # Python digitizer tests (runtime + failure classes: COOKBOOK "Running things")
cd digitizer && .venv/Scripts/python -m digitizer_service   # service on 127.0.0.1:8721
```

- **`.venv/Scripts/` is Kent's Windows box. On Linux — every cloud session —
  the same venv is `.venv/bin/python`.** Nothing else changes. This is not
  written down anywhere else a session reads first, so each one rediscovers it;
  `.claude/skills/run-emb-bot/SKILL.md` already handles both layouts.

- **Build that venv with `python3.12` explicitly, NOT the bare `python3`.**
  `digitizer/pyproject.toml` sets `requires-python = ">=3.12"` and cloud
  containers default `python3` to 3.11. `.claude/skills/run-emb-bot/SKILL.md`
  has said this since it was written — it is repeated here because CLAUDE.md is
  read first and the skill only when invoked.
  **The trap is the `requirements.txt` path**, which does NOT enforce that floor
  the way `pip install -e .` does: it gets as far as `numpy==2.5.1`, which
  publishes no 3.11 wheel, and leaves a venv with no pystitch in it. The failure
  is then quiet exactly where it matters — `node --test` SKIPS the six format
  cross-validation tests and still reports green.
  *(hit 2026-08-22; CI pins 3.12, which is why CI never saw it)*

  **The `pip install -e` path has the MIRROR hole**, so neither documented way
  of building this venv is complete. The `service` extra asks for
  `fastapi>=0.115` UNPINNED, which now resolves `starlette` 1.6, whose
  `TestClient` refuses to import without **`httpx2`** — a separate
  distribution that nothing here pins. Adding `dev` does not save you: it
  installs `httpx>=0.27`, which is a DIFFERENT package from `httpx2`, so the
  skill's own recommended `pip install -e ".[service,dev]"` still has the hole.
  Starlette says so verbatim: *"The starlette.testclient module requires the
  httpx2 package to be installed."*

  The result is a COLLECTION error on `tests/test_service.py`, so its **123
  tests never run** — and pytest reports that as a bland `4 errors` line beside
  a large passing count, which is very easy to wave past. A session did exactly
  that and then published an understated number in a PR body.
  **Symptom:** `1309 tests collected` instead of 1432, or `3 failed, 1291
  passed` where the reference below says 1414+. **Fix:** `pip install httpx2`.
  CI is unaffected — it installs from `requirements.txt`, which pins
  `starlette==1.3.1` and `httpx==0.28.1`, a combination whose TestClient works.
  *(found 2026-08-26 by chasing a suspicious number in my own PR body)*

- Always `python -m pytest`, never `python foo.py` — a bare invocation does not put
  cwd on `sys.path`.
- **Never pipe pytest to `tail`** — you get tail's exit code, so a red run reads green.
- The expected failure classes (golden mismatches on machines that didn't
  capture the golden, OCR skips without `tesseract`) live in `COOKBOOK.md`
  ("Running things"). Check there before treating a red run as a regression.

## Things that will silently go wrong if you skip them

1. **DST axis bug.** EMB-Bot's own DST codec (`src/dst.js` / `src/dstimport.js`) is transposed vs. the Tajima/pyembroidery standard — confirmed, unresolved (fixing it is Kent's call; every existing EMB-Bot DST is affected). Browser-encoded DST round-trips correctly with itself but reads wrong-orientation in third-party software. Treat browser DST as EMB-Bot-internal only; the Python digitizer service's `/export` (pyembroidery convention) is the trustworthy path for anything leaving this app. Full evidence trail: `dst-codec-axis-discrepancy` in memory.

2. **Never touch `.claude/worktrees/`.** It holds live, uncommitted work from parallel feature lanes — run `git worktree list` for the current set, don't trust any doc's snapshot (including this one). Never `git add -A` from the repo root without reviewing what it's about to stage. Never delete or move anything under this path.

3. **PowerShell text replacement mangles UTF-8 in this repo.** `(Get-Content -Raw) -replace ... | Set-Content` silently corrupts source file encoding (mojibake + BOM) — no error thrown. Use the Edit tool (or equivalent) for source edits, never a PowerShell regex round-trip.

4. **`.claude/settings.json` (permissions + hooks) does NOT auto-apply inside nested worktrees.** Confirmed empirically 2026-08-03: a Claude session rooted at `.claude/worktrees/<name>/` does not inherit the main repo root's project settings — the PowerShell-corruption guard hook silently didn't fire there until the settings file was copied in. `.claude/` is committed now, so a worktree cut from a current ref carries its own copy — but a worktree cut from an older ref, or a session rooted outside any checkout, still runs bare. Verify the hooks/settings exist in the lane you're working in before trusting them. On Kent's machine a global SessionStart hook (`~/.claude/hooks/roadmap-gates-global.js`, added 2026-08-17) injects the ROADMAP gates for sessions rooted in nested worktrees (any ref — the walk-up finds the primary's ROADMAP.md) and in any secondary checkout that can reach a ROADMAP.md; a sibling checkout on a pre-ROADMAP ref gets nothing, and cloud sessions don't get that safety net at all.

5. **`scratch_*` directories are gitignored but NOT disposable.** `scratch_corpus/` (37-file third-party DST corpus), `scratch_ink/` (Ink/Stitch font clone — `build-embf.mjs` needs it), `scratch_kent/` (Kent's commissioned files), `scratch_packs/`. "Gitignored" here means "kept out of the public repo on purpose", not "safe to delete" — only `scratch_ink/` has a Drive backup (`BACKUPS.md`). Details: `COOKBOOK.md` "Gitignored reference material that is NOT disposable".

6. **Playwright MCP needs an explicit browser path in this class of sandbox.** `@playwright/mcp`'s bundled `playwright-core` expects a newer browser revision than what's pre-cached at `/opt/pw-browsers/`, and outbound access to Playwright's browser-download CDN is blocked (403) in this environment class — so the plain `npx @playwright/mcp@latest` config fails outright, with no download fallback. `.mcp.json` launches it through `tools/mcp-playwright.mjs` instead, which passes `--executable-path /opt/pw-browsers/chromium` only when that path exists (so a machine without it, e.g. Kent's local setup, still gets normal auto-download behavior). Don't simplify `.mcp.json` back to a bare `npx @playwright/mcp@latest` command. Confirmed 2026-08-03.

7. **Three green checks is NOT a green PR — the fourth is the slow one.** CI runs
   four jobs. `engine` and `studio` finish in well under a minute; `digitizer`
   takes 12–18 minutes and `studio-e2e` several. So a PR shows 3/4 green long
   before it is green, and merging there is how `main` has gone red — run 994
   (PR #249) and run 1006 (PR #253) both merged to a failing conclusion, and
   `preview.js` has arrived unparseable on `main` **four** times, each one caught
   only by the job nobody waited for.

   **Enable auto-merge on the PR instead of waiting or watching**
   (`mcp__github__enable_pr_auto_merge`, or the button in the GitHub UI). GitHub
   then holds the merge until all four pass and merges it unattended. Kent's call,
   2026-08-26, chosen over branch protection deliberately: it costs nothing, needs
   no admin settings, and still leaves a genuine hotfix hand-mergeable.

   **UNVERIFIED — this may not actually be possible via the API.** Two attempts
   the same day, on PRs #268 and #269, both refused with *"The pull request is in
   unstable status (required checks are failing)"* while NOTHING was failing —
   every check was `success` or `in_progress`. The repo has
   `allow_auto_merge: true`, zero rulesets, and branch protection that a session
   token cannot read (403). Likely cause: with no REQUIRED checks, GitHub has
   nothing to hold the merge on, so it refuses while pending and would refuse
   again as "clean" once green. Both PRs were merged by hand instead.

   That second half was never tested — the green window passed while the session
   was asleep — so do not treat this paragraph as settled either way. **Settle it
   in one call:** on the next PR, once all four checks are green, invoke
   `enable_pr_auto_merge` and read the error. "clean status" / "already
   mergeable" ⇒ auto-merge needs a required check (branch protection or a
   ruleset) and the advice above must be rewritten. Success ⇒ delete this
   warning. Kent can also answer it instantly from Settings → Branches, which a
   session cannot see. *(2026-08-26)*

   Two related traps, both already bitten:
   - **`pytest` exit codes.** `pytest > log; echo $?` is fine, but whatever runs
     LAST sets the code your harness reports — a wrapper ending in `tail` reports
     tail's `0` over pytest's `1`. Read the recorded code, not the harness's.
   - **The digitizer suite's expected reds.** A full local run fails exactly
     three golden tests (`test_pushcomp`, `test_flat_lane_byte_identical`,
     `test_stage2_photo_segment` — platform-level numerics). CI deselects those
     same three by node ID, so local `3 failed, 1414 passed` and a green CI job
     agree. A FOURTH failure is a real regression. *(measured 2026-08-26)*
