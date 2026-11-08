---
name: local-lanes-fill-disk-2026-11-08
description: Ultra-K3 night 11-07/08: ~25 local lane worktrees (each with npm ci node_modules) plus 12 workflows filled Kent's C: drive to 143 MB free and agents failed ENOSPC
metadata:
  type: project
---

On 2026-11-08 ~02:15, running many LOCAL lanes on Kent's laptop (each a scratchpad git worktree with its own `npm ci` node_modules, Playwright output, and the digitizer renders) drove C: to 143 MB free; vitest/Playwright failed with ENOSPC. Removing merged lanes' worktrees and downloaded CI artifacts got back to 2.8 GB; the rest of the drive is Kent's.

**Why:** cloud sessions only launch while the conversation is open in the desktop app (Kent was on Remote Control), so refills ran locally and nothing reclaimed space between lanes.

**How to apply:** when refilling with local lanes, remove each lane's worktree as soon as its PR merges (not at the end), check `df -h /c` every sweep and stop starting lanes under ~10 GB free, and prefer CPU/disk-light workflows (reviews, audits) when cloud is unavailable. Related: [[cloud-wave-2026-11-06]], [[foreman-merges-and-bypass-2026-11-06]].
