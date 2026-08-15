---
name: pull-corpus
description: Get Kent's image and stitch-file assets — corpus photos, reference logos, professionally digitized DST/PES — off his machine and into a session that can act on them. Use when Kent says "pull the corpus", "I uploaded the files", "grab the becker logo", "the photos are in Drive", or when work is blocked because a fixture, reference image, or comparison file is not in the checkout.
---

# Pulling corpus and reference assets

EMB-Bot's code arrives in every session automatically; its **images do not**.
That asymmetry is why `becker logo.png` and the 37-file `scratch_corpus/` have
sat in MASTER_SCOPE's "Waiting on Kent" queue for months — not because the work
is hard, but because nobody in a session could see the file. This skill closes
that gap.

**The short version, if you read nothing else:** git is the channel for
anything that should be permanent, and it is the right answer far more often
than it looks. Drive is a narrow fallback for small files that must not be
published — it has a hard size ceiling that rules out photo-sized assets
entirely. Both are below.

## First — decide the channel. Getting this wrong is the failure mode.

There are two ways in, and they are not interchangeable. **`KS-Three/EMB-Bot`
is a PUBLIC repository** (verified 2026-08-14 via the GitHub API — `visibility:
public`). Anything committed is published to the world, permanently, in
history. That single fact decides the routing.

**Kent's ruling, 2026-08-14: the becker comparison assets are fine to publish** —
asked directly whether the professionally digitized DST/PES should stay off a
public repo, he said public is fine. So they go in git, and **this specific
question is settled; do not re-ask it.** What is NOT settled is the general
case: a different third party's file, or a client logo he has not cleared,
still deserves the question.

| The asset | Channel | Why |
|---|---|---|
| Real photos / art meant to be **permanent test fixtures** | **git** | Already this repo's established practice — `digitizer/testdata/photo/` holds 13 MB of committed PNGs (`drone_render.png` alone is 2.4 MB), added deliberately in commits like `fd17a66 test fixture: snowy owl photo`. MASTER_SCOPE's standing ruling clears real-photo provenance. |
| The becker pro DST/PES, and comparison references like it | **git → `digitizer/testdata/reference/`** | Cleared by Kent above. Reference stitch files, not pipeline inputs — keep them out of `testdata/photo/` so they are not mistaken for fixtures. |
| A third party's file Kent has **not** cleared | **ask first** | Publishing is irreversible; git history keeps it even after a delete. One question costs less than a takedown. |
| Genuinely temporary scratch — one-off probes, throwaway renders | **Drive → `scratch_corpus/`** | Gitignored on purpose. |

**Default to git.** It is versioned, needs no tooling, has no size ceiling worth
worrying about, and every future session gets the files for free. The Drive path
below is the exception, for files that genuinely should not be committed.

## The inbox — the default path, and the one to push for

**`digitizer/testdata/inbox/` + `tools/sync-assets.ps1`.** Kent drops files in
the folder, runs one command, and they are in the repo — any number of files,
no per-file ceremony. He asked for exactly this (2026-08-14) after being handed
per-file git commands, and he was right to.

What to tell him:

```powershell
cd C:\Users\EE-LT-11030\Personal\EMB-Bot
.\tools\sync-assets.ps1
```

The script normalises filenames (spaces and `(1)` markers out — a space in a
fixture path has already cost this project time), stages **by explicit path**
per CLAUDE.md footgun #2, commits, and pushes.

### Then file what arrived — the inbox is a staging area, not a home

Assets land unsorted on purpose. Sorting them is the session's job:

| Kind | Destination |
|---|---|
| Real photos / art to digitize, kept as fixtures | `digitizer/testdata/photo/` |
| Professionally digitized DST/PES for comparison | `digitizer/testdata/reference/` |
| Logo / flat art fixtures | `digitizer/testdata/` |

Rename to say what the file *exercises*, matching the existing convention —
`photo_sunset_backlit.png`, `fur_ramp.png`, `tight_crop_pale_subject.png` —
then follow *After a pull* below. **Leave the inbox empty.** Stale files there
mean the process broke.

## The Drive path — small, non-publishable files only

Kent's Drive already has an `EMB-Bot` folder (he uses it for git bundles and
zipped scratch dirs). Assets for this skill go in `EMB-Bot/corpus/`.

### Hard constraint: files come through a context window

`drive.google.com` is **blocked by this environment's network policy** —
`curl` gets `CONNECT tunnel failed, response 403`, confirmed 2026-08-14 against
`$HTTPS_PROXY/__agentproxy/status`. `www.googleapis.com` is reachable but there
is no OAuth token exposed to the shell. So there is **no disk-to-disk download
path**. The only way in is the Google Drive MCP connector, which returns file
contents as base64 *in a tool result* — i.e. through a context window.

Three consequences, all load-bearing:

1. **Always download inside a subagent, one per file.** The base64 must land in
   the subagent's context, not the main session's. The subagent decodes, writes,
   verifies, and reports back one line. A main-session download will blow the
   context on a single photo.
2. **Check `fileSize` from `search_files` BEFORE downloading.** Base64 is ~1.37×
   the byte size. See the ceiling below.
