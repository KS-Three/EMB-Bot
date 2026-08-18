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
  `~/.claude/projects/C--Users-EE-LT-11030-Personal-EMB-Bot/memory` is a junction
  pointing here, so automatic memory recall and these files are the same bytes.

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

cd digitizer && .venv/Scripts/python -m pytest -q  # Python digitizer tests (~21 min serial; -n auto is parallel-safe)
cd digitizer && .venv/Scripts/python -m digitizer_service   # service on 127.0.0.1:8721
```

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
