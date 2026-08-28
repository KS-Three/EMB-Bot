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
- **`DOCTRINE.md` — before proposing work.** What has already been decided,
  tried, disproved, or paid for: standing rulings, measured negatives,
  corrections, and the traps that cost a session. Split out of MASTER_SCOPE
  2026-08-28 because it does not go stale and only accumulates, so it kept
  crowding out current status. **No line budget — but nothing enters unless it
  would change what someone DOES.**
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

## Open PRs ready for review, not as drafts

**Kent's call 2026-08-28.** Open a PR ready-for-review whenever you have
verified the work yourself — tests run, diff re-read adversarially. Keep `draft`
only when you genuinely want his eyes before CI spends fifteen minutes on it.

Two reasons this is not cosmetic:

- **Auto-merge cannot be armed on a draft.** It fails with *"Pull request is a
  draft"*, so every draft puts the ~15-minute `digitizer` wait on Kent instead
  of on the machine. He un-drafted all four PRs on 2026-08-27/28 himself before
  merging.
- **Auto-merge has a THIRD refusal you will hit if you wait too long** —
  *"already in clean status … you can merge directly"*. Arm it while
  `mergeable_state` is `blocked` (required checks pending). Once every check is
  green there is nothing left to arm, and the PR simply sits waiting for a human
  click. Hit on PR #289, 2026-08-28.

**Merging is still Kent's.** Ready-for-review and auto-merge are yours to set;
clicking merge is not.

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
   four jobs on a PR. `engine` and `studio` finish in well under a minute;
   `digitizer` takes 12–18 minutes and `studio-e2e` several. (A fifth job,
   `art-fidelity-baseline`, is push-to-`main`-only and `continue-on-error` — it
   never appears on a PR and gates nothing.) So a PR shows 3/4 green long
   before it is green, and merging there is how `main` has gone red — run 994
   (PR #249) and run 1006 (PR #253) both merged to a failing conclusion, and
   `preview.js` has arrived unparseable on `main` **four** times, each one caught
   only by the job nobody waited for.

   **Protection is ON as of 2026-08-27 — `main` now requires all four.**
   Kent added it after runs 994 and 1006 showed what merging at 3/4 costs.
   Measured state, all of it readable without admin:

   - **Branch protection** requires `engine`, `studio`, `studio-e2e`,
     `digitizer` — all `app_id: 15368` (GitHub Actions) — at
     `enforcement_level: non_admins`, so Kent bypasses and a genuine hotfix
     stays hand-mergeable. Deliberately NOT required: `Supabase Preview`
     (third-party, reports `skipped`, requiring it could hang PRs).
     Deliberately off: "Require branches to be up to date" (`main` moves
     constantly here; it would force a merge-forward on every PR).
   - **Two rulesets also landed alongside it.** `main-1` (id 21660818) blocks
     `deletion` and `non_fast_forward` on `main` — keep it, nobody should be
     force-pushing `main`. `main-2` (id 21660819) required the SAME four checks
     with **no bypass actors**, which stacks on top of branch protection and
     (per GitHub's docs — not measured here) cancels the `non_admins` hotfix
     escape hatch. **Kent's call 2026-08-27: delete `main-2`**, leaving branch
     protection as the single layer enforcing the four checks, at `non_admins`.
     A session cannot do it — `DELETE /rulesets/21660819` returns 403 to a
     session token. If a future read still shows `main-2` present, it was never
     executed; say so rather than assuming.

   Read the live state with `GET /repos/KS-Three/EMB-Bot/rules/branches/main`
   and `GET /repos/KS-Three/EMB-Bot/branches/main` — both answer a session
   token, even though `/branches/main/protection` returns 403 to one.

   **Auto-merge WORKS now — arm it instead of waiting or watching.** Measured on
   PR #275, 2026-08-27: `mcp__github__enable_pr_auto_merge` returned *"Auto-merge
   enabled … will merge automatically once all required checks pass"* instead of
   refusing. That is the arming step, which is the part that was impossible
   before; do not sit on a PR watching `digitizer` for 15 minutes. Two
   conditions, both learned on that same PR:

   - **Mark the PR ready for review FIRST.** On a draft it fails with
     *"Pull request is a draft"* — a third refusal message, distinct from the
     two below, and the one a session hits by default, since PRs here are
     opened as drafts.
   - **Arm it while `mergeable_state` is `blocked`.** That is the state
     required checks produce (required, not yet reported). It is NOT
     `unstable`, which is what this repo used to show and what the note below
     describes.

   **Why it used to refuse, for the record.** Before protection existed the tool
   failed in BOTH available states — *"in unstable status (required checks are
   failing)"* while checks were pending (nothing was failing; every check was
   `success` or `in_progress`), and *"already in clean status … you can merge
   directly"* once green. Tried on PRs #268, #269, #272. The cause was that the
   repo had zero required checks, so the pending window the tool wants never
   existed. Adding the required checks created that window.

   **The CI double-run was fixed FIRST, on purpose** — see the `on:` block in
   `.github/workflows/python-package-conda.yml`. While the workflow fired on
   both `push` and `pull_request`, every PR head got two runs and every check
   name appeared twice on one SHA; a phantom duplicate run pinned PR #272 at
   `unstable` for ~25 minutes on 2026-08-26. Cosmetic then, a hard merge block
   now that the checks are required. If you are reading this because a PR will
   not merge, check for a second run on the same SHA before anything else.

   Two related traps, both already bitten:
   - **`pytest` exit codes.** `pytest > log; echo $?` is fine, but whatever runs
     LAST sets the code your harness reports — a wrapper ending in `tail` reports
     tail's `0` over pytest's `1`. Read the recorded code, not the harness's.
   - **The digitizer suite's expected reds.** A full local run fails exactly
     three golden tests (`test_pushcomp`, `test_flat_lane_byte_identical`,
     `test_stage2_photo_segment` — platform-level numerics). CI deselects those
     same three by node ID, so a local run and a green CI job agree. A FOURTH
     failure is a real regression. **Trust the three NAMED tests, not the
     total** — the count moves as tests land: 1414 passed on 2026-08-26, 1491
     on 2026-08-27. Collection is its own tripwire: 1509 collected that day,
     and anything near 1309 means `tests/test_service.py` failed to collect
     (the `httpx2` hole above). *(measured 2026-08-27)*

8. **`git log --all -- <path>` will tell you a file NEVER existed when your
   remote refs are stale — and the wrong answer looks thorough.** A cloud
   session starts from a fresh clone, but `origin/*` only knows what that clone
   fetched; anything pushed to another lane afterwards is invisible. `git log
   --all`, a `git ls-tree` sweep over `git rev-list --all`, and a filesystem
   `find` will then all agree, confidently, that the file is absent and never
   existed — three independent checks corroborating one stale snapshot.
   **Run `git fetch --all` BEFORE concluding that prior work does not exist.**
   Hit 2026-08-27: a session was asked to continue work whose reasoning and
   rejected-approach table lived in an unmerged
   `digitizer/tools/edge_smoothness.py`, ran all three checks, and reported the
   file had never been committed on any branch. One `git fetch --all` produced
   it — on a sibling lane, intact. The cost of being wrong here is rebuilding
   from scratch exactly what someone wrote down so it would not have to be.
