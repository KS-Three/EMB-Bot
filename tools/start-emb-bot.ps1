#Requires -Version 5.1

# Keep this file ASCII-only. Windows PowerShell 5.1 reads a BOM-less .ps1 as
# ANSI, so a UTF-8 em-dash arrives as three cp1252 chars whose last is U+201D
# -- and PowerShell accepts curly quotes as string delimiters. That desyncs
# every string after it, and the script dies with "the string is missing the
# terminator" pointing at an unrelated line. PowerShell 7 reads UTF-8 and is
# unaffected, which is how this shipped broken under its own #Requires 5.1.
# (2026-08-26)

<#
.SYNOPSIS
    Start EMB-Bot locally and open it in the default browser.

.DESCRIPTION
    Opens the Studio dev server (and, unless -NoDigitizer, the Python
    auto-digitizer service) in their own PowerShell windows, waits until the
    Studio's port accepts a TCP connection AND the digitizer answers /health,
    then opens the browser.

    Both servers block their window until Ctrl+C, which is why each gets its
    own. Closing a window stops that server.

    The repo root is resolved from this script's own location, so the repo can
    be moved or cloned anywhere without editing this file.

    If a digitizer is already listening on 8721 (another session's, for
    instance) it is NOT started over. tools/service-check.mjs reads its
    /health and compares the engine commit it was started from with this
    checkout's HEAD. A stale service (its commit is not HEAD, or its tracked
    tree was dirty when it started) that is idle is stopped and replaced, with
    both commits printed (Kent's ruling 2026-10-25); -KeepStale only reports it.
    A service that is working a job is never stopped. A process on the port
    that is not a digitizer is never touched.

.PARAMETER NoDigitizer
    Skip the Python auto-digitizer. Text and lettering work without it; only
    image auto-digitize needs it.

.PARAMETER KeepStale
    Leave a stale, idle digitizer on 8721 running: report it with both commits
    instead of replacing it. Without this switch a stale idle service is
    stopped and a fresh one started. Replacement never applies to a busy
    service or to a process that is not a python digitizer, switch or not.

.PARAMETER Port
    Studio port to wait on and open. Defaults to 5173. Vite auto-increments
    when the port is taken, so pass the port it actually printed if it moved.

.PARAMETER TimeoutSeconds
    How long to wait for the Studio before giving up on opening the browser.
    Defaults to 180 - a cold `npm install` can take a while.

.EXAMPLE
    .\tools\start-emb-bot.ps1

.EXAMPLE
    .\tools\start-emb-bot.ps1 -NoDigitizer

.EXAMPLE
    .\tools\start-emb-bot.ps1 -KeepStale
#>
[CmdletBinding()]
param(
    [switch]$NoDigitizer,
    [switch]$KeepStale,
    [int]$Port = 5173,
    [int]$TimeoutSeconds = 180
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $repo 'app'
$digitizerDir = Join-Path $repo 'digitizer'
$serviceCheck = Join-Path $PSScriptRoot 'service-check.mjs'
$digitizerPort = 8721
$digitizerUrl = "http://127.0.0.1:$digitizerPort"

if (-not (Test-Path -LiteralPath (Join-Path $appDir 'package.json'))) {
    throw "No app/package.json under '$repo'. Expected this script to live in the repo's tools/ directory."
}

# Each server gets its own window: both hold their terminal until Ctrl+C.
# Only single quotes inside these commands - Start-Process passes the whole
# string as one argument and embedded double quotes would be mangled.
function Start-ServerWindow {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$Command
    )
    $inner = "`$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
    Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoExit', '-Command', $inner | Out-Null
}

# What is on the digitizer's port, decided by tools/service-check.mjs (which
# holds every rule). Returns the verdict object {action, reason, lines}, or
# $null when node is not on PATH or the check itself failed - the caller then
# falls back to the old behaviour of just starting a digitizer.
function Get-DigitizerVerdict {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { return $null }
    $checkArgs = @($serviceCheck, '--json', '--repo', $repo, '--url', $digitizerUrl)
    if ($KeepStale) { $checkArgs += '--keep-stale' }
    try {
        $raw = & node @checkArgs 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return (($raw | Select-Object -Last 1) | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

# Stop the process listening on the digitizer's port - only if it is python.
# service-check.mjs has already said the thing answering /health is a stale,
# idle digitizer; this is the second lock, so a port that changed hands in
# between is never killed.
function Stop-DigitizerListener {
    $conn = Get-NetTCPConnection -LocalPort $digitizerPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $conn) {
        Write-Warning "No listener found on port $digitizerPort to stop."
        return $false
    }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if (-not $proc -or $proc.ProcessName -notlike 'python*') {
        $name = if ($proc) { $proc.ProcessName } else { 'unknown' }
        Write-Warning "The listener on port $digitizerPort is '$name', not python. Leaving it alone."
        return $false
    }
    Write-Host "Stopping the stale digitizer (pid $($proc.Id))..."
    Stop-Process -Id $proc.Id
    $freeBy = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $freeBy) {
        if (-not (Get-NetTCPConnection -LocalPort $digitizerPort -State Listen -ErrorAction SilentlyContinue)) { return $true }
        Start-Sleep -Milliseconds 500
    }
    Write-Warning "Port $digitizerPort is still held 15 s after stopping pid $($proc.Id)."
    return $false
}

Write-Host "Repo:   $repo"
Write-Host 'Window 1: Studio (npm run dev)'
Start-ServerWindow -Title 'EMB-Bot Studio' -Command "Set-Location -LiteralPath '$appDir'; npm install; npm run dev"

# Whether to wait for the digitizer's /health before opening the browser:
# not when it is skipped, when node is missing, or when something that is not
# a digitizer holds the port (the wait would only run out the clock).
$waitForHealth = $false

if ($NoDigitizer) {
    Write-Host 'Window 2: skipped (-NoDigitizer) - image auto-digitize will be unavailable.'
}
else {
    $startDigitizer = $false
    $verdict = Get-DigitizerVerdict
    if ($null -eq $verdict) {
        Write-Warning 'Could not check port 8721 (node missing or the check failed); starting a digitizer as before.'
        $startDigitizer = $true
    }
    else {
        foreach ($line in @($verdict.lines)) { Write-Host "Digitizer: $line" }
        switch ($verdict.action) {
            'start' { $startDigitizer = $true; $waitForHealth = $true }
            'replace' {
                if (Stop-DigitizerListener) { $startDigitizer = $true; $waitForHealth = $true }
                else { Write-Warning 'The stale digitizer was left running.' }
            }
            'foreign' { }
            default { $waitForHealth = $true }
        }
    }
    if ($startDigitizer) {
        Write-Host 'Window 2: auto-digitizer (127.0.0.1:8721)'
        # Self-healing: builds the venv on first run, then goes straight to the
        # service. digitizer/pyproject.toml requires Python 3.12+, so the venv is
        # created through the launcher with an explicit version rather than
        # whatever a bare `python` resolves to.
        $digitizerCommand = @(
            "Set-Location -LiteralPath '$digitizerDir'"
            "if (-not (Test-Path '.venv\Scripts\python.exe')) { py -3.12 -m venv .venv; .venv\Scripts\python -m pip install -e '.[service,dev]' }"
            '.venv\Scripts\python -m digitizer_service'
        ) -join '; '
        Start-ServerWindow -Title 'EMB-Bot digitizer' -Command $digitizerCommand
        if ($null -eq $verdict) { $waitForHealth = [bool](Get-Command node -ErrorAction SilentlyContinue) }
    }
    else {
        Write-Host 'Window 2: not started - see the Digitizer line above.'
    }
}

Write-Host "Waiting for the Studio on port $Port (up to $TimeoutSeconds s)..."
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ready = $false
# Both loopbacks, each with a client built for its own address family.
# Vite binds the IPv6 loopback: it listens on [::1]:$Port with nothing on
# 127.0.0.1, so the old IPv4-literal probe never connected - this loop ran its
# full timeout on every launch and skipped opening the browser while the Studio
# was serving fine. Passing 'localhost' does not fix it (it resolves to
# 127.0.0.1 first and stops there), and neither does passing ::1 to a
# parameterless TcpClient, which is an IPv4 socket and refuses an IPv6 target
# even when something is listening on it. The digitizer, for its part, binds
# 127.0.0.1 - so both families have to be tried. (2026-08-26)
$loopbacks = @([System.Net.IPAddress]::Loopback, [System.Net.IPAddress]::IPv6Loopback)
while ((Get-Date) -lt $deadline) {
    foreach ($ip in $loopbacks) {
        $client = New-Object System.Net.Sockets.TcpClient($ip.AddressFamily)
        try {
            $client.Connect($ip, $Port)
            $ready = $true
        }
        catch {
            # Not listening on this loopback yet.
        }
        finally {
            $client.Dispose()
        }
        if ($ready) { break }
    }
    if ($ready) { break }
    Start-Sleep -Seconds 2
}

if ($ready -and $waitForHealth) {
    # The Studio is serving; a browser opened now would reach it before the
    # digitizer is up and show "service unavailable". Wait for /health too,
    # with at least 30 s of its own (the venv build can outlast the Studio).
    $left = [int][Math]::Max(30, ($deadline - (Get-Date)).TotalSeconds)
    Write-Host "Waiting for the digitizer's /health on port $digitizerPort (up to $left s)..."
    & node $serviceCheck --url $digitizerUrl --wait $left
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'The digitizer did not answer /health. Opening the Studio anyway; image auto-digitize will fail until it is up.'
    }
}

if ($ready) {
    $url = "http://localhost:$Port"
    Write-Host "Studio is up - opening $url"
    Start-Process $url
}
else {
    Write-Warning "Nothing is listening on port $Port after $TimeoutSeconds s."
    Write-Warning 'Check the Studio window: a predev failure in copy-engine.mjs stops Vite before it starts,'
    Write-Warning 'and Vite auto-increments to 5174/5175 when the port is taken (re-run with -Port <n>).'
}
