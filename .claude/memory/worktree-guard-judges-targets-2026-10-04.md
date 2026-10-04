---
name: worktree-guard-judges-targets-2026-10-04
description: "The rm/mv worktree guard now resolves each destructive verb's TARGET instead of matching the command text; what it denies, what it lets through on purpose, the own-lane question put to Kent, and the replay tool that measures it over real transcripts"
metadata:
  type: project
---

# The worktree guard judges targets, not text — 2026-10-04

**What was wrong.** `.claude/hooks/block-worktree-mutation.js` denied any
Bash/PowerShell call that both named `.claude/worktrees/` and contained
`rm`/`rmdir`/`rd`/`del`/`mv` as a word anywhere. Replayed over real
transcripts since 2026-10-01 (2026-10-03): 57 of 3,553 shell calls in
wrong-root sessions (1.6%), 8 of 1,679 in repo-rooted ones (0.5%), and every
sampled catch was a false positive — a scratchpad `rm -rf redcheck` in a
command that set `WT=…/.claude/worktrees/…`, a JS variable called `mv`, `rm
vt.log` inside the session's own lane, prose saying "NEVER run `claude rm`".
Since 2026-10-04 the global hook on Kent's machine runs the same guard for
wrong-root sessions, so those denials reach more sessions. It denied THIS
session's own smoke-test command (a heredoc naming the lane beside `rm`).

**What it does now.** Splits the command into simple commands (newlines, `;`,
`&&`, `||`, `|`, subshell parens; quote-aware; heredoc bodies parsed line by
line in their own scope), resolves each destructive verb's path arguments
against the payload `cwd`, a `cd`/`pushd`/`Set-Location`/`git -C` earlier in
the same command, `VAR=`/`export`/`$name =`/`for v in` assignments, `~`,
`$HOME`, `$PWD`, `$env:X`, Git Bash `/c/…`, WSL `/mnt/c/…`, `C:\…`, and
globs — then denies only when a target is:

1. the `.claude/worktrees/` directory or a glob over it;
2. a lane root, including `rm -rf .` / `*` from inside one;
3. inside a lane the command is NOT running in (OWN_LANE policy);
4. an ancestor holding the lanes (`rm -rf <repo>`, `rm -rf .claude`,
   `git clean -ffdx` at the root) — probed on disk, read-only;
5. unresolvable (a variable from an earlier tool call, `$(…)`, `$_`, xargs
   stdin) AND the command text names `.claude/worktrees/`;
6. `git worktree remove`/`move` of a lane; `git worktree add` with a missing
   or bare-unresolvable path from inside a lane ([[worktree-add-empty-var-wipes-cwd]]).

Verbs: rm rmdir rd del erase unlink Remove-Item ri; mv move Move-Item mi
Rename-Item ren; `find -delete`/`-exec rm`; `xargs rm`; `bash -c`, `cmd /c`,
`powershell -Command`, `eval` are re-lexed. A parse failure falls back to the
old text rule, so it is never more open than before.

**Fail-closed choice, and why.** An unresolvable target is denied only when
the command also names `.claude/worktrees/`. That is exactly the set the old
guard denied, minus everything it can now prove safe — so the true positives
it had (`rm -rf "$LANE"` with `LANE` set in the same command resolves and is
denied on its own; one set in an EARLIER call is caught by the text rule) are
kept, and a command that never mentions a lane is treated as it always was.
The residual: `cd "$UNKNOWN" && rm -rf name` is allowed (relative, does not
climb, does not name a lane); it reaches a lane only if `$UNKNOWN` is exactly
`.claude/worktrees`. Heredoc bodies are judged as commands, so writing a
script that contains a lane deletion is denied (conservative, rare).

**Own lane — Kent's ruling 2026-10-04: `allow`.** A target inside a lane passes
when the command runs inside that same lane (payload cwd, or a `cd` in the
same command — a wrong-root session proves intent by `cd`-ing in first; its
absolute-path deletes inside a lane are denied with a reason saying so). Lane
roots stay denied regardless. `files-only` and `deny` are one-word flips of
`OWN_LANE` in the hook; `EMB_WORKTREE_GUARD_OWN_LANE` overrides for tests.

