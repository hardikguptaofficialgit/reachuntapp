# Run ONCE before the full job — pass Cloudflare in the Chrome window
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python warmup_mailmeteor.py
