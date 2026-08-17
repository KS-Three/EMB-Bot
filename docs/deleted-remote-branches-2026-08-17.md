# Deleted remote branches — 2026-08-17

All were merged into `origin/main` at `4967ed5` except
`claude/real-art-parity-docs`, noted below. Restore any of them with:

```bash
git push origin <sha>:refs/heads/<branch-name>
```

| branch | tip | reachable from main? |
|---|---|---|
| applique-precut-scissors-floor-gate | `c688ede` | yes |
| applique-pull-comp-and-gaps | `b18b8ea` | yes |
| applique-zigzag-cover-style | `7c29bb2` | yes |
| art-prep-guidance-copy | `94aa0d9` | yes |
| border-seam-real-fix | `baa7abc` | yes |
| claude/emb-bot-connectors-plugins-ui0yfs | `70fcaee` | yes |
| claude/emb-bot-document-flow-08gvrv | `72d50c2` | yes |
| claude/emb-bot-link-4mbmmg | `1ab138d` | yes |
| claude/emb-bot-status-prmlr7 | `ad85f82` | yes |
| claude/embot-cleanup-review-zo17ao | `84b7297` | yes |
| claude/pro-parity-loop | `195892c` | yes |
| claude/real-art-parity-and-restore-146 | `8d4e8e0` | yes |
| color-block-sequencer-ui | `0bf2e99` | yes |
| crosshatch-fill-pattern | `7d76006` | yes |
| digitize-panel-test-harness | `d37ebc4` | yes |
| docs-emberdesign-competitive-research | `b06b956` | yes |
| fill-angle-candidate-sweep | `f6bb7fa` | yes |
| fix-chaining-benchmark-fixture | `28ff433` | yes |
| fix-corrupted-golden-json | `e047982` | yes |
| fix-corrupted-textcluster-test-merge | `d951867` | yes |
| fix-export-routing | `02cd97c` | yes |
| fix-lettering-defects-hole-and-regularization | `a578941` | yes |
| fix-satin-flush-corner-short-stitch-guard | `5458b6c` | yes |
| icon-digitize-panel-icons | `1967506` | yes |
| icon-embroidery-field-icons | `093b88b` | yes |
| icon-manual-content-icons | `301393e` | yes |
| icon-smaller-panels-icons | `b10b1cb` | yes |
| insert-vertex-on-edge-click | `75f650c` | yes |
| kent/owl-fixture | `fd17a66` | yes |
| manual-shape-curve-tool | `63c05f7` | yes |
| manual-trace-algorithm | `f5c49fc` | yes |
| manual-trace-e2e | `30a5404` | yes |
| manual-trace-ui | `5fe7948` | yes |
| ocr-suggested-text-convert-flow | `717d97c` | yes |
| refresh-corpus-scorecard-baseline | `e455b6c` | yes |
| remove-legacy-standalone-tool | `cd9dfcb` | yes |
| revert-146-claude/pro-parity-loop | `a6435f2` | yes |
| sam2-segmentation | `d79b8f9` | yes |
| satin-classifier-flat-lane-starburst-fix | `5c3d580` | yes |
| seeds-boundary-contrast-fix | `9d155b1` | yes |
| seeds-superpixel-swap | `6819551` | yes |
| shape-editor-ux-fixes | `71a8661` | yes |
| simplify-tol-mm-scaling-audit | `f650aad` | yes |
| stepnav-layout-ux-fixes | `f6d9396` | yes |
| streamline-fill-flat-lane-override | `ebcb2c4` | yes |
| text-cluster-ocr-confidence-gate | `5d6dedb` | yes |
| textcluster-classical-cv-additions | `19d86e8` | yes |
| ui-icon-system-foundation | `015432f` | yes |
| verify-background-enclosed-live-browser | `bc02c5f` | yes |
| wave-chevron-brick-fill-patterns | `7596064` | yes |
| worktree-agent-a31030c31112d963f | `bc1e59e` | yes |
| worktree-agent-a738d2ebf157d3820 | `1af1825` | yes |
| worktree-agent-a948fa626ac000ec0 | `33c6ff6` | yes |
| worktree-agent-a9efa9bc9f16702db | `c1b9e35` | yes |
| worktree-agent-abdf5554cfb57b3e5 | `8e668d3` | yes |
| worktree-agent-ae54554e9a59d0767 | `8e42313` | yes |
| worktree-agent-af7246f02af344839 | `5f18e94` | yes |
| claude/real-art-parity-docs | `9e92813` | **NO — see note** |

**`claude/real-art-parity-docs` (`9e92813`) is the one commit here that does NOT
survive in `main`'s history.** Its content — "Three" → "Four" findings and a
`describe` → `describes` fix in MASTER_SCOPE's START HERE block — was reapplied
by hand in `832b79f` rather than merged, so nothing in `main` reaches the commit
object.

**Anchored with a tag so the row above is actually true:**
`archive/real-art-parity-docs`, pushed to `origin`. Without it that SHA would
have gone unreachable the moment the local branch was deleted, and a recorded SHA
for a garbage-collected object is not a recovery path — it just looks like one.
Every other branch in the table is reachable from `main`, so no tag is needed.

Delete the tag if you ever decide the commit is genuinely not worth keeping:

```bash
git push origin --delete archive/real-art-parity-docs && git tag -d archive/real-art-parity-docs
```

Kept deliberately: `main`, `claude/emb-bot-stitch-fill-5t69ut` (PR #152, an
open `DO NOT MERGE` draft) and `claude/satin-gate-attribution` (active).
