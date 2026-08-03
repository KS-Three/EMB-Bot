# EMB-Bot — read this first

Read `COOKBOOK.md` before touching code — it's the handoff doc (architecture, running things, working conventions). Read `PRODUCT.md` before making a scope call — it's the launch-scope decisions and non-goals, previously only in Kent's memory. Full narrative history/decisions live in Kent's Claude memory (`emb-bot-digitizer`, `dst-codec-axis-discrepancy`), not this repo.

## Three things that will silently go wrong if you skip them

1. **DST axis bug.** EMB-Bot's own DST codec (`src/dst.js` / `src/dstimport.js`) is transposed vs. the Tajima/pyembroidery standard — confirmed, unresolved (fixing it is Kent's call; every existing EMB-Bot DST is affected). Browser-encoded DST round-trips correctly with itself but reads wrong-orientation in third-party software. Treat browser DST as EMB-Bot-internal only; the Python digitizer service's `/export` (pyembroidery convention) is the trustworthy path for anything leaving this app. Full evidence trail: `dst-codec-axis-discrepancy` in memory.

2. **Never touch `.claude/worktrees/`.** It holds live, uncommitted work from parallel feature lanes — run `git worktree list` for the current set, don't trust any doc's snapshot (including this one). Never `git add -A` from the repo root without reviewing what it's about to stage. Never delete or move anything under this path.

3. **PowerShell text replacement mangles UTF-8 in this repo.** `(Get-Content -Raw) -replace ... | Set-Content` silently corrupts source file encoding (mojibake + BOM) — no error thrown. Use the Edit tool (or equivalent) for source edits, never a PowerShell regex round-trip.

4. **`.claude/settings.json` (permissions + hooks) does NOT auto-apply inside nested worktrees.** Confirmed empirically 2026-08-03: a Claude session rooted at `.claude/worktrees/<name>/` does not inherit the main repo root's project settings — the PowerShell-corruption guard hook silently didn't fire there until the settings file was copied in. When creating a new worktree, copy `.claude/settings.json` into `.claude/worktrees/<name>/.claude/settings.json` too, or the hooks/permissions guarding this repo won't protect work done in that lane.
