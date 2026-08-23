# Cache seam, photo width floor, and three environment betrayals (2026-08-22)

The session Kent opened with "three questions, then run until you're out of
ammo" — workload answer: tonal acceptance loop + tonal engineering pass +
the stage 0-4 cache, per-item branches, Drive photos. What follows is what
survived contact with the machine, ordered by how likely a future session
is to need it.

## The acceptance-photo channel is an unresolved contradiction

Kent approved "drop photos in Drive, pull them into the cloud session" —
and the pull-corpus skill's own measurements make that impossible: binary
through the Drive connector transits a context window, and agent
re-emission corrupts it (1 flipped bit destroyed a 7,213-byte PNG at
correct length; 92% truncation at 24K chars of base64). Photos are MBs.
The skill's git channel publishes to a PUBLIC repo — barred for private
portraits by spec decision 6. So the approved flow has no working
implementation, and the working flows (attach to the conversation, or a
private repo added via add_repo) both need Kent's sign-off. Queued to him;
do not silently substitute a channel he hasn't approved.

## Downloads that lie: the SAM2 prewarm truncation

`urllib` surfaces an early proxy close as ordinary EOF — `read()` returns
b"" and no exception. `--prewarm` twice cached a truncated checkpoint
(136.9 MB, then 140.8 MB of 156.0 MB), printed "checkpoint cached", and
every SAM2 job died with torch's "corrupted checkpoint" error at runtime,
far from the cause. The `.part`-rename discipline did exactly nothing,
because "success" was the lie. Fixed by enforcing Content-Length
(`sam2_worker._ensure_checkpoint`), but the lesson generalizes: **in this
proxied environment, any streamed download must verify byte count against
the server's own claim** — curl with `-C -` resume converged in one
attempt where the naive loop failed twice. A green "cached at ..." line is
not evidence the bytes are whole.

## The satin width floor's class paradox (why the gate is the toggle lane)

Live defect 2's fix ("2·p90 < 1.0mm → run") could not be gated by
classification: `drone_render`/`summit_badge` — the measured defect
population — classify **gradient**, and so do 6 of 7 real customer logos —
the measured DISPROOF population (61/64 of their sub-mm satins are
pro-correct). Same class, opposite verdicts; the separation is content
stage 0 cannot see (phase-2 framing work). The only honest gate is the
photo lane itself (`PHOTO_CLASSES`), reachable via the "This is a photo"
toggle — where the defect population is reachable and the disproof
population is not. Landed that way; the floor constant is Law 31's 1.0mm
adopted verbatim, never swept (gate 1 owns its value).

## The blend tier's real off-switch is the speckle gate, not the r² floor

The spec's "r² floor retune" premise (owl n=27, best 0.481 vs floor 0.5)
inverted under a wider measurement (288 regions, six fixtures): only 4
real regions sit within 0.05 under the floor, while the **speckle gate
rejects 41 of the 42 real regions that clear it** — including drone
patches fitting at r² 0.92. Real-photo texture carries local variance
synthetic ramps don't; the gate was tuned on synthetics. The retune
candidate is `RAMP_SPECKLE_MAX` (or residual-based speckle), and it is
quality-visible — parked for the acceptance eyeball loop, measurement in
`docs/tonal-eng-measurements-2026-08-22.md`.

## Environment betrayals a future cloud session should expect

- **The tail-pipe exit-code trap bit again**, in vitest this time — CLAUDE.md
  warns about pytest; the trap is universal. Never `suite | tail`;
  background the run and read its file.
- **A loaded machine forges Studio failures**: `preloadAllFontsSync`'s 10s
  hookTimeout failed 5 spec files under pip/pytest contention, 3 on a
  second loaded run, 0 solo. A failure set taken under load is not a
  failure set.
- **The service's job cache outlives a fixed environment**: after repairing
  the SAM2 venv, the A/B harness returned the PRE-repair fallback results
  from the job cache (identical content key), 0.0s per row. Restart the
  service (or change a config bit) after changing machine state a cached
  job embedded. Relatedly, `pkill -f <pattern>` kills the wrapper shell
  whose own command line contains the pattern — use `pkill -f "[d]igitizer_service"`.
- **This container runs the full digitizer suite in ~7 min** (`-n auto`,
  4 cores) with exactly the documented Linux golden set failing
  (enthusiast_logo ×2, pushcomp[towel]) — matched the table on the first
  try, twice.
