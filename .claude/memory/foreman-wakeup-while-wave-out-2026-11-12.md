---
name: foreman-wakeup-while-wave-out-2026-11-12
description: Kent 11-12 to a foreman that dispatched 7 cloud sessions then sat idle while all merged ("you've been stale for 10 hours"): while a wave is out, set a wake-up before ending the turn; cloud sessions never report back
metadata:
  type: feedback
---

Kent, 2026-11-12, to a foreman that had dispatched 7 cloud sessions and then
sat idle until Kent spoke while all 7 merged: "you've been stale for 10
hours...". Follows [[cloud-wave-2026-11-06]] (the first big cloud wave) and
[[foreman-merges-and-bypass-2026-11-06]] (the foreman, not Kent, moves PRs to
merge).

**Why:** a cloud session never reports back to the session that started it, and
nothing wakes an idle foreman. A foreman that ends its turn with a wave out has
no event coming: the PRs merge, the next evidence step waits, and every
"Decisions for Kent" in a PR body sits unread until Kent notices the silence.

**How to apply:** whenever a wave is out, before ending the turn:

- Set a wake-up: a `CronCreate` hourly PR sweep, or a background `gh run watch`
  on the slowest run of the wave.
- Prefer local sessions started with `wake_when_done` when the work fits the
  laptop: those do report back and wake the foreman themselves.
- Delete the wake-up (`CronDelete`) when the queue is empty, so it does not
  outlive the wave.
- On waking: report the merged PRs, run the next evidence step, and roll up
  every "Decisions for Kent" from the PR bodies into one question for him.
