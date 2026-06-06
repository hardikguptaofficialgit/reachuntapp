# Fast run — no pause every 100; only waits if Mailmeteor rate-limits
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python enrich_emails.py --browser brave --fast
