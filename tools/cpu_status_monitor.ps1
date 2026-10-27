# Shared CPU status for the two EMB-Bot foremen (director + "Embot stitch out files").
# Kent 2026-10-26: "work with the other Code session to monitor CPU, that's been the limiting factor."
# The slot rules it prints: docs/superpowers/plans/2026-10-27-director-handoff.md section 5.
# Run: pwsh -NoProfile -ExecutionPolicy Bypass -File tools/cpu_status_monitor.ps1 -HotPct 90 -HotExitSamples 0
# Status only: slot 2 is opened/closed by the other foreman's cpu_watchdog.ps1, not here.
# Writes %TEMP%\embwt\cpu_status.txt (read it before starting any heavy run) and appends cpu_log3.csv.
# STATE comes from BUSY time (100 - % Idle Time). % Processor Utility is NOT used for it: when the
# laptop throttles (clock 70%), utility = busy x clock and sits at 70 under full load (measured 10-26).
# Also logged: utility, clock %, processor queue length (threads waiting; >16 on 8 cores = saturated).
# Exits 3 when busy stays >= HotPct for HotExitSamples cycles, so the director is woken to act (0 = never exit).
# -CalmExitSamples N (0 = off): exit 4 once busy stays under CalmPct for N cycles (Kent 2026-10-26:
# "Pause your 3 new teams' heavy runs until CPU busy is under 85%" - the exit wakes the director to resume them).
param([int]$MaxHours = 10, [int]$HotPct = 95, [int]$BusyPct = 80, [int]$HotExitSamples = 8, [int]$CalmPct = 85, [int]$CalmExitSamples = 0)

$dir    = 'C:\Users\EE-LT-11030\AppData\Local\Temp\embwt'
$status = Join-Path $dir 'cpu_status.txt'
$cores  = [Environment]::ProcessorCount
$log    = Join-Path $dir 'cpu_log3.csv'
if (-not (Test-Path $log)) { 'time,busy_pct,busy_avg2m,util_pct,clock_pct,queue,state,free_gb,slot1,slot2,python_pct,claude_pct,system_pct' | Out-File $log -Encoding utf8 }

function Slot($name) {
    $p = Join-Path $dir $name
    if (-not (Test-Path $p)) { return @{ text = 'free'; short = 'free' } }
    $age = [int]((Get-Date) - (Get-Item $p).CreationTime).TotalMinutes
    $h = (Get-Content (Join-Path $p 'holder.txt') -ErrorAction SilentlyContinue | Select-Object -First 2) -join ' | '
    if (-not $h) { $h = '(no holder.txt)' }
    # A WATCHDOG holder (the other foreman's cpu_watchdog.ps1 closing slot 2) is never stale; a job past the 20-min cap is flagged.
    $flag = if ($h -match 'WATCHDOG') { '' } elseif ($age -gt 90) { '  STALE? held over 90 min' } elseif ($age -gt 20) { '  OVER 20-min cap: release between jobs' } else { '' }
    return @{ text = "HELD $age min :: $h$flag"; short = "held${age}m" }
}
function Cut($s, $n) { $s = "$s"; if ($s.Length -gt $n) { $s.Substring(0, $n) } else { $s } }

