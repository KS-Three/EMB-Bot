# Inbox — drop assets here

Kent's drop zone. Put images, stitch files, reference art, anything a Claude
session needs to see, in this folder and run:

```powershell
.\tools\sync-assets.ps1
```

One command, any number of files. Then tell a session "I dropped files in the
inbox."

## Why this exists

EMB-Bot's code reaches every session automatically; its images never did. Two
items sat in MASTER_SCOPE's "Waiting on Kent" queue for months — `becker
logo.png` plus its professionally digitized DST/PES, and the 37-file
`scratch_corpus/` — not because the work was hard, but because no session
could see the file.

## This is a staging area, not a home

Files here are **unsorted by design**. A session moves them where they belong:

| Kind | Destination |
|---|---|
| Real photos / art to digitize, kept as fixtures | `digitizer/testdata/photo/` |
| Professionally digitized DST/PES for comparison | `digitizer/testdata/reference/` |
| Logo / flat art fixtures | `digitizer/testdata/` |

A fixture is invisible to `tools/corpus_scorecard.py` until it is added to that
script's hardcoded `FIXTURES` list — moving the file is not the whole job.

## Two things to know

**This is a public repository.** Anything committed here is published and stays
in git history after a delete. Kent cleared the becker comparison assets on
2026-08-14; a different third party's file still deserves a question first.

**Don't let it become a junk drawer.** Once a session has filed something, it
should leave. If the inbox has stale files in it, that is a bug in the process,
not a feature.
