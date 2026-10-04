---
name: memory-outside-the-repo
description: EMB-Bot sessions rooted in C:\Users\EE-LT-11030\.claude-work write their memory OUTSIDE this repo; a folder spot-check has to read session cwds, not only project folders named emb-bot
metadata:
  type: project
---

Found 2026-10-03. Kent asked on 2026-10-01 for a spot check that all EMB-Bot
work lands in the right folder. That check scanned `~/.claude*/projects/` for
folders with "emb-bot" in the name and called it clean. It missed five live
EMB-Bot sessions rooted in `C:\Users\EE-LT-11030\.claude-work` — the work
profile's config folder — because their project folder is named
`C--Users-EE-LT-11030--claude-work`.

**What lands where for those sessions:**
- Code, commits, PRs: worktrees under this repo's `.claude/worktrees/`. Right place.
- Memory: `~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, a
  plain folder shared with unrelated work notes. NOT the junction to this
  folder, so none of it rides a PR, reaches a cloud session, or is loaded by a
  session rooted in EMB-Bot. Four EMB-Bot notes were there; snapshots are now
  here ([[parallel-agent-with-embot]], [[embot-browser-fill-lane-state]],
  [[embot-handover-numbers-and-stacked-branches]], [[embot-sub-unit-stitches-lane]]).
- Loose files: `.claude-work\emb-bot-bean-probe\` (8 probe renders) — copied,
  hash-verified, to `Claude Personal\Embroidery\Archive\emb-bot-bean-probe-2026-10-02\`.
- Those sessions also do not load this repo's CLAUDE.md, settings or hooks on
  their own (CLAUDE.md, footgun 4).

**Why:** where a session is rooted is a launch habit, and only Kent changes
it. Until he does, new notes keep landing there and the snapshots here age.

**How to apply:**
- For "is work going to the right folder", call `list_sessions` and read each
  `cwd`, and list `~/.claude/projects/*/memory/` by modified time. A name
  filter is not a check.
- Before trusting this folder as the whole memory, look in that one too.
- The other sessions run heavy `pytest -n 4` jobs; with two of them going, a
  full digitizer suite here reached 13% in ten minutes. Read the process
  list's COMMAND LINES before deciding a slow run is yours.
