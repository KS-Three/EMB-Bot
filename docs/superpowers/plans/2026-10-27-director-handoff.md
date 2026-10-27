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
| #1151 | `text_cluster_nest_guard` (OFF): Bridge hat's wheel no longer nests away its letters | Merged. Bridge hat text pieces in the lane 0 -> 7 of 15, LC byte-identical, reach kappa unchanged; the flip precondition is in the body |
| #1153 | Satin-split cuts inside one piece, measured (numbers only): ours 80, pro 30 | Merged. The flag's code is parked on `claude/slot-guard-candidate`, not in the PR |

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
- `text_cluster_nest_guard` (#1151), once merged. Bridge hat: text pieces in the
  Column lane 0 → 7 of 15, folds 2 → 5 (his 35). Reach kappa 0.815 is unchanged
  on all 14 pairs.
  - **Precondition before the flip:** ProSeal's round 1.7–3.5 mm bubbles get
    tagged `text_candidate` (12 on the hat, 11 on the beanie). The Studio's text
    badge and Convert-to-text would then offer them as text.
  - The sewn output is byte-identical. Build a roundness guard at the tagger's
    door first.
- **Not on main, a parked candidate:** `lettering_columns_slot_guard`, on branch
  `claude/slot-guard-candidate` (50c8bc0a).
  - It cuts 3 trims of 261 and 7.1 mm of exposed travel, and nothing rises.
  - It costs ×1.10 Column-lane CPU (×3.4 on Becker's plain letters).
  - The director didn't build it, because it's too small a gain for the CPU it
    costs. `docs/satin-split-cuts-2026-10-27.md` costs it out.

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
2. **Drone badge ground, sewn whole under its details** (lever A, build OFF).
   Measured 10-27 in `docs/drone-between-pieces-2026-10-27.md`. Trims are ours
   104, recipe arm 94, pro 59. His 59 = 37 between-piece cuts + 22 colour changes.
   - The lettering is at parity (21 cuts vs his 19); the badge is the gap
     (50 vs 18).
   - 91 of our 92 in-block cuts have no route under later thread at any length.
     So no walk or bury rule moves them, and gate 3 is not in play.
   - **His rule:** the dark ground is one early pass that walks under the later
     colours (20 walks, 0 cuts, 85% buried). Ours is knock-out and cuts 7.
   - **A:** a stage-5 overlap change, one OFF flag. Gain: at most the ground's 7
     cuts. `silhouette_underfill` does not reach this ground.
   - **B, only after A's numbers:** detail colours as local revisit passes (his
     15 revisits, 0 cuts in blocks 5-14). Gain: up to ~40 badge cuts. Catch:
     each revisit is a colour change, so net trims are unknown until built.
     Needs a stage-7 colour-order flag, not chaining.
   - Both are layout, so Kent flips from renders.
3. **Band corner tip to a point**: #1143's named follow-up. The pro runs the
   outline satin out to a point; ours ends blunt (+1.1 mm² on Becker hat small).
4. **Re-measure satin-split class A after #1143.** These are 16 keyline-band
   loop-to-loop lifts. The recipe carries `keyline_loop_chain`, so Becker's band lifts may already fall.
   Doc: `docs/satin-split-cuts-2026-10-27.md` (#1153).
5. **The in-letter cuts a merge rule can't remove** (5 of 8; the parked slot guard
   takes the other 3). They need a construction change: end each satin where the
   next one starts, under satin still to come, as the pro does.
6. **Rotation-aware letter aspect for arc text.** Bridge's 55 mm wheel text; the
   nest guard (#1151) is the first half and is necessary but not sufficient.
   Ship it in the same worker as the nest guard's flip precondition: a roundness
   guard at the tagger's door, so ProSeal's bubbles are never tagged as text.

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

The worktree guard denies sessions `git worktree remove` of a lane. These six
lanes are clean, pushed and merged (#1150, #1120, #1147, #1145, #1153, #1151), and
their sessions are archived:

```powershell
cd "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot"
git -c core.longpaths=true worktree remove .claude/worktrees/flip-sheet-inline-b6cd02
git -c core.longpaths=true worktree remove .claude/worktrees/diagonal-junction-letters-62899f
git -c core.longpaths=true worktree remove .claude/worktrees/script-italic-census-ac6aea
git -c core.longpaths=true worktree remove .claude/worktrees/tagger-fused-serifs-e5a440
git -c core.longpaths=true worktree remove .claude/worktrees/brave-williams-34ee5d
git -c core.longpaths=true worktree remove .claude/worktrees/bridge-census-d2a759
git branch -d claude/golden-tee-faces claude/no-new-pro-renders claude/satin-split-cuts-5b8621 claude/text-cluster-nest-guard
```

The border lane (`.claude/worktrees/border-from-outline-4d16f7`) gets the same
two steps once #1143 merges.

**`claude/white-keyline-art-flip`** is local-only. It holds a WIP commit,
"white_keyline_art_recipe ON by default", that #1115 superseded on main (the
default is `True` there). Only `git branch -D` removes it, and that's Kent's call.

## 7. The other foreman's handoff, and briefs ready to launch

The "Embot stitch out files" foreman closed the same day. Its handoff is
[`2026-10-27-k3-foreman-handoff.md`](2026-10-27-k3-foreman-handoff.md), copied verbatim:

- what it merged;
- the sew-out card v8 list;
- the lettering board's next queue;
- the Tires 19.95-of-28.65 mm gap;
- its decisions waiting on Kent;
- its own cleanup list.

Three briefs it wrote are ready to launch as written, in
[`2026-10-27-briefs/`](2026-10-27-briefs/):

- **W6-01:** text-heavy art at jacket-back size never finishes (> 600 s). Profile,
  then make a byte-identical speed fix.
- **W6-02:** a timed-out job keeps the one service worker busy, and the next job
  waits about 220 s. Give the worker back within seconds.
- **W6-03:** Studio tests for manual sew order with "sew white areas" ON.

`W6-house.md` holds that foreman's house rules. `director-preamble.md` holds this
director's, the standing rules prepended to every brief. They agree on slots,
the rembg route trap, frozen pins and the roll-up rule. Prepend one of them to
any brief above or in §4.

**The CPU watchdog is stopped too.** Slot 2 is no longer closed automatically, so
the rule "slot 2 only when line 2 reads OK" depends on each worker reading
`cpu_status.txt`. Start `tools/cpu_status_monitor.ps1` before launching a team.
