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

  **The `pip install -e ".[service]"` path has the MIRROR hole** — but ONLY
  that path, and the difference matters. The `service` extra asks for
  `fastapi>=0.115` UNPINNED, which now resolves `starlette` 1.6, whose
  `TestClient` wants **`httpx2`** — a separate distribution that nothing here
  pins. `service` is deliberately minimal (fastapi, uvicorn,
  python-multipart), so on its own NEITHER package is present and the import
  raises verbatim: *"The starlette.testclient module requires the httpx2
  package to be installed."*

  **Adding `dev` DOES save you, as of `starlette` 1.6.0** — so the skill's
  recommended `pip install -e ".[service,dev]"` is complete, and this entry
  used to say the opposite. `testclient.py` tries `httpx2`, then FALLS BACK to
  `httpx`, and raises only when neither is installed; `dev` ships
  `httpx>=0.27`, so you get a `StarletteDeprecationWarning` and all 123 tests.
  Verified 2026-08-31 by uninstalling `httpx2` and re-collecting:
  `123 tests collected`, warning only. Don't spend a session chasing a
  phantom — but do keep the tripwire below, because the `[service]`-only path
  still fails exactly as described, and an older `starlette` has no fallback.

  When it DOES bite, it is a COLLECTION error on `tests/test_service.py`, so
  its **123 tests never run** — and pytest reports that as a bland `4 errors`
  line beside a large passing count, which is very easy to wave past. A
  session did exactly that and then published an understated number in a PR
  body. **Symptom:** a collection count ~123 short of the reference below
  (`1309` against 1432 when this was found; `1441` against 1564 on
  2026-08-31). **Fix:** `pip install httpx2`, or install the `dev` extra.
  CI is unaffected — it installs from `requirements.txt`, which pins
  `starlette==1.3.1` and `httpx==0.28.1`, a combination whose TestClient works.
  *(found 2026-08-26 by chasing a suspicious number in my own PR body;
  scoped down 2026-08-31 after the `[service,dev]` half was measured false)*

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

   **The hook that enforces this judges the TARGET, not the command text — since 2026-10-04.** `.claude/hooks/block-worktree-mutation.js` used to deny any Bash/PowerShell call that both named `.claude/worktrees/` and contained `rm`/`rmdir`/`rd`/`del`/`mv` as a word ANYWHERE — a scratchpad cleanup in a command that set `WT=…/.claude/worktrees/…`, a JS variable called `mv`, prose, `rm vt.log` inside the session's own lane. Measured 2026-10-03 over real transcripts: 1.6% of a wrong-root session's shell calls and 0.5% of a repo-rooted one's, every sampled catch a false positive, and the global hook on Kent's machine now runs it for every session. It now splits the call into simple commands, resolves each destructive verb's paths (payload `cwd`, a `cd`/`git -C` earlier in the same command, `VAR=` and `$name =` assignments, `~`, `$HOME`, `$PWD`, Git Bash `/c/…`, globs) and denies only a target that IS the `.claude/worktrees/` directory, a lane root (`rm -rf .`/`*` inside one included), a path inside a lane the command is NOT running in, a directory holding the lanes (`rm -rf <repo>`, `git clean -ffdx` at the root), `git worktree remove` of a lane, or `git worktree add` with an empty/unresolvable path from inside a lane (the 2026-08-31 incident). A target it cannot resolve (a variable from an EARLIER tool call, `$(…)`, xargs stdin) is denied only when the text also names `.claude/worktrees/` — failing closed on exactly the old guard's true positives. **A session may delete inside its OWN lane** (payload cwd, or a `cd` in the same command, inside that lane) — Kent's ruling 2026-10-04: `allow`; `files-only` and `deny` are one-word flips of `OWN_LANE` in the hook. When it denies you, the reason names the target and the rule; a wrong-root session cleaning inside a lane `cd`s in first. Evidence: `test/worktree-guard.test.js` (pipe-tests) and `tools/replay-worktree-guard.mjs`, which replays old rule vs new over real `*.jsonl` transcripts without executing anything. Memory: `worktree-guard-judges-targets-2026-10-04`.

