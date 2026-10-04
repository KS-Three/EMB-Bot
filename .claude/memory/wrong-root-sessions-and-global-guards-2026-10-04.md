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
- their auto-memory went to another project's memory folder. That half, and
  the seven notes snapshotted in from it, is [[memory-outside-the-repo]].

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
Tests: `node --test` on `embot-guards-global.test.mjs` beside it (18). The
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

**What this session got wrong, so the next one does not.** It asked Kent what
to do with "five notes nobody in the repo can see" and then imported seven,
while four of them were already snapshotted in an OPEN PR (#619, from a
session rooted in the repo that had found the same split the day before).
That PR merged first and the import had to be redone around it. The session
list had been read; the open PRs' diffs had not. Before proposing to add a
file, `git fetch` and look for it on every lane, not only on `main`:
`git log --all --oneline -- <path>`. Same class as
[[concurrent-session-designed-the-same-tool-2026-09-17]].

**Open, not done:**

- `block-worktree-mutation.js` matches `rm`/`mv`/`del`/`rd` as a word anywhere
  in a command that names `.claude/worktrees/`. Replayed: 1.6% of a wrong-root
  session's shell calls against 0.5% of a repo-rooted one's, and the sampled
  catches were scratchpad cleanups. The guard wants to look at the TARGET.
- `.claude-work` cannot simply be deleted: `~/.claude/settings.json`'s
  statusLine runs `.claude-work\statusline.ps1`.
- The work CLI profile (`~\claude\claude-work`) has no hooks in its
  `settings.json`. Unused since 2026-09-18; Kent left it.

**The personal CLI profile, 2026-10-04 (Kent's pick).** `claude-personal.cmd`
sets `CLAUDE_CONFIG_DIR` to `~\claude\claude-personal` and starts in the
`Claude Personal\` container, so its sessions had neither project hooks nor
any global one, and it was in use (16 transcripts in 14 days). It now carries
the same hooks block as `~/.claude/settings.json` (backup beside it,
`settings.json.bak-2026-10-04-pre-hooks`). Proof it loads there: one headless
`claude -p` turn with `CLAUDE_CONFIG_DIR` set, whose transcript records
`PreToolUse:PowerShell` running the guard hook and the gates arriving. A
global hook belongs to ONE profile's settings file; each profile needs its
own copy of the block. That profile's statusLine points at a script that no
longer exists (`.claude-personal\plugins\cache\caveman\...`); not fixed.

Related: [[worktree-session-harness-guard-2026-09-17]],
[[concurrent-session-designed-the-same-tool-2026-09-17]],
[[worktree-add-empty-var-wipes-cwd]].
