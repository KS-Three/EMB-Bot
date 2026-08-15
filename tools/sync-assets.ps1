<#
.SYNOPSIS
    Drop images and stitch files in digitizer/testdata/inbox/, run this, done.

.DESCRIPTION
    EMB-Bot's code reaches every Claude session automatically; its images never
    do. That asymmetry is why `becker logo.png` and the 37-file scratch_corpus/
    sat in MASTER_SCOPE's "Waiting on Kent" queue for months - not hard work,
    just files nobody in a session could see.

    This is the fix, and it is deliberately dumb: one folder, one command, any
    number of files. No per-file ceremony.

        1. Copy anything into digitizer\testdata\inbox\
        2. Run this script
        3. Say "I dropped files in the inbox" in a session

    Filenames are normalised (spaces and parentheses out, lowercase extension)
    because the rest of the pipeline refers to fixtures by name and a space in
    a path has already cost this project time.

    Staging is BY EXPLICIT PATH - never `git add -A`, per CLAUDE.md footgun #2,
    which exists because .claude/worktrees/ holds live uncommitted work that a
    blind stage would sweep up.

.PARAMETER Message
    Commit message. Defaults to a summary naming the files.

.PARAMETER NoPush
    Commit but do not push.

.EXAMPLE
    .\tools\sync-assets.ps1
    .\tools\sync-assets.ps1 -Message "becker logo + pro digitized version"
#>
[CmdletBinding()]
param(
    [string]$Message,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'

$repo  = Split-Path -Parent $PSScriptRoot
$inbox = Join-Path $repo 'digitizer\testdata\inbox'

if (-not (Test-Path $inbox)) {
    New-Item -ItemType Directory -Force -Path $inbox | Out-Null
    Write-Host "Created the inbox: $inbox" -ForegroundColor Green
    Write-Host "Put your files there and run this again."
    exit 0
}

# README.md and .gitkeep are the folder's own scaffolding, not dropped assets.
# Without this the script renames its own README to readme.md on every run.
$skip  = @('README.md', '.gitkeep')
$files = @(Get-ChildItem -Path $inbox -File | Where-Object { $skip -notcontains $_.Name })

if ($files.Count -eq 0) {
    Write-Host "Inbox is empty - nothing to sync." -ForegroundColor Yellow
    Write-Host "  $inbox"
    exit 0
}

Write-Host "Found $($files.Count) file(s) in the inbox." -ForegroundColor Cyan

# Normalise names. Collisions are renamed rather than overwritten - losing a
# file silently would be worse than an ugly name.
$renamed = @()
foreach ($f in $files) {
    $base = [IO.Path]::GetFileNameWithoutExtension($f.Name)
    $ext  = [IO.Path]::GetExtension($f.Name).ToLowerInvariant()

    $clean = $base -replace '\s*\(\d+\)\s*$', ''   # trailing " (1)" duplicate marker
    $clean = $clean -replace '[^\w\-]+', '_'       # anything not word/dash -> underscore
    $clean = $clean -replace '_+', '_'
    $clean = $clean.Trim('_').ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($clean)) { $clean = 'asset' }

    $target = "$clean$ext"
    $n = 2
    while ((Test-Path (Join-Path $inbox $target)) -and $target -ne $f.Name) {
        $target = "${clean}_$n$ext"
        $n++
    }

    if ($target -ne $f.Name) {
        Rename-Item -Path $f.FullName -NewName $target
        Write-Host "  $($f.Name)  ->  $target"
        $renamed += $target
    } else {
        Write-Host "  $target"
        $renamed += $target
    }
}

# Stage by explicit path. Never -A.
Push-Location $repo
try {
    git add -- 'digitizer/testdata/inbox'

    $staged = git diff --cached --name-only
    if (-not $staged) {
        Write-Host "`nNothing changed - these files are already committed." -ForegroundColor Yellow
        exit 0
    }

    if (-not $Message) {
        $names = ($renamed | Select-Object -First 4) -join ', '
        if ($renamed.Count -gt 4) { $names += ", +$($renamed.Count - 4) more" }
        $Message = "assets: add $names"
    }

    git commit -m $Message
    Write-Host "`nCommitted." -ForegroundColor Green

    if ($NoPush) {
        Write-Host "Skipped push (-NoPush)." -ForegroundColor Yellow
    } else {
        $branch = (git rev-parse --abbrev-ref HEAD).Trim()
        git push -u origin $branch
        Write-Host "Pushed to $branch." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host 'Now tell a Claude session: "I dropped files in the inbox"' -ForegroundColor Cyan
}
finally {
    Pop-Location
}