$hist = New-Object System.Collections.Generic.List[double]
$end = (Get-Date).AddHours($MaxHours)
$hot = 0; $calm = 0; $cycle = 0; $jobs = @('  (not read yet)')
while ((Get-Date) -lt $end) {
    $cs = (Get-Counter '\Processor Information(_Total)\% Processor Utility', '\Processor Information(_Total)\% Processor Performance', '\Processor(_Total)\% Idle Time', '\System\Processor Queue Length' -SampleInterval 5 -MaxSamples 6 -ErrorAction SilentlyContinue).CounterSamples
    function AvgOf($pat) { [math]::Round((($cs | Where-Object Path -like $pat).CookedValue | Measure-Object -Average).Average, 0) }
    $util = [math]::Min(100, (AvgOf '*utility*')); $clock = AvgOf '*performance*'; $queue = AvgOf '*queue length*'
    $busy = [math]::Max(0, [math]::Min(100, 100 - (AvgOf '*idle time*')))
    $hist.Add($busy); while ($hist.Count -gt 4) { $hist.RemoveAt(0) }
    $avg = [math]::Round(($hist | Measure-Object -Average).Average, 0)
    $state = if ($avg -ge $HotPct) { 'HOT' } elseif ($avg -ge $BusyPct) { 'BUSY' } else { 'OK' }
    $freeGb = [math]::Round((Get-Counter '\Memory\Available MBytes' -ErrorAction SilentlyContinue).CounterSamples[0].CookedValue / 1024, 1)

    $byName = @{}
    $procs = (Get-Counter '\Process(*)\% Processor Time' -SampleInterval 3 -MaxSamples 1 -ErrorAction SilentlyContinue).CounterSamples |
        Where-Object { $_.InstanceName -notin '_total', 'idle' }
    foreach ($s in $procs) {
        $n = $s.InstanceName -replace '#\d+$', ''
        $byName[$n] = ($byName[$n] + $s.CookedValue / $cores)
    }
    $top = $byName.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 7 |
        ForEach-Object { '{0} {1:N0}%' -f $_.Key, $_.Value }
    $pyPct = [math]::Round($byName['python'], 0); $clPct = [math]::Round($byName['claude'], 0); $syPct = [math]::Round($byName['system'], 0)

    # Command lines need WMI (wmiprvse costs CPU), so read them only every 4th cycle.
    if ($cycle % 4 -eq 0) {
        # One line per ROOT python job (a python child of a python is the same job), tagged with
        # whether any ancestor shell names the cpu.lock slots (a lock-aware wrapper) or not.
        $pmap = @{}
        Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='bash.exe'" -ErrorAction SilentlyContinue |
            ForEach-Object { $pmap[[int]$_.ProcessId] = $_ }
        $jobs = @($pmap.Values | Where-Object { $_.Name -eq 'python.exe' -and "$($_.CommandLine)" -match 'pytest|pro_pair|flip_sheet|digitiz|tools\.|scratchpad|-I ' } |
            Where-Object { $par = $pmap[[int]$_.ParentProcessId]; -not ($par -and $par.Name -eq 'python.exe') } |
            ForEach-Object {
                $tag = 'NO LOCK SEEN'; $a = $pmap[[int]$_.ParentProcessId]
                for ($i = 0; $i -lt 5 -and $a; $i++) {
                    if ("$($a.CommandLine)" -match 'embwt/cpu\.lock') { $tag = 'lock-aware'; break }
                    $a = $pmap[[int]$a.ParentProcessId]
                }
                '  pid {0} [{1}]: {2}' -f $_.ProcessId, $tag, (Cut ($_.CommandLine -replace '\s+', ' ' -replace '^"[^"]*python\.exe"\s*', '') 150)
            })
        if (-not $jobs) { $jobs = @('  (none)') }
    }
    $cycle++

    $s1 = Slot 'cpu.lock'; $s2 = Slot 'cpu.lock2'
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $body = @(
        "updated $stamp (every ~40 s; cpumon.ps1 pid $PID, run by the director session)"
        "STATE=$state   CPU busy now $busy%, 2-min avg $avg%   threads waiting $queue   clock $clock%   utility $util%   free RAM $freeGb GB   ($cores cores)"
        "slot1 cpu.lock : $($s1.text)"
        "slot2 cpu.lock2: $($s2.text)"
        "top (% of machine): $($top -join ', ')"
        'python jobs (refreshed every ~2.5 min):'
    ) + $jobs + @(
        ''
        'RULES (both foremen, every worker; Kent 2026-10-26 "2 lock slots + 3 workers (Recommended)"):'
        '- A heavy run (digitize, flip-sheet batch, census, pytest over 5 min) needs a FREE slot: mkdir the slot dir + holder.txt, rm -r it when done.'
        '- Try cpu.lock, then cpu.lock2; rm -r only the one you took. About 20 min per take: release between jobs. slot 2 only when line 2 reads OK.'
        '- If cpu.lock2 holder says WATCHDOG, slot 2 is closed (CPU idle < 15% for 1 min; reopens after 5 min idle > 40%).'
        '- FAIR TURNS: poll for a slot no more often than every 30 s; after you RELEASE a slot, wait 90 s before trying again.'
        '- Never two MFab jobs at once. pytest -n 2 max. When line 2 reads HOT: start nothing heavy; holders finish the current job and release.'
        '- Scripts: read the state from the start of line 2 only (anchored match); no other line spells the state key.'
    )
    $tmp = "$status.tmp"
    $body | Out-File $tmp -Encoding utf8
    # A reader holding the file open makes the swap fail; skip this write and try again next cycle.
    try { Move-Item -Force $tmp $status -ErrorAction Stop } catch { }
    "$stamp,$busy,$avg,$util,$clock,$queue,$state,$freeGb,$($s1.short),$($s2.short),$pyPct,$clPct,$syPct" | Out-File $log -Append -Encoding utf8

    if ($avg -lt $CalmPct) { $calm++ } else { $calm = 0 }
    if ($CalmExitSamples -gt 0 -and $calm -ge $CalmExitSamples) {
        "CALM: CPU busy 2-min avg $avg% (under $CalmPct%) for $calm cycles. top: $($top -join ', ')"
        exit 4
    }
    if ($state -eq 'HOT') { $hot++ } else { $hot = 0 }
    if ($HotExitSamples -gt 0 -and $hot -ge $HotExitSamples) {
        "HOT: CPU busy 2-min avg $avg% (threads waiting $queue, clock $clock%) for $hot cycles. top: $($top -join ', ')"
        $jobs
        exit 3
    }
}
'max hours reached'
exit 0
