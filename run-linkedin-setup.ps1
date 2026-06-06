# Step 1 — Log into LinkedIn ONLY (no startup search, no Mailmeteor)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python run_startups.py --login-only
