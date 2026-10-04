---
name: embot-handover-numbers-and-stacked-branches
description: "Where an earlier session's sweep scripts live (to reproduce handed-over numbers exactly), and how a branch built on an UNMERGED EMB-Bot PR is opened"
metadata:
  node_type: memory
  type: reference
  originSessionId: 392bc7c8-f62c-4ca4-8244-b73b46ad9065
  modified: 2026-10-03T23:23:38.265Z
---

> **Snapshot, copied 2026-10-03 (evening) from outside the repo.** Sessions rooted in
> `C:\Users\EE-LT-11030\.claude-work` keep their memory in
> `~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, which is not this
> folder: nothing written there rides a PR or reaches a session rooted in EMB-Bot.
> The original was still being edited when this was taken, so check a fact here
> before acting on it. See [[memory-outside-the-repo]].

Two things that shaped an EMB-Bot handover task on 2026-10-03 (PR #617, built on the unmerged #616). Both are my own reading of the machine and the repo, not rulings of Kent's.

**Handed-over numbers can be reproduced with the script that made them.** A task prompt that says "measured on N designs" was written from another session's sweep. Those scripts are still on disk under `C:\Users\EE-LT-11030\AppData\Local\Temp\claude\C--Users-EE-LT-11030--claude-work\<session id>\scratchpad\` (grep the scratchpads for a distinctive word from the handover; #616's was `sweep-lib.cjs`). Read-only: copy the generator into my own scratchpad, never write there, and check the folder's mtimes first because the session may still be live. Reproducing #616's "after" column to the stitch is what let a one-line fix be verified as "the old stream minus N records and nothing else".

**How to apply:** reproduce the claim on its own corpus first, then build a second corpus of my own, then hand both to the independent re-measure as claims. The claimant's corpus alone misses things: #616's 8,255 designs had one notch exactly twice a preset's pull compensation wide; the audit's corpus had 581 hits from it.

**A PR can merge at an OLDER head than its session's local branch.** #613 (island fix) merged at `61ec4daa` on 2026-10-03 while that session's audit fixes were still unpushed; a task prompt written from that session's view ("if #613 merged, `distinctCorners` exists and islands are spared") was false for `main`, and the commits went out later as #620. `origin/main` also moved twice under that one task (#613, #617).

**How to apply:** before relying on "PR N merged, so X exists", fetch and `git grep X origin/main`. Fetch again before building a before/after corpus and before pushing; the "before" engine is whatever `origin/main` is then (copy only `src/*.js` via `git show`, 0.6 MB). When two open PRs add the same helper in different places git merges them cleanly into a double declaration: test the union with `git merge-tree --write-tree` plus `git show <tree>:path` into the scratchpad, and tell the peer.

**A branch cut from an unmerged PR targets `main`, not that PR's branch.** `delete_branch_on_merge` is false on KS-Three/EMB-Bot and none of the last 200 PRs had a non-main base (checked 2026-10-03), so a stacked PR would never be retargeted. Cut from the PR's branch with `--no-track`, merge `origin/main` in, open against `main`, say "merge #X first" at the top of the body, and do NOT arm auto-merge: arming would land #X with it. `docs/scope-history.md` conflicts on every such merge because every lane appends at the end; keep both, `main`'s entries first. See [[embot-browser-fill-lane-state]] and [[parallel-agent-with-embot]].
