# Conventions & memory digest

Source scope: COOKBOOK.md, CLAUDE.md, README set (app/, digitizer/, BACKUPS.md,
sam2_isolated/, rembg_isolated/, testdata/inbox/), all `.claude/memory/`, all
`.claude/agents/`, all `.claude/skills/`, `.claude/settings.json` hooks.

## Working conventions that bind

- Read order before code: `COOKBOOK.md` → `PRODUCT.md` (scope calls) → `MASTER_SCOPE.md` (status, current-state only, 800-line cap) → `.claude/memory/MEMORY.md`. Skipping = acting on stale status (CLAUDE.md).
- Process: brainstorm → spec → plan → build in a git worktree (`subagent-driven-development`/ULTRACODE) → adversarial/multi-lens review before merge. Deviating "will surprise Kent" (COOKBOOK.md § Working conventions this project has settled on).
- Engine changes must be additive/back-compat: new `opts.*` defaults to today's exact output, no migration (COOKBOOK.md § Working conventions; `emb-bot-reviewer`).
- Never trust a prior summary; `git log` is ground truth — COOKBOOK exists because a memory note claimed "merged to main" for work sitting in a worktree (COOKBOOK.md § Working conventions, § Branches & worktrees).
- Never touch `.claude/worktrees/` (delete/move/stage); never `git add -A` from repo root — sweeps another lane's uncommitted work (CLAUDE.md §2; enforced by hook).
- Never edit source via PowerShell `(Get-Content -Raw) -replace | Set-Content` — silent BOM/mojibake, bit this repo twice (CLAUDE.md §3; COOKBOOK.md § Hard-won lessons).
- Engine-file lists must stay in sync in THREE places: `app/scripts/copy-engine.mjs` ENGINE_FILES, `app/src/lib/emb.js` ENGINE_KEYS, `<script>` tags in `app/index.html`. Missing the third broke fonts in the browser while tests stayed green (COOKBOOK.md § Binary font library; `add-font` SKILL.md).
- Fonts: Ink/Stitch-style `inkstitch:satin_column` rails+rungs only; `ALLOWED_LICENSES` = OFL-1.1 / CC-BY-4.0 / CC-BY-SA-4.0 / CC0; only `tier:"verified"` ships and tiering is Kent's call, not an agent's (`add-font` SKILL.md; COOKBOOK.md § Binary font library).
- Python pipeline invariants (wrong = silently bad output, not a crash): RGB uint8 internally (cv2 gives BGR), CIELAB via `skimage.rgb2lab` on [0,1] floats, thread match by CIEDE2000, mm floats with origin at artwork bbox centre and **y-down**, `bg_mask True = background`, warnings carry ENUM codes, machine limits only in `machine.py`, fabric presets mirror `src/fabrics.js` exactly (digitizer/README.md § Conventions that other code depends on; memory/emb-bot-digitizer.md).
- Exactly one y-flip, in `digitizer_core/adapter.py`; `/digitize` returns a `Design`, never a DST (digitizer/README.md; memory/dst-codec-axis-discrepancy.md).
- Run pytest as `cd digitizer && .venv/Scripts/python -m pytest -q`; bare `pytest`/`python probe.py` leaves cwd off `sys.path` (COOKBOOK.md § The Python digitizer; digitizer/README.md).
- Never pipe pytest to `tail` — you get tail's exit code and a red suite reports success (COOKBOOK.md § Hard-won lessons).
- Determinism: `medial_axis(rng=0)` required; stage 2 ships its own seeded k-means; `opencv-contrib-python-headless` is exact-pinned — bump deliberately, then re-check fixtures (digitizer/README.md § Determinism, § Satin for ribbons).
- License policy, digitizer: MIT/BSD/Apache-2.0/zlib only, no GPL/AGPL ever; Ink/Stitch (GPL-3.0) may be read for algorithms, never copied (digitizer/README.md § License policy; memory/inkstitch-research.md).
- Every PR needs a green Actions run **and** a local pass before merge (COOKBOOK.md § Running things).
- `MASTER_SCOPE.md` claims need a `(verb date — source)` pointer with verb `confirmed`/`measured`/`suspected`; test counts/suite totals/corpus grades are banned from it and go to `docs/scope-history.md` (append-only) (`update-master-scope` SKILL.md).
- Push/merge is Kent's explicit call, never automatic (COOKBOOK.md § Branches & worktrees).
- Never re-capture a golden from a Windows run (memory/windows-goldens-fail-locally.md).

