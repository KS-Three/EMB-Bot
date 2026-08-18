# Curve-fidelity tol ladder — shape-fidelity plan Task 2.
# Three sequential arms; each preps both lanes for all 15 designs.
$ErrorActionPreference = 'Continue'
$WT  = 'C:\Users\EE-LT-11030\Personal\EMB-Bot\.claude\worktrees\shape-fidelity'
$PY  = 'C:\Users\EE-LT-11030\Personal\EMB-Bot\digitizer\.venv\Scripts\python.exe'
$log = Join-Path $WT 'parity_out_ladder\ladder.log'
Set-Location (Join-Path $WT 'digitizer')

foreach ($arm in @(@('020', '0.2'), @('010', '0.1'), @('005', '0.05'))) {
    $tag = $arm[0]; $tol = $arm[1]
    "########## ARM tol=$tol -> tol$tag ##########" | Tee-Object -FilePath $log -Append
    $env:PRO_PARITY_OUT = Join-Path $WT "parity_out_ladder\tol$tag"
    $env:PRO_PARITY_SIMPLIFY_TOL = $tol
    & $PY tools\pro_parity\prep_both.py 2>&1 | Tee-Object -FilePath $log -Append
}
'LADDER COMPLETE' | Tee-Object -FilePath $log -Append
