---
name: ci-pin-hygiene-2026-10-25
description: "2026-10-25 — W3-05: hex `==` prints whole (tests/_hexrepr.py), `tools.ci_repin` re-pins from a run id (dry run unless --apply), shard map refreshed (max/mean 1.28 -> 1.00), advisory `default-path-diff` CI job"
metadata:
  type: project
---

# CI pin hygiene (W3-05) — 2026-10-25

Most red PR runs were a pin captured on another host or gone stale behind a
flip (#1057: 5 pin failures in one run, all `flip`), not a regression. Four
pieces, no engine change.

**The brief's premise was half wrong, and that changed the design.** "pytest
truncates md5s in CI logs" is true of the headline and the `FAILED` summary line
(`assert 'bc28d37bc555...9cca8aed4db69' == '4793...'`, ~30 chars a side) — but the
`- / +` diff block under it carries BOTH values whole for any plain `str == str`.
Checked on runs 40114417261, 40153615642, 40079863088, 40225844309: every hash
failure had the full pair. So `tools/ci_repin.py` reads the diff block (and the
`left :`/`right:` lines `tests/_hexrepr.py` adds) and refuses only a failure whose
log holds nothing but the cut headline (a tuple/dict compare) — not every run from
before the plugin, as the brief said.

- **`tests/_hexrepr.py`** (`addopts = "-p tests._hexrepr"` in pyproject, not
  conftest: open PRs edit it) answers a `==` between two 32/64-hex strings with the
  headline whole. Needs `python -m pytest` (cwd on `sys.path`), which every
  entry point here already uses. pytest trims the `FAILED` line to the terminal
  width unless `CI` is set — the meta-test sets it.
- **`tools/ci_repin.py RUN NODE...`** — ledger (node, old, new, explained_by) and
  patch; WRITES NOTHING without `--apply`, all rows or none. Orientation comes from
  the SOURCE (the hash that is a literal in `tests/*.py` is the pin), never from
  left/right. Refuses: node not failed, no whole pair, neither/both hashes literal,
  old pin held in 2+ places (`--all-occurrences`), one pin to two values.
  `explained_by` = `flip` only when a default moved between merge-base and head
  (shared key changed, or a NEW key that starts on — a new OFF flag adds a key and
  moves nothing); else `UNEXPLAINED: a regression until shown otherwise`. It never
  decides a moved pin is fine. Proven as a dry run on #1057's run 40225844309.
- **Shards:** unknown files weigh p75 (was the median), >5% unmeasured warns in
  every shard's log, `ci_shard_durations.py` prints the plan before/after scored on
  the fresh timings. Refreshed from green main run 40226250229 (48 of 401 files had
  been unmeasured): predicted max shard 52.9 -> 41.4 test-min, max/mean 1.28 -> 1.00.
- **`tools/default_path_diff.py`** — five fixed jobs through `pro_pair.request`,
  merge-base vs head on one runner, plan/DST md5 + counts. Artwork is read from the
  HEAD tree for both sides (a changed fixture must not look like an engine
  change). `--set` is head-only (`--set flag=false` proves OFF equals base with no
  hard-coded hash). The three small jobs digitize head twice; a non-repeatable job
  is dropped and listed. CI job is `pull_request` + `digitizer/` only,
  `continue-on-error`, NOT required. It SUPPLEMENTS the md5 pins (a pin also
  catches drift that landed in main between two PRs); making it required, or
  changing the brief template's cross-commit OFF-pin rule, is not this note's call.

**Traps:** the CI job's base is `pull_request.base.sha` (the merge commit's first
parent), so main's own flips are not blamed on the PR; a plain `merge-base` against
a moved `origin/main` would blame them. Local Windows run: five jobs identical,
Becker 128-147 s each at 60 mm (100 mm is ~3 min), small jobs 22-40 s.

Related: [[parallel-agent-with-embot]], [[worktree-session-harness-guard-2026-09-17]].