3. **PowerShell text replacement mangles UTF-8 in this repo.** `(Get-Content -Raw) -replace ... | Set-Content` silently corrupts source file encoding (mojibake + BOM) — no error thrown. Use the Edit tool (or equivalent) for source edits, never a PowerShell regex round-trip.

4. **`.claude/settings.json` (permissions + hooks) does NOT auto-apply inside nested worktrees.** Confirmed empirically 2026-08-03: a Claude session rooted at `.claude/worktrees/<name>/` does not inherit the main repo root's project settings — the PowerShell-corruption guard hook silently didn't fire there until the settings file was copied in. `.claude/` is committed now, so a worktree cut from a current ref carries its own copy — but a worktree cut from an older ref, or a session rooted outside any checkout, still runs bare. Verify the hooks/settings exist in the lane you're working in before trusting them. On Kent's machine a global SessionStart hook (`~/.claude/hooks/roadmap-gates-global.js`, added 2026-08-17) injects the ROADMAP gates for sessions rooted in nested worktrees (any ref — the walk-up finds the primary's ROADMAP.md) and in any secondary checkout that can reach a ROADMAP.md; a sibling checkout on a pre-ROADMAP ref gets nothing, and cloud sessions don't get that safety net at all.

   **"Rooted outside any checkout" is not hypothetical — measured 2026-10-03, two ways.** (a) Eight Desktop sessions in one family — a parent started in `C:\Users\EE-LT-11030\.claude-work` (a leftover config folder, not a repo) and the seven it spawned, directly or through each other; a child session inherits its parent's root. They worked in the right lanes by absolute path — about 3,500 shell commands — with no project settings loaded: that folder holds no `.claude/settings.json`, and the 23 transcripts from that root carry no record of either roadmap hook or of any of the four PreToolUse guards, where repo-rooted transcripts carry the `roadmap-gates.js` record at every start. (A guard that passes silently leaves NO record, so a missing guard name proves nothing on its own; the SessionStart record is the usable tell.) No damage was found: none of those commands matched the replace guard, and the three bare `git add -A .` ran inside one lane's `digitizer/`. (b) A session started in a Desktop scratch workspace that then moves into a lane keeps `CLAUDE_PROJECT_DIR` on the scratch folder, so every guard dies with `Cannot find module ...\scratch-workspaces\...\.claude\hooks\...`. That is a NON-blocking hook error, so the command runs unguarded — 20 Bash calls in `library-filter` and `break-risk`, 2026-10-01/02. **The tell for (a):** `cwd` in a `list_sessions` row is not under `EMB-Bot`. **It also splits the memory:** a wrong-root session's notes land in `~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, not in `.claude/memory/` — seven EMB-Bot notes were sitting there, unseen by every repo-rooted and cloud session. They are in `.claude/memory/` now as snapshots, each marked as one (four on 2026-10-03, two of those refreshed and three added on 2026-10-04, Kent's call), but a wrong-root session that is still running still writes there, so check that folder before trusting a snapshot's status. `memory-outside-the-repo` in memory has the detail.

   **On Kent's machine both holes are closed for the shell guards since 2026-10-04** by a global PreToolUse hook, `~/.claude/hooks/embot-guards-global.js` (Kent's call). It carries no copy of any rule: it reads the guard list from the primary checkout's `.claude/settings.json`, runs those guards from its `.claude/hooks/`, and stays out wherever the project's own copy is healthy, so a guard added here is picked up there. A wrong-root session also gets the roadmap gates, and a pointer to this file, on its first repo command. Evidence: 18 pipe-tests beside the hook (`node --test`); a replay of 351 real commands from those sessions with 0 hook errors, which let one command through (a repo path spelled `$HOME\...`) and, with that fixed, denied all 60 the repo's own regexes catch; and two running wrong-root sessions receiving the gates within a minute of wiring, without a restart. **What it costs:** one `node` start per shell call in every session on the machine, and the guards themselves — a median of 1 to 2 seconds on the loaded laptop — only for a repo command whose project hooks are not healthy. **What it does not cover:** cloud sessions, and the work CLI profile (`~\claude\claude-work`), whose `settings.json` carries no hooks at all. The personal CLI profile (`~\claude\claude-personal`, what `claude-personal.cmd` uses, starting in the `Claude Personal\` container rather than in this repo) had none either; since 2026-10-04 it carries the same hooks block as `~/.claude/settings.json`, and a headless run under it recorded the guard hook firing and the gates arriving. A global hook lives in ONE profile's settings: a new profile folder starts with none. **One thing it makes more visible:** `block-worktree-mutation.js` now reaches a wrong-root session too, and since 2026-10-04 (PR #629) it judges the resolved TARGET of each `rm`/`mv`/`del`/`rd`, not the command text — footgun 2 has the full rule. In short it denies a lane root, the `.claude/worktrees/` directory, an ancestor holding the lanes, a path inside a lane the command is not running in, or a target it cannot resolve when the text names `.claude/worktrees/`. The last two are the ones a wrong-root session meets: it cleans inside a lane by absolute path, which is denied because the command is not running there, and it names its lane in nearly every command, so an `rm -rf "$OUT"` whose variable was set in an EARLIER tool call is denied, fail-closed. The recipe is one command that `cd`s into the lane and names the target there — the `cd` is how it proves where it runs, the spelled target is what the guard can resolve — and the deny reason says the first (`rm -rf <lane>/out` from `.claude-work` denied, `cd <lane> && rm vt.log` allowed; both are pipe-tests in `test/worktree-guard.test.js`, 2026-10-04). **The 1.6% / 0.5% figures are the OLD text rule's catch rate** — a wrong-root session's shell calls denied against a repo-rooted one's, measured 2026-10-03, every sampled catch a scratchpad cleanup or a JS variable called `mv` rather than a lane deletion. They are why the rule changed, not a description of the guard that runs now.

5. **`scratch_*` directories are gitignored but NOT disposable.** `scratch_corpus/` (37-file third-party DST corpus), `scratch_ink/` (Ink/Stitch font clone — `build-embf.mjs` needs it), `scratch_kent/` (Kent's commissioned files), `scratch_packs/`. "Gitignored" here means "kept out of the public repo on purpose", not "safe to delete" — only `scratch_ink/` has a Drive backup (`BACKUPS.md`). Details: `COOKBOOK.md` "Gitignored reference material that is NOT disposable".

6. **Playwright MCP needs an explicit browser path in this class of sandbox.** `@playwright/mcp`'s bundled `playwright-core` expects a newer browser revision than what's pre-cached at `/opt/pw-browsers/`, and outbound access to Playwright's browser-download CDN is blocked (403) in this environment class — so the plain `npx @playwright/mcp@latest` config fails outright, with no download fallback. `.mcp.json` launches it through `tools/mcp-playwright.mjs` instead, which passes `--executable-path /opt/pw-browsers/chromium` only when that path exists (so a machine without it, e.g. Kent's local setup, still gets normal auto-download behavior). Don't simplify `.mcp.json` back to a bare `npx @playwright/mcp@latest` command. Confirmed 2026-08-03.

   **`.mcp.json` carries a SECOND server since 2026-09-12 — `huggingface`, and it
   deliberately sends NO token.** A remote HTTP server at
   `https://huggingface.co/mcp`, added so a session can check a candidate model's
   **license and maintenance status against the Hub** instead of against its own
   README — which matters here specifically because this is a commercial product
   in a public repo and the embroidery-adjacent prior art is largely GPL-3.0
   (Ink/Stitch). **But a Hub licence TAG is a publisher declaration, not a licence
   GRANT — never stop at the tag.** `ZhengPeng7/BiRefNet` reads `license:mit` in
   search results AND in its model card's YAML front matter, yet the weights repo
   ships **no LICENSE file at all** — 9 files, none a licence (`hf_fs find --name
   *LICENSE*` returns zero entries, checked 2026-09-12) — and a 3-vote
   adversarial review REFUTED *"BiRefNet is MIT for BOTH code and published
   weights"* **0-3**. Read the actual file with `hf_fs` before calling any licence
   settled; `docs/tooling-research-2026-09-12.md` §3 carries the full trail.
   **The two endpoints also disagree on DOWNLOAD counts** — `hub_repo_search`
   reported 42.9K for `BiRefNet_HR-matting` where `hub_repo_details` says 2.5M,
   and 1.9M vs 20.0M for `facebook/sam3` — so treat a count as order-of-magnitude
   and never quote one as a measured figure. **Anonymous access is real, measured
   2026-09-12:** `initialize` returns HTTP 200 with no credential and
   `tools/list` gives four tools — `hf_whoami`, `hub_repo_search`,
   `hub_repo_details`, `hf_fs` (which reads files out of a Hub repo, so a
   `LICENSE` can be read directly rather than inferred from a tag). A token
   would add more (paper/space/doc search), but there is **no
   `Authorization` header on purpose**: an unset `${HF_TOKEN}` expands to a bare
   `Bearer `, and sending an empty credential is worse than sending none — it
   turns a working anonymous server into a 401. Add the header only alongside a
   real token, never speculatively.
   **That 200 is no longer the common case — re-measured 2026-09-15: 4 of 11.**
   The other seven were `500` or, mostly, `504` after a THIRTY-SECOND hang, on a
   machine where `https://huggingface.co/` itself answers 200 in 0.15 s. So a
   hang or a 5xx here is the MCP endpoint, not your config and not a missing
   token — do not go add `${HF_TOKEN}` to `.mcp.json` over it (see the paragraph
   above for why that makes it worse). Retry two or three times: the runs that
   did connect completed the handshake and returned the same four tools,
   unchanged. **This is also why a session can see the server's instructions and
   still have NO `mcp__huggingface__*` tools** — `initialize` succeeded and
   `tools/list` did not, which looks like the server is tool-less rather than
   flaky. Hit exactly that way on 2026-09-15.
   **The trap is `hub_repo_search`'s parameter name.** It takes **`repo_types`, an
   ARRAY** (`["model"]`), not `repo_type`. Pass the singular and the call
   SUCCEEDS and returns *"No repositories found for the given criteria"* — a wrong
   argument reads exactly like a true negative, so a session concludes the model
   does not exist on the Hub. Hit while adding this, on a model with 985K
   downloads. **This is NOT a runtime dependency** — nothing in `digitizer/`,
   `src/`, or `app/` calls it, and it moves no defect on its own; it is a
   research-loop tool for license and maintenance questions.

7. **Three green checks is NOT a green PR — the fourth is the slow one.** CI runs
   four jobs on a PR. `engine` and `studio` finish in well under a minute
   (p50 0.5 and 0.8) and `studio-e2e` in about three (p50 2.7).
   **`digitizer` runs 33 to 55 minutes** — re-measured 2026-09-12 over the
   last 36 successful jobs: min **32.7**, p50 **49.7**, p90 54.6, max 55.4,
   with daily medians 48.6 (09-11) and 50.6 (09-12). **Budget an hour, and
    read a 50-minute job as normal rather than stuck.** **Re-measured
    2026-09-29 on PR #562: 1h 02m 50s — above the 09-12 range; the drift the
    paragraph below predicts is happening.**
   **Re-measured 2026-09-30: 65.2 minutes on PR #563, green** — the last
   five successful jobs read 33.3 / 45.0 / 54.0 / 58.4 / 65.2, so the top
   has moved past the hour the line above budgets. Budget seventy, read an
   hour as normal, and spend the one `curl` on `/actions/runs/<id>/jobs`
   before calling anything stuck: that job's test step was live the whole
   time. **And 66.2 on PR #567 the same night, green** — a tree that took
   four merges of `main` inside one PR; the record moves a minute at a
   time now, so seventy is the budget until a job passes it.
   **One did — 75.9 minutes (1h 15m 56s) on PR #575, 2026-09-30, green**,
   on a diff that touched only `.claude/skills/`, so the job's length is the
   suite's, not the change's. **Budget eighty**, read seventy-five as normal,
   and still spend the `curl` before calling anything stuck. (A fifth job,
   `art-fidelity-baseline`, is push-to-`main`-only and `continue-on-error` — it
   never appears on a PR and gates nothing.)

   This line keeps going stale in one direction, so read the trend rather
   than the number: "12–18" (medians 15.0–15.2, 2026-08-27/28) → "10 to 42"
   (220 jobs, 2026-09-06, after the daily median walked 15.0 → 16.5 → 17.6 →
   18.7 → 20.7 → **29.6**, max 41.8) → this. Every revision was TRUE WHEN
   WRITTEN. **The 09-06 text is what makes this worth re-measuring rather
   than nudging:** it said budget half an hour and read 35 minutes as normal,
   and half an hour is now BELOW the fastest job on record — so a session
   trusting it reads a perfectly healthy run as hung and goes looking for a
   failure that is not there. That nearly happened on PR #469, whose
   `digitizer` job took **53m 59s** and went green. If you are reading this
   after 2026-09-12, assume it has drifted again and spend one `curl` on
   `/actions/runs/<id>/jobs` before concluding anything about a long job.

   So a PR shows 3/4 green long
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
     escape hatch. **Kent's call 2026-08-27: delete `main-2`** — leaving branch
     protection as the single layer enforcing the four checks, at `non_admins`.
     A session cannot do it: `DELETE /rulesets/21660819` returns 403 to a
     session token.
     **DONE — verified 2026-08-31, nothing left to chase here.**
     `/rules/branches/main` now returns ONLY ruleset 21660818 (`main-1`,
     `deletion` + `non_fast_forward`); `main-2` is gone. `/branches/main`
     confirms the intended end state survived it: `protected: true`,
     `enforcement_level: non_admins`, contexts exactly
     `engine, studio, studio-e2e, digitizer`.

   Read the live state with `GET /repos/KS-Three/EMB-Bot/rules/branches/main`
   and `GET /repos/KS-Three/EMB-Bot/branches/main`.
   **Use plain `curl` — the repo is public and both answer an UNAUTHENTICATED
   request with HTTP 200.** Don't conclude "no access" from a tool that
   refuses: `WebFetch` returns 403 on these same URLs, and a session that
   stops there reports the ruleset state as unverifiable when one `curl` — no
   token needed — settles it. `/branches/main/protection` is the genuinely
   restricted one. *(measured 2026-08-31)*

   **Auto-merge WORKS now — arm it instead of waiting or watching.** Measured on
   PR #275, 2026-08-27: `mcp__github__enable_pr_auto_merge` returned *"Auto-merge
   enabled … will merge automatically once all required checks pass"* instead of
   refusing. That is the arming step, which is the part that was impossible
   before; do not sit on a PR watching `digitizer` for an hour. Two
   conditions, both learned on that same PR:

   - **Mark the PR ready for review FIRST.** On a draft it fails with
     *"Pull request is a draft"*. That is a third refusal message, distinct
     from the two below. A session hits it whenever it opens a draft, and
     ready-for-review is the default here since 2026-08-28 (top of this file).
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
     on 2026-08-27, 1546 on 2026-08-31 (3 failed, 8 skipped, 7 xfailed, 9m28s
     with `-n auto`). Collection is its own tripwire, but read it as a GAP not
     a fixed number, since the total keeps growing: 1509 collected on
     2026-08-27, 1564 on 2026-08-31, and anything ~123 short of the current
     total means `tests/test_service.py` failed to collect (the `httpx2` hole
     above). *(measured 2026-08-31 — full local run, `python3.12` venv)*

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
