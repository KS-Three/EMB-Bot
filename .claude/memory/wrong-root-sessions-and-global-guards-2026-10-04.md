---
name: wrong-root-sessions-and-global-guards-2026-10-04
description: Eight sessions rooted in `.claude-work` worked the right repo with no project hooks, CLAUDE.md or repo memory; a global hook now applies the repo's guards to them. How to check a session's root, and what the check cannot see
metadata:
  type: project
---

Kent asked (2026-10-03) whether his running Claude sessions were on the right
EMB-Bot repo. They were. The finding was underneath that.

**The repo was right.** Every lane's `origin` was `KS-Three/EMB-Bot`, every
bound PR's head repo was `KS-Three/EMB-Bot`, every lane sat in the primary
checkout's `git worktree list`.

**The root was wrong.** Five of six listed sessions had `cwd`
`C:\Users\EE-LT-11030\.claude-work` — an old work-profile config folder, not a
repo. One parent ("Parallel agent with embot", started 2026-10-02 from the
Desktop app) was rooted there and every session it spawned inherited the root:
eight in the family. They reached the repo by absolute path, so:

- no project settings: none of the four PreToolUse guards, no roadmap gates
  (the global SessionStart hook walks up from the root and finds no ROADMAP.md);
- no project CLAUDE.md unless read by hand;
- their auto-memory went to
  `~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, mixed with
  work notes. Kent's call 2026-10-04: review them, then bring the EMB-Bot ones
  in. Seven were imported that day as SNAPSHOTS, each marked as one, bodies
  byte for byte ([[parallel-agent-with-embot]],
  [[embot-browser-fill-lane-state]],
  [[embot-handover-numbers-and-stacked-branches]], [[embot-closed-ring-lane]],
  [[embot-sub-unit-stitches-lane]], [[embot-star-walk-lane]],
  [[build-what-was-priced]]). The sources were copied, not moved: the sessions
  that wrote them are still running and still writing there, so that folder is
  where a newer version of any of the seven will be. The work notes stayed;
  they are not this repo's and one holds an account identifier.

No damage was found: of about 3,500 shell commands none matched the replace
guard, and three bare `git add -A .` ran inside one lane's `digitizer/`.

**A second hole, same scan.** A session started in a Desktop scratch workspace
and moved into a lane keeps `CLAUDE_PROJECT_DIR` on the scratch folder; every
guard then dies with `Cannot find module` as a non-blocking error and the
command runs (20 Bash calls, `library-filter` and `break-risk`, 10-01/02).

**The fix (Kent chose "make guards global", 2026-10-03).**
`~/.claude/hooks/embot-guards-global.js`, wired in `~/.claude/settings.json`
under PreToolUse `Bash|PowerShell`. It reads the guard list from the primary
checkout's `.claude/settings.json` and runs the guards from its `.claude/hooks/`
— no copy of any rule — and stays out where the project's own copy is healthy.
Tests: `node --test` on `embot-guards-global.test.mjs` beside it (17). The
pre-change settings are at `~/.claude/settings.json.bak-2026-10-03-pre-embot-guards`.
CLAUDE.md footgun 4 carries the numbers.

**How to apply — checking sessions:**

- `list_sessions` gives `cwd`; a root not under `EMB-Bot` is the tell.
  `get_session` adds `parentSessionId`, which is how the family was traced.
- `list_events` shows that a tool was called but NOT its arguments. To find
  which lane a session works in, `search_session_transcripts` for the lane
  path, or read the PR bound to the session.
- A hook that succeeds silently leaves no trace in a transcript. Absence of
  `block-powershell-replace.js` proves nothing; the usable trace is the
  SessionStart `roadmap-gates.js` record, or a dry run of the hook with the
  session's root as `cwd`. Errors and context injections do leave records
  (`hook_non_blocking_error`, `hook_additional_context`).
- Editing `~/.claude/settings.json` reaches RUNNING sessions: the new hook
  fired in other sessions about twenty seconds after the edit. A broken global
  hook is therefore broken everywhere at once; pipe-test before wiring.

**Open, not done:**

- `block-worktree-mutation.js` matches `rm`/`mv`/`del`/`rd` as a word anywhere
  in a command that names `.claude/worktrees/`. Replayed: 1.6% of a wrong-root
  session's shell calls against 0.5% of a repo-rooted one's, and the sampled
  catches were scratchpad cleanups. The guard wants to look at the TARGET.
- `.claude-work` cannot simply be deleted: `~/.claude/settings.json`'s
  statusLine runs `.claude-work\statusline.ps1`.
- The CLI profile folders (`~\claude\claude-personal`, `~\claude\claude-work`)
  have no hooks in their `settings.json`, so `claude-personal.cmd` sessions get
  no global hook of any kind.

Related: [[worktree-session-harness-guard-2026-09-17]],
[[concurrent-session-designed-the-same-tool-2026-09-17]],
[[worktree-add-empty-var-wipes-cwd]].