**Evidence.** `test/worktree-guard.test.js`: 60-odd pipe-tests (stdin JSON →
stdout JSON), the four false positives, the true positives, both policies,
ancestors and a symlinked cwd on a real temp tree. `tools/replay-worktree-guard.mjs`
replays old rule vs new over `*.jsonl` transcripts without executing anything:

    node tools/replay-worktree-guard.mjs --since 2026-10-01 \
      "C:\Users\EE-LT-11030\.claude\projects\C--Users-EE-LT-11030--claude-work" \
      "C:\Users\EE-LT-11030\.claude\projects\C--Users-EE-LT-11030-Claude-Personal-EMB-Bot"

**A cloud session cannot run that replay** — the transcripts live on Kent's
machine and nothing in Drive holds them; the before/after over real
transcripts is a one-command job on his box. On the one transcript the cloud
container had (this session's), old and new agreed on 1 of 19 calls, the
heredoc that wrote the smoke corpus.

**Lesson.** When a guard is about WHAT a command destroys, judge the resolved
target; text matching turns every mention of the protected path into a
denial, and the denials land on the sessions that mention it most — the ones
working carefully by absolute path.

**The replay happened, 2026-10-04 evening — on Kent's laptop, driven from a
cloud session.** A Remote Control session rooted in the repo on his machine
ran it (reached with `send_message` from the claude-code-remote MCP; it
answered in its own reply text because the bridge has no cloud-bound send).
`--since 2026-10-01 --recursive`, 5,021 shell calls: old rule **74**
denials, new guard **9**. The 9: three `git worktree remove <lane>` from the
repo root (true positives — Kent keeps those denied, a session hands lane
removal to him), three `SCR="$(cygpath -u '…')" && … rm -rf "$SCR/base2"`
inside a lane (the documented substitution residual; the target was the
scratchpad), three false positives. The 69 newly allowed, from the guard's
own per-row findings: 50 scratchpad deletes, 11 with no destructive command
at all (the old regex matched `rm`/`mv` inside JavaScript, prose, a filename,
or `git rm`), 7 own-lane temp files, 1 `.git/worktrees/<lane>/index.lock`.
Nothing newly allowed touched a lane root or another session's lane.
`git reset --hard` and `git rm` inside a lane are judged by neither guard;
Kent's call: out of scope. Full tables: the comment on PR #629.

**The three false-positive shapes, fixed the same evening (issue #633):**

- **A — a modifier on a variable the guard knew.** `${S:?}` lexed as the
  name `S:` (the name class held `:` for PowerShell's `env:X`), and
  `${pr%%:*}` / `${pr##*:}` were opaque substitutions. Now `${X:?}`,
  `${X:-w}`, `${X:=w}` read as X when X is known and `%`/`%%`/`#`/`##` trim a
  known X by a plain glob. An UNKNOWN X stays unresolvable even beside a
  default word — substituting the default would let a lane set in an earlier
  tool call through, which the old guard caught.
- **B — an assignment on the same line as `do`/`then`.** The leading
  `NAME=value` loop ran before the reserved words were stripped, so
  `do d="$W/x"; rm -rf "$d"` read as a command named `do`, lost the
  assignment, and `$d` failed closed. The strip now comes first. (The same
  assignment on its own line always worked.)
- **C — commit-message prose in a heredoc.** `git commit -F - <<'EOF'` with a
  wrapped line `move (4,038 of 145,600 swept stars, …` was lexed as the verb
  `move` with the paren group as its target. Heredoc body lines stay judged
  as commands (a heredoc fed to `bash` can delete a lane), but inside a bash
  heredoc an unresolvable target that begins with `(` — never a path — is
  now `status: 'prose'`. `$X`, `$(…)` and backticks in a heredoc still fail
  closed, so `rm "$WHAT" is gone` in a commit message would still deny; a
  known residual, not measured in any real call.
