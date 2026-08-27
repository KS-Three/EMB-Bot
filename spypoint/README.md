# spypoint-sync (proof of concept)

> **Not part of EMB-Bot.** This folder is an unrelated personal utility, parked
> on this branch so it can be pulled onto a Windows machine without a browser
> download going missing. It is not intended to merge into `main`; nothing in
> the stitch engine, Studio, or digitizer imports it, and it adds no
> dependencies to any of the three suites.

Pulls your SpyPoint **cameras** (name, model, location, battery, signal, last
sync) and **photos** to local disk, incrementally, using the same REST API the
SpyPoint app itself uses (`restapi.spypoint.com/api/v3`).

**Unofficial.** Endpoints mirrored from two community clients —
[hstern/pyspypoint](https://github.com/hstern/pyspypoint) and
[coloradude/spypoint-api-wrapper](https://github.com/coloradude/spypoint-api-wrapper).
SpyPoint can change the API without notice; the script fails loudly (nonzero
exit, clear message) rather than guessing when that happens.

## Requirements

- Node **20+** (`node --version`)
- Your SpyPoint login. No npm install — the script has zero dependencies.

## Quick start

```powershell
# PowerShell (current window only — nothing persisted)
$env:SPYPOINT_EMAIL    = "you@example.com"
$env:SPYPOINT_PASSWORD = "your-password"

node spypoint-sync.mjs --dry-run     # 1. logs in, lists cameras + would-be downloads, writes nothing
node spypoint-sync.mjs --inspect     # 2. dumps the raw field names of one camera + one photo
node spypoint-sync.mjs               # 3. real run (caps at 500 photos/camera; --max 0 = full backfill)
```

(`cmd`: `set SPYPOINT_EMAIL=...` — `bash`: `export SPYPOINT_EMAIL=...`)

Step 2 matters: the camera/photo schemas are undocumented, so the script finds
location/battery/signal by hunting key names. `--inspect` shows exactly what
your account returns — paste that output back to Claude (trim anything you
consider sensitive) and the next stage (map dashboard) gets built on your real
field names instead of guesses.

## Options

| Flag | Meaning |
| --- | --- |
| `--out DIR` | output directory (default `./spypoint-data`, or `$SPYPOINT_OUT`) |
| `--max N` | max new downloads per camera per run (default 500; `0` = unlimited) |
| `--limit N` | photos per API page (default 100) |
| `--size S` | `large` (default) / `medium` / `small`; falls back downward |
| `--cameras A,B` | only cameras whose name or id contains one of these |
| `--dry-run` | show what would download, write nothing |
| `--inspect` | dump raw schemas, then exit |
| `--quiet` | errors and final summary only |

## Output

```
spypoint-data/
  cameras.raw.json    full camera documents, untouched
  cameras.csv         location, battery, signal, temperature, memory, plan, last_seen + age
  photos.jsonl        one metadata line per downloaded photo (id, camera, date, tags, url)
  photos/<camera>/<YYYY-MM>/<photoId>.jpg
```

**Incremental by filename:** a photo whose `<photoId>.jpg` already exists
anywhere under `photos/` is skipped — the photo tree *is* the sync state.
Delete a file to re-fetch it. Each run re-walks the photo *list* (metadata
only, ~100 per request) and downloads only what's missing.

## Scheduling on Windows

Create `sync.cmd` next to the script:

```bat
@echo off
set SPYPOINT_EMAIL=you@example.com
set SPYPOINT_PASSWORD=your-password
node "%~dp0spypoint-sync.mjs" --quiet
```

Then Task Scheduler → Create Basic Task → run it hourly. **That `.cmd` holds
your password** — the `.gitignore` here already excludes it and the synced
photos, because EMB-Bot is a public repo. Hourly is plenty: the cameras
themselves only upload a few times a day on their transmission schedule.

## Caveats

- **Unofficial API, your own credentials.** This makes the same requests the
  SpyPoint app makes, against your own account — but it's not a sanctioned
  integration, so treat breakage as expected eventually, not as a bug.
- **Photos are the transmitted versions** (compressed cellular uploads). The
  full-resolution originals stay on the SD card; HD retrieval still goes
  through the SpyPoint app/plan.
- **Coordinates are GeoJSON `[longitude, latitude]`**, from
  `status.coordinates[0].position.coordinates` — confirmed 2026-08-27, not
  assumed. The same object also carries DMS strings (`latitude: "N43
  53.140980"`, `longitude: "W89 1.904100"`), and converting those reproduces
  the numeric array exactly with longitude first. Don't "fix" the order.
- **A camera only has photos if it is still transmitting.** The script flags
  any camera silent for more than 30 days, because a stale camera producing
  zero photos is the expected outcome, not a failure.
- **Politeness is built in:** ~250 ms between API calls, ~150 ms between
  downloads, no retry storms.

## What has actually been verified

As of 2026-08-27, against a real 4-camera FLEX-M account:

- **Login works** and returns a usable bearer token.
- **`camera/all` works** — all four cameras came back with GPS, battery,
  signal, temperature, memory, firmware, and subscription details.
- **Field extraction is unit-tested** against the real camera document, with
  assertions pinning the `[lng, lat]` ordering, the signal fields, and the
  battery source, plus a differently-shaped fixture covering the fallback
  paths and garbage input.
- **Photo listing is reachable and correctly returned zero photos.** Every
  camera on that account had been offline for 7–9 months, and the SpyPoint
  app itself showed no photos either — so the empty result was cross-checked
  against the vendor's own client and matches. The query is not at fault.

The one thing still untested is the **download and paging path**, which has
never run against an actual photo, because there was none to run against.
Expect the first sync from a live camera to be where any remaining bug shows
up.

## Testing from a Claude cloud session

`restapi.spypoint.com` is reachable from Claude's cloud containers (verified
2026-08-27), so a cloud session *can* run this against the live API.

Doing so means putting `SPYPOINT_EMAIL` / `SPYPOINT_PASSWORD` into the cloud
environment's variables — and Anthropic's own documentation advises against
that: cloud environments have **no secrets store**, and anyone who uses the
environment can read the values. For a personal environment that is only you,
but the password sits in plain text in the environment config rather than in a
vault.

Running it locally on Windows avoids the question entirely, which is why the
Quick start above sets the variables per-shell instead. If you do use the cloud
path, treat the SpyPoint password as exposed and change it afterward.
