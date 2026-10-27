# Director handoff (2026-10-27)

Written by the director session of 2026-10-26/27 when Kent closed the team: "Let's
wrap your workers up and close out this session." It updates §2, §5 and §6 of
[`2026-10-23-opus-team-architecture.md`](2026-10-23-opus-team-architecture.md);
the method (§1), brief template (§7) and traps (§8) there still hold. Every number
here comes from a merged PR or one that was open at close, named beside it.

## 1. Where it stands

**Live numbers:** `docs/pro-baseline-2026-10-27.md` (#1141: main against the pro on
all 22 paired jobs) and `docs/scoreboards/lettering-board-2026-10-27.md` (#1152).
Every OFF flag with its kind (layout / fabric / held), PR and flip-sheet row:
`python -m tools.flag_ledger` from `digitizer/`.

**Worst gaps on #1141's baseline (ours / pro):**

- **Trims:** Drone 92 / 59 (the largest absolute gap), To a T 58 / 31, Fremont patch 40 / 21,
  Bridge LC 32 / 20, Golden Tee 26 / 10, Becker hat large 24 / 10.
- **Stitches:** Golden Tee +95%, Bridge LC +79%, To a T +69%.
- **Golden Tee is recorded, not built** (Kent: "Record it, no build (Recommended)").
  39% of its gap is two layers the pro never sews (#1147).

**Open at close.** Each was finishing under the director's wrap-up order; check
`gh pr list` for where each landed.

| PR | What | State at close |
|---|---|---|
| #1143 | White recipe as plain defaults on every job (Kent: "Every job (Recommended)") | Draft. Becker counter fix in; post-fix 22-job re-proof running; MFab byte-identical check pending |
| #1151 | `text_cluster_nest_guard` (OFF): Bridge hat's wheel no longer nests away its letters | Draft. Bridge hat text pieces in the lane 0 -> 7 of 15, LC byte-identical; reach census and ProSeal read running |
| #1153 | `lettering_columns_slot_guard` (OFF): 3 of 8 in-letter cuts go | Unarmed. ON stage-7 CPU cost being measured, then re-armed |

## 2. Kent's rulings this run (verbatim, 2026-10-26/27)

| Topic | Ruling | Where it landed |
|---|---|---|
| CPU | "2 lock slots + 3 workers (Recommended)"; "Pause your 3 new teams' heavy runs until CPU busy is under 85%." | §5 below |
| Questions | "qestions from your workers should roll up to you for me to answer." | #1129, CLAUDE.md |
| Pro renders | "Stop new ones, keep old (Recommended)" | #1145 guard test |
| TM mark | "Name the cause, no build (Recommended)" | #1137 |
| Golden Tee | "Record it, no build (Recommended)" | #1147 |
| Script strokes | "Flip now, fix Bridge next (Recommended)" | #1136 ON; #1150 width (OFF) |
| Bridge script width | "Build it OFF (Recommended)" | #1150 |
| Left chest box | "Measure an area rule first (Recommended)" | #1148 (96 wide, 76.5 tall, 5,800 mm²) |
| White recipe | "Every job (Recommended)" | #1143 |
| Layer pin | "Yes, pinned shape leads (Recommended)" | not built: queue item 1 |

## 3. Kent's flip queue (built OFF, waiting on his flip)

All of these are layout flags, judged from renders and counts against the pro, with
no sew-out needed (Kent 10-22).

- `lettering_columns_apex_cut` + the apex walk (#1139): tip-satin travel 3.96 → 0 mm.
  Per-job travel rises on 5 jobs, which is the open trade.
- `fill_section_travel`: held.
- `script_strokes_drawn_width` (#1150).
- `text_cluster_nest_guard` (#1151), once merged.
- `lettering_columns_slot_guard` (#1153). **Not recommended:** −3 trims of 261. The
  other 5 in-letter cuts need a construction change, not a merge rule.

**Fabric (gate 1; a sew-out card is the only unblock).** No sew-out date is set.
- `pull_comp_by_stroke` and `pro_measured_values`.
- `fill_turn_slant`, held until the card's OFF/ON swatch.
- Two candidate rows for the next card, from Golden Tee: fill stitch length (ours 1.97 mm,
  his 3.45 mm) and the crescent underlay.

## 4. Work queue, ranked (each line is one worker; none started)

1. **Layer pin**, after #1143 merges. Kent: "Yes, pinned shape leads (Recommended)".
   A Studio layer override's pinned shape leads its layer: an ordering rule in
   stage 7 that acts only under an override. Today "pin to layer 0 opens the
   design" fails for a shape that joins a mixed layer (#1143's D3 tests and body).
2. **Drone between-piece trims**, 104 vs the pro's 59. That is #1153's count on
   main 8341d1f7; #1141's baseline read 92. In-piece cuts are already equal
   (20 / 20), so the whole gap is between pieces.
   - Measure on recipe-ON main.
   - Classify every between-piece trim, ours against his: colour-block count and order, colour revisits,
     shape-to-shape hops inside a block (buryable or not), and travel exposure.
   - Memory `buried-walk-2026-10-26` says his metre is layering plus colour revisits.
   - State his rule with its contradicting rows, and report before building. Gate 3: chaining stays as it is.
3. **Band corner tip to a point**: #1143's named follow-up. The pro runs the
   outline satin out to a point; ours ends blunt (+1.1 mm² on Becker hat small).
4. **Re-measure satin-split class A after #1143.** These are 16 keyline-band
   loop-to-loop lifts. The recipe carries `keyline_loop_chain`, so Becker's band lifts may already fall.
   Doc: `docs/satin-split-cuts-2026-10-27.md` (#1153).
5. **The 5 in-letter cuts #1153 can't remove.** They need a construction change: end each satin where the
   next one starts, under satin still to come, as the pro does.
6. **Rotation-aware letter aspect for arc text.** Bridge's 55 mm wheel text; the
   nest guard (#1151) is the first half.

## 5. CPU regime (the limiting factor on this laptop)

The laptop is an 8-core Ryzen 4700U. Under load it throttles to 70% clock, so
`% Processor Utility` caps at 70 while the CPU is saturated. Read busy time
(100 − `% Idle Time`) instead. Kernel time runs 20–35%, and it can't be attributed
without admin rights.

**Two shared slots:** `%TEMP%\embwt\cpu.lock` and `cpu.lock2`. A heavy run takes one
first, and a heavy run means:
- a digitize;
- a census over several jobs;
- a flip-sheet batch;
- a pytest run over 5 minutes.

**Taking a slot:** `mkdir` the slot plus a `holder.txt`, and `rm -r` it the moment the run ends.

**Turns:**
- About 20 minutes per take, one job per take.
- Poll no more often than every 30 s, and wait 90 s after releasing before trying again.
- Never two MFab jobs at once.
- pytest `-n 2` at most.

**`tools/cpu_status_monitor.ps1`** writes `%TEMP%\embwt\cpu_status.txt`:
- line 2 holds `STATE=OK|BUSY|HOT`; scripts read it with an anchored match;
- slot holders, with stale flags;
- top processes;
- each root python job, tagged lock-aware or not.

Its exit codes wake a director: 3 means HOT persisted, and 4 means calm under
`-CalmPct` (pass `-CalmExitSamples N`). The other foreman's `cpu_watchdog.ps1`
(local, not committed) closes slot 2 while the 1-minute mean idle is under 15%.

**Traps:**
- TaskStop on a background waiter leaves its child bash/python running. Kill them by PID.
- A digitize launched from a lane has no `rembg_isolated` venv, so MFab hat and Tires
  silently take the classical route. Grep for `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`.
- A recursive grep on `../..` walks every lane; use `git grep`.
- Many idle `tail` Monitors cost real kernel time.

## 6. Cleanup left for Kent

The worktree guard denies sessions `git worktree remove` of a lane. These four
lanes are clean, pushed and merged (#1150, #1120, #1147, #1145), and their sessions
are archived:

```powershell
cd "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot"
git -c core.longpaths=true worktree remove .claude/worktrees/flip-sheet-inline-b6cd02
git -c core.longpaths=true worktree remove .claude/worktrees/diagonal-junction-letters-62899f
git -c core.longpaths=true worktree remove .claude/worktrees/script-italic-census-ac6aea
git -c core.longpaths=true worktree remove .claude/worktrees/tagger-fused-serifs-e5a440
git branch -d claude/golden-tee-faces claude/no-new-pro-renders
```

**`claude/white-keyline-art-flip`** is local-only. It holds a WIP commit,
"white_keyline_art_recipe ON by default", that #1115 superseded on main (the
default is `True` there). Only `git branch -D` removes it, and that's Kent's call.
