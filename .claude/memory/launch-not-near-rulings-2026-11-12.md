---
name: launch-not-near-rulings-2026-11-12
description: Kent 11-12: not ready for going live, do not raise billing/licence/signing/hosting/legal; plus his rulings that day (accept all 8 built picks, installer name "Decide later", defect 28 close it) and the main ffefc3b1 state
metadata:
  type: project
---

**Kent, 2026-11-12, when the foreman opened a billing/licence grill:** "Woah woah,
we are not ready for going live yet. not even close... I haven't even seen what
you have right now...".

**Why:** the foreman pushed launch-gate decisions before Kent had looked at the
build.
**How to apply:** do not raise billing, licence check, code signing, installer
hosting, update announcements, app name or legal paper until Kent says launch is
near. Show him the running build first. A foreman that dispatches work follows
[[foreman-wakeup-while-wave-out-2026-11-12]]; the wave itself is
[[cloud-wave-2026-11-06]].

**Rulings the same day:**

- On the wave's built picks: "Accept all 8 (Recommended)". They stand as merged:
  undo merges backward only (#1399); Cancel button in the panel only, none on
  the lettering or manual panels, and the "Cancelling…" text (#1400); local app
  windowed, Quit button only, port 8721 fixed (#1405); MASTER_SCOPE area 3
  status cell unchanged (#1401).
- On the installer name "EMB Bot Studio" and the publisher string from #1403:
  "Decide later". Until he rules, no installer leaves his hands and no
  clean-machine run happens, because the first real install pins the AppId.
- On defect 28: "Close it (Recommended)". NOT yet written into `MASTER_SCOPE.md`;
  the next scope-refresh lane moves it to Closed and keeps the chart-limit note.

**State on main `ffefc3b1`:** `windows-app.yml` run 43244077001 green (the frozen
exe matched the venv service on five lanes; installer 109 MB, zip 167 MB; a
hosted runner, not a clean PC). Still unasked from the PR bodies: signing, update
announcement, hosting (#1403). PRODUCT's font line is now 85 (#1401).
