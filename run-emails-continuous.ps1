# Overnight-friendly: slow pace + auto pause when Mailmeteor rate-limits
# Close results.csv in Excel. Leave PowerShell + automation Brave open.
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python enrich_emails.py --browser brave --continuous --delay 10 --jitter 6 --batch-size 60 --batch-cooldown 50
