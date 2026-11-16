$S = "C:\Users\EE-LT-11030\AppData\Local\Temp\claude\1d26d9031c2a3c2e\cf6eeac5-519a-4750-a4a8-5870e3b08bcb\scratchpad\rule7"
Set-Location "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer"
$py = ".venv\Scripts\python.exe"
foreach ($j in @("becker_hat_large","hotel_fremont_patch","golf_hat","mfab_hat","machine_hat","precision_drone","gaulke_roofing_hat")) {
  $o = "$S\ours\$j"
  New-Item -ItemType Directory -Force $o | Out-Null
  $t = Get-Date
  & $py -m tools.pro_pair --job $j --out $o > "$o\log.txt" 2>&1
  $code = $LASTEXITCODE
  "EXIT=$code secs=$([int]((Get-Date)-$t).TotalSeconds)" | Add-Content "$o\log.txt"
  "$j EXIT=$code secs=$([int]((Get-Date)-$t).TotalSeconds)" | Add-Content "$S\ours\progress.txt"
}
"ALLDONE" | Add-Content "$S\ours\progress.txt"
