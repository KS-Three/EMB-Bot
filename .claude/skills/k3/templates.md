# K3 templates

## Session preamble
Build lane from the EMB-Bot foreman under Kent's delegation (<date>). Read CLAUDE.md first
(python3.12 venv at digitizer/.venv/bin/python; never pipe pytest to tail). Finish within
<N> minutes. Rules: don't edit MASTER_SCOPE.md, docs/scope-history.md, DOCTRINE.md,
CLAUDE.md or COOKBOOK.md; don't run the full digitizer suite locally (CI shards it), run
only tests for files you touch; check open PRs first (git fetch --all) and don't duplicate
in-flight work; merge origin/main before every push (never rebase); keep the diff tight;
status goes in the PR body; message nobody unless blocked; ask Kent only for decisions
that are genuinely his. Open a PR READY FOR REVIEW against main, arm auto-merge
(enable_pr_auto_merge) while mergeable_state is blocked, never merge. If CI goes red on
your PR, fix it.

## Sweep (send_later, 30 min)
Foreman sweep (quiet mode). Dispatch one Sonnet steward: arm/undraft all open PRs; for
dirty or truly red heads (ignore all-cancelled digitizer runs) find the owning session via
list_sessions branch match and message it; report only exceptions. Don't subscribe to new
PRs individually. Tell Kent only orphaned PRs, decisions that are his, or a summary if he
asks. Re-arm for 30 min while any foreman session or open PR is active.

## Support-crew brief (local agents, Sonnet)
Slice: open PRs whose number mod N == K. Owner ACTIVE = running or updated <20 min.
Never merge, rebase, force-push or skip tests; never touch .claude/worktrees/ or the
foreman's checkout — fresh scratchpad worktree only, verify pwd before git writes; never
push to an ACTIVE owner's branch (message it instead). Roles: REVIEWER (blocking findings
only → owner), MEDIC (dirty → merge origin/main if owner idle, else message), TRIAGE (real
red on current head → root cause + patch to owner), SHEPHERD (orphaned PRs: ready, armed,
small fixes). Report <120 words; flag anything that needs Kent.

## Rules broadcast (when quieting the team)
Foreman rule, from Kent directly: stop sending routine updates. Ask Kent (AskUserQuestion)
ONLY for a decision that is genuinely his. Message the foreman ONLY when blocked, needing a
branch/permission you lack, or when you found something that affects another session.
Progress, test counts and measurements go in your PR body.