## Traps and hazards

- Playwright e2e is NOT in CI and goes dark silently; 9 service-backed specs were failing for 3 days after an icon swap changed accessible names, and the failure signature is a 300 s locator TIMEOUT that reads as a slow machine (COOKBOOK.md § Hard-won lessons).
- Windows-specific: 3 byte-identical goldens fail locally and pass on `ubuntu-latest`; one contour, 0.3208 vs 0.3784 mm²; the golden's own capture commit fails locally too. Judge by "same failure set before and after"; expect 8 failed locally with `.[service]` (5 of them OCR/tesseract) (memory/windows-goldens-fail-locally.md; COOKBOOK.md § Running things).
- Windows: `rm -rf` on a directory junction deletes the real target's contents; a moved venv keeps running but every console-script `.exe` shim breaks silently (memory/emb-bot-digitizer.md § Gotchas).
- CI has failed since 2026-08-09 with `runner_id: 0` in 2-4 s (no runner assigned) on many PRs — an account billing/quota issue, not code; Kent merges past that exact signature (COOKBOOK.md § Running things).
- Parallel lanes each test against their own base, so cross-lane breakage appears only in the merged full suite (6 tests broke this way at once) (COOKBOOK.md § Hard-won lessons).
- `make_valid` returns nested types (`GeometryCollection` holding a `MultiPolygon` + `LineString`); a flat geom filter found zero polygons and stage 4 silently dropped 2,787 mm² for three days. Flatten recursively; take every part clearing the sewable floor (COOKBOOK.md § Hard-won lessons).
- A warning that makes a large loss sound routine is itself the defect — report HOW MUCH was discarded (COOKBOOK.md § Hard-won lessons).
- `BACKGROUND_ENCLOSED`'s old "toggle it back on in review" text was false: enclosed pixels never got a `shape_id` (COOKBOOK.md § Known bugs).
- A module can be committed, imported and documented and still never execute — `stage6_border.py` was unreachable for a session; grep the call site (memory/emb-bot-digitizer.md § Gotchas).
- Green tests are not quality evidence: Step 4 shipped on 68 green mechanical tests while producing starbursts (COOKBOOK.md; `emb-bot-reviewer`; `stitch-geometry-auditor`).
- Metrics lie unless validated on known-good geometry: a fan metric scored a clean ribbon identical to the spraying logo; scoring by mean hides bimodal defects (use per-pixel median/percentile) (COOKBOOK.md; memory/emb-bot-digitizer.md).
- Synthetic references have flattered this codebase in four independent places (stage-0 gate, `stage6_blend` ramp gate, the parity corpus, direction/sttype weights); reconstructed-from-stitches artwork inflated parity by 11.3 points (memory/real-artwork-parity.md).
- An auto-traced outline has ~1 node/1.3 mm, so a single-vertex drag adds area no fill row can occupy — reads as "fill is broken" (COOKBOOK.md § Hard-won lessons).
- `digitizer/` cites docs relative to the package root, so a repo-root dangling-link scan reports false missing files (COOKBOOK.md § Hard-won lessons).
- Do NOT move binary files through the Google Drive connector: base64 re-emission corrupted a 7,213-byte PNG by one bit at the correct byte count, and truncated a larger file by 92%, with no error anywhere. Binary goes through git via the inbox (`pull-corpus` SKILL.md § Size ceiling).
- Gitignored is not disposable: `scratch_corpus/`, `scratch_ink/`, `scratch_kent/`, `scratch_packs/` (COOKBOOK.md § The Python digitizer).
- Missing optional deps degrade silently-but-documented, not loudly: no `tesseract-ocr` → OCR gate fails open; no `rembg_isolated/venv` → `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`; no SAM2 venv/checkpoint → `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` (digitizer/README.md; rembg_isolated/README.md; sam2_isolated/README.md).
- SAM2 job mode refuses to download the checkpoint (90 s timeout < 156 s cold start), so skipping the `--prewarm` step means every real job silently falls back (sam2_isolated/README.md § The checkpoint).
- `pip install sam2` installs an unrelated PyPI project; Meta's is GitHub-only (sam2_isolated/README.md).
- Vite auto-increments off 5173 and `start-emb-bot.ps1` still opens 5173; `copy-engine.mjs` hard-throws on a missing engine file in `predev` so Vite never boots; bare `localhost:5173` gets HTTPS-upgraded by Chrome/Edge; `Test-NetConnection` with no args silently checks the internet instead (`run-emb-bot` SKILL.md § confirmed failure modes).
- Svelte legacy-mode template calls closing over a prop don't re-run when its contents change — UI goes stale silently (memory/emb-bot-digitizer.md).
- Preview-pane storage is ephemeral across pane restarts and looks exactly like a persistence bug (memory/emb-bot-digitizer.md).
- Dead agents leave uncommitted work in their worktree; harvest `journal.jsonl` (memory/emb-bot-digitizer.md).

