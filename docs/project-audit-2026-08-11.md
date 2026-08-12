# EMB-Bot Project Audit — 2026-08-11

> **READ THIS FIRST — most of this audit was actioned the same night.**
> Written mid-evening 2026-08-11; the work it recommended ran immediately
> after, so the body below is a snapshot of a state that no longer holds.
> Do not chase an item from it without checking here first.
>
> **Closed the same night:** pystitch swap executed (`39a7adc`); per-region
> preflight metric + count-aware scorecard diff (`619e9ad`, `2aca949`);
> the 4 untracked research docs committed (`e922f2f`) plus a 5th recovered
> from Kent's Desktop (`49d498b`); `main` pushed and the remote moved to
> KS-Three; `scratch_ink/` + a fresh bundle archived to Drive (bus factor
> closed); worktree/branch yard emptied; the 2 JS test failures fixed
> (283/283, `.gitattributes` for LF sidecars); MASTER_SCOPE splice damage
> and false test counts repaired; README (69→55 fonts, dead `EMB-Bot.html`
> narrative), PRODUCT.md and COOKBOOK corrected; `tools/bundle.mjs`
> deleted; LINK_UNCOVERED false-block + its raster overhead fixed.
>
> **Ruled by Kent 2026-08-11** (see PRODUCT.md): engine quality is a
> parallel investment, *not* a launch gate; SAM2 ships post-v1 as an
> opt-in download. Launch items 2 (hoop picker) and 4 (shapes tool)
> shipped that night — item 3 (starter design pack) and the billing
> session are what remain.
>
> **Still open exactly as written below:** the DST axis bug reaching
> customers through lettering exports (sew-out gated — still the single
> highest-value unblock); `src/fonts.js` dead CDN path still in the engine
> list; rembg's ~178 MB first-run model download; the 19-minute serial
> pytest suite (no `pytest-xdist`).
>
> Current state always lives in MASTER_SCOPE.md, not here.

Full-project spot check: progress vs anticipated outcomes, .md validation (gaps /
discrepancies), and tool/feature/code alternatives. Produced by a 4-lane audit
(MASTER_SCOPE integrity, docs-vs-code fact-check, digitizer quality lane,
tooling/risk/alternatives), with the high-severity claims independently
re-verified against the tree before writing this doc.

**Snapshot:** branch `photo-quality-and-sam2-seam-2026-08-11` @ 167ce92, with
uncommitted fix #6.3 work in the tree. A parallel session landed work *during*
the audit (fix #6.3 tests, SAM2 venv relocation, probe cleanup, MASTER_SCOPE
edit in progress) — findings marked "fixed mid-audit" where that happened.
Re-verify anything here before acting on it; this repo has multiple active lanes.

## Verdict

Engineering discipline is genuinely strong — root-cause docs, measured claims,
adversarial self-review, honest caveats. But three structural problems persist
that discipline doesn't fix:

1. A known-wrong DST codec still sits in the highest-volume export path.
2. The launch checklist has been frozen 8+ days while effort flows to
   photo-quality engine work whose own scorecard cannot measure improvement.
3. Docs rot faster than the update discipline catches — including the "live
   dashboard" whose mechanics now defeat its stated purpose.

## 1. Highest priority — product correctness

### DST axis bug reaches customers through lettering

`src/dst.js:9-25` bit table is transposed vs the Tajima standard (x in high
nibble, y in low — five independent sources agree on the opposite). The merged
export-routing fix sends only *purely-digitized* designs through the Python
`/export`; any **lettering or manual design — the core use case — silently
downloads browser-codec DST** (`app/src/ui/DownloadStep.svelte` gates on
`isPurelyDigitized`), with no user-facing indication of which encoder produced
the file. Files read a quarter-turn wrong in third-party software, and the
0x43-vs-0xC3 color-change bug means third parties see zero color changes.

Everything blocks on **one sew-out session** — the gate since 2026-07-31 and the
single highest-leverage physical action available. After it:

