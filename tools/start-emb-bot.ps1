#Requires -Version 5.1
<#
.SYNOPSIS
    Start EMB-Bot locally and open it in the default browser.

.DESCRIPTION
    Opens the Studio dev server (and, unless -NoDigitizer, the Python
    auto-digitizer service) in their own PowerShell windows, waits until the
    Studio's port actually accepts a TCP connection, then opens the browser.

    Both servers block their window until Ctrl+C, which is why each gets its
    own. Closing a window stops that server.

    The repo root is resolved from this script's own location, so the repo can
    be moved or cloned anywhere without editing this file.

.PARAMETER NoDigitizer
    Skip the Python auto-digitizer. Text and lettering work without it; only
    image auto-digitize needs it.

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
#>
[CmdletBinding()]
param(
    [switch]$NoDigitizer,
    [int]$Port = 5173,
    [int]$TimeoutSeconds = 180
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $repo 'app'
$digitizerDir = Join-Path $repo 'digitizer'

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

Write-Host "Repo:   $repo"
Write-Host 'Window 1: Studio (npm run dev)'
Start-ServerWindow -Title 'EMB-Bot Studio' -Command "Set-Location -LiteralPath '$appDir'; npm install; npm run dev"

if ($NoDigitizer) {
    Write-Host 'Window 2: skipped (-NoDigitizer) - image auto-digitize will be unavailable.'
}
else {
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
}

Write-Host "Waiting for the Studio on port $Port (up to $TimeoutSeconds s)..."
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ready = $false
while ((Get-Date) -lt $deadline) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $Port)
        $ready = $true
    }
    catch {
        # Not listening yet.
    }
    finally {
        $client.Dispose()
    }
    if ($ready) { break }
    Start-Sleep -Seconds 2
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