## Automation that already exists

Hooks — all `PreToolUse` on `Bash|PowerShell`, from `.claude/settings.json`:
- `block-powershell-replace.js` — DENIES any command combining `-replace` with `Set-Content`/`Out-File`/`Add-Content`.
- `block-worktree-mutation.js` — DENIES `rm`/`rmdir`/`del`/`mv`/`Remove-Item`/`Move-Item` targeting `.claude/worktrees/`.
- `warn-git-add-a.js` — warns (does not block) on `git add -A`/`--all`/`.`, printing `git status --short`.
- `nudge-cookbook-stale.js` — on `git commit`, informational nudge once 20+ commits to `src/`, `digitizer/`, `app/src` have landed since COOKBOOK.md last changed.
- Hooks do NOT auto-apply inside nested worktrees — copy `.claude/settings.json` into `.claude/worktrees/<name>/.claude/` (CLAUDE.md §4).

Agents (`.claude/agents/`, all Read/Grep/Glob/Bash, none auto-fire):
- `digitizing-quality-auditor` — whole-area health check of image→stitches, picks the highest-leverage next digitizing work item; used before choosing digitizing work.
- `stitch-geometry-auditor` — independently re-measures ONE claim/commit/fixture against real stitch geometry; verification only, does not implement fixes.
- `emb-bot-reviewer` — pre-merge review against the 5 CLAUDE.md footguns plus repo conventions (engine-list sync, font licensing, trim lever, MASTER_SCOPE currency).

Skills (`.claude/skills/`):
- `add-font` — license check → `build-font.mjs` → `qc-font.mjs` gate → stop and report to Kent → after approval `_tiers.json`, `build-embf.mjs`, `build-previews.mjs`, `node --test`.
- `run-emb-bot` — decides "Kent's browser vs sandbox" first, then Windows paste blocks / `tools/start-emb-bot.ps1`, e2e + Playwright MCP, `node --test`, digitizer service.
- `pull-corpus` — routing assets in: git via `digitizer/testdata/inbox/` + `tools/sync-assets.ps1` is the channel; Drive is text-only; then file the asset and register it in `corpus_scorecard.py`'s hardcoded `FIXTURES`.
- `update-master-scope` — refreshes `MASTER_SCOPE.md` proactively after PR-sized work or on demand; enforces the in-force/was-true split, the `(verb date — source)` pointer and the 800-line budget.
- Plugins enabled repo-wide: superpowers, caveman, mattpocock-skills, hookify, claude-code-setup, claude-md-management (`.claude/settings.json`).

