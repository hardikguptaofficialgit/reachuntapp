# Step 3 — Mailmeteor emails (uses existing fast Mailmeteor on port 9222)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python run_startups.py --emails-only
