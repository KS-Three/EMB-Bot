# K3 foreman handoff — 2026-10-27 (Kent: "wrap your workers up and close out this session")

Foreman session local_c188b954 is closing. Everything it ran is merged; nothing is in flight.
The director (local_5b2045fa) is closing too (Kent, same day): its cpumon.ps1 stops, cpu_status.txt line 2 then reads STATE=UNKNOWN. A copy of the monitor goes into its handoff PR as tools/cpu_status_monitor.ps1. Whoever starts the next team owns everything below.

## Merged today (foreman lanes)
- #1139 apex walk (OFF) · #1140 flip sheet wave 5 · #1146 Kent's flips ON (bean_ink_outlined_letters, text_cluster_part_touching, lettering_columns_italic_lean; fill_section_travel held OFF)
- #1138 + #1149 upload full-res (OFF) + real 250 mm run · #1152 lettering board v2 (re-baseline, 8 review fixes)

## CPU slots
- Foreman watchdog (cpu_watchdog.ps1) STOPPED, cpu.lock2 released (logged in cpu_watchdog.log). Slot 2 is no longer auto-closed when the laptop saturates.
  The director's cpumon.ps1 / cpu_status.txt remains the shared view. Rule stays: slot 2 only at STATE=OK.
  To restart enforcement: `pwsh -NoProfile -File C:/Users/EE-LT-11030/AppData/Local/Temp/embwt/cpu_watchdog.ps1` (adopts or creates cpu.lock2; holder text names the foreman — edit if a new owner runs it).

## Not started — written briefs (embwt/briefs/)
- W6-01.md — text-heavy art at jacket-back size never finishes (small_text_logo 250 mm jacket_back > 600 s both arms; 277-408 s at 100 mm vs 55 s simple art). Profile + byte-identical speed fix. Opus.
- W6-02.md — a timed-out job keeps the single service worker busy (next job waited ~220 s, #1149); MAX_INFLIGHT counts dead work. Cooperative cancel or killable child process. Opus. Director confirmed none of its lanes touch digitizer_service.
- W6-03.md — Studio tests: manual sew order with "sew white areas" ON (default since #1112), incl. save/reload of pre-#1112 projects. Sonnet, vitest only.
- W6-house.md — house rules every worker gets (slots, rembg route trap, frozen pins, roll-up).
Why not started: Kent on Remote Control — the app allows session starts only on a message typed in the desktop app.

## Queues
- Sew-out card v8: cut_every_jump Python + JS cutEveryJump OFF/ON arm; 0.25 mm letter gap (#1084); bay mouth 0.51 mm; 5's bar slot; small-text bold factor (1.45 vs pro 1.7-3.0); 0.8 mm halo (Drone height); typed-text fabric preset; ENTHUSIAST tagline grow_away ON counters.
- Nitpick before card v8: measure Python cut_every_jump walk with a dense oracle (JS found 17 segments up to 0.015 mm off thread at 0.1 mm sampling).
- Lettering board v2 next queue (22 lines) is in the board md on main. Biggest: Becker BECKER trims 16/1 (hat large); Drone PRECISION / AND DRONE cc 0.00 vs 0.82/1.00; Fremont EST/1895/EAT STAY; Gaulke hat STEEL ROOFING 46/32 columns.
- Tires: ours reads 19.95 of 28.65 mm drawn (5 cols / 2,243 st vs pro 8 / 5,222). Not chased — script lane (#1150) territory.
- Older next-wave candidates: typed-text fabric preset, THERMAL rejoin, stemless house angle, re-set width < 4 mm, size-free legibility floor, flag_ledger fixes, precheck.

## Decisions waiting on Kent
- Upload full-res flip: HOLD — at 250 mm it is a clean-up on simple art (−2 halo colours, −5 trims, geometry tie); text-heavy art finishes in neither arm, so nothing to flip until W6-01 lands.
- apex_cut + walk flip (per-job table in #1139's body).
- Lettering board in CI (workflow push + MFab/ProSeal art permission); card v7 sew date; launcher provisioning tesseract/rembg; stale PRs #643/#647/#648 (from 10-06).

## Traps learned this run
- A lane has no rembg_isolated/sam2_isolated venv: MFab/Tires digitizes from a lane silently take the classical route (PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE). Point at the primary checkout's venvs.
- TaskStop on a background waiter doesn't kill its child bash/python — kill by PID.
- delete_session / start_session need Kent at the desktop app; over Remote Control both are refused.

## Cleanup left for Kent (desktop app)
- Delete finished sessions: "W5-03 lettering board v2" (local_7a4241d4, #1152 merged, worktree clean, HEAD on origin) and "W5-08 upload" (local_ab91ea8a, #1138/#1149 merged, clean, on origin). The approval card cannot reach Remote Control.
- This foreman session (sewout-card-v4 worktree): HEAD on origin/claude/sewout-card-v4. Its 3 untracked files (flip-sheet-2026-10-23-standalone.html, lane_cleanup.sh, remove_backed_up_lanes.sh) are copied and cmp-verified into this folder, so deleting the session loses nothing (the app will want force_worktree_cleanup for those untracked files).
- FOREMAN_STATE.md (full run log) is copied here too.
