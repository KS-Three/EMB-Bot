# Opus team architecture: pro parity, fine lettering first (2026-10-23)

Written by the foreman session of 2026-10-22/23 for the next team, before its own
usage ran out. Everything here is either measured in a merged PR or ruled by Kent
with the date. A fresh Opus director can run from this file alone.

## 0. The goal, in Kent's words

"This tool needs to be a start to finish plug and play digitizer." Standing
priority: "I continuously state fine lettering needs to be improved." The measure
of done is the professional digitizer's stitch file for the same job: flat art in,
pro out.

## 1. The method that worked this week (keep it)

1. **Pair every job with the pro's DST** (repo-root `Embroidery Files.zip`; art in
   `digitizer/testdata/reference/`; Kent's extra client files in `scratch_kent/`,
   gitignored). Read the DST with pystitch. Never a PES for trims.
2. **One reader on both files.** Measure ours and his with the same script, each in
   its own frame (letters by colour block / connected pieces; never a fixed box
   mapped from the art: that misled twice on 10-20/21).
3. **State the pro's rule in one sentence with thresholds**, name the rows that
   contradict it, then build it as a config flag, default OFF.
4. **Prove it as a picture and a number**: `tools/pro_pair.py` (art | ours | pro,
   one scale), OFF | ON | pro crops where the stitches change, the flag's own
   number for OFF / ON / pro. `tools/flip_sheet_renders.py` (PR #1047) makes the
   one-page sheet Kent flips from.
5. **Kent flips by the numbers.** Ruling 2026-10-22: "stitch layout and photo
   conversion quality we can preview ourselves; pull weight and comp need fabric."
   Layout (where stitches go) flips from renders and counts; pull, satin density,
   fill row spacing, stitch length-as-density need a sew-out. Ruling 10-23: when
   the eye cannot tell OFF from ON at viewing size, the number against the pro
   decides.
6. **Build OFF, flip in a separate PR** that re-pins goldens with a ledger (each
   moved pin names the flag). PR #1049 is the template.

## 2. Where it stands (as of 2026-10-23 evening; check `gh pr list`)

Merged this week: #1024/#1029 small text re-set to ~4 mm; #1025/#1046 Column lane
small-bold construction; #1030 trim bury; #1031 sew enclosed white; #1033 cross
underlay; #1040 compact solids satin; #1043 border census; #1045 pull-by-stroke
(OFF, fabric); #1047 flip sheet; #1050 border by size; #1051 5-10 mm band +
alpha-hole counters; #1052 10 mm+ band; #1053 white census.

Open, armed, merging in order: #1049 (flip nine layout flags ON), #1035 + #1048
(`cut_every_jump` with walk-on-the-work; ON lands 187 -> 44 trims on Fremont, pro
20), #1036 fill turn slant, #1039 pro-measured values (fabric, OFF), #1042
`tie_in_off`, #1044 short-column underlay, #1054 corner folds (OFF, ON-eligible),
flip-two (border_by_size + enclosed_alpha_hole_parts ON).

Held OFF by Kent: `cut_every_jump` until #1048's walk lands; `sew_enclosed_white`
until the MFab keyline band construction is fixed (#1053: selection already the
pro's, 32/34; overshoot is 5,785 stitches under 1 mm vs his 468).

Waiting for fabric (gate 1, a sew-out card is the only unblock): `pull_comp_by_stroke`
(#1045), `pro_measured_values` (fill 3.49 fixed + stagger, satin 0.37 hat / 0.35
beanie, bean 0.95; #1039), underlay stitch 2.5-3.5 vs his 4.0, cross-underlay row
spacing 1.0 vs his 0.75.

## 3. Findings that change what to build next

- **Corners**: the pro folds one column round a lone concave corner and cuts only
  where two concave corners face (T junction, slab root). Built #1054. Not built:
  his progressive inside stagger (inner ends spread 0.6-0.7 mm).
- **Borders**: not a stroke threshold. His bordered letters carry an OUTLINE in the
  art and the border is that outline widened to 2.0-2.5 mm (#1052). MARINE and
  MFAB have the same stroke; he satins one, borders the other. `border_by_size`
  (#1050) happens not to touch Becker/MFab letters, but its RULE is wrong; replace
  with "outline in art -> border at the pro's width" (pro width by band from the
  census).
- **Big letters**: the pro's MARINE is the MORE cut construction (163 columns to
  our 77, #1052). Investigate before copying: what his cuts buy (stitch direction
  per stroke) and whether our fewer, longer columns sew worse.
- **Whites**: the pro sews every enclosed body, band and field we do; the gap is
  the keyline band's construction (#1053).
- **Jumps**: 150 of Fremont's 171 uncut jumps are letter-to-letter on the field;
  the pro sews straight through 130 of them with no needle-up (#1048).
- **Ties**: we already locked only after cuts; he locks at no start (#1042).
- **Pull**: he ADDS ~0.58 mm on 0.6-1 mm strokes, ~0.4 at 2-3, negative above 4
  (#1045). Our fixed 0.4 is 0.2 over him on thin strokes, not double.
- **Tier**: MFab hat and Becker beanie silhouettes are split satin in ours; the
  pro fills them (cross-underlay lane, 10-21). A tier decision, not a flag value.
- **Segmentation**: MFab's W of WELDING never reaches the Column lane (a
  segmentation tangle, #1052/#1054).

## 4. The team

CI is the ceiling (each PR ~9 jobs, digitizer sharded 6 ways, ~25 min). Keep
about 8 workers active; drain then refill. Models: Opus for engine/digitizer
changes, census-and-build jobs, CI design; Sonnet for flips, docs, stewards.

**Director** (one session, writes no code): picks work from §5, writes briefs
from the template in §7, keeps the PR queue armed and conflict-free, puts Kent's
decisions to him with `AskUserQuestion` (what delivers, what it costs, the catch),
deletes a session the moment its PR is armed (Kent's rule), and never proposes
GitHub payment of any kind (Kent's rule).

**Manager A, lettering + digitizer engine** (Opus): owns §5 L-items; one writer
per file at a time (`outline_cut.py`, `columns.py`, `stage7_sequence.py` are the
hot files; stagger a second writer until the first PR lands or brief it to merge
the sibling branch and resolve).

**Manager B, instruments + flips + infra** (Sonnet is enough): owns §5 I-items,
every flip PR, the flip sheet refresh after each wave, the memory-index fix, lane
cleanup after each landing, re-merging conflicted PRs whose owner session is gone.

**Workers**: fresh session per task, own worktree, own branch, one PR, deleted
after. A worker that finds its brief's premise false (it happened three times
this week: `tie_only_at_cuts`, "bare fills", `trim_bury_under_later` is ON)
messages the director with the measurement and the replacement; the director
answers on his own authority when it is the same task, asks Kent when it is not.

## 5. Work queue, ranked (each line is one worker)

Lettering (Manager A):
- L1 **Flip corner folds** (`lettering_columns_corner_fold`) by #1054's numbers,
  with ledger. Sonnet. After #1054 and #1049 land.
- L2 **Inside stagger at folds**: the pro's progressive 0.6-0.7 mm spread of the
  inner cross ends, replacing `_short_stitch_guard`'s alternate pull-back at
  corners and S curls. Layout. Files `outline_cut.py`, `columns.py`.
- L3 **Keyline band construction** (unblocks `sew_enclosed_white` and the BECKER /
  MFAB faces): why our white band spends 5,785 stitches under 1 mm where the pro
  spends 468; build his band as a satin keyline at 2.0-2.5 mm with the fill
  under it. Files `stage6_border.py`, `stage7_sequence.py`, whatever
  `sew_enclosed_white` routes through.
- L4 **Border = widened art outline**: replace `border_by_size`'s threshold with
  "shape carries an outline in the art -> satin border at the pro's width by
  band"; keep the flag name or add `border_from_outline`; OFF | ON | pro on
  Becker, MFab, Bridge, Gaulke.
- L5 **MFab W segmentation**: why WELDING's W never reaches the Column lane; fix
  in stage 2-4 with the OFF pins listed.
- L6 **Big-letter construction study**: the pro's MARINE at 163 columns vs our
  77: measure stitch direction per stroke, column length, what his cuts buy;
  decide copy / don't with evidence. Investigation first, build only if the
  measurement says so.
- L7 **Script and italic lettering** (Tires 3D script 4.3-4.6 mm at 0.14 pitch,
  Bridge 11 mm script): census against the pro, same method, top gap built.
- L8 **Below 4 mm**: the pro's floor for text he still sews (ProSeal beanie
  mark, EST 1895 before re-set); where does he refuse / re-set / drop.
- L9 **Fill tier for silhouettes**: MFab hat and Becker beanie, pro fills, we
  satin; the tier rule with thresholds, built OFF, OFF | ON | pro.
- L10 **Sequence like the pro**: block order and travel; 150 letter-to-letter
  moves he sews through (#1048 built the walk; what remains is order).

Instruments and infra (Manager B):
- I1 **Memory index ceiling** (do first; it cost ~15 conflict resolutions in one
  evening). `.claude/memory/MEMORY.md` is at its 24,986-char ceiling, so every PR
  that adds a note conflicts with every other. Move entries older than
  2026-09-15 to `.claude/memory/MEMORY-archive.md` (one index line points at
  it), keep `tests/test_memory_budget.py` on the live index, and update the
  CLAUDE.md sentence about the index. Kent's OK needed for the archive split
  (it changes what a fresh session loads).
- I2 **Flip sheet refresh** after each wave: `tools/flip_sheet_renders.py` with
  the new flags, one standalone HTML with images inlined (the app's viewer
  cannot resolve relative image paths; `tools/` should emit the inlined file).
- I3 **Legibility instrument**: OCR (tesseract exists in CI, not on Kent's box)
  over ours vs pro per word at 4 / 7 / 12 mm, reported chance-corrected (gate 4),
  so a lettering PR carries a legibility number beside its render.
- I4 **Lane hygiene tool**: `tools/lane_cleanup.sh` (written 10-23 in the
  sewout-card-v4 lane, not committed): REMOVE a clean lane whose HEAD is on
  origin and idle 2 h, KEEP the rest; Kent runs it (lane removal stays his).
  Commit it under `tools/`.
- I5 **Sew-out card for the fabric flags** (build when Kent names a date, the
  day before): one 92.5 mm card beside his Fremont patch, arms: today's defaults;
  `pull_comp_by_stroke` ON; `pro_measured_values` ON; both ON; plus the
  short-column underlay pitch. `tools/sewout_card_v6.py` is the latest pattern;
  pin the OFF arms explicitly (the card tools pin None, memory `bean-holds-on`).
- I6 **Pro-pair readers consolidated**: `pro_pair`, `letter_band`,
  `column_ends`, `fan_census`, `trim_classes`, `fill_turns`,
  `pro_fill_underlay`, `pro_satin_underlay`, `border_census`,
  `pro_corner_folds`, `small_text_columns`, `column_harness` into one documented
  `tools/pro/` package with a README of what each number means and its known
  misreads (satin crosses read as fill rows; fixed-box letter heights).

## 6. Kent's decisions outstanding (put each with AskUserQuestion, one at a time)

1. Flip `lettering_columns_corner_fold` (L1) when #1054 is green.
2. Approve the memory-index archive split (I1).
3. A sew-out date for the fabric flags (I5). Nothing else needs fabric.
4. Tier rule for silhouettes (L9) once measured: fill like the pro or keep satin.
5. Whether to copy the pro's more-cut MARINE construction (L6) once measured.

## 7. Brief template (every worker gets this verbatim, then the task)

EMB-Bot is Kent's embroidery auto-digitizer (Python `digitizer/digitizer_core/`,
browser twin `src/`). Judge against the pro's DST for the same job
(`Embroidery Files.zip`, pystitch), one reader on both files, each in its own
frame. Kent's ruling 2026-10-22: layout flags flip from renders and numbers; only
pull / density / stitch-length-as-density need a sew-out and stay OFF. Read
`CLAUDE.md`, `ROADMAP.md` gates, `DOCTRINE.md`, and the memory notes named in the
task. Do not edit MASTER_SCOPE.md, DOCTRINE.md, CLAUDE.md or COOKBOOK.md; status
goes in the PR body. Never run the full digitizer suite locally unless the task is
a flip (then once, background, log with exit code; the three known golden reds
are expected). Worktrees have no `.venv`: run
`C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe`
with cwd in your worktree's `digitizer/`. Always `python -m pytest`, never pipe
pytest to tail. Ready-for-review PR, `git fetch origin main && git merge
origin/main` before every push (never rebase), arm auto-merge while checks are
pending, never merge yourself. MEMORY.md conflicts on every merge until I1 lands:
take main's hooks, re-add only your own line, shorten an old hook, and for a CODE
conflict keep both sides' intent per hunk; never take one side's whole file (that
wiped a branch's code once this week). Kent pays nothing for GitHub; never suggest
billing. If your brief's premise measures false, message the foreman with the
measurement and the replacement, do not build the false premise. Memory note +
one index line per PR. Delete nothing under `.claude/worktrees/`.

## 8. Traps this week, so the next team skips them

- Taking one side's whole file in a conflict (restored by three-way
  `git merge-file` in a follow-up commit; force-push is denied to sessions).
- The app's "finished a turn" note is not "done": a session that backgrounds a
  render ends its turn and resumes on the notification. Read the note.
- `delete_session` refuses a session with a live background task; retry later.
- `bash` in Kent's PowerShell is WSL and times out; Run buttons must use
  `& "C:\Program Files\Git\bin\bash.exe" <script>`; `start ""` is cmd, not
  PowerShell (`Invoke-Item` opens a file).
- A session started on a turn that an automated event began cannot start
  sessions; it proposes cards and Kent clicks.
- Disk: 0.35 GB free killed three census jobs on 10-23. Scratch worktrees under
  `%TEMP%\embwt` were 4.4 GB; 29 clean lanes were 11.7 GB. Clean after each wave.
- "Finished" sessions still hold Remote Control links the app counts as live
  work; Kent closes those from the sidebar.