## Decisions recorded only in memory

- Standing directive since 2026-07-30: **full autonomy, no questions** on digitizer build work (memory/emb-bot-digitizer.md).
- The DT-first classifier swap was tried and **measured negative** — "don't rebuild it from that same recommendation" (memory/emb-bot-digitizer.md § Decisions; `docs/dt-first-verdict-2026-08-11.md`).
- IP clearance reasoning for building an auto-digitizer from scratch: Goldman/SoftSight patent chain expired ~2018, Wilcom's granted patents don't cover this approach (memory/emb-bot-digitizer.md).
- Corpus measurement outranks vendor documentation — the corpus corrected Wilcom's published complementary fill-spacing profile (memory/emb-bot-digitizer.md).
- Chaining stays off (`chain_links=False`) because its validating coverage check was built from the same polygons the router already trusted; re-enabling needs a thread-derived check plus a measured `LINK_COVER_TOL_MM` (memory/emb-bot-digitizer.md § Open).
- No width floor under satin: 19/162 corpus regions sew sub-mm satin; a `2·p90 < ~1.0 mm → run` reroute is proposed, not built (memory/emb-bot-digitizer.md).
- Contour fill stays off after a 2026-08-02 adversarial review found three coverage-measurement gaps, none revisited (memory/emb-bot-digitizer.md).
- Real-photo stage-0 misclassification (photo read as `gradient` at confidence 1.0) is **parked by Kent — don't reopen unprompted** (memory/emb-bot-digitizer.md).
- Kent tabled gradient work 2026-08-16 in favour of non-gradient artwork first; getting more real customer artwork is the highest-leverage non-code action (memory/real-artwork-parity.md).
- The parity metric's own ceiling: a pro scores 75-84 against a pro, so the 95 target is above the ceiling and `direction` measures a choice, not a standard; baseline 42.5 (memory/real-artwork-parity.md).
- Law 19 settled: pro density is quoted between same-direction rows, so tatami sews half pro coverage; satin is correct; do NOT change `FILL_ROW_MM` on analysis (memory/fill-density-convention.md).
- Pro trim behaviour: pro floats up to 16.1 mm uncut vs our `trim_at_mm` 3.0, but the cut/float distributions overlap so distance is not the decision variable — coverage is; the float set is censored below 7.5 mm (memory/pro-trim-threshold.md).
- DST axis now has 5 independent sources plus a bonus defect: `src/dst.js` writes colour change as `0x43` not `0xC3`, so standard readers see ZERO colour changes in every EMB-Bot DST. A 30-second Tajima panel check would confirm on hardware (memory/dst-codec-axis-discrepancy.md).
- `pystitch` (Ink/Stitch's MIT pyembroidery fork) as swap candidate and 5th axis source; Ink/Stitch gaps EMB-Bot lacks: meander/stipple, tartan, ripple, circular fill, e/s-stitch satin — clean-room only, GPL-3.0 (memory/inkstitch-research.md).
- Ember teardowns: no ML in their auto-digitize (fill angle is `90 * (height >= width)`), their client-side codec is a debuggable second DST reference, fill-pattern library + "Ember Bridge" Wi-Fi push are the biggest gaps; EMB-Bot leads on fonts and CIEDE2000 (memory/ember-architecture.md, memory/ember-feature-teardown.md).
- Origin has been 326 commits ahead of a local checkout once; always `git fetch` and read `origin/main` before trusting a baseline. Copilot worktrees live outside the repo at `C:\Users\EE-LT-11030\copilot-worktrees\EMB-Bot\*` (memory/emb-bot-digitizer.md).
- Domain framing: Kent = Fritsch's Stitches, embroidery; the `kent@sdwheel.com` address is an account setting, not business context (memory/fritschs-stitches.md).

## Contradictions

- **COOKBOOK.md § What's next (items 2 and 4) still queues the DT-first migration — M0's corpus leg and "the classifier swap itself, the change a customer can see" — while `docs/dt-first-verdict-2026-08-11.md`, memory/emb-bot-digitizer.md and `digitizing-quality-auditor` all record the swap as measured negative and "don't re-propose it without new evidence."** An agent following COOKBOOK's queue rebuilds a withdrawn architecture. Same class as the 2026-08-11 `bundle.mjs` finding, and the most expensive live one.
- **`.claude/skills/run-emb-bot/SKILL.md` § Standalone bundle: "Test the plain `EMB-Bot.html` + `src/` combo, or the Studio, instead."** `EMB-Bot.html` and `src/app.js` were deleted 2026-08-08, commit `cd9dfcb` (COOKBOOK.md § Running things). Directs an agent at a file that does not exist — the exact `bundle.mjs` pattern, still live in a skill.
- **COOKBOOK.md § Binary font library: `src/fonts/satin-fonts.js` is "still used by legacy `EMB-Bot.html` — do not delete it"**, and § Binary font library again calls `EMB-Bot.html` "a separate, fourth list" to keep. COOKBOOK.md § Running things says `EMB-Bot.html` is deleted. The stated reason for keeping `satin-fonts.js` no longer exists — same doc, two truths.
- **Repo visibility — RESOLVED 2026-08-16/17, the repo is PUBLIC.** This entry recorded a genuine contradiction: CLAUDE.md said "This repo is private … keep it that way" while `pull-corpus` SKILL.md and `digitizer/testdata/inbox/README.md` said "`KS-Three/EMB-Bot` is a PUBLIC repository (verified 2026-08-14 via the GitHub API — `visibility: public`)" and routed client/third-party art into it. The skills were right; CLAUDE.md was wrong and has been corrected — the repo has been public since creation on 2026-07-22, deliberately, because private repos would cost GitHub Actions credits. **So treat everything here as world-readable.** CLAUDE.md now names what is already exposed and requires asking Kent before adding new client artwork, customer names, third-party stitch files, credentials or legal correspondence. *(resolved 2026-08-17 — `CLAUDE.md` ¶1)*
- **`digitizing-quality-auditor`'s open-defect list says chaining "was fixed 2026-08-03 — don't re-flag it as open"; memory/emb-bot-digitizer.md and `stitch-geometry-auditor` record chaining as shipped OFF (`chain_links=False`) with its validation refuted.** Also on that same list: gradient fragmentation and `BACKGROUND_ENCLOSED` are presented as open, both fixed per COOKBOOK.md § Known bugs (the list carries a re-verify caveat, but reads as current).
- **`app/README.md` claims "21 satin fonts" and that `dist/` depends on "the CDN libs the image/PDF paths use."** COOKBOOK.md § Running things says the Studio has no CDN runtime dependencies (jsPDF npm-bundled, Inter via fontsource) and ships 55 fonts.
- **`add-font` SKILL.md § Compliance note: "the existing 69-font library isn't fully compliant yet (missing full license text on disk for 48 fonts)."** COOKBOOK.md § Stage B additions records that gap closed 2026-08-04 with per-font sidecars and guard tests, at 55 fonts.
- **`digitizer/README.md` § Status: "build steps 1, 3, 4 and 8 of 11" and "SAM 2 segmentation (step 2) was deferred"** — the same file then documents SAM2 shipped behind `cfg.photo_segment_sam2` with a live-acceptance doc; § Run states "127 tests, all offline"; the setup block installs `.[dev]` while the service needs `.[service,dev]`. The tesseract prerequisite paragraph also appears twice with different framings (quality gate vs "Convert to text").
- **Python version: COOKBOOK.md says "Python 3.14 venv"; `run-emb-bot` SKILL.md pastes `py -3.12`; `rembg_isolated/README.md` says `python3.12 -m venv`; `sam2_isolated/README.md` says `python3.14`; `digitizer/pyproject.toml` requires `>=3.12`.** No single stated interpreter.
- **`emb-bot-reviewer` § Repo-specific conventions calls `tools/bundle.mjs` "dead code"; it was deleted 2026-08-11** (COOKBOOK.md § Running things). Harmless in effect, but it is the residue of the same audit finding.
- **e2e prerequisites: `run-emb-bot` says the suite "starts its own dev server on port 5183… so it needs nothing running first" (7 specs); COOKBOOK.md says the e2e specs "need a real browser and a live digitizer service" (9 service-backed specs).** An agent trusting the skill will read service-absence failures as test rot.

## Sequence claims

- Read `COOKBOOK.md` before touching code; `PRODUCT.md` before a scope call; `MASTER_SCOPE.md` for status; memory for history (CLAUDE.md).
- brainstorm → spec → plan → build in worktree → review, then merge (COOKBOOK.md § Working conventions).
- `digitizing-quality-auditor` orients in a fixed order: MASTER_SCOPE area 1 → COOKBOOK (digitizer, lessons, known bugs) → digitizer/README.md.
- COOKBOOK.md § What's next: close the two gradient/enclosed regressions first, then M0+M1 of DT-first, and explicitly do **not** jump to photo steps 5+; M2/M3 cannot be judged before M0's corpus disagreement table, which is blocked on Kent running `shape_lens.py corpus scratch_corpus/` locally. (See Contradictions — the DT half of this sequence is withdrawn elsewhere.)
- Sew-out gates almost everything physical: DST axis fix, `FILL_ROW_MM` halving vs interleaving (block 2 of `docs/sewout-card-2026-07-31.md`), `trim_at_mm`, satin curve density, chaining re-enable, fabric-preset confidence. No sew-out has ever been done and scheduling one is Kent's call — don't push (memory/emb-bot-digitizer.md; memory/fill-density-convention.md; digitizer/README.md § Open questions).
- `ember-feature-teardown` ruling: fix the DST-axis and fill-density defects **before** closing the fill-pattern gap — a broken default export undermines parity work.
- Pipeline order is load-bearing: classify → prep → segment (quantize | photo-segment | SAM2) → absorb/holes → vectorize → plan (5-7) → export; `run_stages` (expensive) precedes `plan_stitches` (cheap, re-run per tweak) (COOKBOOK.md § The Python digitizer; digitizer/README.md).
- Sew order is settled BEFORE geometry exists: largest-area-first, each region underlapped beneath what sews after it and forbidden from growing back; stage 7 orders on needle-to-polygon distance because generating first and ordering after started every shape at its own top-left (digitizer/README.md § Stitch planning).
- Font intake: check the license **before** import work → `build-font.mjs` → `qc-font.mjs` → stop and report → Kent approves → `_tiers.json` → `build-embf.mjs` → `build-previews.mjs` → `node --test` (`add-font` SKILL.md).
- SAM2 build: venv → CPU-torch → SAM2 from GitHub → `requirements.txt` → **required** `--prewarm` before any real job → optional warm-cache job-mode smoke test, whose duration (not the cold one) informs the timeout (sam2_isolated/README.md).
- Asset intake: decide the channel first (git vs Drive vs ask) → `sync-assets.ps1` → file out of the inbox → append to `corpus_scorecard.py`'s `FIXTURES` → `diff` before any baseline `capture`; never auto-commit a pull (`pull-corpus` SKILL.md; testdata/inbox/README.md).
- `update-master-scope`: classify each claim in-force vs was-true **before** writing it; the 800-line budget check runs **last**, and compaction moves content, never deletes (`update-master-scope` SKILL.md).
- Run the FULL suite after merging parallel lanes; per-lane green says nothing about interaction. And run `npx playwright test` from `app/` after touching `ContentStep`/`ManualPanel` tiles (COOKBOOK.md § Hard-won lessons).
- Studio startup order: `predev`/`prebuild` runs `copy-engine.mjs` before Vite boots — a missing engine file stops the server (`run-emb-bot` SKILL.md; app/README.md).
- Quality triage order: check the input art's flatness **first**, before touching engine code (COOKBOOK.md § The one rule; `digitizing-quality-auditor`).
