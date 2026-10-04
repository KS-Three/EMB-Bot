---
name: next-work-from-main-not-handoffs
description: When Kent asks "what's next", answer from the current docs on origin/main (ROADMAP, PRODUCT, MASTER_SCOPE), not from a previous session's handoff note or leftover PRs
metadata:
  type: feedback
---

Asked 2026-10-01 what work comes next, the first answer led with a handoff
note's approved-but-unstarted task and the previous sessions' open PRs. Kent:
*"laptop is set now, don't base your work around previouse sessions."*

**Why:** a handoff note is one session's view of its own loose ends. That one
was withdrawn by Kent the next day ("We shouldn't have to warn the user of
anything") — so the answer built on it would have queued work he no longer
wanted. The docs on `origin/main` are what he keeps current.

**How to apply:** for "what's next", `git fetch`, then read ROADMAP (phase and
gates), PRODUCT (launch checklist, open decisions) and MASTER_SCOPE (live
defects, "Waiting on Kent") from `origin/main` — the main checkout can sit
dozens of commits behind. Sort the answer into: his decisions, flips waiting
on him, and work buildable with no decision. Open PRs are one line of live
state, not the frame. A handoff memory is a lead to verify, never the plan.

Also: **after a pause of a day or more, re-read the memory index before
continuing an approved design.** This session resumed on 10-03 with a 10-01
approval for a customer-facing row; the 10-02 ruling above had landed in
between and reversed it. See [[no-warnings-reaches-readouts]].
