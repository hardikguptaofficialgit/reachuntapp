# Step 2 — Fetch founder LinkedIn URLs for all startups (530)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python run_startups.py --linkedin-only
