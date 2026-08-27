# One-command pro-parity run: prep both lanes, score both, write ONE log.
#
# Why this exists: the documented invocation in prep_both.py's docstring is
# bash. Two parts of it are wrong in PowerShell and both fail quietly rather
# than loudly:
#
#   * `PRO_PARITY_OUT=<dir> python ...` is bash's per-command env syntax.
#     PowerShell parses it as a command name and errors, or worse, a previous
#     `$env:PRO_PARITY_OUT` from the same shell is still set and the run
#     silently writes to the WRONG directory.
#   * `scorecard.py <OUT>/real/*` relies on the SHELL expanding the glob.
#     PowerShell does not: scorecard.py receives the literal string `real/*`,
#     finds no `pro_stitches.csv` under it, `continue`s past every entry, and
#     prints a clean empty report. Zero designs scored reads exactly like a
#     successful run with nothing to say.
#
# Path and interpreter resolution follows ladder.ps1's convention (resolve from
# $PSScriptRoot, walk up to the primary checkout's venv when running inside a
# worktree that has none) rather than hardcoding a profile.
[CmdletBinding()]
param(
    # Interpreter. Worktrees carry no .venv, so this falls back to the primary
    # checkout's the same way ladder.ps1 does.
    [string]$Python,

    # Where prep writes, and where the scorer reads. NEVER share one directory
    # between two runs you intend to compare.
    [string]$Out,

    # Corpus root. prep_both.py already defaults to the Google Drive path; pass
    # this only if the corpus has moved.
    [string]$Root,

    # Score an EXISTING -Out without re-prepping. The surface() fix changed the
    # GRADER, not the engine, so scoring a prep directory you already have
    # isolates the scorecard delta in minutes instead of hours. Use the full
    # run for a number that is also current with the engine.
    [switch]$SkipPrep
)

$ErrorActionPreference = 'Stop'

$proParity = $PSScriptRoot                                  # digitizer/tools/pro_parity
$digitizer = Split-Path -Parent (Split-Path -Parent $proParity)
$repo      = Split-Path -Parent $digitizer

if (-not $Python) {
    $candidates = @(
        (Join-Path $digitizer '.venv\Scripts\python.exe'),
        (Join-Path (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $repo))) 'digitizer\.venv\Scripts\python.exe')
    )
    $Python = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Python -or -not (Test-Path -LiteralPath $Python)) {
    throw "No python interpreter found. Pass -Python <path to digitizer\.venv\Scripts\python.exe>."
}
if (-not (Test-Path -LiteralPath (Join-Path $proParity 'prep_both.py'))) {
    throw "prep_both.py not found next to this script ($proParity)."
}

if (-not $Out) { $Out = Join-Path $repo 'parity_out_run' }
if ($SkipPrep -and -not (Test-Path -LiteralPath $Out)) {
    throw "-SkipPrep needs an existing -Out directory; '$Out' does not exist."
}
New-Item -ItemType Directory -Force $Out | Out-Null
$log = Join-Path $Out 'parity_run.log'

# PowerShell runs .ps1 in-process, so a bare `$env:X = ...` outlives the script
# and the next run in the same shell inherits it. ladder.ps1 learned this;
# restore in a finally so a mid-run failure does not leak either.
$savedOut  = $env:PRO_PARITY_OUT
$savedRoot = $env:PRO_PARITY_ROOT

try {
    Push-Location $digitizer
    "=== parity run $(Get-Date -Format o) ===" | Tee-Object -FilePath $log -Append
    "python : $Python"                         | Tee-Object -FilePath $log -Append
    "out    : $Out"                            | Tee-Object -FilePath $log -Append

    $env:PRO_PARITY_OUT = $Out
    if ($Root) { $env:PRO_PARITY_ROOT = $Root }

    if ($SkipPrep) {
        'PREP SKIPPED - scoring the existing directory' | Tee-Object -FilePath $log -Append
    } else {
        '########## PREP (both lanes, 15 designs) ##########' |
            Tee-Object -FilePath $log -Append
        & $Python (Join-Path $proParity 'prep_both.py') 2>&1 |
            Tee-Object -FilePath $log -Append
        # A dead prep must not read as a clean run - the whole point of the
        # exit-code check ladder.ps1 had to add after logging COMPLETE on one.
        if ($LASTEXITCODE -ne 0) {
            "PREP FAILED with exit $LASTEXITCODE - not scoring" |
                Tee-Object -FilePath $log -Append
            exit 1
        }
    }

    foreach ($lane in @('real', 'recon')) {
        $laneDir = Join-Path $Out $lane
        if (-not (Test-Path -LiteralPath $laneDir)) {
            "LANE $lane MISSING at $laneDir" | Tee-Object -FilePath $log -Append
            continue
        }
        # Enumerate explicitly. scorecard.py skips any directory without a
        # pro_stitches.csv WITHOUT complaining, so passing it nothing at all
        # produces an empty report that looks like a successful one - hence
        # the count check below rather than trusting the scorer to object.
        $designs = @(Get-ChildItem -LiteralPath $laneDir -Directory |
                     Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'pro_stitches.csv') } |
                     ForEach-Object { $_.FullName })
        "########## SCORE lane=$lane ($($designs.Count) designs) ##########" |
            Tee-Object -FilePath $log -Append
        if ($designs.Count -eq 0) {
            "NO SCORABLE DESIGNS in $laneDir - nothing was scored for this lane" |
                Tee-Object -FilePath $log -Append
            continue
        }
        & $Python (Join-Path $proParity 'scorecard.py') @designs 2>&1 |
            Tee-Object -FilePath $log -Append
    }
}
finally {
    Pop-Location
    $env:PRO_PARITY_OUT  = $savedOut
    $env:PRO_PARITY_ROOT = $savedRoot
}

'' | Tee-Object -FilePath $log -Append
"PARITY RUN COMPLETE - send this file: $log" | Tee-Object -FilePath $log -Append
Write-Host ''
Write-Host "Done. Send me this file: $log" -ForegroundColor Green
