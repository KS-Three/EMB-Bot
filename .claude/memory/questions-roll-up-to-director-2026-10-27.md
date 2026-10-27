---
name: questions-roll-up-to-director-2026-10-27
description: A worker session started by a foreman or director never asks Kent directly; its decisions go to the starting session via SendMessage, and the director asks Kent
metadata:
  type: feedback
---

A worker session (one started by a foreman or director session) never asks Kent a
question itself: no `AskUserQuestion`, no prose question to him. It sends the decision
to the session that started it with `SendMessage`. The message holds the question, 2-4
options, each with what it delivers, its cost and its catch, and the worker's pick.
The worker then carries on with independent work. The director asks Kent and relays
his words back verbatim.

**Why:** Kent, 2026-10-27, verbatim: "qestions from your workers should roll up to you
for me to answer". With many workers running, questions arriving from every session
at once scatter his attention. One queue at the director lets him answer in one place,
with the director's context on how each decision interacts with the others.

**How to apply:** This is an exception to CLAUDE.md's "End a turn by PROMPTING Kent"
rule, which still holds for a session Kent drives himself. Whether a session is a
worker is set by its first message: if that came from another session ("You are a
session started from another session"), it is one. The k3 skill's §7 and its
`templates.md` preamble carry the rule, so every brief includes it. A relayed answer
carries Kent's authority only when it quotes his words. See also [[build-what-was-priced]].
