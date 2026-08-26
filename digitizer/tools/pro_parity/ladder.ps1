# Curve-fidelity tol ladder - shape-fidelity plan Task 2.
#
# Three sequential arms; each preps both lanes for all 15 designs. Paths are
# resolved from this script's own location (the convention tools/start-emb-bot.ps1
# states and this script originally broke by hardcoding one machine's profile
# and a transient worktree name), so it survives the worktree being merged away.
#
# Reads the corpus from PRO_PARITY_ROOT (prep_both.py's Drive default) and
# writes each arm to its own PRO_PARITY_OUT - never share one between arms.
[CmdletBinding()]
param(
    # Interpreter: worktrees carry no .venv, so this defaults to the primary
    # checkout's. Override when running from a checkout that has its own.
    [string]$Python,
    [string]$OutRoot,
    [double[]]$Tolerances = @(0.2, 0.1, 0.05)
)

$ErrorActionPreference = 'Stop'

$proParity = $PSScriptRoot                                  # digitizer/tools/pro_parity
$digitizer = Split-Path -Parent (Split-Path -Parent $proParity)
$repo      = Split-Path -Parent $digitizer

if (-not $Python) {
    # Walk up out of .claude/worktrees/<name> to the primary checkout if we are
    # in a worktree; otherwise this checkout's own venv.
    $candidates = @(
        (Join-Path $digitizer '.venv\Scripts\python.exe'),
        (Join-Path (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $repo))) 'digitizer\.venv\Scripts\python.exe')
    )
    $Python = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Python -or -not (Test-Path -LiteralPath $Python)) {
    throw "No python interpreter found. Pass -Python <path to digitizer/.venv/Scripts/python.exe>."
}
if (-not (Test-Path -LiteralPath (Join-Path $proParity 'prep_both.py'))) {
    throw "prep_both.py not found next to this script ($proParity)."
}

if (-not $OutRoot) { $OutRoot = Join-Path $repo 'parity_out_ladder' }
New-Item -ItemType Directory -Force $OutRoot | Out-Null
$log = Join-Path $OutRoot 'ladder.log'

# Preserve the caller's environment: PowerShell runs .ps1 in-process, so a bare
# `$env:X = ...` outlives the script and the next prep run in that shell would
# silently inherit the last arm's tolerance and output dir.
$savedOut = $env:PRO_PARITY_OUT
$savedTol = $env:PRO_PARITY_SIMPLIFY_TOL
$failed = @()

try {
    Push-Location $digitizer
    "=== ladder run $(Get-Date -Format o) | python=$Python ===" |
        Tee-Object -FilePath $log -Append
    foreach ($tol in $Tolerances) {
        $tag = ($tol.ToString('0.000') -replace '\.', '')
        "########## ARM tol=$tol -> $tag ##########" | Tee-Object -FilePath $log -Append
        $env:PRO_PARITY_OUT = Join-Path $OutRoot $tag
        $env:PRO_PARITY_SIMPLIFY_TOL = $tol
        & $Python (Join-Path $proParity 'prep_both.py') 2>&1 |
            Tee-Object -FilePath $log -Append
        # A missing interpreter or a dead arm must not read as a clean run:
        # the first version logged LADDER COMPLETE and exited 0 in both cases.
        if ($LASTEXITCODE -ne 0) {
            $failed += "$tol (exit $LASTEXITCODE)"
            "ARM tol=$tol FAILED with exit $LASTEXITCODE" |
                Tee-Object -FilePath $log -Append
        }
    }
}
finally {
    Pop-Location
    $env:PRO_PARITY_OUT = $savedOut
    $env:PRO_PARITY_SIMPLIFY_TOL = $savedTol
}

if ($failed.Count) {
    "LADDER INCOMPLETE - failed arms: $($failed -join ', ')" |
        Tee-Object -FilePath $log -Append
    exit 1
}
'LADDER COMPLETE' | Tee-Object -FilePath $log -Append
