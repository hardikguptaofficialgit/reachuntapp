# Pilot: 10 founders, automated
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python enrich_emails.py --browser brave --setup --limit 10