3. **Zips do not work.** Kent's existing habit is to upload archives
   (`scratch_ink-2026-08-11.zip` is 84 MB). That is fine for his own backups and
   useless here — no context window holds it. **Tell him to upload loose files**
   into `EMB-Bot/corpus/`, not an archive.

### Size ceiling — this is the constraint that decides everything

**Small files round-trip perfectly.** A 2,448-byte PNG of incompressible random
data went local → Drive → local and came back **byte-identical**, sha256
`949166876eff…` on both sides, still a valid PNG under `file`.
*(measured 2026-08-14 — this skill's own build session)*

**Large payloads truncate silently, with no error.** A 120,303-byte PNG passed
as a base64 argument arrived in Drive as **4,908 bytes** — Drive cheerfully
reported success and stored a corrupt file. Nothing raised. *(measured
2026-08-14 — same session)* That was the upload direction, which this skill
does not use (Kent uploads by dragging into Drive's web UI). It is recorded
because it establishes the failure *mode*: **the truncation is silent.** Assume
the download direction fails the same way and verify every file.

**Practical guidance:**

| Size | Verdict |
|---|---|
| < ~250 KB | Fine. Pull it. |
| 250 KB – 1 MB | Risky. One file per subagent, verify hard, expect failures. |
| > 1 MB | Do not attempt. *(estimated, not measured — base64 is ~1.37× and a 1 MB file becomes roughly 350k tokens of tool result)* |
| Archives (.zip) | Never. |

**Always `sha256sum` and `file` the result.** A truncated PNG can still have a
valid header — `file` alone will call it a PNG. Size and hash are the real
checks. If Kent can give you the source hash, compare against it; if not, at
minimum confirm the byte count matches Drive's reported `fileSize`.

**The consequence you must not miss:** the photo fixtures in
`digitizer/testdata/photo/` are **1–2.4 MB each**. Every one of them is far
above this ceiling. So the files that matter most for corpus work **cannot come
through Drive at all** — they have to go through git. Re-read the channel table
above before proposing Drive for anything photo-sized.

### Steps

1. Find the folder, then list its children:
   ```
   search_files: mimeType = 'application/vnd.google-apps.folder' and title = 'corpus'
   search_files: parentId = '<that id>'
   ```
   Use `excludeContentSnippets: true` — snippets on binary files are noise.
2. Diff against what is already on disk. Skip files that exist unless Kent
   asked for a re-pull. Report skips; do not silently overwrite.
3. Reject anything over the ceiling, by name and size, with the reason. Do not
   attempt it and fail halfway.
4. For each remaining file, spawn a subagent that:
   - calls `download_file_content` with the file id,
   - writes the returned base64 to a **text** file in the scratchpad,
   - decodes with `base64 -d > <destination>` — never try to `Write` binary
     bytes directly,
   - verifies with `sha256sum` and `file`, confirming the type is what the
     extension claims,
   - reports: filename, bytes written, `file` output, pass/fail.
5. Report what landed, where, and each destination's git status.

## After a pull — the step that is easy to miss

`digitizer/tools/corpus_scorecard.py` scores fixtures against a stored
baseline, but its `FIXTURES` list is **hardcoded** (`corpus_scorecard.py:64`).
A new fixture dropped into `digitizer/testdata/photo/` is invisible to the
scorecard until it is added to that list. So:

1. Append the new fixture to `FIXTURES`.
2. Run `diff` first — new fixtures report as NEW against the baseline, which is
   the correct signal and worth reading before overwriting it.
3. Recapture the baseline only when the new state is deliberately the reference:
   `.venv/bin/python tools/corpus_scorecard.py capture`

MASTER_SCOPE's "Evaluation corpus & harness" entry describes exactly this: the
harness half is built, the corpus half is the gap. A pull that lands real
photos is the corpus half arriving — update that entry via
`/update-master-scope` rather than leaving the doc claiming the gap is still
open.

## Guardrails

- **Never `git add -A`.** CLAUDE.md footgun #2. Stage pulled files by explicit
  path, and only after Kent has seen what they are.
- **Never auto-commit a pull.** Files landing in `digitizer/testdata/photo/` are
  a real change to a public repo and need Kent's eyes first.
- **Never overwrite an existing local file silently.** Say what you are
  replacing and why.
- `scratch_corpus/`, `scratch_reference/` and any other `scratch_*` path are
  covered by `.gitignore` (the `scratch_*` glob, verified with
  `git check-ignore`). `digitizer/testdata/photo/` is **not** — it is tracked.

## Confirmed failure modes

1. **`drive.google.com` refuses to connect.** Not a bug and not fixable from
   inside a session — it is the environment's network policy. Use the connector,
   not `curl`. Changing it is an environment setting only Kent can alter.
2. **A download returns a Google-native MIME type.** If Kent drags an image into
   Drive and it converts to a Google Doc, `download_file_content` needs an
   `exportMimeType` and the bytes will not be the original. Check `mimeType` in
   the search result; a real PNG reads `image/png`, not
   `application/vnd.google-apps.*`. Have him re-upload with conversion off.
3. **The file is there but the search misses it.** `search_files` matches
   `title`, and Drive keeps the original filename including spaces —
   `becker logo.png` has a space in it. Prefer listing by `parentId` over
   guessing at title matches.
