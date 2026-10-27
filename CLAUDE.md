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
  PR-sized work, not a one-time requirements doc. **Current state ONLY, under a
  27,000-word budget, with 400 words per numbered defect.** Its own rules 4
  and 4b set those numbers, and `tests/test_scope_budget.py` enforces them;
  Kent replaced the old 800-line budget. Every claim carries a `(verb date —
  source)` pointer; one without a pointer is unverified.
  - Dated snapshots: `docs/scope-history.md` — append-only. Never quote a number
    from it as live status.
  - Per-area detail: `docs/scope/`.
- **`.claude/memory/MEMORY.md` — for narrative history and decisions.** Indexes
  every entry, the pre-2026-09-15 ones in `.claude/memory/MEMORY-archive.md`
  (not auto-loaded: `emb-bot-digitizer`, `dst-codec-axis-discrepancy`, the Ember
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

**Exception: a worker session started by a foreman or director never asks Kent
directly.** It sends the decision (question, 2-4 options with cost and catch,
its pick) to the session that started it with `SendMessage`, and carries on
with independent work. The director asks Kent and relays his words verbatim
(Kent, 2026-10-27: "qestions from your workers should roll up to you for me to
answer").

## Open PRs ready for review, not as drafts

**Kent's call 2026-08-28.** Open a PR ready-for-review whenever you have
verified the work yourself — tests run, diff re-read adversarially. Keep `draft`
only when you genuinely want his eyes before CI spends an hour or more on it.

Two reasons this is not cosmetic:

- **Auto-merge cannot be armed on a draft.** It fails with *"Pull request is a
  draft"*, so every draft puts the hour-plus `digitizer` wait on Kent instead
  of on the machine (footgun 7 below has the measured budget). He un-drafted
  all four PRs on 2026-08-27/28 himself before merging.
- **Auto-merge has a THIRD refusal you will hit if you wait too long** —
  *"already in clean status … you can merge directly"*. Arm it while
  `mergeable_state` is `blocked` (required checks pending). Once every check is
  green there is nothing left to arm, and the PR simply sits waiting for a human
  click. Hit on PR #289, 2026-08-28.

**Merging is still Kent's.** Ready-for-review and auto-merge are yours to set;
clicking merge is not.

**Arm auto-merge by DEFAULT — Kent's ruling 2026-09-04.** Do not withhold the
arm to force a human look at a trade-off; flag the trade-off in the PR body
instead. Withholding costs hours of throughput per held PR while everything
behind it queues on the one branch, and the arming window closes the moment
the last check goes green (the third refusal above), so a withheld PR becomes
a manual click either way. Measured that day: PR #289's sibling #346 sat green
and unarmable for over an hour with four finished changes stacked behind it.

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

- **Build the digitizer venv with `python3.12` explicitly, NOT the bare `python3`**
  (cloud containers default to 3.11). On 3.11 the `requirements.txt` path leaves a
  venv with no pystitch, and `node --test` then SKIPS the six format
  cross-validation tests and still reports green. That trap and the
  `[service]`-only `httpx2` hole (a collection count ~123 short) are in
  [`digitizer/CLAUDE.md`](digitizer/CLAUDE.md).

- Always `python -m pytest`, never `python foo.py` — a bare invocation does not put
  cwd on `sys.path`.
- **Never pipe pytest to `tail`** — you get tail's exit code, so a red run reads green.
  **This reaches the BACKGROUND-TASK channel too, which is how it still bites.**
  A backgrounded `pytest ... | tail -25` reports *"completed (exit code 0)"* in
  the task notification while pytest returned 1 — the notification is relaying
  tail's code, not pytest's. A session read that 0 as green on 2026-09-14 and
  nearly shipped two self-inflicted failures. Redirect to a log and append the
  code yourself: `pytest -q > log 2>&1; echo "EXIT=$?" >> log`.
- **A cloud container here is FOUR cores, so `-n auto` IS `-n 4`** (`nproc` 4,
  `sched_getaffinity` 4 — measured 2026-09-14). Do not expect the ~9 min Kent's
  Windows box does; **budget ~45 minutes for a full local digitizer run**, and
  read that as healthy rather than hung.
  **The one thing that actually doubles it is starting a SECOND suite.** Two
  full runs overlapping on those four cores measured **79.1 and 80.9 minutes
  against 44.5 solo** — 1.8x, from self-inflicted contention, not from `-n auto`
  and not from any limit. Start one, let it finish.
  **And do not diagnose a long run as killed the way that session did:** `pytest
  -q` buffers, so a log sitting at 8% says nothing, and `pgrep -c pytest`
  returns 0 against a live run because the process is `.venv/bin/python -m
  pytest` (match `pgrep -fc "python -m pytest"` instead). All three runs that
  day were declared dead and all three had completed normally.
- The expected failure classes (golden mismatches on machines that didn't
  capture the golden, OCR skips without `tesseract`) live in `COOKBOOK.md`
  ("Running things"). Check there before treating a red run as a regression.

## Things that will silently go wrong if you skip them

1. **DST axis bug — FIXED 2026-09-08, both halves. The lesson survives it.** EMB-Bot's own DST codec (`src/dst.js` / `src/dstimport.js`) had X in the HIGH nibble of every record byte and Y in the LOW one; the standard is the reverse. It round-tripped correctly with itself and was wrong everywhere else in both directions. **The entry used to say "transposed" and the Studio told customers to rotate; rendered 2026-09-07, a standard reader saw the design a quarter turn round AND mirror-imaged — letters backwards — which no rotation repairs.** **A swapped bounding box fits a turn and a mirror equally, and only a picture separates them: when a claim is about ORIENTATION, render it.** That rule is why this was ever diagnosed correctly, and it still holds.
   **What the fix was:** the two weight tables swapped, in the writer and in `decodeDelta`, so both now match `pystitch.DstWriter.encode_record` bit-for-bit — verified 10/10 byte-identical across a spread of deltas, and the crossval DST control reads `identity` beside PES and EXP. Rendered both ways: a "FRITSCH" export drew a vertical column of reversed letters before and draws FRITSCH upright at its own 127.2 × 22.6 mm after. `decodeDSTStandard` was the 2026-09-07 import workaround and is now a plain alias of `decodeDST` — its own comment predicted exactly that ("these two collapse into one").
   **The one thing still true:** a `.dst` EMB-Bot wrote BEFORE this fix is in the old dialect, so re-importing one reads transposed. That was already so (the import lane went standard on 2026-09-07), so nothing regressed — but old files are not repaired by this either. The service's `/export` remains a second, independent, always-standard path. Full evidence trail: `dst-codec-axis-discrepancy` in memory, DOCTRINE 2026-09-07, `docs/dst-axis-verdict-2026-07-31.md`, `test/dstimport.test.js`'s signed-area test (kept, repointed: it now shows what a transpose would COST, so the next person reaches for a measurement instead).

2. **Never touch `.claude/worktrees/`.** It holds live, uncommitted work from parallel feature lanes — run `git worktree list` for the current set, don't trust any doc's snapshot (including this one). Never `git add -A` from the repo root without reviewing what it's about to stage. Never delete or move anything under this path.

   **The hook (`.claude/hooks/block-worktree-mutation.js`) judges the resolved TARGET, not the command text** (since 2026-10-04). It denies a target that IS the `.claude/worktrees/` directory, a lane root (`rm -rf .`/`*` inside one included), a path inside a lane the command is NOT running in, a directory holding the lanes (`rm -rf <repo>`, `git clean -ffdx` at the root), `git worktree remove` of a lane, `git worktree add` with an empty/unresolvable path from inside a lane, and — failing closed — a target it cannot resolve (a variable from an EARLIER tool call, `$(…)`, xargs stdin) when the text names `.claude/worktrees/`. **A session may delete inside its OWN lane** (Kent 2026-10-04; `OWN_LANE` in the hook). To clean inside a lane from elsewhere, `cd` into it in the same command and spell the target there. `git reset --hard` and `git rm` inside a lane are out of scope (Kent 2026-10-04). Evidence and the transcript replay: `test/worktree-guard.test.js`, `tools/replay-worktree-guard.mjs`, memory `worktree-guard-judges-targets-2026-10-04`.

3. **PowerShell text replacement mangles UTF-8 in this repo.** `(Get-Content -Raw) -replace ... | Set-Content` silently corrupts source file encoding (mojibake + BOM) — no error thrown. Use the Edit tool (or equivalent) for source edits, never a PowerShell regex round-trip.

4. **`.claude/settings.json` (permissions + hooks) does NOT auto-apply inside nested worktrees.** Confirmed empirically 2026-08-03: a Claude session rooted at `.claude/worktrees/<name>/` does not inherit the main repo root's project settings — the PowerShell-corruption guard hook silently didn't fire there until the settings file was copied in. `.claude/` is committed now, so a worktree cut from a current ref carries its own copy — but a worktree cut from an older ref, or a session rooted outside any checkout, still runs bare. Verify the hooks/settings exist in the lane you're working in before trusting them. On Kent's machine a global SessionStart hook (`~/.claude/hooks/roadmap-gates-global.js`, added 2026-08-17) injects the ROADMAP gates for sessions rooted in nested worktrees (any ref — the walk-up finds the primary's ROADMAP.md) and in any secondary checkout that can reach a ROADMAP.md; a sibling checkout on a pre-ROADMAP ref gets nothing, and cloud sessions don't get that safety net at all.

   **"Rooted outside any checkout" happens — measured 2026-10-03.** (a) A session
   started outside the repo (e.g. `C:\Users\EE-LT-11030\.claude-work`) and every
   session it spawns loads no project settings at all — the tell is a
   `list_sessions` row whose `cwd` is not under `EMB-Bot` — and writes its memory
   to `~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, not
   `.claude/memory/`, so check that folder before trusting a snapshot there. (b)
   A session started in a Desktop scratch workspace that moves into a lane keeps
   `CLAUDE_PROJECT_DIR` on the scratch folder, so every guard fails NON-blocking
   and commands run unguarded. On Kent's machine
   `~/.claude/hooks/embot-guards-global.js` (2026-10-04) runs the repo's own
   guards for both cases; cloud sessions and the work CLI profile
   (`~\claude\claude-work`) get no such net, and a new profile folder starts
   with none. A wrong-root session cleaning inside a lane `cd`s into it in the
   same command and names the target (footgun 2). Detail: memory
   `wrong-root-sessions-and-global-guards-2026-10-04`, `memory-outside-the-repo`.

5. **`scratch_*` directories are gitignored but NOT disposable.** `scratch_corpus/` (37-file third-party DST corpus), `scratch_ink/` (Ink/Stitch font clone — `build-embf.mjs` needs it), `scratch_kent/` (Kent's commissioned files), `scratch_packs/`. "Gitignored" here means "kept out of the public repo on purpose", not "safe to delete" — only `scratch_ink/` has a Drive backup (`BACKUPS.md`). Details: `COOKBOOK.md` "Gitignored reference material that is NOT disposable".

6. **Playwright MCP needs an explicit browser path in this class of sandbox.** `@playwright/mcp`'s bundled `playwright-core` expects a newer browser revision than what's pre-cached at `/opt/pw-browsers/`, and outbound access to Playwright's browser-download CDN is blocked (403) in this environment class — so the plain `npx @playwright/mcp@latest` config fails outright, with no download fallback. `.mcp.json` launches it through `tools/mcp-playwright.mjs` instead, which passes `--executable-path /opt/pw-browsers/chromium` only when that path exists (so a machine without it, e.g. Kent's local setup, still gets normal auto-download behavior). Don't simplify `.mcp.json` back to a bare `npx @playwright/mcp@latest` command. Confirmed 2026-08-03.

   **`.mcp.json` carries a SECOND server — `huggingface`, deliberately with NO
   token.** An unset `${HF_TOKEN}` expands to a bare `Bearer `, which turns a
   working anonymous server into a 401 — add the header only alongside a real
   token, and never over a hang or a 5xx (the endpoint is flaky, not your
   config). It is a research tool for model licence and maintenance checks,
   not a runtime dependency; before using it, read the
   [`hf-hub-check`](.claude/skills/hf-hub-check/SKILL.md) skill — a Hub
   licence TAG is not a licence GRANT, and a wrong parameter name reads like a
   true negative.

7. **Three green checks is NOT a green PR — the fourth is the slow one.** CI runs
   four jobs on a PR. `engine` and `studio` finish in well under a minute
   (p50 0.5 and 0.8) and `studio-e2e` in about three (p50 2.7).
   **SHARDED since PR #669 (2026-10-08): `digitizer` is now an aggregator over
   six `digitizer shard k/6` jobs**, still `-n auto` each, and it goes green or
   red seconds after the slowest shard. The first sharded run (split by file
   COUNT, before `tests/.shard_durations.json` existed) took **24.1 minutes**
   wall, first shard start to aggregator end, against 72–78 for the single
   job on main the same day. Its shards ran 6.9–23.9 minutes, and the 23.9 was
   the imbalance the durations file fixes: 235 test-minutes over 6 × 4 workers
   is about 10 minutes of tests per shard, plus a minute of setup. **Budget
   twenty-five, read fifteen as normal**, and if one shard keeps running
   far longer than the others, refresh the durations
   (`digitizer/tools/ci_shard_durations.py` over a run's `digitizer-shard-*`
   JUnit artifacts) rather than adding shards. Its PR body has the balanced
   run's measured time. (A fifth job, `art-fidelity-baseline`, is
   push-to-`main`-only and `continue-on-error` — it never appears on a PR and
   gates nothing.)

   **Every written budget for this job has gone stale in ONE direction** —
   the single pre-sharding job drifted from 15 to 76 minutes between
   2026-08-27 and 10-04, and each revision of this line was true when written
   (history: [`docs/digitizer-ci-timing-history.md`](docs/digitizer-ci-timing-history.md)).
   So spend one `curl` on `/actions/runs/<id>/jobs` before calling a long job
   stuck.

   So a PR shows 3/4 green long
   before it is green, and merging there is how `main` has gone red — run 994
   (PR #249) and run 1006 (PR #253) both merged to a failing conclusion, and
   `preview.js` has arrived unparseable on `main` **four** times, each one caught
   only by the job nobody waited for.

   **`main` requires all four** (branch protection, Kent 2026-08-27, after runs
   994 and 1006), at `enforcement_level: non_admins` so Kent can hand-merge a
   genuine hotfix. Deliberately NOT required: `Supabase Preview` (third-party,
   reports `skipped`). Deliberately off: "require branches up to date" (`main`
   moves constantly). Ruleset `main-1` blocks deletion and force-push on `main`
   — keep it. Read the live state with **plain `curl`** on
   `/repos/KS-Three/EMB-Bot/branches/main` and `/rules/branches/main`: both
   answer an UNAUTHENTICATED request with 200, while `WebFetch` returns 403 on
   the same URLs — that is not "no access". `/branches/main/protection` is the
   genuinely restricted one.

   **Auto-merge WORKS now — arm it instead of waiting or watching.** Measured on
   PR #275, 2026-08-27: `mcp__github__enable_pr_auto_merge` returned *"Auto-merge
   enabled … will merge automatically once all required checks pass"* instead of
   refusing. That is the arming step, which is the part that was impossible
   before; do not sit on a PR watching `digitizer` for an hour. Two
   conditions, both learned on that same PR:

   - **Mark the PR ready for review FIRST.** On a draft it fails with
     *"Pull request is a draft"*. That is a third refusal message, distinct
     from the two at the top of this file. A session hits it whenever it opens a draft, and
     ready-for-review is the default here since 2026-08-28 (top of this file).
   - **Arm it while `mergeable_state` is `blocked`.** That is the state
     required checks produce (required, not yet reported). It is NOT
     `unstable`, which is what this repo used to show.

   **If a PR will not merge, check for a second CI run on the same SHA before
   anything else.** While the workflow fired on both `push` and `pull_request`
   every check name appeared twice on one SHA, and a phantom duplicate pinned
   PR #272 at `unstable` for ~25 minutes; the `on:` block in
   `.github/workflows/python-package-conda.yml` is the fix — keep it.

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
     on 2026-08-27, 1546 on 2026-08-31 (3 failed, 8 skipped, 7 xfailed, 9m28s
     with `-n auto`). Collection is its own tripwire, but read it as a GAP not
     a fixed number, since the total keeps growing: 1509 collected on
     2026-08-27, 1564 on 2026-08-31, and anything ~123 short of the current
     total means `tests/test_service.py` failed to collect (the `httpx2` hole,
     `digitizer/CLAUDE.md`). *(measured 2026-08-31 — full local run, `python3.12` venv)*

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