- Fix the JS table, with a legacy-file decode fallback (DST has no version
  field — old EMB-Bot files need a heuristic or a one-time clean break;
  Kent's call).
- Execute the **pystitch swap**: `docs/pystitch-evaluation-2026-08-11.md`
  already verified it drop-in (29/29 symbols identical, half-day, MIT,
  maintained by pyembroidery's own author; pyembroidery 1.5.1 is dormant
  upstream). Evaluation done; adoption not started.
- Meanwhile, surface encoder provenance in DownloadStep and warn on
  browser-DST bound for third-party machines.

### The quality yardstick can't see the fixes

Corroborated independently by the audit and by the parallel session: fixes #6.1
and #6.3 are algorithmically verified correct, yet **neither moves a corpus
grade** — `preflight._artwork_colors_by_thread` pools a per-thread median across
all regions sharing a spool, so drone_render reads *worse* (9.2→33.6) while the
honest per-region worst-ΔE *halves* (20.99→10.64). Making that metric
per-region is the prerequisite for any further #6.x work being measurable.
Also: the scorecard diff has a pinned count-blindness (set-based compare,
commit 76af7a6), and only 2 photo-class fixtures exist — both synthetic stubs —
so **SAM2's headline benefit is unmeasurable by the committed corpus**. Fix the
instrument before fix #6.4: per-region worst-ΔE in preflight, count-aware diff,
3–5 real photo fixtures (licensing permitting).

### Strategic drift — the unanswered question in PRODUCT.md

PRODUCT.md (lines 18-23) flags it itself: is engine quality a launch gate or a
parallel investment? Thirteen days post-pivot, ~255 commits since Aug 4 went to
engine/fills/icons/manual-editing; launch items 2 (hoop picker), 3 (starter
pack), 4 (shapes tool) have zero commits; billing still tabled. The hoop picker
is days of work against existing clamp math. This is the highest-leverage
*decision* on the table — it determines whether #6.x cycles are launch work at
all.

## 2. Data safety

- **4 untracked docs, only copies on disk:**
  `docs/ember-competitive-teardown-2026-08-09.md`,
  `docs/hatch-manual-teardown-2026-08-08.md`,
  `docs/research-handoff-2026-08-07.md`,
  `docs/superpowers/plans/2026-08-10-fix-export-routing.md`.
  One `git clean -fd` destroys three research docs. Commit them.
  (This audit doc is a fifth until committed.)
- **Local `main` 25 commits ahead of `origin/main`, unpushed** — yet BACKUPS.md
  claims "GitHub stays current — best reference copy." False right now. The
  Drive bundle is 2026-07-27, 15 days old. Push, and refresh the bundle.
- **`scratch_ink/` bus factor:** 368MB, gitignored, exists on this machine +
  Kent's Desktop only — and the entire 55-font library rebuild
  (`node tools/build-embf.mjs`) hard-depends on it. Archive off-machine and pin
  the upstream Ink/Stitch fonts commit hash in COOKBOOK.
- **Worktree/branch cruft:** `docs-refresh-batch2` worktree + both copilot
  worktrees are fully merged (prunable); `fix/bg-existence-guard` is clean but
  unmerged since 2026-08-03 — merge or kill. Five unmerged remote branches
  (`feat/svg-import-shapes`, `mode2-shape-validation-hardening`,
  `mode2-vertex-editing-shortcuts-tests`, `digitizer-manual-holes-coverage`,
  `docs-cookbook-subline-fix-verified`) need triage.
  (The `sam2-segmentation` worktree was retired mid-audit — venv now real at
  `digitizer/sam2_isolated/venv`.)

## 3. .md validation — gaps and discrepancies

### MASTER_SCOPE.md

Per-entry epistemics excellent; document mechanics failing.

- **Wrong-now claims:** the pystitch evaluation is marked "not done — concrete
  next step" in two places (~lines 2023, 4001), but the eval doc landed in
  commit 8acc232 — *older* than the scope doc's own last update (20bde4d).
  Area 1's headline Status quotes a stale README line ("preflight scoring still
  to come") while the doc's entire fix-grading program runs on that preflight.
- **Falsely-"fresh" test counts:** "347/347 (fresh run this session)" — real
  count 615/615 now; "267/267 JS" — actually 283. "This session" language must
  never survive into a persistent doc.
- **Structural rot:** 1,575 lines (35% of file) of reverse-chronological
  preamble before the At-a-glance table; 29 "Last updated" headers; **four
  mid-sentence splice corruptions** where new entries cut old sentences in half
  (~lines 122, 558, 902, 1005). The stated purpose — "answer where do we stand
  without re-deriving" — is inverted. Fix: one Last-updated block ≤50 lines,
  history to git or a CHANGELOG, repair the four splices, add an explicit
  compaction rule to "How this document works."
- Area 4 says `/export` "Implemented, both paths" while the doc's own
  cross-cutting section shows the path was product-unreachable (now merged, but
  gated to purely-digitized designs — annotate).

### README.md

- **"69-font library" — actual: 55** (post-ShareAlike pull). User-facing
  number, wrong.
- The whole legacy-page narrative is stale: `EMB-Bot.html` was **deleted
  2026-08-08** (commit cd9dfcb), yet README still documents opening it, the
  CDN requirement (opentype.js / jsPDF / Google Fonts), and the eager font
  registry. The Studio has **no CDN runtime deps** (jspdf npm-bundled, Inter
  via fontsource, fonts local .embf) — README sells a fragility that no longer
  exists.
- tools/ inventory lists ~6 of 31 actual tools.

### PRODUCT.md

- Item 1 evidence cell wrong: `export.py` is DST-only; PES/JEF live in
  `digitizer/digitizer_service/formats.py`. Substance still true.
- Item 7 **understates compliance**: 55 `.LICENSE.txt` sidecars now ship in
  `app/public/fonts/` — the "zero sidecars ship" gap is closed.
- CC-BY-SA risk section stale: zero CC-BY-SA fonts ship (all 13 pulled
  2026-08-04); the lawyer question only gates *restoring* them.
- **Parking-list contradiction:** "full freehand draw tools" parked, but manual
  draw mode shipped (`app/src/lib/manualShapes.js`, "Studio's third content
  type"). Scope doc contradicts shipped product.
- "Fast-follow: ltr/ importer (mai_en_fleur)" — already done (in manifest).

### COOKBOOK.md

- **Dangerous contradiction:** ~line 462 declares `bundle.mjs` dead; ~lines
  505/537 still instruct "run after any src/ change." An agent following
  Working conventions would regenerate a deliberately deleted 8MB artifact.
  Purge both stale directives; delete `tools/bundle.mjs` itself (doubly dead —
  its input and output are both deleted).
- Stale counts/pointers: "267/267" engine tests (283 now, 2 failing),
  "348/348" app tests (615 now), stage7 classifier line ref (moved to
  `stage6_satin.py` / `shapefield.py`), "segment, one of two stages" (three now
  with SAM2).

## 4. Code/tool alternatives

| Current | Problem | Alternative |
|---|---|---|
| pyembroidery 1.5.1 | Dormant upstream | **pystitch** (MIT, same author, evaluated drop-in) — execute the swap |
| Browser DST codec for lettering exports | Transposed axis table | Fix table post-sew-out + encoder-provenance warning in DownloadStep meanwhile |
| `src/fonts.js` in Studio engine list | Dead path — 137 CDN URLs requiring a global `opentype` nothing loads; throws if invoked | Drop from `app/src/lib/emb.js` engine list; if outline-text returns, **fontkit** (maintained, MIT) over opentype.js 1.3.4 (2020, dormant) |
| Serial 48-min pytest suite | Won't get run | **pytest-xdist**; also stash-and-rerun to attribute the 8 current failures (audit says #6.3 fallout, parallel session says pre-existing — unresolved; needs a clean-tree baseline) |
| `core.autocrlf` checkout | 35 phantom embf-guard failures on any Windows clone (CRLF sidecars vs LF embedded license text) | `.gitattributes`: `*.LICENSE.txt eol=lf` |
| embf-guard `ALLOWED_MISSING` | Real failure: `apex_lake` verified-tier but ShareAlike-pulled | Whitelist the PULLED set in `test/embf-guard.test.js:110` |
| rembg first-run model download (~178MB) | Paid local-first product with a silent network dependency | Pre-bundle `isnet-general-use` or document the first-run requirement |
| SAM2 dev seam (localStorage + hand-built ~1GB venv) | Fine today; dead end as a shipping path | Decision needed: bundled bootstrap / server-side / cut from v1 — put next to billing on the decision list |

License posture otherwise clean: no Ink/Stitch GPL code contamination (concepts
+ thread-chart data only — worth one line in the eventual lawyer consult), SAM2
Apache-2.0, FastSAM/EdgeSAM correctly avoided (AGPL / non-commercial — recorded
as unverified subagent leads, correctly).

## 5. Test-suite ground truth (fresh runs, 2026-08-11)

- JS engine `node --test`: **281/283** — 2 failures (embf-guard: apex_lake
  whitelist gap + CRLF artifact), both fixable in minutes.
- Studio vitest: **615/615 green**, 33 files, ~41s.
- Python: **1038 passed / 8 failed / 3 skipped**, 48 min serial, on the dirty
  #6.3 tree — failure attribution unresolved (see table above).

## Recommended order

1. **Sew-out session** — unblocks the DST fix, browser-vs-service trust,
   LINK_COVER_TOL_MM, and Law 19. Everything queues behind one hooping.
2. **Kent's ruling: engine quality launch gate or not** — decides whether #6.4
   or the hoop picker is next.
3. `git add` the untracked docs + push main + fix the 2 JS test failures +
   `.gitattributes` — one short session; kills all data-loss and
   false-red-suite risk.
4. pystitch swap (half-day, de-risked).
5. Yardstick fix (per-region preflight metric + count-aware diff + real photo
   fixtures) before any further #6.x.
6. Doc-rot pass: MASTER_SCOPE compaction + README/PRODUCT/COOKBOOK corrections
   listed above.
